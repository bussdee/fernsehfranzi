"""6.9.41: Archiv-Ordner für Filme und Musik - Einträge einzeln freigeben, Filme als Belohnung."""
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))
from fernsehfranzi import archiv  # noqa: E402
from test_hoerbuch import starte_attrappe  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

NACHMITTAG = datetime(2026, 11, 25, 16, 0)
NACHT = datetime(2026, 11, 25, 23, 30)


class Modul(unittest.TestCase):
    def test_pruefe(self):
        ok = lambda link: None                                         # noqa: E731
        archiv.pruefe({"video": {"ordner": "http://s:8080/share/AbCd", "freigaben": {"Film": {"frei": True}}}}, ok)
        for falsch in ({"bilder": {}}, {"video": {"freigaben": {"a/b": {}}}}, {"video": {"freigaben": {"A": {"quatsch": True}}}},
                       {"musik": {"freigaben": {"Lied": {"frei": True}}}}, {"video": {"freigaben": {"..": {}}}}):
            with self.assertRaises(ValueError, msg=falsch):
                archiv.pruefe(falsch, ok)
        with self.assertRaises(ValueError):
            archiv.pruefe({"video": {"ordner": "kaputt"}}, lambda link: "muss ein Freigabelink sein")

    def test_belohnung(self):
        app = {"id": "archiv-video", "zeit": "zaehlt", "limit_min": {"schultag": 30}, "sperr_erlaubt": []}
        self.assertEqual(archiv.als_belohnung(app, {"frei": True})["zeit"], "frei")
        self.assertNotIn("limit_min", archiv.als_belohnung(app, {"frei": True}))
        self.assertEqual(archiv.als_belohnung(app, {"sperre": True})["sperr_erlaubt"], "alle")
        self.assertEqual(archiv.oberster("Film A/CD1/x.mp4"), "Film A")


class Hub(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.link = starte_attrappe()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-6941-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(NACHMITTAG)
        self.hub = neuer_hub(self.ordner, self.uhr)

    def kachel(self, app_id):
        return next((k for k in self.hub.kacheln() if k["id"] == app_id), None)

    def test_ab_werk_keine_kachel_und_freigabe(self):
        self.assertIsNone(self.kachel("archiv-musik"))
        self.hub.einstellungen_aendern({"archiv": {"musik": {"ordner": self.link, "freigaben": {}}}})
        self.assertIsNone(self.kachel("archiv-musik"))                      # ohne Freigabe keine Kachel
        inhalt = self.hub.archiv_inhalt("musik")
        self.assertEqual([e["name"] for e in inhalt["eintraege"]], ["Bibi Blocksberg", "Die drei ??? Kids", "Einzeln.wav"])
        self.hub.einstellungen_aendern({"archiv": {"musik": {"ordner": self.link, "freigaben": {"Bibi Blocksberg": {}}}}})
        k = self.kachel("archiv-musik")
        self.assertTrue(k and k["frei"] and k["typ"] == "hoerbuch")
        oben = self.hub.hoerbuch_liste("archiv-musik", "")
        self.assertEqual([x["name"] for x in oben["ordner"]], ["Bibi Blocksberg"])
        self.assertEqual(oben["titel"], [])
        self.assertEqual(len(self.hub.hoerbuch_liste("archiv-musik", "Bibi Blocksberg")["titel"]), 3)
        with self.assertRaises(ValueError):
            self.hub.hoerbuch_liste("archiv-musik", "Die drei ??? Kids")    # nicht freigegeben
        with self.assertRaises(ValueError):
            self.hub.hoerbuch_datei("archiv-musik", "Einzeln.wav")
        self.assertTrue(self.hub.hoerbuch_datei("archiv-musik", "Bibi Blocksberg/Folge 1.wav"))
        self.assertTrue(self.hub.starte("archiv-musik")[0])

    def test_belohnungsfilm_in_sperrzeit(self):
        self.hub.einstellungen_aendern({"archiv": {"video": {"ordner": self.link, "freigaben": {
            "Bibi Blocksberg": {"frei": False, "sperre": True}, "Die drei ??? Kids": {"frei": False, "sperre": False}}}}})
        self.uhr.jetzt = NACHT
        ok, grund, _ = self.hub.konto.darf_starten(self.hub.app("archiv-video"), NACHT)
        self.assertFalse(ok, "nachts ist Sperrzeit")
        k = self.kachel("archiv-video")
        self.assertTrue(k["frei"], "die Kachel geht, weil ein Belohnungs-Film erlaubt ist")
        oben = self.hub.hoerbuch_liste("archiv-video", "")
        self.assertEqual([x["name"] for x in oben["ordner"]], ["Bibi Blocksberg"])   # nur der Belohnungs-Film

    def test_belohnungsfilm_ohne_zeitlimit_im_takt(self):
        self.hub.einstellungen_aendern({"archiv": {"video": {"ordner": self.link, "freigaben": {"Bibi Blocksberg": {"frei": True, "sperre": False}}}}})
        self.assertTrue(self.hub.starte("archiv-video")[0])
        self.hub.hoerbuch_stand("archiv-video", "Bibi Blocksberg", "Bibi Blocksberg/Folge 1.wav", 10, spielt=True)
        vorher = self.hub.konto._tag(NACHMITTAG)["genutzt_s"]
        for _ in range(5):
            self.hub.tick()
        self.assertEqual(self.hub.konto._tag(NACHMITTAG)["genutzt_s"], vorher, "Belohnung zählt nicht zur Zeit")


if __name__ == "__main__":
    unittest.main()
