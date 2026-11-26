/* FernsehFranzi 3.0 - gemeinsame Helfer (Startseite und Eltern-Seite im Heimnetz). */

const TOKEN = document.querySelector('meta[name="ff-token"]')?.content || "";
let elternToken = "";

export function setzeElternToken(token) { elternToken = token || ""; }
export function hatElternToken() { return Boolean(elternToken); }
export function leseElternToken() { return elternToken; }

function kopf(json) {
  const k = {};
  if (json) k["Content-Type"] = "application/json";
  if (TOKEN && TOKEN !== "__FF_" + "TOKEN__") k["X-FF-Token"] = TOKEN;
  if (elternToken) k["X-FF-Eltern"] = elternToken;
  return k;
}

/** GET als JSON. Wirft bei Fehlern mit .status und .daten. */
export async function hole(pfad) {
  const antwort = await fetch(pfad, { headers: kopf(false), cache: "no-store" });
  return auswerten(antwort);
}

/** POST mit JSON-Inhalt. */
export async function sende(pfad, daten) {
  const antwort = await fetch(pfad, { method: "POST", headers: kopf(true), body: JSON.stringify(daten || {}) });
  return auswerten(antwort);
}

async function auswerten(antwort) {
  let daten = {};
  try { daten = await antwort.json(); } catch (_) { /* leer */ }
  if (!antwort.ok) {
    const fehler = new Error(daten.fehler || daten.meldung || "Fehler " + antwort.status);
    fehler.status = antwort.status;
    fehler.daten = daten;
    throw fehler;
  }
  return daten;
}

export function el(tag, eigenschaften = {}, ...kinder) {
  const knoten = document.createElement(tag);
  for (const [name, wert] of Object.entries(eigenschaften)) {
    if (name === "class") knoten.className = wert;
    else if (name === "text") knoten.textContent = wert;
    else if (name.startsWith("on")) knoten.addEventListener(name.slice(2), wert);
    else if (wert !== false && wert !== null && wert !== undefined) knoten.setAttribute(name, wert === true ? "" : wert);
  }
  for (const kind of kinder) if (kind !== null && kind !== undefined) knoten.append(kind);
  return knoten;
}

export const pause = (ms) => new Promise((ok) => setTimeout(ok, ms));
/** 6.9.15: Animations-Stufe aus dem Elternbereich - "aus" (still), "sparsam" (Pi 3, Vorgabe), "hoch" (Pi 4/5, darf den Pi 3 fordern) */
export function stufe() {
  const s = (typeof document !== "undefined" && document.documentElement.dataset.animation) || "sparsam";
  return s === "aus" || s === "hoch" ? s : "sparsam";
}

/* 6.0: 3D-Bilder statt Emojis (Fluent Emoji 3D von Microsoft, MIT-Lizenz, web/icons/LIZENZ-fluentui-emoji.txt).
   bild(emoji) liefert ein <img> aus web/icons/, wenn es das Bild gibt, sonst das Emoji als Text. */
const ICONS = new Set(["1f302","1f310","1f319","1f31f","1f321","1f324","1f326","1f327","1f328","1f32b","1f333","1f389","1f392","1f393","1f39f","1f3a4","1f3a8","1f3ac","1f3ae","1f3af","1f3b5","1f3b8","1f3b9","1f3bc","1f3c5","1f3c6","1f3e0","1f3eb","1f40d","1f43e","1f44d","1f44f","1f455","1f48c","1f4cc","1f4cd","1f4d6","1f4d8","1f4da","1f4dd","1f4e3","1f4e8","1f4f0","1f4f1","1f4fa","1f504","1f512","1f514","1f534","1f550","1f579","1f5bc","1f5d3","1f604","1f622","1f634","1f680","1f6ab","1f6b2","1f6e0","1f91d","1f941","1f947","1f973","1f9e0","1f9e9","23f0","23f3","25b6","2600","2601","2614","2699","26bd","26c5","26c8","2709","2728","2744","274c","2b50"]);
const ICON_CODE = (emoji) => [...String(emoji || "")].filter((z) => z !== "️").map((z) => z.codePointAt(0).toString(16)).join("-");
export function hatBild(emoji) { return ICONS.has(ICON_CODE(emoji)); }
export function bild(emoji, klasse = "icon") {
  const code = ICON_CODE(emoji);
  return ICONS.has(code) ? el("img", { class: klasse, src: `/icons/${code}.png`, alt: "", draggable: "false" })
                         : el("span", { class: klasse + " als-text", text: emoji || "" });
}
/** Text, der mit einem Emoji beginnt („🏫 Schule“) -> [Bild, " Schule"] */
const VORNE = /^(\p{Extended_Pictographic}️?)\s*(.*)$/su;
export function mitBild(text, klasse = "icon") {
  const m = VORNE.exec(String(text || ""));
  return m && hatBild(m[1]) ? [bild(m[1], klasse), document.createTextNode(" " + m[2])] : [document.createTextNode(String(text || ""))];
}

/* 6.0: Maskottchen „Franzi“ - ein kleiner Fernseher mit Gesicht. Stimmungen: froh (winkt), jubel (Arme hoch), staunen,
 * schlaf. 6.9.43: neu gezeichnet - Franzi wird aus Ebenen zusammengesetzt (Arme, Körper je Farbe, Augen,
 * Mund; 512 × 512 auf der Franzi-Schablone, web/bilder/franzi/). Bewegt wird nur über CSS (transform/opacity, Pi 3). */
const FRANZI_PFAD = "/bilder/franzi/";
const FRANZI_TEILE = {
  froh: { arme: ["rechts-unten", "links-unten"], augen: "offen", mund: "laecheln" },          /* 6.9.45: Ruhehaltung, Arme unten */
  hallo: { arme: ["links-unten"], winken: "rechts-oben", augen: "offen", mund: "laecheln" },   /* begrüßt kurz und winkt */
  jubel: { arme: ["rechts-oben", "links-oben"], augen: "bogen", mund: "lachen" },
  staunen: { arme: ["rechts-oben", "links-oben"], augen: "gross", mund: "staunen" },
  schlaf: { arme: ["rechts-unten", "links-unten"], augen: "zu", mund: "klein" },
  /* 6.9.45: weitere Gefühle aus den neuen Augen und Mündern */
  muede: { arme: ["rechts-unten", "links-unten"], augen: "muede", mund: "klein" },
  verliebt: { arme: ["rechts-oben", "links-oben"], augen: "herz", mund: "laecheln" },
  frech: { arme: ["links-unten"], winken: "rechts-oben", augen: "offen", mund: "zunge-raus" },
  schwindelig: { arme: ["rechts-unten", "links-oben"], augen: "dizzy", mund: "grimmig" },
  grummelig: { arme: ["rechts-unten", "links-unten"], augen: "muede", mund: "grimmig" },
  genervt: { arme: ["rechts-unten", "links-unten"], augen: "sauer", mund: "sauer" },
};
/* Level 1 ist grau; Farben gibt es über Level/Sterne-Shop (eingefärbt von werkzeuge/franzi_bilder.py) */
const FRANZI_FARBEN = ["grau", "orange", "blau", "gruen", "lila", "gold"];
/* Hüte, Brillen und Schmuck sind im alten Maß (120 × 124) gezeichnet: so sitzen sie auf der 512er-Schablone
   (Kopf oben y 156, Augenlinie y 270, Körpermitte x 256) */
const FRANZI_ALT_MASS = "translate(256 156) scale(3.15) translate(-60 -20)";
const FRANZI_HUT = {
  muetze: '<path d="M30 24Q60 -6 90 24Z" fill="#e84a5f"/><rect x="26" y="19" width="68" height="8" rx="4" fill="#fff"/><circle cx="60" cy="3" r="6" fill="#fff"/>',
  zylinder: '<rect x="40" y="-6" width="40" height="26" rx="3" fill="#222"/><rect x="40" y="10" width="40" height="5" fill="#e84a5f"/><rect x="28" y="18" width="64" height="6" rx="3" fill="#222"/>',
  krone: '<path d="M34 24L36 4L48 14L60 0L72 14L84 4L86 24Z" fill="#ffd54f" stroke="#c99a1e" stroke-width="2"/><circle cx="60" cy="15" r="3" fill="#e84a5f"/>',
};
const FRANZI_BRILLE = {
  sonne: '<rect x="33" y="47" width="24" height="16" rx="6" fill="#111" stroke="#e8e8f0" stroke-width="1.4"/><rect x="63" y="47" width="24" height="16" rx="6" fill="#111" stroke="#e8e8f0" stroke-width="1.4"/>' +
         '<path d="M57 53H63" stroke="#e8e8f0" stroke-width="2.4"/><rect x="37" y="50" width="8" height="3" rx="1.5" fill="#fff" opacity=".35"/>',
  rund: '<g fill="none" stroke="#ffd54f" stroke-width="3"><circle cx="45" cy="56" r="11"/><circle cx="75" cy="56" r="11"/><path d="M56 56H64"/></g>',
  taucher: '<rect x="28" y="42" width="64" height="28" rx="12" fill="rgba(150,230,255,.35)" stroke="#ffd54f" stroke-width="4"/>' +
           '<path d="M92 56 Q108 50 106 30" fill="none" stroke="#4fd8f0" stroke-width="6" stroke-linecap="round"/>',
};
/* 6.7: Welten ziehen Franzi passend an - nur was das Kind nicht selbst gewählt hat */
FRANZI_HUT.helm = '<circle cx="60" cy="58" r="58" fill="rgba(200,230,255,.16)" stroke="#c9d3e3" stroke-width="4"/>' +
                  '<rect x="52" y="-2" width="16" height="6" rx="3" fill="#c9d3e3"/>';
const WELT_FRANZI = { rock: { brille: "sonne" }, unterwasser: { brille: "taucher" }, raumstation: { hut: "helm" } };
const FRANZI_EXTRA = {
  schleife: '<g transform="translate(97 27)"><path d="M0 0L-12 -8V8ZM0 0L12 -8V8Z" fill="#ff5fa2"/><circle r="4" fill="#ff8fc0"/></g>',
  stern: '<path d="M18 26l3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z" fill="#ffd54f" stroke="#c99a1e" stroke-width="1"/>',
  /* 6.9.12: Blume im Haar */
  blume: '<g transform="translate(92 24)"><circle r="5" cx="0" cy="-7" fill="#ff8fc0"/><circle r="5" cx="7" cy="0" fill="#ff8fc0"/><circle r="5" cx="0" cy="7" fill="#ff8fc0"/><circle r="5" cx="-7" cy="0" fill="#ff8fc0"/><circle r="4" fill="#ffd54f"/></g>',
  /* 6.9: Schal aus dem Sterne-Shop */
  /* 6.9.36: Schal vorn um den Körper, das Ende hängt links NEBEN den Beinen (verdeckte vorher das rechte Bein) */
  schal: '<path d="M12 84Q60 100 108 84L108 95Q60 111 12 95Z" fill="#e84a5f"/><path d="M60 92Q60 100 60 100" stroke="#fff" stroke-width="0"/>' +
         '<rect x="14" y="88" width="13" height="24" rx="4" fill="#c93a4e"/><rect x="14" y="106" width="13" height="5" fill="#fff" opacity=".5"/>',
};
/* 6.9.59: gezeichnete Kleidung - Teil-Wahl → Bild in /bilder/franzi/ (Mütze und Krone verdecken die Antennen) */
const FRANZI_KLEID_BILD = { "hut-muetze": "kleid-muetze", "hut-krone": "kleid-krone", "hut-zylinder": "kleid-zylinder",
                            "brille-rund": "kleid-rund", "brille-taucher": "kleid-taucher", "extra-stern": "kleid-stern",
                            "extra-schleife": "kleid-schleife", "extra-blume": "kleid-blume" };
const OHNE_ANTENNE = new Set(["muetze", "krone"]);
/* 6.9: Kleidung aus dem Sterne-Shop → Teile der Zeichnung */
export const FRANZI_KLEIDUNG = { "kleid-krone": ["hut", "krone"], "kleid-zauberhut": ["hut", "zylinder"], "kleid-brille": ["brille", "sonne"],
                                 "kleid-schleife": ["extra", "schleife"], "kleid-schal": ["extra", "schal"],
                                 "kleid-muetze": ["hut", "muetze"], "kleid-rundbrille": ["brille", "rund"], "kleid-taucher": ["brille", "taucher"],
                                 "kleid-stern": ["extra", "stern"], "kleid-blume": ["extra", "blume"], "kleid-blau": ["farbe", "blau"],
                                 "kleid-gruen": ["farbe", "gruen"], "kleid-lila": ["farbe", "lila"], "kleid-gold": ["farbe", "gold"],
                                 "franzi-wachsen-1": ["groesse", "1"], "franzi-wachsen-2": ["groesse", "2"] };
export function kleidungZuSachen(liste) {
  const s = {};
  for (const id of liste || []) { const k = FRANZI_KLEIDUNG[id]; if (k) s[k[0]] = k[1]; }
  return s;
}
let franziSachen = {};
/* 6.9.57: Antennen als Rückmeldung - grün = richtig/geschafft, rot = falsch/geht nicht. Gilt auch für Franzis, die in der
   nächsten Sekunde neu gezeichnet werden (Kauf, Pflege). */
let blinkFarbe = "", blinkBis = 0;
const BLINK_MS = 1300;
export function franziBlinken(farbe) {
  if (farbe !== "gruen" && farbe !== "rot") return;
  blinkFarbe = farbe; blinkBis = Date.now() + BLINK_MS;
  for (const f of document.querySelectorAll(".franzi")) {
    f.classList.remove("f-blink-gruen", "f-blink-rot");
    void f.getBoundingClientRect();                       /* Animation neu starten */
    f.classList.add(`f-blink-${farbe}`);
  }
  clearTimeout(franziBlinken.uhr);
  franziBlinken.uhr = setTimeout(() => document.querySelectorAll(".f-blink-gruen, .f-blink-rot")
    .forEach((f) => f.classList.remove("f-blink-gruen", "f-blink-rot")), BLINK_MS);
}
/** 6.4: was Franzi trägt ({farbe, hut, brille, extra}) - gilt für jede Franzi, die danach gezeichnet wird */
export function setzeFranzi(sachen) { franziSachen = sachen && typeof sachen === "object" ? sachen : {}; }

/* 6.9.57: Gold-Deluxe - ein Glanzstreifen wandert über Körper und Arme (nur wo Franzi ist: Maske aus ihren Bildern) */
let glanzNr = 0;
const franziGlanz = (teile) => {
  const id = `f-glanz-${++glanzNr}`;
  return `<g class="f-glanz"><mask id="${id}" mask-type="alpha">${teile}</mask><g mask="url(#${id})">` +
    `<g class="f-glanz-lauf"><rect x="-40" y="60" width="110" height="480" transform="skewX(-18)" fill="url(#f-glanz-v)"/></g></g></g>`;
};
const FRANZI_GLANZ_VERLAUF = '<defs><linearGradient id="f-glanz-v" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#fffbe6" stop-opacity="0"/>' +
  '<stop offset=".5" stop-color="#fffbe6" stop-opacity=".75"/><stop offset="1" stop-color="#fffbe6" stop-opacity="0"/></linearGradient></defs>';

/* 6.9.60: Franzi spielt Gitarre - die Arme kommen aus den Gitarren-Bildern. Anschlag ab/auf im Wechsel, die Greifhand
   wandert über die Bünde 1-4, die Gitarre wippt leicht. Ohne Animation: das feste Bild (beide Hände). */
const FRANZI_GITARRE = (bildTeil) => '<g class="f-gitarre">' + bildTeil("gitarre-fest", "fg-fest") +
  bildTeil("gitarre-ab", "fg-ab") + bildTeil("gitarre-auf", "fg-auf") +
  [1, 2, 3, 4].map((n) => bildTeil(`gitarre-bund-${n}`, `fg-bund fg-bund-${n}`)).join("") + "</g>";

export function franzi(stimmung = "froh", klasse = "", eigene = null) {
  const s = FRANZI_TEILE[stimmung] ? stimmung : "froh";
  const welt = WELT_FRANZI[document.body?.dataset.thema] || {};
  const sachen = { ...welt, ...Object.fromEntries(Object.entries(eigene || franziSachen).filter(([, v]) => v)) };
  const farbe = FRANZI_FARBEN.includes(sachen.farbe) ? sachen.farbe : "grau";
  const t = FRANZI_TEILE[s];
  /* 6.9.53: Antennen blinken - grün = alles gut, rot = Franzi braucht etwas oder will Ruhe; im Schlaf aus */
  const licht = s === "schlaf" ? "" : ["genervt", "grummelig", "muede", "staunen"].includes(s) ? "rot" : "gruen";
  const bildTeil = (name, klasse_ = "") => `<image${klasse_ ? ` class="${klasse_}"` : ""} href="${FRANZI_PFAD}${name}.png" width="512" height="512"/>`;
  const blink = Date.now() < blinkBis ? ` f-blink-${blinkFarbe}` : "";
  const knoten = el("span", { class: `franzi franzi-${s}${licht ? ` f-licht-${licht}` : ""}${blink} ${klasse}`.trim(), "aria-hidden": "true" });
  knoten.innerHTML = '<svg viewBox="67 93 378 391" xmlns="http://www.w3.org/2000/svg">' +   /* fester Inhalt aus diesem Modul */
    '<g class="f-koerper">' +
    (sachen.gitarre ? "" : t.arme.map((a) => bildTeil(`arm-${a}-${farbe}`)).join("")) +
    (t.winken && !sachen.gitarre ? `<g class="f-winken">${bildTeil(`arm-${t.winken}-${farbe}`)}</g>` : "") +
    bildTeil(`koerper-${farbe}`) +
    (OHNE_ANTENNE.has(sachen.hut) ? "" : '<g class="f-antenne">' + ["gruen", "rot"].map((l) => bildTeil(`antenne-${l}-a-${farbe}`, `f-ant-a f-ant-${l}`) +
      bildTeil(`antenne-${l}-b-${farbe}`, `f-ant-b f-ant-${l}`)).join("") + "</g>") +
    (farbe === "gold" ? FRANZI_GLANZ_VERLAUF + franziGlanz(bildTeil(`koerper-${farbe}`) + t.arme.map((a) => bildTeil(`arm-${a}-${farbe}`)).join("")) : "") +
    `<g class="f-augen">${bildTeil(`augen-${t.augen}`)}</g>` + bildTeil(`mund-${t.mund}`) +
    (s === "schlaf" ? '<g class="f-zzz" fill="#fff" stroke="#1e2a4a" stroke-width="3" paint-order="stroke" font-family="sans-serif" font-weight="800">' +
      '<text x="405" y="150" font-size="44">z</text><text x="440" y="112" font-size="30">z</text></g>' : "") +
    /* 6.9.59: gezeichnete Kleidung (512er-Ebenen wie Franzi); was noch nicht gezeichnet ist, bleibt die alte Zeichnung */
    ["brille", "hut", "extra"].map((teil) => {
      const name = sachen[teil] && FRANZI_KLEID_BILD[`${teil}-${sachen[teil]}`];
      if (name) return bildTeil(name);
      const alt = ({ brille: FRANZI_BRILLE, hut: FRANZI_HUT, extra: FRANZI_EXTRA })[teil][sachen[teil]];
      return alt ? `<g transform="${FRANZI_ALT_MASS}">${alt}</g>` : "";
    }).join("") + (sachen.gitarre ? FRANZI_GITARRE(bildTeil) : "") + "</g></svg>";
  return knoten;
}

/* 6.9.62: kleine Franzi unten rechts auf Seiten ohne eigene Franzi (Musik, Filme, Wetter …) - mit Gefühl, optional
   Sprechblase oder Zeichen (🍿). tanzt = wippt im Takt (nur Stufe sparsam/hoch, per CSS). */
export function franziEcke(gesicht = "froh", { text = "", zeichen = "", tanzt = false, sachen = null } = {}) {
  return el("div", { class: "franzi-ecke" + (tanzt ? " tanzt" : ""), "aria-hidden": "true" },
    franzi(gesicht, "", sachen),
    zeichen ? el("span", { class: "fe-zeichen", text: zeichen }) : null,
    text ? el("div", { class: "fe-blase", text }) : null);
}

/* 6.8.12: Franzi bewegt sich nur alle 8 Sekunden kurz (blinzeln, im Schlaf atmen) - keine Daueranimation, der Pi 3 bleibt
   kühl. Nur sichtbare Franzis, nichts, solange die Seite verborgen ist. */
if (typeof window !== "undefined" && !window.__ffFranziRegen) {
  window.__ffFranziRegen = setInterval(() => {
    const stufe = document.documentElement.dataset.animation || "sparsam";
    if (document.hidden || stufe !== "sparsam") return;          /* aus = still, hoch = Dauer per CSS */
    const alle = [...document.querySelectorAll(".franzi")].filter((f) => f.getClientRects().length && f.checkVisibility?.({ visibilityProperty: true }) !== false);
    alle.forEach((f) => f.classList.add("f-regen"));
    if (alle.length) setTimeout(() => alle.forEach((f) => f.classList.remove("f-regen")), 1700);
  }, 8000);
}

/* Bereiche („Ordner“). Eltern können eine App einem Bereich zuordnen (Feld "bereich", auch alte Namen), sonst automatisch. */
export const BEREICHE = [
  { id: "spiele", name: "Spiele", symbol: "🎮", farbe: "#2f8a5e" },
  { id: "filme", name: "Filme", symbol: "🎬", farbe: "#b0442f" },
  { id: "musik", name: "Musik", symbol: "🎵", farbe: "#a8326b" },
  { id: "lernen", name: "Lernen", symbol: "🎓", farbe: "#2f6db5" },
  { id: "zimmer", name: "Mein Zimmer", symbol: "📨", farbe: "#8a4fc2" },
  { id: "retro", name: "Retro", symbol: "🕹️", farbe: "#5a3d8a" },
];
const BEREICH_ALT = { start: "zimmer", medien: "filme" };
const ZIMMER_IDS = ["spiel-nachrichten", "spiel-wecker", "spiel-gutschein", "familie", "spiel-gestalten", "spiel-fotoalbum",
                    "spiel-sticker", "spiel-wetter", "spiel-news", "spiel-meintag", "spiel-hilfe", "spiel-franzi"];
export function bereichVon(app) {
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
