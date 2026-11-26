/* FernsehFranzi 4.0 / 6.9.51 - Video-Seite im Stil einer Streaming-App: Filme/Serien aus einer FileBrowser-Freigabe
 * (Video-Ordner oder Film-Archiv der Eltern).
 *
 * Start: großes Titelbild „Weiterschauen“, darunter Reihen mit Postern: Weiterschauen (mit Fortschritt) · Meine Liste ·
 * Belohnungen 🎁 · Alle Filme & Serien. Ordner = Film oder Serie: Poster, Abspielen/Weiterschauen, ⭐ Meine Liste,
 * Staffeln (Unterordner) und Folgen mit Fortschrittsbalken und ✅ gesehen. Am Ende einer Folge startet die nächste
 * nach 8 Sekunden (OK sofort, STOP zurück).
 * Player: PLAY/PAUSE · ⏪ ⏩ und ← → 10 s · STOP zurück. Am Pi 3 laufen H.264-Videos (.mp4) bis 720p am besten.
 */
import { el, franziEcke } from "./gemeinsam.js";
import { ton } from "./spiele/kern.js";

const SPRUNG_S = 10;
const NAECHSTE_S = 8;
const zeit = (s) => { s = Math.max(0, Math.floor(s || 0)); const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60);
  return (h ? h + ":" + String(m).padStart(2, "0") : m) + ":" + String(s % 60).padStart(2, "0"); };
const ohneEndung = (n) => String(n).replace(/\.[^.]+$/, "");
const name = (pfad) => ohneEndung(String(pfad).split("/").pop());
const oben = (pfad) => String(pfad).split("/")[0];
/* „Pferdehof · Folge 2“ - bei Folgen gehört der Serienname dazu */
const voll = (pfad) => (String(pfad).includes("/") && ohneEndung(oben(pfad)) !== name(pfad) ? `${oben(pfad)} · ${name(pfad)}` : name(pfad));

export function oeffneVideo(box, api, app) {
  const kopfTitel = el("h2", { text: "🎬 " + app.name });
  const hilfe = el("div", { class: "hilfe", text: "Pfeile wählen · OK öffnen · STOP zurück" });
  const flaeche = el("div", { class: "st-flaeche" });
  box.classList.add("streaming");
  box.append(franziEcke("staunen", { zeichen: "🍿" }));               /* 6.9.62: Franzi schaut mit (nicht während ein Film läuft) */
  box.append(el("div", { class: "overlay-kopf" }, kopfTitel, hilfe), flaeche);
  const q = (pfad) => `app=${encodeURIComponent(app.id)}&pfad=${encodeURIComponent(pfad)}`;
  const cover = (pfad) => `/api/hoerbuch/cover?${q(pfad)}`;
  const z = { wurzel: null, fortschritt: {}, belohnung: {}, favoriten: [], ansicht: "start", stapel: [], ordner: null,
              reihen: [], zeile: 0, spalte: [], video: null, gemerkt: 0, naechste: null };

  /* ---------------------------------------------------------------- Laden */
  async function ladeStart() {
    flaeche.replaceChildren(el("div", { class: "leise", text: "Einen Moment …" }));
    try {
      const [d, f] = await Promise.all([api.hole(`/api/hoerbuch/liste?${q("")}`),
                                        api.hole(`/api/hoerbuch/favoriten?app=${encodeURIComponent(app.id)}`).catch(() => ({ favoriten: [] }))]);
      z.wurzel = d; z.fortschritt = d.fortschritt || {}; z.belohnung = d.belohnung || {}; z.favoriten = f.favoriten || [];
      zeigeStart();
    } catch (fehler) { flaeche.replaceChildren(el("div", { class: "meldung-fehler", text: fehler.message })); }
  }

  /* ---------------------------------------------------------------- Bausteine */
  const fortschrittVon = (pfad) => z.fortschritt[pfad];
  const anteil = (f) => (f && f.dauer ? Math.min(1, f.sekunde / f.dauer) : 0);
  function bildFlaeche(klasse, pfadFuerCover, symbol = "🎬") {
    const b = el("div", { class: klasse }, el("span", { class: "st-platzhalter", text: symbol }));
    if (pfadFuerCover !== null && pfadFuerCover !== undefined && pfadFuerCover !== "") {
      const img = el("img", { alt: "", src: cover(pfadFuerCover) });
      img.addEventListener("load", () => b.querySelector(".st-platzhalter")?.replaceWith(img));
    }
    return b;
  }
  function karte(e, { quer = false } = {}) {
    const coverPfad = e.ordner ? e.pfad : (e.pfad.includes("/") ? e.pfad.split("/").slice(0, -1).join("/") : "");
    const b = bildFlaeche(quer ? "st-bild quer" : "st-bild", coverPfad, e.ordner ? "📺" : "🎬");
    const f = e.ordner ? null : fortschrittVon(e.pfad);
    if (f && !f.gesehen && anteil(f) > 0.02) b.append(el("div", { class: "st-fortschritt" }, el("span", { style: `width:${anteil(f) * 100}%` })));
    if (f?.gesehen) b.append(el("div", { class: "st-gesehen", text: "✅" }));
    if (z.belohnung[oben(e.pfad)]) b.append(el("div", { class: "st-belohnung", text: "🎁" }));
    const k = el("div", { class: "st-karte" + (quer ? " quer" : "") }, b, el("div", { class: "st-name", text: e.titel || voll(e.pfad) }));
    k.tun = () => (e.ordner ? oeffneOrdner(e.pfad) : spiele(e.pfad, f && !f.gesehen ? f.sekunde : 0));
    k.addEventListener("click", k.tun);
    return k;
  }
  const knopf = (text, tun, klasse = "") => { const k = el("div", { class: "st-knopf " + klasse, text }); k.tun = tun; k.addEventListener("click", tun); return k; };
  function reihe(titel, karten) {
    if (!karten.length) return null;
    const leiste = el("div", { class: "st-reihe-karten" }, ...karten);
    z.reihen.push(karten);
    return el("section", { class: "st-reihe" }, el("h3", { text: titel }), leiste);
  }

  /* ---------------------------------------------------------------- Start */
  function zeigeStart() {
    z.ansicht = "start"; z.reihen = []; z.stapel = [];
    const d = z.wurzel;
    const weiter = Object.entries(z.fortschritt).filter(([, f]) => !f.gesehen && anteil(f) > 0.02 && anteil(f) < 0.95)
      .sort((a, b) => (a[1].zeit < b[1].zeit ? 1 : -1)).slice(0, 12);
    const teile = [];
    if (weiter.length) {                                                   /* großes Titelbild */
      const [pfad, f] = weiter[0];
      const held = el("div", { class: "st-held" }, bildFlaeche("st-held-bild", pfad.includes("/") ? oben(pfad) : "", "🎬"),
        el("div", { class: "st-held-text" }, el("small", { text: "Weiterschauen" }), el("h2", { text: voll(pfad) }),
          el("div", { class: "st-fortschritt gross" }, el("span", { style: `width:${anteil(f) * 100}%` })),
          el("div", { class: "leise", text: `${zeit(f.sekunde)} von ${zeit(f.dauer)}` })));
      const los = knopf("▶ Weiterschauen", () => spiele(pfad, f.sekunde), "haupt");
      const info = pfad.includes("/") ? knopf("ℹ Zur Serie", () => oeffneOrdner(pfad.split("/").slice(0, -1).join("/"))) : null;
      held.querySelector(".st-held-text").append(el("div", { class: "st-knoepfe" }, los, info));
      teile.push(held);
      z.reihen.push([los, info].filter(Boolean));
    }
    const alle = [...d.ordner.map((o) => ({ pfad: o.pfad, titel: o.name, ordner: true })),
                  ...d.titel.map((t) => ({ pfad: t.pfad, titel: ohneEndung(t.name), ordner: false }))];
    const istOrdner = new Set(d.ordner.map((o) => o.pfad));
    teile.push(reihe("▶ Weiterschauen", weiter.map(([pfad]) => karte({ pfad, ordner: false }, { quer: true }))));
    teile.push(reihe("⭐ Meine Liste", z.favoriten.map((p) => karte({ pfad: p, ordner: istOrdner.has(p) || !/\.[a-z0-9]{2,4}$/i.test(p) }))));
    teile.push(reihe("🎁 Belohnungen", alle.filter((e) => z.belohnung[e.pfad]).map((e) => karte(e))));
    teile.push(reihe("Alle Filme & Serien", alle.map((e) => karte(e))));
    if (!alle.length) teile.push(el("div", { class: "leise", text: "Hier sind noch keine Filme – Mama oder Papa geben sie im Elternbereich frei." }));
    flaeche.replaceChildren(...teile.filter(Boolean));
    z.zeile = 0; z.spalte = z.reihen.map(() => 0);
    markiere();
  }

  /* ---------------------------------------------------------------- Film / Serie (Ordner) */
  async function oeffneOrdner(pfad) {
    ton("ok");
    try {
      const d = await api.hole(`/api/hoerbuch/liste?${q(pfad)}`);
      z.fortschritt = { ...z.fortschritt, ...(d.fortschritt || {}) };
      if (z.ansicht !== "ordner" || !z.stapel.length || !pfad.startsWith(z.stapel[0])) z.stapel = [pfad];
      else if (!z.stapel.includes(pfad)) z.stapel.push(pfad);
      z.ordner = d; zeigeOrdner(pfad, d);
    } catch (f) { api.hinweis(f.message); }
  }

  function zeigeOrdner(pfad, d) {
    z.ansicht = "ordner"; z.reihen = [];
    const folgen = d.titel.map((t) => ({ pfad: t.pfad, titel: ohneEndung(t.name) }));
    const naechste = folgen.find((f) => !fortschrittVon(f.pfad)?.gesehen) || folgen[0];
    const fn = naechste && fortschrittVon(naechste.pfad);
    const fav = z.favoriten.includes(oben(pfad));
    const knoepfe = [];
    if (naechste) knoepfe.push(knopf(fn && !fn.gesehen && anteil(fn) > 0.02 ? `▶ Weiterschauen: ${naechste.titel}` : `▶ Abspielen${folgen.length > 1 ? ": " + naechste.titel : ""}`,
      () => spiele(naechste.pfad, fn && !fn.gesehen ? fn.sekunde : 0), "haupt"));
    const stern = knopf(fav ? "⭐ In meiner Liste" : "➕ Meine Liste", async () => {
      try {
        const an = !z.favoriten.includes(oben(pfad));
        z.favoriten = (await api.sende("/api/hoerbuch/favorit", { app: app.id, pfad: oben(pfad), an })).favoriten;
        stern.textContent = an ? "⭐ In meiner Liste" : "➕ Meine Liste"; ton("ok");
      } catch (f) { api.hinweis(f.message); }
    });
    knoepfe.push(stern, knopf("‹ Zurück", zurueck));
    const staffeln = d.ordner.map((o) => knopf("📁 " + o.name, () => oeffneOrdner(o.pfad), "chip"));
    const liste = folgen.map((f, i) => {
      const fp = fortschrittVon(f.pfad);
      const zeile = el("div", { class: "st-folge" }, el("span", { class: "st-folge-nr", text: String(i + 1) }),
        el("div", { class: "st-folge-text" }, el("b", { text: f.titel }),
          fp && !fp.gesehen && anteil(fp) > 0.02 ? el("div", { class: "st-fortschritt" }, el("span", { style: `width:${anteil(fp) * 100}%` })) : null),
        el("span", { class: "st-folge-zeichen", text: fp?.gesehen ? "✅" : fp && fp.dauer ? zeit(fp.dauer) : "" }));
      zeile.tun = () => spiele(f.pfad, fp && !fp.gesehen ? fp.sekunde : 0);
      zeile.addEventListener("click", zeile.tun);
      return zeile;
    });
    flaeche.replaceChildren(el("div", { class: "st-ordner" },
      el("div", { class: "st-ordner-links" }, bildFlaeche("st-bild gross", pfad, "📺"),
        z.belohnung[oben(pfad)] ? el("div", { class: "st-belohnung-text", text: "🎁 Belohnung" }) : null),
      el("div", { class: "st-ordner-rechts" }, el("h2", { text: name(pfad) }),
        el("div", { class: "leise", text: [d.ordner.length ? `${d.ordner.length} Staffeln` : "", folgen.length > 1 ? `${folgen.length} Folgen` : ""].filter(Boolean).join(" · ") }),
        el("div", { class: "st-knoepfe" }, ...knoepfe), staffeln.length ? el("div", { class: "st-knoepfe" }, ...staffeln) : null,
        folgen.length > 1 || staffeln.length ? el("div", { class: "st-folgen" }, ...liste) : null)));
    z.reihen.push(knoepfe);
    if (staffeln.length) z.reihen.push(staffeln);
    if (folgen.length > 1 || staffeln.length) liste.forEach((zl) => z.reihen.push([zl]));
    z.zeile = 0; z.spalte = z.reihen.map(() => 0);
    markiere();
  }

  function zurueck() {
    z.stapel.pop();
    if (z.stapel.length) oeffneOrdner(z.stapel.pop());
    else ladeStart();
    ton("bewegen");
  }

  /* ---------------------------------------------------------------- Auswahl */
  function markiere() {
    flaeche.querySelectorAll(".gewaehlt").forEach((k) => k.classList.remove("gewaehlt"));
    const r = z.reihen[z.zeile];
    const k = r?.[Math.min(z.spalte[z.zeile] || 0, r.length - 1)];
    if (k) { k.classList.add("gewaehlt"); k.scrollIntoView({ block: "nearest", inline: "nearest" }); }
  }
  function bewege(dz, ds) {
    if (dz) z.zeile = Math.max(0, Math.min(z.reihen.length - 1, z.zeile + dz));
    else { const r = z.reihen[z.zeile] || []; z.spalte[z.zeile] = Math.max(0, Math.min(r.length - 1, (z.spalte[z.zeile] || 0) + ds)); }
    ton("bewegen"); markiere();
  }

  /* ---------------------------------------------------------------- Player */
  function spiele(pfad, ab = 0) {
    const ordner = pfad.includes("/") ? pfad.split("/").slice(0, -1).join("/") : "";
    const video = el("video", { class: "vid-video", autoplay: true, playsinline: true, src: `/api/hoerbuch/datei?${q(pfad)}` });
    const balken = el("div", { class: "hb-balken" }, el("span"));
    const info = el("div", { class: "vid-info" });
    const leiste = el("div", { class: "vid-leiste" }, el("div", { class: "vid-titel", text: name(pfad) }), balken, info);
    const buehne = el("div", { class: "vid-buehne" }, video, leiste);
    box.append(buehne);
    z.video = video; z.titel = pfad; z.ordnerPfad = ordner; z.buehne = buehne; z.leiste = leiste; z.naechste = null;
    if (ab) video.addEventListener("loadedmetadata", () => { video.currentTime = Math.min(ab, (video.duration || ab + 1) - 5); }, { once: true });
    video.addEventListener("error", () => { api.hinweis("Dieses Video lässt sich am Fernseher nicht abspielen (am besten .mp4 mit H.264)."); });
    video.addEventListener("ended", () => { merke(true, true); naechsteFolge(); });
    zeigeLeiste();
    hilfe.textContent = "";
    ton("ok");
  }

  function zeigeLeiste() { z.leisteBis = Date.now() + 4000; }

  function merke(sofort, ende = false) {
    if (!z.video || (!sofort && Date.now() - z.gemerkt < 15000)) return;
    z.gemerkt = Date.now();
    const v = z.video, d = v.duration || 0;
    const fertig = ende || (d > 0 && (d > 300 ? v.currentTime > d - 30 : v.currentTime > d * 0.95));   /* Abspann = fertig geschaut */
    const sek = Math.floor(v.currentTime || 0);
    z.fortschritt[z.titel] = { sekunde: sek, dauer: Math.floor(d), zeit: new Date().toISOString(), gesehen: fertig || Boolean(z.fortschritt[z.titel]?.gesehen) };
    api.sende("/api/hoerbuch/stand", { app: app.id, ordner: z.ordnerPfad, titel: z.titel, sekunde: sek, dauer: Math.floor(d),
                                        fertig, spielt: !v.paused }).catch(() => {});
  }

  /* Am Ende einer Folge: die nächste im selben Ordner nach 8 s (OK sofort, STOP zurück) */
  async function naechsteFolge() {
    let liste = [];
    try { liste = (await api.hole(`/api/hoerbuch/liste?${q(z.ordnerPfad)}`)).titel; } catch (_) { /* dann keine */ }
    const nr = liste.findIndex((t) => t.pfad === z.titel);
    const naechste = nr >= 0 ? liste[nr + 1] : null;
    if (!naechste || !z.video) { schliesseVideo(); return; }
    const anzeige = el("div", { class: "st-naechste" }, el("small", { text: "Nächste Folge" }), el("b", { text: ohneEndung(naechste.name) }),
      el("div", { class: "st-naechste-zeit" }), el("div", { class: "leise", text: "OK: sofort · STOP: zurück" }));
    z.buehne.append(anzeige);
    const ende = Date.now() + NAECHSTE_S * 1000;
    const uhr = setInterval(() => {
      const rest = Math.ceil((ende - Date.now()) / 1000);
      anzeige.querySelector(".st-naechste-zeit").textContent = `in ${Math.max(0, rest)} s`;
      if (rest <= 0) los();
    }, 250);
    const los = () => { clearInterval(uhr); z.naechste = null; z.buehne.remove(); z.video = null; spiele(naechste.pfad, 0); };
    z.naechste = { los, abbrechen: () => { clearInterval(uhr); z.naechste = null; schliesseVideo(); } };
  }

  function schliesseVideo() {
    if (!z.video) return;
    merke(true);
    z.video.pause(); z.video.removeAttribute("src"); z.video.load();
    z.buehne.remove();
    z.video = null;
    hilfe.textContent = "Pfeile wählen · OK öffnen · STOP zurück";
    if (z.ansicht === "ordner" && z.stapel.length) oeffneOrdner(z.stapel.pop()); else ladeStart();
  }

  const takt = setInterval(() => {
    const v = z.video;
    if (!v) return;
    const d = v.duration || 0;
    z.leiste.querySelector(".hb-balken span").style.width = d ? `${v.currentTime / d * 100}%` : "0";
    z.leiste.querySelector(".vid-info").textContent = `${zeit(v.currentTime)} / ${zeit(d)}${v.paused ? "  ·  ⏸ angehalten" : ""}`;
    z.leiste.classList.toggle("zeigen", v.paused || Date.now() < z.leisteBis);
    merke(false);
  }, 1000);                                   /* 6.8.12: 1 s reicht für Leiste und Zeit */
  /* Solange ein Film läuft, zählt die Zeit auch ohne Tastendruck */
  const zaehlen = setInterval(() => { if (z.video && !z.video.paused) api.sende("/api/eingabe", { tasten: [] }).catch(() => {}); }, 60000);

  ladeStart();
  return {
    taste(t) {
      if (z.naechste) {
        if (t === "Enter" || t === " " || t === "MediaPlay" || t === "MediaPlayPause") z.naechste.los();
        else if (t === "Escape" || t === "Backspace") z.naechste.abbrechen();
        return true;
      }
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
      if (t === "ArrowUp") { bewege(-1, 0); return true; }
      if (t === "ArrowDown") { bewege(1, 0); return true; }
      if (t === "ArrowLeft") { bewege(0, -1); return true; }
      if (t === "ArrowRight") { bewege(0, 1); return true; }
      if (t === "Enter" || t === " " || t === "MediaPlay") {
        const r = z.reihen[z.zeile];
        r?.[Math.min(z.spalte[z.zeile] || 0, r.length - 1)]?.tun?.();
        return true;
      }
      if ((t === "Escape" || t === "Backspace") && z.ansicht === "ordner") { zurueck(); return true; }
      return t !== "Escape" && t !== "Backspace";
    },
    schliesse() { clearInterval(takt); clearInterval(zaehlen); if (z.video) { merke(true); z.video.pause(); } },
  };
}
