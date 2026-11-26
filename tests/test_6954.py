"""6.9.54: Gegenstände frei im Raum platzieren (zuletzt gestellt liegt vorne - Teddy aufs Bett)."""
import os
import sys
import unittest
from datetime import datetime

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
from fernsehfranzi import franzi  # noqa: E402

TAG = datetime(2026, 11, 28, 15)
EIN = franzi.einstellungen({"aktiv": True})


class Platzieren(unittest.TestCase):
    def test_setzen_reihenfolge_grenzen(self):
        z, _ = franzi.besuch(EIN, {}, TAG)
        self.assertEqual(z["zimmer"]["raum-zimmer"]["moebel-bett"], [16, 17, 1])      # Start: Bett und Ball stehen
        with self.assertRaises(ValueError):
            franzi.setzen(z, TAG, "spielzeug-teddy", 20, 20)                         # noch nicht gekauft
        z["besitz"].append("spielzeug-teddy")
        z = franzi.setzen(z, TAG, "spielzeug-teddy", 18, 22)
        r = z["zimmer"]["raum-zimmer"]
        self.assertGreater(r["spielzeug-teddy"][2], r["moebel-bett"][2], "zuletzt gestellt = vorne (auf dem Bett)")
        z = franzi.setzen(z, TAG, "spielzeug-teddy", 500, -9)
        self.assertEqual(r["spielzeug-teddy"][:2], [franzi.LAGE_X[1], franzi.LAGE_Y[0]])
        with self.assertRaises(ValueError):
            franzi.setzen(z, TAG, "kleid-krone", 10, 10)                             # Kleidung steht nicht im Raum
        with self.assertRaises(ValueError):
            franzi.setzen(z, TAG, "spielzeug-teddy", "links", 10)
        z = franzi.wegraeumen(z, TAG, "spielzeug-teddy")
        self.assertNotIn("spielzeug-teddy", z["zimmer"]["raum-zimmer"])

    def test_nur_in_passenden_raeumen(self):
        z, _ = franzi.besuch(EIN, {}, TAG)
        alt = dict(franzi.NUR_IN)
        try:
            franzi.NUR_IN["spielzeug-teddy"] = ("raum-garten",)
            z["besitz"].append("spielzeug-teddy")
            with self.assertRaises(ValueError):
                franzi.setzen(z, TAG, "spielzeug-teddy", 20, 10)
        finally:
            franzi.NUR_IN.clear(); franzi.NUR_IN.update(alt)


if __name__ == "__main__":
    unittest.main()
