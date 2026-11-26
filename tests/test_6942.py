"""6.9.42: eigene Hintergründe der Startseite (hochladen, prüfen, je Farbe wählen, löschen)."""
import base64
import os
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from datetime import datetime

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))
from fernsehfranzi import bilder, design  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402


def png(b, h):
    """Kleines, gültiges PNG mit beliebiger Größe im Kopf (eine Farbe, stark komprimiert)."""
    roh = b"".join(b"\x00" + b"\x20\x40\x80" * b for _ in range(h))
    def block(art, inhalt):
        return struct.pack(">I", len(inhalt)) + art + inhalt + struct.pack(">I", zlib.crc32(art + inhalt) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + block(b"IHDR", struct.pack(">IIBBBBB", b, h, 8, 2, 0, 0, 0)) + \
        block(b"IDAT", zlib.compress(roh, 9)) + block(b"IEND", b"")


def jpeg_kopf(b, h):
    return b"\xff\xd8\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + \
        b"\xff\xc0" + struct.pack(">HBHH", 17, 8, h, b) + b"\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01" + b"\xff\xd9"


class Modul(unittest.TestCase):
    def test_art_und_groesse(self):
        self.assertEqual(bilder.art_und_groesse(png(1920, 1080)), ("png", 1920, 1080))
        self.assertEqual(bilder.art_und_groesse(jpeg_kopf(1280, 720)), ("jpg", 1280, 720))
        with self.assertRaises(ValueError):
            bilder.art_und_groesse(b"GIF89a....")
        with self.assertRaises(ValueError):
            bilder.pruefe_hintergrund(png(400, 300))              # zu klein
        with self.assertRaises(ValueError):
            bilder.pruefe_hintergrund(png(5000, 4000))            # zu viele Pixel

    def test_design_pruefe(self):
        design.pruefe({"hintergruende": {"blau": "hg-0123456789ab.png"}})
        for falsch in ({"hintergruende": {"quatsch": "hg-0123456789ab.png"}}, {"hintergruende": {"blau": "../x.png"}}):
            with self.assertRaises(ValueError):
                design.pruefe(falsch)


class Hub(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-6942-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(datetime(2026, 11, 25, 16)))

    def test_hochladen_waehlen_loeschen(self):
        name = self.hub.hintergrund_speichern(png(1920, 1080))
        self.assertEqual(self.hub.hintergruende(), [name])
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"design": {"hintergruende": {"blau": "hg-000000000000.png"}}})   # gibt es nicht
        self.hub.einstellungen_aendern({"design": {"hintergruende": {"blau": name}}})
        self.hub.einstellungen["startseite"] = {"lieblinge": [], "thema": "blau"}
        self.assertEqual(self.hub.startseite_anzeige()["design"]["bild"], "/api/hintergrund?datei=" + name)
        self.hub.einstellungen["startseite"] = {"lieblinge": [], "thema": "gruen"}
        self.assertIsNone(self.hub.startseite_anzeige()["design"]["bild"])
        self.hub.hintergrund_loeschen(name)
        self.assertEqual(self.hub.hintergruende(), [])
        self.assertEqual(self.hub.einstellungen["design"]["hintergruende"], {})
        with self.assertRaises(ValueError):
            self.hub.hintergrund_datei("../einstellungen.json")


class Web(unittest.TestCase):
    """Hochladen über die Eltern-Seite (Base64) und Ausliefern an den Fernseher."""
    def test_hochladen_und_holen(self):
        import json
        import threading
        import urllib.request
        from fernsehfranzi import web
        from test_eltern_handy import PIN
        ordner = tempfile.mkdtemp(prefix="ff-6942w-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(datetime(2026, 11, 25, 16)))
        hub.pin_festlegen(PIN, erster_start_am_tv=True)
        srv = web.baue_server(web.LanHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 0))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        url = "http://127.0.0.1:%d" % srv.server_address[1]
        def post(pfad, daten, token=""):
            r = urllib.request.Request(url + pfad, data=json.dumps(daten).encode(), headers={"Content-Type": "application/json", "X-FF-Eltern": token})
            try:
                with urllib.request.urlopen(r) as a:
                    return a.status, json.loads(a.read())
            except urllib.error.HTTPError as f:
                return f.code, json.loads(f.read())
        bild = "data:image/png;base64," + base64.b64encode(png(1920, 1080)).decode()
        self.assertNotEqual(post("/api/eltern/hintergrund", {"daten": bild})[0], 200)            # ohne PIN nicht
        token = post("/api/eltern/anmelden", {"pin": PIN})[1]["token"]
        code, antwort = post("/api/eltern/hintergrund", {"daten": bild}, token)
        self.assertEqual(code, 200, antwort)
        with urllib.request.urlopen(url + "/api/hintergrund?datei=" + antwort["datei"]) as a:
            self.assertEqual(a.headers["Content-Type"], "image/png")
        code, antwort = post("/api/eltern/hintergrund", {"daten": "data:image/png;base64," + base64.b64encode(b"kaputt").decode()}, token)
        self.assertEqual(code, 400)


if __name__ == "__main__":
    unittest.main()
