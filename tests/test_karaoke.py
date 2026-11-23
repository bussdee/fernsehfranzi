"""4.4 Karaoke mit den Liedern der Klassenkiste: Anmeldung aus dem Kiosk-Profil, nur lesen, Musik durchreichen."""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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

MUSIK = b"ID3" + b"\x00" * 4000


class Klassenkiste(BaseHTTPRequestHandler):
    anfragen = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        Klassenkiste.anfragen.append((self.command, self.path, self.headers.get("Cookie")))
        if self.headers.get("Cookie") != "PHPSESSID=kind123":
            self.send_response(401)
            self.end_headers()
            return
        if self.path == "/api/playlists/karaoke":
            inhalt = json.dumps({"songs": [
                {"id": "s1", "title": "Alle meine Entchen", "playlist": "Kinderlieder", "duration": 30,
                 "lyrics": "[Refrain]\nAlle meine Entchen\nschwimmen auf dem See\n\nKöpfchen in das Wasser",
                 "marken": [0, 1000, None], "src": "/api/playlists/song/s1/stream"},
                {"id": "s3", "title": "Falsche Marken", "lyrics": "eins", "marken": ["x", True]},
                {"id": "../boese", "title": "x", "lyrics": "y"}, {"id": "s2", "title": "Ohne Text", "lyrics": ""}]}).encode()
            typ = "application/json"
        elif self.path == "/api/playlists/song/s1/stream":
            inhalt, typ = MUSIK, "audio/mpeg"
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(inhalt)))
        self.end_headers()
        self.wfile.write(inhalt)

    def do_POST(self):
        Klassenkiste.anfragen.append(("POST", self.path, None))
        self.send_response(405)
        self.end_headers()


def kiosk_attrappe(hub, stopp, cookie="PHPSESSID=kind123"):
    """Spielt kiosk.py: beantwortet den Auftrag kk_anmeldung mit dem Cookie aus dem Profil."""
    gesehen = 0
    while not stopp.is_set():
        auftraege, _ = hub.auftraege_nach(gesehen)
        for a in auftraege:
            gesehen = max(gesehen, a["nr"])
            if a["art"] == "kk_anmeldung":
                hub.kk_anmeldung_empfangen(a["kk"], cookie)
        time.sleep(0.05)


class Karaoke(unittest.TestCase):
    def setUp(self):
        self.kk = ThreadingHTTPServer(("127.0.0.1", 0), Klassenkiste)
        threading.Thread(target=self.kk.serve_forever, daemon=True).start()
        self.addCleanup(self.kk.server_close)
        self.addCleanup(self.kk.shutdown)
        Klassenkiste.anfragen = []
        self.ordner = tempfile.mkdtemp(prefix="ff-kk-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(MITTWOCH))
        apps = self.hub.eltern_daten()["apps"]
        next(a for a in apps if a["id"] == "klassenkiste")["start"] = "http://127.0.0.1:%d/" % self.kk.server_address[1]
        self.hub.katalog_aendern(apps)
        self.stopp = threading.Event()
        self.addCleanup(self.stopp.set)

    def test_lieder_nur_lesen_mit_anmeldung(self):
        self.assertIn("spiel-karaoke", [k["id"] for k in self.hub.kacheln()])
        threading.Thread(target=kiosk_attrappe, args=(self.hub, self.stopp), daemon=True).start()
        lieder = self.hub.karaoke_liste()
        self.assertEqual([l["id"] for l in lieder], ["s1", "s3"], "nur gültige Lieder mit Text")
        self.assertIn("Entchen", lieder[0]["text"])
        self.assertEqual(lieder[0]["marken"], [0.0, 1000.0, None], "4.6.1: Zeitmarken je gesungener Zeile kommen mit")
        self.assertIsNone(lieder[1]["marken"], "ungültige Marken fallen weg")
        adresse, kopf = self.hub.karaoke_musik("s1")
        self.assertTrue(adresse.endswith("/api/playlists/song/s1/stream"))
        with self.assertRaises(ValueError):
            self.hub.karaoke_musik("../x")
        self.assertTrue(all(m == "GET" for m, _, _ in Klassenkiste.anfragen), "nur lesen")
        self.assertNotIn("PHPSESSID", json.dumps(self.hub.eltern_daten()), "die Anmeldung geht nie an einen Browser")

    def test_ohne_anmeldung_freundlicher_hinweis(self):
        threading.Thread(target=kiosk_attrappe, args=(self.hub, self.stopp, ""), daemon=True).start()
        with self.assertRaisesRegex(ValueError, "angemeldet"):
            self.hub.karaoke_liste()

    def test_ohne_klassenkiste_keine_kachel(self):
        apps = self.hub.eltern_daten()["apps"]
        next(a for a in apps if a["id"] == "klassenkiste")["aktiv"] = False
        self.hub.katalog_aendern(apps)
        self.assertNotIn("spiel-karaoke", [k["id"] for k in self.hub.kacheln()])

    @unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
    @unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
    def test_karaoke_am_fernseher(self):
        threading.Thread(target=kiosk_attrappe, args=(self.hub, self.stopp), daemon=True).start()
        server = web.baue_server(web.KioskHandler, self.hub, os.path.join(REPO, "web"), os.path.join(self.ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8765/api/karaoke/musik?id=s1",
                                                           headers={"X-FF-Token": self.hub.token})) as a:
            self.assertEqual(a.read(), MUSIK, "Musik wird durchgereicht")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                                               "--autoplay-policy=no-user-gesture-required"])
            seite = browser.new_page(viewport={"width": 1600, "height": 900})
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            seite.goto("http://127.0.0.1:8765/")
            seite.click(".kachel[data-id=spiel-karaoke]")
            seite.wait_for_selector(".ka-eintrag.gewaehlt")
            self.assertIn("Alle meine Entchen", seite.inner_text(".ka-liste"))
            seite.keyboard.press("Enter")
            seite.wait_for_selector(".ka-text")
            self.assertIn("schwimmen auf dem See", seite.inner_text(".ka-text"))
            # 4.6.1: die gerade gesungene Zeile ist markiert (Überschrift „[Refrain]“ zählt nicht mit)
            seite.wait_for_selector(".ka-text.mit-marken p.dran")
            self.assertEqual(seite.inner_text(".ka-text p.dran"), "Alle meine Entchen")
            self.assertEqual(seite.inner_text(".ka-text p.ka-ueberschrift"), "Refrain")
            seite.wait_for_timeout(800)
            seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "karaoke.png"))
            seite.keyboard.press("Escape")
            seite.wait_for_selector(".ka-liste")
            self.assertEqual(fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()
