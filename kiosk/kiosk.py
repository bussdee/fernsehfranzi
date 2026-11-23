#!/usr/bin/env python3
"""FernsehFranzi 3.0 - Kiosk (ersetzt kiosk.sh). Läuft in der labwc-Sitzung des Kiosk-Benutzers.

Besitzer von Chromium und Desktop-Apps (docs/ENTWICKLUNG.md, „Wer besitzt was“):
  * startet Chromium im Kiosk-Modus und steuert ihn über die DevTools-**Pipe**
    (--remote-debugging-pipe: kein offener Port, keine Erweiterung nötig)
  * holt Aufträge vom Server (lange Abfrage): Seite öffnen, zur Startseite, Hinweis einblenden,
    Desktop-App starten, Linux-Desktop (nur Eltern, nach PIN)
  * meldet die aktuelle Adresse an den Server (Zeitkonto: welche App läuft)
  * startet Chromium nach einem Absturz neu, lädt sich nach einem Update selbst neu
"""
import collections
import json
import logging
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

SERVER = "http://127.0.0.1:8765"
START = SERVER + "/"
RETRO_SEITE = SERVER + "/retro.html"     # 4.1: leichte Seite, solange ein Retro-Spiel läuft
CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP_MAX_S = 20 * 60

log = logging.getLogger("kiosk")


class Pipe:
    """DevTools-Protokoll über zwei Pipes (Chromium liest fd 3, schreibt fd 4; Nachrichten mit \\0)."""

    def __init__(self, schreiben, lesen):
        self.w, self.r = schreiben, lesen
        self.nr = 0
        self.lock = threading.Lock()
        self.antworten, self.warte = {}, threading.Condition()
        self.ereignisse = []                     # (methode, params, sessionId) an Abonnenten
        self.abonnenten = []
        threading.Thread(target=self._lesen, daemon=True).start()

    def senden(self, methode, params=None, sitzung=None, warten=5.0):
        with self.lock:
            self.nr += 1
            nr = self.nr
            nachricht = {"id": nr, "method": methode, "params": params or {}}
            if sitzung:
                nachricht["sessionId"] = sitzung
            os.write(self.w, json.dumps(nachricht).encode() + b"\0")
        if not warten:
            return None
        frist = time.monotonic() + warten
        with self.warte:
            while nr not in self.antworten:
                rest = frist - time.monotonic()
                if rest <= 0:
                    raise TimeoutError(methode)
                self.warte.wait(rest)
            antwort = self.antworten.pop(nr)
        if "error" in antwort:
            raise RuntimeError("%s: %s" % (methode, antwort["error"].get("message")))
        return antwort.get("result", {})

    def _lesen(self):
        puffer = b""
        while True:
            try:
                stueck = os.read(self.r, 65536)
            except OSError:
                stueck = b""
            if not stueck:
                with self.warte:
                    self.antworten[-1] = {"error": {"message": "Pipe geschlossen"}}
                    self.warte.notify_all()
                return
            puffer += stueck
            while b"\0" in puffer:
                roh, puffer = puffer.split(b"\0", 1)
                try:
                    nachricht = json.loads(roh)
                except ValueError:
                    continue
                if "id" in nachricht:
                    with self.warte:
                        self.antworten[nachricht["id"]] = nachricht
                        self.warte.notify_all()
                else:
                    for abo in self.abonnenten:
                        abo(nachricht.get("method"), nachricht.get("params", {}), nachricht.get("sessionId"))


HINWEIS_JS = """(() => {
  const id = "fernsehfranzi-hinweis";
  let box = document.getElementById(id);
  if (!box) {
    box = document.createElement("div");
    box.id = id;
    box.style.cssText = "position:fixed;left:50%;bottom:8vh;transform:translateX(-50%);z-index:2147483647;" +
      "background:#1f2a3d;color:#fff;border:2px solid rgba(255,255,255,.3);border-radius:18px;padding:16px 28px;" +
      "font:700 26px system-ui,sans-serif;box-shadow:0 8px 30px rgba(0,0,0,.5);pointer-events:none";
    document.documentElement.appendChild(box);
  }
  box.textContent = __TEXT__;
  clearTimeout(window.__ffHinweis);
  window.__ffHinweis = setTimeout(() => box.remove(), 30000);   /* 3.4: länger stehen lassen (Erinnerungen) */
})()"""


# 4.0: Plex mit dem Kinderprofil - in der Profilauswahl das Profil mit genau diesem Namen anklicken.
# Gesucht wird nur ein Element mit exakt diesem Text, das anklickbar ist; kein Treffer = nichts passiert.
PROFIL_JS = """(() => {
  const name = __NAME__;
  const kandidaten = [...document.querySelectorAll('button, a, [role="button"], [tabindex], [class*="User"], [class*="user"]')];
  for (const k of kandidaten) {
    const text = (k.innerText || k.textContent || '').trim();
    if (text === name) { k.click(); return true; }
  }
  return false;
})()"""


DIMMEN_JS = """(() => {
  const id = "fernsehfranzi-dimmen";
  let box = document.getElementById(id);
  const stufe = __STUFE__;
  if (!stufe) { if (box) box.remove(); return; }
  if (!box) {
    box = document.createElement("div");
    box.id = id;
    box.style.cssText = "position:fixed;inset:0;background:#000;pointer-events:none;z-index:2147483646";
    document.documentElement.appendChild(box);
  }
  box.style.opacity = stufe;
})()"""


class Kiosk:
    def __init__(self, daten):
        self.daten = daten
        self.chromium = None
        self.pipe = None
        self.ziel = None            # targetId der Seite
        self.sitzung = None         # sessionId (flatten)
        self.adresse = ""
        self.desktop_app = None
        self.desktop_modus = []     # Prozesse im Eltern-Desktop
        self.desktop_seit = 0.0
        self.letzter_auftrag = 0
        # 3.2: welche Hosts Chromium lädt bzw. die Whitelist blockiert (für die Eltern-Seite)
        self.domains = collections.defaultdict(lambda: {"anzahl": 0, "blockiert": 0})
        self.anfragen = {}           # requestId -> host
        self.domains_lock = threading.Lock()
        # 4.2: Während eines Retro-Spiels ist Chromium ganz aus (gibt ~400-600 MiB frei, Zelda/N64 brauchte das)
        self.retro_pause = threading.Event()
        self.start_anker = ""

    # ------------------------------------------------------------ Server
    def token(self):
        try:
            with open(os.path.join(self.daten, "kiosk-token")) as f:
                return f.read().strip()
        except OSError:
            return ""

    def server(self, pfad, daten=None, timeout=5):
        anfrage = urllib.request.Request(SERVER + pfad, headers={"X-FF-Token": self.token(),
                                                                 "Content-Type": "application/json"},
                                         data=None if daten is None else json.dumps(daten).encode(),
                                         method="GET" if daten is None else "POST")
        with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
            return json.loads(antwort.read() or b"{}")

    # ------------------------------------------------------------ Chromium
    def chromium_befehl(self):
        programm = next((p for p in ("/usr/bin/chromium", "/usr/bin/chromium-browser") if os.path.exists(p)), "chromium")
        return [programm, "--kiosk", "--start-fullscreen", "--noerrdialogs", "--disable-infobars", "--no-first-run",
                "--hide-crash-restore-bubble", "--password-store=basic", "--check-for-update-interval=31536000",
                "--enable-spatial-navigation", "--remote-debugging-pipe",
                # Videos (Bass-Ecke, Hörspiele) starten ohne extra Tastendruck - sonst bleibt der Player stumm stehen
                "--autoplay-policy=no-user-gesture-required",
                "--load-extension=" + os.path.join(CODE, "fernbedienung"),
                "--user-data-dir=" + os.path.join(self.daten, "chromium-profil"), START + self.start_anker]

    def starte_chromium(self):
        befehl_r, befehl_w = os.pipe()       # wir schreiben -> Chromium liest (fd 3)
        antwort_r, antwort_w = os.pipe()     # Chromium schreibt (fd 4) -> wir lesen

        def kind():
            # erst auf freie hohe Nummern, dann auf 3/4 (sonst überschreibt dup2 evtl. die andere Pipe)
            a, b = os.dup(befehl_r), os.dup(antwort_w)
            os.dup2(a, 3)
            os.dup2(b, 4)
        # 3 und 4 bleiben offen (subprocess schließt nach preexec_fn alle nicht genannten fds)
        self.chromium = subprocess.Popen(self.chromium_befehl(), pass_fds=(befehl_r, antwort_w, 3, 4),
                                         preexec_fn=kind, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.close(befehl_r)
        os.close(antwort_w)
        self.pipe = Pipe(befehl_w, antwort_r)
        self.pipe.abonnenten.append(self.ereignis)
        # Chromium braucht auf dem Pi 3 nach dem Hochfahren deutlich länger als 5 s bis zur ersten Antwort
        self.pipe.senden("Target.setDiscoverTargets", {"discover": True}, warten=45)
        self.verbinde_seite()
        log.info("Chromium gestartet (PID %s).", self.chromium.pid)
        self.start_anker = ""

    def verbinde_seite(self):
        for _ in range(50):
            seiten = [t for t in self.pipe.senden("Target.getTargets")["targetInfos"] if t["type"] == "page"]
            if seiten:
                self.ziel = seiten[0]["targetId"]
                self.adresse = seiten[0].get("url", "")
                self.sitzung = self.pipe.senden("Target.attachToTarget",
                                                {"targetId": self.ziel, "flatten": True})["sessionId"]
                try:
                    self.pipe.senden("Network.enable", {}, sitzung=self.sitzung)
                except (RuntimeError, TimeoutError) as fehler:
                    log.warning("Netzwerk-Mitschnitt nicht verfügbar: %s", fehler)
                return
            time.sleep(0.2)
        raise RuntimeError("Keine Chromium-Seite gefunden")

    def ereignis(self, methode, params, _sitzung):
        if methode == "Network.requestWillBeSent":
            host = urlsplit(params.get("request", {}).get("url", "")).hostname
            if host:
                with self.domains_lock:
                    self.anfragen[params.get("requestId")] = host
                    if len(self.anfragen) > 2000:
                        self.anfragen.clear()
                    self.domains[host]["anzahl"] += 1
            return
        if methode == "Network.loadingFailed":
            if "BLOCKED_BY_ADMINISTRATOR" in params.get("errorText", ""):
                with self.domains_lock:
                    host = self.anfragen.get(params.get("requestId"))
                    if host:
                        self.domains[host]["blockiert"] += 1
            return
        if methode == "Target.targetInfoChanged":
            info = params.get("targetInfo", {})
            if info.get("targetId") == self.ziel and info.get("url") != self.adresse:
                self.adresse = info.get("url", "")
                threading.Thread(target=self.melde_adresse, daemon=True).start()
                if getattr(self, "stufe", 0):
                    threading.Timer(2.0, lambda: self.dimmen(self.stufe)).start()

    def melde_adresse(self):
        try:
            self.server("/api/kiosk/ort", {"url": self.adresse})
        except (urllib.error.URLError, OSError, ValueError) as fehler:
            log.warning("Adresse nicht gemeldet: %s", fehler)

    def oeffne(self, url):
        self.pipe.senden("Page.navigate", {"url": url}, sitzung=self.sitzung)
        self.fenster("fullscreen")

    def profil_waehlen(self, name, dauer_s=20):
        """Plex: Profilauswahl überspringen - höchstens dauer_s Sekunden lang nach dem Profil suchen."""
        ende = time.monotonic() + dauer_s
        while time.monotonic() < ende:
            time.sleep(1)
            try:
                antwort = self.pipe.senden("Runtime.evaluate", {"expression": PROFIL_JS.replace("__NAME__", json.dumps(name)),
                                                                "returnByValue": True}, sitzung=self.sitzung, warten=2)
            except (RuntimeError, TimeoutError):
                continue
            if (antwort or {}).get("result", {}).get("value") is True:
                log.info("Plex: Profil „%s“ gewählt.", name)
                return

    def hinweis(self, text):
        if self.adresse.startswith(START):
            return        # die Startseite zeigt Meldungen selbst
        self.pipe.senden("Runtime.evaluate", {"expression": HINWEIS_JS.replace("__TEXT__", json.dumps(text))},
                         sitzung=self.sitzung, warten=2)

    def dimmen(self, stufe):
        """Bildschirm abdunkeln (Gute-Nacht-Modus): schwarze, durchlässige Ebene über der Seite."""
        self.stufe = float(stufe or 0)
        self.pipe.senden("Runtime.evaluate", {"expression": DIMMEN_JS.replace("__STUFE__", json.dumps(self.stufe))},
                         sitzung=self.sitzung, warten=2)

    def fenster(self, zustand):
        try:
            fenster = self.pipe.senden("Browser.getWindowForTarget", {"targetId": self.ziel})["windowId"]
            self.pipe.senden("Browser.setWindowBounds", {"windowId": fenster, "bounds": {"windowState": zustand}})
        except (RuntimeError, TimeoutError) as fehler:
            log.warning("Fenster %s: %s", zustand, fehler)

    # ------------------------------------------------------------ Desktop-Apps und Eltern-Desktop
    def starte_desktop_app(self, befehl):
        self.beende_desktop()
        teile = shlex.split(befehl)
        log.info("Desktop-App: %s", teile)
        self.desktop_app = subprocess.Popen(teile, start_new_session=True,
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.fenster("minimized")

    def beende_desktop(self):
        for prozess in [self.desktop_app] + self.desktop_modus:
            if prozess and prozess.poll() is None:
                try:
                    os.killpg(prozess.pid, signal.SIGTERM)
                except OSError:
                    pass
        self.desktop_app, self.desktop_modus = None, []

    def eltern_desktop(self):
        try:
            einstellungen = json.load(open(os.path.join(self.daten, "einstellungen.json")))
            befehle = (einstellungen.get("desktop") or {}).get("befehle") or []
        except (OSError, ValueError):
            befehle = []
        if not befehle:
            befehle = ["/usr/bin/wf-panel-pi", "/usr/bin/pcmanfm --desktop --profile LXDE-pi"]
        self.beende_desktop()
        for befehl in befehle:
            try:
                self.desktop_modus.append(subprocess.Popen(shlex.split(befehl), start_new_session=True,
                                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            except OSError as fehler:
                log.warning("Desktop: %s nicht startbar: %s", befehl, fehler)
        self.desktop_seit = time.monotonic()
        self.fenster("minimized")
        log.info("Eltern-Desktop geöffnet (zurück nach %d min oder über „Zur Startseite“).", DESKTOP_MAX_S // 60)

    def foto(self, nr):
        daten = {"nr": nr}
        if self.desktop_app or self.desktop_modus:
            daten["fehler"] = "Gerade läuft eine Desktop-App – davon gibt es kein Foto."
        else:
            try:
                daten["bild"] = self.pipe.senden("Page.captureScreenshot", {"format": "jpeg", "quality": 60},
                                                 sitzung=self.sitzung, warten=6)["data"]
            except (RuntimeError, TimeoutError, KeyError, TypeError, AttributeError) as fehler:
                daten["fehler"] = "Foto ging nicht (%s)." % fehler
        try:
            self.server("/api/kiosk/foto", daten, timeout=10)
        except (urllib.error.URLError, OSError, ValueError) as fehler:
            log.warning("Foto nicht übergeben: %s", fehler)

    def kk_anmeldung(self, nr, adresse):
        """4.4: Anmelde-Cookie der Klassenkiste aus dem Kiosk-Profil (DevTools, Browser-Ebene) für den Karaoke-Player.
        Geht nur an den eigenen Server (127.0.0.1); der Server liest damit nur Liedliste und Musik."""
        daten = {"nr": nr}
        try:
            host = urlsplit(adresse).hostname or ""
            cookies = self.pipe.senden("Storage.getCookies", {}, warten=5).get("cookies", [])
            passend = [c for c in cookies if host and (c.get("domain", "").lstrip(".") == host or host.endswith("." + c.get("domain", "").lstrip(".")))]
            daten["cookie"] = "; ".join("%s=%s" % (c["name"], c["value"]) for c in passend if c.get("name"))
        except (RuntimeError, TimeoutError, KeyError, TypeError, AttributeError) as fehler:
            daten["fehler"] = "Anmeldung nicht lesbar (%s)." % fehler
        try:
            self.server("/api/kiosk/kk-anmeldung", daten, timeout=10)
        except (urllib.error.URLError, OSError, ValueError) as fehler:
            log.warning("Klassenkiste-Anmeldung nicht übergeben: %s", fehler)

    def zur_startseite(self, eltern=False, pause=0, anker=""):
        self.beende_desktop()
        anker = anker or ("#eltern" if eltern else ("#pause-%d" % int(pause) if pause else ""))
        self.oeffne(START + anker)

    # ------------------------------------------------------------ Aufträge
    def auftrag(self, a):
        art = a.get("art")
        log.info("Auftrag %s: %s", a.get("nr"), art)
        if art == "oeffne":
            self.beende_desktop()
            self.oeffne(a["url"])
            if a.get("profil"):
                threading.Thread(target=self.profil_waehlen, args=(a["profil"],), daemon=True).start()
        elif art == "startseite":
            self.zur_startseite(bool(a.get("eltern")), int(a.get("pause") or 0))
        elif art == "gute_nacht":         # 3.4: Gute-Nacht-Player auf der Startseite (automatisch = mit Alarmen)
            self.zur_startseite(anker="#gute-nacht-auto" if a.get("automatisch") else "#gute-nacht")
        elif art == "sonne":              # 4.0: Sonnenaufgang vor dem Wecken
            self.zur_startseite(anker="#sonne-%d" % int(a.get("minuten") or 10))
        elif art == "wecker":             # 3.5: Weckbildschirm
            self.zur_startseite(anker="#wecker")
        elif art == "nacht":              # 3.4: Countdown zu Beginn der Nachtruhe
            self.zur_startseite(anker="#nacht")
        elif art == "dimmen":
            self.dimmen(a.get("stufe", 0))
        elif art == "hinweis":
            self.hinweis(a.get("text", ""))
        elif art == "desktop":
            self.starte_desktop_app(a["befehl"])
        elif art == "desktop_modus":
            self.eltern_desktop()
        elif art == "kk_anmeldung":       # 4.4: Karaoke mit den Liedern der Klassenkiste
            threading.Thread(target=self.kk_anmeldung, args=(int(a.get("kk") or 0), str(a.get("adresse") or "")), daemon=True).start()
        elif art == "foto":               # 4.1: Bildschirmfoto für die Eltern-Seite
            threading.Thread(target=self.foto, args=(int(a.get("foto") or 0),), daemon=True).start()

    def auftrags_schleife(self):
        try:
            self.letzter_auftrag = self.server("/api/kiosk/auftraege?nach=999999999")["letzte"]
        except (urllib.error.URLError, OSError, ValueError, KeyError):
            pass
        while True:
            try:
                antwort = self.server("/api/kiosk/auftraege?nach=%d&warten=20" % self.letzter_auftrag, timeout=30)
                for a in antwort.get("auftraege", []):
                    self.letzter_auftrag = max(self.letzter_auftrag, a["nr"])
                    try:
                        self.auftrag(a)
                    except Exception:   # noqa: BLE001
                        log.exception("Auftrag fehlgeschlagen: %s", a)
            except (urllib.error.URLError, OSError, ValueError):
                time.sleep(2)           # Server startet gerade

    def domains_melden(self):
        """Alle 30 s die gesammelten Hosts an den Server (der speichert sie für die Eltern-Seite)."""
        while True:
            time.sleep(30)
            with self.domains_lock:
                liste = [dict(host=h, **w) for h, w in self.domains.items()]
                self.domains.clear()
            if liste:
                try:
                    self.server("/api/kiosk/domains", {"domains": liste[:200]})
                except (urllib.error.URLError, OSError, ValueError) as fehler:
                    log.warning("Domains nicht gemeldet: %s", fehler)

    # ------------------------------------------------------------ 4.1: Retro-Spiel läuft -> Chromium entlasten
    def retro_wechsel(self, laeuft):
        """RetroPie gestartet: Chromium ganz beenden (4.2 - die leere Seite aus 4.1 sparte zu wenig; Chromium belegte
        weiter 400-600 MiB, Zelda/N64 ruckelte). Beendet: Chromium mit der Startseite wieder starten.
        Klappt das Beenden nicht, bleibt der Weg aus 4.1: leere, skriptlose Seite und Speicher freigeben."""
        if laeuft and not self.retro_pause.is_set() and self.adresse.startswith(START) and not self.desktop_modus:
            log.info("Retro-Spiel läuft: Chromium wird für das Spiel beendet.")
            self.retro_pause.set()
            try:
                self.pipe.senden("Browser.close", {}, warten=5)
            except (RuntimeError, TimeoutError, OSError) as fehler:
                log.warning("Chromium beenden ging nicht (%s) - nur leere Seite.", fehler)
                self.retro_pause.clear()
                self.pipe.senden("Page.navigate", {"url": RETRO_SEITE}, sitzung=self.sitzung)
                try:
                    self.pipe.senden("Memory.simulatePressureNotification", {"level": "critical"}, warten=5)
                except (RuntimeError, TimeoutError) as fehler2:
                    log.warning("Speicher freigeben: %s", fehler2)
                return
            if self.chromium:
                try:
                    self.chromium.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.chromium.terminate()
        elif not laeuft and self.retro_pause.is_set():
            log.info("Retro-Spiel beendet: Chromium startet wieder mit der Startseite.")
            self.start_anker = "#zurueck"
            self.retro_pause.clear()
        elif not laeuft and self.adresse.startswith(RETRO_SEITE):
            log.info("Retro-Spiel beendet: zurück zur Startseite.")
            self.zur_startseite(anker="#zurueck")

    def retro_wache(self):
        vorher = False
        while True:
            time.sleep(3)
            try:
                laeuft = bool(self.server("/api/status").get("running"))
            except (urllib.error.URLError, OSError, ValueError, AttributeError):
                continue
            if laeuft != vorher or (not laeuft and (self.retro_pause.is_set() or self.adresse.startswith(RETRO_SEITE))):
                try:
                    self.retro_wechsel(laeuft)
                    vorher = laeuft
                except (RuntimeError, TimeoutError, AttributeError) as fehler:
                    log.warning("Retro-Wechsel: %s", fehler)

    def aufpassen(self):
        """Desktop-App beendet -> Startseite. Eltern-Desktop nach 20 min -> zurück in den Kiosk."""
        while True:
            time.sleep(1)
            if self.desktop_app and self.desktop_app.poll() is not None:
                self.desktop_app = None
                try:
                    self.server("/api/ort", {"app": None})
                except (urllib.error.URLError, OSError, ValueError):
                    pass
                self.fenster("fullscreen")
            if self.desktop_modus and time.monotonic() - self.desktop_seit > DESKTOP_MAX_S:
                log.info("Eltern-Desktop: Zeit abgelaufen, zurück in den Kiosk.")
                self.zur_startseite()

    def laufen(self):
        stand = os.path.getmtime(os.path.abspath(__file__))
        threading.Thread(target=self.auftrags_schleife, daemon=True).start()
        threading.Thread(target=self.aufpassen, daemon=True).start()
        threading.Thread(target=self.domains_melden, daemon=True).start()
        threading.Thread(target=self.retro_wache, daemon=True).start()
        while True:
            try:
                self.starte_chromium()
                self.chromium.wait()
                log.warning("Chromium beendet (Code %s).", self.chromium.returncode)
            except Exception:   # noqa: BLE001
                log.exception("Chromium-Start fehlgeschlagen")
                if self.chromium and self.chromium.poll() is None:
                    self.chromium.kill()
            while self.retro_pause.is_set():          # 4.2: Retro-Spiel läuft - Chromium bleibt aus
                time.sleep(1)
            if os.path.getmtime(os.path.abspath(__file__)) != stand:
                log.info("kiosk.py wurde aktualisiert - lade neu.")
                os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
            time.sleep(2)


def main():
    daten = os.environ.get("FERNSEHFRANZI_DATEN") or os.path.expanduser("~/fernsehfranzi-daten")
    os.makedirs(os.path.join(daten, "logs"), exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(os.path.join(daten, "logs", "kiosk.log"))])
    Kiosk(daten).laufen()


if __name__ == "__main__":
    main()
