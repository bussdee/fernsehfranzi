#!/usr/bin/env python3
"""FernsehFranzi 3.0 - Eingabe (ersetzt cec_keys.py). Läuft als root (fernsehfranzi-eingabe.service).

Ein Besitzer für alle Eingabegeräte (docs/ENTWICKLUNG.md, „Wer besitzt was“):
  * TV-Fernbedienung über HDMI-CEC (genau ein cec-client)
  * Controller (Xbox-360 per Kabel, 8BitDo per Bluetooth, jeder Linux-Gamepad)
und ein virtuelles Tastaturgerät (uinput), das Chromium, EmulationStation und Desktop-Apps sehen.

Modi (aus GET /api/status des Servers):
  Hub/App   Controller -> Tasten (Pfeile, OK, Zurück ...), Fernbedienung -> Tasten
  Retro     RetroPie läuft: Controller bleibt nativ (nichts übersetzt), Fernbedienung -> Tasten für ES

Immer:
  EXIT (auf Webseiten schon kurz), EXIT lang (>= 1,5 s) oder Guide-Taste -> Zur Startseite
  BLAU oder Back+Start lang              -> Elternbereich
  ROT / GRÜN                             -> Ton Fernseher / Klinke (im Farben-Echo: Farbtasten F9/F10)
  GELB, dann ↑ ↓ (4 s lang)              -> Lautstärke lauter/leiser (seit 3.2.1; die TV-Tasten regeln nur den Fernseher)
  Controller: Back halten + ↑ ↓          -> Lautstärke
  Pfeiltasten                            -> immer Navigation (nie Lautstärke/Spulen, so gewünscht)

Seit 3.1:
  * Fernseher aus per CEC ("standby"), wenn der Server es verlangt (Schlafenszeit, Gute-Nacht, Eltern);
    an ("an": "on 0" + "as" = unser Eingang) für den Wecker (3.5)
  * Zweiter Controller (Spiele zu zweit): Steuerkreuz -> W A S D, A -> F, B -> G, Start -> P

Seit 4.1 (Tastaturen, z. B. iPazzPort per Bluetooth - gelesen ohne exklusiven Zugriff, Tasten gehen normal weiter):
  Lautstärke +/- und Stumm -> Server (mit der Höchstgrenze der Eltern), auch im Retro-Spiel
  Home (per hwdb auf F20)  -> Startseite (im laufenden Spiel: Spiel beenden, wie EXIT)
  Menü (per hwdb auf F22)  -> Elternbereich (PIN)
  Zurück (hwdb -> Escape) und Suche (hwdb -> F21, Nachrichten) wertet die Startseite selbst aus.
"""
import json
import logging
import os
import re
import select
import subprocess
import threading
import time
import urllib.error
import urllib.request

SERVER = "http://127.0.0.1:8765"
LANG_S = 1.5
WIEDERHOLUNG_ERST_S, WIEDERHOLUNG_S = 0.40, 0.12
STICK_SCHWELLE = 0.55

log = logging.getLogger("eingabe")

# ---------------------------------------------------------------- Fernbedienung (CEC)
# TV (Adresse 0) -> wir (4): Tastendruck 04:44:xx, Loslassen 04:45 (cec-client -d 8)
DRUCK = re.compile(r">>\s*04:44:([0-9a-fA-F]{2})")
LOS = re.compile(r">>\s*04:45")
CEC_TASTEN = {
    0x00: "ENTER", 0x01: "UP", 0x02: "DOWN", 0x03: "LEFT", 0x04: "RIGHT",
    0x20: "0", 0x21: "1", 0x22: "2", 0x23: "3", 0x24: "4", 0x25: "5", 0x26: "6", 0x27: "7", 0x28: "8", 0x29: "9",
    0x44: "PLAY", 0x45: "ESC", 0x46: "P", 0x48: "REWIND", 0x49: "FASTFORWARD",
}
CEC_EXIT, CEC_BLAU, CEC_ROT, CEC_GRUEN, CEC_GELB = 0x0D, 0x71, 0x72, 0x73, 0x74


class Logik:
    """Reine Entscheidungslogik (ohne Geräte) - in Tests mit Testuhr und Attrappen prüfbar.

    ``aus`` bekommt Aktionen: ("taste", NAME) · ("kombi", [NAMEN]) · ("server", pfad, daten)
    · ("retroarch_beenden",).
    """

    def __init__(self, aus, uhr=time.monotonic):
        self.aus, self.uhr = aus, uhr
        self.status = {"running": False, "aktuell": None}
        self.cec_nr = None            # zuletzt gesehener CEC-Befehl des Servers
        self.lautstaerke_bis = 0.0    # GELB gedrückt: so lange regeln ↑ ↓ die Lautstärke
        self.exit_seit = None
        self.exit_lang_erledigt = False

    # ---------------- Lage
    def retro(self):
        return bool(self.status.get("running"))

    def im_echo(self):
        return self.status.get("aktuell") == "spiel-echo" and not self.retro()

    # ---------------- Fernbedienung
    def cec_druck(self, code):
        if code == CEC_EXIT:
            if self.exit_seit is None:
                self.exit_seit, self.exit_lang_erledigt = self.uhr(), False
            return
        if code in (CEC_ROT, CEC_GRUEN, CEC_GELB, CEC_BLAU) and self.im_echo():
            return self.aus(("taste", {CEC_ROT: "F9", CEC_GRUEN: "F10", CEC_GELB: "F11", CEC_BLAU: "F12"}[code]))
        if code == CEC_GELB:
            self.lautstaerke_bis = self.uhr() + 4
            return self.aus(("server", "/api/lautstaerke", {"richtung": "lauter"}))   # GELB allein: einmal lauter
        if self.lautstaerke_bis > self.uhr() and code in (0x01, 0x02):
            self.lautstaerke_bis = self.uhr() + 4
            return self.aus(("server", "/api/lautstaerke", {"richtung": "lauter" if code == 0x01 else "leiser"}))
        self.lautstaerke_bis = 0.0
        if code == CEC_ROT:
            return self.aus(("server", "/api/audio", {"ziel": "hdmi"}))
        if code == CEC_GRUEN:
            return self.aus(("server", "/api/audio", {"ziel": "klinke"}))
        if code == CEC_BLAU:
            return self.aus(("server", "/api/zurueck", {"eltern": True}))
        name = CEC_TASTEN.get(code)
        if name:
            self.aus(("halte", name))
        else:
            log.info("Unbekannte CEC-Taste 0x%02x", code)

    def cec_los(self):
        if self.exit_seit is not None:
            lang = self.exit_lang_erledigt or self.uhr() - self.exit_seit >= LANG_S
            self.exit_seit = None
            if not lang:
                self.exit_kurz()
            elif not self.exit_lang_erledigt:
                self.zur_startseite()
            return
        self.aus(("loslassen",))

    def neuer_status(self, status):
        """Status vom Server übernehmen; einen neuen CEC-Befehl (z. B. Fernseher aus) weitergeben."""
        self.status = status
        cec = status.get("cec") or {}
        if self.cec_nr is not None and cec.get("nr", 0) > self.cec_nr and cec.get("befehl"):
            self.aus(("cec", cec["befehl"]))
        self.cec_nr = cec.get("nr", 0)

    def takt(self):
        """Regelmäßig aufrufen: EXIT lang auch ohne Loslassen erkennen (Fernseher schickt es spät)."""
        if self.exit_seit is not None and not self.exit_lang_erledigt and self.uhr() - self.exit_seit >= LANG_S:
            self.exit_lang_erledigt = True
            self.zur_startseite()

    def zur_startseite(self):
        log.info("Zur Startseite (lang EXIT / Guide).")
        self.aus(("server", "/api/zurueck", {}))

    def exit_kurz(self):
        """EXIT kurz - je nach Lage. Auf Webseiten (Plex …) wie in 2.x: zurück zum Launcher
        (seit 3.1.1; „eine Ebene zurück“ ist dort STOP)."""
        aktuell = self.status.get("aktuell")
        log.info("EXIT kurz (aktuell: %s).", aktuell)
        if self.retro():
            if self.status.get("retroarch"):
                return self.aus(("retroarch_beenden",))
            return self.zur_startseite()
        if aktuell in (None, "") or str(aktuell).startswith("spiel-"):
            return self.aus(("taste", "ESC"))          # Startseite/Spielzimmer: Spiel schließen
        return self.zur_startseite()                   # Webseite, Desktop-App: zurück zum Launcher

    # ---------------- Controller (nur Hub/App)
    def pad_knopf(self, knopf, gedrueckt, gehalten, spieler=1):
        """knopf: A B X Y START BACK GUIDE LB RB; gehalten = Menge aktuell gedrückter Knöpfe."""
        if knopf == "GUIDE" and gedrueckt and not self.retro():
            return self.zur_startseite()
        if knopf == "GUIDE" and gedrueckt and self.retro() and not self.status.get("retroarch"):
            return self.zur_startseite()     # Spieleliste (EmulationStation, Kiosk-Modus): Xbox-Taste = Startseite
        if self.retro():
            return
        if spieler == 2:                       # zweiter Controller: eigene Tasten (Spiele zu zweit)
            ziel = {"A": "F", "B": "G", "START": "P"}.get(knopf)
            if gedrueckt and ziel:
                self.aus(("taste", ziel))
            return
        if gedrueckt and {"BACK", "START"} <= gehalten:
            return       # Kombination läuft (Elternbereich nach LANG_S, siehe pad_takt)
        if not gedrueckt:
            return
        ziel = {"A": "ENTER", "B": "ESC", "X": "SPACE", "Y": "M", "START": "P",
                "LB": "REWIND", "RB": "FASTFORWARD"}.get(knopf)   # BACK allein: nichts (Kombination)
        if ziel:
            self.aus(("taste", ziel))

    # ---------------- Tastatur (4.1)
    def tastatur(self, name):
        """name: VOLUMEUP VOLUMEDOWN MUTE F20 (Home) F22 (Menü). Nur Tastendruck, keine Wiederholung (außer Lautstärke)."""
        if name in ("VOLUMEUP", "VOLUMEDOWN", "MUTE"):
            richtung = {"VOLUMEUP": "lauter", "VOLUMEDOWN": "leiser", "MUTE": "stumm"}[name]
            return self.aus(("server", "/api/lautstaerke", {"richtung": richtung}))
        if name == "F20":
            if self.retro() and self.status.get("retroarch"):
                return self.aus(("retroarch_beenden",))
            return self.zur_startseite()
        if name == "F22":
            return self.aus(("server", "/api/zurueck", {"eltern": True}))

    def pad_richtung(self, richtung, spieler=1, gehalten=frozenset()):
        if richtung in ("UP", "DOWN") and "BACK" in gehalten:       # Back + ↑ ↓ = Lautstärke (auch im Spiel)
            return self.aus(("server", "/api/lautstaerke", {"richtung": "lauter" if richtung == "UP" else "leiser"}))
        if not self.retro() and richtung:
            if spieler == 2:
                richtung = {"UP": "W", "DOWN": "S", "LEFT": "A", "RIGHT": "D"}[richtung]
            self.aus(("taste", richtung))


# ---------------------------------------------------------------- Geräte (nur auf dem Pi)
class Ausgabe:
    """uinput-Tastatur + Server-Aufrufe."""

    def __init__(self, token_datei):
        from evdev import UInput, ecodes
        self.e = ecodes
        self.ui = UInput(name="FernsehFranzi Eingabe", version=3)
        self.token_datei = token_datei
        self.gehalten = None
        self.letzte_meldung = 0.0
        self.gedrueckt = []           # Tastennamen seit der letzten Meldung (Lern-Check, aktive Minuten)
        self.lock = threading.Lock()
        self.cec_client = None        # laufender cec-client (stdin für Befehle)

    def code(self, name):
        return getattr(self.e, "KEY_" + name)

    def __call__(self, aktion):
        art = aktion[0]
        if art in ("taste", "halte"):
            with self.lock:
                self.gedrueckt.append(aktion[1])
        try:
            if art == "taste":
                self._druck([self.code(aktion[1])])
            elif art == "kombi":
                self._druck([self.code(n) for n in aktion[1]])
            elif art == "halte":
                self._loslassen()
                self.ui.write(self.e.EV_KEY, self.code(aktion[1]), 1)
                self.ui.syn()
                self.gehalten = self.code(aktion[1])
            elif art == "loslassen":
                self._loslassen()
            elif art == "server":
                threading.Thread(target=self.server, args=aktion[1:], daemon=True).start()
            elif art == "retroarch_beenden":
                for name in EMULATOREN:
                    subprocess.run(["pkill", "-x", name], check=False)
            elif art == "cec" and aktion[1] == "an" and self.cec_client and self.cec_client.stdin:
                log.info("CEC: Fernseher an (Wecker).")
                self.cec_client.stdin.write("on 0\n")           # einschalten ...
                self.cec_client.stdin.write("as\n")             # ... und auf unseren HDMI-Eingang schalten
                self.cec_client.stdin.flush()
            elif art == "cec" and aktion[1] == "standby" and self.cec_client and self.cec_client.stdin:
                log.info("CEC: Fernseher aus (standby).")
                self.cec_client.stdin.write("standby 0\n")
                self.cec_client.stdin.flush()
        except Exception:   # noqa: BLE001 - eine Taste darf die Eingabe nie beenden
            log.exception("Aktion %s fehlgeschlagen", aktion)
        self.eingabe_melden()

    def _druck(self, codes):
        for c in codes:
            self.ui.write(self.e.EV_KEY, c, 1)
        self.ui.syn()
        for c in reversed(codes):
            self.ui.write(self.e.EV_KEY, c, 0)
        self.ui.syn()

    def _loslassen(self):
        if self.gehalten is not None:
            self.ui.write(self.e.EV_KEY, self.gehalten, 0)
            self.ui.syn()
            self.gehalten = None

    def token(self):
        try:
            with open(self.token_datei) as f:
                return f.read().strip()
        except OSError:
            return ""

    def server(self, pfad, daten=None, methode="POST"):
        anfrage = urllib.request.Request(SERVER + pfad, method=methode,
                                         data=None if methode == "GET" else json.dumps(daten or {}).encode(),
                                         headers={"Content-Type": "application/json", "X-FF-Token": self.token()})
        try:
            with urllib.request.urlopen(anfrage, timeout=5) as antwort:
                return json.loads(antwort.read() or b"{}")
        except (urllib.error.URLError, OSError, ValueError) as fehler:
            log.warning("Server %s %s: %s", methode, pfad, fehler)
            return None

    def eingabe_melden(self):
        """Höchstens alle 5 s: welche Tasten gedrückt wurden (Server zählt aktive Minuten, Lern-Check)."""
        jetzt = time.monotonic()
        if jetzt - self.letzte_meldung > 5:
            self.letzte_meldung = jetzt
            with self.lock:
                tasten, self.gedrueckt = self.gedrueckt[:60], []
            threading.Thread(target=self.server, args=("/api/eingabe", {"tasten": tasten}), daemon=True).start()


def cec_schleife(logik, ausgabe):
    while True:
        prozess = subprocess.Popen(["cec-client", "-d", "8", "-t", "p", "-o", "FernsehFranzi"],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, bufsize=1)
        ausgabe.cec_client = prozess
        log.info("Fernbedienung: cec-client gestartet (PID %s).", prozess.pid)
        for zeile in prozess.stdout:
            treffer = DRUCK.search(zeile)
            if treffer:
                logik.cec_druck(int(treffer.group(1), 16))
            elif LOS.search(zeile):
                logik.cec_los()
        log.warning("cec-client beendet (Code %s) - Neustart in 3 s.", prozess.wait())
        time.sleep(3)


def ist_controller(geraet, ecodes):
    if geraet.name.startswith(("FernsehFranzi", "FamilyHub")):
        return False
    tasten = geraet.capabilities().get(ecodes.EV_KEY, [])
    return ecodes.BTN_SOUTH in tasten or ecodes.BTN_GAMEPAD in tasten


def controller_schleife(logik, ausgabe):
    """Alle Controller lesen (ohne exklusiven Zugriff - ES/RetroArch lesen parallel)."""
    from evdev import InputDevice, ecodes, list_devices
    knoepfe = {ecodes.BTN_SOUTH: "A", ecodes.BTN_EAST: "B", ecodes.BTN_NORTH: "X", ecodes.BTN_WEST: "Y",
               ecodes.BTN_START: "START", ecodes.BTN_SELECT: "BACK", ecodes.BTN_MODE: "GUIDE",
               ecodes.BTN_TL: "LB", ecodes.BTN_TR: "RB"}
    dpad_knoepfe = {ecodes.BTN_DPAD_UP: "UP", ecodes.BTN_DPAD_DOWN: "DOWN",
                    ecodes.BTN_DPAD_LEFT: "LEFT", ecodes.BTN_DPAD_RIGHT: "RIGHT"}
    geraete, gesehen = {}, 0.0
    zustand = {}   # fd -> {"gehalten": set, "achsen": {}, "richtung": None, "naechste": 0, "kombi_seit": None}

    def richtung_aus(z):
        a = z["achsen"]
        x = a.get("hx", 0) or (a.get("x", 0) if abs(a.get("x", 0)) > STICK_SCHWELLE else 0)
        y = a.get("hy", 0) or (a.get("y", 0) if abs(a.get("y", 0)) > STICK_SCHWELLE else 0)
        for k in ("UP", "DOWN", "LEFT", "RIGHT"):
            if k in z["gehalten"]:
                return k
        if abs(x) >= abs(y) and x:
            return "RIGHT" if x > 0 else "LEFT"
        if y:
            return "DOWN" if y > 0 else "UP"
        return None

    while True:
        if time.monotonic() - gesehen > 3:          # neue Controller (z. B. Bluetooth) finden
            gesehen = time.monotonic()
            for pfad in list_devices():
                if pfad in (g.path for g in geraete.values()):
                    continue
                try:
                    g = InputDevice(pfad)
                    if ist_controller(g, ecodes):
                        geraete[g.fd] = g
                        belegt = {z["spieler"] for z in zustand.values()}
                        zustand[g.fd] = {"gehalten": set(), "achsen": {}, "richtung": None, "naechste": 0.0,
                                         "kombi_seit": None, "spieler": 1 if 1 not in belegt else 2,
                                         "abs": {c: g.absinfo(c) for c in (ecodes.ABS_X, ecodes.ABS_Y)
                                                 if c in dict(g.capabilities().get(ecodes.EV_ABS, []))}}
                        log.info("Controller erkannt: %s (%s)", g.name, pfad)
                    else:
                        g.close()
                except OSError:
                    pass
        bereit, _, _ = select.select(list(geraete.values()), [], [], 0.05)
        jetzt = time.monotonic()
        for g in bereit:
            z = zustand[g.fd]
            try:
                ereignisse = list(g.read())
            except OSError:
                log.info("Controller getrennt: %s", g.name)
                del geraete[g.fd], zustand[g.fd]
                continue
            for ev in ereignisse:
                if ev.type == ecodes.EV_KEY and ev.code in knoepfe:
                    k = knoepfe[ev.code]
                    (z["gehalten"].add if ev.value else z["gehalten"].discard)(k)
                    z["kombi_seit"] = jetzt if {"BACK", "START"} <= z["gehalten"] else None
                    logik.pad_knopf(k, bool(ev.value), z["gehalten"], z["spieler"])
                    ausgabe.eingabe_melden()
                elif ev.type == ecodes.EV_KEY and ev.code in dpad_knoepfe:
                    (z["gehalten"].add if ev.value else z["gehalten"].discard)(dpad_knoepfe[ev.code])
                elif ev.type == ecodes.EV_ABS:
                    if ev.code == ecodes.ABS_HAT0X:
                        z["achsen"]["hx"] = ev.value
                    elif ev.code == ecodes.ABS_HAT0Y:
                        z["achsen"]["hy"] = ev.value
                    elif ev.code in z["abs"]:
                        info = z["abs"][ev.code]
                        mitte = (info.max + info.min) / 2
                        wert = (ev.value - mitte) / max(1, (info.max - info.min) / 2)
                        z["achsen"]["x" if ev.code == ecodes.ABS_X else "y"] = wert
        for z in zustand.values():
            r = richtung_aus(z)
            if r != z["richtung"]:
                z["richtung"] = r
                if r:
                    logik.pad_richtung(r, z["spieler"], z["gehalten"])
                    ausgabe.eingabe_melden()
                    z["naechste"] = jetzt + WIEDERHOLUNG_ERST_S
            elif r and jetzt >= z["naechste"]:
                logik.pad_richtung(r, z["spieler"], z["gehalten"])
                z["naechste"] = jetzt + WIEDERHOLUNG_S
            if z["kombi_seit"] and jetzt - z["kombi_seit"] >= LANG_S:
                z["kombi_seit"] = None
                log.info("Back+Start lang: Elternbereich.")
                ausgabe(("server", "/api/zurueck", {"eltern": True}))


TASTATUR_TASTEN = ("VOLUMEUP", "VOLUMEDOWN", "MUTE", "F20", "F22")
LAUT_WIEDERHOLUNG_S = 0.25


def ist_tastatur(geraet, ecodes):
    if geraet.name.startswith(("FernsehFranzi", "FamilyHub")):
        return False
    tasten = geraet.capabilities().get(ecodes.EV_KEY, [])
    return ecodes.KEY_ENTER in tasten or ecodes.KEY_VOLUMEUP in tasten


def tastatur_schleife(logik, ausgabe):
    """4.1: Tastaturen mitlesen (nicht exklusiv) - nur Lautstärke, Stumm, Home, Menü wertet eingabe.py aus."""
    from evdev import InputDevice, ecodes, list_devices
    codes = {getattr(ecodes, "KEY_" + n): n for n in TASTATUR_TASTEN}
    geraete, gesehen, zuletzt = {}, 0.0, 0.0
    while True:
        if time.monotonic() - gesehen > 3:
            gesehen = time.monotonic()
            bekannt = {g.path for g in geraete.values()}
            for pfad in list_devices():
                if pfad in bekannt:
                    continue
                try:
                    g = InputDevice(pfad)
                    if ist_tastatur(g, ecodes) and not ist_controller(g, ecodes):
                        geraete[g.fd] = g
                        log.info("Tastatur erkannt: %s (%s)", g.name, pfad)
                    else:
                        g.close()
                except OSError:
                    pass
        bereit, _, _ = select.select(list(geraete.values()), [], [], 0.2)
        for g in bereit:
            try:
                ereignisse = list(g.read())
            except OSError:
                log.info("Tastatur getrennt: %s", g.name)
                del geraete[g.fd]
                continue
            for ev in ereignisse:
                name = codes.get(ev.code) if ev.type == ecodes.EV_KEY else None
                if not name or ev.value == 0:
                    continue
                if ev.value == 2:              # gehalten: nur die Lautstärke wiederholt, gebremst
                    if name not in ("VOLUMEUP", "VOLUMEDOWN") or time.monotonic() - zuletzt < LAUT_WIEDERHOLUNG_S:
                        continue
                zuletzt = time.monotonic()
                logik.tastatur(name)
                ausgabe.eingabe_melden()


# Laufende Emulatoren (seit 3.2.2 auch Amiberry für den Amiga): EXIT beendet nur das Spiel, nicht RetroPie.
EMULATOREN = ("retroarch", "amiberry")


def emulator_laeuft(lauf=subprocess.run):
    return any(lauf(["pgrep", "-x", name], capture_output=True).returncode == 0 for name in EMULATOREN)


def status_schleife(logik, ausgabe):
    while True:
        status = ausgabe.server("/api/status", methode="GET")
        if status:
            status["retroarch"] = emulator_laeuft()
            logik.neuer_status(status)
        for _ in range(10):
            logik.takt()
            time.sleep(0.1)
        if ausgabe.gedrueckt:
            ausgabe.eingabe_melden()      # Rest der letzten Tastendrücke nicht liegen lassen


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    benutzer_home = os.environ.get("FERNSEHFRANZI_HOME", "/home/family")
    token = os.path.join(os.environ.get("FERNSEHFRANZI_DATEN", os.path.join(benutzer_home, "fernsehfranzi-daten")),
                         "kiosk-token")
    ausgabe = Ausgabe(token)
    logik = Logik(ausgabe)
    threading.Thread(target=status_schleife, args=(logik, ausgabe), daemon=True).start()
    threading.Thread(target=controller_schleife, args=(logik, ausgabe), daemon=True).start()
    threading.Thread(target=tastatur_schleife, args=(logik, ausgabe), daemon=True).start()
    cec_schleife(logik, ausgabe)


if __name__ == "__main__":
    main()
