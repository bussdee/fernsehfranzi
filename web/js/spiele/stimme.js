/* FernsehFranzi 6.0 - Bausteine für die Mikro-Spiele (Singen, Ton-Treffer, Stimmgerät, Rakete, Klatschen).
 *
 *   stimmSpur()  die eigene Stimme als Linie, die von rechts nach links läuft; in der Mitte das Ziel-Band.
 *                zeige(cent | null): Abstand zum Zielton (Oktave egal), halten(0..1): Ring füllt sich beim Halten.
 *   stimmUhr()   großes Stimmgerät mit Zeiger (±50 Cent) und dem Namen des Tons.
 *   pegel(puffer)  Lautstärke 0..1 aus den Rohdaten des Mikrofons.
 * Gezeichnet wird höchstens etwa 12-mal pro Sekunde (so oft hört das Mikro hin) - das schafft der Pi 3. */
import { el } from "../gemeinsam.js";
import { canvasScharf } from "./kern.js";

export const BEREICH_CENT = 600;      /* ±6 Halbtöne sind oben und unten sichtbar */
export const NAH_CENT = 40;

export function centZu(f, zielHz) {
  let cent = 1200 * Math.log2(f / zielHz);
  return ((cent % 1200) + 1800) % 1200 - 600;            /* Oktave egal - Kinderstimmen singen oft höher */
}

export function pegel(puffer) {
  let summe = 0;
  for (const wert of puffer) summe += wert * wert;
  return Math.max(0, Math.min(1, (Math.sqrt(summe / puffer.length) - 0.02) * 4));
}

export function stimmSpur({ breite = 720, hoehe = 300, punkte = 60 } = {}) {
  const canvas = el("canvas", { class: "stimm-spur" });
  const ring = el("div", { class: "stimm-ring" }, el("span"));
  const pfeil = el("div", { class: "stimm-pfeil" });
  const knoten = el("div", { class: "stimm-box" }, canvas, ring, pfeil);
  const g = canvasScharf(canvas, breite, hoehe);
  const verlauf = [];
  const y = (cent) => hoehe / 2 - Math.max(-BEREICH_CENT, Math.min(BEREICH_CENT, cent)) / BEREICH_CENT * (hoehe / 2 - 14);
  function male() {
    g.clearRect(0, 0, breite, hoehe);
    const band = (NAH_CENT / BEREICH_CENT) * (hoehe / 2 - 14);
    g.fillStyle = "rgba(76, 207, 143, .22)";
    g.fillRect(0, hoehe / 2 - band, breite, band * 2);
    g.strokeStyle = "rgba(76, 207, 143, .8)"; g.lineWidth = 3; g.setLineDash([12, 10]);
    g.beginPath(); g.moveTo(0, hoehe / 2); g.lineTo(breite, hoehe / 2); g.stroke(); g.setLineDash([]);
    const schritt = (breite - 30) / punkte;
    g.lineWidth = 7; g.lineCap = "round"; g.lineJoin = "round";
    let vorher = null;
    verlauf.forEach((c, i) => {
      const x = (breite - 30) - (verlauf.length - 1 - i) * schritt;
      if (c === null) { vorher = null; return; }
      if (vorher) {
        g.strokeStyle = Math.abs(c) <= NAH_CENT ? "#4ccf8f" : "#ffc95a";
        g.beginPath(); g.moveTo(vorher[0], vorher[1]); g.lineTo(x, y(c)); g.stroke();
      }
      vorher = [x, y(c)];
    });
    const letzter = verlauf[verlauf.length - 1];
    if (letzter !== null && letzter !== undefined) {
      g.fillStyle = Math.abs(letzter) <= NAH_CENT ? "#4ccf8f" : "#fff";
      g.beginPath(); g.arc(breite - 30, y(letzter), 14, 0, Math.PI * 2); g.fill();
    }
  }
  male();
  return {
    knoten,
    zeige(cent) {
      verlauf.push(cent === null || cent === undefined ? null : cent);
      if (verlauf.length > punkte) verlauf.shift();
      male();
      pfeil.textContent = cent === null || cent === undefined ? "" : Math.abs(cent) <= NAH_CENT ? "😊 genau!" : cent > 0 ? "⬇ tiefer" : "⬆ höher";
      pfeil.className = "stimm-pfeil" + (cent !== null && cent !== undefined && Math.abs(cent) <= NAH_CENT ? " nah" : "");
    },
    halten(anteil) { ring.style.setProperty("--anteil", String(Math.max(0, Math.min(1, anteil)))); ring.classList.toggle("an", anteil > 0); },
    leeren() { verlauf.length = 0; male(); this.halten(0); pfeil.textContent = ""; },
  };
}

export function stimmUhr() {
  const zeiger = el("div", { class: "su-zeiger" });
  const name = el("div", { class: "su-name", text: "–" });
  const info = el("div", { class: "su-info" });
  const skala = el("div", { class: "su-skala" }, ...[-50, -25, 0, 25, 50].map((c) =>
    el("span", { class: "su-strich" + (c === 0 ? " mitte" : ""), style: `transform: rotate(${c * 1.4}deg)` })));
  const knoten = el("div", { class: "stimm-uhr" }, el("div", { class: "su-bogen" }, skala, zeiger), name, info);
  return {
    knoten,
    zeige(tonName, cent, zusatz = "") {
      if (cent === null || cent === undefined) { knoten.classList.remove("genau", "nah"); return; }
      const c = Math.max(-50, Math.min(50, cent));
      zeiger.style.transform = `rotate(${c * 1.4}deg)`;
      name.textContent = tonName;
      knoten.classList.toggle("genau", Math.abs(cent) <= 5);
      knoten.classList.toggle("nah", Math.abs(cent) > 5 && Math.abs(cent) <= 15);
      info.textContent = (Math.abs(cent) <= 5 ? "✔ genau richtig" : cent < 0 ? "⬆ zu tief – etwas fester spannen" : "⬇ zu hoch – etwas lockern")
        + (zusatz ? " · " + zusatz : "");
    },
    leer(text) { name.textContent = "🎤"; info.textContent = text; },
  };
}
