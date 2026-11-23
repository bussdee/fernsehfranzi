/* FernsehFranzi 3.0 - Startseite.
 *
 * Kacheln kommen vom Server (/api/apps: App-Katalog + Spielzimmer, mit Sperrgrund aus dem
 * Zeitkonto). Eingabe: Tastatur-Ereignisse - Fernbedienung und Controller übersetzt
 * eingabe.py in Tasten, die Startseite liest keine Gamepads selbst (ein Besitzer pro Aufgabe).
 */
import { hole, sende, el, pause, bild, mitBild, franzi } from "./gemeinsam.js";
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
                 "spiel-gutschein": "#c2453a", "spiel-wecker": "#d0782a", "spiel-nachrichten": "#c99a1e", "spiel-gestalten": "#8a4fc2",
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
/* 6.0: Startseite „Zuhause + Ordner“ - auf „Zuhause“ die Lieblinge, „Weiter, wo du warst“ und je eine Kachel pro Bereich;
   OK auf einen Bereich öffnet sein Raster, STOP geht zurück. Freie Kacheln zuerst, gesperrte am Ende mit Grund. */
const SPERR_SYMBOL = { zeit: "⏳", nacht: "🌙", schule: "🏫", sperrzeit: "🚫", eltern: "🔒", uhr: "🕐" };
const SPERR_KURZ = { zeit: "Zeit um", nacht: "Nachtruhe", schule: "Schulzeit", sperrzeit: "Sperrzeit", eltern: "gesperrt", uhr: "gleich" };
function baueKachel(app, nummer) {
  const istSpiel = app.typ === "spiel";
  const farbe = app.farbe || FARBEN[app.id] || "#2a3550";
  const symbol = app.ordnerSymbol || SYMBOLE[app.symbol] || (istSpiel && SPIELE[app.id]?.symbol) || "⭐";
  const knoten = el("button", { class: "kachel" + (app.frei === false ? " gesperrt" : "") + (app.ordner ? " ordner-kachel" : ""),
                                type: "button", tabindex: "-1", "data-id": app.ordner ? "ordner-" + app.ordner : app.id },
    el("div", { class: "bg", style: `--farbe: ${farbe}; background: linear-gradient(130deg, var(--kachel-anfang), ${farbe})` }),
    nummer ? el("span", { class: "taste", text: nummer }) : null,
    el("div", { class: "symbol" }, bild(symbol)),
    el("div", { class: "unten" },
      el("div", { class: "name", text: app.name }),
      app.zusatz ? el("div", { class: "zusatz", text: app.zusatz }) : null));
  const symbolSperre = app.frei === false ? (SPERR_SYMBOL[app.sperre] || "🔒") : app.eingerichtet === false ? "⚙️" : "";
  if (symbolSperre) {
    knoten.classList.add("gesperrt");
    knoten.append(el("div", { class: "sperr-symbol", text: symbolSperre }),
      el("div", { class: "grund", text: app.frei === false ? (SPERR_KURZ[app.sperre] || "geht gerade nicht") : "nicht eingerichtet" }));
  }
  if (app.hinweis) knoten.append(el("div", { class: "kachel-hinweis", text: app.hinweis }));
  knoten.addEventListener("click", () => (app.ordner ? oeffneOrdner(app.ordner) : oeffne(app)));
  return knoten;
}

/* Bereiche („Ordner“). Eltern können eine App einem Bereich zuordnen (Feld "bereich", auch alte Namen), sonst automatisch. */
const BEREICHE = [
  { id: "spiele", name: "Spiele", symbol: "🎮", farbe: "#2f8a5e" },
  { id: "filme", name: "Filme", symbol: "🎬", farbe: "#b0442f" },
  { id: "musik", name: "Musik", symbol: "🎵", farbe: "#a8326b" },
  { id: "lernen", name: "Lernen", symbol: "🎓", farbe: "#2f6db5" },
  { id: "zimmer", name: "Mein Zimmer", symbol: "📨", farbe: "#8a4fc2" },
  { id: "retro", name: "Retro", symbol: "🕹️", farbe: "#5a3d8a" },
];
const BEREICH_ALT = { start: "zimmer", medien: "filme" };
const ZIMMER_IDS = ["spiel-nachrichten", "spiel-wecker", "spiel-gutschein", "familie", "spiel-gestalten", "spiel-fotoalbum",
                    "spiel-sticker", "spiel-wetter", "spiel-news"];
function bereichVon(app) {
  const eigen = BEREICH_ALT[app.bereich] || app.bereich;
  if (eigen && BEREICHE.some((b) => b.id === eigen)) return eigen;
  if (ZIMMER_IDS.includes(app.id)) return "zimmer";
  if (app.typ === "hoerbuch" || app.id === "spiel-bass" || app.id === "spiel-karaoke") return "musik";   /* 6.0: getrennt */
  if (app.typ === "youtube" || app.typ === "video" || app.id === "plex") return "filme";
  if (app.typ === "konsole" || app.typ === "retro") return "retro";
  if (app.lernen || app.id === "buecher" || app.id === "spiel-schule") return "lernen";
  if (app.typ === "spiel") return "spiele";
  return "zimmer";
}
const BESCHREIBUNG = { "gute-nacht": "Hörbuch zum Einschlafen", "spiel-wecker": "Deine Wecker", "spiel-gutschein": "Code vom Zettel einlösen",
                       "spiel-bass": "Bass, Gitarre, Keyboard, Singen", youtube: "Deine Videos", games: "Alle Retro-Spiele",
                       "spiel-wetter": "Wann kann ich raus?", "spiel-schule": "Stundenplan und Hausaufgaben",
                       "spiel-kinderwelten": "Geschichten lesen, Rätsel, Draußen-Spiele", "spiel-news": "Nachrichten für Kinder",
                       "spiel-gestalten": "Lieblinge und Farben aussuchen", "spiel-fotoalbum": "Deine Bilder und die Diashow" };
const LIEBLINGE_MAX = 6, ZULETZT_MAX = 4, SPALTEN = 6;
const freiZuerst = (liste) => liste.filter((a) => a.frei !== false && a.eingerichtet !== false)
  .concat(liste.filter((a) => a.frei === false || a.eingerichtet === false));

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
  let gestaltung = { lieblinge: [], thema: "blau", zuletzt: [] };
  try { gestaltung = await hole("/api/startseite"); } catch (_) { /* Vorgabe */ }
  designZeigen(gestaltung.design?.jetzt || gestaltung.thema, gestaltung.design?.hell);   /* 6.0: Farbe (abends dunkel) */
  zustand.alle = alle;
  zustand.gestaltung = gestaltung;
  const vorherId = zustand.reihen[zustand.zeile]?.[zustand.spalte]?.knoten?.dataset.id;
  baueSeite(vorherId);
  return true;
}

/* Eine Seite zeichnen: „Zuhause“ (zustand.ordner = null) oder das Raster eines Bereichs */
function baueSeite(fokusId) {
  const alle = zustand.alle || [], st = zustand.gestaltung || {};
  const reihenBox = document.getElementById("reihen");
  reihenBox.replaceChildren();
  reihenBox.style.transform = "none";
  /* 6.0: Kacheln gleiten nur beim Wechsel der Seite herein, nicht beim stillen Nachladen jede Minute */
  const seite = zustand.ordner || "zuhause", neueSeite = zustand.gezeigteSeite !== seite;
  zustand.gezeigteSeite = seite;
  reihenBox.classList.toggle("rein", neueSeite);
  let nr = 0;
  zustand.reihen = [];
  const neueReihe = (titel, eintraege, art) => {
    if (!eintraege.length) return;
    const zeile = el("div", { class: "zeile-kacheln" + (art ? " " + art : "") });
    const reihe = [];
    eintraege.forEach((app, i) => {
      const taste = i < 9 ? String(i + 1) : "";
      const knoten = baueKachel(app, taste);
      knoten.style.setProperty("--i", String(Math.min(nr++, 14)));
      zeile.append(knoten);
      reihe.push({ daten: app, knoten, taste });
    });
    const abschnitt = el("section", { class: "zeile", "data-art": art || "" }, titel ? el("h2", { class: "reihe-titel", text: titel }) : null, zeile);
    reihenBox.append(abschnitt);
    reihe.abschnitt = abschnitt;
    zustand.reihen.push(reihe);
  };
  const pfad = document.getElementById("pfad");
  document.getElementById("reihen-fenster").classList.toggle("im-ordner", Boolean(zustand.ordner));
  if (!zustand.ordner) {
    pfad.textContent = "";
    const lieb = (st.lieblinge || []).map((id) => alle.find((a) => a.id === id)).filter(Boolean).slice(0, LIEBLINGE_MAX);
    neueReihe("⭐ Meine Lieblinge", lieb.length ? lieb : [{ id: "spiel-gestalten-hinweis", name: "Lieblinge aussuchen", ordnerSymbol: "⭐",
      zusatz: "unter Gestalten", farbe: "#a8791c", frei: true, verweis: "spiel-gestalten" }], "lieblinge");
    const zuletzt = (st.zuletzt || []).map((id) => alle.find((a) => a.id === id)).filter((a) => a && a.frei !== false)
      .filter((a) => !lieb.includes(a)).slice(0, ZULETZT_MAX);
    neueReihe("▶ Weiter, wo du warst", zuletzt, "zuletzt");
    const neu = (zustand.meldungenAnzahl || 0);
    neueReihe("Bereiche", BEREICHE.map((b) => {
      const drin = alle.filter((a) => bereichVon(a) === b.id);
      if (!drin.length) return null;
      const frei = drin.filter((a) => a.frei !== false).length;
      return { id: "ordner-" + b.id, ordner: b.id, name: b.name, ordnerSymbol: b.symbol, farbe: b.farbe, frei: true,
               zusatz: frei === drin.length ? "" : `${frei} von ${drin.length} frei`,
               hinweis: b.id === "zimmer" && neu ? `🔔 ${neu} neu` : "" };
    }).filter(Boolean), "bereiche");
  } else {
    const b = BEREICHE.find((x) => x.id === zustand.ordner);
    pfad.textContent = `🏠 Zuhause  ›  ${b.symbol} ${b.name}`;
    const drin = freiZuerst(alle.filter((a) => bereichVon(a) === b.id));
    for (let i = 0; i < drin.length; i += SPALTEN) neueReihe("", drin.slice(i, i + SPALTEN), "raster");
    if (!drin.length) reihenBox.append(el("div", { class: "seite-leer" }, franzi("staunen", "franzi-leer"), el("div", { text: "Hier ist gerade nichts." })));
  }
  /* Fokus: dieselbe Kachel wie vorher, sonst die erste */
  let z = 0, s = 0;
  if (fokusId) zustand.reihen.forEach((r, ri) => r.forEach((k, ki) => { if (k.knoten.dataset.id === fokusId) { z = ri; s = ki; } }));
  if (zustand.reihen.length) markiere(z, s);
  else { document.getElementById("held-name").textContent = ""; document.getElementById("held-info").textContent = ""; }
}

function oeffneOrdner(id) {
  zustand.ordner = id;
  baueSeite();
  ton("ok");
}
function zuhause() {
  const war = zustand.ordner;
  zustand.ordner = null;
  baueSeite(war ? "ordner-" + war : null);
  ton("bewegen");
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
  /* senkrecht nur so weit schieben, dass die gewählte Reihe ganz zu sehen ist */
  const fenster = document.getElementById("reihen-fenster"), box = document.getElementById("reihen");
  let versatz = Number(box.dataset.versatz || 0);
  const oben = reihe.abschnitt.offsetTop, unten = oben + reihe.abschnitt.offsetHeight, sicht = fenster.clientHeight;
  if (oben - versatz < 0) versatz = Math.max(0, oben - 8);
  if (unten - versatz > sicht) versatz = unten - sicht + 8;
  box.dataset.versatz = String(versatz);
  box.style.transform = `translateY(${-versatz}px)`;
  /* Info-Zeile unten: Name und ein Satz (bei gesperrten Kacheln der Grund) */
  const d = k.daten;
  document.getElementById("held-name").textContent = d.name;
  document.getElementById("held-info").textContent = d.ordner ? "OK öffnet den Bereich" : d.verweis ? "Unter „Gestalten“ suchst du dir bis zu 6 Lieblinge aus"
    : d.frei === false ? d.grund : d.eingerichtet === false ? "Noch nicht eingerichtet"
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
    const ziel = zustand.zeile + dy;
    if (ziel < 0 || ziel >= zustand.reihen.length) return anschlag(0, dy);
    /* dieselbe Spalte (vorhersehbar), höchstens bis zur letzten Kachel der Zielreihe */
    markiere(ziel, Math.min(zustand.spalte, zustand.reihen[ziel].length - 1));
  } else {
    let z = zustand.zeile, s = zustand.spalte + dx;
    /* im Raster am Zeilenende in die nächste Zeile weiter */
    if (zustand.ordner && s >= zustand.reihen[z].length && z + 1 < zustand.reihen.length) { z++; s = 0; }
    else if (zustand.ordner && s < 0 && z > 0) { z--; s = zustand.reihen[z].length - 1; }
    if (s < 0 || s >= zustand.reihen[z].length) return anschlag(dx, 0);
    markiere(z, s);
  }
  ton("bewegen");
}

/* Für Tests und Fehlersuche: zur Kachel einer App springen (öffnet ihren Bereich) und sie wählen */
function zeigeKachel(id) {
  const app = (zustand.alle || []).find((a) => a.id === id);
  if (!app) return false;
  const imZuhause = !zustand.ordner && zustand.reihen.some((r) => r.some((k) => k.knoten.dataset.id === id));
  if (!imZuhause) { zustand.ordner = bereichVon(app); baueSeite(id); }
  zustand.reihen.forEach((r, ri) => r.forEach((k, ki) => { if (k.knoten.dataset.id === id) markiere(ri, ki); }));
  return true;
}

/* ------------------------------------------------------------ Öffnen */
async function oeffne(app) {
  if (app.ordner) return oeffneOrdner(app.ordner);                                  /* 6.0: Bereich öffnen */
  if (app.verweis) { const ziel = (zustand.alle || []).find((a) => a.id === app.verweis); return ziel && oeffne(ziel); }
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
  const steuerung = spiel.oeffne(box, { hinweis, sende, hole, schliessen: schliesseOverlay,
                                       diashow: () => { schliesseOverlay(); schonerPruefen(true); } });   /* 6.0 */
  zustand.overlay = { ...steuerung, id: app.id };
  /* 6.0: jede Überschrift mit dem Symbol des Spiels (einheitlich) */
  const titel = box.querySelector(".overlay-kopf h2");
  if (titel && spiel.symbol && !titel.querySelector(".icon") && !/^\p{Extended_Pictographic}/u.test(titel.textContent))
    titel.replaceChildren(...mitBild(`${spiel.symbol} ${titel.textContent}`, "icon kopf-icon"));
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
      el("div", { class: "meldungen-symbol" }, bild(liste.every((m) => m.symbol && m.symbol === liste[0].symbol) ? liste[0].symbol : "📣")),
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
  if (zustand.wartung) { event.preventDefault(); event.stopPropagation(); return; }   /* 5.3: Wartung - keine Taste wirkt */
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
    case "Home": return zustand.ordner ? zuhause() : markiere(0, 0);
    case "Escape": case "Backspace": return zustand.ordner ? zuhause() : undefined;   /* 6.0: STOP = eine Ebene zurück */
    case "F21": {                                     /* 4.1: Suche-Taste der Tastatur = Nachrichten */
      const app = (zustand.alle || []).find((a) => a.id === "spiel-nachrichten");
      return app && oeffne(app);
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
function zeigeRestzeit(rest, budget) {
  const box = document.getElementById("restzeit");
  if (rest === null || rest === undefined) { box.hidden = true; return; }
  box.hidden = false;
  box.replaceChildren(el("span", { text: rest <= 0 ? "Spielzeit für heute vorbei" : `Noch ${rest} ${rest === 1 ? "Minute" : "Minuten"}` }),
    el("span", { class: "balken" }, el("span", { style: `width: ${budget ? Math.max(0, Math.min(100, Math.round((100 * rest) / budget))) : 100}%` })));
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
  box.replaceChildren(bild(d.symbol, "icon wk-icon"), el("span", { class: "wk-temp", text: `${d.temp}°` }),
    el("span", { class: "wk-satz" + (d.regen.nass || d.regen.ab ? " nass" : ""), text: "· " + d.regen.text }));
}

async function statusAbfrage() {
  let s;
  try { s = await hole("/api/status"); } catch (_) { return; }
  document.getElementById("version").textContent = "FERNSEHFRANZI · V" + s.version;
  if (s.untertitel) document.getElementById("untertitel").textContent = s.untertitel;
  gruessen(s.name);
  zeigeRestzeit(s.rest_min, s.budget_min);

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
  if (anzahl !== (zustand.meldungenAnzahl || 0)) {          /* 6.0: „🔔 2 neu“ auf der Kachel „Mein Zimmer“ */
    zustand.meldungenAnzahl = anzahl;
    const z = document.querySelector('.kachel[data-id="ordner-zimmer"]');
    if (z) { z.querySelector(".kachel-hinweis")?.remove(); if (anzahl) z.append(el("div", { class: "kachel-hinweis", text: `🔔 ${anzahl} neu` })); }
  }
  const glocke = document.getElementById("glocke");
  glocke.hidden = !anzahl;
  glocke.textContent = `🔔 ${anzahl}`;
  document.querySelector('.kachel[data-id="spiel-nachrichten"]')?.classList.toggle("hat-neue", anzahl > 0);
  if (s.wecker && zustand.overlay?.id !== "wecker-klingelt") weckerKlingelt(s.wecker);

  /* 5.3: Wartungsmodus (Ausliefern läuft) - Warnbildschirm über allem, offene Spiele und Player schließen */
  const warAn = Boolean(zustand.wartung);
  vorwarnung(s.wartung?.vorwarnung_s);
  zustand.wartung = s.wartung?.rest_s ? s.wartung : null;
  document.getElementById("wartung").hidden = !zustand.wartung;
  if (zustand.wartung && !warAn) { if (zustand.overlay) schliesseOverlay(); if (zustand.schoner) schonerAus(); }
  if (!zustand.wartung && warAn) { hinweis("Fertig – weiter geht's! 🎉"); ladeKacheln(); }

  const sperre = document.getElementById("sperre");
  zustand.gesperrt = s.gesperrt;
  sperre.hidden = !s.gesperrt || (zustand.overlay && zustand.overlay.id === "eltern");
  if (s.gesperrt) document.getElementById("sperre-text").textContent = s.gesperrt.text;
  auszeitZeigen(s.gesperrt);
}

/* 5.3: Vorwarnung - Countdown oben rechts (über Spielen und Playern), zählt jede Sekunde selbst weiter */
let vorwarnEnde = 0, vorwarnTimer = 0;
function vorwarnung(sekunden) {
  const box = document.getElementById("wartung-bald");
  if (!sekunden) { box.hidden = true; clearInterval(vorwarnTimer); vorwarnTimer = 0; return; }
  if (!vorwarnTimer) ton("fehler");
  vorwarnEnde = Date.now() + sekunden * 1000;
  box.hidden = false;
  const zeichne = () => {
    const rest = Math.max(0, Math.ceil((vorwarnEnde - Date.now()) / 1000));
    document.getElementById("wartung-bald-zahl").textContent = String(rest);
  };
  zeichne();
  if (!vorwarnTimer) vorwarnTimer = setInterval(zeichne, 250);
}

/* 5.1: Auszeit - alles gesperrt, groß nur der Countdown (läuft jede Sekunde, der Status bringt alle 2 s den genauen Rest) */
let auszeitEnde = 0, auszeitTimer = 0;
function auszeitZeigen(g) {
  const uhr = document.getElementById("sperre-uhr");
  const auszeit = Boolean(g && g.auszeit && typeof g.rest_s === "number");
  document.getElementById("sperre").classList.toggle("auszeit", auszeit);
  const sym = document.getElementById("sperre-symbol"), soll = auszeit ? "⏳" : "franzi";
  if (sym.dataset.bild !== soll) {                                                              /* nicht alle 2 s neu */
    sym.dataset.bild = soll;
    sym.replaceChildren(auszeit ? bild(soll) : franzi("schlaf", "franzi-sperre"));
  }
  document.getElementById("sperre-klein").textContent = auszeit
    ? `Bis ${g.bis_uhr} Uhr · Mama oder Papa können sie früher beenden.` : "Mama oder Papa können ihn wieder freigeben.";
  uhr.hidden = !auszeit;
  if (!auszeit) { clearInterval(auszeitTimer); auszeitTimer = 0; return; }
  auszeitEnde = Date.now() + g.rest_s * 1000;
  const zeichne = () => {
    const rest = Math.max(0, Math.round((auszeitEnde - Date.now()) / 1000));
    const h = Math.floor(rest / 3600), m = Math.floor((rest % 3600) / 60), sek = rest % 60;
    uhr.textContent = (h ? `${h}:${String(m).padStart(2, "0")}` : String(m)) + ":" + String(sek).padStart(2, "0");
  };
  zeichne();
  if (!auszeitTimer) auszeitTimer = setInterval(zeichne, 1000);
}

/* ------------------------------------------------------------ Bildschirmschoner (3.1): eigene Zeichnungen */
/* 4.4: oder die im Fotoalbum ausgesuchten Bilder, wenn das Kind „Bildschirmschoner“ eingeschaltet hat */
const SCHONER_NACH_MS = 5 * 60 * 1000;
function auswahlUrl(id) {
  const [art, ...rest] = id.split(":"), wert = rest.join(":");
  if (art === "ordner") return "/api/fotoalbum/bild?pfad=" + encodeURIComponent(wert);
  return (art === "album" ? "/album/" : "/zeichnung/") + encodeURIComponent(wert);
}
async function schonerPruefen(sofort = false) {
  if (zustand.schoner || zustand.overlay || zustand.gesperrt?.auszeit || zustand.wartung) return;
  if (!sofort && Date.now() - zustand.letzteTaste < SCHONER_NACH_MS) return;
  let bilder = [];
  try {
    const fa = await hole("/api/fotoalbum").catch(() => null);
    if (fa?.erlaubt && (fa.bildschirmschoner || sofort) && fa.auswahl.length) bilder = fa.auswahl.map((id) => ({ url: auswahlUrl(id) }));
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
  /* 6.0: feste Symbole der Seite als 3D-Bilder */
  document.querySelectorAll("#wartung .gross, #sperre .gross").forEach((g) => g.replaceChildren(bild(g.textContent.trim())));
  document.getElementById("franzi-kopf").replaceChildren(franzi("froh"));     /* 6.0: Maskottchen winkt zur Begrüßung */
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

window.FernsehFranzi = { zustand, ladeKacheln, oeffneEltern, zeige: zeigeKachel, zuhause };   // für Tests und Fehlersuche
start();
