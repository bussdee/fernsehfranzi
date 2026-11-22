#!/usr/bin/env python3
"""FernsehFranzi - Hub-Server (seit 2.5: RetroPie auf der Konsole).

Laeuft als systemd-Dienst (familyhub-server.service) unter dem Kiosk-Benutzer und
horcht nur auf 127.0.0.1:8765.

Endpunkte:
  GET  /status              - JSON: Version, laeuft RetroPie, aktueller Ton-Ausgang
  POST /api/retropie        - RetroPie starten (systemd-Unit fernsehfranzi-retropie.service)
  POST /api/audio           - Ton umschalten, JSON {"ziel": "hdmi" | "klinke"}
  GET  /api/zeichnungen     - gespeicherte Kinderzeichnungen auflisten (JSON)
  GET  /zeichnung/<datei>   - eine Zeichnung als PNG ausliefern
  POST /api/zeichnung       - neue Zeichnung aus dem Malen-Modus speichern

Seit 2.5 (Hotfix RetroPie):
  - RetroPie laeuft auf einer eigenen Konsole (tty8) als systemd-Unit, nie mehr als
    X11-Fenster. Der Server startet nur die Unit (eng begrenzte sudo-Regel) und
    beendet keinen Chromium mehr: Die Startseite laeuft auf ihrer Konsole weiter
    und ist nach dem Spielen sofort wieder da.
  - Aktionen nur per POST. Anfragen mit fremder Herkunft (Origin einer Webseite,
    z. B. aus Plex) werden abgewiesen; erlaubt sind die Startseite (file://,
    Origin "null") und lokale Dienste ohne Origin (Fernbedienung).
  - Ton-Umschaltung spielt einen kurzen Bestaetigungston auf dem neuen Ausgang;
    /status meldet die Umschaltung, damit die Startseite sie anzeigen kann.
  - Die Version kommt aus der Datei VERSION (einzige Versionsquelle).
"""
import base64
import binascii
import json
import logging
import math
import os
import re
import struct
import subprocess
import tempfile
import threading
import time
import wave
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---------------------------------------------------------------- Konfiguration
HUB_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(HUB_DIR, "logs")
SERVER_LOG = os.path.join(LOG_DIR, "server.log")
HOST, PORT = "127.0.0.1", 8765

RETROPIE_UNIT = "fernsehfranzi-retropie.service"
SYSTEMCTL = "/usr/bin/systemctl"

# Kinderzeichnungen aus dem Malen-Modus (v2.1).
ZEICHNUNGEN_DIR = os.path.join(HUB_DIR, "zeichnungen")
ZEICHNUNGEN_NAME = re.compile(r"[A-Za-z0-9._-]+\.png\Z")
ZEICHNUNG_MAX_BYTES = 5 * 1024 * 1024
JSON_MAX_BYTES = 4096


def lies_version():
    """VERSION neben server.py (Geraet) oder im Repository darueber (Entwicklung)."""
    for pfad in (os.path.join(HUB_DIR, "VERSION"), os.path.join(HUB_DIR, "..", "VERSION")):
        try:
            with open(pfad) as datei:
                return datei.read().strip()
        except OSError:
            continue
    return "unbekannt"


VERSION = lies_version()

# ---------------------------------------------------------------- Logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(SERVER_LOG),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("familyhub")


def sitzungs_umgebung():
    """XDG_RUNTIME_DIR + D-Bus-Adresse der Benutzersitzung (fuer PipeWire)."""
    runtime = "/run/user/%d" % os.getuid()
    if not os.path.isdir(runtime):
        return {}
    return {
        "XDG_RUNTIME_DIR": runtime,
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=" + runtime + "/bus",
    }


# ---------------------------------------------------------------- RetroPie
def retropie_zustand():
    """(laeuft, startmarke) der RetroPie-Unit.

    startmarke ist der Zeitpunkt des letzten Starts (ActiveEnterTimestampMonotonic,
    0 = seit dem Booten nie gelaufen). Die Startseite erkennt daran ein Spiel auch
    dann, wenn sie waehrenddessen nicht nachgefragt hat (z. B. gedrosselt).
    """
    try:
        antwort = subprocess.run(
            [SYSTEMCTL, "show", RETROPIE_UNIT, "-p", "ActiveState",
             "-p", "ActiveEnterTimestampMonotonic"],
            capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired) as fehler:
        log.warning("RetroPie-Status nicht lesbar: %s", fehler)
        return False, 0
    werte = dict(zeile.split("=", 1) for zeile in antwort.stdout.splitlines() if "=" in zeile)
    laeuft = werte.get("ActiveState", "") in ("active", "activating", "reloading")
    try:
        marke = int(werte.get("ActiveEnterTimestampMonotonic", "0"))
    except ValueError:
        marke = 0
    return laeuft, marke


def retropie_aktiv():
    """True, wenn die RetroPie-Unit laeuft oder gerade startet."""
    return retropie_zustand()[0]


def retropie_starten():
    """Unit starten. Rueckgabe (ok, kindgerechte Meldung). Fehler werden geloggt."""
    if retropie_aktiv():
        return True, "RetroPie läuft schon."
    befehl = ["sudo", "-n", SYSTEMCTL, "start", "--no-block", RETROPIE_UNIT]
    try:
        antwort = subprocess.run(befehl, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as fehler:
        log.error("RetroPie-Start fehlgeschlagen: %s", fehler)
        return False, "RetroPie startet gerade nicht. Bitte Mama oder Papa holen."
    if antwort.returncode != 0:
        log.error("RetroPie-Start fehlgeschlagen (Code %d): %s", antwort.returncode,
                  (antwort.stderr or antwort.stdout).strip())
        return False, "RetroPie startet gerade nicht. Bitte Mama oder Papa holen."
    log.info("RetroPie-Start angefordert (%s).", RETROPIE_UNIT)
    return True, "RetroPie startet ..."


# ---------------------------------------------------------------- Ton-Ausgang
# Seit v2.4: Der Hub ruehrt Lautstaerke und Ausgang NICHT mehr beim Spielstart an
# (v1/v2 stellten per amixer die Lautstaerke auf 1/65536 - stumm). Stattdessen
# schaltet die Fernbedienung (ROT = HDMI, GRUEN = Klinke) den PipeWire-Standard-
# Ausgang um; die letzte Wahl merkt sich audio.txt und wird beim Start gesetzt.
AUDIO_DATEI = os.path.join(HUB_DIR, "audio.txt")
# Seit 2.5: pactl (ueber pipewire-pulse) statt wpctl. Auf dem Geraet ist wpctl 0.4.13
# mit PipeWire 1.2.7 kombiniert, "wpctl set-default" stuerzt dort ab (rc=-11, schon in
# v2.4 - am 21.11. im Log gefunden). pactl spricht dieselbe PipeWire-Instanz an.
PACTL = "pactl"
LAUTSTAERKE = re.compile(r"(\d+)%")


def pactl(*argumente, timeout=5):
    """pactl in der Benutzersitzung, Ausgabe auf Englisch (stabil zum Auswerten)."""
    return subprocess.run(
        [PACTL, *argumente], capture_output=True, text=True, timeout=timeout,
        env={**os.environ, **sitzungs_umgebung(), "LC_ALL": "C"},
    )


def audio_senken():
    """Ausgaenge aus 'pactl list short sinks': [(id, name)]. name ist der Knotenname."""
    antwort = pactl("list", "short", "sinks")
    if antwort.returncode != 0:
        raise RuntimeError("pactl list fehlgeschlagen: %s" % antwort.stderr.strip())
    senken = []
    for zeile in antwort.stdout.splitlines():
        teile = zeile.split("\t")
        if len(teile) >= 2 and teile[0].strip().isdigit():
            senken.append((int(teile[0]), teile[1].strip()))
    return senken


def lautstaerke_prozent(name):
    """Hoechster Kanal in Prozent, None wenn nicht lesbar."""
    antwort = pactl("get-sink-volume", name)
    werte = [int(w) for w in LAUTSTAERKE.findall(antwort.stdout)] if antwort.returncode == 0 else []
    return max(werte) if werte else None


def audio_setzen(ziel):
    """ziel 'hdmi' oder 'klinke'. Rueckgabe (ok, Meldung, Name)."""
    try:
        senken = audio_senken()
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as fehler:
        log.warning("Audio: %s", fehler)
        return False, "Audio-System (PipeWire) nicht erreichbar.", ""
    hdmi = [s for s in senken if "hdmi" in s[1].lower()]
    klinke = [s for s in senken if "hdmi" not in s[1].lower()]
    kandidaten = hdmi if ziel == "hdmi" else klinke
    if not kandidaten:
        log.warning("Audio: kein Ausgang fuer %s gefunden: %s", ziel, senken)
        return False, "Kein Ausgang '%s' gefunden." % ziel, ""
    _sink_id, name = kandidaten[0]
    try:
        ergebnis = pactl("set-default-sink", name)
        if ergebnis.returncode != 0:
            log.warning("Audio: set-default-sink %s fehlgeschlagen (rc=%s): %s", name,
                        ergebnis.returncode, (ergebnis.stderr or ergebnis.stdout).strip())
            return False, "Umschalten fehlgeschlagen.", name
        stumm = pactl("set-sink-mute", name, "0")
        if stumm.returncode != 0:
            log.warning("Audio: Stummschaltung nicht aufhebbar: %s", stumm.stderr.strip())
        vol = lautstaerke_prozent(name)
        if vol is not None and vol < 15:
            pactl("set-sink-volume", name, "50%")
    except (OSError, subprocess.TimeoutExpired) as fehler:
        log.warning("Audio: pactl fehlgeschlagen: %s", fehler)
        return False, "Umschalten fehlgeschlagen.", name
    try:
        with open(AUDIO_DATEI, "w") as datei:
            datei.write(ziel)
    except OSError as fehler:
        log.warning("Audio-Wahl nicht speicherbar: %s", fehler)
    log.info("Audio: Standard-Ausgang = %s (%s)", ziel, name)
    with audio_lock:
        audio_stand["ziel"] = ziel
        audio_stand["nummer"] += 1
    bestaetigungston(name)
    return True, "", name


def audio_wiederherstellen():
    """Beim Start die letzte Wahl setzen (PipeWire braucht nach dem Boot etwas)."""
    try:
        with open(AUDIO_DATEI) as datei:
            ziel = datei.read().strip()
    except OSError:
        return
    if ziel not in ("hdmi", "klinke"):
        return
    for _ in range(30):
        ok, _meldung, _name = audio_setzen(ziel)
        if ok:
            return
        time.sleep(2)
    log.warning("Audio: letzte Wahl (%s) konnte nicht gesetzt werden.", ziel)


# ---------------------------------------------------------------- Bestaetigungston
audio_lock = threading.Lock()
audio_stand = {"ziel": None, "nummer": 0}   # nummer zaehlt jede Umschaltung (Anzeige)
TON_DATEI = os.path.join(tempfile.gettempdir(), "fernsehfranzi-ton-%d.wav" % os.getuid())


def ton_datei():
    """Kurzer Zweiklang (0,35 s) als WAV, einmal erzeugt."""
    if os.path.exists(TON_DATEI):
        return TON_DATEI
    rate = 22050
    proben = bytearray()
    for frequenz, dauer in ((660, 0.15), (990, 0.2)):
        anzahl = int(rate * dauer)
        for i in range(anzahl):
            huelle = min(1.0, i / 400.0, (anzahl - i) / 400.0)
            wert = int(9000 * huelle * math.sin(2 * math.pi * frequenz * i / rate))
            proben += struct.pack("<h", wert)
    with wave.open(TON_DATEI, "wb") as datei:
        datei.setnchannels(1)
        datei.setsampwidth(2)
        datei.setframerate(rate)
        datei.writeframes(bytes(proben))
    return TON_DATEI


def bestaetigungston(ziel_name):
    """Ton auf dem gewaehlten Ausgang (Knotenname) abspielen - im Hintergrund, Fehler nur loggen."""
    def spielen():
        try:
            antwort = subprocess.run(["pw-play", "--target", str(ziel_name), ton_datei()],
                                     capture_output=True, text=True, timeout=10,
                                     env={**os.environ, **sitzungs_umgebung()})
            if antwort.returncode != 0:
                log.warning("Bestaetigungston fehlgeschlagen: %s", antwort.stderr.strip())
        except (OSError, subprocess.TimeoutExpired) as fehler:
            log.warning("Bestaetigungston fehlgeschlagen: %s", fehler)
    threading.Thread(target=spielen, daemon=True).start()


class Handler(BaseHTTPRequestHandler):

    def kopf_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")

    def send_bytes(self, data, content_type, code=200):
        self.send_response(code)
        self.kopf_cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, objekt, code=200):
        self.send_bytes(json.dumps(objekt).encode("utf-8"), "application/json; charset=utf-8", code)

    def send_leer(self, code):
        self.send_response(code)
        self.kopf_cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def herkunft_erlaubt(self):
        """Startseite (file:// -> 'null') und lokale Dienste ohne Origin, sonst nichts."""
        origin = self.headers.get("Origin")
        return origin is None or origin == "null"

    def lies_json(self, grenze=JSON_MAX_BYTES):
        try:
            laenge = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            laenge = 0
        if laenge <= 0 or laenge > grenze:
            raise ValueError("Inhalt fehlt oder ist zu gross")
        daten = json.loads(self.rfile.read(laenge).decode("utf-8"))
        if not isinstance(daten, dict):
            raise ValueError("JSON-Objekt erwartet")
        return daten

    def do_OPTIONS(self):
        # CORS-Voranfrage fuer die file://-Kioskseite
        self.send_response(204)
        self.kopf_cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def zeichnungen_auflisten(self):
        try:
            namen = [
                name for name in os.listdir(ZEICHNUNGEN_DIR)
                if ZEICHNUNGEN_NAME.fullmatch(name)
            ]
        except FileNotFoundError:
            return []
        namen.sort(
            key=lambda name: os.path.getmtime(os.path.join(ZEICHNUNGEN_DIR, name)),
            reverse=True,
        )
        return namen[:60]

    def do_GET(self):
        if self.path == "/status":
            with audio_lock:
                ton = dict(audio_stand)
            laeuft, marke = retropie_zustand()
            self.send_json({"version": VERSION, "running": laeuft, "retropie_start": marke,
                            "ton": ton["ziel"], "ton_nummer": ton["nummer"]})
            return

        if self.path == "/api/zeichnungen":
            eintraege = [
                {"datei": name, "url": "/zeichnung/" + name}
                for name in self.zeichnungen_auflisten()
            ]
            self.send_json({"zeichnungen": eintraege})
            return

        if self.path.startswith("/zeichnung/"):
            name = os.path.basename(self.path[len("/zeichnung/"):])
            pfad = os.path.join(ZEICHNUNGEN_DIR, name)
            if not ZEICHNUNGEN_NAME.fullmatch(name) or not os.path.isfile(pfad):
                self.send_leer(404)
                return
            try:
                with open(pfad, "rb") as datei:
                    self.send_bytes(datei.read(), "image/png")
            except OSError as error:
                log.error("Zeichnung %s nicht lesbar: %s", name, error)
                self.send_json({"ok": False, "fehler": "Datei nicht lesbar."}, 500)
            return

        self.send_leer(404)

    def do_POST(self):
        if self.path not in ("/api/retropie", "/api/audio", "/api/zeichnung"):
            self.send_json({"ok": False, "fehler": "Unbekannter Pfad."}, 404)
            return
        if not self.herkunft_erlaubt():
            log.warning("Anfrage von fremder Herkunft abgewiesen: %s %s",
                        self.headers.get("Origin"), self.path)
            self.send_json({"ok": False, "fehler": "Nicht erlaubt."}, 403)
            return

        if self.path == "/api/retropie":
            ok, meldung = retropie_starten()
            self.send_json({"ok": ok, "meldung": meldung}, 200 if ok else 500)
            return

        if self.path == "/api/audio":
            try:
                ziel = self.lies_json().get("ziel")
            except (ValueError, UnicodeDecodeError):
                ziel = None
            if ziel not in ("hdmi", "klinke"):
                self.send_json({"ok": False, "fehler": "ziel muss hdmi oder klinke sein."}, 400)
                return
            ok, meldung, name = audio_setzen(ziel)
            self.send_json({"ok": ok, "ziel": ziel, "name": name, "fehler": meldung},
                           200 if ok else 500)
            return

        try:
            laenge = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            laenge = 0

        if laenge <= 0 or laenge > ZEICHNUNG_MAX_BYTES:
            self.send_json({"ok": False, "fehler": "Bild fehlt oder ist zu gross."}, 400)
            return

        try:
            daten = json.loads(self.rfile.read(laenge).decode("utf-8"))
            bild = daten.get("bild", "")
            praefix = "data:image/png;base64,"
            if not bild.startswith(praefix):
                raise ValueError("Kein PNG-Bild")
            png = base64.b64decode(bild[len(praefix):], validate=True)
        except (ValueError, KeyError, json.JSONDecodeError, binascii.Error) as error:
            log.warning("Ungueltige Zeichnung abgewiesen: %s", error)
            self.send_json({"ok": False, "fehler": "Das Bild konnte nicht gelesen werden."}, 400)
            return

        os.makedirs(ZEICHNUNGEN_DIR, exist_ok=True)
        stamm = datetime.now().strftime("zeichnung-%Y%m%d-%H%M%S")
        name = stamm + ".png"
        anhang = 2
        while os.path.exists(os.path.join(ZEICHNUNGEN_DIR, name)):
            name = "%s-%d.png" % (stamm, anhang)
            anhang += 1

        try:
            with open(os.path.join(ZEICHNUNGEN_DIR, name), "wb") as datei:
                datei.write(png)
        except OSError as error:
            log.error("Zeichnung nicht speicherbar: %s", error)
            self.send_json({"ok": False, "fehler": "Speichern schlug fehl."}, 500)
            return

        log.info("Zeichnung gespeichert: %s (%d KB)", name, len(png) // 1024)
        self.send_json({"ok": True, "datei": name})

    def log_message(self, fmt, *args):
        # Zugriffe ins eigene Log, nicht auf stderr. Die regelmaessige Status-Abfrage
        # der Startseite (alle 2 s) bleibt draussen, Fehler werden trotzdem geloggt.
        if self.path == "/status" and args[1:2] == ("200",):
            return
        log.info("%s - %s", self.client_address[0], fmt % args)


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    log.info("FamilyHub-Server %s auf http://%s:%s", VERSION, HOST, PORT)
    threading.Thread(target=audio_wiederherstellen, daemon=True).start()
    server = ReusableThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Server beendet.")
