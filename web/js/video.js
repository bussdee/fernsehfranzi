/* FernsehFranzi 4.0 - eigener Video-Player (Plex-Ersatz, wenn er gut genug ist): Filme/Serien aus einer FileBrowser-Freigabe.
 *
 * Liste: ↑ ↓ wählen · OK öffnen/abspielen · ← zurück · oben „Weiterschauen“ an der gemerkten Stelle
 * Player: PLAY/PAUSE · ⏪ ⏩ und ← → 10 s · ↑ ↓ blendet die Leiste ein · STOP zurück zur Liste
 * Am Pi 3 laufen H.264-Videos (.mp4) bis 720p am besten.
 */
import { el } from "./gemeinsam.js";
import { ton } from "./spiele/kern.js";

const SPRUNG_S = 10;
const zeit = (s) => { s = Math.max(0, Math.floor(s || 0)); const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60);
  return (h ? h + ":" + String(m).padStart(2, "0") : m) + ":" + String(s % 60).padStart(2, "0"); };
const ohneEndung = (n) => String(n).replace(/\.[^.]+$/, "");

export function oeffneVideo(box, api, app) {
  const kopfTitel = el("h2", { text: "🎬 " + app.name });
  const hilfe = el("div", { class: "hilfe" });
  const liste = el("div", { class: "hb-liste vid-liste" });
  box.append(el("div", { class: "overlay-kopf" }, kopfTitel, hilfe), liste);
  const z = { pfad: "", eintraege: [], wahl: 0, stand: null, video: null, leisteBis: 0, gemerkt: 0, titel: null, ordner: "" };
  const q = (pfad) => `app=${encodeURIComponent(app.id)}&pfad=${encodeURIComponent(pfad)}`;

  async function lade(pfad) {
    hilfe.textContent = "↑ ↓ wählen · OK öffnen · ← zurück · STOP schließen";
    liste.replaceChildren(el("div", { class: "leise", text: "Einen Moment …" }));
    try {
      const d = await api.hole(`/api/hoerbuch/liste?${q(pfad)}`);
      z.pfad = d.pfad; z.stand = d.stand; z.eintraege = [];
      if (d.eltern !== null && d.eltern !== undefined) z.eintraege.push({ art: "hoch", text: "⬆ Zurück", pfad: d.eltern });
      if (!d.pfad && d.stand?.titel) z.eintraege.push({ art: "weiter", text: `▶ Weiterschauen: ${ohneEndung(d.stand.titel.split("/").pop())} (${zeit(d.stand.sekunde)})` });
      for (const o of d.ordner) z.eintraege.push({ art: "ordner", text: o.name, pfad: o.pfad });
      for (const t of d.titel) z.eintraege.push({ art: "titel", text: ohneEndung(t.name), pfad: t.pfad });
      if (!d.ordner.length && !d.titel.length) z.eintraege.push({ art: "leer", text: "Hier sind keine Videos." });
      z.wahl = Math.min(z.wahl, z.eintraege.length - 1);
      zeige();
    } catch (fehler) { liste.replaceChildren(el("div", { class: "meldung-fehler", text: fehler.message })); }
  }

  function zeige() {
    liste.replaceChildren(...z.eintraege.map((e, i) => {
      const k = el("div", { class: "hb-eintrag" + (i === z.wahl ? " gewaehlt" : "") },
        el("span", { class: "hb-symbol-klein", text: { hoch: "⬆", weiter: "▶", ordner: "📁", titel: "🎬", leer: "" }[e.art] }),
        el("span", { class: "hb-name", text: e.text.replace(/^(⬆|▶) /, "") }));
      if (e.art === "ordner") {
        const bild = el("img", { class: "hb-cover", alt: "", src: `/api/hoerbuch/cover?${q(e.pfad)}` });
        bild.addEventListener("load", () => k.firstChild.replaceWith(bild));
      }
      k.addEventListener("click", () => { z.wahl = i; aktiviere(); });
      return k;
    }));
    liste.children[z.wahl]?.scrollIntoView({ block: "nearest" });
  }

  function aktiviere() {
    const e = z.eintraege[z.wahl];
    if (!e) return;
    if (e.art === "hoch" || e.art === "ordner") { z.wahl = 0; ton("bewegen"); return lade(e.pfad); }
    if (e.art === "weiter") return spiele(z.stand.titel, z.stand.ordner, z.stand.sekunde);
    if (e.art === "titel") spiele(e.pfad, z.pfad, 0);
  }

  /* ------------------------------------------------ Player */
  function spiele(pfad, ordner, ab) {
    const video = el("video", { class: "vid-video", autoplay: true, playsinline: true, src: `/api/hoerbuch/datei?${q(pfad)}` });
    const balken = el("div", { class: "hb-balken" }, el("span"));
    const info = el("div", { class: "vid-info" });
    const leiste = el("div", { class: "vid-leiste" }, el("div", { class: "vid-titel", text: ohneEndung(pfad.split("/").pop()) }), balken, info);
    const buehne = el("div", { class: "vid-buehne" }, video, leiste);
    box.append(buehne);
    z.video = video; z.titel = pfad; z.ordner = ordner; z.buehne = buehne; z.leiste = leiste;
    if (ab) video.addEventListener("loadedmetadata", () => { video.currentTime = Math.min(ab, (video.duration || ab + 1) - 5); }, { once: true });
    video.addEventListener("error", () => { api.hinweis("Dieses Video lässt sich am Fernseher nicht abspielen (am besten .mp4 mit H.264)."); });
    video.addEventListener("ended", () => { merke(true); schliesseVideo(); });
    zeigeLeiste();
    hilfe.textContent = "";
  }

  function zeigeLeiste() { z.leisteBis = Date.now() + 4000; }

  function merke(sofort) {
    if (!z.video || (!sofort && Date.now() - z.gemerkt < 15000)) return;
    z.gemerkt = Date.now();
    const v = z.video, d = v.duration || 0;
    const fertig = d > 0 && (d > 300 ? v.currentTime > d - 30 : v.currentTime > d * 0.95);   /* Abspann = fertig geschaut */
    api.sende("/api/hoerbuch/stand", { app: app.id, ordner: z.ordner, titel: fertig ? "" : z.titel,
                                        sekunde: Math.floor(v.currentTime || 0), spielt: !v.paused }).catch(() => {});
  }

  function schliesseVideo() {
    if (!z.video) return;
    merke(true);
    z.video.pause(); z.video.removeAttribute("src"); z.video.load();
    z.buehne.remove();
    z.video = null;
    lade(z.pfad);
  }

  const takt = setInterval(() => {
    const v = z.video;
    if (!v) return;
    const d = v.duration || 0;
    z.leiste.querySelector(".hb-balken span").style.width = d ? `${v.currentTime / d * 100}%` : "0";
    z.leiste.querySelector(".vid-info").textContent = `${zeit(v.currentTime)} / ${zeit(d)}${v.paused ? "  ·  ⏸ angehalten" : ""}`;
    z.leiste.classList.toggle("zeigen", v.paused || Date.now() < z.leisteBis);
    merke(false);
  }, 500);
  /* Solange ein Film läuft, zählt die Zeit auch ohne Tastendruck */
  const zaehlen = setInterval(() => { if (z.video && !z.video.paused) api.sende("/api/eingabe", { tasten: [] }).catch(() => {}); }, 60000);

  lade("");
  return {
    taste(t) {
      const v = z.video;
      if (v) {
        zeigeLeiste();
        if (t === "Escape" || t === "Backspace") { schliesseVideo(); return true; }
        if (["Enter", " ", "MediaPlayPause", "MediaPlay", "MediaPause", "p", "P"].includes(t)) {
          if (v.paused && t !== "MediaPause") v.play().catch(() => {}); else if (t !== "MediaPlay") v.pause();
          return true;
        }
        if (t === "MediaFastForward" || t === "ArrowRight") { v.currentTime = Math.min((v.duration || 0) - 1, v.currentTime + SPRUNG_S); return true; }
        if (t === "MediaRewind" || t === "ArrowLeft") { v.currentTime = Math.max(0, v.currentTime - SPRUNG_S); return true; }
        return true;
      }
      if (t === "ArrowUp") { z.wahl = Math.max(0, z.wahl - 1); zeige(); ton("bewegen"); return true; }
      if (t === "ArrowDown") { z.wahl = Math.min(z.eintraege.length - 1, z.wahl + 1); zeige(); ton("bewegen"); return true; }
      if (t === "Enter" || t === " " || t === "MediaPlay") { aktiviere(); return true; }
      if ((t === "ArrowLeft" || t === "Backspace") && z.pfad) { const hoch = z.eintraege.find((e) => e.art === "hoch"); if (hoch) { z.wahl = 0; lade(hoch.pfad); } return true; }
      return t !== "Escape" && t !== "Backspace";
    },
    schliesse() { clearInterval(takt); clearInterval(zaehlen); if (z.video) { merke(true); z.video.pause(); } },
  };
}
