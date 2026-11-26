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

    # 6.9.38: sechs Reiter; Apps ist eine eigene Seite (Übersicht + Detailseite je App)
    REITER = {"zeit": "Regeln", "abend": "Regeln", "erinnerungen": "Regeln", "internet": "Regeln",
              "meintag": "Franzi", "sterne": "Franzi", "franzi": "Franzi", "shop": "Franzi",
              "design": "Aussehen", "bildplaetze": "Aussehen", "klaenge": "Aussehen",
              "telegram": "Mehr", "bilder": "Mehr", "geraet": "Mehr", "hilfe": "Mehr"}

    def bereich(self, seite, bereich):
        """6.0: Reiter unten antippen, dann den Bereich aufklappen."""
        seite.click(".eh-leiste >> text=" + self.REITER[bereich])
        seite.click(".eh-abschnitt[data-bereich=%s] .eh-abschnitt-kopf" % bereich)
        seite.wait_for_selector(".eh-abschnitt.offen[data-bereich=%s] .eh-abschnitt-inhalt" % bereich)

    def app(self, seite, app_id):
        """6.9.38: Reiter „Apps“, dann die Detailseite einer App."""
        seite.click(".eh-leiste >> text=Apps")
        seite.click(".eh-app-zeile[data-app=%s] .eh-app-name" % app_id)
        seite.wait_for_selector(".eh-detail-kopf")
        return seite.locator(".eh-inhalt")

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
        for name in ("Heute", "Regeln", "Apps", "Franzi", "Aussehen", "Mehr"):
            seite.click(".eh-leiste >> text=" + name)
            seite.wait_for_timeout(250)
            breite = seite.evaluate("document.documentElement.scrollWidth")
            self.assertLessEqual(breite, 390, "%s ist breiter als das Handy" % name)
            seite.screenshot(path=os.path.join(FOTOS, "eltern-%s.png" % name.lower()), full_page=True)
        # 6.0: jeder Bereich jedes Reiters klappt ohne Fehler auf; die Zurück-Taste klappt wieder zu
        self.assertEqual(len(self.REITER), 15)
        for b in self.REITER:
            self.bereich(seite, b)
            self.assertGreaterEqual(seite.locator(".eh-abschnitt.offen .eh-karte").count(), 1, b)
            breite = seite.evaluate("document.documentElement.scrollWidth")
            self.assertLessEqual(breite, 390, "%s ist breiter als das Handy" % b)
            seite.screenshot(path=os.path.join(FOTOS, "eltern-bereich-%s.png" % b), full_page=True)
            if b == "zeit":
                seite.go_back()                                   # Zurück-Taste des Handys
                seite.wait_for_selector(".eh-abschnitt[data-bereich=zeit]:not(.offen)")
        # 6.9.38: jede App hat eine Detailseite ohne Fehler und ohne Quer-Scrollen; „‹ Apps“ führt zurück
        seite.click(".eh-leiste >> text=Apps")
        ids = seite.eval_on_selector_all(".eh-app-zeile", "z => z.map((e) => e.dataset.app)")
        self.assertGreaterEqual(len(ids), 30)
        for app_id in ids:
            seite.evaluate("id => { location.hash = '#apps/' + id; }", app_id)
            seite.wait_for_selector(".eh-detail-kopf")
            self.assertGreaterEqual(seite.locator(".eh-inhalt .eh-karte").count(), 1, app_id)
            self.assertLessEqual(seite.evaluate("document.documentElement.scrollWidth"), 390, app_id)
        seite.click(".eh-zurueck")
        seite.wait_for_selector(".eh-app-gruppen")
        # Suche und Filter
        seite.fill(".eh-suche", "snake")
        self.assertEqual(seite.locator(".eh-app-zeile").count(), 1)
        seite.fill(".eh-suche", "")
        seite.get_by_role("button", name="⚠️ Einrichten").click()
        self.assertTrue(all(x in ("gute-nacht", "plex", "familie", "buecher", "klassenkiste", "kinderwelten")
                            for x in seite.eval_on_selector_all(".eh-app-zeile", "z => z.map((e) => e.dataset.app)")))
        seite.get_by_role("button", name="Alle", exact=True).click()
        # Lesezeichen von früher führen weiter (#erinnerungen -> Reiter Regeln, aufgeklappt; alte Bereiche -> App)
        seite.evaluate("location.hash = '#erinnerungen'")
        seite.wait_for_selector(".eh-abschnitt.offen[data-bereich=erinnerungen]")
        seite.evaluate("location.hash = '#inhalte/youtube'")
        seite.wait_for_selector(".eh-detail-kopf h2:has-text('YouTube')")
        seite.evaluate("location.hash = '#regeln/franzi'")
        seite.wait_for_selector(".eh-abschnitt.offen[data-bereich=franzi]")
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
        seite.click(".eh-leiste >> text=Apps")
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
        offen = self.app(seite, "plex")
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
        offen = self.app(seite, "klassenkiste")
        offen.locator(".eh-segment").get_by_role("button", name="Nur eigenes Limit", exact=True).click()
        self.gespeichert(seite)
        kk = self.hub.app("klassenkiste")
        self.assertEqual((kk["zeit"], kk["limit_min"]), ("frei", {"schultag": 30, "frei": 60}))
        seite.click(".eh-leiste >> text=Apps")
        seite.locator(".eh-app-zeile[data-app=spiel-snake] .eh-schalter").click()
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

    def test_6939_zeit_fuer_alle_eines_bereichs(self):
        """6.9.39: Eine Sammel-Einstellung setzt alle Apps eines Bereichs (eingebaute und eigene); einzeln abweichen geht weiter."""
        seite = self.anmelden()
        seite.click(".eh-leiste >> text=Apps")
        gruppe = seite.locator(".eh-gruppe[data-gruppe=spiele]")
        gruppe.locator(".eh-alle > summary").click()
        gruppe.locator(".eh-alle .eh-segment").get_by_role("button", name="Nur eigenes Limit", exact=True).click()
        gruppe.locator(".eh-alle .eh-zeile", has_text="Schultag").locator("input").fill("25")
        gruppe.locator(".eh-alle .eh-zeile", has_text="Wochenende").locator("input").fill("50")
        gruppe.locator(".eh-alle .eh-knopf").click()
        seite.wait_for_selector(".eh-meldung.zeigen:has-text('übernommen')")
        for app_id in ("spiel-snake", "spiel-memory", "spiel-steine"):
            a = self.hub.app(app_id)
            self.assertEqual((a["zeit"], a["limit_min"]), ("frei", {"schultag": 25, "frei": 50}), app_id)
        self.assertIn("eigenes Limit · höchstens 25/50 min",
                      seite.locator(".eh-gruppe[data-gruppe=spiele] .eh-alle > summary small").inner_text())
        # eigene Apps (Filme: Plex, YouTube) – Gaming-Zeit ohne Limit
        gruppe = seite.locator(".eh-gruppe[data-gruppe=filme]")
        gruppe.locator(".eh-alle > summary").click()
        gruppe.locator(".eh-alle .eh-segment").get_by_role("button", name="Gaming-Zeit", exact=True).click()
        gruppe.locator(".eh-alle .eh-knopf").click()
        seite.wait_for_selector(".eh-gruppe[data-gruppe=filme] .eh-alle > summary small:has-text('Gaming-Zeit')")
        self.assertEqual(self.hub.app("plex")["zeit"], "gaming")
        self.assertEqual(self.hub.app("youtube")["zeit"], "gaming")
        self.assertNotIn("limit_min", self.hub.app("youtube"))
        self.assertEqual(self.fehler, [])

    def test_6940_klaenge_paket_ereignis_ordner(self):
        """6.9.40: Paket setzt alle Ereignisse, ein Ereignis einzeln, Ordner je Art wird gespeichert."""
        seite = self.anmelden()
        self.bereich(seite, "klaenge")
        seite.click(".eh-pakete [data-paket=sanft]")
        self.gespeichert(seite)
        kl = self.hub.eltern_daten()["einstellungen"]["klaenge"]
        self.assertEqual((kl["ereignisse"]["stern"], kl["bedienung_laut"]), ("harfe", 40))
        seite.select_option(".eh-ereignis[data-ereignis=ok] select", "xylophon")
        self.gespeichert(seite)
        self.assertEqual(self.hub.eltern_daten()["einstellungen"]["klaenge"]["ereignisse"]["ok"], "xylophon")
        seite.click("text=Ordner je Art (8)")
        seite.fill(".eh-klang-ordner[data-art=tasten] input", "http://server:8080/share/Tasten123")
        seite.wait_for_selector(".eh-meldung.zeigen", timeout=4000)
        self.assertEqual(self.hub.klaenge_ordner("tasten"), "http://server:8080/share/Tasten123")
        self.assertEqual(self.hub.startseite_anzeige()["klang"]["ereignisse"]["ok"], "xylophon")
        self.hub.einstellungen_aendern({"klaenge": {"ordner": ""}})     # der Test-Ordner ist nicht erreichbar - für die anderen Tests weg
        self.assertEqual([f for f in self.fehler if "klaenge-eigen" not in f and "502" not in f and "400" not in f], [])

    def test_6941_film_archiv_freigeben_und_belohnung(self):
        """6.9.41: Ordner eintragen, Inhalt erscheint, Film freigeben und als Belohnung markieren."""
        from test_hoerbuch import starte_attrappe
        attrappe, link = starte_attrappe()
        self.addCleanup(attrappe.shutdown)
        seite = self.anmelden()
        seite.click(".eh-leiste >> text=Apps")
        seite.click(".eh-app-zeile[data-app=archiv-video] .eh-app-name")
        seite.wait_for_selector(".eh-detail-kopf h2:has-text('Filme')")
        seite.fill(".eh-karte:has-text('Film-Archiv') input[type=url]", link)
        seite.wait_for_selector(".eh-archiv[data-pfad='Bibi Blocksberg']", timeout=6000)
        seite.locator(".eh-archiv[data-pfad='Bibi Blocksberg'] .eh-schalter").click()
        self.gespeichert(seite)
        seite.locator(".eh-archiv[data-pfad='Bibi Blocksberg']").get_by_role("button", name="🌙 auch in Sperrzeiten").click()
        self.gespeichert(seite)
        a = self.hub.archiv()["video"]
        self.assertEqual(a["ordner"], link)
        self.assertEqual(a["freigaben"], {"Bibi Blocksberg": {"frei": False, "sperre": True}})
        self.assertTrue(any(k["id"] == "archiv-video" for k in self.hub.kacheln()))
        self.hub.einstellungen_aendern({"archiv": {}})               # für die anderen Tests wieder aus
        self.assertEqual(self.fehler, [])

    def test_6952_kachel_reihenfolge(self):
        """6.9.52: ↑↓ in der Apps-Übersicht ordnet die Kacheln eines Bereichs (gilt für die Startseite)."""
        seite = self.anmelden()
        seite.click(".eh-leiste >> text=Apps")
        gruppe = seite.locator(".eh-gruppe[data-gruppe=spiele]")
        zweite = gruppe.locator(".eh-app-zeile").nth(1).get_attribute("data-app")
        gruppe.locator(".eh-app-zeile").nth(1).locator(".eh-pfeile button").first.click()      # ↑
        seite.wait_for_selector(".eh-meldung.zeigen:not(.fehler)", timeout=4000)
        self.assertEqual(self.hub.einstellungen["kachel_reihenfolge"]["spiele"][0], zweite)
        self.assertEqual(seite.locator(".eh-gruppe[data-gruppe=spiele] .eh-app-zeile").first.get_attribute("data-app"), zweite)
        self.assertEqual(self.hub.startseite_anzeige()["reihenfolge"]["spiele"][0], zweite)
        self.hub.einstellungen_aendern({"kachel_reihenfolge": {}})
        self.assertEqual(self.fehler, [])

    def test_youtube_reihenfolge_mit_pfeilen(self):
        """6.0: Kategorien und Videos lassen sich mit ↑ ↓ umsortieren; gespeichert wird sofort."""
        v = lambda i, t: {"art": "video", "id": i * 11, "titel": t}
        self.hub.einstellungen_aendern({"youtube": {"kategorien": [
            {"name": "Musik", "eintraege": [v("a", "Eins"), v("b", "Zwei"), v("c", "Drei")]}, {"name": "Tiere", "eintraege": []}]}})
        seite = self.anmelden()
        karte = self.app(seite, "youtube")
        karte.locator("summary >> text=Musik").click()
        karte.locator("details[open] .eh-eintrag:has-text('Eins') .eh-pfeile >> text=↓").click()
        self.gespeichert(seite)
        self.assertEqual([e["titel"] for e in self.hub.youtube()["kategorien"][0]["eintraege"]], ["Zwei", "Eins", "Drei"])
        self.assertEqual(karte.locator("details[open]").count(), 1, "die Kategorie bleibt offen")
        karte.locator("details[open] .eh-zeile:has-text('Reihenfolge') >> text=↓").click()
        self.gespeichert(seite)
        self.assertEqual([k["name"] for k in self.hub.youtube()["kategorien"]], ["Tiere", "Musik"])
        self.assertEqual(self.fehler, [])

    def test_standby_test_beim_wecker(self):
        """6.1: Stand des CEC-Tests und Knopf; das Ergebnis von eingabe.py erscheint."""
        seite = self.anmelden()
        self.bereich(seite, "abend")
        karte = seite.locator(".eh-abschnitt[data-bereich=abend]")
        karte.locator("text=Fernseher nachts ausschalten").wait_for()
        karte.locator("text=Noch nicht geprüft").wait_for()
        karte.locator("text=Jetzt testen").click()
        karte.locator("text=Test läuft").wait_for()
        self.assertEqual(self.hub.cec["befehl"], "test")
        self.hub.cec_test_ergebnis(aus=True, an=True)
        karte.locator("text=Der Wecker kann den Fernseher einschalten").wait_for(timeout=8000)
        self.assertEqual(self.fehler, [])

    def test_bass_songs_als_felder(self):
        seite = self.anmelden()
        self.app(seite, "spiel-bass")
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
