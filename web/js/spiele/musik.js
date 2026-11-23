/* FernsehFranzi 3.5 - Musik-Akademie: Gitarre, Keyboard, Singen, Song-Suche (ultimate-guitar.com).
 * Die Bass-Übungen bleiben in bass.js; dieses Modul bekommt von dort den Rahmen (k):
 *   k.inhalt, k.hilfe, k.modus(m), k.aufraeumen(fn), k.zurueck(), k.api, k.erfolg(art, wert)
 * Pfeile bleiben Navigation; OK spielt/wählt; STOP geht eine Ebene zurück. */
import { el, franzi } from "../gemeinsam.js";
import { ton, konfetti } from "./kern.js";
import { ctx, zupfe, tonhoehe, naechsterTon, mikroHoeren, tonPasst } from "./bass.js";
import { stimmSpur, centZu, NAH_CENT } from "./stimme.js";

const TOENE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "H"];
const hz = (midi) => 440 * Math.pow(2, (midi - 69) / 12);
const tonName = (midi) => TOENE[((midi % 12) + 12) % 12];

/* Weicher Klavier-/Gitarrenton (Dreieck, abklingend) */
function spiele(f, dauer = 1.2, laut = 0.22, art = "triangle", verzoegerung = 0) {
  const a = ctx(), t = a.currentTime + verzoegerung;
  const o = a.createOscillator(), g = a.createGain();
  o.type = art; o.frequency.value = f;
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(laut, t + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dauer);
  o.connect(g).connect(a.destination);
  o.start(t); o.stop(t + dauer + 0.05);
}

/* Fortlaufend die gesungene/gespielte Tonhöhe (Hz oder null) - für Singen. Rückgabe: Stopp-Funktion oder null. */
async function mikroStrom(beiHz) {
  let strom;
  try {
    strom = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
  } catch (_) { return null; }
  const a = ctx(), quelle = a.createMediaStreamSource(strom), analyse = a.createAnalyser();
  analyse.fftSize = 4096;
  quelle.connect(analyse);
  const puffer = new Float32Array(analyse.fftSize);
  let laeuft = true;
  const schleife = () => {
    if (!laeuft) return;
    analyse.getFloatTimeDomainData(puffer);
    beiHz(tonhoehe(puffer, a.sampleRate));
    setTimeout(schleife, 80);
  };
  schleife();
  return () => { laeuft = false; quelle.disconnect(); strom.getTracks().forEach((s) => s.stop()); };
}

function keinMikro(k) {
  k.inhalt.replaceChildren(el("div", { class: "seite-leer" }, franzi("staunen", "franzi-leer"),
    el("div", { text: "Kein Mikrofon gefunden – dafür braucht der Fernseher das USB-Mikrofon." })));
  k.modus({ unter: true, taste: () => false });
}

/* ================================================================== Gitarre */
/* Griffbilder: Bünde je Saite von tief E bis hoch e (-1 = nicht spielen, 0 = leer) */
const AKKORDE = {
  "C": [-1, 3, 2, 0, 1, 0], "D": [-1, -1, 0, 2, 3, 2], "E": [0, 2, 2, 1, 0, 0], "G": [3, 2, 0, 0, 0, 3],
  "A": [-1, 0, 2, 2, 2, 0], "Am": [-1, 0, 2, 2, 1, 0], "Em": [0, 2, 2, 0, 0, 0], "Dm": [-1, -1, 0, 2, 3, 1],
  "F": [1, 3, 3, 2, 1, 1], "D7": [-1, -1, 0, 2, 1, 2], "G7": [3, 2, 0, 0, 0, 1], "C7": [-1, 3, 2, 3, 1, 0],
};
const GITARRE_LEER = [40, 45, 50, 55, 59, 64];          /* E2 A2 D3 G3 H3 E4 (MIDI) */

function schlage(akkord) {
  AKKORDE[akkord].forEach((bund, saite) => {
    if (bund >= 0) zupfe(hz(GITARRE_LEER[saite] + bund) , 1.8, 0.12);
  });
}

function griffbild(akkord) {
  const g = AKKORDE[akkord];
  const bundMax = Math.max(4, ...g);
  const svg = [`<svg viewBox="0 0 220 ${60 + bundMax * 40}" class="griffbild" xmlns="http://www.w3.org/2000/svg">`];
  for (let s = 0; s < 6; s++) svg.push(`<line x1="${30 + s * 32}" y1="40" x2="${30 + s * 32}" y2="${40 + bundMax * 40}" stroke="#9ba8bb" stroke-width="${3 - s * 0.3}"/>`);
  for (let b = 0; b <= bundMax; b++) svg.push(`<line x1="30" y1="${40 + b * 40}" x2="190" y2="${40 + b * 40}" stroke="#9ba8bb" stroke-width="${b === 0 ? 7 : 2}"/>`);
  g.forEach((bund, s) => {
    const x = 30 + s * 32;
    if (bund < 0) svg.push(`<text x="${x}" y="28" fill="#ff6b6b" font-size="22" text-anchor="middle">×</text>`);
    else if (bund === 0) svg.push(`<circle cx="${x}" cy="20" r="8" fill="none" stroke="#4ccf8f" stroke-width="3"/>`);
    else svg.push(`<circle cx="${x}" cy="${20 + bund * 40}" r="13" fill="#7fa8ff"/>`);
  });
  svg.push("</svg>");
  const box = el("div", { class: "griffbild-box" });
  box.innerHTML = svg.join("");                              /* eigener, fester Inhalt - keine fremden Daten */
  return box;
}

export function gitarre(k) {
  k.menue("🎸 Gitarre", [
    { text: "🎤 Stimmgerät (E A D G H E)", aktion: () => k.stimmgeraet("Gitarre: E · A · D · G · H · E (von oben)") },
    { text: "🖐️ Akkorde", aktion: () => akkorde(k) },
    { text: "🔁 Akkordwechsel-Trainer", aktion: () => wechsel(k) },
  ]);
}

function akkorde(k) {
  const namen = Object.keys(AKKORDE);
  let i = 0;
  const zeige = () => {
    k.inhalt.replaceChildren(el("div", { class: "akkord-ansicht" },
      el("div", { class: "akkord-name", text: namen[i] }), griffbild(namen[i]),
      el("div", { class: "akkord-leiste" }, ...namen.map((n, j) => el("span", { class: j === i ? "an" : "", text: n })))));
  };
  k.hilfe.textContent = "← → Akkord · OK anschlagen · STOP zurück";
  zeige(); schlage(namen[i]);
  k.modus({ unter: true, zurueck: () => gitarre(k), taste(t) {
    if (t === "ArrowLeft" || t === "ArrowRight") { i = (i + (t === "ArrowLeft" ? -1 : 1) + namen.length) % namen.length; zeige(); schlage(namen[i]); return true; }
    if (t === "Enter" || t === " ") { schlage(namen[i]); return true; }
    return false;
  } });
}

function wechsel(k) {
  const paare = [["C", "G"], ["G", "D"], ["Am", "Em"], ["C", "Am"], ["D", "A"], ["Em", "C"], ["G", "Em"], ["A", "D"]];
  let p = 0, zaehler = 0, laeuft = false, ende = 0, timer = 0, best = 0;
  const anzeige = el("div", { class: "akkord-ansicht" });
  const zeige = () => {
    const [a, b] = paare[p];
    const rest = laeuft ? Math.max(0, Math.ceil((ende - Date.now()) / 1000)) : 60;
    anzeige.replaceChildren(el("div", { class: "akkord-paar" }, el("div", {}, el("div", { class: "akkord-name", text: a }), griffbild(a)),
      el("div", { class: "akkord-pfeil", text: "↔" }), el("div", {}, el("div", { class: "akkord-name", text: b }), griffbild(b))),
      el("div", { class: "punkte", text: laeuft ? `⏱ ${rest} s · Wechsel: ${zaehler}` : `Bestwert: ${best} Wechsel pro Minute` }));
  };
  k.inhalt.replaceChildren(anzeige);
  k.hilfe.textContent = "← → anderes Paar · OK Start, dann bei jedem Wechsel OK · STOP zurück";
  zeige();
  const stopp = () => { clearInterval(timer); laeuft = false; };
  k.aufraeumen(stopp);
  k.modus({ unter: true, zurueck: () => { stopp(); gitarre(k); }, taste(t) {
    if (!laeuft && (t === "ArrowLeft" || t === "ArrowRight")) { p = (p + (t === "ArrowLeft" ? -1 : 1) + paare.length) % paare.length; zeige(); return true; }
    if (t === "Enter" || t === " ") {
      if (!laeuft) {
        laeuft = true; zaehler = 0; ende = Date.now() + 60000;
        timer = setInterval(() => {
          if (Date.now() >= ende) { stopp(); best = Math.max(best, zaehler); ton("sieg"); if (zaehler >= 30) konfetti(document.body); }
          zeige();
        }, 250);
      } else { zaehler++; ton("bewegen"); }
      zeige();
      return true;
    }
    return false;
  } });
}

/* ================================================================== Keyboard */
const AKKORDE_KLAVIER = { "C": [60, 64, 67], "F": [65, 69, 72], "G": [67, 71, 74], "Am": [69, 72, 76], "Dm": [62, 65, 69],
                          "Em": [64, 67, 71], "D": [62, 66, 69], "A": [69, 73, 76] };
const TIEF = 60, HOCH = 83;                                  /* C4 bis H5: zwei Oktaven */

function klaviatur(markiert, gewaehlt) {
  const weisse = [], schwarze = [];
  let x = 0;
  for (let m = TIEF; m <= HOCH; m++) {
    const schwarz = [1, 3, 6, 8, 10].includes(m % 12);
    const klasse = (markiert.includes(m) ? " an" : "") + (m === gewaehlt ? " gewaehlt" : "");
    if (schwarz) schwarze.push(el("div", { class: "taste-schwarz" + klasse, style: `left:calc(${x} * var(--weiss) - var(--weiss) * .3)` }));
    else { weisse.push(el("div", { class: "taste-weiss" + klasse }, el("small", { text: m % 12 === 0 ? "C" + (Math.floor(m / 12) - 1) : "" }))); x++; }
  }
  return el("div", { class: "klaviatur", style: `--weiss:${100 / x}%` }, ...weisse, ...schwarze);
}

export function keyboard(k) {
  k.menue("🎹 Keyboard", [
    { text: "🎹 Frei spielen", aktion: () => freiSpielen(k) },
    { text: "🎶 Akkorde zeigen", aktion: () => klavierAkkorde(k) },
    { text: "🎤 Nachspielen (mit Mikro)", aktion: () => klavierNachspielen(k) },
  ]);
}

function freiSpielen(k) {
  let m = 60;
  const zeige = () => k.inhalt.replaceChildren(el("div", { class: "klavier-ansicht" },
    el("div", { class: "akkord-name", text: tonName(m) }), klaviatur([], m)));
  k.hilfe.textContent = "← → Taste · ↑ ↓ Oktave · OK spielen · STOP zurück";
  zeige();
  k.modus({ unter: true, zurueck: () => keyboard(k), taste(t) {
    if (t === "ArrowLeft") { m = Math.max(TIEF, m - 1); zeige(); spiele(hz(m), 0.6); return true; }
    if (t === "ArrowRight") { m = Math.min(HOCH, m + 1); zeige(); spiele(hz(m), 0.6); return true; }
    if (t === "ArrowUp") { m = Math.min(HOCH, m + 12); zeige(); return true; }
    if (t === "ArrowDown") { m = Math.max(TIEF, m - 12); zeige(); return true; }
    if (t === "Enter" || t === " ") { spiele(hz(m), 1.4); return true; }
    return false;
  } });
}

function klavierAkkorde(k) {
  const namen = Object.keys(AKKORDE_KLAVIER);
  let i = 0;
  const klinge = () => AKKORDE_KLAVIER[namen[i]].forEach((m, j) => spiele(hz(m), 1.6, 0.16, "triangle", j * 0.04));
  const zeige = () => k.inhalt.replaceChildren(el("div", { class: "klavier-ansicht" },
    el("div", { class: "akkord-name", text: namen[i] }),
    el("div", { class: "leise", text: AKKORDE_KLAVIER[namen[i]].map(tonName).join(" – ") }),
    klaviatur(AKKORDE_KLAVIER[namen[i]], -1)));
  k.hilfe.textContent = "← → Akkord · OK spielen · STOP zurück";
  zeige(); klinge();
  k.modus({ unter: true, zurueck: () => keyboard(k), taste(t) {
    if (t === "ArrowLeft" || t === "ArrowRight") { i = (i + (t === "ArrowLeft" ? -1 : 1) + namen.length) % namen.length; zeige(); klinge(); return true; }
    if (t === "Enter" || t === " ") { klinge(); return true; }
    return false;
  } });
}

async function klavierNachspielen(k) {
  let ziel = null, richtig = 0;
  const anzeige = el("div", { class: "klavier-ansicht" });
  const neu = () => {
    ziel = TIEF + Math.floor(Math.random() * 13);           /* C4 bis C5 */
    anzeige.replaceChildren(el("div", { class: "punkte", text: `Hör zu und spiel den Ton nach! Richtig: ${richtig}` }),
      el("div", { class: "akkord-name", text: "?" }), klaviatur([], -1));
    spiele(hz(ziel), 1.4);
  };
  k.inhalt.replaceChildren(anzeige);
  k.hilfe.textContent = "OK nochmal hören · → neuer Ton · STOP zurück";
  const stopp = await mikroHoeren((f, t) => {
    if (ziel === null) return;
    if (tonPasst(f, tonName(ziel))) {
      richtig++; ton("sieg"); k.erfolg("gehoer", 1);
      anzeige.replaceChildren(el("div", { class: "akkord-name", text: `${tonName(ziel)} ✔` }), klaviatur([ziel], -1));
      ziel = null;
      setTimeout(neu, 1500);
    } else {
      anzeige.firstChild.textContent = `Ich höre ${t.name} – probier weiter · Richtig: ${richtig}`;
    }
  });
  if (!stopp) return keinMikro(k);
  k.aufraeumen(stopp);
  neu();
  k.modus({ unter: true, zurueck: () => keyboard(k), taste(t) {
    if ((t === "Enter" || t === " ") && ziel !== null) { spiele(hz(ziel), 1.4); return true; }
    if (t === "ArrowRight") { neu(); return true; }
    return false;
  } });
}

/* ================================================================== Singen */
export function singen(k) {
  k.menue("🎤 Singen", [
    { text: "🎯 Ton treffen", aktion: () => tonTreffen(k) },
    { text: "🎵 Tonleiter singen", aktion: () => tonTreffen(k, true) },
  ]);
}

async function tonTreffen(k, leiter = false) {
  /* 6.0: Die eigene Stimme läuft als Linie über den Bildschirm, das grüne Band ist der Zielton.
     Wer den Ton eine knappe Sekunde hält, füllt den Ring und bekommt einen Stern. */
  const LEITER = [60, 62, 64, 65, 67, 69, 71, 72];
  const HALTEN_MS = 900;
  let ziel = 0, schritt = 0, getroffenSeit = 0, richtig = 0;
  const name = el("div", { class: "akkord-name sing-ton" });
  const spur = stimmSpur({ breite: 760, hoehe: 320 });
  const saeule = el("div", { class: "sing-saeule" }, spur.knoten);
  const sterne = el("div", { class: "sing-sterne" });
  const info = el("div", { class: "punkte" });
  k.inhalt.replaceChildren(el("div", { class: "sing-ansicht" }, el("div", { class: "sing-kopf" }, name, sterne), saeule, info));
  k.hilfe.textContent = "Sing den Ton nach · OK nochmal hören · → neuer Ton · STOP zurück";
  const sterneZeigen = () => {
    if (leiter) sterne.replaceChildren(...LEITER.map((_, i) => el("span", { class: i < schritt % LEITER.length ? "an" : "", text: "⭐" })));
    else sterne.textContent = richtig ? `⭐ ${richtig}` : "";
  };
  const neu = () => {
    ziel = leiter ? LEITER[schritt % LEITER.length] : 57 + Math.floor(Math.random() * 13);   /* A3 bis A4: gut zu singen */
    name.textContent = tonName(ziel);
    name.classList.remove("geschafft");
    info.textContent = leiter ? `Ton ${schritt % LEITER.length + 1} von ${LEITER.length} – erst zuhören, dann singen` : "Erst zuhören, dann singen";
    getroffenSeit = 0;
    spur.leeren();
    sterneZeigen();
    spiele(hz(ziel), 1.6, 0.2, "sine");
  };
  const stopp = await mikroStrom((f) => {
    if (!ziel) return;
    if (!f) { spur.zeige(null); spur.halten(0); getroffenSeit = 0; return; }
    const cent = centZu(f, hz(ziel));
    spur.zeige(cent);
    if (Math.abs(cent) <= NAH_CENT) {
      getroffenSeit = getroffenSeit || Date.now();
      const anteil = (Date.now() - getroffenSeit) / HALTEN_MS;
      spur.halten(anteil);
      info.textContent = "Super – halten!";
      if (anteil >= 1) {
        richtig++; schritt++; ton("ok"); k.erfolg("gehoer", 1);
        ziel = 0;
        name.classList.add("geschafft");
        info.textContent = "⭐ Getroffen!";
        sterneZeigen();
        if (leiter && schritt % LEITER.length === 0) { konfetti(document.body); ton("sieg"); info.textContent = "🏆 Die ganze Tonleiter!"; }
        setTimeout(neu, 1200);
      }
    } else {
      getroffenSeit = 0; spur.halten(0);
      info.textContent = cent > 0 ? "⬇ etwas tiefer" : "⬆ etwas höher";
    }
  });
  if (!stopp) return keinMikro(k);
  k.aufraeumen(stopp);
  neu();
  k.modus({ unter: true, zurueck: () => singen(k), taste(t) {
    if ((t === "Enter" || t === " ") && ziel) { spiele(hz(ziel), 1.6, 0.2, "sine"); return true; }
    if (t === "ArrowRight") { schritt++; neu(); return true; }
    return false;
  } });
}

/* ================================================================== Song-Suche (ultimate-guitar.com) */
const TASTATUR = ["QWERTZUIOPÜ", "ASDFGHJKLÖÄ", "YXCVBNM-' ⌫", "1234567890"];

export function songSuche(k) {
  let text = "", zeile = 0, spalte = 0;
  const feld = el("div", { class: "such-feld" });
  const tasten = el("div", { class: "such-tastatur" });
  const zeige = () => {
    feld.textContent = text || "Song oder Künstler …";
    feld.classList.toggle("leer", !text);
    const reihen = TASTATUR.map((r, z) => el("div", { class: "such-reihe" }, ...[...r].map((c, s) =>
      el("span", { class: z === zeile && s === spalte ? "gewaehlt" : "", text: c === " " ? "␣" : c }))));
    reihen.push(el("div", { class: "such-reihe" }, el("span", { class: "breit" + (zeile === TASTATUR.length ? " gewaehlt" : ""), text: "🔎 Suchen" })));
    tasten.replaceChildren(...reihen);
  };
  k.inhalt.replaceChildren(el("div", { class: "such-ansicht" },
    el("p", { class: "leise", text: "Akkorde und Tabs für Gitarre, Bass, Keyboard und Gesang – auf ultimate-guitar.com" }), feld, tasten));
  k.hilfe.textContent = "Pfeile Buchstabe · OK tippen · „Suchen“ öffnet die Ergebnisse · STOP zurück";
  zeige();
  const tippe = async () => {
    if (zeile === TASTATUR.length) {
      if (text.trim().length < 2) { k.api.hinweis("Bitte mindestens zwei Buchstaben."); return; }
      try { k.api.hinweis((await k.api.sende("/api/musik/suche", { text: text.trim() })).meldung); }
      catch (fehler) { k.api.hinweis(fehler.message); }
      return;
    }
    const c = TASTATUR[zeile][spalte];
    if (c === "⌫") text = text.slice(0, -1); else if (text.length < 40) text += c.toLowerCase();
    zeige();
  };
  k.modus({ unter: true, zurueck: k.zurueck, taste(t) {
    if (t === "ArrowUp") { zeile = Math.max(0, zeile - 1); spalte = Math.min(spalte, TASTATUR[zeile].length - 1); zeige(); return true; }
    if (t === "ArrowDown") { zeile = Math.min(TASTATUR.length, zeile + 1); if (zeile < TASTATUR.length) spalte = Math.min(spalte, TASTATUR[zeile].length - 1); zeige(); return true; }
    if (t === "ArrowLeft" && zeile < TASTATUR.length) { spalte = (spalte + TASTATUR[zeile].length - 1) % TASTATUR[zeile].length; zeige(); return true; }
    if (t === "ArrowRight" && zeile < TASTATUR.length) { spalte = (spalte + 1) % TASTATUR[zeile].length; zeige(); return true; }
    if (t === "Enter" || t === " ") { tippe(); return true; }
    if (t === "Backspace") { text = text.slice(0, -1); zeige(); return true; }
    if (/^[a-zäöüß0-9]$/i.test(t)) { text += t.toLowerCase(); zeige(); return true; }   /* echte Tastatur geht auch */
    return false;
  } });
}

/* ================================================================== Aufnehmen (4.0) */
/* Sich selbst aufnehmen und anhören (Bass, Stimme, Keyboard). Die Aufnahmen bleiben nur hier im Fernseher-Browser
   (höchstens drei, je höchstens 2 Minuten) und werden nirgendwohin geschickt. */
const AUFNAHMEN = [];
export async function aufnehmen(k) {
  let strom;
  try {
    strom = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
  } catch (_) { return keinMikro(k); }
  const a = ctx(), quelle = a.createMediaStreamSource(strom), analyse = a.createAnalyser();
  analyse.fftSize = 1024;
  quelle.connect(analyse);
  const puffer = new Float32Array(analyse.fftSize);
  let rec = null, teile = [], start = 0, wahl = Math.max(0, AUFNAHMEN.length - 1), abspielen = null, laeuft = true;
  const pegel = el("div", { class: "rec-pegel" }, el("i"));
  const status = el("div", { class: "akkord-name rec-status" });
  const liste = el("div", { class: "akkord-leiste" });
  k.inhalt.replaceChildren(el("div", { class: "akkord-ansicht" }, status, pegel, liste,
    el("p", { class: "leise", text: "Tipp: Stell dich nah ans Mikrofon. Die Aufnahmen bleiben nur hier am Fernseher." })));
  k.hilfe.textContent = "OK Aufnahme starten/stoppen · PLAY anhören · ← → Aufnahme wählen · STOP zurück";
  const zeige = () => {
    status.textContent = rec ? `🔴 ${Math.floor((Date.now() - start) / 1000)} s` : AUFNAHMEN.length ? "🎙️ Bereit" : "🎙️ Drück OK";
    liste.replaceChildren(...AUFNAHMEN.map((x, i) => el("span", { class: i === wahl ? "an" : "", text: `${x.name} · ${x.dauer} s` })));
  };
  const schleife = () => {
    if (!laeuft) return;
    analyse.getFloatTimeDomainData(puffer);
    const spitze = puffer.reduce((m, v) => Math.max(m, Math.abs(v)), 0);
    pegel.firstChild.style.width = `${Math.min(100, spitze * 140)}%`;
    pegel.classList.toggle("laut", spitze > 0.9);
    if (rec && Date.now() - start > 120000) stopp();
    zeige();
    setTimeout(schleife, 100);
  };
  function starte() {
    teile = [];
    rec = new MediaRecorder(strom);
    rec.ondataavailable = (e) => { if (e.data.size) teile.push(e.data); };
    rec.onstop = () => {
      const dauer = Math.round((Date.now() - start) / 1000);
      AUFNAHMEN.push({ name: `Aufnahme ${AUFNAHMEN.length ? Number(AUFNAHMEN[AUFNAHMEN.length - 1].name.split(" ")[1]) + 1 : 1}`, dauer,
                       url: URL.createObjectURL(new Blob(teile, { type: rec.mimeType || "audio/webm" })) });
      while (AUFNAHMEN.length > 3) URL.revokeObjectURL(AUFNAHMEN.shift().url);
      wahl = AUFNAHMEN.length - 1;
      rec = null;
      ton("ok");
      zeige();
    };
    start = Date.now();
    rec.start();
    ton("bewegen");
  }
  function stopp() { if (rec && rec.state === "recording") rec.stop(); }
  function hoeren() {
    const x = AUFNAHMEN[wahl];
    if (!x) return;
    abspielen?.pause();
    abspielen = new Audio(x.url);
    abspielen.play().catch(() => k.api.hinweis("Abspielen geht gerade nicht."));
  }
  schleife();
  k.aufraeumen(() => { laeuft = false; stopp(); abspielen?.pause(); quelle.disconnect(); strom.getTracks().forEach((t) => t.stop()); });
  k.modus({ unter: true, zurueck: k.zurueck, taste(t) {
    if (t === "Enter" || t === " ") { if (rec) stopp(); else { abspielen?.pause(); starte(); } return true; }
    if (t === "MediaPlay" || t === "MediaPlayPause" || t === "p" || t === "P") { if (!rec) hoeren(); return true; }
    if (t === "ArrowLeft" || t === "ArrowRight") { wahl = Math.max(0, Math.min(AUFNAHMEN.length - 1, wahl + (t === "ArrowLeft" ? -1 : 1))); zeige(); return true; }
    return false;
  } });
}
