/* FernsehFranzi 3.5/4.0 - Nachrichten: neue und alte Nachrichten und Erinnerungen (wie die Mitteilungen am Handy).
 * Öffnen bestätigt alle neuen. ↑ ↓ wählen · STOP zurück.
 * 4.0: Ist Telegram eingerichtet, antwortet OK mit vorbereiteten Texten (an den Absender, sonst an alle).
 * 4.1: „⌨️ Eigenen Text tippen“ (wenn die Eltern es erlauben): mit der Tastatur schreiben, Enter senden, STOP abbrechen,
 *      Backspace löscht das letzte Zeichen. Die Pfeiltasten bewegen keinen Cursor (Pfeile = immer Navigation). */
import { el } from "../gemeinsam.js";
import { kopf, ton } from "./kern.js";

function wann(iso) {
  const d = new Date(iso), heute = new Date();
  const uhr = iso.slice(11, 16);
  if (d.toDateString() === heute.toDateString()) return `heute ${uhr}`;
  const gestern = new Date(heute); gestern.setDate(heute.getDate() - 1);
  if (d.toDateString() === gestern.toDateString()) return `gestern ${uhr}`;
  return `${iso.slice(8, 10)}.${iso.slice(5, 7)}. ${uhr}`;
}

export default {
  symbol: "🔔",
  oeffne(box, api) {
    const { inhalt, hilfe } = kopf(box, "🔔 Nachrichten", "↑ ↓ blättern · STOP zurück");
    let liste = [], wahl = 0, telegram = { aktiv: false, antworten: [] }, antwort = null, tippen = null;
    const SICHTBAR = 6, TEXT_MAX = 300;
    const TIPPEN = "⌨️ Eigenen Text tippen";
    const wahlen = () => (telegram.eigene_texte ? [TIPPEN] : []).concat(telegram.antworten);

    const zeige = () => {
      if (tippen) return zeigeTippen();
      if (antwort) return zeigeAntworten();
      const eintraege = telegram.aktiv ? [{ schreiben: true }, ...liste] : liste;
      hilfe.textContent = telegram.aktiv ? "↑ ↓ wählen · OK antworten · STOP zurück" : "↑ ↓ blättern · STOP zurück";
      if (!eintraege.length) { inhalt.replaceChildren(el("div", { class: "witz", text: "Noch keine Nachrichten. 📭" })); return; }
      wahl = Math.min(wahl, eintraege.length - 1);
      const oben = Math.max(0, Math.min(wahl - 2, eintraege.length - SICHTBAR));
      inhalt.replaceChildren(el("div", { class: "nachrichten-liste" }, ...eintraege.slice(oben, oben + SICHTBAR).map((m, i) => {
        const gewaehlt = telegram.aktiv && oben + i === wahl ? " gewaehlt" : "";
        if (m.schreiben) return el("div", { class: "nachricht schreiben" + gewaehlt }, el("div", { class: "nachricht-text", text: "✏️ Nachricht an die Familie schreiben" }));
        return el("div", { class: "nachricht" + (m.gesehen ? "" : " neu") + gewaehlt },
          el("div", { class: "nachricht-kopf" }, el("b", { text: m.quelle || "Nachricht" }), el("span", { text: wann(m.zeit) })),
          el("div", { class: "nachricht-text", text: m.text }));
      })));
    };

    const zeigeAntworten = () => {
      hilfe.textContent = "↑ ↓ wählen · OK senden · STOP zurück";
      inhalt.replaceChildren(el("div", { class: "nachrichten-liste" },
        el("p", { class: "punkte", text: antwort.an ? `Antwort an ${antwort.an}` : "An die Familie" }),
        ...wahlen().map((t, i) => el("div", { class: "nachricht schreiben" + (i === antwort.wahl ? " gewaehlt" : "") },
          el("div", { class: "nachricht-text", text: t })))));
    };

    const zeigeTippen = () => {
      hilfe.textContent = "Tippen · Enter senden · ⌫ löschen · STOP abbrechen";
      inhalt.replaceChildren(el("div", { class: "nachrichten-liste" },
        el("p", { class: "punkte", text: antwort.an ? `Nachricht an ${antwort.an}` : "Nachricht an die Familie" }),
        el("div", { class: "nachricht tippen" }, el("div", { class: "nachricht-text" },
          el("span", { text: tippen.text }), el("span", { class: "schreibmarke", text: "▏" }))),
        el("p", { class: "leise", text: `${tippen.text.length} / ${TEXT_MAX}` })));
    };

    async function senden(eigener) {
      const text = eigener ?? wahlen()[antwort.wahl];
      try {
        const a = await api.sende("/api/telegram/senden", { text, chat: antwort.chat });
        api.hinweis(a.meldung); ton("sieg");
        antwort = null; tippen = null; zeige();
      } catch (fehler) { api.hinweis(fehler.message, 5000); ton("fehler"); }
    }

    Promise.all([api.hole("/api/meldungen"), api.hole("/api/telegram").catch(() => ({ aktiv: false, antworten: [] }))]).then(([d, t]) => {
      liste = d.meldungen;
      telegram = t;
      zeige();
      const neu = liste.filter((m) => !m.gesehen).map((m) => m.nr);
      if (neu.length) { ton("ok"); api.sende("/api/meldungen/gesehen", { nummern: neu }).catch(() => {}); }
    }).catch((f) => inhalt.replaceChildren(el("div", { class: "meldung-fehler", text: f.message })));

    return {
      taste(t) {
        if (tippen) {
          if (t === "Escape") { tippen = null; zeige(); return true; }
          if (t === "Enter") { if (tippen.text.trim() && !tippen.sendet) { tippen.sendet = true; senden(tippen.text).finally(() => { if (tippen) tippen.sendet = false; }); } return true; }
          if (t === "Backspace") { tippen.text = [...tippen.text].slice(0, -1).join(""); zeige(); return true; }
          if ([...t].length === 1 && tippen.text.length < TEXT_MAX) { tippen.text += t; zeige(); }
          return true;                                            /* alles andere (auch Pfeile) tut hier nichts */
        }
        if (antwort) {
          if (t === "ArrowDown") { antwort.wahl = Math.min(wahlen().length - 1, antwort.wahl + 1); zeige(); ton("bewegen"); return true; }
          if (t === "ArrowUp") { antwort.wahl = Math.max(0, antwort.wahl - 1); zeige(); ton("bewegen"); return true; }
          if (t === "Enter" || t === " ") {
            if (wahlen()[antwort.wahl] === TIPPEN) { tippen = { text: "" }; zeige(); ton("ok"); }
            else senden();
            return true;
          }
          if (t === "Escape" || t === "Backspace") { antwort = null; zeige(); return true; }
          return true;
        }
        const anzahl = liste.length + (telegram.aktiv ? 1 : 0);
        if (t === "ArrowDown") { wahl = Math.min(Math.max(0, anzahl - 1), wahl + 1); zeige(); return true; }
        if (t === "ArrowUp") { wahl = Math.max(0, wahl - 1); zeige(); return true; }
        if ((t === "Enter" || t === " ") && telegram.aktiv && wahlen().length) {
          const m = wahl === 0 ? null : liste[wahl - 1];
          antwort = { wahl: 0, chat: m?.chat ?? null, an: m?.chat ? m.quelle : "" };
          zeige(); ton("ok");
          return true;
        }
        return t !== "Escape" && t !== "Backspace";
      },
      schliesse() {},
    };
  },
};
