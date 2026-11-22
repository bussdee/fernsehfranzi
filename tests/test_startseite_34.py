"""3.4 im echten Browser: graue Kacheln mit Symbol, Meldungen bis OK, Nacht-Countdown, Gute Nacht mit Weiterhören
und Sternenhimmel. Bildschirmfotos: .local/bildschirm/start34-*.png"""
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
from test_hoerbuch import hoerbuch_app, medientaste, starte_attrappe  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

FOTOS = os.path.join(REPO, ".local", "bildschirm")


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class Startseite34(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ordner = tempfile.mkdtemp(prefix="ff-start34-")
        cls.attrappe, cls.link = starte_attrappe()
        cls.uhr = Uhr(datetime(2026, 11, 18, 21, 0))             # Mittwoch 21:00 = Nachtruhe
        cls.hub = neuer_hub(cls.ordner, cls.uhr)
        apps = [a for a in cls.hub.eltern_daten()["apps"] if a["id"] != "gute-nacht"] + [hoerbuch_app(cls.link)]
        cls.hub.katalog_aendern(apps)
        cls.server = web.baue_server(web.KioskHandler, cls.hub, os.path.join(REPO, "web"),
                                     os.path.join(cls.ordner, "zeichnungen"), ("127.0.0.1", 8765))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        os.makedirs(FOTOS, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.attrappe.shutdown()
        shutil.rmtree(cls.ordner, True)

    def setUp(self):
        # jeder Test beginnt wach (kein Gute-Nacht-Modus vom vorigen Test)
        self.hub.nachtruhe, self.hub._dunkel_bis, self.hub._hoerbuch_spielt_bis = False, 0, 0

    def seite(self, anker=""):
        seite = self.browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
        self.addCleanup(seite.close)
        self.fehler = []
        seite.on("pageerror", lambda e: self.fehler.append(str(e)))
        seite.add_init_script("window.__ffHoerbuch = { schwarzS: 2, minuteMs: 3000 };")
        seite.goto("http://127.0.0.1:8765/" + anker)
        seite.wait_for_selector(".kachel")
        return seite

    def test_gesperrte_kacheln_grau_mit_symbol(self):
        seite = self.seite()
        plex = seite.locator(".kachel[data-id=plex]")
        self.assertIn("gesperrt", plex.get_attribute("class"))
        self.assertEqual(plex.locator(".sperr-symbol").inner_text(), "🌙")         # Nachtsperre geht vor
        snake = seite.locator(".kachel[data-id=spiel-snake]")
        self.assertEqual(snake.locator(".sperr-symbol").inner_text(), "🌙")
        self.assertEqual(snake.locator(".grund").count(), 0, "kein Text mehr auf der Kachel")
        self.assertNotIn("gesperrt", seite.locator(".kachel[data-id=gute-nacht]").get_attribute("class"))
        seite.screenshot(path=os.path.join(FOTOS, "start34-kacheln.png"))
        self.assertEqual(self.fehler, [])

    def test_meldung_bleibt_bis_ok(self):
        seite = self.seite()
        self.hub.familie.nachricht("Essen ist fertig!", bleibt=True)
        seite.wait_for_selector("#meldungen", timeout=5000)
        self.assertIn("Essen ist fertig!", seite.inner_text("#meldungen"))
        seite.wait_for_timeout(2500)                                             # bleibt stehen
        self.assertTrue(seite.is_visible("#meldungen"))
        seite.screenshot(path=os.path.join(FOTOS, "start34-meldung.png"))
        seite.keyboard.press("Enter")
        seite.wait_for_selector("#meldungen", state="detached")
        seite.wait_for_timeout(300)
        self.assertEqual(self.hub.status()["meldungen"], [])
        self.assertEqual(self.fehler, [])

    def test_nacht_countdown(self):
        seite = self.seite("#nacht")
        seite.wait_for_selector(".nacht-frage")
        self.assertIn("Nachtruhe", seite.inner_text(".nacht-frage"))
        seite.screenshot(path=os.path.join(FOTOS, "start34-nacht.png"))
        seite.keyboard.press("ArrowLeft")
        seite.keyboard.press("ArrowLeft")                                        # Gute Nacht -> an -> aus
        seite.keyboard.press("Enter")
        seite.wait_for_selector("#nacht-schwarz")
        seite.wait_for_timeout(300)
        self.assertEqual(self.hub.cec["befehl"], "standby")
        seite.keyboard.press("ArrowDown")                                        # eine Taste weckt
        seite.wait_for_selector("#nacht-schwarz", state="detached")
        self.assertEqual(self.fehler, [])

    def test_gute_nacht_weiterhoeren_und_sternenhimmel(self):
        self.hub.hoerbuch_stand("gute-nacht", "Bibi Blocksberg", "Bibi Blocksberg/Folge 2.wav", 5)
        seite = self.seite("#gute-nacht")
        seite.wait_for_selector(".hb-wahl:not([hidden])", timeout=8000)          # fragt sofort nach der Zeit
        for _ in range(4):
            seite.keyboard.press("ArrowLeft")
        seite.keyboard.press("Enter")
        seite.wait_for_function("() => document.querySelector('.hb-titel').textContent === 'Folge 2'")
        seite.wait_for_function("() => document.querySelector('audio, .hb-zeit') && "
                                "document.querySelector('.hb-zeit').textContent.startsWith('0:0')", timeout=5000)
        seite.wait_for_selector(".hb-schwarz:not([hidden]) canvas.hb-himmel", timeout=6000)
        seite.wait_for_timeout(1500)
        hell = seite.evaluate("""() => { const c = document.querySelector('canvas.hb-himmel');
            const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let max = 0, summe = 0;
            for (let i = 0; i < d.length; i += 4) { const v = Math.max(d[i], d[i+1], d[i+2]); max = Math.max(max, v); summe += v; }
            return { max, mittel: summe / (d.length / 4) }; }""")
        self.assertLess(hell["mittel"], 6, "Einschlafbild ist sehr dunkel")
        self.assertLess(hell["max"], 150, "nichts grell")
        self.assertGreater(hell["max"], 20, "aber Mond und Sterne sind zu sehen")
        seite.wait_for_timeout(300)
        self.assertTrue(self.hub.still(), "Server weiß: Gute-Nacht-Modus, keine Töne")
        seite.screenshot(path=os.path.join(FOTOS, "start34-sternenhimmel.png"))
        self.assertEqual(self.fehler, [])

    def test_sonnenaufgang_wird_heller(self):
        seite = self.seite("#sonne-1")                                           # 1 Minute (Test)
        seite.wait_for_selector(".overlay.sonne")
        hell = lambda: seite.evaluate("""() => { const m = getComputedStyle(document.querySelector('.overlay.sonne'))
            .backgroundImage.match(/rgb\\((\\d+), (\\d+), (\\d+)\\)/); return m ? +m[1] + +m[2] + +m[3] : 0; }""")
        anfang = hell()
        seite.wait_for_timeout(8500)
        self.assertGreater(hell(), anfang, "wird heller")
        seite.keyboard.press("Enter")                                            # eine Taste beendet ihn
        seite.wait_for_selector(".overlay.sonne", state="detached")
        self.assertEqual(self.fehler, [])

    def test_startseite_selbst_gestalten(self):
        seite = self.seite()
        seite.click(".kachel[data-id=spiel-gestalten]")
        seite.wait_for_selector(".gestalten-zeile.thema")
        seite.keyboard.press("ArrowRight")                                       # Hintergrund: Ozean
        seite.wait_for_function("() => document.body.dataset.thema === 'ozean'")
        for _ in range(40):                                                      # bis Snake gewählt ist, dann ⭐
            seite.keyboard.press("ArrowDown")
            if seite.inner_text(".gestalten-zeile.gewaehlt span") == "Snake":
                break
        seite.keyboard.press("Enter")
        seite.wait_for_timeout(400)
        self.assertEqual(self.hub.einstellungen["startseite"], {"lieblinge": ["spiel-snake"], "thema": "ozean"})
        seite.keyboard.press("Escape")
        seite.wait_for_selector(".reihe[data-bereich=start] .kachel[data-id=spiel-snake]")
        erste = seite.locator(".reihe[data-bereich=start] .kachel").first.get_attribute("data-id")
        self.assertEqual(erste, "spiel-snake", "Liebling steht vorne in Start")
        seite.screenshot(path=os.path.join(FOTOS, "start40-gestaltet.png"))
        self.hub.einstellungen_aendern({"startseite": {"lieblinge": [], "thema": "weltall"}})
        self.assertEqual(self.fehler, [])

    def test_gute_nacht_automatisch_ohne_wahl(self):
        self.hub.hoerbuch_stand("gute-nacht", "", "", 0)
        seite = self.seite("#gute-nacht-auto")
        seite.wait_for_selector(".hb-eintrag")
        # minuteMs = 3000: Alarme nach 15/45/75 s, nach 90 s Countdown (30 s), dann aus - hier nur der erste Alarm
        seite.wait_for_function("() => document.getElementById('hinweis').textContent.includes('wie lange')", timeout=20000)
        self.assertEqual(self.fehler, [])


if __name__ == "__main__":
    unittest.main()
