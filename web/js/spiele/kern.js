/* FernsehFranzi 3.0 - gemeinsamer Spiele-Kern.
 *
 * - takt(): requestAnimationFrame mit festem Logiktakt und Zwischenwert für weiche Bewegung
 * - ton(): kurze Töne über WebAudio (keine Dateien)
 * - kopf(): Überschrift + Hilfezeile für jedes Spiel
 * - canvasScharf(): Canvas in echter Bildschirmauflösung (kein CSS-Skalieren)
 */
import { el, mitBild, franzi } from "../gemeinsam.js";

let audio = null;
const TOENE = {
  bewegen: [[520, 0.03]], ok: [[660, 0.07], [880, 0.09]], fehler: [[220, 0.15]],
  anschlag: [[140, 0.06]], punkt: [[880, 0.06]], sieg: [[523, 0.1], [659, 0.1], [784, 0.1], [1046, 0.2]],
  verloren: [[392, 0.15], [330, 0.15], [262, 0.3]],
  /* Farben-Echo: A-Dur-Dreiklang mit Oktave - gut nach Gehör zu unterscheiden */
  rot: [[220, 0.45]], gruen: [[277.2, 0.45]], gelb: [[329.6, 0.45]], blau: [[440, 0.45]],
};
const LAUT = 0.28;          /* vorher 0.12 - am Fernseher/über die Klinke war es zu leise */

export function ton(art, { dauer = null, laut = LAUT } = {}) {
  try {
    audio = audio || new AudioContext();
    let t = audio.currentTime;
    for (const [frequenz, laenge] of TOENE[art] || []) {
      const dauerHier = dauer ?? laenge;
      const osz = audio.createOscillator();
      const pegel = audio.createGain();
      osz.frequency.value = frequenz;
      osz.type = "triangle";
      pegel.gain.setValueAtTime(0.0001, t);
      pegel.gain.exponentialRampToValueAtTime(laut, t + 0.01);
      pegel.gain.setValueAtTime(laut, t + dauerHier * 0.6);
      pegel.gain.exponentialRampToValueAtTime(0.0001, t + dauerHier);
      osz.connect(pegel).connect(audio.destination);
      osz.start(t);
      osz.stop(t + dauerHier + 0.02);
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
  const f = franzi("jubel", "franzi-jubel");
  box.append(f);
  setTimeout(() => f.remove(), 2600);
}
