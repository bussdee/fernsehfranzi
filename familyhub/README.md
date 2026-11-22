# FernsehFranzi Family Hub (Version: Datei VERSION)

Kiosk-Startseite fuer den Pi 3 am Fernseher: Plex, RetroPie, Familien-Dashboard, Kavita,
Spielzimmer (6 Mini-Spiele), Bedienung per TV-Fernbedienung (CEC), Tastatur oder Controller.

## Bedienung
| Taste | Wirkung |
|---|---|
| Pfeile, OK | navigieren, oeffnen |
| 1-4 / 5-0 | Apps / Spielzimmer direkt |
| STOP | Zurueck (Spiel schliessen) |
| EXIT | im Spiel: Spiel beenden; in EmulationStation: RetroPie beenden (Startseite ist sofort da); in Plex/Kavita: Fenster schliessen, Hub startet nach ca. 5 s neu |
| ROT | Ton ueber HDMI (Fernseher) - ueberall, kurzer Bestaetigungston |
| GRUEN | Ton ueber Klinke - ueberall, kurzer Bestaetigungston |

Die Ton-Wahl bleibt gespeichert (audio.txt) und gilt auch in RetroPie.
RetroPie laeuft seit 2.5 auf einer eigenen Konsole (tty8, `fernsehfranzi-retropie.service`).
Ausliefern und Systemteil: `make deploy` im Repository (richtet `install/system.sh` ein).
Gelb/Blau sind frei. Unbekannte Fernbedienungstasten stehen in logs/cec.log
("Unbekannte CEC-Taste 0x..") und lassen sich in cec_keys.py (KEY_MAP) belegen.

## Installation
1. Alten Ordner sichern: `mv ~/familyhub ~/familyhub-alt`
2. Paket im Home entpacken: `cd ~ && unzip familyhub-v2.4.zip` (ergibt `~/familyhub`)
3. `bash ~/familyhub/install/install.sh`
4. `bash ~/familyhub/tests/pi_check.sh` - alle Punkte sollen [OK] sein (geht auch per ssh)
4b. Probelauf: `bash ~/familyhub/tests/es_test.sh` - startet EmulationStation wie spaeter der Server
5. `sudo reboot`

Das Skript kommentiert alte Zeilen in `~/.config/labwc/autostart` nur aus
(Sicherung: `autostart.vor-familyhub`) und stoppt die alten Dienste.

## Rueckweg
`cp ~/.config/labwc/autostart.vor-familyhub ~/.config/labwc/autostart`,
`sudo systemctl disable --now familyhub-server familyhub-cec`, Ordner zurueckbenennen.

## Einstellungen
Persoenliche Werte (Name, Untertitel, Adressen von Plex, Familien Dashboard und Kavita,
Geburtstage) stehen in `config/einstellungen.js` neben `index.html`. Diese Datei ist nicht
im Repository; die Vorlage liegt im Repository unter `config/beispiel/einstellungen.js`.

Im `CONFIG`-Block von `index.html`:
- `appsAlsPopup: false` - Apps im selben Vollbild-Fenster (sicher). `true` = Popup (EXIT kehrt sofort zurueck, evtl. mit Fensterrahmen).

## Aufbau (ein Besitzer pro Aufgabe)
- `kiosk.sh` (Autostart in labwc): startet Chromium immer wieder; wartet, solange ES laeuft
- `server.py` (systemd, 127.0.0.1:8765): startet EmulationStation als X11-Fenster (XWayland),
  Ton-Umschaltung (`/api/audio?ziel=hdmi|klinke`), Zeichnungs-Galerie
- `cec_keys.py` (systemd, root): TV-Fernbedienung -> virtuelle Tastatur
- `index.html`: Oberflaeche (persoenliche Werte aus `config/einstellungen.js`)

## Fehlersuche
| Symptom | Ansehen |
|---|---|
| Hub erscheint nicht | `logs/kiosk.log`; `bash tests/pi_check.sh` |
| GAMES: schwarz / kurz Ladebild, dann zurueck | `logs/retropie.log`, `/dev/shm/runcommand.log`, `logs/server.log` |
| Fernbedienung tot | `journalctl -u familyhub-cec -n 30`, `logs/cec.log` |
| Kein Ton | ROT/GRUEN druecken; `pactl list short sinks`; `logs/server.log` ("Audio:") |
| Taste ohne Wirkung | `logs/cec.log` zeigt unbekannte Codes |

## Versionen
Siehe CHANGELOG.md.
