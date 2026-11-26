"""6.8.8: Witze mit mehreren Zeilen - jede Zeile erscheint mit OK; eigene Witze der Eltern als mehrzeiliger Text."""
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

EIGEN = ["Zwei Kühe auf der Weide.", "Sagt die eine: „Muh.“", "Sagt die andere: „Das wollte ich auch gerade sagen!“"]


class Pruefen(unittest.TestCase):
    def test_alte_und_neue_witze(self):
        ordner = tempfile.mkdtemp(prefix="ff-688-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(datetime(2026, 11, 18, 15, 0)))
        hub.einstellungen_aendern({"inhalte": {"witze": [{"zeilen": EIGEN}, {"frage": "Was ist grün?", "pointe": "Ein Frosch."}]}})
        for falsch in ({"zeilen": []}, {"zeilen": ["x"] * 11}, {"zeilen": ["x" * 201]}, {"zeilen": ["ok"], "pointe": "x"}):
            with self.assertRaises(ValueError):
                hub.einstellungen_aendern({"inhalte": {"witze": [falsch]}})


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class AmFernseher(unittest.TestCase):
    def test_zeile_fuer_zeile(self):
        ordner = tempfile.mkdtemp(prefix="ff-688w-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(datetime(2026, 11, 18, 15, 0)))
        hub.einstellungen_aendern({"inhalte": {"witze": [{"zeilen": EIGEN}]}})
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
            seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-witz')")
            seite.click("[data-id=spiel-witz]")
            seite.wait_for_selector(".witz .witz-zeile")
            seite.wait_for_timeout(500)                                    # eigene Witze sind nachgeladen
            for _ in range(80):                                           # bis zum eigenen (letzten) Witz blättern
                if seite.inner_text(".witz .witz-zeile") == EIGEN[0]:
                    break
                seite.keyboard.press("ArrowLeft")
            self.assertEqual(seite.locator(".witz .witz-zeile").all_inner_texts(), EIGEN[:1])
            seite.keyboard.press("Enter")
            self.assertEqual(seite.locator(".witz .witz-zeile").all_inner_texts(), EIGEN[:2])
            seite.keyboard.press("Enter")
            self.assertEqual(seite.locator(".witz .witz-zeile").all_inner_texts(), EIGEN)
            self.assertEqual(seite.locator(".witz .witz-zeile.pointe").inner_text(), EIGEN[2])
            seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "688-witz.png"))
            seite.keyboard.press("Enter")                                 # nächster Witz: wieder nur die erste Zeile
            self.assertEqual(seite.locator(".witz .witz-zeile").count(), 1)
            self.assertEqual(fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()
