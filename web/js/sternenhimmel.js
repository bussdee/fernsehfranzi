/* FernsehFranzi 3.4 - Einschlafbild: sehr dunkler Sternenhimmel mit Mond, ab und zu eine Sternschnuppe
 * und ein Vogel, der langsam vorbeifliegt.
 *
 * Absichtlich dunkel (nichts heller als ~45 %), nur 10 Bilder pro Sekunde (der Pi 3 soll dabei kühl und leise bleiben).
 * starte(canvas) -> Funktion zum Beenden.
 */
const BILDER_PRO_S = 10;
const HELL = 0.45;              /* hellste Stelle (Mond), Sterne deutlich darunter */

export function starte(canvas) {
  const g = canvas.getContext("2d");
  let breite = 0, hoehe = 0, sterne = [], schnuppe = null, vogel = null;
  let naechsteSchnuppe = performance.now() + 15000 + Math.random() * 20000;
  let naechsterVogel = performance.now() + 40000 + Math.random() * 40000;
  let laeuft = true, timer = 0;

  function groesse() {
    const dpr = Math.min(1, window.devicePixelRatio || 1);      /* lieber unscharf als heiß */
    breite = canvas.clientWidth || innerWidth;
    hoehe = canvas.clientHeight || innerHeight;
    canvas.width = Math.round(breite * dpr);
    canvas.height = Math.round(hoehe * dpr);
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    sterne = Array.from({ length: 150 }, () => ({
      x: Math.random() * breite, y: Math.random() * hoehe * 0.85,
      r: Math.random() < 0.9 ? 0.6 + Math.random() * 0.8 : 1.4 + Math.random() * 0.6,
      grund: 0.06 + Math.random() * 0.22, tempo: 0.3 + Math.random() * 1.2, phase: Math.random() * 6.3,
    }));
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
    g.fillStyle = "#000";
    g.fillRect(0, 0, breite, hoehe);
    for (const s of sterne) {
      const a = s.grund * (0.6 + 0.4 * Math.sin(t * s.tempo + s.phase));
      g.fillStyle = `rgba(205,215,255,${a.toFixed(3)})`;
      g.beginPath(); g.arc(s.x, s.y, s.r, 0, Math.PI * 2); g.fill();
    }
    const m = mond(t);
    /* Sternschnuppe */
    if (!schnuppe && jetzt > naechsteSchnuppe) {
      schnuppe = { x: Math.random() * breite * 0.6, y: Math.random() * hoehe * 0.3, start: jetzt };
      naechsteSchnuppe = jetzt + 25000 + Math.random() * 35000;
    }
    if (schnuppe) {
      const p = (jetzt - schnuppe.start) / 1300;
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
  timer = setInterval(() => { if (!document.hidden) zeichne(performance.now()); }, 1000 / BILDER_PRO_S);
  zeichne(performance.now());
  return () => { laeuft = false; clearInterval(timer); window.removeEventListener("resize", neu); };
}
