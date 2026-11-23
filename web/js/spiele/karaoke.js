/* FernsehFranzi 4.4 - Karaoke mit den Liedern der Klassenkiste.
 *
 * Der Fernseh-Pi liest die Karaoke-Lieder (Text und Musik) mit der Anmeldung, die in der Klassenkiste-Kachel schon
 * besteht - nur lesen, an der Klassenkiste ändert sich nichts. Der Text läuft groß im Takt des Liedes mit (über die
 * Länge des Liedes); mit dem USB-Mikro gibt es am Ende Sterne fürs Mitsingen.
 * Liste: ↑ ↓ wählen, OK singen. Im Lied: OK/PLAY Pause, ◀◀ ▶▶ 10 s, ↑ ↓ Text etwas schieben, ← → voriges/nächstes
 * Lied, STOP zurück zur Liste.
 * 4.6.1: Hat das Lied Zeitmarken (in der Klassenkiste je Zeile angetippt), wird die gerade gesungene Zeile markiert und
 * in die Mitte geholt - genau wie in der Klassenkiste. Die Zeilen werden dafür genauso gezählt wie dort (liedZeilen):
 * Leerzeilen trennen Strophen, „[Refrain]“ ist eine Überschrift. Ohne Marken läuft der Text wie bisher gleichmäßig. */
import { el } from "../gemeinsam.js";
import { kopf, ton, konfetti } from "./kern.js";
import { ctx, tonhoehe } from "./bass.js";

const SPRUNG_S = 10;
const PHP_TRIM = /^[ \t\n\r\0\x0B]+|[ \t\n\r\0\x0B]+$/g;   /* wie PHP trim() in der Klassenkiste, nicht String.trim() */
const UEBERSCHRIFT = /^\[([\s\S]+)\]$/;

/* [{art: "zeile"|"ueberschrift", text, neueStrophe, nr}] - nr zählt nur gesungene Zeilen (daran hängen die Marken) */
export function liedZeilen(text) {
  const aus = [];
  let luecke = false, nr = 0;
  for (const roh of String(text || "").split(/\r\n|\r|\n/)) {
    const z = roh.replace(PHP_TRIM, "");
    if (z === "") { luecke = aus.length > 0; continue; }
    const t = z.match(UEBERSCHRIFT);
    if (t) aus.push({ art: "ueberschrift", text: t[1], neueStrophe: luecke, nr: -1 });
    else aus.push({ art: "zeile", text: z, neueStrophe: luecke, nr: nr++ });
    luecke = false;
  }
  return aus;
}

/* Welche Zeile ist bei Sekunde t dran? Die letzte, deren Marke erreicht ist; -1 = noch vor der ersten. */
export function zeileZurZeit(marken, t) {
  let dran = -1;
  (marken || []).forEach((m, i) => { if (typeof m === "number" && m <= t) dran = i; });
  return dran;
}

export default {
  symbol: "🎤",
  oeffne(box, api) {
    box.classList.add("karaoke");
    const { inhalt, punkte, hilfe } = kopf(box, "🎤 Karaoke", "↑ ↓ wählen · OK singen · STOP zurück");
    const z = { lieder: [], wahl: 0, lied: null, audio: null, takt: null, versatz: 0, mikro: null, gesungen: 0, gehoert: 0 };

    async function lade() {
      inhalt.replaceChildren(el("div", { class: "witz", text: "Ich hole die Lieder aus der Klassenkiste …" }));
      try {
        z.lieder = (await api.hole("/api/karaoke")).lieder;
        zeigeListe();
      } catch (f) {
        inhalt.replaceChildren(el("div", { class: "witz", text: f.message }));
        hilfe.textContent = "STOP zurück";
      }
    }

    function zeigeListe() {
      z.lied = null;
      punkte.textContent = `${z.lieder.length} Lieder`;
      hilfe.textContent = "↑ ↓ wählen · OK singen · STOP zurück";
      if (!z.lieder.length) { inhalt.replaceChildren(el("div", { class: "witz", text: "In der Klassenkiste gibt es noch keine Lieder mit Text." })); return; }
      const oben = Math.max(0, Math.min(z.wahl - 3, z.lieder.length - 8));
      inhalt.replaceChildren(el("div", { class: "ka-liste" }, ...z.lieder.slice(oben, oben + 8).map((l, i) => el("div", {
        class: "ka-eintrag" + (oben + i === z.wahl ? " gewaehlt" : "") },
        el("b", { text: l.titel }), el("span", { text: [l.liste, l.musik ? "🎵" : "nur Text"].filter(Boolean).join(" · ") })))));
    }

    async function mikroStarten() {
      if (z.mikro) return;
      try {
        const strom = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: false, autoGainControl: false } });
        const a = ctx(), quelle = a.createMediaStreamSource(strom), analyse = a.createAnalyser();
        analyse.fftSize = 4096;
        quelle.connect(analyse);
        z.mikro = { strom, quelle, analyse, puffer: new Float32Array(analyse.fftSize) };
      } catch (_) { z.mikro = false; }               /* ohne Mikro: einfach mitsingen, ohne Sterne */
    }

    function singen(i) {
      stoppeLied();
      z.wahl = i;
      const l = z.lieder[i];
      z.lied = l; z.versatz = 0; z.gesungen = 0; z.gehoert = 0;
      const zeilen = liedZeilen(l.text);
      const marken = Array.isArray(l.marken) && l.marken.length === zeilen.filter((x) => x.art === "zeile").length ? l.marken : null;
      const text = el("div", { class: "ka-text" + (marken ? " mit-marken" : "") }, ...zeilen.map((x) =>
        el("p", { class: (x.art === "ueberschrift" ? "ka-ueberschrift" : "") + (x.neueStrophe ? " ka-strophe" : ""),
                  "data-nr": x.nr, text: x.text })));
      const absatz = [...text.querySelectorAll("p")].filter((p) => p.dataset.nr !== "-1");
      let dranVorher = -2;
      const fenster = el("div", { class: "ka-fenster" }, text);
      const balken = el("div", { class: "hb-balken" }, el("span"));
      const sterne = el("div", { class: "ka-sterne" });
      inhalt.replaceChildren(el("div", { class: "ka-buehne" }, el("h3", { text: l.titel }), fenster, balken, sterne));
      punkte.textContent = l.liste || "";
      hilfe.textContent = "OK Pause · ◀◀ ▶▶ 10 s · ↑ ↓ Text schieben · ← → anderes Lied · STOP Liste";
      if (l.musik) {
        z.audio = el("audio", { src: "/api/karaoke/musik?id=" + encodeURIComponent(l.id), autoplay: true });
        z.audio.addEventListener("ended", ende);
        z.audio.addEventListener("error", () => api.hinweis("Die Musik lässt sich gerade nicht laden – der Text läuft trotzdem.", 5000));
        box.append(z.audio);
      }
      mikroStarten();
      const start = performance.now();
      let zuletzt = start, eigeneZeit = 0;
      const schritt = (jetzt) => {
        if (!z.lied) return;
        const dt = Math.min(0.1, (jetzt - zuletzt) / 1000);
        zuletzt = jetzt;
        const a = z.audio, dauer = (a && isFinite(a.duration) && a.duration) || l.dauer || Math.max(60, l.text.length / 12);
        const laeuft = a ? !a.paused : true;
        if (laeuft && !a) eigeneZeit += dt;
        const zeit = a ? a.currentTime : eigeneZeit;
        if (marken) {
          const dran = zeileZurZeit(marken, zeit);
          if (dran !== dranVorher) {
            absatz.forEach((p, i) => { p.classList.toggle("dran", i === dran); p.classList.toggle("vorbei", i < dran); });
            dranVorher = dran;
          }
          const ziel = absatz[Math.max(0, dran)];
          const soll = ziel ? ziel.offsetTop - fenster.clientHeight / 2 + ziel.offsetHeight / 2 + z.versatz : 0;
          fenster.scrollTop += (Math.max(0, soll) - fenster.scrollTop) * Math.min(1, dt * 6);   /* weich nachziehen */
        } else {
          const strecke = Math.max(0, text.scrollHeight - fenster.clientHeight * 0.5);
          fenster.scrollTop = Math.max(0, zeit / dauer * strecke + z.versatz);
        }
        balken.firstChild.style.width = `${Math.min(100, zeit / dauer * 100)}%`;
        if (laeuft && z.mikro) {
          z.mikro.analyse.getFloatTimeDomainData(z.mikro.puffer);
          z.gehoert += dt;
          if (tonhoehe(z.mikro.puffer, ctx().sampleRate)) z.gesungen += dt;
          sterne.textContent = "🎤 " + "⭐".repeat(sternZahl());
        }
        if (!a && eigeneZeit >= dauer) return ende();
        z.takt = requestAnimationFrame(schritt);
      };
      z.takt = requestAnimationFrame(schritt);
      ton("ok");
    }

    const sternZahl = () => (z.gehoert > 5 ? Math.max(0, Math.min(5, Math.round(z.gesungen / z.gehoert * 7))) : 0);

    function ende() {
      if (!z.lied) return;
      const n = sternZahl();
      cancelAnimationFrame(z.takt);
      if (z.mikro && n) {
        api.hinweis(`Toll gesungen: ${"⭐".repeat(n)}`, 5000);
        if (n >= 4) { konfetti(document.body); ton("sieg"); }
        api.sende("/api/erfolg", { art: "gehoer", wert: 1 }).catch(() => {});
      }
      setTimeout(() => { if (z.lied) { stoppeLied(); zeigeListe(); } }, 2500);
    }

    function stoppeLied() {
      cancelAnimationFrame(z.takt);
      if (z.audio) { z.audio.pause(); z.audio.removeAttribute("src"); z.audio.remove(); z.audio = null; }
      z.lied = null;
    }

    lade();
    return {
      taste(t) {
        if (z.lied) {
          const a = z.audio;
          if (t === "Escape" || t === "Backspace") { stoppeLied(); zeigeListe(); return true; }
          if (["Enter", " ", "MediaPlayPause", "MediaPlay", "MediaPause", "p", "P"].includes(t) && a) { if (a.paused) a.play().catch(() => {}); else a.pause(); return true; }
          if (t === "MediaFastForward" && a) { a.currentTime = Math.min((a.duration || 0) - 1, a.currentTime + SPRUNG_S); return true; }
          if (t === "MediaRewind" && a) { a.currentTime = Math.max(0, a.currentTime - SPRUNG_S); return true; }
          if (t === "ArrowUp") { z.versatz -= 60; return true; }
          if (t === "ArrowDown") { z.versatz += 60; return true; }
          if (t === "ArrowRight" || t === "MediaTrackNext") { singen((z.wahl + 1) % z.lieder.length); return true; }
          if (t === "ArrowLeft" || t === "MediaTrackPrevious") { singen((z.wahl + z.lieder.length - 1) % z.lieder.length); return true; }
          return true;
        }
        if (!z.lieder.length) return t !== "Escape" && t !== "Backspace";
        if (t === "ArrowDown") { z.wahl = (z.wahl + 1) % z.lieder.length; zeigeListe(); ton("bewegen"); return true; }
        if (t === "ArrowUp") { z.wahl = (z.wahl + z.lieder.length - 1) % z.lieder.length; zeigeListe(); ton("bewegen"); return true; }
        if (t === "Enter" || t === " " || t === "MediaPlay") { singen(z.wahl); return true; }
        return t !== "Escape" && t !== "Backspace";
      },
      anhalten() { z.audio?.pause(); },
      fortsetzen() { z.audio?.play().catch(() => {}); },
      schliesse() {
        stoppeLied();
        if (z.mikro) { z.mikro.quelle.disconnect(); z.mikro.strom.getTracks().forEach((s) => s.stop()); }
      },
    };
  },
};
