"""6.9.51: Fortschritt je Film/Folge (gesehen ✓, Weiterschauen), Belohnungs-Zeichen in der Liste."""
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))
from test_hoerbuch import starte_attrappe  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402


class Fortschritt(unittest.TestCase):
    def test_fortschritt_und_gesehen(self):
        att, link = starte_attrappe()
        self.addCleanup(att.shutdown)
        ordner = tempfile.mkdtemp(prefix="ff-6951-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(datetime(2026, 11, 25, 16)))
        hub.einstellungen_aendern({"archiv": {"musik": {"ordner": link, "freigaben": {"Bibi Blocksberg": {}}},
                                              "video": {"ordner": link, "freigaben": {"Bibi Blocksberg": {"frei": True, "sperre": False}}}}})
        hub.hoerbuch_stand("archiv-video", "Bibi Blocksberg", "Bibi Blocksberg/Folge 1.wav", 300, dauer=600)
        d = hub.hoerbuch_liste("archiv-video", "")
        self.assertEqual(d["fortschritt"]["Bibi Blocksberg/Folge 1.wav"]["sekunde"], 300)
        self.assertEqual(d["belohnung"], {"Bibi Blocksberg": {"frei": True, "sperre": False}})
        self.assertEqual(d["stand"]["titel"], "Bibi Blocksberg/Folge 1.wav")
        hub.hoerbuch_stand("archiv-video", "Bibi Blocksberg", "Bibi Blocksberg/Folge 1.wav", 600, dauer=600, fertig=True)
        d = hub.hoerbuch_liste("archiv-video", "")
        self.assertTrue(d["fortschritt"]["Bibi Blocksberg/Folge 1.wav"]["gesehen"])
        self.assertIsNone(d["stand"], "fertig geschaut: kein Weiterschauen")
        self.assertEqual(hub.hoerbuch_liste("archiv-musik", "")["belohnung"], {}, "Musik hat keine Belohnungen")


if __name__ == "__main__":
    unittest.main()
