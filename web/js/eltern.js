/* FernsehFranzi 3.0 - Elternbereich.
 *
 * Eine Oberfläche, zwei Eingänge:
 *   - am Fernseher (BLAU / Back+Start lang): PIN über Ziffern oder Bildschirm-Tastenfeld,
 *     danach große Knöpfe für das Wichtigste (bedienbar mit Fernbedienung und Controller)
 *   - im Heimnetz (eltern.html, Handy/PC): alle Einstellungen - seit 3.3 in eltern-handy.js
 * Die PIN prüft immer der Server (Hash + wachsende Sperre).
 */
import { hole, sende, el, setzeElternToken } from "./gemeinsam.js";

/* ============================================================ PIN-Eingabe */
function pinEingabe(box, titel, fertig, abbrechen) {
  box.replaceChildren();
  let pin = "";
  const felder = el("div", { class: "pinfeld" });
  const fehler = el("div", { class: "meldung-fehler" });
  const tasten = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "OK"];
  const raster = el("div", { style: "display:grid;grid-template-columns:repeat(3,110px);gap:12px;justify-content:center" });
  const knoepfe = tasten.map((t) => {
    const k = el("button", { class: "knopf", type: "button", tabindex: "-1", text: t });
    k.addEventListener("click", () => druecke(t));
    raster.append(k);
    return k;
  });
  box.append(el("h2", { text: titel, style: "text-align:center" }), felder, fehler, raster,
    el("p", { class: "leise", style: "text-align:center", text: "Ziffern direkt eingeben oder mit den Pfeilen wählen · STOP Abbrechen" }));
  let pos = 0;
  function zeige() {
    felder.replaceChildren(...Array.from({ length: Math.max(6, pin.length) }, (_, i) => el("span", { text: i < pin.length ? "●" : "" })));
    knoepfe.forEach((k, i) => k.classList.toggle("gewaehlt", i === pos));
  }
  function druecke(t) {
    fehler.textContent = "";
    if (t === "⌫") pin = pin.slice(0, -1);
    else if (t === "OK") { if (pin.length >= 4) fertig(pin, (text) => { fehler.textContent = text; pin = ""; zeige(); }); }
    else if (pin.length < 8) pin += t;
    zeige();
  }
  zeige();
  return {
    taste(t) {
      /* Ziffern direkt (Fernbedienung/Tastatur): danach steht die Markierung auf OK,
         damit die OK-Taste der Fernbedienung absendet */
      if (/^[0-9]$/.test(t)) { druecke(t); if (pin.length >= 4) { pos = 11; zeige(); } return true; }
      if (t === "Enter" || t === " ") { druecke(tasten[pos]); return true; }
      if (t === "Backspace") { druecke("⌫"); return true; }
      const b = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -3, ArrowDown: 3 }[t];
      if (b !== undefined) { const z = pos + b; if (z >= 0 && z < 12) pos = z; zeige(); return true; }
      if (t === "Escape") { abbrechen(); return true; }
      return true;
    },
  };
}

/* ============================================================ Fernseher */
export function oeffneElternbereich(box, api) {
  let aktiv = null;   // {taste}
  const schliessen = () => { sende("/api/eltern/abmelden").catch(() => {}); setzeElternToken(""); api.schliessen(); };

  async function beginne() {
    let status;
    try { status = await hole("/api/status"); } catch (_) { api.hinweis("Server nicht erreichbar"); return api.schliessen(); }
    if (!status.pin_gesetzt) return ersteFestlegen();
    aktiv = pinEingabe(box, "Elternbereich – PIN", async (pin, fehler) => {
      try {
        const antwort = await sende("/api/eltern/anmelden", { pin });
        setzeElternToken(antwort.token);
        uebersicht();
      } catch (e) { fehler(e.message); }
    }, api.schliessen);
  }

  function ersteFestlegen() {
    aktiv = pinEingabe(box, "Neue Eltern-PIN festlegen (6 Ziffern empfohlen)", (pin1) => {
      aktiv = pinEingabe(box, "PIN zur Sicherheit wiederholen", async (pin2, fehler) => {
        if (pin1 !== pin2) { fehler("Die PINs sind verschieden. Bitte nochmal."); return ersteFestlegen(); }
        try {
          await sende("/api/eltern/pin", { neu: pin1 });
          api.hinweis("PIN gespeichert. Bitte gut merken!");
          beginne();
        } catch (e) { fehler(e.message); }
      }, api.schliessen);
    }, api.schliessen);
  }

  async function uebersicht() {
    let d;
    try { d = await hole("/api/eltern/daten"); } catch (e) { api.hinweis(e.message); return beginne(); }
    const h = d.heute;
    box.replaceChildren();
    box.append(el("div", { class: "overlay-kopf" }, el("h2", { text: "Elternbereich" }),
      el("div", { class: "hilfe", text: "Pfeile Wählen · OK Ausführen · STOP Schließen · Alles weitere: Eltern-Seite im Heimnetz" })));
    const info = el("div", { class: "eltern-raster", style: "margin:0 auto 3vh" },
      el("div", { class: "karte-eltern" }, el("h3", { text: "Heute" }),
        el("div", { class: "gross-zahl", text: h.ohne_limit ? "ohne Limit" : `${h.rest_min ?? "–"} min übrig` }),
        el("div", { class: "leise", text: `gespielt ${h.genutzt_min} min · davon RetroPie ${h.retropie_min} min · ${h.tagesart === "frei" ? "freier Tag" : "Schultag"}` })),
      el("div", { class: "karte-eltern" }, el("h3", { text: "Eltern-Seite am Handy" }),
        el("div", { class: "gross-zahl", style: "font-size:24px",
          text: d.einstellungen.eltern_lan?.aktiv ? (d.adressen || []).join("  oder  ") || `Port ${d.einstellungen.eltern_lan.port}` : "aus" }),
        el("div", { class: "leise", text: d.einstellungen.eltern_lan?.aktiv ? "Im Handy-Browser öffnen (gleiches WLAN), mit derselben PIN anmelden."
                                                                           : "Unten bei „Einstellungen“ einschalten." })));
    box.append(info);
    const lanAn = Boolean(d.einstellungen.eltern_lan?.aktiv);
    /* 3.2: in beschrifteten Reihen - ← → innerhalb einer Reihe, ↑ ↓ zwischen den Reihen */
    const gruppen = [
      ["Zeit", [["+15 Minuten", () => bonus("15")], ["+30 Minuten", () => bonus("30")], ["Heute ohne Limit", () => bonus("ohne_limit")],
                [d.gesperrt ? (d.gesperrt.auszeit ? "Auszeit beenden" : "Fernseher freigeben") : "Fernseher jetzt sperren", () => sperre(!d.gesperrt)]]],
      /* 5.1: Auszeit mit Countdown (bei laufender Auszeit: verlängern) */
      ...(d.gesperrt && !d.gesperrt.auszeit ? [] : [[d.gesperrt ? "Auszeit verlängern" : "Auszeit",
        [5, 10, 15, 30].map((m) => [`${d.gesperrt ? "+" : ""}${m} Minuten`, () => auszeit(m)])]]),
      ["Fernseher", [["Ton: Fernseher", () => sende("/api/audio", { ziel: "hdmi" }).then(() => api.hinweis("Ton: Fernseher"))],
                     ["Ton: Klinke", () => sende("/api/audio", { ziel: "klinke" }).then(() => api.hinweis("Ton: Klinke"))],
                     ...(d.kopfhoerer ? [["Ton: Kopfhörer", () => sende("/api/audio", { ziel: "kopfhoerer" }).then(() => api.hinweis("Ton: Kopfhörer"))]] : []),
                     ["Leiser", () => sende("/api/eltern/lautstaerke", { richtung: "leiser" })],
                     ["Lauter", () => sende("/api/eltern/lautstaerke", { richtung: "lauter" })],
                     ["Gute Nacht starten", () => sende("/api/eltern/gute-nacht").then(() => { api.schliessen(); }).catch((e) => api.hinweis(e.message))],
                     ["Fernseher aus", () => sende("/api/eltern/fernseher-aus").then(() => api.hinweis("Fernseher geht aus."))]]],
      ["Einstellungen", [[lanAn ? "Eltern-Seite ausschalten" : "Eltern-Seite einschalten", () => lan(!lanAn, d)],
                         ["PIN ändern", pinAendern],
                         ["Linux-Desktop", () => sende("/api/eltern/desktop").then(() => api.hinweis("Desktop öffnet – zurück über das Symbol oder nach 20 min."))]]],
      ["Gerät", [["Neustart", () => geraet("neustart")], ["Ausschalten", () => geraet("aus")], ["Schließen", schliessen]]],
    ];
    const reihen = gruppen.map(([titel, aktionen]) => {
      const reihe = el("div", { class: "knopfreihe", style: "justify-content:flex-start" });
      const knoepfe = aktionen.map(([text, tun]) => {
        const k = el("button", { class: "knopf" + (/Ausschalten|Neustart|sperren|aus$/.test(text) ? " gefahr" : ""), type: "button", tabindex: "-1", text });
        k.addEventListener("click", tun);
        reihe.append(k);
        return k;
      });
      box.append(el("div", { style: "max-width:1300px;margin:0 auto 1.6vh;width:100%" },
        el("div", { class: "leise", style: "margin:0 0 6px 4px;font-weight:700;letter-spacing:.08em;text-transform:uppercase", text: titel }), reihe));
      return { aktionen, knoepfe };
    });
    let z = 0, sp = 0;
    const zeige = () => reihen.forEach((r, ri) => r.knoepfe.forEach((k, ki) => k.classList.toggle("gewaehlt", ri === z && ki === sp)));
    zeige();
    aktiv = {
      taste(t) {
        const n = reihen[z].knoepfe.length;
        if (t === "ArrowLeft") { sp = (sp + n - 1) % n; zeige(); return true; }
        if (t === "ArrowRight") { sp = (sp + 1) % n; zeige(); return true; }
        if (t === "ArrowUp" || t === "ArrowDown") {
          z = (z + (t === "ArrowUp" ? reihen.length - 1 : 1)) % reihen.length;
          sp = Math.min(sp, reihen[z].knoepfe.length - 1); zeige(); return true;
        }
        if (t === "Enter" || t === " ") { reihen[z].aktionen[sp][1](); return true; }
        if (t === "Escape" || t === "Backspace") { schliessen(); return true; }
        return true;
      },
    };
  }

  async function bonus(art) {
    try { await sende("/api/eltern/bonus", { art }); api.hinweis("Mehr Zeit geschenkt."); uebersicht(); } catch (e) { api.hinweis(e.message); }
  }
  async function sperre(an) {
    try {
      await sende("/api/eltern/sperre", an ? { text: "Der Fernseher macht jetzt Pause." } : { frei: true });
      api.hinweis(an ? "Gesperrt." : "Freigegeben.");
      uebersicht();
    } catch (e) { api.hinweis(e.message); }
  }
  async function auszeit(minuten) {
    try {
      const a = await sende("/api/eltern/auszeit", { minuten });
      api.hinweis(`Auszeit bis ${a.bis} Uhr.`);
      uebersicht();
    } catch (e) { api.hinweis(e.message); }
  }
  async function lan(an, d) {
    const wert = { ...(d.einstellungen.eltern_lan || { port: 8766 }), aktiv: an };
    try { await sende("/api/eltern/einstellungen", { einstellungen: { eltern_lan: wert } }); api.hinweis(an ? `Eltern-Seite an (Port ${wert.port}).` : "Eltern-Seite aus."); uebersicht(); }
    catch (e) { api.hinweis(e.message); }
  }
  function geraet(aktion) {
    const reihe = el("div", { style: "text-align:center" }, el("p", { class: "punkte", text: aktion === "aus" ? "Wirklich ausschalten?" : "Wirklich neu starten?" }));
    box.replaceChildren(reihe);
    const nein = el("button", { class: "knopf gewaehlt", type: "button", text: "Nein" });
    const ja = el("button", { class: "knopf gefahr", type: "button", text: "Ja" });
    reihe.append(el("div", { class: "knopfreihe" }, nein, ja));
    let jaGewaehlt = false;
    aktiv = { taste(t) {
      if (t.startsWith("Arrow")) { jaGewaehlt = !jaGewaehlt; nein.classList.toggle("gewaehlt", !jaGewaehlt); ja.classList.toggle("gewaehlt", jaGewaehlt); return true; }
      if (t === "Enter" || t === " ") { if (jaGewaehlt) sende("/api/eltern/geraet", { aktion }).catch((e) => api.hinweis(e.message)); else uebersicht(); return true; }
      if (t === "Escape" || t === "Backspace") { uebersicht(); return true; }
      return true;
    } };
  }
  function pinAendern() {
    aktiv = pinEingabe(box, "Alte PIN", (alt) => {
      aktiv = pinEingabe(box, "Neue PIN", async (neu, fehler) => {
        try { await sende("/api/eltern/pin", { alt, neu }); api.hinweis("Neue PIN gespeichert."); beginne(); }
        catch (e) { fehler(e.message); }
      }, uebersicht);
    }, uebersicht);
  }

  beginne();
  return { taste: (t) => (aktiv ? aktiv.taste(t) : true), schliesse() { setzeElternToken(""); } };
}
