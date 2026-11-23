/* FernsehFranzi 5.0 - Kinder-News: Überschriften und kurze Texte aus den Quellen, die Mama oder Papa freigeschaltet
 * haben (reiner Text, ohne Links und Bilder). ↑ ↓ wählen · OK ganz lesen · STOP zurück */
import { el } from "../gemeinsam.js";
import { kopf, ton } from "./kern.js";
import { liste, leser, hinweisZeile } from "./seite.js";

export default {
  symbol: "📰",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "📰 Kinder-News", "↑ ↓ wählen · OK lesen · STOP zurück");
    const z = { eintraege: null, wahl: 0, lesen: null };
    function zeige() {
      if (z.lesen) return;
      if (!z.eintraege) return;
      inhalt.replaceChildren(el("div", { class: "seite" }, liste(z.eintraege.map((e) => ({
        symbol: "📰", titel: e.titel, zeile: `${e.quelle}${e.datum ? " · " + e.datum : ""}` })), z.wahl,
      { sichtbar: 6, leer: "Gerade keine Nachrichten." })));
    }
    inhalt.replaceChildren(hinweisZeile("Einen Moment …"));
    api.hole("/api/news").then((d) => {
      z.eintraege = d.eintraege || [];
      punkte.textContent = (d.quellen || []).join(" · ") + (d.fehlen?.length ? ` (gerade nicht erreichbar: ${d.fehlen.join(", ")})` : "");
      zeige();
    }).catch((f) => inhalt.replaceChildren(hinweisZeile(f.message, "⚠️")));
    return {
      taste(t) {
        if (z.lesen) {
          if (t === "ArrowDown" || t === "ArrowUp") { z.lesen.blaettern(t === "ArrowDown" ? 1 : -1); return true; }
          if (t === "Escape" || t === "Backspace") { z.lesen = null; hilfe.textContent = "↑ ↓ wählen · OK lesen · STOP zurück"; zeige(); return true; }
          return true;
        }
        const n = (z.eintraege || []).length;
        if (t === "ArrowUp") { z.wahl = Math.max(0, z.wahl - 1); zeige(); ton("bewegen"); return true; }
        if (t === "ArrowDown") { z.wahl = Math.min(Math.max(0, n - 1), z.wahl + 1); zeige(); ton("bewegen"); return true; }
        if ((t === "Enter" || t === " ") && n) {
          const e = z.eintraege[z.wahl];
          z.lesen = leser(e.titel, [{ art: "p", text: e.text || "Kein weiterer Text." }], { unten: `${e.quelle}${e.datum ? " · " + e.datum : ""}` });
          hilfe.textContent = "↑ ↓ blättern · STOP zurück";
          inhalt.replaceChildren(z.lesen.knoten);
          ton("ok");
          return true;
        }
        return t !== "Escape" && t !== "Backspace";
      },
      schliesse() {},
    };
  },
};
