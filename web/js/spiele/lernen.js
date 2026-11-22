/* Lernspiele (3.2, eigene Entwürfe): Einmaleins, Uhr lesen, Englisch-Wörter.
 * Bedienung überall gleich: vier Antworten, ← → (oder ↑ ↓) wählen, OK. Ziffern 1-4 wählen direkt.
 * Zählt als Lernen (Lernbonus mit Lern-Check), Erfolge geben Sticker. */
import { el } from "../gemeinsam.js";
import { kopf, ton, menue, konfetti, canvasScharf } from "./kern.js";

const WOERTER = [
  ["🐶", "dog"], ["🐱", "cat"], ["🐭", "mouse"], ["🐴", "horse"], ["🐮", "cow"], ["🐷", "pig"], ["🐸", "frog"],
  ["🐟", "fish"], ["🐦", "bird"], ["🐝", "bee"], ["🍎", "apple"], ["🍌", "banana"], ["🍞", "bread"], ["🧀", "cheese"],
  ["🥛", "milk"], ["🍓", "strawberry"], ["🏠", "house"], ["🚗", "car"], ["🚲", "bike"], ["⚽", "ball"], ["📖", "book"],
  ["🌞", "sun"], ["🌙", "moon"], ["⭐", "star"], ["🌳", "tree"], ["🌸", "flower"], ["☔", "umbrella"], ["👟", "shoe"],
  ["🎸", "guitar"], ["🔑", "key"], ["⏰", "clock"], ["🛏️", "bed"], ["🪑", "chair"], ["🍕", "pizza"], ["🎂", "cake"],
  /* 3.5: mehr Wörter */
  ["🦁", "lion"], ["🐘", "elephant"], ["🐵", "monkey"], ["🐰", "rabbit"], ["🐻", "bear"], ["🦊", "fox"], ["🐢", "turtle"],
  ["🦋", "butterfly"], ["🐧", "penguin"], ["🦉", "owl"], ["🍇", "grapes"], ["🍊", "orange"], ["🥕", "carrot"], ["🍦", "ice cream"],
  ["🥚", "egg"], ["🍪", "cookie"], ["✈️", "plane"], ["🚂", "train"], ["🚢", "ship"], ["🚌", "bus"], ["🏫", "school"],
  ["✏️", "pencil"], ["🎒", "bag"], ["👕", "shirt"], ["🧦", "socks"], ["🎩", "hat"], ["❄️", "snow"], ["🌧️", "rain"],
  ["🔥", "fire"], ["🌊", "wave"], ["🎈", "balloon"], ["🎁", "present"], ["🪁", "kite"], ["🎵", "music"], ["📺", "TV"],
];
/* 3.5: Wissens-Quiz (die Eltern können eigene Fragen dazutun) */
const QUIZ = [
  ["Wie viele Beine hat eine Spinne?", "8", ["6", "10", "4"]],
  ["Welcher Planet ist der Sonne am nächsten?", "Merkur", ["Mars", "Venus", "Erde"]],
  ["Wie viele Tage hat eine Woche?", "7", ["5", "6", "8"]],
  ["Welches Tier ist das größte der Welt?", "Blauwal", ["Elefant", "Giraffe", "Hai"]],
  ["Wie heißt die Hauptstadt von Deutschland?", "Berlin", ["München", "Hamburg", "Köln"]],
  ["Woraus machen Bienen Honig?", "Blütennektar", ["Blättern", "Wasser", "Zucker"]],
  ["Wie viele Monate hat ein Jahr?", "12", ["10", "11", "13"]],
  ["Welche Farbe entsteht aus Blau und Gelb?", "Grün", ["Lila", "Orange", "Braun"]],
  ["Welches Tier schläft im Winter (Winterschlaf)?", "Igel", ["Hund", "Pferd", "Huhn"]],
  ["Wie viele Saiten hat ein Bass meistens?", "4", ["6", "5", "3"]],
  ["Wie viele Saiten hat eine Gitarre meistens?", "6", ["4", "5", "8"]],
  ["Was ist bei 0 Grad Celsius mit Wasser?", "Es gefriert", ["Es kocht", "Es verdampft", "Nichts"]],
  ["Welcher Kontinent ist der größte?", "Asien", ["Afrika", "Europa", "Amerika"]],
  ["Welches Tier legt Eier?", "Huhn", ["Kuh", "Katze", "Hund"]],
  ["Wie heißt der längste Fluss in Deutschland?", "Rhein", ["Elbe", "Donau", "Main"]],
  ["Wie viele Minuten hat eine Stunde?", "60", ["100", "30", "24"]],
  ["Wie nennt man ein Baby-Pferd?", "Fohlen", ["Kalb", "Lamm", "Ferkel"]],
  ["Welches Instrument hat schwarze und weiße Tasten?", "Klavier", ["Geige", "Trommel", "Flöte"]],
  ["Welche Form hat ein Fußball?", "Kugel", ["Würfel", "Kegel", "Zylinder"]],
  ["Was brauchen Pflanzen zum Wachsen?", "Licht und Wasser", ["Nur Erde", "Musik", "Dunkelheit"]],
  ["Wie viele Ecken hat ein Dreieck?", "3", ["4", "5", "6"]],
  ["Welches ist das schnellste Landtier?", "Gepard", ["Löwe", "Pferd", "Hase"]],
  ["Was ist die Hälfte von 100?", "50", ["25", "10", "75"]],
  ["In welcher Jahreszeit fallen die Blätter?", "Herbst", ["Frühling", "Sommer", "Winter"]],
  ["Wie viele Zähne hat ein Erwachsener normalerweise?", "32", ["20", "28", "40"]],
  ["Welcher Vogel kann nicht fliegen?", "Pinguin", ["Adler", "Spatz", "Möwe"]],
  ["Wie heißt der Erdtrabant, der nachts leuchtet?", "Mond", ["Mars", "Venus", "Sirius"]],
  ["Was ist größer: ein Meter oder ein Zentimeter?", "Ein Meter", ["Ein Zentimeter", "Gleich groß", "Weiß niemand"]],
];
const FARBEN_EN = [["rot", "red", "#ff5a5a"], ["grün", "green", "#4ccf6f"], ["blau", "blue", "#4f8dff"],
                   ["gelb", "yellow", "#ffd23f"], ["schwarz", "black", "#222"], ["weiß", "white", "#fff"],
                   ["orange", "orange", "#ff9f1c"], ["lila", "purple", "#9b5de5"]];
const ZAHLEN_EN = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"];

const mische = (liste) => liste.map((x) => [Math.random(), x]).sort((a, b) => a[0] - b[0]).map((x) => x[1]);

/** Vier Antworten zur richtigen (ohne Doppelte). */
export function antworten(richtig, falscheQuelle) {
  const falsch = mische([...new Set(falscheQuelle.filter((x) => String(x) !== String(richtig)))]).slice(0, 3);
  return mische([richtig, ...falsch]);
}

function erfolg(api, art, wert) { api.sende("/api/erfolg", { art, wert }).catch(() => {}); }

export default {
  symbol: "🎓",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "Lernspiele", "Pfeile Wählen · OK · STOP Zurück");
    let modus = null;

    function hauptmenue() {
      hilfe.textContent = "Pfeile Wählen · OK · STOP Zurück";
      punkte.textContent = "";
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text: "Was möchtest du üben?" }));
      inhalt.replaceChildren(spalte);
      modus = menue(spalte, [
        { text: "✖️ Einmaleins", aktion: einmaleinsWahl },
        { text: "🕰️ Uhr lesen", aktion: uhrWahl },
        { text: "🇬🇧 Englisch", aktion: englischWahl },
        { text: "➕ Rechnen", aktion: rechnenWahl },
        { text: "❓ Wissens-Quiz", aktion: wissensQuiz },
      ]);
      modus.unter = false;
    }

    /* Gemeinsamer Ablauf: Frage + vier Antworten, Serie zählen */
    function quiz({ titel, naechste, art, serie = false, anzeige }) {
      let richtig = 0, folge = 0, pos = 0, aufgabe = null, gesperrt = false;
      const frage = el("div", { class: "witz", style: "margin-bottom:3vh" });
      const bild = el("div", { style: "display:flex;justify-content:center;margin-bottom:3vh" });
      const wahl = el("div", { class: "knopfreihe" });
      inhalt.replaceChildren(el("div", { style: "text-align:center" }, frage, bild, wahl));
      hilfe.textContent = "← → Wählen · OK Antworten · 1–4 direkt · STOP Zurück";
      const zeige = () => {
        wahl.replaceChildren(...aufgabe.antworten.map((a, i) => el("span", {
          class: "knopf" + (i === pos ? " gewaehlt" : ""), style: "min-width:120px;font-size:clamp(22px,2.4vw,36px)",
          text: anzeige ? anzeige(a) : String(a) })));
        punkte.textContent = `${titel} · Richtig: ${richtig}` + (serie ? ` · Serie: ${folge}` : "");
      };
      const neu = () => {
        aufgabe = naechste();
        pos = 0;
        frage.textContent = aufgabe.frage;
        bild.replaceChildren(...(aufgabe.bild ? [aufgabe.bild] : []));
        gesperrt = false;
        zeige();
      };
      const antworte = () => {
        if (gesperrt) return;
        gesperrt = true;
        if (String(aufgabe.antworten[pos]) === String(aufgabe.richtig)) {
          richtig++; folge++;
          ton("sieg");
          api.hinweis(["Super!", "Richtig!", "Klasse!", "Genau!"][richtig % 4]);
          if (art === "einmaleins") { if (folge === 10) { erfolg(api, art, 10); konfetti(box); } }
          else erfolg(api, art, 1);
          setTimeout(neu, 700);
        } else {
          folge = 0;
          ton("fehler");
          api.hinweis(`Leider nicht – richtig ist ${anzeige ? anzeige(aufgabe.richtig) : aufgabe.richtig}.`);
          setTimeout(neu, 1600);
        }
        zeige();
      };
      neu();
      modus = { unter: true, zurueck: hauptmenue, taste(t) {
        const n = aufgabe.antworten.length;
        if (t === "ArrowLeft" || t === "ArrowUp") { pos = (pos + n - 1) % n; zeige(); ton("bewegen"); return true; }
        if (t === "ArrowRight" || t === "ArrowDown") { pos = (pos + 1) % n; zeige(); ton("bewegen"); return true; }
        if (/^[1-4]$/.test(t) && +t <= n) { pos = +t - 1; antworte(); return true; }
        if (t === "Enter" || t === " ") { antworte(); return true; }
        return false;
      } };
    }

    /* ---------------------------------------------------- Einmaleins */
    function einmaleinsWahl() {
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text: "Welche Reihe?" }));
      inhalt.replaceChildren(spalte);
      const reihen = [2, 3, 4, 5, 6, 7, 8, 9, 10];
      modus = menue(spalte, [{ text: "Alle gemischt", aktion: () => einmaleins(null) },
                             ...reihen.map((r) => ({ text: `${r}er-Reihe`, aktion: () => einmaleins(r) }))]);
      modus.unter = true;
      modus.zurueck = hauptmenue;
    }

    function einmaleins(reihe) {
      quiz({ titel: reihe ? `${reihe}er-Reihe` : "Einmaleins", art: "einmaleins", serie: true, naechste: () => {
        const a = reihe || 2 + Math.floor(Math.random() * 9), b = 1 + Math.floor(Math.random() * 10);
        const r = a * b;
        const nahe = [r + a, r - a, r + b, r - b, r + 1, r - 1, (a + 1) * b, a * (b + 1)].filter((x) => x > 0);
        return { frage: `${b} × ${a} = ?`, richtig: r, antworten: antworten(r, nahe) };
      } });
    }

    /* ---------------------------------------------------- Uhr lesen */
    function uhrWahl() {
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text: "Wie schwer?" }));
      inhalt.replaceChildren(spalte);
      modus = menue(spalte, [
        { text: "Volle Stunden", aktion: () => uhr(60) }, { text: "Halbe Stunden", aktion: () => uhr(30) },
        { text: "Viertelstunden", aktion: () => uhr(15) }, { text: "5 Minuten", aktion: () => uhr(5) },
      ]);
      modus.unter = true;
      modus.zurueck = hauptmenue;
    }

    function zifferblatt(h, m) {
      const groesse = Math.floor(Math.min(innerHeight * 0.42, 360));
      const canvas = el("canvas", { class: "spielfeld", style: "background:transparent" });
      const g = canvasScharf(canvas, groesse, groesse);
      const r = groesse / 2 - 6, c = groesse / 2;
      g.fillStyle = "#f4f6fb"; g.beginPath(); g.arc(c, c, r, 0, 7); g.fill();
      g.strokeStyle = "#2a3550"; g.lineWidth = 6; g.stroke();
      g.fillStyle = "#1d2636"; g.font = `700 ${groesse / 11}px system-ui, sans-serif`; g.textAlign = "center"; g.textBaseline = "middle";
      for (let i = 1; i <= 12; i++) {
        const w = (i / 12) * Math.PI * 2 - Math.PI / 2;
        g.fillText(String(i), c + Math.cos(w) * r * 0.8, c + Math.sin(w) * r * 0.8);
      }
      for (let i = 0; i < 60; i++) {
        const w = (i / 60) * Math.PI * 2, lang = i % 5 === 0 ? 0.08 : 0.04;
        g.lineWidth = i % 5 === 0 ? 3 : 1;
        g.beginPath();
        g.moveTo(c + Math.sin(w) * r * (0.97 - lang), c - Math.cos(w) * r * (0.97 - lang));
        g.lineTo(c + Math.sin(w) * r * 0.97, c - Math.cos(w) * r * 0.97);
        g.stroke();
      }
      const zeiger = (winkel, laenge, breite, farbe) => {
        g.strokeStyle = farbe; g.lineWidth = breite; g.lineCap = "round";
        g.beginPath(); g.moveTo(c, c); g.lineTo(c + Math.sin(winkel) * r * laenge, c - Math.cos(winkel) * r * laenge); g.stroke();
      };
      zeiger(((h % 12) + m / 60) / 12 * Math.PI * 2, 0.5, 10, "#1d2636");   /* Stundenzeiger: kurz, dick */
      zeiger((m / 60) * Math.PI * 2, 0.78, 6, "#e4002b");                   /* Minutenzeiger: lang, rot */
      g.fillStyle = "#1d2636"; g.beginPath(); g.arc(c, c, 8, 0, 7); g.fill();
      return canvas;
    }

    function uhr(schritt) {
      const text = (h, m) => `${h}:${String(m).padStart(2, "0")}`;
      quiz({ titel: "Uhr lesen", art: "uhr", naechste: () => {
        const h = 1 + Math.floor(Math.random() * 12), m = schritt === 60 ? 0 : Math.floor(Math.random() * (60 / schritt)) * schritt;
        const richtig = text(h, m);
        const falsch = [text(h, (m + 30) % 60), text((h % 12) + 1, m), text(h === 1 ? 12 : h - 1, m),
                        text(Math.floor(m / 5) || 12, h * 5 % 60), text(h, (m + schritt) % 60)];
        return { frage: "Wie spät ist es?", bild: zifferblatt(h, m), richtig, antworten: antworten(richtig, falsch) };
      } });
    }

    /* ---------------------------------------------------- Rechnen (3.5) */
    function rechnenWahl() {
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text: "Was rechnen wir?" }));
      inhalt.replaceChildren(spalte);
      modus = menue(spalte, [{ text: "Plus und Minus bis 20", aktion: () => rechnen(20) },
                             { text: "Plus und Minus bis 100", aktion: () => rechnen(100) },
                             { text: "Geteilt (Einmaleins rückwärts)", aktion: () => rechnen("geteilt") }]);
      modus.unter = true;
      modus.zurueck = hauptmenue;
    }

    function rechnen(art) {
      quiz({ titel: "Rechnen", art: "einmaleins", naechste: () => {
        let a, b, zeichen, r;
        if (art === "geteilt") { b = 2 + Math.floor(Math.random() * 9); r = 1 + Math.floor(Math.random() * 10); a = b * r; zeichen = ":"; }
        else if (Math.random() < 0.5) { a = Math.floor(Math.random() * art); b = Math.floor(Math.random() * (art - a + 1)); r = a + b; zeichen = "+"; }
        else { a = Math.floor(Math.random() * (art + 1)); b = Math.floor(Math.random() * (a + 1)); r = a - b; zeichen = "−"; }
        const nahe = [r + 1, r - 1, r + 2, r - 2, r + 10, r - 10, r + 5].filter((x) => x >= 0);
        return { frage: `${a} ${zeichen} ${b} = ?`, richtig: r, antworten: antworten(r, nahe) };
      } });
    }

    /* ---------------------------------------------------- Wissens-Quiz (3.5) */
    async function wissensQuiz() {
      let fragen = QUIZ.map(([frage, richtig, falsch]) => ({ frage, richtig, falsch }));
      try { fragen = fragen.concat((await api.hole("/api/inhalte")).quiz || []); } catch (_) { /* nur die eingebauten */ }
      let stapel = [];
      quiz({ titel: "Wissens-Quiz", art: "einmaleins", naechste: () => {
        if (!stapel.length) stapel = mische(fragen);            /* jede Frage einmal, dann neu gemischt */
        const q = stapel.pop();
        return { frage: q.frage, richtig: q.richtig, antworten: mische([q.richtig, ...q.falsch]) };
      } });
    }

    /* ---------------------------------------------------- Englisch */
    function englischWahl() {
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text: "Was üben wir?" }));
      inhalt.replaceChildren(spalte);
      modus = menue(spalte, [{ text: "Wörter mit Bildern", aktion: englischWoerter },
                             { text: "Farben", aktion: englischFarben }, { text: "Zahlen", aktion: englischZahlen }]);
      modus.unter = true;
      modus.zurueck = hauptmenue;
    }

    function englischWoerter() {
      quiz({ titel: "Englisch", art: "englisch", naechste: () => {
        const [emoji, wort] = WOERTER[Math.floor(Math.random() * WOERTER.length)];
        return { frage: "Wie heißt das auf Englisch?", bild: el("div", { style: "font-size:clamp(80px,14vh,160px)", text: emoji }),
                 richtig: wort, antworten: antworten(wort, WOERTER.map((w) => w[1])) };
      } });
    }

    function englischFarben() {
      quiz({ titel: "Farben auf Englisch", art: "englisch", naechste: () => {
        const [, en, farbe] = FARBEN_EN[Math.floor(Math.random() * FARBEN_EN.length)];
        return { frage: "Welche Farbe ist das?",
                 bild: el("div", { style: `width:18vh;height:18vh;border-radius:24px;border:3px solid #9ba8bb;background:${farbe}` }),
                 richtig: en, antworten: antworten(en, FARBEN_EN.map((f) => f[1])) };
      } });
    }

    function englischZahlen() {
      quiz({ titel: "Zahlen auf Englisch", art: "englisch", naechste: () => {
        const n = Math.floor(Math.random() * ZAHLEN_EN.length);
        return { frage: "Wie heißt diese Zahl auf Englisch?", bild: el("div", { class: "witz", style: "font-size:clamp(80px,14vh,160px)", text: String(n) }),
                 richtig: ZAHLEN_EN[n], antworten: antworten(ZAHLEN_EN[n], ZAHLEN_EN) };
      } });
    }

    hauptmenue();
    return {
      taste(t) {
        if (modus?.taste(t)) return true;
        if ((t === "Escape" || t === "Backspace") && modus?.unter) { (modus.zurueck || hauptmenue)(); return true; }
        return false;
      },
      schliesse() {},
    };
  },
};
