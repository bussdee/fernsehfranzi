"""6.1: Nachts keine Diashow, Standby nur, wenn der Wecker den Fernseher sicher wieder einschalten kann."""
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

ABEND = datetime(2026, 11, 18, 20, 30)          # Mittwoch, Nachtruhe (Vorgabe 19:30 bis 08:00)
WECKER = {"aktiv": True, "liste": [{"nr": 1, "zeit": "07:00", "tage": [0, 1, 2, 3, 4], "sonne": 10}]}


class StandbyNurMitSicheremWecker(unittest.TestCase):
    def hub(self, jetzt=ABEND):
        ordner = tempfile.mkdtemp(prefix="ff-61-")
        self.addCleanup(shutil.rmtree, ordner, True)
        return neuer_hub(ordner, Uhr(jetzt))

    def test_naechster_wecker(self):
        w = wecker.einstellungen(WECKER)
        self.assertEqual(wecker.naechster(w, ABEND), datetime(2026, 11, 19, 6, 50), "mit 10 min Sonnenaufgang")
        self.assertEqual(wecker.naechster(w, datetime(2026, 11, 20, 8, 0)), datetime(2026, 11, 23, 6, 50), "Wochenende frei")
        self.assertIsNone(wecker.naechster(wecker.einstellungen(dict(WECKER, aktiv=False)), ABEND))

    def test_ohne_wecker_geht_der_fernseher_aus(self):
        hub = self.hub()
        nr = hub.cec["nr"]
        self.assertTrue(hub.hoerbuch_schlaf_ende())
        self.assertEqual((hub.cec["nr"], hub.cec["befehl"]), (nr + 1, "standby"))
        self.assertFalse(hub.status()["nachthimmel"])

    def test_wecker_ungeprueft_nachthimmel_statt_standby(self):
        hub = self.hub()
        hub.einstellungen_aendern({"wecker": WECKER})
        nr = hub.cec["nr"]
        self.assertFalse(hub.hoerbuch_schlaf_ende())
        self.assertEqual(hub.cec["nr"], nr, "kein Standby")
        self.assertTrue(hub.status()["nachthimmel"])
        self.assertEqual(hub.cec_test_stand()["wecker_bald"], "06:50")

    def test_nach_bestandenem_test_wieder_standby(self):
        hub = self.hub()
        hub.einstellungen_aendern({"wecker": WECKER})
        hub.cec_test_starten()
        self.assertEqual(hub.cec["befehl"], "test")
        self.assertTrue(hub.cec_test_stand()["laeuft"])
        hub.cec_test_ergebnis(aus=True, an=True)
        self.assertEqual(hub.cec_test_stand()["cec_an"], True)
        self.assertTrue(hub.hoerbuch_schlaf_ende())
        self.assertEqual(hub.cec["befehl"], "standby")
        hub.cec_test_ergebnis(aus=True, an=False)          # z. B. neuer Fernseher: wieder vorsichtig
        self.assertFalse(hub.hoerbuch_schlaf_ende())

    def test_nachtruhe_aus_beachtet_den_wecker(self):
        hub = self.hub()
        hub.einstellungen_aendern({"wecker": WECKER})
        nr = hub.cec["nr"]
        hub.nacht_wahl("aus")
        self.assertEqual(hub.cec["nr"], nr)
        self.assertTrue(hub.status()["nachtruhe"])

    def test_status_meldet_die_sperrzeit(self):
        self.assertEqual(self.hub().status()["sperrzeit"], {"name": "Nacht", "nacht": True})
        self.assertIsNone(self.hub(datetime(2026, 11, 18, 15, 0)).status()["sperrzeit"])


if __name__ == "__main__":
    unittest.main()
