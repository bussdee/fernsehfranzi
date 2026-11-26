"""6.8.2: eigene Spiele Steine-Brecher und 3D-Labyrinth, 6.8.4: Franzi hüpft (Jump'n'Run)."""
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


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class EigeneSpiele(unittest.TestCase):
    def setUp(self):
        ordner = tempfile.mkdtemp(prefix="ff-682-")
        self.addCleanup(shutil.rmtree, ordner, True)
        self.hub = neuer_hub(ordner, Uhr(datetime(2026, 11, 18, 15, 0)))
        server = web.baue_server(web.KioskHandler, self.hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.pw = sync_playwright().start()
        self.addCleanup(self.pw.stop)
        self.browser = self.pw.chromium.launch()
        self.addCleanup(self.browser.close)
        self.seite = self.browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
        self.fehler = []
        self.seite.on("pageerror", lambda e: self.fehler.append(str(e)))
        self.seite.goto("http://127.0.0.1:8765/")
        self.seite.wait_for_selector(".kachel")

    def oeffne(self, kachel):
        self.seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('%s')" % kachel)
        self.seite.click("[data-id=%s]" % kachel)
        self.seite.wait_for_selector(".knopfreihe .knopf")

    def test_kacheln_im_bereich_spiele(self):
        namen = self.seite.evaluate("FernsehFranzi.zustand.alle.map(a => a.name)")
        for name in ("Steine-Brecher", "3D-Labyrinth", "Stimm-Spiele"):
            self.assertIn(name, namen)

    def test_steine_brecher(self):
        s = self.seite
        self.oeffne("spiel-steine")
        s.keyboard.press("Enter")                                 # Level Herz
        s.wait_for_selector("canvas.spielfeld")
        vorher = s.inner_text(".overlay .punkte")
        self.assertIn("⚪⚪⚪", vorher)
        s.keyboard.press("Enter")                                 # Ball los
        for _ in range(60):                                       # bis ein Stein fällt (oder ein Ball verloren geht)
            s.wait_for_timeout(200)
            if s.inner_text(".overlay .punkte") != vorher:
                break
        self.assertNotEqual(s.inner_text(".overlay .punkte"), vorher)
        s.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "682-steine.png"))
        s.keyboard.press("Escape")
        s.wait_for_selector(".knopfreihe .knopf")
        self.assertEqual(self.fehler, [])

    def test_labyrinth_ist_zusammenhaengend_und_begehbar(self):
        s = self.seite
        ok = s.evaluate("""async () => {
          const { baue } = await import('/js/spiele/labyrinth.js');
          for (const n of [7, 11, 15]) {
            const k = baue(n), gesehen = new Set(['1,1']), weg = [[1, 1]];
            while (weg.length) { const [x, y] = weg.pop();
              for (const [dx, dy] of [[1,0],[-1,0],[0,1],[0,-1]]) { const f = (x+dx)+','+(y+dy);
                if (k[y+dy][x+dx] === 0 && !gesehen.has(f)) { gesehen.add(f); weg.push([x+dx, y+dy]); } } }
            const gaenge = k.flat().filter((v) => v === 0).length;
            if (gesehen.size !== gaenge || k[0].some((v) => v !== 1)) return false;
          }
          return true; }""")
        self.assertTrue(ok, "jeder Gang ist vom Start aus erreichbar, außen Wand")
        self.oeffne("spiel-labyrinth")
        s.keyboard.press("Enter")                                 # klein
        s.wait_for_selector("canvas.labyrinth-bild")
        s.keyboard.press("ArrowUp")                               # der Blick zeigt anfangs in einen Gang
        s.wait_for_function("document.querySelector('.overlay .punkte').textContent.includes('👣 1')")
        s.keyboard.press("Enter")                                 # Karte aus
        s.wait_for_selector(".labyrinth-karte[hidden]", state="attached")
        s.keyboard.press("Enter")
        s.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "682-labyrinth.png"))
        self.assertEqual(self.fehler, [])


    def test_franzi_huepft(self):
        s = self.seite
        self.oeffne("spiel-huepfen")
        s.keyboard.press("Enter")                                 # Wiese
        s.wait_for_selector("canvas.spielfeld")
        self.assertIn("⭐ 0 / ", s.inner_text(".overlay .punkte"))
        s.keyboard.press("ArrowRight")                            # einmal → = läuft los
        for _ in range(20):                                       # springen, bis der erste Stern eingesammelt ist
            s.keyboard.press("Enter")
            s.wait_for_timeout(250)
            if not s.inner_text(".overlay .punkte").startswith("⭐ 0"):
                break
        s.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "684-huepfen.png"))
        self.assertFalse(s.inner_text(".overlay .punkte").startswith("⭐ 0"), "Sterne erreichbar")
        s.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "684-huepfen.png"))
        s.keyboard.press("Escape")
        s.wait_for_selector(".knopfreihe .knopf")
        self.assertEqual(self.fehler, [])


if __name__ == "__main__":
    unittest.main()
