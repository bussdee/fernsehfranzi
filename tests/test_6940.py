"""6.9.40: Klang-Ordner je Art, Klang je Ereignis, Pakete, Hintergrundmusik."""
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))
from fernsehfranzi import klaenge  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

LINK = "http://server:8080/share/AbCd1234"


class Modul(unittest.TestCase):
    def test_eigene_klaenge_je_art(self):
        self.assertEqual(klaenge.eigen_pfad("eigen@tasten:klick.mp3"), "klick.mp3")
        self.assertEqual(klaenge.eigen_art("eigen@tasten:klick.mp3"), "tasten")
        self.assertIsNone(klaenge.eigen_art("eigen:Hupe.mp3"))
        self.assertEqual(klaenge.eigen_pfad("eigen:Hupe.mp3"), "Hupe.mp3")
        for falsch in ("eigen@quatsch:a.mp3", "eigen@tasten:../a.mp3", "eigen@tasten:a.exe"):
            self.assertIsNone(klaenge.eigen_pfad(falsch), falsch)
        self.assertEqual(len(klaenge.ARTEN), 8)

    def test_vorgaben_und_pruefung(self):
        e = klaenge.einstellungen(None)
        self.assertEqual(e["ereignisse"]["tasten"], "")
        self.assertEqual(e["bedienung_laut"], 100)
        self.assertFalse(e["musik"]["start"]["an"])
        ok = lambda link: ""                                          # noqa: E731
        klaenge.pruefe_einstellungen({"ordner_arten": {"tasten": LINK}, "ereignisse": {"ok": "harfe", "stern": "eigen@belohnung:a.mp3"},
                                      "bedienung_laut": 40, "musik": {"start": {"an": True, "klang": "eigen@musik:lied.mp3", "laut": 20}}}, ok)
        for falsch in ({"quatsch": 1}, {"ordner_arten": {"falsch": LINK}}, {"ereignisse": {"ok": "gibtsnicht"}},
                       {"bedienung_laut": 101}, {"musik": {"start": {"an": True, "klang": ""}}},
                       {"musik": {"start": {"klang": "harfe"}}}):
            with self.assertRaises(ValueError, msg=falsch):
                klaenge.pruefe_einstellungen(falsch, ok)
        with self.assertRaises(ValueError):
            klaenge.pruefe_einstellungen({"ordner_arten": {"tasten": "kaputt"}}, lambda link: "ist kein Freigabelink.")

    def test_pakete_nur_gueltige_klaenge(self):
        for name, p in klaenge.PAKETE.items():
            for e, k in p["ereignisse"].items():
                self.assertIn(e, klaenge.EREIGNIS_IDS, name)
                self.assertTrue(klaenge.gueltig(k), (name, k))

    def test_fuer_tv(self):
        tv = klaenge.fuer_tv({"ereignisse": {"ok": "harfe", "meldung": "glocke"}, "musik": {"franzi": {"an": False, "klang": "eigen@musik:a.mp3"}}})
        self.assertEqual(tv["ereignisse"], {"ok": "harfe"})           # Meldungen spielt der Server, nicht der Browser
        self.assertEqual(tv["musik"], {})                              # aus = nichts


class Hub(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-6940-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(datetime(2026, 11, 25, 16)))

    def test_ordner_je_art_und_meldung_vorgabe(self):
        self.hub.einstellungen_aendern({"klaenge": {"ordner": "", "ordner_arten": {"tasten": LINK}, "ereignisse": {"meldung": "harfe"}}})
        self.assertEqual(self.hub.klaenge_ordner("tasten"), LINK)
        self.assertEqual(self.hub.klaenge_ordner(), "")
        self.assertIn("AbCd1234/klick.mp3", self.hub.klang_eigen_adresse("eigen@tasten:klick.mp3"))
        with self.assertRaises(ValueError):
            self.hub.klang_eigen_adresse("eigen:klick.mp3")            # allgemeiner Ordner fehlt
        with self.assertRaises(ValueError):
            self.hub.klaenge_eigen("quatsch")
        gespielt = []
        self.hub.system.gong = lambda klang=None: gespielt.append(klang)
        self.hub.klang_spielen(None)
        self.hub.klang_spielen("glocke")
        self.assertEqual(gespielt, ["harfe", "glocke"])
        self.assertEqual(self.hub.startseite_anzeige()["klang"]["bedienung_laut"], 100)
        self.assertEqual(len(self.hub.eltern_daten()["klang_ereignisse"]), len(klaenge.EREIGNISSE))


if __name__ == "__main__":
    unittest.main()
