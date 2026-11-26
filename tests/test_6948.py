"""6.9.48: Musik-Seite (Musik-Archiv) im Stil einer Musik-App - ohne Schlaf-Timer, mit Alben, Lieblingsliedern, Zufall."""
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
from test_hoerbuch import starte_attrappe  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

TAG = datetime(2026, 11, 25, 16, 0)


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.att, cls.link = starte_attrappe()

    @classmethod
    def tearDownClass(cls):
        cls.att.shutdown()

    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-6948-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(TAG))
        self.hub.einstellungen_aendern({"archiv": {"musik": {"ordner": self.link, "freigaben": {"Bibi Blocksberg": {}}}}})

    def test_favoriten_nur_freigegeben(self):
        self.assertEqual(self.hub.favoriten("archiv-musik"), [])
        self.hub.favorit_setzen("archiv-musik", "Bibi Blocksberg/Folge 1.wav", True)
        self.hub.favorit_setzen("archiv-musik", "Bibi Blocksberg/Folge 2.wav", True)
        self.assertEqual(self.hub.favoriten("archiv-musik"), ["Bibi Blocksberg/Folge 2.wav", "Bibi Blocksberg/Folge 1.wav"])
        self.hub.favorit_setzen("archiv-musik", "Bibi Blocksberg/Folge 1.wav", False)
        self.assertEqual(self.hub.favoriten("archiv-musik"), ["Bibi Blocksberg/Folge 2.wav"])
        with self.assertRaises(ValueError):
            self.hub.favorit_setzen("archiv-musik", "Die drei ??? Kids/01 Teil Eins.wav", True)

    def test_musik_ist_kein_einschlaf_hoerbuch(self):
        self.hub.starte("archiv-musik")
        self.hub.hoerbuch_stand("archiv-musik", "Bibi Blocksberg", "Bibi Blocksberg/Folge 1.wav", 3, spielt=True)
        self.assertFalse(self.hub.hoerbuch_laeuft(), "Musik macht den Fernseher nicht still (Erinnerungen kommen weiter)")
        self.assertFalse(self.hub.still())

    def test_cover_nur_freigegeben(self):
        self.assertIsNotNone(self.hub.hoerbuch_cover("archiv-musik", "Bibi Blocksberg"))
        self.assertIsNone(self.hub.hoerbuch_cover("archiv-musik", "Die drei ??? Kids"))


class Seite(unittest.TestCase):
    def test_musik_seite_ohne_schlaf_timer(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("kein Playwright")
        from fernsehfranzi import web
        from test_spiele_wie_am_geraet import port_frei
        if not port_frei(8765):
            self.skipTest("Port 8765 belegt")
        att, link = starte_attrappe()
        self.addCleanup(att.shutdown)
        ordner = tempfile.mkdtemp(prefix="ff-6948s-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(TAG))
        hub.einstellungen_aendern({"archiv": {"musik": {"ordner": link, "freigaben": {"Bibi Blocksberg": {}, "Einzeln.wav": {}}}}})
        srv = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        with sync_playwright() as pw:
            b = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
            s = b.new_page(viewport={"width": 1280, "height": 720})
            fehler = []
            s.on("pageerror", lambda e: fehler.append(str(e)))
            s.goto("http://127.0.0.1:8765/")
            s.wait_for_selector(".kachel")
            s.wait_for_timeout(500)
            s.evaluate("FernsehFranzi.zeige('archiv-musik')")
            s.keyboard.press("Enter")
            s.wait_for_selector(".overlay.musik .mu-karte")
            self.assertEqual(s.locator(".mu-karte").count(), 2)            # Album + Einzelne Lieder
            s.keyboard.press("ArrowDown")
            s.keyboard.press("Enter")
            s.wait_for_selector(".mu-titel")
            self.assertEqual(s.locator(".mu-titel").count(), 3)
            s.keyboard.press("Enter")                                       # ersten Titel abspielen
            s.wait_for_selector(".mu-leiste:not([hidden]) .mu-jetzt b")
            self.assertEqual(s.locator(".hb-wahl, .hb-schwarz").count(), 0, "kein Schlaf-Timer, kein dunkles Bild")
            self.assertIn("Folge 1", s.inner_text(".mu-jetzt b"))
            s.keyboard.press("ArrowRight")                                  # ⭐ neben dem Titel
            s.keyboard.press("Enter")
            s.wait_for_selector(".mu-titel-reihe .mu-knopf.an")
            self.assertEqual(hub.favoriten("archiv-musik"), ["Bibi Blocksberg/Folge 1.wav"])
            s.keyboard.press("MediaTrackNext")
            s.wait_for_selector(".mu-jetzt b:has-text('Folge 2')")
            s.keyboard.press("Escape")                                      # zurück zu den Alben
            s.wait_for_selector(".mu-raster")
            self.assertEqual(fehler, [])
            b.close()


if __name__ == "__main__":
    unittest.main()
