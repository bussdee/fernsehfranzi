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
 * schlaf. Fester eigener Inhalt (keine fremden Daten), bewegt wird nur über CSS (transform/opacity, Pi 3). */
const FRANZI_GESICHT = {
  froh: '<g class="f-augen"><ellipse cx="45" cy="56" rx="7" ry="9" fill="#fff"/><ellipse cx="75" cy="56" rx="7" ry="9" fill="#fff"/>' +
        '<circle cx="47" cy="58" r="3.6" fill="#1e2a4a"/><circle cx="77" cy="58" r="3.6" fill="#1e2a4a"/></g>' +
        '<path d="M49 72Q60 82 71 72" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round"/>',
  jubel: '<path d="M38 58Q45 48 52 58M68 58Q75 48 82 58" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round"/>' +
         '<path d="M47 68H73Q72 84 60 84Q48 84 47 68Z" fill="#fff"/><path d="M52 78Q60 74 68 78Q66 84 60 84Q54 84 52 78Z" fill="#ff6b7d"/>',
  staunen: '<g class="f-augen"><circle cx="45" cy="55" r="9" fill="#fff"/><circle cx="75" cy="55" r="9" fill="#fff"/>' +
           '<circle cx="45" cy="56" r="4.5" fill="#1e2a4a"/><circle cx="75" cy="56" r="4.5" fill="#1e2a4a"/></g>' +
           '<ellipse cx="60" cy="76" rx="6" ry="7" fill="#fff"/>',
  schlaf: '<path d="M38 57Q45 63 52 57M68 57Q75 63 82 57" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round"/>' +
          '<ellipse cx="60" cy="75" rx="4" ry="3" fill="#fff" opacity=".8"/>' +
          '<g class="f-zzz" fill="#fff" font-family="sans-serif" font-weight="800"><text x="90" y="16" font-size="13">z</text>' +
          '<text x="100" y="6" font-size="9">z</text></g>',
};
const FRANZI_ARME = {
  froh: '<path d="M14 66Q4 72 6 84" fill="none" stroke="#e8603f" stroke-width="7" stroke-linecap="round"/>' +
        '<g class="f-winken"><path d="M106 64Q118 56 116 42" fill="none" stroke="#e8603f" stroke-width="7" stroke-linecap="round"/></g>',
  jubel: '<path d="M14 62Q2 52 6 36M106 62Q118 52 114 36" fill="none" stroke="#e8603f" stroke-width="7" stroke-linecap="round"/>',
  staunen: '<path d="M14 66Q2 66 4 54M106 66Q118 66 116 54" fill="none" stroke="#e8603f" stroke-width="7" stroke-linecap="round"/>',
  schlaf: "",
};
export function franzi(stimmung = "froh", klasse = "") {
  const s = FRANZI_GESICHT[stimmung] ? stimmung : "froh";
  const knoten = el("span", { class: `franzi franzi-${s} ${klasse}`.trim(), "aria-hidden": "true" });
  knoten.innerHTML = '<svg viewBox="0 0 120 124" xmlns="http://www.w3.org/2000/svg">' +   /* fester Inhalt aus diesem Modul */
    '<g class="f-koerper"><path d="M52 22L40 6M68 22L82 8" stroke="#3b4566" stroke-width="4" stroke-linecap="round"/>' +
    '<circle cx="40" cy="6" r="5" fill="#ffd54f"/><circle cx="82" cy="8" r="5" fill="#7fdcaa"/>' + FRANZI_ARME[s] +
    '<rect x="32" y="100" width="16" height="12" rx="5" fill="#c94f35"/><rect x="72" y="100" width="16" height="12" rx="5" fill="#c94f35"/>' +
    '<rect x="10" y="20" width="100" height="84" rx="20" fill="#ff7a59"/><rect x="10" y="20" width="100" height="40" rx="20" fill="#ff9472"/>' +
    '<rect x="21" y="30" width="78" height="62" rx="13" fill="#1e2a4a"/><rect x="25" y="33" width="34" height="8" rx="4" fill="#fff" opacity=".12"/>' +
    '<circle cx="33" cy="76" r="5" fill="#ff8fb1" opacity=".55"/><circle cx="87" cy="76" r="5" fill="#ff8fb1" opacity=".55"/>' +
    FRANZI_GESICHT[s] + "</g></svg>";
  return knoten;
}
