"""3.5: eigene Witze/Quizfragen und Sticker der Eltern, Nachrichten-Verlauf (Kachel mit Glocke)."""
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

from fernsehfranzi import web  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

NACHMITTAG = datetime(2026, 11, 18, 15, 0)


class Inhalte(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-x-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(NACHMITTAG))

    def test_witze_und_quiz_werden_geprueft(self):
        self.hub.einstellungen_aendern({"inhalte": {"witze": [{"frage": "Was ist grün?", "pointe": "Ein Frosch."}],
                                                    "quiz": [{"frage": "2+2?", "richtig": "4", "falsch": ["3", "5", "22"]}]}})
        for falsch in ({"witze": [{"frage": "", "pointe": "x"}]}, {"quiz": [{"frage": "x", "richtig": "y", "falsch": ["a"]}]},
                       {"bilder": []}):
            with self.assertRaises(ValueError):
                self.hub.einstellungen_aendern({"inhalte": falsch})

    def test_eigener_sticker_von_hand_vergeben(self):
        self.hub.einstellungen_aendern({"sticker_eigen": [{"id": "eigen-zimmer", "name": "Zimmer-Profi", "symbol": "🧹",
                                                           "bedingung": "Zimmer aufgeräumt"}]})
        album = {s["id"]: s for s in self.hub.familie.album()}
        self.assertIsNone(album["eigen-zimmer"]["seit"])
        self.assertTrue(self.hub.familie.sticker("eigen-zimmer"))
        self.assertTrue({s["id"]: s for s in self.hub.familie.album()}["eigen-zimmer"]["seit"])
        self.assertIn("Zimmer-Profi", self.hub.status()["meldung"]["text"])
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"sticker_eigen": [{"id": "boese id", "name": "x", "symbol": "x"}]})


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class NachrichtenKachel(unittest.TestCase):
    def test_glocke_und_verlauf(self):
        ordner = tempfile.mkdtemp(prefix="ff-x-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(NACHMITTAG))
        hub.familie.nachricht("Alte Nachricht", bleibt=True)
        hub.familie.meldungen_gesehen([1])
        hub.familie.nachricht("Essen ist fertig!", bleibt=True)
        server = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            seite = browser.new_page(viewport={"width": 1600, "height": 900})
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            seite.goto("http://127.0.0.1:8765/")
            seite.wait_for_selector("#glocke:not([hidden])")
            self.assertEqual(seite.inner_text("#glocke"), "🔔 1")
            seite.keyboard.press("Escape")                              # Meldungs-Fenster wegdrücken (= gesehen)
            seite.wait_for_selector("#meldungen", state="detached")
            seite.click(".kachel[data-id=spiel-nachrichten]")
            seite.wait_for_selector(".nachricht")
            texte = seite.locator(".nachricht-text").all_inner_texts()
            self.assertEqual(texte, ["Essen ist fertig!", "Alte Nachricht"], "neueste zuerst, alte bleiben")
            seite.wait_for_function("() => document.getElementById('glocke').hidden", timeout=5000)
            self.assertEqual(fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()


class Statistik(unittest.TestCase):
    def test_zaehlt_je_app_und_stunde(self):
        ordner = tempfile.mkdtemp(prefix="ff-st-")
        self.addCleanup(shutil.rmtree, ordner, True)
        uhr = Uhr(NACHMITTAG)
        hub = neuer_hub(ordner, uhr)
        hub.starte("spiel-snake")
        for _ in range(12 * 10):                     # 10 Minuten mit Tasten
            uhr.weiter(5)
            hub.eingabe(["ENTER"])
            hub.tick(5)
        for _ in range(12 * 5):                      # 5 Minuten ohne Taste
            uhr.weiter(5)
            hub.tick(5)
        offen, aktiv = hub.statistik()["tage"]["2026-11-18"]["spiel-snake"]["15"]
        self.assertEqual(offen, 15 * 60)
        self.assertAlmostEqual(aktiv, 13 * 60, delta=10, msg="nach 3 min ohne Taste zählt es nicht mehr als aktiv")
        self.assertEqual(hub.statistik()["apps"]["spiel-snake"]["name"], "Snake")
        hub.speichere_konto()
        self.assertEqual(neuer_hub(ordner, uhr).statistik()["tage"]["2026-11-18"]["spiel-snake"]["15"][0], 15 * 60)


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
class PlexProfil(unittest.TestCase):
    """4.0: kiosk.py wählt in der Plex-Profilauswahl das Kinderprofil (nur exakter Name, nur Anklickbares)."""

    def test_profil_wird_angeklickt(self):
        sys.path.insert(0, os.path.join(REPO, "kiosk"))
        import kiosk
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            seite = browser.new_page()
            seite.set_content("""<div id=log></div>
              <div class="UserCard" onclick="log.textContent+='Papa '"><span>Papa</span></div>
              <div class="UserCard" onclick="log.textContent+='Kinderprofil '"><span>Kinderprofil</span></div>
              <p>Kinderprofil und der Zauberwald</p>""")
            self.assertTrue(seite.evaluate(kiosk.PROFIL_JS.replace("__NAME__", json.dumps("Kinderprofil"))))
            self.assertEqual(seite.inner_text("#log").strip(), "Kinderprofil")
            self.assertFalse(seite.evaluate(kiosk.PROFIL_JS.replace("__NAME__", json.dumps("Mama"))))
            browser.close()

    def test_auftrag_traegt_das_profil(self):
        ordner = tempfile.mkdtemp(prefix="ff-px-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(NACHMITTAG))
        apps = hub.eltern_daten()["apps"]
        plex = next(a for a in apps if a["id"] == "plex")
        plex.update(start="http://plex.example:32400/web/", plex_profil="Kinderprofil")
        hub.katalog_aendern(apps)
        hub.starte("plex")
        self.assertEqual(hub.auftraege[-1]["profil"], "Kinderprofil")


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class MemoryEigeneBilder(unittest.TestCase):
    def test_memory_mit_meinen_bildern(self):
        from test_hoerbuch import PNG
        ordner = tempfile.mkdtemp(prefix="ff-mem-")
        self.addCleanup(shutil.rmtree, ordner, True)
        zeichnungen = os.path.join(ordner, "zeichnungen")
        os.makedirs(zeichnungen)
        for i in range(6):
            with open(os.path.join(zeichnungen, "zeichnung-20261121-1200%02d.png" % i), "wb") as f:
                f.write(PNG)
        hub = neuer_hub(ordner, Uhr(NACHMITTAG))
        server = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), zeichnungen, ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            seite = browser.new_page(viewport={"width": 1600, "height": 900})
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            seite.goto("http://127.0.0.1:8765/")
            seite.click(".kachel[data-id=spiel-memory]")
            seite.wait_for_selector("text=Mit meinen Bildern")
            seite.click("text=Mit meinen Bildern")
            seite.wait_for_selector(".karte img.memory-bild", state="attached")      # zugedeckt = unsichtbar
            self.assertEqual(seite.locator(".karte img.memory-bild").count(), 12)
            self.assertEqual(fehler, [])
            browser.close()
