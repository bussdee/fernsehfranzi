/* FernsehFranzi 3.3 - Hörbücher: Ordner im Netzwerk (FileBrowser-Freigabe) mit Wiedergabeliste und Sleep-Timer.
 *
 * Bedienung (Pfeile bleiben immer Navigation):
 *   ↑ ↓ Liste · OK öffnen/abspielen · ← oder Zurück-Taste: Ordner hoch · STOP: schließen
 *   PLAY: abspielen - vorher IMMER die Sleep-Zeit wählen · PAUSE: anhalten (Sleep-Timer endet)
 *   ⏩ / ⏪: 30 Sekunden vor/zurück
 * Nach dem Start zählt 30 Sekunden herunter, dann wird das Bild schwarz (zum Einschlafen). Eine Taste weckt es.
 * Läuft der Sleep-Timer ab: leiser werden, anhalten, Stelle merken, Fernseher aus.
 * 3.4: Einschlafbild = dunkler Sternenhimmel. Gute Nacht (opt.weiter) fragt sofort nach der Zeit und hört weiter,
 * wo am Vorabend aufgehört wurde. Automatisch geöffnet (opt.automatisch) und niemand wählt: kleiner Alarm nach
 * 5, 15 und 25 Minuten, nach 30 Minuten ein Countdown, dann Fernseher aus.
 */
import { el } from "./gemeinsam.js";
import { ton } from "./spiele/kern.js";
import { starte as sternenhimmel } from "./sternenhimmel.js";

const SCHLAF_WAHL = [5, 10, 15, 20, 30, 45, 60, 90, 120];
const TEST = globalThis.__ffHoerbuch || {};          /* nur die Browser-Tests verkürzen damit die Zeiten */
const SCHWARZ_NACH_S = TEST.schwarzS ?? 30;
const MINUTE_MS = TEST.minuteMs ?? 60000;
const SPRUNG_S = 30;
const ALARM_MIN = [5, 15, 25];                       /* automatische Gute Nacht ohne Wahl (Entscheidung 8.2) */
const AUS_NACH_MIN = 30;
const AUS_COUNTDOWN_S = 30;
const ABSPIELEN = new Set(["MediaPlay", "MediaPlayPause"]);
const ANHALTEN = new Set(["MediaPause", "p", "P"]);

function zeit(s) {
  s = Math.max(0, Math.floor(s || 0));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${r}` : `${m}:${r}`;
}

function ohneEndung(name) { return String(name).replace(/\.[^.]+$/, ""); }

export function oeffneHoerbuch(box, api, app, opt = {}) {
  const audio = new Audio();
  audio.preload = "auto";
  const kopfTitel = el("h2", { text: "🎧 " + app.name });
  const ort = el("div", { class: "hb-ort" });
  const hilfe = el("div", { class: "hilfe", text: "↑ ↓ wählen · OK öffnen · PLAY abspielen · PAUSE anhalten · ⏪ ⏩ 30 s · STOP schließen" });
  const liste = el("div", { class: "hb-liste" });
  const titelAnzeige = el("div", { class: "hb-titel", text: "Such dir ein Hörbuch aus" });
  const ordnerAnzeige = el("div", { class: "hb-ordner" });
  const balken = el("div", { class: "hb-balken" }, el("span"));
  const zeitAnzeige = el("div", { class: "hb-zeit" });
  const schlafAnzeige = el("div", { class: "hb-schlaf" });
  const coverGross = el("img", { class: "hb-cover-gross", alt: "", hidden: true });
  coverGross.addEventListener("error", () => { coverGross.hidden = true; symbolGross.hidden = false; });
  coverGross.addEventListener("load", () => { coverGross.hidden = false; symbolGross.hidden = true; });
  const symbolGross = el("div", { class: "hb-symbol", text: "🌙" });
  /* 4.0: Cover des Ordners groß rechts (Hörbuch, das läuft - sonst der geöffnete Ordner) */
  const zeigeCover = (ordner) => {
    const neu = ordner ? `/api/hoerbuch/cover?app=${encodeURIComponent(app.id)}&pfad=${encodeURIComponent(ordner)}` : "";
    if (!neu) { coverGross.hidden = true; symbolGross.hidden = false; coverGross.removeAttribute("src"); return; }
    if (coverGross.getAttribute("src") !== neu) coverGross.src = neu;
  };
  const spieler = el("div", { class: "hb-spieler" }, coverGross, symbolGross,
    titelAnzeige, ordnerAnzeige, balken, zeitAnzeige, schlafAnzeige);
  const himmel = el("canvas", { class: "hb-himmel" });
  const schwarz = el("div", { class: "hb-schwarz", hidden: true }, himmel);
  let himmelStopp = null;
  const dunkel = (an) => {
    schwarz.hidden = !an;
    if (an && !himmelStopp) { himmelStopp = sternenhimmel(himmel); merke(true); }
    if (!an && himmelStopp) { himmelStopp(); himmelStopp = null; }
  };
  /* 6.1: Schlaf-Zeit vorbei - geht der Fernseher in den Standby, hält auch der Sternenhimmel an (der Pi spart Strom);
     bleibt er wegen des Weckers an, läuft der Nachthimmel weiter */
  const schlafEnde = () => api.sende("/api/hoerbuch/schlaf-ende", {}).then((a) => {
    if (a?.standby && himmelStopp) { himmelStopp(); himmelStopp = null; }
  }).catch(() => {});
  const wahlBox = el("div", { class: "hb-wahl", hidden: true });
  box.classList.add("hoerbuch");
  box.append(el("div", { class: "overlay-kopf" }, el("div", {}, kopfTitel, ort), hilfe),
    el("div", { class: "hb-flaeche" }, liste, spieler), wahlBox, schwarz);

  const z = {
    pfad: "", eintraege: [], wahl: 0, stand: null, maxMin: 60,
    wiedergabe: [], nr: -1, ordner: "",      /* was gerade läuft */
    schlafEnde: 0, schwarzAb: 0, wahlOffen: null, zuletztGemerkt: 0, ausblenden: false, geschlossen: false,
    erstesLaden: true, offenSeit: Date.now(), alarme: 0, ausCountdown: 0, gestartet: false,
  };

  /* ---------------------------------------------------------------- Liste */
  async function lade(pfad) {
    liste.replaceChildren(el("div", { class: "leise", text: "Einen Moment …" }));
    try {
      const d = await api.hole(`/api/hoerbuch/liste?app=${encodeURIComponent(app.id)}&pfad=${encodeURIComponent(pfad)}`);
      z.pfad = d.pfad; z.stand = d.stand; z.maxMin = d.schlaf_max_min || 60;
      if (z.nr < 0) zeigeCover(d.cover ? d.pfad : "");
      z.eintraege = [];
      if (d.eltern !== null && d.eltern !== undefined) z.eintraege.push({ art: "hoch", text: "⬆ Zurück", pfad: d.eltern });
      if (!d.pfad && d.stand && d.stand.titel) {
        z.eintraege.push({ art: "weiter", text: `▶ Weiterhören: ${ohneEndung(d.stand.titel.split("/").pop())} (${zeit(d.stand.sekunde)})` });
      }
      for (const o of d.ordner) z.eintraege.push({ art: "ordner", text: "📁 " + o.name, pfad: o.pfad });
      d.titel.forEach((t, i) => z.eintraege.push({ art: "titel", text: "🎵 " + ohneEndung(t.name), pfad: t.pfad, i, alle: d.titel }));
      if (!d.ordner.length && !d.titel.length) z.eintraege.push({ art: "leer", text: "Hier sind keine Hörbücher." });
      z.wahl = Math.min(z.wahl, z.eintraege.length - 1);
      ort.textContent = d.pfad ? d.pfad.split("/").join(" › ") : "";
      zeigeListe();
      if (z.erstesLaden && opt.weiter) {
        const weiter = z.eintraege.findIndex((e) => e.art === "weiter");
        if (weiter >= 0) { z.wahl = weiter; zeigeListe(); aktiviere(); }    /* Gute Nacht: gleich weiterhören */
      }
      z.erstesLaden = false;
    } catch (fehler) {
      liste.replaceChildren(el("div", { class: "meldung-fehler", text: fehler.message }));
    }
  }

  function zeigeListe() {
    liste.replaceChildren(...z.eintraege.map((e, i) => {
      const k = el("div", { class: "hb-eintrag" + (i === z.wahl ? " gewaehlt" : "") +
                                   (e.art === "titel" && z.wiedergabe[z.nr]?.pfad === e.pfad ? " laeuft" : "") }, el("span", { text: e.text }));
      if (e.art === "ordner") {                               /* 4.0: Cover statt Ordner-Symbol, wenn es eins gibt */
        k.replaceChildren(el("span", { class: "hb-symbol-klein", text: "📁" }), el("span", { class: "hb-name", text: e.text.replace(/^📁 /, "") }));
        const bild = el("img", { class: "hb-cover", alt: "",
          src: `/api/hoerbuch/cover?app=${encodeURIComponent(app.id)}&pfad=${encodeURIComponent(e.pfad)}` });
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
    if (e.art === "weiter") {
      const s = z.stand;
      const ordner = s.ordner;
      return api.hole(`/api/hoerbuch/liste?app=${encodeURIComponent(app.id)}&pfad=${encodeURIComponent(ordner)}`)
        .then((d) => {
          const nr = d.titel.findIndex((t) => t.pfad === s.titel);
          if (nr < 0) { api.hinweis("Das Hörbuch gibt es nicht mehr."); return; }
          frageSchlaf(() => spiele(d.titel, nr, ordner, s.sekunde));
        }).catch((f) => api.hinweis(f.message));
    }
    if (e.art === "titel") frageSchlaf(() => spiele(e.alle, e.i, z.pfad, 0));
  }

  /* ---------------------------------------------------------------- Sleep-Zeit wählen (Pflicht bei PLAY) */
  function frageSchlaf(weiter) {
    const zeiten = SCHLAF_WAHL.filter((m) => m <= z.maxMin);
    if (!zeiten.length) zeiten.push(z.maxMin);
    let i = Math.min(zeiten.indexOf(30) >= 0 ? zeiten.indexOf(30) : zeiten.length - 1, zeiten.length - 1);
    const knoepfe = zeiten.map((m) => el("div", { class: "knopf", text: m < 60 ? `${m} min` : `${m / 60} h`.replace(".5", ",5") }));
    knoepfe.forEach((k, n) => k.addEventListener("click", () => { i = n; bestaetige(); }));
    const zeige = () => knoepfe.forEach((k, n) => k.classList.toggle("gewaehlt", n === i));
    wahlBox.replaceChildren(el("div", { class: "hb-wahl-karte" },
      el("h3", { text: "🌙 Wie lange möchtest du hören?" }),
      el("div", { class: "knopfreihe" }, ...knoepfe),
      el("p", { class: "leise", text: "← → wählen · OK starten · STOP abbrechen. Danach geht das Bild aus, das Hörbuch hört von allein auf." })));
    wahlBox.hidden = false;
    zeige();
    const bestaetige = () => {
      wahlBox.hidden = true; z.wahlOffen = null;
      z.gestartet = true; z.ausCountdown = 0;
      z.schlafEnde = Date.now() + zeiten[i] * MINUTE_MS;
      weiter();
    };
    z.wahlOffen = (t) => {
      if (t === "ArrowLeft" || t === "ArrowUp") { i = (i + zeiten.length - 1) % zeiten.length; zeige(); ton("bewegen"); }
      else if (t === "ArrowRight" || t === "ArrowDown") { i = (i + 1) % zeiten.length; zeige(); ton("bewegen"); }
      else if (t === "Enter" || t === " " || ABSPIELEN.has(t)) bestaetige();
      else if (t === "Escape" || t === "Backspace") { wahlBox.hidden = true; z.wahlOffen = null; }
      return true;
    };
  }

  /* ---------------------------------------------------------------- Wiedergabe */
  function spiele(titel, nr, ordner, ab) {
    z.wiedergabe = titel; z.nr = nr; z.ordner = ordner;
    const t = titel[nr];
    audio.src = `/api/hoerbuch/datei?app=${encodeURIComponent(app.id)}&pfad=${encodeURIComponent(t.pfad)}`;
    audio.volume = 1;
    if (ab) audio.addEventListener("loadedmetadata", () => { audio.currentTime = Math.min(ab, (audio.duration || ab + 1) - 1); }, { once: true });
    audio.play().catch((f) => api.hinweis("Abspielen geht gerade nicht: " + f.message));
    titelAnzeige.textContent = ohneEndung(t.name);
    zeigeCover(ordner);
    ordnerAnzeige.textContent = ordner ? ordner.split("/").pop() : "";
    z.schwarzAb = Date.now() + SCHWARZ_NACH_S * 1000;
    zeigeListe();
  }

  function weiterAbspielen() {
    if (z.nr < 0) return;
    audio.volume = 1;
    audio.play().catch(() => {});
    z.schwarzAb = Date.now() + SCHWARZ_NACH_S * 1000;
  }

  function anhalten() {
    audio.pause();
    z.schlafEnde = 0;            /* nächstes PLAY fragt wieder nach der Zeit */
    merke(true);
  }

  function merke(sofort) {
    const t = z.wiedergabe[z.nr];
    if (!sofort && Date.now() - z.zuletztGemerkt < 15000) return;
    if (!t && schwarz.hidden) return;
    z.zuletztGemerkt = Date.now();
    api.sende("/api/hoerbuch/stand", { app: app.id, ordner: t ? z.ordner : "", titel: t ? t.pfad : "",
                                        sekunde: t ? Math.floor(audio.currentTime || 0) : 0,
                                        spielt: Boolean(t) && !audio.paused, dunkel: !schwarz.hidden }).catch(() => {});
  }

  /* Automatisch geöffnet, aber niemand wählt: kleine Alarme, dann Countdown, dann Fernseher aus */
  function automatik() {
    const offenMin = (Date.now() - z.offenSeit) / MINUTE_MS;
    if (z.alarme < ALARM_MIN.length && offenMin >= ALARM_MIN[z.alarme]) {
      z.alarme++;
      ton("ok", { laut: 0.12 });
      api.hinweis("🌙 Such dir noch aus, wie lange du hören möchtest.", 8000);
    }
    if (offenMin >= AUS_NACH_MIN && !z.ausCountdown) {
      z.ausCountdown = Date.now() + AUS_COUNTDOWN_S * 1000;
      wahlBox.hidden = true; z.wahlOffen = null;
    }
    if (z.ausCountdown) {
      const rest = Math.ceil((z.ausCountdown - Date.now()) / 1000);
      schlafAnzeige.textContent = `🌙 Der Fernseher geht in ${Math.max(0, rest)} s aus – drück PLAY für ein Hörbuch`;
      if (rest <= 0) {
        z.gestartet = true;                                /* nichts mehr automatisch */
        dunkel(true);
        schlafEnde();
      }
    }
  }

  audio.addEventListener("ended", () => {
    if (z.nr + 1 < z.wiedergabe.length) {
      const warDunkel = !schwarz.hidden;
      spiele(z.wiedergabe, z.nr + 1, z.ordner, 0);
      if (warDunkel) dunkel(true);                         /* im Dunkeln bleibt es dunkel */
    }
    else {
      /* 6.1: Zu Ende, während das Kind einschläft (Bild dunkel oder Schlaf-Zeit läuft): wie das Ende der Schlaf-Zeit -
         der Fernseher geht aus (der Server lässt ihn an, wenn der Wecker ihn sonst nicht wecken könnte) */
      const imSchlaf = !schwarz.hidden || Boolean(z.schlafEnde);
      z.schlafEnde = 0; merke(true);
      if (imSchlaf) { dunkel(true); schlafEnde(); }
      else api.hinweis("Das Hörbuch ist zu Ende.");
    }
  });
  audio.addEventListener("error", () => { if (audio.src) api.hinweis("Diese Datei lässt sich nicht abspielen."); });

  function wecke() {
    const warSchwarz = !schwarz.hidden;
    dunkel(false);
    if (!audio.paused) z.schwarzAb = Date.now() + SCHWARZ_NACH_S * 1000;
    return warSchwarz;
  }

  /* ---------------------------------------------------------------- Takt (1 s) */
  const takt = setInterval(() => {
    const laeuft = !audio.paused && z.nr >= 0;
    const dauer = audio.duration || 0;
    balken.firstChild.style.width = dauer ? `${Math.min(100, audio.currentTime / dauer * 100)}%` : "0";
    zeitAnzeige.textContent = z.nr >= 0 ? `${zeit(audio.currentTime)} / ${zeit(dauer)}  ·  Titel ${z.nr + 1} von ${z.wiedergabe.length}` +
                                          (laeuft ? "" : "  ·  angehalten") : "";
    const rest = z.schlafEnde ? (z.schlafEnde - Date.now()) / 1000 : 0;
    schlafAnzeige.textContent = laeuft && z.schlafEnde ? `🌙 Hört auf in ${zeit(rest)}` +
      (z.schwarzAb && schwarz.hidden ? `  ·  Bild geht in ${Math.max(0, Math.ceil((z.schwarzAb - Date.now()) / 1000))} s aus` : "") : "";
    if (laeuft && z.schwarzAb && Date.now() >= z.schwarzAb && schwarz.hidden && !z.wahlOffen) dunkel(true);
    if (!schwarz.hidden) merke(false);                     /* Server weiß: Einschlafbild, keine Töne */
    if (opt.automatisch && !z.gestartet) automatik();
    if (laeuft) merke(false);
    if (laeuft && z.schlafEnde && rest <= 8 && !z.ausblenden) {
      /* sanft leiser werden, dann aus */
      z.ausblenden = true;
      const schritt = setInterval(() => {
        audio.volume = Math.max(0, audio.volume - 0.07);
        if (audio.volume <= 0.01 || audio.paused) {
          clearInterval(schritt);
          audio.pause();
          z.schlafEnde = 0; z.ausblenden = false;
          merke(true);
          dunkel(true);
          schlafEnde();
        }
      }, 500);
    }
  }, 1000);

  lade("");

  return {
    taste(t) {
      if (z.wahlOffen) return z.wahlOffen(t);
      const warSchwarz = wecke();
      if (ABSPIELEN.has(t) || (ANHALTEN.has(t) && audio.paused)) {
        if (z.nr < 0) { aktiviere(); return true; }          /* nichts gewählt: gewählten Eintrag starten */
        if (!audio.paused && t === "MediaPlayPause") { anhalten(); return true; }
        if (!audio.paused) return true;
        frageSchlaf(weiterAbspielen);
        return true;
      }
      if (ANHALTEN.has(t)) { anhalten(); return true; }
      if (t === "MediaFastForward") { audio.currentTime = Math.min((audio.duration || 0) - 1, audio.currentTime + SPRUNG_S); return true; }
      if (t === "MediaRewind") { audio.currentTime = Math.max(0, audio.currentTime - SPRUNG_S); return true; }
      if ((t === "MediaTrackNext" || t === "MediaTrackPrevious") && z.nr >= 0) {   /* 4.1: Tastatur ⏮ ⏭ = Titel */
        const neu = t === "MediaTrackNext" ? z.nr + 1 : (audio.currentTime > 5 ? z.nr : z.nr - 1);
        if (neu >= 0 && neu < z.wiedergabe.length) { const warDunkel = !schwarz.hidden; spiele(z.wiedergabe, neu, z.ordner, 0); if (warDunkel) dunkel(true); }
        return true;
      }
      if (warSchwarz) return true;                           /* erste Taste im Dunkeln weckt nur */
      if (t === "ArrowUp") { z.wahl = Math.max(0, z.wahl - 1); zeigeListe(); ton("bewegen"); return true; }
      if (t === "ArrowDown") { z.wahl = Math.min(z.eintraege.length - 1, z.wahl + 1); zeigeListe(); ton("bewegen"); return true; }
      if (t === "Enter" || t === " ") { aktiviere(); return true; }
      if ((t === "ArrowLeft" || t === "Backspace") && z.pfad) {
        const hoch = z.eintraege.find((e) => e.art === "hoch");
        if (hoch) { z.wahl = 0; lade(hoch.pfad); }
        return true;
      }
      if (t === "ArrowLeft" || t === "ArrowRight") return true;
      return t !== "Escape" && t !== "Backspace";             /* STOP schließt */
    },
    schliesse() {
      if (z.geschlossen) return;
      z.geschlossen = true;
      clearInterval(takt);
      dunkel(false);
      if (z.nr >= 0) merke(true);
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
    },
  };
}
