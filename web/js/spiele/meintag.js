/* FernsehFranzi 6.2 - Mein Tag: die Listen der Eltern (Morgen, Abend …) am Fernseher abhaken.
 *
 * ← → andere Liste · ↑ ↓ Schritt wählen · OK abhaken (oder Timer starten) · STOP zurück
 * Schritte mit Timer (z. B. Zähne putzen, 2 Minuten): eine Zeit-Scheibe läuft ab, ein kleines Lied spielt, Franzi macht mit.
 * 6.8.9: Wer früher fertig ist, drückt OK - der Schritt ist abgehakt, der nächste kommt (STOP bricht ohne Haken ab).
 * Oben zeigt eine kleine Zeit-Scheibe, wie lange noch bis „fertig um“ ist. Freundlich, nie beschämend.
 * Das Kind kann nur abhaken - die Listen legen die Eltern auf der Eltern-Seite an.
 */
import { el, bild, franzi, setzeFranzi } from "../gemeinsam.js";
import { kopf, ton, ereignis, konfetti } from "./kern.js";
import { reiter, hinweisZeile } from "./seite.js";
import { pegel } from "./stimme.js";

const SVG = "http://www.w3.org/2000/svg";

/** Zeit-Scheibe: Kreis, der mit der Zeit kleiner wird (anteil 1 = voll, 0 = leer) */
export function scheibe(anteil, text, klasse = "") {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("class", "mt-scheibe " + klasse);
  const grund = document.createElementNS(SVG, "circle");
  for (const [k, v] of [["cx", 50], ["cy", 50], ["r", 46], ["class", "mt-scheibe-grund"]]) grund.setAttribute(k, v);
  const rest = document.createElementNS(SVG, "circle");
  for (const [k, v] of [["cx", 50], ["cy", 50], ["r", 23], ["class", "mt-scheibe-rest"], ["pathLength", 100],
                        ["transform", "rotate(-90 50 50)"]]) rest.setAttribute(k, v);
  const wert = Math.max(0, Math.min(1, anteil));
  rest.setAttribute("stroke-dasharray", `${(wert * 100).toFixed(2)} 100`);
  svg.append(grund, rest);
  return el("div", { class: "mt-scheibe-box" }, svg, text ? el("div", { class: "mt-scheibe-text", text }) : null);
}

const minuten = (s) => (s >= 60 ? `${Math.ceil(s / 60)} ${Math.ceil(s / 60) === 1 ? "Minute" : "Minuten"}` : `${s} Sekunden`);
const uhrText = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

export default {
  symbol: "📋",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "📋 Mein Tag", "← → Liste · ↑ ↓ wählen · OK abhaken · STOP zurück");
    const z = { daten: null, liste: 0, wahl: 0, timer: null, geladen: 0 };

    /* 6.3: Reiter = Listen der Eltern, dazu „🎒 Ranzen“ (Packliste für den nächsten Schultag) und „⭐ Aufgaben“ */
    const seiten = () => {
      const d = z.daten;
      if (!d?.aktiv) return [];
      return [...d.routinen.map((r) => ({ art: "routine", r })), d.ranzen ? { art: "ranzen" } : null,
              d.aufgaben?.length ? { art: "aufgaben" } : null, d.lesen ? { art: "lesen" } : null,
              d.sachen ? { art: "franzi" } : null].filter(Boolean);
    };
    const seite = () => seiten()[z.liste];
    const routine = () => (seite()?.art === "routine" ? seite().r : null);
    const SACH_SYMBOL = { hut: "🎩", brille: "🕶️", extra: "🎀", farbe: "🎨" };
    const AUFGABE_STAND = { wartet: "⏳ Mama oder Papa schauen nach", ja: "⭐ bestätigt", nein: "Fast – nochmal schauen?" };
    function eintraege() {
      const s = seite(), d = z.daten;
      if (!s) return [];
      if (s.art === "routine") return s.r.schritte;
      if (s.art === "ranzen") return d.ranzen.sachen.map((x) => ({ text: x.text, symbol: "", erledigt: x.erledigt, chip: x.fach }));
      if (s.art === "lesen") return [{ text: d.lesen.stempel_heute ? "Weiter vorlesen" : `Vorlesen starten (${d.lesen.ziel_min} Minuten)`,
                                         symbol: "🎤", lesen: true, chip: `heute ${Math.floor(d.lesen.heute_min)} min` }];
      if (s.art === "franzi") {
        /* 6.9.37: Ist Franzi als Haustier an, zeigt die Liste nur, was die Level bringen (angezogen wird bei Franzi) */
        const sachen = d.sachen.map((x) => ({ text: x.name, symbol: x.symbol || SACH_SYMBOL[x.art], erledigt: x.an || (x.belohnung && x.frei),
                                               gesperrt: !x.frei, sache: x, belohnung: x.belohnung,
                                               chip: !x.frei ? `🔒 ab Level ${x.level}` + (x.tage > (d.sammeltage || 0) ? ` · ${x.tage} Sternentage` : "")
                                                 : x.belohnung ? "✔ bei Franzi" : x.an ? "trägt Franzi" : "OK = anziehen" }));
        return d.tausch ? [{ text: `1 Stern gegen ${d.tausch.minuten} Minuten Spielzeit`, symbol: "⭐", tausch: true,
                             chip: d.tausch.rest_min ? `heute noch ${d.tausch.rest_min} min` : "heute genug" }, ...sachen] : sachen;
      }
      return d.aufgaben.map((a) => ({ text: a.text, symbol: a.symbol, erledigt: a.stand === "ja", wartet: a.stand === "wartet",
                                      chip: AUFGABE_STAND[a.stand] || "⭐".repeat(a.sterne || 1) }));
    }

    async function lade(ersteMal = false) {
      try {
        z.daten = await api.hole("/api/meintag");
        z.geladen = Date.now();
      } catch (fehler) { inhalt.replaceChildren(hinweisZeile(fehler.message, "⚠️")); return; }
      if (ersteMal) {
        const i = (z.daten.routinen || []).findIndex((r) => r.nr === z.daten.aktuell);
        z.liste = Math.max(0, i);
        if (z.daten.woche) z.liste = seiten().findIndex((x) => x.art === "franzi");      /* Sonntag: Wochenrückblick zuerst */
        z.wahl = Math.max(0, eintraege().findIndex((s) => !s.erledigt));
      }
      if (!z.timer) zeige();
    }

    function zeige() {
      const d = z.daten;
      const alle = seiten();
      if (!alle.length) {
        punkte.textContent = "";
        inhalt.replaceChildren(hinweisZeile("Heute gibt es keine Liste. Einen schönen Tag!", "🌈"));
        return;
      }
      z.liste = Math.min(z.liste, alle.length - 1);
      const liste = eintraege();
      z.wahl = Math.max(0, Math.min(z.wahl, liste.length - 1));
      const namen = alle.map((x) => x.art === "routine" ? `${x.r.symbol || "📋"} ${x.r.name}${x.r.geschafft ? " ✔" : ""}`
        : x.art === "ranzen" ? `🎒 Ranzen${d.ranzen.erledigt === d.ranzen.sachen.length ? " ✔" : ""}`
        : x.art === "franzi" ? `🌟 Franzi · Level ${d.level}` : x.art === "lesen" ? `📖 Lesen${d.lesen.stempel_heute ? " ✔" : ""}` : "⭐ Aufgaben");
      const r = routine();
      if (!r) return zeigeAndere(alle, namen, liste);
      const vergangen = (Date.now() - z.geladen) / 1000;
      const rest = Math.max(0, Math.round(r.rest_s - vergangen));
      let oben;
      if (r.geschafft) oben = el("div", { class: "mt-oben geschafft" }, franzi("verliebt", "mt-franzi"),      /* 6.9.62: Herzaugen */
        el("div", { class: "mt-oben-text", text: r.puenktlich ? `Super, pünktlich geschafft! (${r.geschafft} Uhr) ⭐⭐ Bonus-Stern!`
                                                                : `Super, alles geschafft! (${r.geschafft} Uhr) ⭐` }));
      else if (r.laeuft) oben = el("div", { class: "mt-oben" }, scheibe(rest / Math.max(1, r.dauer_s), "", "klein"),
        el("div", { class: "mt-oben-text", text: rest > 0 ? `Noch ${minuten(rest)} bis ${r.fertig} Uhr – bis dahin gibt's einen Bonus-Stern!`
                                                       : `Gleich ${r.fertig} Uhr` }));
      else if (!r.vorbei) oben = el("div", { class: "mt-oben" }, el("div", { class: "mt-oben-text", text: `Ab ${r.zeit} Uhr · fertig um ${r.fertig} Uhr` }));
      else oben = el("div", { class: "mt-oben" }, el("div", { class: "mt-oben-text",
        text: r.erledigt ? `Fast geschafft – ${r.erledigt} von ${r.anzahl}!` : "Diese Liste kannst du trotzdem noch abhaken." }));
      punkte.textContent = `${r.erledigt} / ${r.anzahl} ✔`;
      const schritte = el("div", { class: "mt-schritte" }, ...r.schritte.map((s, i) =>
        el("div", { class: "mt-schritt" + (i === z.wahl ? " gewaehlt" : "") + (s.erledigt ? " erledigt" : "") },
          el("div", { class: "mt-haken", text: s.erledigt ? "✔" : "" }),
          s.symbol ? el("div", { class: "mt-symbol" }, bild(s.symbol)) : null,
          el("div", { class: "mt-text", text: s.text }),
          s.timer ? el("div", { class: "mt-timer-chip", text: `⏱ ${uhrText(s.timer)}` }) : null)));
      const fortschritt = el("div", { class: "mt-balken" }, el("span", { style: `width:${Math.round(100 * r.erledigt / r.anzahl)}%` }));
      inhalt.replaceChildren(el("div", { class: "mt-seite" },
        alle.length > 1 ? reiter(namen, z.liste) : null,
        oben, fortschritt, schritte));
      requestAnimationFrame(() => schritte.querySelector(".gewaehlt")?.scrollIntoView({ block: "nearest" }));
    }

    function zeileVon(s, i) {
      return el("div", { class: "mt-schritt" + (i === z.wahl ? " gewaehlt" : "") + (s.erledigt ? " erledigt" : "") + (s.wartet ? " wartet" : "") + (s.sache ? " sache" : "") },
        el("div", { class: "mt-haken", text: s.erledigt ? "✔" : s.wartet ? "⏳" : "" }),
        s.symbol ? el("div", { class: "mt-symbol" }, bild(s.symbol)) : null,
        el("div", { class: "mt-text", text: s.text }),
        s.chip ? el("div", { class: "mt-timer-chip", text: s.chip }) : null);
    }

    /* 6.3: Ranzen und Aufgaben */
    function zeigeAndere(alle, namen, liste) {
      const d = z.daten, art = seite().art;
      let oben;
      if (art === "ranzen") {
        const fertig = d.ranzen.erledigt === d.ranzen.sachen.length;
        punkte.textContent = `${d.ranzen.erledigt} / ${d.ranzen.sachen.length} ✔`;
        oben = el("div", { class: "mt-oben" + (fertig ? " geschafft" : "") }, fertig ? franzi("verliebt", "mt-franzi") : null,
          el("div", { class: "mt-oben-text", text: fertig ? "Ranzen fertig gepackt – super!"
            : `Für ${d.ranzen.name || "morgen"}: ${d.ranzen.faecher.join(", ")}` }));
      } else if (art === "lesen") {
        punkte.textContent = `📖 ${d.lesen.stempel} Stempel`;
        oben = el("div", { class: "mt-lesepass" },
          el("div", { class: "mt-oben-text", text: d.lesen.stempel_heute ? "Heute hast du deinen Stempel – super gelesen!"
            : `Lies ${d.lesen.ziel_min} Minuten laut vor, dann bekommst du einen Stempel und einen Stern.` }),
          el("div", { class: "mt-stempel-reihe" }, ...d.lesen.tage.map((t) => el("div", { class: "mt-stempel" + (t.stempel ? " an" : "") },
            el("div", { class: "mt-stempel-kreis", text: t.stempel ? "📖" : "" }), el("small", { text: t.kurz })))),
          el("div", { class: "mt-timer-chip", text: "Das Mikro hört nur, ob du vorliest – es nimmt nichts auf." }));
      } else if (art === "franzi") {
        punkte.textContent = `⭐ ${d.sterne}`;
        const im = d.verdient - (d.level - 1) * 10;
        oben = el("div", { class: "mt-franzi-oben" }, franzi("froh", "mt-franzi-gross"),
          el("div", { class: "mt-franzi-info" },
            d.woche ? el("div", { class: "mt-woche", text: "🎉 Diese Woche geschafft: " + [d.woche.listen ? `${d.woche.listen} ${d.woche.listen === 1 ? "Liste" : "Listen"}` : "",
                                                       `⭐ ${d.woche.sterne} ${d.woche.sterne === 1 ? "Stern" : "Sterne"}`].filter(Boolean).join(" und ") + "!" }) : null,
            el("div", { class: "mt-oben-text", text: `Level ${d.level} · noch ${d.naechstes_bei - d.verdient} ⭐ bis Level ${d.level + 1}` }),
            el("div", { class: "mt-balken" }, el("span", { style: `width:${im * 10}%` }))));
      } else {
        punkte.textContent = `⭐ ${d.sterne}`;
        oben = el("div", { class: "mt-oben" }, el("div", { class: "mt-oben-text",
          text: `OK = „Hab ich gemacht!“ · Mama oder Papa bestätigen, dann gibt es Sterne. Heute: ⭐ ${d.sterne_heute || 0}` }));
      }
      const zeilen = el("div", { class: "mt-schritte" }, ...liste.map(zeileVon));
      inhalt.replaceChildren(el("div", { class: "mt-seite" }, alle.length > 1 ? reiter(namen, z.liste) : null, oben, zeilen));
      requestAnimationFrame(() => zeilen.querySelector(".gewaehlt")?.scrollIntoView({ block: "nearest" }));
    }

    async function andereOk() {
      const art = seite().art, x = eintraege()[z.wahl];
      if (!x) return;
      try {
        if (art === "ranzen") {
          const vorher = z.daten.ranzen.erledigt === z.daten.ranzen.sachen.length;
          z.daten = await api.sende("/api/meintag/ranzen", { nr: z.wahl, an: !x.erledigt });
          const fertig = z.daten.ranzen && z.daten.ranzen.erledigt === z.daten.ranzen.sachen.length;
          if (fertig && !vorher) { ereignis("geschafft", "sieg"); konfetti(box); } else ton(x.erledigt ? "bewegen" : "ok");
          if (!x.erledigt) { const w = eintraege().findIndex((y, i) => i > z.wahl && !y.erledigt); if (w >= 0) z.wahl = w; }
        } else if (art === "lesen") {
          leseStart();
          return;
        } else if (art === "franzi") {
          if (x.tausch) {
            z.daten = await api.sende("/api/meintag/tauschen", {});
            ton("sieg");
          } else if (x.gesperrt) {
            api.hinweis(`Noch ${z.daten.naechstes_bei - z.daten.verdient} Sterne bis Level ${z.daten.level + 1} – du schaffst das!`);
            return;
          } else if (x.belohnung) {
            api.hinweis(`${x.text} wartet bei Franzi – schau in ihrem Schrank vorbei!`);
            return;
          } else {
            z.daten = await api.sende("/api/meintag/franzi", { art: x.sache.art, id: x.erledigt ? "" : x.sache.id });
            setzeFranzi(z.daten.franzi);
            document.getElementById("franzi-kopf")?.replaceChildren(franzi("froh"));
            ton("ok");
          }
        } else {
          if (x.erledigt) { api.hinweis("Schon bestätigt – toll gemacht! ⭐"); return; }
          if (x.wartet) { api.hinweis("Mama oder Papa schauen gleich nach."); return; }
          z.daten = await api.sende("/api/meintag/aufgabe", { nr: z.daten.aufgaben[z.wahl].nr });
          api.hinweis("Prima! Mama oder Papa schauen gleich nach.");
          ton("ok");
        }
        z.geladen = Date.now();
      } catch (fehler) { api.hinweis(fehler.message, 5000); ton("fehler"); return; }
      zeige();
    }

    async function haken(an) {
      const r = routine(), s = r?.schritte[z.wahl];
      if (!s) return;
      const vorher = r.geschafft;
      try {
        z.daten = await api.sende("/api/meintag/abhaken", { nr: r.nr, schritt: z.wahl, an });
        z.geladen = Date.now();
      } catch (fehler) { api.hinweis(fehler.message, 5000); ton("fehler"); return; }
      const neu = routine();
      if (an && neu?.geschafft && !vorher) { ereignis("geschafft", "sieg"); konfetti(box); }
      else ton(an ? "ok" : "bewegen");
      if (an && neu) {                       /* zum nächsten offenen Schritt */
        const weiter = neu.schritte.findIndex((x, i) => i > z.wahl && !x.erledigt);
        if (weiter >= 0) z.wahl = weiter;
      }
      zeige();
    }

    /* ------------------------------------------------ Timer (z. B. Zähne putzen) */
    /* 6.8.10: Ton im Timer am Fernseher aus- und einschalten (↓), merkt sich der Fernseher */
    const tonAus = () => { try { return localStorage.getItem("ff-meintag-ton") === "aus"; } catch (_) { return false; } };
    const setzeTonAus = (aus) => { try { localStorage.setItem("ff-meintag-ton", aus ? "aus" : "an"); } catch (_) { /* egal */ } };
    function timerStart(s) {
      const musik = routine()?.musik || "";                 /* "" = Zahnputz-Lied, "stumm" = ohne, sonst ein Klang */
      const ende = Date.now() + s.timer * 1000;
      /* einmal aufbauen, danach nur Scheibe und Zahl ändern (Pi 3: nichts jede Sekunde neu zeichnen) */
      const sch = scheibe(1, uhrText(s.timer), "gross");
      const rest_ = sch.querySelector(".mt-scheibe-rest"), zahl = sch.querySelector(".mt-scheibe-text");
      const satz = el("div", { class: "mt-timer-text", text: "Los geht's!" });
      const anzeige = el("div", { class: "mt-timer" },
        el("div", { class: "mt-timer-titel" }, s.symbol ? bild(s.symbol) : null, el("span", { text: s.text })),
        el("div", { class: "mt-timer-mitte" }, sch, el("div", { class: "mt-franzi-platz" }, franzi("froh", "mt-franzi-gross"),
          /* 6.9.34: beim Zähneputzen hält Franzi eine Zahnbürste (schrubbt nur in der Stufe „hoch“) */
          /zahn|zähne/i.test(s.text) ? el("div", { class: "mt-buerste" }, bild("🪥")) : null)), satz);
      let takt = 0;
      let audio = null, lied = 0;
      const tonAn = () => {
        if (tonAus() || musik === "stumm") return;
        if (!musik) { lied = setInterval(() => ton("lied" + ((takt++ % 4) + 1), { laut: 0.18 }), 1100); return; }
        audio = new Audio("/api/klang?id=" + encodeURIComponent(musik));   /* Archiv oder eigener Klang der Eltern */
        audio.loop = true; audio.volume = 0.7;
        audio.play().catch(() => { audio = null; });
      };
      const tonWeg = () => { clearInterval(lied); lied = 0; if (audio) { audio.pause(); audio = null; } };
      const tonZeile = el("div", { class: "mt-timer-ton" });
      const zeigeTon = () => { tonZeile.textContent = musik === "stumm" ? "" : tonAus() ? "🔇 Ton aus · ↓ an" : "🔊 Ton an · ↓ aus"; };
      zeigeTon();
      tonAn();
      const schritt = () => {
        const rest = Math.max(0, Math.round((ende - Date.now()) / 1000));
        rest_.setAttribute("stroke-dasharray", `${(100 * rest / s.timer).toFixed(2)} 100`);
        zahl.textContent = uhrText(rest);
        satz.textContent = rest === 0 ? "Fertig – super gemacht!" : rest <= s.timer / 2 ? "Schon die Hälfte – weiter so!" : "Los geht's!";
        if (rest === 0) fertig(true);
      };
      const id = setInterval(schritt, 1000);
      anzeige.append(tonZeile);
      z.timer = { stopp() { clearInterval(id); tonWeg(); },
                  ton() { setzeTonAus(!tonAus()); tonWeg(); tonAn(); zeigeTon(); } };
      hilfe.textContent = "OK = fertig · STOP abbrechen";          /* 6.8.9: früher fertig? OK hakt ab */
      inhalt.replaceChildren(anzeige);
      schritt();
      ton("ok");
      function fertig(geschafft) {
        if (!z.timer) return;
        z.timer.stopp();
        z.timer = null;
        hilfe.textContent = "← → Liste · ↑ ↓ wählen · OK abhaken · STOP zurück";
        if (geschafft) haken(true); else zeige();
      }
      z.timer.abbrechen = () => fertig(false);
      z.timer.frueh = () => fertig(true);
    }

    /* ------------------------------------------------ 6.5: Vorlesen - nur der Pegel zählt, nichts wird aufgenommen */
    async function leseStart() {
      let strom;
      try {
        strom = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
      } catch (_) {
        api.hinweis("Kein Mikrofon gefunden – bitte Mama oder Papa fragen.", 5000); ton("fehler"); return;
      }
      const ziel = z.daten.lesen.ziel_min * 60, schon = z.daten.lesen.heute_min * 60;
      const ac = new AudioContext(), analyse = ac.createAnalyser();
      analyse.fftSize = 2048;
      ac.createMediaStreamSource(strom).connect(analyse);
      const puffer = new Float32Array(analyse.fftSize);
      const sch = scheibe(Math.max(0, 1 - schon / ziel), uhrText(Math.max(0, Math.ceil(ziel - schon))) || "✔", "gross");
      const rest_ = sch.querySelector(".mt-scheibe-rest"), zahl = sch.querySelector(".mt-scheibe-text");
      const satz = el("div", { class: "mt-timer-text", text: "Lies laut vor – Franzi hört zu!" });
      if (ac.state === "suspended") ac.resume().catch(() => {});
      inhalt.replaceChildren(el("div", { class: "mt-timer" },
        el("div", { class: "mt-timer-titel" }, bild("📖"), el("span", { text: "Vorlese-Zeit" })),
        el("div", { class: "mt-timer-mitte" }, sch, franzi("staunen", "mt-franzi-gross")), satz));
      hilfe.textContent = "STOP beenden";
      let gelesen = 0, gesendet = 0, still = 0, zuletzt = performance.now(), gemeldet = false;
      const id = setInterval(() => {
        const jetzt = performance.now(), dt = Math.min(1, (jetzt - zuletzt) / 1000);
        zuletzt = jetzt;
        analyse.getFloatTimeDomainData(puffer);
        const laut = pegel(puffer) > 0.06;
        /* kurze Atempausen zählen mit, längere Stille nicht */
        if (laut) still = 0; else still += dt;
        if (laut || still < 2) gelesen += dt;
        const gesamt = schon + gelesen, rest = Math.max(0, Math.ceil(ziel - gesamt));
        rest_.setAttribute("stroke-dasharray", `${(100 * rest / ziel).toFixed(2)} 100`);
        zahl.textContent = rest ? uhrText(rest) : "✔";
        satz.textContent = rest === 0 ? "Geschafft – toll vorgelesen! Du darfst weiterlesen." : still >= 2 ? "Lies weiter laut vor …" : "Franzi hört zu …";
        if (rest === 0 && !gemeldet && schon < ziel) { gemeldet = true; melden(); }
      }, 250);
      z.timer = { stopp() { clearInterval(id); strom.getTracks().forEach((t) => t.stop()); ac.close(); } };
      async function melden() {
        const sek = Math.round(gelesen - gesendet);
        gesendet += sek;
        try {
          const d = await api.sende("/api/meintag/lesen", { sekunden: sek });
          if (d.neuer_stempel) { ereignis("stern", "sieg"); konfetti(box); }
        } catch (fehler) { api.hinweis(fehler.message, 5000); }
      }
      z.timer.abbrechen = async () => {
        z.timer.stopp(); z.timer = null;
        hilfe.textContent = "← → Liste · ↑ ↓ wählen · OK abhaken · STOP zurück";
        if (gelesen - gesendet >= 10) await melden();
        await lade();
      };
    }

    inhalt.replaceChildren(hinweisZeile("Einen Moment …"));
    lade(true);
    const auffrischen = setInterval(() => lade(), 30 * 1000);     /* Zeit-Scheibe oben und neue Listen */

    return {
      taste(t) {
        if (z.timer) {
          if (t === "Escape" || t === "Backspace") { z.timer.abbrechen(); return true; }
          if (t === "Enter" || t === " ") { z.timer.frueh(); return true; }                 /* 6.8.9: schon fertig */
          if (t === "ArrowDown") { z.timer.ton(); return true; }                            /* 6.8.10: Ton aus/an */
          return true;                                    /* während des Timers keine anderen Tasten */
        }
        const n = seiten().length;
        if (!n) return t !== "Escape" && t !== "Backspace";
        if (t === "ArrowLeft" || t === "ArrowRight") {
          if (n > 1) { z.liste = (z.liste + (t === "ArrowLeft" ? n - 1 : 1)) % n; z.wahl = Math.max(0, eintraege().findIndex((s) => !s.erledigt)); ton("bewegen"); zeige(); }
          return true;
        }
        if (t === "ArrowUp" || t === "ArrowDown") {
          const m = eintraege().length;
          if (m) { z.wahl = (z.wahl + (t === "ArrowUp" ? m - 1 : 1)) % m; ton("bewegen"); zeige(); }
          return true;
        }
        const r = routine();
        if ((t === "Enter" || t === " ") && !r) { andereOk(); return true; }
        if (t === "Enter" || t === " ") {
          const s = r.schritte[z.wahl];
          if (s.timer && !s.erledigt) timerStart(s); else haken(!s.erledigt);
          return true;
        }
        return t !== "Escape" && t !== "Backspace";
      },
      schliesse() { clearInterval(auffrischen); z.timer?.stopp(); z.timer = null; },
    };
  },
};
