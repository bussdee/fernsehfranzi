"""Systemaufrufe des Servers (RetroPie, Ton, RetroArch, Neustart).

Alles, was das Gerät verändert, läuft hier durch - geprüft und geloggt (Grundsatz 15, docs/ENTWICKLUNG.md).
Die Klasse lässt sich in Tests durch eine Attrappe ersetzen.
"""
import logging
import math
import os
import re
import socket
import struct
import subprocess
import threading
import tempfile
import time
import wave

log = logging.getLogger("fernsehfranzi.system")

SYSTEMCTL = "/usr/bin/systemctl"
RETROPIE_UNIT = "fernsehfranzi-retropie.service"
SPIEL_UNIT = "fernsehfranzi-spiel.service"          # 3.1: ein bestimmtes Spiel direkt starten
RETROARCH_PORT = 55355          # Netzwerkbefehle, nur localhost (network_cmd_enable)
LAUTSTAERKE = re.compile(r"(\d+)%")


def sitzungs_umgebung():
    runtime = "/run/user/%d" % os.getuid()
    if not os.path.isdir(runtime):
        return {}
    return {"XDG_RUNTIME_DIR": runtime, "DBUS_SESSION_BUS_ADDRESS": "unix:path=%s/bus" % runtime}


def ton_datei(name="ton", toene=((660, 0.15), (990, 0.2))):
    """Kurze Tonfolge als WAV, einmal erzeugt. Vorgabe: Zweiklang (Bestätigung beim Umschalten)."""
    pfad = os.path.join(tempfile.gettempdir(), "fernsehfranzi-%s-%d.wav" % (name, os.getuid()))
    if os.path.exists(pfad):
        return pfad
    rate, proben = 22050, bytearray()
    for frequenz, dauer in toene:
        anzahl = int(rate * dauer)
        for i in range(anzahl):
            huelle = min(1.0, i / 400.0, (anzahl - i) / 400.0)
            # weicher Ausklang (Gong), damit Nachrichten freundlich klingen
            ausklang = max(0.0, 1.0 - i / anzahl) ** 1.5 if name == "gong" else 1.0
            proben += struct.pack("<h", int(14000 * huelle * ausklang * math.sin(2 * math.pi * frequenz * i / rate)))
    with wave.open(pfad, "wb") as datei:
        datei.setnchannels(1)
        datei.setsampwidth(2)
        datei.setframerate(rate)
        datei.writeframes(bytes(proben))
    return pfad


def waehle_ausgang(senken, ziel):
    """HDMI oder die eingebaute Klinke des Pi (bcm2835, Name mit "mailbox"/"headphones").
    Eine USB-Soundkarte (3.1.1: fürs Mikrofon der Bass-Ecke) wird nie als „Klinke“ gewählt.
    4.3: "kopfhoerer" = ein verbundener Bluetooth-Kopfhörer (PipeWire-Senke "bluez_output.…")."""
    if ziel == "kopfhoerer":
        return [s for s in senken if s.lower().startswith("bluez")]
    if ziel == "hdmi":
        return [s for s in senken if "hdmi" in s.lower()]
    eingebaut = [s for s in senken if "hdmi" not in s.lower() and "usb" not in s.lower()
                 and any(k in s.lower() for k in ("mailbox", "headphones", "bcm2835", "analog"))]
    return eingebaut or [s for s in senken if "hdmi" not in s.lower() and "usb" not in s.lower()]


class System:
    """Echte Systemaufrufe. Jede Methode gibt (ok, meldung) oder einen Wert zurück."""

    def _run(self, befehl, timeout=10, sitzung=False):
        env = dict(os.environ, LC_ALL="C", **(sitzungs_umgebung() if sitzung else {}))
        try:
            return subprocess.run(befehl, capture_output=True, text=True, timeout=timeout, env=env)
        except (OSError, subprocess.TimeoutExpired) as fehler:
            log.error("%s: %s", " ".join(befehl), fehler)
            return subprocess.CompletedProcess(befehl, 127, "", str(fehler))

    # ------------------------------------------------------------ RetroPie
    def retropie_zustand(self):
        """(laeuft, startmarke) - Startmarke wechselt bei jedem Start."""
        antwort = self._run([SYSTEMCTL, "show", RETROPIE_UNIT, SPIEL_UNIT, "-p", "ActiveState",
                             "-p", "ActiveEnterTimestampMonotonic"], timeout=5)
        laeuft, marke = False, 0
        for block in antwort.stdout.split("\n\n"):       # ein Block je Unit
            werte = dict(z.split("=", 1) for z in block.splitlines() if "=" in z)
            laeuft = laeuft or werte.get("ActiveState") in ("active", "activating", "reloading")
            try:
                marke = max(marke, int(werte.get("ActiveEnterTimestampMonotonic", "0")))
            except ValueError:
                pass
        return laeuft, marke

    def retropie(self, aktion):
        """aktion 'start' oder 'stop' - nur über die enge sudo-Regel."""
        if aktion not in ("start", "stop"):
            raise ValueError(aktion)
        antwort = self._run(["sudo", "-n", SYSTEMCTL, aktion, "--no-block", RETROPIE_UNIT], timeout=15)
        if antwort.returncode != 0:
            log.error("RetroPie %s fehlgeschlagen (%s): %s", aktion, antwort.returncode,
                      (antwort.stderr or antwort.stdout).strip())
            return False
        log.info("RetroPie %s angefordert.", aktion)
        return True

    def spiel(self, aktion):
        """Ein bestimmtes Spiel (spiel-start.json) auf tty8 starten/stoppen - enge sudo-Regel."""
        if aktion not in ("start", "stop"):
            raise ValueError(aktion)
        antwort = self._run(["sudo", "-n", SYSTEMCTL, aktion, "--no-block", SPIEL_UNIT], timeout=15)
        if antwort.returncode != 0 and aktion == "start":
            log.error("Spiel-Start fehlgeschlagen: %s", (antwort.stderr or antwort.stdout).strip())
            return False
        return True

    def scraper(self):
        """4.2: Bilder für Retro-Spiele holen (fernsehfranzi-scraper.service, enge sudo-Regel)."""
        antwort = self._run(["sudo", "-n", SYSTEMCTL, "start", "--no-block", "fernsehfranzi-scraper.service"], timeout=15)
        if antwort.returncode != 0:
            log.error("Scraper-Start fehlgeschlagen: %s", (antwort.stderr or antwort.stdout).strip())
        return antwort.returncode == 0

    def retroarch(self, befehl):
        """Netzwerkbefehl an RetroArch (SHOW_MSG ..., SAVE_STATE, QUIT). Fehler nur loggen."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(befehl.encode("utf-8"), ("127.0.0.1", RETROARCH_PORT))
            return True
        except OSError as fehler:
            log.warning("RetroArch-Befehl %r: %s", befehl, fehler)
            return False

    def retroarch_laeuft(self):
        return self._run(["pgrep", "-x", "retroarch"], timeout=5).returncode == 0

    # ------------------------------------------------------------ Ton (pactl, nicht wpctl)
    def ton_ausgaenge(self):
        antwort = self._run(["pactl", "list", "short", "sinks"], timeout=5, sitzung=True)
        if antwort.returncode != 0:
            return []
        senken = []
        for zeile in antwort.stdout.splitlines():
            teile = zeile.split("\t")
            if len(teile) >= 2 and teile[0].strip().isdigit():
                senken.append(teile[1].strip())
        return senken

    def ton_aktuell(self):
        """Name des aktuellen Standard-Ausgangs (pactl), leer wenn nicht lesbar."""
        antwort = self._run(["pactl", "get-default-sink"], timeout=5, sitzung=True)
        return antwort.stdout.strip() if antwort.returncode == 0 else ""

    def ton_wache(self, ziel):
        """Liegt der Ton noch auf dem gewählten Ausgang? Sonst still zurückstellen (kein Zweiklang).
        Grund: Ein angestecktes USB-Gerät (z. B. Mikrofon) darf den Ausgang nie umstellen."""
        soll = waehle_ausgang(self.ton_ausgaenge(), ziel)
        if not soll:
            return False
        ist = self.ton_aktuell()
        if ist and ist != soll[0]:
            log.warning("Ton: Standard war %s - zurück auf %s (%s).", ist, soll[0], ziel)
            self._run(["pactl", "set-default-sink", soll[0]], sitzung=True)
            return True
        return False

    def ton_setzen(self, ziel):
        """ziel 'hdmi', 'klinke' oder 'kopfhoerer'. Rückgabe (ok, knotenname)."""
        senken = self.ton_ausgaenge()
        passend = waehle_ausgang(senken, ziel)
        if not passend:
            log.warning("Ton: kein Ausgang für %s in %s", ziel, senken)
            return False, ""
        name = passend[0]
        if self._run(["pactl", "set-default-sink", name], sitzung=True).returncode != 0:
            return False, name
        self._run(["pactl", "set-sink-mute", name, "0"], sitzung=True)
        antwort = self._run(["pactl", "get-sink-volume", name], sitzung=True)
        werte = [int(w) for w in LAUTSTAERKE.findall(antwort.stdout)]
        if werte and max(werte) < 15:
            self._run(["pactl", "set-sink-volume", name, "50%"], sitzung=True)
        return True, name

    def gong(self, klang=None):
        """Hinweiston für Nachrichten, Erinnerungen und Zeitwarnungen - auf dem aktuellen Ausgang, überall hörbar.
        5.2: klang = ein Klang aus dem Archiv (klaenge.py), "stumm" = kein Ton, None = Gong."""
        from . import klaenge
        if klang == klaenge.STUMM:
            return
        try:
            subprocess.Popen(["pw-play", klaenge.datei(klang or klaenge.STANDARD)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             env=dict(os.environ, **sitzungs_umgebung()))
        except OSError as fehler:
            log.warning("Gong: %s", fehler)

    KLANG_LANG_S = 600

    def gong_datei(self, pfad, hoechstens_s=KLANG_LANG_S):
        """6.0: eigener Klang (Datei aus dem Klang-Ordner). 6.8.11: so lang wie die Datei (vorher nach 10 s abgeschnitten),
        als Sicherung höchstens 10 Minuten; ein neuer eigener Klang beendet den vorigen, damit sich nichts überlagert."""
        alt = getattr(self, "_klang_prozess", None)
        if alt is not None and alt.poll() is None:
            alt.kill()
        try:
            prozess = subprocess.Popen(["pw-play", pfad], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       env=dict(os.environ, **sitzungs_umgebung()))
            self._klang_prozess = prozess
            timer = threading.Timer(hoechstens_s, lambda: prozess.poll() is None and prozess.kill())
            timer.daemon = True
            timer.start()
        except OSError as fehler:
            log.warning("Eigener Klang: %s", fehler)

    def lautstaerke_setzen(self, prozent):
        """Lautstärke des aktuellen Ausgangs fest setzen (Wecker). Rückgabe: vorheriger Wert oder None."""
        name = self.ton_aktuell()
        if not name:
            return None
        antwort = self._run(["pactl", "get-sink-volume", name], sitzung=True)
        werte = [int(w) for w in LAUTSTAERKE.findall(antwort.stdout)]
        self._run(["pactl", "set-sink-volume", name, "%d%%" % max(0, min(100, int(prozent)))], sitzung=True)
        self._run(["pactl", "set-sink-mute", name, "0"], sitzung=True)
        return max(werte) if werte else None

    def lautstaerke(self, schritt=0, hoechstens=100):
        """Lautstärke des aktuellen Ausgangs um schritt Prozent ändern (begrenzt). Rückgabe: neuer Wert oder None."""
        name = self.ton_aktuell()
        if not name:
            return None
        antwort = self._run(["pactl", "get-sink-volume", name], sitzung=True)
        werte = [int(w) for w in LAUTSTAERKE.findall(antwort.stdout)]
        if not werte:
            return None
        neu = max(0, min(int(hoechstens), max(werte) + int(schritt)))
        if neu != max(werte) or schritt == 0:
            self._run(["pactl", "set-sink-volume", name, "%d%%" % neu], sitzung=True)
            self._run(["pactl", "set-sink-mute", name, "0"], sitzung=True)
        return neu

    def stumm_umschalten(self):
        """4.1: Ton des aktuellen Ausgangs aus/an. Rückgabe: True = jetzt stumm, False = Ton an, None = nicht lesbar."""
        name = self.ton_aktuell()
        if not name or self._run(["pactl", "set-sink-mute", name, "toggle"], sitzung=True).returncode != 0:
            return None
        antwort = self._run(["pactl", "get-sink-mute", name], sitzung=True)
        return None if antwort.returncode != 0 else ("yes" in antwort.stdout or "ja" in antwort.stdout)

    def bestaetigungston(self, ziel_name):
        """Kurzer Zweiklang auf dem neuen Ausgang (im Hintergrund)."""
        try:
            subprocess.Popen(["pw-play", "--target", ziel_name, ton_datei()], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, env=dict(os.environ, **sitzungs_umgebung()))
        except OSError as fehler:
            log.warning("Bestätigungston: %s", fehler)

    # ------------------------------------------------------------ Browser-Whitelist
    def richtlinie(self):
        antwort = self._run(["sudo", "-n", "/usr/local/lib/fernsehfranzi/richtlinie"], timeout=15)
        if antwort.returncode != 0:
            log.error("Chromium-Richtlinie nicht gesetzt: %s", (antwort.stderr or antwort.stdout).strip())
            return False
        log.info("Chromium-Richtlinie: %s", antwort.stdout.strip())
        return True

    # ------------------------------------------------------------ 4.1: Bluetooth (nur Eltern)
    def bluetooth(self, aktion, mac=""):
        """bt-helfer über die enge sudo-Regel. Rückgabe (ok, Ausgabe)."""
        befehl = ["sudo", "-n", "/usr/local/lib/fernsehfranzi/bt-helfer", aktion] + ([mac] if mac else [])
        antwort = self._run(befehl, timeout=60)
        if antwort.returncode != 0:
            log.warning("Bluetooth %s %s: %s", aktion, mac, (antwort.stderr or antwort.stdout).strip()[-300:])
        return antwort.returncode == 0, antwort.stdout if antwort.returncode == 0 else (antwort.stderr or antwort.stdout)

    # ------------------------------------------------------------ Gerät (nur Eltern)
    def geraet(self, aktion):
        """'neustart' oder 'aus' - sudo-Regel erlaubt genau diese zwei Befehle."""
        befehl = {"neustart": "reboot", "aus": "poweroff"}[aktion]
        log.warning("Gerät: %s (vom Elternbereich).", befehl)
        time.sleep(1)
        return self._run(["sudo", "-n", SYSTEMCTL, befehl], timeout=15).returncode == 0
