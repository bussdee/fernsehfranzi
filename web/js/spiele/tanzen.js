/* FernsehFranzi 6.9.50 - Takt aus der laufenden Musik (für Franzis Tanz zur Musikbox).
 *
 * Einfacher Schlag-Erkenner: Die Energie der tiefen Töne (Bass/Trommel) wird ~20-mal je Sekunde gemessen und mit ihrem
 * gleitenden Mittel verglichen. Liegt sie deutlich darüber und ist der letzte Schlag lange genug her, ist es ein Schlag.
 * Findet er eine Weile keinen (leise Musik, Hörspiel), gibt er im ruhigen Takt (~100/min) trotzdem Schläge, damit Franzi
 * weitertanzt. Läuft nur, solange Musik spielt und die Seite sichtbar ist (Pi 3).
 */
const MESS_MS = 50, MIN_ABSTAND_MS = 300, ERSATZ_MS = 600, FAKTOR = 1.35, MINDEST = 0.04;

let kontext = null;
const quellen = new WeakMap();

/** startet die Messung an einem <audio>; beiSchlag(staerke 0..1) je Schlag. Rückgabe: stopp() */
export function taktFolgen(audio, beiSchlag) {
  let analyse = null, daten = null;
  try {
    kontext = kontext || new AudioContext();
    if (kontext.state === "suspended") kontext.resume().catch(() => {});
    let quelle = quellen.get(audio);
    if (!quelle) { quelle = kontext.createMediaElementSource(audio); quellen.set(audio, quelle); quelle.connect(kontext.destination); }
    analyse = kontext.createAnalyser();
    analyse.fftSize = 512;
    analyse.smoothingTimeConstant = 0.5;
    quelle.connect(analyse);
    daten = new Uint8Array(analyse.frequencyBinCount);
  } catch (_) { analyse = null; }                        /* ohne Messung: nur der Ersatztakt */
  let mittel = 0, letzter = 0;
  const uhr = setInterval(() => {
    if (audio.paused || document.hidden) return;
    const jetzt = performance.now();
    let energie = 0;
    if (analyse) {
      analyse.getByteFrequencyData(daten);
      const bis = Math.max(4, Math.floor(daten.length * 0.06));        /* die tiefsten ~6 % = Bass */
      for (let i = 0; i < bis; i++) energie += daten[i];
      energie = energie / bis / 255;
      mittel = mittel ? mittel * 0.92 + energie * 0.08 : energie;
    }
    const schlag = analyse && energie > MINDEST && energie > mittel * FAKTOR && jetzt - letzter > MIN_ABSTAND_MS;
    if (schlag || jetzt - letzter > ERSATZ_MS * 1.6) {
      letzter = jetzt;
      beiSchlag(schlag ? Math.min(1, energie / Math.max(mittel, 0.01) - 1) : 0.3);
    }
  }, MESS_MS);
  return () => { clearInterval(uhr); try { analyse?.disconnect(); } catch (_) { /* schon weg */ } };
}
