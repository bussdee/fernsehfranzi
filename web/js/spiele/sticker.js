/* Sticker-Album (3.1): Erfolge aus allen Bereichen - Spiele, Malen, Bass, Lernen, Bewegungspausen. */
import { el } from "../gemeinsam.js";
import { kopf, ton } from "./kern.js";

export default {
  symbol: "🏅",
  oeffne(box, api) {
    const { inhalt, punkte } = kopf(box, "Mein Sticker-Album", "Pfeile Blättern · STOP Zurück");
    const raster = el("div", { style: "display:grid;grid-template-columns:repeat(6,1fr);gap:1.4vw;max-width:1300px" });
    const info = el("p", { class: "punkte", style: "text-align:center;min-height:2em" });
    inhalt.replaceChildren(el("div", {}, raster, info));
    let liste = [], pos = 0;
    const zeige = () => {
      raster.replaceChildren(...liste.map((s, i) => el("div", {
        class: "karte" + (i === pos ? " gewaehlt" : ""),
        style: `width:auto;flex-direction:column;gap:6px;background:${s.seit ? "#f4f6fb" : "#1d2636"};color:#111;font-size:clamp(30px,4vw,60px)`,
      }, el("span", { text: s.seit ? s.symbol : "❔", style: "visibility:visible" }))));
      const s = liste[pos];
      if (s) info.textContent = s.seit ? `${s.symbol} ${s.name} – seit ${new Date(s.seit).toLocaleDateString("de-DE")}` : `❔ Noch offen: ${s.bedingung}`;
      punkte.textContent = `${liste.filter((x) => x.seit).length} von ${liste.length} gesammelt`;
    };
    api.hole("/api/sticker").then((d) => { liste = d.sticker; zeige(); }).catch(() => { info.textContent = "Album nicht erreichbar."; });
    return {
      taste(t) {
        const d = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -6, ArrowDown: 6 }[t];
        if (d !== undefined && liste.length) { pos = Math.max(0, Math.min(liste.length - 1, pos + d)); zeige(); ton("bewegen"); return true; }
        return false;
      },
      schliesse() {},
    };
  },
};
