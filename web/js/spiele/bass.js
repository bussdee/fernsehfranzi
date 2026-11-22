/* Bass-Ecke (3.0, ausgebaut in 3.1): beim Bass-Lernen helfen.
 *   Stimmen      Referenzton je Saite (E A D G), auf Wunsch eine Oktave höher (TV-Lautsprecher)
 *   Metronom     40-220 Schläge/min, Takt 4/4 mit Betonung, großes Blinken (auch ohne Ton sichtbar)
 *   Griffbrett   „Wo ist das C auf der A-Saite?“ - mit Pfeilen hinfahren, OK; der Ton klingt mit
 *   Meine Songs  von den Eltern gepflegt: Erklärvideo, Tabs, Backing Track (öffnet im Kiosk-Browser)
 * 3.1:
 *   Tempo-Trainer (Metronom wird alle 4 Takte schneller) · Rhythmus-Spiel (OK im Takt)
 *   Gehörbildung (höher/tiefer, welche Saite) · Tabs lesen (Quiz) · Stimmgerät mit Mikrofon + Mithören
 *   Plex-Bibliotheken „Unterricht“ und „Backing Tracks“ · Übungs-Tagebuch mit Serie
 * Lernen zählt nicht zur Spielzeit; Erfolge melden Sticker (POST /api/erfolg). */
import { el } from "../gemeinsam.js";
import { kopf, ton, menue, konfetti } from "./kern.js";
import { gitarre, keyboard, singen, songSuche, aufnehmen } from "./musik.js";      /* 3.5: Musik-Akademie */

const SAITEN = [{ name: "G", hz: 98.0 }, { name: "D", hz: 73.42 }, { name: "A", hz: 55.0 }, { name: "E", hz: 41.2 }];
const TOENE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "H"];
const SAITE_GRUNDTON = { G: 7, D: 2, A: 9, E: 4 };
const BUENDE = 12;
const ARTEN = { video: "Erklärvideo", tab: "Tabs / Noten", backing: "Backing Track" };
const BIBLIOTHEKEN = { unterricht: "📺 Bass-Unterricht (Plex)", backing: "🥁 Backing Tracks (Plex)" };

let audio = null;
export function ctx() { audio = audio || new AudioContext(); return audio; }

/** Gezupfter Ton (Sägezahn durch Tiefpass, abklingend) - bass-ähnlich, auf TV-Lautsprechern hörbar. */
export function zupfe(hz, dauer = 1.6, laut = 0.25) {
  const a = ctx(), t = a.currentTime;
  const osz = a.createOscillator(), filter = a.createBiquadFilter(), g = a.createGain();
  osz.type = "sawtooth";
  osz.frequency.value = hz;
  filter.type = "lowpass";
  filter.frequency.setValueAtTime(hz * 8, t);
  filter.frequency.exponentialRampToValueAtTime(hz * 2, t + dauer);
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(laut, t + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dauer);
  osz.connect(filter).connect(g).connect(a.destination);
  osz.start(t);
  osz.stop(t + dauer + 0.05);
}

function klick(betont) {
  const a = ctx(), t = a.currentTime, osz = a.createOscillator(), g = a.createGain();
  osz.frequency.value = betont ? 1500 : 1000;
  g.gain.setValueAtTime(0.3, t);
  g.gain.exponentialRampToValueAtTime(0.0001, t + 0.05);
  osz.connect(g).connect(a.destination);
  osz.start(t);
  osz.stop(t + 0.06);
}

/** Grundfrequenz per Autokorrelation (Stimmgerät). Rückgabe Hz oder null. */
export function tonhoehe(puffer, rate) {
  let rms = 0;
  for (const x of puffer) rms += x * x;
  if (Math.sqrt(rms / puffer.length) < 0.01) return null;          /* zu leise */
  const min = Math.floor(rate / 400), max = Math.floor(rate / 30);  /* Bass: 30-400 Hz */
  let bester = -1, wert = 0;
  for (let lag = min; lag <= max; lag++) {
    let summe = 0;
    for (let i = 0; i + lag < puffer.length; i++) summe += puffer[i] * puffer[i + lag];
    if (summe > wert) { wert = summe; bester = lag; }
  }
  return bester > 0 ? rate / bester : null;
}

export function naechsterTon(hz) {
  const halbton = 12 * Math.log2(hz / 440) + 57;            /* 57 = A4 ab C0 */
  const rund = Math.round(halbton);
  return { name: TOENE[((rund % 12) + 12) % 12], oktave: Math.floor(rund / 12), cent: Math.round((halbton - rund) * 100) };
}

function erfolg(api, art, wert) { api.sende("/api/erfolg", { art, wert }).catch(() => {}); }

/** Passt ein gehörter Ton (Hz) zum Ziel? Gleicher Tonname; die Oktave darf abweichen
    (die Tonerkennung rutscht beim Bass gern eine Oktave nach oben). */
export function tonPasst(hz, zielName) {
  return Boolean(hz) && naechsterTon(hz).name === zielName;
}

/** Mikrofon (USB) dauerhaft abhören; meldet einen Ton erst, wenn er ~0,25 s stabil ist (gezupft, nicht Rauschen).
    Rückgabe: Funktion zum Beenden, oder null ohne Mikrofon. */
export async function mikroHoeren(beiTon) {
  let strom;
  try {
    strom = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
  } catch (_) { return null; }
  const a = ctx(), quelle = a.createMediaStreamSource(strom), analyse = a.createAnalyser();
  analyse.fftSize = 4096;
  quelle.connect(analyse);
  const puffer = new Float32Array(analyse.fftSize);
  let laeuft = true, letzter = null, gleich = 0, gemeldet = null;
  const schleife = () => {
    if (!laeuft) return;
    analyse.getFloatTimeDomainData(puffer);
    const hz = tonhoehe(puffer, a.sampleRate);
    const name = hz ? naechsterTon(hz).name : null;
    if (name && name === letzter) gleich++; else { gleich = 0; letzter = name; }
    if (!name) gemeldet = null;
    if (name && gleich === 3 && gemeldet !== name) { gemeldet = name; beiTon(hz, naechsterTon(hz)); }
    setTimeout(schleife, 80);
  };
  schleife();
  return () => { laeuft = false; quelle.disconnect(); strom.getTracks().forEach((s) => s.stop()); };
}

export default {
  symbol: "🎼",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "🎼 Musik-Akademie", "Pfeile Wählen · OK · STOP Zurück");
    let modus = null, aufraeumen = null;
    let standardZurueck = null;          /* STOP in einer Übung ohne eigenes Ziel: zurück ins letzte Menü */

    function stopp() { aufraeumen?.(); aufraeumen = null; }

    /* 3.5: Rahmen für die anderen Instrumente (musik.js) */
    const k = {
      inhalt, hilfe, api,
      modus: (m) => { modus = m; },
      aufraeumen: (f) => { aufraeumen = f; },
      zurueck: () => hauptmenue(),
      erfolg: (art, wert) => erfolg(api, art, wert),
      stimmgeraet: (info) => stimmgeraet(info),
      menue(titel, eintraege) {
        stopp();
        hilfe.textContent = "Pfeile Wählen · OK · STOP Zurück";
        punkte.textContent = "";
        const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text: titel }));
        inhalt.replaceChildren(spalte);
        modus = menue(spalte, eintraege);
        modus.unter = true;
        modus.zurueck = hauptmenue;
        standardZurueck = () => k.menue(titel, eintraege);
      },
    };

    function hauptmenue() {
      stopp();
      hilfe.textContent = "Pfeile Wählen · OK · STOP Zurück";
      punkte.textContent = "";
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text: "Was möchtest du heute machen?" }));
      inhalt.replaceChildren(spalte);
      modus = menue(spalte, [
        { text: "🎸 Bass", aktion: bassMenue },
        { text: "🪕 Gitarre", aktion: () => gitarre(k) },
        { text: "🎹 Keyboard", aktion: () => keyboard(k) },
        { text: "🎤 Singen", aktion: () => singen(k) },
        { text: "🎙️ Aufnehmen", aktion: () => aufnehmen(k) },
        { text: "🔎 Song suchen", aktion: () => songSuche(k) },
        { text: "📺 Meine Songs", aktion: songs },
        { text: "📒 Mein Übungs-Tagebuch", aktion: tagebuch },
      ]);
      modus.unter = false;
      standardZurueck = hauptmenue;
    }

    function bassMenue() {
      stopp();
      hilfe.textContent = "Pfeile Wählen · OK · STOP Zurück";
      punkte.textContent = "";
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text: "🎸 Bass – was möchtest du üben?" }));
      inhalt.replaceChildren(spalte);
      modus = menue(spalte, [
        { text: "🎵 Stimmen", aktion: stimmen },
        { text: "🎤 Stimmgerät", aktion: stimmgeraet },
        { text: "⏱️ Metronom", aktion: () => metronom(false) },
        { text: "🚀 Tempo-Trainer", aktion: () => metronom(true) },
        { text: "🥁 Rhythmus-Spiel", aktion: rhythmus },
        { text: "🎯 Griffbrett-Trainer", aktion: () => griffbrett(false) },
        { text: "🎸 Griffbrett mit dem Bass", aktion: () => griffbrett(true) },
        { text: "👂 Gehörbildung", aktion: gehoer },
        { text: "🎤 Nachspielen", aktion: nachspielen },
        { text: "📄 Tabs lesen", aktion: tabsLesen },
      ]);
      modus.unter = true;
      modus.zurueck = hauptmenue;
      standardZurueck = bassMenue;
    }

    /* ---------------------------------------------------- Stimmen */
    function stimmen() {
      let oktave = 2, i = 3;
      const anzeige = el("div", { class: "witz" });
      const info = el("p", { class: "leise", style: "text-align:center" });
      inhalt.replaceChildren(el("div", {}, anzeige, info));
      hilfe.textContent = "← → Saite · OK Ton nochmal · ↑ ↓ Oktave · STOP Zurück";
      const zeige = () => {
        anzeige.textContent = `${SAITEN[i].name}-Saite`;
        info.textContent = oktave === 1 ? "Original-Tonhöhe (tief – am besten mit Anlage/Kopfhörer)"
                                        : "Eine Oktave höher (gut hörbar am Fernseher)";
        zupfe(SAITEN[i].hz * oktave, 2.5);
      };
      zeige();
      const wiederholen = setInterval(() => zupfe(SAITEN[i].hz * oktave, 2.5), 3000);
      aufraeumen = () => clearInterval(wiederholen);
      modus = { unter: true, taste(t) {
        if (t === "ArrowLeft") { i = (i + 1) % 4; zeige(); return true; }    /* links = tiefere Saite */
        if (t === "ArrowRight") { i = (i + 3) % 4; zeige(); return true; }
        if (t === "ArrowUp" || t === "ArrowDown") { oktave = oktave === 1 ? 2 : 1; zeige(); return true; }
        if (t === "Enter" || t === " ") { zeige(); return true; }
        return false;
      } };
    }

    /* ---------------------------------------------------- Metronom */
    function metronom(trainer) {
      let bpm = Number(localStorage.getItem("ff-bpm") || 80), laeuft = false, schlag = 0, timer = 0;
      let ziel = Math.min(220, bpm + 40);
      const zahl = el("div", { class: "witz", style: "font-size:clamp(60px,10vw,140px)" });
      const licht = el("div", { style: "width:22vh;height:22vh;border-radius:50%;margin:3vh auto;background:#233;transition:background .05s" });
      const info = el("p", { class: "leise", style: "text-align:center" });
      inhalt.replaceChildren(el("div", { style: "text-align:center" }, zahl, licht, info));
      hilfe.textContent = trainer ? "OK Start/Stopp · ← → Start-Tempo · ↑ ↓ Ziel-Tempo · STOP Zurück"
                                  : "OK Start/Stopp · ← → ±5 · ↑ ↓ ±1 · STOP Zurück";
      const zeige = () => {
        zahl.textContent = bpm;
        info.textContent = (laeuft ? "läuft" : "angehalten") + " · Schläge pro Minute · Takt 4/4" +
          (trainer ? ` · alle 4 Takte +2 bis ${ziel}` : "");
        if (!trainer) localStorage.setItem("ff-bpm", bpm);
      };
      const tick = () => {
        const betont = schlag % 4 === 0;
        klick(betont);
        licht.style.background = betont ? "#ff6b6b" : "#4ccf8f";
        setTimeout(() => { licht.style.background = "#233"; }, 90);
        schlag++;
        if (trainer && schlag % 16 === 0 && bpm < ziel) { bpm = Math.min(ziel, bpm + 2); zeige(); }
        timer = setTimeout(tick, 60000 / bpm);
      };
      const umschalten = () => { laeuft = !laeuft; clearTimeout(timer); schlag = 0; if (laeuft) tick(); zeige(); };
      zeige();
      aufraeumen = () => clearTimeout(timer);
      modus = { unter: true, taste(t) {
        if (trainer && (t === "ArrowUp" || t === "ArrowDown")) {
          ziel = Math.max(bpm, Math.min(220, ziel + (t === "ArrowUp" ? 5 : -5))); zeige(); return true;
        }
        const d = { ArrowLeft: -5, ArrowRight: 5, ArrowDown: -1, ArrowUp: 1 }[t];
        if (d) { bpm = Math.max(40, Math.min(220, bpm + d)); ziel = Math.max(ziel, bpm); zeige(); return true; }
        if (t === "Enter" || t === " " || t === "p" || t === "P") { umschalten(); return true; }
        return false;
      } };
    }

    /* ---------------------------------------------------- Griffbrett-Trainer */
    async function griffbrett(mitBass) {
      const breite = Math.floor(innerWidth * 0.85), hoehe = Math.floor(innerHeight * 0.42);
      const canvas = el("canvas", { class: "spielfeld", width: breite, height: hoehe });
      const frage = el("div", { class: "punkte", style: "text-align:center;margin-bottom:2vh" });
      inhalt.replaceChildren(el("div", {}, frage, canvas));
      hilfe.textContent = mitBass ? "Spiel den Ton auf deinem Bass · OK nächste Aufgabe · STOP Zurück"
                                  : "Pfeile Fahren · OK Antworten · STOP Zurück";
      const g = canvas.getContext("2d");
      const s = { saite: 2, bund: 0, ziel: null, richtig: 0, versuche: 0, rueckmeldung: "" };
      const tonAn = (saite, bund) => TOENE[(SAITE_GRUNDTON[SAITEN[saite].name] + bund) % 12];
      const neueFrage = () => {
        const saite = Math.floor(Math.random() * 4), bund = Math.floor(Math.random() * BUENDE);
        s.ziel = { saite, name: tonAn(saite, bund) };
        frage.textContent = `Wo ist das ${s.ziel.name} auf der ${SAITEN[saite].name}-Saite?`;
      };
      const zeichne = () => {
        const rand = 40, abstand = (breite - rand * 2) / BUENDE, zeilen = (hoehe - 40) / 4;
        g.fillStyle = "#3b2a1a"; g.fillRect(0, 0, breite, hoehe);
        for (let b = 0; b <= BUENDE; b++) {
          const x = rand + b * abstand;
          g.fillStyle = b === 0 ? "#eee" : "#999"; g.fillRect(x - (b === 0 ? 3 : 1), 20, b === 0 ? 6 : 2, hoehe - 40);
          if ([3, 5, 7, 9].includes(b)) { g.fillStyle = "#c9b48a"; g.beginPath(); g.arc(x - abstand / 2, hoehe / 2, 6, 0, 7); g.fill(); }
          if (b === 12) { g.fillStyle = "#c9b48a"; [hoehe / 3, (hoehe * 2) / 3].forEach((y) => { g.beginPath(); g.arc(x - abstand / 2, y, 6, 0, 7); g.fill(); }); }
        }
        SAITEN.forEach((saite, i) => {
          const y = 20 + zeilen * (i + 0.5);
          g.fillStyle = "#ddd"; g.fillRect(rand, y - 1 - i * 0.6, breite - rand * 2, 2 + i * 1.2);
          g.fillStyle = "#fff"; g.font = "700 18px system-ui"; g.fillText(saite.name, 10, y + 6);
        });
        const x = s.bund === 0 ? rand - 18 : rand + (s.bund - 0.5) * abstand;
        const y = 20 + zeilen * (s.saite + 0.5);
        g.fillStyle = "#4f8dff"; g.beginPath(); g.arc(x, y, 16, 0, 7); g.fill();
        g.fillStyle = "#fff"; g.font = "700 14px system-ui"; g.textAlign = "center";
        g.fillText(tonAn(s.saite, s.bund), x, y + 5); g.textAlign = "start";
        punkte.textContent = `Richtig: ${s.richtig} von ${s.versuche}` + (s.rueckmeldung ? " · " + s.rueckmeldung : "");
      };
      const klinge = () => zupfe(SAITEN[s.saite].hz * 2 * Math.pow(2, s.bund / 12), 0.9, 0.18);
      neueFrage();
      zeichne();
      if (mitBass) {
        /* Antwort auf dem echten Bass: das Mikro erkennt den Ton */
        const stopp = await mikroHoeren((hz, ton_) => {
          if (!s.ziel) return;
          s.versuche++;
          if (tonPasst(hz, s.ziel.name)) {
            s.richtig++; s.rueckmeldung = `Richtig – ${ton_.name}! 🎉`; ton("sieg"); erfolg(api, "griffbrett", 1);
            if (s.richtig % 5 === 0) konfetti(box);
            neueFrage();
          } else {
            s.rueckmeldung = `Ich höre ${ton_.name} – gesucht ist ${s.ziel.name}`;
          }
          zeichne();
        });
        if (!stopp) {
          frage.textContent = "Kein Mikrofon gefunden – dafür braucht der Fernseh-Pi das USB-Mikrofon.";
          modus = { unter: true, taste: () => false };
          return;
        }
        aufraeumen = stopp;
        modus = { unter: true, taste(t) {
          if (t === "Enter" || t === " ") { neueFrage(); zeichne(); return true; }
          return false;
        } };
        return;
      }
      modus = { unter: true, taste(t) {
        const b = { ArrowLeft: [0, -1], ArrowRight: [0, 1], ArrowUp: [-1, 0], ArrowDown: [1, 0] }[t];
        if (b) {
          s.saite = Math.max(0, Math.min(3, s.saite + b[0]));
          s.bund = Math.max(0, Math.min(BUENDE, s.bund + b[1]));
          klinge(); zeichne(); return true;
        }
        if (t === "Enter" || t === " ") {
          s.versuche++;
          const treffer = s.saite === s.ziel.saite && tonAn(s.saite, s.bund) === s.ziel.name;
          if (treffer) { s.richtig++; s.rueckmeldung = "Super! 🎉"; ton("sieg"); erfolg(api, "griffbrett", 1); if (s.richtig % 5 === 0) konfetti(box); neueFrage(); }
          else { s.rueckmeldung = `Das ist ein ${tonAn(s.saite, s.bund)} auf der ${SAITEN[s.saite].name}-Saite`; ton("fehler"); }
          zeichne(); return true;
        }
        return false;
      } };
    }

    /* ---------------------------------------------------- Meine Songs */
    async function songs() {
      let liste = [], bibliotheken = [];
      try { const d = await api.hole("/api/bass"); liste = d.songs; bibliotheken = d.bibliotheken || []; } catch (_) { /* leer */ }
      const spalte = el("div", { style: "text-align:center;max-width:90vw" });
      inhalt.replaceChildren(spalte);
      const plex = bibliotheken.map((art) => ({ text: BIBLIOTHEKEN[art], aktion: async () => {
        try { const a = await api.sende("/api/bass/bibliothek", { art }); api.hinweis(a.meldung); } catch (e) { api.hinweis(e.message); }
      } }));
      if (!liste.length && plex.length) {
        spalte.append(el("p", { class: "punkte", text: "Videos und Backing Tracks" }));
        modus = menue(spalte, plex);
        modus.unter = true;
        return;
      }
      if (!liste.length) {
        spalte.append(el("p", { class: "punkte", text: "Noch keine Songs eingetragen." }),
          el("p", { class: "leise", text: "Mama oder Papa können Songs auf der Eltern-Seite hinzufügen (Video, Tabs, Backing Track)." }));
        modus = { unter: true, taste: () => false };
        return;
      }
      spalte.append(el("p", { class: "punkte", text: "Welcher Song?" }));
      modus = menue(spalte, plex.concat(liste.map((song) => ({ text: song.titel, aktion: () => songWahl(song) }))));
      modus.unter = true;
    }

    function songWahl(song) {
      const spalte = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text: song.titel }));
      inhalt.replaceChildren(spalte);
      modus = menue(spalte, song.arten.map((art) => ({ text: ARTEN[art], aktion: async () => {
        try { const a = await api.sende("/api/bass/oeffne", { nr: song.nr, art }); api.hinweis(a.meldung); }
        catch (e) { api.hinweis(e.message); }
      } })));
      modus.unter = true;
      modus.zurueck = songs;
    }

    /* ---------------------------------------------------- Stimmgerät (Mikrofon) */
    async function stimmgeraet(saitenInfo = "Bass: E · A · D · G") {
      const name = el("div", { class: "witz", style: "font-size:clamp(60px,10vw,140px)", text: "–" });
      const zeiger = el("div", { style: "height:24px;width:60vw;margin:3vh auto;background:#1d2636;border-radius:12px;position:relative" },
        el("div", { style: "position:absolute;left:50%;top:-6px;width:3px;height:36px;background:#fff" }));
      const punkt = el("div", { style: "position:absolute;top:2px;width:20px;height:20px;border-radius:50%;background:#4ccf8f;left:50%;transition:left .1s" });
      zeiger.append(punkt);
      const info = el("p", { class: "leise", style: "text-align:center" });
      inhalt.replaceChildren(el("div", { style: "text-align:center" }, el("p", { class: "leise", text: saitenInfo }), name, zeiger, info));
      hilfe.textContent = "Saite zupfen · OK Mithören an/aus · STOP Zurück";
      let strom;
      try {
        strom = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
      } catch (_) {
        name.textContent = "🎤?";
        info.textContent = "Kein Mikrofon gefunden. Dafür braucht der Fernseh-Pi ein USB-Mikrofon oder ein Audio-Interface.";
        modus = { unter: true, taste: () => false };
        return;
      }
      const a = ctx(), quelle = a.createMediaStreamSource(strom), analyse = a.createAnalyser();
      analyse.fftSize = 4096;
      quelle.connect(analyse);
      const puffer = new Float32Array(analyse.fftSize);
      let mithoeren = false, laeuft = true;
      const schleife = () => {
        if (!laeuft) return;
        analyse.getFloatTimeDomainData(puffer);
        const hz = tonhoehe(puffer, a.sampleRate);
        if (hz) {
          const t = naechsterTon(hz);
          name.textContent = t.name;
          punkt.style.left = `calc(50% + ${Math.max(-50, Math.min(50, t.cent))}% - 10px)`;
          punkt.style.background = Math.abs(t.cent) <= 5 ? "#4ccf8f" : "#ffc95a";
          info.textContent = `${hz.toFixed(1)} Hz · ${t.cent > 0 ? "+" : ""}${t.cent} Cent` + (mithoeren ? " · Mithören an" : "");
        }
        setTimeout(() => requestAnimationFrame(schleife), 80);
      };
      schleife();
      aufraeumen = () => { laeuft = false; quelle.disconnect(); strom.getTracks().forEach((s) => s.stop()); };
      modus = { unter: true, taste(t) {
        if (t === "Enter" || t === " ") {
          mithoeren = !mithoeren;
          if (mithoeren) quelle.connect(a.destination); else { quelle.disconnect(); quelle.connect(analyse); }
          return true;
        }
        return false;
      } };
    }

    /* ---------------------------------------------------- Rhythmus-Spiel */
    function rhythmus() {
      const bpm = 70, schlaege = 16, takt = 60000 / bpm;
      const anzeige = el("div", { class: "witz", text: "Hör zu: 4 Klicks vorweg – dann drück OK genau auf jeden Klick!" });
      const licht = el("div", { style: "width:20vh;height:20vh;border-radius:50%;margin:3vh auto;background:#233" });
      inhalt.replaceChildren(el("div", { style: "text-align:center" }, anzeige, licht));
      hilfe.textContent = "OK im Takt drücken · STOP Zurück";
      const start = performance.now() + 1500, treffer = [];
      let n = 0, timer = 0;
      const klickTimer = () => {
        const betont = n % 4 === 0;
        klick(betont);
        licht.style.background = n < 4 ? "#7fa8ff" : betont ? "#ff6b6b" : "#4ccf8f";
        setTimeout(() => { licht.style.background = "#233"; }, 90);
        n++;
        if (n < schlaege + 4) timer = setTimeout(klickTimer, start + n * takt - performance.now());
        else setTimeout(auswerten, takt);
      };
      timer = setTimeout(klickTimer, 1500);
      const auswerten = () => {
        const guete = Math.round(100 * treffer.filter((d) => d < 120).length / schlaege);
        anzeige.textContent = `${guete} % im Takt` + (guete >= 80 ? " – super! 🥁" : guete >= 50 ? " – gut, nochmal?" : " – übe weiter!");
        ton(guete >= 80 ? "sieg" : "ok");
        erfolg(api, "rhythmus", guete);
        if (guete >= 80) konfetti(box);
        modus = { unter: true, taste(t) { if (t === "Enter" || t === " ") { rhythmus(); return true; } return false; } };
      };
      aufraeumen = () => clearTimeout(timer);
      modus = { unter: true, taste(t) {
        if (t === "Enter" || t === " ") {
          const jetzt = performance.now(), i = Math.round((jetzt - start) / takt);
          if (i >= 4 && i < schlaege + 4) treffer[i - 4] = Math.min(treffer[i - 4] ?? 9999, Math.abs(jetzt - (start + i * takt)));
          return true;
        }
        return false;
      } };
    }

    /* ---------------------------------------------------- Gehörbildung */
    function gehoer() {
      const anzeige = el("div", { class: "witz" });
      const info = el("p", { class: "leise", style: "text-align:center" });
      inhalt.replaceChildren(el("div", { style: "text-align:center" }, anzeige, info));
      let richtig = 0, aufgabe = null;
      const neue = () => {
        if (Math.random() < 0.5) {
          const a = 41.2 * Math.pow(2, Math.floor(Math.random() * 12) / 12) * 2;
          const schritt = (Math.floor(Math.random() * 5) + 1) * (Math.random() < 0.5 ? -1 : 1);
          aufgabe = { art: "hoehe", a, b: a * Math.pow(2, schritt / 12), loesung: schritt > 0 ? "ArrowUp" : "ArrowDown" };
          anzeige.textContent = "Ist der zweite Ton höher (↑) oder tiefer (↓)?";
          zupfe(aufgabe.a, 0.8); setTimeout(() => zupfe(aufgabe.b, 0.8), 900);
        } else {
          const i = Math.floor(Math.random() * 4);
          aufgabe = { art: "saite", i, loesung: ["ArrowUp", "ArrowRight", "ArrowLeft", "ArrowDown"][i] };
          anzeige.textContent = "Welche leere Saite klingt? ↑ G · → D · ← A · ↓ E";
          zupfe(SAITEN[i].hz * 2, 1.4);
        }
        info.textContent = `Richtig: ${richtig} · OK = nochmal anhören`;
      };
      hilfe.textContent = "Pfeile Antworten · OK Nochmal hören · STOP Zurück";
      neue();
      modus = { unter: true, taste(t) {
        if (t === "Enter" || t === " ") {
          if (aufgabe.art === "hoehe") { zupfe(aufgabe.a, 0.8); setTimeout(() => zupfe(aufgabe.b, 0.8), 900); }
          else zupfe(SAITEN[aufgabe.i].hz * 2, 1.4);
          return true;
        }
        if (t.startsWith("Arrow")) {
          if (t === aufgabe.loesung) { richtig++; ton("sieg"); erfolg(api, "gehoer", 1); api.hinweis("Richtig! 👂"); setTimeout(neue, 700); }
          else { ton("fehler"); api.hinweis("Leider nicht – hör nochmal (OK)."); }
          return true;
        }
        return false;
      } };
    }

    /* ---------------------------------------------------- Nachspielen (Mikro) */
    async function nachspielen() {
      const anzeige = el("div", { class: "witz", text: "Hör gut zu – und spiel den Ton auf deinem Bass nach!" });
      const gehoert = el("div", { class: "punkte", style: "text-align:center;margin-top:3vh" });
      inhalt.replaceChildren(el("div", { style: "text-align:center" }, anzeige, gehoert));
      hilfe.textContent = "OK Ton nochmal · → nächster Ton · STOP Zurück";
      let ziel = null, richtig = 0;
      const neu = () => {
        const halbton = Math.floor(Math.random() * 15);              /* E bis G auf den tiefen Saiten */
        const hz = 41.2 * Math.pow(2, halbton / 12);
        ziel = { hz, name: TOENE[(4 + halbton) % 12] };
        zupfe(hz * 2, 1.6);
        gehoert.textContent = `Richtig: ${richtig}`;
      };
      const stopp = await mikroHoeren((hz, t) => {
        if (!ziel) return;
        if (tonPasst(hz, ziel.name)) {
          richtig++; ton("sieg"); erfolg(api, "gehoer", 1);
          api.hinweis(`Super – das war ${ziel.name}!`);
          ziel = null;
          setTimeout(neu, 1200);
        } else {
          gehoert.textContent = `Ich höre ${t.name} – probier weiter (OK = nochmal hören) · Richtig: ${richtig}`;
        }
      });
      if (!stopp) {
        anzeige.textContent = "Kein Mikrofon gefunden – dafür braucht der Fernseh-Pi das USB-Mikrofon.";
        modus = { unter: true, taste: () => false };
        return;
      }
      aufraeumen = stopp;
      neu();
      modus = { unter: true, taste(t) {
        if ((t === "Enter" || t === " ") && ziel) { zupfe(ziel.hz * 2, 1.6); return true; }
        if (t === "ArrowRight") { neu(); return true; }
        return false;
      } };
    }

    /* ---------------------------------------------------- Tabs lesen */
    function tabsLesen() {
      const block = el("pre", { style: "font-size:clamp(20px,2.6vw,38px);background:#0e1522;padding:24px 34px;border-radius:16px;text-align:left;line-height:1.4" });
      const frage = el("div", { class: "punkte", style: "text-align:center;margin-bottom:2vh" });
      const wahl = el("div", { class: "knopfreihe" });
      inhalt.replaceChildren(el("div", { style: "text-align:center" }, frage, block, wahl));
      hilfe.textContent = "← → Antwort wählen · OK · STOP Zurück";
      let richtig = 0, antworten = [], pos = 0, loesung = 0;
      const neue = () => {
        const saite = Math.floor(Math.random() * 4), bund = Math.floor(Math.random() * 8);
        const zeilen = SAITEN.map((s, i) => `${s.name}|${"-".repeat(4)}${i === saite ? String(bund).padEnd(2, "-") : "--"}${"-".repeat(6)}|`);
        block.textContent = zeilen.join("\n");
        const tonName = TOENE[(SAITE_GRUNDTON[SAITEN[saite].name] + bund) % 12];
        frage.textContent = `Welcher Ton wird hier gespielt? (Richtig: ${richtig})`;
        const falsch = TOENE.filter((t) => t !== tonName).sort(() => Math.random() - 0.5).slice(0, 3);
        antworten = [tonName, ...falsch].sort(() => Math.random() - 0.5);
        loesung = antworten.indexOf(tonName);
        pos = 0;
        zeige();
        aufgabe = { saite, bund };
      };
      let aufgabe = null;
      const zeige = () => wahl.replaceChildren(...antworten.map((a, i) => el("span", { class: "knopf" + (i === pos ? " gewaehlt" : ""), text: a })));
      neue();
      modus = { unter: true, taste(t) {
        if (t === "ArrowLeft" || t === "ArrowRight") { pos = (pos + (t === "ArrowLeft" ? 3 : 1)) % 4; zeige(); return true; }
        if (t === "Enter" || t === " ") {
          zupfe(SAITEN[aufgabe.saite].hz * 2 * Math.pow(2, aufgabe.bund / 12), 0.9, 0.18);
          if (pos === loesung) { richtig++; ton("sieg"); erfolg(api, "griffbrett", 1); setTimeout(neue, 800); }
          else { ton("fehler"); api.hinweis(`Das wäre ${antworten[pos]} – schau auf die Saite und den Bund.`); }
          return true;
        }
        return false;
      } };
    }

    /* ---------------------------------------------------- Übungs-Tagebuch */
    async function tagebuch() {
      let d = { tagebuch: { tage: [], serie: 0, gesamt_min: 0 } };
      try { d = await api.hole("/api/bass"); } catch (_) { /* leer */ }
      const t = d.tagebuch;
      const hoechst = Math.max(15, ...t.tage.map((x) => x.minuten));
      const balken = el("div", { style: "display:flex;gap:10px;align-items:flex-end;height:30vh;justify-content:center" },
        ...t.tage.map((x) => el("div", { style: "text-align:center" },
          el("div", { style: `width:44px;height:${Math.max(4, 28 * x.minuten / hoechst)}vh;background:${x.minuten >= 5 ? "#4ccf8f" : "#2a3550"};border-radius:8px 8px 0 0` }),
          el("div", { class: "leise", text: new Date(x.datum).toLocaleDateString("de-DE", { weekday: "short" }) }))));
      inhalt.replaceChildren(el("div", { style: "text-align:center" },
        el("p", { class: "punkte", text: t.serie ? `🔥 ${t.serie} ${t.serie === 1 ? "Tag" : "Tage"} hintereinander geübt!` : "Heute schon geübt? Ab 5 Minuten zählt der Tag." }),
        balken, el("p", { class: "leise", text: `Insgesamt ${t.gesamt_min} Minuten Bass geübt · Sticker gibt es für 3 und 7 Tage am Stück` })));
      hilfe.textContent = "STOP Zurück";
      modus = { unter: true, taste: () => false };
    }

    hauptmenue();
    return {
      taste(t) {
        if (modus?.taste(t)) return true;
        if ((t === "Escape" || t === "Backspace") && modus?.unter) {
          (modus.zurueck || standardZurueck || hauptmenue)();
          return true;
        }
        return false;
      },
      schliesse() { stopp(); },
    };
  },
};
