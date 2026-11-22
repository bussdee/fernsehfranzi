/* FernsehFranzi 3.5 - Gutschein einlösen: 6 Ziffern mit der Fernbedienung (oder Pfeile + OK auf dem Tastenfeld). */
import { el } from "../gemeinsam.js";
import { kopf, konfetti, ton } from "./kern.js";

const TASTEN = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "OK"];

export default {
  symbol: "🎟️",
  oeffne(box, api) {
    const { inhalt } = kopf(box, "🎟️ Gutschein einlösen", "Ziffern eintippen · OK einlösen · STOP zurück");
    let code = "", pos = 0, sperre = false;
    const felder = el("div", { class: "pinfeld gutschein-feld" });
    const meldung = el("div", { class: "gutschein-meldung" });
    const raster = el("div", { class: "gutschein-tasten" });
    const knoepfe = TASTEN.map((t) => {
      const k = el("button", { class: "knopf", type: "button", tabindex: "-1", text: t });
      k.addEventListener("click", () => druecke(t));
      raster.append(k);
      return k;
    });
    inhalt.append(el("div", { class: "gutschein" }, el("p", { class: "leise", text: "Tipp den Code von deinem Gutschein-Zettel ein:" }),
      felder, meldung, raster));

    function zeige() {
      felder.replaceChildren(...Array.from({ length: 6 }, (_, i) => el("span", { text: code[i] || "" })));
      knoepfe.forEach((k, i) => k.classList.toggle("gewaehlt", i === pos));
    }
    async function einloesen() {
      if (code.length !== 6 || sperre) return;
      sperre = true;
      meldung.className = "gutschein-meldung";
      meldung.textContent = "Einen Moment …";
      try {
        const antwort = await api.sende("/api/gutschein", { code });
        meldung.textContent = "🎉 " + antwort.meldung;
        meldung.classList.add("gut");
        ton("sieg");
        konfetti(box);
        code = "";
      } catch (fehler) {
        meldung.textContent = fehler.message;
        meldung.classList.add("schlecht");
        felder.classList.remove("wackeln"); void felder.offsetWidth; felder.classList.add("wackeln");
        ton("fehler");
        code = "";
      }
      sperre = false;
      zeige();
    }
    function druecke(t) {
      if (t === "⌫") code = code.slice(0, -1);
      else if (t === "OK") return einloesen();
      else if (code.length < 6) { code += t; meldung.textContent = ""; }
      zeige();
      if (code.length === 6) { pos = 11; zeige(); }
    }
    zeige();
    return {
      taste(t) {
        if (/^[0-9]$/.test(t)) { druecke(t); return true; }
        if (t === "Backspace") { druecke("⌫"); return true; }
        if (t === "Enter" || t === " ") { druecke(TASTEN[pos]); return true; }
        const schritt = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -3, ArrowDown: 3 }[t];
        if (schritt !== undefined) { const neu = pos + schritt; if (neu >= 0 && neu < 12) { pos = neu; zeige(); ton("bewegen"); } return true; }
        return false;
      },
    };
  },
};
