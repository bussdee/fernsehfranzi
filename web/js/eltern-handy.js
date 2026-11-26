/* FernsehFranzi 3.3 - Eltern-Seite im Heimnetz (Handy/PC), neu aufgebaut.
 *
 * 4.5: Leiste unten nur noch Heute · Menü · Statistik. Das Menü zeigt große Kacheln in Gruppen (5.0: fünf); jede Kachel öffnet
 *      einen Bereich zu genau einem Thema (mit „‹ Menü“ und einem Satz, worum es geht). Die Zurück-Taste des Handys geht
 *      zurück. Die Einstellungskarten sind dieselben wie vorher, nur sortiert.
 * - früher: Leiste unten: Heute · Regeln · Apps · Bass · Mehr (je eine Seite statt einer langen Liste)
 * - echte Eingabefelder (Uhrzeit, Wochentage zum Antippen, Datum) statt "a | b | c"-Textzeilen
 * - speichert von selbst (kurz nach der Eingabe) und zeigt „Gespeichert ✔“; Fehler stehen am Feld
 * Die PIN prüft der Server; alle Änderungen gehen über dieselben /api/eltern/...-Aufrufe wie bisher.
 */
import { hole, sende, el, setzeElternToken, leseElternToken, BEREICHE, bereichVon } from "./gemeinsam.js";

const TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const SYMBOL_WAHL = [["film", "🎬 Film"], ["musik", "🎵 Musik"], ["lernen", "🎓 Lernen"], ["buch", "📚 Buch"],
                     ["haus", "🏠 Haus"], ["spiel", "🕹️ Spiel"], ["stern", "⭐ Stern"], ["web", "🌐 Internet"],
                     ["malen", "🎨 Malen"], ["tier", "🐾 Tiere"], ["ball", "⚽ Sport"], ["mond", "🌙 Mond"], ["video", "▶️ Video"]];
/* 4.6: Wovon geht die Zeit ab? Bildschirmzeit · Gaming-Zeit (Teil der Bildschirmzeit) · nur ein eigenes Limit · kein Limit.
 * Optional zusätzlich „höchstens X min“ je App. Sperrzeiten gelten für alle Apps. */
const ZEIT_WAHL = [["zaehlt", "Bildschirmzeit"], ["gaming", "Gaming-Zeit"], ["limit", "Nur eigenes Limit"], ["frei", "Kein Limit"]];
const ZEIT_KURZ = { zaehlt: "Bildschirmzeit", gaming: "Gaming-Zeit", limit: "eigenes Limit", frei: "kein Limit" };
const ZEIT_ERKLAERT = {
  zaehlt: "Zieht von der Bildschirmzeit ab (Zeit → Spielzeit & Sperrzeiten).",
  gaming: "Zieht von der Bildschirmzeit UND von der Gaming-Zeit ab – Spiele sind ein Teil der Bildschirmzeit.",
  limit: "Kostet keine Bildschirmzeit, hat aber eine eigene Höchstgrenze am Tag (unten eintragen).",
  frei: "Kostet keine Zeit – nur die Sperrzeiten gelten.",
};
const hatLimit = (app) => { const l = app.limit_min; return typeof l === "number" ? l > 0 : Boolean(l && (l.schultag || l.frei)); };
const zeitart = (app) => (["zaehlt", "gaming"].includes(app.zeit) ? app.zeit : hatLimit(app) ? "limit" : "frei");
const BUNDESLAND_HINWEIS = "Die Ferien stammen aus den amtlichen Tabellen der Kultusministerkonferenz und kommen mit den Updates – abgefragt wird kein fremder Dienst.";
const TYP_NAME = { web: "Webseite", hoerbuch: "Hörbücher", konsole: "Retro-Spiele", desktop: "Programm", youtube: "YouTube", video: "Videos" };
/* Symbole für eigene Sticker - nur solche, die die Emoji-Schrift am Fernseher sicher hat (sie steht in dieser Datei) */
const STICKER_SYMBOLE = ["🦄", "🌟", "🏆", "🥇", "💎", "👑", "🚀", "🌈", "🎉", "💖", "🧹", "🛏️", "🦷", "🍎", "🥦", "📚",
                         "✏️", "🎹", "🎤", "🐶", "🐱", "🦋", "🌻", "⚽", "🚲", "🏊", "🧩", "🎨", "🌙", "☀️"];
/* 6.0: Reiter unten statt Menü - jeder Reiter zeigt seine Bereiche als kurze Zeilen, ein Tipp klappt einen auf.
 * 6.9.38: sechs Reiter (Heute · Regeln · Apps · Franzi · Aussehen · Mehr). „Apps“ ist eine eigene Seite: Übersicht nach
 * Bereichen der Startseite, je App eine Detailseite mit allem, was zu ihr gehört (#apps/<id>). */
const LEISTE = [["heute", "🏠", "Heute"], ["regeln", "⏰", "Regeln"], ["apps", "🧩", "Apps"], ["franzi", "⭐", "Franzi"],
                ["aussehen", "🎨", "Aussehen"], ["mehr", "⚙️", "Mehr"]];
const REITER = {
  regeln: { titel: "Zeit und Regeln", bereiche: ["zeit", "abend", "erinnerungen", "internet"] },
  franzi: { titel: "Franzi & Mein Tag", bereiche: ["meintag", "sterne", "franzi", "shop"] },
  aussehen: { titel: "Aussehen und Klang", bereiche: ["design", "bildplaetze", "klaenge"] },
  mehr: { titel: "Familie, Gerät und Hilfe", bereiche: ["telegram", "bilder", "geraet", "hilfe"] },
};
/* Lesezeichen von früher führen weiter (auch die Reiter und Bereiche bis 6.9.37) */
const ALTE_SEITEN = { menue: "regeln", mehr_alt: "mehr", technik: "mehr", familie: "mehr", inhalte: "apps", statistik: "heute/statistik",
                      bass: "apps/spiel-bass", musik: "apps/spiel-bass", youtube: "apps/youtube", spiele: "apps",
                      wetter: "apps/spiel-wetter", schule: "apps/spiel-schule", kinderwelten: "apps/spiel-kinderwelten" };
const reiterVon = (bereich) => Object.keys(REITER).find((r) => REITER[r].bereiche.includes(bereich));

export function elternHandy(wurzel) {
  let d = null;                     /* Daten vom Server (wird beim Speichern mitgeändert) */
  /* Adresse: #reiter oder #reiter/bereich (aufgeklappt); ein einzelner Bereichsname führt in seinen Reiter */
  function ausAdresse() {
    const s = decodeURIComponent((location.hash || "#heute").slice(1)) || "heute";
    let [r, b] = s.split("/");
    if (!LEISTE.some(([id]) => id === r)) {
      const ziel = (b && ALTE_SEITEN[b]) || ALTE_SEITEN[r];
      if (ziel) [r, b] = ziel.split("/");
      else { b = r; r = reiterVon(r) || "heute"; }
    } else if (b && REITER[r] && !REITER[r].bereiche.includes(b) && reiterVon(b)) r = reiterVon(b);   /* z. B. #regeln/franzi */
    return { r, b: b || null };
  }
  let { r: seite, b: offen } = ausAdresse();
  const vonAdresse = () => { if (d) { ({ r: seite, b: offen } = ausAdresse()); zeichne(); } };
  window.addEventListener("popstate", vonAdresse);   /* Zurück-Taste des Handys */
  window.addEventListener("hashchange", vonAdresse);
  function geheZu(ziel, bereich = null) {
    seite = ziel; offen = bereich;
    history.pushState(null, "", "#" + ziel + (bereich ? "/" + bereich : ""));
    zeichne();
    if (bereich && ziel !== "apps") requestAnimationFrame(() => document.querySelector(`.eh-abschnitt[data-bereich="${bereich}"]`)?.scrollIntoView({ block: "start" }));
    else scrollTo(0, 0);
  }

  /* ---------------------------------------------------------------- Rückmeldung */
  const meldung = el("div", { class: "eh-meldung", role: "status" });
  let meldungTimer = 0;
  function zeige(text, fehler = false) {
    meldung.textContent = text;
    meldung.className = "eh-meldung zeigen" + (fehler ? " fehler" : "");
    clearTimeout(meldungTimer);
    meldungTimer = setTimeout(() => { meldung.className = "eh-meldung"; }, fehler ? 7000 : 1800);
  }
  const fehlerText = (e) => e.message + (e.daten?.details ? ": " + e.daten.details.join(" · ") : "");

  /* Speichern mit kurzer Verzögerung (beim Tippen nicht bei jedem Buchstaben) */
  const wartend = new Map();
  function speichere(schluessel, tun, { sofort = false, feld = null } = {}) {
    clearTimeout(wartend.get(schluessel));
    wartend.set(schluessel, setTimeout(async () => {
      wartend.delete(schluessel);
      try {
        await tun();
        feld?.classList.remove("eh-falsch");
        zeige("Gespeichert ✔");
      } catch (e) {
        feld?.classList.add("eh-falsch");
        zeige(fehlerText(e), true);
      }
    }, sofort ? 0 : 700));
  }
  const einstellung = (feld, wert, opt) => speichere("e:" + feld, () => sende("/api/eltern/einstellungen", { einstellungen: { [feld]: wert } }), opt);
  const familie = (opt) => speichere("familie", () => sende("/api/eltern/einstellungen", { einstellungen: { familie: d.familie } }), opt);
  const regeln = (opt) => speichere("zeit", () => sende("/api/eltern/einstellungen", { einstellungen: { zeit: d.regeln } }), opt);
  const apps = (opt) => speichere("apps", () => sende("/api/eltern/apps", { apps: d.apps }), opt);

  async function aktion(knopf, tun, danach = "Erledigt ✔") {
    knopf.disabled = true;
    try { await tun(); if (danach) zeige(danach); } catch (e) { zeige(fehlerText(e), true); } finally { knopf.disabled = false; }
  }

  /* ---------------------------------------------------------------- Bausteine */
  const knopf = (text, tun, art = "", danach) => {
    const k = el("button", { class: "eh-knopf " + art, type: "button", text });
    k.addEventListener("click", () => aktion(k, tun, danach));
    return k;
  };
  const karte = (titel, ...inhalt) => el("section", { class: "eh-karte" }, titel ? el("h3", { text: titel }) : null, ...inhalt);
  /* 6.0: lange Erklärungen klappen ein („ℹ️ Mehr dazu“), damit die Seiten kurz bleiben */
  const hilfe = (text) => (String(text).length <= 120 ? el("p", { class: "eh-hilfe", text })
    : el("details", { class: "eh-info" }, el("summary", { text: "ℹ️ " + String(text).split(/(?<=[.!?:])\s/)[0].slice(0, 90) + (String(text).length > 90 ? " …" : "") }),
      el("p", { class: "eh-hilfe", text })));
  /* 4.2: lange Sammlungen nach n Einträgen einklappen („… weitere anzeigen“), sonst werden die Seiten endlos */
  const kurzliste = (elemente, n = 5) => elemente.length <= n + 1 ? elemente : [...elemente.slice(0, n),
    el("details", { class: "eh-mehr" }, el("summary", { text: `${elemente.length - n} weitere anzeigen` }), ...elemente.slice(n))];
  const zeile = (beschriftung, ...rechts) => el("label", { class: "eh-zeile" }, el("span", { text: beschriftung }), el("span", { class: "eh-rechts" }, ...rechts));

  function eingabe(wert, bei, attr = {}) {
    const i = el("input", { value: wert ?? "", ...attr });
    i.addEventListener("input", () => bei(i.value, i));
    return i;
  }
  function zahl(wert, min, max, bei) {
    return eingabe(wert, (v, i) => { if (v !== "") bei(+v, i); }, { type: "number", min, max, inputmode: "numeric", class: "eh-zahl" });
  }
  function uhr(wert, bei) { return eingabe(wert, (v, i) => v && bei(v, i), { type: "time", class: "eh-uhr" }); }
  function schalter(an, bei) {
    const c = el("input", { type: "checkbox", class: "eh-schalter", role: "switch" });
    c.checked = Boolean(an);
    c.addEventListener("change", () => bei(c.checked, c));
    return c;
  }
  function segment(optionen, wert, bei) {
    const box = el("div", { class: "eh-segment" });
    const knoepfe = optionen.map(([w, t]) => {
      const k = el("button", { type: "button", text: t, class: w === wert ? "an" : "" });
      k.addEventListener("click", () => { knoepfe.forEach((x) => x.classList.toggle("an", x === k)); bei(w); });
      return k;
    });
    box.append(...knoepfe);
    return box;
  }
  function auswahl(optionen, wert, bei) {
    const s = el("select", {}, ...optionen.map(([w, t]) => { const o = el("option", { value: w, text: t }); o.selected = w === wert; return o; }));
    s.addEventListener("change", () => bei(s.value, s));
    return s;
  }
  /* 5.2: Klang aus dem Archiv wählen - ▶ hört am Handy, 📺 am Fernseher. 6.0: dazu die eigenen Klänge aus dem Klang-Ordner */
  let probeTon = null;
  let auszeitAuf = false;                               /* 6.0: Auszeit-Minuten auf „Heute“ aufgeklappt */
  /* 6.9.40: eigene Klänge je Ordner ("" = allgemeiner Klang-Ordner, sonst eine Art) - je Sitzung einmal geholt */
  const eigeneCache = new Map(), eigeneFehlerJe = new Map();
  let eigeneKlaenge = null, eigeneFehler = "";          /* allgemeiner Ordner (wie bisher) */
  const ordnerVon = (art) => (art ? d?.einstellungen?.klaenge?.ordner_arten?.[art] : d?.einstellungen?.klaenge?.ordner) || "";
  function eigeneLaden(neu = false, art = "") {
    if (eigeneCache.has(art) && !neu) return Promise.resolve(eigeneCache.get(art));
    const fertig = (l, f) => { eigeneCache.set(art, l); eigeneFehlerJe.set(art, f); if (!art) { eigeneKlaenge = l; eigeneFehler = f; } return l; };
    if (!ordnerVon(art)) return Promise.resolve(fertig([], ""));
    return hole("/api/eltern/klaenge-eigen" + (art ? "?art=" + art : "")).then((r) => fertig(r.klaenge || [], ""))
      .catch((e) => fertig([], e.message));
  }
  function klangWahl(wert, bei, { leer = "🔔 Gong (Standard)", leerId = "gong", art = "", nurEigene = false } = {}) {      /* 6.8.10: eigene Vorgabe (Timer-Musik) */
    const liste = nurEigene ? [] : (d.klaenge || []).filter((k) => k.id !== leerId);
    const s = auswahl([["", leer], ...liste.map((k) => [k.id, `${k.symbol} ${k.name}`])], wert || "", (v) => bei(v || null));
    const artName = (a) => (d.klang_arten || []).find((x) => x.id === a);
    const ordner = [...new Set([art, ""])].filter((a) => a === "" || ordnerVon(a));
    const gruppen = new Map();
    const eigeneGruppe = (a, namen) => {
      gruppen.get(a)?.remove();
      const vorne = a ? `eigen@${a}:` : "eigen:";
      const bekannt = new Set(namen.map((k) => k.id));
      if (wert && String(wert).startsWith(vorne) && !bekannt.has(wert)) namen = [...namen, { id: wert, name: wert.slice(vorne.length) + " (fehlt im Ordner)" }];
      if (!namen.length) return;
      const titel = a ? `${artName(a)?.symbol || "📁"} ${artName(a)?.name || a}` : "🎵 Eigene Klänge";
      const g = el("optgroup", { label: titel }, ...namen.map((k) => { const o = el("option", { value: k.id, text: "🎵 " + k.name }); o.selected = k.id === wert; return o; }));
      gruppen.set(a, g);
      s.append(g);
    };
    for (const a of ordner) {
      eigeneGruppe(a, eigeneCache.get(a) || []);
      if (!eigeneCache.has(a)) eigeneLaden(false, a).then((l) => eigeneGruppe(a, l));
    }
    const id = () => s.value || leerId;
    const hoeren = el("button", { type: "button", class: "eh-knopf rund", text: "▶", title: "Am Handy anhören" });
    hoeren.addEventListener("click", (e) => {
      e.preventDefault();
      if (id() === "stumm") { zeige("Ohne Ton – hier gibt es nichts zu hören."); return; }
      if (!id()) { zeige("Der eingebaute Ton kommt nur vom Fernseher."); return; }
      try { probeTon?.pause(); } catch (_) { /* weiter */ }
      probeTon = new Audio("/api/klang?id=" + encodeURIComponent(id()));
      probeTon.play().catch(() => zeige("Das Handy spielt den Ton gerade nicht ab.", true));
    });
    const tv = knopf("📺", () => (id() === "stumm" || !id() ? Promise.resolve() : sende("/api/eltern/klang-test", { klang: id() })), "rund", "Am Fernseher ✔");
    tv.title = "Am Fernseher anhören";
    return el("span", { class: "eh-klang" }, s, hoeren, tv);
  }
  function tageWahl(tage, bei) {
    const gewaehlt = new Set(tage && tage.length ? tage : [0, 1, 2, 3, 4, 5, 6]);
    const box = el("div", { class: "eh-tage" });
    TAGE.forEach((t, i) => {
      const k = el("button", { type: "button", text: t, class: gewaehlt.has(i) ? "an" : "" });
      k.addEventListener("click", () => {
        if (gewaehlt.has(i) && gewaehlt.size > 1) gewaehlt.delete(i); else gewaehlt.add(i);
        k.classList.toggle("an", gewaehlt.has(i));
        bei([...gewaehlt].sort());
      });
      box.append(k);
    });
    return box;
  }

  /* ---------------------------------------------------------------- Anmelden */
  function anmelden(fehler = "") {
    const feld = el("input", { type: "password", inputmode: "numeric", autocomplete: "current-password", placeholder: "PIN", class: "eh-pin" });
    const box = el("div", { class: "eh-fehlertext", text: fehler });
    const form = el("form", { class: "eh-anmelden" },
      el("div", { class: "eh-logo", text: "📺" }), el("h1", { text: "FernsehFranzi" }), el("p", { class: "eh-hilfe", text: "Eltern-Bereich" }),
      feld, el("button", { class: "eh-knopf haupt", type: "submit", text: "Anmelden" }), box,
      el("a", { href: "/anleitung.pdf", target: "_blank", text: "📖 Anleitung (PDF)" }));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try { setzeElternToken((await sende("/api/eltern/anmelden", { pin: feld.value })).token); laden(); }
      catch (err) { box.textContent = err.message; feld.value = ""; }
    });
    wurzel.replaceChildren(form);
    feld.focus();
  }

  async function laden() {
    try { d = await hole("/api/eltern/daten"); } catch (_) { return anmelden(); }
    zeichne();
  }

  function zeichne() {
    const inhalt = el("main", { class: "eh-inhalt" });
    if (!LEISTE.some(([id]) => id === seite)) seite = "heute";
    const aktiv = seite;
    const leiste = el("nav", { class: "eh-leiste" }, ...LEISTE.map(([id, symbol, name]) => {
      const a = el("a", { href: "#" + id, class: id === aktiv ? "an" : "" }, el("span", { text: symbol }), el("small", { text: name }));
      a.addEventListener("click", (e) => { e.preventDefault(); geheZu(id); });
      return a;
    }));
    const h = d.heute;
    const kopf = el("header", { class: "eh-kopf" }, el("b", { text: "📺 FernsehFranzi" }),
      el("span", { class: "eh-chip" + (d.gesperrt ? " rot" : ""), text: d.gesperrt ? "gesperrt" : h.ohne_limit ? "ohne Limit" : `${h.rest_min ?? "–"} min übrig` }));
    if (seite === "heute") inhalt.append(...seiteHeute(), abschnitt("heute", "statistik", { symbol: "📊", titel: "Statistik",
      text: "Was wann wie lange lief", inhalt: () => seiteStatistik() }));
    else if (seite === "apps") inhalt.append(...seiteApps());
    else inhalt.append(...seiteReiter(seite));
    wurzel.replaceChildren(kopf, inhalt, leiste, meldung);
  }

  /* ================================================================ 4.5: Menü und Bereiche */
  function bereiche() {
    const tg = d.einstellungen.telegram || {};
    const blockiert = Object.entries(d.domains || {}).filter(([h, x]) => x.blockiert > 0 && !(d.einstellungen.whitelist?.zusatz || []).includes(h)).length;
    const r = () => seiteRegeln(), m = () => seiteMehr();
    return {
      zeit: { symbol: "⏰", titel: "Spielzeit & Sperrzeiten", text: "Wie lange am Tag gespielt werden darf, wann Pause ist, Ferien.",
              status: `${d.regeln.budget_min.schultag} / ${d.regeln.budget_min.frei} min am Tag` + (d.erst_dann?.aktiv ? " · Erst-dann" : ""),
              inhalt: () => { const x = r(); return [x.timer, karteErstDann(), x.sperrzeiten, x.ferien]; } },
      abend: { symbol: "🌙", titel: "Gute Nacht & Wecker", text: "Hörbuch zum Einschlafen und der Wecker am Morgen.",
               status: d.apps.find((a) => a.id === "gute-nacht")?.start ? "" : "Hörbuch-Ordner fehlt", warn: !d.apps.find((a) => a.id === "gute-nacht")?.start, inhalt: () => { const x = r(); return [x.gutenacht, x.wecker]; } },
      erinnerungen: { symbol: "🔔", titel: "Erinnerungen & Pausen", text: "Erinnerungen zur Uhrzeit, Bewegungspause, Lernen bringt Spielzeit.",
                      status: `${(d.familie.erinnerungen || []).length} Erinnerungen`, inhalt: () => { const x = r(); return [x.erinnerungen, x.bewegung, x.lernbonus]; } },
      /* 6.2 */
      meintag: { symbol: "📋", titel: "Mein Tag (Routinen)", text: "Listen zum Abhaken, Zahnputz-Timer, Aufgaben mit Sternen, Ranzen-Check, Lesepass.",
                 status: d.meintag.aktiv ? `${d.meintag.routinen.length} Listen · ${d.meintag.aufgaben.length} Aufgaben`
                   : d.meintag.routinen.length || d.meintag.aufgaben.length ? "angelegt, aber aus" : "aus",
                 warn: !d.meintag.aktiv && Boolean(d.meintag.routinen.length || d.meintag.aufgaben.length),
                 inhalt: () => [karteMeinTag(), karteAufgaben(), karteRanzen(), karteLesen()] },
      /* 6.9.38 */
      sterne: { symbol: "🌟", titel: "Sterne & Level", text: "Wofür es Sterne gibt, was die Level bringen, Tausch gegen Spielzeit.",
                status: d.meintag.aktiv ? `⭐ ${d.meintag_heute?.sterne ?? 0} · Level ${d.meintag_heute?.level ?? 1}` : "", inhalt: () => [karteSterne()] },
      /* 6.9 */
      franzi: { symbol: "🐾", titel: "Franzi als Haustier", text: "Ein- und ausschalten, Abenteuer-Pause, Geburtstag, Zeit bei Franzi.",
                status: d.franzi.aktiv ? "an" : "aus", inhalt: () => [karteFranzi(), karteSprueche()] },
      shop: { symbol: "🛍️", titel: "Sterne-Shop", text: "Eure Angebote (Spielzeit …), Preise für Spiele, Kleidung, Möbel; schenken.",
              status: d.franzi.aktiv ? `${d.franzi.angebote.length} Angebote` : "Franzi aus", inhalt: () => [karteShop()] },
      /* 6.9.52 */
      bildplaetze: { symbol: "🧩", titel: "Bild-Plätze", text: "Räume, Postkarten, Briefmarken, Franzis Augen und Münder durch eigene Bilder ersetzen.",
                     status: (() => { const n = (d.bildplaetze || []).filter((b) => b.eigen).length; return n ? `${n} eigene` : ""; })(),
                     inhalt: () => karteBildplaetze() },
      klaenge: { symbol: "🎵", titel: "Klänge & Lautstärke", text: "Lautstärke, Klang je Ereignis, Klang-Ordner je Art, Hintergrundmusik.",
                 status: Object.values(d.einstellungen.klaenge?.ereignisse || {}).some(Boolean) ? "eigene Auswahl" : "",
                 inhalt: () => { const x = r(); return [x.lautstaerke, karteKlangEreignisse(), x.klaengeEigen, karteMusik()]; } },
      telegram: { symbol: "💬", titel: "Telegram & Kontakte", text: "Nachrichten und Fotos ans Handy, Freunde freigeben, mitlesen.",
                  status: tg.aktiv ? `${(tg.chats || []).length} Kontakte` : "aus", inhalt: () => [m().telegram, karteHilfe()] },
      bilder: { symbol: "🖼️", titel: "Bilder & Fotoalbum", text: "Gemalte Bilder ansehen, Fotoalbum und Speicherplatz.",
                status: d.speicher ? `${d.speicher.belegt_mb} von ${d.speicher.limit_mb} MB` + (d.speicher.voll ? " – voll" : "") : "", warn: Boolean(d.speicher?.voll), inhalt: () => { const x = m(); return [x.fotoalbum, x.bilder]; } },
      /* 5.0 */
      design: { symbol: "🎨", titel: "Farben & Animationen", text: "Farben der Startseite, abends automatisch dunkel, wie viel sich bewegt.",
                status: `${d.design.erlaubt.length} Farben` + (d.design.abend_aktiv ? ` · abends ab ${d.design.abend_ab} dunkel` : ""),
                inhalt: () => [karteDesign(), karteHintergruende()] },
      internet: { symbol: "🌐", titel: "Internetseiten", text: "Welche Seiten der Fernseher laden darf.",
                  status: blockiert ? `${blockiert} blockiert` : "", warn: blockiert > 0, inhalt: () => { const x = m(); return [karteFragen(), x.internet, x.zusatz]; } },
      geraet: { symbol: "🔧", titel: "Gerät", text: "Name, Bildschirmschoner, Standby, Bluetooth, Retro-Bilder, Sicherung, Neustart.",
                status: `Version ${d.version || ""}`, inhalt: () => { const x = m(); return [x.geraet, karteBildschirm(), x.bluetooth, x.scraper, x.sicherung]; } },
      hilfe: { symbol: "📖", titel: "Hilfe & Anleitungen", text: "Handbuch, Kurzanleitung zum Ausdrucken, Anleitung für Kinder.",
               status: "", inhalt: () => [m().anleitungen, karte("So funktioniert diese Seite",
                 hilfe("Unten: „Heute“ für das Wichtigste (Zeit, Nachricht, Ton, Statistik), „Regeln“ für Zeit und Internet, „Apps“ für jede Kachel mit allem, was dazugehört, „Franzi“ für Mein Tag, Sterne und Shop, „Aussehen“ für Farben und Klänge, „Mehr“ für Familie, Gerät und Hilfe."),
                 hilfe("Es gibt keine Speichern-Knöpfe: Jede Änderung wird kurz nach der Eingabe gespeichert, unten erscheint „Gespeichert ✔“."),
                 hilfe("Die Seite geht nur im Heimnetz. Von unterwegs steuert ihr den Fernseher über Telegram (/status, /zeit 30 …)."))] },
    };
  }

  /* 6.0: ein Reiter = Liste seiner Bereiche; der aufgeklappte zeigt seine Einstellungen */
  function seiteReiter(r) {
    const alle = bereiche();
    return [el("h2", { class: "eh-reiter-titel", text: REITER[r].titel }),
            ...REITER[r].bereiche.map((id) => abschnitt(r, id, alle[id]))];
  }
  function abschnitt(r, id, b) {
    const auf = offen === id;
    const kopf = el("button", { type: "button", class: "eh-abschnitt-kopf", "aria-expanded": String(auf) },
      el("span", { class: "eh-kachel-symbol", text: b.symbol }),
      el("span", { class: "eh-kachel-text" }, el("b", { text: b.titel }), el("small", { text: b.text })),
      b.status ? el("span", { class: "eh-kachel-status" + (b.warn ? " warn" : ""), text: b.status }) : null,
      el("span", { class: "eh-pfeil", text: auf ? "▾" : "▸" }));
    kopf.addEventListener("click", () => (auf ? geheZu(r) : geheZu(r, id)));
    return el("section", { class: "eh-abschnitt" + (auf ? " offen" : ""), "data-bereich": id }, kopf,
      auf ? el("div", { class: "eh-abschnitt-inhalt" }, ...b.inhalt().filter(Boolean)) : null);
  }

  /* ================================================================ Heute */
  function seiteHeute() {
    const h = d.heute;
    const nachricht = el("input", { type: "text", maxlength: 140, placeholder: "Nachricht an den Fernseher …", class: "eh-breit" });
    /* 5.3: Absender - die Eltern-Kontakte aus Telegram; jedes Handy merkt sich seine Wahl */
    const elternKontakte = (d.einstellungen.telegram?.chats || []).filter((c) => c.eltern !== false && Number.isInteger(c.id));
    let von = "";
    try { von = localStorage.getItem("ff-eltern-von") || ""; } catch (_) { /* ohne */ }
    if (!elternKontakte.some((c) => String(c.id) === von)) von = "";
    const vonWahl = elternKontakte.length ? zeile("Von", auswahl([["", "Mama oder Papa"],
      ...elternKontakte.map((c) => [String(c.id), `${c.symbol || "💬"} ${c.name}`])], von, (v) => {
        von = v; try { localStorage.setItem("ff-eltern-von", v); } catch (_) { /* ohne */ }
      })) : null;
    const senden = async (text) => { await sende("/api/eltern/nachricht", { text, von: von ? Number(von) : null }); nachricht.value = ""; };
    const sendenKnopf = el("button", { class: "eh-knopf haupt", type: "submit", text: "Senden" });
    const form = el("form", { class: "eh-reihe eng" }, nachricht, sendenKnopf);
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      if (nachricht.value.trim()) aktion(sendenKnopf, () => senden(nachricht.value), "Gesendet ✔");
    });
    const woche = Object.entries(d.woche || {}).slice(-7);
    const groesste = Math.max(30, ...woche.map(([, w]) => w.genutzt_min));
    const ton = d.ton_jetzt || d.einstellungen.ton?.ziel || "hdmi";
    return [
      d.zeit_pruefen ? karte("", el("b", { text: "Neu in 3.4: Sperrzeiten" }),
        hilfe("Die Zeitregeln wurden übernommen (Zeitfenster → Sperrzeiten „Nacht“ und „Schule“). Bitte unter Regeln und bei den Apps kurz prüfen."),
        el("div", { class: "eh-reihe" }, knopf("Zu den Regeln", () => { geheZu("regeln", "zeit"); return Promise.resolve(); }, "haupt", ""),
          knopf("✔ Gesehen", () => sende("/api/eltern/einstellungen", { einstellungen: { zeit: d.einstellungen.zeit } }).then(() => { d.zeit_pruefen = false; zeichne(); }), "leise", ""))) : null,   /* 6.9.65 */
      (d.sperrzeiten_jetzt || []).length ? karte("", el("div", { text: `🌙 Gerade Sperrzeit: ${d.sperrzeiten_jetzt.join(", ")}` })) : null,
      karte("", el("div", { class: "eh-gross", text: d.gesperrt?.auszeit ? `⏳ Auszeit bis ${d.gesperrt.bis_uhr}`
                                                    : d.gesperrt ? "🔒 gesperrt" : h.ohne_limit ? "ohne Limit" : `${h.rest_min ?? "–"} min` }),
        el("div", { class: "eh-hilfe", text: `übrig heute (${h.tagesart === "frei" ? "freier Tag" : "Schultag"}) · gespielt ${h.genutzt_min} min` +
                                           (h.gaming_rest_min != null ? ` · davon Gaming ${h.gaming_min ?? 0} min (noch ${h.gaming_rest_min} min)` : "") +
                                           (h.bonus_min ? ` · Bonus ${h.bonus_min} min` : "") }),
        el("div", { class: "eh-reihe" },
          knopf("+15 min", () => sende("/api/eltern/bonus", { art: "15" }).then(laden)),
          knopf("+30 min", () => sende("/api/eltern/bonus", { art: "30" }).then(laden)),
          knopf("ohne Limit", () => sende("/api/eltern/bonus", { art: "ohne_limit" }).then(laden))),
        /* 6.0: Sperren und Auszeit nebeneinander; die Auszeit-Minuten klappen erst beim Antippen auf */
        d.gesperrt ? el("div", { class: "eh-reihe" }, knopf(d.gesperrt.auszeit ? "🔓 Auszeit beenden" : "🔓 Fernseher freigeben",
                           () => sende("/api/eltern/sperre", { frei: true }).then(laden), "haupt"),
                           d.gesperrt.auszeit ? auszeitSchalter("⏳ Verlängern") : null)
                   : el("div", { class: "eh-reihe" },
                       knopf("🔒 Sperren", () => sende("/api/eltern/sperre", { text: "Der Fernseher macht jetzt Pause." }).then(laden), "gefahr"),
                       auszeitSchalter("⏳ Auszeit …")),
        auszeitAuf ? karteAuszeit() : null),
      karte("Nachricht", vonWahl, form,
        el("div", { class: "eh-chips" }, ...["Essen ist fertig!", "Bitte Zähne putzen!", "In 5 Minuten ausschalten, bitte.", "Komm mal kurz zu mir"]
          .map((t) => knopf(t, () => senden(t), "chip", "Gesendet ✔")))),
      karte("Fernseher",
        zeile("Ton", segment([["hdmi", "Fernseher"], ["klinke", "Klinke"], ...(d.kopfhoerer ? [["kopfhoerer", "🎧 Kopfhörer"]] : [])], ton,
          (z) => speichere("ton", async () => {
            await sende("/api/eltern/ton", { ziel: z });
            if (z !== "kopfhoerer") d.einstellungen.ton = { ...(d.einstellungen.ton || {}), ziel: z };
            d.ton_jetzt = z;
          }, { sofort: true }))),
        zeile("Lautstärke", knopf("–", () => sende("/api/eltern/lautstaerke", { richtung: "leiser" }), "rund", ""),
          knopf("+", () => sende("/api/eltern/lautstaerke", { richtung: "lauter" }), "rund", "")),
        fotoBereich(),
        el("div", { class: "eh-reihe" },
          knopf("🌙 Gute Nacht starten", () => sende("/api/eltern/gute-nacht"), "", "Gute Nacht läuft ✔"),
          knopf("📴 Fernseher aus", () => sende("/api/eltern/fernseher-aus"), "gefahr"))),
      (d.meldungen || []).length ? karte("Nachrichten und Erinnerungen", ...kurzliste(d.meldungen.map((m) => el("div", { class: "eh-eintrag" },
        el("div", { class: "eh-app-name" }, el("b", { text: m.text }),
          el("small", { text: `${m.quelle ? m.quelle + " · " : ""}${m.zeit.slice(11, 16)} Uhr` })),
        el("small", { class: m.gesehen ? "eh-gut" : "eh-warn", text: m.gesehen ? `gesehen ${m.gesehen.slice(11, 16)} ✔` : "noch nicht gesehen" }))), 3)) : null,
      woche.length ? karte("Letzte 7 Tage", el("div", { class: "eh-balken" }, ...woche.map(([tag, w]) =>
        el("div", { title: `${w.genutzt_min} min` }, el("i", { style: `height:${Math.round(w.genutzt_min / groesste * 100)}%` }),
          el("small", { text: TAGE[(new Date(tag).getDay() + 6) % 7] }), el("b", { text: String(w.genutzt_min) })))),
        hilfe("Minuten Spielzeit pro Tag (nur was zählt)")) : null,
      fragenHeute(),
      meintagHeute(),
      karte("Lernen und Bass",
        el("div", { text: `Heute gelernt: ${d.lernstand.bestaetigt_min} min bestätigt` + (d.lernstand.offen_min ? `, ${d.lernstand.offen_min} min offen` : "") +
                          (d.lernstand.bonus_min ? ` · Bonus ${d.lernstand.bonus_min} min` : "") }),
        el("div", { text: d.bass_tagebuch.serie ? `🎸 ${d.bass_tagebuch.serie} Tage am Stück geübt · insgesamt ${d.bass_tagebuch.gesamt_min} min`
                                                : `🎸 insgesamt ${d.bass_tagebuch.gesamt_min} min geübt` })),
    ].filter(Boolean);
  }

  /* ================================================================ Regeln */
  function seiteRegeln() {
    const r = d.regeln, f = d.familie;
    const timer = (art, topf = "budget_min") => zeile(art === "schultag" ? "Schultag" : "Wochenende & Ferien",
      zahl(r[topf][art], 0, 1440, (v, i) => { r[topf][art] = v; regeln({ feld: i }); }), el("small", { text: "min" }));

    const sperrBox = el("div", { class: "eh-liste" });
    const zeichneSperren = () => sperrBox.replaceChildren(...r.sperrzeiten.map((s, n) => el("div", { class: "eh-eintrag spalte eh-sperre" },
      el("div", { class: "eh-reihe eng" },
        eingabe(s.name, (v, i) => { const alt = s.name; s.name = v.trim(); if (s.name) { umbenennen(alt, s.name); regeln({ feld: i }); } },
          { type: "text", maxlength: 30, placeholder: "Name, z. B. Nacht", class: "eh-breit fett" }),
        knopf("×", () => { if (!confirm(`Sperrzeit „${s.name}“ löschen?`)) return Promise.resolve();
          r.sperrzeiten.splice(n, 1); zeichneSperren(); regeln({ sofort: true }); return Promise.resolve(); }, "rund", "")),
      el("div", { class: "eh-reihe eng" }, el("span", { text: "von" }), uhr(s.von, (v, i) => { s.von = v; regeln({ feld: i }); }),
        el("span", { text: "bis" }), uhr(s.bis, (v, i) => { s.bis = v; regeln({ feld: i }); })),
      tageWahl(s.tage, (tage) => { s.tage = tage; regeln(); }),
      zeile("nicht in den Ferien", schalter(s.ferien_frei, (an) => { s.ferien_frei = an; regeln({ sofort: true }); })),
      zeile("Nachtruhe (Gute Nacht / Countdown)", schalter(s.nacht, (an) => { s.nacht = an; regeln({ sofort: true }); })))));
    const umbenennen = (alt, neu) => {             /* Apps, die in der Sperrzeit erlaubt waren, behalten das */
      let geaendert = false;
      for (const a of d.apps) {
        if (Array.isArray(a.sperr_erlaubt) && a.sperr_erlaubt.includes(alt)) { a.sperr_erlaubt = a.sperr_erlaubt.map((x) => (x === alt ? neu : x)); geaendert = true; }
      }
      if (geaendert) apps();
    };
    zeichneSperren();

    const ferienBox = el("div", { class: "eh-liste eh-ferienliste" });
    const neueFerien = new WeakSet();
    const landKnopf = knopf("📅 Ferien eintragen", async () => {
      const a = await sende("/api/eltern/ferien-eintragen", { land: r.bundesland, feiertage: r.ferien_feiertage !== false, auto: Boolean(r.ferien_auto) });
      r.ferien = a.ferien; zeichneFerien();
      zeige(`${a.land}: ${a.neu} Zeiträume neu eingetragen ✔`);
    }, "haupt breit", "");
    landKnopf.disabled = !r.bundesland;
    /* 4.6: fertige Zeiträume als Text (auf dem Handy sind Datumsfelder zu schmal), neue eigene Einträge als Felder */
    const tagText = (iso) => { const t = new Date(iso + "T12:00"); return `${TAGE[(t.getDay() + 6) % 7]} ${iso.slice(8, 10)}.${iso.slice(5, 7)}.${iso.slice(0, 4)}`; };
    const zeichneFerien = () => ferienBox.replaceChildren(...kurzliste(r.ferien.map((zeitraum, n) => {
      const weg = knopf("×", () => { r.ferien.splice(n, 1); zeichneFerien(); regeln({ sofort: true }); return Promise.resolve(); }, "rund", "");
      if (zeitraum[0] && zeitraum[1] && !neueFerien.has(zeitraum)) {
        return el("div", { class: "eh-eintrag eh-ferien" }, el("span", { class: "eh-breit",
          text: zeitraum[0] === zeitraum[1] ? `${tagText(zeitraum[0])} (1 Tag)` : `${tagText(zeitraum[0])} – ${tagText(zeitraum[1])}` }), weg);
      }
      return el("div", { class: "eh-eintrag spalte" },
        el("div", { class: "eh-reihe eng" }, el("span", { text: "von" }),
          eingabe(zeitraum[0], (v, i) => { zeitraum[0] = v; if (v && zeitraum[1]) regeln({ feld: i }); }, { type: "date", class: "eh-breit" }), weg),
        el("div", { class: "eh-reihe eng" }, el("span", { text: "bis" }),
          eingabe(zeitraum[1], (v, i) => { zeitraum[1] = v; if (v && zeitraum[0]) regeln({ feld: i }); }, { type: "date", class: "eh-breit" })));
    }), 4));
    zeichneFerien();

    const erinnerungBox = el("div", { class: "eh-liste" });
    const zeichneErinnerungen = () => erinnerungBox.replaceChildren(...f.erinnerungen.map((e, n) => el("div", { class: "eh-eintrag spalte" },
      el("div", { class: "eh-reihe eng" },
        uhr(e.zeit, (v, i) => { e.zeit = v; if (e.text.trim()) familie({ feld: i }); }),
        eingabe(e.text, (v, i) => { e.text = v; if (v.trim()) familie({ feld: i }); }, { type: "text", maxlength: 120, placeholder: "z. B. Zähneputzen!", class: "eh-breit" }),
        knopf("×", () => { f.erinnerungen.splice(n, 1); zeichneErinnerungen(); familie({ sofort: true }); return Promise.resolve(); }, "rund", "")),
      tageWahl(e.tage, (tage) => { e.tage = tage; if (e.text.trim()) familie(); }),
      segment([["immer", "immer"], ["schule", "nicht in den Ferien"], ["ferien", "nur in den Ferien"]], e.wann || "immer",
        (w) => { e.wann = w; if (e.text.trim()) familie({ sofort: true }); }),
      zeile("Klang", klangWahl(e.klang, (k) => { if (k) e.klang = k; else delete e.klang; if (e.text.trim()) familie({ sofort: true }); })))));
    zeichneErinnerungen();

    const b = f.bewegungspause, l = f.lernbonus;
    const gn = d.apps.find((a) => a.id === "gute-nacht");
    return {
      timer: karte("Wie viel Spielzeit am Tag?",
        el("h4", { text: "📺 Bildschirmzeit (alles zusammen)" }), timer("schultag"), timer("frei"),
        el("h4", { text: "🎮 davon höchstens Gaming" }), timer("schultag", "gaming_min"), timer("frei", "gaming_min"),
        hilfe("Bildschirmzeit gilt für alle Apps mit „Bildschirmzeit“ oder „Gaming-Zeit“. Gaming-Zeit ist ein Teil davon: Ist sie " +
              "aufgebraucht, gehen Spiele nicht mehr, Filme und Lernen aber schon. Welche App wovon abzieht, steht unter Inhalte → Apps & Kacheln."),
        zeile("Fernseher aus, wenn der Timer abgelaufen ist", schalter(f.tv_aus_bei_zeitende, (an) => { f.tv_aus_bei_zeitende = an; familie({ sofort: true }); }))),
      sperrzeiten: karte("Sperrzeiten (z. B. Nacht, Schule)", sperrBox,
        hilfe("In einer Sperrzeit sind alle Apps gesperrt – außer die, die sie ausdrücklich erlauben (Inhalte → Apps & Kacheln → „erlaubt in“). 10, 5 und 1 Minute vorher kommt ein Hinweis."),
        knopf("+ Sperrzeit", () => { r.sperrzeiten.push({ name: "Pause " + (r.sperrzeiten.length + 1), von: "12:00", bis: "13:00",
          tage: [0, 1, 2, 3, 4, 5, 6], ferien_frei: false, nacht: false }); zeichneSperren(); regeln({ sofort: true }); return Promise.resolve(); }, "leise", "")),
      gutenacht: karte("Gute Nacht (Hörbuch zum Einschlafen)",
        zeile("Zur Nachtruhe automatisch öffnen", schalter(f.gute_nacht?.automatisch, (an) => { f.gute_nacht = { automatisch: an }; familie({ sofort: true }); })),
        hilfe("An: Zu Beginn der Nachtruhe öffnet sich Gute Nacht und fragt nach der Zeit, dann geht das Hörbuch dort weiter, wo es gestern aufgehört hat. " +
              "Aus: ein 15-Sekunden-Countdown fragt „Fernseher aus / an / Gute Nacht“."),
        zeile("längster Sleep-Timer", auswahl([[15, "15 min"], [30, "30 min"], [45, "45 min"], [60, "1 Stunde"], [90, "1½ Stunden"], [120, "2 Stunden"]]
          .map(([w, t]) => [String(w), t]), String(f.hoerbuch?.schlaf_max_min ?? 60), (v) => { f.hoerbuch = { ...(f.hoerbuch || {}), schlaf_max_min: +v }; familie({ sofort: true }); })),
        hilfe(gn && gn.start ? "Hörbuch-Ordner: eingerichtet (Inhalte → Apps & Kacheln → Gute Nacht)." : "⚠️ Noch kein Hörbuch-Ordner: Inhalte → Apps & Kacheln → Gute Nacht → Freigabelink eintragen.")),
      wecker: karteWecker(),
      ferien: karte("Ferien und freie Tage",
        zeile("Bundesland", auswahl([["", "bitte wählen …"], ...Object.entries(d.bundeslaender || {}).sort((a, b) => a[1].localeCompare(b[1]))],
          r.bundesland || "", (v) => { r.bundesland = v; landKnopf.disabled = !v; })),
        zeile("gesetzliche Feiertage mit eintragen", schalter(r.ferien_feiertage !== false, (an) => { r.ferien_feiertage = an; })),
        zeile("jedes Jahr automatisch", schalter(r.ferien_auto, (an) => { r.ferien_auto = an; if (r.bundesland) regeln({ sofort: true }); })),
        landKnopf,
        hilfe(BUNDESLAND_HINWEIS + (d.ferien_bekannt_bis ? ` Bekannt bis ${d.ferien_bekannt_bis.split("-").reverse().join(".")}.` : "")),
        el("h4", { text: "Eingetragen" }), ferienBox,
        knopf("+ eigene freie Tage", () => { const z = ["", ""]; neueFerien.add(z); r.ferien.unshift(z); zeichneFerien(); return Promise.resolve(); }, "leise", ""),
        hilfe("Eigene Einträge (z. B. bewegliche Ferientage der Schule) bleiben beim Eintragen erhalten.")),
      klaengeEigen: karteEigeneKlaenge(),
      erinnerungen: karte("Erinnerungen", erinnerungBox,
        el("div", { class: "eh-feld" }, el("span", { text: "Klang für Nachrichten von Mama oder Papa" }),
          klangWahl(f.klang_nachricht, (k) => { f.klang_nachricht = k; familie({ sofort: true }); })),
        hilfe("Erscheinen zur Uhrzeit am Fernseher (mit ihrem Klang, ▶ zum Anhören) und bleiben stehen, bis sie mit OK bestätigt werden – alle 5 Minuten kommen sie wieder. " +
              "„nicht in den Ferien“: z. B. Sportsachen oder Training – an Ferien und Feiertagen (Zeit → Spielzeit & Sperrzeiten → Ferien) kommt sie dann nicht."),
        knopf("+ Erinnerung", () => { f.erinnerungen.push({ zeit: "19:00", text: "", tage: [0, 1, 2, 3, 4, 5, 6], wann: "immer" }); zeichneErinnerungen(); return Promise.resolve(); }, "leise", "")),
      bewegung: karte("Bewegungspause",
        zeile("Bewegungspause", schalter(b.aktiv, (an) => { b.aktiv = an; familie({ sofort: true }); })),
        zeile("nach … Spielen am Stück", zahl(b.nach_min, 10, 240, (v, i) => { b.nach_min = v; familie({ feld: i }); }), el("small", { text: "min" })),
        zeile("Dauer", zahl(b.dauer_min, 1, 15, (v, i) => { b.dauer_min = v; familie({ feld: i }); }), el("small", { text: "min" })),
        el("details", { class: "eh-mehr eh-bewegung-liste" }, el("summary", { text: "Bei welchen Angeboten? (antippen)" }),
          hilfe("Gezählt wird nur die Zeit in den eingeschalteten Angeboten. Alles andere (z. B. die Startseite) zählt als Erholung."),
          ...[...d.apps.map((a) => [a, false]), ...(d.spielzimmer || []).map((a) => [a, true])].map(([a, eingebaut]) =>
            zeile(a.name, schalter(a.bewegung ?? ["zaehlt", "gaming"].includes(a.zeit), (an) => {
              a.bewegung = an; (eingebaut ? spielzimmer : apps)({ sofort: true }); }))))),
      lernbonus: karte("Lernen bringt Spielzeit",
        zeile("Lernbonus", schalter(l.aktiv, (an) => { l.aktiv = an; familie({ sofort: true }); })),
        zeile("je … Lernen", zahl(l.lernen_min, 5, 120, (v, i) => { l.lernen_min = v; familie({ feld: i }); }), el("small", { text: "min" })),
        zeile("gibt es Bonus", zahl(l.bonus_min, 1, 60, (v, i) => { l.bonus_min = v; familie({ feld: i }); }), el("small", { text: "min" })),
        zeile("höchstens am Tag", zahl(l.max_bonus_min, 0, 240, (v, i) => { l.max_bonus_min = v; familie({ feld: i }); }), el("small", { text: "min" })),
        el("details", {}, el("summary", { text: "Wie wird geprüft?" }),
          zeile("mindestens Tasten pro Minute", zahl(l.tasten_pro_minute ?? 3, 1, 30, (v, i) => { l.tasten_pro_minute = v; familie({ feld: i }); })),
          zeile("„Bist du noch da?“ alle", zahl(l.check_min ?? 10, 3, 60, (v, i) => { l.check_min = v; familie({ feld: i }); }), el("small", { text: "min" })),
          hilfe("Es zählen nur aktive Minuten. Wer die Frage (drei Pfeile in Folge) verpasst, bekommt die Zeit seit der letzten Frage nicht gutgeschrieben."))),
      lautstaerke: karte("Ton und Lautstärke",
        zeile("höchstens", zahl(d.einstellungen.ton?.max ?? 100, 20, 100, (v, i) => {
          d.einstellungen.ton = { ...(d.einstellungen.ton || {}), max: v }; einstellung("ton", d.einstellungen.ton, { feld: i }); }), el("small", { text: "%" })),
        hilfe("Am Fernseher: GELB, dann ↑ ↓ (Controller: Back + ↑ ↓). Die TV-Lautstärketasten regeln nur den Fernseher selbst."),
        zeile("Ton automatisch in den Bluetooth-Kopfhörer", schalter(d.einstellungen.ton?.kopfhoerer_auto !== false, (an) => {
          d.einstellungen.ton = { ...(d.einstellungen.ton || {}), kopfhoerer_auto: an };
          einstellung("ton", d.einstellungen.ton, { sofort: true });
        }))),
    };
  }

  /* ================================================================ Apps */
  /* 4.6: eingebaute Spiele speichern - je Spiel an/aus, Zeitart, Limit, Sperrzeiten, Bewegungspause */
  const SPIELZIMMER_FELDER = ["aktiv", "zeit", "limit_min", "sperr_erlaubt", "bewegung"];
  const spielzimmer = (opt) => einstellung("spielzimmer", Object.fromEntries((d.spielzimmer || []).map((a) =>
    [a.id, Object.fromEntries(SPIELZIMMER_FELDER.filter((f) => a[f] !== undefined).map((f) => [f, a[f]]))])), opt);
  /* Handy-Spiele und Fotoalbum haben schon einen eigenen Schalter - die Kachel nutzt genau den */
  const EIGENER_SCHALTER = {
    "spiel-handys": { lies: () => Boolean(d.einstellungen.handyspiele?.aktiv),
      setze: (an) => { d.einstellungen.handyspiele = { ...(d.einstellungen.handyspiele || {}), aktiv: an }; einstellung("handyspiele", d.einstellungen.handyspiele, { sofort: true }); } },
    "spiel-fotoalbum": { lies: () => Boolean(d.einstellungen.fotoalbum?.erlaubt),
      setze: (an) => { d.einstellungen.fotoalbum = { ...(d.einstellungen.fotoalbum || {}), erlaubt: an }; einstellung("fotoalbum", d.einstellungen.fotoalbum, { sofort: true }); } },
  };
  const appAn = (app) => (EIGENER_SCHALTER[app.id] ? EIGENER_SCHALTER[app.id].lies() && app.aktiv !== false : app.aktiv !== false);

  /* ================================================================ 6.9.38: Apps - Übersicht und Detailseite */
  const alleApps = () => [...d.apps.map((app) => ({ app, eingebaut: false })),
                          ...(d.spielzimmer || []).map((app) => ({ app, eingebaut: true }))];
  const startBereich = ({ app, eingebaut }) => bereichVon(eingebaut ? { ...app, typ: app.typ || "spiel" } : app);
  const nichtEingerichtet = ({ app, eingebaut }) => !eingebaut && !app.start && !["konsole", "youtube"].includes(app.typ);
  function appText({ app, eingebaut }) {
    const l = app.limit_min;
    const limit = !hatLimit(app) ? "" : typeof l === "number" ? ` · höchstens ${l} min` : ` · höchstens ${l.schultag ?? "–"}/${l.frei ?? "–"} min`;
    const erlaubt = app.sperr_erlaubt === "alle" ? " · auch in Sperrzeiten" :
      (app.sperr_erlaubt || []).length ? ` · erlaubt in: ${app.sperr_erlaubt.join(", ")}` : "";
    return (appAn(app) ? "" : "ausgeschaltet · ") + (eingebaut ? "" : `${TYP_NAME[app.typ] || app.typ} · `) +
      ZEIT_KURZ[zeitart(app)] + limit + erlaubt + (nichtEingerichtet({ app, eingebaut }) ? " · ⚠️ nicht eingerichtet" : "");
  }
  function sichtbarSchalter(e, danach) {
    const { app, eingebaut } = e, speichern = eingebaut ? spielzimmer : apps;
    const sch = schalter(appAn(app), (an) => {
      if (EIGENER_SCHALTER[app.id]) { EIGENER_SCHALTER[app.id].setze(an); if (an && app.aktiv === false) { app.aktiv = true; speichern({ sofort: true }); } }
      else { app.aktiv = an; speichern({ sofort: true }); }
      danach?.();
    });
    sch.setAttribute("aria-label", `${app.name} auf der Startseite zeigen`);
    sch.addEventListener("click", (ev) => ev.stopPropagation());
    return sch;
  }

  let appSuche = "", appFilter = "alle";
  const APP_FILTER = [["alle", "Alle"], ["aus", "Aus"], ["offen", "⚠️ Einrichten"], ["zeit", "⏱ Zeit"]];
  const passt = (e) => (!appSuche || e.app.name.toLowerCase().includes(appSuche)) &&
    (appFilter === "alle" || (appFilter === "aus" && !appAn(e.app)) || (appFilter === "offen" && nichtEingerichtet(e)) ||
     (appFilter === "zeit" && ["zaehlt", "gaming"].includes(zeitart(e.app))));

  function seiteApps() {
    const e = offen && alleApps().find((x) => x.app.id === offen);
    if (e) return appDetail(e);
    const liste = alleApps();
    const gruppen = el("div", { class: "eh-app-gruppen" });
    const zeigeGruppen = () => {
      gruppen.replaceChildren(...BEREICHE.map((b) => {
        const drin = sortiert(b.id, liste.filter((x) => startBereich(x) === b.id && passt(x)));
        if (!drin.length) return null;
        return el("section", { class: "eh-karte eh-gruppe", "data-gruppe": b.id },
          el("h3", { class: "eh-gruppe-kopf" }, el("span", { text: `${b.symbol} ${b.name}` }), el("small", { text: `${drin.length}` })),
          zeitFuerAlle(b, drin), ...drin.map((e, i) => appZeile(e, { bereich: b.id, oben: i === 0, unten: i === drin.length - 1, neu: zeigeGruppen })));
      }).filter(Boolean));
      if (!gruppen.children.length) gruppen.append(hilfe("Keine App passt zur Suche."));
    };
    const suche = el("input", { type: "search", placeholder: "🔍 App suchen …", class: "eh-breit eh-suche", value: appSuche });
    suche.addEventListener("input", () => { appSuche = suche.value.trim().toLowerCase(); zeigeGruppen(); });
    const filter = segment(APP_FILTER, appFilter, (w) => { appFilter = w; zeigeGruppen(); });
    zeigeGruppen();
    const offenZahl = liste.filter(nichtEingerichtet).length;
    return [el("h2", { class: "eh-reiter-titel", text: "Apps & Kacheln" }),
            hilfe("So, wie euer Kind sie auf der Startseite findet. Antippen öffnet die App, der Schalter blendet sie aus."),
            el("div", { class: "eh-app-werkzeug" }, suche, filter),
            offenZahl ? el("p", { class: "eh-hinweis-warn", text: `⚠️ ${offenZahl} ${offenZahl === 1 ? "App muss" : "Apps müssen"} noch eingerichtet werden.` }) : null,
            gruppen, neueApp()].filter(Boolean);
  }

  /* 6.9.52: Reihenfolge je Bereich (wie auf der Startseite) */
  const reihenfolge = () => (d.kachel_reihenfolge = d.kachel_reihenfolge || {});
  function sortiert(bereich, liste_) {
    const r = reihenfolge()[bereich] || [];
    const rang = (x) => { const i = r.indexOf(x.app.id); return i < 0 ? 1e6 : i; };
    return liste_.map((x, i) => [x, i]).sort((a, b) => rang(a[0]) - rang(b[0]) || a[1] - b[1]).map(([x]) => x);
  }
  function verschiebe(bereich, id, schritt, neu) {
    const alle_ = sortiert(bereich, alleApps().filter((x) => startBereich(x) === bereich)).map((x) => x.app.id);
    const i = alle_.indexOf(id), j = i + schritt;
    if (i < 0 || j < 0 || j >= alle_.length) return;
    [alle_[i], alle_[j]] = [alle_[j], alle_[i]];
    reihenfolge()[bereich] = alle_;
    einstellung("kachel_reihenfolge", reihenfolge(), { sofort: true });
    neu();
  }

  function appZeile(e, ort = null) {
    const { app } = e;
    const unter = el("small", { text: appText(e) });
    const zeile_ = el("div", { class: "eh-app-zeile" + (appAn(app) ? "" : " eh-aus"), "data-app": app.id });
    const name = el("button", { type: "button", class: "eh-app-name" }, el("b", { text: app.name }), unter);
    name.addEventListener("click", () => geheZu("apps", app.id));
    const pfeile = ort && !appSuche && appFilter === "alle" ? el("span", { class: "eh-pfeile" },
      ...[["↑", -1, ort.oben], ["↓", 1, ort.unten]].map(([t, s_, aus]) => {
        const k = el("button", { type: "button", class: "eh-knopf rund", text: t, "aria-label": t === "↑" ? "nach oben" : "nach unten" });
        k.disabled = aus;
        k.addEventListener("click", (ev) => { ev.stopPropagation(); verschiebe(ort.bereich, app.id, s_, ort.neu); });
        return k;
      })) : null;
    zeile_.append(...[pfeile, name, sichtbarSchalter(e, () => { unter.textContent = appText(e); zeile_.classList.toggle("eh-aus", !appAn(app)); }),
                  el("span", { class: "eh-pfeil", text: "›" })].filter(Boolean));
    return zeile_;
  }

  /* 6.9.39: Zeit für alle Apps eines Bereichs auf einmal (eine Sammel-Einstellung, kein neues Datenmodell:
     sie setzt die Felder jeder App; danach kann jede App einzeln abweichen) */
  const limitKurz = (app) => { const l = app.limit_min; return !hatLimit(app) ? "" : typeof l === "number" ? `${l}` : `${l.schultag ?? "–"}/${l.frei ?? "–"}`; };
  function zeitFuerAlle(b, drin) {
    const arten = new Set(drin.map(({ app }) => zeitart(app) + "|" + limitKurz(app)));
    const erste = drin[0].app;
    const stand = arten.size === 1 ? ZEIT_KURZ[zeitart(erste)] + (limitKurz(erste) ? ` · höchstens ${limitKurz(erste)} min` : "") : "unterschiedlich";
    let wahl = arten.size === 1 ? zeitart(erste) : "gaming";
    const lim = { schultag: "", frei: "" };
    if (arten.size === 1 && typeof erste.limit_min === "object" && erste.limit_min) Object.assign(lim, erste.limit_min);
    const limitBox = el("div");
    const feld = (art) => eingabe(lim[art] ?? "", (v) => { lim[art] = v; }, { type: "number", min: 1, max: 600, placeholder: "–", class: "eh-zahl" });
    const zeigeLimit = () => limitBox.replaceChildren(...(wahl === "frei" ? [] : [
      zeile("höchstens am Schultag", feld("schultag"), el("small", { text: "min" })),
      zeile("höchstens Wochenende/Ferien", feld("frei"), el("small", { text: "min" }))]));
    zeigeLimit();
    const box = el("details", { class: "eh-alle" },
      el("summary", {}, el("span", { text: "⏱ Zeit für alle" }), el("small", { text: stand })),
      hilfe(`Setzt alle ${drin.length} Apps in „${b.name}“ auf einmal. Einzelne Apps könnt ihr danach auf ihrer Seite anders einstellen.`),
      segment(ZEIT_WAHL, wahl, (w) => { wahl = w; zeigeLimit(); }), limitBox,
      knopf(`Für alle ${drin.length} übernehmen`, async () => {
        const zahl_ = (v) => (v === "" || v == null ? null : Math.max(1, Math.min(600, +v)));
        const neuLimit = Object.fromEntries(["schultag", "frei"].map((a) => [a, zahl_(lim[a])]).filter(([, v]) => v));
        for (const { app } of drin) {
          if (wahl === "frei") { app.zeit = "frei"; delete app.limit_min; continue; }
          app.zeit = wahl === "limit" ? "frei" : wahl;
          if (Object.keys(neuLimit).length) app.limit_min = { ...neuLimit };
          else if (wahl === "limit") app.limit_min = { schultag: 30, frei: 60 };
          else delete app.limit_min;
        }
        const eigene = drin.some((e) => !e.eingebaut), eingebaute = drin.some((e) => e.eingebaut);
        if (eigene) await sende("/api/eltern/apps", { apps: d.apps });
        if (eingebaute) await sende("/api/eltern/einstellungen", { einstellungen: { spielzimmer: Object.fromEntries((d.spielzimmer || []).map((a) =>
          [a.id, Object.fromEntries(SPIELZIMMER_FELDER.filter((f) => a[f] !== undefined).map((f) => [f, a[f]]))])) } });
        zeichne();
      }, "haupt", "Für alle übernommen ✔"));
    return box;
  }

  /* Was zu einer App gehört (früher eigene Bereiche) */
  function verweis(reiter, bereich, text) {
    return karte("", hilfe("Das stellt ihr an anderer Stelle ein:"), knopf(text, () => { geheZu(reiter, bereich); return Promise.resolve(); }, "breit", ""));
  }
  function appInhalt(id) {
    const m = () => seiteMehr(), r = () => seiteRegeln();
    const INHALT = {
      youtube: () => [karteYoutube()],
      "spiel-bass": () => seiteBass(),
      "spiel-witz": () => [m().inhalte],
      "spiel-sticker": () => { const x = m(); return [x.stickerEigen, x.sticker]; },
      "spiel-gutschein": () => [m().gutscheine],
      "spiel-handys": () => [m().handyspiele],
      "spiel-wetter": () => [karteWetter()],
      "spiel-schule": () => [karteSchule()], klassenkiste: () => [karteSchule()],
      "spiel-kinderwelten": () => [karteKinderwelten()], kinderwelten: () => [karteKinderwelten()],
      "spiel-news": () => [karteNews()],
      "spiel-fotoalbum": () => [m().fotoalbum],
      "spiel-malen": () => [m().bilder],
      "gute-nacht": () => [r().gutenacht],
      "spiel-wecker": () => [r().wecker],
      "spiel-hilfe": () => [karteHilfe()],
      "spiel-meintag": () => [verweis("franzi", "meintag", "📋 Mein Tag einstellen")],
      "spiel-franzi": () => [verweis("franzi", "franzi", "🐾 Franzi einstellen"), verweis("franzi", "shop", "🛍️ Sterne-Shop")],
      "spiel-nachrichten": () => [verweis("mehr", "telegram", "💬 Telegram & Kontakte")],
      "spiel-gestalten": () => [verweis("aussehen", "design", "🎨 Farben & Animationen")],
      "archiv-video": () => [karteArchiv("video")],
      "archiv-musik": () => [karteArchiv("musik")],
    };
    return (INHALT[id]?.() || []).filter(Boolean);
  }

  /* 6.9.41: Archiv-Ordner (Filme, Musik) - Ordner eintragen, Inhalt laden, Einträge einzeln freigeben; Filme als Belohnung */
  function karteArchiv(art) {
    const a = d.archiv = d.archiv || {};
    const x = a[art] = Object.assign({ ordner: "", freigaben: {} }, a[art] || {});
    const speichernA = (opt) => einstellung("archiv", d.archiv, opt);
    const film = art === "video";
    const liste = el("div", { class: "eh-liste eh-archiv-liste" });
    const stand = el("p", { class: "eh-hilfe" });
    let eintraege = [];
    const zeichneListe = () => {
      const n = Object.keys(x.freigaben).length;
      stand.textContent = !x.ordner ? "Noch kein Ordner eingetragen." : eintraege.length ? `${n} von ${eintraege.length} freigegeben.` : stand.textContent;
      liste.replaceChildren(...eintraege.map((e) => {
        const fr = x.freigaben[e.pfad];
        const reihe = el("div", { class: "eh-eintrag spalte eh-archiv", "data-pfad": e.pfad });
        reihe.append(zeile(`${e.ordner ? "📁" : film ? "🎬" : "🎵"} ${e.name}`, schalter(Boolean(fr), (an) => {
          if (an) x.freigaben[e.pfad] = film ? { frei: false, sperre: false } : {}; else delete x.freigaben[e.pfad];
          zeichneListe(); speichernA({ sofort: true });
        })));
        if (fr && film) {
          const chip = (feld, text) => {
            const k = el("button", { type: "button", class: fr[feld] ? "an" : "", text });
            k.addEventListener("click", () => { fr[feld] = !fr[feld]; k.classList.toggle("an", fr[feld]); speichernA({ sofort: true }); });
            return k;
          };
          reihe.append(el("div", { class: "eh-tage eh-chips-breit" }, chip("frei", "🎁 zählt nicht zur Zeit"), chip("sperre", "🌙 auch in Sperrzeiten")));
        }
        return reihe;
      }));
    };
    const laden_ = () => {
      if (!x.ordner) { eintraege = []; zeichneListe(); return Promise.resolve(); }
      stand.textContent = "Inhalt wird geladen …";
      return hole("/api/eltern/archiv?art=" + art).then((r) => { eintraege = r.eintraege || []; if (!eintraege.length) stand.textContent = "Der Ordner ist leer."; zeichneListe(); })
        .catch((f) => { eintraege = []; liste.replaceChildren(); stand.textContent = "⚠️ " + f.message; });
    };
    const feld = eingabe(x.ordner, (v, i) => {
      x.ordner = v.trim();
      speichere("archiv", () => sende("/api/eltern/einstellungen", { einstellungen: { archiv: d.archiv } }).then(laden_), { feld: i });
    }, { type: "url", placeholder: "http://server:8080/share/…", class: "eh-breit" });
    const alle = (an) => knopf(an ? "Alle freigeben" : "Keine", () => {
      x.freigaben = an ? Object.fromEntries(eintraege.map((e) => [e.pfad, x.freigaben[e.pfad] || (film ? { frei: false, sperre: false } : {})])) : {};
      zeichneListe(); speichernA({ sofort: true }); return Promise.resolve();
    }, "leise", "");
    laden_();
    return karte(film ? "🎬 Film-Archiv" : "🎵 Musik-Archiv",
      hilfe((film ? "Einen Ordner mit Filmen (am besten .mp4) im FileBrowser freigeben" : "Einen Ordner mit Musik (mp3 …) im FileBrowser freigeben") +
            " (unbefristet, ohne Passwort) und den Link eintragen. Dann jeden Eintrag einzeln freigeben – am Fernseher erscheint nur, was hier an ist." +
            (film ? " Ein Film als Belohnung kann ohne Zeitlimit laufen und/oder auch in Sperrzeiten (z. B. am Wochenende morgens)." : "")),
      el("div", { class: "eh-feld" }, el("span", { text: "Freigabelink des Ordners" }), feld),
      hoerbuchHilfe(), stand,
      el("div", { class: "eh-reihe" }, alle(true), alle(false), knopf("Neu laden", () => laden_(), "leise", "")),
      liste);
  }

  function appDetail(e) {
    const { app, eingebaut } = e;
    const speichern = eingebaut ? spielzimmer : apps;
    const geaendert = (o) => speichern(o);
    const zurueck = el("a", { href: "#apps", class: "eh-zurueck", text: "‹ Apps" });
    zurueck.addEventListener("click", (ev) => { ev.preventDefault(); geheZu("apps"); });
    const kopf = el("div", { class: "eh-detail-kopf" }, zurueck,
      el("h2", { class: "eh-reiter-titel", text: app.name }),
      zeile("auf der Startseite", sichtbarSchalter(e)),
      el("p", { class: "eh-hilfe", text: `${BEREICHE.find((b) => b.id === startBereich(e))?.name || ""}${eingebaut ? " · eingebaut" : " · " + (TYP_NAME[app.typ] || app.typ)}` }));
    /* Zeit */
    const limitBox = el("div");
    const limitFeld = (art) => {
      const l = app.limit_min;
      const wert = l == null ? "" : typeof l === "number" ? l : (l[art] ?? "");
      return eingabe(wert, (v, i) => {
        const neu = typeof app.limit_min === "object" && app.limit_min ? { ...app.limit_min } :
          (typeof app.limit_min === "number" ? { schultag: app.limit_min, frei: app.limit_min } : {});
        if (v === "") delete neu[art]; else neu[art] = +v;
        if (Object.keys(neu).length) app.limit_min = neu; else delete app.limit_min;
        geaendert({ feld: i });
      }, { type: "number", min: 1, max: 600, placeholder: "–", class: "eh-zahl" });
    };
    const zeigeLimit = () => limitBox.replaceChildren(...(zeitart(app) !== "frei" ? [
      zeile("höchstens am Schultag", limitFeld("schultag"), el("small", { text: "min" })),
      zeile("höchstens Wochenende/Ferien", limitFeld("frei"), el("small", { text: "min" })),
      zeitart(app) === "limit" ? null : hilfe("Leer lassen = keine eigene Grenze.")].filter(Boolean) : []));
    const erkl = hilfe(ZEIT_ERKLAERT[zeitart(app)]);
    const zeitKarte = karte("⏰ Zeit",
      el("div", { class: "eh-feld" }, el("span", { text: "Wovon geht die Zeit ab?" }),
        segment(ZEIT_WAHL, zeitart(app), (w) => {
          if (w === "frei") { app.zeit = "frei"; delete app.limit_min; }
          else if (w === "limit") { app.zeit = "frei"; if (!hatLimit(app)) app.limit_min = { schultag: 30, frei: 60 }; }
          else app.zeit = w;
          erkl.textContent = ZEIT_ERKLAERT[w]; zeigeLimit(); geaendert({ sofort: true }); })),
      erkl, limitBox, sperrWahl(app, () => geaendert({ sofort: true })),
      zeile("Bewegungspause", schalter(app.bewegung ?? ["zaehlt", "gaming"].includes(app.zeit), (an) => { app.bewegung = an; geaendert({ sofort: true }); })));
    zeigeLimit();
    /* Allgemein (nur eigene Apps haben Adresse, Bereich, Löschen) */
    const allgemein = [];
    if (!eingebaut && app.typ !== "konsole") {
      const adresse = eingabe(app.start, (v, i) => { app.start = v.trim(); geaendert({ feld: i }); },
        { type: "url", class: "eh-breit", placeholder: ["hoerbuch", "video"].includes(app.typ) ? "http://…:8080/share/…" : "https://…" });
      allgemein.push(el("div", { class: "eh-feld" }, el("span", { text: ["hoerbuch", "video"].includes(app.typ) ? "Freigabelink des Ordners" : "Adresse" }), adresse));
      if (["hoerbuch", "video"].includes(app.typ)) allgemein.push(hoerbuchHilfe());
    }
    if (!eingebaut) {
      allgemein.push(zeile("Bereich auf der Startseite", auswahl([["", "automatisch"], ["start", "📨 Mein Zimmer"], ["spiele", "🎮 Spiele"],
        ["lernen", "🎓 Lernen"], ["musik", "🎵 Musik"], ["filme", "🎬 Filme"], ["retro", "🕹️ Retro"]], app.bereich || "",
        (v) => { if (v) app.bereich = v; else delete app.bereich; geaendert({ sofort: true }); })));
    }
    if (app.id === "plex") {
      allgemein.push(el("div", { class: "eh-feld" }, el("span", { text: "Kinderprofil in Plex (Name genau wie in Plex, ohne PIN)" }),
        eingabe(app.plex_profil || "", (v, i) => { if (v.trim()) app.plex_profil = v.trim(); else delete app.plex_profil; geaendert({ feld: i }); },
          { type: "text", maxlength: 40, class: "eh-breit", placeholder: "z. B. Kinder" })),
        hilfe("Erscheint beim Öffnen die Profilauswahl, wählt der Fernseher dieses Profil von selbst."));
    }
    if (!eingebaut && app.typ === "web") {
      allgemein.push(el("div", { class: "eh-feld" }, el("span", { text: "Weitere erlaubte Internetseiten" }),
        eingabe((app.domains || []).join(" "), (v, i) => { app.domains = v.split(/[\s,]+/).filter(Boolean); geaendert({ feld: i }); },
          { type: "text", class: "eh-breit", placeholder: "z. B. cdn.beispiel.de" })),
        zeile("Lernangebot (Lernbonus, Lern-Check)", schalter(app.lernen, (an) => { app.lernen = an; geaendert({ sofort: true }); })));
    }
    if (!eingebaut && app.typ !== "konsole") {
      allgemein.push(knopf("App löschen", async () => {
        if (!confirm(`„${app.name}“ wirklich löschen?`)) return;
        d.apps = d.apps.filter((a) => a !== app);
        await sende("/api/eltern/apps", { apps: d.apps });
        geheZu("apps");
      }, "gefahr leise", "Gelöscht ✔"));
    }
    const inhalt_ = appInhalt(app.id);
    return [kopf,
            nichtEingerichtet(e) ? el("p", { class: "eh-hinweis-warn", text: "⚠️ Diese App ist noch nicht eingerichtet – unten bei „Allgemein“ die Adresse eintragen." }) : null,
            ...(inhalt_.length ? [el("h3", { class: "eh-zwischen", text: "Inhalt" }), ...inhalt_] : []),
            zeitKarte,
            allgemein.length ? karte("⚙️ Allgemein", ...allgemein) : null].filter(Boolean);
  }

  /* In welchen Sperrzeiten ist die App trotzdem erlaubt? (Vorgabe: in keiner) */
  function sperrWahl(app, geaendert) {
    const box = el("div", { class: "eh-feld" }, el("span", { text: "Erlaubt in Sperrzeiten" }));
    const chips = el("div", { class: "eh-tage eh-chips-breit" });
    const zeige = () => {
      const alle = app.sperr_erlaubt === "alle";
      const liste = alle ? [] : (app.sperr_erlaubt || []);
      chips.replaceChildren(...d.regeln.sperrzeiten.map((s) => {
        const k = el("button", { type: "button", text: s.name, class: alle || liste.includes(s.name) ? "an" : "" });
        k.disabled = alle;
        k.addEventListener("click", () => {
          const neu = liste.includes(s.name) ? liste.filter((x) => x !== s.name) : liste.concat([s.name]);
          app.sperr_erlaubt = neu; zeige(); geaendert();
        });
        return k;
      }));
    };
    box.append(chips, zeile("immer erlaubt (auch in neuen Sperrzeiten)", schalter(app.sperr_erlaubt === "alle", (an) => {
      app.sperr_erlaubt = an ? "alle" : []; zeige(); geaendert(); })));
    zeige();
    return box;
  }

  function hoerbuchHilfe() {
    return el("details", { class: "eh-hilfe-box" }, el("summary", { text: "Wie bekomme ich den Freigabelink?" }),
      el("ol", {},
        el("li", { text: "FileBrowser auf dem Server öffnen und zum Hörbuch-Ordner gehen." }),
        el("li", { text: "Ordner markieren → „Teilen“ (Symbol mit dem Pfeil)." }),
        el("li", { text: "Zeit „unbefristet“ lassen, kein Passwort → Link erstellen und kopieren." }),
        el("li", { text: "Hier einfügen. Unterordner erscheinen am Fernseher als einzelne Hörbücher." })),
      hilfe("Der Fernseher kann darüber nur lesen und abspielen, nichts löschen."));
  }

  function neueApp() {
    const z = { typ: "web", name: "", start: "", zeit: "frei", symbol: "lernen", lernen: true };
    const name = eingabe("", (v) => { z.name = v; }, { type: "text", maxlength: 40, placeholder: "Name, z. B. Anton", class: "eh-breit" });
    const adresse = eingabe("", (v) => { z.start = v.trim(); }, { type: "url", placeholder: "https://…", class: "eh-breit" });
    const hilfeBox = el("div");
    const lernen = zeile("Lernangebot (Lernbonus, Lern-Check)", schalter(true, (an) => { z.lernen = an; }));
    const typ = segment([["web", "🌐 Webseite"], ["hoerbuch", "🎧 Hörbuch-Ordner"], ["video", "🎬 Video-Ordner"]], "web", (w) => {
      z.typ = w;
      adresse.placeholder = w !== "web" ? "http://…:8080/share/…" : "https://…";
      hilfeBox.replaceChildren(w !== "web" ? hoerbuchHilfe() : "");
      lernen.hidden = w !== "web";
      if (w === "hoerbuch") { z.zeit = "frei"; z.symbol = "musik"; z.lernen = false; }
      if (w === "video") { z.zeit = "zaehlt"; z.symbol = "film"; z.lernen = false; }
    });
    return el("details", { class: "eh-karte eh-neu" }, el("summary", { text: "➕ Neue App anlegen" }),
      el("div", { class: "eh-feld" }, el("span", { text: "Art" }), typ), name, adresse, hilfeBox,
      el("div", { class: "eh-feld" }, el("span", { text: "Symbol" }), auswahl(SYMBOL_WAHL, z.symbol, (v) => { z.symbol = v; })),
      lernen,
      knopf("Anlegen", async () => {
        const kennung = (z.name.trim().toLowerCase().replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss")
          .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 30) || "app");
        let id = /^[a-z]/.test(kennung) ? kennung : "app-" + kennung;
        while (d.apps.some((a) => a.id === id)) id += "-2";
        const host = (() => { try { return z.typ === "web" ? new URL(z.start).hostname : ""; } catch (_) { return ""; } })();
        const neu = { id, name: z.name.trim(), typ: z.typ, start: z.start, zeit: z.zeit, lernen: z.typ === "web" && z.lernen, sperr_erlaubt: [],
                      eingabe: "tasten", domains: host ? [host] : [], aktiv: true, symbol: z.symbol, farbe: z.typ === "hoerbuch" ? "#5e35b1" : z.typ === "video" ? "#b23a3a" : "#3949ab",
                      reihenfolge: 100 + d.apps.length };
        await sende("/api/eltern/apps", { apps: d.apps.concat([neu]) });
        await laden();
      }, "haupt breit", "Angelegt ✔"));
  }

  /* ================================================================ Bass */
  function seiteBass() {
    const songs = d.einstellungen.bass = d.einstellungen.bass || [];
    const speichernSongs = (opt) => einstellung("bass", songs.filter((s) => s.titel && s.titel.trim()), opt);
    const box = el("div", { class: "eh-liste" });
    const feld = (song, art, platzhalter) => eingabe(song[art] || "", (v, i) => {
      if (v.trim()) song[art] = v.trim(); else delete song[art]; speichernSongs({ feld: i }); }, { type: "url", placeholder: platzhalter, class: "eh-breit" });
    const zeichneSongs = () => box.replaceChildren(...songs.map((song, n) => el("div", { class: "eh-eintrag spalte" },
      el("div", { class: "eh-reihe eng" },
        eingabe(song.titel || "", (v, i) => { song.titel = v; speichernSongs({ feld: i }); }, { type: "text", placeholder: "Titel des Songs", class: "eh-breit fett" }),
        knopf("×", () => { songs.splice(n, 1); zeichneSongs(); speichernSongs({ sofort: true }); }, "rund", "")),
      feld(song, "video", "🎬 Erklärvideo (YouTube …)"), feld(song, "tab", "📄 Tabs / Noten (z. B. ultimate-guitar.com)"),
      feld(song, "backing", "🥁 Backing Track"))));
    zeichneSongs();
    const bib = d.familie.bass_bibliotheken;
    return [
      karte("Songs", hilfe("Erscheinen in der Bass-Ecke. Die Seiten werden automatisch in der Browser-Whitelist erlaubt."), box,
        knopf("+ Song", () => { songs.push({ titel: "" }); zeichneSongs(); return Promise.resolve(); }, "leise", "")),
      karte("Plex-Bibliotheken",
        el("div", { class: "eh-feld" }, el("span", { text: "Bass-Unterricht" }),
          eingabe(bib.unterricht, (v, i) => { bib.unterricht = v.trim(); familie({ feld: i }); }, { type: "url", placeholder: "Plex-Adresse", class: "eh-breit" })),
        el("div", { class: "eh-feld" }, el("span", { text: "Backing Tracks" }),
          eingabe(bib.backing, (v, i) => { bib.backing = v.trim(); familie({ feld: i }); }, { type: "url", placeholder: "Plex-Adresse", class: "eh-breit" })),
        hilfe("In Plex die Bibliothek bzw. Playlist öffnen und die Adresse aus der Adresszeile kopieren.")),
      karte("Tagebuch",
        el("div", { class: "eh-gross klein", text: d.bass_tagebuch.serie ? `🔥 ${d.bass_tagebuch.serie} Tage am Stück` : "noch keine Serie" }),
        hilfe(`Insgesamt ${d.bass_tagebuch.gesamt_min} min geübt`),
        el("div", { class: "eh-balken" }, ...d.bass_tagebuch.tage.slice(-7).map((t) => el("div", {},
          el("i", { style: `height:${Math.min(100, t.minuten / 60 * 100)}%` }), el("small", { text: TAGE[(new Date(t.datum).getDay() + 6) % 7] }),
          el("b", { text: String(t.minuten) }))))),
    ];
  }

  /* ================================================================ YouTube-Bereich (3.5) */
  function karteYoutube() {
    const y = d.youtube = d.youtube || { kategorien: [] };
    const speichernY = (opt) => speichere("youtube", () => sende("/api/eltern/einstellungen", { einstellungen: { youtube: y } }), opt);
    const box = el("div", { class: "eh-liste" });
    let katWahl = y.kategorien[0]?.name || "";
    const link = el("input", { type: "url", class: "eh-breit", placeholder: "YouTube-Link (Video oder Playlist)" });
    const neuKat = el("input", { type: "text", class: "eh-breit", maxlength: 30, placeholder: "neue Kategorie, z. B. Basteln" });
    const katAuswahl = el("div");
    const zeichneAuswahl = () => katAuswahl.replaceChildren(y.kategorien.length ?
      auswahl(y.kategorien.map((k) => [k.name, k.name]).concat([["", "➕ neue Kategorie …"]]), katWahl, (v) => { katWahl = v; neuKat.hidden = Boolean(v); })
      : el("span"));
    /* 6.0: Reihenfolge ändern - Kategorien und Videos mit ↑ ↓; offene Kategorien bleiben beim Neuzeichnen offen */
    const offen = new Set();
    const verschiebe = (liste, i, schritt) => {
      const j = i + schritt;
      if (j < 0 || j >= liste.length) return false;
      [liste[i], liste[j]] = [liste[j], liste[i]];
      return true;
    };
    const pfeile = (liste, i, danach) => el("span", { class: "eh-pfeile" },
      knopf("↑", () => { if (verschiebe(liste, i, -1)) danach(); return Promise.resolve(); }, "rund" + (i === 0 ? " aus" : ""), ""),
      knopf("↓", () => { if (verschiebe(liste, i, 1)) danach(); return Promise.resolve(); }, "rund" + (i === liste.length - 1 ? " aus" : ""), ""));
    const neuOrdnen = () => { zeichneListe(); zeichneAuswahl(); speichernY({ sofort: true }); };
    const zeichneListe = () => box.replaceChildren(...y.kategorien.map((k, n) => el("details", { class: "eh-app", open: offen.has(k) ? true : null,
      ontoggle: (ev) => { if (ev.target.open) offen.add(k); else offen.delete(k); } },
      el("summary", { class: k.aktiv === false ? "eh-aus" : "" }, el("span", { class: "eh-app-name" }, el("b", { text: k.name }),
        el("small", { text: `${k.eintraege.length} Einträge` + (k.aktiv === false ? " · gerade aus" : "") }))),
      y.kategorien.length > 1 ? zeile("Reihenfolge der Kategorie", pfeile(y.kategorien, n, neuOrdnen)) : null,
      zeile("Am Fernseher zeigen", schalter(k.aktiv !== false, (an) => { if (an) delete k.aktiv; else k.aktiv = false; speichernY({ sofort: true }); zeichneListe(); })),
      eingabe(k.name, (v, i) => { const neu = v.trim(); if (neu) { k.name = neu; speichernY({ feld: i }); zeichneAuswahl(); } },
        { type: "text", maxlength: 30, class: "eh-breit fett" }),
      ...k.eintraege.map((e, m) => el("div", { class: "eh-eintrag" },
        e.bild ? el("img", { src: e.bild, alt: "", class: "eh-yt-bild" }) : null,
        el("div", { class: "eh-app-name" }, el("b", { text: e.titel }), el("small", { text: e.art === "playlist" ? "Playlist" : "Video" })),
        k.eintraege.length > 1 ? pfeile(k.eintraege, m, neuOrdnen) : null,
        knopf("×", () => { k.eintraege.splice(m, 1); zeichneListe(); speichernY({ sofort: true }); return Promise.resolve(); }, "rund", ""))),
      knopf("Kategorie löschen", () => { if (!confirm(`„${k.name}“ mit allen Einträgen löschen?`)) return Promise.resolve();
        y.kategorien.splice(n, 1); zeichneListe(); zeichneAuswahl(); speichernY({ sofort: true }); return Promise.resolve(); }, "gefahr leise", ""))));
    zeichneListe(); zeichneAuswahl();
    neuKat.hidden = y.kategorien.length > 0;
    return karte("YouTube-Bereich",
      hilfe("Hier gespeicherte Videos und Playlists sieht das Kind in der Kachel „YouTube“ – nur das Video, ohne YouTube-Seite, ohne Vorschläge und ohne Suche. Zeit: wie jede App (oben bei „YouTube“)."),
      katAuswahl, neuKat, link,
      knopf("Hinzufügen", async () => {
        const kategorie = (katWahl || neuKat.value).trim();
        if (!kategorie) throw new Error("Bitte eine Kategorie wählen oder eingeben.");
        const antwort = await sende("/api/eltern/youtube-eintrag", { kategorie, link: link.value.trim() });
        let k = y.kategorien.find((x) => x.name === kategorie);
        if (!k) { k = { name: kategorie, eintraege: [] }; y.kategorien.push(k); }
        k.eintraege.push(antwort.eintrag);
        link.value = ""; neuKat.value = ""; katWahl = kategorie; neuKat.hidden = true;
        zeichneListe(); zeichneAuswahl();
      }, "haupt", "Hinzugefügt ✔"),
      box);
  }

  /* ================================================================ Wecker (3.5) */
  function karteWecker() {
    const w = d.wecker;
    const speichernW = (opt) => speichere("wecker", () => sende("/api/eltern/einstellungen", { einstellungen: { wecker: w } }), opt);
    let toene = [""];
    const box = el("div", { class: "eh-liste" });
    const tonWahl = (e) => auswahl(toene.map((t) => [t, t ? t.replace(/\.[^.]+$/, "") : "🎵 Sanfter Ton"]), e.ton || "",
      (v) => { e.ton = v; speichernW({ sofort: true }); });
    const zeichne_ = () => box.replaceChildren(...w.liste.map((e, n) => el("div", { class: "eh-eintrag spalte" },
      el("div", { class: "eh-reihe eng" },
        uhr(e.zeit, (v, i) => { e.zeit = v; speichernW({ feld: i }); }),
        schalter(e.an !== false, (an) => { e.an = an; speichernW({ sofort: true }); }),
        el("span", { class: "eh-breit" }),
        knopf("×", () => { w.liste.splice(n, 1); zeichne_(); speichernW({ sofort: true }); return Promise.resolve(); }, "rund", "")),
      tageWahl(e.tage, (tage) => { e.tage = tage; speichernW(); }),
      zeile("Ton", tonWahl(e)),
      zeile("Lautstärke", zahl(e.laut ?? w.max_laut, 5, 100, (v, i) => { e.laut = v; speichernW({ feld: i }); }), el("small", { text: "%" })),
      zeile("🌅 Sonnenaufgang vorher", auswahl([[0, "aus"], [5, "5 min"], [10, "10 min"], [15, "15 min"], [20, "20 min"], [30, "30 min"]]
        .map(([v, t]) => [String(v), t]), String(e.sonne || 0), (v) => { e.sonne = +v; speichernW({ sofort: true }); })),
      zeile("Szene", auswahl([["huegel", "⛰️ Hügel"], ["ostsee", "🌊 Ostsee (Wellen, Möwen)"], ["wald", "🌲 Wald (Vögel)"]], e.szene || "huegel",
        (v) => { e.szene = v; speichernW({ sofort: true }); })))));
    zeichne_();
    if (w.toene) hole("/api/eltern/wecker-toene").then((a) => { toene = ["", ...a.toene]; zeichne_(); }).catch(() => {});
    return karte("Wecker",
      hilfe("Das Kind stellt seine Wecker selbst am Fernseher ein (Kachel „Wecker“). Hier: Grenzen und dieselben Wecker bearbeiten. Zur Weckzeit geht der Fernseher an und der Ton wird langsam lauter; OK = schlummern, STOP = aus."),
      zeile("Wecker erlaubt", schalter(w.aktiv, (an) => { w.aktiv = an; speichernW({ sofort: true }); })),
      zeile("frühestens", uhr(w.fruehestens, (v, i) => { w.fruehestens = v; speichernW({ feld: i }); })),
      zeile("höchste Lautstärke", zahl(w.max_laut, 10, 100, (v, i) => { w.max_laut = v; speichernW({ feld: i }); }), el("small", { text: "%" })),
      el("div", { class: "eh-feld" }, el("span", { text: "Weckton-Ordner (FileBrowser-Freigabelink)" }),
        eingabe(w.toene, (v, i) => { w.toene = v.trim(); speichernW({ feld: i }); }, { type: "url", class: "eh-breit", placeholder: "http://…:8080/share/…" })),
      box,
      w.liste.length < 5 ? knopf("+ Wecker", () => {
        w.liste.push({ nr: Math.max(0, ...w.liste.map((x) => x.nr)) + 1, zeit: w.fruehestens > "07:00" ? w.fruehestens : "07:00",
                       tage: [0, 1, 2, 3, 4], ton: "", laut: w.max_laut, an: true });
        zeichne_(); speichernW({ sofort: true }); return Promise.resolve(); }, "leise", "") : null,
      standbyTest());
  }

  /* 6.1: Geht der Fernseher nachts aus (Standby), muss der Wecker ihn morgens per HDMI-CEC wieder einschalten können.
     Der Test schaltet ihn aus und nach 15 s wieder an und fragt jeweils, ob er wirklich aus bzw. an ist. */
  function standbyTest() {
    const stand = el("div", { class: "eh-hilfe" }, "Einen Moment …");
    const text = (t) => {
      const wann = t.geprueft ? ` (geprüft am ${t.geprueft.slice(8, 10)}.${t.geprueft.slice(5, 7)}. um ${t.geprueft.slice(11, 16)})` : "";
      if (t.laeuft) return "⏳ Test läuft: Der Fernseher geht gleich aus und nach etwa 15 Sekunden wieder an …";
      if (t.cec_an === true) return `✅ Der Wecker kann den Fernseher einschalten${wann}. Nach Gute Nacht geht er in den Standby und spart Strom.`;
      if (t.cec_an === false) return (t.cec_aus ? "⚠️ Der Fernseher ging aus, ließ sich aber nicht wieder einschalten" :
        "⚠️ Der Fernseher hat auf den Befehl nicht geantwortet") + `${wann}. Ist ein Wecker gestellt, bleibt er nachts an und zeigt den dunklen Nachthimmel.`;
      return "Noch nicht geprüft. Ist ein Wecker gestellt, bleibt der Fernseher nachts an und zeigt den dunklen Nachthimmel – " +
        "bis der Test zeigt, dass der Wecker ihn einschalten kann. Ohne Wecker geht er wie bisher aus.";
    };
    const zeige = (t) => stand.replaceChildren(text(t));
    const holen = () => hole("/api/eltern/cec-test").then((t) => { zeige(t); return t; });
    holen().catch(() => stand.replaceChildren(""));
    return el("div", { class: "eh-eintrag spalte" },
      el("b", { text: "📴 Fernseher nachts ausschalten" }), stand,
      knopf("Jetzt testen (aus und wieder an)", async () => {
        await sende("/api/eltern/cec-test");
        zeige({ laeuft: true });
        for (let i = 0; i < 25; i++) {
          await new Promise((f) => setTimeout(f, 3000));
          const t = await holen();
          if (!t.laeuft) return;
        }
        stand.replaceChildren("Keine Antwort vom Fernseher. Läuft die Eingabe (Fernbedienung)?");
      }, "leise", ""));
  }

  /* 4.2: Bilder für Retro-Spiele holen (EmulationStation zeigt sie in der Spieleliste) */
  function karteScraper() {
    const stand = el("div", { class: "eh-liste" }, hilfe("Einen Moment …"));
    let wache = null;
    const uhrzeit = (s) => s ? new Date(s * 1000).toTimeString().slice(0, 5) : "";
    const zeichne_ = (s) => {
      clearTimeout(wache);
      const systeme = Object.entries(s.systeme || {});
      const neu = systeme.reduce((n, [, x]) => n + (x.neu || 0), 0);
      const kopfzeile = s.laeuft ? `⏳ Läuft seit ${uhrzeit(s.start)} Uhr …` :
        s.ende ? `Zuletzt ${new Date(s.ende * 1000).toLocaleDateString("de-DE")} ${uhrzeit(s.ende)} Uhr: ${neu} neue Bilder` : "Noch nie gelaufen.";
      stand.replaceChildren(el("div", { text: kopfzeile }), s.fehler ? hilfe("⚠️ " + s.fehler) : null,
        ...systeme.filter(([, x]) => x.neu || (x.ohne || []).length || x.fehler).map(([name, x]) => el("details", { class: "eh-hilfe-box" },
          el("summary", { text: `${name}: ${x.neu} neu` + ((x.ohne || []).length ? ` · ${x.ohne.length} ohne Bild` : "") + (x.fehler ? " · " + x.fehler : "") }),
          (x.ohne || []).length ? hilfe("Ohne Bild: " + x.ohne.join(", ")) : null)));
      if (s.laeuft) wache = setTimeout(holen, 5000);
    };
    const holen = () => hole("/api/eltern/scraper").then(zeichne_).catch((e) => stand.replaceChildren(hilfe(e.message)));
    holen();
    return karte("Retro-Spiele: Bilder", stand,
      knopf("🖼️ Bilder für neue Spiele holen", async () => { await sende("/api/eltern/scraper"); setTimeout(holen, 1500); }, "", "Gestartet ✔"),
      hilfe("Nach dem Hochladen neuer ROMs. Holt nur, was fehlt (freie Bilder des libretro-Projekts), und läuft außerdem jede Nacht um 4 Uhr. RetroPie darf dabei nicht laufen – die Bilder erscheinen beim nächsten Start der Spieleliste."));
  }

  /* 4.1: Bluetooth - Tastatur, Controller, Kopfhörer koppeln (nur die Eltern, nicht am Fernseher) */
  function karteBluetooth() {
    const liste = el("div", { class: "eh-liste" }, hilfe("Einen Moment …"));
    const gefunden = el("div", { class: "eh-liste" });
    const bt = (aktion, mac) => sende("/api/eltern/bluetooth", { aktion, mac });
    const zeichne_ = (geraete) => liste.replaceChildren(...(geraete.length ? geraete.map((g) => el("div", { class: "eh-eintrag" },
      el("div", { class: "eh-app-name" }, el("b", { text: g.name }),
        el("small", { text: (g.verbunden ? "verbunden ✔" : "nicht verbunden") + (g.akku !== null ? ` · Akku ${g.akku} %` : "") })),
      el("div", { class: "eh-reihe eng" },
        g.verbunden ? knopf("Trennen", async () => zeichne_((await bt("trennen", g.mac)).geraete), "chip", "")
                    : knopf("Verbinden", async () => zeichne_((await bt("verbinden", g.mac)).geraete), "chip", ""),
        knopf("×", async () => { if (confirm(`„${g.name}“ entfernen? Danach muss es neu gekoppelt werden.`)) zeichne_((await bt("entfernen", g.mac)).geraete); }, "rund", ""))))
      : [hilfe("Noch keine Geräte gekoppelt.")]));
    hole("/api/eltern/bluetooth").then((a) => (a.fehler ? liste.replaceChildren(hilfe(a.fehler)) : zeichne_(a.geraete)))
      .catch((e) => liste.replaceChildren(hilfe(e.message)));
    const suchen = async () => {
      gefunden.replaceChildren(hilfe("Suche läuft (12 Sekunden) – das Gerät jetzt in den Kopplungsmodus schalten …"));
      const a = await bt("suchen");
      gefunden.replaceChildren(...(a.gefunden.length ? a.gefunden.map((g) => el("div", { class: "eh-eintrag" },
        el("div", { class: "eh-app-name" }, el("b", { text: g.name }), el("small", { text: g.mac })),
        knopf("Koppeln", async () => { zeichne_((await bt("koppeln", g.mac)).geraete); gefunden.replaceChildren(); }, "chip", "Gekoppelt ✔")))
        : [hilfe("Nichts gefunden. Ist das Gerät im Kopplungsmodus (meist eine Taste lange drücken, bis es blinkt)?")]));
    };
    return karte("Bluetooth", liste,
      knopf("🔍 Neue Geräte suchen", suchen, "leise", ""), gefunden,
      hilfe("Für Tastatur, Controller und Kopfhörer. Geräte, die beim Koppeln eine Zahl zum Eintippen verlangen, bitte per SSH koppeln (Anleitung)."));
  }

  /* 4.1: Sicherung herunterladen / einspielen (ohne PIN und Telegram-Token) */
  function karteSicherung() {
    const datei = el("input", { type: "file", accept: ".zip,application/zip", hidden: true });
    const laden_ = async () => {
      const antwort = await fetch("/api/eltern/sicherung", { headers: { "X-FF-Eltern": leseElternToken() } });
      if (!antwort.ok) throw new Error("Sicherung ging nicht.");
      const name = (antwort.headers.get("Content-Disposition") || "").match(/filename="([^"]+)"/)?.[1] || "fernsehfranzi-sicherung.zip";
      const a = el("a", { href: URL.createObjectURL(await antwort.blob()), download: name });
      document.body.append(a); a.click(); a.remove();
    };
    datei.addEventListener("change", async () => {
      const f = datei.files[0];
      datei.value = "";
      if (!f || !confirm(`„${f.name}“ einspielen? Der jetzige Stand wird vorher auf dem Pi gesichert, danach lädt der Fernseher neu.`)) return;
      try {
        const antwort = await fetch("/api/eltern/sicherung-einspielen", { method: "POST", body: f,
          headers: { "X-FF-Eltern": leseElternToken(), "Content-Type": "application/zip" } });
        const d_ = await antwort.json();
        if (!antwort.ok) throw new Error(d_.fehler || "Einspielen ging nicht.");
        zeige(d_.meldung);
        setTimeout(laden, 8000);
      } catch (e) { zeige(fehlerText(e), true); }
    });
    return karte("Sicherung",
      hilfe("Alles Eingestellte, Zeitkonto, Statistik, Gutscheine, Nachrichten, Sticker und die gemalten Bilder – als ZIP-Datei. Ohne PIN und ohne Telegram-Token."),
      el("div", { class: "eh-reihe" },
        knopf("⬇ Sicherung herunterladen", laden_, "", "Heruntergeladen ✔"),
        knopf("⬆ Sicherung einspielen …", () => { datei.click(); return Promise.resolve(); }, "leise", "")),
      datei);
  }

  /* 4.1: Was läuft gerade? Ein Bild vom Fernseher (nur Chromium; am TV erscheint kurz „📷“) */
  function fotoBereich() {
    const bild = el("img", { class: "eh-foto", alt: "Bild vom Fernseher", hidden: true });
    const text = el("small", { class: "eh-hilfe" });
    const holen = async () => {
      text.textContent = "Einen Moment …";
      const antwort = await fetch("/api/eltern/bildschirm", { headers: { "X-FF-Eltern": leseElternToken() } });
      if (!antwort.ok) {
        let grund = "Kein Bild.";
        try { grund = (await antwort.json()).fehler || grund; } catch (_) { /* kein JSON */ }
        bild.hidden = true; text.textContent = grund;
        throw new Error(grund);
      }
      if (bild.src) URL.revokeObjectURL(bild.src);
      bild.src = URL.createObjectURL(await antwort.blob());
      bild.hidden = false;
      text.textContent = `Stand ${new Date().toTimeString().slice(0, 5)} Uhr · am Fernseher erschien kurz „📷“`;
    };
    return el("div", { class: "eh-foto-box" }, knopf("📷 Was läuft gerade?", holen, "", "Bild geholt ✔"), bild, text);
  }

  /* 4.4: Fotos/Sprache/Videos aus dem Verlauf (mit Eltern-Sitzung geholt, als blob angezeigt) */
  async function mediumZeigen(medium) {
    const a = await fetch("/medien/" + medium.datei, { headers: { "X-FF-Eltern": leseElternToken() } });
    if (!a.ok) throw new Error("Nicht mehr da (nach 7 Tagen gelöscht).");
    const url = URL.createObjectURL(await a.blob());
    const inhalt = medium.art === "foto" ? el("img", { src: url, class: "eh-foto" })
      : el(medium.art === "video" ? "video" : "audio", { src: url, controls: true, autoplay: true, class: "eh-foto" });
    const box = el("div", { class: "eh-medium-box" }, inhalt, knopf("Schließen", () => { box.remove(); URL.revokeObjectURL(url); return Promise.resolve(); }, "", ""));
    document.body.append(box);
  }

  /* ================================================================ Speicherplatz und Fotoalbum (4.4) */
  function karteSpeicherFotoalbum() {
    const sp = d.einstellungen.speicher = Object.assign({ limit_mb: 200 }, d.einstellungen.speicher || {});
    const fa = d.einstellungen.fotoalbum = Object.assign({ erlaubt: false, ordner: "", bildschirmschoner: false, auswahl: [] }, d.einstellungen.fotoalbum || {});
    const s = d.speicher || { belegt_mb: 0, limit_mb: sp.limit_mb };
    return karte("🖼️ Fotoalbum und Speicherplatz",
      hilfe(`Zeichnungen und Album-Fotos belegen ${s.belegt_mb} von ${s.limit_mb} MB.` + (s.voll ? " Der Speicher ist voll – das Kind muss erst alte Bilder löschen (Fotoalbum am Fernseher)." : "")),
      zeile("Speicherplatz für das Kind (MB)", zahl(sp.limit_mb, 10, 5000, (v, i) => { sp.limit_mb = v; einstellung("speicher", sp, { feld: i }); })),
      zeile("Fotoalbum erlauben", schalter(fa.erlaubt, (an) => { fa.erlaubt = an; einstellung("fotoalbum", fa, { sofort: true }); })),
      el("div", { class: "eh-feld" }, el("span", { text: "Foto-Ordner (FileBrowser-Freigabelink, wie bei den Hörbüchern)" }),
        eingabe(fa.ordner, (v, i) => { fa.ordner = v.trim(); einstellung("fotoalbum", fa, { feld: i }); }, { type: "url", class: "eh-breit", placeholder: "http://server:8080/share/…" })),
      hilfe("Am Fernseher wählt das Kind in der Kachel „Fotoalbum“ Bilder aus diesem Ordner und aus seinem Album (⭐) und startet mit „▶ Diashow“ " +
            "selbst eine Diashow – z. B. wenn Freunde zu Besuch sind. Seit 6.8.7 startet die Diashow nie mehr von allein (sie hat den Pi zu warm werden lassen)."));
  }

  /* ================================================================ Handy-Spiele (4.3) */
  function karteHandyspiele() {
    const hs = d.einstellungen.handyspiele = Object.assign({ aktiv: false, port: 8767 }, d.einstellungen.handyspiele || {});
    return karte("📱 Handy-Spiele",
      hilfe("Am Fernseher gibt es dann die Kachel „Mit Handys spielen“: Der Fernseher zeigt einen QR-Code, jeder scannt ihn " +
            "und spielt am eigenen Handy mit – Buzzer-Runde, Quizrennen, Malen & Raten, Raumschiff-Rettung und Ton-Treffer. " +
            "Das Kind spielt mit der Fernbedienung. Der Zugang fürs Heimnetz ist nur offen, solange am Fernseher ein Spiel läuft, " +
            "und kann nur das Spiel. Die Zeit zählt wie bei jedem Spiel mit Timer."),
      zeile("Handy-Spiele erlauben", schalter(hs.aktiv, (an) => { hs.aktiv = an; einstellung("handyspiele", hs, { sofort: true }); })),
      hilfe(`Die Handys verbinden sich über Port ${hs.port}. Ton-Treffer braucht das USB-Mikrofon am Fernseher.`));
  }

  /* ================================================================ Telegram (4.0) */
  function karteTelegram() {
    const t = d.einstellungen.telegram = Object.assign({ aktiv: false, token: "", chats: [], antworten: [] }, d.einstellungen.telegram || {});
    const speichernT = (opt) => einstellung("telegram", { ...t, antworten: t.antworten.filter((a) => a.trim()),
                                                          chats: t.chats.filter((c) => c.name.trim() && Number.isInteger(c.id)) }, opt);
    const chatBox = el("div", { class: "eh-liste" });
    /* 4.3: je Kontakt Grenzen und Verlauf. Eltern dürfen alles; neue Kontakte (z. B. Freunde) starten streng. */
    const verlauf = Object.fromEntries((d.telegram_verlauf || []).map((v) => [v.id, v.nachrichten]));
    const kontaktKarte = (c, n) => {
      const schalterZeile = (text, feld, an) => zeile(text, schalter(c[feld], (wert) => { c[feld] = wert; speichernT({ sofort: true }); zeichneChats(); }), an);
      const nachrichten = (verlauf[c.id] || []).slice().reverse().map((m) => el("div", { class: "eh-verlauf " + m.richtung },
        el("small", { text: `${m.richtung === "rein" ? "⬅" : "➡"} ${m.zeit.slice(8, 10)}.${m.zeit.slice(5, 7)}. ${m.zeit.slice(11, 16)}${m.wartet ? " · wartete bis nach der Sperrzeit" : ""}` }),
        el("div", { text: m.text }),
        m.medium ? knopf(m.medium.art === "foto" ? "📷 Foto ansehen" : "▶ Abspielen", () => mediumZeigen(m.medium), "chip", "") : null));
      return el("div", { class: "eh-eintrag spalte" },
        el("div", { class: "eh-reihe eng" },
          eingabe(c.symbol, (v, i) => { c.symbol = v.trim() || "💬"; speichernT({ feld: i }); }, { type: "text", maxlength: 8, class: "eh-symbol", "aria-label": "Symbol" }),
          eingabe(c.name, (v, i) => { c.name = v; speichernT({ feld: i }); }, { type: "text", maxlength: 30, class: "eh-breit", "aria-label": "Name" }),
          knopf("×", () => { if (!confirm(`${c.name} entfernen?`)) return Promise.resolve(); t.chats.splice(n, 1); zeichneChats(); speichernT({ sofort: true }); return Promise.resolve(); }, "rund", "")),
        el("small", { class: "eh-hilfe", text: `Chat ${c.id}` }),
        schalterZeile("Eltern (darf alles)", "eltern"),
        zeile("Klang bei Nachrichten", klangWahl(c.klang, (k) => { if (k) c.klang = k; else delete c.klang; speichernT({ sofort: true }); })),
        c.eltern ? null : schalterZeile("Kind darf schreiben", "darf_schreiben"),
        c.eltern || !c.darf_schreiben ? null : schalterZeile("Eigene Texte (Tastatur) erlaubt", "eigene_texte"),
        c.eltern ? null : schalterZeile("Fotos, Sprachnachrichten und Videos erlaubt", "medien"),
        c.eltern ? null : schalterZeile("In Sperrzeiten nur zählen (lesen und antworten erst danach)", "nur_freizeit"),
        c.eltern ? el("details", { class: "eh-mehr" }, el("summary", { text: "Meldungen an diesen Elternteil" }),
          ...Object.entries(d.telegram_meldungen || {}).map(([art, text]) => zeile(text, schalter((c.meldungen || {})[art] !== false, (an) => {
            c.meldungen = { ...(c.meldungen || {}), [art]: an }; speichernT({ sofort: true });
          })))) : null,
        nachrichten.length ? el("details", { class: "eh-mehr" }, el("summary", { text: `Verlauf (${nachrichten.length})` }), ...nachrichten) : null);
    };
    const zeichneChats = () => chatBox.replaceChildren(...t.chats.map(kontaktKarte),
      ...(d.telegram_unbekannt || []).filter((u) => !t.chats.some((c) => c.id === u.id)).map((u) => el("div", { class: "eh-eintrag" },
        el("div", { class: "eh-app-name" }, el("b", { text: `Neu: ${u.name}` }), el("small", { text: `„${u.text}“ · Chat ${u.id}` })),
        knopf("Erlauben", async () => {
          t.chats.push({ id: u.id, name: u.name, symbol: "💬", eltern: false, darf_schreiben: false, eigene_texte: false, nur_freizeit: true, medien: false });
          zeichneChats(); speichernT({ sofort: true });
        }, "chip", ""))));
    zeichneChats();
    const antwortBox = el("div", { class: "eh-liste" });
    const zeichneAntworten = () => antwortBox.replaceChildren(...t.antworten.map((a, n) => el("div", { class: "eh-reihe eng" },
      eingabe(a, (v, i) => { t.antworten[n] = v; speichernT({ feld: i }); }, { type: "text", maxlength: 60, class: "eh-breit" }),
      knopf("×", () => { t.antworten.splice(n, 1); zeichneAntworten(); speichernT({ sofort: true }); return Promise.resolve(); }, "rund", ""))));
    zeichneAntworten();
    return karte("Telegram",
      el("details", { class: "eh-hilfe-box" }, el("summary", { text: "So richtest du es ein" }),
        el("ol", {},
          el("li", { text: "In Telegram @BotFather öffnen → /newbot → Namen vergeben → den Token kopieren." }),
          el("li", { text: "Token hier eintragen, Telegram einschalten." }),
          el("li", { text: "Jeder aus der Familie schreibt dem Bot einmal „Hallo“ – er erscheint unten als „Neu“ → „Erlauben“." }),
          el("li", { text: "Neue Kontakte (z. B. eine Freundin) dürfen erst nur schreiben. Ob das Kind ihnen antworten darf, eigene Texte tippen darf und ob ihre Nachrichten in Sperrzeiten warten, stellt ihr je Kontakt ein. Unter „Verlauf“ lest ihr mit." }),
          el("li", { text: "Ab dann erscheinen eure Nachrichten am Fernseher, und das Kind antwortet in der Kachel „Nachrichten“." }))),
      zeile("Telegram an", schalter(t.aktiv, (an) => { t.aktiv = an; speichernT({ sofort: true }); })),
      el("div", { class: "eh-feld" }, el("span", { text: "Bot-Token (wird danach nicht mehr angezeigt)" }),
        eingabe(t.token, (v, i) => { t.token = v.trim(); speichernT({ feld: i }); }, { type: "password", class: "eh-breit", autocomplete: "off", placeholder: "123456:ABC…" })),
      el("h4", { text: "Kontakte" }), chatBox,
      knopf("Neu laden (neue Chats anzeigen)", () => laden(), "leise", ""),
      zeile("Eigene Texte erlauben (Tastatur)", schalter(t.eigene_texte !== false, (an) => { t.eigene_texte = an; speichernT({ sofort: true }); })),
      zeile("Nachrichten in Sperrzeiten ohne Ton (Eltern-Nachrichten kommen trotzdem an)", schalter(t.sperrzeit_still !== false, (an) => { t.sperrzeit_still = an; speichernT({ sofort: true }); })),
      zeile("Tagesbericht um", uhr(t.bericht_uhr || "19:30", (v, i) => { t.bericht_uhr = v; speichernT({ feld: i }); })),
      hilfe("Befehle für Eltern im Chat mit dem Bot: /status, /zeit 15, /zeit 30, /zeit frei, /sperren, /auszeit 15, /freigeben, /gutenacht, /aus, /foto, /bericht"),
      el("h4", { text: "Antworten des Kindes" }), antwortBox,
      t.antworten.length < 12 ? knopf("+ Antwort", () => { t.antworten.push(""); zeichneAntworten(); return Promise.resolve(); }, "leise", "") : null);
  }

  /* ================================================================ Eigene Inhalte (3.5) */
  function karteInhalte() {
    const inh = d.einstellungen.inhalte = d.einstellungen.inhalte || { witze: [], quiz: [] };
    inh.witze = inh.witze || []; inh.quiz = inh.quiz || [];
    /* 6.8.8: ein Witz = mehrere Zeilen (alte Frage/Pointe werden zu zwei Zeilen) */
    inh.witze = inh.witze.map((w) => (Array.isArray(w.zeilen) ? w : { zeilen: [w.frage || "", w.pointe || ""].filter((z) => z.trim()) }));
    const fertigeWitze = () => inh.witze.map((w) => ({ zeilen: w.zeilen.map((z) => z.trim()).filter(Boolean).slice(0, 10) }))
      .filter((w) => w.zeilen.length);
    const fertigeQuiz = () => inh.quiz.filter((q) => q.frage.trim() && q.richtig.trim() && q.falsch.every((f) => f.trim()));
    const speichernI = (opt) => einstellung("inhalte", { witze: fertigeWitze(), quiz: fertigeQuiz() }, opt);
    const witzBox = el("div", { class: "eh-liste" }), quizBox = el("div", { class: "eh-liste" });
    const feld = (obj, schluessel, platz, i_ = null) => eingabe(i_ === null ? obj[schluessel] : obj[schluessel][i_], (v, i) => {
      if (i_ === null) obj[schluessel] = v; else obj[schluessel][i_] = v; speichernI({ feld: i }); }, { type: "text", class: "eh-breit", placeholder: platz, maxlength: 120 });
    const zeichneW = () => witzBox.replaceChildren(...inh.witze.map((w, n) => {
      const text = el("textarea", { rows: Math.max(2, w.zeilen.length), class: "eh-breit", maxlength: 1500,
                                    placeholder: "Eine Zeile pro Zeile – am Fernseher erscheint jede mit OK.\nDie letzte ist die Pointe." });
      text.value = w.zeilen.join("\n");
      text.addEventListener("input", () => { w.zeilen = text.value.split("\n"); speichernI({ feld: text }); });
      return el("div", { class: "eh-eintrag spalte" }, el("div", { class: "eh-reihe eng" }, text,
        knopf("×", () => { inh.witze.splice(n, 1); zeichneW(); speichernI({ sofort: true }); return Promise.resolve(); }, "rund", "")));
    }));
    const zeichneQ = () => quizBox.replaceChildren(...inh.quiz.map((q, n) => el("div", { class: "eh-eintrag spalte" },
      el("div", { class: "eh-reihe eng" }, feld(q, "frage", "Frage"),
        knopf("×", () => { inh.quiz.splice(n, 1); zeichneQ(); speichernI({ sofort: true }); return Promise.resolve(); }, "rund", "")),
      feld(q, "richtig", "✅ richtige Antwort"), feld(q, "falsch", "❌ falsch 1", 0), feld(q, "falsch", "❌ falsch 2", 1), feld(q, "falsch", "❌ falsch 3", 2))));
    zeichneW(); zeichneQ();
    return karte("Eigene Witze und Quizfragen",
      hilfe("Kommen zu den eingebauten dazu: Witze im Spiel „Witz“, Fragen im Lernspiel „Wissens-Quiz“. Witze dürfen mehrere Zeilen haben " +
            "(z. B. ein Gespräch): Am Fernseher erscheint jede Zeile mit OK, die letzte ist die Pointe."),
      el("h4", { text: "😄 Witze" }), witzBox,
      knopf("+ Witz", () => { inh.witze.push({ zeilen: [""] }); zeichneW(); return Promise.resolve(); }, "leise", ""),
      el("h4", { text: "❓ Quizfragen" }), quizBox,
      knopf("+ Quizfrage", () => { inh.quiz.push({ frage: "", richtig: "", falsch: ["", "", ""] }); zeichneQ(); return Promise.resolve(); }, "leise", ""));
  }

  function karteStickerEigen() {
    const eigene = d.einstellungen.sticker_eigen = d.einstellungen.sticker_eigen || [];
    const speichernS = (opt) => einstellung("sticker_eigen", eigene.filter((s) => s.name.trim() && s.symbol.trim()), opt);
    const seit = (id) => (d.sticker.find((s) => s.id === id) || {}).seit;
    const box = el("div", { class: "eh-liste" });
    const zeichne_ = () => box.replaceChildren(...eigene.map((s, n) => el("div", { class: "eh-eintrag spalte" },
      el("div", { class: "eh-reihe eng" },
        auswahl([["", "Symbol"], ...STICKER_SYMBOLE.map((z) => [z, z])], s.symbol, (v) => { s.symbol = v; speichernS({ sofort: true }); }),
        eingabe(s.name, (v, i) => { s.name = v; speichernS({ feld: i }); }, { type: "text", class: "eh-breit", maxlength: 30, placeholder: "Name, z. B. Zimmer-Profi" }),
        knopf("×", () => { eigene.splice(n, 1); zeichne_(); speichernS({ sofort: true }); return Promise.resolve(); }, "rund", "")),
      eingabe(s.bedingung || "", (v, i) => { s.bedingung = v; speichernS({ feld: i }); }, { type: "text", class: "eh-breit", maxlength: 80, placeholder: "wofür, z. B. Zimmer aufgeräumt" }),
      seit(s.id) ? el("small", { class: "eh-gut", text: `vergeben am ${seit(s.id)} ✔` }) :
        knopf("🏅 Jetzt vergeben", async () => {
          await speichernS({ sofort: true });
          await sende("/api/eltern/einstellungen", { einstellungen: { sticker_eigen: eigene.filter((x) => x.name.trim() && x.symbol.trim()) } });
          await sende("/api/eltern/sticker-vergeben", { id: s.id });
          await laden();
        }, "haupt", "Vergeben ✔"))));
    zeichne_();
    return karte("Eigene Sticker",
      hilfe("Eigene Belohnungs-Sticker für das Album – zum Beispiel fürs Zimmeraufräumen. Vergeben von Hand, das Kind sieht sie im Sticker-Album."),
      box,
      eigene.length < 30 ? knopf("+ Sticker", () => {
        eigene.push({ id: "eigen-" + Math.random().toString(36).slice(2, 10), name: "", symbol: "", bedingung: "" });
        zeichne_(); return Promise.resolve(); }, "leise", "") : null);
  }

  /* ================================================================ Gutscheine (3.5) */
  function karteGutscheine() {
    const z = { art: "normal", minuten: 15, anzahl: 3 };
    const liste = el("div", { class: "eh-liste" });
    const zeichneListe = () => {
      const codes = (d.gutscheine || []).slice().reverse();
      liste.replaceChildren(...(codes.length ? kurzliste(codes.slice(0, 200).map((c) => el("div", { class: "eh-eintrag" },
        el("div", { class: "eh-app-name" }, el("b", { class: "eh-code", text: c.code.replace(/(\d{3})(\d{3})/, "$1 $2") }),
          el("small", { text: `${c.art === "besonders" ? "⭐ besonders" : "normal"} · ${c.minuten} min` +
                              (c.eingeloest ? ` · eingelöst ${c.eingeloest.slice(8, 10)}.${c.eingeloest.slice(5, 7)}. ${c.eingeloest.slice(11, 16)}` : "") })),
        c.eingeloest ? el("small", { class: "eh-gut", text: "✔" }) :
          knopf("×", async () => { await sende("/api/eltern/gutschein-loeschen", { code: c.code });
            d.gutscheine = d.gutscheine.filter((x) => x.code !== c.code); zeichneListe(); }, "rund", "Gelöscht ✔"))), 8)
        : [hilfe("Noch keine Gutscheine.")]));
    };
    zeichneListe();
    const drucken = () => {
      const offen = (d.gutscheine || []).filter((c) => !c.eingeloest);
      if (!offen.length) { zeige("Keine offenen Gutscheine zum Drucken.", true); return; }
      const fenster = window.open("", "_blank");
      if (!fenster) { zeige("Bitte Pop-ups für diese Seite erlauben.", true); return; }
      fenster.document.write(`<!doctype html><meta charset="utf-8"><title>Gutscheine</title><style>
        body{font-family:sans-serif;display:grid;grid-template-columns:repeat(2,1fr);gap:8mm;padding:10mm}
        .g{border:2px dashed #888;border-radius:6mm;padding:6mm;text-align:center;break-inside:avoid}
        .c{font-size:30pt;font-weight:800;letter-spacing:4pt;margin:3mm 0}.a{font-size:13pt}</style>` +
        offen.map((c) => `<div class="g"><div class="a">${c.art === "besonders" ? "⭐ Besonderer Gutschein" : "🎟️ Gutschein"}</div>` +
          `<div class="c">${c.code.replace(/(\d{3})(\d{3})/, "$1 $2")}</div><div class="a">${c.minuten} Minuten` +
          `${c.art === "besonders" ? " – geht immer" : " mehr Spielzeit"}</div></div>`).join(""));
      fenster.document.close();
      fenster.focus();
      fenster.print();
    };
    return karte("Gutscheine",
      hilfe("Zum Ausdrucken: Das Kind tippt den Code am Fernseher ein (Kachel „Gutschein“). Normal = mehr Spielzeit, nur außerhalb der Sperrzeiten. Besonders = so viele Minuten geht alles, auch nachts, und nichts zählt."),
      el("div", { class: "eh-feld" }, el("span", { text: "Art" }), segment([["normal", "🎟️ normal"], ["besonders", "⭐ besonders"]], z.art, (w) => { z.art = w; })),
      zeile("Minuten", auswahl([[15, "15"], [30, "30"], [45, "45"], [60, "60"], [90, "90"], [120, "120"]].map(([w, t]) => [String(w), t + " min"]),
        String(z.minuten), (v) => { z.minuten = +v; })),
      zeile("Anzahl", auswahl([1, 2, 3, 5, 10].map((n) => [String(n), String(n)]), String(z.anzahl), (v) => { z.anzahl = +v; })),
      el("div", { class: "eh-reihe" },
        knopf("Gutscheine erstellen", async () => {
          const antwort = await sende("/api/eltern/gutscheine", z);
          d.gutscheine = (d.gutscheine || []).concat(antwort.neu); zeichneListe();
        }, "haupt", "Erstellt ✔"),
        knopf("🖨️ Offene drucken", async () => drucken(), "leise", "")),
      liste);
  }

  /* ================================================================ Statistik (4.0) */
  function seiteStatistik() {
    const box = el("div", { class: "eh-inhalt" }, hilfe("Lädt …"));
    hole("/api/eltern/statistik").then((s) => statistikZeichnen(box, s)).catch((e) => box.replaceChildren(hilfe(e.message)));
    return [box];
  }

  function statistikZeichnen(box, s) {
    const tage = Object.keys(s.tage).sort();
    const heute = new Date().toISOString().slice(0, 10);
    let bereich = 7, tagWahl = tage.length ? tage[tage.length - 1] : heute;
    const name = (id) => s.apps[id]?.name || (id === "games" ? "Retro-Spiele" : id);
    const farbe = (id) => s.apps[id]?.farbe || "#7fa8ff";
    const min = (sek) => Math.round(sek / 60);
    const dauer = (sek) => { const m = min(sek); return m >= 60 ? `${Math.floor(m / 60)} h ${m % 60} min` : `${m} min`; };
    const zeichne_ = () => {
      const auswahl_ = tage.slice(-bereich);
      const summe = {}, aktiv = {}, stunden = Array.from({ length: 24 }, () => 0);
      const proTag = {};
      for (const t of auswahl_) {
        proTag[t] = 0;
        for (const [app, h] of Object.entries(s.tage[t])) {
          for (const [stunde, [offen, akt]] of Object.entries(h)) {
            summe[app] = (summe[app] || 0) + offen; aktiv[app] = (aktiv[app] || 0) + akt;
            stunden[+stunde] += offen; proTag[t] += offen;
          }
        }
      }
      const gesamt = Object.values(summe).reduce((a, b) => a + b, 0);
      const art = (pred) => Object.entries(summe).filter(([id]) => pred(s.apps[id] || {}, id)).reduce((a, [, v]) => a + v, 0);
      const mitZeit = art((a, id) => a.zeit === "zaehlt" || id === "games");
      const lernen = art((a, id) => a.lernen || id === "spiel-bass" || id === "spiel-lernen");
      const guteNacht = summe["gute-nacht"] || 0;
      const top = Object.entries(summe).sort((a, b) => b[1] - a[1]);
      const groesste = top[0]?.[1] || 1;
      const maxStunde = Math.max(1, ...stunden);
      const maxTag = Math.max(1, ...Object.values(proTag));
      /* ein Tag im Detail */
      const tag = s.tage[tagWahl] || {};
      const zeitstrahl = Array.from({ length: 24 }, (_, h) => {
        const hh = String(h).padStart(2, "0");
        const inStunde = Object.entries(tag).map(([app, x]) => [app, (x[hh] || [0])[0]]).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
        return { h, apps: inStunde, summe: inStunde.reduce((a, [, v]) => a + v, 0) };
      });
      box.replaceChildren(...[
        karte("", segment([["1", "Heute"], ["7", "7 Tage"], ["30", "30 Tage"]], String(bereich), (w) => { bereich = +w; zeichne_(); }),
          el("div", { class: "st-kacheln" },
            el("div", {}, el("b", { text: dauer(gesamt) }), el("small", { text: "insgesamt am Fernseher" })),
            el("div", {}, el("b", { text: dauer(mitZeit) }), el("small", { text: "mit Spielzeit" })),
            el("div", {}, el("b", { text: dauer(lernen) }), el("small", { text: "Lernen & Musik" })),
            el("div", {}, el("b", { text: dauer(guteNacht) }), el("small", { text: "Gute Nacht" })))),
        karte("Was am meisten", ...(top.length ? top.slice(0, 12).map(([id, v]) => el("div", { class: "st-zeile" },
          el("div", { class: "st-name" }, el("span", { text: name(id) }), el("small", { text: `${dauer(v)} · davon aktiv ${dauer(aktiv[id] || 0)}` })),
          el("div", { class: "st-balken" }, el("i", { style: `width:${v / groesste * 100}%;background:${farbe(id)}` }),
            el("i", { class: "aktiv", style: `width:${(aktiv[id] || 0) / groesste * 100}%` }))))
          : [hilfe("Noch keine Nutzung in diesem Zeitraum.")])),
        karte("Wann am Tag", el("div", { class: "st-uhr" }, ...stunden.map((v, h) => el("div", { title: `${h}–${h + 1} Uhr: ${dauer(v)}` },
          el("i", { style: `height:${v / maxStunde * 100}%` }), el("small", { text: h % 3 === 0 ? String(h) : "" })))),
          hilfe("Summe je Stunde im gewählten Zeitraum.")),
        bereich > 1 ? karte("Jeder Tag", el("div", { class: "eh-balken st-tage" }, ...auswahl_.map((t) => el("div", { title: `${t}: ${dauer(proTag[t])}` },
          el("i", { style: `height:${proTag[t] / maxTag * 100}%` }), el("small", { text: bereich <= 7 ? TAGE[(new Date(t).getDay() + 6) % 7] : t.slice(8) }),
          el("b", { text: String(min(proTag[t])) }))))) : null,
        karte("Ein Tag im Detail",
          el("div", { class: "eh-reihe eng" },
            knopf("‹", () => { const i = tage.indexOf(tagWahl); if (i > 0) { tagWahl = tage[i - 1]; zeichne_(); } return Promise.resolve(); }, "rund", ""),
            el("b", { class: "eh-breit st-datum", text: new Date(tagWahl).toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long" }) }),
            knopf("›", () => { const i = tage.indexOf(tagWahl); if (i < tage.length - 1) { tagWahl = tage[i + 1]; zeichne_(); } return Promise.resolve(); }, "rund", "")),
          el("div", { class: "st-strahl" }, ...zeitstrahl.map((z) => el("div", { title: `${z.h} Uhr` },
            ...z.apps.map(([app, v]) => el("i", { style: `flex:${v};background:${farbe(app)}` })),
            z.summe < 3600 ? el("i", { class: "leer", style: `flex:${3600 - z.summe}` }) : null))),
          el("div", { class: "st-achse" }, ...[0, 6, 12, 18, 24].map((h) => el("small", { text: `${h}` }))),
          ...kurzliste(zeitstrahl.filter((z) => z.summe).map((z) => el("div", { class: "eh-eintrag" },
            el("b", { class: "st-stunde", text: `${String(z.h).padStart(2, "0")}:00` }),
            el("div", { class: "eh-app-name" }, ...z.apps.map(([app, v]) => el("small", { text: `${name(app)} · ${dauer(v)}` }))))), 6)),
        (s.gutscheine || []).length ? karte("Eingelöste Gutscheine", ...kurzliste(s.gutscheine.slice(-50).reverse().map((c) =>
          el("div", { class: "eh-eintrag" }, el("span", { text: `${c.art === "besonders" ? "⭐" : "🎟️"} ${c.minuten} min` }),
            el("small", { text: `${c.eingeloest.slice(8, 10)}.${c.eingeloest.slice(5, 7)}. ${c.eingeloest.slice(11, 16)}` }))), 5)) : null,
      ].filter(Boolean));
    };
    zeichne_();
  }

  /* ================================================================ 6.0: Klang-Ordner (eigene Klänge) */
  /* 6.9.47: Bildschirmschoner (Franzi + Uhr) und Standby nach Minuten ohne Eingabe */
  function karteBildschirm() {
    const b = d.einstellungen.bildschirm = Object.assign({ schoner_min: 5, standby_min: 0 }, d.bildschirm || {}, d.einstellungen.bildschirm || {});
    const speichernB = () => einstellung("bildschirm", { schoner_min: b.schoner_min, standby_min: b.standby_min }, { sofort: true });
    return karte("🖥️ Bildschirmschoner & Standby",
      zeile("Bildschirmschoner nach", auswahl([["0", "aus"], ["2", "2 min"], ["5", "5 min"], ["10", "10 min"], ["15", "15 min"], ["30", "30 min"]],
        String(b.schoner_min), (v) => { b.schoner_min = +v; speichernB(); })),
      hilfe("Tagsüber: große Uhr und eine dösende Franzi auf dunklem Grund, alles wandert alle 30 Sekunden ein Stück (schont den Fernseher). Nachts kommt wie bisher der Nachthimmel."),
      zeile("Fernseher aus (Standby) nach", auswahl([["0", "nie"], ["15", "15 min"], ["30", "30 min"], ["60", "1 Stunde"], ["90", "1½ Stunden"], ["120", "2 Stunden"]],
        String(b.standby_min), (v) => { b.standby_min = +v; speichernB(); })),
      hilfe("Nur, wenn niemand eine Taste drückt und nichts läuft (kein Video, Hörbuch, Musik, Spiel). Eine Minute vorher erscheint ein Hinweis. Ist ein Wecker eingestellt und das Einschalten per CEC nicht geprüft, bleibt der Fernseher an."));
  }

  /* 6.9.40: EIN gemeinsames Objekt für alle Klang-Karten (sonst überschreibt eine Karte beim Speichern die andere) */
  function klangEinst() {
    const kl = d.einstellungen.klaenge = d.einstellungen.klaenge || {};
    for (const [k, v] of Object.entries({ ordner: "", ordner_arten: {}, ereignisse: {}, bedienung_laut: 100, musik: {} })) if (kl[k] === undefined) kl[k] = v;
    return kl;
  }
  function karteEigeneKlaenge() {
    const kl = klangEinst();
    /* Ordner: allgemein + je Art (6.9.40) */
    const ordnerZeile = (art, titel, symbol) => {
      const stand = el("small", { class: "eh-klang-stand" });
      const zeigeStand = () => {
        if (!ordnerVon(art)) { stand.textContent = "kein Ordner"; return Promise.resolve(); }
        stand.textContent = "wird gesucht …";
        return eigeneLaden(true, art).then((l) => { const f = eigeneFehlerJe.get(art); stand.textContent = f ? "⚠️ " + f : `${l.length} Klänge`; });
      };
      if (ordnerVon(art)) zeigeStand();
      const feld = eingabe(art ? kl.ordner_arten[art] || "" : kl.ordner, (v, i) => {
        if (art) kl.ordner_arten = { ...kl.ordner_arten, [art]: v.trim() }; else kl.ordner = v.trim();
        speichere("klaenge", () => sende("/api/eltern/einstellungen", { einstellungen: { klaenge: kl } }).then(zeigeStand), { feld: i });
      }, { type: "url", placeholder: "http://server:8080/share/…", class: "eh-breit" });
      return el("div", { class: "eh-feld eh-klang-ordner", "data-art": art || "allgemein" }, el("span", {}, `${symbol} ${titel} `, stand), feld);
    };
    const ordnerKarte = karte("📁 Klang-Ordner",
      hilfe("Je Art einen Ordner mit Klängen (mp3, ogg, wav …) im FileBrowser freigeben (unbefristet, ohne Passwort) und den Link eintragen. " +
            "Die Klänge erscheinen dann in jeder passenden Klang-Auswahl. Der allgemeine Ordner steht überall zur Wahl (wie bisher). " +
            "Eigene Klänge spielen so lang wie die Datei (höchstens 10 Minuten, 50 MB)."),
      ordnerZeile("", "Allgemein", "🎵"),
      el("details", { class: "eh-mehr" }, el("summary", { text: "Ordner je Art (8)" }),
        ...(d.klang_arten || []).map((a) => ordnerZeile(a.id, a.name, a.symbol))));
    return ordnerKarte;
  }

  /* 6.9.40: Klang je Ereignis, Pakete, Lautstärke der Bedienung */
  function karteKlangEreignisse() {
    const kl = klangEinst();
    const speichernKl = (opt) => speichere("klaenge", () => sende("/api/eltern/einstellungen", { einstellungen: { klaenge: kl } }), opt);
    const tabelle = el("div", { class: "eh-liste" });
    const zeichneTabelle = () => {
      let gruppe = "";
      tabelle.replaceChildren(...(d.klang_ereignisse || []).flatMap((e) => {
        const kopf_ = e.gruppe !== gruppe ? [el("h4", { text: (gruppe = e.gruppe) })] : [];
        const leer = e.id === "meldung" ? "🔔 Gong (Standard)" : "Eingebaut";
        return [...kopf_, el("div", { class: "eh-eintrag spalte eh-ereignis", "data-ereignis": e.id }, el("span", { text: e.name }),
          klangWahl(kl.ereignisse[e.id] || "", (v) => { kl.ereignisse = { ...kl.ereignisse, [e.id]: v || "" }; speichernKl({ sofort: true }); },
                    { leer, leerId: e.id === "meldung" ? "gong" : "", art: e.art }))];
      }));
    };
    zeichneTabelle();
    const paketKnoepfe = el("div", { class: "eh-chips eh-pakete" }, ...Object.entries(d.klang_pakete || {}).map(([id, p]) => {
      const k = el("button", { type: "button", class: "eh-knopf leise", text: p.name, "data-paket": id });
      k.addEventListener("click", () => {
        kl.ereignisse = { ...p.ereignisse }; kl.bedienung_laut = p.bedienung_laut;
        laut.value = String(p.bedienung_laut); lautText.textContent = `${p.bedienung_laut} %`;
        zeichneTabelle(); speichernKl({ sofort: true });
      });
      return k;
    }));
    const laut = el("input", { type: "range", min: 0, max: 100, step: 10, value: String(kl.bedienung_laut ?? 100), class: "eh-regler" });
    const lautText = el("small", { text: `${kl.bedienung_laut ?? 100} %` });
    laut.addEventListener("input", () => { kl.bedienung_laut = +laut.value; lautText.textContent = `${laut.value} %`; speichernKl(); });
    return karte("🎛️ Klang je Ereignis",
      hilfe("Welcher Ton wann spielt. „Eingebaut“ ist der Ton des Fernsehers, „Ohne Ton“ macht still. Töne in den Spielen selbst bleiben fest."),
      el("div", { class: "eh-feld" }, el("span", { text: "Paket (setzt alles auf einmal)" }), paketKnoepfe),
      zeile("Lautstärke der Bedienung", laut, lautText),
      tabelle);
  }

  /* 6.9.40: Hintergrundmusik auf der Startseite und in Franzis Zimmer (ab Werk aus) */
  function karteMusik() {
    const kl = klangEinst();
    const speichernKl = (opt) => speichere("klaenge", () => sende("/api/eltern/einstellungen", { einstellungen: { klaenge: kl } }), opt);
    const ort = (id, titel) => {
      const m = kl.musik[id] = Object.assign({ an: false, klang: "", laut: 30 }, kl.musik[id] || {});
      const an = schalter(m.an, (v, c) => { if (v && !m.klang) { c.checked = false; zeige("Erst ein Stück wählen, dann einschalten.", true); return; } m.an = v; speichernKl({ sofort: true }); });
      const laut = el("input", { type: "range", min: 5, max: 100, step: 5, value: String(m.laut), class: "eh-regler" });
      laut.addEventListener("input", () => { m.laut = +laut.value; speichernKl(); });
      return el("div", { class: "eh-eintrag spalte", "data-musik": id }, zeile(titel, an),
        klangWahl(m.klang, (v) => { m.klang = v || ""; if (!m.klang) { m.an = false; an.checked = false; } speichernKl({ sofort: true }); },
                  { leer: "– kein Stück –", leerId: "", art: "musik", nurEigene: true }),
        zeile("Lautstärke", laut));
    };
    return karte("🎶 Hintergrundmusik",
      hilfe("Leise Musik in Schleife – nur, wenn gerade nichts anderes läuft. Stücke kommen aus dem Ordner „Hintergrundmusik“ (oder dem allgemeinen)."),
      ort("start", "Startseite"), hilfe("In Franzis Zimmer gibt es dafür die Musikbox aus dem Sterne-Shop – Franzi tanzt mit."));
  }

  /* ================================================================ 5.1: Auszeit */
  function auszeitSchalter(text) {
    const k = el("button", { type: "button", class: "eh-knopf" + (auszeitAuf ? " an" : ""), text });
    k.addEventListener("click", () => { auszeitAuf = !auszeitAuf; zeichne(); });
    return k;
  }
  function karteAuszeit() {
    if (d.gesperrt && !d.gesperrt.auszeit) return null;             /* fest gesperrt: erst freigeben */
    const laeuft = Boolean(d.gesperrt?.auszeit);
    const feld = el("input", { type: "number", min: 1, max: 240, value: 20, inputmode: "numeric", class: "eh-zahl", "aria-label": "Minuten" });
    const starte = (min) => sende("/api/eltern/auszeit", { minuten: min }).then((a) => { laden(); return a; });
    return el("div", { class: "eh-auszeit" },
      el("h4", { text: laeuft ? `⏳ Auszeit verlängern (noch ${Math.ceil((d.gesperrt.rest_s || 0) / 60)} min)` : "⏳ Auszeit" }),
      hilfe(laeuft ? "Die Minuten kommen zur laufenden Auszeit dazu."
                   : "Alles wird gesperrt, am Fernseher läuft nur ein Countdown. Danach ist er von selbst wieder frei."),
      el("div", { class: "eh-chips" }, ...(laeuft ? [5, 10, 15] : [5, 10, 15, 30, 60]).map((m) =>
        knopf(`${laeuft ? "+" : ""}${m} min`, () => starte(m), "chip", laeuft ? "Verlängert ✔" : "Auszeit läuft ✔"))),
      el("div", { class: "eh-reihe eh-suche" }, feld,
        knopf(laeuft ? "Verlängern" : "Auszeit starten", () => {
          const m = parseInt(feld.value, 10);
          if (!(m >= 1 && m <= 240)) return Promise.reject(new Error("Bitte 1 bis 240 Minuten."));
          return starte(m);
        }, laeuft ? "" : "gefahr", laeuft ? "Verlängert ✔" : "Auszeit läuft ✔")));
  }

  /* ================================================================ 5.0: Designs, Wetter, Schule, Kinderwelten, Kinder-News */
  /* 6.9.42: das ganze Design speichern (Farben, Abend, Animation, eigene Hintergründe) - eine Stelle für alle Karten */
  const designSpeichern = (opt) => { const ds = d.design; return einstellung("design", { erlaubt: ds.erlaubt, ansichten: ds.ansichten,
    abend_aktiv: ds.abend_aktiv, abend_ab: ds.abend_ab, morgen_ab: ds.morgen_ab, animation: ds.animation || "sparsam",
    hintergruende: ds.hintergruende || {}, hintergrund_ordner: ds.hintergrund_ordner || "" }, opt); };

  /* 6.9.52: Bild-Plätze - je Platz ein eigenes Bild hochladen oder zurück zur Vorgabe; Schablonen zum Herunterladen */
  function karteBildplaetze() {
    const gruppen = [...new Set((d.bildplaetze || []).map((b) => b.gruppe))];
    const stempel = Date.now();
    const zeile_ = (b) => {
      const vorschau = el("img", { class: "eh-bp-bild", alt: "", src: `/bilder/${b.platz}?v=${stempel}` });
      const datei = el("input", { type: "file", accept: b.alpha ? "image/png" : "image/png,image/jpeg,image/webp", class: "eh-datei" });
      datei.addEventListener("change", () => {
        const f = datei.files?.[0];
        if (!f) return;
        if (f.size > 6 * 1024 * 1024) { zeige("Das Bild ist zu groß (höchstens 6 MB).", true); datei.value = ""; return; }
        const leser = new FileReader();
        leser.onload = async () => {
          try { await sende("/api/eltern/bildplatz", { platz: b.platz, daten: leser.result }); b.eigen = true; zeige("Bild gespeichert ✔");
                vorschau.src = `/bilder/${b.platz}?v=${Date.now()}`; zurueck.hidden = false; }
          catch (e) { zeige(fehlerText(e), true); }
          datei.value = "";
        };
        leser.readAsDataURL(f);
      });
      const zurueck = knopf("Vorgabe", async () => {
        await sende("/api/eltern/bildplatz-zuruecksetzen", { platz: b.platz }); b.eigen = false;
        vorschau.src = `/bilder/${b.platz}?v=${Date.now()}`; zurueck.hidden = true;
      }, "leise", "Zurück zur Vorgabe ✔");
      zurueck.hidden = !b.eigen;
      return el("div", { class: "eh-eintrag eh-bp", "data-platz": b.platz }, vorschau,
        el("div", { class: "eh-bp-text" }, el("b", { text: b.name }), el("small", { text: `mind. ${b.min[0]} × ${b.min[1]}${b.alpha ? " · PNG durchsichtig" : ""}` }), datei),
        zurueck);
    };
    const SCHABLONEN = [["Franzi (512 × 512)", "franzi-schablone-zeichnen"], ["Raum (1600 × 1320)", "raum-schablone-zeichnen"],
                        ["Postkarte Vorderseite", "postkarte-vorderseite-schablone-beschriftet"], ["Postkarte Rückseite", "postkarte-rueckseite-schablone-beschriftet"],
                        ["Hintergrund (1920 × 1080)", "hintergrund-schablone-zeichnen"], ["Gegenstand (512 × 512)", "gegenstand-schablone-beschriftet"]];
    return [karte("🧩 Bild-Plätze",
      hilfe("Eigene Bilder statt der mitgelieferten – je Platz hochladen; „Vorgabe“ holt das Original zurück. Die Bilder bleiben auf dem Fernseher (auch bei Updates). Schablonen helfen beim Zeichnen."),
      el("div", { class: "eh-reihe" }, ...SCHABLONEN.map(([n, f]) => el("a", { class: "eh-knopf leise", href: `/bilder/schablonen/${f}.png`, download: f + ".png", text: "⬇ " + n })))),
      ...gruppen.map((g) => karte(g, ...(d.bildplaetze || []).filter((b) => b.gruppe === g).map(zeile_)))];
  }

  /* 6.9.42: eigene Hintergründe - hochladen oder aus einem FileBrowser-Ordner übernehmen, je Farbe wählen */
  function karteHintergruende() {
    const ds = d.design;
    ds.hintergruende = ds.hintergruende || {};
    const box = el("div");
    const neuLaden = async () => { d.hintergruende = (await hole("/api/eltern/daten")).hintergruende; zeichneBox(); };
    const bildName = (n) => `Bild ${d.hintergruende.indexOf(n) + 1}`;
    function zeichneBox() {
      const galerie = el("div", { class: "eh-hg-galerie" }, ...(d.hintergruende || []).map((n) => el("figure", { class: "eh-hg", "data-datei": n },
        el("img", { src: "/api/hintergrund?datei=" + n, alt: bildName(n), loading: "lazy" }),
        el("figcaption", {}, el("span", { text: bildName(n) }), knopf("Löschen", async () => {
          if (!confirm(`${bildName(n)} löschen?`)) return;
          await sende("/api/eltern/hintergrund-loeschen", { datei: n });
          for (const [k, v] of Object.entries(ds.hintergruende)) if (v === n) delete ds.hintergruende[k];
          await neuLaden();
        }, "gefahr leise", "Gelöscht ✔")))));
      const wahl = el("div", { class: "eh-liste eh-hg-wahl" }, ...ds.alle.filter((x) => ds.erlaubt.includes(x.id)).map((x) =>
        zeile(x.name, auswahl([["", "Gezeichnetes Motiv"], ...(d.hintergruende || []).map((n) => [n, bildName(n)])], ds.hintergruende[x.id] || "", (v) => {
          if (v) ds.hintergruende[x.id] = v; else delete ds.hintergruende[x.id];
          designSpeichern({ sofort: true });
        }))));
      box.replaceChildren(d.hintergruende?.length ? galerie : hilfe("Noch keine eigenen Bilder."),
                          d.hintergruende?.length ? el("h4", { text: "Welches Bild zu welcher Farbe?" }) : null,
                          d.hintergruende?.length ? wahl : null);
    }
    zeichneBox();
    const datei = el("input", { type: "file", accept: "image/png,image/jpeg,image/webp", class: "eh-datei" });
    datei.addEventListener("change", () => {
      const f = datei.files?.[0];
      if (!f) return;
      if (f.size > 6 * 1024 * 1024) { zeige("Das Bild ist zu groß (höchstens 6 MB).", true); datei.value = ""; return; }
      const leser = new FileReader();
      leser.onload = async () => {
        try { await sende("/api/eltern/hintergrund", { daten: leser.result }); zeige("Bild hochgeladen ✔"); await neuLaden(); }
        catch (e) { zeige(fehlerText(e), true); }
        datei.value = "";
      };
      leser.readAsDataURL(f);
    });
    /* aus einem FileBrowser-Ordner */
    const ordnerListe = el("div", { class: "eh-liste" });
    const ordnerLaden = () => {
      if (!ds.hintergrund_ordner) { ordnerListe.replaceChildren(); return Promise.resolve(); }
      return hole("/api/eltern/hintergrund-ordner").then((r) => ordnerListe.replaceChildren(...(r.bilder.length ? r.bilder.map((pfad) =>
        zeile(pfad, knopf("Übernehmen", async () => { await sende("/api/eltern/hintergrund-aus-ordner", { pfad }); await neuLaden(); }, "leise", "Übernommen ✔")))
        : [hilfe("Im Ordner sind keine Bilder (PNG, JPEG, WebP).")])))
        .catch((e) => ordnerListe.replaceChildren(hilfe("⚠️ " + e.message)));
    };
    const ordnerFeld = eingabe(ds.hintergrund_ordner || "", (v, i) => { ds.hintergrund_ordner = v.trim();
      speichere("e:design", () => sende("/api/eltern/einstellungen", { einstellungen: { design: { erlaubt: ds.erlaubt, ansichten: ds.ansichten,
        abend_aktiv: ds.abend_aktiv, abend_ab: ds.abend_ab, morgen_ab: ds.morgen_ab, animation: ds.animation || "sparsam",
        hintergruende: ds.hintergruende, hintergrund_ordner: ds.hintergrund_ordner } } }).then(ordnerLaden), { feld: i }); },
      { type: "url", placeholder: "http://server:8080/share/…", class: "eh-breit" });
    ordnerLaden();
    return karte("🖼️ Eigene Hintergründe",
      hilfe("Eigene Bilder statt des gezeichneten Motivs – je Farbe wählbar. Am besten 1920 × 1080 Pixel (Querformat), höchstens 6 MB. " +
            "Das Kind wählt weiter seine Farbe unter „Gestalten“; zu der Farbe erscheint dann euer Bild."),
      el("div", { class: "eh-feld" }, el("span", { text: "Bild hochladen" }), datei),
      box,
      el("details", { class: "eh-mehr" }, el("summary", { text: "Aus einem FileBrowser-Ordner übernehmen" }),
        hilfe("Ordner mit Bildern freigeben (unbefristet, ohne Passwort), Link eintragen, dann einzelne Bilder übernehmen – sie werden auf den Fernseher kopiert."),
        ordnerFeld, ordnerListe));
  }

  function karteDesign() {
    const ds = d.design;
    const speichernD = (opt) => designSpeichern(opt);
    const liste = el("div", { class: "eh-liste" }, ...ds.alle.map((x) => zeile(`${x.name}${x.hell ? " (hell)" : ""}`,
      schalter(ds.erlaubt.includes(x.id), (an, c) => {
        const neu = an ? [...ds.erlaubt, x.id] : ds.erlaubt.filter((y) => y !== x.id);
        if (!neu.length) { c.checked = true; zeige("Mindestens ein Design muss bleiben.", true); return; }
        ds.erlaubt = ds.alle.map((y) => y.id).filter((y) => neu.includes(y));
        speichernD({ sofort: true });
      }))));
    return karte("🎨 Farben der Startseite",
      hilfe("Am Fernseher wählt das Kind unter „Gestalten“ die Farbe und bis zu 6 Lieblinge. Hier legt ihr fest, welche Farben es gibt. " +
            "Spiele, Player und der Elternbereich bleiben immer dunkel."),
      el("h4", { text: "Farben" }),
      liste,

      el("h4", { text: "Abends automatisch dunkel (helle Farben)" }),
      zeile("Abend-Automatik", schalter(ds.abend_aktiv, (an) => { ds.abend_aktiv = an; speichernD({ sofort: true }); })),
      zeile("Dunkel ab", uhr(ds.abend_ab, (v, i) => { ds.abend_ab = v; speichernD({ feld: i }); })),
      zeile("Wieder hell ab", uhr(ds.morgen_ab, (v, i) => { ds.morgen_ab = v; speichernD({ feld: i }); })),
      hilfe("Abends wird eine helle Farbe zu ihrer dunklen Schwester (z. B. Hellblau → Blau). Eine dunkle Farbe bleibt, wie sie ist."),

      el("h4", { text: "Animationen" }),
      segment([["aus", "Aus"], ["sparsam", "Sparsam"], ["hoch", "Hoch"]], ds.animation || "sparsam", (w) => { ds.animation = w; speichernD({ sofort: true }); }),
      hilfe("Sparsam (Vorgabe) schont den Pi 3: Deko und Franzi bewegen sich nur ab und zu, der Sternenhimmel zieht langsam. " +
            "Hoch = flüssig wie früher (für einen Pi 5). Aus = alles steht still. Spiele laufen immer flüssig. Gilt nach dem nächsten Neuladen der Startseite."));
  }

  function karteWetter() {
    const w = d.wetter;
    const speichernW = (opt) => einstellung("wetter", { aktiv: w.aktiv, ort: w.ort, kopf: w.kopf, draussen: w.draussen }, opt);
    const ortText = el("b", { text: w.ort ? w.ort.name : "noch keiner" });
    const treffer = el("div", { class: "eh-liste" });
    const such = el("input", { type: "search", placeholder: "Ort oder Postleitzahl", class: "eh-breit", maxlength: 60 });
    const suchen = async () => {
      const { orte } = await hole("/api/eltern/wetter/orte?q=" + encodeURIComponent(such.value.trim()));
      treffer.replaceChildren(...(orte.length ? orte.map((o) => {
        const k = el("button", { type: "button", class: "eh-knopf leise", text: `${o.name}${o.zusatz ? " – " + o.zusatz : ""}` });
        k.addEventListener("click", () => { w.ort = { name: o.name, lat: o.lat, lon: o.lon }; ortText.textContent = o.name; treffer.replaceChildren();
                                           speichernW({ sofort: true }); });
        return k;
      }) : [hilfe("Nichts gefunden.")]));
    };
    such.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); suchen().catch((f) => zeige(f.message, true)); } });
    const j = w.jetzt || {};
    return karte("🌤️ Wetter",
      hilfe("Vorhersage von Open-Meteo, ohne Konto und ohne Schlüssel, mit denselben Regen-Regeln wie im Familien Dashboard. " +
            "Der Fernseher fragt höchstens alle 30 Minuten nach, nur für den Ort, den ihr hier eintragt."),
      el("div", { class: "eh-feld" }, el("span", {}, "Ort: ", ortText)),
      el("div", { class: "eh-reihe eh-suche" }, such, knopf("Suchen", suchen, "", "")),
      treffer,
      zeile("Wetter einschalten", schalter(w.aktiv, (an, c) => {
        if (an && !w.ort) { c.checked = false; zeige("Bitte zuerst einen Ort suchen und antippen.", true); return; }
        w.aktiv = an; speichernW({ sofort: true }); })),
      zeile("Oben auf der Startseite zeigen", schalter(w.kopf, (an) => { w.kopf = an; speichernW({ sofort: true }); })),
      zeile("Draußen-Spiele vorschlagen, wenn es trocken ist", schalter(w.draussen, (an) => { w.draussen = an; speichernW({ sofort: true }); })),
      j.daten ? hilfe(`Jetzt: ${j.daten.symbol} ${j.daten.temp}° · ${j.daten.regen.text}`) : j.fehler ? hilfe(j.fehler) : null);
  }

  function karteSchule() {
    const sc = d.schule;
    const speichernS = (opt) => einstellung("schule", { aktiv: sc.aktiv, tv_hinweis: sc.tv_hinweis, telegram: sc.telegram,
                                                         morgen_check: sc.morgen_check, morgen_check_um: sc.morgen_check_um,
                                                         klang: sc.klang, klang_morgen: sc.klang_morgen }, opt);
    const st = sc.stand || {};
    return karte("🏫 Schule (Klassenkiste)",
      hilfe("Der Fernseher liest mit der Anmeldung des Kindes aus der Klassenkiste: heutige Stunden mit Ausfall und Vertretung, " +
            "Hausaufgaben, Termine und Klassennachrichten. Er hakt nichts ab und markiert nichts als gelesen – er liest nur."),
      sc.eingerichtet ? null : hilfe("⚠️ Zuerst unter „Apps & Kacheln“ die Kachel „Klassenkiste“ einrichten und am Fernseher einmal anmelden."),
      zeile("Schul-Seite einschalten", schalter(sc.aktiv, (an) => { sc.aktiv = an; speichernS({ sofort: true }); })),
      el("h4", { text: "Was ist neu? (alle 15 Minuten)" }),
      zeile("Hinweis am Fernseher", schalter(sc.tv_hinweis, (an) => { sc.tv_hinweis = an; speichernS({ sofort: true }); })),
      zeile("Klang", klangWahl(sc.klang, (k) => { sc.klang = k; speichernS({ sofort: true }); })),
      zeile("Telegram an die Eltern", schalter(sc.telegram, (an) => { sc.telegram = an; speichernS({ sofort: true }); })),
      hilfe("Gemeldet werden neue Hausaufgaben, neue Klassennachrichten und Stundenausfälle oder Vertretungen – jeweils einmal."),
      el("h4", { text: "Morgen-Check am Abend" }),
      zeile("Morgen-Check", schalter(sc.morgen_check, (an) => { sc.morgen_check = an; speichernS({ sofort: true }); })),
      zeile("Uhrzeit", uhr(sc.morgen_check_um, (v, i) => { sc.morgen_check_um = v; speichernS({ feld: i }); })),
      zeile("Klang", klangWahl(sc.klang_morgen, (k) => { sc.klang_morgen = k; speichernS({ sofort: true }); })),
      hilfe("Nur am Abend vor einem Schultag: erste Stunde und Hausaufgaben bis morgen."),
      st.stand ? hilfe(`Zuletzt ${st.zeit || ""}: ${st.stand.hausaufgaben.length} offene Hausaufgaben, ${st.stand.nachrichten.length} Nachrichten.` +
                       (st.stand.morgen?.satz ? " " + st.stand.morgen.satz : "") + (st.hinweis ? " (" + st.hinweis + ")" : "")) : st.fehler ? hilfe("⚠️ " + st.fehler) : null,
      sc.aktiv ? knopf("Jetzt abrufen", async () => { const r = await sende("/api/eltern/schule/abrufen", {});
        zeige(`✔ ${r.hausaufgaben} Hausaufgaben, ${r.nachrichten} Nachrichten, ${r.stunden} Stunden heute`); }, "leise", "") : null);
  }

  function karteKinderwelten() {
    const kw = d.kinderwelten;
    const speichernK = () => einstellung("kinderwelten", { ...kw }, { sofort: true });
    const TEIL_NAMEN = [["geschichten", "📖 Geschichten"], ["buecher", "📚 Bücher (frei lesbare, kapitelweise)"], ["news", "📰 News der Familienfabrik"],
                        ["draussen", "🌳 Spiele für draußen"], ["raetsel", "🧩 Rätsel des Tages"]];
    return karte("📖 Kinderwelten (Familienfabrik)",
      hilfe("Kachel „Geschichten & Rätsel“: Inhalte der Kinderwelten in großer Schrift zum Selberlesen – direkt von familienfabrik.at, " +
            "ohne Anmeldung, nur lesen. Die Kachel „Kinderwelten“ (die ganze App im Browser) bleibt daneben bestehen."),
      zeile("Geschichten & Rätsel einschalten", schalter(kw.aktiv, (an) => { kw.aktiv = an; speichernK(); })),
      ...TEIL_NAMEN.map(([id, name]) => zeile(name, schalter(kw[id], (an) => { kw[id] = an; speichernK(); }))));
  }

  function karteNews() {
    const feld = el("textarea", { rows: 4, class: "eh-breit", placeholder: "eine RSS-Adresse pro Zeile, z. B. https://…/feed" });
    feld.value = (d.news.feeds || []).join("\n");
    feld.addEventListener("change", () => {
      d.news.feeds = feld.value.split(/\s+/).filter(Boolean);
      einstellung("news", { feeds: d.news.feeds }, { feld, sofort: true });
    });
    return karte("📰 Kinder-News",
      hilfe("Tragt hier die RSS-Adressen ein, die ihr selbst ausgesucht habt (höchstens 10). Ohne Adresse gibt es keine Kachel. " +
            "Gezeigt werden Überschrift und kurzer Text, ohne Links und Bilder. Gespeichert wird, sobald ihr das Feld verlasst."),
      feld);
  }

  /* ================================================================ 6.2: Mein Tag */
  const MT_SYMBOLE = ["☀️", "🌙", "🎒", "🦷", "👕", "🛏️", "🥣", "🧹", "📚", "✏️", "🚿", "🧦", "🍎", "💧", "🐶", "🌻", "⭐", "📋"];
  const MT_TIMER = [[0, "kein Timer"], [30, "½ Minute"], [60, "1 Minute"], [90, "1½ Minuten"], [120, "2 Minuten"], [180, "3 Minuten"], [300, "5 Minuten"], [600, "10 Minuten"], [900, "15 Minuten"]];
  const MT_VORLAGEN = {
    morgen: { name: "Morgen", symbol: "☀️", zeit: "06:45", fertig: "07:30", tage: [0, 1, 2, 3, 4], wann: "schule",
              schritte: [["Anziehen", "👕"], ["Frühstücken", "🥣"], ["Zähne putzen", "🦷", 120], ["Ranzen packen", "🎒"]] },
    abend: { name: "Abend", symbol: "🌙", zeit: "19:00", fertig: "19:45", tage: [0, 1, 2, 3, 4, 5, 6], wann: "immer",
             schritte: [["Zimmer aufräumen", "🧹"], ["Duschen", "🚿"], ["Zähne putzen", "🦷", 120], ["Schlafanzug an", "🛏️"]] },
  };
  function meintagHeute() {
    const h = d.meintag_heute;
    if (!h?.aktiv || (!h.routinen.length && !h.aufgaben?.length && !h.ranzen && !h.lesen)) return null;
    const lesen = h.lesen ? el("div", { class: "eh-eintrag" },
      el("div", { class: "eh-app-name" }, el("b", { text: "📖 Vorlesen" }), el("small", { text: `${h.lesen.stempel} Stempel im Lesepass` })),
      el("small", { class: h.lesen.stempel_heute ? "eh-gut" : "", text: `heute ${Math.floor(h.lesen.heute_min)} / ${h.lesen.ziel_min} min` + (h.lesen.stempel_heute ? " ✔" : "") })) : null;
    const antwort = (nr, ja) => sende("/api/eltern/meintag-aufgabe", { nr, ja }).then(laden);
    const aufgaben = (h.aufgaben || []).map((a) => el("div", { class: "eh-eintrag" },
      el("div", { class: "eh-app-name" }, el("b", { text: `${a.symbol || "⭐"} ${a.text}` }),
        el("small", { text: { wartet: "sagt: erledigt – stimmt das?", ja: "bestätigt ✔", nein: "noch nicht ganz" }[a.stand] || "noch offen" })),
      a.stand === "wartet" ? el("span", { class: "eh-reihe eng" }, knopf("👍 Ja", () => antwort(a.nr, true), "haupt", "Sterne gutgeschrieben ✔"),
                                knopf("Nein", () => antwort(a.nr, false), "", "Gesendet ✔")) : null));
    const ranzen = h.ranzen ? el("div", { class: "eh-eintrag" },
      el("div", { class: "eh-app-name" }, el("b", { text: `🎒 Ranzen für ${h.ranzen.name || "morgen"}` }),
        el("small", { text: h.ranzen.sachen.filter((x) => !x.erledigt).map((x) => x.text).join(", ") || "alles eingepackt" })),
      el("small", { class: h.ranzen.erledigt === h.ranzen.sachen.length ? "eh-gut" : "", text: `${h.ranzen.erledigt} / ${h.ranzen.sachen.length}` })) : null;
    return karte(`📋 Mein Tag · ⭐ ${h.sterne}`, ...aufgaben, ranzen, lesen, ...h.routinen.map((r) => el("div", { class: "eh-eintrag" },
      el("div", { class: "eh-app-name" }, el("b", { text: `${r.symbol || "📋"} ${r.name}` }),
        el("small", { text: r.schritte.filter((s) => !s.erledigt).map((s) => s.text).join(", ") || "alles erledigt" })),
      el("small", { class: r.geschafft ? "eh-gut" : r.vorbei ? "eh-warn" : "",
                    text: r.geschafft ? `geschafft ${r.geschafft} ✔` : `${r.erledigt} / ${r.anzahl}` + (r.vorbei ? "" : ` · bis ${r.fertig}`) }))));
  }
  function karteMeinTag() {
    const m = d.meintag;
    const speichernM = (opt) => einstellung("meintag", m, opt);
    const box = el("div", { class: "eh-liste" });
    const symbolWahl = (wert, bei) => auswahl([["", "–"], ...MT_SYMBOLE.map((x) => [x, x])], wert || "", bei);
    const mtOffen = karteMeinTag.offen = karteMeinTag.offen || new Set();
    const zeichne = () => box.replaceChildren(...m.routinen.map((r, n) => {
      const schritte = el("div", { class: "eh-liste" }, ...r.schritte.map((s, i) => el("div", { class: "eh-eintrag spalte" },
        el("div", { class: "eh-reihe eng" },
          symbolWahl(s.symbol, (v) => { s.symbol = v; speichernM({ sofort: true }); }),
          eingabe(s.text, (v, f) => { s.text = v; if (v.trim()) speichernM({ feld: f }); }, { type: "text", maxlength: 60, placeholder: "z. B. Zähne putzen", class: "eh-breit" }),
          knopf("×", () => { if (r.schritte.length < 2) { zeige("Eine Liste braucht mindestens einen Schritt.", true); return Promise.resolve(); }
            r.schritte.splice(i, 1); zeichne(); speichernM({ sofort: true }); return Promise.resolve(); }, "rund", "")),
        zeile("Timer", auswahl(MT_TIMER.map(([w, t]) => [String(w), t]), String(s.timer || 0), (v) => {
          if (+v) s.timer = +v; else delete s.timer; speichernM({ sofort: true }); })))));
      /* 6.9.65: jede Liste als zuklappbare Karte - Kopf mit Name, Uhrzeit und Erinnerung */
      const auf = el("details", { class: "eh-mt-gruppe" }, el("summary", {},
        el("b", { text: `${r.symbol || "📋"} ${r.name || "Neue Liste"}` }),
        el("small", { text: ` · ${r.zeit}–${r.fertig} · ${r.schritte.length} Schritte${r.erinnern ? " · 🔔 erinnert" : ""}${r.oeffnen === false ? "" : " · 📺 öffnet"}` })));
      if (mtOffen.has(r.nr)) auf.open = true;
      auf.addEventListener("toggle", () => { if (auf.open) mtOffen.add(r.nr); else mtOffen.delete(r.nr); });
      auf.append(el("div", { class: "eh-eintrag spalte eh-meintag" },
        el("div", { class: "eh-reihe eng" },
          symbolWahl(r.symbol, (v) => { r.symbol = v; speichernM({ sofort: true }); }),
          eingabe(r.name, (v, f) => { r.name = v; if (v.trim()) speichernM({ feld: f }); }, { type: "text", maxlength: 30, placeholder: "Name, z. B. Morgen", class: "eh-breit fett" }),
          knopf("×", () => { if (!confirm(`Liste „${r.name}“ löschen?`)) return Promise.resolve();
            m.routinen.splice(n, 1); zeichne(); speichernM({ sofort: true }); return Promise.resolve(); }, "rund", "")),
        el("div", { class: "eh-reihe eng" }, el("span", { text: "ab" }), uhr(r.zeit, (v, f) => { r.zeit = v; speichernM({ feld: f }); }),
          el("span", { text: "fertig um" }), uhr(r.fertig, (v, f) => { r.fertig = v; speichernM({ feld: f }); })),
        tageWahl(r.tage, (tage) => { r.tage = tage; speichernM(); }),
        segment([["immer", "immer"], ["schule", "nicht in den Ferien"], ["ferien", "nur in den Ferien"]], r.wann || "immer",
          (w) => { r.wann = w; speichernM({ sofort: true }); }),
        zeile("Erinnern: zu Beginn und alle 10 Min., bis geschafft (sonst Nachricht an euch)",
          schalter(r.erinnern, (an) => { r.erinnern = an; speichernM({ sofort: true }); })),
        zeile("Mein Tag am Fernseher von selbst öffnen", schalter(r.oeffnen !== false, (an) => {      /* 6.9.58 */
          if (an) delete r.oeffnen; else r.oeffnen = false; speichernM({ sofort: true }); })),
        zeile("Klang", klangWahl(r.klang, (k) => { if (k) r.klang = k; else delete r.klang; speichernM({ sofort: true }); })),
        zeile("Musik beim Timer", klangWahl(r.musik, (k) => { if (k) r.musik = k; else delete r.musik; speichernM({ sofort: true }); },
          { leer: "🎵 Zahnputz-Lied (eingebaut)", leerId: "" })),
        el("h4", { text: "Schritte" }), schritte,
        r.schritte.length < 12 ? knopf("+ Schritt", () => { r.schritte.push({ text: "", symbol: "" }); zeichne(); return Promise.resolve(); }, "leise", "") : null));
      return auf;
    }));
    zeichne();
    const neu = (art) => () => {
      const v = MT_VORLAGEN[art];
      const nr = Math.max(0, ...m.routinen.map((r) => r.nr)) + 1;
      mtOffen.add(nr);
      m.routinen.push({ nr, name: v.name, symbol: v.symbol, zeit: v.zeit, fertig: v.fertig, tage: [...v.tage], wann: v.wann, erinnern: true,
                        schritte: v.schritte.map(([text, symbol, timer]) => (timer ? { text, symbol, timer } : { text, symbol })) });
      zeichne(); speichernM({ sofort: true });
      return Promise.resolve();
    };
    const ausAberAngelegt = !m.aktiv && (m.routinen.length || m.aufgaben.length || m.ranzen.aktiv || m.lesen.aktiv);
    return karte("📋 Mein Tag",
      ausAberAngelegt ? el("div", { class: "eh-warnung", text: "⚠️ Listen sind angelegt, aber Mein Tag ist noch aus – am Fernseher erscheint nichts. Hier einschalten:" }) : null,
      zeile("Mein Tag einschalten", schalter(m.aktiv, (an, c) => {
        if (an && !m.routinen.length && !m.aufgaben.length && !m.ranzen.aktiv) { c.checked = false; zeige("Bitte zuerst eine Liste, eine Aufgabe oder den Ranzen-Check anlegen.", true); return; }
        m.aktiv = an; speichernM({ sofort: true }); })),
      hilfe("Listen für den Morgen, den Abend oder die Hausaufgaben. Am Fernseher hakt euer Kind die Schritte mit OK ab – ändern kann es nichts. " +
            "Schritte mit Timer (z. B. Zähne putzen, 2 Minuten) zeigen eine ablaufende Zeit-Scheibe mit Lied. Oben zeigt eine kleine Scheibe, " +
            "wie lange es noch bis „fertig um“ ist. Ist eine Liste geschafft, kommt eine Telegram-Meldung (Familie → Telegram, je Kontakt abschaltbar). " +
            "Jeden Tag beginnt die Liste neu. Den Stand seht ihr unter „Heute“."),
      box,
      m.routinen.length < 6 ? el("div", { class: "eh-reihe" }, knopf("+ Morgen-Liste", neu("morgen"), "leise", ""), knopf("+ Abend-Liste", neu("abend"), "leise", "")) : null);
  }
  /* 6.3: Ranzen-Check aus dem Stundenplan der Klassenkiste (nur lesen) */
  const kommaListe = (liste) => (liste || []).join(", ");
  const ausKomma = (text) => text.split(",").map((x) => x.trim()).filter(Boolean);
  function karteRanzen() {
    const m = d.meintag, r = m.ranzen;
    const speichernM = (opt) => einstellung("meintag", m, opt);
    const box = el("div", { class: "eh-liste" });
    const zeichne = () => box.replaceChildren(...r.faecher.map((f, n) => el("div", { class: "eh-eintrag spalte" },
      el("div", { class: "eh-reihe eng" },
        eingabe(f.fach, (v, i) => { f.fach = v; if (v.trim()) speichernM({ feld: i }); }, { type: "text", maxlength: 40, placeholder: "Fach, z. B. Sport", class: "eh-breit fett", list: "eh-faecher" }),
        knopf("×", () => { r.faecher.splice(n, 1); zeichne(); speichernM({ sofort: true }); return Promise.resolve(); }, "rund", "")),
      eingabe(kommaListe(f.sachen), (v, i) => { f.sachen = ausKomma(v); speichernM({ feld: i }); }, { type: "text", maxlength: 300, placeholder: "Sachen, mit Komma getrennt: Turnbeutel, Trinkflasche", class: "eh-breit" }))));
    zeichne();
    const faecher = d.meintag_faecher || [];
    return karte("🎒 Ranzen-Check",
      zeile("Ranzen-Check einschalten", schalter(r.aktiv, (an) => { r.aktiv = an; speichernM({ sofort: true }); })),
      hilfe("Aus dem Stundenplan der Klassenkiste (Inhalte → Schule muss an sein) entsteht für den nächsten Schultag eine Packliste: " +
            "was immer mit muss, dazu die Sachen der Fächer, die dran sind. Fällt eine Stunde aus, fehlt auch ihr Fach. Am Fernseher steht sie " +
            "in „Mein Tag“ unter „🎒 Ranzen“ und gilt bis zum Schultag."),
      el("div", { class: "eh-feld" }, el("span", { text: "Immer dabei" }),
        eingabe(kommaListe(r.immer), (v, i) => { r.immer = ausKomma(v); speichernM({ feld: i }); }, { type: "text", maxlength: 300, placeholder: "Federmäppchen, Hausaufgabenheft, Brotdose", class: "eh-breit" })),
      el("h4", { text: "Fach → Sachen" }), box,
      el("datalist", { id: "eh-faecher" }, ...faecher.map((f) => el("option", { value: f }))),
      faecher.length ? hilfe("Fächer im Stundenplan: " + faecher.join(", ")) : hilfe("Fächer werden vorgeschlagen, sobald die Schule-Seite den Stundenplan geholt hat."),
      r.faecher.length < 20 ? knopf("+ Fach", () => { r.faecher.push({ fach: "", sachen: [] }); zeichne(); return Promise.resolve(); }, "leise", "") : null);
  }
  /* 6.8.6: „Mama/Papa fragen“ bei gesperrten Seiten */
  function fragenHeute() {
    const offen = (d.fragen || []).filter((f) => f.stand === "offen");
    if (!offen.length) return null;
    const antwort = (nr, ja) => sende("/api/eltern/frage", { nr, ja }).then(laden);
    return karte("❓ Seite freigeben?", ...offen.map((f) => el("div", { class: "eh-eintrag" },
      el("div", { class: "eh-app-name" }, el("b", { text: f.host }), el("small", { text: `gefragt um ${f.zeit} Uhr` })),
      el("span", { class: "eh-reihe eng" }, knopf("✅ Erlauben", () => antwort(f.nr, true), "haupt", "Erlaubt ✔"),
        knopf("Nein", () => antwort(f.nr, false), "", "Abgelehnt ✔")))));
  }
  function karteFragen() {
    const fr = d.einstellungen.fragen = d.einstellungen.fragen || { aktiv: false };
    const tg = d.einstellungen.telegram || {};
    const bereit = tg.aktiv && (tg.chats || []).some((c) => c.eltern !== false);
    return karte("❓ Mama/Papa fragen",
      zeile("Bei gesperrten Seiten fragen lassen", schalter(fr.aktiv, (an) => { fr.aktiv = an; einstellung("fragen", fr, { sofort: true }); })),
      hilfe("Landet euer Kind auf einer Seite, die nicht auf der Liste steht, zeigt der Fernseher: „Drück ROT, dann fragen wir Mama oder Papa.“ " +
            "(Controller: Y, Tastatur: Suche-Taste.) Ihr bekommt per Telegram die Frage mit der Adresse und antwortet mit /erlauben 2 oder " +
            "/ablehnen 2 – oder hier unter „Heute“. Bei Ja kommt die Seite dauerhaft auf die Liste (unten bei den eigenen Seiten, dort auch wieder löschbar). " +
            "Dieselbe Seite fragt höchstens alle 10 Minuten. Solange keine Seite gesperrt ist, schalten ROT/GRÜN wie gewohnt den Ton."),
      bereit ? null : hilfe("⚠️ Dafür muss Telegram mit mindestens einem Eltern-Kontakt eingerichtet sein."));
  }
  /* 6.8.5: „Ich brauche Hilfe“ - Knopf am Fernseher, schickt sofort Telegram an die Eltern-Kontakte (ab Werk aus) */
  function karteHilfe() {
    const hi = d.einstellungen.hilfe = d.einstellungen.hilfe || { aktiv: false };
    const tg = d.einstellungen.telegram || {};
    const bereit = tg.aktiv && (tg.chats || []).some((c) => c.eltern !== false);
    return karte("🆘 Hilfe-Knopf am Fernseher",
      zeile("„Ich brauche Hilfe“ anzeigen", schalter(hi.aktiv, (an) => { hi.aktiv = an; einstellung("hilfe", hi, { sofort: true }); })),
      hilfe("Eine rote Kachel in „Mein Zimmer“. Drückt euer Kind dort OK, bekommen alle Eltern-Kontakte sofort eine Telegram-Nachricht " +
            "(höchstens alle 2 Minuten). Gedacht für Momente, in denen es allein zu Hause ist. Die Meldung lässt sich je Kontakt abschalten – " +
            "besser anlassen."),
      bereit ? null : hilfe("⚠️ Dafür muss Telegram eingerichtet sein und mindestens ein Kontakt „Eltern“ sein – sonst erscheint die Kachel nicht."));
  }
  /* 6.5: Lesen üben - Vorlese-Zeit mit dem USB-Mikro (nur Pegel, keine Aufnahme) */
  function karteLesen() {
    const m = d.meintag, le = m.lesen;
    const speichernM = (opt) => einstellung("meintag", m, opt);
    return karte("📖 Lesen üben",
      zeile("Lesen üben einschalten", schalter(le.aktiv, (an) => { le.aktiv = an; speichernM({ sofort: true }); })),
      zeile("Ziel am Tag", zahl(le.ziel_min, 2, 60, (v, i) => { le.ziel_min = v; speichernM({ feld: i }); }), el("small", { text: "min vorlesen" })),
      hilfe("Am Fernseher unter „Mein Tag → 📖 Lesen“: Euer Kind liest laut vor (z. B. ein Buch oder eine Geschichte aus „Geschichten & Rätsel“), " +
            "eine Scheibe zeigt, wie lange noch. Das USB-Mikro misst nur, ob gerade gesprochen wird – es wird nichts aufgenommen, gespeichert " +
            "oder erkannt. Ist das Ziel erreicht, gibt es einen Stempel im Lesepass und einen Stern. Ohne USB-Mikro geht es nicht."));
  }
  /* 6.4: Sterne, Level und Tausch gegen Spielzeit (ab Werk aus) */
  function karteSterne() {
    const m = d.meintag, t = m.tausch, h = d.meintag_heute || {};
    const speichernM = (opt) => einstellung("meintag", m, opt);
    return karte("🌟 Sterne & Franzi",
      h.aktiv ? el("div", { class: "eh-gross", text: `⭐ ${h.sterne} · Level ${h.level}` }) : null,
      hilfe("Sterne gibt es für jede geschaffte Liste (1), den gepackten Ranzen (1) und bestätigte Aufgaben (wie eingestellt). " +
            "Alle 10 verdienten Sterne steigt Franzi ein Level. Level 2–4 bringen je ein Kleidungsstück (Mütze, Blau, Sonnenbrille), " +
            "ab Level 5 je einen neuen Raum – dafür braucht es außerdem genug Sternentage (Tage mit mindestens einem Stern: Raum 2 ab 4, Raum 3 ab 10). Alles andere gibt es im Sterne-Shop. Ist Franzi als Haustier aus, " +
            "zieht euer Kind die Sachen unter „Mein Tag → 🌟 Franzi“ an. Sonntags zeigt der Fernseher einen Wochenrückblick."),
      zeile("Sterne gegen Spielzeit tauschen", schalter(t.aktiv, (an) => { t.aktiv = an; speichernM({ sofort: true }); })),
      zeile("Minuten je Stern", zahl(t.minuten, 1, 30, (v, i) => { t.minuten = v; speichernM({ feld: i }); }), el("small", { text: "min" })),
      zeile("höchstens am Tag", zahl(t.max_tag, 0, 240, (v, i) => { t.max_tag = v; speichernM({ feld: i }); }), el("small", { text: "min" })),
      hilfe("Getauschte Zeit kommt als Bonus zur Bildschirmzeit dazu. Beim Tauschen sinkt der Sterne-Stand, das Level bleibt."));
  }
  /* 6.9: Franzi als Haustier + Sterne-Shop */
  function karteFranzi() {
    const f = d.franzi;
    const speichernF = (opt) => einstellung("franzi", f, opt);
    return karte("🐾 Franzi als Haustier",
      hilfe("Franzi wohnt am Fernseher in ihrem Zimmer: füttern, waschen, streicheln, schlafen legen, mit ihr spielen. Ohne Pflege sind ihre " +
            "Werte nach etwa einem Tag leer (nachts langsamer), Fernsehzeit macht sie zusätzlich müde. Sie stirbt nie und nichts geht verloren. Mit der Zeit bekommt sie eine eigene Persönlichkeit. " +
            "Minispiele bei Franzi geben keine Sterne – Sterne gibt es in „Mein Tag“, ausgeben kann euer Kind sie im Sterne-Shop. " +
            "Wie viel Zeit bei Franzi zählt, stellt ihr unter „Apps & Kacheln“ ein (Kachel „Franzi“)."),
      zeile("Franzi ist da", schalter(f.aktiv, (an) => { f.aktiv = an; speichernF({ sofort: true }); })),
      zeile("Abenteuerreise nach", zahl(f.abenteuer_tage, 1, 60, (v, i) => { f.abenteuer_tage = v; speichernF({ feld: i }); }), el("small", { text: "Tagen Pause" })),
      hilfe("War euer Kind so lange nicht bei Franzi, geht sie auf Abenteuerreise und schickt eine Postkarte. Beim nächsten Besuch kommt sie fröhlich zurück – ohne Vorwürfe."),
      zeile("Geburtstag eures Kindes", eingabe(f.geburtstag || "", (v, i) => { f.geburtstag = v.trim(); if (!v.trim() || /^\d{1,2}\.\d{1,2}\.?$/.test(v.trim())) speichernF({ feld: i }); },
                                              { type: "text", maxlength: 6, placeholder: "TT.MM.", class: "eh-zahl" })),
      hilfe("Freiwillig: Dann gratuliert Franzi an diesem Tag. Nur Tag und Monat, kein Jahr."));
  }
  /* 6.9.66: Erst-dann - Spiele erst nach Lernen oder einer geschafften Mein-Tag-Liste */
  function karteErstDann() {
    const e = d.erst_dann = Object.assign({ aktiv: false, lernen_min: 15, liste: true }, d.erst_dann || {});
    const speichernE = (opt) => einstellung("erst_dann", e, opt);
    return karte("🎓 Erst-dann (Lernen vor Daddeln)",
      hilfe("Spiele mit „Gaming-Zeit“ gehen erst, wenn euer Kind heute gelernt oder eine Liste in „Mein Tag“ geschafft hat. " +
            "Filme, Musik, Lernen und Malen gehen immer. Ab Werk aus."),
      zeile("Erst-dann einschalten", schalter(e.aktiv, (an) => { e.aktiv = an; speichernE({ sofort: true }); })),
      zeile("… nach so viel Lernen", auswahl([[0, "– nicht nötig –"], [5, "5 min"], [10, "10 min"], [15, "15 min"], [20, "20 min"], [30, "30 min"],
                                             [45, "45 min"], [60, "60 min"]].map(([w, t]) => [String(w), t]), String(e.lernen_min),
                                            (v) => { e.lernen_min = +v; speichernE({ sofort: true }); })),
      zeile("… oder nach einer geschafften Mein-Tag-Liste", schalter(e.liste, (an) => { e.liste = an; speichernE({ sofort: true }); })));
  }

  /* 6.9.61: Was Franzi auf der Startseite sagt */
  function karteSprueche() {
    const f = d.franzi;
    f.sprueche = Object.assign({ witze: false, ordnung: false, schule: false, eigene: [] }, f.sprueche || {});
    const sp = f.sprueche;
    const speichernF = (opt) => einstellung("franzi", f, opt);
    const ANLAESSE = [["immer", "immer"], ["morgens", "morgens"], ["abends", "abends"], ["schule", "vor Schultagen"],
                      ["wochenende", "am Wochenende"], ["geschafft", "wenn etwas geschafft ist"], ["witz", "als Witz"]];
    const liste = el("div", { class: "eh-liste" });
    const zeichne = () => liste.replaceChildren(...sp.eigene.map((e, n) => el("div", { class: "eh-eintrag spalte" },
      el("div", { class: "eh-reihe eng" },
        eingabe(e.text, (v, i) => { e.text = v; if (v.trim()) speichernF({ feld: i }); }, { type: "text", maxlength: 120, placeholder: "z. B. Hast du heute schon getrunken?", class: "eh-breit" }),
        knopf("×", () => { sp.eigene.splice(n, 1); zeichne(); speichernF({ sofort: true }); return Promise.resolve(); }, "rund", "")),
      zeile("Wann", auswahl(ANLAESSE, e.anlass || "immer", (v) => { e.anlass = v; speichernF({ sofort: true }); })))));
    zeichne();
    return karte("💬 Was Franzi sagt",
      hilfe("Alle paar Minuten sagt Franzi auf der Startseite etwas Passendes: zum Wetter, zur laufenden Routine, zu Aufgaben, " +
            "wenn etwas geschafft ist – oder tröstet, wenn es mal nicht geklappt hat. Hier schaltet ihr weitere Arten dazu und " +
            "schreibt eigene Sätze."),
      zeile("😄 Witze (die Witze-Kachel fällt dann weg)", schalter(sp.witze, (an) => { sp.witze = an; speichernF({ sofort: true }); })),
      zeile("🧹 Ordnungs-Tipps", schalter(sp.ordnung, (an) => { sp.ordnung = an; speichernF({ sofort: true }); })),
      zeile("🎒 Schule & Kleidung (abends vor Schultagen)", schalter(sp.schule, (an) => { sp.schule = an; speichernF({ sofort: true }); })),
      el("h4", { text: "Eigene Sätze" }), liste,
      sp.eigene.length < 40 ? knopf("+ Satz", () => { sp.eigene.push({ text: "", anlass: "immer" }); zeichne(); return Promise.resolve(); }, "leise", "") : null);
  }
  function karteShop() {
    const f = d.franzi;
    const speichernF = (opt) => einstellung("franzi", f, opt);
    const ARTEN = [["spiel", "🎮 Spiele (bei Franzi)"], ["raum", "🏠 Räume"], ["kleidung", "👗 Kleidung"], ["spielzeug", "🧸 Spielzeug"], ["moebel", "🪴 Möbel"]];
    const preise = el("div", { class: "eh-liste" });
    for (const [art, titel] of ARTEN) {
      /* 6.9.59: je Art aufklappbar und als Raster (am PC mehrspaltig) statt einer endlosen Liste */
      const gruppe = el("div", { class: "eh-shop-raster" });
      const alle = d.franzi_katalog.filter((x) => x.art === art);
      const auf = el("details", { class: "eh-shop-gruppe" }, el("summary", { text: `${titel} (${alle.length})` }), gruppe);
      preise.append(auf);
      const preiseHaupt = preise;
      for (const k of alle) {
        const preise = gruppe;                              /* Einträge landen in der Gruppe */
        if (k.start) { preise.append(zeile(`${k.symbol} ${k.name}`, el("small", { text: "von Anfang an da" }))); continue; }
        const hat = (d.franzi_besitz || []).includes(k.id);
        /* 6.9.37: Level-Belohnungen haben keinen Preis (verschenken geht trotzdem) */
        if (k.level) { preise.append(zeile(`${k.symbol} ${k.name}`, el("small", { text: `Belohnung für Level ${k.level}` + (k.tage ? ` + ${k.tage} Sternentage` : "") }),
          hat ? el("small", { text: "✔ hat sie" }) : knopf("🎁", () => sende("/api/eltern/franzi-geschenk", { item: k.id }).then((a) => {
            d.franzi_besitz = a.besitz; zeige(`${a.name} ist bei Franzi – sie sagt es beim nächsten Besuch.`); return a; }), "leise rund"))); continue; }
        preise.append(zeile(`${k.symbol} ${k.name}`, zahl(f.preise[k.id] ?? k.preis, 0, 999, (v, i) => { f.preise[k.id] = v; speichernF({ feld: i }); }), el("small", { text: "⭐" }),
          hat ? el("small", { text: "✔ hat sie" }) : knopf("🎁", () => sende("/api/eltern/franzi-geschenk", { item: k.id }).then((a) => {
            d.franzi_besitz = a.besitz; zeige(`${a.name} ist bei Franzi – sie sagt es beim nächsten Besuch.`); return a; }), "leise rund")));
      }
      void preiseHaupt;
    }
    const angebote = el("div", { class: "eh-liste" });
    const ART_A = [["minuten", "Spielzeit"], ["wochenende", "Spielzeit am Wochenende"], ["sperrzeit", "Spielzeit in der Pause (Sperrzeit)"], ["frei", "Etwas anderes (Text)"]];
    const zeichne = () => angebote.replaceChildren(...f.angebote.map((a, n) => el("div", { class: "eh-eintrag spalte" },
      el("div", { class: "eh-reihe eng" },
        auswahl([["🎁", "🎁"], ["⏰", "⏰"], ["🎮", "🎮"], ["🍦", "🍦"], ["🎬", "🎬"], ["🌙", "🌙"], ["🏊", "🏊"]], a.symbol || "🎁", (v) => { a.symbol = v; speichernF({ sofort: true }); }),
        eingabe(a.name, (v, i) => { a.name = v; if (v.trim()) speichernF({ feld: i }); }, { type: "text", maxlength: 60, placeholder: "z. B. 30 Minuten extra", class: "eh-breit" }),
        knopf("×", () => { f.angebote.splice(n, 1); zeichne(); speichernF({ sofort: true }); return Promise.resolve(); }, "rund", "")),
      zeile("Art", auswahl(ART_A, a.art, (v) => { a.art = v; if (v !== "frei" && !a.minuten) a.minuten = 30; zeichne(); speichernF({ sofort: true }); })),
      a.art !== "frei" ? zeile("Minuten", zahl(a.minuten || 30, 1, 240, (v, i) => { a.minuten = v; speichernF({ feld: i }); })) : null,
      zeile("Preis", zahl(a.preis, 1, 999, (v, i) => { a.preis = v; speichernF({ feld: i }); }), el("small", { text: "⭐" })),
      zeile("je Woche höchstens", zahl(a.pro_woche ?? 1, 0, 50, (v, i) => { a.pro_woche = v; speichernF({ feld: i }); }), el("small", { text: "mal (0 = immer)" })),
      zeile("Angebot an", schalter(a.aktiv !== false, (an) => { a.aktiv = an; speichernF({ sofort: true }); })))));
    zeichne();
    return karte("🛍️ Sterne-Shop",
      hilfe("Preise in Sternen. Gekauftes gehört eurem Kind für immer (Spiele, Räume, Kleidung, Spielzeug, Möbel). " +
            "Eure Angebote: Spielzeit kommt als Bonus dazu (nicht während einer Pause), „in der Pause“ gibt Minuten, in denen alles geht, " +
            "„Etwas anderes“ meldet nur per Telegram, dass es eingelöst wurde."),
      el("h4", { text: "Eure Angebote" }),
      angebote,
      f.angebote.length < 12 ? knopf("+ Angebot", () => {
        f.angebote.push({ nr: Math.max(0, ...f.angebote.map((a) => a.nr)) + 1, name: "30 Minuten extra", symbol: "⏰", art: "minuten", minuten: 30, preis: 5, pro_woche: 1, aktiv: true });
        zeichne(); speichernF({ sofort: true }); return Promise.resolve(); }, "leise", "") : null,
      el("h4", { text: "Preise" }),
      hilfe("🎁 schenkt Franzi etwas direkt – ohne Sterne. Sie freut sich beim nächsten Besuch und schreibt es ins Tagebuch."),
      preise);
  }
  /* 6.3: Ämter und Aufgaben - das Kind meldet „erledigt“, die Eltern bestätigen → Sterne */
  function karteAufgaben() {
    const m = d.meintag;
    const speichernM = (opt) => einstellung("meintag", m, opt);
    const box = el("div", { class: "eh-liste" });
    const zeichne = () => box.replaceChildren(...m.aufgaben.map((a, n) => el("div", { class: "eh-eintrag spalte" },
      el("div", { class: "eh-reihe eng" },
        auswahl([["", "–"], ...MT_SYMBOLE.map((x) => [x, x])], a.symbol || "", (v) => { a.symbol = v; speichernM({ sofort: true }); }),
        eingabe(a.text, (v, i) => { a.text = v; if (v.trim()) speichernM({ feld: i }); }, { type: "text", maxlength: 60, placeholder: "z. B. Zimmer aufräumen", class: "eh-breit" }),
        knopf("×", () => { m.aufgaben.splice(n, 1); zeichne(); speichernM({ sofort: true }); return Promise.resolve(); }, "rund", "")),
      tageWahl(a.tage, (tage) => { a.tage = tage; if (a.text.trim()) speichernM(); }),
      zeile("Sterne", auswahl([1, 2, 3, 4, 5].map((x) => [String(x), "⭐".repeat(x)]), String(a.sterne || 1), (v) => { a.sterne = +v; if (a.text.trim()) speichernM({ sofort: true }); })))));
    zeichne();
    return karte("⭐ Ämter & Aufgaben",
      hilfe("Aufgaben an bestimmten Tagen (z. B. Tisch decken, Blumen gießen). Am Fernseher drückt euer Kind „Hab ich gemacht!“; ihr bestätigt " +
            "unter „Heute“ oder per Telegram mit /ja 3 bzw. /nein 3 (die Nummer steht in der Meldung). Bei Ja gibt es Sterne, bei Nein heißt es " +
            "freundlich „fast geschafft, schau nochmal nach“. Wofür die Sterne gut sind, kommt mit der nächsten Version."),
      box,
      m.aufgaben.length < 12 ? knopf("+ Aufgabe", () => {
        m.aufgaben.push({ nr: Math.max(0, ...m.aufgaben.map((a) => a.nr)) + 1, text: "", symbol: "🧹", tage: [0, 1, 2, 3, 4, 5, 6], sterne: 1 });
        zeichne(); return Promise.resolve(); }, "leise", "") : null);
  }

  /* ================================================================ Mehr */
  function seiteMehr() {
    const w = d.einstellungen.whitelist = d.einstellungen.whitelist || {};
    const domains = Object.entries(d.domains || {}).sort((a, b) => (b[1].blockiert - a[1].blockiert) || (b[1].anzahl - a[1].anzahl));
    const erlaubt = new Set(w.zusatz || []);
    const blockiert = domains.filter(([host, x]) => x.blockiert > 0 && !erlaubt.has(host));
    const zusatz = el("textarea", { rows: 3, class: "eh-breit", placeholder: "eine Domain pro Zeile, z. B. beispiel.de" });
    zusatz.value = (w.zusatz || []).join("\n");
    zusatz.addEventListener("input", () => {
      w.zusatz = zusatz.value.split(/\s+/).filter(Boolean); einstellung("whitelist", w, { feld: zusatz }); });
    const exportiere = (format) => async () => {
      const antwort = await fetch("/api/eltern/whitelist?format=" + format, { headers: { "X-FF-Eltern": leseElternToken() } });
      el("a", { href: URL.createObjectURL(await antwort.blob()), download: `fernsehfranzi-${format}.txt` }).click();
    };
    const bilder = el("div", { class: "eh-bilder" });
    const bilderTitel = el("h3", { text: "Bilder" });
    hole("/api/eltern/zeichnungen").then(({ zeichnungen }) => {
      const gesehen = d.zeichnungen_gesehen || 0;
      const neu = zeichnungen.filter((z) => z.zeit > gesehen).length;
      if (neu) {
        bilderTitel.textContent = `Bilder – ${neu} neu ✨`;
        bilderTitel.after(knopf("Als gesehen markieren", () => sende("/api/eltern/zeichnungen-gesehen", { zeit: Date.now() / 1000 }).then(laden), "leise"));
      }
      for (const z of zeichnungen) {
        const bild = el("img", { alt: z.datei, class: z.zeit > gesehen ? "neu" : "" });
        fetch(z.url, { headers: { "X-FF-Eltern": leseElternToken() } }).then((a) => a.blob()).then((b) => { bild.src = URL.createObjectURL(b); });
        bilder.append(el("figure", {}, bild, knopf("Löschen", () => sende("/api/eltern/zeichnung-loeschen", { datei: z.datei }).then(laden), "leise gefahr", "Gelöscht ✔")));
      }
      if (!zeichnungen.length) bilder.append(hilfe("Noch keine Bilder gemalt."));
    }).catch(() => {});
    const sticker = d.sticker.filter((s) => s.seit);
    const name = eingabe(d.einstellungen.name || "", (v, i) => einstellung("name", v.trim(), { feld: i }), { type: "text", maxlength: 40, placeholder: "Name des Kindes" });
    return {
      fotoalbum: karteSpeicherFotoalbum(),
      handyspiele: karteHandyspiele(),
      telegram: karteTelegram(),
      gutscheine: karteGutscheine(),
      inhalte: karteInhalte(),
      stickerEigen: karteStickerEigen(),
      internet: karte(`Internetseiten${blockiert.length ? ` – ${blockiert.length} blockiert` : ""}`,
        hilfe("Was der Fernseher-Browser geladen hat. Fehlen auf einer Seite Bilder oder Videos, steht hier oft ein blockierter Eintrag."),
        blockiert.length > 1 ? knopf(`Alle ${blockiert.length} blockierten erlauben`, () =>
          sende("/api/eltern/domains-erlauben", { hosts: blockiert.map(([h]) => h) }).then(laden), "haupt") : null,
        ...(domains.length ? kurzliste(domains.slice(0, 200).map(([host, x]) => el("div", { class: "eh-eintrag" },
          el("div", { class: "eh-app-name" }, el("b", { text: host }),
            el("small", { text: `${x.anzahl}× geladen${x.blockiert ? `, ${x.blockiert}× blockiert` : ""} · ${x.apps.join(", ")}` })),
          erlaubt.has(host) || !x.blockiert ? el("small", { text: erlaubt.has(host) ? "erlaubt" : "" }) :
            knopf("Erlauben", () => sende("/api/eltern/domains-erlauben", { hosts: [host] }).then(laden), "chip"))), 8)
          : [hilfe("Noch nichts aufgezeichnet.")])),
      zusatz: karte("Zusätzlich erlaubte Seiten", zusatz,
        el("div", { class: "eh-reihe" }, knopf("Export Pi-hole", exportiere("pihole"), "leise", ""), knopf("Export Fritzbox", exportiere("fritzbox"), "leise", ""))),
      bilder: karte("", bilderTitel, bilder),
      sticker: karte(`Sticker (${sticker.length} von ${d.sticker.length})`,
        el("div", { class: "eh-sticker", text: sticker.map((s) => s.symbol).join(" ") || "Noch keine." }),
        ...kurzliste(sticker.slice().reverse().map((s) => hilfe(`${s.symbol} ${s.name} – ${s.seit}`)), 5)),
      anleitungen: karte("Anleitungen zum Lesen und Drucken",
        el("div", { class: "eh-reihe" },
          el("a", { class: "eh-knopf leise", href: "/handbuch.pdf", target: "_blank", text: "📕 Handbuch (alles)" }),
          el("a", { class: "eh-knopf leise", href: "/kurzanleitung.pdf", target: "_blank", text: "🗒️ Kurzanleitung zum Ausdrucken" })),
        el("div", { class: "eh-reihe" },
          el("a", { class: "eh-knopf leise", href: "/anleitung.pdf", target: "_blank", text: "📖 Anleitung" }),
          el("a", { class: "eh-knopf leise", href: "/kinder-anleitung.pdf", target: "_blank", text: "🧒 Kinder-Anleitung" }))),
      geraet: karte("Gerät",
        el("div", { class: "eh-feld" }, el("span", { text: "Begrüßung mit Namen" }), name),
        el("div", { class: "eh-reihe" },
          knopf("Neustart", () => confirm("Fernseher-Pi neu starten?") ? sende("/api/eltern/geraet", { aktion: "neustart" }) : null, "gefahr leise"),
          knopf("Ausschalten", () => confirm("Fernseher-Pi ausschalten?") ? sende("/api/eltern/geraet", { aktion: "aus" }) : null, "gefahr leise"),
          knopf("Abmelden", () => sende("/api/eltern/abmelden").then(() => { setzeElternToken(""); anmelden(); }), "leise", "")),
        hilfe(`Version ${d.version || ""} · Die PIN wird am Fernseher festgelegt und geändert (BLAU).`)),
      scraper: karteScraper(),
      bluetooth: karteBluetooth(),
      sicherung: karteSicherung(),
    };
  }

  anmelden();
}
