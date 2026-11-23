"""3.5 Musik-Akademie: Instrumente (Gitarre, Keyboard, Singen) im Browser, Song-Suche auf ultimate-guitar.com."""
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import web  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

NACHMITTAG = datetime(2026, 11, 18, 15, 0)
FOTOS = os.path.join(REPO, ".local", "bildschirm")


class SongSuche(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-musik-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(NACHMITTAG))

    def test_suche_oeffnet_ultimate_guitar_und_zaehlt_als_lernen(self):
        ok, text = self.hub.musik_suche("  wonderwall   oasis ")
        self.assertTrue(ok)
        auftrag = self.hub.auftraege[-1]
        self.assertEqual(auftrag["url"], "https://www.ultimate-guitar.com/search.php?search_type=title&value=wonderwall+oasis")
        self.assertEqual(self.hub.aktuell, "spiel-bass")
        self.hub.kiosk_ort("https://tabs.ultimate-guitar.com/tab/oasis/wonderwall-chords-27596")
        self.assertEqual(self.hub.aktuell, "spiel-bass", "Akkordseite gehört zur Akademie (Lernen)")
        with self.assertRaises(ValueError):
            self.hub.musik_suche("a")

    def test_ultimate_guitar_in_der_whitelist(self):
        self.hub.richtlinie_aktualisieren()
        with open(os.path.join(self.ordner, "whitelist-richtlinie.json")) as f:
            self.assertIn("tabs.ultimate-guitar.com", json.load(f)["domains"])

    def test_heisst_musik_akademie(self):
        self.assertEqual(next(k for k in self.hub.kacheln() if k["id"] == "spiel-bass")["name"], "Musik-Akademie")


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class AkademieImBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ordner = tempfile.mkdtemp(prefix="ff-musik-")
        cls.hub = neuer_hub(cls.ordner, Uhr(NACHMITTAG))
        cls.server = web.baue_server(web.KioskHandler, cls.hub, os.path.join(REPO, "web"),
                                     os.path.join(cls.ordner, "zeichnungen"), ("127.0.0.1", 8765))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                                                   "--autoplay-policy=no-user-gesture-required"])
        os.makedirs(FOTOS, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.ordner, True)

    def seite(self):
        seite = self.browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
        self.addCleanup(seite.close)
        self.fehler = []
        seite.on("pageerror", lambda e: self.fehler.append(str(e)))
        seite.goto("http://127.0.0.1:8765/")
        seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-bass')")
        seite.click(".kachel[data-id=spiel-bass]")
        seite.wait_for_selector("text=Was möchtest du heute machen?")
        return seite

    def waehle(self, seite, text):
        knoepfe = seite.locator(".knopfreihe .knopf").all_inner_texts()
        ziel = next(i for i, t in enumerate(knoepfe) if text in t)
        jetzt = next(i for i, k in enumerate(seite.locator(".knopfreihe .knopf").all()) if "gewaehlt" in (k.get_attribute("class") or ""))
        for _ in range(ziel - jetzt):
            seite.keyboard.press("ArrowRight")
        seite.keyboard.press("Enter")

    def test_instrumente(self):
        seite = self.seite()
        menue = " ".join(seite.locator(".knopfreihe .knopf").all_inner_texts())
        for teil in ("Bass", "Gitarre", "Keyboard", "Singen", "Song suchen", "Meine Songs"):
            self.assertIn(teil, menue)
        self.waehle(seite, "Gitarre")
        self.waehle(seite, "Akkorde")
        seite.wait_for_selector(".griffbild-box svg")
        self.assertEqual(seite.inner_text(".akkord-name"), "C")
        seite.keyboard.press("ArrowRight")
        self.assertEqual(seite.inner_text(".akkord-name"), "D")
        seite.screenshot(path=os.path.join(FOTOS, "musik-akkorde.png"))
        seite.keyboard.press("Escape")                                  # zurück ins Gitarren-Menü
        seite.wait_for_selector("text=🎸 Gitarre")
        seite.keyboard.press("Escape")                                  # zurück ins Hauptmenü
        seite.wait_for_selector("text=Was möchtest du heute machen?")
        self.waehle(seite, "Keyboard")
        self.waehle(seite, "Akkorde zeigen")
        seite.wait_for_selector(".klaviatur")
        self.assertEqual(seite.locator(".taste-weiss.an").count() + seite.locator(".taste-schwarz.an").count(), 3)
        seite.screenshot(path=os.path.join(FOTOS, "musik-keyboard.png"))
        seite.keyboard.press("Escape")
        seite.keyboard.press("Escape")
        self.waehle(seite, "Singen")
        self.waehle(seite, "Ton treffen")
        seite.wait_for_selector(".sing-saeule")
        seite.wait_for_timeout(800)
        seite.screenshot(path=os.path.join(FOTOS, "musik-singen.png"))
        self.assertEqual(self.fehler, [])

    def test_aufnehmen_und_anhoeren(self):
        seite = self.seite()
        self.waehle(seite, "Aufnehmen")
        seite.wait_for_selector(".rec-pegel")
        seite.keyboard.press("Enter")                                   # Aufnahme an
        seite.wait_for_function("() => document.querySelector('.rec-status').textContent.includes('🔴')")
        seite.wait_for_timeout(1500)
        seite.keyboard.press("Enter")                                   # Aufnahme aus
        seite.wait_for_function("() => document.querySelector('.akkord-leiste').textContent.includes('Aufnahme 1')")
        seite.evaluate("t => document.dispatchEvent(new KeyboardEvent('keydown', {key: 'MediaPlay', bubbles: true}))", None)
        seite.wait_for_timeout(300)
        self.assertEqual(self.fehler, [])

    def test_song_suche(self):
        seite = self.seite()
        self.waehle(seite, "Song suchen")
        seite.wait_for_selector(".such-tastatur")
        for taste in "abba":
            seite.keyboard.press(taste)                                 # echte Tastatur geht auch
        self.assertEqual(seite.inner_text(".such-feld"), "abba")
        for _ in range(4):
            seite.keyboard.press("ArrowDown")                           # bis zu „Suchen“
        seite.keyboard.press("Enter")
        seite.wait_for_timeout(500)
        self.assertIn("value=abba", self.hub.auftraege[-1]["url"])
        seite.screenshot(path=os.path.join(FOTOS, "musik-suche.png"))
        self.assertEqual(self.fehler, [])


if __name__ == "__main__":
    unittest.main()
