"""6.9.56: Shop-Vorschau - gewählter Gegenstand erscheint im Zimmer (Kleidung an Franzi, Möbel im Raum, Raum als Ansicht)."""
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


class Vorschau(unittest.TestCase):
    def test_vorschau_im_shop(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("kein Playwright")
        from fernsehfranzi import web
        from test_spiele_wie_am_geraet import port_frei
        if not port_frei(8765):
            self.skipTest("Port 8765 belegt")
        ordner = tempfile.mkdtemp(prefix="ff-6956-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(datetime(2026, 11, 28, 15)))
        hub.einstellungen["franzi"] = {"aktiv": True}
        srv = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            s = b.new_page(viewport={"width": 1280, "height": 720})
            fehler = []
            s.on("pageerror", lambda e: fehler.append(str(e)))
            s.goto("http://127.0.0.1:8765/#spiel-franzi")
            s.wait_for_selector(".fz-raum")
            s.wait_for_timeout(600)
            s.keyboard.press("ArrowRight"); s.keyboard.press("ArrowRight")          # Shop
            def bis(text):
                for _ in range(80):
                    if s.locator(".gewaehlt .titel, .gewaehlt").filter(has_text=text).count():
                        return
                    s.keyboard.press("ArrowDown")
                self.fail("nicht gefunden: " + text)
            bis("Musikbox")
            s.wait_for_selector(".fz-vorschau-text:has-text('Franzi tanzt')")
            self.assertEqual(s.locator('.fz-ding[data-ding="spielzeug-musikbox"].fz-einrichten').count(), 1)
            bis("Krone")
            s.wait_for_selector(".fz-vorschau-text:has-text('anziehen')")
            bis("Level 2")                                                             # Level-Belohnung Sonnenzimmer: Raum als Ansicht
            s.wait_for_selector('.fz-raum[data-raum="raum-hell"]')
            s.keyboard.press("ArrowLeft")                                              # Reiter wechseln: wieder das eigene Zimmer
            s.wait_for_selector('.fz-raum[data-raum="raum-zimmer"]')
            self.assertEqual(s.locator(".fz-vorschau-text").count(), 0)
            self.assertEqual(fehler, [])
            b.close()


if __name__ == "__main__":
    unittest.main()
