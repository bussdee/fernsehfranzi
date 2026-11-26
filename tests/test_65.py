"""6.5: Lesen üben - Lesepass mit Stempeln, Vorlese-Zeit über den Pegel des Mikros (keine Aufnahme)."""
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

from fernsehfranzi import meintag, web  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

HEUTE = datetime(2026, 11, 18, 16, 0)
EINST = {"aktiv": True, "lesen": {"aktiv": True, "ziel_min": 2}}


class Logik(unittest.TestCase):
    def test_ab_werk_aus_und_pruefen(self):
        m = meintag.pruefe({"aktiv": True})
        self.assertFalse(m["lesen"]["aktiv"])
        self.assertIsNone(meintag.heute(m, HEUTE, False, {})["lesen"])
        with self.assertRaises(ValueError):
            meintag.lesen_melden(m, HEUTE, {}, 60)
        for falsch in ({"aktiv": True, "ziel_min": 1}, {"aktiv": True, "ziel_min": 90}, {"aktiv": 1}):
            with self.assertRaises(ValueError):
                meintag.pruefe(dict(EINST, lesen=falsch))

    def test_stempel_einmal_am_tag(self):
        m = meintag.pruefe(EINST)
        z, stempel = meintag.lesen_melden(m, HEUTE, {}, 60)
        self.assertFalse(stempel)
        z, stempel = meintag.lesen_melden(m, HEUTE, z, 70)
        self.assertTrue(stempel)
        self.assertEqual(z["sterne"], 1)
        z, stempel = meintag.lesen_melden(m, HEUTE, z, 300)
        self.assertFalse(stempel, "zweiter Stempel am selben Tag gibt es nicht")
        p = meintag.heute(m, HEUTE, False, z)["lesen"]
        self.assertEqual((p["stempel"], p["stempel_heute"], len(p["tage"])), (1, True, 14))
        self.assertTrue(p["tage"][-1]["stempel"])
        for falsch in (-1, 99999, "60", True):
            with self.assertRaises(ValueError):
                meintag.lesen_melden(m, HEUTE, z, falsch)

    def test_kachel_nur_mit_lesen(self):
        ordner = tempfile.mkdtemp(prefix="ff-65-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(HEUTE))
        hub.einstellungen_aendern({"meintag": EINST})
        self.assertIn("spiel-meintag", [k["id"] for k in hub.kacheln()])
        gemeldet = []
        hub.telegram.melde_eltern = lambda art, text: gemeldet.append(text)
        self.assertTrue(hub.lesen_melden(130)["neuer_stempel"])
        self.assertEqual(gemeldet, ["📖 Heute 2 Minuten vorgelesen – Stempel im Lesepass!"])


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class AmFernseher(unittest.TestCase):
    def test_vorlesen_mit_test_mikro(self):
        ordner = tempfile.mkdtemp(prefix="ff-65w-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(HEUTE))
        hub.einstellungen_aendern({"meintag": EINST})
        hub.meintag_zustand = meintag.zustand_fuer({}, HEUTE.date())
        hub.meintag_zustand["lesepass"]["2026-11-18"] = 1.95          # noch 3 Sekunden bis zum Ziel
        hub.telegram.melde_eltern = lambda art, text: None
        server = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            seite = browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
            # gleichmäßiger lauter Ton statt Mikrofon (das Test-Mikro von Chromium piept nur kurz - der Test würde wackeln)
            seite.add_init_script("""navigator.mediaDevices.getUserMedia = async () => {
                const ac = new AudioContext(), o = ac.createOscillator(), g = ac.createGain(), ziel = ac.createMediaStreamDestination();
                g.gain.value = 0.5; o.connect(g).connect(ziel); o.start(); return ziel.stream; };""")
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            seite.goto("http://127.0.0.1:8765/")
            seite.wait_for_selector(".kachel")
            seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-meintag')")
            seite.click("[data-id=spiel-meintag]")
            seite.wait_for_selector(".mt-stempel-reihe")
            self.assertEqual(seite.locator(".mt-stempel.an").count(), 0)
            seite.keyboard.press("Enter")                                # Vorlesen starten
            seite.wait_for_selector(".mt-timer .mt-scheibe.gross")
            seite.wait_for_function("document.querySelector('.mt-scheibe-text')?.textContent === '✔'", timeout=15000)
            for _ in range(30):
                if hub.meintag_zustand["lesepass"].get("2026-11-18", 0) >= 2:
                    break
                seite.wait_for_timeout(200)
            self.assertGreaterEqual(hub.meintag_zustand["lesepass"]["2026-11-18"], 2)
            self.assertEqual(hub.meintag_zustand["sterne"], 1)
            seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "65-vorlesen.png"))
            seite.keyboard.press("Escape")                               # STOP beendet die Vorlese-Zeit
            seite.wait_for_selector(".mt-stempel.an")
            self.assertEqual(fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()
