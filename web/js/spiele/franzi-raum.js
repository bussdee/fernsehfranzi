/* FernsehFranzi 6.9.15 - Franzis Räume als gezeichnete Szenen (eigene SVG, Stil wie Franzi: rund, flach, ein wenig Licht).
 *
 * raumSzene(raum, {nacht, wetter}) -> SVG-Text (fester Inhalt aus diesem Modul, keine Eingaben von außen).
 * Die Szene ist der Hintergrund; Möbel, Spielzeug und Franzi liegen darüber (franzi.js).
 * Bewegung nur in der Stufe „hoch“ (CSS: html[data-animation="hoch"] .fzs-…): ziehende Wolken, Regen, Schnee, wiegendes Gras,
 * glimmende Lampe. In „sparsam“ und „aus“ steht alles still - kostet dann nur das einmalige Zeichnen.
 */

const B = 800, H = 500, OBEN = -160;          /* die Wand reicht nach oben weiter - der Kasten schneidet nur oben ab */

function himmel(nacht, wetter) {
  const [oben, unten] = nacht ? ["#0d1838", "#2a3a6e"]
    : wetter === "regen" ? ["#7f93a8", "#b9c7d4"] : wetter === "schnee" ? ["#b8c6d8", "#e8eef6"] : ["#7cc8ff", "#d9f1ff"];
  return { oben, unten };
}

/** Ausblick (Fenster oder Garten-Himmel): Sonne/Mond, Wolken, Regen/Schnee */
function ausblick(x, y, b, h, nacht, wetter, id) {
  const hm = himmel(nacht, wetter);
  const hs = Math.min(h, 180);                       /* Größe von Sonne, Mond, Wolken - nicht mit dem Himmel mitwachsen */
  const teile = [`<defs><linearGradient id="${id}h" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${hm.oben}"/>` +
    `<stop offset="1" stop-color="${hm.unten}"/></linearGradient><clipPath id="${id}c"><rect x="${x}" y="${y}" width="${b}" height="${h}" rx="6"/></clipPath></defs>`,
    `<g clip-path="url(#${id}c)"><rect x="${x}" y="${y}" width="${b}" height="${h}" fill="url(#${id}h)"/>`];
  if (nacht) {
    teile.push(`<circle cx="${x + b * 0.72}" cy="${y + hs * 0.3 + (h - hs) * 0.3}" r="${hs * 0.13}" fill="#fff6d0"/>` +
      `<circle cx="${x + b * 0.75}" cy="${y + hs * 0.27 + (h - hs) * 0.3}" r="${hs * 0.12}" fill="${hm.oben}"/>`);
    for (let i = 0; i < 9; i++) {
      const sx = x + ((i * 37) % 100) / 100 * b, sy = y + ((i * 53) % 70) / 100 * h;
      teile.push(`<circle class="fzs-funkeln" style="animation-delay:${(i % 4) * 0.7}s" cx="${sx}" cy="${sy}" r="1.6" fill="#fff"/>`);
    }
  } else if (wetter !== "regen" && wetter !== "schnee") {
    teile.push(`<circle cx="${x + b * 0.78}" cy="${y + hs * 0.28 + (h - hs) * 0.3}" r="${hs * 0.15}" fill="#ffe27a"/>` +
      `<circle cx="${x + b * 0.78}" cy="${y + hs * 0.28 + (h - hs) * 0.3}" r="${hs * 0.24}" fill="#ffe27a" opacity=".25"/>`);
  }
  /* äußere Gruppe bewegt sich (CSS), innere trägt die Lage - sonst überschreibt die Animation das transform */
  const wolke = (wx, wy, s, farbe) => `<g class="fzs-wolke"><g transform="translate(${wx} ${wy}) scale(${s})" fill="${farbe}">` +
    '<ellipse cx="0" cy="0" rx="30" ry="14"/><circle cx="-12" cy="-8" r="13"/><circle cx="10" cy="-12" r="16"/></g></g>';
  const wf = nacht ? "rgba(200,210,255,.25)" : wetter === "regen" ? "#8e9cab" : "#ffffff";
  teile.push(wolke(x + b * 0.25, y + h * 0.35, hs / 160, wf), wolke(x + b * 0.6, y + h * 0.55, hs / 220, wf));
  if (wetter === "regen") {
    for (let i = 0; i < 14; i++) {
      const rx = x + ((i * 29) % 100) / 100 * b, ry = y + ((i * 41) % 100) / 100 * h;
      teile.push(`<path class="fzs-regen" style="animation-delay:${(i % 5) * 0.15}s" d="M${rx} ${ry}l-4 12" stroke="#dfe8f2" stroke-width="2" stroke-linecap="round"/>`);
    }
  }
  if (wetter === "schnee") {
    for (let i = 0; i < 14; i++) {
      const rx = x + ((i * 29) % 100) / 100 * b, ry = y + ((i * 41) % 100) / 100 * h;
      teile.push(`<circle class="fzs-schnee" style="animation-delay:${(i % 6) * 0.4}s" cx="${rx}" cy="${ry}" r="2.6" fill="#fff"/>`);
    }
  }
  teile.push("</g>");
  return teile.join("");
}

/** Fenster mit Rahmen, Kreuz, Vorhängen und Fensterbank */
function fenster(x, y, b, h, nacht, wetter, id, vorhang = "#ff9eb5") {
  return `<rect x="${x - 8}" y="${y - 8}" width="${b + 16}" height="${h + 16}" rx="10" fill="#fff" opacity=".9"/>` +
    ausblick(x, y, b, h, nacht, wetter, id) +
    `<path d="M${x + b / 2} ${y}V${y + h}M${x} ${y + h / 2}H${x + b}" stroke="#fff" stroke-width="6"/>` +
    `<path d="M${x - 18} ${y - 14}Q${x + 10} ${y + h * 0.5} ${x - 6} ${y + h + 10}H${x - 22}Z" fill="${vorhang}"/>` +
    `<path d="M${x + b + 18} ${y - 14}Q${x + b - 10} ${y + h * 0.5} ${x + b + 6} ${y + h + 10}H${x + b + 22}Z" fill="${vorhang}"/>` +
    `<rect x="${x - 26}" y="${y - 20}" width="${b + 52}" height="8" rx="4" fill="#b98a5c"/>` +
    `<rect x="${x - 14}" y="${y + h + 8}" width="${b + 28}" height="10" rx="4" fill="#e9d8c4"/>`;
}

function boden(farbe1, farbe2, y = 330) {
  let s = `<rect x="0" y="${y}" width="${B}" height="${H - y}" fill="${farbe1}"/>`;
  for (let i = 0; i < 6; i++) s += `<path d="M0 ${y + 18 + i * 28}H${B}" stroke="${farbe2}" stroke-width="2" opacity=".5"/>`;
  for (let i = 0; i < 12; i++) s += `<path d="M${(i * 97 + (i % 2) * 40) % B} ${y + 18 + (i % 6) * 28}v28" stroke="${farbe2}" stroke-width="2" opacity=".5"/>`;
  return s + `<rect x="0" y="${y - 8}" width="${B}" height="10" fill="#fff" opacity=".55"/>`;
}

function lampe(x, y, nacht) {
  return `<path d="M${x} ${OBEN}V${y - 30}" stroke="#6b5a4a" stroke-width="3"/>` +
    `<path d="M${x - 34} ${y}L${x - 18} ${y - 34}H${x + 18}L${x + 34} ${y}Z" fill="#ffd27a"/>` +
    (nacht ? `<ellipse class="fzs-licht" cx="${x}" cy="${y + 120}" rx="160" ry="150" fill="#ffd98a" opacity=".16"/>` : "");
}

const SZENEN = {
  "raum-zimmer": (nacht, wetter) => `<defs><pattern id="tapete" width="60" height="60" patternUnits="userSpaceOnUse">` +
    `<rect width="60" height="60" fill="#ffe9cf"/><path d="M30 18l3 7 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z" fill="#ffd9a8"/></pattern></defs>` +
    `<rect y="${OBEN}" width="${B}" height="${H - OBEN}" fill="url(#tapete)"/>` +
    fenster(70, 60, 170, 130, nacht, wetter, "fz1") +
    `<rect x="470" y="110" width="200" height="12" rx="5" fill="#b98a5c"/><rect x="490" y="78" width="22" height="32" rx="3" fill="#7fb4ff"/>` +
    `<rect x="516" y="84" width="18" height="26" rx="3" fill="#ff8f8f"/><rect x="538" y="74" width="24" height="36" rx="3" fill="#8fd6a4"/>` +
    `<circle cx="630" cy="96" r="14" fill="#ffd54f"/>` +
    boden("#d9a273", "#b98055") +
    `<ellipse cx="400" cy="440" rx="230" ry="42" fill="#9fd0ff" opacity=".85"/><ellipse cx="400" cy="440" rx="190" ry="30" fill="#c7e4ff" opacity=".8"/>` +
    lampe(400, 70, nacht),
  "raum-garten": (nacht, wetter) => ausblick(0, OBEN, B, 330 - OBEN, nacht, wetter, "fz2") +
    `<path d="M0 270Q160 200 330 260T800 240V340H0Z" fill="${nacht ? "#25456a" : "#9ad08a"}"/>` +
    `<path d="M0 300Q220 250 430 300T800 290V340H0Z" fill="${nacht ? "#2c5a5a" : "#7cc070"}"/>` +
    `<rect x="0" y="320" width="${B}" height="${H - 320}" fill="${nacht ? "#2f6a4a" : "#6cc070"}"/>` +
    Array.from({ length: 14 }, (_, i) => `<rect x="${i * 60 + 6}" y="282" width="16" height="62" rx="4" fill="${nacht ? "#8a7a6a" : "#fff3e0"}"/>`).join("") +
    `<rect x="0" y="298" width="${B}" height="8" fill="${nacht ? "#8a7a6a" : "#fff3e0"}"/><rect x="0" y="326" width="${B}" height="8" fill="${nacht ? "#8a7a6a" : "#fff3e0"}"/>` +
    `<path d="M330 500Q380 420 400 360H440Q430 420 470 500Z" fill="#e9d2a8" opacity=".9"/>` +
    Array.from({ length: 22 }, (_, i) => `<path class="fzs-gras" style="animation-delay:${(i % 5) * 0.3}s" d="M${(i * 37) % B} ${470 - (i % 3) * 30}q4 -16 8 0" stroke="#4fa35a" stroke-width="3" fill="none" stroke-linecap="round"/>`).join(""),
  "raum-kueche": (nacht, wetter) => `<defs><pattern id="fliese" width="40" height="40" patternUnits="userSpaceOnUse">` +
    `<rect width="40" height="40" fill="#fff6e3"/><rect x="1" y="1" width="38" height="38" rx="3" fill="#fffaf0"/></pattern>` +
    `<pattern id="karo" width="80" height="80" patternUnits="userSpaceOnUse"><rect width="80" height="80" fill="#e9e2d0"/>` +
    `<rect width="40" height="40" fill="#c9bfa6"/><rect x="40" y="40" width="40" height="40" fill="#c9bfa6"/></pattern></defs>` +
    `<rect y="${OBEN}" width="${B}" height="${H - OBEN}" fill="url(#fliese)"/>` +
    fenster(300, 50, 200, 120, nacht, wetter, "fz3", "#ffd27a") +
    `<rect x="0" y="230" width="${B}" height="100" fill="#8fc7a8"/><rect x="0" y="222" width="${B}" height="14" rx="4" fill="#f4efe6"/>` +
    Array.from({ length: 5 }, (_, i) => `<rect x="${i * 160 + 14}" y="244" width="132" height="76" rx="8" fill="#a6d6bb"/><rect x="${i * 160 + 70}" y="274" width="20" height="5" rx="2.5" fill="#5f8f74"/>`).join("") +
    `<rect x="0" y="330" width="${B}" height="${H - 330}" fill="url(#karo)"/>` + lampe(140, 80, nacht) + lampe(660, 80, nacht),
  "raum-bad": (nacht, wetter) => `<defs><pattern id="blau" width="44" height="44" patternUnits="userSpaceOnUse">` +
    `<rect width="44" height="44" fill="#bfe6f6"/><rect x="2" y="2" width="40" height="40" rx="4" fill="#d6f1fb"/></pattern></defs>` +
    `<rect y="${OBEN}" width="${B}" height="${H - OBEN}" fill="url(#blau)"/>` +
    fenster(520, 60, 140, 110, nacht, wetter, "fz4", "#a8e0ff") +
    `<rect x="120" y="140" width="100" height="10" rx="5" fill="#c9d3e3"/><rect x="132" y="150" width="34" height="70" rx="6" fill="#ff9eb5"/>` +
    `<rect x="172" y="150" width="34" height="58" rx="6" fill="#ffe27a"/>` +
    boden("#9fd3e4", "#7fb7cb") +
    `<ellipse cx="300" cy="455" rx="120" ry="26" fill="#ffb7c8" opacity=".85"/>` + lampe(400, 60, nacht),
};

/* 6.9.44: gezeichnete Räume (1600 × 1320 nach der Raum-Schablone) ersetzen die Zeichnung im Code - unten mittig wie die
   Szene, nachts abgedunkelt. Neue Räume: Bild nach web/bilder/raeume/ und hier eintragen. */
export const RAUM_BILDER = { "raum-zimmer": "/bilder/raeume/raum-1.jpg", "raum-hell": "/bilder/raeume/raum-2.jpg",
                             "raum-probe": "/bilder/raeume/raum-3.jpg", "raum-garten": "/bilder/raeume/raum-garten.jpg",
                             "raum-kueche": "/bilder/raeume/raum-kueche.jpg", "raum-spiel": "/bilder/raeume/raum-spiel.jpg" };

export function raumSzene(raum, { nacht = false, wetter = null } = {}) {
  if (RAUM_BILDER[raum]) {
    return `<svg class="fz-szene" viewBox="0 ${OBEN} ${B} ${H - OBEN}" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">` +
      `<image href="${RAUM_BILDER[raum]}" x="0" y="${OBEN}" width="${B}" height="${H - OBEN}" preserveAspectRatio="xMidYMax slice"/>` +
      (nacht ? `<rect y="${OBEN}" width="${B}" height="${H - OBEN}" fill="#0b1440" opacity=".45"/>` : "") + "</svg>";
  }
  const szene = SZENEN[raum] || SZENEN["raum-zimmer"];
  return `<svg class="fz-szene" viewBox="0 ${OBEN} ${B} ${H - OBEN}" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">` +
    szene(nacht, wetter) + (nacht ? `<rect y="${OBEN}" width="${B}" height="${H - OBEN}" fill="#0b1440" opacity=".38"/>` : "") + "</svg>";
}
