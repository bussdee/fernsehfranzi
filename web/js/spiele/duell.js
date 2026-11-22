/* Zu zweit (3.1): Spiele für zwei Controller (oder Fernbedienung + Controller). Eigene Entwürfe.
 *   Spieler 1: Pfeile + OK (Fernbedienung, Tastatur oder erster Controller)
 *   Spieler 2: zweiter Controller (eingabe.py: Steuerkreuz -> W A S D, A -> F) oder Tastatur W A S D + F
 *   Ballduell   zwei Schläger, ein Ball - wer zuerst 7 Punkte hat
 *   Snake-Duell zwei Schlangen, wer länger überlebt
 *   Quiz-Duell  Frage erscheint, wer zuerst drückt, darf antworten
 *   Sternen-Abwehr (4.0) gemeinsam (oder allein): zwei Raumschiffe unten, Wellen von Außerirdischen kommen näher
 */
import { el } from "../gemeinsam.js";
import { kopf, takt, ton, canvasScharf, menue, konfetti } from "./kern.js";

const P2 = { w: "ArrowUp", s: "ArrowDown", a: "ArrowLeft", d: "ArrowRight", f: "Enter",
             W: "ArrowUp", S: "ArrowDown", A: "ArrowLeft", D: "ArrowRight", F: "Enter" };

const FRAGEN = [
  ["Wie viele Beine hat eine Spinne?", ["8", "6", "10"]],
  ["Welche Farbe entsteht aus Blau und Gelb?", ["Grün", "Lila", "Orange"]],
  ["Wie viele Saiten hat ein normaler E-Bass?", ["4", "6", "5"]],
  ["Was ist 7 × 8?", ["56", "54", "64"]],
  ["Welcher Planet ist der Sonne am nächsten?", ["Merkur", "Venus", "Mars"]],
  ["Wie heißt das größte Säugetier?", ["Blauwal", "Elefant", "Giraffe"]],
  ["Wie viele Minuten hat eine Stunde?", ["60", "100", "30"]],
  ["Welches Tier legt Eier?", ["Huhn", "Hund", "Katze"]],
  ["Welche Note liegt zwischen C und E?", ["D", "F", "H"]],
  ["Wie viele Tage hat ein Schaltjahr?", ["366", "365", "364"]],
  ["Was ist die Hauptstadt von Österreich?", ["Wien", "Graz", "Salzburg"]],
  ["Welches Instrument hat Tasten?", ["Klavier", "Geige", "Trommel"]],
  ["Was ist 100 − 37?", ["63", "73", "67"]],
  ["Wie viele Kontinente gibt es?", ["7", "5", "9"]],
  ["Was trinkt ein Kälbchen?", ["Milch", "Saft", "Tee"]],
  ["Welches Tier kann am schnellsten laufen?", ["Gepard", "Pferd", "Hase"]],
  ["Was ist gefrorenes Wasser?", ["Eis", "Dampf", "Nebel"]],
  ["Wie viele Ecken hat ein Würfel?", ["8", "6", "12"]],
  ["Welche Jahreszeit kommt nach dem Winter?", ["Frühling", "Sommer", "Herbst"]],
  ["Was ist 9 + 9 + 9?", ["27", "24", "29"]],
];

function erfolg(api, art, wert) { api.sende("/api/erfolg", { art, wert }).catch(() => {}); }

export default {
  symbol: "🤝",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "Zu zweit", "Spieler 1: Pfeile + OK · Spieler 2: zweiter Controller (oder W A S D + F)");
    let modus = null, spiel = null;

    function auswahl() {
      spiel?.stopp?.();
      spiel = null;
      punkte.textContent = "";
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text: "Was spielt ihr?" }));
      inhalt.replaceChildren(spalte);
      modus = menue(spalte, [{ text: "🏓 Ballduell", aktion: ballduell }, { text: "🐍 Snake-Duell", aktion: snakeDuell },
                             { text: "❓ Quiz-Duell", aktion: quizDuell }, { text: "👾 Sternen-Abwehr", aktion: sternenAbwehr }]);
    }

    function sieger(text, gewinner) {
      spiel?.stopp?.();
      spiel = null;
      ton("sieg");
      konfetti(box);
      if (gewinner) erfolg(api, "duell", 1);
      const ende = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text }));
      inhalt.replaceChildren(ende);
      modus = menue(ende, [{ text: "Nochmal", aktion: spiel_neu }, { text: "Anderes Spiel", aktion: auswahl }]);
    }
    let spiel_neu = auswahl;

    /* ---------------------------------------------------- Ballduell */
    function ballduell() {
      spiel_neu = ballduell;
      modus = null;
      const b = Math.floor(innerWidth * 0.85), h = Math.floor(innerHeight * 0.7);
      const canvas = el("canvas", { class: "spielfeld" });
      inhalt.replaceChildren(canvas);
      const g = canvasScharf(canvas, b, h);
      const sh = h * 0.2, sb = 16;
      const s = { y1: h / 2, y2: h / 2, v1: 0, v2: 0, bx: b / 2, by: h / 2, vx: b / 160, vy: h / 220, p1: 0, p2: 0 };
      const runde = (richtung) => { Object.assign(s, { bx: b / 2, by: h / 2, vx: richtung * b / 160, vy: (Math.random() - 0.5) * h / 110 }); };
      punkte.textContent = "0 : 0";
      spiel = takt(1000 / 60, () => {
        s.y1 = Math.max(sh / 2, Math.min(h - sh / 2, s.y1 + s.v1));
        s.y2 = Math.max(sh / 2, Math.min(h - sh / 2, s.y2 + s.v2));
        s.bx += s.vx; s.by += s.vy;
        if (s.by < 8 || s.by > h - 8) s.vy *= -1;
        const trifft = (x, y) => Math.abs(s.bx - x) < sb && Math.abs(s.by - y) < sh / 2 + 8;
        if (s.vx < 0 && trifft(30, s.y1)) { s.vx = Math.abs(s.vx) * 1.05; s.vy += (s.by - s.y1) / sh * 4; ton("bewegen"); }
        if (s.vx > 0 && trifft(b - 30, s.y2)) { s.vx = -Math.abs(s.vx) * 1.05; s.vy += (s.by - s.y2) / sh * 4; ton("bewegen"); }
        if (s.bx < 0 || s.bx > b) {
          if (s.bx < 0) s.p2++; else s.p1++;
          ton("punkt");
          punkte.textContent = `${s.p1} : ${s.p2}`;
          if (s.p1 >= 7 || s.p2 >= 7) return sieger(`Spieler ${s.p1 > s.p2 ? 1 : 2} gewinnt ${Math.max(s.p1, s.p2)} : ${Math.min(s.p1, s.p2)}!`, true);
          runde(s.bx < 0 ? 1 : -1);
        }
      }, () => {
        g.fillStyle = "#0e1522"; g.fillRect(0, 0, b, h);
        g.fillStyle = "#2a3550"; for (let y = 0; y < h; y += 30) g.fillRect(b / 2 - 2, y, 4, 16);
        g.fillStyle = "#7dffb8"; g.fillRect(30 - sb / 2, s.y1 - sh / 2, sb, sh);
        g.fillStyle = "#7fa8ff"; g.fillRect(b - 30 - sb / 2, s.y2 - sh / 2, sb, sh);
        g.fillStyle = "#fff"; g.beginPath(); g.arc(s.bx, s.by, 9, 0, 7); g.fill();
      });
      const tempo = h / 70;
      spiel.taste = (t, los) => {
        const v = los ? 0 : tempo;
        if (t === "ArrowUp") s.v1 = -v; else if (t === "ArrowDown") s.v1 = v;
        else if (P2[t] === "ArrowUp") s.v2 = -v; else if (P2[t] === "ArrowDown") s.v2 = v;
        else return false;
        if (!los) setTimeout(() => { if (t === "ArrowUp" || t === "ArrowDown") s.v1 = 0; else s.v2 = 0; }, 180);
        return true;
      };
    }

    /* ---------------------------------------------------- Sternen-Abwehr (4.0, gemeinsam) */
    function sternenAbwehr() {
      spiel_neu = sternenAbwehr;
      modus = null;
      const b = Math.floor(innerWidth * 0.85), h = Math.floor(innerHeight * 0.72);
      const canvas = el("canvas", { class: "spielfeld" });
      inhalt.replaceChildren(canvas);
      const g = canvasScharf(canvas, b, h);
      const schiffe = [{ x: b * 0.35, farbe: "#7dffb8", nachladen: 0 }, { x: b * 0.65, farbe: "#7fa8ff", nachladen: 0 }];
      const s = { welle: 0, punkte: 0, leben: 3, schuesse: [], bomben: [], feinde: [], richtung: 1, tempo: 0, getroffen: 0 };
      const sterne = Array.from({ length: 60 }, () => [Math.random() * b, Math.random() * h, Math.random() * 1.5 + 0.5]);
      const neueWelle = () => {
        s.welle++;
        s.feinde = [];
        const spalten = 8, reihen = 3 + Math.min(2, Math.floor(s.welle / 2));
        for (let r = 0; r < reihen; r++) for (let c = 0; c < spalten; c++) {
          s.feinde.push({ x: b * 0.15 + c * b * 0.09, y: h * 0.08 + r * h * 0.08, art: r % 3 });
        }
        s.richtung = 1;
        s.tempo = b / 900 * (1 + s.welle * 0.25);
        api.hinweis(`Welle ${s.welle}!`);
      };
      neueWelle();
      const anzeige = () => { punkte.textContent = `⭐ ${s.punkte} · ❤️ ${s.leben} · Welle ${s.welle}`; };
      anzeige();
      const schiessen = (n) => {
        const sch = schiffe[n];
        if (sch.nachladen > 0) return;
        sch.nachladen = 18;
        s.schuesse.push({ x: sch.x, y: h - 40, spieler: n });
        ton("bewegen");
      };
      spiel = takt(1000 / 60, () => {
        for (const sch of schiffe) sch.nachladen = Math.max(0, sch.nachladen - 1);
        /* Feinde wandern, am Rand eine Reihe tiefer */
        let rand = false;
        for (const f of s.feinde) { f.x += s.richtung * s.tempo; if (f.x < 20 || f.x > b - 20) rand = true; }
        if (rand) { s.richtung *= -1; for (const f of s.feinde) f.y += h * 0.035; }
        /* Bomben der Feinde */
        if (s.feinde.length && Math.random() < 0.012 + s.welle * 0.003) {
          const f = s.feinde[Math.floor(Math.random() * s.feinde.length)];
          s.bomben.push({ x: f.x, y: f.y + 10 });
        }
        for (const sc of s.schuesse) sc.y -= h / 60;
        for (const bo of s.bomben) bo.y += h / 160;
        /* Treffer */
        for (const sc of s.schuesse) {
          const i = s.feinde.findIndex((f) => Math.abs(f.x - sc.x) < 22 && Math.abs(f.y - sc.y) < 16);
          if (i >= 0) { s.feinde.splice(i, 1); sc.weg = true; s.punkte += 10; ton("punkt"); anzeige(); }
        }
        for (const bo of s.bomben) {
          for (const sch of schiffe) {
            if (Math.abs(bo.x - sch.x) < 26 && bo.y > h - 46 && bo.y < h - 10 && !bo.weg) {
              bo.weg = true; s.leben--; s.getroffen = 30; ton("fehler"); anzeige();
            }
          }
        }
        s.schuesse = s.schuesse.filter((x) => !x.weg && x.y > 0);
        s.bomben = s.bomben.filter((x) => !x.weg && x.y < h);
        s.getroffen = Math.max(0, s.getroffen - 1);
        if (s.leben <= 0 || s.feinde.some((f) => f.y > h - 70)) {
          if (s.punkte >= 300) erfolg(api, "duell", 1);
          return sieger(`Geschafft bis Welle ${s.welle} – ${s.punkte} Punkte!`, s.punkte >= 300);
        }
        if (!s.feinde.length) { s.punkte += 50; ton("sieg"); anzeige(); neueWelle(); }
      }, () => {
        g.fillStyle = s.getroffen ? "#2a0e14" : "#05070f"; g.fillRect(0, 0, b, h);
        g.fillStyle = "#cfd8ff";
        for (const [x, y, r] of sterne) g.fillRect(x, y, r, r);
        const farben = ["#ff7eb6", "#ffd23f", "#7fd4ff"];
        for (const f of s.feinde) {
          g.fillStyle = farben[f.art];
          g.beginPath(); g.ellipse(f.x, f.y, 18, 11, 0, 0, 7); g.fill();
          g.fillStyle = "#05070f"; g.fillRect(f.x - 9, f.y - 3, 5, 5); g.fillRect(f.x + 4, f.y - 3, 5, 5);
          g.fillStyle = farben[f.art]; g.fillRect(f.x - 16, f.y + 8, 4, 6); g.fillRect(f.x + 12, f.y + 8, 4, 6);
        }
        for (const [n, sch] of schiffe.entries()) {
          g.fillStyle = sch.farbe;
          g.beginPath(); g.moveTo(sch.x, h - 44); g.lineTo(sch.x - 22, h - 14); g.lineTo(sch.x + 22, h - 14); g.closePath(); g.fill();
          g.fillStyle = "#05070f"; g.font = "bold 12px sans-serif"; g.textAlign = "center"; g.fillText(String(n + 1), sch.x, h - 20);
        }
        g.fillStyle = "#fff"; for (const sc of s.schuesse) g.fillRect(sc.x - 2, sc.y - 10, 4, 12);
        g.fillStyle = "#ff6b6b"; for (const bo of s.bomben) g.fillRect(bo.x - 3, bo.y - 6, 6, 10);
      });
      const schritt = b / 40;
      spiel.taste = (t) => {
        if (t === "ArrowLeft" || t === "ArrowRight") { const sch = schiffe[0]; sch.x = Math.max(24, Math.min(b - 24, sch.x + (t === "ArrowLeft" ? -schritt : schritt))); return true; }
        if (P2[t] === "ArrowLeft" || P2[t] === "ArrowRight") { const sch = schiffe[1]; sch.x = Math.max(24, Math.min(b - 24, sch.x + (P2[t] === "ArrowLeft" ? -schritt : schritt))); return true; }
        if (t === "Enter" || t === " " || t === "ArrowUp") { schiessen(0); return true; }
        if (P2[t] === "Enter" || P2[t] === "ArrowUp") { schiessen(1); return true; }
        return false;
      };
    }

    /* ---------------------------------------------------- Snake-Duell */
    function snakeDuell() {
      spiel_neu = snakeDuell;
      modus = null;
      const sp = 28, ze = 16;
      const feld = Math.floor(Math.min((innerWidth * 0.9) / sp, (innerHeight * 0.72) / ze));
      const canvas = el("canvas", { class: "spielfeld" });
      inhalt.replaceChildren(canvas);
      const g = canvasScharf(canvas, feld * sp, feld * ze);
      const s = {
        a: { k: [[5, 8], [4, 8], [3, 8]], r: [1, 0], neu: null, farbe: "#7dffb8" },
        b: { k: [[22, 8], [23, 8], [24, 8]], r: [-1, 0], neu: null, farbe: "#7fa8ff" },
      };
      punkte.textContent = "Grün: Spieler 1 · Blau: Spieler 2";
      const belegt = (x, y) => [s.a, s.b].some((sch) => sch.k.some(([a, b]) => a === x && b === y));
      spiel = takt(1000 / 6, () => {
        const koepfe = {};
        for (const [n, sch] of Object.entries(s)) {
          if (sch.neu) { sch.r = sch.neu; sch.neu = null; }
          const [x, y] = sch.k[0];
          koepfe[n] = [x + sch.r[0], y + sch.r[1]];
        }
        const raus = (p) => p[0] < 0 || p[1] < 0 || p[0] >= sp || p[1] >= ze || belegt(p[0], p[1]);
        const aRaus = raus(koepfe.a) || (koepfe.a[0] === koepfe.b[0] && koepfe.a[1] === koepfe.b[1]);
        const bRaus = raus(koepfe.b) || (koepfe.a[0] === koepfe.b[0] && koepfe.a[1] === koepfe.b[1]);
        if (aRaus || bRaus) {
          return sieger(aRaus && bRaus ? "Unentschieden!" : `Spieler ${aRaus ? 2 : 1} gewinnt!`, !(aRaus && bRaus));
        }
        s.a.k.unshift(koepfe.a);
        s.b.k.unshift(koepfe.b);     /* Schlangen wachsen ständig - wer zuerst anstößt, verliert */
      }, () => {
        g.fillStyle = "#0e1522"; g.fillRect(0, 0, feld * sp, feld * ze);
        for (const sch of [s.a, s.b]) {
          g.fillStyle = sch.farbe;
          for (const [x, y] of sch.k) g.fillRect(x * feld + 1, y * feld + 1, feld - 2, feld - 2);
        }
      });
      const lenke = (sch, r) => { const alt = sch.neu || sch.r; if (r[0] !== -alt[0] || r[1] !== -alt[1]) sch.neu = r; };
      const R = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] };
      spiel.taste = (t) => {
        if (R[t]) { lenke(s.a, R[t]); return true; }
        if (P2[t] && R[P2[t]]) { lenke(s.b, R[P2[t]]); return true; }
        return false;
      };
    }

    /* ---------------------------------------------------- Quiz-Duell */
    function quizDuell() {
      spiel_neu = quizDuell;
      modus = null;
      const fragen = FRAGEN.slice().sort(() => Math.random() - 0.5).slice(0, 10);
      const stand = [0, 0];
      let nr = 0, dran = 0, antworten = [], richtig = "", pos = 0;
      const text = el("div", { class: "witz" });
      const wahl = el("div", { class: "knopfreihe", style: "margin-top:4vh" });
      const info = el("p", { class: "leise", style: "text-align:center" });
      inhalt.replaceChildren(el("div", { style: "text-align:center" }, text, wahl, info));
      const neue = () => {
        if (nr >= fragen.length) {
          const [a, b] = stand;
          return sieger(a === b ? `Unentschieden – ${a} : ${b}!` : `Spieler ${a > b ? 1 : 2} gewinnt ${Math.max(a, b)} : ${Math.min(a, b)}!`, a !== b);
        }
        const [frage, liste] = fragen[nr];
        richtig = liste[0];
        antworten = liste.slice().sort(() => Math.random() - 0.5);
        dran = 0;
        pos = 0;
        text.textContent = `Frage ${nr + 1}: ${frage}`;
        wahl.replaceChildren();
        info.textContent = "Wer weiß es? Spieler 1: OK · Spieler 2: F (oder A am zweiten Controller)";
        punkte.textContent = `Spieler 1: ${stand[0]} · Spieler 2: ${stand[1]}`;
      };
      const zeige = () => wahl.replaceChildren(...antworten.map((a, i) => el("span", { class: "knopf" + (i === pos ? " gewaehlt" : ""), text: a })));
      neue();
      spiel = { stopp() {}, taste(t) {
        if (t === "Escape" || t === "Backspace") return false;      /* STOP schließt (vorher blieb das Quiz hängen) */
        const zweiter = Boolean(P2[t]);
        const t1 = zweiter ? P2[t] : t;
        if (!dran) {
          if (t1 === "Enter") { dran = zweiter ? 2 : 1; info.textContent = `Spieler ${dran} antwortet: ← → wählen, OK bestätigen`; ton("ok"); zeige(); }
          return true;
        }
        if ((dran === 2) !== zweiter) return true;     /* nur wer gedrückt hat, darf antworten */
        if (t1 === "ArrowLeft" || t1 === "ArrowRight") { pos = (pos + (t1 === "ArrowLeft" ? antworten.length - 1 : 1)) % antworten.length; zeige(); return true; }
        if (t1 === "Enter") {
          if (antworten[pos] === richtig) { stand[dran - 1]++; ton("sieg"); api.hinweis(`Richtig, Spieler ${dran}!`); }
          else { stand[2 - dran]++; ton("fehler"); api.hinweis(`Leider falsch – richtig ist ${richtig}. Punkt für Spieler ${3 - dran}.`); }
          nr++;
          setTimeout(neue, 1200);
          dran = -1;
          return true;
        }
        return true;
      } };
    }

    auswahl();
    return {
      taste(t) {
        if (modus) return modus.taste(t);
        if (spiel?.taste) return spiel.taste(t) || false;
        return false;
      },
      schliesse() { spiel?.stopp?.(); },
    };
  },
};
