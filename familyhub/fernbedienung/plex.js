/* FernsehFranzi - Fernbedienung in Plex (seit 2.5.2).
 *
 * Chromium laeuft im Kiosk mit --enable-spatial-navigation: Pfeiltasten springen von
 * Element zu Element. Plex belegt die Pfeile aber selbst (hoch/runter = Lautstaerke,
 * links/rechts = Spulen) und verhindert damit das Springen.
 *
 * Regel (seit 2.5.4, so gewuenscht): Die Pfeiltasten navigieren IMMER - auch waehrend
 * Musik oder ein Film laeuft. Fuer den Player hat die Fernbedienung eigene Tasten:
 *   PLAY / PAUSE  -> Abspielen/Pause umschalten
 *   Vorlauf       -> 30 s vor
 *   Ruecklauf     -> 10 s zurueck
 *   STOP (Esc)    -> bleibt bei Plex (zurueck/schliessen)
 *
 * Dieses Skript laeuft vor Plex (document_start). Pfeile haelt es von Plex fern, ohne
 * preventDefault - so bleibt die Sprung-Navigation von Chromium wirksam. OK (Enter) auf
 * einem Element, das Enter nicht selbst kennt, loest einen Klick aus.
 * Einzige Ausnahme: Im Textfeld (Suche) bewegen links/rechts den Cursor.
 */
(function () {
  "use strict";

  const PFEILE = new Set(["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"]);
  const ENTER_NATIV = new Set(["A", "BUTTON", "INPUT", "SELECT", "TEXTAREA", "SUMMARY"]);
  /* Fernbedienung (cec_keys.py): PLAY = KEY_PLAY, PAUSE = KEY_P, Vor-/Ruecklauf =
     KEY_FASTFORWARD / KEY_REWIND. Chromium nennt sie je nach Tastaturbelegung leicht
     unterschiedlich - deshalb mehrere Namen. */
  const ABSPIELEN = new Set(["MediaPlay", "MediaPause", "MediaPlayPause", "p", "P"]);
  const VOR = new Set(["MediaFastForward"]);
  const ZURUECK = new Set(["MediaRewind"]);
  const VOR_S = 30;
  const ZURUECK_S = 10;

  /* Das Medium, das Plex gerade benutzt (Film oder Musik - Plex spielt beides ueber
     ein Medienelement): zuerst ein laufendes, sonst ein geladenes. */
  function aktuellesMedium() {
    const medien = Array.from(document.querySelectorAll("video, audio"));
    return medien.find((m) => !m.paused && !m.ended) ||
           medien.find((m) => m.readyState > 0 && (m.currentSrc || m.srcObject)) || null;
  }

  function istTextfeld(el) {
    if (!el) return false;
    if (el.isContentEditable) return true;
    if (el.tagName === "TEXTAREA") return true;
    if (el.tagName !== "INPUT") return false;
    const typ = (el.getAttribute("type") || "text").toLowerCase();
    return ["text", "search", "email", "url", "tel", "password", "number"].includes(typ);
  }

  function schlucken(event) {
    event.stopImmediatePropagation();
    event.preventDefault();
  }

  window.addEventListener("keydown", (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    const fokus = document.activeElement;
    const taste = event.key;

    if (PFEILE.has(taste)) {
      if (istTextfeld(fokus) && (taste === "ArrowLeft" || taste === "ArrowRight")) return;
      /* Plex bekommt die Taste nicht, Chromium springt (kein preventDefault). */
      event.stopImmediatePropagation();
      return;
    }

    if (ABSPIELEN.has(taste) || VOR.has(taste) || ZURUECK.has(taste)) {
      if (istTextfeld(fokus) && taste.length === 1) return;   /* "p" in der Suche tippen */
      const medium = aktuellesMedium();
      if (!medium) return;                                    /* nichts geladen: Plex entscheidet */
      schlucken(event);
      if (ABSPIELEN.has(taste)) {
        if (medium.paused) medium.play().catch(() => {}); else medium.pause();
      } else if (Number.isFinite(medium.duration)) {
        const ziel = medium.currentTime + (VOR.has(taste) ? VOR_S : -ZURUECK_S);
        medium.currentTime = Math.max(0, Math.min(medium.duration - 1, ziel));
      }
      return;
    }

    if (taste === "Enter" && fokus && fokus !== document.body &&
        !ENTER_NATIV.has(fokus.tagName) && !istTextfeld(fokus)) {
      schlucken(event);
      fokus.click();
    }
  }, true);
})();
