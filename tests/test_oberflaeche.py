"""Startseite im Headless-Chromium (Playwright): mit und ohne persönliche Konfiguration."""
import os
import shutil
import tempfile
import unittest

try:
    from playwright.sync_api import sync_playwright
except ImportError:   # make venv richtet Playwright ein
    sync_playwright = None

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEST_KONFIG = """window.FERNSEHFRANZI_EINSTELLUNGEN = {
  name: "Testkind",
  untertitel: "Test Edition",
  links: { plex: "http://plex.example:32400/web/", familie: "http://familie.example:8088" },
  geburtstage: [],
};
"""


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
class Startseite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        # Schalter wie im Kiosk (familyhub/kiosk.sh)
        cls.browser = cls.pw.chromium.launch(args=["--enable-spatial-navigation"])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def lade(self, konfig=None, server=None):
        ordner = tempfile.mkdtemp(prefix="ff-ui-")
        self.addCleanup(shutil.rmtree, ordner, True)
        shutil.copytree(os.path.join(REPO, "familyhub"), os.path.join(ordner, "hub"))
        if konfig is not None:
            os.makedirs(os.path.join(ordner, "hub", "config"))
            with open(os.path.join(ordner, "hub", "config", "einstellungen.js"), "w", encoding="utf-8") as f:
                f.write(konfig)
        seite = self.browser.new_page(viewport={"width": 1920, "height": 1080})
        self.addCleanup(seite.close)
        fehler = []
        seite.on("pageerror", lambda e: fehler.append(str(e)))
        if server is not None:
            seite.route("http://127.0.0.1:8765/**", server)
        seite.goto("file://" + os.path.join(ordner, "hub", "index.html"))
        seite.wait_for_timeout(300)
        return seite, fehler

    def test_ohne_konfiguration(self):
        seite, fehler = self.lade()
        self.assertEqual(fehler, [])
        self.assertEqual(seite.text_content("#untertitel"), "Home Entertainment")
        gruss = seite.text_content("#gruss")
        self.assertTrue(gruss.endswith("!") and "," not in gruss, gruss)
        url = seite.url
        seite.keyboard.press("Home")
        seite.keyboard.press("Enter")
        seite.wait_for_timeout(200)
        self.assertEqual(seite.url, url, "Kachel ohne Adresse darf nicht navigieren")
        self.assertIn("noch nicht eingerichtet", seite.text_content("#notice"))

    def test_mit_konfiguration(self):
        seite, fehler = self.lade(TEST_KONFIG)
        self.assertEqual(fehler, [])
        self.assertIn("Testkind", seite.text_content("#gruss"))
        self.assertEqual(seite.text_content("#untertitel"), "Home Entertainment · Test Edition")
        self.assertEqual(seite.get_attribute("#plex", "href"), "http://plex.example:32400/web/")
        self.assertEqual(seite.get_attribute("#family", "href"), "http://familie.example:8088")
        # Kavita fehlt in der Test-Konfiguration -> freundlicher Hinweis statt Navigation
        self.assertIsNotNone(seite.get_attribute("#books", "data-coming"))
        self.assertIsNone(seite.get_attribute("#plex", "data-coming"))

    def test_games_kachel_navigiert_nicht(self):
        """GAMES bleibt auf der Startseite und meldet sich (Server fehlt im Test)."""
        seite, fehler = self.lade()
        url = seite.url
        seite.click("#games")
        seite.wait_for_timeout(500)
        self.assertEqual(seite.url, url)
        self.assertEqual(fehler, [])
        self.assertIn("RetroPie", seite.text_content("#notice"))

    def falscher_server(self, zustand):
        """Ersetzt den Hub-Server: /status liefert `zustand`, POST /api/retropie setzt 'angefordert'."""
        import json

        def antwort(route):
            anfrage = route.request
            pfad = anfrage.url.split("8765", 1)[1]
            if anfrage.method == "POST" and pfad == "/api/retropie":
                zustand["angefordert"] = True
                route.fulfill(json={"ok": True, "meldung": "RetroPie startet ..."})
            elif pfad == "/status":
                route.fulfill(body=json.dumps(zustand["status"]()), content_type="application/json")
            else:
                route.fulfill(status=404, body="")
        return antwort

    def test_spiel_zwischen_zwei_abfragen_wird_erkannt(self):
        """Läuft RetroPie, ohne dass die Seite 'running' sieht, kommt trotzdem 'Willkommen zurück!'."""
        zustand = {"angefordert": False}
        zustand["status"] = lambda: {"version": "2.5.0", "running": False, "ton": None, "ton_nummer": 0,
                                     "retropie_start": 999 if zustand["angefordert"] else 0}
        seite, fehler = self.lade(server=self.falscher_server(zustand))
        seite.wait_for_timeout(500)
        self.assertEqual(seite.text_content("#version"), "FAMILY HUB \u00b7 V2.5.0")
        seite.click("#games")
        seite.wait_for_function("document.getElementById('notice').textContent.includes('Willkommen')",
                                timeout=6000)
        self.assertEqual(fehler, [])

    def test_ton_umschaltung_wird_angezeigt(self):
        zustand = {"nummer": 0}
        zustand["status"] = lambda: {"version": "2.5.0", "running": False, "retropie_start": 0,
                                     "ton": "klinke" if zustand["nummer"] else None,
                                     "ton_nummer": zustand["nummer"]}
        seite, fehler = self.lade(server=self.falscher_server(zustand))
        seite.wait_for_timeout(500)
        zustand["nummer"] = 1   # z. B. GRÜN auf der Fernbedienung in Plex
        seite.wait_for_function("document.getElementById('notice').textContent.includes('Ton: Klinke')",
                                timeout=6000)
        self.assertEqual(fehler, [])

    def test_pfeile_bleiben_auf_der_startseite(self):
        """Mit Spatial Navigation darf ← → nur die eigene Kachel-Markierung bewegen."""
        seite, fehler = self.lade(TEST_KONFIG)
        seite.keyboard.press("Home")
        gewaehlt = "Array.from(document.querySelectorAll('.selected')).map(e => e.id).join(',')"
        fokus = "document.activeElement ? (document.activeElement.id || document.activeElement.tagName) : ''"
        vorher, fokus_vorher = seite.evaluate(gewaehlt), seite.evaluate(fokus)
        seite.keyboard.press("ArrowRight")
        seite.wait_for_timeout(100)
        nachher = seite.evaluate(gewaehlt)
        self.assertTrue(vorher and nachher and vorher != nachher, (vorher, nachher))
        self.assertEqual(len(nachher.split(",")), 1, "genau eine markierte Kachel")
        # Spatial Navigation hat den Browser-Fokus nicht woandershin geschoben
        self.assertEqual(seite.evaluate(fokus), fokus_vorher)
        self.assertTrue(seite.url.startswith("file://"))
        self.assertEqual(fehler, [])

    def test_kaputte_konfiguration_bricht_nichts(self):
        seite, fehler = self.lade("window.FERNSEHFRANZI_EINSTELLUNGEN = { name: 42, links: 'x' };")
        self.assertEqual(fehler, [])
        self.assertEqual(seite.text_content("#untertitel"), "Home Entertainment")
        self.assertIsNotNone(seite.get_attribute("#plex", "data-coming"))


if __name__ == "__main__":
    unittest.main()
