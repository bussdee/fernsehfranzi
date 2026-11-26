/* FernsehFranzi 3.0 - gemeinsamer Spiele-Kern.
 *
 * - takt(): requestAnimationFrame mit festem Logiktakt und Zwischenwert für weiche Bewegung
 * - ton(): kurze Töne über WebAudio (keine Dateien)
 * - kopf(): Überschrift + Hilfezeile für jedes Spiel
 * - canvasScharf(): Canvas in echter Bildschirmauflösung (kein CSS-Skalieren)
 */
import { el, mitBild, franzi, franziBlinken } from "../gemeinsam.js";

let audio = null;
const TOENE = {
  bewegen: [[520, 0.03]], ok: [[660, 0.07], [880, 0.09]], fehler: [[220, 0.15]],
  anschlag: [[140, 0.06]], punkt: [[880, 0.06]], sieg: [[523, 0.1], [659, 0.1], [784, 0.1], [1046, 0.2]],
  verloren: [[392, 0.15], [330, 0.15], [262, 0.3]],
  /* Farben-Echo: A-Dur-Dreiklang mit Oktave - gut nach Gehör zu unterscheiden */
  /* 6.2: Zahnputz-Lied (Mein Tag) - vier kurze, fröhliche Takte in C-Dur, im Wechsel gespielt */
  lied1: [[523, 0.22], [659, 0.22], [784, 0.22], [659, 0.3]], lied2: [[587, 0.22], [698, 0.22], [880, 0.22], [698, 0.3]],
  lied3: [[659, 0.22], [784, 0.22], [1046, 0.3], [784, 0.22]], lied4: [[784, 0.22], [659, 0.22], [587, 0.22], [523, 0.35]],
  rot: [[220, 0.45]], gruen: [[277.2, 0.45]], gelb: [[329.6, 0.45]], blau: [[440, 0.45]],
  /* 6.9.21: Nachtruhe - leise und weich */
  leise: [[392, 0.18]], glocke: [[784, 0.5], [1176, 0.4]],
};
/* 6.8.3: Klänge je Welt - [Frequenz, Dauer, Zielfrequenz?]; ersetzen nur die Bedien-Töne, nicht die Spiel-Töne */
const WELT_TOENE = {
  rock: { typ: "sawtooth", laut: 0.45, bewegen: [[196, 0.05]], ok: [[196, 0.07], [294, 0.12]], fehler: [[110, 0.2]],
          sieg: [[196, 0.1], [247, 0.1], [294, 0.1], [392, 0.3]] },
  unterwasser: { typ: "sine", laut: 1.1, bewegen: [[700, 0.06, 350]], ok: [[500, 0.08, 900], [700, 0.1, 1200]], fehler: [[300, 0.2, 150]],
                 sieg: [[400, 0.1, 800], [500, 0.1, 1000], [600, 0.25, 1400]] },
  raumstation: { typ: "square", laut: 0.35, bewegen: [[1320, 0.03]], ok: [[880, 0.05], [1760, 0.08]], fehler: [[220, 0.18, 110]],
                 sieg: [[523, 0.07], [784, 0.07], [1046, 0.07], [1568, 0.25]] },
};
const LAUT = 0.28;          /* vorher 0.12 - am Fernseher/über die Klinke war es zu leise */

/* 6.9.24: gemeinsamer Ausgang für alle Töne - Kompressor (nichts übersteuert, auch wenn viele Töne zusammenkommen)
   und ein leichtes Echo für etwas Raum. Wird einmal gebaut. */
let ausgang = null;
function bus() {
  if (ausgang) return ausgang;
  const komp = audio.createDynamicsCompressor();
  komp.threshold.value = -18; komp.knee.value = 12; komp.ratio.value = 4; komp.attack.value = 0.004; komp.release.value = 0.2;
  const sanft = audio.createBiquadFilter();                    /* nimmt die harte Spitze aus Dreieck/Rechteck */
  sanft.type = "lowpass"; sanft.frequency.value = 5200;
  const echo = audio.createDelay(0.5), rueck = audio.createGain(), nass = audio.createGain();
  echo.delayTime.value = 0.13; rueck.gain.value = 0.22; nass.gain.value = 0.16;
  sanft.connect(komp);
  sanft.connect(echo); echo.connect(rueck).connect(echo); echo.connect(nass).connect(komp);
  komp.connect(audio.destination);
  ausgang = sanft;
  return ausgang;
}

/* 6.9.40: Klang je Ereignis (Eltern-Seite → Aussehen → Klänge). Leer = eingebauter Ton, "stumm" = still, sonst eine
   Datei vom Server (Archiv-Klang oder eigener Klang aus einem Klang-Ordner). Bedienung kann leiser gestellt werden. */
let klangWahl = { ereignisse: {}, bedienung_laut: 100 };
const BEDIENUNG = { bewegen: "tasten", anschlag: "tasten", ok: "ok", fehler: "fehler" };
const klangDateien = new Map();
export function setzeKlaenge(k) {
  klangWahl = { ereignisse: (k && k.ereignisse) || {}, bedienung_laut: k && Number.isInteger(k.bedienung_laut) ? k.bedienung_laut : 100 };
}
function spieleDatei(id, laut) {
  let a = klangDateien.get(id);
  if (!a) { a = new Audio("/api/klang?id=" + encodeURIComponent(id)); a.preload = "auto"; klangDateien.set(id, a); }
  a.volume = Math.max(0, Math.min(1, laut));
  try { a.currentTime = 0; } catch (_) { /* noch nicht geladen */ }
  a.play().catch(() => { /* ohne Ton weiter */ });
}
/** Ereignis-Klang (stern, geschafft, franzi, kauf): Wahl der Eltern, sonst der eingebaute Ton `ersatz`. */
/* 6.9.57: Franzis Antennen zeigen richtig (grün) / falsch (rot) */
const BLINK = { stern: "gruen", geschafft: "gruen", franzi: "gruen", kauf: "gruen", fehler: "rot", sieg: "gruen", punkt: "gruen", verloren: "rot" };

export function ereignis(id, ersatz) {
  franziBlinken(BLINK[id]);
  const k = klangWahl.ereignisse[id];
  if (k === "stumm") return;
  if (k) { spieleDatei(k, 1); return; }
  ton(ersatz);
}

export function ton(art, { dauer = null, laut = LAUT, faktor = 1 } = {}) {   /* 6.9.16: faktor = Tonhöhe (Combo) */
  if (art === "fehler" || art === "sieg" || art === "verloren") franziBlinken(BLINK[art]);
  const bed = BEDIENUNG[art];
  if (bed) {
    const k = klangWahl.ereignisse[bed], anteil = klangWahl.bedienung_laut / 100;
    if (k === "stumm" || anteil <= 0) return;
    if (k) { spieleDatei(k, anteil); return; }
    laut *= anteil;
  }
  try {
    audio = audio || new AudioContext();
    let t = audio.currentTime;
    const welt = WELT_TOENE[document.body?.dataset.thema];
    const eigen = welt && welt[art];
    if (eigen) laut *= welt.laut;
    const ziel_ = bus();
    for (const [frequenz, laenge, ziel] of eigen || TOENE[art] || []) {
      const dauerHier = dauer ?? laenge;
      const pegel = audio.createGain();
      /* Grundton + (ohne Welt-Klang) ein leiser Oberton eine Oktave höher - klingt runder, fast wie eine kleine Glocke */
      const teile = eigen ? [[1, 1, welt.typ]] : [[1, 1, "triangle"], [2, 0.18, "sine"]];
      for (const [mal, anteil, typ] of teile) {
        const osz = audio.createOscillator(), teilPegel = audio.createGain();
        osz.type = typ;
        osz.frequency.setValueAtTime(frequenz * faktor * mal, t);
        if (ziel) osz.frequency.exponentialRampToValueAtTime(ziel * faktor * mal, t + dauerHier);
        teilPegel.gain.value = anteil;
        osz.connect(teilPegel).connect(pegel);
        osz.start(t);
        osz.stop(t + dauerHier + 0.08);
      }
      pegel.gain.setValueAtTime(0.0001, t);
      pegel.gain.exponentialRampToValueAtTime(laut, t + 0.012);
      pegel.gain.setValueAtTime(laut, t + dauerHier * 0.45);
      pegel.gain.exponentialRampToValueAtTime(0.0001, t + dauerHier + 0.06);       /* weich ausklingen */
      pegel.connect(ziel_);
      t += dauerHier * 0.9;
    }
  } catch (_) { /* ohne Ton weiter */ }
}

/** Fester Logiktakt (schritt in ms) + zeichne(anteil 0..1). Pausiert bei verstecktem Fenster. */
export function takt(schritt, logik, zeichne) {
  let laeuft = true, rest = 0, zuletzt = performance.now(), id = 0;
  const steuerung = {
    schritt,
    pausiert: false,
    stopp() { laeuft = false; cancelAnimationFrame(id); },
  };
  function rahmen(jetzt) {
    if (!laeuft) return;
    const delta = Math.min(250, jetzt - zuletzt);
    zuletzt = jetzt;
    if (!steuerung.pausiert && !document.hidden) {
      rest += delta;
      while (rest >= steuerung.schritt) { rest -= steuerung.schritt; logik(); if (!laeuft) return; }
    }
    zeichne(steuerung.pausiert ? 0 : rest / steuerung.schritt);
    id = requestAnimationFrame(rahmen);
  }
  id = requestAnimationFrame(rahmen);
  return steuerung;
}

export function kopf(box, titel, hilfe) {
  const hilfeKnoten = el("div", { class: "hilfe", text: hilfe });
  const punkte = el("div", { class: "punkte" });
  box.append(el("div", { class: "overlay-kopf" }, el("h2", {}, ...mitBild(titel, "icon kopf-icon")), punkte, hilfeKnoten));
  const inhalt = el("div", { class: "overlay-inhalt" });
  box.append(inhalt);
  return { inhalt, punkte, hilfe: hilfeKnoten };
}

export function canvasScharf(canvas, breite, hoehe) {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(breite * dpr);
  canvas.height = Math.round(hoehe * dpr);
  canvas.style.width = breite + "px";
  canvas.style.height = hoehe + "px";
  const g = canvas.getContext("2d");
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  return g;
}

/** Auswahl-Menü aus Knöpfen (links/rechts/hoch/runter, OK). Rückgabe {taste, knoepfe}. */
export function menue(box, eintraege, gewaehlt = 0) {
  const reihe = el("div", { class: "knopfreihe gross" });            /* 6.0: Auswahl groß wie Kacheln */
  const knoepfe = eintraege.map((e, i) => {
    const k = el("button", { class: "knopf", type: "button", tabindex: "-1", text: e.text });
    k.addEventListener("click", () => e.aktion());
    reihe.append(k);
    return k;
  });
  box.append(reihe);
  let i = gewaehlt;
  const zeige = () => knoepfe.forEach((k, n) => k.classList.toggle("gewaehlt", n === i));
  zeige();
  return {
    knoepfe,
    taste(t) {
      if (t === "ArrowLeft" || t === "ArrowUp") { i = (i + knoepfe.length - 1) % knoepfe.length; zeige(); ton("bewegen"); return true; }
      if (t === "ArrowRight" || t === "ArrowDown") { i = (i + 1) % knoepfe.length; zeige(); ton("bewegen"); return true; }
      if (t === "Enter" || t === " ") { eintraege[i].aktion(); return true; }
      if (/^[1-9]$/.test(t) && eintraege[+t - 1]) { eintraege[+t - 1].aktion(); return true; }
      return false;
    },
  };
}

export function konfetti(box) {
  const canvas = el("canvas", { style: "position:fixed;inset:0;pointer-events:none;z-index:35" });
  box.append(canvas);
  const g = canvasScharf(canvas, innerWidth, innerHeight);
  const teile = Array.from({ length: 90 }, () => ({
    x: Math.random() * innerWidth, y: -20 - Math.random() * innerHeight * 0.5,
    v: 2 + Math.random() * 4, f: `hsl(${Math.random() * 360} 90% 60%)`, s: 6 + Math.random() * 6,
  }));
  let n = 0;
  const schritt = () => {
    g.clearRect(0, 0, innerWidth, innerHeight);
    for (const t of teile) { t.y += t.v; g.fillStyle = t.f; g.fillRect(t.x, t.y, t.s, t.s * 0.6); }
    if (++n < 150) requestAnimationFrame(schritt); else canvas.remove();
  };
  requestAnimationFrame(schritt);
  /* 6.0: Franzi jubelt mit */
  const f = franzi("jubel", "franzi-konfetti");   /* 6.9.8: eigene Klasse - „franzi-jubel“ trägt jede jubelnde Franzi */
  box.append(f);
  setTimeout(() => f.remove(), 2600);
}
