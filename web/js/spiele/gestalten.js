/* FernsehFranzi 4.0 - Startseite selbst gestalten: Lieblinge (⭐ kommen ganz vorne in „Start“) und Hintergrund.
 * ↑ ↓ wählen · OK ⭐ an/aus · ← → Hintergrund (in der obersten Zeile) · STOP fertig */
import { el } from "../gemeinsam.js";
import { kopf, ton } from "./kern.js";

export const THEMEN = [["weltall", "🌌 Weltall"], ["ozean", "🌊 Ozean"], ["wald", "🌲 Wald"], ["sonne", "🌅 Sonnenuntergang"],
                       ["bonbon", "🍬 Bonbon"], ["nacht", "🌙 Nacht"]];

export default {
  symbol: "🎨",
  oeffne(box, api) {
    const { inhalt } = kopf(box, "🎨 Meine Startseite", "↑ ↓ wählen · OK ⭐ an/aus · ← → Hintergrund · STOP fertig");
    const z = { apps: [], st: { lieblinge: [], thema: "weltall" }, wahl: 0, oben: 0 };
    const speichern = () => api.sende("/api/startseite", z.st).then(() => document.body.dataset.thema = z.st.thema)
      .catch((f) => api.hinweis(f.message));
    function zeige() {
      const zeilen = [el("div", { class: "gestalten-zeile thema" + (z.wahl === 0 ? " gewaehlt" : "") },
        el("span", { text: "Hintergrund" }), el("b", { text: "◀ " + THEMEN.find(([t]) => t === z.st.thema)[1] + " ▶" }))];
      z.apps.forEach((a, i) => {
        const fav = z.st.lieblinge.includes(a.id);
        zeilen.push(el("div", { class: "gestalten-zeile" + (z.wahl === i + 1 ? " gewaehlt" : "") + (fav ? " fav" : "") },
          el("span", { text: a.name }), el("b", { text: fav ? "⭐" : "○" })));
      });
      const sichtbar = 8;
      if (z.wahl < z.oben) z.oben = z.wahl;
      if (z.wahl >= z.oben + sichtbar) z.oben = z.wahl - sichtbar + 1;
      inhalt.replaceChildren(el("div", { class: "gestalten" },
        el("p", { class: "leise", text: "Deine ⭐ Lieblinge stehen ganz vorne bei „Start“ (höchstens 12)." }),
        ...zeilen.slice(z.oben, z.oben + sichtbar)));
    }
    Promise.all([api.hole("/api/apps"), api.hole("/api/startseite")]).then(([a, st]) => {
      z.apps = a.apps.filter((x) => !["spiel-gestalten"].includes(x.id));
      z.st = { lieblinge: st.lieblinge || [], thema: st.thema || "weltall" };
      zeige();
    }).catch((f) => inhalt.replaceChildren(el("div", { class: "meldung-fehler", text: f.message })));
    return {
      taste(t) {
        const n = z.apps.length + 1;
        if (t === "ArrowUp") { z.wahl = Math.max(0, z.wahl - 1); zeige(); ton("bewegen"); return true; }
        if (t === "ArrowDown") { z.wahl = Math.min(n - 1, z.wahl + 1); zeige(); ton("bewegen"); return true; }
        if (z.wahl === 0 && (t === "ArrowLeft" || t === "ArrowRight")) {
          const i = THEMEN.findIndex(([x]) => x === z.st.thema);
          z.st.thema = THEMEN[(i + (t === "ArrowLeft" ? -1 : 1) + THEMEN.length) % THEMEN.length][0];
          document.body.dataset.thema = z.st.thema;
          zeige(); speichern(); ton("ok");
          return true;
        }
        if ((t === "Enter" || t === " ") && z.wahl > 0) {
          const id = z.apps[z.wahl - 1].id;
          if (z.st.lieblinge.includes(id)) z.st.lieblinge = z.st.lieblinge.filter((x) => x !== id);
          else if (z.st.lieblinge.length < 12) z.st.lieblinge = [...z.st.lieblinge, id];
          else { api.hinweis("Höchstens 12 Lieblinge."); return true; }
          zeige(); speichern(); ton("ok");
          return true;
        }
        return t !== "Escape" && t !== "Backspace";
      },
      schliesse() {},
    };
  },
};
