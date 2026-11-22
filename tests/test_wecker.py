"""3.5 Wecker: Grenzen der Eltern, klingelt einmal, Fernseher an, Lautstärke, schlummern, aus."""
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import wecker  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

MONTAG_FRUEH = datetime(2026, 11, 23, 6, 55)


class Wecker(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-wecker-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(MONTAG_FRUEH)
        self.hub = neuer_hub(self.ordner, self.uhr)
        self.hub.wecker_liste_setzen([{"nr": 1, "zeit": "07:00", "tage": [0, 1, 2, 3, 4], "ton": "", "laut": 50, "an": True}])

    def laufe(self, minuten):
        for _ in range(int(minuten * 12)):
            self.uhr.weiter(5)
            self.hub.tick(5)

    def test_grenzen_der_eltern(self):
        with self.assertRaisesRegex(ValueError, "frühestens 06:00"):
            self.hub.wecker_liste_setzen([{"nr": 1, "zeit": "05:30", "tage": [0], "an": True}])
        with self.assertRaises(ValueError):
            self.hub.wecker_liste_setzen([{"nr": n, "zeit": "07:00", "tage": [0]} for n in range(1, 7)])
        with self.assertRaises(ValueError):
            self.hub.wecker_liste_setzen([{"nr": 1, "zeit": "07:00", "tage": [0], "ton": "../geheim.mp3"}])
        w = self.hub.wecker()
        w["max_laut"] = 30
        self.hub.einstellungen_aendern({"wecker": w})
        self.assertEqual(wecker.lautstaerke(self.hub.wecker(), self.hub.wecker()["liste"][0]), 30)

    def test_klingelt_einmal_mit_fernseher_an_und_lautstaerke(self):
        self.hub.nachtruhe = True                                  # Gute Nacht hatte den Fernseher aus gemacht
        self.laufe(6)
        self.assertEqual(self.hub.cec["befehl"], "an")
        self.assertIn(("lautstaerke_setzen", 50), self.hub.system.aufrufe)
        self.assertIn("wecker", [a["art"] for a in self.hub.auftraege])
        self.assertEqual(self.hub.status()["wecker"]["zeit"], "07:00")
        self.assertFalse(self.hub.still(), "morgens wieder Töne")
        self.hub.wecker_aktion("aus")
        self.assertIsNone(self.hub.status()["wecker"])
        self.assertEqual(self.hub.system.lautstaerke_wert, 40, "vorherige Lautstärke zurück")
        self.laufe(5)
        self.assertIsNone(self.hub.status()["wecker"], "nur einmal am Tag")

    def test_sonnenaufgang_vorher(self):
        self.hub.wecker_liste_setzen([{"nr": 1, "zeit": "07:00", "tage": [0, 1, 2, 3, 4], "ton": "", "laut": 50, "an": True,
                                       "sonne": 10}])
        self.hub.nachtruhe = True
        self.uhr.jetzt = datetime(2026, 11, 23, 6, 49)
        self.laufe(2)
        sonne = [a for a in self.hub.auftraege if a["art"] == "sonne"]
        self.assertEqual(len(sonne), 1)
        self.assertEqual(sonne[0]["minuten"], 10)
        self.assertEqual(self.hub.cec["befehl"], "an")
        self.assertFalse(self.hub.still())
        self.assertIsNone(self.hub.status()["wecker"], "geklingelt wird erst um 7")
        with self.assertRaises(ValueError):
            self.hub.wecker_liste_setzen([{"nr": 1, "zeit": "07:00", "tage": [0], "sonne": 7}])

    def test_schlummern(self):
        self.laufe(6)
        self.hub.wecker_aktion("schlummern")
        self.assertIsNone(self.hub.status()["wecker"])
        self.laufe(4)
        self.assertIsNone(self.hub.status()["wecker"])
        self.laufe(1.5)
        self.assertIsNotNone(self.hub.status()["wecker"], "nach 5 Minuten wieder")

    def test_nicht_am_wochenende_und_nicht_wenn_aus(self):
        self.uhr.jetzt = datetime(2026, 11, 28, 6, 55)              # Samstag
        self.laufe(6)
        self.assertIsNone(self.hub.status()["wecker"])
        w = self.hub.wecker()
        w["aktiv"] = False
        self.hub.einstellungen_aendern({"wecker": w})
        self.uhr.jetzt = datetime(2026, 11, 30, 6, 55)              # Montag, aber Eltern haben ausgeschaltet
        self.laufe(6)
        self.assertIsNone(self.hub.status()["wecker"])


if __name__ == "__main__":
    unittest.main()
