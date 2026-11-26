/* FernsehFranzi 5.0 - Wetter: jetzt, die nächsten Stunden, fünf Tage, Trockenfenster („Wann können wir raus?“),
 * Anzieh-Tipp und - wenn es gerade trocken ist und die Eltern es erlauben - ein Spiel für draußen aus den Kinderwelten.
 * Die Daten holt der Server von Open-Meteo (Regeln wie im Familien Dashboard). STOP zurück. */
import { el, bild, franziEcke } from "../gemeinsam.js";
import { kopf } from "./kern.js";
import { hinweisZeile } from "./seite.js";

export default {
  symbol: "🌤️",
  oeffne(box, api) {
    const { inhalt, punkte } = kopf(box, "🌤️ Wetter", "STOP zurück");
    let tipp = null;
    function zeige(w) {
      if (!w.aktiv) { inhalt.replaceChildren(hinweisZeile("Das Wetter ist ausgeschaltet.", "🔒")); return; }
      const d = w.daten;
      punkte.textContent = w.ort ? "📍 " + w.ort + (w.stand ? " · Stand " + w.stand : "") : "";
      if (!d) { inhalt.replaceChildren(hinweisZeile(w.fehler || "Das Wetter wird geholt …", "🌥️")); return; }
      const jetzt = el("div", { class: "wetter-jetzt" },
        el("div", { class: "wetter-gross" }, bild(d.symbol)),
        el("div", {},
          el("div", { class: "wetter-temp", text: `${d.temp}°` }),
          el("div", { class: "wetter-text", text: `${d.text} · fühlt sich an wie ${d.gefuehlt}°` }),
          el("div", { class: "wetter-regen" + (d.regen.nass ? " nass" : ""), text: (d.regen.nass ? "☔ " : "🌂 ") + d.regen.text }),
          el("div", { class: "wetter-anziehen", text: "👕 " + d.anziehen })));
      const stunden = el("div", { class: "wetter-stunden" }, ...d.stunden.map((s) =>
        el("div", { class: "wetter-stunde" + (s.nass ? " nass" : "") },
          el("div", { class: "ws-uhr", text: s.uhr }), el("div", { class: "ws-symbol" }, bild(s.symbol)),
          el("div", { class: "ws-temp", text: `${s.temp}°` }), el("div", { class: "ws-regen", text: s.prozent ? `${s.prozent} %` : "" }))));
      const tage = el("div", { class: "wetter-tage" }, ...d.tage.map((t) =>
        el("div", { class: "wetter-tag" },
          el("div", { class: "wt-name", text: t.name }), el("div", { class: "wt-symbol" }, bild(t.symbol)),
          el("div", { class: "wt-temp", text: `${t.max}° / ${t.min}°` }),
          el("div", { class: "wt-regen", text: t.regen ? `☔ ${t.regen} %` : "☀️ trocken" }))));
      const fenster = d.fenster.length
        ? el("div", { class: "wetter-fenster" }, el("div", { class: "wf-titel", text: "🚲 Wann können wir raus?" }),
          ...d.fenster.map((f) => el("div", { class: "wf-zeile" + (f.jetzt ? " jetzt" : ""),
            text: `${f.jetzt ? "Jetzt" : f.tag + " " + f.von_text} bis ${f.bis_text} trocken${f.sonnig ? " und sonnig ☀️" : ""}` })))
        : el("div", { class: "wetter-fenster" }, el("div", { class: "wf-titel", text: "🚲 Wann können wir raus?" }),
          el("div", { class: "wf-zeile", text: "Heute und morgen leider kein längeres trockenes Fenster bei Tageslicht." }));
      const teile = [jetzt, stunden, el("div", { class: "wetter-unten" }, tage, fenster)];
      /* 6.9.62: Franzi zeigt, wie sich das Wetter anfühlt - und zieht sich passend an */
      const sonnig = /☀/.test(d.symbol || ""), kalt = d.temp <= 3;
      teile.push(franziEcke(d.regen.nass ? "muede" : kalt ? "grummelig" : sonnig ? "jubel" : "froh",
        { text: d.regen.nass ? "Regenjacke nicht vergessen!" : kalt ? "Brrr – Mütze auf!" : sonnig ? "Ab nach draußen!" : "",
          sachen: kalt ? { extra: "schal" } : sonnig ? { brille: "sonne" } : null }));
      if (tipp && d.draussen_gut) teile.push(el("div", { class: "wetter-tipp", text: `🌳 Draußen-Idee: ${tipp.titel} – ${tipp.anriss}` }));
      if (w.fehler) teile.push(el("div", { class: "seite-zeile", text: w.fehler }));
      inhalt.replaceChildren(el("div", { class: "wetter-seite" }, ...teile));
    }
    const laden = () => api.hole("/api/wetter").then(zeige).catch((f) => inhalt.replaceChildren(hinweisZeile(f.message, "⚠️")));
    inhalt.replaceChildren(hinweisZeile("Einen Moment …"));
    api.hole("/api/wetter").then((w) => {
      zeige(w);
      if (w.draussen && w.daten?.draussen_gut) {
        api.hole("/api/kinderwelten/draussen").then((r) => {
          const liste = r.eintraege || [];
          if (!liste.length) return;
          tipp = liste[new Date().getDate() % liste.length];
          zeige(w);
        }).catch(() => { /* ohne Tipp */ });
      }
    }).catch((f) => inhalt.replaceChildren(hinweisZeile(f.message, "⚠️")));
    const timer = setInterval(laden, 5 * 60 * 1000);
    return {
      taste(t) { return t !== "Escape" && t !== "Backspace"; },
      schliesse() { clearInterval(timer); },
    };
  },
};
