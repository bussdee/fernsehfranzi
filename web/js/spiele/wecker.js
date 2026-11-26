/* FernsehFranzi 3.5 - Wecker einstellen (das Kind selbst, „wie im Handy“).
 *
 * Liste: ↑ ↓ wählen · OK bearbeiten · ← → an/aus · STOP zurück
 * Bearbeiten: ↑ ↓ Feld · ← → ändern · OK (Tage: Tag an/aus, Ton: anhören) · Speichern/Löschen mit OK
 * Grenzen der Eltern (frühestens, höchste Lautstärke) gelten - der Server prüft sie.
 */
import { el } from "../gemeinsam.js";
import { kopf, ton } from "./kern.js";

const TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const SANFT = "";                                       /* eingebauter Ton */

function name(ton_) { return ton_ ? ton_.split("/").pop().replace(/\.[^.]+$/, "") : "🎵 Sanfter Ton"; }

export default {
  symbol: "⏰",
  oeffne(box, api) {
    const { inhalt, hilfe } = kopf(box, "⏰ Wecker", "");
    const z = { wecker: null, toene: [SANFT], wahl: 0, bearbeiten: null, feld: 0, tag: 0, probe: null };

    async function lade() {
      try {
        const d = await api.hole("/api/wecker");
        z.wecker = d.wecker;
        z.toene = [SANFT, ...d.toene];
      } catch (fehler) { inhalt.replaceChildren(el("div", { class: "meldung-fehler", text: fehler.message })); return; }
      liste();
    }

    /* ------------------------------------------------ Liste */
    function liste() {
      z.bearbeiten = null;
      stopProbe();
      hilfe.textContent = "↑ ↓ wählen · OK bearbeiten · ← → an/aus · STOP zurück";
      const w = z.wecker;
      const zeilen = w.liste.map((e) => el("div", { class: "wecker-zeile" + (e.an === false ? " aus" : "") },
        el("div", { class: "wecker-zeit", text: e.zeit }),
        el("div", { class: "wecker-info" }, el("div", { text: e.tage.length === 7 ? "jeden Tag" :
          JSON.stringify(e.tage) === "[0,1,2,3,4]" ? "Mo – Fr" : e.tage.map((t) => TAGE[t]).join(" ") }),
          el("small", { text: name(e.ton) })),
        el("div", { class: "wecker-schalter" + (e.an === false ? "" : " an"), text: e.an === false ? "aus" : "an" })));
      if (w.liste.length < 5) zeilen.push(el("div", { class: "wecker-zeile neu", text: "➕ Neuer Wecker" }));
      z.wahl = Math.min(z.wahl, zeilen.length - 1);
      zeilen.forEach((k, i) => k.classList.toggle("gewaehlt", i === z.wahl));
      inhalt.replaceChildren(el("div", { class: "wecker-liste" },
        w.aktiv ? null : el("div", { class: "meldung-fehler", text: "Mama oder Papa haben den Wecker gerade ausgeschaltet." }),
        ...zeilen,
        el("p", { class: "leise", text: `Frühestens ${w.fruehestens} Uhr · Lautstärke höchstens ${w.max_laut} %` })));
    }

    async function speichern(liste_) {
      try {
        await api.sende("/api/wecker", { liste: liste_ });
        z.wecker.liste = liste_;
        api.hinweis("Wecker gespeichert ✔");
        ton("ok");
        return true;
      } catch (fehler) { api.hinweis(fehler.message, 5000); ton("fehler"); return false; }
    }

    /* ------------------------------------------------ Bearbeiten */
    const FELDER = ["stunde", "minute", "tage", "ton", "laut", "sonne", "szene", "speichern", "loeschen"];
    const SONNE = [0, 5, 10, 15, 20, 30];
    const SZENEN = [["huegel", "⛰️ Hügel"], ["ostsee", "🌊 Ostsee mit Wellen und Möwen"], ["wald", "🌲 Wald mit Vögeln"]];   /* 6.6 */
    function bearbeite(e) {
      const nr = Math.max(0, ...z.wecker.liste.map((x) => x.nr)) + 1;
      z.bearbeiten = e ? { ...e, tage: [...e.tage] } : { nr, zeit: "07:00", tage: [0, 1, 2, 3, 4], ton: SANFT, laut: z.wecker.max_laut, an: true, sonne: 10 };
      z.neu = !e;
      z.feld = 0;
      zeichneBearbeiten();
    }
    function zeichneBearbeiten() {
      const b = z.bearbeiten;
      const [h, m] = b.zeit.split(":");
      hilfe.textContent = "↑ ↓ Feld · ← → ändern · OK auswählen · STOP zurück (ohne Speichern)";
      const feld = (i, ...kinder) => el("div", { class: "wecker-feld" + (z.feld === i ? " gewaehlt" : "") }, ...kinder);
      inhalt.replaceChildren(el("div", { class: "wecker-bearbeiten" },
        el("div", { class: "wecker-gross" },
          feld(0, el("span", { text: h })), el("span", { class: "wecker-doppelpunkt", text: ":" }), feld(1, el("span", { text: m }))),
        feld(2, el("div", { class: "wecker-tage" }, ...TAGE.map((t, i) => el("span", {
          class: (b.tage.includes(i) ? "an" : "") + (z.feld === 2 && z.tag === i ? " zeiger" : ""), text: t })))),
        feld(3, el("span", { text: "Ton: " + name(b.ton) + "  ◀ ▶  (OK = anhören)" })),
        feld(4, el("span", { text: `Lautstärke: ${b.laut} %` }), el("div", { class: "hb-balken" }, el("span", { style: `width:${b.laut}%` }))),
        feld(5, el("span", { text: b.sonne ? `🌅 Sonnenaufgang: ${b.sonne} Minuten vorher` : "🌅 Sonnenaufgang: aus" })),
        feld(6, el("span", { text: `Szene: ${(SZENEN.find(([k]) => k === (b.szene || "huegel")) || SZENEN[0])[1]}  ◀ ▶` })),
        el("div", { class: "knopfreihe" }, feld(7, el("span", { text: "✔ Speichern" })), z.neu ? null : feld(8, el("span", { text: "🗑 Löschen" })))));
    }
    function aendern(richtung) {
      const b = z.bearbeiten;
      let [h, m] = b.zeit.split(":").map(Number);
      const f = FELDER[z.feld];
      if (f === "stunde") h = (h + richtung + 24) % 24;
      else if (f === "minute") m = (m + richtung * 5 + 60) % 60;
      else if (f === "tage") z.tag = (z.tag + richtung + 7) % 7;
      else if (f === "ton") { const i = z.toene.indexOf(b.ton); b.ton = z.toene[(Math.max(0, i) + richtung + z.toene.length) % z.toene.length]; stopProbe(); }
      else if (f === "laut") b.laut = Math.max(5, Math.min(z.wecker.max_laut, b.laut + richtung * 5));
      else if (f === "szene") { const i = SZENEN.findIndex(([k]) => k === (b.szene || "huegel")); b.szene = SZENEN[(i + richtung + SZENEN.length) % SZENEN.length][0]; }
      else if (f === "sonne") { const i = SONNE.indexOf(b.sonne || 0); b.sonne = SONNE[Math.max(0, Math.min(SONNE.length - 1, i + richtung))]; }
      b.zeit = `${String(h).padStart(2, "0")}:${String(m - (m % 5)).padStart(2, "0")}`;
      ton("bewegen");
      zeichneBearbeiten();
    }
    async function ok() {
      const b = z.bearbeiten, f = FELDER[z.feld];
      if (f === "tage") {
        if (b.tage.includes(z.tag)) { if (b.tage.length > 1) b.tage = b.tage.filter((t) => t !== z.tag); }
        else b.tage = [...b.tage, z.tag].sort();
        zeichneBearbeiten();
      } else if (f === "ton") probe(b.ton);
      else if (f === "speichern") {
        const neu = z.neu ? [...z.wecker.liste, b] : z.wecker.liste.map((e) => (e.nr === b.nr ? b : e));
        if (await speichern(neu)) liste();
      } else if (f === "loeschen") {
        if (await speichern(z.wecker.liste.filter((e) => e.nr !== b.nr))) liste();
      }
    }

    /* Ton anhören (10 s) */
    function probe(t) {
      stopProbe();
      if (!t) { ton("sieg"); return; }
      const a = new Audio(`/api/wecker/ton?pfad=${encodeURIComponent(t)}`);
      a.volume = 0.6;
      a.play().catch(() => api.hinweis("Der Ton lässt sich gerade nicht abspielen."));
      z.probe = { a, timer: setTimeout(stopProbe, 10000) };
    }
    function stopProbe() {
      if (!z.probe) return;
      clearTimeout(z.probe.timer);
      z.probe.a.pause();
      z.probe = null;
    }

    lade();
    return {
      taste(t) {
        if (!z.wecker) return t !== "Escape";
        if (z.bearbeiten) {
          if (t === "Escape" || t === "Backspace") { liste(); return true; }
          /* Stunde und Minute stehen nebeneinander: OK springt von der Stunde zur Minute */
          if (t === "ArrowUp") { z.feld = z.feld === 2 ? 0 : Math.max(0, z.feld - 1); zeichneBearbeiten(); return true; }
          if (t === "ArrowDown") { z.feld = Math.min(z.neu ? 7 : 8, z.feld <= 1 ? 2 : z.feld + 1); zeichneBearbeiten(); return true; }
          if (t === "ArrowLeft" || t === "ArrowRight") { aendern(t === "ArrowLeft" ? -1 : 1); return true; }
          if (t === "Tab") { z.feld = z.feld === 0 ? 1 : 0; zeichneBearbeiten(); return true; }
          if (t === "Enter" || t === " ") { if (z.feld === 0) { z.feld = 1; zeichneBearbeiten(); } else ok(); return true; }
          return true;
        }
        const anzahl = z.wecker.liste.length + (z.wecker.liste.length < 5 ? 1 : 0);
        if (t === "ArrowUp") { z.wahl = Math.max(0, z.wahl - 1); liste(); ton("bewegen"); return true; }
        if (t === "ArrowDown") { z.wahl = Math.min(anzahl - 1, z.wahl + 1); liste(); ton("bewegen"); return true; }
        if (t === "ArrowLeft" || t === "ArrowRight") {
          const e = z.wecker.liste[z.wahl];
          if (e) speichern(z.wecker.liste.map((x) => (x === e ? { ...x, an: x.an === false } : x))).then(liste);
          return true;
        }
        if (t === "Enter" || t === " ") { bearbeite(z.wecker.liste[z.wahl] || null); return true; }
        return false;
      },
      schliesse() { stopProbe(); },
    };
  },
};
