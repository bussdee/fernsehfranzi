/* FernsehFranzi 3.3 - Eltern-Seite im Heimnetz (Handy/PC), neu aufgebaut.
 *
 * - Leiste unten: Heute · Regeln · Apps · Bass · Mehr (je eine Seite statt einer langen Liste)
 * - echte Eingabefelder (Uhrzeit, Wochentage zum Antippen, Datum) statt "a | b | c"-Textzeilen
 * - speichert von selbst (kurz nach der Eingabe) und zeigt „Gespeichert ✔“; Fehler stehen am Feld
 * Die PIN prüft der Server; alle Änderungen gehen über dieselben /api/eltern/...-Aufrufe wie bisher.
 */
import { hole, sende, el, setzeElternToken, leseElternToken } from "./gemeinsam.js";

const TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const SYMBOL_WAHL = [["film", "🎬 Film"], ["musik", "🎵 Musik"], ["lernen", "🎓 Lernen"], ["buch", "📚 Buch"],
                     ["haus", "🏠 Haus"], ["spiel", "🕹️ Spiel"], ["stern", "⭐ Stern"], ["web", "🌐 Internet"],
                     ["malen", "🎨 Malen"], ["tier", "🐾 Tiere"], ["ball", "⚽ Sport"], ["mond", "🌙 Mond"], ["video", "▶️ Video"]];
/* 3.4: frei = kein Timer · zaehlt = allgemeiner Timer (optional höchstens X min). Sperrzeiten gelten für alle Apps. */
const ZEIT_WAHL = [["frei", "frei (kein Timer)"], ["zaehlt", "Timer"]];
const ZEIT_ERKLAERT = { zaehlt: "zieht vom allgemeinen Timer ab", frei: "kostet keine Zeit – nur die Sperrzeiten gelten" };
const zeitart = (app) => (app.zeit === "zaehlt" ? "zaehlt" : "frei");
const TYP_NAME = { web: "Webseite", hoerbuch: "Hörbücher", konsole: "Retro-Spiele", desktop: "Programm", youtube: "YouTube", video: "Videos" };
/* Symbole für eigene Sticker - nur solche, die die Emoji-Schrift am Fernseher sicher hat (sie steht in dieser Datei) */
const STICKER_SYMBOLE = ["🦄", "🌟", "🏆", "🥇", "💎", "👑", "🚀", "🌈", "🎉", "💖", "🧹", "🛏️", "🦷", "🍎", "🥦", "📚",
                         "✏️", "🎹", "🎤", "🐶", "🐱", "🦋", "🌻", "⚽", "🚲", "🏊", "🧩", "🎨", "🌙", "☀️"];
const SEITEN = [["heute", "🏠", "Heute"], ["regeln", "⏰", "Regeln"], ["apps", "🧩", "Apps"], ["bass", "🎼", "Musik"], ["statistik", "📊", "Statistik"], ["mehr", "⚙️", "Mehr"]];

export function elternHandy(wurzel) {
  let d = null;                     /* Daten vom Server (wird beim Speichern mitgeändert) */
  let seite = (location.hash || "#heute").slice(1);
  if (!SEITEN.some(([id]) => id === seite)) seite = "heute";

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
  const hilfe = (text) => el("p", { class: "eh-hilfe", text });
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
    const leiste = el("nav", { class: "eh-leiste" }, ...SEITEN.map(([id, symbol, name]) => {
      const a = el("a", { href: "#" + id, class: id === seite ? "an" : "" }, el("span", { text: symbol }), el("small", { text: name }));
      a.addEventListener("click", (e) => { e.preventDefault(); seite = id; history.replaceState(null, "", "#" + id); zeichne(); scrollTo(0, 0); });
      return a;
    }));
    const h = d.heute;
    const kopf = el("header", { class: "eh-kopf" }, el("b", { text: "📺 FernsehFranzi" }),
      el("span", { class: "eh-chip" + (d.gesperrt ? " rot" : ""), text: d.gesperrt ? "gesperrt" : h.ohne_limit ? "ohne Limit" : `${h.rest_min ?? "–"} min übrig` }));
    const seiten = { heute: seiteHeute, regeln: seiteRegeln, apps: seiteApps, bass: seiteBass, statistik: seiteStatistik, mehr: seiteMehr };
    inhalt.append(...seiten[seite]());
    wurzel.replaceChildren(kopf, inhalt, leiste, meldung);
  }

  /* ================================================================ Heute */
  function seiteHeute() {
    const h = d.heute;
    const nachricht = el("input", { type: "text", maxlength: 140, placeholder: "Nachricht an den Fernseher …", class: "eh-breit" });
    const senden = async (text) => { await sende("/api/eltern/nachricht", { text }); nachricht.value = ""; };
    const sendenKnopf = el("button", { class: "eh-knopf haupt", type: "submit", text: "Senden" });
    const form = el("form", { class: "eh-reihe eng" }, nachricht, sendenKnopf);
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      if (nachricht.value.trim()) aktion(sendenKnopf, () => senden(nachricht.value), "Gesendet ✔");
    });
    const woche = Object.entries(d.woche || {}).slice(-7);
    const groesste = Math.max(30, ...woche.map(([, w]) => w.genutzt_min));
    const ton = d.einstellungen.ton?.ziel || "hdmi";
    return [
      d.zeit_pruefen ? karte("", el("b", { text: "Neu in 3.4: Sperrzeiten" }),
        hilfe("Die Zeitregeln wurden übernommen (Zeitfenster → Sperrzeiten „Nacht“ und „Schule“). Bitte unter Regeln und bei den Apps kurz prüfen."),
        knopf("Zu den Regeln", () => { seite = "regeln"; history.replaceState(null, "", "#regeln"); zeichne(); scrollTo(0, 0); return Promise.resolve(); }, "haupt", "")) : null,
      (d.sperrzeiten_jetzt || []).length ? karte("", el("div", { text: `🌙 Gerade Sperrzeit: ${d.sperrzeiten_jetzt.join(", ")}` })) : null,
      karte("", el("div", { class: "eh-gross", text: d.gesperrt ? "🔒 gesperrt" : h.ohne_limit ? "ohne Limit" : `${h.rest_min ?? "–"} min` }),
        el("div", { class: "eh-hilfe", text: `übrig heute (${h.tagesart === "frei" ? "freier Tag" : "Schultag"}) · gespielt ${h.genutzt_min} min · RetroPie ${h.retropie_min} min` +
                                           (h.bonus_min ? ` · Bonus ${h.bonus_min} min` : "") }),
        el("div", { class: "eh-reihe" },
          knopf("+15 min", () => sende("/api/eltern/bonus", { art: "15" }).then(laden)),
          knopf("+30 min", () => sende("/api/eltern/bonus", { art: "30" }).then(laden)),
          knopf("ohne Limit", () => sende("/api/eltern/bonus", { art: "ohne_limit" }).then(laden))),
        d.gesperrt ? knopf("🔓 Fernseher freigeben", () => sende("/api/eltern/sperre", { frei: true }).then(laden), "haupt breit")
                   : knopf("🔒 Jetzt sperren", () => sende("/api/eltern/sperre", { text: "Der Fernseher macht jetzt Pause." }).then(laden), "gefahr breit")),
      karte("Nachricht", form,
        el("div", { class: "eh-chips" }, ...["Essen ist fertig!", "Bitte Zähne putzen!", "In 5 Minuten ausschalten, bitte.", "Komm mal kurz zu mir"]
          .map((t) => knopf(t, () => senden(t), "chip", "Gesendet ✔")))),
      karte("Fernseher",
        zeile("Ton", segment([["hdmi", "Fernseher"], ["klinke", "Klinke"]], ton,
          (z) => speichere("ton", async () => {
            await sende("/api/eltern/ton", { ziel: z });
            d.einstellungen.ton = { ...(d.einstellungen.ton || {}), ziel: z };
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
    const timer = (art) => zeile(art === "schultag" ? "Schultag" : "Wochenende & Ferien",
      zahl(r.budget_min[art], 0, 1440, (v, i) => { r.budget_min[art] = v; regeln({ feld: i }); }), el("small", { text: "min" }));

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

    const ferienBox = el("div", { class: "eh-liste" });
    const zeichneFerien = () => ferienBox.replaceChildren(...r.ferien.map((zeitraum, n) => el("div", { class: "eh-eintrag" },
      eingabe(zeitraum[0], (v, i) => { zeitraum[0] = v; if (v && zeitraum[1]) regeln({ feld: i }); }, { type: "date" }),
      el("span", { text: "bis" }),
      eingabe(zeitraum[1], (v, i) => { zeitraum[1] = v; if (v && zeitraum[0]) regeln({ feld: i }); }, { type: "date" }),
      knopf("×", () => { r.ferien.splice(n, 1); zeichneFerien(); regeln({ sofort: true }); return Promise.resolve(); }, "rund", ""))));
    zeichneFerien();

    const erinnerungBox = el("div", { class: "eh-liste" });
    const zeichneErinnerungen = () => erinnerungBox.replaceChildren(...f.erinnerungen.map((e, n) => el("div", { class: "eh-eintrag spalte" },
      el("div", { class: "eh-reihe eng" },
        uhr(e.zeit, (v, i) => { e.zeit = v; if (e.text.trim()) familie({ feld: i }); }),
        eingabe(e.text, (v, i) => { e.text = v; if (v.trim()) familie({ feld: i }); }, { type: "text", maxlength: 120, placeholder: "z. B. Zähneputzen!", class: "eh-breit" }),
        knopf("×", () => { f.erinnerungen.splice(n, 1); zeichneErinnerungen(); familie({ sofort: true }); return Promise.resolve(); }, "rund", "")),
      tageWahl(e.tage, (tage) => { e.tage = tage; if (e.text.trim()) familie(); }))));
    zeichneErinnerungen();

    const b = f.bewegungspause, l = f.lernbonus;
    const gn = d.apps.find((a) => a.id === "gute-nacht");
    return [
      karte("Allgemeiner Timer", timer("schultag"), timer("frei"),
        hilfe("Gilt für alle Apps mit Zeitart „Timer“. Einzelne Apps können zusätzlich „höchstens X min“ haben (Apps)."),
        zeile("Fernseher aus, wenn der Timer abgelaufen ist", schalter(f.tv_aus_bei_zeitende, (an) => { f.tv_aus_bei_zeitende = an; familie({ sofort: true }); }))),
      karte("Sperrzeiten", sperrBox,
        hilfe("In einer Sperrzeit sind alle Apps gesperrt – außer die, die sie ausdrücklich erlauben (Apps → „erlaubt in“). 10, 5 und 1 Minute vorher kommt ein Hinweis."),
        knopf("+ Sperrzeit", () => { r.sperrzeiten.push({ name: "Pause " + (r.sperrzeiten.length + 1), von: "12:00", bis: "13:00",
          tage: [0, 1, 2, 3, 4, 5, 6], ferien_frei: false, nacht: false }); zeichneSperren(); regeln({ sofort: true }); return Promise.resolve(); }, "leise", "")),
      karte("Gute Nacht",
        zeile("Zur Nachtruhe automatisch öffnen", schalter(f.gute_nacht?.automatisch, (an) => { f.gute_nacht = { automatisch: an }; familie({ sofort: true }); })),
        hilfe("An: Zu Beginn der Nachtruhe öffnet sich Gute Nacht und fragt nach der Zeit, dann geht das Hörbuch dort weiter, wo es gestern aufgehört hat. " +
              "Aus: ein 15-Sekunden-Countdown fragt „Fernseher aus / an / Gute Nacht“."),
        zeile("längster Sleep-Timer", auswahl([[15, "15 min"], [30, "30 min"], [45, "45 min"], [60, "1 Stunde"], [90, "1½ Stunden"], [120, "2 Stunden"]]
          .map(([w, t]) => [String(w), t]), String(f.hoerbuch?.schlaf_max_min ?? 60), (v) => { f.hoerbuch = { ...(f.hoerbuch || {}), schlaf_max_min: +v }; familie({ sofort: true }); })),
        hilfe(gn && gn.start ? "Hörbuch-Ordner: eingerichtet (Apps → Gute Nacht)." : "⚠️ Noch kein Hörbuch-Ordner: Apps → Gute Nacht → Freigabelink eintragen.")),
      karteWecker(),
      karte("Ferien", ferienBox,
        knopf("+ Ferien eintragen", () => { r.ferien.push(["", ""]); zeichneFerien(); return Promise.resolve(); }, "leise", "")),
      karte("Erinnerungen", erinnerungBox,
        hilfe("Erscheinen zur Uhrzeit am Fernseher (mit Gong) und bleiben stehen, bis sie mit OK bestätigt werden – alle 5 Minuten kommen sie wieder."),
        knopf("+ Erinnerung", () => { f.erinnerungen.push({ zeit: "19:00", text: "", tage: [0, 1, 2, 3, 4, 5, 6] }); zeichneErinnerungen(); return Promise.resolve(); }, "leise", "")),
      karte("Bewegungspause",
        zeile("Bewegungspause", schalter(b.aktiv, (an) => { b.aktiv = an; familie({ sofort: true }); })),
        zeile("nach … Spielen am Stück", zahl(b.nach_min, 10, 240, (v, i) => { b.nach_min = v; familie({ feld: i }); }), el("small", { text: "min" })),
        zeile("Dauer", zahl(b.dauer_min, 1, 15, (v, i) => { b.dauer_min = v; familie({ feld: i }); }), el("small", { text: "min" }))),
      karte("Lernen bringt Spielzeit",
        zeile("Lernbonus", schalter(l.aktiv, (an) => { l.aktiv = an; familie({ sofort: true }); })),
        zeile("je … Lernen", zahl(l.lernen_min, 5, 120, (v, i) => { l.lernen_min = v; familie({ feld: i }); }), el("small", { text: "min" })),
        zeile("gibt es Bonus", zahl(l.bonus_min, 1, 60, (v, i) => { l.bonus_min = v; familie({ feld: i }); }), el("small", { text: "min" })),
        zeile("höchstens am Tag", zahl(l.max_bonus_min, 0, 240, (v, i) => { l.max_bonus_min = v; familie({ feld: i }); }), el("small", { text: "min" })),
        el("details", {}, el("summary", { text: "Wie wird geprüft?" }),
          zeile("mindestens Tasten pro Minute", zahl(l.tasten_pro_minute ?? 3, 1, 30, (v, i) => { l.tasten_pro_minute = v; familie({ feld: i }); })),
          zeile("„Bist du noch da?“ alle", zahl(l.check_min ?? 10, 3, 60, (v, i) => { l.check_min = v; familie({ feld: i }); }), el("small", { text: "min" })),
          hilfe("Es zählen nur aktive Minuten. Wer die Frage (drei Pfeile in Folge) verpasst, bekommt die Zeit seit der letzten Frage nicht gutgeschrieben."))),
      karte("Lautstärke",
        zeile("höchstens", zahl(d.einstellungen.ton?.max ?? 100, 20, 100, (v, i) => {
          d.einstellungen.ton = { ...(d.einstellungen.ton || {}), max: v }; einstellung("ton", d.einstellungen.ton, { feld: i }); }), el("small", { text: "%" })),
        hilfe("Am Fernseher: GELB, dann ↑ ↓ (Controller: Back + ↑ ↓). Die TV-Lautstärketasten regeln nur den Fernseher selbst.")),
    ];
  }

  /* ================================================================ Apps */
  function seiteApps() {
    const liste = d.apps.map((app, n) => appKarte(app, n));
    return [hilfe("Kacheln der Startseite. Antippen zum Bearbeiten – Änderungen werden sofort gespeichert."), ...liste, neueApp(), karteYoutube()];
  }

  function appKarte(app) {
    const limitText = () => {
      const l = app.limit_min;
      if (!l) return "";
      if (typeof l === "number") return ` · höchstens ${l} min`;
      return ` · höchstens ${l.schultag ?? "–"}/${l.frei ?? "–"} min`;
    };
    const erlaubtText = () => (app.sperr_erlaubt === "alle" ? " · auch in Sperrzeiten" :
      (app.sperr_erlaubt || []).length ? ` · erlaubt in: ${app.sperr_erlaubt.join(", ")}` : "");
    const zusammenfassung = () => `${TYP_NAME[app.typ] || app.typ} · ${zeitart(app) === "zaehlt" ? "Timer" : "frei"}` + limitText() + erlaubtText() +
                                  (app.start || ["konsole", "youtube"].includes(app.typ) ? "" : " · ⚠️ nicht eingerichtet");
    const unter = el("small", { text: zusammenfassung() });
    const geaendert = (opt) => { unter.textContent = zusammenfassung(); apps(opt); };
    const sichtbar = schalter(app.aktiv !== false, (an) => { app.aktiv = an; geaendert({ sofort: true }); });
    const details = el("details", { class: "eh-app" },
      el("summary", {}, el("span", { class: "eh-app-name" }, el("b", { text: app.name }), unter), sichtbar));
    sichtbar.addEventListener("click", (e) => e.stopPropagation());
    if (app.typ !== "konsole") {
      const adresse = eingabe(app.start, (v, i) => { app.start = v.trim(); geaendert({ feld: i }); },
        { type: "url", class: "eh-breit", placeholder: ["hoerbuch", "video"].includes(app.typ) ? "http://…:8080/share/…" : "https://…" });
      details.append(el("div", { class: "eh-feld" }, el("span", { text: ["hoerbuch", "video"].includes(app.typ) ? "Freigabelink des Ordners" : "Adresse" }), adresse));
      if (["hoerbuch", "video"].includes(app.typ)) details.append(hoerbuchHilfe());
    }
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
    const zeigeLimit = () => limitBox.replaceChildren(...(zeitart(app) === "zaehlt" ? [
      zeile("höchstens am Schultag", limitFeld("schultag"), el("small", { text: "min" })),
      zeile("höchstens Wochenende/Ferien", limitFeld("frei"), el("small", { text: "min" }))] : []));
    const erkl = hilfe(ZEIT_ERKLAERT[zeitart(app)]);
    details.append(
      el("div", { class: "eh-feld" }, el("span", { text: "Zeitart" }),
        segment(ZEIT_WAHL, zeitart(app), (w) => {
          app.zeit = w; if (w === "frei") delete app.limit_min;
          erkl.textContent = ZEIT_ERKLAERT[w]; zeigeLimit(); geaendert({ sofort: true }); })),
      erkl, limitBox, sperrWahl(app, () => geaendert({ sofort: true })),
      zeile("Bereich auf der Startseite", auswahl([["", "automatisch"], ["start", "🏠 Start"], ["spiele", "🎮 Spiele"],
        ["lernen", "🎓 Lernen"], ["musik", "🎼 Musik"], ["filme", "🎬 Filme & YouTube"], ["retro", "🕹️ Retro"]], app.bereich || "",
        (v) => { if (v) app.bereich = v; else delete app.bereich; geaendert({ sofort: true }); })));
    zeigeLimit();
    if (app.id === "plex") {
      details.append(el("div", { class: "eh-feld" }, el("span", { text: "Kinderprofil in Plex (Name genau wie in Plex, ohne PIN)" }),
        eingabe(app.plex_profil || "", (v, i) => { if (v.trim()) app.plex_profil = v.trim(); else delete app.plex_profil; geaendert({ feld: i }); },
          { type: "text", maxlength: 40, class: "eh-breit", placeholder: "z. B. Kinder" })),
        hilfe("Erscheint beim Öffnen die Profilauswahl, wählt der Fernseher dieses Profil von selbst."));
    }
    if (app.typ === "web") {
      details.append(el("div", { class: "eh-feld" }, el("span", { text: "Weitere erlaubte Internetseiten" }),
        eingabe((app.domains || []).join(" "), (v, i) => { app.domains = v.split(/[\s,]+/).filter(Boolean); geaendert({ feld: i }); },
          { type: "text", class: "eh-breit", placeholder: "z. B. cdn.beispiel.de" })),
        zeile("Lernangebot (Lernbonus, Lern-Check)", schalter(app.lernen, (an) => { app.lernen = an; geaendert({ sofort: true }); })));
    }
    if (app.typ !== "konsole") {
      details.append(knopf("App löschen", async () => {
        if (!confirm(`„${app.name}“ wirklich löschen?`)) return;
        d.apps = d.apps.filter((a) => a !== app);
        await sende("/api/eltern/apps", { apps: d.apps });
        zeichne();
      }, "gefahr leise", "Gelöscht ✔"));
    }
    return el("section", { class: "eh-karte eng" }, details);
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
    const zeichneListe = () => box.replaceChildren(...y.kategorien.map((k, n) => el("details", { class: "eh-app" },
      el("summary", {}, el("span", { class: "eh-app-name" }, el("b", { text: k.name }), el("small", { text: `${k.eintraege.length} Einträge` }))),
      eingabe(k.name, (v, i) => { const neu = v.trim(); if (neu) { k.name = neu; speichernY({ feld: i }); zeichneAuswahl(); } },
        { type: "text", maxlength: 30, class: "eh-breit fett" }),
      ...k.eintraege.map((e, m) => el("div", { class: "eh-eintrag" },
        e.bild ? el("img", { src: e.bild, alt: "", class: "eh-yt-bild" }) : null,
        el("div", { class: "eh-app-name" }, el("b", { text: e.titel }), el("small", { text: e.art === "playlist" ? "Playlist" : "Video" })),
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
        .map(([v, t]) => [String(v), t]), String(e.sonne || 0), (v) => { e.sonne = +v; speichernW({ sofort: true }); })))));
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
        zeichne_(); speichernW({ sofort: true }); return Promise.resolve(); }, "leise", "") : null);
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

  /* ================================================================ Telegram (4.0) */
  function karteTelegram() {
    const t = d.einstellungen.telegram = Object.assign({ aktiv: false, token: "", chats: [], antworten: [] }, d.einstellungen.telegram || {});
    const speichernT = (opt) => einstellung("telegram", { ...t, antworten: t.antworten.filter((a) => a.trim()),
                                                          chats: t.chats.filter((c) => c.name.trim() && Number.isInteger(c.id)) }, opt);
    const chatBox = el("div", { class: "eh-liste" });
    const zeichneChats = () => chatBox.replaceChildren(...t.chats.map((c, n) => el("div", { class: "eh-eintrag" },
      el("div", { class: "eh-app-name" }, el("b", { text: c.name }), el("small", { text: `Chat ${c.id}` })),
      knopf("×", () => { t.chats.splice(n, 1); zeichneChats(); speichernT({ sofort: true }); return Promise.resolve(); }, "rund", ""))),
      ...(d.telegram_unbekannt || []).filter((u) => !t.chats.some((c) => c.id === u.id)).map((u) => el("div", { class: "eh-eintrag" },
        el("div", { class: "eh-app-name" }, el("b", { text: `Neu: ${u.name}` }), el("small", { text: `„${u.text}“ · Chat ${u.id}` })),
        knopf("Erlauben", async () => { t.chats.push({ id: u.id, name: u.name }); zeichneChats(); speichernT({ sofort: true }); }, "chip", ""))));
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
          el("li", { text: "Ab dann erscheinen eure Nachrichten am Fernseher, und das Kind antwortet in der Kachel „Nachrichten“." }))),
      zeile("Telegram an", schalter(t.aktiv, (an) => { t.aktiv = an; speichernT({ sofort: true }); })),
      el("div", { class: "eh-feld" }, el("span", { text: "Bot-Token (wird danach nicht mehr angezeigt)" }),
        eingabe(t.token, (v, i) => { t.token = v.trim(); speichernT({ feld: i }); }, { type: "password", class: "eh-breit", autocomplete: "off", placeholder: "123456:ABC…" })),
      el("h4", { text: "Erlaubte Chats" }), chatBox,
      knopf("Neu laden (neue Chats anzeigen)", () => laden(), "leise", ""),
      zeile("Eigene Texte erlauben (Tastatur)", schalter(t.eigene_texte !== false, (an) => { t.eigene_texte = an; speichernT({ sofort: true }); })),
      el("h4", { text: "Antworten des Kindes" }), antwortBox,
      t.antworten.length < 12 ? knopf("+ Antwort", () => { t.antworten.push(""); zeichneAntworten(); return Promise.resolve(); }, "leise", "") : null);
  }

  /* ================================================================ Eigene Inhalte (3.5) */
  function karteInhalte() {
    const inh = d.einstellungen.inhalte = d.einstellungen.inhalte || { witze: [], quiz: [] };
    inh.witze = inh.witze || []; inh.quiz = inh.quiz || [];
    const fertigeWitze = () => inh.witze.filter((w) => w.frage.trim() && w.pointe.trim());
    const fertigeQuiz = () => inh.quiz.filter((q) => q.frage.trim() && q.richtig.trim() && q.falsch.every((f) => f.trim()));
    const speichernI = (opt) => einstellung("inhalte", { witze: fertigeWitze(), quiz: fertigeQuiz() }, opt);
    const witzBox = el("div", { class: "eh-liste" }), quizBox = el("div", { class: "eh-liste" });
    const feld = (obj, schluessel, platz, i_ = null) => eingabe(i_ === null ? obj[schluessel] : obj[schluessel][i_], (v, i) => {
      if (i_ === null) obj[schluessel] = v; else obj[schluessel][i_] = v; speichernI({ feld: i }); }, { type: "text", class: "eh-breit", placeholder: platz, maxlength: 120 });
    const zeichneW = () => witzBox.replaceChildren(...inh.witze.map((w, n) => el("div", { class: "eh-eintrag spalte" },
      el("div", { class: "eh-reihe eng" }, feld(w, "frage", "Frage"),
        knopf("×", () => { inh.witze.splice(n, 1); zeichneW(); speichernI({ sofort: true }); return Promise.resolve(); }, "rund", "")),
      feld(w, "pointe", "Pointe"))));
    const zeichneQ = () => quizBox.replaceChildren(...inh.quiz.map((q, n) => el("div", { class: "eh-eintrag spalte" },
      el("div", { class: "eh-reihe eng" }, feld(q, "frage", "Frage"),
        knopf("×", () => { inh.quiz.splice(n, 1); zeichneQ(); speichernI({ sofort: true }); return Promise.resolve(); }, "rund", "")),
      feld(q, "richtig", "✅ richtige Antwort"), feld(q, "falsch", "❌ falsch 1", 0), feld(q, "falsch", "❌ falsch 2", 1), feld(q, "falsch", "❌ falsch 3", 2))));
    zeichneW(); zeichneQ();
    return karte("Eigene Witze und Quizfragen",
      hilfe("Kommen zu den eingebauten dazu: Witze im Spiel „Witz“, Fragen im Lernspiel „Wissens-Quiz“."),
      el("h4", { text: "😄 Witze" }), witzBox,
      knopf("+ Witz", () => { inh.witze.push({ frage: "", pointe: "" }); zeichneW(); return Promise.resolve(); }, "leise", ""),
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
    return [
      karteTelegram(),
      karteGutscheine(),
      karteInhalte(),
      karteStickerEigen(),
      karte(`Internetseiten${blockiert.length ? ` – ${blockiert.length} blockiert` : ""}`,
        hilfe("Was der Fernseher-Browser geladen hat. Fehlen auf einer Seite Bilder oder Videos, steht hier oft ein blockierter Eintrag."),
        blockiert.length > 1 ? knopf(`Alle ${blockiert.length} blockierten erlauben`, () =>
          sende("/api/eltern/domains-erlauben", { hosts: blockiert.map(([h]) => h) }).then(laden), "haupt") : null,
        ...(domains.length ? kurzliste(domains.slice(0, 200).map(([host, x]) => el("div", { class: "eh-eintrag" },
          el("div", { class: "eh-app-name" }, el("b", { text: host }),
            el("small", { text: `${x.anzahl}× geladen${x.blockiert ? `, ${x.blockiert}× blockiert` : ""} · ${x.apps.join(", ")}` })),
          erlaubt.has(host) || !x.blockiert ? el("small", { text: erlaubt.has(host) ? "erlaubt" : "" }) :
            knopf("Erlauben", () => sende("/api/eltern/domains-erlauben", { hosts: [host] }).then(laden), "chip"))), 8)
          : [hilfe("Noch nichts aufgezeichnet.")])),
      karte("Zusätzlich erlaubte Seiten", zusatz,
        el("div", { class: "eh-reihe" }, knopf("Export Pi-hole", exportiere("pihole"), "leise", ""), knopf("Export Fritzbox", exportiere("fritzbox"), "leise", ""))),
      karte("", bilderTitel, bilder),
      karte(`Sticker (${sticker.length} von ${d.sticker.length})`,
        el("div", { class: "eh-sticker", text: sticker.map((s) => s.symbol).join(" ") || "Noch keine." }),
        ...kurzliste(sticker.slice().reverse().map((s) => hilfe(`${s.symbol} ${s.name} – ${s.seit}`)), 5)),
      karte("Gerät",
        el("div", { class: "eh-feld" }, el("span", { text: "Begrüßung mit Namen" }), name),
        el("div", { class: "eh-reihe" },
          el("a", { class: "eh-knopf leise", href: "/anleitung.pdf", target: "_blank", text: "📖 Anleitung" }),
          el("a", { class: "eh-knopf leise", href: "/kinder-anleitung.pdf", target: "_blank", text: "🧒 Kinder-Anleitung" })),
        el("div", { class: "eh-reihe" },
          knopf("Neustart", () => confirm("Fernseher-Pi neu starten?") ? sende("/api/eltern/geraet", { aktion: "neustart" }) : null, "gefahr leise"),
          knopf("Ausschalten", () => confirm("Fernseher-Pi ausschalten?") ? sende("/api/eltern/geraet", { aktion: "aus" }) : null, "gefahr leise"),
          knopf("Abmelden", () => sende("/api/eltern/abmelden").then(() => { setzeElternToken(""); anmelden(); }), "leise", "")),
        hilfe(`Version ${d.version || ""} · Die PIN wird am Fernseher festgelegt und geändert (BLAU).`)),
      karteScraper(),
      karteBluetooth(),
      karteSicherung(),
    ];
  }

  anmelden();
}
