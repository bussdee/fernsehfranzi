"""4.1 Sicherung: herunterladen (ohne PIN/Token), prüfen, einspielen (eigene Sicherung vorher, Token/PIN bleiben)."""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import zipfile
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import sicherung  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


class Sicherung(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-sich-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(datetime(2026, 11, 18, 15, 0)))
        self.neustarts = []
        self.hub.prozess_neustart = lambda: self.neustarts.append(1)
        self.hub.einstellungen_aendern({"name": "Testkind", "telegram": {"aktiv": True, "token": "123:GEHEIM",
                                                                        "chats": [{"id": 1, "name": "Papa"}]}})
        os.makedirs(os.path.join(self.ordner, "zeichnungen"), exist_ok=True)
        with open(os.path.join(self.ordner, "zeichnungen", "bild-1.png"), "wb") as f:
            f.write(PNG)

    def zip_lesen(self, roh):
        z = zipfile.ZipFile(io.BytesIO(roh))
        return {n: z.read(n) for n in z.namelist()}

    def test_herunterladen_ohne_geheimes(self):
        inhalt = self.zip_lesen(self.hub.sicherung_erstellen())
        self.assertIn("zeichnungen/bild-1.png", inhalt)
        self.assertIn("zeitkonto.json", inhalt)
        self.assertNotIn("pin.json", inhalt)
        self.assertNotIn("kiosk-token", inhalt)
        einst = json.loads(inhalt["einstellungen.json"])
        self.assertEqual(einst["name"], "Testkind")
        self.assertEqual(einst["telegram"]["token"], "", "Token nie in der Sicherung")
        self.assertNotIn(b"GEHEIM", b"".join(inhalt.values()))

    def test_einspielen_mit_eigener_sicherung_und_neustart(self):
        roh = self.hub.sicherung_erstellen()
        self.hub.einstellungen_aendern({"name": "Anders"})
        os.remove(os.path.join(self.ordner, "zeichnungen", "bild-1.png"))
        meldung = self.hub.sicherung_einspielen(roh)
        self.assertIn("1 Bilder", meldung)
        for _ in range(40):
            if self.neustarts:
                break
            time.sleep(0.1)
        self.assertEqual(self.neustarts, [1], "danach startet der Server neu")
        with open(os.path.join(self.ordner, "einstellungen.json"), encoding="utf-8") as f:
            einst = json.load(f)
        self.assertEqual(einst["name"], "Testkind")
        self.assertEqual(einst["telegram"]["token"], "123:GEHEIM", "Token des Geräts bleibt")
        self.assertTrue(os.path.isfile(os.path.join(self.ordner, "zeichnungen", "bild-1.png")))
        alt = os.listdir(os.path.join(self.ordner, "sicherungen"))
        self.assertEqual(len(alt), 1)
        alt_inhalt = self.zip_lesen(open(os.path.join(self.ordner, "sicherungen", alt[0]), "rb").read())
        self.assertEqual(json.loads(alt_inhalt["einstellungen.json"])["name"], "Anders", "alter Stand gesichert")

    def test_eigene_sicherungen_hoechstens_drei(self):
        for sekunde in range(5):
            sicherung.eigene_sicherung(self.ordner, "t", "2026-11-18T15:00:0%d" % sekunde)
        self.assertEqual(len(os.listdir(os.path.join(self.ordner, "sicherungen"))), 3)

    def test_fremde_und_kaputte_dateien_abgewiesen(self):
        def zipbau(dateien):
            puffer = io.BytesIO()
            with zipfile.ZipFile(puffer, "w") as z:
                for n, inhalt in dateien.items():
                    z.writestr(n, inhalt)
            return puffer.getvalue()
        gut = {sicherung.INFO: "{}", "einstellungen.json": "{}"}
        sicherung.pruefen(zipbau(gut))
        for kaputt, text in ((b"kein zip", "keine ZIP"), (zipbau({"einstellungen.json": "{}"}), "keine Sicherung"),
                             (zipbau(dict(gut, **{"../../etc/passwd": "x"})), "Unbekannte"),
                             (zipbau(dict(gut, **{"pin.json": "{}"})), "Unbekannte"),
                             (zipbau(dict(gut, **{"zeitkonto.json": "{kaputt"})), "beschädigt"),
                             (zipbau(dict(gut, **{"zeichnungen/x.png": "kein bild"})), "kein Bild")):
            with self.assertRaisesRegex(ValueError, text):
                sicherung.pruefen(kaputt)
        self.assertEqual(self.neustarts, [])


if __name__ == "__main__":
    unittest.main()
