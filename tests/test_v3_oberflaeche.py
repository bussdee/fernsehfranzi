"""Startseite 3.0 im Headless-Chromium gegen einen echten Server 3.0 (Systemaufrufe als Attrappe).

Der Server läuft auf 127.0.0.1:8765 (wie auf dem Gerät), damit die Herkunftsprüfung echt greift.
"""
import os
import shutil
import socket
import sys
import tempfile
import threading
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import web  # noqa: E402
from test_v3_server import MITTWOCH, Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def port_frei(port):
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class Startseite3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ordner = tempfile.mkdtemp(prefix="ff-ui3-")
        cls.hub = neuer_hub(cls.ordner, Uhr(MITTWOCH))
        cls.server = web.baue_server(web.KioskHandler, cls.hub, os.path.join(REPO, "web"),
                                     os.path.join(cls.ordner, "zeichnungen"), ("127.0.0.1", 8765))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(args=["--enable-spatial-navigation", "--autoplay-policy=no-user-gesture-required"])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.ordner, True)

    def seite(self):
        # bypass_csp: die strenge CSP der Startseite verbietet sonst auch die Prüfskripte des Tests
        seite = self.browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
        self.addCleanup(seite.close)
        self.fehler = []
        seite.on("pageerror", lambda e: self.fehler.append(str(e)))
        seite.goto("http://127.0.0.1:8765/")
        seite.wait_for_selector(".kachel")
        return seite

    def test_kacheln_aus_dem_katalog(self):
        seite = self.seite()
        # 6.0: „Zuhause“ zeigt die Bereiche, die Apps liegen in den Bereichen
        self.assertEqual(seite.locator(".zeile-kacheln.bereiche .kachel .name").all_text_contents(),
                         ["Spiele", "Filme", "Musik", "Lernen", "Mein Zimmer", "Retro"])
        namen = seite.evaluate("FernsehFranzi.zustand.alle.map(a => a.name)")
        for name in ("Plex", "Games", "Klassenkiste", "Kinderwelten", "Snake", "Farben-Echo", "Musik-Akademie"):
            self.assertIn(name, namen)
        seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('plex')")
        self.assertEqual(seite.locator("[data-id=plex] .sperr-symbol").text_content(), "⚙️")   # 3.4: Symbol statt Text
        seite.wait_for_function("document.getElementById('restzeit').textContent.includes('Minuten')")
        self.assertEqual(self.fehler, [])

    def test_spiel_oeffnen_und_schliessen(self):
        seite = self.seite()
        seite.keyboard.press("ArrowDown")      # 6.0: Reihe „Bereiche“, erste Kachel „Spiele“
        seite.keyboard.press("Enter")          # Bereich öffnen: Snake steht vorne
        seite.wait_for_selector("#pfad:has-text('Spiele')")
        seite.keyboard.press("Enter")
        seite.keyboard.press("Enter")          # gleich danach: gehört schon dem Spiel (Tempostufe)
        seite.wait_for_selector("canvas.spielfeld")
        self.assertEqual(self.hub.aktuell, "spiel-snake")
        seite.keyboard.press("Escape")
        seite.wait_for_selector(".overlay", state="detached")
        seite.keyboard.press("Escape")         # 6.0: STOP führt zurück nach „Zuhause“
        seite.wait_for_selector(".zeile-kacheln.bereiche")
        seite.wait_for_function("true")
        self.assertEqual(self.fehler, [])

    def test_web_app_wird_kiosk_auftrag(self):
        seite = self.seite()
        seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('klassenkiste')")
        seite.locator("[data-id=klassenkiste]").click()
        seite.wait_for_function("document.getElementById('hinweis').textContent.includes('startet')")
        auftraege, _ = self.hub.auftraege_nach(0)
        self.assertIn(("oeffne", "https://klassenkiste.eu/"), [(a["art"], a.get("url")) for a in auftraege])

    def test_elternbereich_erste_pin_und_anmelden(self):
        seite = self.seite()
        seite.evaluate("window.FernsehFranzi.oeffneEltern()")
        seite.wait_for_selector(".pinfeld")
        for _ in range(2):
            for ziffer in "482913":
                seite.keyboard.press(ziffer)
            seite.keyboard.press("Enter")
            seite.wait_for_timeout(300)
        seite.wait_for_function("document.querySelector('.overlay h2').textContent.includes('PIN')")
        for ziffer in "482913":
            seite.keyboard.press(ziffer)
        seite.keyboard.press("Enter")
        seite.wait_for_function("document.querySelector('.overlay h2').textContent === 'Elternbereich'")
        self.assertIn("+15 Minuten", seite.locator(".overlay").text_content())
        self.assertEqual(self.fehler, [])


if __name__ == "__main__":
    unittest.main()
