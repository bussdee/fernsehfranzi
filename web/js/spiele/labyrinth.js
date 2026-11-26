/* FernsehFranzi 6.8.2 - 3D-Labyrinth (eigener Entwurf, Raycasting wie in alten Labyrinth-Spielen).
 *
 * Bewegung Feld für Feld, damit es auch mit kurzen Tastendrücken der Fernbedienung gut geht:
 * ↑ ein Feld vor · ↓ ein Feld zurück · ← → drehen · OK Karte an/aus · STOP zurück.
 * Ziel: den Schatz finden; unterwegs liegen Sterne. Jedes Labyrinth wird neu gebaut (drei Größen).
 * Gezeichnet wird in kleiner Auflösung (320 × 180) und vom Browser hochskaliert - so bleibt der Pi 3 flüssig.
 */
import { el, stufe } from "../gemeinsam.js";
import { kopf, ton, konfetti, menue } from "./kern.js";

const GROESSEN = [{ name: "🌱 Klein", n: 7 }, { name: "🌳 Mittel", n: 11 }, { name: "🏰 Groß", n: 15 }];
/* 6.9.19: Auflösung je Stufe - sparsam 320×180 (Pi 3), hoch 480×270 */
let RB = 320, RH = 180;
const RICHTUNG = [[1, 0], [0, 1], [-1, 0], [0, -1]];     /* Osten, Süden, Westen, Norden */

/** Labyrinth (ungerade Größe n): 1 = Wand, 0 = Gang. Tiefensuche mit Rücksprung. */
export function baue(n, zufall = Math.random) {
  const k = Array.from({ length: n }, () => Array(n).fill(1));
  const stapel = [[1, 1]];
  k[1][1] = 0;
  while (stapel.length) {
    const [x, y] = stapel[stapel.length - 1];
    const frei = [[2, 0], [-2, 0], [0, 2], [0, -2]].filter(([dx, dy]) => {
      const nx = x + dx, ny = y + dy;
      return nx > 0 && ny > 0 && nx < n - 1 && ny < n - 1 && k[ny][nx] === 1;
    });
    if (!frei.length) { stapel.pop(); continue; }
    const [dx, dy] = frei[Math.floor(zufall() * frei.length)];
    k[y + dy / 2][x + dx / 2] = 0; k[y + dy][x + dx] = 0;
    stapel.push([x + dx, y + dy]);
  }
  return k;
}

/** weitestes Feld vom Start (Breitensuche) - dort liegt der Schatz */
function weitestes(k) {
  const n = k.length, weit = Array.from({ length: n }, () => Array(n).fill(-1));
  const schlange = [[1, 1]]; weit[1][1] = 0;
  let best = [1, 1];
  while (schlange.length) {
    const [x, y] = schlange.shift();
    if (weit[y][x] > weit[best[1]][best[0]]) best = [x, y];
    for (const [dx, dy] of RICHTUNG) {
      if (k[y + dy][x + dx] === 0 && weit[y + dy][x + dx] < 0) { weit[y + dy][x + dx] = weit[y][x] + 1; schlange.push([x + dx, y + dy]); }
    }
  }
  return best;
}

export default {
  symbol: "🏰",
  oeffne(box, api) {
    /* 6.9.64: Ist Franzi da, versteckt sie sich ab und zu in einer Sackgasse - einmal am Tag gibt's dafür einen Stern */
    let versteck = { aktiv: false, stern: false };
    (api.hole ? api.hole("/api/franzi/versteck") : Promise.reject()).then((v) => { versteck = v || versteck; }).catch(() => {});
    const franziBild = new Image(); franziBild.src = "/bilder/franzi/versteck.png";
    const { inhalt, punkte, hilfe } = kopf(box, "🏰 3D-Labyrinth", "↑ vor · ↓ zurück · ← → drehen · OK Karte · STOP zurück");
    let spiel = null, auswahl = null;

    function menueZeigen(text = "Wie groß?") {
      spiel?.stopp(); spiel = null;
      punkte.textContent = "";
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text }));
      inhalt.replaceChildren(spalte);
      auswahl = menue(spalte, GROESSEN.map((gr) => ({ text: gr.name, aktion: () => starte(gr.n) })));
    }

    function starte(n) {
      auswahl = null;
      [RB, RH] = stufe() === "hoch" ? [480, 270] : [320, 180];
      const k = baue(n);
      const schatz = weitestes(k);
      const sterne = [];
      for (let i = 0; i < Math.floor(n / 2); i++) {
        const x = 1 + 2 * Math.floor(Math.random() * ((n - 1) / 2)), y = 1 + 2 * Math.floor(Math.random() * ((n - 1) / 2));
        if ((x !== 1 || y !== 1) && (x !== schatz[0] || y !== schatz[1]) && !sterne.some((s) => s.x === x && s.y === y)) sterne.push({ x, y });
      }
      /* Sackgassen: freies Feld mit genau einem offenen Nachbarn (nicht Start, nicht Schatz, kein Stern) */
      let franzi = null;
      if (versteck.aktiv && Math.random() < 0.6) {
        const gassen = [];
        for (let y = 1; y < n - 1; y += 2) for (let x = 1; x < n - 1; x += 2) {
          if (k[y][x] !== 0 || (x === 1 && y === 1) || (x === schatz[0] && y === schatz[1]) || sterne.some((s_) => s_.x === x && s_.y === y)) continue;
          if (RICHTUNG.filter(([dx, dy]) => k[y + dy][x + dx] === 0).length === 1) gassen.push({ x, y });
        }
        if (gassen.length) franzi = gassen[Math.floor(Math.random() * gassen.length)];
      }
      const canvas = el("canvas", { class: "spielfeld labyrinth-bild", width: RB, height: RH });
      const karte = el("canvas", { class: "labyrinth-karte", width: n * 8, height: n * 8 });
      inhalt.replaceChildren(el("div", { class: "labyrinth" }, canvas, karte));
      const g = canvas.getContext("2d"), gk = karte.getContext("2d");
      /* Himmel und Boden einmal vorzeichnen (Wolken, Nebel zum Horizont) */
      const grund = document.createElement("canvas"); grund.width = RB; grund.height = RH;
      { const h = grund.getContext("2d");
        const hi = h.createLinearGradient(0, 0, 0, RH / 2); hi.addColorStop(0, "#2a3d6b"); hi.addColorStop(1, "#8aa6d8");
        h.fillStyle = hi; h.fillRect(0, 0, RB, RH / 2);
        h.fillStyle = "rgba(255,255,255,.35)";
        for (let i = 0; i < 5; i++) { const x = (i * 0.23 + 0.05) * RB, y = RH * (0.08 + (i % 3) * 0.08);
          h.beginPath(); h.ellipse(x, y, RB * 0.06, RH * 0.025, 0, 0, Math.PI * 2); h.ellipse(x + RB * 0.03, y - RH * 0.015, RB * 0.04, RH * 0.025, 0, 0, Math.PI * 2); h.fill(); }
        const bo = h.createLinearGradient(0, RH / 2, 0, RH); bo.addColorStop(0, "#6f8f6a"); bo.addColorStop(0.25, "#4c7a4a"); bo.addColorStop(1, "#2f5a33");
        h.fillStyle = bo; h.fillRect(0, RH / 2, RB, RH / 2);
        h.fillStyle = "rgba(0,0,0,.08)";
        for (let y = RH / 2 + 4; y < RH; y += Math.max(2, (y - RH / 2) * 0.25)) h.fillRect(0, y, RB, 1); }
      const z = { x: 1.5, y: 1.5, w: 0, ziel: null, sterne: 0, schritte: 0, karteAn: true, gesehen: new Set(["1,1"]) };
      /* ersten Blick in einen Gang richten */
      z.richtung = RICHTUNG.findIndex(([dx, dy]) => k[1 + dy][1 + dx] === 0);
      z.w = z.richtung * Math.PI / 2;
      const zeigePunkte = () => { punkte.textContent = `⭐ ${z.sterne} / ${sterne.length + z.sterne} · 👣 ${z.schritte}`; };
      zeigePunkte();

      function zeichne() {
        g.drawImage(grund, 0, 0);
        const tiefe = new Float32Array(RB);
        for (let sx = 0; sx < RB; sx++) {
          const winkel = z.w + Math.atan((sx / RB - 0.5) * 1.2);
          const dx = Math.cos(winkel), dy = Math.sin(winkel);
          let mx = Math.floor(z.x), my = Math.floor(z.y);
          const schrittX = dx < 0 ? -1 : 1, schrittY = dy < 0 ? -1 : 1;
          const ddx = Math.abs(1 / dx), ddy = Math.abs(1 / dy);
          let seiteX = (dx < 0 ? z.x - mx : mx + 1 - z.x) * ddx, seiteY = (dy < 0 ? z.y - my : my + 1 - z.y) * ddy, seite = 0;
          for (let i = 0; i < 64; i++) {
            if (seiteX < seiteY) { seiteX += ddx; mx += schrittX; seite = 0; } else { seiteY += ddy; my += schrittY; seite = 1; }
            if (k[my]?.[mx] !== 0) break;
          }
          const abstand = (seite === 0 ? seiteX - ddx : seiteY - ddy) * Math.cos(winkel - z.w);
          tiefe[sx] = abstand;
          const h = Math.min(RH * 3, RH / Math.max(0.05, abstand));
          const hell = Math.max(0.25, 1 - abstand / 9) * (seite ? 0.8 : 1);
          /* Ziegel: wo die Wand getroffen wurde (0..1 entlang der Wand) - Fugen waagrecht und versetzt senkrecht */
          const roh = seite === 0 ? z.y + (seiteX - ddx) * dy : z.x + (seiteY - ddy) * dx;
          const stelle = roh - Math.floor(roh);
          const oben = (RH - h) / 2;
          g.fillStyle = `rgb(${Math.round(200 * hell)},${Math.round(150 * hell)},${Math.round(110 * hell)})`;
          g.fillRect(sx, oben, 1, h);
          if (h > 12) {
            g.fillStyle = `rgba(60,35,20,${(0.45 * hell).toFixed(2)})`;
            for (let r = 1; r < 6; r++) g.fillRect(sx, oben + h * r / 6, 1, Math.max(1, h / 60));
            for (let r = 0; r < 6; r++) {
              const versatz = (stelle + (r % 2) * 0.25) % 0.5;
              if (versatz < 0.02) g.fillRect(sx, oben + h * r / 6, 1, h / 6);
            }
            if (stelle < 0.015 || stelle > 0.985) { g.fillStyle = "rgba(0,0,0,.25)"; g.fillRect(sx, oben, 1, h); }
          }
        }
        /* Sterne und Schatz als Bildchen, wenn sichtbar (vor der Wand) */
        const dinge = sterne.map((s) => ({ ...s, art: "⭐" })).concat([{ x: schatz[0], y: schatz[1], art: "💰" }]);
        if (franzi) dinge.push({ ...franzi, art: "franzi" });
        for (const d of dinge) {
          const vx = d.x + 0.5 - z.x, vy = d.y + 0.5 - z.y;
          const ab = Math.hypot(vx, vy);
          let rel = Math.atan2(vy, vx) - z.w;
          rel = Math.atan2(Math.sin(rel), Math.cos(rel));
          if (Math.abs(rel) > 0.65 || ab < 0.3) continue;
          const sx = Math.round((Math.tan(rel) / 1.2 + 0.5) * RB);
          if (sx < 0 || sx >= RB || tiefe[sx] < ab * Math.cos(rel) - 0.3) continue;
          const groesse = Math.min(90, RH * 0.45 / ab);
          g.font = `${Math.round(groesse)}px "FF Emoji", sans-serif`;   /* das Gerät hat nur die eigene Emoji-Schrift */ g.textAlign = "center"; g.textBaseline = "middle";
          if (d.art === "franzi") {                                       /* 6.9.64: Franzi lugt aus der Sackgasse */
            if (franziBild.complete && franziBild.naturalWidth) g.drawImage(franziBild, sx - groesse * 0.9, RH / 2 - groesse * 0.75, groesse * 1.8, groesse * 1.8);
            continue;
          }
          g.fillText(d.art, sx, RH / 2 + groesse * 0.4);
        }
        /* Karte: nur was schon gesehen wurde */
        karte.hidden = !z.karteAn;
        if (z.karteAn) {
          gk.clearRect(0, 0, karte.width, karte.height);
          for (const f of z.gesehen) {
            const [x, y] = f.split(",").map(Number);
            for (const [dx, dy] of [[0, 0], ...RICHTUNG]) {
              gk.fillStyle = k[y + dy]?.[x + dx] === 0 ? "rgba(255,255,255,.55)" : "rgba(120,80,50,.9)";
              gk.fillRect((x + dx) * 8, (y + dy) * 8, 8, 8);
            }
          }
          gk.fillStyle = "#ffd34d"; gk.beginPath(); gk.arc(z.x * 8, z.y * 8, 3.5, 0, Math.PI * 2); gk.fill();
          gk.strokeStyle = "#ffd34d"; gk.lineWidth = 2;
          gk.beginPath(); gk.moveTo(z.x * 8, z.y * 8); gk.lineTo(z.x * 8 + Math.cos(z.w) * 8, z.y * 8 + Math.sin(z.w) * 8); gk.stroke();
        }
      }

      /* weich gleiten (wenige Bilder, nur während der Bewegung) */
      let anim = 0;
      function gleite(ziel) {
        cancelAnimationFrame(anim);
        const start = { x: z.x, y: z.y, w: z.w }, t0 = performance.now(), dauer = 220;
        const schritt = (jetzt) => {
          const p = Math.min(1, (jetzt - t0) / dauer);
          z.x = start.x + (ziel.x - start.x) * p; z.y = start.y + (ziel.y - start.y) * p; z.w = start.w + (ziel.w - start.w) * p;
          zeichne();
          if (p < 1) anim = requestAnimationFrame(schritt); else { z.w = ((ziel.w % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI); angekommen(); }
        };
        anim = requestAnimationFrame(schritt);
      }
      function angekommen() {
        const fx = Math.floor(z.x), fy = Math.floor(z.y);
        z.gesehen.add(`${fx},${fy}`);
        const i = sterne.findIndex((s) => s.x === fx && s.y === fy);
        if (i >= 0) { sterne.splice(i, 1); z.sterne++; ton("punkt"); }
        if (franzi && fx === franzi.x && fy === franzi.y) {
          franzi = null;
          ton("sieg"); konfetti(box);
          api.sende("/api/franzi/versteck", {}).then((r) => api.hinweis?.(r?.stern ? "🎉 Du hast Franzi gefunden – ein Bonusstern für dich! ⭐" : "🎉 Du hast Franzi gefunden!"))
            .catch(() => api.hinweis?.("🎉 Du hast Franzi gefunden!"));
        }
        zeigePunkte();
        zeichne();
        if (fx === schatz[0] && fy === schatz[1]) {
          ton("sieg"); konfetti(box);
          setTimeout(() => menueZeigen(`💰 Schatz gefunden – in ${z.schritte} Schritten mit ${z.sterne} Sternen! Noch eins?`), 900);
          spiel = null;
        }
      }
      function gehen(r) {
        const [dx, dy] = RICHTUNG[(z.richtung + (r < 0 ? 2 : 0)) % 4];
        const fx = Math.floor(z.x) + dx, fy = Math.floor(z.y) + dy;
        if (k[fy]?.[fx] !== 0) { ton("anschlag"); return; }
        z.schritte++;
        gleite({ x: fx + 0.5, y: fy + 0.5, w: z.w });
      }
      function drehen(r) {
        z.richtung = (z.richtung + r + 4) % 4;
        gleite({ x: z.x, y: z.y, w: z.w + r * Math.PI / 2 });
      }
      zeichne();
      spiel = {
        stopp() { cancelAnimationFrame(anim); },
        taste(t) {
          if (t === "ArrowUp") gehen(1);
          else if (t === "ArrowDown") gehen(-1);
          else if (t === "ArrowLeft") drehen(-1);
          else if (t === "ArrowRight") drehen(1);
          else if (t === "Enter" || t === " ") { z.karteAn = !z.karteAn; zeichne(); }
          return true;
        },
      };
    }

    menueZeigen();
    return {
      taste(t) {
        if (t === "Escape" || t === "Backspace") { if (spiel) { menueZeigen(); return true; } return false; }
        if (spiel) return spiel.taste(t);
        return auswahl ? auswahl.taste(t) : true;
      },
      schliesse() { spiel?.stopp(); },
    };
  },
};
