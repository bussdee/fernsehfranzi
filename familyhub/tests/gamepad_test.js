(() => {
  const erg = [];
  const druck = (key, extra) => {
    document.dispatchEvent(new KeyboardEvent('keydown', Object.assign({key: key, bubbles: true, cancelable: true}, extra || {})));
  };

  /* 1. Ziffer 5 oeffnet Snake */
  druck('5');
  erg.push('Snake offen=' + (!$('ov-snake') ? 'FEHLER' : ($('ov-snake').hidden === false)));

  /* 2. Gamepad simulieren: A-Knopf (0) = Enter -> Snake startet */
  const fakePad = {
    connected: true, id: 'Test-Pad',
    buttons: Array.from({length: 17}, (_, i) => ({pressed: i === 0, value: i === 0 ? 1 : 0})),
    axes: [0, 0, 0, 0],
  };
  navigator.getGamepads = () => [fakePad];
  return new Promise((loes) => {
    setTimeout(() => {
      erg.push('Snake läuft nach Pad-A=' + (SPIELE.snake.status === 'laeuft'));
      /* 3. Steuerkreuz rechts gedrückt -> Richtung muss sich merken */
      fakePad.buttons[0] = {pressed: false, value: 0};
      fakePad.buttons[15] = {pressed: true, value: 1};
      setTimeout(() => {
        erg.push('Pad-Rechts erkannt=' + (snake.richtung[0] === 1 && snake.wartende.length >= 0));
        fakePad.buttons[15] = {pressed: false, value: 0};
        /* 4. Alt+F4 im Spiel: nur Spiel schliessen */
        const af4 = new KeyboardEvent('keydown', {key: 'F4', altKey: true, bubbles: true, cancelable: true});
        document.dispatchEvent(af4);
        erg.push('AltF4 abgefangen=' + af4.defaultPrevented);
        erg.push('Snake zu=' + ($('ov-snake').hidden === true) + ', kein aktivesSpiel=' + (aktivesSpiel === null));
        /* 5. Memory: Ziffer 6, Karte 1 per Mausklick aufdecken */
        druck('6');
        const karten = $('mem-gitter').children;
        erg.push('Memory-Karten=' + karten.length + ', tabIndex=' + karten[0].tabIndex);
        karten[2].click();
        erg.push('Karte3 offen nach Klick=' + karten[2].classList.contains('offen'));
        /* 6. ESC schliesst Memory */
        druck('Escape');
        erg.push('Memory zu=' + ($('ov-memory').hidden === true));
        loes(erg.join(' | '));
      }, 120);
    }, 120);
  });
})()
