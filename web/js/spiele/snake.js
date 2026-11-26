/* Snake (neu in 3.0): Tempostufen, weiche Gleitbewegung, große Felder, Eingabepuffer gegen die
   CEC-Verzögerung, durchlässige Wände (wer rausläuft, kommt gegenüber wieder rein). */
import { el, stufe as animStufe } from "../gemeinsam.js";
import { kopf, takt, ton, canvasScharf, menue, konfetti } from "./kern.js";

const STUFEN = [
  { name: "Gemütlich", felderProSek: 4, steigend: false },
  { name: "Normal", felderProSek: 6, steigend: false },
  { name: "Flott", felderProSek: 8, steigend: true },
];
const SPALTEN = 20, ZEILEN = 12;
const RICHTUNG = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] };

export default {
  symbol: "🐍",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "Snake", "Pfeile Lenken · PAUSE/P Pause · STOP Zurück");
    let modus = null, spiel = null, rekord = Number(localStorage.getItem("ff-snake-rekord") || 0);

    function auswahl() {
      inhalt.replaceChildren();
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text: "Wie schnell?" }));
      inhalt.append(spalte);
      modus = menue(spalte, STUFEN.map((s, i) => ({ text: s.name, aktion: () => starte(i) })), 0);
      punkte.textContent = rekord ? "Rekord: " + rekord : "";
    }

    function starte(stufe) {
      modus = null;
      inhalt.replaceChildren();
      const feld = Math.floor(Math.min((innerWidth * 0.9) / SPALTEN, (innerHeight * 0.72) / ZEILEN));
      const canvas = el("canvas", { class: "spielfeld" });
      inhalt.append(canvas);
      const g = canvasScharf(canvas, feld * SPALTEN, feld * ZEILEN);
      const s = {
        schlange: [[6, 6], [5, 6], [4, 6]], vorher: null, richtung: [1, 0], puffer: [],
        futter: null, punkte: 0, aus: false, stufe: STUFEN[stufe],
      };
      s.vorher = s.schlange.map((p) => [...p]);
      const neuesFutter = () => {
        do { s.futter = [Math.floor(Math.random() * SPALTEN), Math.floor(Math.random() * ZEILEN)]; }
        while (s.schlange.some(([x, y]) => x === s.futter[0] && y === s.futter[1]));
      };
      neuesFutter();
      const zeigePunkte = () => { punkte.textContent = `Punkte: ${s.punkte}` + (rekord ? ` · Rekord: ${rekord}` : ""); };
      zeigePunkte();

      function logik() {
        if (s.aus) return;
        if (s.puffer.length) s.richtung = s.puffer.shift();
        s.vorher = s.schlange.map((p) => [...p]);
        const [kx, ky] = s.schlange[0];
        const neu = [(kx + s.richtung[0] + SPALTEN) % SPALTEN, (ky + s.richtung[1] + ZEILEN) % ZEILEN];
        const frisst = neu[0] === s.futter[0] && neu[1] === s.futter[1];
        const koerper = frisst ? s.schlange : s.schlange.slice(0, -1);
        if (koerper.some(([x, y]) => x === neu[0] && y === neu[1])) return verloren();
        s.schlange.unshift(neu);
        if (frisst) {
          s.vorher.push([...s.vorher[s.vorher.length - 1]]);
          s.punkte++;
          ton("punkt");
          neuesFutter();
          if (s.stufe.steigend && s.punkte % 5 === 0) spiel.schritt = Math.max(70, spiel.schritt * 0.92);
          zeigePunkte();
        } else s.schlange.pop();
      }

      /* 6.9.26: Wiese einmal vorzeichnen; Schlange rund mit Augen, Apfel statt Punkt; „hoch“: Schatten, hüpfender Apfel */
      const hoch = animStufe() === "hoch";
      const wiese = document.createElement("canvas");
      wiese.width = feld * SPALTEN; wiese.height = feld * ZEILEN;
      { const w = wiese.getContext("2d");
        for (let x = 0; x < SPALTEN; x++) for (let y = 0; y < ZEILEN; y++) {
          w.fillStyle = (x + y) % 2 ? "#2f7d45" : "#358a4c"; w.fillRect(x * feld, y * feld, feld, feld);
          if ((x * 7 + y * 13) % 11 === 0) { w.fillStyle = (x + y) % 3 ? "#ffe27a" : "#ffffff";
            w.beginPath(); w.arc(x * feld + feld * 0.3, y * feld + feld * 0.7, feld * 0.06, 0, Math.PI * 2); w.fill(); }
          if ((x * 5 + y * 3) % 7 === 0) { w.strokeStyle = "rgba(20,60,30,.35)"; w.lineWidth = 2; w.beginPath();
            w.moveTo(x * feld + feld * 0.6, y * feld + feld * 0.8); w.lineTo(x * feld + feld * 0.65, y * feld + feld * 0.55); w.stroke(); }
        } }
      let bild = 0;
      function zeichne(anteil) {
        bild++;
        g.drawImage(wiese, 0, 0);
        const fx = (s.futter[0] + 0.5) * feld, fy = (s.futter[1] + 0.5) * feld + (hoch ? Math.sin(bild * 0.15) * feld * 0.06 : 0);
        g.textAlign = "center"; g.textBaseline = "middle"; g.font = `${Math.round(feld * 0.78)}px "FF Emoji", sans-serif`; g.fillStyle = "#000";
        g.fillText("🍎", fx, fy);
        const punkte = s.schlange.map((p, i) => {
          const alt = s.vorher[i] || p;
          let dx = p[0] - alt[0], dy = p[1] - alt[1];
          if (Math.abs(dx) > 1) dx = -Math.sign(dx);   /* über den Rand: nicht quer übers Feld gleiten */
          if (Math.abs(dy) > 1) dy = -Math.sign(dy);
          return [(alt[0] + dx * anteil + 0.5) * feld, (alt[1] + dy * anteil + 0.5) * feld];
        });
        /* Verbindung zwischen den Gliedern (nicht über den Rand hinweg, wo die Schlange gegenüber wieder reinkommt) */
        g.strokeStyle = "#3fcf86"; g.lineCap = "round"; g.lineJoin = "round"; g.lineWidth = feld * 0.62;
        g.beginPath();
        punkte.forEach(([x, y], i) => {
          const [vx, vy] = punkte[i - 1] || [x, y];
          if (!i || Math.abs(vx - x) > feld * 1.5 || Math.abs(vy - y) > feld * 1.5) g.moveTo(x, y); else g.lineTo(x, y);
        });
        g.stroke();
        /* Körper als runde Kette - vom Schwanz zum Kopf, nach hinten dünner */
        for (let i = punkte.length - 1; i >= 0; i--) {
          const [x, y] = punkte[i], r = feld * (0.42 - Math.min(0.14, i * 0.01));
          if (hoch) { g.fillStyle = "rgba(0,0,0,.18)"; g.beginPath(); g.arc(x + 3, y + 4, r, 0, Math.PI * 2); g.fill(); }
          g.fillStyle = i === 0 ? "#7dffb8" : i % 2 ? "#3fcf86" : "#4fdd94";
          g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
        }
        /* Kopf: Augen in Laufrichtung */
        const [kx, ky] = punkte[0], [rx, ry] = s.richtung;
        for (const seite_ of [-1, 1]) {
          const ax = kx + rx * feld * 0.14 - ry * seite_ * feld * 0.17, ay = ky + ry * feld * 0.14 + rx * seite_ * feld * 0.17;
          g.fillStyle = "#fff"; g.beginPath(); g.arc(ax, ay, feld * 0.11, 0, Math.PI * 2); g.fill();
          g.fillStyle = "#1e2a4a"; g.beginPath(); g.arc(ax + rx * feld * 0.04, ay + ry * feld * 0.04, feld * 0.055, 0, Math.PI * 2); g.fill();
        }
        if (spiel.pausiert && !s.aus) {
          g.fillStyle = "rgba(0,0,0,.5)";
          g.fillRect(0, 0, feld * SPALTEN, feld * ZEILEN);
          g.fillStyle = "#fff";
          g.font = `700 ${feld}px system-ui`;
          g.textAlign = "center";
          g.fillText("Pause", (feld * SPALTEN) / 2, (feld * ZEILEN) / 2);
        }
      }

      function verloren() {
        s.aus = true;
        spiel.stopp();
        ton("verloren");
        api.sende("/api/erfolg", { art: "snake", wert: s.punkte }).catch(() => {});
        const neuerRekord = s.punkte > rekord;
        if (neuerRekord) { rekord = s.punkte; localStorage.setItem("ff-snake-rekord", rekord); konfetti(box); }
        hilfe.textContent = "OK Nochmal · STOP Zurück";
        const ende = el("div", { style: "text-align:center" },
          el("p", { class: "punkte", text: (neuerRekord ? "Neuer Rekord! " : "Vorbei! ") + s.punkte + " Punkte" }));
        inhalt.replaceChildren(ende);
        modus = menue(ende, [{ text: "Nochmal", aktion: () => starte(stufe) }, { text: "Andere Stufe", aktion: auswahl }]);
      }

      spiel = takt(1000 / s.stufe.felderProSek, logik, zeichne);
      spiel.s = s;
    }

    auswahl();
    return {
      taste(t) {
        if (modus) return modus.taste(t);
        if (!spiel) return false;
        if (t === "p" || t === "P" || t === " " || t === "Enter") { spiel.pausiert = !spiel.pausiert; return true; }
        const r = RICHTUNG[t];
        if (r) {
          const s = spiel.s;
          const letzte = s.puffer[s.puffer.length - 1] || s.richtung;
          if (r[0] !== -letzte[0] || r[1] !== -letzte[1]) { if (s.puffer.length < 2) s.puffer.push(r); }
          return true;
        }
        return false;
      },
      schliesse() { spiel?.stopp(); },
    };
  },
};
