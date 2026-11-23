# FernsehFranzi auf einem neuen Raspberry Pi einrichten

Diese Anleitung führt von einer leeren SD-Karte bis zum fertigen Kinder-Fernseher. Sie beschreibt den Weg, auf dem
FernsehFranzi entwickelt wurde. **Auf einem ganz frisch aufgesetzten Gerät ist sie noch nicht vollständig
durchgespielt** – bitte jeden Schritt prüfen und bei Abweichungen die Entwickler-Dokumentation
([ENTWICKLUNG.md](ENTWICKLUNG.md)) zu Rate ziehen. Zeitbedarf: etwa zwei Stunden, mit RetroPie länger.

## 1 · Was man braucht

| Teil | Hinweis |
|---|---|
| Raspberry Pi 3B+ (oder neuer) | mit Netzteil (5 V, 2,5 A), Kühlkörper, besser Gehäuse mit Lüfter |
| microSD-Karte | mindestens 16 GB, besser 32 GB oder mehr (Retro-Spiele, Bilder) |
| Fernseher mit HDMI-CEC | bei Samsung „Anynet+“, bei LG „SimpLink“, bei Sony „Bravia Sync“ – im Fernseher einschalten |
| Linux-PC | zum Ausliefern: Python 3, `make`, `ssh`, `rsync`, `git` |
| Optional | Xbox-Controller (Kabel), Bluetooth-Tastatur mit Touchpad, USB-Mikrofon (Bass-Ecke, Singen, Ton-Treffer), Bluetooth-Kopfhörer |
| Optional im Heimnetz | Plex, Kavita, FileBrowser (Hörbücher, Video-Ordner, Wecktöne), ein Telegram-Bot |

## 2 · Raspberry Pi OS aufsetzen

1. Mit dem **Raspberry Pi Imager** „Raspberry Pi OS (mit Desktop)“ in der Fassung **Bookworm** auf die Karte schreiben.
   In den Einstellungen des Imagers gleich festlegen:
   - Gerätename (z. B. „fernseher“),
   - Benutzer und Passwort – das wird der **Kiosk-Benutzer**, unter dem FernsehFranzi läuft,
   - WLAN (oder später ein LAN-Kabel, das ist für Videos besser),
   - **SSH einschalten** (Anmeldung mit Passwort genügt für den Anfang).
2. Pi am Fernseher starten, einmal anmelden und alles aktualisieren:
   ```bash
   sudo apt update && sudo apt full-upgrade -y
   ```
3. `sudo raspi-config`:
   - *System Options → Boot / Auto Login → Desktop Autologin* (der Kiosk-Benutzer meldet sich selbst an),
   - *Advanced Options → Wayland → labwc* (FernsehFranzi ist für labwc gebaut),
   - danach neu starten.
4. Benötigte Pakete (meist schon vorhanden, sonst nachinstallieren):
   ```bash
   sudo apt install -y chromium cec-utils rsync pipewire-pulse bluez
   ```
   Auf älteren Fassungen heißt das Browser-Paket `chromium-browser`.

## 3 · Optional: RetroPie für Retro-Spiele

RetroPie wird mit dem offiziellen Installationsskript eingerichtet (siehe retropie.org.uk, „Manual Installation“ für
Raspberry Pi OS): *Basic install*, danach die gewünschten Emulatoren. FernsehFranzi startet EmulationStation selbst auf
einer eigenen Konsole – der Autostart von RetroPie wird **nicht** eingeschaltet.

C64 und Amiga lassen sich später vom PC aus nachinstallieren (`make retro-plan`, `make retro-erweitern`,
`make retro-einrichten`). ROMs, Kickstart- und BIOS-Dateien gehören nicht zu FernsehFranzi.

## 4 · Am PC: FernsehFranzi holen und das Gerät eintragen

```bash
git clone https://github.com/bussdee/fernsehfranzi.git
cd fernsehfranzi
make venv
cp config/beispiel/pi.mk config/pi.mk
```

In `config/pi.mk` den Kiosk-Benutzer und das Gerät eintragen: `PI_HOST := BENUTZER@GERAET`. Für `GERAET` den
Gerätenamen mit der Endung „.local“ oder die IP-Adresse des Pi nehmen (`config/pi.mk` bleibt privat und wird nie
hochgeladen). Dann den SSH-Schlüssel des PCs aufs Gerät bringen:

```bash
ssh-copy-id BENUTZER@GERAET
```

Zur Probe, ohne etwas zu verändern:

```bash
make check
make test
make pi-check-vor
make v3-plan
```

## 5 · Ausliefern

```bash
make v3-deploy
```

Das Werkzeug prüft zuerst alles, zeigt den Plan und fragt **zweimal** nach. Dann überträgt es den Code nach
`~/fernsehfranzi`, richtet Dienste, Kiosk-Sitzung, Chromium-Richtlinien und die enge sudo-Regel ein (vorher wird alles
gesichert) und schreibt ein Protokoll nach `.local/`. Anschließend das Gerät sauber neu starten:

```bash
ssh -t BENUTZER@GERAET sudo systemctl reboot
```

Nach ein bis zwei Minuten:

```bash
make v3-pruefen
```

### Volles sudo des Kiosk-Benutzers entfernen (empfohlen)

Frisch aufgesetzt darf der Kiosk-Benutzer alles als root, ohne Passwort. Für den Betrieb wird das auf ein eigenes
Admin-Konto mit Passwort umgestellt:

```bash
make admin-plan
make admin-einrichten
```

Ab dann laufen alle Updates über das Admin-Konto; sein Passwort wird bei jedem Deploy eingetippt.

## 6 · Erste Inbetriebnahme am Fernseher

1. Im Fernseher HDMI-CEC einschalten und den richtigen HDMI-Eingang wählen. Die Fernbedienung bedient jetzt den Pi.
2. **BLAU** drücken und die **Eltern-PIN** festlegen (zweimal eingeben).
3. Im Elternbereich „Eltern-Seite einschalten“ wählen und die angezeigte Adresse am Handy öffnen (gleiches WLAN).
4. Auf der Eltern-Seite: Zeiten und Sperrzeiten (Regeln), Adressen für Plex, Bücher, Gute Nacht und Video-Ordner
   (Apps), YouTube-Videos, auf Wunsch Telegram und Handy-Spiele (Mehr).
5. Ton mit **ROT** (Fernseher) oder **GRÜN** (Klinke) wählen.

Alles Weitere erklärt das Handbuch (`web/handbuch.pdf`, auch auf der Eltern-Seite).

## 7 · Prüfliste

- [ ] Nach dem Einschalten erscheint die Startseite (kein Desktop, keine Taskleiste)
- [ ] Fernbedienung: Pfeile, OK, STOP, EXIT funktionieren
- [ ] Strg+Alt+T (mit Tastatur) öffnet **kein** Terminal
- [ ] BLAU öffnet den Elternbereich, die PIN funktioniert
- [ ] Ton über ROT/GRÜN, lauter/leiser mit GELB + Pfeilen
- [ ] Eine Web-App (z. B. Plex) öffnet sich, EXIT führt zurück
- [ ] Retro-Spiele starten und enden sauber (falls RetroPie installiert)
- [ ] Eltern-Seite am Handy erreichbar
- [ ] `make v3-pruefen` ist grün

## 8 · Zurück

`make v3-deploy` druckt am Ende die Zeile zum Zurückrollen, z. B.
`make v3-rollback SICHERUNG=/var/backups/fernsehfranzi/v3-…`. Die Daten in `~/fernsehfranzi-daten` bleiben dabei
erhalten.
