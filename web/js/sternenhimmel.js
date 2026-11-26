/* FernsehFranzi 3.4 (6.8.12 sparsamer) - Einschlafbild: sehr dunkler Sternenhimmel mit Mond, ab und zu eine Sternschnuppe
 * und ein Vogel, der langsam vorbeifliegt.
 * 6.1: schöner - tiefblauer Verlauf statt Schwarz, zarte Milchstraße, Hügel mit Tannen und einem Häuschen mit warmem
 * Fenster, langsam ziehende Wolken, Sterne in leicht verschiedenen Farben. Der feste Hintergrund wird einmal
 * vorgezeichnet, je Bild kommen nur Sterne, Mond, Wolken und Schnuppe dazu.
 *
 * Absichtlich dunkel (nichts heller als ~45 %), nur 10 Bilder pro Sekunde (der Pi 3 soll dabei kühl und leise bleiben).
 * starte(canvas) -> Funktion zum Beenden.
 */
const STUFE = () => document.documentElement.dataset.animation || "sparsam";
const BILDER_PRO_S_STUFE = { hoch: 10, sparsam: 2, aus: 0 };
const BILDER_PRO_S = 2;          /* 6.8.12: 2 statt 10 - der Pi 3 drosselte beim Hörbuch; Funkeln braucht nicht mehr */
const AUFLOESUNG = 0.5;          /* 6.8.12: halbe Auflösung (ein Viertel der Pixel), der Browser skaliert hoch */
const HELL = 0.45;              /* hellste Stelle (Mond), Sterne deutlich darunter */

export function starte(canvas) {
  const g = canvas.getContext("2d");
  let breite = 0, hoehe = 0, sterne = [], schnuppe = null, vogel = null, hintergrund = null, wolken = [];
  let naechsteSchnuppe = performance.now() + 15000 + Math.random() * 20000;
  let naechsterVogel = performance.now() + 40000 + Math.random() * 40000;
  let laeuft = true, timer = 0;

  const dpr = () => (STUFE() === "hoch" ? 1 : AUFLOESUNG);
  function groesse() {
    const d = dpr();      /* lieber unscharf als heiß */
    breite = canvas.clientWidth || innerWidth;
    hoehe = canvas.clientHeight || innerHeight;
    canvas.width = Math.round(breite * d);
    canvas.height = Math.round(hoehe * d);
    g.setTransform(d, 0, 0, d, 0, 0);
    const FARBEN = ["205,215,255", "205,215,255", "205,215,255", "255,232,205", "190,210,255"];
    sterne = Array.from({ length: 170 }, () => ({
      x: Math.random() * breite, y: Math.pow(Math.random(), 1.4) * hoehe * 0.72,
      r: Math.random() < 0.9 ? 0.6 + Math.random() * 0.8 : 1.4 + Math.random() * 0.6,
      grund: 0.06 + Math.random() * 0.22, tempo: 0.3 + Math.random() * 1.2, phase: Math.random() * 6.3,
      farbe: FARBEN[Math.floor(Math.random() * FARBEN.length)],
    }));
    wolken = Array.from({ length: 3 }, (_, i) => ({ x: Math.random() * breite, y: hoehe * (0.12 + i * 0.13),
      s: 0.7 + Math.random() * 0.6, tempo: 3 + Math.random() * 3 }));
    hintergrund = vorzeichnen();
  }

  /* fester Hintergrund: Verlauf, Milchstraße, Hügel, Tannen, Häuschen - einmal je Größe */
  function vorzeichnen() {
    const c = document.createElement("canvas");
    c.width = Math.max(1, Math.round(breite * dpr())); c.height = Math.max(1, Math.round(hoehe * dpr()));
    const h = c.getContext("2d");
    h.setTransform(dpr(), 0, 0, dpr(), 0, 0);
    const himmel = h.createLinearGradient(0, 0, 0, hoehe);
    himmel.addColorStop(0, "#000000"); himmel.addColorStop(0.55, "#000105"); himmel.addColorStop(0.85, "#01030a");
    h.fillStyle = himmel; h.fillRect(0, 0, breite, hoehe);
    /* Milchstraße: schräges, sehr schwaches Band aus Schleiern und winzigen Punkten */
    for (let i = 0; i < 16; i++) {
      const t = i / 15, x = breite * (0.05 + t * 0.9), y = hoehe * (0.62 - t * 0.5);
      const r = Math.min(breite, hoehe) * (0.12 + Math.random() * 0.08);
      const s = h.createRadialGradient(x, y, 0, x, y, r);
      s.addColorStop(0, "rgba(150,160,220,0.014)"); s.addColorStop(1, "rgba(150,160,220,0)");
      h.fillStyle = s; h.fillRect(x - r, y - r, r * 2, r * 2);
    }
    for (let i = 0; i < 500; i++) {
      const t = Math.random(), x = breite * (0.05 + t * 0.9) + (Math.random() - 0.5) * breite * 0.12;
      const y = hoehe * (0.62 - t * 0.5) + (Math.random() - 0.5) * hoehe * 0.12;
      h.fillStyle = `rgba(200,210,255,${(0.04 + Math.random() * 0.08).toFixed(3)})`;
      h.fillRect(x, y, 1, 1);
    }
    /* Hügel: zwei Schichten, die hintere einen Hauch heller */
    const huegel = (basis, hoehe2, farbe, phase) => {
      h.fillStyle = farbe; h.beginPath(); h.moveTo(0, hoehe);
      for (let x = 0; x <= breite; x += 20) h.lineTo(x, basis - hoehe2 * (0.5 + 0.5 * Math.sin(x / breite * Math.PI * 2.2 + phase)));
      h.lineTo(breite, hoehe); h.closePath(); h.fill();
    };
    huegel(hoehe * 0.86, hoehe * 0.07, "#010307", 0.6);
    huegel(hoehe * 0.93, hoehe * 0.05, "#000103", 2.4);
    /* Tannen am Rand */
    h.fillStyle = "#010307";
    const tanne = (x, y, s) => { h.beginPath(); h.moveTo(x, y - 70 * s); h.lineTo(x - 18 * s, y); h.lineTo(x + 18 * s, y); h.closePath(); h.fill(); };
    for (let i = 0; i < 7; i++) tanne(breite * 0.02 + i * breite * 0.035, hoehe * (0.93 + Math.random() * 0.02), 0.8 + Math.random() * 0.6);
    for (let i = 0; i < 5; i++) tanne(breite * 0.8 + i * breite * 0.04, hoehe * (0.92 + Math.random() * 0.02), 0.8 + Math.random() * 0.5);
    /* Häuschen mit einem warmen, gedimmten Fenster */
    const hx = breite * 0.62, hy = hoehe * 0.905, hb = Math.min(breite, hoehe) * 0.06;
    h.fillStyle = "#02040a";
    h.fillRect(hx, hy - hb * 0.7, hb, hb * 0.7);
    h.beginPath(); h.moveTo(hx - hb * 0.12, hy - hb * 0.7); h.lineTo(hx + hb / 2, hy - hb * 1.15); h.lineTo(hx + hb * 1.12, hy - hb * 0.7); h.closePath(); h.fill();
    const fenster = h.createRadialGradient(hx + hb * 0.5, hy - hb * 0.38, 0, hx + hb * 0.5, hy - hb * 0.38, hb * 0.6);
    fenster.addColorStop(0, "rgba(255,180,100,0.10)"); fenster.addColorStop(1, "rgba(255,180,100,0)");
    h.fillStyle = fenster; h.fillRect(hx - hb, hy - hb * 1.2, hb * 3, hb * 1.5);
    h.fillStyle = "rgba(255,190,110,0.28)";
    h.fillRect(hx + hb * 0.38, hy - hb * 0.5, hb * 0.24, hb * 0.2);
    return c;
  }

  function wolke(w, t) {
    const x = ((w.x + t * w.tempo) % (breite + 400)) - 200, r = 60 * w.s;
    g.fillStyle = "rgba(120,135,190,0.022)";
    for (const [dx, dy, f] of [[0, 0, 1], [-0.9, 0.25, 0.7], [0.9, 0.25, 0.75], [-0.4, -0.3, 0.7], [0.45, -0.25, 0.65]]) {
      g.beginPath(); g.ellipse(x + dx * r, w.y + dy * r * 0.6, r * f, r * f * 0.55, 0, 0, Math.PI * 2); g.fill();
    }
  }

  /* Mondsichel einmal vorzeichnen: Scheibe, davon ein Kreis ausgestanzt (durchsichtig - der Schein bleibt rund) */
  let sichel = null;
  function mondVorzeichnen(r) {
    sichel = document.createElement("canvas");
    sichel.width = sichel.height = Math.ceil(r * 2 + 4);
    const m = sichel.getContext("2d"), c = r + 2;
    const flaeche = m.createRadialGradient(c + r * 0.3, c, r * 0.2, c, c, r);
    flaeche.addColorStop(0, `rgba(240,234,205,${HELL})`);
    flaeche.addColorStop(1, `rgba(205,198,165,${HELL * 0.85})`);
    m.fillStyle = flaeche;
    m.beginPath(); m.arc(c, c, r, 0, Math.PI * 2); m.fill();
    m.globalCompositeOperation = "destination-out";
    m.fillStyle = "#000";                                       /* voll deckend ausstanzen */
    m.beginPath(); m.arc(c - r * 0.45, c - r * 0.15, r * 0.9, 0, Math.PI * 2); m.fill();
  }

  function mond(t) {
    const x = breite * 0.8, y = hoehe * 0.22, r = Math.min(breite, hoehe) * 0.07;
    if (!sichel || sichel.width !== Math.ceil(r * 2 + 4)) mondVorzeichnen(r);
    const schein = g.createRadialGradient(x + r * 0.3, y, r * 0.6, x, y, r * 3.5);
    schein.addColorStop(0, "rgba(180,190,230,0.05)");
    schein.addColorStop(1, "rgba(180,190,230,0)");
    g.fillStyle = schein;
    g.fillRect(x - r * 4, y - r * 4, r * 8, r * 8);
    g.drawImage(sichel, x - r - 2, y - r - 2);
    return { x, y, r, t };
  }

  function zeichne(jetzt) {
    if (!laeuft) return;
    const t = jetzt / 1000;
    if (hintergrund) g.drawImage(hintergrund, 0, 0, breite, hoehe);
    else { g.fillStyle = "#000"; g.fillRect(0, 0, breite, hoehe); }
    for (const s of sterne) {
      const a = s.grund * (0.6 + 0.4 * Math.sin(t * s.tempo + s.phase));
      g.fillStyle = `rgba(${s.farbe},${a.toFixed(3)})`;
      g.beginPath(); g.arc(s.x, s.y, s.r, 0, Math.PI * 2); g.fill();
    }
    const m = mond(t);
    /* 6.9.22: Stufe „hoch“ - ein paar sehr schwache Glühwürmchen über den Hügeln (bleibt dunkel) */
    if (STUFE() === "hoch") {
      for (let i = 0; i < 7; i++) {
        const gx = breite * (0.1 + ((i * 0.137) % 0.8)) + Math.sin(t * 0.3 + i * 2) * 30;
        const gy = hoehe * (0.8 + (i % 3) * 0.03) + Math.cos(t * 0.4 + i) * 12;
        const a = 0.12 + 0.12 * Math.max(0, Math.sin(t * 0.9 + i * 1.7));
        g.fillStyle = `rgba(210,255,150,${a.toFixed(3)})`;
        g.beginPath(); g.arc(gx, gy, 1.8, 0, Math.PI * 2); g.fill();
      }
    }
    for (const w of wolken) wolke(w, t);
    /* Sternschnuppe */
    if (!schnuppe && jetzt > naechsteSchnuppe) {
      schnuppe = { x: Math.random() * breite * 0.6, y: Math.random() * hoehe * 0.3, start: jetzt };
      naechsteSchnuppe = jetzt + 25000 + Math.random() * 35000;
    }
    if (schnuppe) {
      const p = (jetzt - schnuppe.start) / 3000;
      if (p >= 1) schnuppe = null;
      else {
        const x = schnuppe.x + p * breite * 0.25, y = schnuppe.y + p * hoehe * 0.12;
        const verlauf = g.createLinearGradient(x, y, x - 90, y - 43);
        verlauf.addColorStop(0, `rgba(220,230,255,${(0.4 * (1 - p)).toFixed(3)})`);
        verlauf.addColorStop(1, "rgba(220,230,255,0)");
        g.strokeStyle = verlauf; g.lineWidth = 1.6;
        g.beginPath(); g.moveTo(x, y); g.lineTo(x - 90, y - 43); g.stroke();
      }
    }
    /* Vogel: dunkler Schattenriss, fliegt langsam von rechts nach links am Mond vorbei */
    if (!vogel && jetzt > naechsterVogel) {
      vogel = { start: jetzt, y: m.y + (Math.random() - 0.5) * m.r * 1.5 };
      naechsterVogel = jetzt + 70000 + Math.random() * 60000;
    }
    if (vogel) {
      const p = (jetzt - vogel.start) / 22000;
      if (p >= 1) vogel = null;
      else {
        const x = breite * (1.05 - p * 1.2), y = vogel.y + Math.sin(p * 9) * 12;
        const schlag = Math.sin(t * 5) * 7, w = 16;
        g.strokeStyle = "rgba(120,130,170,0.35)"; g.lineWidth = 2; g.lineCap = "round";
        g.beginPath();
        g.moveTo(x - w, y - schlag); g.quadraticCurveTo(x - w / 2, y - 4 - schlag / 2, x, y);
        g.quadraticCurveTo(x + w / 2, y - 4 - schlag / 2, x + w, y - schlag);
        g.stroke();
      }
    }
  }

  groesse();
  const neu = () => groesse();
  window.addEventListener("resize", neu);
  /* 6.8.12: Stufe aus = ein stilles Bild, sparsam = 2, hoch = 10 Bilder pro Sekunde */
  const bps = BILDER_PRO_S_STUFE[STUFE()] ?? BILDER_PRO_S;
  if (bps) timer = setInterval(() => { if (!document.hidden) zeichne(performance.now()); }, 1000 / bps);
  zeichne(performance.now());
  return () => { laeuft = false; clearInterval(timer); window.removeEventListener("resize", neu); };
}
