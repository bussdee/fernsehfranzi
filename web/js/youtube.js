/* FernsehFranzi 3.5 - YouTube-Bereich: Kategorien -> Videos -> eigener Player (nur das Video).
 *
 * Sicherheit: Das Video läuft als youtube-nocookie-Einbettung, gesteuert über die IFrame-API. Der Fokus bleibt immer
 * auf unserer Seite (das iframe bekommt keinen Fokus und keine Maus) - also keine Klicks auf Vorschläge, Kanal, Suche.
 * Pause und Ende verdecken wir selbst, bevor YouTube „Weitere Videos“ zeigt.
 * Tasten: ↑ ↓ ← → wählen · OK öffnen/abspielen · PLAY/PAUSE · ⏪ ⏩ 10 s · im Player ← → voriges/nächstes · STOP zurück
 */
import { el } from "./gemeinsam.js";
import { ton } from "./spiele/kern.js";

const SPRUNG_S = 10;
let apiLaden = null;

function ladeApi() {
  if (window.YT && window.YT.Player) return Promise.resolve(window.YT);
  if (!apiLaden) {
    apiLaden = new Promise((fertig, fehler) => {
      window.onYouTubeIframeAPIReady = () => fertig(window.YT);
      const s = document.createElement("script");
      s.src = "https://www.youtube.com/iframe_api";
      s.onerror = () => { apiLaden = null; fehler(new Error("YouTube ist gerade nicht erreichbar.")); };
      document.head.append(s);
    });
  }
  return apiLaden;
}

const QUALITAET = { tiny: "144p", small: "240p", medium: "360p", large: "480p", hd720: "720p", hd1080: "1080p" };

export function oeffneYoutube(box, api) {
  box.classList.add("yt");
  const titel = el("h2", { text: "▶️ YouTube" });
  const hilfe = el("div", { class: "hilfe" });
  const inhalt = el("div", { class: "yt-inhalt" });
  box.append(el("div", { class: "overlay-kopf" }, titel, hilfe), inhalt);
  const z = { kategorien: [], kat: 0, eintrag: 0, ebene: "kategorien", spieler: null, player: null };

  async function lade() {
    try { z.kategorien = (await api.hole("/api/youtube")).kategorien.filter((k) => k.eintraege.length); }
    catch (fehler) { inhalt.replaceChildren(el("div", { class: "meldung-fehler", text: fehler.message })); return; }
    if (!z.kategorien.length) {
      inhalt.replaceChildren(el("div", { class: "witz", text: "Hier sind noch keine Videos. Mama oder Papa können welche aussuchen." }));
      return;
    }
    zeigeKategorien();
  }

  /* ------------------------------------------------ Kategorien und Videos */
  function zeigeKategorien() {
    z.ebene = "kategorien";
    titel.textContent = "▶️ YouTube";
    hilfe.textContent = "← → wählen · OK öffnen · STOP zurück";
    inhalt.replaceChildren(el("div", { class: "yt-kategorien" }, ...z.kategorien.map((k, i) =>
      el("div", { class: "yt-kategorie" + (i === z.kat ? " gewaehlt" : "") },
        el("div", { class: "yt-vorschau", style: k.eintraege[0]?.bild ? `background-image:url("${k.eintraege[0].bild}")` : "" }),
        el("div", { class: "yt-name", text: k.name }), el("small", { text: `${k.eintraege.length} ${k.eintraege.length === 1 ? "Video" : "Videos"}` })))));
    inhalt.querySelector(".gewaehlt")?.scrollIntoView({ block: "nearest", inline: "center" });
  }

  function zeigeVideos() {
    z.ebene = "videos";
    const k = z.kategorien[z.kat];
    titel.textContent = "▶️ " + k.name;
    hilfe.textContent = "Pfeile wählen · OK abspielen · STOP zurück";
    inhalt.replaceChildren(el("div", { class: "yt-raster" }, ...k.eintraege.map((e, i) =>
      el("div", { class: "yt-video" + (i === z.eintrag ? " gewaehlt" : "") },
        el("div", { class: "yt-vorschau", style: e.bild ? `background-image:url("${e.bild}")` : "" },
          e.art === "playlist" ? el("span", { class: "yt-liste", text: "📃 Playlist" }) : null),
        el("div", { class: "yt-name", text: e.titel })))));
    inhalt.querySelector(".gewaehlt")?.scrollIntoView({ block: "nearest" });
  }

  /* ------------------------------------------------ Player */
  async function spiele(stelle = 0) {
    const e = z.kategorien[z.kat].eintraege[z.eintrag];
    /* 4.0.1: Playlisten spielt unser Player selbst nacheinander ab (Videoliste vom Server) */
    const liste = e.art === "playlist" && e.videos?.length ? e.videos : null;
    z.stelle = liste ? Math.max(0, Math.min(stelle, liste.length - 1)) : 0;
    z.ebene = "player";
    hilfe.textContent = "PLAY/PAUSE · ⏪ ⏩ 10 s · ← → voriges/nächstes · U Untertitel · STOP zurück";
    titel.textContent = "▶️ " + e.titel + (liste ? ` (${z.stelle + 1}/${liste.length})` : "");
    const ziel = el("div", { id: "yt-ziel" });
    const deckel = el("div", { class: "yt-deckel" }, el("div", { class: "yt-deckel-symbol", text: "⏳" }),
      el("div", { class: "yt-deckel-text", text: e.titel }));
    const buehne = el("div", { class: "yt-buehne" }, ziel, deckel);
    inhalt.replaceChildren(buehne);
    z.spieler = { buehne, deckel, e, liste };
    let YT;
    try { YT = await ladeApi(); } catch (fehler) { deckelZeigen("⚠️", fehler.message); return; }
    if (z.ebene !== "player") return;
    const vars = { autoplay: 1, controls: 0, disablekb: 1, fs: 0, rel: 0, modestbranding: 1, iv_load_policy: 3,
                   playsinline: 1, cc_load_policy: z.untertitel ? 1 : 0, hl: "de", cc_lang_pref: "de", origin: location.origin };
    if (e.art === "playlist" && !liste) Object.assign(vars, { listType: "playlist", list: e.id });   /* alter Weg als Rückfall */
    z.player = new YT.Player(ziel, {
      host: "https://www.youtube-nocookie.com",
      videoId: liste ? liste[z.stelle] : e.art === "video" ? e.id : undefined,
      playerVars: vars, width: "100%", height: "100%",
      events: {
        onReady: (ev) => { const f = ev.target.getIframe(); f.setAttribute("tabindex", "-1"); ev.target.playVideo(); fokusZurueck(); },
        onStateChange: (ev) => zustand(ev.data),
        onApiChange: () => untertitelAnwenden(),
        onError: () => deckelZeigen("⚠️", "Dieses Video lässt sich hier nicht abspielen."),
      },
    });
  }

  /* 4.1: Untertitel sind aus (YouTube blendet sonst automatische ein, cc_load_policy allein reicht nicht).
     U schaltet sie ein und aus; die Wahl gilt, bis der YouTube-Bereich geschlossen wird. */
  function untertitelAnwenden() {
    const p = z.player;
    if (!p) return;
    try {
      if (z.untertitel) { p.loadModule?.("captions"); p.setOption?.("captions", "track", { languageCode: "de" }); }
      else { p.unloadModule?.("captions"); p.unloadModule?.("cc"); }
    } catch (_) { /* ältere Player kennen das Modul nicht */ }
  }

  function deckelZeigen(symbol, text) {
    if (!z.spieler) return;
    z.spieler.deckel.hidden = false;
    z.spieler.deckel.firstChild.textContent = symbol;
    z.spieler.deckel.lastChild.textContent = text;
  }

  function zustand(s) {
    const YT = window.YT;
    if (!z.spieler) return;
    if (s === YT.PlayerState.PLAYING) { z.spieler.deckel.hidden = true; z.spieler.buehne.classList.remove("ende"); untertitelAnwenden(); }
    else if (s === YT.PlayerState.PAUSED) {
      const q = QUALITAET[z.player.getPlaybackQuality?.()] || "";        /* 4.1: Qualität im Pause-Bild (zur Kontrolle) */
      deckelZeigen("⏸", ((z.player.getVideoData?.().title) || z.spieler.e.titel) + (q ? `  ·  ${q}` : ""));
    }
    else if (s === YT.PlayerState.BUFFERING) { /* Deckel bleibt, wie er ist */ }
    else if (s === YT.PlayerState.ENDED) {
      z.spieler.buehne.classList.add("ende");                     /* sofort weg, bevor Vorschläge kommen */
      deckelZeigen("⏭", "Gleich geht's weiter …");
      setTimeout(weiter, 800);
    }
    fokusZurueck();
  }

  function weiter() {
    if (z.ebene !== "player") return;
    const e = z.spieler.e;
    if (z.spieler.liste) {
      if (z.stelle < z.spieler.liste.length - 1) { const s = z.stelle + 1; stopp(); spiele(s); return; }
    } else if (e.art === "playlist") {
      const liste = z.player.getPlaylist?.() || [];
      if (z.player.getPlaylistIndex() < liste.length - 1) { z.spieler.buehne.classList.remove("ende"); z.player.nextVideo(); return; }
    }
    const k = z.kategorien[z.kat];
    if (z.eintrag < k.eintraege.length - 1) { z.eintrag++; stopp(); spiele(); }
    else { stopp(); zeigeVideos(); }
  }

  function wechsle(richtung) {
    const e = z.spieler.e;
    if (z.spieler.liste) {
      const s = z.stelle + richtung;
      if (s >= 0 && s < z.spieler.liste.length) { stopp(); spiele(s); }
      return;
    }
    if (e.art === "playlist") {
      if (richtung > 0) z.player.nextVideo(); else z.player.previousVideo();
      return;
    }
    const k = z.kategorien[z.kat];
    const neu = z.eintrag + richtung;
    if (neu < 0 || neu >= k.eintraege.length) return;
    z.eintrag = neu; stopp(); spiele();
  }

  function stopp() {
    try { z.player?.destroy(); } catch (_) { /* weg */ }
    z.player = null; z.spieler = null;
  }

  /* Der Fokus darf nie im Video landen (sonst könnte man darin herumklicken) */
  function fokusZurueck() {
    const aktiv = document.activeElement;
    if (aktiv && aktiv.tagName === "IFRAME") aktiv.blur();
    window.focus();
  }
  const wache = setInterval(fokusZurueck, 1000);
  window.addEventListener("blur", fokusZurueck);
  /* Solange ein Video läuft, zählt die Zeit auch ohne Tastendruck (wie bei einer Taste) */
  const zaehlen = setInterval(() => {
    if (z.player?.getPlayerState?.() === 1) api.sende("/api/eingabe", { tasten: [] }).catch(() => {});
  }, 60000);

  lade();
  return {
    taste(t) {
      if (z.ebene === "kategorien") {
        if (t === "ArrowLeft" || t === "ArrowUp") { z.kat = Math.max(0, z.kat - 1); zeigeKategorien(); ton("bewegen"); return true; }
        if (t === "ArrowRight" || t === "ArrowDown") { z.kat = Math.min(z.kategorien.length - 1, z.kat + 1); zeigeKategorien(); ton("bewegen"); return true; }
        if (t === "Enter" || t === " ") { if (z.kategorien.length) { z.eintrag = 0; zeigeVideos(); ton("ok"); } return true; }
        return false;
      }
      if (z.ebene === "videos") {
        const n = z.kategorien[z.kat].eintraege.length, spalten = 4;
        const schritt = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -spalten, ArrowDown: spalten }[t];
        if (schritt !== undefined) { z.eintrag = Math.max(0, Math.min(n - 1, z.eintrag + schritt)); zeigeVideos(); ton("bewegen"); return true; }
        if (t === "Enter" || t === " " || t === "MediaPlay" || t === "MediaPlayPause") { spiele(); return true; }
        if (t === "Escape" || t === "Backspace") { zeigeKategorien(); return true; }
        return true;
      }
      /* Player */
      const p = z.player;
      if (t === "Escape" || t === "Backspace") { stopp(); zeigeVideos(); return true; }
      if (!p || !p.getPlayerState) return true;
      if (t === "Enter" || t === " " || t === "MediaPlayPause" || t === "MediaPlay" || t === "MediaPause" || t === "p" || t === "P") {
        if (p.getPlayerState() === 1 && t !== "MediaPlay") p.pauseVideo(); else p.playVideo();
        return true;
      }
      if (t === "u" || t === "U" || t === "Subtitle") {
        z.untertitel = !z.untertitel; untertitelAnwenden();
        api.hinweis(z.untertitel ? "Untertitel an" : "Untertitel aus");
        return true;
      }
      if (t === "MediaFastForward") { p.seekTo(p.getCurrentTime() + SPRUNG_S, true); return true; }
      if (t === "MediaRewind") { p.seekTo(Math.max(0, p.getCurrentTime() - SPRUNG_S), true); return true; }
      if (t === "ArrowRight" || t === "MediaTrackNext") { wechsle(1); return true; }
      if (t === "ArrowLeft" || t === "MediaTrackPrevious") { wechsle(-1); return true; }
      return true;
    },
    schliesse() {
      clearInterval(wache); clearInterval(zaehlen);
      window.removeEventListener("blur", fokusZurueck);
      stopp();
    },
  };
}
