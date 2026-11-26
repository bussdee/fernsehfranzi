/* FernsehFranzi 6.8 - Stimm-Spiele: Spiele, die man mit der Stimme steuert (USB-Mikro am Fernseher).
 *
 *   🐦 Möwenflug   Je höher der Ton, desto höher fliegt die Möwe über die Ostsee. Fische sammeln, Gewitterwolken ausweichen.
 *   🐉 Pst!        Leise am schlafenden Drachen vorbei zum Schatz schleichen (→ ein Schritt). Wird es laut, wacht er auf.
 *   👏 Klatsch-Läufer (6.8.1)  Franzi rennt, Klatschen = springen (ohne Mikro: OK oder ↑).
 *   🎈 Ton-Kanone (6.8.1)      Luftballons mit Tönen steigen auf - den Ton singen (Oktave egal), dann platzt er
 *                              (ohne Mikro: ← → Ton wählen, OK feuern).
 *
 * Ohne Mikro geht beides auch mit den Pfeilen (Grundsatz 3): Möwe mit ↑ ↓, beim Drachen öffnet er ab und zu ein Auge -
 * wer dann einen Schritt macht, weckt ihn. Das Mikro misst nur Tonhöhe und Pegel, nichts wird aufgenommen.
 * Beide Spiele sind während des Spielens still (sonst hört das Mikro den Fernseher). Zeichnen höchstens 30-mal je Sekunde.
 */
import { el, stufe } from "../gemeinsam.js";
import { kopf, ton, menue, takt, canvasScharf, konfetti } from "./kern.js";
import { pegel, stimmHz } from "./stimme.js";
import { naechsterTon } from "./bass.js";

const RUNDE_S = 60;

async function mikro() {
  try {
    const strom = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
    const ac = new AudioContext(), analyse = ac.createAnalyser();
    analyse.fftSize = 2048;
    ac.createMediaStreamSource(strom).connect(analyse);
    if (ac.state === "suspended") ac.resume().catch(() => {});
    const puffer = new Float32Array(analyse.fftSize);
    return {
      lies() { analyse.getFloatTimeDomainData(puffer); return { laut: pegel(puffer), hz: stimmHz(puffer, ac.sampleRate) }; },
      stopp() { strom.getTracks().forEach((t) => t.stop()); ac.close().catch(() => {}); },
    };
  } catch (_) { return null; }
}

/* ------------------------------------------------------------ Möwenflug */
function moewenflug(box, inhalt, punkte, hilfe, mik, fertig) {
  const B = Math.min(1200, Math.round(innerWidth * 0.86)), H = Math.round(B * 0.5);
  const canvas = el("canvas", { class: "spielfeld" });
  inhalt.replaceChildren(canvas);
  const g = canvasScharf(canvas, B, H);
  const z = { y: H * 0.5, ziel: H * 0.5, fische: 0, herzen: 3, dinge: [], rest: RUNDE_S * 30, takt: 0, taste: 0, wellen: 0 };
  hilfe.textContent = mik ? "Hoch singen = hoch fliegen · leise = sinken · ↑ ↓ geht auch · STOP Ende" : "↑ ↓ fliegen · STOP Ende (ohne Mikro)";
  const MEER = H * 0.82;
  function logik() {
    z.takt++;
    if (mik && z.takt % 3 === 0) {
      const { laut, hz } = mik.lies();
      if (hz && laut > 0.04 && hz > 90 && hz < 1200) {
        /* 150 Hz (tief) unten bis 600 Hz (hoch) oben - Kinderstimmen liegen meist dazwischen */
        const t = Math.max(0, Math.min(1, Math.log2(hz / 150) / 2));
        z.ziel = MEER - 30 - t * (MEER - 70);
      } else if (!z.taste) z.ziel = Math.min(MEER - 25, z.ziel + 2.2);            /* still: langsam zum Wasser gleiten */
    }
    if (z.taste) { z.ziel = Math.max(40, Math.min(MEER - 25, z.ziel + z.taste * 9)); }
    z.y += (z.ziel - z.y) * 0.18;
    z.wellen = (z.wellen + 2) % 80;
    if (z.takt % 38 === 0) {
      const sturm = Math.random() < 0.35;
      z.dinge.push({ x: B + 40, y: 60 + Math.random() * (MEER - 120), art: sturm ? "wolke" : "fisch" });
    }
    for (const d of z.dinge) {
      d.x -= 5;
      if (!d.weg && Math.abs(d.x - B * 0.22) < 34 && Math.abs(d.y - z.y) < (d.art === "wolke" ? 40 : 30)) {
        d.weg = true;
        if (d.art === "fisch") z.fische++; else z.herzen--;
      }
    }
    z.dinge = z.dinge.filter((d) => d.x > -60 && !d.weg);
    punkte.textContent = `🐟 ${z.fische} · ${"❤️".repeat(Math.max(0, z.herzen))} · ⏱ ${Math.ceil(z.rest / 30)}`;
    if (--z.rest <= 0 || z.herzen <= 0) fertig(`🐟 ${z.fische} Fische gefangen!`, z.fische);
  }
  /* 6.9.28: Himmel, Küste und Meer einmal vorzeichnen; Wolken ziehen langsamer (Parallax); „hoch“: Segelboot, mehr Glitzer */
  const hoch = stufe() === "hoch";
  const grund = document.createElement("canvas"); grund.width = B; grund.height = H;
  { const h = grund.getContext("2d");
    const hi = h.createLinearGradient(0, 0, 0, MEER); hi.addColorStop(0, "#6fb8f0"); hi.addColorStop(1, "#e2f4ff");
    h.fillStyle = hi; h.fillRect(0, 0, B, MEER);
    const so = h.createRadialGradient(B * 0.82, H * 0.2, 0, B * 0.82, H * 0.2, H * 0.22);
    so.addColorStop(0, "rgba(255,250,210,1)"); so.addColorStop(0.25, "rgba(255,236,150,.9)"); so.addColorStop(1, "rgba(255,236,150,0)");
    h.fillStyle = so; h.fillRect(0, 0, B, MEER);
    h.fillStyle = "#9cc6a8"; h.beginPath(); h.moveTo(0, MEER);                       /* ferne Küste */
    for (let x = 0; x <= B * 0.45; x += 10) {
      const auslauf = Math.max(0, Math.min(1, (B * 0.45 - x) / (B * 0.08)));      /* läuft am Ende sanft ins Meer aus */
      h.lineTo(x, MEER - (14 + Math.sin(x / 60) * 6 + (x < B * 0.2 ? 10 : 0)) * auslauf);
    }
    h.lineTo(B * 0.45, MEER); h.fill();
    h.fillStyle = "#f4f4f0"; h.fillRect(B * 0.33, MEER - 52, 9, 34); h.fillStyle = "#d6403c"; h.fillRect(B * 0.33, MEER - 40, 9, 7); h.fillRect(B * 0.33 - 2, MEER - 56, 13, 6);
    const me = h.createLinearGradient(0, MEER, 0, H); me.addColorStop(0, "#3a8ccc"); me.addColorStop(1, "#1d5d96");
    h.fillStyle = me; h.fillRect(0, MEER, B, H - MEER); }
  const wolkenband = document.createElement("canvas"); wolkenband.width = B; wolkenband.height = Math.round(MEER * 0.6);
  { const w = wolkenband.getContext("2d"); w.fillStyle = "rgba(255,255,255,.85)";
    for (const [x, y, r] of [[0.12, 0.35, 26], [0.45, 0.2, 34], [0.78, 0.45, 22]]) {
      const cx = x * B, cy = y * wolkenband.height;
      w.beginPath(); w.ellipse(cx, cy, r * 2.4, r * 0.8, 0, 0, Math.PI * 2); w.arc(cx - r, cy - r * 0.4, r, 0, Math.PI * 2); w.arc(cx + r * 0.6, cy - r * 0.6, r * 1.2, 0, Math.PI * 2); w.fill();
    } }
  function zeichne() {
    g.drawImage(grund, 0, 0);
    const wx = -((z.takt * 0.8) % B);
    g.drawImage(wolkenband, wx, 0); g.drawImage(wolkenband, wx + B, 0);
    if (hoch) {                                                                    /* Segelboot weit draußen */
      const bx = B - ((z.takt * 0.4) % (B + 120)), by = MEER - 4;
      g.fillStyle = "#8b5a3c"; g.beginPath(); g.moveTo(bx - 18, by - 6); g.lineTo(bx + 18, by - 6); g.lineTo(bx + 12, by); g.lineTo(bx - 12, by); g.fill();
      g.fillStyle = "#fff"; g.beginPath(); g.moveTo(bx, by - 8); g.lineTo(bx, by - 40); g.lineTo(bx + 16, by - 10); g.fill();
    }
    g.strokeStyle = "rgba(255,255,255,.5)"; g.lineWidth = 3;
    for (let x = -z.wellen; x < B; x += 80) { g.beginPath(); g.arc(x + 40, MEER + 14, 18, Math.PI * 1.1, Math.PI * 1.9); g.stroke(); }
    g.fillStyle = "rgba(255,255,255,.55)";
    for (let i = 0; i < (hoch ? 26 : 10); i++) {
      const gx = ((i * 197 - z.takt * 3) % B + B) % B, gy = MEER + 24 + ((i * 37) % Math.max(1, Math.round(H - MEER - 30)));
      if ((z.takt + i * 7) % 40 < 20) g.fillRect(gx, gy, 10, 2);
    }
    for (const d of z.dinge) {
      if (d.art === "fisch") {
        g.fillStyle = "#ff9f43";
        g.beginPath(); g.ellipse(d.x, d.y, 18, 10, 0, 0, Math.PI * 2); g.fill();
        g.beginPath(); g.moveTo(d.x + 16, d.y); g.lineTo(d.x + 30, d.y - 10); g.lineTo(d.x + 30, d.y + 10); g.fill();
        g.fillStyle = "#ffd07a"; g.fillRect(d.x - 2, d.y - 8, 4, 16); g.fillRect(d.x + 6, d.y - 7, 3, 14);
        g.fillStyle = "#fff"; g.beginPath(); g.arc(d.x - 9, d.y - 2, 3.5, 0, Math.PI * 2); g.fill();
        g.fillStyle = "#1e2a4a"; g.beginPath(); g.arc(d.x - 10, d.y - 2, 1.8, 0, Math.PI * 2); g.fill();
      } else {
        g.fillStyle = "#56607a";
        for (const [dx, dy, r] of [[-22, 4, 20], [0, -8, 26], [24, 4, 20]]) { g.beginPath(); g.arc(d.x + dx, d.y + dy, r, 0, Math.PI * 2); g.fill(); }
        g.strokeStyle = "#2c3346"; g.lineWidth = 2.5;                                  /* grimmiges Gesicht */
        g.beginPath(); g.moveTo(d.x - 12, d.y - 8); g.lineTo(d.x - 4, d.y - 4); g.moveTo(d.x + 12, d.y - 8); g.lineTo(d.x + 4, d.y - 4);
        g.moveTo(d.x - 8, d.y + 10); g.quadraticCurveTo(d.x, d.y + 4, d.x + 8, d.y + 10); g.stroke();
        g.strokeStyle = "#ffd34d"; g.lineWidth = 4;
        g.beginPath(); g.moveTo(d.x, d.y + 18); g.lineTo(d.x - 8, d.y + 34); g.lineTo(d.x + 4, d.y + 34); g.lineTo(d.x - 4, d.y + 50); g.stroke();
      }
    }
    /* Möwe: Körper, gefüllte Flügel mit grauen Spitzen, Schatten auf dem Wasser */
    const x = B * 0.22, schlag = Math.sin(z.takt * 0.35) * 14;
    g.fillStyle = "rgba(0,40,80,.18)"; g.beginPath(); g.ellipse(x, MEER + 10, 26 * (1 - (MEER - z.y) / MEER * 0.6), 5, 0, 0, Math.PI * 2); g.fill();
    for (const [von, bis] of [[-6, -46], [4, 40]]) {
      g.fillStyle = "#ffffff"; g.strokeStyle = "#5b6475"; g.lineWidth = 2.5;
      g.beginPath(); g.moveTo(x + von, z.y - 4); g.quadraticCurveTo(x + (von + bis) / 2, z.y - 26 - schlag, x + bis, z.y - 8 - schlag);
      g.quadraticCurveTo(x + (von + bis) / 2, z.y - 10 - schlag * 0.4, x + von, z.y + 2); g.fill(); g.stroke();
      g.fillStyle = "#8a93a6"; g.beginPath(); g.arc(x + bis, z.y - 8 - schlag, 4, 0, Math.PI * 2); g.fill();
    }
    g.fillStyle = "#fff"; g.strokeStyle = "#5b6475"; g.lineWidth = 3;
    g.beginPath(); g.ellipse(x, z.y, 24, 11, 0, 0, Math.PI * 2); g.fill(); g.stroke();
    g.fillStyle = "#ffb000"; g.beginPath(); g.moveTo(x + 22, z.y - 2); g.lineTo(x + 34, z.y + 1); g.lineTo(x + 22, z.y + 4); g.fill();
    g.fillStyle = "#1e2a4a"; g.beginPath(); g.arc(x + 14, z.y - 3, 2.5, 0, Math.PI * 2); g.fill();
  }
  const steuer = takt(1000 / 30, logik, zeichne);
  return {
    taste(t, losgelassen) {
      if (t === "ArrowUp" || t === "ArrowDown") {
        const richtung = t === "ArrowUp" ? -1 : 1;
        z.taste = losgelassen ? 0 : richtung;
        if (!losgelassen) z.ziel = Math.max(40, Math.min(MEER - 25, z.ziel + richtung * 40));   /* Fernbedienung: kurzer Druck */
        return true;
      }
      return false;
    },
    stopp() { steuer.stopp(); },
  };
}

/* ------------------------------------------------------------ Pst - der Drache schläft */
function drache(box, inhalt, punkte, hilfe, mik, fertig) {
  const SCHRITTE = 14;
  const B = Math.min(1200, Math.round(innerWidth * 0.86)), H = Math.round(B * 0.45);
  const canvas = el("canvas", { class: "spielfeld" });
  const wach = el("div", { class: "drache-wach" }, el("span"));
  inhalt.replaceChildren(el("div", { class: "drache-seite" }, canvas, wach));
  const g = canvasScharf(canvas, B, H);
  const z = { schritt: 0, wach: 0, auge: 0, naechstesAuge: 120 + Math.random() * 120, takt: 0, versuche: 1, zzz: 0 };
  hilfe.textContent = (mik ? "Leise sein! " : "") + "→ ein Schritt · wenn der Drache blinzelt: stillhalten · STOP Ende";
  function aufwecken() {
    z.wach = 0; z.schritt = 0; z.versuche++; z.auge = 0;
    punkte.textContent = "🥱 Der Drache hat sich nur umgedreht – nochmal ganz leise!";
  }
  function logik() {
    z.takt++;
    if (mik) {
      const { laut } = mik.lies();
      z.wach += laut > 0.12 ? laut * 3 : -0.35;                 /* Lärm weckt, Stille beruhigt */
    } else z.wach -= 0.2;
    z.wach = Math.max(0, z.wach);
    if (z.auge > 0) z.auge--;
    else if (--z.naechstesAuge <= 0) { z.auge = 45; z.naechstesAuge = 90 + Math.random() * 150; }
    z.zzz = (z.zzz + 1) % 90;
    wach.firstChild.style.transform = `scaleX(${Math.min(1, z.wach / 100).toFixed(3)})`;
    if (z.wach >= 100) aufwecken();
  }
  /* 6.9.29: Burghalle einmal vorzeichnen - Steinwand, Boden, Fackelhalter, Schatztruhe mit Münzen */
  const hoch = stufe() === "hoch";
  const halle = document.createElement("canvas"); halle.width = B; halle.height = H;
  { const h = halle.getContext("2d");
    const w = h.createLinearGradient(0, 0, 0, H * 0.78); w.addColorStop(0, "#241c3c"); w.addColorStop(1, "#33284f");
    h.fillStyle = w; h.fillRect(0, 0, B, H * 0.78);
    h.strokeStyle = "rgba(0,0,0,.22)"; h.lineWidth = 2;
    for (let y = 0, r = 0; y < H * 0.78; y += 34, r++) {
      h.beginPath(); h.moveTo(0, y); h.lineTo(B, y); h.stroke();
      for (let x = (r % 2) * 40; x < B; x += 80) { h.beginPath(); h.moveTo(x, y); h.lineTo(x, y + 34); h.stroke(); }
    }
    const b = h.createLinearGradient(0, H * 0.78, 0, H); b.addColorStop(0, "#3d3160"); b.addColorStop(1, "#231b3a");
    h.fillStyle = b; h.fillRect(0, H * 0.78, B, H * 0.22);
    for (const fx of [B * 0.18, B * 0.86]) { h.fillStyle = "#6b5a4a"; h.fillRect(fx - 4, H * 0.3, 8, 30); h.fillRect(fx - 10, H * 0.3, 20, 6); }
    const tx = B - 112, ty = H * 0.6;
    h.fillStyle = "#ffcf3a";
    for (let i = 0; i < 9; i++) { h.beginPath(); h.ellipse(tx + 10 + (i % 5) * 16, ty - 8 - Math.floor(i / 5) * 8, 9, 4, 0, 0, Math.PI * 2); h.fill(); }
    h.fillStyle = "#8a5a2b"; h.beginPath(); h.roundRect(tx, ty, 84, 52, 6); h.fill();
    h.fillStyle = "#6e4320"; h.fillRect(tx, ty + 16, 84, 6); h.fillStyle = "#e0b040"; h.fillRect(tx + 36, ty + 12, 12, 16);
    h.fillStyle = "#a06a34"; h.beginPath(); h.roundRect(tx - 4, ty - 14, 92, 18, [10, 10, 2, 2]); h.fill(); }
  function zeichne() {
    g.drawImage(halle, 0, 0);
    for (const fx of [B * 0.18, B * 0.86]) {                     /* Fackeln - flackern nur in „hoch“ */
      const fl = hoch ? Math.sin(z.takt * 0.4 + fx) * 3 : 0;
      const sch = g.createRadialGradient(fx, H * 0.27, 0, fx, H * 0.27, 90); sch.addColorStop(0, "rgba(255,180,80,.25)"); sch.addColorStop(1, "rgba(255,180,80,0)");
      g.fillStyle = sch; g.fillRect(fx - 90, H * 0.27 - 90, 180, 180);
      g.fillStyle = "#ff9a3c"; g.beginPath(); g.ellipse(fx, H * 0.27, 9, 16 + fl, 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = "#ffe07a"; g.beginPath(); g.ellipse(fx, H * 0.28, 5, 9 + fl * 0.6, 0, 0, Math.PI * 2); g.fill();
    }
    if (hoch && (z.takt + 20) % 40 < 20) {                       /* Münzen blitzen */
      g.fillStyle = "rgba(255,255,255,.8)"; g.fillRect(B - 84, H * 0.6 - 16, 3, 3); g.fillRect(B - 52, H * 0.6 - 10, 3, 3);
    }
    /* Drache in der Mitte */
    const dx = B * 0.52, dy = H * 0.6, atmen = Math.sin(z.takt * 0.06) * 4;
    g.fillStyle = "#3fae6a";
    g.beginPath(); g.ellipse(dx, dy + atmen * 0.3, 150, 62 + atmen, 0, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.ellipse(dx + 150, dy - 20, 62, 44, -0.2, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#b8e6a0"; g.beginPath(); g.ellipse(dx + 10, dy + 30 + atmen * 0.3, 110, 26, 0, 0, Math.PI * 2); g.fill();    /* Bauch */
    g.fillStyle = "#2f8a52"; g.beginPath(); g.moveTo(dx - 40, dy - 40); g.quadraticCurveTo(dx - 10, dy - 120 - atmen, dx + 50, dy - 50); g.fill();   /* Flügel */
    g.fillStyle = "#1e5a36"; g.beginPath(); g.arc(dx + 200, dy - 22, 4, 0, Math.PI * 2); g.fill();                              /* Nüster */
    g.fillStyle = "#3fae6a"; g.beginPath(); g.moveTo(dx - 140, dy + 10); g.quadraticCurveTo(dx - 230, dy + 40, dx - 200, dy - 10); g.lineTo(dx - 130, dy - 10); g.fill();   /* Schwanz */
    if (hoch) for (let i = 0; i < 3; i++) {                         /* Rauchkringel aus der Nüster */
      const p = ((z.takt * 0.6 + i * 30) % 90) / 90;
      g.fillStyle = `rgba(200,200,220,${(0.35 * (1 - p)).toFixed(2)})`; g.beginPath(); g.arc(dx + 205 + p * 30, dy - 26 - p * 50, 5 + p * 10, 0, Math.PI * 2); g.fill();
    }
    g.fillStyle = "#2f8a52";
    for (let i = 0; i < 5; i++) { g.beginPath(); g.moveTo(dx - 100 + i * 45, dy - 55); g.lineTo(dx - 80 + i * 45, dy - 95); g.lineTo(dx - 60 + i * 45, dy - 55); g.fill(); }
    if (z.auge > 0) {
      g.fillStyle = "#fff"; g.beginPath(); g.arc(dx + 170, dy - 34, 12, 0, Math.PI * 2); g.fill();
      g.fillStyle = "#1e2a4a"; g.beginPath(); g.arc(dx + 166, dy - 34, 6, 0, Math.PI * 2); g.fill();
    } else {
      g.strokeStyle = "#1e2a4a"; g.lineWidth = 4;
      g.beginPath(); g.arc(dx + 170, dy - 38, 10, 0.2, Math.PI - 0.2); g.stroke();
      g.fillStyle = "rgba(255,255,255,.75)"; g.font = "bold 28px sans-serif";
      g.globalAlpha = 1 - z.zzz / 90; g.fillText("z", dx + 210 + z.zzz * 0.4, dy - 70 - z.zzz * 0.8); g.globalAlpha = 1;
    }
    /* Franzi schleicht auf Zehenspitzen */
    const fx = 50 + (B - 220) * (z.schritt / SCHRITTE), fy = H * 0.7;
    g.fillStyle = "rgba(0,0,0,.25)"; g.beginPath(); g.ellipse(fx, fy + 8, 26, 5, 0, 0, Math.PI * 2); g.fill();
    g.strokeStyle = "#3b4566"; g.lineWidth = 3; g.beginPath(); g.moveTo(fx - 8, fy - 40); g.lineTo(fx - 14, fy - 54); g.moveTo(fx + 8, fy - 40); g.lineTo(fx + 16, fy - 52); g.stroke();
    g.fillStyle = "#ffd54f"; g.beginPath(); g.arc(fx - 14, fy - 54, 4, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#7fdcaa"; g.beginPath(); g.arc(fx + 16, fy - 52, 4, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#c94f35"; g.fillRect(fx - 16, fy - 2, 10, 8); g.fillRect(fx + 6, fy - 2, 10, 8);
    g.fillStyle = "#ff7a59"; g.beginPath(); g.roundRect(fx - 22, fy - 40, 44, 38, 9); g.fill();
    g.fillStyle = "#1e2a4a"; g.beginPath(); g.roundRect(fx - 16, fy - 34, 32, 24, 6); g.fill();
    g.fillStyle = "#fff"; g.fillRect(fx - 10, fy - 26, 5, 6); g.fillRect(fx + 5, fy - 26, 5, 6);
    g.strokeStyle = "#fff"; g.lineWidth = 2; g.beginPath(); g.moveTo(fx - 4, fy - 16); g.lineTo(fx + 4, fy - 16); g.stroke();   /* ganz leise: Mund zu */
  }
  const steuer = takt(1000 / 30, logik, zeichne);
  return {
    taste(t, losgelassen) {
      if (losgelassen) return t === "ArrowRight";
      if (t === "ArrowRight" || t === "Enter") {
        if (z.auge > 0) { aufwecken(); punkte.textContent = "👁️ Erwischt! Wenn der Drache blinzelt: stillhalten."; return true; }
        z.schritt++;
        z.wach += 4;                                   /* jeder Schritt macht ein bisschen Geräusch */
        if (z.schritt >= SCHRITTE) fertig(`💰 Schatz geholt – ${z.versuche === 1 ? "beim ersten Versuch!" : `nach ${z.versuche} Versuchen!`}`, 1);
        else punkte.textContent = `🦶 ${z.schritt} / ${SCHRITTE}`;
        return true;
      }
      return t === "ArrowLeft" || t === "ArrowUp" || t === "ArrowDown";
    },
    stopp() { steuer.stopp(); },
  };
}

/* ------------------------------------------------------------ Klatsch-Läufer (6.8.1) */
function klatschLaeufer(box, inhalt, punkte, hilfe, mik, fertig) {
  const B = Math.min(1200, Math.round(innerWidth * 0.86)), H = Math.round(B * 0.42);
  const canvas = el("canvas", { class: "spielfeld" });
  inhalt.replaceChildren(canvas);
  const g = canvasScharf(canvas, B, H);
  const BODEN = H * 0.8, X = B * 0.2;
  const z = { y: 0, vy: 0, huerden: [], gesprungen: 0, herzen: 3, rest: RUNDE_S * 30, takt: 0, leiseVorher: true, pause: 0, naechste: 60 };
  hilfe.textContent = (mik ? "Klatschen = springen · " : "") + "OK oder ↑ springt auch · STOP Ende";
  const springen = () => { if (z.y === 0) z.vy = 15; };
  function logik() {
    z.takt++;
    if (mik) {
      const { laut } = mik.lies();
      if (z.pause > 0) z.pause--;
      if (laut > 0.45 && z.leiseVorher && z.pause === 0) { springen(); z.pause = 9; }   /* Klatschen: plötzlich laut */
      z.leiseVorher = laut < 0.2;
    }
    z.vy -= 0.9; z.y = Math.max(0, z.y + z.vy);
    if (z.y === 0) z.vy = 0;
    if (--z.naechste <= 0) { z.huerden.push({ x: B + 30, h: 34 + Math.random() * 22 }); z.naechste = 55 + Math.random() * 50; }
    for (const h of z.huerden) {
      h.x -= 6.5;
      if (!h.vorbei && h.x < X - 20) { h.vorbei = true; if (!h.getroffen) z.gesprungen++; }
      if (!h.getroffen && Math.abs(h.x - X) < 24 && z.y < h.h - 6) { h.getroffen = true; z.herzen--; }
    }
    z.huerden = z.huerden.filter((h) => h.x > -40);
    punkte.textContent = `🏅 ${z.gesprungen} · ${"❤️".repeat(Math.max(0, z.herzen))} · ⏱ ${Math.ceil(z.rest / 30)}`;
    if (--z.rest <= 0 || z.herzen <= 0) fertig(`🏅 ${z.gesprungen} Hürden übersprungen!`, z.gesprungen);
  }
  /* 6.9.30: Laufstrecke - Himmel mit Hügeln und Wolken (zieht langsamer), Laufbahn mit Linien; einmal vorgezeichnet */
  const hinten = document.createElement("canvas"); hinten.width = B; hinten.height = BODEN;
  { const h = hinten.getContext("2d");
    const v = h.createLinearGradient(0, 0, 0, BODEN); v.addColorStop(0, "#8fd3ff"); v.addColorStop(1, "#e6f7ff");
    h.fillStyle = v; h.fillRect(0, 0, B, BODEN);
    h.fillStyle = "#a9dcae"; h.beginPath(); h.moveTo(0, BODEN);
    for (let x = 0; x <= B; x += 10) h.lineTo(x, BODEN - 40 - Math.sin(x / B * Math.PI * 4) * 16); h.lineTo(B, BODEN); h.fill();
    h.fillStyle = "rgba(255,255,255,.9)";
    for (const [x, y, r] of [[0.15, 0.25, 18], [0.55, 0.15, 24], [0.85, 0.32, 16]]) {
      h.beginPath(); h.ellipse(x * B, y * BODEN, r * 2.2, r * 0.8, 0, 0, Math.PI * 2); h.arc(x * B - r, y * BODEN - r * 0.4, r, 0, Math.PI * 2); h.arc(x * B + r * 0.6, y * BODEN - r * 0.6, r * 1.1, 0, Math.PI * 2); h.fill();
    } }
  function zeichne() {
    const hx = -((z.takt * 1.2) % B);
    g.drawImage(hinten, hx, 0); g.drawImage(hinten, hx + B, 0);
    g.fillStyle = "#d9734a"; g.fillRect(0, BODEN, B, H - BODEN);                         /* Laufbahn */
    g.fillStyle = "#5bbf6a"; g.fillRect(0, H - 14, B, 14);
    g.fillStyle = "rgba(255,255,255,.75)"; g.fillRect(0, BODEN + 4, B, 3);
    for (let x = -((z.takt * 6.5) % 60); x < B; x += 60) g.fillRect(x, BODEN + (H - BODEN) * 0.5, 30, 4);
    for (const h of z.huerden) {                                                     /* Hürde mit Füßen und Streifen */
      const farbe = h.getroffen ? "#9aa" : "#e8603f";
      g.fillStyle = "#6b5a4a"; g.fillRect(h.x - 16, BODEN - h.h, 4, h.h); g.fillRect(h.x + 12, BODEN - h.h, 4, h.h);
      g.fillRect(h.x - 22, BODEN - 4, 14, 4); g.fillRect(h.x + 8, BODEN - 4, 14, 4);
      g.fillStyle = farbe; g.fillRect(h.x - 18, BODEN - h.h, 36, 12);
      g.fillStyle = "#fff"; g.fillRect(h.x - 8, BODEN - h.h, 8, 12); g.fillRect(h.x + 8, BODEN - h.h, 6, 12);
    }
    const y = BODEN - z.y, bein = z.y > 0 ? 0 : Math.sin(z.takt * 0.6) * 6;
    g.fillStyle = "rgba(0,0,0,.2)"; g.beginPath(); g.ellipse(X, BODEN + 2, 26 - Math.min(14, z.y * 0.1), 5, 0, 0, Math.PI * 2); g.fill();
    g.strokeStyle = "#3b4566"; g.lineWidth = 3; g.beginPath(); g.moveTo(X - 8, y - 56); g.lineTo(X - 14, y - 70); g.moveTo(X + 8, y - 56); g.lineTo(X + 16, y - 68); g.stroke();
    g.fillStyle = "#ffd54f"; g.beginPath(); g.arc(X - 14, y - 70, 4, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#7fdcaa"; g.beginPath(); g.arc(X + 16, y - 68, 4, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#c94f35"; g.fillRect(X - 16 + bein, y - 10, 10, 10); g.fillRect(X + 6 - bein, y - 10, 10, 10);
    g.fillStyle = "#ff7a59"; g.beginPath(); g.roundRect(X - 24, y - 56, 48, 46, 10); g.fill();
    g.fillStyle = "#ff9472"; g.beginPath(); g.roundRect(X - 24, y - 56, 48, 18, [10, 10, 0, 0]); g.fill();
    g.fillStyle = "#1e2a4a"; g.beginPath(); g.roundRect(X - 17, y - 49, 34, 30, 7); g.fill();
    g.fillStyle = "#fff"; g.fillRect(X - 10, y - 41, 5, 7); g.fillRect(X + 5, y - 41, 5, 7);
    g.strokeStyle = "#fff"; g.lineWidth = 2; g.beginPath(); g.arc(X, y - 30, 6, 0.2, Math.PI - 0.2); g.stroke();
  }
  const steuer = takt(1000 / 30, logik, zeichne);
  return {
    taste(t, losgelassen) {
      if (losgelassen) return false;
      if (t === "Enter" || t === " " || t === "ArrowUp") { springen(); return true; }
      return t === "ArrowDown" || t === "ArrowLeft" || t === "ArrowRight";
    },
    stopp() { steuer.stopp(); },
  };
}

/* ------------------------------------------------------------ Ton-Kanone (6.8.1) */
const KANONE_TOENE = [["C", "#ff6b6b"], ["D", "#ffa94d"], ["E", "#ffd43b"], ["F", "#69db7c"], ["G", "#4dabf7"]];
const TON_ANZEIGE = { C: "C", D: "D", E: "E", F: "F", G: "G" };
function tonKanone(box, inhalt, punkte, hilfe, mik, fertig) {
  const B = Math.min(1200, Math.round(innerWidth * 0.86)), H = Math.round(B * 0.5);
  const canvas = el("canvas", { class: "spielfeld" });
  inhalt.replaceChildren(canvas);
  const g = canvasScharf(canvas, B, H);
  const spalte = (i) => B * (0.14 + i * 0.18);
  const z = { ballons: [], geplatzt: 0, wahl: 2, gehoert: null, gleich: 0, rest: RUNDE_S * 30, takt: 0, naechster: 20, knall: [] };
  hilfe.textContent = (mik ? "Sing den Ton des untersten Ballons · " : "") + "← → Ton · OK feuern · STOP Ende";
  function platzen(name) {
    const i = KANONE_TOENE.findIndex(([n]) => n === name);
    const kandidaten = z.ballons.filter((b) => b.ton === i && !b.weg && b.y < H - 70).sort((a, b) => b.y - a.y);   /* nur sichtbare */
    if (!kandidaten.length) return false;
    const b = kandidaten[0];
    b.weg = true; z.geplatzt++;
    z.knall.push({ x: spalte(b.ton), y: b.y, t: 12 });
    return true;
  }
  function logik() {
    z.takt++;
    if (mik && z.takt % 3 === 0) {
      const { laut, hz } = mik.lies();
      const name = hz && laut > 0.04 ? naechsterTon(hz).name : null;
      if (name && name === z.gehoert) z.gleich++; else { z.gehoert = name; z.gleich = 0; }
      if (name && TON_ANZEIGE[name] && z.gleich === 4) { platzen(name); z.gleich = 0; }    /* ~1/3 Sekunde halten */
    }
    if (--z.naechster <= 0) { z.ballons.push({ ton: Math.floor(Math.random() * 5), y: H + 40, v: 1.1 + Math.random() * 0.6 }); z.naechster = 50 + Math.random() * 40; }
    for (const b of z.ballons) b.y -= b.v;
    z.ballons = z.ballons.filter((b) => !b.weg && b.y > -60);
    for (const k of z.knall) k.t--;
    z.knall = z.knall.filter((k) => k.t > 0);
    punkte.textContent = `🎈 ${z.geplatzt} · ⏱ ${Math.ceil(z.rest / 30)}` + (z.gehoert ? ` · 🎤 ${z.gehoert}` : "");
    if (--z.rest <= 0) fertig(`🎈 ${z.geplatzt} Ballons geplatzt!`, z.geplatzt);
  }
  /* 6.9.29: Abendhimmel mit Sternen und Hügeln einmal vorzeichnen */
  const hoch = stufe() === "hoch";
  const himmel = document.createElement("canvas"); himmel.width = B; himmel.height = H;
  { const h = himmel.getContext("2d");
    const v = h.createLinearGradient(0, 0, 0, H); v.addColorStop(0, "#1a2350"); v.addColorStop(0.7, "#4a3f86"); v.addColorStop(1, "#7a5a9a");
    h.fillStyle = v; h.fillRect(0, 0, B, H);
    for (let i = 0; i < 70; i++) { h.fillStyle = `rgba(255,255,255,${(0.2 + (i % 5) * 0.12).toFixed(2)})`; h.fillRect((i * 173) % B, (i * 97) % (H * 0.7), 2, 2); }
    h.fillStyle = "#2d2a5a"; h.beginPath(); h.moveTo(0, H);
    for (let x = 0; x <= B; x += 20) h.lineTo(x, H - 60 - Math.sin(x / B * Math.PI * 3) * 18); h.lineTo(B, H); h.fill(); }
  function zeichne() {
    g.drawImage(himmel, 0, 0);
    g.textAlign = "center"; g.textBaseline = "middle";
    for (const b of z.ballons) {
      const [name, farbe] = KANONE_TOENE[b.ton], x = spalte(b.ton) + (hoch ? Math.sin(b.y * 0.03 + b.ton) * 6 : 0);
      g.strokeStyle = "rgba(255,255,255,.5)"; g.lineWidth = 2;
      g.beginPath(); g.moveTo(x, b.y + 34); g.quadraticCurveTo(x - 6, b.y + 52, x, b.y + 70); g.stroke();
      g.fillStyle = farbe; g.beginPath(); g.ellipse(x, b.y, 28, 34, 0, 0, Math.PI * 2); g.fill();
      g.beginPath(); g.moveTo(x - 5, b.y + 33); g.lineTo(x + 5, b.y + 33); g.lineTo(x, b.y + 39); g.fill();
      g.fillStyle = "rgba(255,255,255,.45)"; g.beginPath(); g.ellipse(x - 10, b.y - 14, 6, 10, -0.4, 0, Math.PI * 2); g.fill();
      g.fillStyle = "#1e2a4a"; g.font = "bold 30px sans-serif"; g.fillText(name, x, b.y);
    }
    for (const k of z.knall) {
      g.strokeStyle = `rgba(255,255,255,${k.t / 12})`; g.lineWidth = 4;
      for (let a = 0; a < 8; a++) {
        const w = a * Math.PI / 4, r1 = 20 + (12 - k.t) * 3, r2 = r1 + 14;
        g.beginPath(); g.moveTo(k.x + Math.cos(w) * r1, k.y + Math.sin(w) * r1); g.lineTo(k.x + Math.cos(w) * r2, k.y + Math.sin(w) * r2); g.stroke();
      }
    }
    /* Kanone unter der gewählten Spalte, Tonleiste unten */
    KANONE_TOENE.forEach(([name, farbe], i) => {                 /* Tasten wie beim Klavier */
      g.fillStyle = i === z.wahl ? farbe : "#f4f1ea";
      g.beginPath(); g.roundRect(spalte(i) - 40, H - 36, 80, 32, [4, 4, 10, 10]); g.fill();
      g.fillStyle = "rgba(0,0,0,.15)"; g.fillRect(spalte(i) - 40, H - 8, 80, 4);
      g.fillStyle = "#1e2a4a"; g.font = "bold 20px sans-serif"; g.fillText(name, spalte(i), H - 20);
    });
    const kx = spalte(z.wahl);                                    /* Kanone: Rohr mit Ring und Rädchen */
    g.fillStyle = "#5b6680"; g.beginPath(); g.roundRect(kx - 12, H - 74, 24, 40, 8); g.fill();
    g.fillStyle = "#8a97b4"; g.fillRect(kx - 14, H - 78, 28, 8);
    g.fillStyle = "#3b4566"; g.beginPath(); g.arc(kx - 16, H - 40, 8, 0, Math.PI * 2); g.arc(kx + 16, H - 40, 8, 0, Math.PI * 2); g.fill();
  }
  const steuer = takt(1000 / 30, logik, zeichne);
  return {
    taste(t, losgelassen) {
      if (losgelassen) return false;
      if (t === "ArrowLeft" || t === "ArrowRight") { z.wahl = (z.wahl + (t === "ArrowLeft" ? 4 : 1)) % 5; return true; }
      if (t === "Enter" || t === " ") { platzen(KANONE_TOENE[z.wahl][0]); return true; }
      return t === "ArrowUp" || t === "ArrowDown";
    },
    stopp() { steuer.stopp(); },
  };
}

export default {
  symbol: "🎤",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "🎤 Stimm-Spiele", "← → wählen · OK starten · STOP zurück");
    let mik = null, spiel = null, auswahl = null;
    const losgelassen = (e) => spiel?.taste(e.key, true);
    window.addEventListener("keyup", losgelassen);

    function menueZeigen(text = "Welches Spiel?") {
      spiel?.stopp(); spiel = null;
      hilfe.textContent = "← → wählen · OK starten · STOP zurück";
      punkte.textContent = "";
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text }),
        el("p", { class: "leise", text: mik ? "🎤 Mikro bereit – es hört nur zu, nichts wird aufgenommen." : "Ohne Mikro: mit den Pfeilen spielen." }));
      inhalt.replaceChildren(spalte);
      auswahl = menue(spalte, [
        { text: "🐦 Möwenflug", aktion: () => starte(moewenflug) },
        { text: "🐉 Pst – der Drache schläft", aktion: () => starte(drache) },
        { text: "👏 Klatsch-Läufer", aktion: () => starte(klatschLaeufer) },
        { text: "🎈 Ton-Kanone", aktion: () => starte(tonKanone) },
      ]);
    }
    function starte(art) {
      auswahl = null;
      spiel = art(box, inhalt, punkte, hilfe, mik, (text, wert) => {
        spiel?.stopp(); spiel = null;
        if (wert) { ton("sieg"); konfetti(box); }
        setTimeout(() => menueZeigen(text + " Nochmal?"), 400);
      });
    }
    inhalt.replaceChildren(el("p", { class: "punkte", text: "Einen Moment …" }));
    mikro().then((m) => { mik = m; menueZeigen(); });

    return {
      taste(t) {
        if (t === "Escape" || t === "Backspace") {
          if (spiel) { menueZeigen(); return true; }
          return false;
        }
        if (spiel) return spiel.taste(t, false);
        return auswahl ? auswahl.taste(t) : true;
      },
      schliesse() { spiel?.stopp(); mik?.stopp(); window.removeEventListener("keyup", losgelassen); },
    };
  },
};
