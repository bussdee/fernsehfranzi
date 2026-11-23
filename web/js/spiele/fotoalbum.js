/* FernsehFranzi 4.4 - Fotoalbum: Bilder aussuchen und als Bildschirmschoner zeigen (z. B. wenn Freunde zu Besuch sind).
 *
 * Drei Quellen: 📁 der Foto-Ordner der Eltern (FileBrowser-Freigabe), 📷 das eigene Album (Fotos von Telegram, mit
 * „⭐ Ins Album“ übernommen) und 🎨 die eigenen Zeichnungen. Oben schaltet das Kind den Bildschirmschoner ein und aus.
 * Pfeile wählen, OK: ⭐ aussuchen (im Ordner) bzw. Menü mit ⭐, Schicken, Löschen (Album, Zeichnungen).
 * Ist der Speicher voll, zeigt die Leiste das an - dann alte Bilder löschen. */
import { el } from "../gemeinsam.js";
import { kopf, ton } from "./kern.js";

const SPALTEN = 5;

export default {
  symbol: "🖼️",
  oeffne(box, api) {
    box.classList.add("fotoalbum");
    const { inhalt, punkte, hilfe } = kopf(box, "🖼️ Fotoalbum", "Pfeile wählen · OK auswählen · STOP zurück");
    const z = { fa: null, quelle: "ordner", pfad: "", eintraege: [], wahl: -1, kopfWahl: 0, menue: null, speicher: null, kontakte: [] };

    async function lade() {
      try {
        z.fa = await api.hole("/api/fotoalbum");
        if (!z.fa.ordner && z.quelle === "ordner") z.quelle = "album";
        try { const t = await api.hole("/api/telegram"); z.kontakte = t.aktiv ? t.kontakte || [] : []; } catch (_) { z.kontakte = []; }
        await ladeQuelle();
      } catch (f) { inhalt.replaceChildren(el("div", { class: "witz", text: f.message })); }
    }

    async function ladeQuelle() {
      z.menue = null;
      if (z.quelle === "ordner") {
        const d = await api.hole("/api/fotoalbum/liste?pfad=" + encodeURIComponent(z.pfad));
        z.eintraege = [...(d.eltern !== null ? [{ art: "hoch", pfad: d.eltern, name: "⬆ zurück" }] : []),
          ...d.ordner.map((o) => ({ art: "ordner", pfad: o.pfad, name: o.name })),
          ...d.titel.map((b) => ({ art: "bild", id: "ordner:" + b.pfad, name: b.name, url: "/api/fotoalbum/bild?pfad=" + encodeURIComponent(b.pfad) }))];
      } else if (z.quelle === "album") {
        const d = await api.hole("/api/album");
        z.speicher = d.speicher;
        z.eintraege = d.bilder.map((b) => ({ art: "bild", id: "album:" + b.datei, name: b.datei, datei: b.datei, url: b.url, eigen: "album" }));
      } else {
        const d = await api.hole("/api/zeichnungen");
        z.eintraege = d.zeichnungen.map((b) => ({ art: "bild", id: "zeichnung:" + b.datei, name: b.datei, datei: b.datei, url: b.url, eigen: "zeichnung" }));
        try { z.speicher = await api.hole("/api/speicher"); } catch (_) { /* egal */ }
      }
      z.wahl = Math.min(z.wahl, z.eintraege.length - 1);
      zeige();
    }

    const kopfKnoepfe = () => [
      ...(z.fa.ordner ? [{ text: "📁 Fotos", quelle: "ordner" }] : []),
      { text: "📷 Mein Album", quelle: "album" }, { text: "🎨 Meine Bilder", quelle: "zeichnungen" },
      { text: z.fa.bildschirmschoner ? "🖥️ Bildschirmschoner: AN" : "🖥️ Bildschirmschoner: aus", schoner: true },
    ];

    function zeige() {
      const gewaehlt = new Set(z.fa.auswahl);
      punkte.textContent = `⭐ ${gewaehlt.size} ausgesucht` + (z.speicher ? ` · Speicher ${z.speicher.belegt_mb} von ${z.speicher.limit_mb} MB${z.speicher.voll ? " – voll!" : ""}` : "");
      const kk = kopfKnoepfe();
      const leiste = el("div", { class: "knopfreihe fa-leiste" }, ...kk.map((k, i) => el("span", {
        class: "knopf" + (z.wahl < 0 && i === z.kopfWahl ? " gewaehlt" : "") + ((k.quelle && k.quelle === z.quelle) || (k.schoner && z.fa.bildschirmschoner) ? " an" : ""), text: k.text })));
      const raster = el("div", { class: "fa-raster" }, ...z.eintraege.map((e, i) => el("div", { class: "fa-kachel" + (i === z.wahl ? " gewaehlt" : "") },
        e.art === "bild" ? el("img", { src: e.url, alt: "", loading: "lazy" }) : el("div", { class: "fa-ordner", text: e.art === "hoch" ? "⬆" : "📁" }),
        el("span", { class: "fa-name", text: e.art === "bild" ? "" : e.name }),
        e.art === "bild" && gewaehlt.has(e.id) ? el("span", { class: "fa-stern", text: "⭐" }) : null)));
      const leer = !z.eintraege.length ? el("div", { class: "witz", text: z.quelle === "album" ? "Noch keine Fotos im Album. Fotos aus Nachrichten kommen mit „⭐ Ins Album“ hierher." :
        z.quelle === "zeichnungen" ? "Noch keine gemalten Bilder." : "Dieser Ordner ist leer." }) : null;
      const menue = z.menue ? el("div", { class: "knopfreihe fa-menue" }, ...z.menue.eintraege.map((m, i) => el("span", { class: "knopf" + (i === z.menue.wahl ? " gewaehlt" : ""), text: m.text }))) : null;
      inhalt.replaceChildren(...[leiste, menue, leer, raster].filter(Boolean));
      inhalt.querySelector(".fa-kachel.gewaehlt")?.scrollIntoView({ block: "nearest" });
      hilfe.textContent = z.menue ? "← → wählen · OK · STOP zurück" : "Pfeile wählen · OK: ⭐ aussuchen / öffnen · STOP zurück";
    }

    async function speichereAuswahl(neu) {
      z.fa = await api.sende("/api/fotoalbum", { auswahl: neu });
    }

    async function stern(e) {
      const gesetzt = z.fa.auswahl.includes(e.id);
      await speichereAuswahl(gesetzt ? z.fa.auswahl.filter((a) => a !== e.id) : [...z.fa.auswahl, e.id]);
      ton(gesetzt ? "bewegen" : "ok");
      zeige();
    }

    function bildMenue(e) {
      z.menue = { wahl: 0, eintraege: [
        { text: z.fa.auswahl.includes(e.id) ? "🚫 Nicht mehr zeigen" : "⭐ Im Bildschirmschoner zeigen", tun: () => stern(e) },
        ...z.kontakte.map((k) => ({ text: `📤 an ${k.symbol} ${k.name}`, tun: () => api.sende("/api/bild/teilen", { art: e.eigen, name: e.datei, chat: k.id })
          .then((a) => { api.hinweis(a.meldung); ton("sieg"); }) })),
        { text: "🗑 Löschen", tun: () => api.sende("/api/kind/loeschen", { art: e.eigen, name: e.datei }).then(async (a) => {
          z.speicher = a.speicher; z.fa = await api.hole("/api/fotoalbum"); api.hinweis("Gelöscht."); await ladeQuelle(); }) },
        { text: "Zurück", tun: () => Promise.resolve() },
      ] };
      zeige();
    }

    function bewege(dx, dy) {
      if (z.wahl < 0) {
        const n = kopfKnoepfe().length;
        if (dx) { z.kopfWahl = (z.kopfWahl + dx + n) % n; zeige(); ton("bewegen"); }
        if (dy > 0 && z.eintraege.length) { z.wahl = 0; zeige(); ton("bewegen"); }
        return;
      }
      let neu = z.wahl + dx + dy * SPALTEN;
      if (neu < 0 && dy < 0) { z.wahl = -1; zeige(); return; }
      neu = Math.max(0, Math.min(z.eintraege.length - 1, neu));
      if (neu !== z.wahl) { z.wahl = neu; zeige(); ton("bewegen"); }
    }

    lade();
    return {
      taste(t) {
        if (!z.fa) return t !== "Escape" && t !== "Backspace";
        if (z.menue) {
          const n = z.menue.eintraege.length;
          if (t === "ArrowLeft" || t === "ArrowUp") { z.menue.wahl = (z.menue.wahl + n - 1) % n; zeige(); return true; }
          if (t === "ArrowRight" || t === "ArrowDown") { z.menue.wahl = (z.menue.wahl + 1) % n; zeige(); return true; }
          if (t === "Enter" || t === " ") { const m = z.menue.eintraege[z.menue.wahl]; z.menue = null; m.tun().catch((f) => { api.hinweis(f.message, 5000); ton("fehler"); }).finally(zeige); return true; }
          if (t === "Escape" || t === "Backspace") { z.menue = null; zeige(); return true; }
          return true;
        }
        const richtung = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[t];
        if (richtung) { bewege(...richtung); return true; }
        if (t === "Enter" || t === " ") {
          if (z.wahl < 0) {
            const k = kopfKnoepfe()[z.kopfWahl];
            if (k.schoner) {
              api.sende("/api/fotoalbum", { bildschirmschoner: !z.fa.bildschirmschoner }).then((fa) => {
                z.fa = fa; api.hinweis(fa.bildschirmschoner ? (fa.auswahl.length ? "Deine Bilder sind jetzt der Bildschirmschoner." : "An – such dir noch Bilder aus (⭐).") : "Bildschirmschoner: wieder deine Zeichnungen."); zeige();
              }).catch((f) => api.hinweis(f.message, 5000));
            } else { z.quelle = k.quelle; z.pfad = ""; z.wahl = -1; ladeQuelle().catch((f) => api.hinweis(f.message, 5000)); }
            ton("ok");
            return true;
          }
          const e = z.eintraege[z.wahl];
          if (!e) return true;
          if (e.art === "ordner" || e.art === "hoch") { z.pfad = e.pfad || ""; z.wahl = 0; ladeQuelle().catch((f) => api.hinweis(f.message, 5000)); return true; }
          if (e.eigen) bildMenue(e); else stern(e).catch((f) => api.hinweis(f.message, 5000));
          return true;
        }
        if ((t === "Escape" || t === "Backspace") && z.quelle === "ordner" && z.pfad) {
          z.pfad = z.pfad.includes("/") ? z.pfad.slice(0, z.pfad.lastIndexOf("/")) : ""; z.wahl = 0;
          ladeQuelle().catch((f) => api.hinweis(f.message, 5000));
          return true;
        }
        return t !== "Escape" && t !== "Backspace";
      },
      schliesse() {},
    };
  },
};
