"""5.1: Auszeit - alles gesperrt, am Fernseher nur ein Countdown, danach von selbst wieder frei."""
import os
import shutil
import sys
import tempfile
import unittest
from datetime import timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from test_v3_server import MITTWOCH, Uhr, neuer_hub  # noqa: E402


class Auszeit(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-51-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(MITTWOCH)
        self.hub = neuer_hub(self.ordner, self.uhr)

    def test_sperrt_zaehlt_runter_und_gibt_frei(self):
        a = self.hub.auszeit(10)
        self.assertEqual((a["bis"], a["rest_s"]), ("15:10", 600))
        self.assertFalse(self.hub.starte("spiel-snake")[0], "während der Auszeit geht nichts")
        self.assertTrue(all(not k["frei"] for k in self.hub.kacheln()))
        g = self.hub.status()["gesperrt"]
        self.assertTrue(g["auszeit"])
        self.assertEqual((g["rest_s"], g["bis_uhr"]), (600, "15:10"))
        self.uhr.weiter(4 * 60)
        self.hub.tick()
        self.assertEqual(self.hub.status()["gesperrt"]["rest_s"], 360)
        self.uhr.weiter(6 * 60)
        self.hub.tick()
        self.assertIsNone(self.hub.status()["gesperrt"], "nach dem Countdown wieder frei")
        self.assertIn("Auszeit ist vorbei", self.hub.meldung["text"])
        self.assertTrue(self.hub.starte("spiel-snake")[0])

    def test_verlaengern_und_frueher_beenden(self):
        self.hub.auszeit(10)
        self.uhr.weiter(120)
        self.assertEqual(self.hub.auszeit(5)["bis"], "15:15", "kommt zum bisherigen Ende dazu")
        self.hub.entsperren()
        self.assertIsNone(self.hub.status()["gesperrt"])

    def test_ueberlebt_neustart(self):
        self.hub.auszeit(30)
        neu = neuer_hub(self.ordner, self.uhr)
        self.assertEqual(neu.status()["gesperrt"]["rest_s"], 1800)
        self.uhr.jetzt += timedelta(minutes=31)
        neu.tick()
        self.assertIsNone(neu.status()["gesperrt"])

    def test_feste_sperre_bleibt_fest(self):
        self.hub.sperren("Pause!")
        self.uhr.weiter(24 * 3600)
        self.hub.tick()
        self.assertEqual(self.hub.status()["gesperrt"]["text"], "Pause!", "ohne Auszeit kein Ende")

    def test_pruefen(self):
        for falsch in (0, 241, "15", True, None, 2.5):
            with self.assertRaises(ValueError, msg=falsch):
                self.hub.auszeit(falsch)

    def test_telegram(self):
        antworten = []
        self.hub.telegram.antwort = lambda c, text: antworten.append(text)
        befehl = getattr(self.hub.telegram, "befehl", None) or getattr(self.hub.telegram, "_befehl", None)
        if befehl is None:
            self.skipTest("Befehls-Funktion nicht gefunden")
        befehl({"id": 1, "eltern": True, "name": "Papa"}, "/auszeit 20")
        self.assertIn("Auszeit bis 15:20", antworten[-1])
        befehl({"id": 1, "eltern": True, "name": "Papa"}, "/auszeit viel")
        self.assertIn("So geht's", antworten[-1])


if __name__ == "__main__":
    unittest.main()
