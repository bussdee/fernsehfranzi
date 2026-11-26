/* FernsehFranzi 5.0 - Schule: Stundenplan, Hausaufgaben, Termine und Klassennachrichten aus der Klassenkiste.
 * Nur lesen - hier wird nichts abgehakt und nichts als gelesen markiert (das geht weiter in der Klassenkiste selbst).
 * ← → Reiter · ↑ ↓ wählen · OK Nachricht oder Hausaufgabe ganz lesen · STOP zurück */
import { el } from "../gemeinsam.js";
import { kopf, ton } from "./kern.js";
import { reiter, liste, leser, hinweisZeile } from "./seite.js";

const REITER = ["📅 Heute", "📝 Hausaufgaben", "🗓️ Termine", "✉️ Nachrichten", "🎒 Morgen"];

function stundenEintraege(stunden) {
  return stunden.map((s) => ({
    symbol: s.faellt_aus ? "❌" : s.laeuft ? "▶️" : s.geaendert ? "🔄" : "📘",
    titel: `${s.nr ? s.nr + ". " : ""}${s.fach || "Unterricht"}${s.faellt_aus ? " – fällt aus" : ""}`,
    zeile: [s.von && (s.bis ? `${s.von}–${s.bis}` : s.von), s.raum && `Raum ${s.raum}`, s.geaendert && !s.faellt_aus && "geändert"]
      .filter(Boolean).join(" · "),
    aus: s.faellt_aus,
  }));
}

export default {
  symbol: "🏫",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "🏫 Schule", "← → Reiter · ↑ ↓ wählen · OK lesen · STOP zurück");
    const z = { daten: null, reiter: 0, wahl: 0, lesen: null };

    function eintraege() {
      const s = z.daten?.stand;
      if (!s) return [];
      if (z.reiter === 0) return s.frei.length ? s.frei.map((f) => ({ symbol: "🎉", titel: `Heute schulfrei: ${f}` })) : stundenEintraege(s.stunden);
      if (z.reiter === 1) return s.hausaufgaben.map((h) => ({ symbol: h.bis_morgen ? "⏰" : "📝", titel: `${h.fach ? h.fach + ": " : ""}${h.titel}`,
        zeile: [h.faellig_text && `bis ${h.faellig_text}`, h.klasse].filter(Boolean).join(" · "), neu: h.bis_morgen, lesen: h }));
      if (z.reiter === 2) return s.termine.map((t) => ({ symbol: t.von_schule ? "🏫" : "🗓️", titel: t.titel,
        rechts: `${t.tag_text}${t.uhr ? " " + t.uhr : ""}`, zeile: t.klasse }));
      if (z.reiter === 3) return s.nachrichten.map((m) => ({ symbol: m.angeheftet ? "📌" : m.nur_fuer_mich ? "💌" : "✉️",
        titel: m.titel || m.text.slice(0, 60), zeile: [m.von, m.datum_text].filter(Boolean).join(" · "), lesen: m }));
      const m = s.morgen;
      if (!m.datum) return [];
      return [{ symbol: "🎒", titel: m.satz || `${m.name}: kein Stundenplan eingetragen`, markieren: false }]
        .concat(m.frei.length ? [] : stundenEintraege(m.stunden));
    }

    function zeige() {
      if (z.lesen) return;
      const d = z.daten;
      if (!d) { inhalt.replaceChildren(hinweisZeile("Einen Moment, die Klassenkiste wird gefragt …")); return; }
      if (!d.aktiv) { inhalt.replaceChildren(hinweisZeile("Die Schul-Seite ist ausgeschaltet.", "🔒")); return; }
      if (!d.stand) { inhalt.replaceChildren(hinweisZeile(d.fehler || "Die Klassenkiste wird gerade gefragt …", d.fehler ? "⚠️" : "⏳")); return; }
      punkte.textContent = d.zeit ? `Stand ${d.zeit}` + (d.fehler || d.hinweis ? " · gerade nicht erreichbar" : "") : "";
      const e = eintraege();
      z.wahl = Math.min(z.wahl, Math.max(0, e.length - 1));
      const leer = ["Heute kein Unterricht eingetragen.", "Keine offenen Hausaufgaben. 🎉", "Keine Termine in nächster Zeit.",
                    "Keine Nachrichten.", "Für den nächsten Schultag ist nichts eingetragen."][z.reiter];
      inhalt.replaceChildren(el("div", { class: "seite" }, reiter(REITER, z.reiter),
        liste(e, z.wahl, { leer, sichtbar: 6, markieren: z.reiter === 1 || z.reiter === 3 })));
    }

    function oeffneLesen(x) {
      const bloecke = (x.text || "").split(/\n+/).filter(Boolean).map((t) => ({ art: "p", text: t }));
      const titel = x.fach !== undefined ? `${x.fach ? x.fach + ": " : ""}${x.titel}` : (x.titel || "Nachricht");
      const unten = x.fach !== undefined ? (x.faellig_text ? `Bis ${x.faellig_text}.` : "") : [x.von, x.datum_text].filter(Boolean).join(" · ");
      z.lesen = leser(titel, bloecke.length ? bloecke : [{ art: "p", text: "Kein weiterer Text." }], { unten });
      hilfe.textContent = "↑ ↓ blättern · STOP zurück";
      inhalt.replaceChildren(z.lesen.knoten);
    }

    const laden = () => api.hole("/api/schule").then((d) => { z.daten = d; zeige(); })
      .catch((f) => inhalt.replaceChildren(hinweisZeile(f.message, "⚠️")));
    zeige();
    laden();
    const timer = setInterval(() => { if (!z.lesen) laden(); }, 60 * 1000);

    return {
      taste(t) {
        if (z.lesen) {
          if (t === "ArrowDown" || t === "ArrowUp") { z.lesen.blaettern(t === "ArrowDown" ? 1 : -1); return true; }
          if (t === "Escape" || t === "Backspace") { z.lesen = null; hilfe.textContent = "← → Reiter · ↑ ↓ wählen · OK lesen · STOP zurück"; zeige(); return true; }
          return true;
        }
        const n = eintraege().length;
        if (t === "ArrowLeft" || t === "ArrowRight") {
          z.reiter = (z.reiter + (t === "ArrowLeft" ? -1 : 1) + REITER.length) % REITER.length; z.wahl = 0; zeige(); ton("bewegen"); return true;
        }
        if (t === "ArrowUp") { z.wahl = Math.max(0, z.wahl - 1); zeige(); ton("bewegen"); return true; }
        if (t === "ArrowDown") { z.wahl = Math.min(Math.max(0, n - 1), z.wahl + 1); zeige(); ton("bewegen"); return true; }
        if (t === "Enter" || t === " ") {
          const x = eintraege()[z.wahl]?.lesen;
          if (x) { oeffneLesen(x); ton("ok"); }
          return true;
        }
        return t !== "Escape" && t !== "Backspace";
      },
      schliesse() { clearInterval(timer); },
    };
  },
};
