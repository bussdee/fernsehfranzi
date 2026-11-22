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
