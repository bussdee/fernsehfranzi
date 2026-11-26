"""4.4 Wecker klingelt: Pfeile wählen zwischen „Noch 5 Minuten“ und „Wecker aus“, OK bestätigt, STOP = aus.
Fehler aus dem Betrieb (23.11.2026): Jede Taste außer STOP war „Schlummern“ - der Wecker ging nicht aus."""
import os
import shutil
import sys
import tempfile
import threading
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import web  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_v3_server import MITTWOCH, Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class WeckerTasten(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-wt-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(MITTWOCH.replace(hour=7)))
        self.server = web.baue_server(web.KioskHandler, self.hub, os.path.join(REPO, "web"), os.path.join(self.ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def klingeln(self, seite):
        self.hub.wecker_laeuft = {"nr": 1, "zeit": "07:00", "ton": "", "laut": 50, "seit": 0, "vorher": None}
        seite.wait_for_selector(".wecker-klingelt .wecker-knoepfe")
        seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "wecker-klingelt.png"))   # 6.9.33

    def test_pfeil_dann_ok_schaltet_aus(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            seite = browser.new_page(viewport={"width": 1600, "height": 900})
            seite.goto("http://127.0.0.1:8765/")
            seite.wait_for_selector(".kachel")
            self.klingeln(seite)
            seite.keyboard.press("ArrowRight")
            seite.wait_for_timeout(300)
            self.assertIsNotNone(self.hub.wecker_laeuft, "ein Pfeil darf nichts bestätigen")
            self.assertEqual(seite.inner_text(".wecker-knoepfe .knopf.gewaehlt"), "⏹ Wecker aus")
            seite.keyboard.press("Enter")
            seite.wait_for_selector(".wecker-klingelt", state="detached")
            for _ in range(20):
                if self.hub.wecker_laeuft is None:
                    break
                seite.wait_for_timeout(100)
            self.assertIsNone(self.hub.wecker_laeuft)
            self.assertFalse(self.hub.wecker_schlummern if hasattr(self.hub, "wecker_schlummern") else False)
            # zweites Klingeln: OK ohne Pfeil = schlummern, STOP = aus
            self.klingeln(seite)
            seite.keyboard.press("Escape")
            seite.wait_for_selector(".wecker-klingelt", state="detached")
            browser.close()


if __name__ == "__main__":
    unittest.main()
