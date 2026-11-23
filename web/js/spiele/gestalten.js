/* FernsehFranzi 4.0 - Startseite selbst gestalten: Lieblinge (⭐ kommen ganz vorne in „Start“) und Design.
 * 5.0: Design statt Hintergrund - dunkle und helle Farbwelten; welche es gibt, legen die Eltern fest (Abend-Automatik).
 * 5.0: Ansicht - die Aufteilung der Startseite (Konsole, Seitenleiste, Karussell), unabhängig von den Farben.
 * ↑ ↓ wählen · OK ⭐ an/aus · ← → Design bzw. Ansicht (in den obersten Zeilen) · STOP fertig */
import { el } from "../gemeinsam.js";
import { kopf, ton } from "./kern.js";

/* Vorgabe, falls der Server (noch) keine Liste schickt */
export const THEMEN = [["weltall", "🌌 Weltall"], ["ozean", "🌊 Ozean"], ["wald", "🌲 Wald"], ["sonne", "🌅 Sonnenuntergang"],
                       ["bonbon", "🍬 Bonbon"], ["nacht", "🌙 Nacht"]];

/* 5.0: Design auf der Startseite zeigen (data-thema + Klasse „hell“) */
export function designZeigen(thema, hell, ansicht) {
  document.body.dataset.thema = thema || "weltall";
  document.body.classList.toggle("hell", Boolean(hell));
  if (ansicht) document.body.dataset.ansicht = ansicht;
}
const ANSICHTEN = [{ id: "konsole", name: "🎮 Konsole" }];

export default {
  symbol: "🎨",
  oeffne(box, api) {
    const { inhalt } = kopf(box, "🎨 Meine Startseite", "↑ ↓ wählen · OK ⭐ an/aus · ← → Design oder Ansicht · STOP fertig");
    const z = { apps: [], st: { lieblinge: [], thema: "weltall", ansicht: "konsole" }, wahl: 0, oben: 0,
                designs: THEMEN.map(([id, name]) => ({ id, name, hell: false })), ansichten: ANSICHTEN, abend: null };
    const OBEN = 2;            /* Zeilen vor den Lieblingen: Design, Ansicht */
    const speichern = () => api.sende("/api/startseite", { lieblinge: z.st.lieblinge, thema: z.st.thema, ansicht: z.st.ansicht })
      .catch((f) => api.hinweis(f.message));
    const design = () => z.designs.find((d) => d.id === z.st.thema) || z.designs[0];
    const ansicht = () => z.ansichten.find((d) => d.id === z.st.ansicht) || z.ansichten[0];
    function zeige() {
      const zeilen = [el("div", { class: "gestalten-zeile thema" + (z.wahl === 0 ? " gewaehlt" : "") },
                        el("span", { text: "Farben" }), el("b", { text: "◀ " + design().name + " ▶" })),
                      el("div", { class: "gestalten-zeile thema" + (z.wahl === 1 ? " gewaehlt" : "") },
                        el("span", { text: "Ansicht" }), el("b", { text: "◀ " + ansicht().name + " ▶" }))];
      z.apps.forEach((a, i) => {
        const fav = z.st.lieblinge.includes(a.id);
        zeilen.push(el("div", { class: "gestalten-zeile" + (z.wahl === i + OBEN ? " gewaehlt" : "") + (fav ? " fav" : "") },
          el("span", { text: a.name }), el("b", { text: fav ? "⭐" : "○" })));
      });
      const sichtbar = 8;
      if (z.wahl < z.oben) z.oben = z.wahl;
      if (z.wahl >= z.oben + sichtbar) z.oben = z.wahl - sichtbar + 1;
      inhalt.replaceChildren(el("div", { class: "gestalten" },
        el("p", { class: "leise", text: "Deine ⭐ Lieblinge stehen ganz vorne bei „Start“ (höchstens 12)." +
          (z.abend ? ` Ab ${z.abend} Uhr wird die Startseite von selbst dunkel.` : "") }),
        ...zeilen.slice(z.oben, z.oben + sichtbar)));
    }
    Promise.all([api.hole("/api/apps"), api.hole("/api/startseite")]).then(([a, st]) => {
      z.apps = a.apps.filter((x) => !["spiel-gestalten"].includes(x.id));
      z.st = { lieblinge: st.lieblinge || [], thema: st.thema || "weltall", ansicht: st.design?.ansicht || st.ansicht || "konsole" };
      if (st.design?.designs?.length) z.designs = st.design.designs;
      if (st.design?.ansichten?.length) z.ansichten = st.design.ansichten;
      z.abend = st.design?.abend_ab || null;
      if (!z.designs.some((d) => d.id === z.st.thema)) z.st.thema = z.designs[0].id;
      zeige();
    }).catch((f) => inhalt.replaceChildren(el("div", { class: "meldung-fehler", text: f.message })));
    return {
      taste(t) {
        const n = z.apps.length + OBEN;
        if (t === "ArrowUp") { z.wahl = Math.max(0, z.wahl - 1); zeige(); ton("bewegen"); return true; }
        if (t === "ArrowDown") { z.wahl = Math.min(n - 1, z.wahl + 1); zeige(); ton("bewegen"); return true; }
        if (z.wahl === 0 && (t === "ArrowLeft" || t === "ArrowRight")) {
          const i = z.designs.findIndex((d) => d.id === z.st.thema);
          z.st.thema = z.designs[(i + (t === "ArrowLeft" ? -1 : 1) + z.designs.length) % z.designs.length].id;
          designZeigen(z.st.thema, design().hell);
          zeige(); speichern(); ton("ok");
          return true;
        }
        if (z.wahl === 1 && (t === "ArrowLeft" || t === "ArrowRight")) {
          const i = z.ansichten.findIndex((d) => d.id === z.st.ansicht);
          z.st.ansicht = z.ansichten[(i + (t === "ArrowLeft" ? -1 : 1) + z.ansichten.length) % z.ansichten.length].id;
          designZeigen(z.st.thema, design().hell, z.st.ansicht);
          zeige(); speichern(); ton("ok");
          return true;
        }
        if ((t === "Enter" || t === " ") && z.wahl >= OBEN) {
          const id = z.apps[z.wahl - OBEN].id;
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
