"""6.8.6: „Mama/Papa fragen“ bei gesperrten Seiten - Sperre melden, ROT/Y/Suche fragt, Eltern erlauben oder lehnen ab."""
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "eingabe"))
sys.path.insert(0, os.path.join(REPO, "kiosk"))
sys.path.insert(0, os.path.join(REPO, "tests"))

import eingabe  # noqa: E402
import kiosk  # noqa: E402
from fernsehfranzi import telegram  # noqa: E402
from test_telegram44 import TOKEN  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

TG = {"aktiv": True, "token": TOKEN, "chats": [{"id": 111, "name": "Papa"}]}


class Fragen(unittest.TestCase):
    def setUp(self):
        alt, telegram.BASIS = telegram.BASIS, "http://127.0.0.1:9"        # nie ins Netz
        self.addCleanup(setattr, telegram, "BASIS", alt)
        self.ordner = tempfile.mkdtemp(prefix="ff-686-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(datetime(2026, 11, 18, 15, 0))
        self.hub = neuer_hub(self.ordner, self.uhr)
        self.gesendet = []
        self.hub.telegram.melde_eltern = lambda art, text: (self.gesendet.append((art, text)), ["Papa"])[1]
        self.addCleanup(lambda: self.hub.einstellungen_aendern({"telegram": {"aktiv": False, "token": TOKEN}}))

    def test_ab_werk_aus(self):
        self.assertEqual(self.hub.seite_gesperrt("spiele.example"), {"frage": False})
        self.assertIsNone(self.hub.status()["fragen_host"])
        with self.assertRaises(ValueError):
            self.hub.frage_stellen()
        with self.assertRaises(ValueError):
            self.hub.seite_gesperrt("böse seite")

    def test_fragen_erlauben_ablehnen(self):
        self.hub.einstellungen_aendern({"fragen": {"aktiv": True}, "telegram": TG, "name": "Kind"})
        self.assertEqual(self.hub.seite_gesperrt("lernen.example"), {"frage": True})
        self.assertEqual(self.hub.status()["fragen_host"], "lernen.example")
        self.assertEqual(self.hub.frage_stellen(), {"schon": False, "nr": 1})
        self.assertEqual(self.gesendet, [("fragen", "❓ Kind möchte die Seite lernen.example öffnen. Antwort: /erlauben 1 oder /ablehnen 1")])
        self.assertTrue(self.hub.frage_stellen()["schon"], "dieselbe Seite nicht zweimal")
        antworten = []
        self.hub.telegram.antwort = lambda c, text: antworten.append(text)
        self.hub.telegram.befehl({"id": 111}, "/erlauben 1")
        self.assertEqual(antworten[-1], "✅ lernen.example ist jetzt erlaubt.")
        self.assertIn("lernen.example", self.hub.einstellungen["whitelist"]["zusatz"])
        self.assertIn("lernen.example geht jetzt", self.hub.meldung["text"])
        self.hub.telegram.befehl({"id": 111}, "/erlauben 1")
        self.assertIn("⚠️", antworten[-1], "schon beantwortet")
        self.hub.seite_gesperrt("andere.example")
        self.hub.frage_stellen()
        self.hub.telegram.befehl({"id": 111}, "/ablehnen 2")
        self.assertNotIn("andere.example", self.hub.einstellungen["whitelist"]["zusatz"])
        self.assertIn("lieber nicht", self.hub.meldung["text"])
        self.assertEqual([f["stand"] for f in self.hub.eltern_daten()["fragen"]], ["ja", "nein"])

    def test_frage_gilt_nur_kurz_nach_der_sperre(self):
        self.hub.einstellungen_aendern({"fragen": {"aktiv": True}, "telegram": TG})
        self.hub.seite_gesperrt("x.example")
        self.uhr.weiter(181)
        self.assertIsNone(self.hub.fragen_host())


class Tasten(unittest.TestCase):
    def setUp(self):
        self.aktionen = []
        self.logik = eingabe.Logik(self.aktionen.append, uhr=lambda: 100.0)

    def test_rot_y_suche_nur_auf_der_sperrseite(self):
        self.logik.status = {"running": False, "aktuell": "internet", "fragen_host": None}
        self.logik.cec_druck(eingabe.CEC_ROT)
        self.assertEqual(self.aktionen[-1], ("server", "/api/audio", {"ziel": "hdmi"}), "sonst wie immer: Ton")
        self.logik.status["fragen_host"] = "x.example"
        self.logik.cec_druck(eingabe.CEC_ROT)
        self.assertEqual(self.aktionen[-1], ("server", "/api/frage", {}))
        self.logik.pad_knopf("Y", True, {"Y"})
        self.assertEqual(self.aktionen[-1], ("server", "/api/frage", {}))
        self.logik.tastatur("F21")
        self.assertEqual(self.aktionen[-1], ("server", "/api/frage", {}))
        self.assertEqual(len(self.aktionen), 4)



class KioskMeldet(unittest.TestCase):
    def test_gesperrte_hauptseite_wird_gemeldet(self):
        k = kiosk.Kiosk(tempfile.mkdtemp(prefix="ff-686k-"))
        gemeldet, hinweise = [], []
        k.server = lambda pfad, daten=None, timeout=5: (gemeldet.append((pfad, daten)), {"frage": True})[1]
        k.hinweis = hinweise.append
        k.anfragen.update({"a": "spiele.example", "b": "werbung.example"})
        k.ereignis("Network.loadingFailed", {"requestId": "b", "errorText": "net::ERR_BLOCKED_BY_ADMINISTRATOR", "type": "Image"}, None)
        k.ereignis("Network.loadingFailed", {"requestId": "a", "errorText": "net::ERR_BLOCKED_BY_ADMINISTRATOR", "type": "Document"}, None)
        for _ in range(100):                                   # die Meldung läuft in einem eigenen Faden (mit 1 s Pause)
            if hinweise:
                break
            time.sleep(0.05)
        self.assertEqual(gemeldet, [("/api/kiosk/gesperrt", {"host": "spiele.example"})], "nur die Seite selbst, keine Bilder")
        self.assertIn("ROT", hinweise[0])
        self.assertEqual(k.domains["werbung.example"]["blockiert"], 1)


if __name__ == "__main__":
    unittest.main()
