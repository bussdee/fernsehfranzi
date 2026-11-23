/* Malen mit Galerie (3.0): Stift an/aus und bewegen = durchgehend malen, Pinselgrößen, Füllen,
   Rückgängig, Speichern. Die Galerie (alle gespeicherten Bilder) ist Teil von Malen. */
import { el } from "../gemeinsam.js";
import { kopf, ton, menue } from "./kern.js";

const FARBEN = ["#222222", "#ff4d4d", "#ff9f1c", "#ffd23f", "#3ecf6f", "#3a86ff", "#9b5de5", "#ffffff"];
const PINSEL = [4, 10, 22];

export default {
  symbol: "🎨",
  oeffne(box, api) {
    const { inhalt, punkte, hilfe } = kopf(box, "Malen",
      "Pfeile Bewegen · OK Stift an/aus · 1–8 Farbe · 9 Pinsel · 0/Y Menü · STOP Zurück");
    const breite = Math.floor(innerWidth * 0.68), hoehe = Math.floor(innerHeight * 0.7);
    const canvas = el("canvas", { class: "spielfeld", width: breite, height: hoehe, style: "background:#fff" });
    const zeiger = el("canvas", { width: breite, height: hoehe, style: "position:absolute;left:0;top:0;pointer-events:none" });
    const buehne = el("div", { style: "position:relative" }, canvas, zeiger);
    const farbleiste = el("div");
    FARBEN.forEach((f, i) => farbleiste.append(el("span", { class: "farbfeld", style: `background:${f}`, title: String(i + 1) })));
    const anzeige = el("div", { class: "leise" });
    const werkzeuge = el("div", { class: "werkzeuge" }, el("div", { class: "leise", text: "Farben 1–8" }), farbleiste, anzeige);
    const bereich = el("div", { class: "malen" }, buehne, werkzeuge);
    inhalt.append(bereich);

    const g = canvas.getContext("2d", { willReadFrequently: true });
    const z = zeiger.getContext("2d");
    g.fillStyle = "#fff";
    g.fillRect(0, 0, breite, hoehe);
    const s = { x: breite / 2, y: hoehe / 2, stift: false, farbe: 1, pinsel: 1, schritt: 14, verlauf: [], menue: null, galerie: null };

    function merke() {
      s.verlauf.push(g.getImageData(0, 0, breite, hoehe));
      if (s.verlauf.length > 12) s.verlauf.shift();
    }

    function zeichneZeiger() {
      z.clearRect(0, 0, breite, hoehe);
      z.strokeStyle = s.stift ? FARBEN[s.farbe] : "#888";
      z.lineWidth = 3;
      z.beginPath();
      z.arc(s.x, s.y, PINSEL[s.pinsel] / 2 + 6, 0, Math.PI * 2);
      z.stroke();
      if (!s.stift) {
        z.beginPath(); z.moveTo(s.x - 12, s.y); z.lineTo(s.x + 12, s.y); z.moveTo(s.x, s.y - 12); z.lineTo(s.x, s.y + 12); z.stroke();
      }
      farbleiste.querySelectorAll(".farbfeld").forEach((f, i) => f.classList.toggle("aktiv", i === s.farbe));
      anzeige.textContent = `Pinsel: ${["fein", "mittel", "dick"][s.pinsel]} · Stift ${s.stift ? "AN – bewegen malt" : "aus"}`;
    }

    function punkt() {
      g.fillStyle = FARBEN[s.farbe];
      g.beginPath();
      g.arc(s.x, s.y, PINSEL[s.pinsel] / 2, 0, Math.PI * 2);
      g.fill();
    }

    function bewege(dx, dy) {
      const ax = s.x, ay = s.y;
      s.x = Math.max(0, Math.min(breite, s.x + dx * s.schritt));
      s.y = Math.max(0, Math.min(hoehe, s.y + dy * s.schritt));
      if (s.stift) {
        g.strokeStyle = FARBEN[s.farbe];
        g.lineWidth = PINSEL[s.pinsel];
        g.lineCap = "round";
        g.beginPath(); g.moveTo(ax, ay); g.lineTo(s.x, s.y); g.stroke();
      }
      zeichneZeiger();
    }

    function fuellen() {
      merke();
      const bild = g.getImageData(0, 0, breite, hoehe), d = bild.data;
      const x0 = Math.floor(s.x), y0 = Math.floor(s.y), start = (y0 * breite + x0) * 4;
      const ziel = [d[start], d[start + 1], d[start + 2]];
      const neu = FARBEN[s.farbe].match(/\w\w/g).map((h) => parseInt(h, 16));
      if (ziel.every((v, i) => Math.abs(v - neu[i]) < 8)) return;
      const gleich = (i) => Math.abs(d[i] - ziel[0]) < 40 && Math.abs(d[i + 1] - ziel[1]) < 40 && Math.abs(d[i + 2] - ziel[2]) < 40;
      const stapel = [[x0, y0]];
      while (stapel.length) {
        const [x, y] = stapel.pop();
        let links = x;
        while (links > 0 && gleich((y * breite + links - 1) * 4)) links--;
        for (let i = links; i < breite && gleich((y * breite + i) * 4); i++) {
          const p = (y * breite + i) * 4;
          d[p] = neu[0]; d[p + 1] = neu[1]; d[p + 2] = neu[2]; d[p + 3] = 255;
          if (y > 0 && gleich(p - breite * 4)) stapel.push([i, y - 1]);
          if (y < hoehe - 1 && gleich(p + breite * 4)) stapel.push([i, y + 1]);
        }
      }
      g.putImageData(bild, 0, 0);
      ton("ok");
    }

    async function speichern() {
      try {
        await api.sende("/api/zeichnung", { bild: canvas.toDataURL("image/png") });
        api.hinweis("Bild gespeichert – es ist jetzt in der Galerie.");
        ton("sieg");
      } catch (f) { api.hinweis(f.message || "Speichern hat nicht geklappt.", 6000); ton("fehler"); }
    }

    function schliesseMenue() { s.menue?.box.remove(); s.menue = null; }

    function oeffneMenue() {
      const kasten = el("div", { class: "overlay", style: "background:rgba(8,12,20,.92);z-index:32;justify-content:center" });
      box.append(kasten);
      const m = menue(kasten, [
        { text: "Speichern", aktion: () => { schliesseMenue(); speichern(); } },
        { text: "Füllen", aktion: () => { schliesseMenue(); fuellen(); } },
        { text: "Rückgängig", aktion: () => { schliesseMenue(); const b = s.verlauf.pop(); if (b) g.putImageData(b, 0, 0); } },
        { text: "Neues Bild", aktion: () => { schliesseMenue(); merke(); g.fillStyle = "#fff"; g.fillRect(0, 0, breite, hoehe); } },
        { text: "Galerie", aktion: () => { schliesseMenue(); oeffneGalerie(); } },
        { text: "Weiter malen", aktion: schliesseMenue },
      ]);
      s.menue = { box: kasten, ...m };
    }

    async function oeffneGalerie() {
      let bilder = [];
      try { bilder = (await api.hole("/api/zeichnungen")).zeichnungen; } catch (_) { /* leer */ }
      const kasten = el("div", { class: "overlay", style: "z-index:32;align-items:center;justify-content:center;gap:2vh" });
      const titel = el("div", { class: "punkte" });
      const bild = el("img", { class: "galerie-bild", alt: "" });
      const aktionen = el("div", { class: "knopfreihe" });
      kasten.append(titel, bild, aktionen, el("div", { class: "leise", text: "← → Blättern · OK: schicken oder löschen · STOP Zurück zum Malen" }));
      box.append(kasten);
      s.galerie = { box: kasten, i: 0, bilder, titel, bild, aktionen, menue: null };
      zeigeGaleriebild();
    }

    /* 4.4: Bild an einen freigegebenen Kontakt schicken oder löschen (Speicherplatz) */
    async function galerieMenue() {
      const ga = s.galerie, b = ga.bilder[ga.i];
      if (!b) return;
      let kontakte = [];
      try { const t = await api.hole("/api/telegram"); if (t.aktiv) kontakte = t.kontakte || []; } catch (_) { /* ohne Telegram */ }
      ga.menue = { wahl: 0, eintraege: [
        ...kontakte.map((k) => ({ text: `📤 an ${k.symbol} ${k.name}`, tun: () => api.sende("/api/bild/teilen", { art: "zeichnung", name: b.datei, chat: k.id })
          .then((a) => { api.hinweis(a.meldung); ton("sieg"); }) })),
        { text: "🗑 Löschen", tun: () => api.sende("/api/kind/loeschen", { art: "zeichnung", name: b.datei }).then(() => {
          ga.bilder.splice(ga.i, 1); ga.i = Math.max(0, Math.min(ga.i, ga.bilder.length - 1)); api.hinweis("Gelöscht."); }) },
        { text: "Zurück", tun: () => Promise.resolve() },
      ] };
      zeigeGaleriebild();
    }

    function zeigeGaleriebild() {
      const ga = s.galerie;
      ga.aktionen.replaceChildren(...(ga.menue ? ga.menue.eintraege.map((e, n) => el("span", { class: "knopf" + (n === ga.menue.wahl ? " gewaehlt" : ""), text: e.text })) : []));
      if (!ga.bilder.length) { ga.titel.textContent = "Noch keine Bilder gespeichert."; ga.bild.hidden = true; return; }
      ga.bild.hidden = false;
      ga.bild.src = ga.bilder[ga.i].url;
      ga.titel.textContent = `Bild ${ga.i + 1} von ${ga.bilder.length}`;
    }

    zeichneZeiger();
    return {
      taste(t) {
        if (s.galerie?.menue) {
          const m = s.galerie.menue, n = m.eintraege.length;
          if (t === "ArrowLeft" || t === "ArrowUp") { m.wahl = (m.wahl + n - 1) % n; zeigeGaleriebild(); return true; }
          if (t === "ArrowRight" || t === "ArrowDown") { m.wahl = (m.wahl + 1) % n; zeigeGaleriebild(); return true; }
          if (t === "Enter" || t === " ") {
            const e = m.eintraege[m.wahl];
            s.galerie.menue = null;
            e.tun().catch((f) => { api.hinweis(f.message, 5000); ton("fehler"); }).finally(() => s.galerie && zeigeGaleriebild());
            return true;
          }
          if (t === "Escape" || t === "Backspace") { s.galerie.menue = null; zeigeGaleriebild(); return true; }
          return true;
        }
        if (s.galerie) {
          if (t === "Enter" || t === " ") { galerieMenue(); return true; }
          if (t === "ArrowLeft" || t === "ArrowRight") {
            const n = s.galerie.bilder.length;
            if (n) s.galerie.i = (s.galerie.i + (t === "ArrowLeft" ? n - 1 : 1)) % n;
            zeigeGaleriebild();
            return true;
          }
          if (t === "Escape" || t === "Backspace") { s.galerie.box.remove(); s.galerie = null; return true; }
          return true;
        }
        if (s.menue) {
          if (t === "Escape" || t === "Backspace" || t === "0" || t === "m") { schliesseMenue(); return true; }
          return s.menue.taste(t) || true;
        }
        const b = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[t];
        if (b) { bewege(...b); return true; }
        if (t === "Enter" || t === " ") { s.stift = !s.stift; if (s.stift) { merke(); punkt(); } zeichneZeiger(); ton("bewegen"); return true; }
        if (/^[1-8]$/.test(t)) { s.farbe = +t - 1; zeichneZeiger(); ton("bewegen"); return true; }
        if (t === "9") { s.pinsel = (s.pinsel + 1) % PINSEL.length; zeichneZeiger(); return true; }
        if (t === "0" || t === "m" || t === "p" || t === "P") { oeffneMenue(); return true; }
        return false;
      },
      schliesse() {},
    };
  },
};
