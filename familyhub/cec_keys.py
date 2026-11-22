#!/usr/bin/env python3
"""FernsehFranzi v2 - CEC-Fernbedienung (weitgehend unverändert aus v1).

Verbindet die TV-Fernbedienung (Samsung Anynet+ / HDMI-CEC) mit dem
System: Tastendrucke des Fernsehers werden von cec-client gemeldet und
als echte Tastaturereignisse über ein virtuelles Eingabegerät (uinput)
 eingespeist. Chromium und EmulationStation merken davon nichts - sie
sehen nur eine normale Tastatur.

Laeuft als systemd-Dienst (familyhub-cec.service) als root: cec-client
braucht Zugriff auf den VideoCore-IO-Treiber, uinput auf /dev/uinput.

Neu in v2:
  - Logging nach logs/cec.log (v1 schrieb die leere cec.log nie)
  - Absicherung einzelner Tastaturereignisse gegen Fehler
  - Beim Beenden wird sauber freigegeben

Neu in v2.2 (Steuerung):
  - ALT+F4 (EXIT) wird von der Startseite abgefangen, solange ein
    Spielzimmer-Spiel offen ist: Dann schliesst es nur das Spiel,
    nicht den ganzen Kiosk. Auf der Startseite und in Plex/Kavita
    bleibt EXIT = Fenster schliessen wie bisher.

Tastenbelegung (CEC-Code -> Taste):
  0x00 OK/Enter        0x01-0x04 Pfeiltasten
  0x20-0x29 Ziffern 0-9 (Hub: 1-4 Apps, 5-0 Spielzimmer)
  0x0D EXIT = Alt+F4   (schliesst das oberste Fenster und dient so
                        als "Zurueck" aus Plex/Kavita; auf dem Hub
                        selbst startet der Kiosk durch den Supervisor
                        einfach neu)
  0x44 PLAY  = Medientaste   0x45 STOP  = Escape (Zurueck)
  0x46 PAUSE = P (Pause)     0x48/0x49 Rueck-/Vorlauf (Medientasten)

Seit 2.5:
  - ROT/GRUEN schalten den Ton direkt ueber den Hub-Server (POST /api/audio) -
    ueberall, auch in Plex und im Spiel. Der Server spielt einen
    Bestaetigungston auf dem neuen Ausgang, die Startseite zeigt es an.
  - EXIT bei laufendem RetroPie (nur EmulationStation) beendet die
    systemd-Unit; die Startseite ist danach sofort wieder da.

Der Controller braucht diese Bruecke nicht: Chromium liest ihn direkt
ueber die Gamepad-API (siehe index.html, Abschnitt "Controller").
"""
import json
import logging
import os
import re
import subprocess
import threading
import urllib.error
import urllib.request

from evdev import UInput, ecodes as e

HUB_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(HUB_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "cec.log")

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("cec")

KEY_MAP = {
    0x00: e.KEY_ENTER,
    0x01: e.KEY_UP,
    0x02: e.KEY_DOWN,
    0x03: e.KEY_LEFT,
    0x04: e.KEY_RIGHT,

    0x20: e.KEY_0,
    0x21: e.KEY_1,
    0x22: e.KEY_2,
    0x23: e.KEY_3,
    0x24: e.KEY_4,
    0x25: e.KEY_5,
    0x26: e.KEY_6,
    0x27: e.KEY_7,
    0x28: e.KEY_8,
    0x29: e.KEY_9,

    0x44: e.KEY_PLAY,
    0x45: e.KEY_ESC,   # STOP = Zurueck (v2.1, Spielzimmer)
    0x46: e.KEY_P,     # PAUSE = Pause in Snake (v2.1)
    0x48: e.KEY_REWIND,
    0x49: e.KEY_FASTFORWARD,

}

# Farbtasten (seit 2.5 direkt an den Server): ROT = Ton HDMI, GRUEN = Ton Klinke.
TON_TASTEN = {0x72: "hdmi", 0x73: "klinke"}
SERVER = "http://127.0.0.1:8765"
RETROPIE_UNIT = "fernsehfranzi-retropie.service"

# TV (Adresse 0) schickt uns (Adresse 4) Tastendrucke 04:44:xx
# und Tastenloslassen 04:45:xx (Debug-Stufe 8 von cec-client).
PRESS_RE = re.compile(r">>\s*04:44:([0-9a-fA-F]{2})")
RELEASE_RE = re.compile(r">>\s*04:45")


def send(ui, *events):
    """Tastaturereignis absetzen und synchronisieren."""
    for event in events:
        ui.write(e.EV_KEY, event[0], event[1])
    ui.syn()


def laeuft(*pgrep_args):
    """True, wenn pgrep einen Treffer findet."""
    return subprocess.run(["pgrep", *pgrep_args],
                          capture_output=True).returncode == 0


def ton_umschalten(ziel):
    """Ton ueber den Hub-Server umschalten (im Hintergrund, Fehler ins Log)."""
    def senden():
        anfrage = urllib.request.Request(
            SERVER + "/api/audio", data=json.dumps({"ziel": ziel}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(anfrage, timeout=10) as antwort:
                log.info("Ton: %s (%s)", ziel, antwort.status)
        except urllib.error.HTTPError as fehler:
            log.warning("Ton-Umschaltung %s fehlgeschlagen: %s %s", ziel, fehler.code,
                        fehler.read()[:200])
        except (urllib.error.URLError, OSError) as fehler:
            log.warning("Ton-Umschaltung %s: Server nicht erreichbar (%s)", ziel, fehler)
    threading.Thread(target=senden, daemon=True).start()


def retropie_unit_aktiv():
    return subprocess.run(["systemctl", "is-active", "--quiet", RETROPIE_UNIT]).returncode == 0


def exit_taste(ui):
    """EXIT/ZURUECK der Fernbedienung (v2.4).

    Entscheidet nach Lage, damit es nie vom Fensterfokus abhaengt:
      - RetroArch laeuft (Spiel)       -> Spiel beenden, zurueck in ES
      - anderer Emulator (runcommand)  -> Alt+F4 an das Fenster
      - nur EmulationStation (Unit)    -> Unit beenden, Startseite ist sofort da
      - sonst (Hub, Plex, Kavita)      -> Alt+F4, wie bisher
    """
    if laeuft("-x", "retroarch"):
        log.info("EXIT: RetroArch wird beendet.")
        subprocess.run(["pkill", "-x", "retroarch"])
    elif laeuft("-f", "runcommand.sh"):
        log.info("EXIT: Emulator laeuft - Alt+F4.")
        alt_f4(ui)
    elif retropie_unit_aktiv():
        log.info("EXIT: RetroPie (EmulationStation) wird beendet.")
        ergebnis = subprocess.run(["systemctl", "stop", "--no-block", RETROPIE_UNIT],
                                  capture_output=True, text=True)
        if ergebnis.returncode != 0:
            log.error("EXIT: Stoppen fehlgeschlagen: %s", ergebnis.stderr.strip())
    elif laeuft("-x", "emulationstation"):
        # Nur Prozesse, die so heissen (-x) - nicht jede Befehlszeile, in der das Wort
        # vorkommt (-f traf beim Probelauf auch dessen ssh/sudo-Huelle).
        log.info("EXIT: EmulationStation wird beendet.")
        subprocess.run(["pkill", "-x", "emulationstation"])
    else:
        alt_f4(ui)


def alt_f4(ui):
    send(ui, (e.KEY_LEFTALT, 1), (e.KEY_F4, 1))
    send(ui, (e.KEY_F4, 0), (e.KEY_LEFTALT, 0))


def main():
    ui = UInput(name="FamilyHub Remote", version=1)

    process = subprocess.Popen(
        ["cec-client", "-d", "8", "-t", "p", "-o", "FamilyHub"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    log.info("FamilyHub bei Anynet+ angemeldet (cec-client PID %s).",
             process.pid)

    pressed_key = None

    try:
        for line in process.stdout:
            match = PRESS_RE.search(line)

            if match:
                code = int(match.group(1), 16)

                if code == 0x0D:
                    exit_taste(ui)
                    continue

                if code in TON_TASTEN:
                    ton_umschalten(TON_TASTEN[code])
                    continue

                key = KEY_MAP.get(code)

                if key is None:
                    log.info("Unbekannte CEC-Taste 0x%02x (nicht belegt).", code)

                if key is not None:
                    if pressed_key is not None:
                        send(ui, (pressed_key, 0))

                    send(ui, (key, 1))
                    pressed_key = key

            elif RELEASE_RE.search(line):
                if pressed_key is not None:
                    send(ui, (pressed_key, 0))
                    pressed_key = None

    except KeyboardInterrupt:
        pass
    finally:
        if pressed_key is not None:
            send(ui, (pressed_key, 0))
        process.terminate()
        ui.close()
        log.info("CEC-Bruecke beendet.")


if __name__ == "__main__":
    main()
