"""6.2: Mein Tag - Routinen der Eltern, das Kind hakt ab, Erinnerung, Zeit-Scheibe, Zahnputz-Timer."""
import json
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

MORGEN = datetime(2026, 11, 18, 6, 40)          # Mittwoch, Schultag
LISTE = {"aktiv": True, "routinen": [
    {"nr": 1, "name": "Morgen", "symbol": "☀️", "zeit": "06:45", "fertig": "07:30", "tage": [0, 1, 2, 3, 4], "wann": "schule",
     "erinnern": True, "klang": "glocke",
     "schritte": [{"text": "Anziehen", "symbol": "👕"}, {"text": "Zähne putzen", "symbol": "🦷", "timer": 120}]},
    {"nr": 2, "name": "Abend", "symbol": "🌙", "zeit": "19:00", "fertig": "19:45", "tage": [0, 1, 2, 3, 4, 5, 6],
     "schritte": [{"text": "Schlafanzug an"}]}]}


class Logik(unittest.TestCase):
    def test_ab_werk_aus(self):
        m = meintag.einstellungen(None)
        self.assertFalse(m["aktiv"])
        self.assertEqual(meintag.heute(m, MORGEN, False, {})["routinen"], [])

    def test_pruefen(self):
        meintag.pruefe(LISTE)
        for timer in (600, 900):                       # 6.8.9: 10 und 15 Minuten (Abendbrot)
            meintag.pruefe(dict(LISTE, routinen=[dict(LISTE["routinen"][0], schritte=[{"text": "Abendbrot", "timer": timer}])]))
        falsch = [
            dict(LISTE, routinen=[dict(LISTE["routinen"][0], fertig="06:00")]),            # fertig vor Beginn
            dict(LISTE, routinen=[dict(LISTE["routinen"][0], schritte=[])]),                # ohne Schritt
            dict(LISTE, routinen=[dict(LISTE["routinen"][0], schritte=[{"text": "x", "timer": 7}])]),
            dict(LISTE, routinen=[dict(LISTE["routinen"][0], schritte=[{"text": "x", "timer": 1200}])]),
            dict(LISTE, routinen=[dict(LISTE["routinen"][0], tage=[])]),
            dict(LISTE, routinen=[LISTE["routinen"][0], dict(LISTE["routinen"][1], nr=1)]),   # Nummer doppelt
            dict(LISTE, unbekannt=1),
        ]
        for m in falsch:
            with self.assertRaises(ValueError):
                meintag.pruefe(m)

    def test_heute_ferien_und_zeit_scheibe(self):
        m = meintag.pruefe(LISTE)
        h = meintag.heute(m, MORGEN.replace(hour=7, minute=20), False, {})
        self.assertEqual([r["name"] for r in h["routinen"]], ["Morgen", "Abend"])
        self.assertEqual(h["aktuell"], 1)
        morgen = h["routinen"][0]
        self.assertTrue(morgen["laeuft"])
        self.assertEqual((morgen["rest_s"], morgen["dauer_s"]), (600, 45 * 60), "noch 10 Minuten bis zum Losgehen")
        self.assertEqual([r["name"] for r in meintag.heute(m, MORGEN, True, {})["routinen"]], ["Abend"], "Ferien: keine Schul-Liste")
        self.assertEqual(meintag.heute(m, MORGEN.replace(hour=12), False, {})["aktuell"], 2, "nach dem Morgen: die nächste Liste")

    def test_abhaken_und_neuer_tag(self):
        m = meintag.pruefe(LISTE)
        z, fertig = meintag.abhaken(m, MORGEN, False, {}, 1, 0, True)
        self.assertIsNone(fertig)
        z, fertig = meintag.abhaken(m, MORGEN, False, z, 1, 1, True)
        self.assertEqual(fertig["name"], "Morgen")
        self.assertEqual(z["geschafft"], {"1": "06:40"})
        z, fertig = meintag.abhaken(m, MORGEN, False, z, 1, 1, False)       # wieder weg und neu: keine zweite Meldung
        z, fertig = meintag.abhaken(m, MORGEN, False, z, 1, 1, True)
        self.assertIsNone(fertig)
        self.assertEqual(meintag.heute(m, MORGEN.replace(day=19), False, z)["routinen"][0]["erledigt"], 0, "jeden Tag neu")
        for nr, schritt in ((9, 0), (1, 5), (1, True)):
            with self.assertRaises(ValueError):
                meintag.abhaken(m, MORGEN, False, z, nr, schritt, True)
        with self.assertRaises(ValueError):
            meintag.abhaken(m, MORGEN, True, z, 1, 0, True)                 # in den Ferien gibt es die Liste nicht


class ImHub(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-62-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(MORGEN)
        self.hub = neuer_hub(self.ordner, self.uhr)

    def ids(self):
        return [k["id"] for k in self.hub.kacheln()]

    def test_kachel_erst_wenn_eingeschaltet(self):
        self.assertNotIn("spiel-meintag", self.ids())
        self.hub.einstellungen_aendern({"meintag": LISTE})
        self.assertIn("spiel-meintag", self.ids())
        kachel = next(k for k in self.hub.kacheln() if k["id"] == "spiel-meintag")
        self.assertTrue(kachel["frei"])
        self.assertFalse(kachel["zaehlt"], "Mein Tag kostet keine Zeit")
        self.assertIn("meintag", self.hub.eltern_daten())
        self.assertEqual(self.hub.eltern_daten()["meintag_heute"]["aktuell"], 1)

    def test_erinnerung_einmal(self):
        self.hub.einstellungen_aendern({"meintag": LISTE})
        self.uhr.weiter(5 * 60)                        # 06:45
        nr = self.hub.meldung["nr"]
        self.hub._meintag_takt(self.uhr())
        self.hub._meintag_takt(self.uhr())
        self.assertEqual(self.hub.meldung, {"nr": nr + 1, "text": "Mein Tag: Morgen – los geht's!"}, "einmal, als Hinweis")
        self.uhr.weiter(5 * 60)
        self.hub._meintag_takt(self.uhr())
        self.assertEqual(self.hub.meldung["nr"], nr + 1, "nicht noch einmal (6.9.58: erst nach 10 Minuten wieder)")

    def test_abhaken_speichert_und_meldet(self):
        self.hub.einstellungen_aendern({"meintag": LISTE})
        gemeldet = []
        self.hub.telegram.melde_eltern = lambda art, text: gemeldet.append((art, text))
        self.hub.meintag_abhaken(1, 0)
        h = self.hub.meintag_abhaken(1, 1)
        self.assertEqual(h["routinen"][0]["geschafft"], "06:40")
        self.assertEqual(gemeldet, [("meintag", "✅ Morgen geschafft (06:40 Uhr) – pünktlich, Bonus-Stern.")])
        with open(os.path.join(self.ordner, "meintag.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["erledigt"], {"1": [0, 1]})
        neu = neuer_hub(self.ordner, self.uhr)            # nach einem Neustart bleibt der Stand
        self.assertEqual(neu.meintag_heute()["routinen"][0]["erledigt"], 2)


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class AmFernseher(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-62w-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(MORGEN.replace(hour=7, minute=20)))
        liste = json.loads(json.dumps(LISTE))
        liste["routinen"][0]["oeffnen"] = False             # 6.9.58: hier öffnet der Test Mein Tag selbst (Auto-Öffnen: test_6958)
        self.hub.einstellungen_aendern({"meintag": liste})
        self.server = web.baue_server(web.KioskHandler, self.hub, os.path.join(REPO, "web"), os.path.join(self.ordner, "z"),
                                      ("127.0.0.1", 8765))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def test_abhaken_mit_tasten_und_timer(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            seite = browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            seite.goto("http://127.0.0.1:8765/")
            seite.wait_for_selector(".kachel")
            seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-meintag')")
            seite.click("[data-id=spiel-meintag]")
            seite.wait_for_selector(".mt-schritt")
            self.assertIn("Noch 10 Minuten bis 07:30 Uhr", seite.inner_text(".mt-oben"))
            self.assertEqual(seite.locator(".seite-reiter-knopf").count(), 3, "Morgen, Abend, 6.4: Franzi")
            seite.keyboard.press("Enter")                       # Anziehen abhaken
            seite.wait_for_selector(".mt-schritt.erledigt")
            self.assertEqual(self.hub.meintag_heute()["routinen"][0]["erledigt"], 1)
            seite.wait_for_selector(".mt-schritt.gewaehlt:has-text('Zähne putzen')")
            seite.keyboard.press("Enter")                       # Zahnputz-Timer startet
            seite.wait_for_selector(".mt-timer .mt-scheibe.gross")
            self.assertIn("2:00", seite.inner_text(".mt-timer"))
            seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "62-zahnputz-timer.png"))
            seite.keyboard.press("ArrowDown")                   # Pfeile beenden den Timer nicht
            self.assertEqual(seite.locator(".mt-timer").count(), 1)
            seite.keyboard.press("Escape")                      # STOP bricht ab, nichts abgehakt
            seite.wait_for_selector(".mt-schritte")
            self.assertEqual(self.hub.meintag_heute()["routinen"][0]["erledigt"], 1)
            seite.wait_for_selector(".mt-schritt.gewaehlt:has-text('Zähne putzen')")
            seite.keyboard.press("Enter")                       # 6.8.9: Timer nochmal, diesmal früher fertig
            seite.wait_for_selector(".mt-timer")
            self.assertIn("OK = fertig", seite.inner_text(".overlay .hilfe"))
            seite.keyboard.press("Enter")                       # OK = fertig -> abgehakt
            seite.wait_for_selector(".mt-schritte")
            for _ in range(20):
                if self.hub.meintag_heute()["routinen"][0]["erledigt"] == 2:
                    break
                seite.wait_for_timeout(100)
            self.assertEqual(self.hub.meintag_heute()["routinen"][0]["geschafft"], "07:20", "früher fertig zählt")
            seite.keyboard.press("ArrowRight")                  # zur Abend-Liste
            seite.wait_for_selector(".seite-reiter-knopf.an:has-text('Abend')")
            seite.keyboard.press("Escape")
            seite.wait_for_selector(".overlay", state="detached")
            self.assertEqual(fehler, [])
            browser.close()


    def test_timer_musik_und_ton_aus(self):
        """6.8.10: eigene Musik beim Timer (Archiv oder Klang-Ordner), ↓ schaltet den Ton am Fernseher aus und an."""
        liste = dict(LISTE, routinen=[dict(LISTE["routinen"][0], musik="glocke", oeffnen=False)] + LISTE["routinen"][1:])
        self.hub.einstellungen_aendern({"meintag": liste})
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"meintag": dict(LISTE, routinen=[dict(LISTE["routinen"][0], musik="gibtsnicht")])})
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
            seite = browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
            seite.add_init_script("""window.__musik = []; const P = HTMLMediaElement.prototype.play;
                HTMLMediaElement.prototype.play = function () { window.__musik.push(this.src); return Promise.resolve(); };""")
            seite.goto("http://127.0.0.1:8765/")
            seite.wait_for_selector(".kachel")
            seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-meintag')")
            seite.click("[data-id=spiel-meintag]")
            seite.wait_for_selector(".mt-schritt")
            seite.keyboard.press("ArrowDown")                       # Zähne putzen (mit Timer)
            seite.keyboard.press("Enter")
            seite.wait_for_selector(".mt-timer-ton:has-text('Ton an')")
            self.assertTrue(seite.evaluate("window.__musik.some(u => u.includes('/api/klang?id=glocke'))"))
            seite.keyboard.press("ArrowDown")                       # Ton aus
            seite.wait_for_selector(".mt-timer-ton:has-text('Ton aus')")
            self.assertEqual(seite.evaluate("localStorage.getItem('ff-meintag-ton')"), "aus")
            seite.keyboard.press("ArrowDown")                       # wieder an
            seite.wait_for_selector(".mt-timer-ton:has-text('Ton an')")
            self.assertEqual(self.hub.meintag_heute()["routinen"][0]["erledigt"], 0, "↓ hakt nichts ab")
            browser.close()


if __name__ == "__main__":
    unittest.main()
