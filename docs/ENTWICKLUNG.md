# FernsehFranzi – Entwickler-Dokumentation

Stand: Version 6.0.0 (November 2026). Diese Datei beschreibt, wie FernsehFranzi aufgebaut ist, nach welchen Grundsätzen
es gebaut wurde und wie man es weiterentwickelt, testet und ausliefert. Die Bedienung für Eltern und Kinder steht in den
Anleitungen (`docs/anleitung/`, als PDF in `web/`), die Änderungen je Version im [CHANGELOG](../CHANGELOG.md).

## Inhalt

1. [Was FernsehFranzi ist](#1--was-fernsehfranzi-ist)
2. [Grundsätze](#2--grundsätze)
3. [Gerät und Voraussetzungen](#3--gerät-und-voraussetzungen)
4. [Architektur](#4--architektur)
5. [Wer besitzt was](#5--wer-besitzt-was)
6. [Ordner im Repository](#6--ordner-im-repository)
7. [Server im Detail](#7--server-im-detail)
8. [Weboberfläche](#8--weboberfläche)
9. [Kiosk, Eingabe und RetroPie](#9--kiosk-eingabe-und-retropie)
10. [Datenablage](#10--datenablage)
11. [Sicherheit und Kinderschutz](#11--sicherheit-und-kinderschutz)
12. [Entwicklungsumgebung, Prüfungen und Tests](#12--entwicklungsumgebung-prüfungen-und-tests)
13. [Ausliefern auf das Gerät](#13--ausliefern-auf-das-gerät)
14. [Konventionen](#14--konventionen)
15. [Lehren aus der Entwicklung](#15--lehren-aus-der-entwicklung)
16. [Bekannte Grenzen und Ideen](#16--bekannte-grenzen-und-ideen)

---

## 1 · Was FernsehFranzi ist

Ein Raspberry Pi 3B+ am Fernseher wird zu einem **Smart-TV für Kinder**: eine schnelle Startseite mit Kacheln für Video
(Plex, YouTube-Auswahl der Eltern, eigene Video-Ordner), Bücher (Kavita), Hörbücher, Retro-Spiele (RetroPie), Lern-Apps
und ein eigenes Spielzimmer mit kleinen Spielen. Dazu kommen ein **Zeitkonto** mit Regeln der Eltern, ein
**Elternbereich** am Fernseher (PIN) und eine **Eltern-Seite** fürs Handy im Heimnetz.

Bedient wird alles mit der **TV-Fernbedienung** (HDMI-CEC), einem **Controller** oder einer **Tastatur**.

Abgrenzung: FernsehFranzi ist ein **Starter**, kein Dashboard. Es startet, was die Eltern freigeben, und bietet ein
kleines Spielzimmer. Kalender, Einkaufslisten und ähnliche Familien-Funktionen gehören nicht hinein.

## 2 · Grundsätze

Diese Grundsätze gelten für jede Änderung. Im Code wird auf sie als „Grundsatz N“ verwiesen.

**Produkt**

1. **Starter, kein Dashboard.** Die Startseite startet, was die Eltern freigeben, und bietet ein kleines Spielzimmer.
2. **Flüssig auf dem Pi 3, macht Spaß, kein Schnickschnack.** Eine neue Funktion muss etwas starten, spielen oder
   schützen. Leistung wird am Gerät gemessen, nicht geschätzt.
3. **Fernbedienung, Controller und Tastatur funktionieren überall.** Eine Funktion, die nur mit einem der drei geht, ist
   nicht fertig. Die Pfeiltasten sind immer Navigation.
4. **Kindgerecht:** deutsche, freundliche Texte, nie ein schwarzer Bildschirm ohne Erklärung.
5. **Eigene Spiele sind eigene Entwürfe** in bekannten Genres, keine Nachbauten bestimmter Spiele.

**Kinderschutz**

6. **Sicher von Grund auf.** Neue Schalter starten im strengsten Zustand. Aus dem Kiosk (Desktop, Terminal,
   Einstellungen) geht es nur mit Eltern-PIN.
7. **Die Eltern konfigurieren alles** (Zeit, Apps, Freigaben). Das Kind kann nichts davon ändern.
8. **Apps können „zählt nie“ sein** (z. B. Plex): Sie verbrauchen keine Zeit vom Zeitkonto.
9. Die PIN wird nur als **gesalzener Hash** gespeichert, nie im Code und nie im Klartext.
10. Die **Eltern-Seite ist nur fürs Heimnetz.** Die Kiosk-API horcht nur auf `127.0.0.1`.

**Technik**

11. **RetroPie läuft nur auf der Konsole** (eigenes VT, echtes Terminal). Kein X11/Wayland-Zwang, keine
    Display-Variablen, kein `SDL_VIDEODRIVER`.
12. **Ein Besitzer pro Aufgabe** (siehe [Abschnitt 5](#5--wer-besitzt-was)). Niemand außer dem Besitzer startet oder
    beendet dessen Prozess.
13. **Leicht für den Pi 3:** Python nur mit Standardbibliothek, JavaScript ohne Framework und ohne Build-Schritt, keine
    Node-Laufzeit auf dem Pi. Zusätzliche Pakete auf dem Gerät nur, wenn es nicht anders geht.
14. **Code und Daten getrennt:** Daten liegen außerhalb des Code-Ordners und überleben jedes Update. Migrationen sind
    idempotent und protokolliert.
15. **Fehler werden nie still verschluckt:** Ein gescheiterter Systemaufruf (sudo, systemctl, wpctl …) wird geprüft,
    geloggt und dem Nutzer verständlich gezeigt.

**Ausliefern und Repository**

16. **Das Gerät ist ein Live-System.** Lesen ist jederzeit erlaubt, Schreiben nur über die Werkzeuge im Repository
    (`make v3-deploy` usw.), die vorher sichern und zweimal nachfragen.
17. **Erst vollständig lokal prüfen, dann ausliefern.** Das Gerät ist kein Testserver. Bei Rot: zurückrollen, Zustand
    sichern, Ursache suchen.
18. **Namen, Pfade, URLs, Ports und Konten werden nie geraten.** Sie werden am Gerät nachgesehen.
19. **Keine privaten Daten in versionierten Dateien:** keine Adressen, Hostnamen, Namen von Familienmitgliedern, PINs
    oder Schlüssel. Sie gehören in `config/` oder `.local/` (beide nicht versioniert). `make check` sucht danach.
20. **Eine Versionsquelle:** die Datei `VERSION`. Was eine Version anzeigt oder meldet, liest sie von dort.

## 3 · Gerät und Voraussetzungen

Entwickelt und betrieben auf:

| Teil | Stand |
|---|---|
| Rechner | Raspberry Pi 3B+ (1 GB RAM), Kühlkörper; bei 60 °C drosselt der Pi auf 1,2 GHz |
| System | Raspberry Pi OS (Bookworm), labwc (Wayland), lightdm-Autologin des Kiosk-Benutzers |
| Browser | Chromium aus Raspberry Pi OS, gesteuert über die DevTools-Pipe |
| Retro | RetroPie (EmulationStation, RetroArch, lr-vice für C64, Amiberry für Amiga) |
| Eingabe | TV-Fernbedienung über HDMI-CEC (`cec-client`), Xbox-360-Controller (Kabel), Bluetooth-Tastatur mit Touchpad |
| Ton | HDMI (Vorgabe) oder Klinke; ein USB-Mikrofon für die Bass-Ecke ist nie Ausgang |
| Netz | WLAN oder LAN |

Optional im Heimnetz: Plex, Kavita, FileBrowser (für Hörbücher, Video-Ordner und Wecktöne), ein Telegram-Bot.

**Konten auf dem Gerät:** Der **Kiosk-Benutzer** (Autologin, Chromium, Server) hat nur eine enge sudo-Regel
(`system/sudoers.d/fernsehfranzi`). Ein eigenes **Admin-Konto** mit Passwort übernimmt Deploys und Installationen
(`make admin-einrichten`, siehe [Abschnitt 13](#13--ausliefern-auf-das-gerät)).

> **Hinweis:** Die Werkzeuge sind für genau diesen Aufbau geschrieben. Eine fertige Installationsanleitung für ein
> frisch aufgesetztes Gerät gibt es noch nicht. `install/install.sh` übernimmt eine vorhandene 2.x-Installation
> (`~/familyhub`), funktioniert aber auch ohne sie.

## 4 · Architektur

```
 Fernbedienung (CEC) ─┐
 Controller ──────────┼──► eingabe.py (root)  ── virtuelle Tastatur (uinput) ──► Chromium / EmulationStation / Apps
 Tastatur ────────────┘        │  meldet Tasten und „Zur Startseite“
                               ▼
 server (python3 -m fernsehfranzi, Kiosk-Benutzer) – das Gehirn
   127.0.0.1:8765  Startseite, Kiosk-API, Elternbereich am TV
   LAN-Port 8766   nur Eltern-Seite (einschaltbar im Elternbereich)
   LAN-Port 8767   nur Mitspiel-Seite der Handy-Spiele, solange ein Spielraum offen ist (4.3)
   Zeitkonto · PIN · App-Katalog · Whitelist · Familie · Telegram · Statistik
        │ Aufträge (lange Abfrage)            │ systemctl über die enge sudo-Regel
        ▼                                     ▼
 kiosk.py (labwc-Sitzung)               fernsehfranzi-retropie.service (tty8)
   Chromium im Kiosk-Modus                EmulationStation → runcommand → RetroArch (KMS)
   über --remote-debugging-pipe          fernsehfranzi-spiel.service (tty8)
   Desktop-Apps, Bildschirmfoto            ein Spiel direkt aus „Zuletzt gespielt“
                                         fernsehfranzi-scraper.service (oneshot)
                                           Spielbilder für EmulationStation
```

Ablauf beim Start einer Kachel: Die Startseite schickt `POST /api/start` (mit Token). Der Server prüft Freigabe und
Zeitkonto und entscheidet: Eine Web-App wird als Auftrag an `kiosk.py` gegeben (Chromium öffnet die Adresse), RetroPie
wird über `systemctl start --no-block fernsehfranzi-retropie.service` gestartet. Während eines Retro-Spiels ist Chromium
ganz beendet (spart 400–600 MiB RAM). Danach startet `kiosk.py` die Startseite neu mit `#zurueck`.

„Zur Startseite“ geht von überall: EXIT auf der Fernbedienung, die Xbox-Taste oder Home auf der Tastatur. `eingabe.py`
meldet das dem Server, der beendet RetroPie bzw. lässt `kiosk.py` zurück zur Startseite wechseln.

## 5 · Wer besitzt was

| Aufgabe | Besitzer |
|---|---|
| Chromium starten, steuern, beenden (Seite wechseln, Hinweis einblenden, Adresse fürs Zeitkonto, Bildschirmfoto) | `kiosk/kiosk.py` über die DevTools-**Pipe** (kein offener Port, keine Erweiterung) |
| Desktop-Apps starten und beenden | `kiosk.py`, im Auftrag des Servers |
| RetroPie, Spiel direkt starten, Scraper | systemd-Units, gestartet nur vom Server |
| Zeit, PIN, Katalog, Whitelist, Einstellungen, Familie, Telegram | Server (`server/fernsehfranzi/`) |
| Fernbedienung und Controller | `eingabe/eingabe.py` (genau ein `cec-client`) |
| Chromium-Whitelist als Richtlinie | `system/richtlinie` (root, über sudo, ohne Argumente) |
| Bluetooth | `system/bt-helfer` (root, über sudo, geprüfte MAC-Adresse) |
| Oberfläche, Spielzimmer | `web/` (ES-Module, ohne Build-Schritt) |

## 6 · Ordner im Repository

| Ordner | Inhalt |
|---|---|
| `server/fernsehfranzi/` | Server: Logik (`kern.py`), HTTP (`web.py`), Systemaufrufe (`system.py`) und Bausteine |
| `web/` | Startseite (`index.html`), Elternbereich am TV, Eltern-Seite fürs Handy, Spiele, Schrift, Anleitungen als PDF |
| `kiosk/` | `kiosk.py`: Chromium und Desktop-Apps |
| `eingabe/` | `eingabe.py`: CEC, Controller, Tastatur-Sondertasten → virtuelle Tastatur |
| `fernbedienung/` | Chromium-Erweiterung: Pfeiltasten navigieren auch in Plex und YouTube |
| `system/` | systemd-Units, sudo-Regel, Chromium-Richtlinie, labwc-Kiosk-Konfiguration, hwdb, NetworkManager, RetroArch, Helfer |
| `install/` | `install.sh` und `rollback.sh` (laufen als root auf dem Gerät), ES-Tastatur, RetroPie-Probe |
| `werkzeuge/` | Deploy, Gerätprüfung, RetroPie-Erweiterung, Admin-Konto, PDF- und Emoji-Erzeugung (laufen am PC) |
| `config/beispiel/` | Vorlagen für die nicht versionierte Konfiguration (`config/pi.mk`, `config/einstellungen.js`) |
| `tests/` | Unittests, Oberflächentests (Playwright), Prüfung auf private Daten |
| `docs/` | Diese Dokumentation, Anleitungen als HTML (Quellen der PDFs) |
| `familyhub/` | Version 2.x zum Nachlesen und für den Rückweg (`make v3-rollback`); wird nicht mehr weiterentwickelt |

Nicht versioniert (`.gitignore`): `config/*` außer den Vorlagen, `.local/` (Gerätedaten, Protokolle, private Notizen),
`.venv/`, Laufzeitdaten.

## 7 · Server im Detail

Start: `python3 -m fernsehfranzi` (Arbeitsordner `server/`). `__main__.py` lädt die Daten, baut den `Hub`, startet den
Kiosk-Server auf `127.0.0.1:8765`, bei Bedarf den LAN-Server für die Eltern-Seite und einen Takt (`tick` alle 5 s).

| Modul | Aufgabe |
|---|---|
| `kern.py` | `Hub`: hält Einstellungen, Katalog, Zeitkonto, PIN und Eltern-Sitzungen, entscheidet über Starts, verteilt Aufträge an `kiosk.py`, Bildschirmfoto, Sicherung, Bluetooth, Scraper-Start. Kennt kein HTTP und ruft das Gerät nur über `system` auf. |
| `web.py` | HTTP-Schicht: Routen für Kiosk und Eltern-Seite, Token- und Herkunftsprüfung, Sicherheits-Header (CSP), Durchreichen von Hörbüchern und Wecktönen |
| `system.py` | Alle Systemaufrufe: RetroPie, Ton (`wpctl`), Lautstärke, RetroArch-Netzwerkbefehle, Neustart, Bluetooth, Scraper. In Tests eine Attrappe. |
| `daten.py` | Datenordner, atomares Schreiben, Schema-Version und Migration |
| `katalog.py` | App-Katalog `apps.json`: Prüfung mit verständlichen Fehlern, Vorgabe-Kacheln ohne Adressen |
| `zeitkonto.py` | Tages-Timer (Bildschirmzeit), 4.6: Gaming-Zeit als Teil davon (`zeit: "gaming"`, `gaming_min`) und „nur eigenes Limit“ (`zeit: "frei"` + `limit_min`), App-Limits, Sperrzeiten, Warnungen, Kulanz, Bonus, Leerlauf, Lernzeit verdient Spielzeit |
| `ferien.py` (4.6) | Ferien des Bundeslandes aus `ferien_daten.json` (KMK-Tabellen, mit `werkzeuge/ferien_uebernehmen.py` aus der Ferienliste der Klassenkiste erzeugt – nur lesen), gesetzliche Feiertage (Osterformel), Zusammenführen mit eigenen Einträgen; jährlich nach dem Ferien-Import der Klassenkiste neu erzeugen |
| `design.py` (5.0) | Farben (`DESIGNS`, hell/dunkel) und Ansichten (`ANSICHTEN`: Konsole, Seitenleiste, Karussell) der Startseite, Erlaubtes und Abend-Automatik der Eltern; `fuer_startseite()` liefert das gerade gültige Design |
| `wetter.py` (5.0) | Open-Meteo (ohne Schlüssel) im Hintergrund höchstens alle 30 min; Regen-Satz aus Viertelstunden, Trockenfenster (≥ 1,5 h bei Tageslicht, 0,1 mm / 55 %) wie im Familien Dashboard, Anzieh-Tipp; Ortssuche für die Eltern-Seite |
| `schule.py` (5.0) | Klassenkiste nur lesen (`/api/overview`, `/api/homework/mine`, `/api/messages`, `/api/timetable`) mit der Anmeldung des Kindes (`Hub.klassenkiste_json`); alle 15 min, Neues einmal melden (Merkliste in `schule.json`), Morgen-Check am Abend vor einem Schultag |
| `kinderwelten.py` (5.0) | Öffentliche Schnittstelle der Familienfabrik (`familienfabrik.at/api`, nur lesen, 30 min Zwischenspeicher); HTML wird zu schlichten Absätzen, Bilder nur von `familienfabrik.at/bilder/` über `/api/kinderwelten/bild` |
| `news.py` (5.0, 6.0) | Kinder-News: nur RSS-Adressen, die die Eltern selbst eintragen (höchstens 10, ab Werk keine), reiner Text |
| `klaenge.py` (5.2) | Klang-Archiv: Rezepte aus Tönen mit Klangfarbe und Hüllkurve, daraus WAV (22 kHz, mono, deterministisch), beim Start im Hintergrund vorgerechnet; `system.gong(klang)` spielt sie mit pw-play, `/api/klang?id=` liefert sie zum Probehören |
| `pin.py` | PBKDF2-SHA256 mit Salz, Vergleich in konstanter Zeit, wachsende Sperre nach Fehlversuchen |
| `familie.py` | Nachrichten ans TV, Erinnerungen, Schlafenszeit, Sticker, Bass-Tagebuch |
| `gutschein.py` | Gutschein-Codes (normal: +Minuten, besonders: alles frei), Schutz gegen Raten |
| `wecker.py` | Wecker mit Grenzen der Eltern (frühestens, höchste Lautstärke) |
| `youtube.py` | YouTube-Kategorien der Eltern, Videos und Playlisten für den eigenen Player |
| `hoerbuch.py` | Hörbücher aus einem FileBrowser-Freigabelink (nur lesen, Range-Anfragen) |
| `telegram.py` | Telegram-Bot per Long-Polling: Nachrichten erlaubter Chats ans TV, Antworten des Kindes; 4.3: Kontakte mit Grenzen (Eltern, schreiben, eigene Texte, nur Freizeit), Verlauf für die Eltern; 4.4: Fotos/Sprache/Musik/Videos (getFile, ≤ 20 MB, 7 Tage), Befehle für Eltern, Meldungen an Eltern, Tagesbericht, Bilder senden (sendPhoto, multipart) |
| `nutzung.py` | Nutzungsstatistik je Tag, App und Stunde (62 Tage) |
| `sicherung.py` | Sicherung als ZIP erstellen, prüfen, einspielen (ohne PIN und ohne Telegram-Token) |
| `scraper.py` | Spielbilder aus den freien libretro-thumbnails für EmulationStation (läuft als eigener Dienst) |
| `whitelist.py` | Domainliste aus dem Katalog, Export für Fritzbox und Pi-hole |
| `raum.py` | 4.3: Spielraum für Handy-Spiele – Raum, Spieler, die fünf Spiele (Buzzer, Quizrennen, Malen & Raten, Raumschiff-Rettung, Ton-Treffer); Handys bekommen fertige Ansichten, der Fernseher je Spiel eine eigene |
| `qr.py` | 4.3: QR-Codes (Byte-Modus, Fehlerkorrektur M, Versionen 1–10) als SVG, nur Standardbibliothek |
| `kern.py` (4.4) | dazu: Speicherplatz des Kindes, Album, Fotoalbum (Auswahl, Bildschirmschoner), Bilder teilen, Karaoke (Anmeldung der Klassenkiste über kiosk.py, nur GET auf `/api/playlists/karaoke` und den Musik-Stream) |
| `uebernahme.py` | Einmalige Übernahme aus Version 2.x |

**Schnittstellen.** Alle Routen stehen als Tabellen in `web.py` (`KioskHandler.routen`, `Basis.eltern_routen`; der
LAN-Server `LanHandler` liefert nur die Eltern-Routen).

- Kiosk (`127.0.0.1:8765`): `GET /api/status`, `GET /api/apps`, `POST /api/start`, `POST /api/zurueck`,
  `POST /api/eingabe`, `GET /api/kiosk/auftraege` (lange Abfrage für `kiosk.py`), `/api/retro*`, `/api/hoerbuch/*`,
  `/api/youtube`, `/api/wecker*`, `/api/telegram*`, `/api/zeichnung*` und weitere.
- Eltern (`/api/eltern/*`, am TV und im Heimnetz): `anmelden`, `daten`, `einstellungen`, `apps`, `gutscheine`,
  `statistik`, `bildschirm`, `sicherung`, `sicherung-einspielen`, `bluetooth`, `scraper`, `whitelist` und weitere.

- Spielraum (4.3): am Fernseher `POST /api/raum/oeffnen`, `GET /api/raum/tv`, `POST /api/raum/tv-aktion`,
  `POST /api/raum/schliessen`; für die Handys ein eigener Server (`web.RaumHandler`, Port 8767), der nur
  `/mitspielen`, `/js/mitspielen.js`, `/css/mitspielen.css` und `/api/raum/beitreten|zustand|aktion` kennt. Beitreten
  braucht den Schlüssel aus dem QR-Code oder den Raumcode, danach weist sich jedes Handy mit seinem Geheimnis aus
  (`X-FF-Spieler`). `__main__.py` startet ihn nur, solange ein Raum offen ist und die Eltern Handy-Spiele erlaubt haben.

Aktionen gehen nur per `POST`. Kiosk-Aufrufe brauchen den Token `X-FF-Token`, den der Server beim Ausliefern in die
Startseite schreibt (`__FF_TOKEN__`). Eltern-Aufrufe brauchen eine PIN-Sitzung (`X-FF-Eltern`).

## 8 · Weboberfläche

- `web/index.html` + `web/js/start.js`: Startseite, Navigation, Kacheln, Restzeit, Meldungen, Spielzimmer.
- `web/js/spiele/*.js`: je Spiel ein ES-Modul (Snake, Memory, Drei gewinnt, Echo, Duell, Malen, Musik, Bass,
  Lernen, Sticker, Witze, Gutschein, Wecker, Nachrichten). Gemeinsames in `spiele/kern.js`.
  6.0: `spiele/stimme.js` (Stimmlinie, Stimmgerät, Pegel) für Singen, Ton-Treffer, Rakete und Stimmgerät.
  `gemeinsam.js`: `bild(emoji)` liefert das 3D-Bild aus `web/icons/` (Fluent Emoji, MIT), sonst das Emoji als Text;
  `franzi(stimmung)` zeichnet das Maskottchen (froh, jubel, staunen, schlaf) als festes SVG. Die Hintergrund-Motive
  `web/hintergrund/*.svg` erzeugt `werkzeuge/hintergruende.py`. Bewegung nur mit transform/opacity (Pi 3).
  5.0: Seiten mit Inhalten von außen (`wetter.js`, `schule.js`, `kinderwelten.js`, `news.js`) nutzen die Bausteine aus
  `spiele/seite.js` (Reiter, Liste, Lesefenster); Texte immer als Text, nie als HTML. Farben und Ansichten der Startseite
  setzt `designZeigen()` (`gestalten.js`) als `body[data-thema]`, Klasse `hell` und `body[data-ansicht]`; die hellen
  Designs überschreiben nur die Farb-Variablen von `main`, die Ansichten nur das Layout (Navigation in `markiere()`).
- `web/js/eltern.js`: Elternbereich am TV (PIN). `web/eltern.html` + `eltern-seite.js` + `eltern-handy.js`:
  Eltern-Seite fürs Handy. 6.0: fünf Reiter (`LEISTE`, `REITER`: Heute · Zeit · Inhalte · Familie · Gerät); jeder
  Reiter zeigt seine Bereiche aus `bereiche()` (Symbol, Titel, Status-Chip, Karten) als aufklappbare Zeilen. Adresse
  `#reiter/bereich` mit `history.pushState`, damit die Zurück-Taste des Handys zuklappt; ein einzelner Bereichsname und
  `ALTE_SEITEN` führen alte Lesezeichen weiter. `hilfe()` klappt lange Erklärungen hinter „ℹ️“ ein. Neue Einstellungen
  als Karte in den passenden Bereich hängen, nicht als neue Seite.
- `web/js/youtube.js`, `video.js`, `hoerbuch.js`: eigene Player.
- `web/retro.html`: Platzhalter-Seite, falls Chromium während eines Spiels nicht beendet werden konnte.
- `web/fonts/emoji.ttf`: Ausschnitt aus Noto Color Emoji (das Gerät hat keine Emoji-Schrift). Nach neuen Emojis im Code
  `werkzeuge/emoji_schrift.py` ausführen.
- Animiert werden nur `transform` und `opacity`, kein `blur` (Pi 3).

Kein Framework, kein Build-Schritt: Die Dateien werden so ausgeliefert, wie sie im Repository liegen.

## 9 · Kiosk, Eingabe und RetroPie

**kiosk.py** läuft in der labwc-Sitzung des Kiosk-Benutzers. Es startet Chromium mit eigenem Profil, Kiosk-Schaltern
und `--remote-debugging-pipe`, holt Aufträge vom Server (Seite öffnen, Hinweis einblenden, Desktop-App, Bildschirmfoto
per `Page.captureScreenshot`) und meldet die aktuelle Adresse fürs Zeitkonto. Während RetroPie läuft, beendet es
Chromium (`Browser.close`) und startet es danach neu.

**labwc** hat eine eigene Kiosk-Konfiguration (`system/labwc/rc.xml`, `menu.xml`): keine Menüs und genau ein harmloses
Kürzel. Ohne jedes Kürzel lädt labwc seine Vorgaben, und dann öffnet Strg+Alt+T ein Terminal.

**eingabe.py** läuft als root. Es liest CEC (ein `cec-client`), Controller und Tastatur-Sondertasten und schreibt auf
eine virtuelle Tastatur (uinput). Die Sondertasten einer Tastatur (Zurück, Home, Menü, Medien) legt
`system/udev/90-fernsehfranzi-tastatur.hwdb` im Kernel auf eigene Codes um, damit Chromium sie nicht selbst ausführt.

**RetroPie** läuft als `fernsehfranzi-retropie.service` auf tty8 mit echtem Terminal (`TTYPath`, `StandardInput=tty-force`).
EmulationStation ist im Kiosk-Modus, RetroArch ebenfalls (`kiosk_mode_enable`). Der Server spricht mit RetroArch über
dessen Netzwerkbefehle (`SHOW_MSG`, `SAVE_STATE`, `QUIT`) für Zeitwarnungen und sicheres Beenden.
`system/retroarch/n64-pi3.cfg` enthält sparsame N64-Einstellungen. `werkzeuge/retro_erweitern.sh` installiert C64 und
Amiga nach und richtet Kickstarts, C64-Tasten und CD32-Abbilder ein (`make retro-*`, `make amiga-bibliothek`).

**Scraper:** `fernsehfranzi-scraper.service` (oneshot, Kiosk-Benutzer) ordnet ROM-Dateinamen den Namen der
libretro-thumbnails zu (mit und ohne Artikel, ohne Klammerzusätze), lädt fehlende Bilder und ergänzt die
`gamelist.xml`, ohne Gespielt-Zähler, Favoriten oder eigene Namen anzutasten. Er startet nie, während RetroPie läuft.
Status: `scraper.json` im Datenordner.

## 10 · Datenablage

Code liegt auf dem Gerät in `~/fernsehfranzi/`, Daten in `~/fernsehfranzi-daten/` (änderbar über
`FERNSEHFRANZI_DATEN`). Jede Datei wird atomar geschrieben (temporäre Datei + `os.replace`).

| Datei | Inhalt |
|---|---|
| `einstellungen.json` | Alle Einstellungen der Eltern (mit `schema`-Version), auch Telegram, Wecker, YouTube, Eltern-Seite |
| `apps.json` | App-Katalog (Kacheln) |
| `zeitkonto.json`, `woche.json` | Zustand des Zeitkontos, Wochenübersicht |
| `pin.json` | PIN-Hash und Sperre |
| `familie.json` | Nachrichten, Erinnerungen, Sticker, Bass-Tagebuch |
| `gutscheine.json`, `hoerbuch.json`, `nutzung.json`, `domains.json` | Gutscheine, Hörbuch-Stände, Statistik, gesehene Domains |
| `scraper.json`, `spiel-start.json`, `whitelist-richtlinie.json` | Übergabedateien an Dienste und Helfer |
| `telegram-verlauf.json` | 4.3: Nachrichten je Telegram-Kontakt (die letzten 50, 30 Tage) und wartende Nachrichten; nicht in der Sicherung |
| `medien/` | 4.4: Fotos, Sprachnachrichten, Musik und Videos von Telegram (7 Tage, höchstens 200 MB) |
| `album/` | 4.4: vom Kind übernommene Fotos (zählen zum Speicherplatz, sind in der Sicherung) |
| `zeichnungen/` | Gemalte Bilder |
| `sicherungen/` | Automatische Sicherungen vor dem Einspielen (die letzten drei) |
| `logs/` | `server.log`, `kiosk.log` |

Neue Felder bekommen einen Vorgabewert im Code. Ändert sich der Aufbau, wird `SCHEMA_VERSION` in `daten.py` erhöht und
`migriere` ergänzt (idempotent, protokolliert).

## 11 · Sicherheit und Kinderschutz

- Kiosk-API nur auf `127.0.0.1`, Aktionen nur per POST mit Token und ohne fremde Herkunft.
- Eltern-Seite nur, wenn im Elternbereich eingeschaltet und eine PIN gesetzt ist; jede Eltern-Aktion braucht eine Sitzung.
- Chromium-Richtlinien (`system/chromium/fernsehfranzi.json`): keine Downloads, keine Dateiauswahl, kein Drucken,
  kein Gast- oder Inkognito-Modus, SafeSearch und eingeschränkter YouTube-Modus erzwungen, Mikrofon nur für die Startseite.
  Die Whitelist der Eltern wird als `URLBlocklist ["*"]` + `URLAllowlist` geschrieben.
- Die sudo-Regel erlaubt dem Kiosk-Benutzer nur feste Befehle ohne frei wählbare Argumente.
- Der Telegram-Token wird nie an einen Browser zurückgegeben und ist nicht in Sicherungen enthalten.
- Handy-Spiele: Vorgabe aus; der Zugang fürs Heimnetz läuft nur, solange ein Raum offen ist, liefert nichts außer dem
  Spiel und weist fremde Herkunft bei Aktionen ab. Über Mitspieler wird nichts gespeichert.
- Telegram: Kinder können nur freigegebenen Kontakten schreiben; neue Kontakte starten streng (Grundsatz 6). Befehle
  nimmt der Bot nur von Eltern-Kontakten an. Medien nur mit Recht je Kontakt.
- Karaoke: Das Anmelde-Cookie der Klassenkiste liest kiosk.py über DevTools (`Storage.getCookies`) und gibt es nur an
  den eigenen Server; der Server hält es im Speicher (10 Minuten), nutzt es nur für zwei GET-Anfragen und gibt es nie an
  einen Browser.
- Strenge Content-Security-Policy auf allen Seiten. Bilder aus `blob:` sind erlaubt (Bildschirmfoto, Zeichnungen).

## 12 · Entwicklungsumgebung, Prüfungen und Tests

Voraussetzungen am PC: Linux, Python 3, Node.js (nur für `node --check`), `systemd-analyze`, `visudo`, `rsync`, `ssh`.

```bash
make venv          # einmalig: Playwright, shellcheck, fonttools in .venv
cp config/beispiel/pi.mk config/pi.mk                         # Zielgerät (nicht versioniert)
cp config/beispiel/einstellungen.js config/einstellungen.js   # persönliche Werte (nicht versioniert)
make v3-lokal      # Server lokal: http://127.0.0.1:8765/ (Daten in /tmp/fernsehfranzi-lokal)
make check         # statische Prüfungen
make test          # Unittests und Oberflächentests
```

Lokal bedient man die Startseite mit Pfeilen, Enter, Ziffern und Esc.

**`make check`:** Python kompilieren, JavaScript (`node --check`, ES-Module), shellcheck ab Warnung, systemd-Units
(`systemd-analyze verify`), sudoers (`visudo -c`), JSON, Suche nach privaten Daten (`tests/pruefe_privat.py`:
private IP-Adressen, mDNS-Namen, E-Mail-Adressen, Werte aus `config/` und Wörter aus `.local/private-woerter.txt`).

**`make test`:** alle `tests/test_*.py`. Server- und Logiktests laufen mit Testuhr und Attrappen für das System.
Oberflächentests starten einen echten Chromium (Playwright), auch in Handy-Größe und ohne Emoji-Schrift wie am Gerät.
Die Handy-Spiele werden mit Fernseher und Handys in echten Browsern durchgespielt (`tests/test_raum_web.py`, Ton-Treffer
mit dem Test-Mikrofon von Chromium); die Lesbarkeit der QR-Codes prüft OpenCV, falls vorhanden (`tests/test_raum.py`).
Bildschirmfotos der Tests landen in `.local/bildschirm/`.

Tests rufen nie Endpunkte mit echter Wirkung auf das System auf (siehe Lehre 13).

**Anleitungen:** Quellen in `docs/anleitung/*.html` (Anleitung, Kinder-Anleitung, Handbuch mit Umschlag,
Kurzanleitung), PDFs mit `make anleitung` (braucht `pdftotext`, `pdfunite` und `pdfinfo` aus poppler-utils: Das
Handbuch wird zweimal gedruckt, damit das Inhaltsverzeichnis die echten Seitenzahlen bekommt; die Kurzanleitung muss auf
eine Seite passen, sonst bricht das Werkzeug ab). Ein Test prüft, dass das PDF zur
aktuellen HTML-Fassung passt.

**Bildschirmfotos:** `make bildschirmfotos` erzeugt die Bilder in `docs/bilder/` (README, Handbuch) mit Beispieldaten in
einem temporären Ordner, ohne persönliche Werte (die Spielraum-Adresse ist ein Beispiel). Port 8765 muss frei sein.

## 13 · Ausliefern auf das Gerät

Alle Befehle laufen am PC im Projektordner. `config/pi.mk` enthält `PI_HOST` (Kiosk-Benutzer@Gerät) und `ADMIN_HOST`.

| Befehl | Wirkung |
|---|---|
| `make v3-plan` | Trockenlauf: was übertragen würde (ändert nichts) |
| `make v3-deploy` | `check` + `test`, zwei Rückfragen, Sicherung, Code per rsync, `install/install.sh` als root über das Admin-Konto, Protokoll in `.local/` |
| `make v3-pruefen` | Nachprüfung nach dem Neustart: Dienste, Ports, Version, Kiosk-Härtung; grün = Wartungsmodus aus (löscht nur `wartung.json`) |
| `make v3-wartung-aus` | 5.3: Wartungsmodus am Fernseher von Hand beenden |
| `make v3-rollback SICHERUNG=/var/backups/fernsehfranzi/v3-…` | Zurück auf den Stand vor einem Deploy |
| `make pi-check-vor` / `pi-check-nach` | Zustand lesen und vergleichen (ändert nichts) |
| `make admin-plan` / `admin-einrichten` / `admin-zurueck` | Admin-Konto anlegen, volles sudo des Kiosk-Benutzers entfernen bzw. zurückgeben |
| `make retro-plan` / `retro-erweitern` | C64 und Amiga in RetroPie nachinstallieren |
| `make retro-einrichten-plan` / `retro-einrichten` | Kickstarts, C64-Tasten und Schnelllauf, CD32 |
| `make amiga-bibliothek-plan` / `amiga-bibliothek` | Fehlende Bibliothek für Amiberry (apt) |

Ablauf: `make v3-deploy` → Gerät sauber neu starten (`sudo systemctl reboot`, nicht den Strom ziehen) →
`make v3-pruefen` → am Fernseher kurz durchklicken. Während des Deploys kein Retro-Spiel laufen lassen. Seit 5.3 setzt der Deploy nach der zweiten Bestätigung `wartung.json` in den Datenordner (`ab` = jetzt + 10 s Vorwarnung, `bis` = + 45 min): Countdown in der Ecke, danach Warnbildschirm ohne Tasten; `make v3-pruefen` löscht die Datei, wenn es grün ist.

`install/install.sh` ist wiederholbar und sichert alles, was es ersetzt, nach `/var/backups/fernsehfranzi/v3-<zeit>/`.
`install/rollback.sh` stellt das wieder her. Die Daten in `~/fernsehfranzi-daten` werden nie übertragen und nie gelöscht.

**Release:** `VERSION` erhöhen, `CHANGELOG.md` ergänzen, Anleitungen und PDFs nachziehen (`make anleitung`),
`make check` und `make test` grün, ausliefern, am Gerät prüfen, erst dann taggen (`v<VERSION>`).

## 14 · Konventionen

- **Sprache:** Code-Bezeichner, Kommentare, Texte und Commit-Nachrichten auf Deutsch. Kindertexte freundlich und kurz.
- **Python:** nur Standardbibliothek, reine Bausteine mit einsetzbarer Uhr, Systemzugriffe nur über `system.py`.
- **JavaScript:** ES-Module ohne Framework, kein Build-Schritt.
- **Shell:** `set -euo pipefail`, shellcheck-sauber, gefährliche Schritte mit zwei Rückfragen.
- **Units:** nicht ausführbar markiert, Platzhalter `@BENUTZER@` und `@HOME@` setzt `install.sh` ein.
- **Commits:** eine Version oder eine abgeschlossene Änderung je Commit, Nachricht beginnt mit der Version
  (z. B. `4.2.0: …`).

## 15 · Lehren aus der Entwicklung

Jede dieser Lehren hat einmal einen Fehlschlag gekostet.

| # | Lehre |
|---|---|
| 1 | RetroArch (RetroPie, Pi 3) zeichnet über KMS und braucht ein echtes Terminal. Ein X11/XWayland-Fenster bei laufendem Desktop startet ES, aber keine Spiele. Nie `SDL_VIDEODRIVER` erzwingen. |
| 2 | ES als Kindprozess eines Dienstes hat kein Terminal (`runcommand.sh: /dev/tty`). Konsolen-Apps brauchen `TTYPath` + `StandardInput=tty-force`. |
| 3 | `pkill chromium-browser` trifft nie: Prozessnamen sind auf 15 Zeichen begrenzt. Den eigenen Prozess verwalten. |
| 4 | `amixer cset numid=3 1` stellte nicht die Klinke ein, sondern die Lautstärke auf fast null. Systembefehle nie blind übernehmen, Wirkung am Gerät prüfen. |
| 5 | Der `chromium-browser`-Wrapper leitet neue Fenster an eine alte Sitzung weiter. Eigenes `--user-data-dir`. |
| 6 | Zwei `cec-client` gleichzeitig blockieren den Adapter. Genau ein Besitzer für CEC. |
| 7 | `sudo -n` ohne passende Regel scheitert still. Rückgabewerte prüfen und sichtbar melden. |
| 8 | Marken-Dateien in `/tmp` brauchen einen Ablauf-Schutz, sonst bedeutet ein Absturz einen schwarzen Bildschirm bis zum Neustart. |
| 9 | Handänderungen am Gerät ohne Versionierung ergeben einen unbekannten Stand. Eine Quelle der Wahrheit: Git + `VERSION`, ausliefern nur über `make`. |
| 10 | Eine alte Doku beschrieb X11/Openbox, das Gerät lief mit labwc/Wayland. Fakten am Gerät nachsehen. |
| 11 | GET-Endpunkte mit Wirkung plus CORS `*`: Jede geöffnete Webseite kann sie auslösen. Aktionen nur per POST mit Token. |
| 12 | Ein Desktop mit Taskleiste hinter dem Kiosk blitzt bei jedem Wechsel auf und ist ein Ausweg für das Kind. Die Kiosk-Sitzung startet nur, was sie braucht. |
| 13 | Ein Server-Test, der einen Endpunkt mit Systemwirkung aufrief, beendete jeden Chromium des Entwicklungsrechners. Tests nie gegen echte Systemaufrufe laufen lassen. |
| 14 | Systemdateien waren am Gerät von Hand geändert. Vor jedem Eingriff den Ist-Zustand sichern und vergleichen. |
| 15 | labwc nimmt ohne eigene `rc.xml` seine Vorgaben: Strg+Alt+T öffnete ein Terminal im Kiosk. Eigene `rc.xml` mit mindestens einem harmlosen Kürzel. |
| 16 | Chromium mit Startseite im Hintergrund kostete während eines N64-Spiels rund 600 MiB RAM und Swap auf der SD-Karte. Erst messen (`free`, `ps`, `vcgencmd get_throttled`), dann ändern. Seit 4.2 ist Chromium während Retro-Spielen ganz aus. |
| 17 | „Die LAN-Verbindung“ war WLAN mit Energiesparen. Netzprobleme am Gerät messen (`ip`, `iw`, Download-Test). |
| 18 | Sondertasten einer Tastatur führt Chromium selbst aus (Verlauf zurück, leere Seite, Kontextmenü). Im Kernel per hwdb umlegen, nicht im Browser abfangen. |
| 19 | Den Strom zu ziehen statt sauber neu zu starten, ließ frisch geschriebene Dateien verloren gehen. `install.sh` schreibt mit `sync` und repariert Reste. |
| 20 | Amiberry startet CD-Abbilder nur als `.cue`, nicht aus einem ZIP, und braucht `libserialport0`. |
| 21 | `replaceChildren(null)` und `append(null)` schreiben das Wort „null“ auf die Seite. Leere Teile vorher herausfiltern. |
| 22 | Eine Klasse wie `ansicht buzzer` am Rahmen färbt ihn wie den Buzzer-Knopf. Ansichts-Klassen eindeutig benennen (`ansicht-buzzer`). |
| 23 | Handy-Browser geben Mikrofon (und Kamera) nur über HTTPS frei. Mikrofon-Spiele laufen deshalb über das USB-Mikro am Fernseher. |
| 24 | `.overlay-inhalt` legt Teile nebeneinander und zentriert sie. Höhere Inhalte (Karaoke) ragen sonst über den Kopf; für Spalten-Ansichten `flex-direction: column`. |

## 16 · Bekannte Grenzen und Ideen

**Grenzen von 5.0.0**

- Videos puffern über WLAN gelegentlich. Abhilfe: LAN-Kabel oder Powerline, eventuell feste 720p.
- Anspruchsvolle N64-Spiele laufen auf dem Pi 3 nur knapp flüssig. Nächster Schritt wäre zram statt Swap auf der SD-Karte.
- Amiga CD32 braucht die CD32-Kickstart-ROMs, sie liegen dem Projekt nicht bei.
- Die Installationsanleitung (`docs/INSTALLATION.md`) ist auf einem ganz frischen Gerät noch nicht durchgespielt.
- Handy-Spiele: Handy-Mikrofone gehen im Heimnetz ohne HTTPS nicht; bei vielen Handys auf dem Pi 3 noch ungemessen.
- Wetter, Schule, Kinderwelten und Kinder-News brauchen Internet am Pi. Ohne Netz bleibt der letzte Stand stehen; die
  Schul-Seite braucht zusätzlich die Anmeldung in der Klassenkiste-Kachel (Cookie aus dem Kiosk-Profil, nur im Speicher).
- Die Kinder-News bringen keine eigenen Quellen mit, nur die RSS-Adressen der Eltern (http/https, höchstens 10).

**Ideen für später**

- Web-Benachrichtigungen von Lernseiten in die Nachrichten übernehmen (erst prüfen, ob Web-Push im Pi-Chromium ankommt).
- Temperaturgrenze erst nach Einbau eines Lüfters und nur im offiziell erlaubten Rahmen anpassen.
- Pi-Kamera (z. B. für Videotelefonie mit der Familie).
- Kinder-Smartwatch (Xplora): nur Nachrichten an die Uhr, über die inoffizielle Schnittstelle – erst als Versuch.
- Lesen üben mit dem Mikrofon auf Basis von „Geschichten & Rätsel“, Countdown bis Ferien und Geburtstag.
- Prüfungen bei jedem Push (CI).
