"""3.3 Eltern-Seite am Handy: alle Seiten ohne Fehler, Speichern ohne Speichern-Knopf, Hörbuch-App anlegen.

Echter Chromium in Handy-Größe gegen den LAN-Server (wie im Heimnetz). Bildschirmfotos: .local/bildschirm/eltern-*.png
"""
import os
import shutil
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

PIN = "482913"
FOTOS = os.path.join(REPO, ".local", "bildschirm")


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
class ElternAmHandy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ordner = tempfile.mkdtemp(prefix="ff-eltern-")
        cls.hub = neuer_hub(cls.ordner, Uhr(MITTWOCH))
        cls.hub.pin_festlegen(PIN, erster_start_am_tv=True)
        cls.server = web.baue_server(web.LanHandler, cls.hub, os.path.join(REPO, "web"),
                                     os.path.join(cls.ordner, "zeichnungen"), ("127.0.0.1", 0))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:%d/" % cls.server.server_address[1]
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
        os.makedirs(FOTOS, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.ordner, True)

    def anmelden(self):
        seite = self.browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        self.addCleanup(seite.close)
        self.fehler = []
        seite.on("pageerror", lambda e: self.fehler.append(str(e)))
        seite.on("console", lambda m: m.type == "error" and self.fehler.append(m.text))
        seite.goto(self.url)
        seite.fill(".eh-pin", PIN)
        seite.click("text=Anmelden")
        seite.wait_for_selector(".eh-leiste")
        return seite

    REITER = {"zeit": "Zeit", "abend": "Zeit", "erinnerungen": "Zeit", "apps": "Inhalte", "youtube": "Inhalte", "musik": "Inhalte",
              "spiele": "Inhalte", "kinderwelten": "Inhalte", "schule": "Inhalte", "wetter": "Inhalte", "design": "Inhalte",
              "telegram": "Familie", "bilder": "Familie", "geraet": "Gerät", "internet": "Gerät", "hilfe": "Gerät"}

    def bereich(self, seite, bereich):
        """6.0: Reiter unten antippen, dann den Bereich aufklappen."""
        seite.click(".eh-leiste >> text=" + self.REITER[bereich])
        seite.click(".eh-abschnitt[data-bereich=%s] .eh-abschnitt-kopf" % bereich)
        seite.wait_for_selector(".eh-abschnitt.offen[data-bereich=%s] .eh-abschnitt-inhalt" % bereich)

    def gespeichert(self, seite):
        seite.wait_for_selector(".eh-meldung.zeigen:not(.fehler)", timeout=4000)
        seite.wait_for_selector(".eh-meldung:not(.zeigen)", timeout=4000)

    def test_alle_seiten_ohne_fehler_und_ohne_quer_scrollen(self):
        # 4.0: Beispiel-Nutzung für die Statistik (heute und gestern)
        from datetime import timedelta
        for tag, app, stunde, sek in ((0, "spiel-snake", 15, 1500), (0, "youtube", 16, 2400), (0, "gute-nacht", 19, 1800),
                                      (1, "spiel-bass", 17, 1200), (1, "games", 18, 2700)):
            jetzt = self.hub.uhr().replace(hour=stunde) - timedelta(days=tag)
            for _ in range(sek // 60):
                self.hub.nutzung.zaehle(jetzt, app, 60, True)
        seite = self.anmelden()
        for name in ("Heute", "Zeit", "Inhalte", "Familie", "Gerät"):
            seite.click(".eh-leiste >> text=" + name)
            seite.wait_for_timeout(250)
            breite = seite.evaluate("document.documentElement.scrollWidth")
            self.assertLessEqual(breite, 390, "%s ist breiter als das Handy" % name)
            seite.screenshot(path=os.path.join(FOTOS, "eltern-%s.png" % name.lower()), full_page=True)
        # 6.0: jeder Bereich jedes Reiters klappt ohne Fehler auf; die Zurück-Taste klappt wieder zu
        self.assertEqual(len(self.REITER), 16)
        for b in self.REITER:
            self.bereich(seite, b)
            self.assertGreaterEqual(seite.locator(".eh-abschnitt.offen .eh-karte").count(), 1, b)
            breite = seite.evaluate("document.documentElement.scrollWidth")
            self.assertLessEqual(breite, 390, "%s ist breiter als das Handy" % b)
            seite.screenshot(path=os.path.join(FOTOS, "eltern-bereich-%s.png" % b), full_page=True)
            if b == "zeit":
                seite.go_back()                                   # Zurück-Taste des Handys
                seite.wait_for_selector(".eh-abschnitt[data-bereich=zeit]:not(.offen)")
        # Lesezeichen von früher führen weiter (#erinnerungen -> Reiter Zeit, aufgeklappt)
        seite.evaluate("location.hash = '#erinnerungen'")
        seite.wait_for_selector(".eh-abschnitt.offen[data-bereich=erinnerungen]")
        seite.click(".eh-leiste >> text=Heute")
        seite.click(".eh-abschnitt[data-bereich=statistik] .eh-abschnitt-kopf")
        seite.wait_for_selector(".eh-abschnitt.offen[data-bereich=statistik] .eh-abschnitt-inhalt")
        self.assertEqual(self.fehler, [])

    def test_bildschirmfoto_wird_angezeigt(self):
        """4.2: Das Bild kam an, wurde aber nicht gezeigt (Sicherheitsregel ohne blob:)."""
        seite = self.anmelden()
        jpeg = seite.screenshot(type="jpeg")
        alt, self.hub.bildschirmfoto = self.hub.bildschirmfoto, lambda: (jpeg, "")
        self.addCleanup(setattr, self.hub, "bildschirmfoto", alt)
        seite.click("text=📷 Was läuft gerade?")
        seite.wait_for_function("() => { const b = document.querySelector('.eh-foto'); return b && !b.hidden && b.complete && b.naturalWidth > 0; }",
                                timeout=5000)
        self.assertEqual(self.fehler, [])

    def test_lange_listen_eingeklappt(self):
        """4.2: Nachrichten und andere Sammlungen klappen nach wenigen Einträgen ein."""
        for n in range(8):
            self.hub.familie.nachricht("Nachricht %d" % n, bleibt=True)
        seite = self.anmelden()
        karte = seite.locator("section.eh-karte", has_text="Nachrichten und Erinnerungen")
        karte.wait_for()
        self.assertEqual(karte.locator(":scope > .eh-eintrag").count(), 3)
        self.assertIn("weitere anzeigen", karte.locator("details.eh-mehr > summary").inner_text())
        self.assertFalse(karte.locator("details.eh-mehr .eh-eintrag").first.is_visible())
        karte.locator("details.eh-mehr > summary").click()
        self.assertTrue(karte.locator("details.eh-mehr .eh-eintrag").first.is_visible())
        self.assertEqual(self.fehler, [])

    def test_regeln_speichern_von_selbst(self):
        seite = self.anmelden()
        self.bereich(seite, "zeit")
        feld = seite.locator(".eh-karte", has_text="Wie viel Spielzeit am Tag?").locator("input[type=number]").first
        feld.fill("75")
        self.gespeichert(seite)
        self.assertEqual(self.hub.eltern_daten()["regeln"]["budget_min"]["schultag"], 75)
        # Erinnerung mit Wochentagen - ohne "a | b | c" (4.5: eigener Bereich „Erinnerungen & Pausen“)
        self.bereich(seite, "erinnerungen")
        seite.click("text=+ Erinnerung")
        eintrag = seite.locator(".eh-eintrag.spalte").last
        eintrag.locator("input[type=text]").fill("Zähneputzen!")
        self.gespeichert(seite)
        eintrag.locator(".eh-tage >> text=Sa").click()
        eintrag.locator(".eh-tage >> text=So").click()
        self.gespeichert(seite)
        er = self.hub.familie.einstellungen()["erinnerungen"]
        self.assertEqual(er[-1]["text"], "Zähneputzen!")
        self.assertEqual(er[-1]["tage"], [0, 1, 2, 3, 4])
        # falscher Wert: Fehler am Feld, nichts kaputt
        self.bereich(seite, "zeit")
        feld = seite.locator(".eh-karte", has_text="Wie viel Spielzeit am Tag?").locator("input[type=number]").first
        feld.fill("5000")
        seite.wait_for_selector(".eh-meldung.zeigen.fehler", timeout=4000)
        self.assertIn("eh-falsch", feld.get_attribute("class"))
        self.assertEqual(self.hub.eltern_daten()["regeln"]["budget_min"]["schultag"], 75)
        self.assertEqual([f for f in self.fehler if "400" not in f], [])   # die 400 war gewollt
        self.fehler.clear()
        feld.fill("80")
        self.gespeichert(seite)
        self.assertNotIn("eh-falsch", feld.get_attribute("class"))
        # Sperrzeit: Uhrzeit ändern, Ferien-Schalter
        nacht = seite.locator(".eh-sperre").first
        nacht.locator("input[type=time]").first.fill("19:00")
        self.gespeichert(seite)
        self.assertEqual(self.hub.eltern_daten()["regeln"]["sperrzeiten"][0]["von"], "19:00")
        # Gute Nacht steht im Bereich „Gute Nacht & Wecker“
        self.bereich(seite, "abend")
        seite.locator(".eh-zeile", has_text="Zur Nachtruhe automatisch öffnen").locator(".eh-schalter").click()
        self.gespeichert(seite)
        self.assertTrue(self.hub.familie.einstellungen()["gute_nacht"]["automatisch"])
        self.assertEqual(self.fehler, [])

    def test_hoerbuch_app_anlegen_und_plex_mit_limit(self):
        seite = self.anmelden()
        self.bereich(seite, "apps")
        seite.click("text=➕ Neue App anlegen")
        seite.click("text=🎧 Hörbuch-Ordner")
        neu = seite.locator(".eh-neu")
        neu.locator("input[type=text]").fill("Gute-Nacht-Hörbücher")
        neu.locator("input[type=url]").fill("http://server:8080/share/AbCd1234")
        neu.get_by_role("button", name="Anlegen", exact=True).click()
        seite.wait_for_selector("text=Gute-Nacht-Hörbücher")
        app = self.hub.app("gute-nacht-hoerbuecher")
        self.assertEqual((app["typ"], app["zeit"], app["start"]), ("hoerbuch", "frei", "http://server:8080/share/AbCd1234"))
        # Plex: tagsüber frei, nachts gesperrt - in der Sperrzeit "Schule" erlauben, "Nacht" bleibt aus
        seite.click(".eh-app >> text=Plex")
        offen = seite.locator(".eh-app[open]")
        offen.locator(".eh-chips-breit >> text=Schule").click()
        self.gespeichert(seite)
        self.assertEqual(self.hub.app("plex")["sperr_erlaubt"], ["Schule"])
        offen.locator(".eh-segment").get_by_role("button", name="Bildschirmzeit", exact=True).click()
        self.gespeichert(seite)
        offen.locator(".eh-zeile", has_text="höchstens am Schultag").locator("input").fill("60")
        self.gespeichert(seite)
        self.assertEqual((self.hub.app("plex")["zeit"], self.hub.app("plex")["limit_min"]), ("zaehlt", {"schultag": 60}))
        seite.screenshot(path=os.path.join(FOTOS, "eltern-apps-offen.png"), full_page=True)
        self.assertEqual(self.fehler, [])

    def test_46_zeitarten_spiele_ferien_erinnerungen(self):
        """4.6: Gaming-Zeit, nur eigenes Limit, eingebaute Spiele aus, Bewegungspause je Angebot, Ferien per Knopf,
        Erinnerung „nicht in den Ferien“."""
        seite = self.anmelden()
        self.bereich(seite, "zeit")
        seite.locator(".eh-zeile", has_text="Schultag").nth(1).locator("input").fill("40")     # Gaming Schultag
        self.gespeichert(seite)
        self.assertEqual(self.hub._regeln()["gaming_min"]["schultag"], 40)
        seite.select_option(".eh-zeile:has-text('Bundesland') select", "SH")
        seite.click("text=📅 Ferien eintragen")
        seite.wait_for_selector(".eh-meldung.zeigen:has-text('Schleswig-Holstein')")
        self.assertEqual(self.hub._regeln()["bundesland"], "SH")
        self.assertIn(["2026-12-21", "2027-01-06"], self.hub._regeln()["ferien"])
        self.assertIn("Mo 21.12.2026 – Mi 06.01.2027", seite.inner_text(".eh-ferienliste"))
        seite.click("text=+ eigene freie Tage")
        neu = seite.locator(".eh-ferienliste .eh-eintrag.spalte").first
        neu.locator("input[type=date]").first.fill("2027-05-07")
        neu.locator("input[type=date]").last.fill("2027-05-07")
        self.gespeichert(seite)
        self.assertIn(["2027-05-07", "2027-05-07"], self.hub._regeln()["ferien"])
        # Apps: Klassenkiste nur mit eigenem Limit, Snake ausschalten
        self.bereich(seite, "apps")
        seite.click(".eh-app[data-app=klassenkiste] summary")
        offen = seite.locator(".eh-app[open]")
        offen.locator(".eh-segment").get_by_role("button", name="Nur eigenes Limit", exact=True).click()
        self.gespeichert(seite)
        kk = self.hub.app("klassenkiste")
        self.assertEqual((kk["zeit"], kk["limit_min"]), ("frei", {"schultag": 30, "frei": 60}))
        seite.locator(".eh-app[data-app=spiel-snake] summary .eh-schalter").click()
        self.gespeichert(seite)
        self.assertIs(self.hub.app("spiel-snake")["aktiv"], False)
        self.assertNotIn("spiel-snake", [k["id"] for k in self.hub.kacheln()])
        # Bewegungspause nur bei bestimmten Angeboten, Erinnerung nicht in den Ferien
        self.bereich(seite, "erinnerungen")
        seite.click(".eh-bewegung-liste summary")
        seite.locator(".eh-bewegung-liste .eh-zeile", has_text="Memory").locator("input").click()
        self.gespeichert(seite)
        self.assertIs(self.hub.app("spiel-memory")["bewegung"], False)
        seite.click("text=+ Erinnerung")
        seite.locator(".eh-eintrag.spalte input[type=text]").last.fill("Sportsachen einpacken!")
        self.gespeichert(seite)
        seite.locator(".eh-eintrag.spalte").last.get_by_role("button", name="nicht in den Ferien").click()
        self.gespeichert(seite)
        self.assertEqual(self.hub.familie.einstellungen()["erinnerungen"][-1]["wann"], "schule")
        seite.screenshot(path=os.path.join(FOTOS, "eltern-46.png"), full_page=True)
        self.assertEqual(self.fehler, [])

    def test_youtube_reihenfolge_mit_pfeilen(self):
        """6.0: Kategorien und Videos lassen sich mit ↑ ↓ umsortieren; gespeichert wird sofort."""
        v = lambda i, t: {"art": "video", "id": i * 11, "titel": t}
        self.hub.einstellungen_aendern({"youtube": {"kategorien": [
            {"name": "Musik", "eintraege": [v("a", "Eins"), v("b", "Zwei"), v("c", "Drei")]}, {"name": "Tiere", "eintraege": []}]}})
        seite = self.anmelden()
        self.bereich(seite, "youtube")
        karte = seite.locator(".eh-abschnitt[data-bereich=youtube]")
        karte.locator("summary >> text=Musik").click()
        karte.locator("details[open] .eh-eintrag:has-text('Eins') .eh-pfeile >> text=↓").click()
        self.gespeichert(seite)
        self.assertEqual([e["titel"] for e in self.hub.youtube()["kategorien"][0]["eintraege"]], ["Zwei", "Eins", "Drei"])
        self.assertEqual(karte.locator("details[open]").count(), 1, "die Kategorie bleibt offen")
        karte.locator("details[open] .eh-zeile:has-text('Reihenfolge') >> text=↓").click()
        self.gespeichert(seite)
        self.assertEqual([k["name"] for k in self.hub.youtube()["kategorien"]], ["Tiere", "Musik"])
        self.assertEqual(self.fehler, [])

    def test_bass_songs_als_felder(self):
        seite = self.anmelden()
        self.bereich(seite, "musik")
        seite.click("text=+ Song")
        song = seite.locator(".eh-eintrag.spalte").last
        song.locator("input[type=text]").fill("Seven Nation Army")
        self.gespeichert(seite)
        song.locator("input[type=url]").first.fill("https://www.youtube.com/watch?v=abc")
        self.gespeichert(seite)
        self.assertEqual(self.hub.eltern_daten()["einstellungen"]["bass"][-1],
                         {"titel": "Seven Nation Army", "video": "https://www.youtube.com/watch?v=abc"})
        self.assertEqual(self.fehler, [])


if __name__ == "__main__":
    unittest.main()
