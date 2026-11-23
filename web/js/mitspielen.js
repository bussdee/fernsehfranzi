/* FernsehFranzi 4.3 - Mitspielen am Handy (Spielraum).
 *
 * Das Handy scannt den QR-Code am Fernseher (…/mitspielen?r=<Schlüssel>) oder gibt den Raumcode ein, wählt Namen und
 * Tier und ist dabei. Danach fragt die Seite den Fernseh-Pi regelmäßig nach der eigenen Ansicht und zeigt sie an:
 *   warten · buzzer · wahl · malen · knoepfe · daumen · ergebnis
 * Nichts wird gespeichert außer dem eigenen Geheimnis im sessionStorage (zum Wiederverbinden nach WLAN-Abbruch).
 * Eigenständig (keine Module von der Startseite): dieser Server liefert nur diese Seite. */

const SYMBOLE = ["🦊", "🐼", "🐸", "🦄", "🐯", "🐙", "🐧", "🦁", "🐨", "🐵", "🐲", "🐝"];
const buehne = document.getElementById("buehne");
const ichBox = document.getElementById("ich");
const meldungBox = document.getElementById("meldung");
const params = new URLSearchParams(location.search);
let sitzung = lies() || {};
let letzte = "", zustand = null, abfrage = null, malen = null;

function el(tag, attr = {}, ...kinder) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attr)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "text") e.textContent = v;
    else if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kinder.flat()) if (k !== null && k !== undefined && k !== false) e.append(k);
  return e;
}

function lies() { try { return JSON.parse(sessionStorage.getItem("ff-raum") || "null"); } catch (_) { return null; } }
function merke(s) { try { sessionStorage.setItem("ff-raum", JSON.stringify(s)); } catch (_) { /* privat */ } }

function zeigeMeldung(text, fehler = false) {
  meldungBox.textContent = text;
  meldungBox.className = fehler ? "fehler" : "";
  meldungBox.hidden = false;
  clearTimeout(zeigeMeldung.t);
  zeigeMeldung.t = setTimeout(() => { meldungBox.hidden = true; }, 3500);
}

async function anfrage(pfad, daten) {
  const opt = { headers: { "X-FF-Spieler": sitzung.geheim || "" }, cache: "no-store" };
  if (daten !== undefined) Object.assign(opt, { method: "POST", body: JSON.stringify(daten) }, { headers: { ...opt.headers, "Content-Type": "application/json" } });
  const a = await fetch(pfad, opt);
  let d = {};
  try { d = await a.json(); } catch (_) { /* leer */ }
  if (!a.ok) { const f = new Error(d.fehler || "Fehler " + a.status); f.status = a.status; throw f; }
  return d;
}

/* ---------------------------------------------------------------- Beitreten */
function beitretenSeite(hinweis = "") {
  stoppeAbfrage();
  ichBox.textContent = "";
  let symbol = SYMBOLE[Math.floor(Math.random() * SYMBOLE.length)];
  const schluessel = params.get("r") || sitzung.schluessel || "";
  const code = el("input", { class: "eingabe gross", maxlength: 4, placeholder: "Raumcode", autocapitalize: "characters", autocomplete: "off" });
  const name = el("input", { class: "eingabe", maxlength: 16, placeholder: "Dein Name", autocomplete: "nickname" });
  const leicht = el("input", { type: "checkbox", id: "leicht" });
  const tiere = el("div", { class: "tiere" }, ...SYMBOLE.map((s) => el("button", {
    type: "button", class: "tier" + (s === symbol ? " an" : ""), text: s,
    onclick: (e) => { symbol = s; tiere.querySelectorAll(".tier").forEach((t) => t.classList.toggle("an", t === e.currentTarget)); },
  })));
  const los = el("button", { class: "knopf haupt", type: "submit", text: "Mitspielen" });
  const form = el("form", { class: "beitreten" },
    el("h1", { text: "Mitspielen 🎮" }),
    hinweis ? el("p", { class: "hinweis", text: hinweis }) : null,
    schluessel ? null : el("label", {}, el("span", { text: "Code vom Fernseher" }), code),
    el("label", {}, el("span", { text: "Name" }), name),
    el("span", { class: "klein", text: "Dein Tier" }), tiere,
    el("label", { class: "zeile" }, leicht, el("span", { text: "Ich bin noch klein – mehr Zeit beim Quiz" })),
    los);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    los.disabled = true;
    try {
      const d = await anfrage("/api/raum/beitreten", { schluessel: schluessel || code.value.trim().toUpperCase(), name: name.value,
                                                       symbol, leicht: leicht.checked });
      sitzung = { schluessel: schluessel || code.value.trim().toUpperCase(), geheim: d.geheim };
      merke(sitzung);
      history.replaceState(null, "", "/mitspielen");
      starteAbfrage();
    } catch (f) { zeigeMeldung(f.message, true); los.disabled = false; }
  });
  buehne.replaceChildren(form);
  setTimeout(() => name.focus(), 50);
}

/* ---------------------------------------------------------------- Abfragen */
function starteAbfrage() {
  stoppeAbfrage();
  const runde = async () => {
    try {
      const d = await anfrage("/api/raum/zustand");
      zeige(d);
    } catch (f) {
      if (f.status === 400) { sessionStorage.removeItem("ff-raum"); sitzung = {}; return beitretenSeite(f.message); }
      zeigeMeldung("Verbindung wackelt … ich versuche es weiter.", true);
    }
    abfrage = setTimeout(runde, 700);
  };
  runde();
}
function stoppeAbfrage() { clearTimeout(abfrage); abfrage = null; }

async function aktion(daten) {
  try { zeige(await anfrage("/api/raum/aktion", daten), true); if (navigator.vibrate) navigator.vibrate(30); }
  catch (f) { zeigeMeldung(f.message, true); }
}

/* ---------------------------------------------------------------- Ansichten */
function zeige(d, sofort = false) {
  zustand = d;
  ichBox.textContent = `${d.ich.symbol} ${d.ich.name} · ${d.ich.punkte} ⭐`;
  const schluessel = JSON.stringify([d.version, d.ansicht, d.titel, d.text, d.optionen, d.wort, d.knoepfe, d.aktiv, d.gegeben, d.platz]);
  if (d.ansicht === "malen" && malen && malen.wort === d.wort) { malen.rest(d.rest); return; }       /* nicht neu aufbauen, solange gemalt wird */
  if (schluessel === letzte && !sofort) { const r = buehne.querySelector(".rest"); if (r && d.rest !== undefined) r.textContent = `⏳ ${d.rest} s`; return; }
  letzte = schluessel;
  if (malen && d.ansicht !== "malen") { malen.stopp(); malen = null; }
  const titel = d.titel ? el("h2", { text: d.titel }) : null;
  const text = d.text ? el("p", { class: "text", text: d.text }) : null;
  const rest = d.rest !== undefined ? el("div", { class: "rest", text: `⏳ ${d.rest} s` }) : null;
  const ansichten = {
    warten: () => [titel, text, d.gewaehlt ? el("p", { class: "klein", text: `Deine Antwort: ${d.gewaehlt}` }) : null, el("div", { class: "warten-punkte", text: "• • •" })],
    buzzer: () => [titel, text, el("div", { class: "buzzer-box" }, el("button", { class: "buzzer", type: "button", text: "BUZZ!", onclick: () => aktion({ art: "buzz" }) }))],
    wahl: () => [titel, text, rest, el("div", { class: "optionen" }, ...(d.optionen || []).map((o, i) =>
      el("button", { class: "option o" + i, type: "button", text: o, onclick: () => aktion({ art: "wahl", index: i }) })))],
    malen: () => { malen = malFlaeche(d); return [el("h2", { text: `Male: ${d.wort}` }), malen.knoten]; },
    knoepfe: () => [titel, el("div", { class: "rest", text: d.aktiv ? `⏳ ${d.rest} s` : "" }), text,
      el("div", { class: "schalter" }, ...(d.knoepfe || []).map((k) => el("button", { class: "schalter-knopf", type: "button", text: k.text,
        disabled: !d.aktiv, onclick: () => aktion({ art: "knopf", id: k.id }) }))),
      (d.handbuch || []).length ? el("div", { class: "handbuch" }, el("h3", { text: "📖 Dein Handbuch" }),
        ...d.handbuch.map((z) => el("div", { class: "regel", text: z }))) : el("p", { class: "klein", text: "Du hast kein Handbuch – frag die anderen!" })],
    daumen: () => [titel, text, el("button", { class: "daumen" + (d.gegeben ? " an" : ""), type: "button", text: d.gegeben ? "👍 Danke!" : "👍",
      disabled: d.gegeben, onclick: () => aktion({ art: "daumen" }) })],
    ergebnis: () => [el("h2", { text: d.platz === 1 ? "🏆 Gewonnen!" : `Platz ${d.platz}` }), d.text ? el("p", { class: "text", text: d.text }) : null,
      el("ol", { class: "rangliste" }, ...(d.rangliste || []).map((r) => el("li", { class: r.id === d.ich.id ? "ich" : "", text: `${r.symbol} ${r.name} – ${r.punkte} ⭐` }))),
      el("p", { class: "klein", text: "Am Fernseher geht es gleich weiter." })],
  };
  buehne.replaceChildren(el("section", { class: "ansicht ansicht-" + d.ansicht }, ...(ansichten[d.ansicht] || ansichten.warten)()));
}

/* Malen: Finger zeichnet, Striche gehen gesammelt alle 250 ms zum Fernseher (Koordinaten 0 bis 1000) */
function malFlaeche(d) {
  const flaeche = el("canvas", { class: "malflaeche" });
  let farbe = d.farben?.[0] || "#111111", dicke = 8, offen = [], aktuell = null, sendet = false;
  const restBox = el("div", { class: "rest", text: `⏳ ${d.rest} s` });
  const farben = el("div", { class: "farben" }, ...(d.farben || []).map((f) => el("button", {
    type: "button", class: "farbe" + (f === farbe ? " an" : ""), style: `background:${f}`, "aria-label": "Farbe",
    onclick: (e) => { farbe = f; farben.querySelectorAll(".farbe").forEach((x) => x.classList.toggle("an", x === e.currentTarget)); },
  })), el("button", { type: "button", class: "farbe dick", text: "◯", onclick: () => { dicke = dicke === 8 ? 18 : 8; } }),
     el("button", { type: "button", class: "farbe loeschen", text: "🗑", onclick: () => { g.clearRect(0, 0, flaeche.width, flaeche.height); aktion({ art: "loeschen" }); } }));
  const knoten = el("div", { class: "malen-box" }, restBox, flaeche, farben);
  let g;
  requestAnimationFrame(() => {
    const breite = flaeche.clientWidth, dpr = devicePixelRatio || 1;
    flaeche.width = breite * dpr; flaeche.height = breite * 0.75 * dpr; flaeche.style.height = breite * 0.75 + "px";
    g = flaeche.getContext("2d"); g.scale(dpr, dpr); g.lineCap = "round"; g.lineJoin = "round";
  });
  const punkt = (e) => { const r = flaeche.getBoundingClientRect(); return [Math.round((e.clientX - r.left) / r.width * 1000), Math.round((e.clientY - r.top) / r.height * 1000)]; };
  const male = (a, b) => { const r = flaeche.getBoundingClientRect(); g.strokeStyle = farbe; g.lineWidth = dicke * r.width / 500;
    g.beginPath(); g.moveTo(a[0] / 1000 * r.width, a[1] / 1000 * r.height); g.lineTo(b[0] / 1000 * r.width, b[1] / 1000 * r.height); g.stroke(); };
  flaeche.addEventListener("pointerdown", (e) => { e.preventDefault(); flaeche.setPointerCapture(e.pointerId); const p = punkt(e); aktuell = { p: [...p, ...p], f: farbe, d: dicke, neu: true }; offen.push(aktuell); male(p, p); });
  flaeche.addEventListener("pointermove", (e) => { if (!aktuell) return; const p = punkt(e); const n = aktuell.p.length; male([aktuell.p[n - 2], aktuell.p[n - 1]], p); aktuell.p.push(...p);
    if (aktuell.p.length > 300) { const weiter = { p: aktuell.p.slice(-2), f: farbe, d: dicke }; aktuell = weiter; offen.push(weiter); } });
  const ende = () => { aktuell = null; };
  flaeche.addEventListener("pointerup", ende); flaeche.addEventListener("pointercancel", ende);
  const takt = setInterval(async () => {
    if (sendet || !offen.length) return;
    const pakete = offen.filter((s) => s !== aktuell || s.p.length > 2);
    if (!pakete.length) return;
    const raus = pakete.map((s) => ({ ...s, p: s.p.slice() }));
    pakete.forEach((s) => { if (s === aktuell) { aktuell = { p: s.p.slice(-2), f: s.f, d: s.d }; offen.push(aktuell); } });
    offen = offen.filter((s) => !pakete.includes(s));
    sendet = true;
    try { await anfrage("/api/raum/aktion", { art: "striche", striche: raus }); } catch (_) { offen.unshift(...raus); }
    sendet = false;
  }, 250);
  return { knoten, wort: d.wort, stopp: () => clearInterval(takt), rest: (s) => { restBox.textContent = `⏳ ${s} s`; } };
}

/* ---------------------------------------------------------------- Los */
if (sitzung.geheim && !params.get("r")) starteAbfrage();
else if (sitzung.geheim && params.get("r") === sitzung.schluessel) starteAbfrage();
else beitretenSeite();
