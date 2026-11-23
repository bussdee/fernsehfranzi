/* FernsehFranzi 4.0 - Startseite selbst gestalten: Lieblinge (⭐ kommen ganz vorne in „Start“) und Design.
 * 5.0: Design statt Hintergrund - dunkle und helle Farbwelten; welche es gibt, legen die Eltern fest (Abend-Automatik).
 * 6.0: Startseite „Zuhause + Ordner“ - höchstens 6 Lieblinge stehen ganz oben auf „Zuhause“; die Ansichten von 5.0 gibt es
 *      nicht mehr (die Einstellung bleibt gespeichert, wird aber nicht mehr gebraucht).
 * ↑ ↓ wählen · OK ⭐ an/aus · ← → Farbe (oberste Zeile) · STOP fertig */
import { el } from "../gemeinsam.js";
import { kopf, ton } from "./kern.js";

/* Vorgabe, falls der Server (noch) keine Liste schickt */
export const THEMEN = [["blau", "🔵 Blau"], ["gruen", "🟢 Grün"], ["lila", "🟣 Lila"], ["rot", "🔴 Rot"], ["schwarz", "⚫ Schwarz"]];

/* 5.0: Design auf der Startseite zeigen (data-thema + Klasse „hell“) */
export function designZeigen(thema, hell, ansicht) {
  document.body.dataset.thema = thema || "blau";
  document.body.classList.toggle("hell", Boolean(hell));
  if (ansicht) document.body.dataset.ansicht = ansicht;
}
const ANSICHTEN = [{ id: "konsole", name: "🎮 Konsole" }];

export default {
  symbol: "🎨",
  oeffne(box, api) {
    const { inhalt } = kopf(box, "🎨 Meine Startseite", "↑ ↓ wählen · OK ⭐ an/aus · ← → Farbe · STOP fertig");
    const z = { apps: [], st: { lieblinge: [], thema: "blau", ansicht: "konsole" }, wahl: 0, oben: 0,
                designs: THEMEN.map(([id, name]) => ({ id, name, hell: false })), ansichten: ANSICHTEN, abend: null };
    const OBEN = 1;            /* Zeilen vor den Lieblingen: Farbe */
    const LIEBLINGE_MAX = 6;
    const speichern = () => api.sende("/api/startseite", { lieblinge: z.st.lieblinge, thema: z.st.thema, ansicht: z.st.ansicht })
      .catch((f) => api.hinweis(f.message));
    const design = () => z.designs.find((d) => d.id === z.st.thema) || z.designs[0];
    const ansicht = () => z.ansichten.find((d) => d.id === z.st.ansicht) || z.ansichten[0];
    function zeige() {
      const zeilen = [el("div", { class: "gestalten-zeile thema" + (z.wahl === 0 ? " gewaehlt" : "") },
                        el("span", { text: "Farben" }), el("b", { text: "◀ " + design().name + " ▶" }))];
      z.apps.forEach((a, i) => {
        const fav = z.st.lieblinge.includes(a.id);
        zeilen.push(el("div", { class: "gestalten-zeile" + (z.wahl === i + OBEN ? " gewaehlt" : "") + (fav ? " fav" : "") },
          el("span", { text: a.name }), el("b", { text: fav ? "⭐" : "○" })));
      });
      const sichtbar = 8;
      if (z.wahl < z.oben) z.oben = z.wahl;
      if (z.wahl >= z.oben + sichtbar) z.oben = z.wahl - sichtbar + 1;
      /* 6.0: kleine Vorschau in der gewählten Farbe (die Startseite selbst liegt unter dieser Seite) */
      const d = design(), zeigt = sichtbare(d);
      const zeigtD = z.designs.find((x) => x.id === zeigt) || d;
      const abendText = d.hell && z.abend
        ? (z.istAbend ? `Jetzt am Abend zeigt die Startseite ${name(zeigt)} – morgen früh wieder ${d.name.replace(/^\S+\s/, "")}.`
                      : `Ab ${z.abend} Uhr wird daraus ${name(d.abends)}.`) : "";
      const vorschau = el("div", { class: "farb-vorschau" + (zeigtD.hell ? " hell" : ""), "data-thema": zeigt },
        el("div", { class: "fv-titel", text: "Startseite" }),
        el("div", { class: "fv-kacheln" }, ...["#1d7a5e", "#8a3b8a", "#a8791c", "#2a6b9e", "#b06520", "#2f5fa8"].map((f, i) =>
          el("div", { class: "fv-kachel" + (i === 0 ? " an" : ""),
                      style: `background: linear-gradient(130deg, ${zeigtD.hell ? `color-mix(in srgb, ${f} 45%, #fff)` : "var(--kachel-anfang)"}, ${f})` }))),
        abendText ? el("div", { class: "fv-text", text: abendText }) : null);
      inhalt.replaceChildren(el("div", { class: "gestalten-oben" }, el("div", { class: "gestalten" },
        el("p", { class: "leise", text: `Deine ⭐ Lieblinge stehen ganz oben auf „Zuhause“ (höchstens ${LIEBLINGE_MAX}, ${z.st.lieblinge.length} ausgesucht).` }),
        ...zeilen.slice(z.oben, z.oben + sichtbar)), vorschau));
    }
    const name = (id) => (z.designs.find((x) => x.id === id)?.name || id).replace(/^\S+\s/, "");
    /* abends wird eine helle Farbe zu ihrer dunklen Schwester */
    const sichtbare = (d) => (z.istAbend && d.hell ? d.abends : d.id);
    Promise.all([api.hole("/api/apps"), api.hole("/api/startseite")]).then(([a, st]) => {
      z.apps = a.apps.filter((x) => !["spiel-gestalten"].includes(x.id));
      z.st = { lieblinge: (st.lieblinge || []).slice(0, LIEBLINGE_MAX), thema: st.design?.gewaehlt || st.thema || "blau", ansicht: st.design?.ansicht || st.ansicht || "konsole" };
      if (st.design?.designs?.length) z.designs = st.design.designs;
      if (st.design?.ansichten?.length) z.ansichten = st.design.ansichten;
      z.abend = st.design?.abend_ab || null;
      z.istAbend = Boolean(st.design?.abend);
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
          { const zeigt = sichtbare(design()); designZeigen(zeigt, Boolean(z.designs.find((x) => x.id === zeigt)?.hell)); }
          zeige(); speichern(); ton("ok");
          return true;
        }
        if ((t === "Enter" || t === " ") && z.wahl >= OBEN) {
          const id = z.apps[z.wahl - OBEN].id;
          if (z.st.lieblinge.includes(id)) z.st.lieblinge = z.st.lieblinge.filter((x) => x !== id);
          else if (z.st.lieblinge.length < LIEBLINGE_MAX) z.st.lieblinge = [...z.st.lieblinge, id];
          else { api.hinweis(`Höchstens ${LIEBLINGE_MAX} Lieblinge – nimm erst einen weg.`); ton("fehler"); return true; }
          zeige(); speichern(); ton("ok");
          return true;
        }
        return t !== "Escape" && t !== "Backspace";
      },
      schliesse() {},
    };
  },
};
