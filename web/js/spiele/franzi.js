/* FernsehFranzi 6.9.1 - Franzi als Haustier (eigener Entwurf): ihr Zimmer, Pflege, Minispiele, Sterne-Shop, Schrank, Tagebuch.
 *
 * ← → Reiter · ↑ ↓ wählen · OK machen · STOP zurück.
 * Ruhe im Alltag: Das Zimmer steht still, Franzi bewegt sich nur kurz (Animations-Stufe aus 6.8.12); kein Takt im
 * Hintergrund außer dem Nachladen alle 60 s. Nur Minispiele zeichnen flüssig - und nur, solange sie laufen.
 * Minispiele geben keine Sterne (sie machen Franzi glücklich). Sterne gibt es in „Mein Tag“, ausgeben kann man sie im Shop.
 */
import { el, bild, franzi, kleidungZuSachen, stufe } from "../gemeinsam.js";
import bass from "./bass.js";
import fotoalbum from "./fotoalbum.js";
import { kopf, ton, ereignis, takt, canvasScharf } from "./kern.js";
import { reiter, liste, hinweisZeile } from "./seite.js";
import { raumSzene } from "./franzi-raum.js";
import { musikQuelle, musikSpieler } from "../musik.js";
import { taktFolgen } from "./tanzen.js";
import { DING_SVG, dingBilderLaden, hatDingBild } from "./dinge.js";
import memory from "./memory.js";
import drei from "./drei.js";
import echo from "./echo.js";
import snake from "./snake.js";
import stimmspiele from "./stimmspiele.js";
import huepfen from "./huepfen.js";

const REITER = [["zimmer", "🏠 Zimmer"], ["spielen", "🎮 Spielen"], ["shop", "🛍️ Shop"], ["schrank", "👗 Schrank & Zimmer"], ["tagebuch", "📔 Tagebuch"]];
const AKTIONEN = [["fuettern", "🍎", "Füttern"], ["waschen", "🛁", "Waschen"], ["streicheln", "🤗", "Streicheln"],
                  ["schlafen", "🛏️", "Schlafen legen"], ["ball", "⚽", "Ball spielen"]];
const WERTE = [["hunger", "🍎", "Satt"], ["sauber", "🫧", "Sauber"], ["energie", "⚡", "Energie"], ["glueck", "💛", "Glück"]];
const GESICHT = { froehlich: "froh", anhaenglich: "verliebt", muede: "muede", schlaefrig: "schlaf", vertraeumt: "schlaf",
                  hungrig: "staunen", schmutzig: "staunen", gelangweilt: "staunen", trotzig: "grummelig", unterwegs: "staunen",
                  genervt: "genervt", grummelig: "grummelig" };   /* 6.9.45: neue Gesichter */
/* 6.9.45: Gesicht nach einer Pflege (statt immer Jubel) */
const PFLEGE_GESICHT = { fuettern: "jubel", waschen: "jubel", streicheln: "verliebt", schlafen: "muede", ball: "frech" };
const REAKTION = { fuettern: "Mmmh, lecker! 😋", waschen: "Plitsch, platsch – schön sauber!", streicheln: "Hihi, das kitzelt! 💛",
                   schlafen: "Kurz die Augen zu … ahh, besser!", ball: "Fang! Nochmal, nochmal!" };
const RAUM_NAME = { "raum-zimmer": "Kinderzimmer", "raum-hell": "Sonnenzimmer", "raum-probe": "Proberaum", "raum-garten": "Garten", "raum-kueche": "Küche", "raum-spiel": "Spielzimmer", "raum-bad": "Badezimmer" };
/* 6.9.9: feste Deko je Raum (steht immer da, gehört nicht zum Shop) - [Symbol, Klasse für die Lage] */
const RAUM_DEKO = { "raum-garten": [], "raum-probe": [], "raum-kueche": [], "raum-spiel": [],   /* gezeichnete Räume bringen ihre Deko mit */
                    "raum-bad": [["🛁", "fz-d-wanne"], ["🪞", "fz-d-spiegel"], ["🧼", "fz-d-seife"]],
                    "raum-zimmer": [], "raum-hell": [] };
const RAUM_TIPP = { "raum-kueche": "In der Küche schmeckt's am besten!", "raum-bad": "Im Bad wird man besonders sauber!",
                    "raum-garten": "Im Garten macht Ballspielen doppelt Spaß!", "raum-zimmer": "Im eigenen Bett schläft es sich am besten.",
                    "raum-hell": "Hier scheint die Sonne so schön herein!", "raum-probe": "Auf die Bühne – hier wird Musik gemacht!",
                    "raum-spiel": "Im Spielzimmer macht Streicheln besonders glücklich!" };
/* 6.9.36: Jeder Gegenstand weiß, wohin er gehört und wie groß er ist (Höhe in % der Zimmerhöhe).
   gross = hinten auf dem Boden, klein = vorne neben Franzi, wand = an die Wand, fenster = aufs Fensterbrett (sonst vorne). */
const DING = {
  "spielzeug-musikbox": ["klein", 14],                     /* 6.9.50 */
  /* 6.9.55: Gegenstände je Raum */
  "moebel-mikrofon": ["gross", 30], "spielzeug-keyboard": ["gross", 22], "moebel-verstaerker": ["klein", 16], "moebel-discokugel": ["wand", 14],
  "moebel-gartenzwerg": ["klein", 14], "spielzeug-planschbecken": ["gross", 20], "moebel-blumenbeet": ["klein", 16], "spielzeug-sandkasten": ["gross", 20],
  "moebel-sessel": ["gross", 24], "moebel-stehlampe": ["gross", 36], "moebel-teppich": ["klein", 22], "moebel-spielkiste": ["klein", 14],
  "moebel-nachttisch": ["klein", 16],
  "moebel-esstisch": ["gross", 20], "moebel-obstkorb": ["klein", 11], "spielzeug-kuchen": ["klein", 12],
  "spielzeug-trommel": ["klein", 12], "spielzeug-hase": ["klein", 12], "spielzeug-kreisel": ["klein", 8], "spielzeug-zug": ["klein", 9],
  "spielzeug-buch": ["klein", 7], "moebel-girlande": ["wand", 12], "moebel-rahmen": ["wand", 14], "moebel-kissen": ["klein", 9],
  "moebel-hochbeet": ["gross", 22],
  "spielzeug-schaukelpferd": ["klein", 20], "spielzeug-zelt": ["gross", 30], "spielzeug-rutsche": ["gross", 28],
  "moebel-bett": ["gross", 30], "moebel-lampe": ["gross", 24], "spielzeug-schaukel": ["gross", 28], "spielzeug-gitarre": ["gross", 24],
  "moebel-aquarium": ["gross", 18], "moebel-pflanze": ["fenster", 13], "moebel-bild": ["wand", 15], "spielzeug-drachen": ["wand", 17],
  "spielzeug-ball": ["klein", 11], "spielzeug-teddy": ["klein", 13], "spielzeug-rakete": ["klein", 14], "spielzeug-ballon": ["klein", 15],
  "spielzeug-puzzle": ["klein", 9], "moebel-regal": ["gross", 30], "moebel-badeente": ["klein", 9],
};
/* 6.9.55: gezeichnete Gegenstände - PNG aus web/bilder/dinge (wenn vorhanden), sonst SVG aus dinge.js, sonst 3D-Symbol */
dingBilderLaden();
let dingNacht = false;
function dingBild(k) {
  /* 6.9.60: Nachttisch-Lampe leuchtet nur nachts */
  const datei = k.id === "moebel-nachttisch" && !dingNacht ? "moebel-nachttisch-aus" : k.id;
  if (hatDingBild(k.id)) return el("img", { class: "fz-ding-png", src: `/bilder/dinge/${datei}.png`, alt: "" });
  if (!DING_SVG[k.id]) return bild(k.symbol);
  const b = el("span", { class: "fz-ding-svg" });
  b.innerHTML = DING_SVG[k.id];                     /* fester Inhalt aus diesem Modul */
  return b;
}
/* 6.9.56: was ein Gegenstand Besonderes kann (Shop-Vorschau) */
const BESCHREIBUNG = {
  "spielzeug-musikbox": "Spielt Musik aus deinem Musik-Archiv – und Franzi tanzt dazu mit Discolicht! 💃",
  "spielzeug-ball": "Damit kannst du mit Franzi Ball spielen.", "moebel-bett": "Hier schläft Franzi am besten.",
  "spiel-memory": "Merkspiel: Finde die Paare.", "spiel-dreigewinnt": "Drei in eine Reihe – gegen Franzi.",
  "spiel-simon": "Farben-Echo: Merk dir die Reihenfolge der Farben.", "spiel-snake": "Sammle Futter, werde immer länger.",
  "spiel-stimme": "Spiele mit deiner Stimme (Mikrofon): Möwenflug, Drache und Ton-Kanone.", "spiel-huepfen": "Laufen, springen, Sterne sammeln mit Franzi.",
  "raum-hell": "Ein heller Raum mit zwei großen Fenstern.", "raum-probe": "Eine Bühne mit Schlagzeug und Boxen – hier wird Musik gemacht!",
  "raum-garten": "Draußen auf der Terrasse, mit Blick aufs Meer.", "raum-bad": "Im Bad wird Franzi besonders sauber.",
  "raum-kueche": "Eine gemütliche Küche mit Herd – hier schmeckt das Essen am besten.",
  "raum-spiel": "Ein grünes Spielzimmer mit Bauklötzen und Eisenbahn – hier kuschelt Franzi am liebsten.",
  "spielzeug-trommel": "Bumm, bumm – zum Krachmachen.", "spielzeug-hase": "Ein weicher Hase zum Kuscheln.",
  "spielzeug-kreisel": "Dreht sich und dreht sich …", "spielzeug-zug": "Eine kleine Eisenbahn aus Holz.",
  "spielzeug-buch": "Ein Buch mit vielen Bildern.", "moebel-girlande": "Bunte Fähnchen für die Wand – wie bei einer Party.",
  "moebel-rahmen": "Ein Bilderrahmen für die Wand.", "moebel-kissen": "Ein weiches Kissen – gern aufs Bett legen.",
  "moebel-hochbeet": "Hier wächst Gemüse für Franzi.",
  "moebel-esstisch": "Ein Tisch zum gemeinsamen Essen.", "moebel-obstkorb": "Frisches Obst – gesund und lecker.",
  "spielzeug-kuchen": "Ein Kuchen mit Kerzen – für Geburtstage und Feste.", "spielzeug-schaukelpferd": "Hü-hott! Zum Schaukeln.",
  "spielzeug-zelt": "Ein kleines Zelt zum Verstecken und Kuscheln.", "spielzeug-rutsche": "Eine kleine Rutsche – wieeeh!",
  "moebel-discokugel": "Glitzert an der Decke – passt super zur Musikbox.", "spielzeug-planschbecken": "Zum Planschen an warmen Tagen.",
  "moebel-stehlampe": "Macht es gemütlich hell.", "moebel-teppich": "Weich unter den Füßen – kommt auf den Boden.",
};
/* 6.9.59/6.9.60: Gegenstände im Zimmer starten passende Spiele und Seiten (zusätzlich zu den Kacheln) */
const DING_AKTIONEN = [
  { ding: "moebel-mikrofon", spiel: "spiel-stimme", symbol: "🎤", titel: "Ins Mikrofon singen" },
  { ding: "spielzeug-gitarre", spiel: "spiel-bass", symbol: "🎸", titel: "Gitarre spielen" },
  { ding: "spielzeug-keyboard", spiel: "spiel-bass", symbol: "🎹", titel: "Keyboard spielen" },
  { ding: "spielzeug-trommel", spiel: "spiel-simon", symbol: "🥁", titel: "Trommel-Echo (Töne nachspielen)" },
  { ding: "spielzeug-puzzle", spiel: "spiel-memory", symbol: "🧩", titel: "Bilder-Memory" },
  { ding: "moebel-rahmen", spiel: "spiel-fotoalbum", symbol: "🖼️", titel: "Fotos ansehen" },
];
const OHNE_FREUDE = new Set(["spiel-fotoalbum"]);          /* Seiten, keine Spiele: Franzi zählt sie nicht als gespielt */
const EINGEBAUT = { "spiel-fotoalbum": fotoalbum, "spiel-bass": bass, "spiel-memory": memory, "spiel-dreigewinnt": drei, "spiel-simon": echo, "spiel-snake": snake, "spiel-stimme": stimmspiele, "spiel-huepfen": huepfen };
const ART_NAME = { spiel: "Spiel", raum: "Raum", kleidung: "Kleidung", spielzeug: "Spielzeug", moebel: "Möbel" };

export default {
  symbol: "🐾",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "🐾 Franzi", "← → Reiter · ↑ ↓ wählen · OK machen · STOP zurück");
    box.classList.add("franzi-haus");
    const z = { d: null, reiter: 0, wahl: 0, satz: "", jubel: 0, kaufen: null, spiel: null, fehler: "" };

    async function lade(besuch = false) {
      try {
        z.d = await api.hole("/api/franzi" + (besuch ? "?besuch=1" : ""));
        if (besuch && z.d.satz) z.satz = z.d.satz;
        z.fehler = "";
      } catch (e) { z.fehler = e.message || "Franzi ist gerade nicht erreichbar."; }
      zeige();
    }
    async function sende(pfad, daten, danach) {
      try {
        z.d = await api.sende(pfad, daten);
        if (z.d.satz) z.satz = z.d.satz;
        danach?.();
        if (z.jubel > Date.now()) setTimeout(() => { if (z.jubel <= Date.now()) zeige(); }, z.jubel - Date.now() + 100);
      } catch (e) { api.hinweis(e.message || "Das ging gerade nicht."); ton("fehler"); }
      zeige();
    }

    /* ---------------------------------------------------------------- Einträge je Reiter */
    const art = () => REITER[z.reiter][0];
    function eintraege() {
      const d = z.d;
      if (!d) return [];
      if (art() === "zimmer" && z.tanz?.alben) return [{ tanz: "zufall", symbol: "🔀", titel: "Alles zufällig" },
        ...z.tanz.alben.map((a) => ({ tanz: "album", pfad: a.pfad, symbol: "💿", titel: a.name })), { tanz: "zurueck", symbol: "‹", titel: "Zurück" }];
      if (art() === "zimmer" && z.tanz?.spieler) {
        const p = z.tanz.spieler.audio.paused;
        return [{ tanz: "pause", symbol: p ? "▶️" : "⏸️", titel: p ? "Weiter tanzen" : "Pause" }, { tanz: "weiter", symbol: "⏭️", titel: "Nächstes Lied" },
                { tanz: "auswahl", symbol: "💿", titel: "Andere Musik" }, { tanz: "aus", symbol: "⏹️", titel: "Musik aus" }];
      }
      if (art() === "zimmer") return [...AKTIONEN.filter(([a]) => a !== "ball" || d.besitz.includes("spielzeug-ball"))
        .map(([a, s, t]) => ({ id: a, symbol: s, titel: t })),
        ...(d.musikbox ? [{ id: "musik", symbol: "🎶", titel: "Musik & tanzen" }] : []),
        /* 6.9.59: Mikrofon und Gitarre im Zimmer starten die Stimm- und Bass-Spiele (zusätzlich zu den Kacheln) */
        ...DING_AKTIONEN.filter((x) => d.besitz.includes(x.ding)).map((x) => ({ spiel: x.spiel, symbol: x.symbol, titel: x.titel })),
        ...(zimmerDinge().length ? [{ anfassen: true, symbol: "👆", titel: "Etwas anfassen" }] : [])];
      if (art() === "spielen") return d.katalog.filter((k) => k.art === "spiel" && k.hat)
        .map((k) => ({ id: k.id, symbol: k.symbol, titel: k.name, rechts: d.rekorde[k.id] ? `Rekord ${d.rekorde[k.id]}` : "" }));
      if (art() === "shop") return [
        ...d.angebote.map((a) => ({ angebot: a.nr, symbol: a.symbol, titel: a.name, preis: a.preis,
                                    zeile: a.minuten ? `${a.minuten} Minuten${a.art === "wochenende" ? " · nur am Wochenende" : a.art === "sperrzeit" ? " · auch in der Pause" : ""}` : "von Mama oder Papa",
                                    rechts: `${a.preis} ⭐` + (a.noch === 0 ? " · diese Woche schon" : "") })),
        ...d.katalog.filter((k) => !k.hat && !k.level).map((k) => ({ item: k.id, symbol: k.symbol, titel: k.name, preis: k.preis,
                                                          zeile: ART_NAME[k.art] + ((k.nur_in || []).length ? ` · für ${k.nur_in.map((r) => RAUM_NAME[r] || r).join(" und ")}` : ""),
                                                          rechts: `${k.preis} ⭐` })),
        /* 6.9.37: Level-Belohnungen stehen am Ende, nicht käuflich (bis Level 4 Gegenstände, danach Räume) */
        ...d.katalog.filter((k) => !k.hat && k.level).sort((a, b) => a.level - b.level)
          .map((k) => ({ stufe: k.level, vorschauId: k.id, symbol: k.symbol, titel: k.name, zeile: `${ART_NAME[k.art]} · Belohnung`,
                         tage: Math.max(0, (k.tage || 0) - (d.sammeltage || 0)),
                         rechts: `🔒 Level ${k.level}` + ((k.tage || 0) > (d.sammeltage || 0) ? ` · noch ${(k.tage || 0) - (d.sammeltage || 0)} Tage` : "") }))];
      if (art() === "schrank") {
        const hat = (a) => d.katalog.filter((k) => k.art === a && k.hat);
        const steht = (id) => Array.isArray((d.zimmer || {})[id]);
        return [
          ...hat("raum").map((k) => ({ raum: k.id, symbol: k.symbol, titel: k.name, rechts: d.raum === k.id ? "✔ hier" : "hingehen" })),
          ...hat("kleidung").map((k) => ({ kleid: k.id, symbol: k.symbol, titel: k.name, rechts: d.angezogen.includes(k.id) ? "✔ an" : "anziehen" })),
          ...[...hat("moebel"), ...hat("spielzeug")].map((k) => ({ ding: k.id, symbol: k.symbol, titel: k.name,
                                                                    rechts: steht(k.id) ? "✔ verschieben" :
                                                                      (k.nur_in || []).length && !k.nur_in.includes(d.raum) ? `nur ${RAUM_NAME[k.nur_in[0]] || ""}` : "hinstellen" }))];
      }
      const album = (d.postkarten || []).length ? [{ album: true, symbol: "📮", titel: `Postkarten-Album (${d.postkarten.length})`, zeile: "OK = ansehen" }] : [];
      return [...album, ...d.tagebuch.map((t) => ({ symbol: { hallo: "👋", reise: "🧳", wieder: "🎨", spiel: "🎮", neu: "🎁", angebot: "⭐", ereignis: "✨", geschenk: "🎁" }[t.art] || "📔",
                                       titel: t.text, zeile: t.zeit.slice(8, 10) + "." + t.zeit.slice(5, 7) + ". " + t.zeit.slice(11, 16) }))];
    }

    /* ---------------------------------------------------------------- 6.9.49: Postkarten (Vorderseite, OK dreht) */
    const datumText = (iso) => { const [j, m, t] = String(iso || "").split("-"); return t ? `${+t}.${+m}.${j}` : ""; };
    function postkarteKnoten(k, hinten) {
      const vorn = el("div", { class: "pk-seite pk-vorn" }, el("img", { src: `/bilder/postkarten/${k.karte}.jpg`, alt: "" }));
      const stempel = el("div", { class: "pk-stempel" }, el("b", { text: (k.gruss_aus || "").replace(/^(aus|vom) (dem |den )?/, "") }), el("small", { text: datumText(k.datum) }));
      const rueck = el("div", { class: "pk-seite pk-hinten" }, el("img", { class: "pk-papier", src: "/bilder/postkarten/rueckseite.png", alt: "" }),
        el("div", { class: "pk-text" }, el("p", { class: "pk-anrede", text: z.d?.kind ? `Hallo ${z.d.kind}!` : "Hallo du!" }),
          el("p", { text: k.text || "" }), el("p", { class: "pk-gruss", text: `Viele Grüße ${k.gruss_aus || ""}!` }), el("p", { class: "pk-name", text: "Deine Franzi 💛" })),
        el("img", { class: "pk-marke", src: `/bilder/postkarten/marke-${k.marke || 1}.png`, alt: "" }), stempel,
        el("div", { class: "pk-an" }, el("span", { text: "An" }), el("b", { text: z.d?.kind || "mein liebstes Kind" }), el("span", { text: "Franzis Zimmer" })));
      return el("div", { class: "pk-karte" + (hinten ? " gedreht" : "") }, el("div", { class: "pk-innen" }, vorn, rueck));
    }
    function zeigeKarte() {
      const k = z.karte;
      if (!k) { inhalt.querySelector(".pk-ansicht")?.remove(); return; }
      const karte = k.liste[k.i];
      const hilfe = k.abenteuer ? (k.hinten ? "OK: Franzi kommt heim" : "OK: Karte umdrehen") :
        `OK umdrehen · ← → blättern (${k.i + 1} von ${k.liste.length}) · STOP zurück`;
      const alt = inhalt.querySelector(".pk-ansicht");
      const neu = el("div", { class: "pk-ansicht" }, postkarteKnoten(karte, k.hinten), el("div", { class: "pk-hilfe", text: hilfe }));
      if (alt) alt.replaceWith(neu); else inhalt.append(neu);
    }
    function karteOeffnen(liste, i = 0, abenteuer = false) { z.karte = { liste, i, hinten: false, abenteuer }; zeigeKarte(); ton("ok"); }
    function karteTaste(t) {
      const k = z.karte;
      if (t === "Enter" || t === " ") {
        if (!k.hinten) {
          k.hinten = true;
          const knoten = inhalt.querySelector(".pk-karte");
          if (knoten) { knoten.classList.add("gedreht"); inhalt.querySelector(".pk-hilfe").textContent = k.abenteuer ? "OK: Franzi kommt heim" : inhalt.querySelector(".pk-hilfe").textContent; }
          ton("bewegen");
        } else if (k.abenteuer) { z.karte = null; zeigeKarte(); lade(true); ton("sieg"); }
        else { k.hinten = false; zeigeKarte(); ton("bewegen"); }
        return true;
      }
      if (!k.abenteuer && (t === "ArrowLeft" || t === "ArrowRight")) {
        k.i = (k.i + (t === "ArrowLeft" ? k.liste.length - 1 : 1)) % k.liste.length; k.hinten = false; zeigeKarte(); ton("bewegen"); return true;
      }
      if (t === "Escape" || t === "Backspace") { if (k.abenteuer) return true; z.karte = null; zeigeKarte(); ton("bewegen"); return true; }
      return true;
    }

    /* ---------------------------------------------------------------- Zeichnen */
    let szeneSpeicher = {};
    /* 6.9.56: Vorschau im Shop - was gewählt ist, erscheint im Zimmer (Kleidung an Franzi, Möbel im Raum, ein neuer Raum
       als Ansicht), dazu ein Kasten, was es kann. Erst sehen, dann kaufen. */
    function shopVorschau(d) {
      if (art() !== "shop" || z.einrichten || z.jubel > Date.now()) return null;   /* nach dem Kauf erst Franzis Danke */
      const x = eintraege()[z.wahl];
      const id = x?.item || x?.vorschauId;
      return id ? d.katalog.find((k) => k.id === id) || null : null;
    }
    function vorschauText(k) {
      const extra = BESCHREIBUNG[k.id] || { raum: "Ein neuer Raum zum Einrichten.", kleidung: "Franzi kann es anziehen.",
        spiel: "Ein Minispiel, das du mit Franzi spielen kannst.", moebel: "Kannst du im Zimmer aufstellen.", spielzeug: "Kannst du im Zimmer aufstellen." }[k.art] || "";
      const wo = (k.nur_in || []).length ? ` Passt in: ${k.nur_in.map((r) => RAUM_NAME[r] || r).join(" und ")}.` : "";
      const preis = k.level ? `Belohnung für Level ${k.level}` : `${k.preis} ⭐`;
      return `👀 ${k.name} – ${extra}${wo} (${preis})`;
    }
    function zimmerBild(d) {
      const vorschau = shopVorschau(d);
      const raumId = vorschau?.art === "raum" ? vorschau.id : d.raum;
      const stimmung = d.abenteuer ? "unterwegs" : d.stimmung;
      const gesicht = z.jubel > Date.now() ? (z.jubelGesicht || "jubel") : vorschau ? "staunen" : GESICHT[stimmung] || "froh";
      const raum = el("div", { class: "fz-raum" + (vorschau ? " fz-mit-vorschau" : ""), "data-raum": raumId, "data-nacht": d.nacht ? "1" : "0" });
      /* 6.9.15: gezeichnete Szene (einmal je Raum/Tageszeit/Wetter erzeugt, dann aus dem Zwischenspeicher) */
      const schluessel = `${raumId}|${d.nacht}|${d.wetter}`;
      if (szeneSpeicher.schluessel !== schluessel) szeneSpeicher = { schluessel, svg: raumSzene(raumId, { nacht: d.nacht, wetter: d.wetter }) };
      const hinten = el("div", { class: "fz-szene-box" });
      hinten.innerHTML = szeneSpeicher.svg;                    /* fester Inhalt aus franzi-raum.js */
      raum.append(hinten);
      for (const [symbol, lage] of RAUM_DEKO[raumId] || []) raum.append(el("div", { class: "fz-deko " + lage }, bild(symbol)));
      /* 6.9.54: Gegenstände frei im Raum - [x, y, Reihenfolge]; zuletzt gestellt liegt vorne (Teddy aufs Bett).
         Was ganz vorne steht (y klein), steht vor Franzi, alles andere dahinter. Beim Einrichten folgt eins den Pfeilen. */
      dingNacht = Boolean(d.nacht);
      const lagen = vorschau?.art === "raum" ? [] : Object.entries(d.zimmer || {}).filter(([, v]) => Array.isArray(v));
      if (vorschau && (vorschau.art === "moebel" || vorschau.art === "spielzeug") && !lagen.some(([id]) => id === vorschau.id)) {
        const [art_] = DING[vorschau.id] || ["klein"];
        lagen.push([vorschau.id, art_ === "wand" ? [62, 55, 1e9] : art_ === "gross" ? [74, 14, 1e9] : [72, 4, 1e9]]);
      }
      if (z.einrichten && !lagen.some(([id]) => id === z.einrichten.id)) lagen.push([z.einrichten.id, [z.einrichten.x, z.einrichten.y, 1e9]]);
      lagen.sort((a, b) => a[1][2] - b[1][2]).forEach(([id, [x0, y0]], rang) => {
        const k = d.katalog.find((x) => x.id === id);
        if (!k) return;
        const einrichten_ = z.einrichten?.id === id;
        const aktiv = einrichten_ || vorschau?.id === id || z.anfassen?.id === id;   /* leuchtet: Einrichten, Vorschau, Anfassen */
        const [x, y] = einrichten_ ? [z.einrichten.x, z.einrichten.y] : [x0, y0];
        const hoehe = (DING[id] || ["klein", 11])[1];
        const ebene = (y < 9 ? 20 : 1) + Math.min(rang, 15) + (aktiv ? 30 : 0);
        const png = hatDingBild(id);
        const offen = id === "moebel-spielkiste" && z.effekt?.id === id;           /* 6.9.63: Kiste geht beim Anfassen auf */
        const inhalt_ = offen && png ? el("img", { class: "fz-ding-png", src: "/bilder/dinge/moebel-spielkiste-offen.png", alt: "" }) : dingBild(k);
        const fische = id === "moebel-aquarium" && png ? el("div", { class: "fz-fische" + (z.effekt?.id === id ? " schnell" : "") },
          ...["blau", "orange", "gruen"].map((f) => el("img", { class: "fz-fisch " + f, src: `/bilder/dinge/fisch-${f}.png`, alt: "" }))) : null;
        raum.append(el("div", { class: "fz-ding" + (id === "moebel-aquarium" && !png ? " fz-aquarium" : "") + (aktiv ? " fz-einrichten" : "") +
                                (z.effekt?.id === id ? " fz-effekt" : ""), "data-ding": id,
                                style: `font-size:${hoehe}cqh;left:${x}%;bottom:${y}%;z-index:${ebene}` }, inhalt_, fische));
      });
      if (d.ereignis?.symbol) raum.append(el("div", { class: "fz-ereignis" }, bild(d.ereignis.symbol)));
      if (d.abenteuer) raum.append(el("div", { class: "fz-postkarte" }, d.abenteuer.postkarte ? el("img", { src: `/bilder/postkarten/${d.abenteuer.postkarte.karte}.jpg`, alt: "" }) : bild("🧳"),
                                      el("div", { text: `Postkarte ${d.abenteuer.ort}` })));
      else {
        /* 6.9.5: Wetter zieht Franzi an - nur, was das Kind nicht selbst gewählt hat */
        const sachen = kleidungZuSachen(vorschau?.art === "kleidung" ? [...d.angezogen, vorschau.id] : d.angezogen);
        if (d.wetter === "kalt" || d.wetter === "schnee") sachen.extra = sachen.extra || "schal";
        if (d.wetter === "sonne" && !d.nacht) sachen.brille = sachen.brille || "sonne";
        if (z.tanz?.spieler && !z.tanz.spieler.audio.paused) {
          /* 6.9.50: Franzi tanzt - drei Haltungen, je Schlag die nächste; dazu Discolicht */
          raum.append(el("div", { class: "fz-disco" }));
          /* 6.9.60: Discokugel im Raum wirft Lichtpunkte, die sich drehen */
          const kugel = lagen.find(([id]) => id === "moebel-discokugel");
          if (kugel) raum.append(el("div", { class: "fz-kugellicht", style: `left:${kugel[1][0]}%;bottom:${kugel[1][1] + 12}%` }));
          /* 6.9.60: Hat Franzi eine Gitarre, spielt sie mit (Anschlag und Greifhand animiert) */
          const mitGitarre = d.besitz.includes("spielzeug-gitarre") ? { ...sachen, gitarre: true } : sachen;
          raum.append(el("div", { class: "fz-franzi fz-tanzt " + (z.tanz.bewegung || "huepf") },
            ...["jubel", "frech", "verliebt"].map((g, i) => el("div", { class: "fz-tanz-haltung" + (i === (z.tanz.haltung || 0) ? " an" : "") }, franzi(g, "fz-figur", mitGitarre)))));
        } else {
          raum.append(el("div", { class: "fz-franzi" }, franzi(gesicht, "fz-figur", sachen),
            d.wetter === "regen" ? el("div", { class: "fz-schirm" }, bild("☂️")) : null));
        }
      }
      raum.append(vorschau ? el("div", { class: "fz-blase fz-vorschau-text", text: vorschauText(vorschau) })
                           : el("div", { class: "fz-blase", text: z.satz || d.satz }));
      return raum;
    }
    function werteLeiste(d) {
      return el("div", { class: "fz-werte" }, ...WERTE.map(([k, s, t]) =>
        el("div", { class: "fz-wert" + (d.werte[k] < 25 ? " niedrig" : "") }, bild(s),
          el("span", { class: "fz-wert-name", text: t }),
          el("span", { class: "fz-balken" }, el("span", { style: `width:${d.werte[k]}%` })))),
        d.typ ? el("div", { class: "fz-typ", text: `✨ ${d.typ}` }) : null);
    }
    function zeige() {
      if (z.spiel) return;
      const d = z.d;
      if (z.fehler) { inhalt.replaceChildren(hinweisZeile(z.fehler, "😴")); return; }
      if (!d) { inhalt.replaceChildren(hinweisZeile("Franzi kommt …")); return; }
      punkte.textContent = `⭐ ${d.sterne}`;
      const e = eintraege();
      z.wahl = Math.min(z.wahl, Math.max(0, e.length - 1));
      const leer = { spielen: "Noch keine Spiele.", shop: "Du hast schon alles! 🎉", schrank: "Noch nichts im Schrank.", tagebuch: "Noch keine Einträge." }[art()];
      const rechts = z.einrichten ? el("div", { class: "fz-seite fz-einrichten-hilfe" },
        el("h3", { text: "🏠 Einrichten" }),
        z.einrichten.menue ? liste([{ symbol: "✔️", titel: "Hier hinstellen" }, { symbol: "🧹", titel: "Wegräumen" }, { symbol: "↔️", titel: "Weiter verschieben" }],
                                   z.einrichten.menue.wahl, { sichtbar: 3 })
          : el("div", { class: "fz-tasten-hilfe" }, el("p", { text: "← ↑ → ↓  verschieben" }), el("p", { text: "OK  fertig oder wegräumen" }),
               el("p", { text: "STOP  abbrechen" }), el("p", { class: "leise", text: "Tipp: Was du zuletzt hinstellst, liegt vorne – so kann der Teddy auf dem Bett sitzen." })))
      : el("div", { class: "fz-seite" },
        art() === "zimmer" ? werteLeiste(d) : null,
        liste(e.map((x, i) => (z.kaufen === i ? { ...x, rechts: "Nochmal OK = kaufen" } : x)), z.wahl,
              { sichtbar: art() === "zimmer" ? 5 : 7, leer, markieren: art() !== "tagebuch" }));
      inhalt.replaceChildren(el("div", { class: "fz-wurzel" }, reiter(REITER.map((r) => r[1]), z.reiter), el("div", { class: "fz-haupt" }, zimmerBild(d), rechts)));
      if (z.karte) zeigeKarte();                          /* 6.9.49: offene Postkarte bleibt beim Neuzeichnen */
    }

    /* ---------------------------------------------------------------- 6.9.54: Einrichten (frei platzieren) */
    const SCHRITT = 2;
    function einrichtenTaste(t) {
      const e = z.einrichten;
      if (e.menue) {                                     /* kleines Menü nach OK: Fertig · Wegräumen · Weiter schieben */
        if (t === "ArrowUp" || t === "ArrowDown") { e.menue.wahl = (e.menue.wahl + (t === "ArrowUp" ? 2 : 1)) % 3; ton("bewegen"); zeige(); return true; }
        if (t === "Enter" || t === " ") {
          const was = e.menue.wahl;
          if (was === 2) { e.menue = null; ton("bewegen"); zeige(); return true; }
          z.einrichten = null;
          if (was === 0) sende("/api/franzi/tun", { aktion: "setzen", item: e.id, x: e.x, y: e.y }, () => { ton("ok"); z.satz = "Schön so!"; });
          else sende("/api/franzi/tun", { aktion: "wegraeumen", item: e.id }, () => { ton("bewegen"); z.satz = "Aufgeräumt!"; });
          return true;
        }
        if (t === "Escape" || t === "Backspace") { e.menue = null; zeige(); return true; }
        return true;
      }
      const d_ = { ArrowLeft: [-SCHRITT, 0], ArrowRight: [SCHRITT, 0], ArrowUp: [0, SCHRITT], ArrowDown: [0, -SCHRITT] }[t];
      if (d_) {
        e.x = Math.max(3, Math.min(97, e.x + d_[0])); e.y = Math.max(0, Math.min(80, e.y + d_[1]));
        const knoten = inhalt.querySelector(`.fz-ding[data-ding="${e.id}"]`);
        if (knoten) { knoten.style.left = e.x + "%"; knoten.style.bottom = e.y + "%"; }      /* ohne Neuzeichnen - flüssig */
        return true;
      }
      if (t === "Enter" || t === " ") { e.menue = { wahl: 0 }; ton("ok"); zeige(); return true; }
      if (t === "Escape" || t === "Backspace") { z.einrichten = null; z.satz = ""; ton("bewegen"); zeige(); return true; }
      return true;
    }

    /* ---------------------------------------------------------------- 6.9.63: Zimmer zum Anfassen */
    /* Was ein Gegenstand beim Anfassen tut: Spiel/Seite, Pflege, Musik - oder eine kleine Überraschung */
    const DING_PFLEGE = { "moebel-bett": "schlafen", "moebel-kissen": "schlafen", "moebel-obstkorb": "fuettern", "moebel-esstisch": "fuettern",
                          "spielzeug-kuchen": "fuettern", "moebel-badeente": "waschen", "spielzeug-ball": "ball", "spielzeug-teddy": "streicheln",
                          "spielzeug-hase": "streicheln" };
    const DING_MUSIK = new Set(["spielzeug-musikbox", "moebel-verstaerker", "moebel-discokugel"]);
    const DING_SATZ = { "moebel-aquarium": "Schau mal, wie die Fische flitzen! 🐠", "moebel-spielkiste": "Oh, so viele Spielsachen!",
                        "moebel-pflanze": "Ich gieße sie – plitsch!", "moebel-blumenbeet": "Hmm, die duften!", "moebel-hochbeet": "Bald gibt's Karotten! 🥕",
                        "spielzeug-zug": "Tschu-tschuuu! 🚂", "spielzeug-kreisel": "Wiiiie er sich dreht!", "spielzeug-buch": "Lies du mir was vor?",
                        "moebel-gartenzwerg": "Psst, der passt auf den Garten auf.", "moebel-stehlampe": "Klick – Licht an!", "moebel-nachttisch": "Klick!",
                        "spielzeug-drachen": "Wenn's windig ist, lassen wir ihn steigen!", "spielzeug-rakete": "3 … 2 … 1 … Start! 🚀",
                        "spielzeug-ballon": "Nicht loslassen!", "moebel-girlande": "Party-Stimmung! 🎉", "spielzeug-planschbecken": "Platsch!",
                        "spielzeug-sandkasten": "Wir bauen eine Sandburg!", "spielzeug-schaukelpferd": "Hü-hott!", "spielzeug-zelt": "Hier ist mein Versteck!",
                        "spielzeug-rutsche": "Wiiiieh!", "spielzeug-schaukel": "Höher, höher!" };
    function zimmerDinge() {
      const d = z.d;
      if (!d || art() !== "zimmer") return [];
      return Object.entries(d.zimmer || {}).filter(([, v]) => Array.isArray(v)).sort((a, b) => a[1][0] - b[1][0]).map(([id]) => id);
    }
    function anfassenTaste(t) {
      const l = zimmerDinge(), a = z.anfassen;
      if (!l.length) { z.anfassen = null; zeige(); return true; }
      if (t === "ArrowLeft" || t === "ArrowRight" || t === "ArrowUp" || t === "ArrowDown") {
        a.i = (l.indexOf(a.id) + (t === "ArrowLeft" || t === "ArrowUp" ? l.length - 1 : 1)) % l.length;
        a.id = l[a.i];
        const k = z.d.katalog.find((x) => x.id === a.id);
        z.satz = k ? `${k.symbol} ${k.name}` : ""; ton("bewegen"); zeige(); return true;
      }
      if (t === "Enter" || t === " ") { dingAnfassen(a.id); return true; }
      if (t === "Escape" || t === "Backspace") { z.anfassen = null; z.satz = ""; ton("bewegen"); zeige(); return true; }
      return true;
    }
    function dingAnfassen(id) {
      const spiel = DING_AKTIONEN.find((x) => x.ding === id);
      if (spiel) { z.anfassen = null; starteSpiel(spiel.spiel); return; }
      if (DING_MUSIK.has(id) && z.d.musikbox) { z.anfassen = null; tanzAktion({ id: "musik" }); return; }
      const pflege = DING_PFLEGE[id];
      if (pflege) { pflegen(pflege); return; }
      z.effekt = { id, bis: Date.now() + 4000 };
      z.satz = DING_SATZ[id] || "Das mag ich! 💛";
      z.jubelGesicht = "jubel"; z.jubel = Date.now() + 2500;
      ereignis("franzi", "ok"); zeige();
      setTimeout(() => { if (z.effekt?.id === id && Date.now() >= z.effekt.bis) { z.effekt = null; zeige(); } }, 4100);
    }

    /* ---------------------------------------------------------------- 6.9.50: Musikbox und Tanzen */
    const quelle = musikQuelle(api, "archiv-musik");
    const BEWEGUNGEN = ["huepf", "wiege", "dreh", "seit"];
    function tanzSchlag() {
      const t = z.tanz;
      if (!t) return;
      t.schlaege = (t.schlaege || 0) + 1;
      t.haltung = ((t.haltung || 0) + 1) % 3;
      if (t.schlaege % 8 === 0) t.bewegung = BEWEGUNGEN[(t.schlaege / 8) % BEWEGUNGEN.length];
      const fz = inhalt.querySelector(".fz-tanzt");
      if (!fz) return;
      fz.querySelectorAll(".fz-tanz-haltung").forEach((h, i) => h.classList.toggle("an", i === t.haltung));
      BEWEGUNGEN.forEach((b) => fz.classList.toggle(b, b === (t.bewegung || "huepf")));
      fz.classList.remove("schlag"); void fz.offsetWidth; fz.classList.add("schlag");
      inhalt.querySelector(".fz-disco")?.style.setProperty("--disco", String((t.schlaege * 47) % 360));
    }
    function tanzStopp() {
      if (!z.tanz) return;
      z.tanz.takt?.(); z.tanz.spieler?.stopp();
      z.tanz = null;
    }
    async function tanzAktion(x) {
      try {
        if (x.id === "musik" || x.tanz === "auswahl") {
          const d = await quelle.liste("");
          const alben = [...d.ordner.map((o) => ({ pfad: o.pfad, name: o.name })), ...(d.titel.length ? [{ pfad: "", name: "Einzelne Lieder" }] : [])];
          if (!alben.length) { api.hinweis("Es ist noch keine Musik freigegeben."); return; }
          z.tanz = { ...(z.tanz || {}), alben };
          z.wahl = 0; ton("ok"); zeige(); return;
        }
        if (x.tanz === "zurueck") { if (z.tanz?.spieler) z.tanz.alben = null; else z.tanz = null; z.wahl = 0; zeige(); return; }
        if (x.tanz === "album" || x.tanz === "zufall") {
          let liste = [];
          if (x.tanz === "album") liste = await quelle.titel(x.pfad);
          else for (const a of z.tanz.alben.slice(0, 12)) liste.push(...await quelle.titel(a.pfad));
          if (!liste.length) { api.hinweis("Hier sind keine Lieder."); return; }
          if (!z.tanz.spieler) {
            z.tanz.spieler = musikSpieler(api, quelle, () => {
              const t = z.tanz?.spieler?.aktuell();
              if (t) z.satz = `💃 Tanz mit mir! 🎵 ${t.name}`;
              zeige();
            });
            z.tanz.takt = taktFolgen(z.tanz.spieler.audio, tanzSchlag);
          }
          z.tanz.alben = null;
          z.tanz.spieler.starte(liste, x.tanz === "zufall" ? Math.floor(Math.random() * liste.length) : 0, { zufall: x.tanz === "zufall" });
          z.wahl = 0; ton("ok"); zeige(); return;
        }
        const sp = z.tanz?.spieler;
        if (!sp) return;
        if (x.tanz === "pause") sp.umschalten();
        else if (x.tanz === "weiter") sp.weiter(1);
        else if (x.tanz === "aus") { tanzStopp(); z.satz = "Das hat Spaß gemacht! 💛"; z.wahl = 0; }
        ton("ok"); zeige();
      } catch (e) { api.hinweis(e.message || "Die Musik geht gerade nicht."); ton("fehler"); }
    }

    /* ---------------------------------------------------------------- OK */
    function pflegen(aktion) {
      sende("/api/franzi/tun", { aktion }, () => {
        /* 6.9.45: Franzi mag nicht immer - dann sagt sie es freundlich (und es passiert nichts) */
        const r = z.d.reaktion;
        if (r) { z.satz = r.text; z.jubelGesicht = r.gesicht; z.jubel = Date.now() + 3500; ton(r.gesicht === "genervt" ? "fehler" : "bewegen"); }
        else { z.satz = REAKTION[aktion]; z.jubelGesicht = PFLEGE_GESICHT[aktion]; z.jubel = Date.now() + 2500; ereignis("franzi", "ok"); }
        setTimeout(zeige, (r ? 3600 : 2600));
      });
    }
    function ok() {
      const d = z.d, x = eintraege()[z.wahl];
      if (!d || !x) return;
      if (d.abenteuer) {
        if (d.abenteuer.postkarte) { karteOeffnen([d.abenteuer.postkarte], 0, true); return; }    /* 6.9.49: erst die Karte */
        lade(true); ton("sieg"); return;
      }
      if (x.album) { karteOeffnen(d.postkarten, 0); return; }
      if (x.id === "musik" || x.tanz) { tanzAktion(x); return; }
      if (x.spiel) { starteSpiel(x.spiel); return; }
      if (x.anfassen) { const l = zimmerDinge(); z.anfassen = { id: l[0], i: 0 }; z.satz = "← → aussuchen · OK anfassen · STOP fertig"; ton("ok"); zeige(); return; }
      if (art() === "zimmer") {
        pflegen(x.id);
      } else if (art() === "spielen") {
        starteSpiel(x.id);
      } else if (art() === "shop") {
        if (x.stufe) { z.satz = `${x.titel} bekommen wir mit Level ${x.stufe}` + (x.tage ? ` – und nach ${x.tage} weiteren Sternentagen` : "") +
                       ". Sammle Sterne in „Mein Tag“!"; ton("bewegen"); zeige(); return; }
        if (d.sterne < x.preis) { z.satz = `Dafür brauchst du ${x.preis} Sterne – sammle sie in „Mein Tag“!`; ton("fehler"); zeige(); return; }
        if (z.kaufen !== z.wahl) { z.kaufen = z.wahl; ton("bewegen"); zeige(); return; }
        z.kaufen = null;
        if (x.item) sende("/api/franzi/kaufen", { item: x.item }, () => { ereignis("kauf", "sieg"); z.jubel = Date.now() + 3000; });
        else sende("/api/franzi/angebot", { nr: x.angebot }, () => { ereignis("kauf", "sieg"); z.satz = `${x.titel} – viel Spaß! 🎉`; z.jubel = Date.now() + 3000; });
      } else if (art() === "schrank") {
        if (x.raum) sende("/api/franzi/tun", { aktion: "raum", raum: x.raum }, () => { ton("ok"); z.satz = RAUM_TIPP[x.raum] || ""; });
        else if (x.kleid) sende("/api/franzi/tun", { aktion: "anziehen", item: x.kleid, an: !d.angezogen.includes(x.kleid) }, () => ton("ok"));
        else if (x.ding) {
          const nurIn = d.katalog.find((k) => k.id === x.ding)?.nur_in || [];
          if (nurIn.length && !nurIn.includes(d.raum)) {                /* 6.9.55: passt nur in bestimmte Räume */
            z.satz = `Das passt in: ${nurIn.map((r) => RAUM_NAME[r] || r).join(" und ")}. Geh dorthin, dann kannst du es aufstellen!`; ton("fehler"); zeige(); return;
          }
          /* 6.9.54: OK = einrichten - mit den Pfeilen hinschieben, OK = fertig/wegräumen, STOP = abbrechen */
          const lage = (d.zimmer || {})[x.ding];
          const [art_] = DING[x.ding] || ["klein"];
          const start = Array.isArray(lage) ? lage : { gross: [30, 17], wand: [40, 55], fenster: [22, 45] }[art_] || [62, 4];
          z.einrichten = { id: x.ding, x: start[0], y: start[1], war: Array.isArray(lage), menue: null };
          z.satz = "Schieb es mit den Pfeilen hin – OK, wenn es passt!"; ton("ok"); zeige();
        }
      }
    }

    /* ---------------------------------------------------------------- Minispiele */
    function spielEnde(id, punkte_ = 0) {
      const dauer = performance.now() - (z.spielStart || 0);
      z.spiel?.schliesse?.();
      z.spiel = null;
      box.classList.remove("fz-spielt");
      if (OHNE_FREUDE.has(id)) { z.satz = "Schöne Bilder!"; zeige(); return; }
      /* 6.9.4: nur wer wirklich gespielt hat (mindestens 15 s oder Punkte), macht Franzi glücklich */
      if (dauer < 15000 && !punkte_) { z.satz = "Doch nicht? Okay, vielleicht später!"; zeige(); return; }
      sende("/api/franzi/tun", { aktion: "gespielt", spiel: id, punkte: punkte_ }, () => {
        z.satz = punkte_ ? `${punkte_} Punkte – das hat Spaß gemacht!` : "Das hat Spaß gemacht! Nochmal?";
        z.jubel = Date.now() + 2500;
      });
    }
    function starteSpiel(id) {
      tanzStopp();                                       /* 6.9.50: Spiel beendet die Musik */
      z.spielStart = performance.now();
      const flaeche = el("div", { class: "fz-spiel" });
      inhalt.replaceChildren(flaeche);
      box.classList.add("fz-spielt");
      if (id === "spiel-fangen") { z.spiel = sterneFangen(flaeche, (p) => spielEnde(id, p)); return; }
      const modul = EINGEBAUT[id];
      if (!modul) { api.hinweis("Dieses Spiel kommt bald."); z.spiel = null; zeige(); return; }
      const innen = modul.oeffne(flaeche, api);
      z.spiel = { taste: (t) => innen.taste(t), schliesse: () => innen.schliesse?.(), id };
    }

    lade(true);
    const offenAb = performance.now() + 500;          /* das OK, das die Kachel geöffnet hat, füttert Franzi nicht gleich mit */
    const auffrischen = setInterval(() => { if (!z.spiel && !document.hidden) lade(); }, 60 * 1000);

    return {
      taste(t) {
        if (z.karte) return karteTaste(t);                 /* 6.9.49: Postkarte offen */
        if (z.einrichten) return einrichtenTaste(t);       /* 6.9.54: Gegenstand wird verschoben */
        if (z.anfassen) return anfassenTaste(t);           /* 6.9.63: Gegenstände im Zimmer anwählen */
        if (z.spiel) {
          const weiter = z.spiel.taste(t);
          if (!weiter && (t === "Escape" || t === "Backspace")) spielEnde(z.spiel.id || "spiel-fangen", z.spiel.punkte?.() || 0);
          return true;
        }
        if (t === "ArrowLeft" || t === "ArrowRight") {
          z.reiter = (z.reiter + (t === "ArrowLeft" ? REITER.length - 1 : 1)) % REITER.length;
          z.wahl = 0; z.kaufen = null; z.satz = ""; ton("bewegen"); zeige();
          return true;
        }
        if (t === "ArrowUp" || t === "ArrowDown") {
          const n = eintraege().length;
          if (n) { z.wahl = (z.wahl + (t === "ArrowUp" ? n - 1 : 1)) % n; z.kaufen = null; ton("bewegen"); zeige(); }
          return true;
        }
        if (t === "Enter" || t === " ") { if (performance.now() >= offenAb) ok(); return true; }
        return t !== "Escape" && t !== "Backspace";
      },
      schliesse() { clearInterval(auffrischen); tanzStopp(); z.spiel?.schliesse?.(); },
      /* 6.9.1: ist Franzis Zimmer offen, sagt sie Meldungen selbst (statt des Meldungsfensters) */
      sagen(text) { if (z.spiel) return false; z.satz = text; z.jubel = Date.now() + 2000; zeige(); return true; },
    };
  },
};

/* ---------------------------------------------------------------- Startspiel „Sterne fangen“ (45 Sekunden)
   ← → Franzi läuft (ein Druck = ein Stück, gedrückt halten geht auch) · STOP beendet. 30 Bilder pro Sekunde, nur solange es läuft.
   6.9.16: vorgezeichneter Hintergrund (Hügel, ferne Sterne), Funken beim Fangen, Combo mit steigendem Ton, Franzi als Fänger.
   Stufe „hoch“: zweite Sternenebene zieht langsam (Parallax), Schweife hinter den Sternen, doppelt so viele Funken. */
function sterneFangen(flaeche, fertig) {
  const B = Math.min(1100, Math.round(innerWidth * 0.8)), H = Math.round(Math.min(innerHeight * 0.62, B * 0.56));
  const hoch = stufe() === "hoch";
  const canvas = el("canvas", { class: "spielfeld" });
  const info = el("div", { class: "punkte", text: "⭐ 0 · 45 s" });
  flaeche.append(info, canvas);
  const g = canvasScharf(canvas, B, H);
  /* Hintergrund einmal vorzeichnen - je Bild nur noch ein drawImage */
  const grund = document.createElement("canvas");
  grund.width = B; grund.height = H;
  const h = grund.getContext("2d");
  const v = h.createLinearGradient(0, 0, 0, H);
  v.addColorStop(0, "#141c46"); v.addColorStop(0.7, "#3a3f86"); v.addColorStop(1, "#5a4f96");
  h.fillStyle = v; h.fillRect(0, 0, B, H);
  for (let i = 0; i < 90; i++) {
    h.fillStyle = `rgba(255,255,255,${(0.15 + Math.random() * 0.5).toFixed(2)})`;
    h.beginPath(); h.arc(Math.random() * B, Math.random() * H * 0.75, Math.random() * 1.4 + 0.3, 0, Math.PI * 2); h.fill();
  }
  h.fillStyle = "#fff6d0"; h.beginPath(); h.arc(B * 0.84, H * 0.18, 26, 0, Math.PI * 2); h.fill();
  h.fillStyle = "#141c46"; h.beginPath(); h.arc(B * 0.84 + 10, H * 0.18 - 6, 24, 0, Math.PI * 2); h.fill();
  for (const [hoehe, farbe] of [[0.78, "#2d3570"], [0.86, "#24295a"]]) {
    h.fillStyle = farbe; h.beginPath(); h.moveTo(0, H);
    for (let x = 0; x <= B; x += 20) h.lineTo(x, H * hoehe + Math.sin(x / (B / 4) + hoehe * 9) * H * 0.04);
    h.lineTo(B, H); h.fill();
  }
  const fern = hoch ? Array.from({ length: 40 }, () => ({ x: Math.random() * B, y: Math.random() * H * 0.7, r: Math.random() * 1.6 + 0.6 })) : [];
  const s = { x: B / 2, richtung: 0, sterne: [], funken: [], punkte: 0, combo: 0, ende: performance.now() + 45000, takt: 0, aus: false, schritt: 0 };
  const los = (e) => { if ((e.key === "ArrowLeft" && s.richtung < 0) || (e.key === "ArrowRight" && s.richtung > 0)) s.richtung = 0; };
  window.addEventListener("keyup", los);
  function funken(x, y, gold) {
    const n = (hoch ? 16 : 8) * (gold ? 1.5 : 1);
    for (let i = 0; i < n; i++) {
      const w = Math.random() * Math.PI * 2, t = 2 + Math.random() * 4;
      s.funken.push({ x, y, vx: Math.cos(w) * t, vy: Math.sin(w) * t - 2, leben: 18 + Math.random() * 10, gold });
    }
    if (s.funken.length > 120) s.funken.splice(0, s.funken.length - 120);
  }
  function logik() {
    s.takt++;
    const vorher = s.x;
    s.x = Math.max(44, Math.min(B - 44, s.x + s.richtung * 12));
    if (s.x !== vorher) s.schritt++;
    if (s.takt % 18 === 0) s.sterne.push({ x: 30 + Math.random() * (B - 60), y: -20, v: 2.5 + Math.random() * 2 + s.takt / 900, gold: Math.random() < 0.15, dreh: Math.random() * 6 });
    for (const st of s.sterne) { st.y += st.v; st.dreh += 0.05; }
    s.sterne = s.sterne.filter((st) => {
      if (st.y > H - 84 && st.y < H - 24 && Math.abs(st.x - s.x) < 52) {
        s.combo++;
        s.punkte += (st.gold ? 3 : 1) + (s.combo >= 5 ? 1 : 0);
        ton("punkt", { faktor: Math.min(2, 1 + s.combo * 0.06) });
        funken(st.x, st.y, st.gold);
        return false;
      }
      if (st.y >= H + 20) { s.combo = 0; return false; }
      return true;
    });
    for (const f of s.funken) { f.x += f.vx; f.y += f.vy; f.vy += 0.25; f.leben--; }
    s.funken = s.funken.filter((f) => f.leben > 0);
    const rest = Math.max(0, Math.ceil((s.ende - performance.now()) / 1000));
    info.textContent = `⭐ ${s.punkte} · ${rest} s` + (s.combo >= 5 ? ` · 🔥 ${s.combo}er-Serie` : "");
    if (!rest && !s.aus) { s.aus = true; steuer.stopp(); ton("sieg"); setTimeout(() => fertig(s.punkte), 600); }
  }
  function zeichne() {
    g.drawImage(grund, 0, 0, B, H);
    if (hoch) {
      g.fillStyle = "rgba(255,255,255,.7)";
      for (const f of fern) { const x = (f.x - s.takt * 0.15 * f.r + B * 10) % B; g.beginPath(); g.arc(x, f.y, f.r, 0, Math.PI * 2); g.fill(); }
    }
    g.textAlign = "center"; g.textBaseline = "middle"; g.font = `34px "FF Emoji", sans-serif`;
    for (const st of s.sterne) {
      if (hoch) {
        const sch = g.createLinearGradient(st.x, st.y - 50, st.x, st.y);
        sch.addColorStop(0, "rgba(255,220,120,0)"); sch.addColorStop(1, st.gold ? "rgba(255,200,80,.55)" : "rgba(255,240,180,.4)");
        g.fillStyle = sch; g.fillRect(st.x - 4, st.y - 50, 8, 50);
      }
      g.save(); g.translate(st.x, st.y); g.rotate(Math.sin(st.dreh) * 0.3);
      g.fillStyle = "#000"; g.fillText(st.gold ? "🌟" : "⭐", 0, 0); g.restore();
    }
    for (const f of s.funken) {
      g.globalAlpha = Math.max(0, f.leben / 28);
      g.fillStyle = f.gold ? "#ffcf4d" : "#fff6b0";
      g.fillRect(f.x - 2, f.y - 2, 4, 4);
    }
    g.globalAlpha = 1;
    /* Franzi als Fänger: Fernseher-Körper mit Antennen, Beinen, Gesicht; lacht bei einer Serie */
    const fx = s.x - 36, fy = H - 82, bein = s.richtung ? Math.sin(s.schritt * 0.7) * 4 : 0;
    g.fillStyle = "rgba(0,0,0,.25)"; g.beginPath(); g.ellipse(s.x, H - 12, 40, 8, 0, 0, Math.PI * 2); g.fill();
    g.strokeStyle = "#3b4566"; g.lineWidth = 3; g.beginPath(); g.moveTo(fx + 26, fy + 4); g.lineTo(fx + 18, fy - 12);
    g.moveTo(fx + 46, fy + 4); g.lineTo(fx + 56, fy - 10); g.stroke();
    g.fillStyle = "#ffd54f"; g.beginPath(); g.arc(fx + 18, fy - 12, 5, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#7fdcaa"; g.beginPath(); g.arc(fx + 56, fy - 10, 5, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#c94f35"; g.fillRect(fx + 14 + bein, fy + 58, 12, 10); g.fillRect(fx + 46 - bein, fy + 58, 12, 10);
    g.fillStyle = "#ff7a59"; g.beginPath(); g.roundRect(fx, fy, 72, 62, 15); g.fill();
    g.fillStyle = "#ff9472"; g.beginPath(); g.roundRect(fx, fy, 72, 26, [15, 15, 0, 0]); g.fill();
    g.fillStyle = "#1e2a4a"; g.beginPath(); g.roundRect(fx + 8, fy + 8, 56, 42, 9); g.fill();
    g.fillStyle = "#fff";
    if (s.combo >= 5) { g.strokeStyle = "#fff"; g.lineWidth = 3; g.beginPath(); g.arc(fx + 24, fy + 24, 5, Math.PI, 0); g.arc(fx + 48, fy + 24, 5, Math.PI, 0); g.stroke(); }
    else { g.fillRect(fx + 21, fy + 19, 6, 8); g.fillRect(fx + 45, fy + 19, 6, 8); }
    g.strokeStyle = "#fff"; g.lineWidth = 3; g.beginPath(); g.arc(fx + 36, fy + 32, 9, 0.2, Math.PI - 0.2); g.stroke();
  }
  const steuer = takt(1000 / 30, logik, zeichne);
  return {
    id: "spiel-fangen",
    punkte: () => s.punkte,
    taste(t) {
      if (t === "ArrowLeft" || t === "ArrowRight") { const r = t === "ArrowLeft" ? -1 : 1; s.x += r * 40; s.richtung = r; return true; }
      return !(t === "Escape" || t === "Backspace");
    },
    schliesse() { steuer.stopp(); window.removeEventListener("keyup", los); },
  };
}
