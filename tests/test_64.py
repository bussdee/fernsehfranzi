"""6.4: Sterne ergeben Level, Franzi bekommt Sachen, Tausch gegen Spielzeit (ab Werk aus), Wochenrückblick am Sonntag."""
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

MITTWOCH = datetime(2026, 11, 18, 17, 0)
SONNTAG = datetime(2026, 11, 22, 10, 0)
EINST = {"aktiv": True, "routinen": [{"nr": 1, "name": "Abend", "zeit": "18:00", "fertig": "19:00", "tage": list(range(7)),
                                      "schritte": [{"text": "Zähne putzen"}]}]}


class Logik(unittest.TestCase):
    def test_tausch_ab_werk_aus(self):
        m = meintag.pruefe(EINST)
        self.assertFalse(m["tausch"]["aktiv"])
        self.assertIsNone(meintag.heute(m, MITTWOCH, False, {})["tausch"])
        with self.assertRaises(ValueError):
            meintag.tauschen(m, MITTWOCH, {"sterne": 5})
        for falsch in ({"aktiv": True, "minuten": 0}, {"aktiv": True, "minuten": 31}, {"aktiv": "ja"}, {"max_tag": 500}):
            with self.assertRaises(ValueError):
                meintag.pruefe(dict(EINST, tausch=falsch))

    def test_tausch_einstellbar_mit_tagesgrenze(self):
        m = meintag.pruefe(dict(EINST, tausch={"aktiv": True, "minuten": 10, "max_tag": 20}))
        z = meintag.zustand_fuer({}, MITTWOCH.date())
        meintag.sterne_geben(z, MITTWOCH, 3)
        z, minuten = meintag.tauschen(m, MITTWOCH, z)
        self.assertEqual(minuten, 10)
        z, _ = meintag.tauschen(m, MITTWOCH, z)
        with self.assertRaises(ValueError):
            meintag.tauschen(m, MITTWOCH, z)                        # 20 min am Tag erreicht
        self.assertEqual((z["sterne"], z["verdient"]), (1, 3), "Tauschen senkt den Stand, nicht das Level")
        self.assertEqual(meintag.heute(m, MITTWOCH, False, z)["tausch"], {"minuten": 10, "rest_min": 0})

    def test_level_und_sachen(self):
        z = meintag.zustand_fuer({}, MITTWOCH.date())
        with self.assertRaises(ValueError):
            meintag.franzi_setzen(z, "hut", "muetze")                # Level 1: noch nichts
        meintag.sterne_geben(z, MITTWOCH, 10)
        self.assertEqual(meintag.level(z["verdient"]), 2)
        meintag.franzi_setzen(z, "hut", "muetze")
        with self.assertRaises(ValueError):
            meintag.franzi_setzen(z, "hut", "krone")                 # erst ab Level 10
        with self.assertRaises(ValueError):
            meintag.franzi_setzen(z, "schuhe", "")
        h = meintag.heute(meintag.pruefe(EINST), MITTWOCH, False, z)
        self.assertEqual(h["franzi"], {"hut": "muetze"})
        self.assertEqual((h["level"], h["naechstes_bei"]), (2, 20))
        meintag.franzi_setzen(z, "hut", "")
        self.assertEqual(z["franzi"], {})

    def test_sterne_fuer_listen_und_altdaten(self):
        m = meintag.pruefe(EINST)
        z, _ = meintag.abhaken(m, MITTWOCH.replace(hour=18), False, {"datum": "2026-11-17", "sterne": 4}, 1, 0, True)
        self.assertEqual((z["sterne"], z["verdient"], z["listen_tage"]), (6, 6, {"2026-11-18": 1}),
                         "alter Stand (6.3, ohne verdient) zählt mit; 6.8.9: bis „fertig um“ +1 Bonus-Stern")

    def test_bonus_stern_nur_puenktlich(self):
        """6.8.9: Liste bis „fertig um“ geschafft = 2 Sterne, danach = 1 Stern."""
        m = meintag.pruefe(EINST)
        z, _ = meintag.abhaken(m, MITTWOCH.replace(hour=19, minute=10), False, {}, 1, 0, True)       # fertig um 19:00
        self.assertEqual(z["sterne"], 1)
        self.assertFalse(meintag.heute(m, MITTWOCH.replace(hour=19, minute=10), False, z)["routinen"][0]["puenktlich"])
        z, _ = meintag.abhaken(m, MITTWOCH.replace(hour=18, minute=30), False, {}, 1, 0, True)
        self.assertEqual(z["sterne"], 2)
        self.assertTrue(meintag.heute(m, MITTWOCH.replace(hour=18, minute=30), False, z)["routinen"][0]["puenktlich"])

    def test_wochenrueckblick_nur_sonntags(self):
        m = meintag.pruefe(EINST)
        z = meintag.zustand_fuer({}, SONNTAG.date())
        z["sterne_tage"] = {"2026-11-16": 2, "2026-11-22": 3, "2026-11-10": 9}
        z["listen_tage"] = {"2026-11-20": 2}
        self.assertEqual(meintag.heute(m, SONNTAG, False, z)["woche"], {"sterne": 5, "listen": 2})
        self.assertIsNone(meintag.heute(m, MITTWOCH, False, z)["woche"])


class ImHub(unittest.TestCase):
    def test_tausch_gibt_bonus(self):
        ordner = tempfile.mkdtemp(prefix="ff-64-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(MITTWOCH))
        hub.einstellungen_aendern({"meintag": dict(EINST, tausch={"aktiv": True, "minuten": 7, "max_tag": 30})})
        hub.meintag_zustand = meintag.zustand_fuer(hub.meintag_zustand, MITTWOCH.date())
        meintag.sterne_geben(hub.meintag_zustand, MITTWOCH, 1)
        vorher = hub.konto._tag(MITTWOCH)["bonus_min"]
        h = hub.sterne_tauschen()
        self.assertEqual(hub.konto._tag(MITTWOCH)["bonus_min"], vorher + 7)
        self.assertEqual(h["sterne"], 0)
        self.assertIn("7 Minuten", hub.meldung["text"])


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class AmFernseher(unittest.TestCase):
    def test_franzi_anziehen_und_rueckblick(self):
        ordner = tempfile.mkdtemp(prefix="ff-64w-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(SONNTAG))
        hub.einstellungen_aendern({"meintag": EINST})
        hub.meintag_zustand = meintag.zustand_fuer({}, SONNTAG.date())
        meintag.sterne_geben(hub.meintag_zustand, SONNTAG, 12)
        server = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            seite = browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            seite.goto("http://127.0.0.1:8765/")
            seite.wait_for_selector(".kachel")
            seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-meintag')")
            seite.click("[data-id=spiel-meintag]")
            seite.wait_for_selector(".mt-woche")                     # Sonntag: Rückblick zuerst
            self.assertIn("⭐ 12 Sterne", seite.inner_text(".mt-woche"))
            self.assertIn("Level 2", seite.inner_text(".mt-franzi-info"))
            seite.keyboard.press("Enter")                            # erste Sache: Mütze (Level 2)
            seite.wait_for_selector(".mt-schritt.erledigt")
            self.assertEqual(hub.meintag_zustand["franzi"], {"hut": "muetze"})
            seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "64-franzi.png"))
            seite.keyboard.press("ArrowDown")                        # Blau: erst ab Level 3
            seite.keyboard.press("Enter")
            seite.wait_for_selector("#hinweis.zeigen:has-text('Level 3')")
            self.assertEqual(fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()
