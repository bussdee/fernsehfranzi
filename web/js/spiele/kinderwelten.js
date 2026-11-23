/* FernsehFranzi 5.0 - Geschichten & Rätsel aus den Kinderwelten (Familienfabrik), nur lesen.
 * Geschichten und frei lesbare Bücher in großer Schrift zum Selberlesen (Bücher kapitelweise), Kinder-News der
 * Familienfabrik, Spiele für draußen und das Rätsel des Tages. Welche Reiter es gibt, legen die Eltern fest.
 * ← → Reiter (im Buch: Kapitel zurück/weiter) · ↑ ↓ wählen oder blättern · OK öffnen · STOP zurück */
import { el } from "../gemeinsam.js";
import { kopf, ton } from "./kern.js";
import { reiter, liste, leser, hinweisZeile } from "./seite.js";

const TEILE = { geschichten: "📖 Geschichten", buecher: "📚 Bücher", news: "📰 News", draussen: "🌳 Draußen", raetsel: "🧩 Rätsel" };
const LISTE_WEG = { geschichten: "/api/kinderwelten/geschichten", buecher: "/api/kinderwelten/buecher",
                    news: "/api/kinderwelten/news", draussen: "/api/kinderwelten/draussen" };
const HILFE = "← → Reiter · ↑ ↓ wählen · OK öffnen · STOP zurück";

function merke(schluessel, wert) { try { localStorage.setItem("ff-kw-" + schluessel, String(wert)); } catch (_) { /* ohne */ } }
function gemerkt(schluessel) { try { return +(localStorage.getItem("ff-kw-" + schluessel) || 0); } catch (_) { return 0; } }

export default {
  symbol: "📖",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "📖 Geschichten & Rätsel", HILFE);
    const z = { teile: [], reiter: 0, wahl: 0, listen: {}, lesen: null, buch: null, raetsel: null, offen: false, fehler: "" };
    const teil = () => z.teile[z.reiter];

    function eintraege() {
      const l = z.listen[teil()] || [];
      if (teil() === "geschichten") return l.map((g) => ({ bild: g.bild, titel: g.titel, zeile: [g.reihe, g.lesezeit && `${g.lesezeit} min lesen`].filter(Boolean).join(" · ") }));
      if (teil() === "buecher") return l.map((b) => ({ bild: b.bild, titel: b.titel, zeile: b.reihe + (b.band ? ` · Band ${b.band}` : ""),
        rechts: gemerkt(b.adresse) > 1 ? `Kapitel ${gemerkt(b.adresse)}` : "" }));
      return l.map((n) => ({ bild: n.bild, titel: n.titel, zeile: n.anriss }));
    }

    function zeige() {
      if (z.lesen) return;
      if (!z.teile.length) { inhalt.replaceChildren(hinweisZeile(z.fehler || "Einen Moment …", z.fehler ? "🔒" : "⏳")); return; }
      const kopfzeile = reiter(z.teile.map((t) => TEILE[t]), z.reiter);
      punkte.textContent = "";
      if (teil() === "raetsel") {
        const r = z.raetsel;
        const teile = !r ? [hinweisZeile("Das Rätsel wird geholt …")] : [
          r.spruch ? el("div", { class: "kw-spruch", text: r.spruch }) : null,
          r.raetsel ? el("div", { class: "kw-raetsel" }, el("div", { class: "kw-frage", text: "🧩 " + r.raetsel.frage }),
            el("div", { class: "kw-antwort", text: z.offen ? `${r.raetsel.tipp} ${r.raetsel.antwort}` : "OK drücken für die Lösung" }))
            : hinweisZeile("Heute gibt es kein Rätsel.", "🧩")];
        inhalt.replaceChildren(el("div", { class: "seite" }, kopfzeile, ...teile));
        return;
      }
      const l = z.listen[teil()];
      inhalt.replaceChildren(el("div", { class: "seite" }, kopfzeile,
        l === undefined ? hinweisZeile("Einen Moment …") : typeof l === "string" ? hinweisZeile(l, "⚠️")
          : liste(eintraege(), z.wahl, { sichtbar: 4, leer: "Hier ist gerade nichts." })));
    }

    function holeTeil() {
      const t = teil();
      if (t === "raetsel") {
        if (!z.raetsel) api.hole("/api/kinderwelten/raetsel").then((r) => { z.raetsel = r; zeige(); })
          .catch((f) => { z.raetsel = { spruch: f.message, raetsel: null }; zeige(); });
        return;
      }
      if (z.listen[t] !== undefined) return;
      api.hole(LISTE_WEG[t]).then((r) => { z.listen[t] = r.eintraege || []; zeige(); })
        .catch((f) => { z.listen[t] = f.message; zeige(); });
    }

    async function lese(weg, { buch = null } = {}) {
      inhalt.replaceChildren(hinweisZeile("Einen Moment …"));
      try {
        const d = await api.hole(weg);
        const unten = buch ? (d.von && d.nummer < d.von ? "→ nächstes Kapitel" : "Ende des Buches. 🎉") : "Ende. 🎉";
        z.lesen = leser(d.titel, d.bloecke || [], { bild: buch ? null : d.bild, unten });
        z.buch = buch ? { ...buch, nummer: d.nummer, von: d.von } : null;
        if (buch) { merke(buch.adresse, d.nummer); punkte.textContent = `Kapitel ${d.nummer}${d.von ? " von " + d.von : ""}`; }
        hilfe.textContent = buch ? "↑ ↓ blättern · ← → Kapitel · STOP zurück" : "↑ ↓ blättern · STOP zurück";
        inhalt.replaceChildren(z.lesen.knoten);
      } catch (f) {
        z.lesen = null;
        api.hinweis(f.message);
        zeige();
      }
    }

    function zurListe() { z.lesen = null; z.buch = null; hilfe.textContent = HILFE; zeige(); }

    api.hole("/api/kinderwelten").then((u) => {
      if (!u.aktiv) { z.fehler = "Die Kinderwelten sind ausgeschaltet."; zeige(); return; }
      z.teile = u.teile.filter((t) => TEILE[t]);
      if (!z.teile.length) { z.fehler = "Hier ist gerade nichts eingeschaltet."; zeige(); return; }
      zeige(); holeTeil();
    }).catch((f) => { z.fehler = f.message; zeige(); });

    return {
      taste(t) {
        if (z.lesen) {
          if (t === "ArrowDown" || t === "ArrowUp") {
            const bewegt = z.lesen.blaettern(t === "ArrowDown" ? 1 : -1);
            if (!bewegt && t === "ArrowDown" && z.buch && z.buch.von && z.buch.nummer < z.buch.von) {   /* am Ende: nächstes Kapitel */
              lese(`/api/kinderwelten/kapitel?a=${encodeURIComponent(z.buch.adresse)}&n=${z.buch.nummer + 1}`, { buch: z.buch }); ton("ok");
            }
            return true;
          }
          if (z.buch && (t === "ArrowLeft" || t === "ArrowRight")) {
            const n = z.buch.nummer + (t === "ArrowLeft" ? -1 : 1);
            if (n >= 1 && (!z.buch.von || n <= z.buch.von)) { lese(`/api/kinderwelten/kapitel?a=${encodeURIComponent(z.buch.adresse)}&n=${n}`, { buch: z.buch }); ton("bewegen"); }
            else ton("anschlag");
            return true;
          }
          if (t === "Escape" || t === "Backspace") { zurListe(); return true; }
          return true;
        }
        if (!z.teile.length) return t !== "Escape" && t !== "Backspace";
        if (t === "ArrowLeft" || t === "ArrowRight") {
          z.reiter = (z.reiter + (t === "ArrowLeft" ? -1 : 1) + z.teile.length) % z.teile.length;
          z.wahl = 0; z.offen = false; zeige(); holeTeil(); ton("bewegen"); return true;
        }
        const n = eintraege().length;
        if (t === "ArrowUp") { z.wahl = Math.max(0, z.wahl - 1); zeige(); ton("bewegen"); return true; }
        if (t === "ArrowDown") { z.wahl = Math.min(Math.max(0, n - 1), z.wahl + 1); zeige(); ton("bewegen"); return true; }
        if (t === "Enter" || t === " ") {
          if (teil() === "raetsel") { z.offen = !z.offen; zeige(); ton(z.offen ? "sieg" : "ok"); return true; }
          const x = (z.listen[teil()] || [])[z.wahl];
          if (!x || typeof z.listen[teil()] === "string") return true;
          ton("ok");
          if (teil() === "geschichten") lese("/api/kinderwelten/geschichte?a=" + encodeURIComponent(x.adresse));
          else if (teil() === "buecher") lese(`/api/kinderwelten/kapitel?a=${encodeURIComponent(x.adresse)}&n=${Math.max(1, gemerkt(x.adresse))}`,
                                            { buch: { adresse: x.adresse } });
          else lese("/api/kinderwelten/beitrag?a=" + encodeURIComponent(x.adresse));
          return true;
        }
        return t !== "Escape" && t !== "Backspace";
      },
      schliesse() {},
    };
  },
};
