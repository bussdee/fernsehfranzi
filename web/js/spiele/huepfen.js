/* FernsehFranzi 6.8.4 (6.9.17 schöner) - „Franzi hüpft“: ein Jump'n'Run (eigener Entwurf im bekannten Genre).
 *
 * Steuerung passend zur Fernbedienung (kurze Tastendrücke): → einmal = Franzi läuft nach rechts, bis man ← drückt
 * (← hält an, nochmal ← läuft nach links) · OK oder ↑ springt · STOP zurück.
 * Sterne sammeln, über Lücken springen, Schnecken von oben plattdrücken (seitlich berührt: zurück zum letzten Fähnchen),
 * am Ende wartet die Zielflagge. Drei Level als kleine Textbilder. 30 Bilder pro Sekunde, nur sichtbare Kacheln (Pi 3).
 */
import { el, stufe } from "../gemeinsam.js";
import { kopf, ton, takt, canvasScharf, konfetti, menue } from "./kern.js";

/* # Boden · = Block · * Stern · s Schnecke · f Fähnchen (Zwischenstand) · Z Ziel · Leerzeichen = Luft */
const LEVEL = [
  { name: "🌳 Wiese", himmel: ["#8fd3ff", "#e6f7ff"], boden: "#5bbf6a", block: "#c98a4b", karte: [
    "                                                                ",
    "                                                                ",
    "            * *                    * * *                        ",
    "           =====      *           =======                       ",
    "    *  *             ===                         * *          Z ",
    "   ======    s   f            s         f    s  =====      s  # ",
    "###################   ##########   ###################   #######",
    "###################   ##########   ###################   #######"] },
  { name: "🪨 Höhle", himmel: ["#2b2140", "#54406e"], boden: "#7a6a8a", block: "#a08cb8", karte: [
    "################################################################",
    "                                                                ",
    "            * * *                    *   *            * * * *   ",
    "           =======      =====       =======          =======    ",
    "     *                          s               f             Z ",
    "    ===    s      f   ===   ========    s   ===     s    ===  # ",
    "#############  ########   ############ ####### ###############  ",
    "#############  ########   ############ ####### ###############  "] },
  { name: "☁️ Wolken", himmel: ["#ffb6d9", "#fff0f8"], boden: "#ffffff", block: "#ffd6ec", karte: [
    "                                                                ",
    "                            * *                    * * *        ",
    "                  * *      =====        *  *       =====    *Z  ",
    "         * *     =====              s  ======  f         =====  ",
    "        =====                   =====               ====        ",
    "   f                  f   ===                ===                ",
    "#######   ######   #####   #####   ####   #####   ####          ",
    "#######   ######   #####   #####   ####   #####   ####          "] },
];
const T = 40;                       /* Kachelgröße */

/** 6.9.17: Hintergrund-Ebenen und Kacheln einmal vorzeichnen (je Level) - je Bild nur drawImage */
function vorzeichnen(L, B, H, hoch) {
  const leinwand = (b, h) => { const c = document.createElement("canvas"); c.width = b; c.height = h; return [c, c.getContext("2d")]; };
  const [himmel, h1] = leinwand(B, H);
  const v = h1.createLinearGradient(0, 0, 0, H);
  v.addColorStop(0, L.himmel[0]); v.addColorStop(1, L.himmel[1]);
  h1.fillStyle = v; h1.fillRect(0, 0, B, H);
  const art = L.name.includes("Höhle") ? "hoehle" : L.name.includes("Wolken") ? "wolken" : "wiese";
  const ebene = (farbe, hoehe, wellen, extra) => {
    const [c, e] = leinwand(B, H);
    e.fillStyle = farbe; e.beginPath(); e.moveTo(0, H);
    for (let x = 0; x <= B; x += 10) e.lineTo(x, H * hoehe + Math.sin(x / B * Math.PI * 2 * wellen) * H * 0.06);
    e.lineTo(B, H); e.fill();
    extra?.(e);
    return c;
  };
  const wolke = (e, x, y, s, farbe) => { e.fillStyle = farbe; e.beginPath(); e.ellipse(x, y, 40 * s, 16 * s, 0, 0, Math.PI * 2);
    e.arc(x - 16 * s, y - 8 * s, 16 * s, 0, Math.PI * 2); e.arc(x + 12 * s, y - 12 * s, 20 * s, 0, Math.PI * 2); e.fill(); };
  let fern, nah, schweber;
  if (art === "hoehle") {
    fern = ebene("rgba(40,30,70,.7)", 0.7, 3, (e) => { e.fillStyle = "rgba(160,140,220,.35)";
      for (let i = 0; i < 9; i++) { const x = i * B / 9 + 20; e.beginPath(); e.moveTo(x, 0); e.lineTo(x + 14, 40 + (i % 3) * 30); e.lineTo(x + 28, 0); e.fill(); } });
    nah = ebene("rgba(70,50,110,.6)", 0.8, 2, (e) => { for (let i = 0; i < 6; i++) { e.fillStyle = i % 2 ? "#7fe0ff" : "#c79bff";
      const x = i * B / 6 + 40, y = H * 0.78; e.beginPath(); e.moveTo(x, y); e.lineTo(x + 8, y - 26); e.lineTo(x + 16, y); e.fill(); } });
    schweber = "#bfa8ff";
  } else if (art === "wolken") {
    fern = ebene("rgba(255,255,255,.55)", 0.75, 2, (e) => { for (let i = 0; i < 4; i++) wolke(e, i * B / 4 + 80, 70 + (i % 2) * 40, 1.4, "rgba(255,255,255,.7)"); });
    nah = ebene("rgba(255,220,240,.5)", 0.85, 3, (e) => { e.fillStyle = "rgba(255,240,250,.8)";
      e.fillRect(B * 0.6, H * 0.45, 60, H * 0.4); e.beginPath(); e.moveTo(B * 0.6 - 6, H * 0.45); e.lineTo(B * 0.6 + 30, H * 0.33); e.lineTo(B * 0.6 + 66, H * 0.45); e.fill(); });
    schweber = "#ffffff";
  } else {
    fern = ebene("#a9dcae", 0.62, 2, (e) => { for (let i = 0; i < 3; i++) wolke(e, i * B / 3 + 120, 60 + (i % 2) * 30, 1, "rgba(255,255,255,.9)"); });
    nah = ebene("#86c98f", 0.74, 3, (e) => { for (let i = 0; i < 7; i++) { const x = i * B / 7 + 30, y = H * 0.72;
      e.fillStyle = "#6b4a2f"; e.fillRect(x - 3, y - 10, 6, 22); e.fillStyle = "#4f9a5a"; e.beginPath(); e.arc(x, y - 18, 16, 0, Math.PI * 2); e.fill(); } });
    schweber = "#fff8c0";
  }
  const kachel = (zeichne) => { const [c, e] = leinwand(T, T); zeichne(e); return c; };
  const gras = kachel((e) => { e.fillStyle = L.boden; e.fillRect(0, 0, T, T); e.fillStyle = "rgba(0,0,0,.12)"; e.fillRect(0, 10, T, T - 10);
    e.fillStyle = "rgba(255,255,255,.35)"; e.fillRect(0, 0, T, 5);
    for (let i = 0; i < 5; i++) { e.fillStyle = "rgba(0,0,0,.1)"; e.fillRect(4 + i * 8, 16 + (i % 2) * 10, 3, 3); } });
  const erde = kachel((e) => { e.fillStyle = L.boden; e.fillRect(0, 0, T, T); e.fillStyle = "rgba(0,0,0,.2)"; e.fillRect(0, 0, T, T);
    for (let i = 0; i < 4; i++) { e.fillStyle = "rgba(0,0,0,.12)"; e.fillRect(6 + i * 9, 8 + (i % 3) * 9, 4, 4); } });
  const block = kachel((e) => { e.fillStyle = L.block; e.beginPath(); e.roundRect(1, 1, T - 2, T - 2, 5); e.fill();
    e.strokeStyle = "rgba(60,30,60,.35)"; e.lineWidth = 2; e.stroke();                     /* Rand: auch auf hellem Himmel gut zu sehen */
    e.fillStyle = "rgba(255,255,255,.35)"; e.fillRect(3, 3, T - 6, 5); e.fillStyle = "rgba(0,0,0,.15)"; e.fillRect(3, T - 7, T - 6, 4);
    e.fillStyle = "rgba(0,0,0,.2)"; for (const [x, y] of [[7, 13], [T - 10, 13], [7, T - 13], [T - 10, T - 13]]) e.fillRect(x, y, 3, 3); });
  return { himmel, fern, nah: hoch ? nah : null, schweber, gras, erde, block };
}

export default {
  symbol: "🦘",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "🦘 Franzi hüpft", "→ / ← laufen und anhalten · OK springen · STOP zurück");
    let spiel = null, auswahl = null;

    function menueZeigen(text = "Welche Welt?") {
      spiel?.stopp(); spiel = null;
      punkte.textContent = "";
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text }));
      inhalt.replaceChildren(spalte);
      auswahl = menue(spalte, LEVEL.map((l, i) => ({ text: l.name, aktion: () => starte(i) })));
    }

    function starte(nr) {
      auswahl = null;
      const L = LEVEL[nr], karte = L.karte.map((z) => [...z]);
      /* 6.9.17: Spielfeld so groß wie möglich - gezeichnet wird in Spiel-Einheiten, der Maßstab k vergrößert */
      const H = karte.length * T;
      const k = Math.max(1, Math.min((innerHeight * 0.72) / H, (innerWidth * 0.92) / 800));   /* mind. 800 Einheiten sichtbar */
      const B = Math.round(Math.min(1200 * k, innerWidth * 0.92) / k);
      const canvas = el("canvas", { class: "spielfeld" });
      inhalt.replaceChildren(canvas);
      const g = canvasScharf(canvas, Math.round(B * k), Math.round(H * k));
      g.scale(k, k);
      const hoch = stufe() === "hoch";
      const bilder = vorzeichnen(L, B, H, hoch);
      const teilchen = [];
      const staub = (x, y, n, farbe) => { for (let i = 0; i < n; i++) teilchen.push({ x, y, vx: (Math.random() - 0.5) * 4, vy: -Math.random() * 3, leben: 16 + Math.random() * 10, farbe }); };
      const breite = karte[0].length * T;
      const schnecken = [];
      karte.forEach((zeile, y) => zeile.forEach((c, x) => {
        if (c === "s") { schnecken.push({ x: x * T + 4, y: y * T + T - 22, v: -1.2, platt: 0 }); zeile[x] = " "; }
      }));
      const fest = (x, y) => "#=".includes(karte[Math.floor(y / T)]?.[Math.floor(x / T)] ?? " ");
      const z = { x: T, y: T * 4, vx: 0, vy: 0, lauf: 0, amBoden: false, sterne: 0, start: { x: T, y: T * 4 }, kamera: 0, takt: 0, aus: false };
      const alleSterne = L.karte.join("").split("*").length - 1;
      const zeigePunkte = () => { punkte.textContent = `⭐ ${z.sterne} / ${alleSterne}`; };
      zeigePunkte();
      function zurueck() { z.x = z.start.x; z.y = z.start.y; z.vx = 0; z.vy = 0; z.lauf = 0; ton("fehler"); }
      function logik() {
        z.takt++;
        z.vx = z.lauf * 4.2;
        z.vy = Math.min(14, z.vy + 0.8);
        /* waagrecht */
        const nx = z.x + z.vx;
        /* an einer Wand bleibt sie stehen, will aber weiter - ein Sprung reicht, dann läuft sie weiter (Fernbedienung) */
        if (!fest(nx + (z.vx > 0 ? 28 : 2), z.y + 4) && !fest(nx + (z.vx > 0 ? 28 : 2), z.y + 34)) z.x = nx;
        z.x = Math.max(0, Math.min(breite - 30, z.x));
        /* senkrecht */
        const ny = z.y + z.vy;
        z.amBoden = false;
        if (z.vy > 0 && (fest(z.x + 4, ny + 36) || fest(z.x + 26, ny + 36))) {
          if (z.vy > 6) { z.stauch = 6; staub(z.x + 15, Math.floor((ny + 36) / T) * T, hoch ? 10 : 5, "rgba(255,255,255,.8)"); }
          z.y = Math.floor((ny + 36) / T) * T - 36; z.vy = 0; z.amBoden = true;
        }
        else if (z.vy < 0 && (fest(z.x + 4, ny) || fest(z.x + 26, ny))) { z.vy = 0; }
        else z.y = ny;
        if (z.y > H + 40) { zurueck(); return; }
        /* Sterne, Fähnchen, Ziel: jede Berührung zählt (alle Felder, die Franzi gerade berührt) */
        let ziel = false;
        for (const [ox, oy] of [[3, 3], [27, 3], [3, 33], [27, 33], [15, 18]]) {
          const kx = Math.floor((z.x + ox) / T), ky = Math.floor((z.y + oy) / T), c = karte[ky]?.[kx];
          if (c === "*") { karte[ky][kx] = " "; z.sterne++; ton("punkt", { faktor: 1 + z.sterne * 0.04 }); zeigePunkte(); staub(kx * T + T / 2, ky * T + T / 2, hoch ? 14 : 7, "#ffd34d"); }
          if (c === "f") { z.start = { x: kx * T, y: ky * T }; karte[ky][kx] = "F"; ton("ok"); }
          if (c === "Z") ziel = true;
        }
        if (ziel && !z.aus) {
          z.aus = true; ton("sieg"); konfetti(box);
          setTimeout(() => menueZeigen(`🏁 Geschafft – ${z.sterne} von ${alleSterne} Sternen! Noch eine Welt?`), 900);
          return;
        }
        /* Schnecken */
        for (const s of schnecken) {
          if (s.platt) { s.platt--; continue; }
          const vor = s.x + (s.v < 0 ? -2 : 34);
          if (fest(vor, s.y + 10) || !fest(vor, s.y + 30)) s.v *= -1;
          s.x += s.v;
          if (Math.abs(s.x + 16 - (z.x + 15)) < 26 && Math.abs(s.y + 11 - (z.y + 18)) < 26) {
            if (z.vy > 0 && z.y + 36 < s.y + 14) { s.platt = 99999; z.vy = -9; ton("punkt"); }
            else zurueck();
          }
        }
        z.kamera = Math.max(0, Math.min(breite - B, z.x - B * 0.35));
        if (z.lauf) z.blick = z.lauf;
        if (z.stauch) z.stauch--;
        for (const t of teilchen) { t.x += t.vx; t.y += t.vy; t.vy += 0.2; t.leben--; }
        for (let i = teilchen.length - 1; i >= 0; i--) if (teilchen[i].leben <= 0) teilchen.splice(i, 1);
      }
      function zeichne() {
        /* Hintergrund: Himmel fest, Ebenen ziehen langsamer als das Spielfeld (Parallax) */
        g.drawImage(bilder.himmel, 0, 0, B, H);
        const ebene = (bild, faktor) => { const x = -((z.kamera * faktor) % bild.width); g.drawImage(bild, x, 0); g.drawImage(bild, x + bild.width, 0); };
        ebene(bilder.fern, 0.2);
        if (hoch) {
          ebene(bilder.nah, 0.45);
          g.fillStyle = bilder.schweber;
          for (let i = 0; i < 24; i++) {
            const x = ((i * 157 + z.takt * (0.4 + (i % 3) * 0.2) - z.kamera * 0.6) % B + B) % B, y = (i * 53) % (H - 80) + Math.sin(z.takt * 0.03 + i) * 8;
            g.globalAlpha = 0.35 + (i % 4) * 0.12; g.beginPath(); g.arc(x, y, 2 + (i % 3), 0, Math.PI * 2); g.fill();
          }
          g.globalAlpha = 1;
        }
        g.save(); g.translate(-Math.round(z.kamera), 0);
        const von = Math.floor(z.kamera / T), bis = Math.min(karte[0].length, von + Math.ceil(B / T) + 1);
        g.textAlign = "center"; g.textBaseline = "middle"; g.font = `${T - 8}px "FF Emoji", sans-serif`;
        for (let y = 0; y < karte.length; y++) {
          for (let x = von; x < bis; x++) {
            const c = karte[y][x], px = x * T, py = y * T;
            if (c === "#") g.drawImage(karte[y - 1]?.[x] === "#" ? bilder.erde : bilder.gras, px, py);
            else if (c === "=") g.drawImage(bilder.block, px, py);
            else if ("*fFZ".includes(c)) g.fillStyle = "#000";            /* Emojis deckend zeichnen (Chrome übernimmt die Deckkraft) */
            if (c === "*") g.fillText("⭐", px + T / 2, py + T / 2 + Math.sin(z.takt * 0.12 + x) * 3);
            else if (c === "f" || c === "F") g.fillText(c === "F" ? "🚩" : "🏳️", px + T / 2, py + T / 2);
            else if (c === "Z") g.fillText("🏁", px + T / 2, py + T / 2);
          }
        }
        for (const sn of schnecken) {
          if (sn.platt > 9000 || sn.x < z.kamera - T || sn.x > z.kamera + B) continue;
          const kr = sn.v < 0 ? 1 : -1;                                   /* Blickrichtung */
          g.fillStyle = "#9bd07a"; g.beginPath(); g.roundRect(sn.x, sn.y + 13, 34, 9, 4); g.fill();
          g.strokeStyle = "#9bd07a"; g.lineWidth = 2; g.beginPath();
          const kx = sn.x + (kr > 0 ? 4 : 30); g.moveTo(kx, sn.y + 14); g.lineTo(kx - kr * 3, sn.y + 4); g.stroke();
          g.fillStyle = "#1e2a4a"; g.beginPath(); g.arc(kx - kr * 3, sn.y + 3, 2, 0, Math.PI * 2); g.fill();
          g.fillStyle = "#e0a040"; g.beginPath(); g.arc(sn.x + 18, sn.y + 8, 11, 0, Math.PI * 2); g.fill();
          g.strokeStyle = "#b8742a"; g.lineWidth = 2; g.beginPath();
          for (let w = 0; w < 9; w += 0.3) { const r = 9 - w; g.lineTo(sn.x + 18 + Math.cos(w * 1.4) * r, sn.y + 8 + Math.sin(w * 1.4) * r); }
          g.stroke();
        }
        for (const t of teilchen) { g.globalAlpha = Math.max(0, t.leben / 26); g.fillStyle = t.farbe; g.fillRect(t.x - 2, t.y - 2, 4, 4); }
        g.globalAlpha = 1;
        /* Franzi: Fernseher-Körper, Antennen, Beine, Gesicht in Blickrichtung; staucht beim Landen */
        const fx = Math.round(z.x), fy = Math.round(z.y), bein = z.amBoden && z.lauf ? Math.sin(z.takt * 0.7) * 4 : 0;
        const st = z.stauch ? 1 - z.stauch * 0.03 : 1, blick = z.blick || 1;
        g.save(); g.translate(fx + 15, fy + 36); g.scale(2 - st, st); g.translate(-15, -36);
        g.fillStyle = "rgba(0,0,0,.18)"; if (z.amBoden) { g.beginPath(); g.ellipse(15, 37, 16, 3, 0, 0, Math.PI * 2); g.fill(); }
        g.strokeStyle = "#3b4566"; g.lineWidth = 2; g.beginPath(); g.moveTo(10, 2); g.lineTo(6, -7); g.moveTo(20, 2); g.lineTo(25, -6); g.stroke();
        g.fillStyle = "#ffd54f"; g.beginPath(); g.arc(6, -7, 2.6, 0, Math.PI * 2); g.fill();
        g.fillStyle = "#7fdcaa"; g.beginPath(); g.arc(25, -6, 2.6, 0, Math.PI * 2); g.fill();
        g.fillStyle = "#c94f35"; g.fillRect(4 + bein, 29, 8, 7); g.fillRect(18 - bein, 29, 8, 7);
        g.fillStyle = "#ff7a59"; g.beginPath(); g.roundRect(0, 0, 30, 30, 7); g.fill();
        g.fillStyle = "#ff9472"; g.beginPath(); g.roundRect(0, 0, 30, 12, [7, 7, 0, 0]); g.fill();
        g.fillStyle = "#1e2a4a"; g.beginPath(); g.roundRect(4, 4, 22, 20, 5); g.fill();
        g.fillStyle = "#fff"; g.fillRect(9 + blick * 2, 9, 3, 5); g.fillRect(17 + blick * 2, 9, 3, 5);
        g.strokeStyle = "#fff"; g.lineWidth = 1.6; g.beginPath(); g.arc(15 + blick * 2, 16, 4, 0.2, Math.PI - 0.2); g.stroke();
        g.restore();
        g.restore();
      }
      const steuer = takt(1000 / 30, logik, zeichne);
      spiel = {
        stopp: () => steuer.stopp(),
        taste(t) {
          if (t === "ArrowRight") { z.lauf = z.lauf < 0 ? 0 : 1; return true; }
          if (t === "ArrowLeft") { z.lauf = z.lauf > 0 ? 0 : -1; return true; }
          if (t === "Enter" || t === " " || t === "ArrowUp") { if (z.amBoden) { z.vy = -13.5; ton("bewegen"); } return true; }
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
      schliesse() { spiel?.stopp(); },
    };
  },
};
