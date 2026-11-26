"""6.9.47: Bildschirmschoner (Franzi + Uhr) und Standby nach X Minuten ohne Eingabe."""
import os
import shutil
import sys
import tempfile
import threading
import unittest
from datetime import datetime

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))
from test_v3_server import Uhr, neuer_hub  # noqa: E402

TAG = datetime(2026, 11, 25, 15, 0)


class Standby(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-6947-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(TAG))
        self.befehle, self.auftraege = [], []
        self.hub.cec_befehl = lambda b: self.befehle.append(b)
        alt = self.hub.auftrag
        self.hub.auftrag = lambda art, **k: (self.auftraege.append((art, k)), alt(art, **k))

    def test_ab_werk_aus(self):
        self.assertEqual(self.hub.bildschirm(), {"schoner_min": 5, "standby_min": 0})
        self.hub._standby_takt(False, 99999)
        self.assertEqual(self.befehle, [])

    def test_hinweis_dann_aus(self):
        self.hub.einstellungen_aendern({"bildschirm": {"schoner_min": 5, "standby_min": 15}})
        self.hub._standby_takt(False, 13 * 60)
        self.assertEqual(self.befehle, [])
        self.hub._standby_takt(False, 14 * 60 + 5)
        self.assertTrue(any(a == "hinweis" and "Minute" in k.get("text", "") for a, k in self.auftraege))
        self.assertEqual(self.befehle, [])
        self.hub._standby_takt(False, 15 * 60 + 1)
        self.assertEqual(self.befehle, ["standby"])
        self.hub._standby_takt(False, 15 * 60 + 30)
        self.assertEqual(self.befehle, ["standby"], "nur einmal")

    def test_nicht_wenn_etwas_laeuft(self):
        self.hub.einstellungen_aendern({"bildschirm": {"standby_min": 15}})
        self.hub.aktuell = "youtube"
        for s in (14 * 60 + 5, 16 * 60):
            self.hub._standby_takt(False, s)
        self.hub.aktuell = None
        self.hub._standby_takt(True, 16 * 60)                    # RetroPie läuft
        self.assertEqual(self.befehle, [])

    def test_pruefung(self):
        for falsch in ({"standby_min": 7}, {"schoner_min": True}, {"quatsch": 1}):
            with self.assertRaises(ValueError):
                self.hub.einstellungen_aendern({"bildschirm": falsch})
        self.assertEqual(self.hub.startseite_anzeige()["bildschirm"]["schoner_min"], 5)


class Schoner(unittest.TestCase):
    """Startseite: nach der eingestellten Zeit Franzi + Uhr, eine Taste beendet ihn."""
    def test_franzi_schoner(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("kein Playwright")
        from fernsehfranzi import web
        from test_spiele_wie_am_geraet import port_frei
        if not port_frei(8765):
            self.skipTest("Port 8765 belegt")
        ordner = tempfile.mkdtemp(prefix="ff-6947s-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(TAG))
        hub.einstellungen_aendern({"bildschirm": {"schoner_min": 2}})
        srv = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            s = b.new_page(viewport={"width": 1280, "height": 720})
            fehler = []
            s.on("pageerror", lambda e: fehler.append(str(e)))
            s.goto("http://127.0.0.1:8765/")
            s.wait_for_function("window.FernsehFranzi && FernsehFranzi.zustand.bildschirm")
            s.evaluate("FernsehFranzi.zustand.letzteTaste = Date.now() - 3 * 60 * 1000")
            s.wait_for_selector("#schoner.franzi-schoner .franzi", timeout=35000)
            self.assertIn(":", s.inner_text("#schoner .fs-uhr b"))
            s.keyboard.press("ArrowRight")
            s.wait_for_selector("#schoner", state="detached")
            self.assertEqual(fehler, [])
            b.close()


if __name__ == "__main__":
    unittest.main()
