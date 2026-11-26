/* FernsehFranzi 6.6 (6.9.25: Amsel, Kuckuck, Stereo im Wald) - Geräusche der Weckszenen, selbst erzeugt (keine fremden Dateien):
 *   ostsee: Wellenrauschen (gefiltertes Rauschen, das langsam an- und abschwillt) und ab und zu Möwen
 *   wald:   leiser Wind in den Bäumen und Vogelzwitschern
 * Alles wird über die Dauer des Sonnenaufgangs sanft lauter (von still bis ZIEL), damit niemand erschrickt.
 * starte(szene, dauerMs) -> Funktion zum Beenden (oder null, wenn die Szene keine Geräusche hat).
 */
const ZIEL = 0.35;

function rauschen(ac, sekunden = 3) {
  const puffer = ac.createBuffer(1, ac.sampleRate * sekunden, ac.sampleRate);
  const d = puffer.getChannelData(0);
  let braun = 0;
  for (let i = 0; i < d.length; i++) {        /* braunes Rauschen klingt weicher als weißes */
    braun = (braun + 0.02 * (Math.random() * 2 - 1)) / 1.02;
    d[i] = braun * 3.5;
  }
  const quelle = ac.createBufferSource();
  quelle.buffer = puffer;
  quelle.loop = true;
  return quelle;
}

function zwitschern(ac, ziel, t, { von = 2600, bis = 3800, anzahl = 4, laut = 0.12 } = {}) {
  for (let i = 0; i < anzahl; i++) {
    const o = ac.createOscillator(), g = ac.createGain(), s = t + i * (0.11 + Math.random() * 0.08);
    const f = von + Math.random() * (bis - von);
    o.type = "sine";
    o.frequency.setValueAtTime(f, s);
    o.frequency.exponentialRampToValueAtTime(f * (1.2 + Math.random() * 0.4), s + 0.06);
    o.frequency.exponentialRampToValueAtTime(f * 0.9, s + 0.1);
    g.gain.setValueAtTime(0.0001, s);
    g.gain.exponentialRampToValueAtTime(laut, s + 0.015);
    g.gain.exponentialRampToValueAtTime(0.0001, s + 0.1);
    o.connect(g).connect(ziel);
    o.start(s);
    o.stop(s + 0.12);
  }
}

function moewe(ac, ziel, t) {
  for (let i = 0; i < 2 + Math.floor(Math.random() * 2); i++) {
    const o = ac.createOscillator(), filter = ac.createBiquadFilter(), g = ac.createGain(), s = t + i * 0.42;
    o.type = "sawtooth";
    o.frequency.setValueAtTime(1500, s);
    o.frequency.exponentialRampToValueAtTime(950, s + 0.32);
    filter.type = "bandpass"; filter.frequency.value = 1400; filter.Q.value = 3;
    g.gain.setValueAtTime(0.0001, s);
    g.gain.exponentialRampToValueAtTime(0.09, s + 0.05);
    g.gain.exponentialRampToValueAtTime(0.0001, s + 0.34);
    o.connect(filter).connect(g).connect(ziel);
    o.start(s);
    o.stop(s + 0.36);
  }
}

/* 6.9.25: Ruf von links oder rechts (Stereo) - jeder Vogel sitzt woanders */
function seite(ac, ziel) {
  try { const p = ac.createStereoPanner(); p.pan.value = Math.random() * 1.6 - 0.8; p.connect(ziel); return p; } catch (_) { return ziel; }
}

/** Amsel: kleine Melodie aus 5-8 gleitenden Tönen (eigene Erfindung, klingt nach Frühlingsmorgen) */
function amsel(ac, ziel, t) {
  const aus = seite(ac, ziel);
  let s = t, f = 1500 + Math.random() * 500;
  for (let i = 0; i < 5 + Math.floor(Math.random() * 4); i++) {
    const o = ac.createOscillator(), g = ac.createGain(), lang = 0.1 + Math.random() * 0.16;
    const naechste = Math.max(1100, Math.min(2800, f * (0.8 + Math.random() * 0.5)));
    o.type = "sine";
    o.frequency.setValueAtTime(f, s); o.frequency.exponentialRampToValueAtTime(naechste, s + lang);
    g.gain.setValueAtTime(0.0001, s); g.gain.exponentialRampToValueAtTime(0.07, s + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, s + lang);
    o.connect(g).connect(aus); o.start(s); o.stop(s + lang + 0.02);
    f = naechste; s += lang + 0.03 + Math.random() * 0.06;
  }
}

/** Kuckuck in der Ferne: zwei weiche Töne, leise */
function kuckuck(ac, ziel, t) {
  const aus = seite(ac, ziel);
  for (const [f, s] of [[680, 0], [560, 0.38]]) {
    const o = ac.createOscillator(), g = ac.createGain();
    o.type = "sine"; o.frequency.setValueAtTime(f, t + s); o.frequency.linearRampToValueAtTime(f * 0.97, t + s + 0.28);
    g.gain.setValueAtTime(0.0001, t + s); g.gain.exponentialRampToValueAtTime(0.05, t + s + 0.04); g.gain.exponentialRampToValueAtTime(0.0001, t + s + 0.3);
    o.connect(g).connect(aus); o.start(t + s); o.stop(t + s + 0.32);
  }
}

export function starte(szene, dauerMs) {
  if (szene !== "ostsee" && szene !== "wald") return null;            /* Hügel bleibt bewusst still (6.6) */
  let ac;
  try { ac = new AudioContext(); } catch (_) { return null; }
  const haupt = ac.createGain();
  haupt.gain.setValueAtTime(0.0001, ac.currentTime);
  haupt.gain.exponentialRampToValueAtTime(ZIEL, ac.currentTime + Math.max(5, dauerMs / 1000));
  haupt.connect(ac.destination);

  const grund = rauschen(ac), filter = ac.createBiquadFilter(), welle = ac.createGain();
  if (szene === "ostsee") { filter.type = "lowpass"; filter.frequency.value = 700; welle.gain.value = 0.5; }
  else { filter.type = "bandpass"; filter.frequency.value = 450; filter.Q.value = 0.6; welle.gain.value = 0.18; }
  grund.connect(filter).connect(welle).connect(haupt);
  grund.start();

  let naechsteWelle = ac.currentTime, naechsterRuf = ac.currentTime + 3;
  const takt = setInterval(() => {               /* Ereignisse immer ein Stück im Voraus planen */
    const t = ac.currentTime;
    if (szene === "ostsee" && t + 1 > naechsteWelle) {
      const lang = 5 + Math.random() * 3;
      welle.gain.setTargetAtTime(0.75 + Math.random() * 0.25, naechsteWelle, lang * 0.25);
      welle.gain.setTargetAtTime(0.25, naechsteWelle + lang * 0.5, lang * 0.2);
      naechsteWelle += lang;
    }
    if (t + 1 > naechsterRuf) {
      const w = Math.random();
      if (szene === "ostsee") moewe(ac, haupt, naechsterRuf);
      else if (w < 0.05) kuckuck(ac, haupt, naechsterRuf);
      else if (w < 0.32) amsel(ac, haupt, naechsterRuf);
      else zwitschern(ac, seite(ac, haupt), naechsterRuf, { anzahl: 3 + Math.floor(Math.random() * 5) });
      naechsterRuf += szene === "ostsee" ? 7 + Math.random() * 10 : 1.5 + Math.random() * 4;
    }
  }, 500);
  if (ac.state === "suspended") ac.resume().catch(() => {});
  return () => { clearInterval(takt); try { ac.close(); } catch (_) { /* schon zu */ } };
}
