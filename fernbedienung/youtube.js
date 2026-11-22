/* FernsehFranzi - YouTube flüssig auf dem Pi 3 (seit 3.2.1).
 *
 * Der Pi 3 dekodiert nur H.264 in Hardware. YouTube liefert sonst VP9/AV1 - das muss die CPU rechnen,
 * das Video ruckelt. Dieses Skript läuft vor YouTube (document_start, in der Seite selbst) und meldet:
 * kein VP9, kein AV1, höchstens 30 Bilder/s und höchstens 720p. YouTube nimmt dann H.264.
 * (Gleicher Weg wie die bekannte Erweiterung „h264ify“.)
 */
(function () {
  "use strict";
  const verboten = (typ) => {
    if (!typ) return false;
    const t = String(typ).toLowerCase();
    if (/vp0?9|av01|av1/.test(t)) return true;
    const fps = t.match(/framerate=(\d+)/);
    if (fps && Number(fps[1]) > 30) return true;
    const breite = t.match(/width=(\d+)/), hoehe = t.match(/height=(\d+)/);
    if ((breite && Number(breite[1]) > 1280) || (hoehe && Number(hoehe[1]) > 720)) return true;
    return false;
  };
  if (window.MediaSource && MediaSource.isTypeSupported) {
    const original = MediaSource.isTypeSupported.bind(MediaSource);
    MediaSource.isTypeSupported = (typ) => !verboten(typ) && original(typ);
  }
  if (window.ManagedMediaSource && ManagedMediaSource.isTypeSupported) {
    const original = ManagedMediaSource.isTypeSupported.bind(ManagedMediaSource);
    ManagedMediaSource.isTypeSupported = (typ) => !verboten(typ) && original(typ);
  }
  const canPlay = HTMLMediaElement.prototype.canPlayType;
  HTMLMediaElement.prototype.canPlayType = function (typ) { return verboten(typ) ? "" : canPlay.call(this, typ); };
  if (navigator.mediaCapabilities && navigator.mediaCapabilities.decodingInfo) {
    const info = navigator.mediaCapabilities.decodingInfo.bind(navigator.mediaCapabilities);
    navigator.mediaCapabilities.decodingInfo = (konfig) => {
      const typ = (konfig && konfig.video && konfig.video.contentType) || "";
      if (verboten(typ) || (konfig && konfig.video && (konfig.video.framerate > 30 || konfig.video.height > 720))) {
        return Promise.resolve({ supported: false, smooth: false, powerEfficient: false });
      }
      return info(konfig);
    };
  }
})();
