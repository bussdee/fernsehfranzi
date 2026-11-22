/* Drei Gewinnt: leicht / mittel / schwer gegen den Fernseher oder zu zweit. */
import { el } from "../gemeinsam.js";
import { kopf, ton, menue, konfetti } from "./kern.js";

const LINIEN = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];
const STUFEN = ["Leicht", "Mittel", "Schwer"];

export function sieger(feld) {
  for (const l of LINIEN) if (feld[l[0]] && feld[l[0]] === feld[l[1]] && feld[l[1]] === feld[l[2]]) return { wer: feld[l[0]], linie: l };
  return feld.every(Boolean) ? { wer: "unentschieden", linie: [] } : null;
}

function minimax(feld, wer) {
  const s = sieger(feld);
  if (s) return { wert: s.wer === "🔵" ? 1 : s.wer === "❌" ? -1 : 0 };
  let bester = { wert: wer === "🔵" ? -2 : 2, zug: -1 };
  feld.forEach((x, i) => {
    if (x) return;
    feld[i] = wer;
    const w = minimax(feld, wer === "🔵" ? "❌" : "🔵").wert;
    feld[i] = null;
    if ((wer === "🔵" && w > bester.wert) || (wer === "❌" && w < bester.wert)) bester = { wert: w, zug: i };
  });
  return bester;
}

/** Zug des Fernsehers (🔵). stufe 0 zufällig, 1 gewinnt/blockt, 2 perfekt. */
export function computerZug(feld, stufe) {
  const frei = feld.map((x, i) => (x ? -1 : i)).filter((i) => i >= 0);
  if (stufe >= 1) {
    for (const wer of ["🔵", "❌"]) {
      for (const i of frei) {
        feld[i] = wer;
        const gewinnt = sieger(feld)?.wer === wer;
        feld[i] = null;
        if (gewinnt) return i;
      }
    }
  }
  if (stufe === 2) return minimax(feld.slice(), "🔵").zug;
  return frei[Math.floor(Math.random() * frei.length)];
}

export default {
  symbol: "⭐",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "Drei Gewinnt", "Pfeile Wählen · OK Setzen · STOP Zurück");
    let modus = null, spiel = null, letzteWahl = null;

    function auswahl() {
      spiel = null;
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text: "Gegen wen?" }));
      inhalt.replaceChildren(spalte);
      modus = menue(spalte, [
        ...STUFEN.map((s, i) => ({ text: "Fernseher · " + s, aktion: () => starte({ stufe: i }) })),
        { text: "Zu zweit", aktion: () => starte({ zweit: true }) },
      ]);
      punkte.textContent = "";
    }

    function starte(wahl) {
      letzteWahl = wahl;
      modus = null;
      const raster = el("div", { class: "drei-feld" });
      const zellen = Array.from({ length: 9 }, () => { const z = el("div", { class: "zelle" }); raster.append(z); return z; });
      inhalt.replaceChildren(raster);
      spiel = { feld: Array(9).fill(null), zellen, pos: 4, dran: "❌", aus: false, ...wahl };
      zeige();
    }

    function zeige(linie = []) {
      spiel.zellen.forEach((z, i) => {
        z.textContent = spiel.feld[i] || "";
        z.classList.toggle("gewaehlt", i === spiel.pos && !spiel.aus);
        z.classList.toggle("sieg", linie.includes(i));
      });
      punkte.textContent = spiel.aus ? "" : spiel.zweit ? `${spiel.dran} ist dran` : "Du bist ❌";
    }

    function setze(i) {
      if (spiel.aus || spiel.feld[i]) return ton("anschlag");
      spiel.feld[i] = spiel.dran;
      ton("bewegen");
      if (pruefe()) return;
      spiel.dran = spiel.dran === "❌" ? "🔵" : "❌";
      zeige();
      if (!spiel.zweit && spiel.dran === "🔵") {
        setTimeout(() => {
          if (!spiel || spiel.aus) return;
          spiel.feld[computerZug(spiel.feld, spiel.stufe)] = "🔵";
          if (!pruefe()) { spiel.dran = "❌"; zeige(); }
        }, 450);
      }
    }

    function pruefe() {
      const s = sieger(spiel.feld);
      if (!s) return false;
      spiel.aus = true;
      zeige(s.linie);
      let text = "Unentschieden!";
      if (s.wer !== "unentschieden") {
        text = spiel.zweit ? `${s.wer} gewinnt!` : s.wer === "❌" ? "Du hast gewonnen!" : "Der Fernseher gewinnt!";
        if (spiel.zweit || s.wer === "❌") { ton("sieg"); konfetti(box); } else ton("verloren");
        if (!spiel.zweit && s.wer === "❌" && spiel.stufe === 2) api.sende("/api/erfolg", { art: "drei-schwer", wert: 1 }).catch(() => {});
        if (spiel.zweit) api.sende("/api/erfolg", { art: "duell", wert: 1 }).catch(() => {});
      }
      setTimeout(() => {
        const ende = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text }));
        inhalt.replaceChildren(ende);
        modus = menue(ende, [{ text: "Nochmal", aktion: () => starte(letzteWahl) }, { text: "Andere Wahl", aktion: auswahl }]);
      }, 1200);
      return true;
    }

    auswahl();
    return {
      taste(t) {
        if (modus) return modus.taste(t);
        if (!spiel) return false;
        const b = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[t];
        if (b) {
          const x = (spiel.pos % 3) + b[0], y = Math.floor(spiel.pos / 3) + b[1];
          if (x < 0 || x > 2 || y < 0 || y > 2) ton("anschlag"); else { spiel.pos = y * 3 + x; ton("bewegen"); }
          zeige();
          return true;
        }
        if (/^[1-9]$/.test(t)) { spiel.pos = +t - 1; setze(spiel.pos); return true; }
        if (t === "Enter" || t === " ") { setze(spiel.pos); return true; }
        return false;
      },
      schliesse() { spiel = null; },
    };
  },
};
