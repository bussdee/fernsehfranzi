# Test-Suite des Family Hub

Diese Tests gehoeren zum Entwickler-Paket v2.3.1 und schuetzen die
haeufigsten Bruchstellen (Navigation, Eingabe-Pipeline, Server-Preflight)
vor Rueckschritten. Hintergrund und Fehlerbilder: siehe
`docs/ENTWICKLERDOKUMENTATION.md`, Kapitel 11.

## Voraussetzungen (einmalig, nur fuer den Navigationstest)

```bash
pip install playwright
python3 -m playwright install chromium
```

## 1. Navigationstest (der wichtigste)

```bash
python3 tests/test_nav.py
```

Prueft die raeumliche Kachel-Navigation in zwei Layouts (1920x1080 mit
Spielzimmer-Reihe, 800x600 mit 3x2-Raster): Pfeil-Nachbarn, Anschlag am
Rand, Tab/Shift+Tab-Reihenfolge, Home/End, Ziffern-Direktwahl, Overlay
auf/zu - und sammelt nebenbei alle JavaScript-Laufzeitfehler.
Ergebnis: `Alle Navigationspruefungen bestanden, keine JS-Fehler.`
(Exit-Code 1 plus Fehlerliste, wenn etwas daneben geht.)

## 2. Konsolen-Schnelltests (ohne Installation)

`index.html` im Chromium oeffnen, DevTools-Konsole oeffnen
(Strg+Shift+I), Dateiinhalt einfuegen und Enter:

- `nav_test.js` - drueckt synthetische Tasten und protokolliert
  Kachelfolge, Tab-Verhalten und den F7-Abfang.
- `gamepad_test.js` - simuliert einen Controller ohne angeschlossenes
  Pad (A-Knopf, Steuerkreuz, Alt+F4-Abfang im Spiel, Memory-Klick).

## 3. Server-Smoke-Test (ohne Pi)

**Achtung:** Fall B ruft `/games` auf. Der Server beendet dabei mit
`pkill -9 -f chromium` **jeden** Chromium des Rechners. Nicht auf einem
Arbeitsrechner mit offenem Browser ausfuehren; `make test` nutzt ihn deshalb nicht.

```bash
bash tests/smoke_test_server.sh
```

Kopiert das Paket in ein temporäres Verzeichnis und prueft:
Fall A - ohne X-Socket auf Anzeige :99 muss der Spielstart abgelehnt
und im Log begruendet werden (X-Preflight). Fall B - mit vorhandenem
X-Socket wird der Start angeordnet und scheitert auf dem
Entwicklungsrechner sauber im Log (EmulationStation fehlt dort - genau
diese Meldung wird geprueft). Ausserdem /status, 404-Verhalten und die
Log-Ausgaben. Der echte X-Socket des Rechners wird nicht angetastet.

## 4. Manueller Prüfplan am Gerät

Rund 10 Minuten Checkliste inklusive Games-Zyklus und Bildschirmschoner:
`docs/ENTWICKLERDOKUMENTATION.md`, Kapitel 11.3.
