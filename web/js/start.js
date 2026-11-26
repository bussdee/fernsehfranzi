/* FernsehFranzi 3.0 - Startseite.
 *
 * Kacheln kommen vom Server (/api/apps: App-Katalog + Spielzimmer, mit Sperrgrund aus dem
 * Zeitkonto). Eingabe: Tastatur-Ereignisse - Fernbedienung und Controller übersetzt
 * eingabe.py in Tasten, die Startseite liest keine Gamepads selbst (ein Besitzer pro Aufgabe).
 */
import { hole, sende, el, pause, bild, mitBild, franzi, setzeFranzi, kleidungZuSachen, BEREICHE, bereichVon } from "./gemeinsam.js";
import { oeffneElternbereich } from "./eltern.js";
import { oeffneHoerbuch } from "./hoerbuch.js";
import { oeffneMusik } from "./musik.js";
import { starte as sternenhimmel } from "./sternenhimmel.js";
import { starte as weckklang } from "./weckklang.js";
import { oeffneYoutube } from "./youtube.js";
import { oeffneVideo } from "./video.js";
import { ton, setzeKlaenge } from "./spiele/kern.js";
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
import meintag from "./spiele/meintag.js";
import stimmspiele from "./spiele/stimmspiele.js";
import steine from "./spiele/steine.js";
import labyrinth from "./spiele/labyrinth.js";
import huepfen from "./spiele/huepfen.js";
import hilfe from "./spiele/hilfe.js";
import franziHaus from "./spiele/franzi.js";

const SPIELE = { "spiel-snake": snake, "spiel-memory": memory, "spiel-drei": drei,
                 "spiel-echo": echo, "spiel-malen": malen, "spiel-witz": witz, "spiel-bass": bass,
                 "spiel-duell": duell, "spiel-sticker": sticker, "spiel-lernen": lernen, "spiel-gutschein": gutschein, "spiel-wecker": wecker,
                 "spiel-nachrichten": nachrichten, "spiel-gestalten": gestalten, "spiel-handys": handys, "spiel-fotoalbum": fotoalbum, "spiel-karaoke": karaoke,
                 "spiel-wetter": wetter, "spiel-schule": schule, "spiel-kinderwelten": kinderwelten, "spiel-news": news,
                 "spiel-meintag": meintag, "spiel-stimme": stimmspiele,
                 "spiel-steine": steine, "spiel-labyrinth": labyrinth, "spiel-huepfen": huepfen,
                 "spiel-hilfe": hilfe, "spiel-franzi": franziHaus };
const SYMBOLE = { video: "▶️", film: "🎬", spiel: "🕹️", haus: "🏠", buch: "📚", lernen: "🎓", musik: "🎵",
                  malen: "🎨", web: "🌐", stern: "⭐", mond: "🌙", tier: "🐾", ball: "⚽" };
const FARBEN = { "spiel-snake": "#1d7a5e", "spiel-memory": "#8a3b8a", "spiel-drei": "#a8791c",
                 "spiel-echo": "#2a6b9e", "spiel-malen": "#6d3fa8", "spiel-witz": "#b06520",
                 "spiel-bass": "#8d2f2f", "spiel-duell": "#2f6d8d", "spiel-sticker": "#8d7a2f", "spiel-lernen": "#00897b", "spiel-handys": "#2f5fa8", "spiel-fotoalbum": "#2f7a8d", "spiel-karaoke": "#a8326b",
                 "spiel-gutschein": "#c2453a", "spiel-wecker": "#d0782a", "spiel-nachrichten": "#c99a1e", "spiel-gestalten": "#8a4fc2",
                 "spiel-wetter": "#2f86c9", "spiel-schule": "#3a7d44", "spiel-kinderwelten": "#e07b1a", "spiel-news": "#6b4fb3", "spiel-meintag": "#e0a020", "spiel-stimme": "#2f8ab0", "spiel-steine": "#b0472f", "spiel-labyrinth": "#6b5a2f", "spiel-huepfen": "#3f9a4f", "spiel-hilfe": "#c62f3e", "spiel-franzi": "#ff7a59",
                 "archiv-video": "#b23a3a", "archiv-musik": "#a8326b",
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

/* Bereiche („Ordner“): 6.9.38 nach gemeinsam.js umgezogen (die Eltern-Seite gruppiert die Apps genauso) */
const BESCHREIBUNG = { "gute-nacht": "Hörbuch zum Einschlafen", "spiel-wecker": "Deine Wecker", "spiel-gutschein": "Code vom Zettel einlösen",
                       "spiel-bass": "Bass, Gitarre, Keyboard, Singen", youtube: "Deine Videos", games: "Alle Retro-Spiele",
                       "spiel-wetter": "Wann kann ich raus?", "spiel-schule": "Stundenplan und Hausaufgaben",
                       "spiel-kinderwelten": "Geschichten lesen, Rätsel, Draußen-Spiele", "spiel-news": "Nachrichten für Kinder", "spiel-meintag": "Deine Listen für heute", "spiel-franzi": "Dein Haustier – pflegen, spielen, Shop", "archiv-video": "Filme von Mama und Papa", "archiv-musik": "Deine Musik", "spiel-stimme": "Möwenflug und Drache – mit der Stimme",
                       "spiel-steine": "Bilder aus Steinen abräumen", "spiel-labyrinth": "Finde den Schatz in 3D", "spiel-huepfen": "Laufen, springen, Sterne sammeln",
                       "spiel-hilfe": "Mama und Papa sofort Bescheid sagen",
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
  document.documentElement.dataset.animation = gestaltung.design?.animation || "sparsam";   /* 6.8.12: aus/sparsam/hoch */
  setzeKlaenge(gestaltung.klang);                                   /* 6.9.40: Klang je Ereignis */
  zustand.bildschirm = gestaltung.bildschirm || { schoner_min: 5 };    /* 6.9.47: Franzi-Schoner nach X Minuten */
  /* 6.9.42: eigenes Hintergrundbild der Eltern für diese Farbe (sonst das gezeichnete Motiv aus start.css) */
  /* leicht abgedunkelt, damit Schrift und Kacheln auf jedem Foto lesbar bleiben (helle Farben etwas weniger) */
  if (gestaltung.design?.bild) document.body.style.setProperty("--motiv",
    `linear-gradient(rgba(0,0,0,${gestaltung.design.hell ? ".18" : ".38"}), rgba(0,0,0,${gestaltung.design.hell ? ".18" : ".38"})), url("${gestaltung.design.bild}")`);
  else document.body.style.removeProperty("--motiv");
  zustand.musik = gestaltung.klang?.musik || {};
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
    /* 6.9.52: Reihenfolge der Eltern je Bereich (Elternbereich → Apps, ↑↓); nicht Genannte danach wie bisher */
    const reihe = (st.reihenfolge || {})[b.id] || [];
    const rang = (a) => { const i = reihe.indexOf(a.id); return i < 0 ? 1e6 : i; };
    const drin = freiZuerst(alle.filter((a) => bereichVon(a) === b.id).map((a, i) => [a, i])
      .sort((x, y) => rang(x[0]) - rang(y[0]) || x[1] - y[1]).map(([a]) => a));
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
  if (app.id === "archiv-musik") return oeffneMusikSeite(app);                     /* 6.9.48: Musik-App statt Hörbuch-Player */
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

/* 6.9.48: Musik-Seite (Musik-Archiv) - ohne Schlaf-Timer, mit Alben, Lieblingsliedern, Zufall und Wiederholen */
async function oeffneMusikSeite(app) {
  if (zustand.overlay) schliesseOverlay();
  try { await sende("/api/start", { id: app.id }); } catch (fehler) { hinweis(fehler.message); ton("fehler"); return; }
  const box = el("section", { class: "overlay" });
  document.getElementById("overlay-wurzel").replaceChildren(box);
  zustand.overlay = { ...oeffneMusik(box, { hinweis, sende, hole }, app), id: app.id };
  ton("ok");
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
/* 6.9.21: Nachtszene hinter der Nachtruhe-Frage (fester Inhalt) - Sterne funkeln nur in der Stufe „hoch“ */
const NACHT_SZENE = '<svg viewBox="0 0 1600 900" preserveAspectRatio="xMidYMax slice" aria-hidden="true">' +
  '<defs><linearGradient id="nfh" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#050a1f"/><stop offset="1" stop-color="#1c2552"/></linearGradient></defs>' +
  '<rect width="1600" height="900" fill="url(#nfh)"/>' +
  Array.from({ length: 60 }, (_, i) => `<circle class="fzs-funkeln" style="animation-delay:${(i % 7) * 0.4}s" cx="${(i * 263) % 1600}" cy="${(i * 137) % 560}" r="${1 + (i % 3) * 0.6}" fill="#fff" opacity="${0.35 + (i % 4) * 0.15}"/>`).join("") +
  '<mask id="nfm"><rect width="1600" height="900" fill="#fff"/><circle cx="1326" cy="132" r="56" fill="#000"/></mask>' +
  '<circle cx="1300" cy="150" r="60" fill="#fff4cf" mask="url(#nfm)"/>' +
  '<path d="M0 700 C 300 600 600 640 900 690 S 1400 610 1600 660 V900 H0Z" fill="#141c3e"/>' +
  '<path d="M0 790 C 400 730 800 760 1200 780 S 1500 750 1600 770 V900 H0Z" fill="#0c1230"/>' +
  '<path d="M1330 676 h110 v-60 l-55 -44 l-55 44 Z" fill="#0c1230"/><rect x="1352" y="628" width="22" height="22" rx="3" fill="#ffd27a"/>' +
  '<rect x="1396" y="628" width="22" height="22" rx="3" fill="#ffd27a" opacity=".6"/></svg>';

function nachtFrage() {
  if (zustand.overlay) schliesseOverlay();
  const box = el("section", { class: "overlay nacht-frage" });
  const zahl = el("div", { class: "nacht-zahl" });
  const wahl = [["aus", "📴 Fernseher aus"], ["an", "📺 Fernseher an"], ["gute-nacht", "🌙 Gute Nacht"]];
  const knoepfe = wahl.map(([w, t]) => { const k = el("button", { class: "knopf", type: "button", tabindex: "-1", text: t });
    k.addEventListener("click", () => fertig(w)); return k; });
  const szene = el("div", { class: "nf-szene" });
  szene.innerHTML = NACHT_SZENE;                                          /* fester Inhalt aus diesem Modul */
  const ring = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  ring.setAttribute("viewBox", "0 0 100 100"); ring.setAttribute("class", "nf-ring");
  ring.innerHTML = '<circle cx="50" cy="50" r="44" class="nf-ring-grund"/><circle cx="50" cy="50" r="44" class="nf-ring-rest" pathLength="100" transform="rotate(-90 50 50)"/>';
  box.append(szene, el("div", { class: "nf-inhalt" }, franzi("schlaf", "nf-franzi"), el("h2", { text: "Jetzt ist Nachtruhe" }),
    el("div", { class: "nf-uhr" }, ring, zahl), el("div", { class: "knopfreihe" }, ...knoepfe)));
  document.getElementById("overlay-wurzel").replaceChildren(box);
  let i = 2, rest = 15;
  const zeige = () => knoepfe.forEach((k, n) => k.classList.toggle("gewaehlt", n === i));
  const takt = () => {
    zahl.textContent = String(rest);
    ring.querySelector(".nf-ring-rest").setAttribute("stroke-dasharray", `${(rest / 15 * 100).toFixed(1)} 100`);
    if (rest <= 0) return fertig("aus");
    if (!zustand.still) ton(rest <= 5 ? "glocke" : "leise");                 /* 6.9.21: sanft statt Spieltöne */
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
  nachtSchwarzWeg();
  if (zustand.schoner) schonerAus();
  const box = el("section", { class: "overlay wecker-klingelt" });
  const uhr = el("div", { class: "wecker-uhr" });
  /* 6.9.33: Morgenszene - Hügel unten, Sonne hinter einer jubelnden Franzi */
  const szene = el("div", { class: "wecker-szene" });
  szene.innerHTML = '<svg viewBox="0 0 1600 300" preserveAspectRatio="none" aria-hidden="true">' +
    '<path d="M0 150 C 250 60 450 80 700 140 S 1200 60 1600 120 V300 H0Z" fill="#7cc070"/>' +
    '<path d="M0 220 C 300 150 600 170 900 210 S 1400 150 1600 190 V300 H0Z" fill="#5aa85a"/></svg>';     /* fester Inhalt */
  box.append(szene, el("div", { class: "wecker-kopf" }, el("div", { class: "wecker-sonne" }), franzi("jubel", "wecker-franzi")), uhr, el("h2", { text: "Guten Morgen!" }),
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
   (das Zimmer wird langsam hell). Eine Taste beendet ihn; der Wecker klingelt trotzdem zur Weckzeit.
   6.1: als kleine Szene - Sterne verblassen, die Sonne steigt hinter Hügeln auf, Himmel und Hügel färben sich, am Ende
   ziehen Vögel vorbei. Alle 2 s neue Werte, dazwischen gleitet CSS (transform/opacity/Farben). */
const SONNE_HIMMEL = [   /* Anteil, Farbe oben, Farbe am Horizont */
  [0, [0, 0, 0], [5, 2, 8]], [0.25, [11, 8, 32], [60, 12, 8]], [0.5, [42, 26, 64], [168, 53, 12]],
  [0.75, [90, 122, 176], [240, 144, 58]], [1, [188, 216, 245], [255, 233, 200]]];
const SONNE_KUGEL = [[0, [255, 58, 16]], [0.5, [255, 120, 40]], [1, [255, 244, 208]]];
const SONNE_HUEGEL = [[0, [0, 0, 0]], [0.4, [20, 12, 14]], [1, [61, 107, 58]]];
function mische(liste, p, feld = 1) {
  let i = 0;
  while (i < liste.length - 2 && p > liste[i + 1][0]) i++;
  const a = liste[i], b = liste[i + 1], t = Math.min(1, Math.max(0, (p - a[0]) / (b[0] - a[0])));
  return `rgb(${a[feld].map((x, k) => Math.round(x + (b[feld][k] - x) * t)).join(",")})`;
}
/* 6.6: Weckszenen - Vordergrund je Szene (fester Inhalt), gefärbt wie die Hügel; Ostsee und Wald mit eigenen Geräuschen */
const SONNE_MEER = [[0, [0, 0, 0]], [0.4, [10, 18, 40]], [1, [40, 110, 170]]];
const SONNE_SAND = [[0, [0, 0, 0]], [0.4, [40, 30, 20]], [1, [230, 205, 150]]];
function tannen(y, hoehe, abstand, versatz) {
  let d = "";
  for (let x = versatz; x < 1640; x += abstand) {
    const h = hoehe * (0.75 + ((x * 37) % 50) / 100);
    d += `M${x - h * 0.32} ${y} L${x} ${y - h} L${x + h * 0.32} ${y}Z`;
  }
  return d + `M0 ${y} H1600 V300 H0Z`;
}
/* 6.9.20: Szenen mit mehr Tiefe (blasse Hügel weit hinten) und kleinen Dingen, die mit dem Morgen wechseln */
const SA_FERN = '<path class="sa-h0" d="M0 110 C 200 70 380 90 560 100 S 900 50 1100 80 S 1400 60 1600 90 V300 H0Z"/>';
const SA_HAUS = '<g class="sa-haus"><path class="sa-hf" d="M1180 112 h70 v-38 l-35 -28 l-35 28 Z"/><rect class="sa-hf" x="1232" y="44" width="9" height="20"/>' +
  '<rect class="sa-fenster" x="1197" y="84" width="14" height="14" rx="2"/><rect class="sa-fenster" x="1220" y="84" width="14" height="14" rx="2"/></g>' +
  '<g class="sa-hf"><circle cx="420" cy="92" r="22"/><rect x="416" y="100" width="8" height="30"/><circle cx="470" cy="100" r="16"/><rect x="467" y="106" width="6" height="24"/></g>';
const SA_TURM = '<path class="sa-turm" d="M1330 70 l10 -120 h24 l10 120 Z"/><path class="sa-turm-band" d="M1335 10 h34 l1.5 18 h-37 Z M1339 -30 h26 l1.5 16 h-29 Z"/>' +
  '<rect class="sa-turm-band" x="1336" y="-62" width="32" height="14" rx="3"/>' +
  '<path class="sa-strahl" d="M1352 -55 L1600 -110 L1600 0 Z M1352 -55 L1100 -110 L1100 0 Z"/>' +
  '<g class="sa-glitzer"><path d="M760 90h80M740 120h120M720 155h160M700 195h200M690 235h220"/></g>';
const SA_NEBEL = '<rect class="sa-nebel" x="0" y="150" width="1600" height="90"/>';
const SZENE_BILD = {
  huegel: '<svg viewBox="0 0 1600 300" preserveAspectRatio="none">' + SA_FERN +
    '<path class="sa-h1" d="M0 150 C 250 60 450 80 700 140 S 1200 60 1600 120 V300 H0Z"/>' + SA_HAUS +
    '<path class="sa-h2" d="M0 220 C 300 150 600 170 900 210 S 1400 150 1600 190 V300 H0Z"/></svg>',
  ostsee: '<svg viewBox="0 -120 1600 420" preserveAspectRatio="none"><path class="sa-h1 sa-meer" d="M0 70 H1600 V300 H0Z"/>' + SA_TURM +
    '<g class="sa-wellen"><path d="M100 120h180M520 150h240M980 115h160M1250 165h220M300 200h260M820 215h200"/></g>' +
    '<path class="sa-h2 sa-sand" d="M0 245 C 400 215 900 235 1600 220 V300 H0Z"/></svg>',
  wald: '<svg viewBox="0 0 1600 300" preserveAspectRatio="none">' + SA_FERN +
    `<path class="sa-h1" d="${tannen(200, 170, 70, 10)}"/>` + SA_NEBEL + `<path class="sa-h2" d="${tannen(300, 190, 95, 40)}"/></svg>`,
};
const SA_TURM_WEISS = [[0, [0, 0, 0]], [0.4, [40, 30, 36]], [1, [245, 244, 240]]];
const SA_TURM_ROT = [[0, [0, 0, 0]], [0.4, [60, 20, 24]], [1, [214, 64, 60]]];
const SA_WOLKE = [[0, [40, 30, 50]], [0.45, [255, 150, 140]], [0.75, [255, 220, 200]], [1, [255, 255, 255]]];
const SA_WOLKEN = '<svg viewBox="0 0 1600 400" preserveAspectRatio="xMidYMid slice">' +
  [[260, 120, 1.3], [820, 70, 1], [1260, 150, 1.6]].map(([x, y, s]) => `<g class="sa-wolke"><g transform="translate(${x} ${y}) scale(${s})">` +
    '<ellipse cx="0" cy="0" rx="90" ry="26"/><circle cx="-40" cy="-14" r="34"/><circle cx="20" cy="-26" r="44"/><circle cx="70" cy="-8" r="26"/></g></g>').join("") + "</svg>";

function sonnenaufgang(minuten, szene = "huegel") {
  if (zustand.overlay) schliesseOverlay();
  nachtSchwarzWeg();
  if (zustand.schoner) schonerAus();
  const sterne = el("div", { class: "sa-sterne" });
  const sonne = el("div", { class: "sa-sonne" });
  const huegel = el("div", { class: "sa-huegel" });
  if (!SZENE_BILD[szene]) szene = "huegel";
  huegel.innerHTML = SZENE_BILD[szene];                                 /* fester Inhalt aus diesem Modul */
  const wolken = el("div", { class: "sa-wolken" });
  wolken.innerHTML = SA_WOLKEN;                                           /* fester Inhalt aus diesem Modul */
  const strahlen = el("div", { class: "sa-strahlen" });                   /* nur Stufe „hoch“ sichtbar (CSS) */
  const voegel = el("div", { class: "sa-voegel" });
  voegel.innerHTML = '<svg viewBox="0 0 160 40"><path d="M5 20q8-8 16 0q8-8 16 0M60 10q7-7 14 0q7-7 14 0M110 26q6-6 12 0q6-6 12 0" ' +
    'fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></svg>';            /* fester Inhalt */
  const box = el("section", { class: "overlay sonne szene-" + szene }, sterne, strahlen, sonne, wolken, huegel, voegel);
  document.getElementById("overlay-wurzel").replaceChildren(box);
  const start = Date.now(), dauer = minuten * 60000;
  const schritt = () => {
    const p = Math.min(1, (Date.now() - start) / dauer);
    box.style.background = `linear-gradient(180deg, ${mische(SONNE_HIMMEL, p, 1)} 0%, ${mische(SONNE_HIMMEL, Math.min(1, p * 1.1), 2)} 78%)`;
    sterne.style.opacity = String(Math.max(0, 1 - p * 2.2));
    sonne.style.transform = `translate(-50%, ${Math.round(70 - p * 95)}vh) scale(${(1.25 - p * 0.35).toFixed(2)})`;
    sonne.style.background = `radial-gradient(circle, #fff8e0 0, ${mische(SONNE_KUGEL, p)} 45%, rgba(255,140,60,0) 72%)`;
    sonne.style.opacity = String(Math.min(1, p * 3));
    huegel.querySelector(".sa-h1").style.fill = mische(szene === "ostsee" ? SONNE_MEER : SONNE_HUEGEL, p * 0.85);
    const vorn = mische(SONNE_HUEGEL, p * 0.8);
    huegel.querySelectorAll(".sa-hf, .sa-hf *").forEach((t) => { t.style.fill = vorn; });
    huegel.querySelectorAll(".sa-turm").forEach((t) => { t.style.fill = mische(SA_TURM_WEISS, p); });
    huegel.querySelectorAll(".sa-turm-band").forEach((t) => { t.style.fill = mische(SA_TURM_ROT, p); });
    const fern = huegel.querySelector(".sa-h0");
    if (fern) fern.style.fill = mische(SONNE_HIMMEL, Math.min(1, p * 1.1), 2);
    huegel.querySelectorAll(".sa-fenster").forEach((t) => { t.style.opacity = String(Math.max(0, 1 - p * 2.2)); });
    const strahl = huegel.querySelector(".sa-strahl");
    if (strahl) strahl.style.opacity = String(Math.max(0, 0.5 - p * 0.9));
    const glitzer = huegel.querySelector(".sa-glitzer");
    if (glitzer) glitzer.style.opacity = String(Math.max(0, Math.min(1, p * 1.6 - 0.4)));
    const nebel = huegel.querySelector(".sa-nebel");
    if (nebel) nebel.style.opacity = String(Math.max(0.05, 0.75 - p * 0.8));
    wolken.style.fill = mische(SA_WOLKE, p);
    wolken.style.opacity = String(Math.min(0.9, 0.35 + p));
    strahlen.style.opacity = String(Math.max(0, Math.min(0.5, (p - 0.3) * 1.2)));
    huegel.querySelector(".sa-h2").style.fill = mische(szene === "ostsee" ? SONNE_SAND : SONNE_HUEGEL, p * (szene === "wald" ? 0.55 : 0.7));
    voegel.classList.toggle("an", p > 0.65);
    const wellen = huegel.querySelector(".sa-wellen");
    if (wellen) wellen.style.opacity = String(Math.max(0, p * 1.4 - 0.3));
  };
  schritt();
  const timer = setInterval(schritt, 2000);
  const geraeusch = weckklang(szene, dauer);
  zustand.overlay = { id: "sonne", schliesse: () => { clearInterval(timer); geraeusch?.(); }, taste() { schliesseOverlay(); return true; } };
}

/* Fernseher aus: zusätzlich schwarzes Bild (falls der Fernseher CEC nicht befolgt); eine Taste weckt */
function nachtSchwarz() {
  const box = el("div", { id: "nacht-schwarz" });
  document.body.append(box);
  zustand.nachtSchwarz = box;
  setTimeout(() => { if (zustand.nachtSchwarz === box && zustand.nachthimmel && !box.stopp) himmelIn(box); }, 2500);
}
function nachtSchwarzWeg() {
  zustand.nachtSchwarz?.stopp?.();
  zustand.nachtSchwarz?.remove();
  zustand.nachtSchwarz = null;
}

/* 3.4: Erinnerungen und Nachrichten bleiben stehen, bis OK gedrückt wird */
function zeigeMeldungen(liste) {
  const nummern = liste.map((m) => m.nr).join(",");
  if (!liste.length || zustand.still) {
    if (zustand.meldungen) { zustand.meldungen.box.remove(); zustand.meldungen = null; }
    return;
  }
  if (zustand.meldungen?.nummern === nummern) return;
  /* 6.9.1: Ist Franzis Zimmer offen, sagt sie die Meldung selbst (in der Sprechblase) - dann gilt sie als gesehen */
  if (zustand.overlay?.sagen && liste.every((m) => !m.medium) && zustand.overlay.sagen(liste.map((m) => (m.quelle ? m.quelle + ": " : "") + m.text).join("  ·  "))) {
    zustand.meldungen?.box.remove();
    zustand.meldungen = null;
    sende("/api/meldungen/gesehen", { nummern: liste.map((m) => m.nr) }).catch(() => {});
    ton("ok");
    return;
  }
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
  kopfFranzi();                                    /* 6.9.59: z. B. nach Mein Tag gleich mit Herzaugen */
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
  if (zustand.nachtSchwarz) { event.preventDefault(); nachtSchwarzWeg(); ladeKacheln(); return; }
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

  if (zustand.meldungNr !== null && s.meldung.nr !== zustand.meldungNr && s.meldung.text) {
    if (!zustand.overlay?.sagen?.(s.meldung.text)) hinweis(s.meldung.text, 6000);    /* 6.9.7: bei Franzi in der Sprechblase */
  }
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
  /* 6.1: Sperrzeit und Nacht - keine Diashow; nachts statt dessen der Nachthimmel */
  zustand.sperrzeit = s.sperrzeit || null;
  zustand.nacht = Boolean(s.nachtruhe || s.still || s.sperrzeit?.nacht);
  zustand.nachthimmel = Boolean(s.nachthimmel);
  if (zustand.schoner && !zustand.schoner.nacht && (zustand.nacht || zustand.sperrzeit || s.gesperrt)) schonerAus();
  if (zustand.nachthimmel && zustand.nachtSchwarz && !zustand.nachtSchwarz.stopp) himmelIn(zustand.nachtSchwarz);
  zeigeMeldungen(s.meldungen || []);
  /* 3.5: Glocke oben mit Zahl der neuen Nachrichten (und auf der Kachel) */
  /* 4.4: Nachrichten von Freunden in der Sperrzeit zählen nur mit (lesen erst danach) */
  const anzahl = (s.meldungen || []).length + (s.freunde_spaeter || 0);
  if (anzahl !== (zustand.meldungenAnzahl || 0)) {          /* 6.0: „🔔 2 neu“ auf der Kachel „Mein Zimmer“ */
    zustand.meldungenAnzahl = anzahl;
    const z = document.querySelector('.kachel[data-id="ordner-zimmer"]');
    if (z) { z.querySelector(".kachel-hinweis:not(.routine)")?.remove(); if (anzahl) z.append(el("div", { class: "kachel-hinweis", text: `🔔 ${anzahl} neu` })); }
  }
  const glocke = document.getElementById("glocke");
  glocke.hidden = !anzahl;
  glocke.textContent = `🔔 ${anzahl}`;
  document.querySelector('.kachel[data-id="spiel-nachrichten"]')?.classList.toggle("hat-neue", anzahl > 0);
  if (s.wecker && zustand.overlay?.id !== "wecker-klingelt") weckerKlingelt(s.wecker);
  routineJetzt(s);

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

/* 6.9.58: Morgen-/Abend-Routine deutlich auslösen. Läuft eine Liste von Mein Tag (und ist noch nicht geschafft), leuchtet
   die Kachel, und steht der Fernseher auf der Startseite (kein Spiel, kein Player, kein Wecker), öffnet sich Mein Tag von
   selbst - zu Beginn und bei jeder Erinnerung (alle 10 Minuten), auch direkt nach dem Wecker. Je Runde nur einmal: wer
   Mein Tag schließt, wird erst bei der nächsten Erinnerung wieder geholt. Eltern schalten das je Liste ab („oeffnen“). */
const routineGeoeffnet = new Set();
function routineJetzt(s) {
  const r = s.routine;
  /* liegt Mein Tag in einem Bereich, leuchtet der Ordner (und im Ordner die Kachel selbst) */
  const app = (zustand.alle || []).find((a) => a.id === "spiel-meintag");
  document.querySelectorAll(".kachel.routine-jetzt").forEach((k) => {
    if (!r || (k.dataset.id !== "spiel-meintag" && k.dataset.id !== `ordner-${app && bereichVon(app)}`)) {
      k.classList.remove("routine-jetzt"); k.querySelector(".kachel-hinweis.routine")?.remove();
    }
  });
  for (const kachel of document.querySelectorAll(`.kachel[data-id="spiel-meintag"]${app ? `, .kachel[data-id="ordner-${bereichVon(app)}"]` : ""}`)) {
    kachel.classList.toggle("routine-jetzt", Boolean(r));
    const alt = kachel.querySelector(".kachel-hinweis.routine");
    const text = r ? `⏰ ${r.name} · ${r.offen}` : "";
    if (alt && alt.textContent !== text) alt.remove();
    if (r && (!alt || alt.textContent !== text)) kachel.append(el("div", { class: "kachel-hinweis routine", text }));
  }
  if (!r || !r.oeffnen || !SPIELE["spiel-meintag"]) return;
  const runde = `${r.schluessel}-${r.runde}`;
  if (routineGeoeffnet.has(runde)) return;
  /* Sperrzeit (auch nachts) hält Mein Tag nicht auf - es kostet keine Zeit; nur Nachtruhe/Still, Spiel, Player, Auszeit */
  if (zustand.overlay || s.aktuell || s.running || zustand.gesperrt || zustand.wartung || s.nachtruhe || s.still || zustand.nachtSchwarz) return;
  routineGeoeffnet.add(runde);
  if (zustand.schoner) schonerAus();
  oeffneSpiel({ id: "spiel-meintag" });
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
  if (!vorwarnTimer) vorwarnTimer = setInterval(zeichne, 1000);
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
    sym.replaceChildren(auszeit ? el("span", { class: "sperre-auszeit" }, franzi("muede", "franzi-sperre"), el("span", { class: "fe-zeichen", text: "⏳" }))   /* 6.9.62 */
      : franzi("schlaf", "franzi-sperre"));
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

/* ------------------------------------------------------------ Diashow (3.1 Zeichnungen, 4.4 Fotoalbum)
   6.8.7: startet nur noch von Hand („▶ Diashow jetzt“ im Fotoalbum) - die automatische Diashow nach 5 Minuten hat den Pi 3
   auf 60 °C gebracht. Sparsam: jedes Bild wird einmal auf Bildschirmgröße verkleinert (createImageBitmap) und auf eine
   von zwei Leinwänden gemalt, der Wechsel ist eine einzige Überblendung (opacity) alle 10 s, dazwischen ruht alles.
   Das nächste Bild wird vorher vorbereitet, alte Bilder werden freigegeben. Nachts kommt weiter der Nachthimmel. */
const DIA_TAKT_MS = 10000;
function auswahlUrl(id) {
  const [art, ...rest] = id.split(":"), wert = rest.join(":");
  if (art === "ordner") return "/api/fotoalbum/bild?pfad=" + encodeURIComponent(wert);
  return (art === "album" ? "/album/" : "/zeichnung/") + encodeURIComponent(wert);
}
const NACHTHIMMEL_NACH_MS = 60 * 1000;
function bildElement(url) {
  return new Promise((ja, nein) => { const img = new Image(); img.onload = () => ja(img); img.onerror = nein; img.src = url; });
}
async function bildFuerSchirm(url, breite, hoehe) {
  const blob = await (await fetch(url)).blob();
  const roh = await createImageBitmap(blob).catch(() => bildElement(url).then((img) => createImageBitmap(img)));
  const faktor = Math.min(1, breite / roh.width, hoehe / roh.height);
  if (faktor >= 1) return roh;
  const klein = await createImageBitmap(roh, { resizeWidth: Math.round(roh.width * faktor), resizeHeight: Math.round(roh.height * faktor),
                                               resizeQuality: "medium" });
  roh.close();
  return klein;
}
async function schonerPruefen(sofort = false) {
  if (zustand.schoner || zustand.overlay || zustand.gesperrt?.auszeit || zustand.wartung || zustand.nachtSchwarz) return;
  /* 6.1: In Sperrzeiten keine Diashow (stört beim Schlafen); nachts nach einer Minute der dunkle Nachthimmel */
  if (zustand.nacht || zustand.sperrzeit || zustand.gesperrt) {
    if (zustand.nacht && Date.now() - zustand.letzteTaste >= NACHTHIMMEL_NACH_MS) nachthimmelSchoner();
    return;
  }
  if (!sofort) {                                         /* 6.8.7: keine automatische Diashow mehr - 6.9.47: Franzi + Uhr */
    const min = zustand.bildschirm?.schoner_min ?? 5;
    if (min > 0 && Date.now() - zustand.letzteTaste >= min * 60 * 1000) franziSchoner();
    return;
  }
  let bilder = [];
  try {
    const fa = await hole("/api/fotoalbum").catch(() => null);
    if (fa?.erlaubt && fa.auswahl.length) bilder = fa.auswahl.map((id) => auswahlUrl(id));
    else bilder = (await hole("/api/zeichnungen")).zeichnungen.map((z_) => z_.url);
  } catch (_) { return; }
  const box = el("div", { id: "schoner" });
  const B = Math.min(1280, innerWidth), H = Math.min(720, innerHeight);
  const leinwand = [0, 1].map(() => el("canvas", { class: "dia-bild", width: B, height: H }));
  const uhr = el("div", { class: "schoner-uhr" });
  box.append(...leinwand, uhr);
  if (!bilder.length) box.append(el("div", { class: "schoner-leer", text: "Noch keine Bilder – such dir im Fotoalbum welche aus (⭐)." }));
  document.body.append(box);
  let i = 0, vorn = 0, naechstes = null, aus = false, diaMini = null;
  const vorbereiten = () => {
    if (!bilder.length) return null;
    const url = bilder[i++ % bilder.length];
    return bildFuerSchirm(url, B, H).catch(() => null);
  };
  const zeigen = async () => {
    const jetzt = new Date();
    uhr.replaceChildren(el("b", { text: jetzt.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }) }),
      el("small", { text: jetzt.toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long" }) }));
    const bild = await (naechstes || vorbereiten());
    if (aus) { bild?.close?.(); return; }
    if (bild) {
      const hinten = leinwand[1 - vorn], g = hinten.getContext("2d");
      g.fillStyle = "#000"; g.fillRect(0, 0, B, H);
      /* 6.9.22: Ränder mit demselben Foto füllen - unscharf und dunkel. Unschärfe billig über ein winziges Zwischenbild
         (der Browser vergrößert weich) - geht auch auf dem Pi 3, einmal je Bild */
      if (bild.width < B - 4 || bild.height < H - 4) {
        const mini = diaMini || (diaMini = document.createElement("canvas"));
        mini.width = 32; mini.height = Math.max(1, Math.round(32 * H / B));
        const m = mini.getContext("2d"), f = Math.max(mini.width / bild.width, mini.height / bild.height);
        m.drawImage(bild, (mini.width - bild.width * f) / 2, (mini.height - bild.height * f) / 2, bild.width * f, bild.height * f);
        g.imageSmoothingQuality = "low"; g.drawImage(mini, 0, 0, B, H);
        g.fillStyle = "rgba(0,0,0,.55)"; g.fillRect(0, 0, B, H);
        g.save(); g.shadowColor = "rgba(0,0,0,.6)"; g.shadowBlur = 40; g.fillStyle = "#000";
        g.fillRect(Math.round((B - bild.width) / 2), Math.round((H - bild.height) / 2), bild.width, bild.height); g.restore();
      }
      g.drawImage(bild, Math.round((B - bild.width) / 2), Math.round((H - bild.height) / 2));
      hinten.dataset.zoom = String((i % 4));                         /* Stufe „hoch“: Richtung des langsamen Zooms */
      bild.close?.();
      hinten.classList.add("an"); leinwand[vorn].classList.remove("an");
      vorn = 1 - vorn;
    }
    naechstes = bilder.length > 1 ? vorbereiten() : null;          /* das nächste schon jetzt, in Ruhe */
  };
  zeigen();
  zustand.schoner = { box, timer: setInterval(zeigen, DIA_TAKT_MS), stopp: () => { aus = true; naechstes?.then((b) => b?.close?.()); } };
}

/* 6.9.47: Bildschirmschoner tagsüber - ruhig: große Uhr, Franzi döst (später schläft sie). Alle 30 s wandert alles sanft
   an eine andere Stelle (schont den Fernseher vor Einbrennen), sonst bewegt sich nichts - kaum Last für den Pi 3. */
function franziSchoner() {
  const box = el("div", { id: "schoner", class: "franzi-schoner" });
  const wandern = el("div", { class: "fs-wandern" });
  const figur = el("div", { class: "fs-franzi" }, franzi("muede"));
  const uhr = el("div", { class: "schoner-uhr fs-uhr" });
  wandern.append(figur, uhr);
  box.append(wandern);
  document.body.append(box);
  const seit = Date.now();
  const takt = () => {
    const jetzt = new Date();
    uhr.replaceChildren(el("b", { text: jetzt.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }) }),
      el("small", { text: jetzt.toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long" }) }));
    if (Date.now() - seit > 2 * 60 * 1000 && !figur.dataset.schlaeft) { figur.dataset.schlaeft = "1"; figur.replaceChildren(franzi("schlaf")); }
    const x = Math.round((Math.random() - 0.5) * 36), y = Math.round((Math.random() - 0.5) * 30);
    wandern.style.transform = `translate(${x}vw, ${y}vh)`;
  };
  takt();
  zustand.schoner = { box, timer: setInterval(takt, 30000) };
}

function schonerAus() {
  clearInterval(zustand.schoner.timer);
  zustand.schoner.stopp?.();
  zustand.schoner.box.remove();
  zustand.schoner = null;
}

/* 6.1: Nachthimmel als „Schoner“ in der Nacht - sehr dunkel, eine Taste beendet ihn */
function himmelIn(box) {
  const canvas = el("canvas", { class: "nacht-himmel" });
  box.append(canvas);
  box.stopp = sternenhimmel(canvas);
  return box.stopp;
}
function nachthimmelSchoner() {
  const box = el("div", { id: "schoner", class: "nacht" });
  document.body.append(box);
  zustand.schoner = { box, timer: 0, nacht: true, stopp: himmelIn(box) };
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
  const sonne = location.hash.match(/^#sonne-(\d+)(?:-(huegel|ostsee|wald))?$/);
  if (sonne) { history.replaceState(null, "", location.pathname); sonnenaufgang(Math.min(60, Math.max(1, +sonne[1])), sonne[2] || "huegel"); }
  if (location.hash === "#wecker") { history.replaceState(null, "", location.pathname); statusAbfrage(); }   /* Status bringt den Wecker */
  if (location.hash === "#zurueck") { history.replaceState(null, "", location.pathname); hinweis("Willkommen zurück!"); }   /* 4.1: nach dem Retro-Spiel */
  const pause = location.hash.match(/^#pause-(\d+)$/);
  if (pause) { history.replaceState(null, "", location.pathname); bewegungspause(Math.min(900, +pause[1])); }
  /* 6.9.8: ein Spiel direkt öffnen (#spiel-franzi) - der Server prüft beim Start, ob es gerade erlaubt ist */
  const spiel = location.hash.match(/^#(spiel-[a-z]+)$/);
  if (spiel && SPIELE[spiel[1]]) { history.replaceState(null, "", location.pathname); oeffneSpiel({ id: spiel[1] }); }
}

/* 6.4: was Franzi trägt (aus „Mein Tag“) - danach den Kopf neu zeichnen */
export async function franziAnziehen() {
  try { setzeFranzi((await hole("/api/meintag")).franzi); } catch (_) { return; }
  kopfFranzi();
}

/* 6.9.32: Franzi oben im Kopf passt zur Tageszeit (nachts schläft sie, früh staunt sie). Ist Franzi als Haustier an,
   zeigt sie ihre echte Stimmung und Kleidung. Abfrage nur alle 15 Minuten. */
const KOPF_GESICHT = { muede: "muede", schlaefrig: "schlaf", vertraeumt: "schlaf", hungrig: "staunen", gelangweilt: "staunen",
                       anhaenglich: "verliebt", trotzig: "grummelig", genervt: "genervt", grummelig: "grummelig" };
const WETTER_GESICHT = { sonne: "jubel", schnee: "staunen", regen: "muede", kalt: "grummelig" };
if (typeof window !== "undefined" && !window.__ffKopf) window.__ffKopf = setInterval(() => { if (!document.hidden && !zustand.overlay) kopfFranzi(); }, 30000);
async function kopfFranzi() {
  const stunde = new Date().getHours();
  let gesicht = stunde >= 21 || stunde < 6 ? "schlaf" : stunde < 8 ? "staunen" : "froh", sachen = null, f = null;
  try {
    f = await hole("/api/franzi");
    /* 6.9.59: Reihenfolge - Schlafenszeit, Lob (Stern in den letzten 45 Min. = Herzaugen), was Franzi braucht, Wetter, Uhrzeit */
    if (f?.aktiv && !f.abenteuer) {
      sachen = { ...kleidungZuSachen(f.angezogen) };
      if (gesicht !== "schlaf") gesicht = f.lob ? "verliebt" : KOPF_GESICHT[f.stimmung] || WETTER_GESICHT[f.wetter] || gesicht;
    }
  } catch (_) { /* dann eben nach der Uhr */ }
  /* 6.9.61: Franzi sagt etwas - alle paar Minuten für ein paar Sekunden (nur auf der Startseite, nicht nachts) */
  const neu = spruchFaellig(f, gesicht);
  if (neu) spruchJetzt = { ...neu, bis: Date.now() + SPRUCH_SICHTBAR_MS };
  const blase = spruchJetzt && Date.now() < spruchJetzt.bis && gesicht !== "schlaf" ? spruchJetzt : null;
  if (blase) gesicht = blase.gesicht || gesicht;
  const kopf = document.getElementById("franzi-kopf");
  kopf?.replaceChildren(franzi(gesicht, "", sachen && Object.keys(sachen).length ? sachen : null),
    ...(blase ? [el("div", { class: "kopf-blase" + (neu ? "" : " ruhig"), text: blase.text })] : []));
  if (blase) { clearTimeout(kopfFranzi.blaseWeg); kopfFranzi.blaseWeg = setTimeout(() => kopf?.querySelector(".kopf-blase")?.classList.add("weg"), blase.bis - Date.now()); }
}
let spruchJetzt = null;
const SPRUCH_ABSTAND_MS = 3 * 60 * 1000, SPRUCH_SICHTBAR_MS = 12000;
let spruchZuletzt = Date.now() - SPRUCH_ABSTAND_MS + 20000;      /* erster Satz kurz nach dem Start */
function spruchFaellig(f, gesicht) {
  if (!f?.spruch?.text || gesicht === "schlaf" || zustand.overlay || zustand.schoner || document.hidden) return null;
  if (Date.now() - spruchZuletzt < SPRUCH_ABSTAND_MS) return null;
  spruchZuletzt = Date.now();
  return f.spruch;
}

/* 6.9.40: Hintergrundmusik (Eltern: Aussehen → Klänge) - auf der Startseite oder in Franzis Zimmer, in Schleife.
   Nur, wenn nichts anderes läuft (kein Spiel, kein Video, keine Sperre, Seite sichtbar). Ab Werk aus. */
let musikSpieler = null, musikKlang = "";
function musikPruefen() {
  const m = zustand.musik || {};
  const ov = zustand.overlay;
  const ort = document.hidden || zustand.schoner || !document.getElementById("sperre")?.hidden || !document.getElementById("wartung")?.hidden ? null
    : !ov ? "start" : null;                                        /* 6.9.50: im Zimmer spielt die Musikbox */
  const wahl = ort && m[ort];
  if (!wahl) { if (musikSpieler && !musikSpieler.paused) musikSpieler.pause(); return; }
  if (!musikSpieler || musikKlang !== wahl.klang) {
    musikSpieler?.pause();
    musikSpieler = new Audio("/api/klang?id=" + encodeURIComponent(wahl.klang));
    musikSpieler.loop = true;
    musikKlang = wahl.klang;
  }
  musikSpieler.volume = Math.max(0, Math.min(1, (wahl.laut ?? 30) / 100));
  if (musikSpieler.paused) musikSpieler.play().catch(() => { /* Autoplay verweigert: beim nächsten Mal */ });
}

async function start() {
  /* 6.0: feste Symbole der Seite als 3D-Bilder */
  document.querySelectorAll("#wartung .gross, #sperre .gross").forEach((g) => g.replaceChildren(bild(g.textContent.trim())));
  document.getElementById("franzi-kopf").replaceChildren(franzi("hallo"));    /* 6.0: Maskottchen winkt zur Begrüßung (6.9.45: danach Arme unten) */
  uhrStellen();
  setInterval(uhrStellen, 10000);
  setInterval(musikPruefen, 2000);                                  /* 6.9.40: billig, nur ein Vergleich */
  document.addEventListener("visibilitychange", musikPruefen);
  gruessen("");
  while (!(await ladeKacheln())) await pause(2000);
  franziAnziehen();
  setTimeout(kopfFranzi, 5000);                                    /* 6.9.45: nach dem Winken Arme runter (Stimmung/Tageszeit) */
  setInterval(kopfFranzi, 15 * 60 * 1000);
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
