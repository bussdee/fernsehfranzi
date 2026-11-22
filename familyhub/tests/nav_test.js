(() => {
  const sel = () => [...document.querySelectorAll('.tile.selected, .sz.selected')].map(e => e.id).join(',');
  const erg = [];
  const druck = (key, extra) => {
    document.dispatchEvent(new KeyboardEvent('keydown', Object.assign({key: key, bubbles: true, cancelable: true}, extra || {})));
  };
  erg.push('Start=' + sel());
  druck('ArrowRight'); erg.push('Rechts=' + sel());
  druck('ArrowDown');  erg.push('Runter=' + sel());
  druck('ArrowLeft');  erg.push('Links=' + sel());
  druck('ArrowUp');    erg.push('Hoch=' + sel());
  druck('Tab');        erg.push('Tab=' + sel());
  druck('Tab', {shiftKey: true}); erg.push('ShiftTab=' + sel());
  const f7 = new KeyboardEvent('keydown', {key: 'F7', bubbles: true, cancelable: true});
  document.dispatchEvent(f7);
  erg.push('F7Abgefangen=' + f7.defaultPrevented);
  erg.push('Fokus=' + (document.activeElement ? document.activeElement.tagName : 'null'));
  return erg.join(' | ');
})()
