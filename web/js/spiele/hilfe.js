/* FernsehFranzi 6.8.5 - „Ich brauche Hilfe“: ein großer Knopf, OK schickt sofort eine Telegram-Nachricht an Mama und Papa.
 * Erscheint nur, wenn die Eltern ihn eingeschaltet haben und Telegram eingerichtet ist. STOP zurück. */
import { el, franzi } from "../gemeinsam.js";
import { kopf, ton } from "./kern.js";

export default {
  symbol: "🆘",
  oeffne(box, api) {
    const { inhalt } = kopf(box, "🆘 Ich brauche Hilfe", "OK = Mama und Papa Bescheid sagen · STOP zurück");
    let gesendet = false;
    const text = el("p", { class: "hilfe-text", text: "Brauchst du Hilfe? Drück OK – dann bekommen Mama und Papa sofort eine Nachricht." });
    const knopf = el("button", { class: "knopf hilfe-knopf gewaehlt", type: "button", tabindex: "-1", text: "🆘 Hilfe holen" });
    const figur = el("div", { class: "hilfe-franzi" }, franzi("staunen", "franzi-leer"));
    inhalt.replaceChildren(el("div", { class: "hilfe-seite" }, figur, text, knopf));
    async function senden() {
      if (gesendet) return;
      gesendet = true;
      knopf.disabled = true;
      text.textContent = "Einen Moment …";
      try {
        const a = await api.sende("/api/hilfe", {});
        figur.replaceChildren(franzi("froh", "franzi-leer"));
        text.textContent = a.schon ? "Mama und Papa haben deine Nachricht schon – sie melden sich gleich."
          : a.gesendet.length ? "Mama und Papa wissen Bescheid und melden sich gleich. Bleib ruhig – das wird schon!"
          : "Die Nachricht ging gerade nicht raus. Bitte geh zu einem Erwachsenen oder ruf an.";
        knopf.textContent = a.gesendet.length || a.schon ? "✔ Nachricht ist unterwegs" : "⚠️ Bitte einen Erwachsenen holen";
        ton(a.gesendet.length || a.schon ? "ok" : "fehler");
      } catch (fehler) {
        text.textContent = fehler.message;
        knopf.textContent = "⚠️ Bitte einen Erwachsenen holen";
        ton("fehler");
      }
    }
    knopf.addEventListener("click", senden);
    return {
      taste(t) {
        if (t === "Enter" || t === " ") { senden(); return true; }
        return t !== "Escape" && t !== "Backspace";
      },
      schliesse() {},
    };
  },
};
