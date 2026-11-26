"""6.8.3: Jede Welt klingt anders (Bedien-Töne), die normalen Farben bleiben beim gewohnten Klang."""
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

ZAEHLER = """window.__typen = [];
const O = window.OscillatorNode;
Object.defineProperty(O.prototype, 'type', { set(v) { window.__typen.push(v); }, get() { return 'sine'; }, configurable: true });"""


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class WeltKlaenge(unittest.TestCase):
    def test_klang_je_welt(self):
        ordner = tempfile.mkdtemp(prefix="ff-683-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(datetime(2026, 11, 18, 15, 0)))
        server = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
            seite = browser.new_page(viewport={"width": 1600, "height": 900})
            seite.add_init_script(ZAEHLER)
            for thema, typ in (("blau", "triangle"), ("rock", "sawtooth"), ("unterwasser", "sine"), ("raumstation", "square")):
                hub.einstellungen_aendern({"startseite": dict(hub.einstellungen.get("startseite") or {}, thema=thema)})
                seite.goto("http://127.0.0.1:8765/")
                seite.wait_for_selector(".kachel")
                seite.wait_for_timeout(300)
                seite.evaluate("window.__typen = []")
                seite.keyboard.press("ArrowDown")                       # Bewegen auf der Startseite
                seite.wait_for_function("window.__typen.length > 0")
                self.assertEqual(seite.evaluate("window.__typen[0]"), typ, thema)
            browser.close()


if __name__ == "__main__":
    unittest.main()
