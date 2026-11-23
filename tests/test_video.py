"""4.0 Video-Player aus einer FileBrowser-Freigabe: Ordner mit Cover, Abspielen, Weiterschauen."""
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

import test_hoerbuch  # noqa: E402
from fernsehfranzi import web  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def testvideo():
    """14 s Testbild (WebM/VP8 - der Test-Chromium kann kein H.264), erzeugt mit ffmpeg testsrc."""
    with open(os.path.join(REPO, "tests", "daten", "testfilm.webm"), "rb") as f:
        return f.read()


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class VideoPlayer(unittest.TestCase):
    def test_filme_abspielen_und_weiterschauen(self):
        alt = dict(test_hoerbuch.BAUM)
        test_hoerbuch.BAUM.clear()
        test_hoerbuch.BAUM.update({"Filme": {"Testfilm.webm": testvideo(), "cover.png": test_hoerbuch.PNG}})
        self.addCleanup(lambda: (test_hoerbuch.BAUM.clear(), test_hoerbuch.BAUM.update(alt)))
        attrappe, link = test_hoerbuch.starte_attrappe()
        self.addCleanup(attrappe.shutdown)
        ordner = tempfile.mkdtemp(prefix="ff-vid-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(datetime(2026, 11, 18, 15, 0)))
        hub.katalog_aendern(hub.eltern_daten()["apps"] + [{"id": "filme", "name": "Filme", "typ": "video", "start": link,
            "zeit": "zaehlt", "sperr_erlaubt": [], "eingabe": "tasten", "domains": [], "aktiv": True, "symbol": "film"}])
        server = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
            seite = browser.new_page(viewport={"width": 1600, "height": 900})
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            seite.goto("http://127.0.0.1:8765/")
            seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('filme')")
            seite.click(".kachel[data-id=filme]")
            seite.wait_for_selector(".vid-liste .hb-eintrag img.hb-cover")             # Ordner mit Cover
            seite.keyboard.press("Enter")
            seite.wait_for_selector("text=Testfilm")
            seite.keyboard.press("ArrowDown")
            seite.keyboard.press("Enter")
            seite.wait_for_function("() => { const v = document.querySelector('.vid-video'); return v && v.currentTime > 1; }", timeout=15000)
            seite.keyboard.press("ArrowRight")                                          # 10 s vor
            self.assertGreater(seite.evaluate("document.querySelector('.vid-video').currentTime"), 9)
            seite.keyboard.press("Escape")                                              # zurück zur Liste, Stelle gemerkt
            seite.wait_for_selector(".vid-video", state="detached")
            seite.wait_for_timeout(500)
            self.assertGreater(hub.hoerbuch_liste("filme")["stand"]["sekunde"], 9)
            seite.keyboard.press("ArrowLeft")                                           # Ordner hoch
            seite.wait_for_selector("text=Weiterschauen")
            self.assertEqual(fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()
