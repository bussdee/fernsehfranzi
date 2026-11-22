/* Farben-Echo (neu in 3.0): Merkspiel mit vier Farben. Eigener Entwurf.
   Eingabe: Pfeile (← Rot, ↑ Grün, → Gelb, ↓ Blau) - geht mit jedem Gerät -,
   die Farbtasten der Fernbedienung (eingabe.py sendet sie hier als F9-F12) oder
   das Steuerkreuz des Controllers. */
import { el, pause } from "../gemeinsam.js";
import { kopf, ton, menue, konfetti } from "./kern.js";

const FARBEN = ["rot", "gruen", "gelb", "blau"];
const TASTEN = { ArrowLeft: 0, ArrowUp: 1, ArrowRight: 2, ArrowDown: 3, F9: 0, F10: 1, F11: 2, F12: 3 };

export default {
  symbol: "🔴",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "Farben-Echo", "Merk dir die Farben! Pfeile oder Farbtasten · STOP Zurück");
    let modus = null, spiel = null, rekord = Number(localStorage.getItem("ff-echo-rekord") || 0);

    function auswahl() {
      spiel = null;
      const spalte = el("div", { style: "text-align:center" },
        el("p", { class: "punkte", text: "Der Fernseher zeigt Farben – du machst sie nach." }));
      inhalt.replaceChildren(spalte);
      modus = menue(spalte, [{ text: "Los geht's", aktion: starte }, { text: "Gemütlich (langsamer)", aktion: () => starte(true) }]);
      punkte.textContent = rekord ? "Rekord: " + rekord : "";
    }

    function starte(langsam = false) {
      modus = null;
      const feld = el("div", { class: "echo-feld" });
      const knoepfe = FARBEN.map((f, i) => {
        const k = el("div", { class: "farbe " + f, text: ["←", "↑", "→", "↓"][i] });
        feld.append(k);
        return k;
      });
      const mitte = el("div", { class: "mitte", text: "Schau zu!" });
      feld.append(mitte);
      inhalt.replaceChildren(feld);
      spiel = { folge: [], eingabe: 0, zuhoeren: false, knoepfe, mitte, tempo: langsam ? 1.4 : 1 };
      naechsteRunde();
    }

    async function leuchte(i, ms) {
      if (!spiel) return;
      spiel.knoepfe[i].classList.add("leuchtet");
      ton(FARBEN[i], { dauer: ms / 1000, laut: 0.35 });     /* Ton so lang wie das Leuchten */
      await pause(ms);
      spiel?.knoepfe[i].classList.remove("leuchtet");
    }

    async function naechsteRunde() {
      spiel.folge.push(Math.floor(Math.random() * 4));
      spiel.eingabe = 0;
      spiel.zuhoeren = false;
      spiel.mitte.textContent = "Schau zu!";
      punkte.textContent = `Runde ${spiel.folge.length}` + (rekord ? ` · Rekord: ${rekord}` : "");
      await pause(700);
      const dauer = Math.max(260, 560 - spiel.folge.length * 20) * spiel.tempo;
      for (const i of spiel.folge) {
        if (!spiel) return;
        await leuchte(i, dauer);
        await pause(dauer * 0.35);
      }
      if (!spiel) return;
      spiel.zuhoeren = true;
      spiel.mitte.textContent = "Du bist dran!";
    }

    async function druecke(i) {
      if (!spiel?.zuhoeren) return;
      leuchte(i, 220);
      if (spiel.folge[spiel.eingabe] !== i) return verloren();
      spiel.eingabe++;
      if (spiel.eingabe === spiel.folge.length) {
        spiel.zuhoeren = false;
        spiel.mitte.textContent = "Super!";
        await pause(600);
        if (spiel) naechsteRunde();
      }
    }

    function verloren() {
      const geschafft = spiel.folge.length - 1;
      spiel = null;
      api.sende("/api/erfolg", { art: "echo", wert: geschafft }).catch(() => {});
      ton("verloren");
      const neu = geschafft > rekord;
      if (neu) { rekord = geschafft; localStorage.setItem("ff-echo-rekord", rekord); konfetti(box); }
      const ende = el("div", { style: "text-align:center" },
        el("p", { class: "punkte", text: (neu ? "Neuer Rekord! " : "") + `${geschafft} Runden geschafft!` }));
      inhalt.replaceChildren(ende);
      modus = menue(ende, [{ text: "Nochmal", aktion: () => starte() }, { text: "Zurück zur Auswahl", aktion: auswahl }]);
    }

    auswahl();
    return {
      taste(t) {
        if (modus) return modus.taste(t);
        if (!spiel) return false;
        if (t in TASTEN) { druecke(TASTEN[t]); return true; }
        return false;
      },
      schliesse() { spiel = null; },
    };
  },
};
