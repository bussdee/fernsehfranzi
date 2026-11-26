"""6.9.45: Franzi hat auch mal genug - genervt, geweckt, „mir geht's doch gut“; freundlich und ohne Strafe."""
import os
import sys
import unittest
from datetime import datetime, timedelta

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
from fernsehfranzi import franzi  # noqa: E402

TAG = datetime(2026, 11, 25, 15, 0)
EIN = franzi.einstellungen({"aktiv": True})


def neu(**werte):
    z = franzi.neu(TAG - timedelta(days=1))
    z["letzter_besuch"] = TAG.isoformat()
    z["stand"] = TAG.isoformat()
    for k in franzi.WERTE:
        z["werte"][k] = werte.get(k, 50.0)
    return z


class Genervt(unittest.TestCase):
    def test_zu_oft_dasselbe(self):
        z = neu()
        for i in range(3):
            z = franzi.pflegen(EIN, z, TAG + timedelta(seconds=i * 5), "streicheln")
            self.assertIsNone(z.get("reaktion"))
        z = franzi.pflegen(EIN, z, TAG + timedelta(seconds=20), "streicheln")
        self.assertEqual(z["reaktion"]["gesicht"], "schwindelig")         # 4.: Hinweis
        z = franzi.pflegen(EIN, z, TAG + timedelta(seconds=25), "streicheln")
        glueck = z["werte"]["glueck"]
        z = franzi.pflegen(EIN, z, TAG + timedelta(seconds=30), "streicheln")
        self.assertEqual(z["reaktion"]["gesicht"], "genervt")             # 6.: genervt
        self.assertAlmostEqual(z["werte"]["glueck"], glueck, delta=0.5, msg="genervt: es passiert nichts (keine Strafe, kein Plus)")
        self.assertEqual(franzi.stimmung(z, TAG + timedelta(minutes=1)), "genervt")
        z = franzi.pflegen(EIN, z, TAG + timedelta(minutes=1), "fuettern")
        self.assertEqual(z["reaktion"]["gesicht"], "genervt")             # noch in Ruhe
        self.assertNotEqual(franzi.stimmung(z, TAG + timedelta(minutes=4)), "genervt")   # nach 3 min vorbei

    def test_unnoetig_dreimal(self):
        z = neu(sauber=100.0)
        z = franzi.pflegen(EIN, z, TAG, "waschen")
        self.assertIn("sauber", z["reaktion"]["text"])
        self.assertEqual(z["reaktion"]["gesicht"], "grummelig")
        z = franzi.pflegen(EIN, z, TAG + timedelta(seconds=70), "waschen")
        z = franzi.pflegen(EIN, z, TAG + timedelta(seconds=140), "waschen")
        self.assertEqual(z["reaktion"]["gesicht"], "genervt")

    def test_alle_werte_voll(self):
        z = neu(hunger=100.0, sauber=100.0, energie=100.0, glueck=100.0)
        z = franzi.pflegen(EIN, z, TAG, "streicheln")
        self.assertIsNotNone(z.get("reaktion"))

    def test_geweckt(self):
        z = neu(energie=40.0)
        z = franzi.pflegen(EIN, z, TAG, "schlafen")
        z = franzi.pflegen(EIN, z, TAG + timedelta(minutes=5), "ball" if "spielzeug-ball" in z["besitz"] else "streicheln")
        self.assertEqual(z["reaktion"]["gesicht"], "grummelig")
        self.assertEqual(franzi.stimmung(z, TAG + timedelta(minutes=6)), "grummelig")
        nacht = neu()
        nacht = franzi.pflegen(EIN, nacht, datetime(2026, 11, 25, 22, 30), "streicheln")
        self.assertEqual(nacht["reaktion"]["gesicht"], "grummelig")

    def test_normal_keine_reaktion(self):
        z = franzi.pflegen(EIN, neu(), TAG, "fuettern")
        self.assertIsNone(z.get("reaktion"))


if __name__ == "__main__":
    unittest.main()
