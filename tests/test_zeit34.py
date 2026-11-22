"""3.4: Übernahme der 3.3-Daten (Zeitfenster, Schlafenszeit, Hörbücher, Plex-Gute-Nacht) - einmalig und ohne Verlust."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from test_v3_server import Uhr, neuer_hub  # noqa: E402

# so sahen die Daten am Gerät mit 3.3.0 aus (Werte erfunden, Form echt)
EINSTELLUNGEN_33 = {
    "name": "Kind", "zeit": {"budget_min": {"schultag": 60, "frei": 120}, "retropie_max_min": {"schultag": 30, "frei": 50},
                             "fenster": {"schultag": ["14:00", "19:30"], "frei": ["09:00", "20:00"]},
                             "ferien": [["2026-12-21", "2027-01-06"]]},
    "familie": {"schlafenszeit": {"aktiv": True, "zeit": "19:00", "tage": [0, 1, 2, 3, 4, 5, 6]},
                "gute_nacht": {"url": "http://plex.example:32400/web/#!/playlist", "minuten": 30},
                "erinnerungen": [{"zeit": "18:30", "text": "Zähneputzen!", "tage": [0, 1, 2, 3, 4]}]},
}
APPS_33 = [
    {"id": "plex", "name": "Plex", "typ": "web", "start": "http://plex.example:32400/web/", "zeit": "frei",
     "eingabe": "tasten", "domains": [], "aktiv": True, "symbol": "film", "reihenfolge": 10},
    {"id": "games", "name": "Games", "typ": "konsole", "start": "fernsehfranzi-retropie.service", "zeit": "zaehlt",
     "eingabe": "tasten", "domains": [], "aktiv": True, "symbol": "spiel", "reihenfolge": 20},
    {"id": "familie", "name": "Familie", "typ": "web", "start": "http://familie.example:8088", "zeit": "nie",
     "eingabe": "tasten", "domains": [], "aktiv": True, "symbol": "haus", "reihenfolge": 30},
    {"id": "kinderwelten", "name": "Kinderwelten", "typ": "web", "start": "https://app.familienfabrik.at/", "zeit": "zaehlt",
     "limit_min": 40, "eingabe": "tasten", "domains": [], "aktiv": True, "symbol": "stern", "reihenfolge": 60},
    {"id": "hoerspiele", "name": "Hörbücher", "typ": "hoerbuch", "start": "http://server.example:8080/share/AbCd1234",
     "zeit": "nie", "eingabe": "tasten", "domains": [], "aktiv": True, "symbol": "musik", "reihenfolge": 70},
]


class Uebernahme(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-34-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        for name, inhalt in (("einstellungen.json", EINSTELLUNGEN_33), ("apps.json", APPS_33),
                             ("hoerbuch.json", {"hoerspiele": {"ordner": "Bibi", "titel": "Bibi/1.mp3", "sekunde": 99}})):
            with open(os.path.join(self.ordner, name), "w") as f:
                json.dump(inhalt, f)
        self.uhr = Uhr(datetime(2026, 11, 23, 15, 0))           # Montag
        self.hub = neuer_hub(self.ordner, self.uhr)

    def test_sperrzeiten_aus_zeitfenster_und_schlafenszeit(self):
        r = self.hub.eltern_daten()["regeln"]
        self.assertEqual(r["budget_min"], {"schultag": 60, "frei": 120})
        self.assertEqual(r["ferien"], [["2026-12-21", "2027-01-06"]])
        nacht, schule = r["sperrzeiten"]
        self.assertEqual((nacht["name"], nacht["von"], nacht["bis"], nacht["nacht"]), ("Nacht", "19:00", "09:00", True))
        self.assertEqual((schule["von"], schule["bis"]), ("09:00", "14:00"))
        self.assertTrue(self.hub.eltern_daten()["zeit_pruefen"])
        f = self.hub.familie.einstellungen()
        self.assertEqual(f["gute_nacht"], {"automatisch": True}, "Schlafenszeit war an -> Gute Nacht automatisch")
        self.assertNotIn("schlafenszeit", self.hub.einstellungen["familie"])
        self.assertEqual(f["erinnerungen"][0]["text"], "Zähneputzen!")

    def test_apps(self):
        a = {x["id"]: x for x in self.hub.eltern_daten()["apps"]}
        self.assertEqual(a["games"]["limit_min"], {"schultag": 30, "frei": 50})
        self.assertEqual((a["familie"]["zeit"], a["familie"]["sperr_erlaubt"]), ("frei", ["Schule"]))
        self.assertEqual(a["plex"]["sperr_erlaubt"], ["Schule"])
        self.assertEqual((a["kinderwelten"]["zeit"], a["kinderwelten"]["sperr_erlaubt"], a["kinderwelten"]["limit_min"]),
                         ("zaehlt", [], 40))
        self.assertNotIn("hoerspiele", a)
        gn = a["gute-nacht"]
        self.assertEqual((gn["typ"], gn["start"], gn["sperr_erlaubt"]), ("hoerbuch", "http://server.example:8080/share/AbCd1234", "alle"))
        self.assertEqual(json.load(open(os.path.join(self.ordner, "hoerbuch.json")))["gute-nacht"]["sekunde"], 99)

    def test_kacheln_tragen_ein_symbol_statt_text(self):
        self.uhr.weiter(6 * 3600)                                 # 21:00 = Nacht
        k = {x["id"]: x for x in self.hub.kacheln()}
        self.assertEqual((k["plex"]["frei"], k["plex"]["sperre"]), (False, "nacht"))
        self.assertTrue(k["gute-nacht"]["frei"])
        self.assertEqual(k["spiel-snake"]["sperre"], "nacht")

    def test_nur_einmal(self):
        self.hub.einstellungen_aendern({"zeit": dict(self.hub.eltern_daten()["regeln"], budget_min={"schultag": 45, "frei": 90})})
        wieder = neuer_hub(self.ordner, self.uhr)
        self.assertEqual(wieder.eltern_daten()["regeln"]["budget_min"]["schultag"], 45)
        self.assertFalse(wieder.eltern_daten()["zeit_pruefen"], "Eltern haben die Regeln gespeichert")
        self.assertEqual(wieder.app("games")["limit_min"], {"schultag": 30, "frei": 50})


if __name__ == "__main__":
    unittest.main()
