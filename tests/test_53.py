"""5.3: Wartungsmodus beim Ausliefern - Datei wartung.json im Datenordner: Warnbildschirm, kein Start, endet von selbst."""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from test_v3_server import MITTWOCH, Uhr, neuer_hub  # noqa: E402


class Wartung(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-53-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(MITTWOCH))
        self.datei = os.path.join(self.ordner, "wartung.json")

    def setze(self, bis):
        with open(self.datei, "w") as f:
            json.dump({"bis": bis, "grund": "deploy"}, f)
        self.hub._wartung_gelesen = 0          # nicht 2 s warten

    def test_an_und_wieder_aus(self):
        self.assertIsNone(self.hub.status()["wartung"])
        self.setze(time.time() + 600)
        self.assertGreater(self.hub.status()["wartung"]["rest_s"], 590)
        ok, grund = self.hub.starte("spiel-snake")
        self.assertFalse(ok)
        self.assertIn("aktualisiert", grund)
        os.remove(self.datei)
        self.hub._wartung_gelesen = 0
        self.assertIsNone(self.hub.status()["wartung"])
        self.assertTrue(self.hub.starte("spiel-snake")[0])

    def test_vorwarnung_vor_der_sperre(self):
        with open(self.datei, "w") as f:
            json.dump({"ab": time.time() + 10, "bis": time.time() + 600}, f)
        self.hub._wartung_gelesen = 0
        w = self.hub.status()["wartung"]
        self.assertIn(w["vorwarnung_s"], (10, 11))
        self.assertTrue(self.hub.starte("spiel-snake")[0], "während der Vorwarnung geht noch alles")
        self.assertIn("speichern", self.hub.meldung["text"])
        self.assertIn("hinweis", [a["art"] for a in self.hub.auftraege])
        with open(self.datei, "w") as f:
            json.dump({"ab": time.time() - 1, "bis": time.time() + 600}, f)
        self.hub._wartung_gelesen = 0
        self.assertIn("rest_s", self.hub.status()["wartung"])
        self.assertFalse(self.hub.starte("spiel-snake")[0])

    def test_endet_von_selbst(self):
        self.setze(time.time() - 1)
        self.assertIsNone(self.hub.wartung(), "abgelaufen")
        self.setze(time.time() + 99 * 3600)
        self.assertLessEqual(self.hub.wartung()["rest_s"], self.hub.WARTUNG_MAX_S, "höchstens 2 Stunden")

    def test_kaputte_datei_heisst_aus(self):
        with open(self.datei, "w") as f:
            f.write("{kaputt")
        self.hub._wartung_gelesen = 0
        self.assertIsNone(self.hub.wartung())


class Absender(unittest.TestCase):
    def test_nachricht_mit_namen_des_elternteils(self):
        ordner = tempfile.mkdtemp(prefix="ff-53a-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(MITTWOCH))
        hub.einstellungen_aendern({"telegram": {"aktiv": False, "token": "", "chats": [
            {"id": 5, "name": "Papa", "symbol": "🐼", "eltern": True, "darf_schreiben": True, "eigene_texte": True,
             "nur_freizeit": False, "medien": True, "klang": "fanfare"},
            {"id": 7, "name": "Lena", "symbol": "🦄", "eltern": False, "darf_schreiben": False, "eigene_texte": False,
             "nur_freizeit": True, "medien": False}]}})
        hub.eltern_nachricht("Update in 5 Minuten!", 5)
        m = hub.familie.offene_meldungen()[-1]
        self.assertEqual((m["quelle"], m["symbol"], m["klang"]), ("Papa", "🐼", "fanfare"))
        self.assertIn("Papa: Update", hub.meldung["text"])
        hub.eltern_nachricht("Ohne Namen")
        self.assertEqual(hub.familie.offene_meldungen()[-1]["quelle"], "Nachricht von Mama oder Papa")
        with self.assertRaises(ValueError):
            hub.eltern_nachricht("Freundin ist kein Elternteil", 7)


class Zuletzt(unittest.TestCase):
    """6.0: „Weiter, wo du warst“ auf der Startseite."""
    def test_neueste_zuerst_ohne_werkzeuge(self):
        ordner = tempfile.mkdtemp(prefix="ff-60z-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(MITTWOCH))
        for app in ("spiel-snake", "spiel-memory", "spiel-wecker", "spiel-snake"):
            hub.starte(app)
        self.assertEqual(hub.zuletzt(), ["spiel-snake", "spiel-memory"], "neueste zuerst, doppelt nur einmal, Wecker zählt nicht")
        st = hub.status()
        self.assertEqual(st["budget_min"], 90, "für den Restzeit-Balken")


if __name__ == "__main__":
    unittest.main()
