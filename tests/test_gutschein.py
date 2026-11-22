"""3.5 Gutschein-Codes: normal (+Minuten, nicht in Sperrzeiten), besonders (alles erlaubt, nichts zählt), einmalig, gegen Raten."""
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from test_v3_server import Uhr, neuer_hub  # noqa: E402

NACHMITTAG = datetime(2026, 11, 18, 15, 0)       # Mittwoch, keine Sperrzeit
ABEND = datetime(2026, 11, 18, 21, 0)            # Nachtruhe (Vorgabe ab 19:30)


class Gutscheine(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-gs-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(NACHMITTAG)
        self.hub = neuer_hub(self.ordner, self.uhr)

    def code(self, art="normal", minuten=30):
        return self.hub.gutscheine.erstellen(art, minuten, 1, self.uhr())[0]["code"]

    def test_codes_sind_sechsstellig_und_verschieden(self):
        codes = [c["code"] for c in self.hub.gutscheine.erstellen("normal", 15, 20, self.uhr())]
        self.assertEqual(len(set(codes)), 20)
        self.assertTrue(all(len(c) == 6 and c.isdigit() for c in codes))
        with self.assertRaises(ValueError):
            self.hub.gutscheine.erstellen("gold", 15, 1, self.uhr())
        with self.assertRaises(ValueError):
            self.hub.gutscheine.erstellen("normal", 1000, 1, self.uhr())

    def test_normal_gibt_minuten_und_gilt_einmal(self):
        code = self.code(minuten=30)
        ok, text = self.hub.gutschein_einloesen(code)
        self.assertTrue(ok)
        self.assertIn("30 Minuten", text)
        self.assertEqual(self.hub.status()["rest_min"], 90 + 30)
        self.assertEqual(self.hub.gutschein_einloesen(code), (False, "Dieser Gutschein wurde schon eingelöst."))
        self.assertTrue(self.hub.eltern_daten()["gutscheine"][0]["eingeloest"])

    def test_normal_nicht_in_der_sperrzeit(self):
        code = self.code()
        self.uhr.jetzt = ABEND
        ok, text = self.hub.gutschein_einloesen(code)
        self.assertFalse(ok)
        self.assertIn("keine Pause", text)
        self.assertFalse(self.hub.eltern_daten()["gutscheine"][0]["eingeloest"], "bleibt gültig")

    def test_besonders_hebt_sperren_auf_und_zaehlt_nicht(self):
        self.uhr.jetzt = ABEND
        self.assertFalse(self.hub.starte("spiel-snake")[0])
        ok, _ = self.hub.gutschein_einloesen(self.code("besonders", 20))
        self.assertTrue(ok)
        self.assertTrue(self.hub.starte("spiel-snake")[0])
        for _ in range(10 * 12):                     # 10 Minuten spielen
            self.uhr.weiter(5)
            self.hub.eingabe(["ENTER"])
            self.hub.tick(5)
        self.assertEqual(self.hub.status()["rest_min"], 90, "nichts gezählt")
        self.assertEqual(self.hub.aktuell, "spiel-snake")
        for _ in range(11 * 12):                     # Gutschein läuft ab -> Spiel ist gesperrt
            self.uhr.weiter(5)
            self.hub.eingabe(["ENTER"])
            self.hub.tick(5)
        self.assertIsNone(self.hub.aktuell)
        self.assertFalse(self.hub.starte("spiel-snake")[0])

    def test_raten_wird_gebremst(self):
        echt = self.code()
        for _ in range(5):
            self.assertFalse(self.hub.gutschein_einloesen("111112")[0])
        ok, text = self.hub.gutschein_einloesen(echt)
        self.assertFalse(ok)
        self.assertIn("Zu viele", text)
        self.uhr.weiter(11 * 60)
        self.assertTrue(self.hub.gutschein_einloesen(echt)[0])

    def test_gutschein_kachel_geht_immer(self):
        self.uhr.jetzt = ABEND
        kachel = next(k for k in self.hub.kacheln() if k["id"] == "spiel-gutschein")
        self.assertTrue(kachel["frei"])


if __name__ == "__main__":
    unittest.main()
