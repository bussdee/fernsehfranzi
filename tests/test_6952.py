"""6.9.52: Bild-Plätze - eigene Bilder statt der Vorgaben (Prüfung, Vorrang, zurück zur Vorgabe)."""
import base64
import json
import os
import shutil
import struct
import sys
import tempfile
import threading
import unittest
import urllib.request
import zlib
from datetime import datetime

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))
from fernsehfranzi import bilder, web  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402


def png(b, h, alpha=False):
    farbtyp, px = (6, b"\x20\x40\x80\x00") if alpha else (2, b"\x20\x40\x80")
    roh = b"".join(b"\x00" + px * b for _ in range(h))
    def block(art, inhalt):
        return struct.pack(">I", len(inhalt)) + art + inhalt + struct.pack(">I", zlib.crc32(art + inhalt) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + block(b"IHDR", struct.pack(">IIBBBBB", b, h, 8, farbtyp, 0, 0, 0)) + \
        block(b"IDAT", zlib.compress(roh, 9)) + block(b"IEND", b"")


class Pruefung(unittest.TestCase):
    def test_regeln(self):
        bilder.pruefe_bildplatz("raeume/raum-1.jpg", png(1600, 1320))
        bilder.pruefe_bildplatz("franzi/augen-offen.png", png(512, 512, alpha=True))
        for platz, daten in (("raeume/raum-1.jpg", png(1600, 900)),            # falsches Verhältnis
                             ("raeume/raum-1.jpg", png(800, 660)),             # zu klein
                             ("franzi/augen-offen.png", png(512, 512)),        # nicht durchsichtig
                             ("gibts/nicht.png", png(512, 512, alpha=True))):
            with self.assertRaises(ValueError, msg=platz):
                bilder.pruefe_bildplatz(platz, daten)

    def test_vorgaben_existieren(self):
        for platz in bilder.BILDPLAETZE:
            self.assertTrue(os.path.isfile(os.path.join(REPO, "web", "bilder", platz)), platz)


class Web(unittest.TestCase):
    def test_hochladen_vorrang_und_zuruecksetzen(self):
        from test_eltern_handy import PIN
        ordner = tempfile.mkdtemp(prefix="ff-6952-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(datetime(2026, 11, 25, 16)))
        hub.pin_festlegen(PIN, erster_start_am_tv=True)
        lan = web.baue_server(web.LanHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 0))
        threading.Thread(target=lan.serve_forever, daemon=True).start()
        self.addCleanup(lan.shutdown)
        url = "http://127.0.0.1:%d" % lan.server_address[1]
        def post(pfad, daten, token=""):
            r = urllib.request.Request(url + pfad, data=json.dumps(daten).encode(), headers={"Content-Type": "application/json", "X-FF-Eltern": token})
            try:
                with urllib.request.urlopen(r) as a:
                    return a.status
            except urllib.error.HTTPError as f:
                return f.code
        def hole(pfad):
            with urllib.request.urlopen(url + pfad) as a:
                return a.headers["Content-Type"], a.read()
        vorgabe = hole("/bilder/raeume/raum-2.jpg")[1]
        eigen = png(1600, 1320)
        daten = "data:image/png;base64," + base64.b64encode(eigen).decode()
        self.assertNotEqual(post("/api/eltern/bildplatz", {"platz": "raeume/raum-2.jpg", "daten": daten}), 200)   # ohne PIN nicht
        with urllib.request.urlopen(urllib.request.Request(url + "/api/eltern/anmelden", data=json.dumps({"pin": PIN}).encode(),
                                                           headers={"Content-Type": "application/json"})) as a:
            token = json.loads(a.read())["token"]
        self.assertEqual(post("/api/eltern/bildplatz", {"platz": "raeume/raum-2.jpg", "daten": daten}, token), 200)
        typ, inhalt = hole("/bilder/raeume/raum-2.jpg")
        self.assertEqual((typ, inhalt), ("image/png", eigen), "eigenes Bild hat Vorrang (Typ aus dem Inhalt)")
        self.assertTrue(next(b for b in hub.bildplaetze() if b["platz"] == "raeume/raum-2.jpg")["eigen"])
        self.assertEqual(post("/api/eltern/bildplatz-zuruecksetzen", {"platz": "raeume/raum-2.jpg"}, token), 200)
        self.assertEqual(hole("/bilder/raeume/raum-2.jpg")[1], vorgabe)
        self.assertEqual(post("/api/eltern/bildplatz", {"platz": "raeume/raum-2.jpg", "daten": "data:image/png;base64," +
                                                        base64.b64encode(png(400, 300)).decode()}, token), 400)


if __name__ == "__main__":
    unittest.main()
