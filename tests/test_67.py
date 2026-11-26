"""6.7: Welten - Rock, Unterwasser, Raumstation mit Hintergrund, Bewegung und Franzi-Ausstattung."""
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

from fernsehfranzi import design, web  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ABEND = datetime(2026, 11, 18, 20, 0)


class Welten(unittest.TestCase):
    def test_welten_sind_dunkel_und_haben_ein_motiv(self):
        for w in design.WELTEN:
            self.assertIn(w, design.KENNUNGEN)
            self.assertNotIn(w, design.HELL)
            self.assertTrue(os.path.exists(os.path.join(REPO, "web", "hintergrund", w + ".svg")))

    def test_abends_bleibt_die_welt(self):
        ordner = tempfile.mkdtemp(prefix="ff-67-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(ABEND))
        hub.einstellungen_aendern({"design": {"abend_aktiv": True, "abend_ab": "19:00"}})
        self.assertEqual(design.fuer_startseite(hub.einstellungen.get("design"), {"thema": "rock"}, ABEND)["jetzt"], "rock")


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class AmFernseher(unittest.TestCase):
    def test_rock_mit_flammen_und_sonnenbrille(self):
        ordner = tempfile.mkdtemp(prefix="ff-67w-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(datetime(2026, 11, 18, 15, 0)))
        server = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            seite = browser.new_page(viewport={"width": 1600, "height": 900})
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            for welt, teil, franzi in (("rock", ".welt-flamme", "#111"), ("unterwasser", ".welt-blase", "kleid-taucher"),
                                       ("raumstation", ".welt-stern", "rgba(200,230,255")):
                hub.startseite_setzen({"thema": welt}) if hasattr(hub, "startseite_setzen") else \
                    hub.einstellungen_aendern({"startseite": dict(hub.einstellungen.get("startseite") or {}, thema=welt)})
                seite.goto("http://127.0.0.1:8765/")
                seite.wait_for_selector("#welt-deko[data-welt=%s] %s" % (welt, teil))
                seite.wait_for_function("document.querySelector('#franzi-kopf svg')?.innerHTML.includes(%r)" % franzi)
                if welt == "rock":
                    seite.wait_for_timeout(800)
                    seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "67-rock.png"))
            hub.einstellungen_aendern({"startseite": dict(hub.einstellungen.get("startseite") or {}, thema="blau")})
            seite.goto("http://127.0.0.1:8765/")
            seite.wait_for_selector(".kachel")
            self.assertEqual(seite.locator("#welt-deko").count(), 0, "normale Farben ohne Bewegung")
            self.assertEqual(fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()
