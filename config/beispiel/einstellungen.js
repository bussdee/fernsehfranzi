/* FernsehFranzi – persönliche Einstellungen (VORLAGE).
 *
 * Kopieren nach config/einstellungen.js und dort anpassen:
 *     cp config/beispiel/einstellungen.js config/einstellungen.js
 *
 * config/einstellungen.js ist nicht im Repository (.gitignore) und wird beim
 * Ausliefern nur angelegt, wenn sie auf dem Gerät noch fehlt – nie überschrieben.
 * Auf dem Gerät liegt sie unter <Hub-Ordner>/config/einstellungen.js.
 */
window.FERNSEHFRANZI_EINSTELLUNGEN = {
  // Name des Kindes für die Begrüßung ("Guten Morgen, …!"). Leer = ohne Namen.
  name: "",

  // Zusatz im Kopf: "Home Entertainment · <untertitel>". Leer = ohne Zusatz.
  untertitel: "",

  // Adressen der App-Kacheln im Heimnetz. Fehlt eine, zeigt die Kachel einen Hinweis.
  links: {
    plex: "http://SERVER-ADRESSE:32400/web/",
    familie: "http://SERVER-ADRESSE:8088",
    buecher: "http://SERVER-ADRESSE:5000/login",
  },

  // Geburtstage als "MM-TT", z. B. { name: "Kim", tag: "03-14" }.
  geburtstage: [],
};
