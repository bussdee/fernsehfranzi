"""6.9.61: Franzi spricht - Sätze aus der Lage, Arten im Elternbereich, eigene Texte, Witze-Kachel."""
import os
import random
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))
from fernsehfranzi import franzi, sprueche  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

ABEND = datetime(2026, 11, 26, 18, 0)


def texte(einst, lage, jetzt=ABEND):
    return [t for _, t, _ in sprueche.kandidaten(einst, jetzt, lage)]


class Modul(unittest.TestCase):
    def test_lage(self):
        t = texte({}, {"routine": {"name": "Abend", "offen": 2}, "wetter": "regen"})
        self.assertTrue(any("Abend" in x and "2 Sachen" in x for x in t))
        self.assertTrue(any("regnet" in x or "Regen" in x for x in t))
        self.assertFalse(any(x in t for x in sprueche.WITZE), "Witze nur, wenn eingeschaltet")
        t = texte({}, {"nicht_geschafft": "Morgen"})
        self.assertTrue(any("morgen schaffen" in x or "neuer Tag" in x for x in t))
        self.assertFalse(any("vergessen" in x for x in t), "nie beschämend")

    def test_arten_und_eigene(self):
        einst = {"witze": True, "schule": True, "eigene": [{"text": "Trink mal was!", "anlass": "abends"},
                                                          {"text": "Nur morgens", "anlass": "morgens"}, {"text": "  ", "anlass": "immer"}]}
        sprueche.pruefe(einst)
        t = texte(einst, {"schule_morgen": True, "kleid": "Krone"})
        self.assertTrue(set(sprueche.WITZE) <= set(t))
        self.assertIn("Trink mal was!", t)
        self.assertNotIn("Nur morgens", t)
        self.assertTrue(any("Krone" in x for x in t))
        with self.assertRaises(ValueError):
            sprueche.pruefe({"witze": "ja"})
        with self.assertRaises(ValueError):
            sprueche.pruefe({"eigene": [{"text": "x", "anlass": "nie"}]})
        w = sprueche.waehle(einst, ABEND, {}, random.Random(1))
        self.assertTrue(w["text"] and w["gesicht"])


class ImHub(unittest.TestCase):
    def test_spruch_im_stand_und_witze_kachel(self):
        o = tempfile.mkdtemp(prefix="ff-6961-")
        self.addCleanup(shutil.rmtree, o, True)
        hub = neuer_hub(o, Uhr(ABEND))
        hub.einstellungen_aendern({"franzi": {"aktiv": True}})
        st = hub.franzi_stand(besuch=True)
        self.assertTrue(st["spruch"]["text"])
        ids = [k["id"] for k in hub.kacheln()]
        hub.einstellungen_aendern({"franzi": {"aktiv": True, "sprueche": {"witze": True}}})
        ids2 = [k["id"] for k in hub.kacheln()]
        if "spiel-witz" in ids:
            self.assertNotIn("spiel-witz", ids2)
        franzi.pruefe({"aktiv": True, "sprueche": {"witze": True}})


if __name__ == "__main__":
    unittest.main()
