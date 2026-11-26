/* FernsehFranzi 6.9.55/6.9.58 - gezeichnete Gegenstände für Franzis Räume (eigene SVG, bis gezeichnete Bilder kommen).
 *
 * Jedes Bild: viewBox 0 0 100 100, der Gegenstand steht unten auf der Kante (y = 100), mittig. Größe im Raum kommt aus
 * DING in franzi.js. Kräftige Konturen und klare Farben (wirken aus 3 m Entfernung). Liegt eine gezeichnete PNG-Datei
 * in web/bilder/dinge/ (Liste in liste.json), hat sie Vorrang.
 */
const K = 'stroke="#2b2f45" stroke-width="2.5" stroke-linejoin="round"';
const svg = (inhalt) => `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">${inhalt}</svg>`;

export const DING_SVG = {
  /* ---------------- Proberaum */
  "moebel-mikrofon": svg(
    `<ellipse cx="50" cy="97" rx="18" ry="4" fill="#2b2f45"/><rect x="47.5" y="30" width="5" height="66" fill="#8b93a8" ${K}/>` +
    `<path d="M50 30 L66 18" stroke="#8b93a8" stroke-width="5" stroke-linecap="round"/><path d="M50 30 L66 18" stroke="#2b2f45" stroke-width="1.5" fill="none"/>` +
    `<rect x="62" y="4" width="14" height="20" rx="7" fill="#c9ced9" ${K} transform="rotate(35 69 14)"/>` +
    `<path d="M64 8l10 9M62 12l10 9" stroke="#8b93a8" stroke-width="1.5" transform="rotate(35 69 14)"/>`),
  "spielzeug-keyboard": svg(
    `<path d="M22 100 L28 58 M78 100 L72 58" stroke="#2b2f45" stroke-width="4" stroke-linecap="round"/><path d="M28 100 L22 58 M72 100 L78 58" stroke="#2b2f45" stroke-width="4" stroke-linecap="round"/>` +
    `<rect x="6" y="40" width="88" height="20" rx="3" fill="#2f3550" ${K}/><rect x="10" y="49" width="80" height="9" fill="#fff" ${K}/>` +
    Array.from({ length: 13 }, (_, i) => `<path d="M${16 + i * 6} 49v9" stroke="#2b2f45" stroke-width="1"/>`).join("") +
    Array.from({ length: 13 }, (_, i) => ([2, 6, 9, 13].includes(i % 7) ? "" : `<rect x="${14.5 + i * 6}" y="49" width="3" height="5" fill="#2b2f45"/>`)).join("") +
    `<circle cx="18" cy="44.5" r="2" fill="#ff5f7a"/><circle cx="25" cy="44.5" r="2" fill="#5fd38a"/><rect x="60" y="42.5" width="26" height="4" rx="1" fill="#7fdcff"/>`),
  "moebel-verstaerker": svg(
    `<rect x="14" y="34" width="72" height="64" rx="6" fill="#33384f" ${K}/><rect x="14" y="34" width="72" height="14" rx="6" fill="#d8b46a" ${K}/>` +
    `<circle cx="26" cy="41" r="3" fill="#2b2f45"/><circle cx="38" cy="41" r="3" fill="#2b2f45"/><circle cx="50" cy="41" r="3" fill="#2b2f45"/>` +
    `<circle cx="50" cy="73" r="18" fill="#1f2333" ${K}/><circle cx="50" cy="73" r="8" fill="#4a5070"/><circle cx="50" cy="73" r="3" fill="#8b93a8"/>`),
  "moebel-discokugel": svg(
    `<path d="M50 0 V18" stroke="#8b93a8" stroke-width="2"/><circle cx="50" cy="52" r="34" fill="#c9d2e6" ${K}/>` +
    Array.from({ length: 6 }, (_, r) => Array.from({ length: 6 }, (_, c) => {
      const x = 22 + c * 10, y = 24 + r * 10, d = Math.hypot(x + 5 - 50, y + 5 - 52);
      return d < 30 ? `<rect x="${x}" y="${y}" width="9" height="9" fill="${["#ffffff", "#9fb2d9", "#e7ecf7", "#7fdcff", "#ffd1f0"][(r * 3 + c) % 5]}" opacity=".9"/>` : "";
    }).join("")).join("") + `<circle cx="38" cy="38" r="5" fill="#fff" opacity=".9"/>`),
  /* ---------------- Garten */
  "moebel-gartenzwerg": svg(
    `<ellipse cx="50" cy="97" rx="20" ry="4" fill="#5a8f3a"/><path d="M34 96 Q32 72 50 68 Q68 72 66 96Z" fill="#3f7be0" ${K}/>` +
    `<rect x="36" y="84" width="28" height="5" fill="#6b4a2f"/><circle cx="50" cy="58" r="12" fill="#ffd6b8" ${K}/>` +
    `<path d="M38 62 Q50 82 62 62 Q56 70 50 70 Q44 70 38 62Z" fill="#fff" ${K}/><path d="M36 52 L50 12 L64 52Z" fill="#e84a5f" ${K}/>` +
    `<circle cx="45" cy="57" r="1.8" fill="#2b2f45"/><circle cx="55" cy="57" r="1.8" fill="#2b2f45"/><circle cx="50" cy="61" r="2.5" fill="#ff9b8f"/>`),
  "spielzeug-planschbecken": svg(
    `<ellipse cx="50" cy="82" rx="46" ry="16" fill="#ff8fb1" ${K}/><ellipse cx="50" cy="78" rx="38" ry="11" fill="#5fc8f0" ${K}/>` +
    `<path d="M24 78 Q34 74 44 78 T64 78 T80 77" stroke="#fff" stroke-width="2" fill="none" opacity=".8"/>` +
    `<circle cx="64" cy="74" r="5" fill="#ffd54f" ${K}/><path d="M68 71 l4 -2" stroke="#ff8f3a" stroke-width="2.5" stroke-linecap="round"/>`),
  "moebel-blumenbeet": svg(
    `<path d="M8 100 L14 80 H86 L92 100Z" fill="#8a5a3a" ${K}/>` +
    [[22, "#ff5f7a"], [38, "#ffd54f"], [54, "#b48cf0"], [70, "#ff8fb1"], [84, "#ff9b3d"]].map(([x, f], i) =>
      `<path d="M${x} 80 V${54 - (i % 2) * 8}" stroke="#3f9a4f" stroke-width="2.5"/><path d="M${x} ${68 - (i % 2) * 4} q-6 -2 -8 -8 q6 0 8 6" fill="#5fbf6a"/>` +
      `<circle cx="${x}" cy="${50 - (i % 2) * 8}" r="7" fill="${f}" ${K}/><circle cx="${x}" cy="${50 - (i % 2) * 8}" r="2.5" fill="#fff6c8"/>`).join("")),
  "spielzeug-sandkasten": svg(
    `<path d="M4 98 L12 76 H88 L96 98Z" fill="#c98a4f" ${K}/><path d="M14 80 H86 L90 92 H10Z" fill="#f2d48a"/>` +
    `<path d="M30 86 q8 -12 16 0Z" fill="#e6c070" ${K}/><path d="M62 74 l10 -22" stroke="#e84a5f" stroke-width="3" stroke-linecap="round"/>` +
    `<path d="M70 50 h8 l-2 8 h-4Z" fill="#e84a5f" ${K}/><path d="M50 86 h16 l-3 8 h-10Z" fill="#3f7be0" ${K}/>`),
  /* ---------------- Sonnenzimmer */
  "moebel-sessel": svg(
    `<rect x="12" y="38" width="76" height="40" rx="14" fill="#5f8fd8" ${K}/><rect x="8" y="58" width="20" height="32" rx="8" fill="#4a78c2" ${K}/>` +
    `<rect x="72" y="58" width="20" height="32" rx="8" fill="#4a78c2" ${K}/><rect x="24" y="66" width="52" height="20" rx="6" fill="#74a3ea" ${K}/>` +
    `<path d="M16 90 V98 M84 90 V98" stroke="#6b4a2f" stroke-width="5" stroke-linecap="round"/><circle cx="50" cy="52" r="5" fill="#ffd54f" opacity=".8"/>`),
  "moebel-stehlampe": svg(
    `<ellipse cx="50" cy="97" rx="16" ry="3.5" fill="#2b2f45"/><rect x="48" y="26" width="4" height="70" fill="#d8b46a" ${K}/>` +
    `<path d="M30 30 L38 4 H62 L70 30Z" fill="#fff1c2" ${K}/><path d="M30 30 L38 4 H62 L70 30Z" fill="#ffd54f" opacity=".35"/>` +
    `<ellipse cx="50" cy="31" rx="14" ry="3" fill="#ffe9a8" opacity=".9"/>`),
  "moebel-teppich": svg(
    `<ellipse cx="50" cy="88" rx="48" ry="11" fill="#e8708a" ${K}/><ellipse cx="50" cy="88" rx="36" ry="7.5" fill="#ffd1dc"/>` +
    `<ellipse cx="50" cy="88" rx="22" ry="4.5" fill="#f0a0b4"/>`),
  /* ---------------- Kinderzimmer */
  "moebel-spielkiste": svg(
    `<rect x="12" y="44" width="76" height="54" rx="5" fill="#ff9b3d" ${K}/><path d="M12 56 H88" stroke="#2b2f45" stroke-width="2.5"/>` +
    `<rect x="40" y="62" width="20" height="10" rx="3" fill="#c96f20"/><path d="M26 44 q4 -14 14 -6" fill="#e84a5f" ${K}/>` +
    `<circle cx="64" cy="38" r="9" fill="#5fc8f0" ${K}/><path d="M64 29 v18 M55 38 h18" stroke="#fff" stroke-width="1.5"/>` +
    `<rect x="44" y="30" width="10" height="14" rx="2" fill="#ffd54f" ${K}/>`),
  "moebel-nachttisch": svg(
    `<rect x="18" y="40" width="64" height="52" rx="5" fill="#c98a5b" ${K}/><path d="M18 62 H82" stroke="#2b2f45" stroke-width="2.5"/>` +
    `<circle cx="50" cy="52" r="2.5" fill="#2b2f45"/><circle cx="50" cy="76" r="2.5" fill="#2b2f45"/>` +
    `<path d="M24 92 V99 M76 92 V99" stroke="#8a5a3a" stroke-width="5" stroke-linecap="round"/>` +
    `<path d="M40 40 L44 26 H56 L60 40Z" fill="#fff1c2" ${K}/><rect x="48" y="22" width="4" height="5" fill="#d8b46a"/>`),
  /* ---------------- Küche (6.9.58) */
  "moebel-esstisch": svg(
    `<rect x="6" y="40" width="88" height="10" rx="3" fill="#c98a5b" ${K}/><path d="M6 44 H94" stroke="#e8b07a" stroke-width="2"/>` +
    `<path d="M16 50 V98 M84 50 V98" stroke="#8a5a3a" stroke-width="6" stroke-linecap="round"/>` +
    `<path d="M16 50 V98 M84 50 V98" stroke="#2b2f45" stroke-width="1.5" fill="none" opacity=".4"/>` +
    `<ellipse cx="34" cy="37" rx="11" ry="3.5" fill="#fff" ${K}/><ellipse cx="66" cy="37" rx="11" ry="3.5" fill="#fff" ${K}/>` +
    `<path d="M48 22 h6 v14 h-6Z" fill="#7fdcff" ${K}/><circle cx="66" cy="34" r="3" fill="#ff5f7a"/>`),
  "moebel-obstkorb": svg(
    `<circle cx="36" cy="60" r="12" fill="#ff5f5f" ${K}/><path d="M36 48 q2 -6 6 -7" stroke="#6b4a2f" stroke-width="2.5" fill="none"/>` +
    `<path d="M50 44 q10 -6 18 2 q-4 14 -18 18 q-8 -10 0 -20Z" fill="#ffd54f" ${K}/>` +
    `<circle cx="64" cy="62" r="11" fill="#ff9b3d" ${K}/><circle cx="50" cy="62" r="7" fill="#7a3fb0" ${K}/>` +
    `<path d="M14 66 H86 L78 96 H22Z" fill="#d8a05a" ${K}/><path d="M18 76 H82 M21 86 H79" stroke="#a8743a" stroke-width="2.5"/>` +
    `<path d="M30 66 L34 96 M50 66 V96 M70 66 L66 96" stroke="#a8743a" stroke-width="2"/>`),
  "spielzeug-kuchen": svg(
    `<ellipse cx="50" cy="94" rx="40" ry="5" fill="#e6ebf5" ${K}/><rect x="16" y="56" width="68" height="36" rx="6" fill="#ffb3c7" ${K}/>` +
    `<path d="M16 66 q8 8 17 0 q8 8 17 0 q8 8 17 0 q8 8 17 0 V60 H16Z" fill="#fff" ${K}/><path d="M16 78 H84" stroke="#ff7fa3" stroke-width="3"/>` +
    [30, 50, 70].map((x) => `<rect x="${x - 2.5}" y="36" width="5" height="20" rx="1.5" fill="#7fdcff" ${K}/>` +
      `<path d="M${x} 24 q5 6 0 11 q-5 -5 0 -11Z" fill="#ffd54f" stroke="#ff9b3d" stroke-width="1.5"/>`).join("") +
    `<circle cx="28" cy="84" r="2" fill="#5fd38a"/><circle cx="50" cy="86" r="2" fill="#ffd54f"/><circle cx="72" cy="84" r="2" fill="#7fdcff"/>`),
  /* ---------------- Spielzimmer (6.9.58) */
  "spielzeug-schaukelpferd": svg(
    `<path d="M8 90 Q50 108 92 90" stroke="#c96f20" stroke-width="6" fill="none" stroke-linecap="round"/>` +
    `<path d="M30 92 L36 70 M70 92 L64 70" stroke="#8a5a3a" stroke-width="5" stroke-linecap="round"/>` +
    `<path d="M26 72 Q24 54 44 54 H66 Q74 54 72 64 L70 72Z" fill="#f2f2f2" ${K}/>` +
    `<path d="M64 56 L70 26 Q84 22 90 34 L86 42 Q80 40 76 44 L72 58Z" fill="#f2f2f2" ${K}/>` +
    `<path d="M70 26 Q60 30 62 50" stroke="#ff7a59" stroke-width="6" fill="none" stroke-linecap="round"/>` +
    `<circle cx="80" cy="32" r="2" fill="#2b2f45"/><path d="M40 54 h20 v10 h-20Z" fill="#e84a5f" ${K}/>` +
    `<path d="M26 64 Q14 60 12 70" stroke="#ff7a59" stroke-width="5" fill="none" stroke-linecap="round"/>`),
  "spielzeug-zelt": svg(
    `<path d="M6 98 L50 10 L94 98Z" fill="#ff8f3a" ${K}/><path d="M50 10 L28 98 H72Z" fill="#ffd54f" ${K}/>` +
    `<path d="M50 40 L40 98 H60Z" fill="#5a3d8a"/><path d="M50 40 L40 98 M50 40 L60 98" stroke="#2b2f45" stroke-width="2"/>` +
    `<path d="M50 10 V2" stroke="#2b2f45" stroke-width="2.5"/><path d="M50 2 L62 6 L50 10Z" fill="#e84a5f" stroke="#2b2f45" stroke-width="1.5"/>` +
    `<circle cx="20" cy="84" r="2.5" fill="#fff"/><circle cx="80" cy="84" r="2.5" fill="#fff"/><circle cx="30" cy="66" r="2.5" fill="#fff"/><circle cx="70" cy="66" r="2.5" fill="#fff"/>`),
  "spielzeug-rutsche": svg(
    `<path d="M14 98 V24 M30 98 V24" stroke="#3f7be0" stroke-width="5" stroke-linecap="round"/>` +
    [36, 52, 68, 84].map((y) => `<path d="M14 ${y} H30" stroke="#3f7be0" stroke-width="4" stroke-linecap="round"/>`).join("") +
    `<rect x="10" y="18" width="26" height="8" rx="3" fill="#ffd54f" ${K}/>` +
    `<path d="M32 22 Q56 26 66 60 Q74 88 96 92 L96 100 Q66 98 58 64 Q50 34 32 32Z" fill="#ff5f7a" ${K}/>` +
    `<path d="M36 27 Q56 32 62 62 Q70 90 94 95" stroke="#ffb3c7" stroke-width="2.5" fill="none"/>`),
};

let liste = null;
/** Gezeichnete PNG-Gegenstände (web/bilder/dinge/liste.json) - einmal geholt */
export async function dingBilderLaden() {
  if (liste) return liste;
  try { liste = new Set((await (await fetch("/bilder/dinge/liste.json")).json()).dinge || []); } catch (_) { liste = new Set(); }
  return liste;
}
export const hatDingBild = (id) => Boolean(liste && liste.has(id));
