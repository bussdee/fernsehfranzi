"""6.3: Ranzen-Check aus dem Stundenplan und Aufgaben mit Bestätigung der Eltern (Sterne)."""
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

ABEND = datetime(2026, 11, 18, 18, 0)           # Mittwoch
MORGEN_SCHULE = {"datum": "2026-11-19", "name": "morgen", "frei": [], "stunden": [
    {"nr": 1, "fach": "Deutsch", "faellt_aus": False}, {"nr": 2, "fach": "Sport", "faellt_aus": False},
    {"nr": 3, "fach": "Musik", "faellt_aus": True}]}
EINST = {"aktiv": True, "routinen": [],
         "ranzen": {"aktiv": True, "immer": ["Federmäppchen"],
                    "faecher": [{"fach": "sport", "sachen": ["Turnbeutel", "Trinkflasche"]},
                                {"fach": "Musik", "sachen": ["Flöte"]}, {"fach": "Deutsch", "sachen": ["Lesebuch", "federmäppchen"]}]},
         "aufgaben": [{"nr": 3, "text": "Tisch decken", "symbol": "🍽️", "tage": [2], "sterne": 2},
                      {"nr": 4, "text": "Blumen gießen", "tage": [5]}]}


class Logik(unittest.TestCase):
    def test_pruefen(self):
        meintag.pruefe(EINST)
        for falsch in (dict(EINST, ranzen={"aktiv": True, "immer": ["x"] * 11}),
                       dict(EINST, ranzen={"aktiv": True, "faecher": [{"fach": "", "sachen": []}]}),
                       dict(EINST, aufgaben=[{"nr": 1, "text": "x", "tage": [1], "sterne": 9}]),
                       dict(EINST, aufgaben=[{"nr": 1, "text": "x", "tage": []}])):
            with self.assertRaises(ValueError):
                meintag.pruefe(falsch)

    def test_packliste(self):
        m = meintag.pruefe(EINST)
        p = meintag.packliste(m, MORGEN_SCHULE)
        self.assertEqual(p["faecher"], ["Deutsch", "Sport"], "ausgefallene Stunde zählt nicht")
        self.assertEqual([x["text"] for x in p["sachen"]], ["Federmäppchen", "Lesebuch", "Turnbeutel", "Trinkflasche"],
                         "ohne Doppelte, Groß/klein egal")
        self.assertIsNone(meintag.packliste(m, dict(MORGEN_SCHULE, frei=["Ferien"])))
        self.assertIsNone(meintag.packliste(m, None))

    def test_ranzen_gilt_bis_zum_schultag(self):
        m = meintag.pruefe(EINST)
        z, fertig = meintag.ranzen_abhaken(m, ABEND, {}, MORGEN_SCHULE, 2, True)
        self.assertFalse(fertig)
        frueh = ABEND.replace(day=19, hour=7)
        h = meintag.heute(m, frueh, False, z, MORGEN_SCHULE)
        self.assertEqual(h["ranzen"]["erledigt"], 1, "am Morgen des Schultags noch da")
        for i in (0, 1, 3):
            z, fertig = meintag.ranzen_abhaken(m, frueh, z, MORGEN_SCHULE, i, True)
        self.assertTrue(fertig)
        h = meintag.heute(m, ABEND.replace(day=20), False, z, dict(MORGEN_SCHULE, datum="2026-11-23"))
        self.assertEqual(h["ranzen"]["erledigt"], 0, "neuer Schultag = neue Packliste")

    def test_aufgaben_und_sterne(self):
        m = meintag.pruefe(EINST)
        self.assertEqual([a["nr"] for a in meintag.heute(m, ABEND, False, {})["aufgaben"]], [3], "nur am Mittwoch")
        with self.assertRaises(ValueError):
            meintag.aufgabe_bestaetigen(m, ABEND, {}, 3, True)                  # nichts gemeldet
        z, _ = meintag.aufgabe_melden(m, ABEND, {}, 3)
        z, _ = meintag.aufgabe_bestaetigen(m, ABEND, z, 3, False)
        self.assertEqual(z["sterne"], 0)
        z, _ = meintag.aufgabe_melden(m, ABEND, z, 3)                          # nochmal versuchen
        z, _ = meintag.aufgabe_bestaetigen(m, ABEND, z, 3, True)
        self.assertEqual((z["sterne"], z["sterne_tage"]), (2, {"2026-11-18": 2}))
        with self.assertRaises(ValueError):
            meintag.aufgabe_melden(m, ABEND, z, 3)                              # schon bestätigt
        morgen = meintag.zustand_fuer(z, ABEND.date().replace(day=19))
        self.assertEqual((morgen["sterne"], morgen["aufgaben"]), (2, {}), "Sterne bleiben, Aufgaben neu")


class ImHub(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-63-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(ABEND)
        self.hub = neuer_hub(self.ordner, self.uhr)
        self.hub.einstellungen_aendern({"meintag": EINST})
        self.hub._schulmorgen = lambda: MORGEN_SCHULE
        self.gemeldet = []
        self.hub.telegram.melde_eltern = lambda art, text: self.gemeldet.append((art, text))

    def test_kachel_auch_ohne_routinen(self):
        self.assertIn("spiel-meintag", [k["id"] for k in self.hub.kacheln()])

    def test_aufgabe_ueber_telegram_bestaetigen(self):
        self.hub.aufgabe_melden(3)
        self.assertEqual(self.gemeldet, [("meintag", "🍽️ Aufgabe erledigt: Tisch decken – stimmt das? Antwort: /ja 3 oder /nein 3")])
        antworten = []
        self.hub.telegram.antwort = lambda c, text: antworten.append(text)
        self.hub.telegram.befehl({"id": 1}, "/ja 3")
        self.assertIn("Sterne", antworten[-1])
        self.assertEqual(self.hub.meintag_heute()["sterne"], 2)
        self.assertIn("Super! Tisch decken – du bekommst 2 Sterne.", self.hub.meldung["text"])
        self.hub.telegram.befehl({"id": 1}, "/ja 3")
        self.assertIn("⚠️", antworten[-1], "nichts mehr offen")
        self.hub.telegram.befehl({"id": 1}, "/ja drei")
        self.assertIn("So geht's", antworten[-1])

    def test_ranzen_im_hub(self):
        h = self.hub.ranzen_abhaken(0)
        self.assertEqual(h["ranzen"]["erledigt"], 1)
        self.assertEqual(neuer_hub(self.ordner, self.uhr).meintag_zustand["ranzen"]["erledigt"], ["Federmäppchen"])


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class AmFernseher(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-63w-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(ABEND))
        self.hub.einstellungen_aendern({"meintag": EINST})
        self.hub._schulmorgen = lambda: MORGEN_SCHULE
        self.hub.telegram.melde_eltern = lambda art, text: None
        self.server = web.baue_server(web.KioskHandler, self.hub, os.path.join(REPO, "web"), os.path.join(self.ordner, "z"),
                                      ("127.0.0.1", 8765))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def test_ranzen_und_aufgabe(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            seite = browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            seite.goto("http://127.0.0.1:8765/")
            seite.wait_for_selector(".kachel")
            seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-meintag')")
            seite.click("[data-id=spiel-meintag]")
            seite.wait_for_selector(".seite-reiter-knopf.an:has-text('Ranzen')")
            self.assertIn("Deutsch, Sport", seite.inner_text(".mt-oben"))
            seite.keyboard.press("Enter")
            seite.wait_for_selector(".mt-schritt.erledigt")
            self.assertEqual(self.hub.meintag_heute()["ranzen"]["erledigt"], 1)
            seite.keyboard.press("ArrowRight")
            seite.wait_for_selector(".seite-reiter-knopf.an:has-text('Aufgaben')")
            seite.keyboard.press("Enter")
            seite.wait_for_selector(".mt-schritt.wartet")
            self.assertEqual(self.hub.meintag_heute()["aufgaben"][0]["stand"], "wartet")
            seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "63-aufgaben.png"))
            seite.keyboard.press("Escape")
            seite.wait_for_selector(".overlay", state="detached")
            self.assertEqual(fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()
