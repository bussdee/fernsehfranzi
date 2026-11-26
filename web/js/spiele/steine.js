/* FernsehFranzi 6.8.2 (6.9.18 schöner) - Steine-Brecher (eigener Entwurf im bekannten Genre).
 *
 * ← → Schläger (Fernbedienung: jeder Druck ein Stück, Tastatur/Controller: gedrückt halten) · OK Ball abschießen ·
 * STOP zurück. Drei Level mit Bildern aus Steinen (Herz, Stern, Franzi), drei Bälle. 30 Bilder pro Sekunde (Pi 3).
 */
import { el, stufe } from "../gemeinsam.js";
import { kopf, ton, takt, canvasScharf, konfetti, menue } from "./kern.js";

/* Level als kleine Bilder: Buchstabe = Farbe, Punkt = leer */
const LEVEL = [
  { name: "❤️ Herz", bild: ["..rr...rr..", ".rrrr.rrrr.", "rrrrrrrrrrr", "rrrrrrrrrrr", ".rrrrrrrrr.", "..rrrrrrr..", "...rrrrr...", "....rrr...."] },
  { name: "⭐ Stern", bild: [".....g.....", "....ggg....", "ggggggggggg", ".ggggggggg.", "..ggggggg..", ".ggg...ggg.", "gg.......gg"] },
  { name: "📺 Franzi", bild: ["...a...b...", "oooooooooo.", "onnnnnnnno.", "onwnnnnwno.", "onnnnnnnno.", "onnwwwwnno.", "oooooooooo.", ".c......c.."] },
];
const FARBEN = { r: "#ff5c6c", g: "#ffd34d", o: "#ff7a59", n: "#1e2a4a", w: "#ffffff", a: "#ffd54f", b: "#7fdcaa", c: "#c94f35" };

export default {
  symbol: "🧱",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "🧱 Steine-Brecher", "← → Schläger · OK abschießen · STOP zurück");
    let spiel = null, auswahl = null;
    const losgelassen = (e) => spiel?.los(e.key);
    window.addEventListener("keyup", losgelassen);

    function menueZeigen(text = "Welches Level?") {
      spiel?.stopp(); spiel = null;
      punkte.textContent = "";
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text }));
      inhalt.replaceChildren(spalte);
      auswahl = menue(spalte, LEVEL.map((l, i) => ({ text: l.name, aktion: () => starte(i) })));
    }

    function starte(nr) {
      auswahl = null;
      const B = Math.min(1000, Math.round(innerWidth * 0.7)), H = Math.round(B * 0.62);
      const canvas = el("canvas", { class: "spielfeld" });
      inhalt.replaceChildren(canvas);
      const g = canvasScharf(canvas, B, H);
      const bild = LEVEL[nr].bild, spalten = bild[0].length;
      const sb = (B - 40) / spalten, sh = 26;
      const steine = [];
      bild.forEach((zeile, y) => [...zeile].forEach((c, x) => {
        if (c !== ".") steine.push({ x: 20 + x * sb, y: 50 + y * (sh + 4), farbe: FARBEN[c] });
      }));
      const z = { sx: B / 2, richtung: 0, bx: 0, by: 0, vx: 0, vy: 0, klebt: true, baelle: 3, punkte: 0, spur: [], splitter: [], wackeln: 0 };
      /* 6.9.18: Hintergrund und Steine einmal vorzeichnen */
      const hoch = stufe() === "hoch";
      const grund = document.createElement("canvas"); grund.width = B; grund.height = H;
      { const h = grund.getContext("2d");
        const v = h.createLinearGradient(0, 0, 0, H); v.addColorStop(0, "#16224a"); v.addColorStop(1, "#0c1226");
        h.fillStyle = v; h.fillRect(0, 0, B, H);
        h.strokeStyle = "rgba(127,168,255,.06)"; h.lineWidth = 1;
        for (let x = 0; x < B; x += 40) { h.beginPath(); h.moveTo(x, 0); h.lineTo(x, H); h.stroke(); }
        for (let y = 0; y < H; y += 40) { h.beginPath(); h.moveTo(0, y); h.lineTo(B, y); h.stroke(); }
        const vg = h.createRadialGradient(B / 2, H / 2, H * 0.2, B / 2, H / 2, B * 0.7);
        vg.addColorStop(0, "rgba(0,0,0,0)"); vg.addColorStop(1, "rgba(0,0,0,.45)"); h.fillStyle = vg; h.fillRect(0, 0, B, H); }
      const steinBild = {};
      for (const farbe of new Set(steine.map((st) => st.farbe))) {
        const c = document.createElement("canvas"); c.width = Math.ceil(sb - 4); c.height = sh;
        const h = c.getContext("2d");
        const v = h.createLinearGradient(0, 0, 0, sh); v.addColorStop(0, farbe); v.addColorStop(1, "rgba(0,0,0,.25)");
        h.fillStyle = farbe; h.beginPath(); h.roundRect(0, 0, c.width, sh, 6); h.fill();
        h.fillStyle = v; h.globalAlpha = 0.5; h.fill(); h.globalAlpha = 1;
        h.fillStyle = "rgba(255,255,255,.35)"; h.beginPath(); h.roundRect(3, 2, c.width - 6, 6, 3); h.fill();
        h.strokeStyle = "rgba(255,255,255,.3)"; h.lineWidth = 1.5; h.beginPath(); h.roundRect(0.75, 0.75, c.width - 1.5, sh - 1.5, 6); h.stroke();
        steinBild[farbe] = c;
      }
      const SW = B * 0.16, SY = H - 30, R = 9;
      const zeigePunkte = () => { punkte.textContent = `${"⚪".repeat(z.baelle)} · ${z.punkte} Punkte · ${steine.length} Steine`; };
      zeigePunkte();
      function abschiessen() {
        if (!z.klebt) return;
        z.klebt = false; z.vx = (Math.random() < 0.5 ? -1 : 1) * 4.5; z.vy = -7;
      }
      function logik() {
        z.sx = Math.max(SW / 2, Math.min(B - SW / 2, z.sx + z.richtung * 14));
        for (const f of z.splitter) { f.x += f.vx; f.y += f.vy; f.vy += 0.3; f.leben--; }
        z.splitter = z.splitter.filter((f) => f.leben > 0);
        if (z.wackeln) z.wackeln--;
        if (z.klebt) { z.bx = z.sx; z.by = SY - R - 2; return; }
        z.bx += z.vx; z.by += z.vy;
        z.spur.push([z.bx, z.by]); if (z.spur.length > (hoch ? 12 : 4)) z.spur.shift();
        if (z.bx < R || z.bx > B - R) { z.vx *= -1; z.bx = Math.max(R, Math.min(B - R, z.bx)); }
        if (z.by < R) { z.vy = Math.abs(z.vy); }
        if (z.vy > 0 && z.by + R >= SY && z.by + R <= SY + 14 && Math.abs(z.bx - z.sx) < SW / 2 + R) {
          /* wo der Ball den Schläger trifft, bestimmt den Winkel */
          const t = (z.bx - z.sx) / (SW / 2);
          const tempo = Math.min(11, Math.hypot(z.vx, z.vy) + 0.15);
          z.vx = tempo * t * 0.8; z.vy = -Math.sqrt(Math.max(9, tempo * tempo - z.vx * z.vx));
          ton("anschlag");
        }
        for (let i = steine.length - 1; i >= 0; i--) {
          const s = steine[i];
          if (z.bx + R > s.x && z.bx - R < s.x + sb - 4 && z.by + R > s.y && z.by - R < s.y + sh) {
            const seitlich = Math.min(Math.abs(z.bx - s.x), Math.abs(z.bx - (s.x + sb - 4))) < Math.min(Math.abs(z.by - s.y), Math.abs(z.by - (s.y + sh)));
            if (seitlich) z.vx *= -1; else z.vy *= -1;
            for (let n = 0; n < (hoch ? 14 : 6); n++) {
              const w = Math.random() * Math.PI * 2, t = 1 + Math.random() * 4;
              z.splitter.push({ x: s.x + sb / 2, y: s.y + sh / 2, vx: Math.cos(w) * t, vy: Math.sin(w) * t, leben: 22, farbe: s.farbe });
            }
            steine.splice(i, 1); z.punkte += 10; ton("punkt", { faktor: 0.9 + Math.random() * 0.3 }); zeigePunkte();
            break;
          }
        }
        if (!steine.length) { ende(true); return; }
        if (z.by > H + 20) {
          z.baelle--; z.klebt = true; z.wackeln = 10; zeigePunkte();
          if (!z.baelle) ende(false);
        }
      }
      function zeichne() {
        g.save();
        if (z.wackeln) g.translate((Math.random() - 0.5) * z.wackeln, (Math.random() - 0.5) * z.wackeln);
        g.drawImage(grund, 0, 0, B, H);
        for (const st of steine) g.drawImage(steinBild[st.farbe], st.x, st.y);
        for (const f of z.splitter) { g.globalAlpha = f.leben / 22; g.fillStyle = f.farbe; g.fillRect(f.x - 3, f.y - 3, 6, 6); }
        g.globalAlpha = 1;
        /* Schläger: rund, mit Licht oben */
        const sv = g.createLinearGradient(0, SY, 0, SY + 14); sv.addColorStop(0, "#b7ceff"); sv.addColorStop(1, "#5b84e8");
        g.fillStyle = sv; g.beginPath(); g.roundRect(z.sx - SW / 2, SY, SW, 14, 7); g.fill();
        if (hoch) { g.fillStyle = "rgba(127,168,255,.18)"; g.beginPath(); g.roundRect(z.sx - SW / 2 - 6, SY - 4, SW + 12, 22, 11); g.fill(); }
        /* Ball mit Leuchtspur */
        z.spur.forEach(([x, y], n) => { g.globalAlpha = (n + 1) / (z.spur.length + 1) * 0.5; g.fillStyle = "#cfe0ff"; g.beginPath(); g.arc(x, y, R * (0.4 + n / z.spur.length * 0.5), 0, Math.PI * 2); g.fill(); });
        g.globalAlpha = 1;
        if (hoch) { const gl = g.createRadialGradient(z.bx, z.by, 0, z.bx, z.by, R * 3.2); gl.addColorStop(0, "rgba(255,255,255,.5)"); gl.addColorStop(1, "rgba(255,255,255,0)"); g.fillStyle = gl; g.fillRect(z.bx - R * 4, z.by - R * 4, R * 8, R * 8); }
        g.fillStyle = "#fff"; g.beginPath(); g.arc(z.bx, z.by, R, 0, Math.PI * 2); g.fill();
        if (z.klebt) { g.fillStyle = "rgba(255,255,255,.7)"; g.font = "20px sans-serif"; g.textAlign = "center"; g.fillText("OK = los!", B / 2, H * 0.62); z.spur.length = 0; }
        g.restore();
      }
      function ende(gewonnen) {
        steuer.stopp(); spiel = null;
        if (gewonnen) { ton("sieg"); konfetti(box); } else ton("verloren");
        setTimeout(() => menueZeigen(gewonnen ? `Geschafft! ${z.punkte} Punkte. Noch eins?` : `${z.punkte} Punkte – fast! Nochmal?`), 600);
      }
      const steuer = takt(1000 / 30, logik, zeichne);
      spiel = {
        stopp: () => steuer.stopp(),
        los(t) { if ((t === "ArrowLeft" && z.richtung < 0) || (t === "ArrowRight" && z.richtung > 0)) z.richtung = 0; },
        taste(t) {
          if (t === "ArrowLeft" || t === "ArrowRight") {
            const r = t === "ArrowLeft" ? -1 : 1;
            z.sx = Math.max(SW / 2, Math.min(B - SW / 2, z.sx + r * 40));    /* kurzer Druck (Fernbedienung) */
            z.richtung = r;
            return true;
          }
          if (t === "Enter" || t === " " || t === "ArrowUp") { abschiessen(); return true; }
          return t === "ArrowDown";
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
      schliesse() { spiel?.stopp(); window.removeEventListener("keyup", losgelassen); },
    };
  },
};
