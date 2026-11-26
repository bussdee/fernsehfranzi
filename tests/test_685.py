"""6.8.5: „Ich brauche Hilfe“ - Kachel nur mit Erlaubnis und Telegram, Nachricht an die Eltern, höchstens alle 2 Minuten."""
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

from fernsehfranzi import telegram, web  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_telegram44 import TOKEN  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class Hilfe(unittest.TestCase):
    def setUp(self):
        alt, telegram.BASIS = telegram.BASIS, "http://127.0.0.1:9"        # nie ins Netz
        self.addCleanup(setattr, telegram, "BASIS", alt)
        self.ordner = tempfile.mkdtemp(prefix="ff-685-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(datetime(2026, 11, 18, 15, 0))
        self.hub = neuer_hub(self.ordner, self.uhr)
        self.gesendet = []
        self.hub.telegram.melde_eltern = lambda art, text: (self.gesendet.append((art, text)), ["Papa"])[1]
        self.addCleanup(lambda: self.hub.einstellungen_aendern({"telegram": {"aktiv": False, "token": TOKEN}}))

    def ids(self):
        return [k["id"] for k in self.hub.kacheln()]

    def test_ab_werk_aus_und_nur_mit_telegram(self):
        self.assertNotIn("spiel-hilfe", self.ids())
        self.hub.einstellungen_aendern({"hilfe": {"aktiv": True}})
        self.assertNotIn("spiel-hilfe", self.ids(), "ohne Telegram keine Kachel")
        with self.assertRaises(ValueError):
            self.hub.hilfe_rufen()
        self.hub.einstellungen_aendern({"telegram": {"aktiv": True, "token": TOKEN, "chats": [{"id": 111, "name": "Papa"}]}})
        self.assertIn("spiel-hilfe", self.ids())
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"hilfe": {"aktiv": "ja"}})

    def test_nachricht_und_pause(self):
        self.hub.einstellungen_aendern({"hilfe": {"aktiv": True}, "name": "Kind",
                                        "telegram": {"aktiv": True, "token": TOKEN, "chats": [{"id": 111, "name": "Papa"}]}})
        self.assertEqual(self.hub.hilfe_rufen(), {"gesendet": ["Papa"], "schon": False})
        self.assertEqual(self.gesendet, [("hilfe", "🆘 Kind braucht Hilfe und hat am Fernseher den Hilfe-Knopf gedrückt (15:00 Uhr).")])
        self.assertTrue(self.hub.hilfe_rufen()["schon"], "zweimal drücken: keine zweite Nachricht")
        self.uhr.weiter(121)
        self.assertFalse(self.hub.hilfe_rufen()["schon"])
        self.assertEqual(len(self.gesendet), 2)
        self.assertIn("hilfe", telegram.MELDUNG_ARTEN)


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class AmFernseher(Hilfe):
    def test_knopf_am_fernseher(self):
        self.hub.einstellungen_aendern({"hilfe": {"aktiv": True},
                                        "telegram": {"aktiv": True, "token": TOKEN, "chats": [{"id": 111, "name": "Papa"}]}})
        server = web.baue_server(web.KioskHandler, self.hub, os.path.join(REPO, "web"), os.path.join(self.ordner, "z"), ("127.0.0.1", 8765))
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
            seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-hilfe')")
            seite.click("[data-id=spiel-hilfe]")
            seite.wait_for_selector(".hilfe-knopf")
            seite.keyboard.press("Enter")
            seite.wait_for_selector(".hilfe-text:has-text('wissen Bescheid')")
            self.assertEqual(len(self.gesendet), 1)
            seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "685-hilfe.png"))
            self.assertEqual(fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()
