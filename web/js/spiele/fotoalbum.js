/* FernsehFranzi 4.4 - Fotoalbum: Bilder aussuchen und als Diashow zeigen (z. B. wenn Freunde zu Besuch sind).
 *
 * 6.8.7: Mosaik mit vollständigen Miniaturen im Originalformat. Die Miniaturen werden einmal (nacheinander) verkleinert
 * und für die Sitzung gemerkt; ein Pfeildruck verschiebt nur die Markierung - vorher wurde bei jedem Druck alles neu
 * aufgebaut und jedes Foto in voller Größe neu entpackt (kurz schwarzer Bildschirm). Die Diashow startet nur noch von Hand.
 *
 * Drei Quellen: 📁 der Foto-Ordner der Eltern (FileBrowser-Freigabe), 📷 das eigene Album (Fotos von Telegram, mit
 * „⭐ Ins Album“ übernommen) und 🎨 die eigenen Zeichnungen. Oben schaltet das Kind den Bildschirmschoner ein und aus.
 * Pfeile wählen, OK: ⭐ aussuchen (im Ordner) bzw. Menü mit ⭐, Schicken, Löschen (Album, Zeichnungen).
 * Ist der Speicher voll, zeigt die Leiste das an - dann alte Bilder löschen. */
import { el } from "../gemeinsam.js";
import { kopf, ton } from "./kern.js";

const MINI_H = 220;                         /* Höhe der Miniaturen in Pixeln (Breite nach Seitenverhältnis) */
const miniaturen = new Map();               /* url -> {canvas, verhaeltnis} - bleibt für die Sitzung */
let warteschlange = Promise.resolve();
function miniatur(url) {
  if (miniaturen.has(url)) return miniaturen.get(url);
  const versprechen = (warteschlange = warteschlange.then(async () => {      /* eins nach dem anderen (Pi 3) */
    const roh = await createImageBitmap(await (await fetch(url)).blob());
    const h = Math.min(MINI_H, roh.height), w = Math.max(1, Math.round(roh.width * h / roh.height));
    const klein = await createImageBitmap(roh, { resizeWidth: w, resizeHeight: h, resizeQuality: "medium" });
    roh.close();
    const canvas = el("canvas", { width: w, height: h });
    canvas.getContext("2d").drawImage(klein, 0, 0);
    klein.close();
    return { canvas, verhaeltnis: w / h };
  }).catch(() => null));           /* nicht zu entpacken: dann das Bild selbst (siehe baueRaster) */
  miniaturen.set(url, versprechen);
  return versprechen;
}

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
      raster = null;                                     /* neuer Ordner: Raster neu bauen (Miniaturen bleiben gemerkt) */
      zeige();
    }

    const kopfKnoepfe = () => [
      ...(z.fa.ordner ? [{ text: "📁 Fotos", quelle: "ordner" }] : []),
      { text: "📷 Mein Album", quelle: "album" }, { text: "🎨 Meine Bilder", quelle: "zeichnungen" },
      { text: "▶ Diashow", diashow: true },                     /* 6.8.7: nur noch von Hand */
    ];

    /* Raster einmal je Ordner bauen; danach nur Markierung, Sterne, Leiste und Menü auffrischen */
    let raster = null, kacheln = [], leer = null;
    function baueRaster() {
      kacheln = z.eintraege.map((e) => {
        const k = el("div", { class: "fa-kachel" + (e.art === "bild" ? " fa-foto" : "") },
          e.art === "bild" ? el("div", { class: "fa-platz" }) : el("div", { class: "fa-ordner", text: e.art === "hoch" ? "⬆" : "📁" }),
          el("span", { class: "fa-name", text: e.art === "bild" ? "" : e.name }),
          el("span", { class: "fa-stern", text: "⭐" }));
        if (e.art === "bild") {
          miniatur(e.url).then((m) => {
            if (!m) {                                    /* Notweg: das Bild selbst, vollständig im Originalformat */
              const img = el("img", { src: e.url, alt: "" });
              img.addEventListener("load", () => k.style.setProperty("--verhaeltnis", (img.naturalWidth / Math.max(1, img.naturalHeight)).toFixed(3)));
              img.addEventListener("error", () => { k.querySelector(".fa-platz, img")?.replaceWith(el("div", { class: "fa-platz", text: "🖼️" })); });
              k.querySelector(".fa-platz").replaceWith(img);
              return;
            }
            const bild = m.canvas.cloneNode(false);
            bild.getContext("2d").drawImage(m.canvas, 0, 0);
            k.style.setProperty("--verhaeltnis", m.verhaeltnis.toFixed(3));
            k.querySelector(".fa-platz").replaceWith(bild);
          });
        }
        return k;
      });
      raster = el("div", { class: "fa-raster fa-mosaik" }, ...kacheln);
      leer = !z.eintraege.length ? el("div", { class: "witz", text: z.quelle === "album" ? "Noch keine Fotos im Album. Fotos aus Nachrichten kommen mit „⭐ Ins Album“ hierher." :
        z.quelle === "zeichnungen" ? "Noch keine gemalten Bilder." : "Dieser Ordner ist leer." }) : null;
    }
    function zeige() {
      if (!raster) baueRaster();
      const gewaehlt = new Set(z.fa.auswahl);
      punkte.textContent = `⭐ ${gewaehlt.size} für die Diashow` + (z.speicher ? ` · Speicher ${z.speicher.belegt_mb} von ${z.speicher.limit_mb} MB${z.speicher.voll ? " – voll!" : ""}` : "");
      const kk = kopfKnoepfe();
      const leiste = el("div", { class: "knopfreihe fa-leiste" }, ...kk.map((k, i) => el("span", {
        class: "knopf" + (z.wahl < 0 && i === z.kopfWahl ? " gewaehlt" : "") + (k.quelle && k.quelle === z.quelle ? " an" : ""), text: k.text })));
      const menue = z.menue ? el("div", { class: "knopfreihe fa-menue" }, ...z.menue.eintraege.map((m, i) => el("span", { class: "knopf" + (i === z.menue.wahl ? " gewaehlt" : ""), text: m.text }))) : null;
      kacheln.forEach((k, i) => {
        k.classList.toggle("gewaehlt", i === z.wahl);
        k.classList.toggle("mit-stern", z.eintraege[i].art === "bild" && gewaehlt.has(z.eintraege[i].id));
      });
      const teile = [leiste, menue, leer, raster].filter(Boolean);
      if (inhalt.children.length !== teile.length || [...inhalt.children].some((c, i) => c !== teile[i])) {
        inhalt.replaceChildren(...teile);                 /* das Raster selbst wird nur umgehängt, nicht neu gebaut */
      }
      kacheln[z.wahl]?.scrollIntoView({ block: "nearest" });
      hilfe.textContent = z.menue ? "← → wählen · OK · STOP zurück" : "Pfeile wählen · OK: ⭐ für die Diashow / öffnen · STOP zurück";
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
        { text: z.fa.auswahl.includes(e.id) ? "🚫 Nicht mehr zeigen" : "⭐ In der Diashow zeigen", tun: () => stern(e) },
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
      let neu = z.wahl + dx;
      if (dy) {                                          /* Mosaik: nächste Reihe nach Lage auf dem Bildschirm */
        const jetzt = kacheln[z.wahl].getBoundingClientRect(), mitte = jetzt.left + jetzt.width / 2;
        let beste = -1, abstand = Infinity;
        kacheln.forEach((k, i) => {
          const r = k.getBoundingClientRect();
          const reihe = dy > 0 ? r.top > jetzt.top + 4 : r.top < jetzt.top - 4;
          if (!reihe) return;
          const d = Math.abs(r.top - jetzt.top) * 4 + Math.abs(r.left + r.width / 2 - mitte);
          if (d < abstand) { abstand = d; beste = i; }
        });
        if (beste < 0 && dy < 0) { z.wahl = -1; zeige(); return; }
        neu = beste < 0 ? z.wahl : beste;
      }
      if (neu < 0) { z.wahl = -1; zeige(); return; }
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
            if (k.diashow) { api.diashow?.(); ton("ok"); return true; }
            z.quelle = k.quelle; z.pfad = ""; z.wahl = -1; ladeQuelle().catch((f) => api.hinweis(f.message, 5000));
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
