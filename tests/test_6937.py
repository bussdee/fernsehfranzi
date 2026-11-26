"""6.9.37: Franzis Level schalten nur bei Level 2-4 Gegenstände frei, danach je Level einen Raum; alles andere im Shop."""
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))
from fernsehfranzi import franzi, meintag  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

MITTAG = datetime(2026, 11, 25, 16, 0)
EIN = franzi.einstellungen({"aktiv": True})


class Modul(unittest.TestCase):
    def test_belohnungen_nur_raeume_und_gold(self):
        """6.9.59: Level bringen nur Räume (2-7) und die goldene Franzi, die bei 10 und 20 wächst."""
        self.assertEqual(franzi.LEVEL_BELOHNUNG, [(2, "raum-hell"), (3, "raum-probe"), (4, "raum-garten"), (5, "raum-kueche"),
                                                  (6, "raum-spiel"), (7, "raum-bad"), (10, "kleid-gold"),
                                                  (10, "franzi-wachsen-1"), (20, "franzi-wachsen-2")])

    def test_level_belohnen_einmal(self):
        z = franzi.neu(MITTAG)
        z, neu = franzi.level_belohnen(z, MITTAG, 1)
        self.assertEqual(neu, [])
        z, neu = franzi.level_belohnen(z, MITTAG, 2)
        self.assertEqual(neu, ["Sonnenzimmer"])
        self.assertIn("Level 2", z["tagebuch"][-1]["text"])
        z, neu = franzi.level_belohnen(z, MITTAG, 2)
        self.assertEqual(neu, [])                                    # nichts doppelt
        z["besitz"].append("raum-kueche")                           # z. B. geschenkt
        z, neu = franzi.level_belohnen(z, MITTAG, 10)
        self.assertEqual(neu, ["Proberaum", "Garten", "Spielzimmer", "Badezimmer", "Goldene Franzi", "Franzi wächst"])
        self.assertIn("franzi-wachsen-1", z["angezogen"])            # Wachsen gilt sofort
        z, neu = franzi.level_belohnen(z, MITTAG, 20)
        self.assertEqual(neu, ["Franzi wächst weiter"])
        self.assertEqual([x for x in z["angezogen"] if x.startswith("franzi-wachsen")], ["franzi-wachsen-2"])

    def test_level_dinge_nicht_kaeuflich(self):
        z = franzi.neu(MITTAG)
        for _, item in franzi.LEVEL_BELOHNUNG:
            with self.assertRaises(ValueError):
                franzi.kaufen(EIN, z, 999, MITTAG, item)
        for item in ("kleid-krone", "kleid-muetze", "kleid-blau"):    # alles andere (auch Mütze, Blau) gibt es im Shop
            z, p = franzi.kaufen(EIN, z, 999, MITTAG, item)
            self.assertIn(item, z["besitz"])
        tv = franzi.fuer_tv(EIN, z, MITTAG, 0)
        self.assertEqual(next(k for k in tv["katalog"] if k["id"] == "raum-garten")["level"], 4)
        self.assertIsNone(next(k for k in tv["katalog"] if k["id"] == "kleid-krone")["level"])

    def test_mein_tag_sachen_nur_bis_level_4(self):
        self.assertEqual(sorted(lv for lv, *_ in meintag.SACHEN), [2, 3, 4])
        z = meintag.zustand_fuer({}, MITTAG.date())
        meintag.sterne_geben(z, MITTAG, 200)
        with self.assertRaises(ValueError):
            meintag.franzi_setzen(z, "hut", "krone")                 # Krone gibt es nur noch im Shop


class Sammeltage(unittest.TestCase):
    """6.9.44: Raum 3 dauert 1-2 Wochen - viele Sterne an einem Tag reichen nicht."""
    def test_viele_sterne_an_einem_tag_kein_raum(self):
        z = franzi.neu(MITTAG)
        z, neu = franzi.level_belohnen(z, MITTAG, 9, sammeltage=1)
        self.assertNotIn("raum-hell", z["besitz"])
        z, neu = franzi.level_belohnen(z, MITTAG, 9, sammeltage=4)
        self.assertEqual(neu, ["Sonnenzimmer"])
        z, neu = franzi.level_belohnen(z, MITTAG, 9, sammeltage=10)
        self.assertEqual(neu, ["Proberaum"])
        self.assertGreaterEqual(franzi.MIN_TAGE["raum-probe"], 7)   # Raum 3: mindestens eine Woche

    def test_sammeltage_zaehlen_tage_nicht_sterne(self):
        from datetime import timedelta
        z = meintag.zustand_fuer({}, MITTAG.date())
        self.assertEqual(z["sammeltage"], 0)
        meintag.sterne_geben(z, MITTAG, 5)
        meintag.sterne_geben(z, MITTAG, 5)
        self.assertEqual(z["sammeltage"], 1)
        meintag.sterne_geben(z, MITTAG + timedelta(days=1), 1)
        self.assertEqual(z["sammeltage"], 2)
        z2 = meintag.zustand_fuer(z, (MITTAG + timedelta(days=3)).date())   # neuer Tag: bleibt erhalten
        self.assertEqual(z2["sammeltage"], 2)
        alt = meintag.zustand_fuer({"sterne_tage": {"2026-11-20": 2, "2026-11-21": 0, "2026-11-22": 1}}, MITTAG.date())
        self.assertEqual(alt["sammeltage"], 2)                       # Altdaten: aus der Tagesliste


class Hub(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-6937-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(MITTAG))
        self.hub.einstellungen["meintag"] = {"aktiv": True}

    def verdienen(self, n, tage_zurueck=0):
        from datetime import timedelta
        z = meintag.zustand_fuer(self.hub.meintag_zustand, MITTAG.date())
        meintag.sterne_geben(z, MITTAG - timedelta(days=tage_zurueck), n)
        self.hub.meintag_zustand = z

    def test_franzi_bekommt_raum_mit_level(self):
        self.hub.einstellungen["franzi"] = {"aktiv": True}
        self.hub.franzi_stand(besuch=True)
        for tag in range(4):                                         # 6.9.44: Räume brauchen auch Sternentage
            self.verdienen(10, tag)                                  # 4 Tage je 10 Sterne -> Level 5, 4 Sammeltage
        st = self.hub.franzi_stand(besuch=True)
        self.assertIn("raum-hell", st["besitz"])
        self.assertIn("Level", st["satz"])
        self.assertNotIn("raum-bad", st["besitz"])
        with self.assertRaises(ValueError):
            self.hub.franzi_kaufen("raum-kueche")
        h = self.hub.meintag_heute()
        self.assertTrue(all(x["belohnung"] for x in h["sachen"]))
        self.assertEqual([x["frei"] for x in h["sachen"]], [True, False, False, False, False, False, False, False, False])   # 4 Sammeltage: nur das Sonnenzimmer

    def test_ohne_haustier_bleibt_mein_tag_schrank(self):
        self.verdienen(10)
        h = self.hub.meintag_heute()
        self.assertEqual([x["id"] for x in h["sachen"]], ["muetze", "blau", "sonne"])
        self.assertFalse(any(x.get("belohnung") for x in h["sachen"]))
        self.assertNotIn("raum-bad", (self.hub.franzi_zustand or {}).get("besitz") or [])


if __name__ == "__main__":
    unittest.main()
