"""kiosk/kiosk.py: Steuerung von Chromium über die DevTools-Pipe - mit echtem (Headless-)Chromium."""
import os
import shutil
import sys
import tempfile
import time
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "kiosk"))

import kiosk  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as _pw:
        CHROMIUM = _pw.chromium.executable_path
except Exception:   # noqa: BLE001
    CHROMIUM = None


class TestKiosk(kiosk.Kiosk):
    def chromium_befehl(self):
        befehl = super().chromium_befehl()
        befehl[0] = CHROMIUM
        befehl.remove("--kiosk")
        return befehl[:1] + ["--headless=new"] + befehl[1:-1] + ["about:blank"]

    def melde_adresse(self):
        self.gemeldet = getattr(self, "gemeldet", []) + [self.adresse]


@unittest.skipUnless(CHROMIUM and os.path.exists(CHROMIUM), "Chromium aus Playwright fehlt – make venv")
class Pipe(unittest.TestCase):
    def setUp(self):
        self.daten = tempfile.mkdtemp(prefix="ff-kiosk-")
        self.addCleanup(shutil.rmtree, self.daten, True)
        self.k = TestKiosk(self.daten)
        self.k.starte_chromium()
        self.addCleanup(self.k.chromium.kill)

    def warte(self, bedingung, frist=10):
        ende = time.time() + frist
        while time.time() < ende:
            if bedingung():
                return True
            time.sleep(0.1)
        return False

    def test_seite_oeffnen_und_adresse_melden(self):
        self.k.oeffne("data:text/html,<title>Plex-Attrappe</title><p>hallo</p>")
        self.assertTrue(self.warte(lambda: any("Plex-Attrappe" in a for a in getattr(self.k, "gemeldet", []))))

    def test_hinweis_auf_fremder_seite(self):
        self.k.oeffne("data:text/html,<p>Plex</p>")
        self.warte(lambda: self.k.adresse.startswith("data:"))
        time.sleep(0.5)
        self.k.hinweis("Noch 5 Minuten!")
        text = self.k.pipe.senden("Runtime.evaluate", {
            "expression": "document.getElementById('fernsehfranzi-hinweis').textContent", "returnByValue": True},
            sitzung=self.k.sitzung)["result"]["value"]
        self.assertEqual(text, "Noch 5 Minuten!")

    def test_dimmen(self):
        self.k.oeffne("data:text/html,<p>Hoerspiel</p>")
        self.warte(lambda: self.k.adresse.startswith("data:"))
        time.sleep(0.5)
        self.k.dimmen(0.6)
        wert = self.k.pipe.senden("Runtime.evaluate", {
            "expression": "document.getElementById('fernsehfranzi-dimmen').style.opacity", "returnByValue": True},
            sitzung=self.k.sitzung)["result"]["value"]
        self.assertEqual(wert, "0.6")
        self.k.dimmen(0)
        weg = self.k.pipe.senden("Runtime.evaluate", {
            "expression": "document.getElementById('fernsehfranzi-dimmen') === null", "returnByValue": True},
            sitzung=self.k.sitzung)["result"]["value"]
        self.assertTrue(weg)

    def test_domains_werden_gesammelt(self):
        self.k.oeffne("data:text/html,<img src='http://bilder.example.invalid/x.png'>")
        self.assertTrue(self.warte(lambda: "bilder.example.invalid" in self.k.domains))

    def test_auftrag_bewegungspause(self):
        aufrufe = []
        self.k.oeffne = aufrufe.append
        self.k.auftrag({"nr": 2, "art": "startseite", "pause": 120})
        self.assertEqual(aufrufe, ["http://127.0.0.1:8765/#pause-120"])

    def test_auftrag_startseite_mit_eltern(self):
        aufrufe = []
        self.k.oeffne = aufrufe.append
        self.k.auftrag({"nr": 1, "art": "startseite", "eltern": True})
        self.assertEqual(aufrufe, ["http://127.0.0.1:8765/#eltern"])


    def test_foto_als_jpeg(self):
        import base64
        self.k.oeffne("data:text/html,<body style='background:red'>TV</body>")
        self.warte(lambda: self.k.adresse.startswith("data:"))
        time.sleep(0.5)
        gesendet = []
        self.k.server = lambda pfad, daten=None, timeout=5: gesendet.append((pfad, daten))
        self.k.foto(7)
        pfad, daten = gesendet[0]
        self.assertEqual((pfad, daten["nr"]), ("/api/kiosk/foto", 7))
        self.assertTrue(base64.b64decode(daten["bild"]).startswith(b"\xff\xd8"), daten.get("fehler"))
        self.k.desktop_app = object()                                # Desktop-App: kein Foto
        self.k.foto(8)
        self.assertIn("Desktop-App", gesendet[1][1]["fehler"])
        self.k.desktop_app = None

    def test_speicher_freigeben_kennt_chromium(self):
        self.k.pipe.senden("Memory.simulatePressureNotification", {"level": "critical"}, warten=5)   # wirft sonst


class RetroEntlasten(unittest.TestCase):
    """4.1/4.2: Während RetroPie läuft, ist Chromium aus (Rückfall: leere Seite) - RAM/CPU fürs Spiel."""

    class Pipe:
        def __init__(self):
            self.befehle = []

        def senden(self, methode, params=None, sitzung=None, warten=5.0):
            self.befehle.append((methode, (params or {}).get("url") or (params or {}).get("level")))
            return {}

    def setUp(self):
        self.k = kiosk.Kiosk(tempfile.mkdtemp(prefix="ff-kiosk-"))
        self.addCleanup(shutil.rmtree, self.k.daten, True)
        self.k.pipe = self.Pipe()
        self.geoeffnet = []
        self.k.oeffne = self.geoeffnet.append

    def test_chromium_aus_waehrend_des_spiels(self):
        """4.2: Chromium wird ganz beendet (RAM fürs Spiel) und danach mit der Startseite neu gestartet."""
        self.k.adresse = kiosk.START
        self.k.retro_wechsel(True)
        self.assertEqual(self.k.pipe.befehle, [("Browser.close", None)])
        self.assertTrue(self.k.retro_pause.is_set(), "laufen() startet Chromium jetzt nicht neu")
        self.k.retro_wechsel(True)                                   # läuft weiter: nichts Neues
        self.assertEqual(len(self.k.pipe.befehle), 1)
        self.k.retro_wechsel(False)
        self.assertFalse(self.k.retro_pause.is_set())
        self.assertEqual(self.k.chromium_befehl()[-1], kiosk.START + "#zurueck", "neu gestartet mit „Willkommen zurück“")

    def test_wenn_beenden_scheitert_leere_seite(self):
        def scheitert(methode, params=None, sitzung=None, warten=5.0):
            self.k.pipe.befehle.append((methode, (params or {}).get("url") or (params or {}).get("level")))
            if methode == "Browser.close":
                raise RuntimeError("geht nicht")
            return {}
        self.k.pipe.senden = scheitert
        self.k.adresse = kiosk.START
        self.k.retro_wechsel(True)
        self.assertFalse(self.k.retro_pause.is_set())
        self.assertEqual(self.k.pipe.befehle[1:], [("Page.navigate", kiosk.RETRO_SEITE),
                                                   ("Memory.simulatePressureNotification", "critical")])
        self.k.adresse = kiosk.RETRO_SEITE
        self.k.retro_wechsel(False)
        self.assertEqual(self.geoeffnet, [kiosk.START + "#zurueck"])

    def test_fremde_seite_bleibt(self):
        self.k.adresse = "https://app.plex.tv/desktop"
        self.k.retro_wechsel(True)
        self.k.retro_wechsel(False)
        self.assertEqual((self.k.pipe.befehle, self.geoeffnet), ([], []))

    def test_retro_seite_ohne_skript(self):
        with open(os.path.join(REPO, "web", "retro.html"), encoding="utf-8") as f:
            self.assertNotIn("<script", f.read())


class Befehl(unittest.TestCase):
    def test_schalter(self):
        befehl = kiosk.Kiosk("/tmp/x").chromium_befehl()
        for schalter in ("--kiosk", "--enable-spatial-navigation", "--remote-debugging-pipe"):
            self.assertIn(schalter, befehl)
        self.assertNotIn("--remote-debugging-port", " ".join(befehl))
        self.assertTrue(any(s.startswith("--load-extension=") and s.endswith("fernbedienung") for s in befehl))
        self.assertEqual(befehl[-1], "http://127.0.0.1:8765/")

    def test_erweiterung_hat_plex_und_youtube(self):
        import json
        with open(os.path.join(REPO, "fernbedienung", "manifest.json")) as f:
            skripte = {s["js"][0]: s for s in json.load(f)["content_scripts"]}
        self.assertEqual(skripte["youtube.js"]["world"], "MAIN")
        self.assertEqual(skripte["youtube.js"]["run_at"], "document_start")

if __name__ == "__main__":
    unittest.main()
