"""6.6: Weckszenen Ostsee und Wald - Szene je Wecker, eigene Bilder und selbst erzeugte Geräusche."""
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

from fernsehfranzi import web, wecker  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

FRUEH = datetime(2026, 11, 18, 6, 50)


class Szene(unittest.TestCase):
    def test_pruefen(self):
        w = {"aktiv": True, "liste": [{"nr": 1, "zeit": "07:00", "tage": [2], "sonne": 10, "szene": "ostsee"}]}
        wecker.pruefe(w)
        w["liste"][0]["szene"] = "mond"
        with self.assertRaises(ValueError):
            wecker.pruefe(w)

    def test_auftrag_mit_szene(self):
        ordner = tempfile.mkdtemp(prefix="ff-66-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(FRUEH))
        hub.einstellungen_aendern({"wecker": {"aktiv": True, "liste": [
            {"nr": 1, "zeit": "07:00", "tage": [2], "sonne": 10, "szene": "wald"}]}})
        hub._wecker_takt(FRUEH)
        sonne = [a for a in hub.auftraege if a["art"] == "sonne"]
        self.assertEqual((sonne[-1]["minuten"], sonne[-1]["szene"]), (10, "wald"))


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class AmFernseher(unittest.TestCase):
    def test_szenen_zeigen(self):
        ordner = tempfile.mkdtemp(prefix="ff-66w-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(FRUEH))
        server = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
            seite = browser.new_page(viewport={"width": 1600, "height": 900})
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            seite.add_init_script("""window.__klaenge = 0; const A = window.AudioContext;
                window.AudioContext = class extends A { constructor(...a) { super(...a); window.__klaenge++; } };""")
            seite.goto("http://127.0.0.1:8765/")                         # erst die Startseite, dann je Szene zählen, wie viele Klang-Kontexte dazukommen
            seite.wait_for_selector(".kachel")
            seite.wait_for_timeout(2500)
            for szene, merkmal in (("ostsee", ".sa-meer"), ("wald", ".sa-h1"), ("huegel", ".sa-h1")):
                grund = seite.evaluate("window.__klaenge")
                seite.goto("http://127.0.0.1:8765/#sonne-1-" + szene)
                seite.wait_for_selector(".overlay.sonne.szene-%s %s" % (szene, merkmal))
                seite.wait_for_timeout(2500)
                if szene == "ostsee":
                    seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "66-ostsee.png"))
                klaenge = seite.evaluate("window.__klaenge") - grund
                self.assertEqual(klaenge >= 1, szene != "huegel", szene + ": Geräusche nur bei Ostsee und Wald")
            seite.goto("http://127.0.0.1:8765/#sonne-1")                 # alte Adresse (vor 6.6) geht weiter
            seite.wait_for_selector(".overlay.sonne.szene-huegel")
            self.assertEqual(fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()
