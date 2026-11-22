/* Memory: Größen 3×4 / 4×4 / 4×6, allein oder zu zweit. */
import { el } from "../gemeinsam.js";
import { kopf, ton, menue, konfetti } from "./kern.js";

const BILDER = ["🐶", "🐱", "🦊", "🐼", "🐸", "🦁", "🐵", "🐧", "🦄", "🐢", "🐙", "🦋", "🍓", "🍌", "🚀", "⚽"];
const GROESSEN = [{ name: "Klein (3×4)", z: 3, s: 4 }, { name: "Mittel (4×4)", z: 4, s: 4 }, { name: "Groß (4×6)", z: 4, s: 6 }];

export default {
  symbol: "🧠",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "Memory", "Pfeile Wählen · OK Umdrehen · STOP Zurück");
    let modus = null, spiel = null, spieler = 1, groesse = 0;

    let eigene = [];                                   /* 4.0: Adressen der eigenen Zeichnungen */
    api?.hole("/api/zeichnungen").then((d) => { eigene = (d.zeichnungen || []).map((z_) => z_.url); if (!spiel) auswahl(); }).catch(() => {});

    function auswahl() {
      spiel = null;
      inhalt.replaceChildren();
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text: "Wie groß – und wie viele spielen?" }));
      inhalt.append(spalte);
      const eintraege = [];
      GROESSEN.forEach((g, i) => {
        eintraege.push({ text: g.name + " · allein", aktion: () => starte(i, 1) });
        eintraege.push({ text: g.name + " · zu zweit", aktion: () => starte(i, 2) });
      });
      /* 4.0: mit den eigenen Bildern aus „Malen“ (ab 6 Bildern) */
      if (eigene.length >= 6) eintraege.push({ text: "🎨 Mit meinen Bildern", aktion: () => starte(0, 1, true) });
      modus = menue(spalte, eintraege);
      punkte.textContent = "";
    }

    function starte(g, anzahl, mitBildern = false) {
      modus = null;
      groesse = g;
      spieler = anzahl;
      const { z, s } = GROESSEN[g];
      const quelle = mitBildern ? eigene.map((u) => "bild:" + u) : BILDER;
      const paare = quelle.slice().sort(() => Math.random() - 0.5).slice(0, (z * s) / 2);
      const karten = paare.concat(paare).sort(() => Math.random() - 0.5)
        .map((bild) => ({ bild, offen: false, gefunden: false }));
      const feld = el("div", { class: "memory-feld", style: `grid-template-columns: repeat(${s}, auto)` });
      karten.forEach((k) => {
        const inhalt_ = k.bild.startsWith("bild:") ? el("span", {}, el("img", { class: "memory-bild", src: k.bild.slice(5), alt: "" }))
                                                   : el("span", { text: k.bild });
        k.knoten = el("div", { class: "karte" }, inhalt_);
        feld.append(k.knoten);
      });
      inhalt.replaceChildren(feld);
      spiel = { karten, s, z, pos: 0, offen: [], sperre: false, dran: 0, stand: [0, 0], zuege: 0 };
      zeige();
    }

    function zeige() {
      spiel.karten.forEach((k, i) => {
        k.knoten.classList.toggle("gewaehlt", i === spiel.pos);
        k.knoten.classList.toggle("offen", k.offen);
        k.knoten.classList.toggle("gefunden", k.gefunden);
      });
      punkte.textContent = spieler === 2
        ? `Spieler 1: ${spiel.stand[0]} · Spieler 2: ${spiel.stand[1]} · dran: ${spiel.dran + 1}`
        : `Züge: ${spiel.zuege}`;
    }

    function umdrehen() {
      const k = spiel.karten[spiel.pos];
      if (spiel.sperre || k.offen || k.gefunden) return ton("anschlag");
      k.offen = true;
      spiel.offen.push(k);
      ton("bewegen");
      if (spiel.offen.length === 2) {
        spiel.zuege++;
        const [a, b] = spiel.offen;
        if (a.bild === b.bild) {
          a.gefunden = b.gefunden = true;
          spiel.stand[spiel.dran]++;
          spiel.offen = [];
          ton("punkt");
          if (spiel.karten.every((x) => x.gefunden)) return setTimeout(fertig, 500);
        } else {
          spiel.sperre = true;
          setTimeout(() => {
            a.offen = b.offen = false;
            spiel.offen = [];
            spiel.sperre = false;
            if (spieler === 2) spiel.dran = 1 - spiel.dran;
            zeige();
          }, 1100);
        }
      }
      zeige();
    }

    function fertig() {
      ton("sieg");
      api.sende("/api/erfolg", { art: groesse === 2 ? "memory-gross" : "memory", wert: 1 }).catch(() => {});
      konfetti(box);
      let text = `Geschafft in ${spiel.zuege} Zügen!`;
      if (spieler === 2) {
        const [a, b] = spiel.stand;
        text = a === b ? `Unentschieden – ${a} zu ${b}!` : `Spieler ${a > b ? 1 : 2} gewinnt – ${Math.max(a, b)} zu ${Math.min(a, b)}!`;
      }
      const ende = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text }));
      inhalt.replaceChildren(ende);
      spiel = null;
      modus = menue(ende, [{ text: "Nochmal", aktion: () => starte(groesse, spieler) }, { text: "Andere Größe", aktion: auswahl }]);
    }

    auswahl();
    return {
      taste(t) {
        if (modus) return modus.taste(t);
        if (!spiel) return false;
        const { s } = spiel, n = spiel.karten.length;
        const bewegung = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -s, ArrowDown: s }[t];
        if (bewegung !== undefined) {
          const ziel = spiel.pos + bewegung;
          const zeilenwechsel = Math.abs(bewegung) === 1 && Math.floor(ziel / s) !== Math.floor(spiel.pos / s);
          if (ziel < 0 || ziel >= n || zeilenwechsel) ton("anschlag"); else { spiel.pos = ziel; ton("bewegen"); }
          zeige();
          return true;
        }
        if (t === "Enter" || t === " ") { umdrehen(); return true; }
        return false;
      },
      schliesse() {},
    };
  },
};
