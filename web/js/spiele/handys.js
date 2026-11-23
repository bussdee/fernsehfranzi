/* FernsehFranzi 4.3 - Mit Handys spielen: der Fernseher als Spieltafel.
 *
 * Lobby: großer QR-Code (Handys scannen ihn), Liste der Mitspieler, Auswahl der fünf Spiele.
 * Das Kind spielt mit der Fernbedienung als eigener Spieler mit (Pfeile wählen, OK drückt).
 * STOP: im Spiel zurück zur Auswahl, in der Auswahl den Raum schließen.
 * Der Spielstand liegt auf dem Server (raum.py); diese Seite fragt ihn alle 0,4 s ab und zeichnet.
 * Ton-Treffer: Der Fernseher spielt die Tonfolge und hört über das USB-Mikro zu (Tonerkennung aus der Bass-Ecke). */
import { el } from "../gemeinsam.js";
import { kopf, ton, konfetti } from "./kern.js";
import { ctx, tonhoehe } from "./bass.js";

const hz = (midi) => 440 * Math.pow(2, (midi - 69) / 12);
const SPIEL_SYMBOL = { buzzer: "🔔", quiz: "🏁", malen: "🎨", raumschiff: "🚀", ton: "🎤", rakete: "📣", klatsch: "👏" };
/* replaceChildren(null) schreibt „null“ hin - leere Teile weglassen */
const setze = (knoten, ...kinder) => knoten.replaceChildren(...kinder.filter((k) => k !== null && k !== undefined && k !== false));
const FARBE_CSS = { rot: "#e4574b", blau: "#3f8de0", gelb: "#f2c230", "grün": "#3bb36b" };

export default {
  symbol: "📱",
  oeffne(box, api) {
    box.classList.add("handys");
    const { inhalt, punkte, hilfe } = kopf(box, "📱 Mit Handys spielen", "");
    let z = null, wahl = 0, unter = null, tvWahl = 0, strichAb = 0, malRunde = null, abfrage = null, offen = true;
    let tonSchluessel = "", mikro = null, singt = false, letzteZeichnung = "", holt = false, nochmal = false;
    const ansicht = el("div", { class: "hs-ansicht" });
    inhalt.append(ansicht);

    /* ------------------------------------------------ Server */
    async function holen() {                                   /* immer nur eine Abfrage zugleich */
      if (!offen) return;
      if (holt) { nochmal = true; return; }
      holt = true;
      clearTimeout(abfrage);
      try {
        const malen = z?.spiel === "malen";
        const neu = await api.hole("/api/raum/tv" + (malen ? `?striche_ab=${strichAb}` : ""));
        if (offen) verarbeite(neu);
      } catch (f) {
        if (f.status === 400) { holt = false; api.hinweis(f.message, 5000); return api.schliessen(); }
      }
      holt = false;
      if (!offen) return;
      abfrage = setTimeout(holen, nochmal ? 0 : 400);
      nochmal = false;
    }
    const tvAktion = (daten) => api.sende("/api/raum/tv-aktion", daten).then(() => holen()).catch((f) => { api.hinweis(f.message, 4000); ton("fehler"); });
    const spielerAktion = (daten) => tvAktion({ art: "spieler", daten });

    api.sende("/api/raum/oeffnen", {}).then((d) => { verarbeite(d); abfrage = setTimeout(holen, 400); })
      .catch((f) => { setze(ansicht, el("div", { class: "witz", text: f.message })); });

    function verarbeite(neu) {
      const vorher = z;
      z = neu;
      if (z.spiel !== "malen" || (vorher && vorher.tv?.runde !== z.tv?.runde)) { strichAb = 0; }
      if (z.ergebnis && !(vorher && vorher.ergebnis)) { ton("sieg"); konfetti(document.body); }
      zeichne();
    }

    /* ------------------------------------------------ Zeichnen */
    function spielerLeiste() {
      return el("div", { class: "hs-spielerleiste" }, ...z.spieler.map((s) => el("span", { class: "hs-spieler" + (s.da ? "" : " weg"), style: `border-color:${s.farbe}` },
        `${s.symbol} ${s.name}`, el("b", { text: ` ${s.punkte}` }))));
    }

    function zeichne() {
      if (!z) return;
      punkte.textContent = z.spiel ? (z.titel || "") : `Raum ${z.code}`;
      if (!z.spiel && z.ergebnis) return zeichneErgebnis();
      if (!z.spiel) return zeichneLobby();
      ({ buzzer: zeichneBuzzer, quiz: zeichneQuiz, malen: zeichneMalen, raumschiff: zeichneRaumschiff, ton: zeichneTon,
         rakete: zeichneRakete, klatsch: zeichneKlatsch })[z.spiel]();
    }

    function zeichneLobby() {
      hilfe.textContent = unter ? "← → wählen · OK starten · STOP zurück" : "Handys scannen den QR-Code · Pfeile wählen · OK starten · STOP schließen";
      const qr = el("div", { class: "hs-qr" });
      qr.innerHTML = z.qr;                                       /* SVG vom eigenen Server (raum.py/qr.py), keine fremden Daten */
      const spiele = unter ? unter.eintraege : z.spiele.map((s) => ({ text: `${SPIEL_SYMBOL[s.id]} ${s.name}`, geht: s.geht, id: s.id }));
      wahl = Math.min(wahl, spiele.length - 1);
      const handys = z.spieler.filter((s) => s.id !== "tv").length;
      setze(ansicht, el("div", { class: "hs-lobby" },
        el("div", { class: "hs-qr-box" }, qr, el("div", { class: "hs-adresse" }, "Oder im Handy-Browser: ", el("b", { text: z.adresse }),
          el("br"), "Code: ", el("b", { class: "hs-code", text: z.code }))),
        el("div", { class: "hs-rechts" },
          el("h3", { text: handys ? `${handys} ${handys === 1 ? "Handy ist" : "Handys sind"} dabei` : "Noch kein Handy dabei – scannt den Code!" }),
          el("div", { class: "hs-liste" }, ...z.spieler.map((s) => el("div", { class: "hs-zeile", style: `border-left-color:${s.farbe}` },
            `${s.symbol} ${s.name}`, s.id === "tv" ? el("small", { text: " (Fernbedienung)" }) : null))),
          el("h3", { text: unter ? unter.titel : "Was spielen wir?" }),
          el("div", { class: "hs-menue" }, ...spiele.map((s, i) => el("div", { class: "hs-eintrag" + (i === wahl ? " gewaehlt" : "") + (s.geht === false ? " geht-nicht" : ""), text: s.text }))))));
    }

    function zeichneErgebnis() {
      hilfe.textContent = "OK oder STOP: zurück zur Auswahl";
      const e = z.ergebnis;
      setze(ansicht, el("div", { class: "hs-ergebnis" },
        el("h2", { text: `🏆 ${e.spiel}` }), e.text ? el("p", { class: "witz", text: e.text }) : null,
        el("ol", { class: "hs-rangliste" }, ...e.rangliste.map((r, i) => el("li", {}, `${["🥇", "🥈", "🥉"][i] || ""} ${r.symbol} ${r.name}`, el("b", { text: ` ${r.punkte} ⭐` }))))));
    }

    function tvSpielerPanel() {
      const t = z.tv_spieler || {};
      if (t.ansicht === "buzzer") return el("div", { class: "hs-tv-panel" }, el("span", { class: "hs-tv-name", text: "📺 Du:" }), el("span", { class: "hs-knopf gewaehlt", text: "OK = BUZZ!" }));
      if (t.ansicht === "wahl") {
        tvWahl = Math.min(tvWahl, t.optionen.length - 1);
        return el("div", { class: "hs-tv-panel" }, el("span", { class: "hs-tv-name", text: "📺 Du:" }),
          ...t.optionen.map((o, i) => el("span", { class: "hs-knopf" + (i === tvWahl ? " gewaehlt" : ""), text: o })));
      }
      if (t.ansicht === "knoepfe" && t.knoepfe.length) {
        tvWahl = Math.min(tvWahl, t.knoepfe.length - 1);
        return el("div", { class: "hs-tv-panel" }, el("span", { class: "hs-tv-name", text: "📺 Deine Schalter:" }),
          ...t.knoepfe.map((k, i) => el("span", { class: "hs-knopf" + (i === tvWahl ? " gewaehlt" : "") + (t.aktiv ? "" : " aus"), text: k.text })));
      }
      if (t.ansicht === "daumen") return el("div", { class: "hs-tv-panel" }, el("span", { class: "hs-tv-name", text: "📺 Du:" }),
        el("span", { class: "hs-knopf" + (t.gegeben ? "" : " gewaehlt"), text: t.gegeben ? "👍 gegeben" : "OK = 👍" }));
      return t.titel ? el("div", { class: "hs-tv-panel leise" }, el("span", { text: t.titel })) : null;
    }

    function optionenGitter(optionen, richtig) {
      return el("div", { class: "hs-optionen" }, ...optionen.map((o, i) => el("div", {
        class: `hs-option o${i}` + (richtig ? (o === richtig ? " richtig" : " falsch") : ""), text: o })));
    }

    function zeichneBuzzer() {
      const t = z.tv;
      hilfe.textContent = "OK = Buzzer (du am Fernseher) · STOP: zur Auswahl";
      const status = t.phase === "frage" ? `🔔 Buzzer frei! · ⏳ ${t.rest} s` : t.phase === "antwort" ? `${t.buzzer} antwortet … ⏳ ${t.rest} s` : (t.ergebnis?.text || "");
      setze(ansicht, spielerLeiste(), el("div", { class: "hs-frage-nr", text: `Frage ${t.nr} von ${t.von}` }),
        el("div", { class: "hs-frage", text: t.frage }), el("div", { class: "hs-status", text: status }),
        t.optionen.length ? optionenGitter(t.optionen, t.richtig) : el("div", { class: "hs-buzzer-bild", text: "🔴" }),
        t.gesperrt.length && t.phase !== "aufloesung" ? el("div", { class: "leise", text: `Diesmal nicht mehr: ${t.gesperrt.join(", ")}` }) : null,
        tvSpielerPanel());
    }

    function zeichneQuiz() {
      const t = z.tv;
      hilfe.textContent = "← → wählen · OK antworten (du am Fernseher) · STOP: zur Auswahl";
      setze(ansicht, 
        el("div", { class: "hs-bahn" }, ...t.bahn.map((s) => el("div", { class: "hs-spur" },
          el("span", { class: "hs-spur-name", text: `${s.name}` }),
          el("div", { class: "hs-spur-strecke" }, el("span", { class: "hs-figur", style: `left:${s.feld / t.ziel * 92}%`, text: s.symbol }), el("span", { class: "hs-ziel", text: "🏁" }))))),
        el("div", { class: "hs-frage-nr", text: `Frage ${t.nr}` + (t.phase === "frage" ? ` · ⏳ ${t.rest} s · geantwortet: ${t.geantwortet.length}` : "") }),
        el("div", { class: "hs-frage", text: t.frage }), optionenGitter(t.optionen, t.richtig), tvSpielerPanel());
    }

    function zeichneMalen() {
      const t = z.tv;
      hilfe.textContent = "← → wählen · OK raten (du am Fernseher) · STOP: zur Auswahl";
      const neueRunde = malRunde !== t.runde;
      if (neueRunde || !ansicht.querySelector(".hs-leinwand")) {
        malRunde = t.runde;
        strichAb = 0;
        const leinwand = el("canvas", { class: "hs-leinwand", width: 960, height: 720 });
        setze(ansicht, spielerLeiste(), el("div", { class: "hs-malen" }, leinwand, el("div", { class: "hs-malen-rechts" })));
        letzteZeichnung = "";
      }
      const g = ansicht.querySelector(".hs-leinwand").getContext("2d");
      if (strichAb === 0) { g.fillStyle = "#fff"; g.fillRect(0, 0, 960, 720); }
      for (const s of z.striche || []) {
        if (s.leer) { g.fillStyle = "#fff"; g.fillRect(0, 0, 960, 720); continue; }
        g.strokeStyle = s.f; g.lineWidth = s.d * 960 / 500; g.lineCap = "round"; g.lineJoin = "round";
        g.beginPath();
        for (let i = 0; i < s.p.length; i += 2) { const x = s.p[i] / 1000 * 960, y = s.p[i + 1] / 1000 * 720; if (i === 0) g.moveTo(x, y); else g.lineTo(x, y); }
        g.stroke();
      }
      strichAb += (z.striche || []).length;
      const rechts = el("div", {}, el("h3", { text: `🎨 ${t.maler} malt` }), el("div", { class: "hs-status", text: t.phase === "malen" ? `Runde ${t.runde} von ${t.von} · ⏳ ${t.rest} s` : `Es war: ${t.wort}` }),
        t.geraten.length ? el("div", { class: "leise", text: `Richtig: ${t.geraten.join(", ")}` }) : null, tvSpielerPanel());
      const schluessel = JSON.stringify([t.phase, t.rest, t.geraten, z.tv_spieler, tvWahl]);
      if (schluessel !== letzteZeichnung) { letzteZeichnung = schluessel; ansicht.querySelector(".hs-malen-rechts").replaceChildren(rechts); }
    }

    function zeichneRaumschiff() {
      const t = z.tv;
      hilfe.textContent = "Sprecht euch ab! · ← → Schalter wählen · OK drücken (du am Fernseher) · STOP: zur Auswahl";
      setze(ansicht, spielerLeiste(), el("div", { class: "hs-raumschiff" },
        el("div", { class: "hs-cockpit" + (t.phase === "stoerung" ? " alarm" : "") },
          el("div", { class: "hs-lampe", style: `--lampe:${FARBE_CSS[t.farbe] || "#888"}` }, el("span", { text: t.zeichen_symbol || "⚠️" })),
          el("div", { class: "hs-alarm-text", text: t.phase === "stoerung" ? `STÖRUNG: ${t.farbe.toUpperCase()}${t.zeichen ? " + " + t.zeichen.toUpperCase() : ""}` : t.meldung }),
          el("div", { class: "hs-zeitbalken" }, el("span", { style: `width:${t.phase === "stoerung" ? Math.max(0, t.rest) / (t.stufe === 1 ? 30 : 40) * 100 : 0}%` }))),
        el("div", { class: "hs-stand" }, el("div", { text: "❤️".repeat(Math.max(0, t.leben)) + "🖤".repeat(Math.max(0, 3 - t.leben)) }),
          el("div", { text: `🔧 ${t.gerettet} von ${t.ziel} repariert` }),
          el("div", { class: "leise", text: "Wer das Handbuch hat, liest vor – wer den Schalter hat, drückt!" }))),
      tvSpielerPanel());
    }

    function zeichneTon() {
      const t = z.tv;
      hilfe.textContent = "Hör zu und sing nach – ins Mikro am Fernseher · STOP: zur Auswahl";
      const schluessel = `${t.runde}|${t.saenger}|${t.folge.map((n) => n.midi).join(",")}`;
      if (!ansicht.querySelector(".hs-ton") || ansicht.dataset.ton !== schluessel) {
        ansicht.dataset.ton = schluessel;
        setze(ansicht, spielerLeiste(), el("div", { class: "hs-ton" },
          el("h3", { class: "hs-saenger" }), el("div", { class: "hs-leiter" }, ...t.folge.map((n, i) => el("div", { class: "hs-note", "data-i": i, style: `--hoehe:${n.stufe}` },
            el("span", { text: n.silbe })))), el("div", { class: "hs-status hs-ton-status" }), el("div", { class: "hs-pegel" }, el("span"))), el("div", { class: "hs-tv-box" }));
      }
      ansicht.querySelector(".hs-saenger").textContent = `🎤 ${t.saenger} · Runde ${t.runde} von ${t.runden}`;
      ansicht.querySelector(".hs-spielerleiste")?.replaceWith(spielerLeiste());   /* Punkte aktuell halten */
      const status = ansicht.querySelector(".hs-ton-status");
      if (t.phase === "vorspielen") status.textContent = "👂 Gut zuhören …";
      if (t.phase === "daumen") {
        const n = (t.treffer || []).filter(Boolean).length;
        status.textContent = `${n} von ${t.folge.length} Tönen getroffen${t.daumen ? ` · ${t.daumen}× 👍` : ""}`;
        (t.treffer || []).forEach((ok, i) => ansicht.querySelector(`.hs-note[data-i="${i}"]`)?.classList.add(ok ? "treffer" : "daneben"));
      }
      ansicht.querySelector(".hs-tv-box").replaceChildren(tvSpielerPanel() || "");
      if (t.phase === "vorspielen" && tonSchluessel !== schluessel + "v") { tonSchluessel = schluessel + "v"; vorspielen(t); }
      if (t.phase === "singen" && tonSchluessel !== schluessel + "s" && !singt) { tonSchluessel = schluessel + "s"; singen(t, status); }
    }

    /* ------------------------------------------------ 4.4: Lautstärke-Rakete */
    let raketeSchluessel = "";
    function zeichneRakete() {
      const t = z.tv;
      hilfe.textContent = "So laut und so lange wie möglich ins Mikro am Fernseher! · STOP: zur Auswahl";
      const schluessel = `${t.runde}|${t.dran}`;
      if (!ansicht.querySelector(".hs-rakete") || ansicht.dataset.rakete !== schluessel) {
        ansicht.dataset.rakete = schluessel;
        setze(ansicht, spielerLeiste(), el("div", { class: "hs-rakete" },
          el("h3", { class: "hs-saenger" }), el("div", { class: "hs-himmel" }, el("div", { class: "hs-rekord" }), el("span", { class: "hs-rakete-bild", text: "🚀" })),
          el("div", { class: "hs-status hs-rakete-status" })), el("div", { class: "hs-tv-box" }));
      }
      ansicht.querySelector(".hs-saenger").textContent = `📣 ${t.dran} · Runde ${t.runde} von ${t.runden}`;
      ansicht.querySelector(".hs-spielerleiste")?.replaceWith(spielerLeiste());   /* Punkte aktuell halten */
      ansicht.querySelector(".hs-rekord").style.bottom = `${Math.min(92, t.rekord / 1000 * 92)}%`;
      ansicht.querySelector(".hs-rekord").textContent = t.rekord ? `Rekord ${t.rekord} m` : "";
      const status = ansicht.querySelector(".hs-rakete-status");
      if (t.phase === "countdown") status.textContent = `Gleich geht's los … ${t.rest}`;
      if (t.phase === "daumen") {
        status.textContent = `${t.ergebnis.text}${t.ergebnis.rekord ? " 🏆 Neuer Rekord!" : ""}${t.daumen ? ` · ${t.daumen}× 👍` : ""}`;
        ansicht.querySelector(".hs-rakete-bild").style.bottom = `${t.ergebnis.hoehe / 1000 * 88}%`;
      }
      ansicht.querySelector(".hs-tv-box").replaceChildren(tvSpielerPanel() || "");
      if (t.phase === "messen" && raketeSchluessel !== schluessel) { raketeSchluessel = schluessel; laut(t, status); }
    }

    async function laut(t, status) {
      const m = await mikroHolen();
      if (!m) { api.hinweis("Kein Mikrofon gefunden – das Spiel braucht das USB-Mikro am Fernseher.", 6000); return tvAktion({ art: "kein_mikro" }); }
      const bild = ansicht.querySelector(".hs-rakete-bild");
      let hoehe = 0;
      const ende = Date.now() + t.messen_s * 1000, schritt = 1000 / (t.messen_s * 20);
      status.textContent = "AAAAAH! 📣";
      while (offen && Date.now() < ende) {
        m.analyse.getFloatTimeDomainData(m.puffer);
        let summe = 0;
        for (const wert of m.puffer) summe += wert * wert;
        const pegel = Math.max(0, Math.min(1, (Math.sqrt(summe / m.puffer.length) - 0.02) * 4));
        hoehe = Math.min(1000, hoehe + pegel * schritt);
        if (bild) bild.style.bottom = `${hoehe / 1000 * 88}%`;
        status.textContent = `${Math.round(hoehe)} m`;
        await new Promise((f) => setTimeout(f, 50));
      }
      if (offen) tvAktion({ art: "ergebnis", hoehe: Math.round(hoehe) });
    }

    /* ------------------------------------------------ 4.4: Klatsch-Rhythmus */
    let klatschSchluessel = "";
    function zeichneKlatsch() {
      const t = z.tv;
      hilfe.textContent = "Hör zu und klatsch den Rhythmus nach – nah am Mikro · STOP: zur Auswahl";
      const schluessel = `${t.runde}|${t.dran}|${t.abstaende.join(",")}`;
      if (!ansicht.querySelector(".hs-klatsch") || ansicht.dataset.klatsch !== schluessel) {
        ansicht.dataset.klatsch = schluessel;
        const punkteReihe = [0, ...t.abstaende];
        setze(ansicht, spielerLeiste(), el("div", { class: "hs-klatsch" }, el("h3", { class: "hs-saenger" }),
          el("div", { class: "hs-takt" }, ...punkteReihe.map((a, i) => el("span", { class: "hs-schlag", "data-i": i, style: `margin-left:${a * 3}vw` }, "👏"))),
          el("div", { class: "hs-status hs-klatsch-status" })), el("div", { class: "hs-tv-box" }));
      }
      ansicht.querySelector(".hs-saenger").textContent = `👏 ${t.dran} · Runde ${t.runde} von ${t.runden}`;
      ansicht.querySelector(".hs-spielerleiste")?.replaceWith(spielerLeiste());   /* Punkte aktuell halten */
      const status = ansicht.querySelector(".hs-klatsch-status");
      if (t.phase === "vorspielen") status.textContent = "👂 Gut zuhören …";
      if (t.phase === "daumen") status.textContent = `${t.ergebnis.text}${t.daumen ? ` · ${t.daumen}× 👍` : ""}`;
      ansicht.querySelector(".hs-tv-box").replaceChildren(tvSpielerPanel() || "");
      if (t.phase === "vorspielen" && klatschSchluessel !== schluessel + "v") { klatschSchluessel = schluessel + "v"; klopfen(t); }
      if (t.phase === "messen" && klatschSchluessel !== schluessel + "m") { klatschSchluessel = schluessel + "m"; klatschenHoeren(t, status); }
    }

    function klick() {
      const a = ctx(), o = a.createOscillator(), g = a.createGain(), t0 = a.currentTime;
      o.type = "square"; o.frequency.value = 1100;
      g.gain.setValueAtTime(0.25, t0); g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.08);
      o.connect(g).connect(a.destination); o.start(t0); o.stop(t0 + 0.1);
    }

    async function klopfen(t) {
      const reihe = [0, ...t.abstaende];
      for (let i = 0; i < reihe.length && offen; i++) {
        if (i) await new Promise((f) => setTimeout(f, reihe[i] * t.einheit_ms));
        klick();
        const s = ansicht.querySelector(`.hs-schlag[data-i="${i}"]`);
        s?.classList.add("klingt");
        setTimeout(() => s?.classList.remove("klingt"), 150);
      }
      await new Promise((f) => setTimeout(f, 700));
      if (offen) tvAktion({ art: "bereit" });
    }

    async function klatschenHoeren(t, status) {
      const m = await mikroHolen();
      if (!m) { api.hinweis("Kein Mikrofon gefunden – das Spiel braucht das USB-Mikro am Fernseher.", 6000); return tvAktion({ art: "kein_mikro" }); }
      status.textContent = "👏 Jetzt du!";
      const erwartet = t.abstaende.length + 1;
      const dauer = t.abstaende.reduce((a, b) => a + b, 0) * t.einheit_ms;
      const zeiten = [];
      let mittel = 0.01, zuletzt = 0, start = Date.now(), erster = 0;
      while (offen && Date.now() - start < 8000) {
        m.analyse.getFloatTimeDomainData(m.puffer);
        let spitze = 0;
        for (const wert of m.puffer) spitze = Math.max(spitze, Math.abs(wert));
        const jetzt = Date.now();
        if (spitze > 0.25 && spitze > mittel * 4 && jetzt - zuletzt > 120) {
          zeiten.push(jetzt); zuletzt = jetzt; erster = erster || jetzt;
          ansicht.querySelector(`.hs-schlag[data-i="${zeiten.length - 1}"]`)?.classList.add("treffer");
          ton("punkt");
        }
        mittel = mittel * 0.95 + spitze * 0.05;
        if (erster && (zeiten.length >= erwartet || jetzt - erster > dauer + 1500)) break;
        await new Promise((f) => setTimeout(f, 15));
      }
      /* Vergleich der Abstände: ±35 % gilt als im Takt; der erste Klatscher zählt, wenn es überhaupt einen gab */
      let treffer = zeiten.length ? 1 : 0;
      t.abstaende.forEach((a, i) => {
        if (zeiten[i + 1] === undefined) return;
        const soll = a * t.einheit_ms, ist = zeiten[i + 1] - zeiten[i];
        if (Math.abs(ist - soll) <= soll * 0.35) treffer++;
      });
      if (offen) tvAktion({ art: "ergebnis", treffer });
    }

    /* ------------------------------------------------ Ton-Treffer: vorspielen und zuhören */
    function spieleNote(midi, dauer = 0.55) {
      const a = ctx(), o = a.createOscillator(), g = a.createGain(), t0 = a.currentTime;
      o.type = "sine"; o.frequency.value = hz(midi);
      g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(0.3, t0 + 0.02);
      g.gain.setValueAtTime(0.3, t0 + dauer * 0.7); g.gain.exponentialRampToValueAtTime(0.0001, t0 + dauer);
      o.connect(g).connect(a.destination); o.start(t0); o.stop(t0 + dauer + 0.05);
    }

    async function vorspielen(t) {
      for (let i = 0; i < t.folge.length; i++) {
        if (!offen) return;
        const note = ansicht.querySelector(`.hs-note[data-i="${i}"]`);
        note?.classList.add("klingt");
        spieleNote(t.folge[i].midi);
        await new Promise((f) => setTimeout(f, 700));
        note?.classList.remove("klingt");
      }
      await new Promise((f) => setTimeout(f, 400));
      if (offen) tvAktion({ art: "bereit" });
    }

    async function mikroHolen() {
      if (mikro) return mikro;
      try {
        const strom = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
        const a = ctx(), quelle = a.createMediaStreamSource(strom), analyse = a.createAnalyser();
        analyse.fftSize = 4096;
        quelle.connect(analyse);
        mikro = { strom, analyse, puffer: new Float32Array(analyse.fftSize), quelle };
        return mikro;
      } catch (_) { return null; }
    }

    async function singen(t, status) {
      const m = await mikroHolen();
      if (!m) { api.hinweis("Kein Mikrofon gefunden – Ton-Treffer braucht das USB-Mikro am Fernseher.", 6000); return tvAktion({ art: "kein_mikro" }); }
      singt = true;
      const treffer = [];
      const proNote = Math.max(4000, t.singen_s * 1000 / t.folge.length);
      const pegel = ansicht.querySelector(".hs-pegel span");
      for (let i = 0; i < t.folge.length && offen; i++) {
        const note = ansicht.querySelector(`.hs-note[data-i="${i}"]`);
        note?.classList.add("jetzt");
        status.textContent = `🎤 Sing: ${t.folge[i].silbe}`;
        const ziel = t.folge[i].midi, start = Date.now();
        let haltSeit = 0, ok = false;
        while (offen && Date.now() - start < proNote) {
          m.analyse.getFloatTimeDomainData(m.puffer);
          const f = tonhoehe(m.puffer, ctx().sampleRate);
          if (f) {
            let cent = 1200 * Math.log2(f / hz(ziel));
            cent = ((cent % 1200) + 1800) % 1200 - 600;           /* Oktave egal - Kinderstimmen singen oft höher */
            if (pegel) pegel.style.left = `${50 + Math.max(-50, Math.min(50, cent / 6))}%`;
            if (Math.abs(cent) <= 60) { haltSeit = haltSeit || Date.now(); if (Date.now() - haltSeit > 350) { ok = true; break; } } else haltSeit = 0;
          } else haltSeit = 0;
          await new Promise((f2) => setTimeout(f2, 80));
        }
        note?.classList.remove("jetzt");
        note?.classList.add(ok ? "treffer" : "daneben");
        ton(ok ? "punkt" : "anschlag");
        treffer.push(ok);
      }
      singt = false;
      if (offen) tvAktion({ art: "ton_ergebnis", treffer });
    }

    /* ------------------------------------------------ Tasten */
    function lobbyTaste(t) {
      const eintraege = unter ? unter.eintraege : z.spiele;
      if (["ArrowDown", "ArrowRight"].includes(t)) { wahl = (wahl + 1) % eintraege.length; ton("bewegen"); zeichne(); return true; }
      if (["ArrowUp", "ArrowLeft"].includes(t)) { wahl = (wahl + eintraege.length - 1) % eintraege.length; ton("bewegen"); zeichne(); return true; }
      if (t === "Enter" || t === " ") {
        if (unter) { const e = unter.eintraege[wahl]; unter = null; wahl = 0; tvAktion(e.start); return true; }
        const s = z.spiele[wahl];
        if (!s.geht) { api.hinweis("Dafür braucht es mindestens ein Handy – scannt den QR-Code!", 4000); ton("fehler"); return true; }
        if (s.id === "quiz" || s.id === "buzzer") {
          unter = { titel: `${SPIEL_SYMBOL[s.id]} ${s.name}: welche Fragen?`, eintraege: Object.entries(z.pakete)
            .filter(([k]) => k !== "eigene" || z.eigene_fragen > 0).map(([k, v]) => ({ text: v, start: { art: "start", spiel: s.id, paket: k } })) };
          wahl = 0; zeichne(); ton("ok"); return true;
        }
        if (s.id === "raumschiff") {
          unter = { titel: "🚀 Raumschiff-Rettung: wie schwer?", eintraege: [
            { text: "🙂 Leicht (nur Farben)", start: { art: "start", spiel: "raumschiff", stufe: 1 } },
            { text: "🤓 Schwer (Farben und Zeichen)", start: { art: "start", spiel: "raumschiff", stufe: 2 } }] };
          wahl = 0; zeichne(); ton("ok"); return true;
        }
        tvAktion({ art: "start", spiel: s.id }); ton("ok"); return true;
      }
      if (t === "Escape" || t === "Backspace") {
        if (unter) { unter = null; wahl = 0; zeichne(); return true; }
        return false;                                              /* schließt das Overlay -> schliesse() */
      }
      return true;
    }

    function spielTaste(t) {
      const s = z.tv_spieler || {};
      if (t === "Escape" || t === "Backspace") { tvAktion({ art: "lobby" }); return true; }
      if (s.ansicht === "buzzer" && (t === "Enter" || t === " ")) { spielerAktion({ art: "buzz" }); ton("ok"); return true; }
      const liste = s.ansicht === "wahl" ? s.optionen : s.ansicht === "knoepfe" ? s.knoepfe : null;
      if (liste && liste.length) {
        if (t === "ArrowRight" || t === "ArrowDown") { tvWahl = (tvWahl + 1) % liste.length; ton("bewegen"); zeichne(); return true; }
        if (t === "ArrowLeft" || t === "ArrowUp") { tvWahl = (tvWahl + liste.length - 1) % liste.length; ton("bewegen"); zeichne(); return true; }
        if (t === "Enter" || t === " ") {
          spielerAktion(s.ansicht === "wahl" ? { art: "wahl", index: tvWahl } : { art: "knopf", id: liste[tvWahl].id });
          ton("ok"); tvWahl = 0; return true;
        }
      }
      if (s.ansicht === "daumen" && (t === "Enter" || t === " ") && !s.gegeben) { spielerAktion({ art: "daumen" }); return true; }
      return true;
    }

    return {
      taste(t) {
        if (!z) return t !== "Escape" && t !== "Backspace";
        if (!z.spiel && z.ergebnis) { if (["Enter", " ", "Escape", "Backspace"].includes(t)) tvAktion({ art: "lobby" }); return true; }
        return z.spiel ? spielTaste(t) : lobbyTaste(t);
      },
      anhalten() { /* Bewegungspause: Spielstand läuft auf dem Server weiter */ },
      schliesse() {
        offen = false;
        clearTimeout(abfrage);
        if (mikro) { mikro.quelle.disconnect(); mikro.strom.getTracks().forEach((s) => s.stop()); mikro = null; }
        api.sende("/api/raum/schliessen", {}).catch(() => {});
      },
    };
  },
};
