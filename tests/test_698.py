"""6.9.8: Franzis Zimmer im echten Browser - öffnen, füttern, Shop (zweimal OK), Startspiel, Schrank, Tagebuch.
Bildschirmfotos: .local/bildschirm/franzi-*.png"""
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

from fernsehfranzi import meintag, web  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

FOTOS = os.path.join(REPO, ".local", "bildschirm")


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class FranziZimmer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ordner = tempfile.mkdtemp(prefix="ff-franzi-web-")
        cls.uhr = Uhr(datetime(2026, 11, 28, 15, 0))             # Samstag 15:00, keine Sperrzeit
        cls.hub = neuer_hub(cls.ordner, cls.uhr)
        cls.server = web.baue_server(web.KioskHandler, cls.hub, os.path.join(REPO, "web"),
                                     os.path.join(cls.ordner, "zeichnungen"), ("127.0.0.1", 8765))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
        os.makedirs(FOTOS, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.ordner, True)

    def setUp(self):
        self.hub.einstellungen["franzi"] = {"aktiv": True, "abenteuer_tage": 4, "preise": {}, "angebote": [
            {"nr": 1, "name": "20 Minuten extra", "symbol": "⏰", "art": "minuten", "minuten": 20, "preis": 3, "pro_woche": 1}]}
        self.hub.franzi_zustand = {}
        z = meintag.zustand_fuer(self.hub.meintag_zustand, self.uhr().date())
        z["sterne"] = 20
        self.hub.meintag_zustand = z

    def seite(self):
        seite = self.browser.new_page(viewport={"width": 1600, "height": 900})
        self.addCleanup(seite.close)
        self.fehler = []
        seite.on("pageerror", lambda e: self.fehler.append(str(e)))
        seite.goto("http://127.0.0.1:8765/#spiel-franzi")
        seite.wait_for_selector(".fz-raum .fz-figur")
        seite.wait_for_timeout(600)                               # Sperre gegen das Öffnungs-OK
        return seite

    def blase(self, seite):
        return seite.inner_text(".fz-blase")

    def test_zimmer_fuettern(self):
        seite = self.seite()
        self.assertIn("20", seite.inner_text(".overlay-kopf .punkte"))
        self.assertEqual(seite.locator(".fz-ding").count(), 2)    # Bett und Ball
        seite.keyboard.press("Enter")                            # Füttern
        seite.wait_for_function("() => document.querySelector('.fz-blase').textContent.includes('lecker')")
        seite.screenshot(path=os.path.join(FOTOS, "franzi-zimmer.png"))
        self.assertEqual(self.fehler, [])

    def test_shop_zweimal_ok_und_angebot(self):
        seite = self.seite()
        seite.keyboard.press("ArrowRight")
        seite.keyboard.press("ArrowRight")                       # Shop
        seite.wait_for_selector(".seite-eintrag.gewaehlt")
        self.assertIn("20 Minuten extra", seite.inner_text(".seite-eintrag.gewaehlt"))
        seite.keyboard.press("ArrowDown")                        # Memory
        seite.keyboard.press("Enter")
        seite.wait_for_function("() => document.querySelector('.seite-eintrag.gewaehlt').textContent.includes('Nochmal OK')")
        self.assertIn("20", seite.inner_text(".overlay-kopf .punkte"))     # noch nichts gekauft
        seite.keyboard.press("Enter")
        seite.wait_for_function("() => document.querySelector('.overlay-kopf .punkte').textContent.includes('12')")
        self.assertIn("Memory", self.blase(seite))
        self.assertEqual(seite.locator(".franzi-konfetti").count(), 0)    # keine fliegende Konfetti-Franzi (6.9.7)
        pos = seite.evaluate("getComputedStyle(document.querySelector('.fz-figur')).position")
        self.assertNotEqual(pos, "fixed")                           # die Franzi im Zimmer bleibt im Zimmer (6.9.8)
        seite.keyboard.press("ArrowUp")                          # Angebot
        seite.keyboard.press("Enter")
        seite.keyboard.press("Enter")
        seite.wait_for_function("() => document.querySelector('.overlay-kopf .punkte').textContent.includes('9')")
        seite.screenshot(path=os.path.join(FOTOS, "franzi-shop.png"))
        self.assertEqual(self.fehler, [])

    def test_startspiel_und_tagebuch(self):
        seite = self.seite()
        seite.keyboard.press("ArrowRight")                       # Spielen
        seite.keyboard.press("Enter")
        seite.wait_for_selector(".fz-spiel canvas.spielfeld")
        seite.keyboard.press("ArrowLeft")
        seite.wait_for_timeout(300)
        seite.keyboard.press("Escape")                           # zu kurz gespielt: Franzi bleibt gelassen
        seite.wait_for_function("() => document.querySelector('.fz-blase')?.textContent.includes('später')")
        for _ in range(3):
            seite.keyboard.press("ArrowRight")                   # Tagebuch
        seite.wait_for_function("() => document.body.innerText.includes('Hallo! Ich bin Franzi')")
        self.assertEqual(self.fehler, [])

    def test_schrank_raum_und_anziehen(self):
        self.hub.franzi_stand(besuch=True)
        self.hub.franzi_zustand["besitz"] += ["kleid-krone", "raum-garten"]
        seite = self.seite()
        for _ in range(3):
            seite.keyboard.press("ArrowRight")                   # Schrank & Zimmer
        seite.wait_for_selector(".seite-eintrag.gewaehlt")
        seite.keyboard.press("ArrowDown")                        # Garten
        seite.keyboard.press("Enter")
        seite.wait_for_selector('.fz-raum[data-raum="raum-garten"]')
        seite.wait_for_timeout(300)
        seite.screenshot(path=os.path.join(FOTOS, "franzi-garten.png"))
        seite.keyboard.press("ArrowDown")                        # Krone
        seite.keyboard.press("Enter")
        seite.wait_for_function("() => document.querySelector('.seite-eintrag.gewaehlt').textContent.includes('✔ an')")
        self.assertEqual(self.fehler, [])

    def test_aus_keine_kachel(self):
        ids = lambda: [k["id"] for k in self.hub.kacheln()]
        self.assertIn("spiel-franzi", ids())
        self.assertNotIn("spiel-memory", ids())                    # 6.9.13: wohnt bei Franzi
        self.assertNotIn("spiel-huepfen", ids())                   # 6.9.14
        self.assertIn("spiel-steine", ids())                       # große Spiele bleiben
        self.hub.einstellungen["franzi"]["aktiv"] = False
        self.assertNotIn("spiel-franzi", ids())
        self.assertIn("spiel-memory", ids())                       # Franzi aus: alles wie vorher

if __name__ == "__main__":
    unittest.main()
