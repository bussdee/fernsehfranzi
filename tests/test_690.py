"""6.9.0: Franzi als Haustier (Werte, Stimmung, Abenteuer, Typ) und der Sterne-Shop."""
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))
from fernsehfranzi import franzi, meintag  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

MITTAG = datetime(2026, 11, 25, 16, 0)          # Mittwoch
EIN = franzi.einstellungen({"aktiv": True})


class Modul(unittest.TestCase):
    def test_neu_mit_startausstattung(self):
        z, satz = franzi.besuch(EIN, {}, MITTAG)
        self.assertIn("spiel-fangen", z["besitz"])
        self.assertIn("raum-zimmer", z["besitz"])
        self.assertNotIn("spiel-memory", z["besitz"])
        self.assertEqual(franzi.stimmung(z, MITTAG), "froehlich")
        self.assertEqual(z["tagebuch"][0]["art"], "hallo")

    def test_werte_sinken_tags_nachts_kaum(self):
        z, _ = franzi.besuch(EIN, {}, MITTAG)
        tag = franzi.altern(dict(z, werte=dict(z["werte"])), MITTAG + timedelta(hours=6))
        self.assertLess(tag["werte"]["hunger"], 60)
        nacht0 = datetime(2026, 11, 25, 22, 0)
        z2, _ = franzi.besuch(EIN, {}, nacht0)
        nacht = franzi.altern(z2, nacht0 + timedelta(hours=8))
        self.assertGreater(nacht["werte"]["hunger"], 60)          # 6.9.59: nachts ein Viertel
        self.assertEqual(nacht["werte"]["energie"], 100.0)

    def test_stimmungen_und_pflege(self):
        z, _ = franzi.besuch(EIN, {}, MITTAG)
        z["werte"]["hunger"] = 10
        self.assertEqual(franzi.stimmung(z, MITTAG), "hungrig")
        z = franzi.pflegen(EIN, z, MITTAG, "fuettern")
        self.assertGreater(z["werte"]["hunger"], 40)
        z = franzi.pflegen(EIN, z, MITTAG, "streicheln")
        self.assertEqual(z["zuege"]["verschmust"], 1)
        with self.assertRaises(ValueError):
            franzi.pflegen(EIN, z, MITTAG, "zaubern")
        self.assertEqual(franzi.stimmung(z, datetime(2026, 11, 25, 23, 0)) in ("schlaefrig", "vertraeumt"), True)

    def test_nie_tot_abenteuer_und_rueckkehr(self):
        z, _ = franzi.besuch(EIN, {}, MITTAG)
        spaeter = MITTAG + timedelta(days=20)
        z, satz = franzi.besuch(EIN, z, spaeter)
        self.assertIsNotNone(z["abenteuer"])
        self.assertIn("Abenteuerreise", satz)
        self.assertTrue(all(v >= 70 for v in z["werte"].values()))
        z, satz = franzi.besuch(EIN, z, spaeter + timedelta(minutes=1))
        self.assertIsNone(z["abenteuer"])
        self.assertIn("zurück", satz)

    def test_abenteuer_tage_einstellbar_und_gedaechtnis(self):
        e = franzi.einstellungen({"aktiv": True, "abenteuer_tage": 10})
        z, _ = franzi.besuch(e, {}, MITTAG)
        z, satz = franzi.besuch(e, z, MITTAG + timedelta(days=3))
        self.assertIsNone(z["abenteuer"])
        self.assertIn("3 Tage", satz)

    def test_typ_erst_nach_zwei_wochen(self):
        z, _ = franzi.besuch(EIN, {}, MITTAG)
        for _ in range(8):
            z = franzi.pflegen(EIN, z, MITTAG, "streicheln")
            z = franzi.pflegen(EIN, z, MITTAG, "ball")
        self.assertIsNone(franzi.typ(z, MITTAG))
        self.assertEqual(franzi.typ(z, MITTAG + timedelta(days=15)), "Kuschel-Clown")

    def test_minispiel_ohne_sterne_nur_besessene(self):
        z, _ = franzi.besuch(EIN, {}, MITTAG)
        z = franzi.gespielt(z, MITTAG, "spiel-fangen", 42)
        self.assertEqual(z["rekorde"]["spiel-fangen"], 42)
        with self.assertRaises(ValueError):
            franzi.gespielt(z, MITTAG, "spiel-memory")

    def test_kaufen(self):
        e = franzi.einstellungen({"aktiv": True, "preise": {"spiel-memory": 3}})
        z, _ = franzi.besuch(e, {}, MITTAG)
        with self.assertRaises(ValueError):
            franzi.kaufen(e, z, 2, MITTAG, "spiel-memory")
        z, p = franzi.kaufen(e, z, 5, MITTAG, "spiel-memory")
        self.assertEqual(p, 3)
        self.assertIn("spiel-memory", z["besitz"])
        with self.assertRaises(ValueError):
            franzi.kaufen(e, z, 5, MITTAG, "spiel-memory")

    def test_anziehen_raum_stellen(self):
        z, _ = franzi.besuch(EIN, {}, MITTAG)
        with self.assertRaises(ValueError):
            franzi.anziehen(z, MITTAG, "kleid-krone", True)
        z["besitz"].append("kleid-krone")
        z = franzi.anziehen(z, MITTAG, "kleid-krone", True)
        self.assertEqual(z["angezogen"], ["kleid-krone"])
        z["besitz"] += ["kleid-zauberhut", "kleid-blau"]
        z = franzi.anziehen(z, MITTAG, "kleid-blau", True)
        z = franzi.anziehen(z, MITTAG, "kleid-zauberhut", True)            # ersetzt die Krone (beides Hut)
        self.assertEqual(sorted(z["angezogen"]), ["kleid-blau", "kleid-zauberhut"])
        z = franzi.setzen(z, MITTAG, "moebel-bett", 20, 17)                  # 6.9.54: frei platzieren
        self.assertEqual(z["zimmer"]["raum-zimmer"]["moebel-bett"][:2], [20, 17])
        self.assertTrue(set(franzi.KLEIDUNG_TEIL) == franzi.KLEIDUNG_IDS)
        with self.assertRaises(ValueError):
            franzi.raum_wechseln(z, MITTAG, "raum-garten")

    def test_ereignis_hoechstens_einmal_am_tag(self):
        z, _ = franzi.besuch(EIN, {}, MITTAG)
        texte = 0
        for tag in range(60):
            jetzt = MITTAG + timedelta(days=tag)
            t1 = franzi.ereignis(z, jetzt)
            self.assertIsNone(franzi.ereignis(z, jetzt + timedelta(hours=1)))
            texte += bool(t1)
        self.assertTrue(5 <= texte <= 40)

    def test_wetter_art(self):
        self.assertEqual(franzi.wetter_art({"code": 61, "gefuehlt": 8}), "regen")
        self.assertEqual(franzi.wetter_art({"code": 73, "gefuehlt": -3}), "schnee")
        self.assertEqual(franzi.wetter_art({"code": 3, "gefuehlt": 0}), "kalt")
        self.assertEqual(franzi.wetter_art({"code": 0, "gefuehlt": 18, "symbol": "☀️"}), "sonne")
        self.assertIsNone(franzi.wetter_art(None))
        z, _ = franzi.besuch(EIN, {}, MITTAG)
        tv = franzi.fuer_tv(EIN, z, MITTAG, 0, wetter="regen")
        self.assertIn("Regencape", tv["satz"])
        self.assertIn("warm", franzi.fuer_tv(EIN, z, MITTAG, 0, warm=True)["satz"])

    def test_raum_bonus(self):
        z, _ = franzi.besuch(EIN, {}, MITTAG)
        z["werte"]["sauber"] = 10
        a = franzi.pflegen(EIN, dict(z, werte=dict(z["werte"])), MITTAG, "waschen")["werte"]["sauber"]
        z["besitz"].append("raum-bad")
        z = franzi.raum_wechseln(z, MITTAG, "raum-bad")
        b = franzi.pflegen(EIN, z, MITTAG, "waschen")["werte"]["sauber"]
        self.assertEqual(b - a, 20)

    def test_geburtstag_und_erinnerung(self):
        e = franzi.einstellungen({"aktiv": True, "geburtstag": "25.11."})
        z, _ = franzi.besuch(e, {}, MITTAG)
        self.assertIn("Geburtstag", franzi.fuer_tv(e, z, MITTAG, 0)["satz"])
        self.assertNotIn("Geburtstag", franzi.fuer_tv(e, z, MITTAG + timedelta(days=1), 0)["satz"])
        for _ in range(3):
            z = franzi.gespielt(z, MITTAG, "spiel-fangen", 5)
        self.assertIn("Sterne fangen", franzi.erinnerung(z, MITTAG))
        for falsch in ("31.02.", "1.13.", "abc", "2026-11-25"):
            with self.assertRaises(ValueError):
                franzi.pruefe({"geburtstag": falsch})
        self.assertEqual(franzi.pruefe({"geburtstag": "29.02."})["geburtstag"], "29.02.")

    def test_alte_plaetze_ziehen_um(self):
        z, _ = franzi.besuch(EIN, {}, MITTAG)
        z["zimmer"] = {"raum-zimmer": {"links": "moebel-bett", "rechts": "spielzeug-ball", "mitte": "spielzeug-teddy", "wand": "moebel-bild"}}
        z, _ = franzi.besuch(EIN, z, MITTAG)
        r = z["zimmer"]["raum-zimmer"]                                      # 6.9.54: alte Plätze -> freie Lage
        self.assertEqual(sorted(r), ["moebel-bett", "moebel-bild", "spielzeug-ball", "spielzeug-teddy"])
        self.assertEqual(r["moebel-bett"][:2], list(franzi.PLATZ_LAGE["hinten-links"]))
        self.assertEqual(r["moebel-bild"][:2], list(franzi.PLATZ_LAGE["wand-rechts"]))

    def test_pruefe(self):
        ok = franzi.pruefe({"aktiv": True, "abenteuer_tage": 4, "preise": {"raum-garten": 20},
                            "angebote": [{"nr": 1, "name": "30 Minuten", "art": "minuten", "minuten": 30, "preis": 5, "pro_woche": 2}]})
        self.assertEqual(ok["preise"]["raum-garten"], 20)
        for schlecht in ({"preise": {"gibtsnicht": 1}}, {"abenteuer_tage": 0},
                         {"angebote": [{"nr": 1, "name": "x", "art": "zauber", "preis": 1}]}):
            with self.assertRaises(ValueError):
                franzi.pruefe(schlecht)


class Hub(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-franzi-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(MITTAG)
        self.hub = neuer_hub(self.ordner, self.uhr)

    def sterne(self, n):
        z = meintag.zustand_fuer(self.hub.meintag_zustand, MITTAG.date())
        z["sterne"] = n
        self.hub.meintag_zustand = z

    def test_aus_ab_werk(self):
        self.assertFalse(self.hub.franzi()["aktiv"])
        with self.assertRaises(ValueError):
            self.hub.franzi_tun("streicheln")

    def test_shop_und_angebot(self):
        self.hub.einstellungen["franzi"] = {"aktiv": True, "angebote": [
            {"nr": 1, "name": "Extra-Zeit", "art": "minuten", "minuten": 20, "preis": 4, "pro_woche": 1},
            {"nr": 2, "name": "Eis essen", "art": "frei", "preis": 2, "pro_woche": 0}]}
        self.sterne(20)
        st = self.hub.franzi_stand(besuch=True)
        self.assertEqual(st["sterne"], 20)
        st = self.hub.franzi_kaufen("spiel-memory")
        self.assertEqual(st["sterne"], 12)
        self.assertTrue(next(k for k in st["katalog"] if k["id"] == "spiel-memory")["hat"])
        st = self.hub.franzi_angebot(1)
        self.assertEqual(st["sterne"], 8)
        with self.assertRaises(ValueError):
            self.hub.franzi_angebot(1)                     # nur einmal je Woche
        self.assertEqual(self.hub.franzi_angebot(2)["sterne"], 6)
        self.hub.franzi_schenken("kleid-krone")                       # 6.9.11: Geschenk ohne Sterne
        st = self.hub.franzi_stand(besuch=True)
        self.assertEqual(st["sterne"], 6)
        self.assertIn("Krone", st["satz"])
        self.assertIn("Krone", self.hub.franzi_stand(besuch=True)["tagebuch"][0]["text"])
        self.assertNotIn("Geschenk", self.hub.franzi_stand(besuch=True)["satz"])   # nur einmal gesagt
        with self.assertRaises(ValueError):
            self.hub.franzi_schenken("kleid-krone")
        self.assertTrue(os.path.exists(os.path.join(self.ordner, "franzi.json")))


if __name__ == "__main__":
    unittest.main()
