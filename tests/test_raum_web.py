"""4.3 Spielraum über HTTP und im echten Browser: Fernseher (Startseite) + Handy (Mitspiel-Seite)."""
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import web  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_v3_server import MITTWOCH, Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def anfrage(url, daten=None, kopf=None):
    k = {"Content-Type": "application/json"} if daten is not None else {}
    k.update(kopf or {})
    a = urllib.request.Request(url, data=json.dumps(daten).encode() if daten is not None else None, headers=k)
    try:
        with urllib.request.urlopen(a, timeout=5) as antwort:
            return antwort.status, json.loads(antwort.read() or b"{}")
    except urllib.error.HTTPError as fehler:
        roh = fehler.read()
        try:
            return fehler.code, json.loads(roh or b"{}")
        except ValueError:
            return fehler.code, {}


class RaumUeberHttp(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-raumweb-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(MITTWOCH))
        self.raum_server = web.baue_server(web.RaumHandler, self.hub, os.path.join(REPO, "web"),
                                           os.path.join(self.ordner, "z"), ("127.0.0.1", 0))
        threading.Thread(target=self.raum_server.serve_forever, daemon=True).start()
        self.addCleanup(self.raum_server.server_close)
        self.addCleanup(self.raum_server.shutdown)
        self.url = "http://127.0.0.1:%d" % self.raum_server.server_address[1]

    def test_aus_heisst_aus_und_kachel_versteckt(self):
        self.assertNotIn("spiel-handys", [k["id"] for k in self.hub.kacheln()])
        with self.assertRaisesRegex(ValueError, "ausgeschaltet"):
            self.hub.raum_oeffnen()
        status, _ = anfrage(self.url + "/mitspielen")
        self.assertEqual(status, 404, "ohne offenen Raum liefert der Zugang nichts")
        self.hub.einstellungen_aendern({"handyspiele": {"aktiv": True}})
        self.assertIn("spiel-handys", [k["id"] for k in self.hub.kacheln()])
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"handyspiele": {"aktiv": "ja"}})

    def test_beitreten_spielen_und_nichts_sonst(self):
        self.hub.einstellungen_aendern({"handyspiele": {"aktiv": True}})
        tv = self.hub.raum_oeffnen()
        self.assertTrue(tv["qr"].startswith("<svg"))
        self.assertTrue(tv["adresse"].endswith(":8767"))
        token = self.hub.raum.token
        for pfad in ("/eltern.html", "/index.html", "/js/start.js", "/api/status", "/api/eltern/daten", "/anleitung.pdf"):
            status, _ = anfrage(self.url + pfad)
            self.assertEqual(status, 404, pfad)
        status, _ = anfrage(self.url + "/api/raum/beitreten", {"schluessel": "falsch", "name": "Papa"})
        self.assertEqual(status, 400)
        status, d = anfrage(self.url + "/api/raum/beitreten", {"schluessel": token, "name": "Papa", "symbol": "🐼"})
        self.assertEqual(status, 200)
        geheim = d["geheim"]
        status, d2 = anfrage(self.url + "/api/raum/beitreten", {"schluessel": self.hub.raum.code.lower(), "name": "Mama"})
        self.assertEqual(status, 200, "Raumcode statt QR geht auch")
        status, z = anfrage(self.url + "/api/raum/zustand", kopf={"X-FF-Spieler": geheim})
        self.assertEqual((status, z["ansicht"], z["ich"]["name"]), (200, "warten", "Papa"))
        status, _ = anfrage(self.url + "/api/raum/zustand", kopf={"X-FF-Spieler": "nein"})
        self.assertEqual(status, 400)
        status, _ = anfrage(self.url + "/api/raum/zustand", kopf={"X-FF-Spieler": geheim, "Origin": "http://boese.example"})
        self.assertEqual(status, 200, "GET ohne Wirkung")
        status, _ = anfrage(self.url + "/api/raum/aktion", {"art": "buzz"}, {"X-FF-Spieler": geheim, "Origin": "http://boese.example"})
        self.assertEqual(status, 403, "fremde Herkunft wird abgewiesen")
        self.hub.raum_tv_aktion({"art": "start", "spiel": "buzzer"})
        status, z = anfrage(self.url + "/api/raum/aktion", {"art": "buzz"}, {"X-FF-Spieler": geheim})
        self.assertEqual(z["ansicht"], "wahl")
        self.hub.raum_schliessen()
        status, _ = anfrage(self.url + "/api/raum/zustand", kopf={"X-FF-Spieler": geheim})
        self.assertEqual(status, 400)

    def test_sperrzeit_schliesst_den_raum(self):
        self.hub.einstellungen_aendern({"handyspiele": {"aktiv": True}})
        self.hub.raum_oeffnen()
        self.hub.uhr.jetzt = MITTWOCH.replace(hour=21)            # Nachtruhe
        self.hub.tick(5)
        self.assertIsNone(self.hub.raum)
        self.assertTrue(any(a["art"] == "hinweis" for a in self.hub.auftraege_nach(0)[0]))


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class RaumImBrowser(unittest.TestCase):
    def test_fernseher_und_handy_spielen_buzzer(self):
        ordner = tempfile.mkdtemp(prefix="ff-raumbr-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(MITTWOCH))
        hub.einstellungen_aendern({"handyspiele": {"aktiv": True}})
        kiosk = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        raum = web.baue_server(web.RaumHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 0))
        for s in (kiosk, raum):
            threading.Thread(target=s.serve_forever, daemon=True).start()
            self.addCleanup(s.server_close)
            self.addCleanup(s.shutdown)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            fehler = []
            tv = browser.new_page(viewport={"width": 1600, "height": 900})
            tv.on("pageerror", lambda e: fehler.append("TV: " + str(e)))
            tv.goto("http://127.0.0.1:8765/")
            tv.click(".kachel[data-id=spiel-handys]")
            tv.wait_for_selector(".hs-qr svg")
            self.assertIn(hub.raum.code, tv.inner_text(".hs-adresse"))
            handy = browser.new_page(viewport={"width": 390, "height": 800}, is_mobile=True, has_touch=True)
            handy.on("pageerror", lambda e: fehler.append("Handy: " + str(e)))
            handy.goto("http://127.0.0.1:%d/mitspielen?r=%s" % (raum.server_address[1], hub.raum.token))
            handy.fill("input[placeholder='Dein Name']", "Papa")
            handy.click("button[type=submit]")
            handy.wait_for_selector("text=Du bist dabei!")
            tv.wait_for_selector(".hs-zeile:has-text('Papa')")
            tv.keyboard.press("Enter")                              # Buzzer-Runde
            tv.wait_for_selector("text=welche Fragen?")
            tv.keyboard.press("Enter")                              # Gemischt
            tv.wait_for_selector(".hs-frage")
            handy.wait_for_selector(".buzzer")
            handy.click(".buzzer")
            handy.wait_for_selector(".option")
            tv.wait_for_selector("text=antwortet")
            richtig = hub.raum.spiel.richtig
            handy.click(".option:text-is('%s')" % richtig)
            tv.wait_for_selector(".hs-option.richtig")
            self.assertNotIn("null", tv.inner_text(".hs-ansicht"))
            self.assertEqual(hub.raum.spieler[[s for s in hub.raum.spieler if s != "tv"][0]]["punkte"], 1)
            tv.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "handys-buzzer-tv.png"))
            handy.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "handys-buzzer-handy.png"))
            tv.keyboard.press("Escape")                             # zur Auswahl
            tv.wait_for_selector(".hs-lobby")
            tv.keyboard.press("Escape")                             # Raum schließen
            tv.wait_for_selector(".hs-lobby", state="detached")
            self.assertIsNone(hub.raum)
            self.assertEqual(fehler, [])

    def test_alle_spiele_am_fernseher_ohne_fehler(self):
        """Jede Spielansicht am Fernseher zeichnet ohne Fehler; Malen kommt vom Handy auf den Fernseher; Ton-Treffer
        spielt vor, hört zu (Test-Mikrofon von Chromium) und meldet das Ergebnis."""
        ordner = tempfile.mkdtemp(prefix="ff-raumalle-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(MITTWOCH))
        hub.einstellungen_aendern({"handyspiele": {"aktiv": True}})
        kiosk = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        raum = web.baue_server(web.RaumHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 0))
        for s in (kiosk, raum):
            threading.Thread(target=s.serve_forever, daemon=True).start()
            self.addCleanup(s.server_close)
            self.addCleanup(s.shutdown)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                                               "--autoplay-policy=no-user-gesture-required"])
            fehler = []
            tv = browser.new_page(viewport={"width": 1600, "height": 900})
            tv.on("pageerror", lambda e: fehler.append("TV: " + str(e)))
            tv.goto("http://127.0.0.1:8765/")
            tv.click(".kachel[data-id=spiel-handys]")
            tv.wait_for_selector(".hs-qr svg")
            handys = []
            for name in ("Papa", "Mama"):
                h = browser.new_page(viewport={"width": 390, "height": 800}, is_mobile=True, has_touch=True)
                h.on("pageerror", lambda e: fehler.append("Handy: " + str(e)))
                h.goto("http://127.0.0.1:%d/mitspielen?r=%s" % (raum.server_address[1], hub.raum.token))
                h.fill("input[placeholder='Dein Name']", name)
                h.click("button[type=submit]")
                h.wait_for_selector("text=Du bist dabei!")
                handys.append(h)
            for spiel, opt, zeichen in (("quiz", {"paket": "einmaleins"}, ".hs-bahn"), ("raumschiff", {"stufe": 2}, ".hs-lampe"),
                                        ("malen", {}, ".hs-leinwand")):
                hub.raum_tv_aktion(dict({"art": "start", "spiel": spiel}, **opt))
                tv.wait_for_selector(zeichen)
                tv.wait_for_timeout(500)
                self.assertNotIn("null", tv.inner_text(".hs-ansicht"), spiel)
                tv.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "handys-%s-tv.png" % spiel))
                if spiel == "raumschiff":
                    handys[0].wait_for_selector(".handbuch")
                    handys[0].screenshot(path=os.path.join(REPO, ".local", "bildschirm", "handys-raumschiff-handy.png"))
                if spiel == "malen":
                    maler = next(h for h in handys if h.query_selector(".malflaeche") or h.wait_for_timeout(300) or h.query_selector(".malflaeche"))
                    box = maler.query_selector(".malflaeche").bounding_box()
                    maler.mouse.move(box["x"] + 40, box["y"] + 40)
                    maler.mouse.down()
                    for i in range(12):
                        maler.mouse.move(box["x"] + 40 + i * 20, box["y"] + 40 + i * 12)
                    maler.mouse.up()
                    tv.wait_for_function("() => true")
                    for _ in range(30):
                        if hub.raum.spiel.striche:
                            break
                        tv.wait_for_timeout(200)
                    self.assertTrue(hub.raum.spiel.striche, "Striche vom Handy angekommen")
                    tv.wait_for_timeout(800)
                    hell = tv.evaluate("""() => { const c = document.querySelector('.hs-leinwand').getContext('2d');
                        const d = c.getImageData(0, 0, 960, 720).data; let dunkel = 0;
                        for (let i = 0; i < d.length; i += 4) if (d[i] < 100) dunkel++; return dunkel; }""")
                    self.assertGreater(hell, 50, "der Fernseher zeichnet die Striche")
                    tv.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "handys-malen-tv.png"))
                    maler.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "handys-malen-handy.png"))
                hub.raum_tv_aktion({"art": "lobby"})
                tv.wait_for_selector(".hs-lobby")
            hub.raum_tv_aktion({"art": "start", "spiel": "ton"})
            tv.wait_for_selector(".hs-leiter")
            for _ in range(150):                                    # vorspielen -> singen -> Ergebnis (Test-Mikrofon)
                if hub.raum.spiel and hub.raum.spiel.phase == "daumen":
                    break
                tv.wait_for_timeout(200)
            self.assertEqual(hub.raum.spiel.phase, "daumen")
            self.assertEqual(len(hub.raum.spiel.treffer), 3)
            tv.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "handys-ton-tv.png"))
            for spiel, zeichen in (("rakete", ".hs-himmel"), ("klatsch", ".hs-takt")):    # 4.4
                hub.raum_tv_aktion({"art": "lobby"})
                hub.raum_tv_aktion({"art": "start", "spiel": spiel})
                tv.wait_for_selector(zeichen)
                for _ in range(150):
                    if hub.raum.spiel and hub.raum.spiel.phase == "daumen":
                        break
                    if hub.raum.spiel.phase == "countdown":
                        hub.uhr.weiter(3.5)                         # Testuhr steht - Countdown vorspulen
                    tv.wait_for_timeout(200)
                self.assertEqual(hub.raum.spiel.phase, "daumen", spiel)
                self.assertNotIn("null", tv.inner_text(".hs-ansicht"))
                tv.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "handys-%s-tv.png" % spiel))
            self.assertEqual(fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()
