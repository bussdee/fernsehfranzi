"""6.8: Stimm-Spiele Möwenflug und „Pst – der Drache schläft“, 6.8.1: Klatsch-Läufer, Ton-Kanone, Stimmen-Erkennung."""
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

TON = """navigator.mediaDevices.getUserMedia = async () => {
  const ac = new AudioContext(), o = ac.createOscillator(), g = ac.createGain(), ziel = ac.createMediaStreamDestination();
  o.frequency.value = 520; g.gain.value = 0.6; o.connect(g).connect(ziel); o.start(); return ziel.stream; };"""
KEIN_MIKRO = "navigator.mediaDevices.getUserMedia = async () => { throw new Error('kein Mikro'); };"


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class StimmSpiele(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-68-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(datetime(2026, 11, 18, 15, 0)))
        server = web.baue_server(web.KioskHandler, self.hub, os.path.join(REPO, "web"), os.path.join(self.ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

    def oeffnen(self, pw, skript):
        browser = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        seite = browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
        self.fehler = []
        seite.on("pageerror", lambda e: self.fehler.append(str(e)))
        seite.add_init_script(skript)
        seite.goto("http://127.0.0.1:8765/")
        seite.wait_for_selector(".kachel")
        seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-stimme')")
        seite.click("[data-id=spiel-stimme]")
        seite.wait_for_selector(".knopfreihe .knopf")
        return browser, seite

    def test_drache_ohne_mikro_mit_tasten(self):
        with sync_playwright() as pw:
            browser, seite = self.oeffnen(pw, KEIN_MIKRO)
            self.assertIn("Ohne Mikro", seite.inner_text(".overlay"))
            seite.keyboard.press("ArrowRight")                    # zweites Spiel: Drache
            seite.keyboard.press("Enter")
            seite.wait_for_selector(".drache-wach")
            for _ in range(14):
                seite.keyboard.press("ArrowRight")
            seite.wait_for_selector(".knopfreihe .knopf")       # Schatz geholt -> zurück zur Auswahl
            self.assertIn("Schatz geholt", seite.inner_text(".overlay"))
            self.assertEqual(self.hub.aktuell, "spiel-stimme")
            self.assertEqual(self.fehler, [])
            browser.close()

    def test_moewe_steigt_mit_hohem_ton(self):
        with sync_playwright() as pw:
            browser, seite = self.oeffnen(pw, TON)
            self.assertIn("Mikro bereit", seite.inner_text(".overlay"))
            seite.keyboard.press("Enter")                         # Möwenflug
            seite.wait_for_selector("canvas.spielfeld")
            seite.wait_for_timeout(2500)
            seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "68-moewenflug.png"))
            self.assertIn("⏱", seite.inner_text(".overlay .punkte"))
            seite.keyboard.press("Escape")                        # STOP: zurück zur Auswahl
            seite.wait_for_selector(".knopfreihe .knopf")
            seite.keyboard.press("Escape")
            seite.wait_for_selector(".overlay", state="detached")
            self.assertEqual(self.fehler, [])
            browser.close()


    def test_stimmen_erkennung_hohe_toene(self):
        """6.8.1: stimmHz erkennt auch hohe Kinderstimmen richtig (tonhoehe aus bass.js geht nur bis 400 Hz)."""
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            seite = browser.new_page()
            seite.goto("http://127.0.0.1:8765/")
            ergebnis = seite.evaluate("""async () => {
              const { stimmHz } = await import('/js/spiele/stimme.js');
              const rate = 48000, aus = {};
              for (const f of [110, 220, 330, 523, 784, 880]) {
                const p = new Float32Array(4096);
                for (let i = 0; i < p.length; i++) p[i] = 0.5 * Math.sin(2 * Math.PI * f * i / rate) + 0.15 * Math.sin(4 * Math.PI * f * i / rate);
                aus[f] = stimmHz(p, rate);
              }
              const still = new Float32Array(4096);
              const rauschen = Float32Array.from({ length: 4096 }, () => Math.random() - 0.5);
              aus.still = stimmHz(still, rate); aus.rauschen = stimmHz(rauschen, rate);
              return aus; }""")
            for f in (110, 220, 330, 523, 784, 880):
                self.assertAlmostEqual(ergebnis[str(f)], f, delta=f * 0.03, msg="%d Hz" % f)
            self.assertIsNone(ergebnis["still"])
            self.assertIsNone(ergebnis["rauschen"])
            browser.close()

    def test_klatsch_laeufer_und_ton_kanone_mit_tasten(self):
        with sync_playwright() as pw:
            browser, seite = self.oeffnen(pw, KEIN_MIKRO)
            seite.keyboard.press("ArrowRight")
            seite.keyboard.press("ArrowRight")                    # Klatsch-Läufer
            seite.keyboard.press("Enter")
            seite.wait_for_selector("canvas.spielfeld")
            seite.keyboard.press("Enter")                         # springen
            seite.wait_for_timeout(500)
            self.assertIn("🏅", seite.inner_text(".overlay .punkte"))
            seite.keyboard.press("Escape")
            seite.wait_for_selector(".knopfreihe .knopf")
            for _ in range(3):                                    # Ton-Kanone (die Auswahl steht wieder vorne)
                seite.keyboard.press("ArrowRight")
            seite.keyboard.press("Enter")
            seite.wait_for_selector("canvas.spielfeld")
            treffer = 0
            for _ in range(40):                                   # alle Töne durchfeuern, bis etwas platzt
                for _ in range(5):
                    seite.keyboard.press("Enter")
                    seite.keyboard.press("ArrowRight")
                seite.wait_for_timeout(250)
                treffer = int(seite.inner_text(".overlay .punkte").split("🎈")[1].split("·")[0])
                if treffer:
                    break
            self.assertGreater(treffer, 0)
            seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "681-ton-kanone.png"))
            self.assertEqual(self.fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()
