"""6.9.50: Musikbox im Sterne-Shop - Musik aus dem Musik-Archiv in Franzis Zimmer, Franzi tanzt im Takt."""
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
from fernsehfranzi import franzi  # noqa: E402
from test_hoerbuch import starte_attrappe  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

TAG = datetime(2026, 11, 28, 15)


class Server(unittest.TestCase):
    def test_musikbox_nur_mit_musik_archiv_und_besitz(self):
        self.assertIn("spielzeug-musikbox", franzi.KATALOG_IDS)
        z = franzi.neu(TAG)
        ein = franzi.einstellungen({"aktiv": True})
        self.assertFalse(franzi.fuer_tv(ein, z, TAG, 0, musik=True)["musikbox"])          # noch nicht gekauft
        z["besitz"].append("spielzeug-musikbox")
        self.assertFalse(franzi.fuer_tv(ein, z, TAG, 0, musik=False)["musikbox"])         # kein Musik-Archiv
        self.assertTrue(franzi.fuer_tv(ein, z, TAG, 0, musik=True)["musikbox"])


class Zimmer(unittest.TestCase):
    def test_franzi_tanzt(self):
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
        ordner = tempfile.mkdtemp(prefix="ff-6950-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(TAG))
        hub.einstellungen["franzi"] = {"aktiv": True}
        hub.einstellungen_aendern({"archiv": {"musik": {"ordner": link, "freigaben": {"Bibi Blocksberg": {}}}}})
        hub.franzi_stand(besuch=True)
        hub.franzi_zustand["besitz"].append("spielzeug-musikbox")
        srv = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        with sync_playwright() as pw:
            b = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
            s = b.new_page(viewport={"width": 1280, "height": 720})
            fehler = []
            s.on("pageerror", lambda e: fehler.append(str(e)))
            s.goto("http://127.0.0.1:8765/#spiel-franzi")
            s.wait_for_selector(".fz-raum")
            s.wait_for_timeout(700)
            for _ in range(12):                                            # 6.9.63: danach kommt noch „Etwas anfassen“
                if s.locator(".gewaehlt:has-text('Musik & tanzen')").count():
                    break
                s.keyboard.press("ArrowUp")
                s.wait_for_timeout(80)
            s.wait_for_selector(".gewaehlt:has-text('Musik & tanzen')")
            s.keyboard.press("Enter")
            s.wait_for_selector(".gewaehlt:has-text('Alles zufällig')")
            s.keyboard.press("ArrowDown")                                  # das Album
            s.keyboard.press("Enter")
            s.wait_for_selector(".fz-tanzt .fz-tanz-haltung.an")
            vorher = s.evaluate("[...document.querySelectorAll('.fz-tanzt .fz-tanz-haltung')].findIndex((h) => h.classList.contains('an'))")
            s.wait_for_timeout(1600)                                      # mindestens ein (Ersatz-)Schlag
            nachher = s.evaluate("[...document.querySelectorAll('.fz-tanzt .fz-tanz-haltung')].findIndex((h) => h.classList.contains('an'))")
            self.assertNotEqual(vorher, nachher, "Franzi wechselt im Takt die Haltung")
            self.assertEqual(s.locator(".fz-disco").count(), 1)
            s.keyboard.press("ArrowUp")                                    # Musik aus
            s.keyboard.press("Enter")
            s.wait_for_selector(".fz-tanzt", state="detached")
            self.assertEqual(fehler, [])
            b.close()


if __name__ == "__main__":
    unittest.main()
