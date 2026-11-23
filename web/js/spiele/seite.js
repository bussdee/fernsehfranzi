/* FernsehFranzi 5.0 - Bausteine für Seiten mit Inhalten von außen (Wetter, Schule, Kinderwelten, Kinder-News).
 *
 * - reiter(): Reiter oben (← → wechseln)
 * - liste(): Liste mit Auswahl, zeigt nur einen Ausschnitt (↑ ↓)
 * - leser(): Lesefenster für lange Texte; ↑ ↓ blättern seitenweise (Pfeile = Navigation, kein Cursor)
 * Alle Texte werden als Text gesetzt (el(..., {text})), nie als HTML.
 */
import { el } from "../gemeinsam.js";

export function reiter(namen, aktiv) {
  return el("div", { class: "seite-reiter" }, ...namen.map((n, i) =>
    el("span", { class: "seite-reiter-knopf" + (i === aktiv ? " an" : ""), text: n })));
}

/** eintraege: [{titel, zeile?, rechts?, symbol?, neu?}] */
export function liste(eintraege, wahl, { sichtbar = 6, leer = "Hier ist gerade nichts.", markieren = true } = {}) {
  if (!eintraege.length) return el("div", { class: "seite-leer", text: leer });
  const oben = Math.max(0, Math.min(wahl - Math.floor(sichtbar / 2), eintraege.length - sichtbar));
  const teile = eintraege.slice(oben, oben + sichtbar).map((e, i) =>
    el("div", { class: "seite-eintrag" + (markieren && oben + i === wahl ? " gewaehlt" : "") + (e.neu ? " neu" : "") + (e.aus ? " aus" : "") },
      e.bild ? el("img", { class: "seite-bild", src: e.bild, alt: "", loading: "lazy" }) : e.symbol ? el("div", { class: "seite-symbol", text: e.symbol }) : null,
      el("div", { class: "seite-eintrag-text" },
        el("div", { class: "seite-titel", text: e.titel }),
        e.zeile ? el("div", { class: "seite-zeile", text: e.zeile }) : null),
      e.rechts ? el("div", { class: "seite-rechts", text: e.rechts }) : null));
  return el("div", { class: "seite-liste" },
    oben > 0 ? el("div", { class: "seite-mehr", text: "▲" }) : null, ...teile,
    oben + sichtbar < eintraege.length ? el("div", { class: "seite-mehr", text: "▼" }) : null);
}

/** Lesefenster: bloecke [{art: h|p|li|zitat, text}] → {knoten, blaettern(richtung) -> bool (true = bewegt)} */
export function leser(titel, bloecke, { bild = null, unten = "" } = {}) {
  const text = el("div", { class: "lesen-text" },
    bild ? el("img", { class: "lesen-bild", src: bild, alt: "" }) : null,
    el("h3", { class: "lesen-titel", text: titel }),
    ...bloecke.map((b) => el(b.art === "h" ? "h4" : "p", { class: "lesen-" + b.art, text: (b.art === "li" ? "• " : "") + b.text })),
    unten ? el("p", { class: "lesen-ende", text: unten }) : null);
  const fenster = el("div", { class: "lesen-fenster" }, text);
  const balken = el("div", { class: "lesen-balken" }, el("span"));
  const knoten = el("div", { class: "lesen" }, fenster, balken);
  const stand = () => {
    const max = Math.max(1, fenster.scrollHeight - fenster.clientHeight);
    balken.firstChild.style.width = Math.round(100 * Math.min(1, fenster.scrollTop / max)) + "%";
  };
  requestAnimationFrame(stand);
  let ziel = null;
  return {
    knoten,
    blaettern(richtung) {
      /* Ziel selbst ausrechnen: beim weichen Scrollen steht scrollTop direkt danach noch auf dem alten Wert */
      const max = Math.max(0, fenster.scrollHeight - fenster.clientHeight);
      const vorher = ziel ?? fenster.scrollTop;
      ziel = Math.max(0, Math.min(max, vorher + richtung * Math.round(fenster.clientHeight * 0.8)));
      fenster.scrollTo({ top: ziel, behavior: "smooth" });
      balken.firstChild.style.width = Math.round(100 * (max ? ziel / max : 1)) + "%";
      return ziel !== vorher;
    },
    amEnde: () => (ziel ?? fenster.scrollTop) + fenster.clientHeight >= fenster.scrollHeight - 4,
  };
}

/** Fehler oder Laden als große, freundliche Zeile */
export function hinweisZeile(text, symbol = "⏳") {
  return el("div", { class: "seite-leer" }, el("div", { class: "seite-leer-symbol", text: symbol }), el("div", { text }));
}
