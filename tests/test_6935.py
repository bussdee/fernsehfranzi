"""6.9.35: Bluetooth koppeln mit Agent, Klassenkiste mit zweitem Versuch und Hinweis statt Fehler,
eigene Klänge auch im Elternbereich durchreichen, Karaoke-Hinweis auf Premium."""
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import datetime

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))
from fernsehfranzi import schule, web  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402


class Bluetooth(unittest.TestCase):
    def test_koppeln_mit_agent_und_pruefung(self):
        with open(os.path.join(REPO, "system", "bt-helfer"), encoding="utf-8") as f:
            text = f.read()
        teil = text[text.index("  koppeln)"):text.index("  verbinden)")]
        for muss in ("agent NoInputNoOutput", "default-agent", "pairable on", "scan on", 'grep -q "Paired: yes"', "exit 1"):
            self.assertIn(muss, teil)


class Klassenkiste(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-6935-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(datetime(2026, 11, 25, 16, 0)))

    def test_zweiter_versuch_bei_stummem_fernseher(self):
        versuche = []
        def einmal(neu, warten_s):
            versuche.append(neu)
            if len(versuche) == 1:
                raise ValueError("Der Fernseher antwortet gerade nicht. Bitte nochmal versuchen.")
            return "https://x", "cookie"
        self.hub._kk_cookie_einmal = einmal
        self.assertEqual(self.hub._kk_cookie(), ("https://x", "cookie"))
        self.assertEqual(versuche, [False, True])

    def test_andere_fehler_ohne_zweiten_versuch(self):
        versuche = []
        def einmal(neu, warten_s):
            versuche.append(neu)
            raise ValueError("Dafür muss die Klassenkiste angemeldet sein.")
        self.hub._kk_cookie_einmal = einmal
        with self.assertRaises(ValueError):
            self.hub._kk_cookie()
        self.assertEqual(len(versuche), 1)

    def test_hinweis_statt_fehler_wenn_stand_da(self):
        s = self.hub.schule
        s.einstellungen = lambda: {"aktiv": True}
        self.hub.klassenkiste_basis = lambda: "https://x"
        s.stand, s.stand_zeit, s.geholt, s.fehler = {"hausaufgaben": []}, time.time() - 600, time.time(), "Der Fernseher antwortet gerade nicht."
        tv = s.fuer_tv()
        self.assertEqual(tv["fehler"], "")
        self.assertIn("gleich wieder", tv["hinweis"])
        s.stand = None
        self.assertIn("Fernseher", s.fuer_tv()["fehler"])

    def test_schnelle_wiederholung(self):
        self.assertLess(schule.KIOSK_PAUSE_S, schule.FEHLER_PAUSE_S)


class Rest(unittest.TestCase):
    def test_eltern_seite_reicht_klaenge_durch(self):
        self.assertTrue(hasattr(web.LanHandler, "_durchreichen"))

    def test_karaoke_premium_hinweis(self):
        with open(os.path.join(REPO, "web", "js", "spiele", "karaoke.js"), encoding="utf-8") as f:
            self.assertIn("Premium", f.read())


if __name__ == "__main__":
    unittest.main()
