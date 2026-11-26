"""6.9.66: Erst-dann - Gaming-Apps erst nach Lernen oder geschaffter Mein-Tag-Liste (ab Werk aus)."""
import copy
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))
from test_62 import LISTE  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402


class ErstDann(unittest.TestCase):
    def setUp(self):
        o = tempfile.mkdtemp(prefix="ff-6966-")
        self.addCleanup(shutil.rmtree, o, True)
        self.uhr = Uhr(datetime(2026, 11, 18, 19, 5))      # Mittwoch, Abend-Liste läuft (19:00-19:45)
        self.hub = neuer_hub(o, self.uhr)
        self.app = {"id": "test-spiel", "name": "Testspiel", "typ": "spiel", "zeit": "gaming"}

    def darf(self):
        return self.hub._start_app(self.app, self.uhr(), True)

    def test_ab_werk_aus(self):
        self.assertFalse(self.hub.erst_dann()["aktiv"])
        self.assertTrue(self.darf()[0])

    def test_erst_lernen_oder_liste(self):
        self.hub.einstellungen_aendern({"meintag": copy.deepcopy(LISTE), "erst_dann": {"aktiv": True, "lernen_min": 10, "liste": True}})
        ok, grund, _ = self.darf()
        self.assertFalse(ok)
        self.assertIn("10 Minuten lernen", grund)
        self.assertIn("Mein Tag", grund)
        self.assertTrue(self.hub._start_app(dict(self.app, zeit="zaehlt"), self.uhr(), True)[0], "nur Gaming ist betroffen")
        z = self.hub.familie.zustand
        z.update(lern_datum=self.uhr().date().isoformat(), lern_s=600)
        self.assertTrue(self.darf()[0], "10 Minuten gelernt")
        z.update(lern_s=0)
        self.hub.meintag_abhaken(2, 0)                       # Abend-Liste (1 Schritt) geschafft
        self.assertTrue(self.darf()[0], "Liste geschafft")

    def test_pruefung(self):
        for falsch in ({"aktiv": "ja"}, {"lernen_min": 7}, {"liste": 1}, {"gibts": True}):
            with self.assertRaises(ValueError):
                self.hub.einstellungen_aendern({"erst_dann": falsch})


if __name__ == "__main__":
    unittest.main()
