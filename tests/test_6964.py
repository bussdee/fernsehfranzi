"""6.9.64: Franzi versteckt sich im Labyrinth - Bonusstern höchstens einmal am Tag."""
import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))
from fernsehfranzi import meintag  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402


class Versteck(unittest.TestCase):
    def test_einmal_am_tag(self):
        o = tempfile.mkdtemp(prefix="ff-6964-")
        self.addCleanup(shutil.rmtree, o, True)
        uhr = Uhr(datetime(2026, 11, 26, 15))
        hub = neuer_hub(o, uhr)
        self.assertEqual(hub.franzi_versteck_gefunden(), {"stern": False}, "ohne Franzi kein Versteck")
        hub.einstellungen_aendern({"franzi": {"aktiv": True}})
        hub.franzi_stand(besuch=True)
        self.assertEqual(hub.franzi_versteck_moeglich(), {"aktiv": True, "stern": True})
        self.assertEqual(hub.franzi_versteck_gefunden(), {"stern": True})
        self.assertEqual(meintag.zustand_fuer(hub.meintag_zustand, uhr().date())["sterne"], 1)
        self.assertEqual(hub.franzi_versteck_gefunden(), {"stern": False})
        self.assertFalse(hub.franzi_versteck_moeglich()["stern"])
        uhr.weiter(24 * 3600)
        self.assertTrue(hub.franzi_versteck_moeglich()["stern"], "am nächsten Tag wieder")

    def test_labyrinth_kennt_franzi(self):
        js = open(os.path.join(REPO, "web/js/spiele/labyrinth.js"), encoding="utf-8").read()
        self.assertIn("/api/franzi/versteck", js)
        self.assertTrue(re.search(r"filter\(\(\[dx, dy\]\) => k\[y \+ dy\]\[x \+ dx\] === 0\)\.length === 1", js), "Sackgasse")
        self.assertTrue(os.path.exists(os.path.join(REPO, "web/bilder/franzi/versteck.png")))


if __name__ == "__main__":
    unittest.main()
