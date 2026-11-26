/* FernsehFranzi 6.9.48 - Musik-Seite (Kachel „Musik“ aus dem Musik-Archiv der Eltern) im Stil einer Musik-App.
 *
 * Start: Weiterhören · Lieblingslieder · Alles zufällig, darunter die Alben als Cover-Raster.
 * Album: großes Cover, Abspielen/Zufällig, Titelliste (→ auf einem Titel: ⭐ merken).
 * Unten die Player-Leiste: ⏮ ⏯ ⏭ 🔀 🔁. Kein Schlaf-Timer, kein dunkles Bild - das gehört zu den Hörbüchern.
 * Tasten: Pfeile wählen · OK · PLAY/PAUSE · ⏩/⏭ nächster Titel · ⏪/⏮ vorheriger · STOP zurück/schließen.
 * Der Server liefert nur Freigegebenes (archiv.py); gemerkt werden Stand (Weiterhören) und Lieblingslieder.
 */
import { el, franziEcke } from "./gemeinsam.js";
import { ton } from "./spiele/kern.js";

const ohneEndung = (n) => String(n).replace(/\.[^.]+$/, "");
const zeit = (s) => { s = Math.max(0, Math.floor(s || 0)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
const ABSPIELEN = new Set(["MediaPlay", "MediaPlayPause"]);
const ANHALTEN = new Set(["MediaPause"]);
const SPALTEN = 5;
const ZUFALL_ALBEN_MAX = 12;

/** Musik-Quelle (auch für die Musikbox bei Franzi): Alben, Titel eines Albums, Cover-Adresse. */
export function musikQuelle(api, appId = "archiv-musik") {
  const q = (pfad) => `app=${encodeURIComponent(appId)}&pfad=${encodeURIComponent(pfad)}`;
  return {
    appId,
    liste: (pfad = "") => api.hole(`/api/hoerbuch/liste?${q(pfad)}`),
    cover: (pfad) => `/api/hoerbuch/cover?${q(pfad)}`,
    datei: (pfad) => `/api/hoerbuch/datei?${q(pfad)}`,
    async titel(pfad) {
      const d = await api.hole(`/api/hoerbuch/liste?${q(pfad)}`);
      return d.titel.map((t) => ({ pfad: t.pfad, name: ohneEndung(t.name), album: pfad.split("/").pop() || "Einzelne Lieder", albumPfad: pfad }));
    },
  };
}

/** Wiedergabe mit Warteschlange, Zufall und Wiederholen (auch für die Musikbox). */
export function musikSpieler(api, quelle, beiWechsel = () => {}) {
  const audio = new Audio();
  audio.preload = "auto";
  const s = { liste: [], nr: -1, zufall: false, wiederholen: "aus", gemerkt: 0, original: [] };
  const aktuell = () => s.liste[s.nr] || null;
  const merke = (sofort = false) => {
    const t = aktuell();
    if (!t || (!sofort && Date.now() - s.gemerkt < 15000)) return;
    s.gemerkt = Date.now();
    api.sende("/api/hoerbuch/stand", { app: quelle.appId, ordner: t.albumPfad || "", titel: t.pfad,
                                        sekunde: Math.floor(audio.currentTime || 0), spielt: !audio.paused }).catch(() => {});
  };
  function spiele(nr, ab = 0) {
    if (nr < 0 || nr >= s.liste.length) return;
    s.nr = nr;
    audio.src = quelle.datei(s.liste[nr].pfad);
    if (ab) audio.addEventListener("loadedmetadata", () => { audio.currentTime = Math.min(ab, (audio.duration || ab + 1) - 1); }, { once: true });
    audio.play().catch((f) => api.hinweis("Abspielen geht gerade nicht: " + f.message));
    merke(true);
    beiWechsel();
  }
  const mischen = (liste, vorne) => {
    const rest = liste.filter((t) => t !== vorne);
    for (let i = rest.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [rest[i], rest[j]] = [rest[j], rest[i]]; }
    return vorne ? [vorne, ...rest] : rest;
  };
  const weiter = (richtung) => {
    if (!s.liste.length) return;
    if (richtung < 0 && audio.currentTime > 5) { audio.currentTime = 0; return; }
    let nr = s.nr + richtung;
    if (nr >= s.liste.length) nr = s.wiederholen === "alle" ? 0 : -1;
    if (nr < 0 && richtung < 0) nr = 0;
    if (nr >= 0) spiele(nr);
    else { audio.pause(); merke(true); beiWechsel(); }
  };
  audio.addEventListener("ended", () => (s.wiederholen === "eins" ? spiele(s.nr) : weiter(1)));
  audio.addEventListener("error", () => { if (audio.src) api.hinweis("Dieses Lied lässt sich nicht abspielen."); });
  audio.addEventListener("pause", () => beiWechsel());
  audio.addEventListener("play", () => beiWechsel());
  const uhr = setInterval(() => { if (!audio.paused) merke(); }, 5000);
  return {
    audio, zustand: s, aktuell,
    starte(liste, nr = 0, { zufall = s.zufall, ab = 0 } = {}) {
      s.original = liste.slice();
      s.liste = zufall ? mischen(liste, liste[nr]) : liste.slice();
      s.zufall = zufall;
      spiele(zufall ? 0 : nr, ab);
    },
    umschalten() { if (s.nr < 0) return; if (audio.paused) audio.play().catch(() => {}); else { audio.pause(); merke(true); } },
    weiter, spiele,
    zufall() {
      s.zufall = !s.zufall;
      const t = aktuell();
      if (s.original.length) { s.liste = s.zufall ? mischen(s.original, t) : s.original.slice(); s.nr = t ? s.liste.indexOf(t) : -1; }
      beiWechsel();
    },
    wiederholen() { s.wiederholen = { aus: "alle", alle: "eins", eins: "aus" }[s.wiederholen]; beiWechsel(); },
    stopp() { clearInterval(uhr); merke(true); audio.pause(); audio.removeAttribute("src"); audio.load(); },
  };
}

export function oeffneMusik(box, api, app) {
  const quelle = musikQuelle(api, app.id);
  const kopf = el("div", { class: "overlay-kopf" }, el("h2", { text: "🎵 " + (app.name || "Musik") }),
    el("div", { class: "hilfe", text: "Pfeile wählen · OK · PLAY/PAUSE · ⏩ ⏪ Titel · STOP zurück" }));
  const flaeche = el("div", { class: "mu-flaeche" });
  const leiste = el("div", { class: "mu-leiste", hidden: true });
  box.classList.add("musik");
  box.append(franziEcke("jubel", { tanzt: true }));                  /* 6.9.62: Franzi hört mit (tanzt, wenn Musik läuft) */
  box.append(kopf, flaeche, leiste);

  const z = { ansicht: "start", alben: [], einzeln: [], stand: null, favoriten: [], album: null, titel: [], zeile: 0, spalte: 0, reihen: [] };
  const spieler = musikSpieler(api, quelle, () => zeigeLeiste());

  /* ---------------------------------------------------------------- Laden */
  async function ladeStart() {
    flaeche.replaceChildren(el("div", { class: "leise", text: "Einen Moment …" }));
    try {
      const [d, f] = await Promise.all([quelle.liste(""), api.hole(`/api/hoerbuch/favoriten?app=${encodeURIComponent(app.id)}`).catch(() => ({ favoriten: [] }))]);
      z.alben = d.ordner.map((o) => ({ pfad: o.pfad, name: o.name }));
      z.einzeln = d.titel.map((t) => ({ pfad: t.pfad, name: ohneEndung(t.name), album: "Einzelne Lieder", albumPfad: "" }));
      z.stand = d.stand; z.favoriten = f.favoriten || [];
      zeigeStart();
    } catch (fehler) { flaeche.replaceChildren(el("div", { class: "meldung-fehler", text: fehler.message })); }
  }

  /* ---------------------------------------------------------------- Ansichten */
  const knopf = (text, tun, klasse = "") => { const k = el("div", { class: "mu-knopf " + klasse, text }); k.tun = tun; k.addEventListener("click", tun); return k; };

  function zeigeStart() {
    z.ansicht = "start";
    const oben = [];
    if (z.stand?.titel) oben.push(knopf(`▶ Weiterhören: ${ohneEndung(z.stand.titel.split("/").pop())}`, weiterhoeren, "breit"));
    oben.push(knopf(`⭐ Lieblingslieder (${z.favoriten.length})`, zeigeFavoriten));
    oben.push(knopf("🔀 Alles zufällig", allesZufaellig));
    const karten = z.alben.map((a) => albumKarte(a));
    if (z.einzeln.length) karten.push(albumKarte({ pfad: "", name: "Einzelne Lieder", einzeln: true }));
    const raster = [];
    for (let i = 0; i < karten.length; i += SPALTEN) raster.push(karten.slice(i, i + SPALTEN));
    flaeche.replaceChildren(el("div", { class: "mu-oben" }, ...oben),
      karten.length ? el("div", { class: "mu-raster" }, ...karten) : el("div", { class: "leise", text: "Hier ist noch keine Musik freigegeben – Mama oder Papa können das im Elternbereich." }));
    z.reihen = [oben, ...raster];
    z.zeile = Math.min(z.zeile, z.reihen.length - 1); z.spalte = 0;
    markiere();
  }

  function albumKarte(a) {
    const bild = el("div", { class: "mu-cover" }, el("span", { text: "💿" }));
    if (!a.einzeln) {
      const img = el("img", { alt: "", src: quelle.cover(a.pfad) });
      img.addEventListener("load", () => bild.replaceChildren(img));
    }
    const k = el("div", { class: "mu-karte" }, bild, el("div", { class: "mu-name", text: a.name }));
    k.tun = () => oeffneAlbum(a);
    k.addEventListener("click", k.tun);
    return k;
  }

  async function oeffneAlbum(a) {
    ton("ok");
    try {
      z.album = a;
      z.titel = a.einzeln ? z.einzeln : await quelle.titel(a.pfad);
      const unter = a.einzeln ? [] : (await quelle.liste(a.pfad)).ordner;       /* CD 1, CD 2 … */
      zeigeAlbum(unter);
    } catch (f) { api.hinweis(f.message); }
  }

  function titelZeile(t, i, liste) {
    const fav = z.favoriten.includes(t.pfad);
    const zeile = el("div", { class: "mu-titel" + (spieler.aktuell()?.pfad === t.pfad ? " laeuft" : ""), "data-pfad": t.pfad },
      el("span", { class: "mu-nr", text: String(i + 1) }), el("span", { class: "mu-titel-name", text: t.name }),
      el("span", { class: "mu-album-klein", text: t.album || "" }));
    zeile.tun = () => { spieler.starte(liste, i, { zufall: false }); ton("ok"); };
    zeile.addEventListener("click", zeile.tun);
    const stern = knopf(fav ? "⭐" : "➕", () => favorit(t, stern), "rund" + (fav ? " an" : ""));
    return [zeile, stern];
  }

  function zeigeAlbum(unter = []) {
    z.ansicht = "album";
    const a = z.album;
    const cover = el("div", { class: "mu-cover gross" }, el("span", { text: "💿" }));
    if (!a.einzeln) { const img = el("img", { alt: "", src: quelle.cover(a.pfad) }); img.addEventListener("load", () => cover.replaceChildren(img)); }
    const knoepfe = [knopf("▶ Abspielen", () => { spieler.starte(z.titel, 0, { zufall: false }); ton("ok"); }),
                     knopf("🔀 Zufällig", () => { spieler.starte(z.titel, Math.floor(Math.random() * z.titel.length), { zufall: true }); ton("ok"); }),
                     knopf("‹ Alle Alben", zurueck)];
    const unterKnoepfe = unter.map((o) => knopf("📁 " + o.name, () => oeffneAlbum({ pfad: o.pfad, name: o.name })));
    const zeilen = z.titel.map((t, i) => titelZeile(t, i, z.titel));
    flaeche.replaceChildren(el("div", { class: "mu-album" },
      el("div", { class: "mu-album-links" }, cover, el("h3", { text: a.name }), el("div", { class: "leise", text: `${z.titel.length} Lieder` })),
      el("div", { class: "mu-album-rechts" }, el("div", { class: "mu-oben" }, ...knoepfe, ...unterKnoepfe),
        el("div", { class: "mu-liste" }, ...zeilen.map(([zl, st]) => el("div", { class: "mu-titel-reihe" }, zl, st))))));
    z.reihen = [[...knoepfe, ...unterKnoepfe], ...zeilen];
    z.zeile = zeilen.length ? 1 : 0; z.spalte = 0;
    markiere();
  }

  function zeigeFavoriten() {
    z.album = { name: "⭐ Lieblingslieder", einzeln: true };
    z.titel = z.favoriten.map((p) => ({ pfad: p, name: ohneEndung(p.split("/").pop()), album: p.includes("/") ? p.split("/")[0] : "Einzelne Lieder",
                                         albumPfad: p.includes("/") ? p.split("/").slice(0, -1).join("/") : "" }));
    if (!z.titel.length) { api.hinweis("Noch keine Lieblingslieder – in einem Album → drücken und ⭐ wählen."); return; }
    zeigeAlbum();
  }

  async function weiterhoeren() {
    const st = z.stand;
    try {
      const liste = st.ordner || !z.einzeln.length ? await quelle.titel(st.ordner || "") : z.einzeln;
      const nr = liste.findIndex((t) => t.pfad === st.titel);
      if (nr < 0) { api.hinweis("Das Lied gibt es nicht mehr."); return; }
      spieler.starte(liste, nr, { zufall: false, ab: st.sekunde }); ton("ok");
    } catch (f) { api.hinweis(f.message); }
  }

  async function allesZufaellig() {
    try {
      const alle = [...z.einzeln];
      for (const a of z.alben.slice(0, ZUFALL_ALBEN_MAX)) alle.push(...await quelle.titel(a.pfad));
      if (!alle.length) return;
      spieler.starte(alle, Math.floor(Math.random() * alle.length), { zufall: true }); ton("ok");
    } catch (f) { api.hinweis(f.message); }
  }

  async function favorit(t, stern) {
    const an = !z.favoriten.includes(t.pfad);
    try {
      z.favoriten = (await api.sende("/api/hoerbuch/favorit", { app: app.id, pfad: t.pfad, an })).favoriten;
      stern.textContent = an ? "⭐" : "➕"; stern.classList.toggle("an", an); ton(an ? "ok" : "bewegen");
    } catch (f) { api.hinweis(f.message); }
  }

  function zurueck() { z.zeile = 1; zeigeStart(); ton("bewegen"); }

  /* ---------------------------------------------------------------- Player-Leiste */
  function zeigeLeiste() {
    const t = spieler.aktuell(), s = spieler.zustand;
    if (!t) { leiste.replaceChildren(); leiste.hidden = true; z.leiste = []; return; }
    leiste.hidden = false;
    const cover = el("div", { class: "mu-cover klein" }, el("span", { text: "🎵" }));
    if (t.albumPfad) { const img = el("img", { alt: "", src: quelle.cover(t.albumPfad) }); img.addEventListener("load", () => cover.replaceChildren(img)); }
    z.leiste = [knopf("⏮", () => spieler.weiter(-1), "rund"), knopf(spieler.audio.paused ? "▶" : "⏸", () => spieler.umschalten(), "rund gross"),
                knopf("⏭", () => spieler.weiter(1), "rund"), knopf("🔀", () => spieler.zufall(), "rund" + (s.zufall ? " an" : "")),
                knopf(s.wiederholen === "eins" ? "🔂" : "🔁", () => spieler.wiederholen(), "rund" + (s.wiederholen !== "aus" ? " an" : ""))];
    z.zeit = el("div", { class: "mu-zeit" });
    z.balken = el("div", { class: "mu-balken" }, el("span"));
    leiste.replaceChildren(cover, el("div", { class: "mu-jetzt" }, el("b", { text: t.name }), el("small", { text: t.album || "" }), z.balken, z.zeit),
      el("div", { class: "mu-steuer" }, ...z.leiste));
    if (z.inLeiste) markiere();
    flaeche.querySelectorAll(".mu-titel").forEach((zl) => zl.classList.toggle("laeuft", zl.dataset.pfad === t.pfad));
  }
  const takt = setInterval(() => {
    if (!z.balken) return;
    const a = spieler.audio, d = a.duration || 0;
    z.balken.firstChild.style.width = d ? `${Math.min(100, a.currentTime / d * 100)}%` : "0";
    z.zeit.textContent = `${zeit(a.currentTime)} / ${zeit(d)}`;
  }, 1000);

  /* ---------------------------------------------------------------- Auswahl */
  function markiere() {
    box.querySelectorAll(".gewaehlt").forEach((k) => k.classList.remove("gewaehlt"));
    const reihe = z.inLeiste ? z.leiste : z.reihen[z.zeile];
    const k = reihe?.[Math.min(z.spalte, (reihe?.length || 1) - 1)];
    if (k) { k.classList.add("gewaehlt"); k.scrollIntoView({ block: "nearest" }); }
  }
  function bewege(dz, ds) {
    if (z.inLeiste) {
      if (dz < 0) { z.inLeiste = false; z.zeile = z.reihen.length - 1; }
      else if (ds) z.spalte = Math.max(0, Math.min(z.leiste.length - 1, z.spalte + ds));
    } else if (dz) {
      const ziel = z.zeile + dz;
      if (ziel >= z.reihen.length && z.leiste?.length) { z.inLeiste = true; z.spalte = 1; }
      else if (ziel >= 0 && ziel < z.reihen.length) z.zeile = ziel;
    } else {
      const reihe = z.reihen[z.zeile] || [];
      z.spalte = Math.max(0, Math.min(reihe.length - 1, Math.min(z.spalte, reihe.length - 1) + ds));
    }
    ton("bewegen"); markiere();
  }

  ladeStart();

  return {
    taste(t) {
      if (ABSPIELEN.has(t)) { if (spieler.aktuell()) spieler.umschalten(); else (z.reihen[z.zeile]?.[z.spalte])?.tun?.(); return true; }
      if (ANHALTEN.has(t)) { spieler.audio.pause(); return true; }
      if (t === "MediaFastForward" || t === "MediaTrackNext") { spieler.weiter(1); return true; }
      if (t === "MediaRewind" || t === "MediaTrackPrevious") { spieler.weiter(-1); return true; }
      if (t === "ArrowUp") { bewege(-1, 0); return true; }
      if (t === "ArrowDown") { bewege(1, 0); return true; }
      if (t === "ArrowLeft") { bewege(0, -1); return true; }
      if (t === "ArrowRight") { bewege(0, 1); return true; }
      if (t === "Enter" || t === " ") {
        const reihe = z.inLeiste ? z.leiste : z.reihen[z.zeile];
        reihe?.[Math.min(z.spalte, reihe.length - 1)]?.tun?.();
        return true;
      }
      if ((t === "Escape" || t === "Backspace") && z.ansicht === "album") { z.inLeiste = false; zurueck(); return true; }
      return t !== "Escape" && t !== "Backspace";            /* STOP auf der Startansicht schließt */
    },
    schliesse() { clearInterval(takt); spieler.stopp(); },
  };
}
