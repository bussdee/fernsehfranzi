"""6.9.59: Werte sinken schneller und durch Fernsehzeit, Mikrofon/Gitarre starten Spiele, Lob im Status."""
import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
from fernsehfranzi import franzi, meintag  # noqa: E402

MITTAG = datetime(2026, 11, 26, 12, 0)


class Werte(unittest.TestCase):
    def test_tag_leert_franzi(self):
        z = franzi.neu(MITTAG)
        for w in franzi.WERTE:
            z["werte"][w] = 100.0
        z = franzi.altern(z, MITTAG + timedelta(hours=8))         # 12-20 Uhr wach
        self.assertLess(max(z["werte"].values()), 65)

    def test_fernsehzeit_kostet(self):
        z = franzi.neu(MITTAG)
        vorher = dict(z["werte"])
        z = franzi.fernsehzeit(z, MITTAG, 60)
        self.assertLess(z["werte"]["energie"], vorher["energie"] - 4)
        self.assertLess(z["werte"]["hunger"], vorher["hunger"] - 2)

    def test_mikrofon_startet_stimmspiel(self):
        z = franzi.neu(MITTAG)
        with self.assertRaises(ValueError):
            franzi.gespielt(z, MITTAG, "spiel-stimme", 5)
        z["besitz"].append("moebel-mikrofon")
        z = franzi.gespielt(z, MITTAG, "spiel-stimme", 5)
        z["besitz"].append("spielzeug-gitarre")
        franzi.gespielt(z, MITTAG, "spiel-bass", 0)

    def test_gegenstand_im_raum_hilft(self):
        """6.9.60: Obstkorb im Raum - Füttern macht satter."""
        ein = franzi.einstellungen({"aktiv": True})
        ohne = franzi.neu(MITTAG); ohne["werte"]["hunger"] = 20.0
        mit = franzi.neu(MITTAG); mit["werte"]["hunger"] = 20.0
        mit["zimmer"]["raum-zimmer"]["moebel-obstkorb"] = [50, 5, 3]
        a = franzi.pflegen(ein, ohne, MITTAG, "fuettern")["werte"]["hunger"]
        b = franzi.pflegen(ein, mit, MITTAG, "fuettern")["werte"]["hunger"]
        self.assertAlmostEqual(b - a, 8, places=3)

    def test_trommel_startet_echo(self):
        z = franzi.neu(MITTAG)
        z["besitz"].append("spielzeug-trommel")
        franzi.gespielt(z, MITTAG, "spiel-simon", 3)

    def test_stern_merkt_zeit(self):
        z = meintag.zustand_fuer({}, MITTAG.date())
        meintag.sterne_geben(z, MITTAG, 1)
        self.assertEqual(z["letzter_stern"], MITTAG.isoformat(timespec="seconds"))


if __name__ == "__main__":
    unittest.main()
