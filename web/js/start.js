/* FernsehFranzi 3.0 - Startseite.
 *
 * Kacheln kommen vom Server (/api/apps: App-Katalog + Spielzimmer, mit Sperrgrund aus dem
 * Zeitkonto). Eingabe: Tastatur-Ereignisse - Fernbedienung und Controller übersetzt
 * eingabe.py in Tasten, die Startseite liest keine Gamepads selbst (ein Besitzer pro Aufgabe).
 */
import { hole, sende, el, pause } from "./gemeinsam.js";
import { oeffneElternbereich } from "./eltern.js";
import { oeffneHoerbuch } from "./hoerbuch.js";
import { oeffneYoutube } from "./youtube.js";
import { oeffneVideo } from "./video.js";
import { ton } from "./spiele/kern.js";
import snake from "./spiele/snake.js";
import memory from "./spiele/memory.js";
import drei from "./spiele/drei.js";
import echo from "./spiele/echo.js";
import malen from "./spiele/malen.js";
import witz from "./spiele/witz.js";
import bass from "./spiele/bass.js";
import duell from "./spiele/duell.js";
import sticker from "./spiele/sticker.js";
import lernen from "./spiele/lernen.js";
import gutschein from "./spiele/gutschein.js";
import wecker from "./spiele/wecker.js";
import nachrichten from "./spiele/nachrichten.js";
import gestalten, { designZeigen } from "./spiele/gestalten.js";
import handys from "./spiele/handys.js";
import fotoalbum from "./spiele/fotoalbum.js";
import karaoke from "./spiele/karaoke.js";
import wetter from "./spiele/wetter.js";
import schule from "./spiele/schule.js";
import kinderwelten from "./spiele/kinderwelten.js";
import news from "./spiele/news.js";

const SPIELE = { "spiel-snake": snake, "spiel-memory": memory, "spiel-drei": drei,
                 "spiel-echo": echo, "spiel-malen": malen, "spiel-witz": witz, "spiel-bass": bass,
                 "spiel-duell": duell, "spiel-sticker": sticker, "spiel-lernen": lernen, "spiel-gutschein": gutschein, "spiel-wecker": wecker,
                 "spiel-nachrichten": nachrichten, "spiel-gestalten": gestalten, "spiel-handys": handys, "spiel-fotoalbum": fotoalbum, "spiel-karaoke": karaoke,
                 "spiel-wetter": wetter, "spiel-schule": schule, "spiel-kinderwelten": kinderwelten, "spiel-news": news };
const SYMBOLE = { video: "▶️", film: "🎬", spiel: "🕹️", haus: "🏠", buch: "📚", lernen: "🎓", musik: "🎵",
                  malen: "🎨", web: "🌐", stern: "⭐", mond: "🌙", tier: "🐾", ball: "⚽" };
const FARBEN = { "spiel-snake": "#1d7a5e", "spiel-memory": "#8a3b8a", "spiel-drei": "#a8791c",
                 "spiel-echo": "#2a6b9e", "spiel-malen": "#6d3fa8", "spiel-witz": "#b06520",
                 "spiel-bass": "#8d2f2f", "spiel-duell": "#2f6d8d", "spiel-sticker": "#8d7a2f", "spiel-lernen": "#00897b", "spiel-handys": "#2f5fa8", "spiel-fotoalbum": "#2f7a8d", "spiel-karaoke": "#a8326b",
                 "spiel-wetter": "#2f86c9", "spiel-schule": "#3a7d44", "spiel-kinderwelten": "#e07b1a", "spiel-news": "#6b4fb3",
                 "gute-nacht": "#2b2f6b", "retro": "#4a2b6b" };
const TON_NAMEN = { hdmi: "Fernseher (HDMI)", klinke: "Klinke (Kopfhörer / Anlage)", kopfhoerer: "🎧 Bluetooth-Kopfhörer" };

const zustand = {
  reihen: [[], [], []],      // [Apps, Spielzimmer, Zuletzt gespielt] - je eine Liste von {daten, knoten}
  letzteTaste: Date.now(), schoner: null, meldungen: null, nachtSchwarz: null, still: false,
  zeile: 0, spalte: 0,
  overlay: null,             // offenes Spiel oder Elternbereich: {taste(key) -> bool, schliesse()}
  meldungNr: null, tonNr: null, retropie: false, retropieMarke: null,
  gesperrt: null, letzteEingabeGemeldet: 0,
};

/* ------------------------------------------------------------ Hinweis */
let hinweisTimer = 0;
export function hinweis(text, ms = 3500) {
  const box = document.getElementById("hinweis");
  box.textContent = text;
  box.classList.add("zeigen");
  clearTimeout(hinweisTimer);
  hinweisTimer = setTimeout(() => box.classList.remove("zeigen"), ms);
}

/* ------------------------------------------------------------ Uhr und Gruß */
function uhrStellen() {
  const jetzt = new Date();
  document.getElementById("uhr").textContent =
    jetzt.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
  document.getElementById("datum").textContent =
    jetzt.toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long" });
}

function gruessen(name) {
  const h = new Date().getHours();
  const gruss = h < 11 ? "Guten Morgen" : h < 17 ? "Hallo" : "Guten Abend";
  document.getElementById("gruss").textContent = name ? `${gruss}, ${name}!` : `${gruss}!`;
}

/* ------------------------------------------------------------ Kacheln */
const SPERR_SYMBOL = { zeit: "⏳", nacht: "🌙", schule: "🏫", sperrzeit: "🚫", eltern: "🔒", uhr: "🕐" };
function baueKachel(app, nummer) {
  const istSpiel = app.typ === "spiel";
  const farbe = app.farbe || FARBEN[app.id] || "#2a3550";
  const symbol = SYMBOLE[app.symbol] || (istSpiel && SPIELE[app.id]?.symbol) || "⭐";
  const knoten = el("button", { class: "kachel" + (app.frei ? "" : " gesperrt"), type: "button", tabindex: "-1",
                                "data-id": app.id },
    el("div", { class: "bg", style: `--farbe: ${farbe}; background: linear-gradient(130deg, var(--kachel-anfang), ${farbe})` }),
    el("span", { class: "taste", text: nummer }),
    el("div", { class: "symbol", text: symbol }),
    el("div", {},
      el("div", { class: "name", text: app.name }),
      null));
  /* 3.4: gesperrt = nur grau mit einem Symbol (den Grund sagt der Hinweis beim Anwählen) */
  const symbolSperre = !app.frei ? (SPERR_SYMBOL[app.sperre] || "🔒") : app.eingerichtet === false ? "⚙️" : "";
  if (symbolSperre) {
    knoten.classList.add("gesperrt");
    knoten.append(el("div", { class: "sperr-symbol", text: symbolSperre }));
  }
  if (app.liebling) knoten.append(el("div", { class: "liebling", text: "⭐" }));
  knoten.addEventListener("click", () => oeffne(app));
  return knoten;
}

/* 3.5: Bereiche (Konsolen-Stil). Eltern können eine App einem Bereich zuordnen (Feld "bereich"), sonst automatisch. */
const BEREICHE = [
  { id: "start", name: "Start", symbol: "🏠" }, { id: "spiele", name: "Spiele", symbol: "🎮" },
  { id: "lernen", name: "Lernen", symbol: "🎓" }, { id: "musik", name: "Musik", symbol: "🎼" },
  { id: "filme", name: "Filme & YouTube", symbol: "🎬" }, { id: "retro", name: "Retro", symbol: "🕹️" },
];
const START_IDS = ["gute-nacht", "spiel-nachrichten", "spiel-wecker", "spiel-gutschein", "familie", "spiel-gestalten", "spiel-fotoalbum",
                   "spiel-wetter", "spiel-schule", "spiel-news"];
function bereichVon(app) {
  if (app.bereich && BEREICHE.some((b) => b.id === app.bereich)) return app.bereich;
  if (START_IDS.includes(app.id)) return "start";
  if (app.typ === "youtube" || app.typ === "hoerbuch" || app.typ === "video" || app.id === "plex") return "filme";
  if (app.typ === "konsole" || app.typ === "retro") return "retro";
  if (app.id === "spiel-bass" || app.id === "spiel-karaoke") return "musik";
  if (app.lernen || app.id === "buecher") return "lernen";
  if (app.typ === "spiel") return "spiele";
  return "start";
}
const BESCHREIBUNG = { "gute-nacht": "Hörbuch zum Einschlafen", "spiel-wecker": "Deine Wecker", "spiel-gutschein": "Code vom Zettel einlösen",
                       "spiel-bass": "Bass, Gitarre, Keyboard, Singen", youtube: "Deine Videos", games: "Alle Retro-Spiele",
                       "spiel-wetter": "Wann kann ich raus?", "spiel-schule": "Stundenplan und Hausaufgaben",
                       "spiel-kinderwelten": "Geschichten lesen, Rätsel, Draußen-Spiele", "spiel-news": "Nachrichten für Kinder" };

async function ladeKacheln() {
  let apps;
  try {
    apps = (await hole("/api/apps")).apps;
  } catch (_) {
    hinweis("Die Startseite wartet auf den Server ...");
    return false;
  }
  /* 3.1: Zuletzt gespielt / Lieblingsspiele aus RetroPie - in den Bereich Retro */
  let retro = [];
  try { retro = (await hole("/api/retro")).spiele; } catch (_) { /* ohne */ }
  const gamesFrei = apps.find((a) => a.id === "games");
  const alle = apps.concat(retro.map((spiel) => ({ id: "retro", typ: "retro", name: spiel.name, symbol: spiel.favorit ? "stern" : "spiel",
    frei: gamesFrei ? gamesFrei.frei : true, grund: gamesFrei?.grund, sperre: gamesFrei?.sperre, zaehlt: true, spiel })));
  /* 4.0: vom Kind gestaltet - Lieblinge vorne in „Start“, Hintergrund */
  let gestaltung = { lieblinge: [], thema: "weltall" };
  try { gestaltung = await hole("/api/startseite"); } catch (_) { /* Vorgabe */ }
  designZeigen(gestaltung.design?.jetzt || gestaltung.thema, gestaltung.design?.hell,   /* 5.0: Design (abends dunkel) */
               gestaltung.design?.ansicht || "konsole");                              /* 5.0: Ansicht */
  const vorher = zustand.reihen[zustand.zeile]?.bereich;
  zustand.reihen = [];
  const reihenBox = document.getElementById("reihen");
  reihenBox.replaceChildren();
  for (const b of BEREICHE) {
    let inhalt = alle.filter((a) => bereichVon(a) === b.id);
    if (b.id === "start") {
      const lieb = (gestaltung.lieblinge || []).map((id) => alle.find((a) => a.id === id)).filter(Boolean)
        .map((a) => ({ ...a, liebling: true }));
      inhalt = lieb.concat(inhalt.filter((a) => !(gestaltung.lieblinge || []).includes(a.id)));
    }
    if (!inhalt.length) continue;
    const zeile = el("div", { class: "reihe-kacheln" });
    const reihe = [];
    inhalt.forEach((app, i) => {
      const taste = i < 10 ? String((i + 1) % 10) : "";
      const knoten = baueKachel(app, taste);
      zeile.append(knoten);
      reihe.push({ daten: app, knoten, taste });
    });
    const abschnitt = el("section", { class: "reihe", "data-bereich": b.id, "aria-label": b.name },
      el("h2", { class: "reihe-titel", text: `${b.symbol} ${b.name}` }), zeile);
    reihenBox.append(abschnitt);
    reihe.bereich = b.id;
    reihe.abschnitt = abschnitt;
    zustand.reihen.push(reihe);
  }
  /* Leiste oben */
  const leiste = document.getElementById("bereiche");
  leiste.replaceChildren(...zustand.reihen.map((r, z) => {
    const b = BEREICHE.find((x) => x.id === r.bereich);
    const k = el("button", { type: "button", tabindex: "-1", class: "bereich", "data-bereich": b.id }, el("span", { text: b.symbol }), b.name);
    k.addEventListener("click", () => { markiere(z, 0); ton("bewegen"); });
    return k;
  }));
  const zeile = Math.max(0, zustand.reihen.findIndex((r) => r.bereich === vorher));
  markiere(zeile, zustand.reihen[zeile]?.bereich === vorher ? zustand.spalte : 0);
  return true;
}

function markiere(zeile, spalte) {
  if (!zustand.reihen[zeile]?.length) zeile = zustand.reihen.findIndex((r) => r.length);
  if (zeile < 0) return;
  const reihe = zustand.reihen[zeile] || [];
  if (!reihe.length) return;
  zustand.zeile = zeile;
  zustand.spalte = Math.max(0, Math.min(spalte, reihe.length - 1));
  for (const r of zustand.reihen) {
    r.abschnitt.classList.toggle("aktiv", r === reihe);
    for (const k of r) k.knoten.classList.remove("gewaehlt");
  }
  const k = reihe[zustand.spalte];
  k.knoten.classList.add("gewaehlt");
  /* aktive Reihe nach oben schieben, gewählte Kachel in den sichtbaren Bereich */
  const fenster = document.getElementById("reihen");
  const ansicht = document.body.dataset.ansicht || "konsole";     /* 5.0: Konsole · Seitenleiste · Karussell */
  fenster.style.transform = ansicht === "konsole" ? `translateY(${-reihe.abschnitt.offsetTop}px)` : "none";
  const streifen = k.knoten.parentElement;
  if (ansicht === "seitenleiste") {
    /* Raster: nur so weit nach oben schieben, dass die gewählte Kachel ganz zu sehen ist */
    const sicht = document.getElementById("reihen-fenster").clientHeight;
    let versatz = Number(streifen.dataset.versatz || 0);
    const oben = k.knoten.offsetTop, unten = oben + k.knoten.offsetHeight;
    if (oben - versatz < 10) versatz = Math.max(0, oben - 10);
    if (unten - versatz > sicht - 20) versatz = unten - sicht + 20;
    streifen.dataset.versatz = String(versatz);
    streifen.style.transform = `translateY(${-versatz}px)`;
  } else if (ansicht === "karussell") {
    /* die gewählte Kachel steht immer in der Mitte */
    const versatz = k.knoten.offsetLeft + k.knoten.offsetWidth / 2 - streifen.clientWidth / 2;
    streifen.dataset.versatz = String(versatz);
    streifen.style.transform = `translateX(${-versatz}px)`;
  } else {
    /* Reihe nur so weit schieben, dass die gewählte Kachel ganz zu sehen ist (mit etwas Rand) */
    let versatz = Number(streifen.dataset.versatz || 0);
    const rand = 40, sicht = streifen.clientWidth;
    const links = k.knoten.offsetLeft, rechts = links + k.knoten.offsetWidth;
    if (links - versatz < rand) versatz = Math.max(0, links - rand);
    if (rechts - versatz > sicht - rand) versatz = rechts - sicht + rand;
    streifen.dataset.versatz = String(versatz);
    streifen.style.transform = `translateX(${-versatz}px)`;
  }
  for (const b of document.querySelectorAll("#bereiche .bereich")) b.classList.toggle("an", b.dataset.bereich === reihe.bereich);
  /* großer Titel wie bei der Konsole, Hintergrund in der Farbe der Kachel */
  const d = k.daten;
  document.getElementById("held-name").textContent = d.name;
  document.getElementById("held-info").textContent = !d.frei ? d.grund : d.eingerichtet === false ? "Noch nicht eingerichtet"
    : BESCHREIBUNG[d.id] || (d.typ === "retro" ? "Zuletzt gespielt" : d.zaehlt ? "Mit Spielzeit" : "Ohne Zeit");
  document.body.style.setProperty("--held-farbe", d.farbe || FARBEN[d.id] || "#2a3550");
}

function anschlag(dx, dy) {
  const k = zustand.reihen[zustand.zeile][zustand.spalte]?.knoten;
  if (!k) return;
  k.style.setProperty("--stoss-x", dx * 10 + "px");
  k.style.setProperty("--stoss-y", dy * 10 + "px");
  k.classList.remove("anschlag");
  void k.offsetWidth;
  k.classList.add("anschlag");
  ton("anschlag");
}

function bewege(dx, dy) {
  if (dy) {
    let ziel = zustand.zeile + dy;
    while (ziel >= 0 && ziel < zustand.reihen.length && !zustand.reihen[ziel].length) ziel += dy;
    if (ziel < 0 || ziel >= zustand.reihen.length) return anschlag(0, dy);
    /* ungefähr gleiche horizontale Lage in der anderen Reihe */
    const anteil = (zustand.spalte + 0.5) / zustand.reihen[zustand.zeile].length;
    markiere(ziel, Math.floor(anteil * zustand.reihen[ziel].length));
  } else {
    const ziel = zustand.spalte + dx;
    if (ziel < 0 || ziel >= zustand.reihen[zustand.zeile].length) return anschlag(dx, 0);
    markiere(zustand.zeile, ziel);
  }
  ton("bewegen");
}

/* ------------------------------------------------------------ Öffnen */
async function oeffne(app) {
  if (!app.frei) { hinweis(app.grund); ton("fehler"); return; }
  if (app.eingerichtet === false) { hinweis(`${app.name} ist noch nicht eingerichtet. Bitte Mama oder Papa fragen.`); ton("fehler"); return; }
  if (app.typ === "retro") {
    try {
      hinweis((await sende("/api/retro/start", { system: app.spiel.system, rom: app.spiel.rom })).meldung);
      zustand.retropieAngefordert = Date.now();
      zustand.retropieMarke = zustand.letzteMarke;
      ton("ok");
    } catch (e) { hinweis(e.message); ton("fehler"); }
    return;
  }
  if (app.typ === "spiel") return oeffneSpiel(app);
  if (app.typ === "hoerbuch") return oeffneHoerbuecher(app, { weiter: app.id === GUTE_NACHT });
  if (app.typ === "youtube") return oeffneYoutubeBereich(app);
  if (app.typ === "video") return oeffneVideoBereich(app);
  try {
    const antwort = await sende("/api/start", { id: app.id });
    hinweis(antwort.meldung || "Los geht's!");
    ton("ok");
    if (app.typ === "konsole") { zustand.retropieAngefordert = Date.now(); zustand.retropieMarke = zustand.letzteMarke; }
  } catch (fehler) {
    hinweis(fehler.message);
    ton("fehler");
    ladeKacheln();
  }
}

function oeffneSpiel(app) {
  const spiel = SPIELE[app.id];
  if (!spiel) return;
  /* Sofort öffnen (Tasten direkt danach gehören schon dem Spiel), anmelden im Hintergrund */
  sende("/api/start", { id: app.id }).catch((fehler) => {
    if (zustand.overlay?.id === app.id) { schliesseOverlay(); hinweis(fehler.message); ton("fehler"); }
  });
  const wurzel = document.getElementById("overlay-wurzel");
  const box = el("section", { class: "overlay" });
  wurzel.replaceChildren(box);
  const steuerung = spiel.oeffne(box, { hinweis, sende, hole, schliessen: schliesseOverlay });
  zustand.overlay = { ...steuerung, id: app.id };
  ton("ok");
}

/* 3.3: Hörbücher - Player als Overlay auf der Startseite. 3.4: "Gute Nacht" ist die Hörbuch-App gute-nacht */
const GUTE_NACHT = "gute-nacht";
async function oeffneHoerbuecher(app, opt = {}) {
  if (zustand.overlay) schliesseOverlay();
  try {
    await sende("/api/start", { id: app.id });
  } catch (fehler) { hinweis(fehler.message); ton("fehler"); return; }
  const box = el("section", { class: "overlay" });
  document.getElementById("overlay-wurzel").replaceChildren(box);
  zustand.overlay = { ...oeffneHoerbuch(box, { hinweis, sende, hole }, app, opt), id: app.id };
  if (!opt.automatisch) ton("ok");
}

/* 3.5: YouTube-Bereich (eigener Player, nur Videos/Playlists der Eltern) */
async function oeffneYoutubeBereich(app) {
  if (zustand.overlay) schliesseOverlay();
  try { await sende("/api/start", { id: app.id }); } catch (fehler) { hinweis(fehler.message); ton("fehler"); return; }
  const box = el("section", { class: "overlay" });
  document.getElementById("overlay-wurzel").replaceChildren(box);
  zustand.overlay = { ...oeffneYoutube(box, { hinweis, sende, hole }), id: app.id };
  ton("ok");
}

/* 4.0: eigener Video-Player (Filme/Serien aus einer FileBrowser-Freigabe) */
async function oeffneVideoBereich(app) {
  if (zustand.overlay) schliesseOverlay();
  try { await sende("/api/start", { id: app.id }); } catch (fehler) { hinweis(fehler.message); ton("fehler"); return; }
  const box = el("section", { class: "overlay" });
  document.getElementById("overlay-wurzel").replaceChildren(box);
  zustand.overlay = { ...oeffneVideo(box, { hinweis, sende, hole }, app), id: app.id };
  ton("ok");
}

async function guteNachtOeffnen(automatisch) {
  let apps = [];
  try { apps = (await hole("/api/apps")).apps; } catch (_) { /* unten */ }
  const app = apps.find((a) => a.id === GUTE_NACHT);
  if (!app || app.eingerichtet === false) { hinweis("Gute Nacht ist noch nicht eingerichtet. Bitte Mama oder Papa fragen."); return; }
  oeffneHoerbuecher(app, { weiter: true, automatisch });
}

/* 3.4: Beginn der Nachtruhe ohne automatische Gute Nacht - 15 s Countdown mit drei Knöpfen */
function nachtFrage() {
  if (zustand.overlay) schliesseOverlay();
  const box = el("section", { class: "overlay nacht-frage" });
  const zahl = el("div", { class: "nacht-zahl" });
  const wahl = [["aus", "📴 Fernseher aus"], ["an", "📺 Fernseher an"], ["gute-nacht", "🌙 Gute Nacht"]];
  const knoepfe = wahl.map(([w, t]) => { const k = el("button", { class: "knopf", type: "button", tabindex: "-1", text: t });
    k.addEventListener("click", () => fertig(w)); return k; });
  box.append(el("div", { class: "nacht-mond", text: "🌙" }), el("h2", { text: "Jetzt ist Nachtruhe" }), zahl,
    el("div", { class: "knopfreihe" }, ...knoepfe));
  document.getElementById("overlay-wurzel").replaceChildren(box);
  let i = 2, rest = 15;
  const zeige = () => knoepfe.forEach((k, n) => k.classList.toggle("gewaehlt", n === i));
  const takt = () => {
    zahl.textContent = String(rest);
    if (rest <= 0) return fertig("aus");
    if (!zustand.still) ton(rest <= 5 ? "punkt" : "bewegen");
    rest--;
  };
  const timer = setInterval(takt, 1000);
  function fertig(w) {
    clearInterval(timer);
    zustand.overlay = null;
    box.remove();
    sende("/api/nacht", { wahl: w === "gute-nacht" ? "an" : w }).catch(() => {});
    if (w === "aus") nachtSchwarz();
    else if (w === "gute-nacht") guteNachtOeffnen(false);
    else ladeKacheln();
  }
  zeige(); takt();
  zustand.overlay = { id: "nacht", schliesse: () => clearInterval(timer), taste(t) {
    if (t === "ArrowLeft" || t === "ArrowUp") { i = (i + 2) % 3; zeige(); return true; }
    if (t === "ArrowRight" || t === "ArrowDown") { i = (i + 1) % 3; zeige(); return true; }
    if (t === "Enter" || t === " ") { fertig(wahl[i][0]); return true; }
    return true;
  } };
}

/* 3.5: Wecker klingelt - große Uhr, Ton wird langsam lauter. OK = schlummern (5 min), STOP = aus. */
function weckerKlingelt(info) {
  if (zustand.overlay?.id === "wecker-klingelt") return;
  if (zustand.overlay) schliesseOverlay();
  zustand.nachtSchwarz?.remove(); zustand.nachtSchwarz = null;
  if (zustand.schoner) schonerAus();
  const box = el("section", { class: "overlay wecker-klingelt" });
  const uhr = el("div", { class: "wecker-uhr" });
  box.append(el("div", { class: "wecker-sonne", text: "☀️" }), uhr, el("h2", { text: "Guten Morgen!" }),
    el("div", { class: "knopfreihe wecker-knoepfe" }, el("div", { class: "knopf gewaehlt", "data-aktion": "schlummern", text: "😴 Noch 5 Minuten" }),
      el("div", { class: "knopf", "data-aktion": "aus", text: "⏹ Wecker aus" })),
    el("div", { class: "leise", text: "◀ ▶ wählen · OK bestätigen · STOP = aus" }));
  document.getElementById("overlay-wurzel").replaceChildren(box);
  const stellen = () => { uhr.textContent = new Date().toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }); };
  stellen();
  let lautstaerke = 0.15, audio = null, sanft = null;
  if (info.ton) {
    audio = new Audio(`/api/wecker/ton?pfad=${encodeURIComponent(info.ton)}`);
    audio.loop = true;
    audio.volume = lautstaerke;
    audio.play().catch(() => { audio = null; sanft = setInterval(() => ton("sieg", { laut: lautstaerke }), 2500); });
  } else sanft = setInterval(() => ton("sieg", { laut: Math.min(0.35, lautstaerke) }), 2500);
  const lauter = setInterval(() => {                            /* in 30 s auf volle Lautstärke (die Höhe setzt der Server) */
    lautstaerke = Math.min(1, lautstaerke + 0.03);
    if (audio) audio.volume = lautstaerke;
    stellen();
  }, 1000);
  const vonSelbstAus = setTimeout(() => fertig("aus"), 15 * 60 * 1000);
  function fertig(aktion) {
    clearInterval(lauter); clearInterval(sanft); clearTimeout(vonSelbstAus);
    if (audio) { audio.pause(); audio.removeAttribute("src"); audio.load(); }
    zustand.overlay = null;
    box.remove();
    sende("/api/wecker/aktion", { aktion }).catch(() => {});
    hinweis(aktion === "schlummern" ? "😴 Noch 5 Minuten …" : "☀️ Einen schönen Tag!");
    ladeKacheln();
  }
  zustand.overlay = { id: "wecker-klingelt", schliesse: () => { clearInterval(lauter); clearInterval(sanft); clearTimeout(vonSelbstAus); audio?.pause(); },
    /* 4.4: Pfeile wählen zwischen den Knöpfen (Pfeile = immer Navigation), OK bestätigt die Auswahl, STOP = aus.
       Vorher war jede Taste „Schlummern“ - auch die Pfeile, mit denen man „Aus“ wählen wollte. */
    taste(t) {
      if (t === "Escape" || t === "Backspace" || t === "MediaStop") { fertig("aus"); return true; }
      if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(t)) {
        const knoepfe = [...box.querySelectorAll(".wecker-knoepfe .knopf")];
        const jetzt = knoepfe.findIndex((k) => k.classList.contains("gewaehlt"));
        knoepfe.forEach((k, i) => k.classList.toggle("gewaehlt", i === (jetzt + 1) % knoepfe.length));
        ton("bewegen");
        return true;
      }
      if (t === "Enter" || t === " " || t === "MediaPlayPause") {
        fertig(box.querySelector(".wecker-knoepfe .knopf.gewaehlt")?.dataset.aktion || "schlummern");
        return true;
      }
      return true;                                             /* andere Tasten tun nichts (kein versehentliches Schlummern) */
    } };
}

/* 4.0: Sonnenaufgang - der Bildschirm wird über einige Minuten von schwarz über dunkelrot und orange zu warmweiß
   (das Zimmer wird langsam hell). Eine Taste beendet ihn; der Wecker klingelt trotzdem zur Weckzeit. */
const SONNE_FARBEN = [[0, [0, 0, 0]], [0.25, [60, 8, 4]], [0.5, [150, 40, 10]], [0.75, [235, 130, 50]], [1, [255, 236, 205]]];
function sonnenaufgang(minuten) {
  if (zustand.overlay) schliesseOverlay();
  zustand.nachtSchwarz?.remove(); zustand.nachtSchwarz = null;
  if (zustand.schoner) schonerAus();
  const box = el("section", { class: "overlay sonne" });
  document.getElementById("overlay-wurzel").replaceChildren(box);
  const start = Date.now(), dauer = minuten * 60000;
  const farbe = (p) => {
    let i = 0;
    while (i < SONNE_FARBEN.length - 2 && p > SONNE_FARBEN[i + 1][0]) i++;
    const [p0, a] = SONNE_FARBEN[i], [p1, b] = SONNE_FARBEN[i + 1];
    const t = Math.min(1, Math.max(0, (p - p0) / (p1 - p0)));
    return `rgb(${a.map((x, k) => Math.round(x + (b[k] - x) * t)).join(",")})`;
  };
  const schritt = () => {
    const p = Math.min(1, (Date.now() - start) / dauer);
    box.style.background = `radial-gradient(ellipse at 50% 110%, ${farbe(Math.min(1, p * 1.15))} 0, ${farbe(p * 0.8)} 70%)`;
  };
  schritt();
  const timer = setInterval(schritt, 2000);
  zustand.overlay = { id: "sonne", schliesse: () => clearInterval(timer), taste() { schliesseOverlay(); return true; } };
}

/* Fernseher aus: zusätzlich schwarzes Bild (falls der Fernseher CEC nicht befolgt); eine Taste weckt */
function nachtSchwarz() {
  const box = el("div", { id: "nacht-schwarz" });
  document.body.append(box);
  zustand.nachtSchwarz = box;
}

/* 3.4: Erinnerungen und Nachrichten bleiben stehen, bis OK gedrückt wird */
function zeigeMeldungen(liste) {
  const nummern = liste.map((m) => m.nr).join(",");
  if (!liste.length || zustand.still) {
    if (zustand.meldungen) { zustand.meldungen.box.remove(); zustand.meldungen = null; }
    return;
  }
  if (zustand.meldungen?.nummern === nummern) return;
  zustand.meldungen?.box.remove();
  const uhr = (iso) => iso.slice(11, 16);
  const box = el("div", { id: "meldungen" },
    el("div", { class: "meldungen-karte" },
      /* 4.3: Wer schreibt? Symbol und Name des Telegram-Kontakts (sonst „Nachricht von Mama oder Papa“) */
      el("div", { class: "meldungen-symbol", text: liste.every((m) => m.symbol && m.symbol === liste[0].symbol) ? liste[0].symbol : "📣" }),
      ...liste.map((m) => el("div", { class: "meldung-zeile" }, el("span", { class: "meldung-uhr", text: uhr(m.zeit) }),
        el("span", {}, el("b", { text: (m.quelle ? (m.symbol ? m.symbol + " " : "") + m.quelle + ": " : "") }), m.text))),
      mediumAnzeige(liste.filter((m) => m.medium).pop()?.medium),
      el("button", { class: "knopf gewaehlt", type: "button", tabindex: "-1", text: "OK, gesehen" })));
  box.querySelector("button").addEventListener("click", meldungenBestaetigen);
  document.body.append(box);
  zustand.meldungen = { box, nummern, liste };
  ton("ok");
}

/* 4.4: Foto, Sprachnachricht, Musik oder Video von Telegram - groß in der Meldung, Ton/Video spielt einmal von selbst */
function mediumAnzeige(medium) {
  if (!medium?.datei) return null;
  const quelle = "/medien/" + medium.datei;
  if (medium.art === "foto") return el("img", { class: "meldung-foto", src: quelle, alt: "" });
  if (medium.art === "video") return el("video", { class: "meldung-video", src: quelle, autoplay: true, playsinline: true });
  return el("audio", { src: quelle, autoplay: true });
}

function meldungenBestaetigen() {
  if (!zustand.meldungen) return;
  const nummern = zustand.meldungen.liste.map((m) => m.nr);
  zustand.meldungen.box.remove();
  zustand.meldungen = null;
  sende("/api/meldungen/gesehen", { nummern }).catch(() => {});
}

function schliesseOverlay() {
  if (!zustand.overlay) return;
  try { zustand.overlay.schliesse?.(); } catch (_) { /* weiter */ }
  const war = zustand.overlay.id;
  zustand.overlay = null;
  document.getElementById("overlay-wurzel").replaceChildren();
  if (war && war !== "eltern") sende("/api/ort", { app: null }).catch(() => {});
  if (location.hash) history.replaceState(null, "", location.pathname);
  ladeKacheln();
}

function oeffneEltern() {
  if (zustand.overlay) schliesseOverlay();
  const box = el("section", { class: "overlay" });
  document.getElementById("overlay-wurzel").replaceChildren(box);
  zustand.overlay = { ...oeffneElternbereich(box, { hinweis, schliessen: schliesseOverlay, amFernseher: true }), id: "eltern" };
}

/* ------------------------------------------------------------ Tasten */
/* Tastendrücke gesammelt melden (Server: aktive Lernminuten, „Bist du noch da?“-Prüfung) */
const TASTEN_NAME = { ArrowLeft: "LEFT", ArrowRight: "RIGHT", ArrowUp: "UP", ArrowDown: "DOWN", Enter: "ENTER", Escape: "ESC" };
let gedrueckt = [];
function eingabeMelden(taste) {
  gedrueckt.push(TASTEN_NAME[taste] || String(taste).slice(0, 12).toUpperCase());
  const jetzt = Date.now();
  if (jetzt - zustand.letzteEingabeGemeldet > 5000) {
    zustand.letzteEingabeGemeldet = jetzt;
    const tasten = gedrueckt.slice(0, 60);
    gedrueckt = [];
    sende("/api/eingabe", { tasten }).catch(() => {});
  }
}

let tonZeit = 0;
function tonAusgang(ziel) {
  if (Date.now() - tonZeit < 1500) return;
  tonZeit = Date.now();
  sende("/api/audio", { ziel }).then(() => hinweis("Ton: " + TON_NAMEN[ziel]))
    .catch(() => hinweis("Ton-Umschaltung fehlgeschlagen"));
}

document.addEventListener("keydown", (event) => {
  if (event.ctrlKey || event.metaKey) return;
  if (event.altKey) {
    /* EXIT der Fernbedienung (kurz) = Alt+F4: im Spiel nur das Spiel schließen */
    if (event.key === "F4") { event.preventDefault(); if (zustand.overlay) schliesseOverlay(); }
    return;
  }
  /* 4.1: „Zurück“ einer Tastatur ist wie STOP (sonst ginge Chromium im Verlauf zurück) */
  const taste = event.key === "BrowserBack" ? "Escape" : event.key;
  if (taste !== event.key || /^(BrowserHome|BrowserSearch|ContextMenu)$/.test(taste)) event.preventDefault();
  eingabeMelden(taste);
  zustand.letzteTaste = Date.now();
  if (zustand.nachtSchwarz) { event.preventDefault(); zustand.nachtSchwarz.remove(); zustand.nachtSchwarz = null; ladeKacheln(); return; }
  if (zustand.meldungen && (taste === "Enter" || taste === " " || taste === "Escape" || taste === "Backspace")) {
    event.preventDefault(); meldungenBestaetigen(); return;
  }
  if (zustand.schoner) { event.preventDefault(); schonerAus(); return; }
  if (taste === "F13") { event.preventDefault(); return tonAusgang("hdmi"); }
  if (taste === "F14") { event.preventDefault(); return tonAusgang("klinke"); }
  /* Enter/Leertaste: kein natives Auslösen der fokussierten Kachel (sonst öffnet sie ein zweites Mal) */
  if (taste === "F7" || taste === "Tab" || taste.startsWith("Arrow") || taste === " " || taste === "Enter" ||
      taste === "Backspace" || /^[0-9]$/.test(taste) || /^F(9|1[0-2])$/.test(taste)) event.preventDefault();
  if (zustand.gesperrt && !(zustand.overlay && zustand.overlay.id === "eltern")) return;

  if (zustand.overlay) {
    if (zustand.overlay.taste(taste)) return;
    if (taste === "Escape" || taste === "Backspace") schliesseOverlay();
    return;
  }
  switch (taste) {
    case "ArrowLeft": return bewege(-1, 0);
    case "ArrowRight": return bewege(1, 0);
    case "ArrowUp": return bewege(0, -1);
    case "ArrowDown": return bewege(0, 1);
    case "Enter": case " ": {
      const k = zustand.reihen[zustand.zeile][zustand.spalte];
      return k && oeffne(k.daten);
    }
    case "Home": return markiere(0, 0);
    case "F21": {                                     /* 4.1: Suche-Taste der Tastatur = Nachrichten */
      const k = zustand.reihen.flat().find((x) => x.daten?.id === "spiel-nachrichten");
      return k && oeffne(k.daten);
    }
    default:
      if (/^[0-9]$/.test(taste)) {                     /* 3.5: Ziffern gelten in der gewählten Reihe */
        const reihe = zustand.reihen[zustand.zeile] || [];
        const i = reihe.findIndex((k) => k.taste === taste);
        if (i >= 0) { markiere(zustand.zeile, i); return oeffne(reihe[i].daten); }
      }
  }
}, true);

/* ------------------------------------------------------------ Status (alle 2 s) */
function zeigeRestzeit(rest) {
  const box = document.getElementById("restzeit");
  if (rest === null || rest === undefined) { box.hidden = true; return; }
  box.hidden = false;
  box.textContent = rest <= 0 ? "Spielzeit für heute vorbei" : `Noch ${rest} ${rest === 1 ? "Minute" : "Minuten"}`;
  box.className = rest <= 0 ? "aus" : rest <= 10 ? "knapp" : "";
}

/* 5.0: Wetter oben rechts (alle 5 Minuten; der Server fragt Open-Meteo höchstens alle 30 Minuten) */
async function wetterKopf() {
  const box = document.getElementById("wetter-kopf");
  let w;
  try { w = await hole("/api/wetter"); } catch (_) { return; }
  const d = w.aktiv && w.kopf ? w.daten : null;
  box.hidden = !d;
  if (!d) return;
  box.replaceChildren(el("span", { text: d.symbol }), el("span", { class: "wk-temp", text: `${d.temp}°` }),
    el("span", { class: "wk-satz" + (d.regen.nass || d.regen.ab ? " nass" : ""), text: "· " + d.regen.text }));
}

async function statusAbfrage() {
  let s;
  try { s = await hole("/api/status"); } catch (_) { return; }
  document.getElementById("version").textContent = "FERNSEHFRANZI · V" + s.version;
  if (s.untertitel) document.getElementById("untertitel").textContent = s.untertitel;
  gruessen(s.name);
  zeigeRestzeit(s.rest_min);

  if (zustand.meldungNr !== null && s.meldung.nr !== zustand.meldungNr && s.meldung.text) hinweis(s.meldung.text, 6000);
  zustand.meldungNr = s.meldung.nr;
  if (zustand.tonNr !== null && s.ton_nummer !== zustand.tonNr && s.ton && Date.now() - tonZeit > 3000) {
    hinweis("Ton: " + (TON_NAMEN[s.ton] || s.ton));
  }
  zustand.tonNr = s.ton_nummer;

  /* RetroPie: Startmarke wechselt = lief seit der Anforderung (auch wenn wir es nicht gesehen haben) */
  zustand.letzteMarke = s.retropie_start;
  const warDa = zustand.retropie || (zustand.retropieAngefordert && s.retropie_start !== zustand.retropieMarke);
  if (s.running) zustand.retropie = true;
  else if (warDa) {
    zustand.retropie = false;
    zustand.retropieAngefordert = 0;
    hinweis("Willkommen zurück!");
    ladeKacheln();
  } else if (zustand.retropieAngefordert && Date.now() - zustand.retropieAngefordert > 30000) {
    zustand.retropieAngefordert = 0;
    hinweis("RetroPie ist nicht gestartet. Bitte Mama oder Papa holen.");
  }

  if (s.pause_rest > 0 && !zustand.pauseLaeuft) bewegungspause(Math.min(900, s.pause_rest));   /* 4.2.1: ohne Neuladen */

  zustand.still = Boolean(s.still);
  zeigeMeldungen(s.meldungen || []);
  /* 3.5: Glocke oben mit Zahl der neuen Nachrichten (und auf der Kachel) */
  /* 4.4: Nachrichten von Freunden in der Sperrzeit zählen nur mit (lesen erst danach) */
  const anzahl = (s.meldungen || []).length + (s.freunde_spaeter || 0);
  const glocke = document.getElementById("glocke");
  glocke.hidden = !anzahl;
  glocke.textContent = `🔔 ${anzahl}`;
  document.querySelector('.kachel[data-id="spiel-nachrichten"]')?.classList.toggle("hat-neue", anzahl > 0);
  if (s.wecker && zustand.overlay?.id !== "wecker-klingelt") weckerKlingelt(s.wecker);

  const sperre = document.getElementById("sperre");
  zustand.gesperrt = s.gesperrt;
  sperre.hidden = !s.gesperrt || (zustand.overlay && zustand.overlay.id === "eltern");
  if (s.gesperrt) document.getElementById("sperre-text").textContent = s.gesperrt.text;
}

/* ------------------------------------------------------------ Bildschirmschoner (3.1): eigene Zeichnungen */
/* 4.4: oder die im Fotoalbum ausgesuchten Bilder, wenn das Kind „Bildschirmschoner“ eingeschaltet hat */
const SCHONER_NACH_MS = 5 * 60 * 1000;
function auswahlUrl(id) {
  const [art, ...rest] = id.split(":"), wert = rest.join(":");
  if (art === "ordner") return "/api/fotoalbum/bild?pfad=" + encodeURIComponent(wert);
  return (art === "album" ? "/album/" : "/zeichnung/") + encodeURIComponent(wert);
}
async function schonerPruefen() {
  if (zustand.schoner || zustand.overlay || Date.now() - zustand.letzteTaste < SCHONER_NACH_MS) return;
  let bilder = [];
  try {
    const fa = await hole("/api/fotoalbum").catch(() => null);
    if (fa?.erlaubt && fa.bildschirmschoner && fa.auswahl.length) bilder = fa.auswahl.map((id) => ({ url: auswahlUrl(id) }));
    else bilder = (await hole("/api/zeichnungen")).zeichnungen;
  } catch (_) { return; }
  const box = el("div", { id: "schoner" });
  const bild = el("img", { alt: "" });
  box.append(bild, el("div", { class: "schoner-uhr" }));
  document.body.append(box);
  let i = 0;
  const weiter = () => {
    box.querySelector(".schoner-uhr").textContent = new Date().toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
    if (bilder.length) { bild.src = bilder[i % bilder.length].url; i++; } else bild.hidden = true;
  };
  weiter();
  zustand.schoner = { box, timer: setInterval(weiter, 8000) };
}

function schonerAus() {
  clearInterval(zustand.schoner.timer);
  zustand.schoner.box.remove();
  zustand.schoner = null;
}

/* ------------------------------------------------------------ Bewegungspause (3.1) */
/* 4.2.1: Die Pause legt sich ÜBER das, was gerade offen ist (YouTube, Video, Hörbuch, Spiel), und hält nur an. Danach
   geht es an derselben Stelle weiter. Vorher wurde die Startseite neu geladen und der Film begann von vorn. */
function medienAnhalten(offen) {
  const liefen = [...document.querySelectorAll("video, audio")].filter((m) => !m.paused);
  liefen.forEach((m) => m.pause());
  try { offen?.anhalten?.(); } catch (_) { /* weiter */ }
  return () => {
    liefen.forEach((m) => m.play().catch(() => {}));
    try { offen?.fortsetzen?.(); } catch (_) { /* weiter */ }
  };
}

function bewegungspause(sekunden) {
  if (zustand.pauseLaeuft) return;
  zustand.pauseLaeuft = true;
  const vorher = zustand.overlay?.id === "pause" ? null : zustand.overlay;
  const weiter = medienAnhalten(vorher);
  const box = el("section", { class: "overlay pause-ebene", style: "align-items:center;justify-content:center;gap:4vh;text-align:center;z-index:50" });
  const zahl = el("div", { class: "witz", style: "font-size:clamp(70px,12vw,170px)" });
  const uebungen = ["Hampelmann! 🤸", "Auf einem Bein stehen 🦩", "Arme kreisen 🌀", "Hüpfen wie ein Frosch 🐸", "Strecken bis zur Decke 🙆"];
  const uebung = el("div", { class: "witz" });
  box.append(el("div", { class: "punkte", text: "Bewegungspause" }), uebung, zahl);
  if (vorher) box.append(el("div", { class: "hilfe", text: "Danach geht es genau hier weiter." }));
  document.getElementById("overlay-wurzel").append(box);     /* anhängen, nicht ersetzen: der Player bleibt, wie er ist */
  let rest = sekunden;
  const ende = () => {
    clearInterval(timer);
    box.remove();
    zustand.pauseLaeuft = false;
    zustand.overlay = vorher;
    weiter();
    hinweis(vorher ? "Super gemacht! Weiter geht's 🎉" : "Super gemacht! 🎉");
    ton("sieg");
  };
  const tick = () => {
    zahl.textContent = `${Math.floor(rest / 60)}:${String(rest % 60).padStart(2, "0")}`;
    uebung.textContent = uebungen[Math.floor((sekunden - rest) / 20) % uebungen.length];
    if (rest-- <= 0) ende();
  };
  const timer = setInterval(tick, 1000);
  tick();
  zustand.overlay = { id: "pause", taste: () => true,
                      /* wird die Pause von außen beendet (Elternbereich, Zur Startseite), schließt das Darunter mit */
                      schliesse: () => { clearInterval(timer); zustand.pauseLaeuft = false;
                                         try { vorher?.schliesse?.(); } catch (_) { /* weiter */ } } };
}

/* ------------------------------------------------------------ Los */
function hashPruefen() {
  if (location.hash === "#eltern") oeffneEltern();
  const gn = location.hash.match(/^#gute-nacht(-auto)?$/);
  if (gn) { history.replaceState(null, "", location.pathname); guteNachtOeffnen(Boolean(gn[1])); }
  if (location.hash === "#nacht") { history.replaceState(null, "", location.pathname); nachtFrage(); }
  const sonne = location.hash.match(/^#sonne-(\d+)$/);
  if (sonne) { history.replaceState(null, "", location.pathname); sonnenaufgang(Math.min(60, Math.max(1, +sonne[1]))); }
  if (location.hash === "#wecker") { history.replaceState(null, "", location.pathname); statusAbfrage(); }   /* Status bringt den Wecker */
  if (location.hash === "#zurueck") { history.replaceState(null, "", location.pathname); hinweis("Willkommen zurück!"); }   /* 4.1: nach dem Retro-Spiel */
  const pause = location.hash.match(/^#pause-(\d+)$/);
  if (pause) { history.replaceState(null, "", location.pathname); bewegungspause(Math.min(900, +pause[1])); }
}

async function start() {
  uhrStellen();
  setInterval(uhrStellen, 10000);
  gruessen("");
  while (!(await ladeKacheln())) await pause(2000);
  await statusAbfrage();
  setInterval(() => { if (!document.hidden) statusAbfrage(); }, 2000);
  setInterval(() => { if (!document.hidden && !zustand.overlay) ladeKacheln(); }, 60000);
  wetterKopf();
  setInterval(() => { if (!document.hidden) wetterKopf(); }, 5 * 60 * 1000);
  window.addEventListener("hashchange", hashPruefen);
  hashPruefen();
  setInterval(schonerPruefen, 30000);
}

window.FernsehFranzi = { zustand, ladeKacheln, oeffneEltern };   // für Tests und Fehlersuche
start();
