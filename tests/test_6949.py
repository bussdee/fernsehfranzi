"""6.9.49: Abenteuer mit Postkarten (Vorderseite je Ziel, gemeinsame Rückseite, Briefmarke) und Postkarten-Album."""
import os
import sys
import unittest
from datetime import datetime, timedelta

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
from fernsehfranzi import franzi  # noqa: E402

EIN = franzi.einstellungen({"aktiv": True, "abenteuer_tage": 4})
WEB = os.path.join(REPO, "web", "bilder", "postkarten")


class Postkarten(unittest.TestCase):
    def test_bilder_da(self):
        for k, *_ in franzi.ABENTEUER:
            self.assertTrue(os.path.isfile(os.path.join(WEB, k + ".jpg")), k)
        self.assertTrue(os.path.isfile(os.path.join(WEB, "rueckseite.png")))
        for i in range(1, franzi.MARKEN + 1):
            self.assertTrue(os.path.isfile(os.path.join(WEB, "marke-%d.png" % i)))

    def test_abenteuer_bringt_postkarte_ins_album(self):
        start = datetime(2026, 11, 1, 15)
        z = franzi.neu(start)
        z["letzter_besuch"] = start.isoformat()
        tag = start + timedelta(days=6)
        z, satz = franzi.besuch(EIN, z, tag)
        karte = z["abenteuer"]["postkarte"]
        self.assertIn(karte["karte"], [a[0] for a in franzi.ABENTEUER])
        self.assertIn(karte["ort"], satz)
        self.assertEqual(z["postkarten"], [karte])
        self.assertTrue(karte["text"] and karte["gruss_aus"] and karte["datum"] == tag.date().isoformat())
        tv = franzi.fuer_tv(dict(EIN, _kind="Mia"), z, tag, 0)
        self.assertEqual((tv["kind"], tv["postkarten"][0]["karte"]), ("Mia", karte["karte"]))
        z, _ = franzi.besuch(EIN, z, tag + timedelta(minutes=1))      # Franzi kommt heim
        self.assertIsNone(z["abenteuer"])
        self.assertEqual(len(z["postkarten"]), 1, "die Karte bleibt im Album")
        z["letzter_besuch"] = tag.isoformat()
        z, _ = franzi.besuch(EIN, z, tag + timedelta(days=5))
        self.assertNotEqual(z["postkarten"][-1]["karte"], karte["karte"], "nicht zweimal hintereinander dieselbe")


if __name__ == "__main__":
    unittest.main()
