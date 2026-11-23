/* FernsehFranzi 3.5/4.0 - Nachrichten: neue und alte Nachrichten und Erinnerungen (wie die Mitteilungen am Handy).
 * Öffnen bestätigt alle neuen. ↑ ↓ wählen · STOP zurück.
 * 4.0: Ist Telegram eingerichtet, antwortet OK mit vorbereiteten Texten (an den Absender, sonst an alle).
 * 4.1: „⌨️ Eigenen Text tippen“ (wenn die Eltern es erlauben): mit der Tastatur schreiben, Enter senden, STOP abbrechen,
 *      Backspace löscht das letzte Zeichen. Die Pfeiltasten bewegen keinen Cursor (Pfeile = immer Navigation).
 * 4.3: Jede Nachricht zeigt, von wem sie ist (Symbol + Name). „Nachricht schreiben“ fragt „An wen?“ – nur Kontakte, die
 *      die Eltern zum Schreiben freigegeben haben; eigene Texte nur, wenn sie für diesen Kontakt erlaubt sind.
 * 4.4: Fotos, Sprachnachrichten, Musik und Videos: OK öffnet sie groß (Ton/Video spielt), darunter „⭐ Ins Album“,
 *      „▶ Nochmal“ und „↩ Antworten“. */
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
    let spaeter = 0, ansehen = null;
    const MEDIEN_SYMBOL = { foto: "📷", sprache: "🎙️", musik: "🎵", video: "🎬" };
    let liste = [], wahl = 0, telegram = { aktiv: false, antworten: [], kontakte: [] }, antwort = null, tippen = null, empfaenger = null;
    const SICHTBAR = 6, TEXT_MAX = 300;
    const TIPPEN = "⌨️ Eigenen Text tippen";
    const kontakte = () => telegram.kontakte || [];
    const darfTippen = () => (antwort?.kontakt ? antwort.kontakt.eigene_texte : telegram.eigene_texte);
    const wahlen = () => (darfTippen() ? [TIPPEN] : []).concat(telegram.antworten);
    const kannSchreiben = () => telegram.aktiv && kontakte().length > 0;
    const antwortAn = (k) => ({ wahl: 0, chat: k ? k.id : null, an: k ? `${k.symbol} ${k.name}` : "", kontakt: k || null });

    const zeige = () => {
      if (ansehen) return zeigeMedium();
      if (tippen) return zeigeTippen();
      if (antwort) return zeigeAntworten();
      if (empfaenger) return zeigeEmpfaenger();
      const eintraege = (kannSchreiben() ? [{ schreiben: true }] : []).concat(liste, spaeter ? [{ spaeter }] : []);
      hilfe.textContent = kannSchreiben() ? "↑ ↓ wählen · OK antworten · STOP zurück" : "↑ ↓ blättern · STOP zurück";
      if (!kannSchreiben() && spaeter && wahl >= liste.length) wahl = liste.length;
      if (!eintraege.length) { inhalt.replaceChildren(el("div", { class: "witz", text: "Noch keine Nachrichten. 📭" })); return; }
      wahl = Math.min(wahl, eintraege.length - 1);
      const oben = Math.max(0, Math.min(wahl - 2, eintraege.length - SICHTBAR));
      inhalt.replaceChildren(el("div", { class: "nachrichten-liste" }, ...eintraege.slice(oben, oben + SICHTBAR).map((m, i) => {
        const gewaehlt = (kannSchreiben() || liste.some((x) => x.medium)) && oben + i === wahl ? " gewaehlt" : "";
        if (m.schreiben) return el("div", { class: "nachricht schreiben" + gewaehlt }, el("div", { class: "nachricht-text", text: "✏️ Nachricht schreiben" }));
        if (m.spaeter) return el("div", { class: "nachricht" + gewaehlt }, el("div", { class: "nachricht-text",
          text: `🔒 ${m.spaeter} ${m.spaeter === 1 ? "neue Nachricht" : "neue Nachrichten"} von Freunden – lesen kannst du sie nach der Sperrzeit.` }));
        return el("div", { class: "nachricht" + (m.gesehen ? "" : " neu") + gewaehlt },
          el("div", { class: "nachricht-kopf" }, el("b", { text: (m.symbol ? m.symbol + " " : "") + (m.quelle || "Nachricht") }), el("span", { text: wann(m.zeit) })),
          el("div", { class: "nachricht-text", text: (m.medium ? MEDIEN_SYMBOL[m.medium.art] + " " : "") + m.text }));
      })));
    };

    /* 4.4: Foto ansehen, Sprachnachricht/Video abspielen */
    const zeigeMedium = () => {
      const { m } = ansehen;
      const quelle = "/medien/" + m.medium.datei;
      if (!ansehen.knoten) {
        ansehen.knoten = m.medium.art === "foto" ? el("img", { class: "medium-gross", src: quelle, alt: "" })
          : el(m.medium.art === "video" ? "video" : "audio", { class: "medium-gross", src: quelle, autoplay: true, playsinline: true });
        ansehen.knoten.addEventListener("error", () => { api.hinweis("Diese Nachricht ist nicht mehr da (nach 7 Tagen gelöscht).", 4000); });
      }
      const k = kontakte().find((x) => x.id === m.chat);
      ansehen.knoepfe = [
        m.medium.art === "foto" ? { text: "⭐ Ins Album", tun: async () => { const a = await api.sende("/api/album/uebernehmen", { datei: m.medium.datei }); api.hinweis("Im Album ✔ (Fotoalbum)"); ton("sieg"); return a; } }
                                : { text: "▶ Nochmal", tun: async () => { ansehen.knoten.currentTime = 0; ansehen.knoten.play(); } },
        ...(telegram.aktiv && (k || !m.chat) ? [{ text: "↩ Antworten", tun: async () => { stoppeMedium(); antwort = antwortAn(k || null); zeige(); } }] : []),
        { text: "Zurück", tun: async () => { stoppeMedium(); zeige(); } },
      ];
      ansehen.wahl = Math.min(ansehen.wahl, ansehen.knoepfe.length - 1);
      hilfe.textContent = "← → wählen · OK · STOP zurück";
      inhalt.replaceChildren(el("div", { class: "medium-ansicht" },
        el("p", { class: "punkte", text: `${m.symbol ? m.symbol + " " : ""}${m.quelle || ""}: ${m.text}` }), ansehen.knoten,
        el("div", { class: "knopfreihe" }, ...ansehen.knoepfe.map((b, i) => el("span", { class: "knopf" + (i === ansehen.wahl ? " gewaehlt" : ""), text: b.text })))));
    };
    const stoppeMedium = () => { ansehen?.knoten?.pause?.(); ansehen = null; };

    const zeigeEmpfaenger = () => {
      hilfe.textContent = "↑ ↓ wählen · OK weiter · STOP zurück";
      inhalt.replaceChildren(el("div", { class: "nachrichten-liste" },
        el("p", { class: "punkte", text: "An wen?" }),
        ...kontakte().map((k, i) => el("div", { class: "nachricht schreiben" + (i === empfaenger.wahl ? " gewaehlt" : "") },
          el("div", { class: "nachricht-text", text: `${k.symbol} ${k.name}` })))));
    };

    const zeigeAntworten = () => {
      hilfe.textContent = "↑ ↓ wählen · OK senden · STOP zurück";
      inhalt.replaceChildren(el("div", { class: "nachrichten-liste" },
        el("p", { class: "punkte", text: antwort.an ? `An ${antwort.an}` : "An Mama und Papa" }),
        ...wahlen().map((t, i) => el("div", { class: "nachricht schreiben" + (i === antwort.wahl ? " gewaehlt" : "") },
          el("div", { class: "nachricht-text", text: t })))));
    };

    const zeigeTippen = () => {
      hilfe.textContent = "Tippen · Enter senden · ⌫ löschen · STOP abbrechen";
      inhalt.replaceChildren(el("div", { class: "nachrichten-liste" },
        el("p", { class: "punkte", text: antwort.an ? `Nachricht an ${antwort.an}` : "Nachricht an Mama und Papa" }),
        el("div", { class: "nachricht tippen" }, el("div", { class: "nachricht-text" },
          el("span", { text: tippen.text }), el("span", { class: "schreibmarke", text: "▏" }))),
        el("p", { class: "leise", text: `${tippen.text.length} / ${TEXT_MAX}` })));
    };

    async function senden(eigener) {
      const text = eigener ?? wahlen()[antwort.wahl];
      try {
        const a = await api.sende("/api/telegram/senden", { text, chat: antwort.chat });
        api.hinweis(a.meldung); ton("sieg");
        antwort = null; tippen = null; empfaenger = null; zeige();
      } catch (fehler) { api.hinweis(fehler.message, 5000); ton("fehler"); }
    }

    Promise.all([api.hole("/api/meldungen"), api.hole("/api/telegram").catch(() => ({ aktiv: false, antworten: [], kontakte: [] }))]).then(([d, t]) => {
      liste = d.meldungen;
      spaeter = d.freunde_spaeter || 0;
      telegram = t;
      zeige();
      const neu = liste.filter((m) => !m.gesehen).map((m) => m.nr);
      if (neu.length) { ton("ok"); api.sende("/api/meldungen/gesehen", { nummern: neu }).catch(() => {}); }
    }).catch((f) => inhalt.replaceChildren(el("div", { class: "meldung-fehler", text: f.message })));

    return {
      taste(t) {
        if (ansehen) {
          const n = ansehen.knoepfe.length;
          if (t === "ArrowRight" || t === "ArrowDown") { ansehen.wahl = (ansehen.wahl + 1) % n; zeige(); ton("bewegen"); return true; }
          if (t === "ArrowLeft" || t === "ArrowUp") { ansehen.wahl = (ansehen.wahl + n - 1) % n; zeige(); ton("bewegen"); return true; }
          if (t === "Enter" || t === " ") { ansehen.knoepfe[ansehen.wahl].tun().catch((f) => { api.hinweis(f.message, 5000); ton("fehler"); }); return true; }
          if (t === "Escape" || t === "Backspace") { stoppeMedium(); zeige(); return true; }
          return true;
        }
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
        if (empfaenger) {
          if (t === "ArrowDown") { empfaenger.wahl = Math.min(kontakte().length - 1, empfaenger.wahl + 1); zeige(); ton("bewegen"); return true; }
          if (t === "ArrowUp") { empfaenger.wahl = Math.max(0, empfaenger.wahl - 1); zeige(); ton("bewegen"); return true; }
          if (t === "Enter" || t === " ") { antwort = antwortAn(kontakte()[empfaenger.wahl]); empfaenger = null; zeige(); ton("ok"); return true; }
          if (t === "Escape" || t === "Backspace") { empfaenger = null; zeige(); return true; }
          return true;
        }
        const anzahl = liste.length + (kannSchreiben() ? 1 : 0) + (spaeter ? 1 : 0);
        if (t === "Enter" || t === " ") {                            /* 4.4: Foto/Sprache/Video öffnen */
          const m = liste[wahl - (kannSchreiben() ? 1 : 0)];
          if (m?.medium?.datei && !(kannSchreiben() && wahl === 0)) { ansehen = { m, wahl: 0 }; zeige(); ton("ok"); return true; }
        }
        if (t === "ArrowDown") { wahl = Math.min(Math.max(0, anzahl - 1), wahl + 1); zeige(); return true; }
        if (t === "ArrowUp") { wahl = Math.max(0, wahl - 1); zeige(); return true; }
        if ((t === "Enter" || t === " ") && kannSchreiben()) {
          if (wahl === 0) {                                          /* neue Nachricht: an wen? */
            if (kontakte().length === 1) antwort = antwortAn(kontakte()[0]);
            else empfaenger = { wahl: 0 };
          } else {
            const m = liste[wahl - 1];
            if (!m) { api.hinweis("Nach der Sperrzeit kannst du sie lesen und antworten.", 4000); return true; }
            if (m.chat) {
              const k = kontakte().find((x) => x.id === m.chat);
              if (!k) { api.hinweis("Diesem Kontakt kannst du nicht antworten.", 4000); ton("fehler"); return true; }
              antwort = antwortAn(k);
            } else antwort = antwortAn(null);                        /* Eltern-Seite, Erinnerung: an Mama und Papa */
          }
          zeige(); ton("ok");
          return true;
        }
        return t !== "Escape" && t !== "Backspace";
      },
      schliesse() { stoppeMedium(); },
    };
  },
};
