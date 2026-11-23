"""4.6: Gaming-Zeit als Teil der Bildschirmzeit, „nur eigenes Limit“, eingebaute Spiele an/aus und mit Zeitart,
Bewegungspause je Angebot, Erinnerungen mit Ferien-Schalter, Ferien des Bundeslandes per Knopf (und automatisch)."""
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import ferien, zeitkonto  # noqa: E402
from test_v3_server import MITTWOCH, Uhr, neuer_hub  # noqa: E402

FREI = datetime(2026, 11, 18, 15, 0)            # Mittwoch, keine Sperrzeit (Vorgabe: Schule bis 14, Nacht ab 19:30)


class GamingZeit(unittest.TestCase):
    def konto(self, **regeln):
        return zeitkonto.Zeitkonto(zeitkonto.neue_regeln(dict({"sperrzeiten": []}, **regeln)), {})

    def test_gaming_zaehlt_in_beide_toepfe(self):
        k = self.konto(budget_min={"schultag": 90, "frei": 150}, gaming_min={"schultag": 30, "frei": 60})
        spiel = {"id": "snake", "name": "Snake", "zeit": "gaming"}
        film = {"id": "yt", "name": "YouTube", "zeit": "zaehlt"}
        for _ in range(30):
            k.tick(FREI, spiel, 60)
        self.assertEqual(k.zustand["genutzt_s"], 30 * 60, "Gaming ist Teil der Bildschirmzeit")
        self.assertEqual(k.zustand["gaming_s"], 30 * 60)
        ok, grund, _ = k.darf_starten(spiel, FREI)
        self.assertFalse(ok)
        self.assertIn("Spielzeit", grund)
        self.assertTrue(k.darf_starten(film, FREI)[0], "Filme gehen noch, solange Bildschirmzeit übrig ist")
        self.assertEqual(k.rest_s(FREI, film), 60 * 60)

    def test_bildschirmzeit_begrenzt_auch_gaming(self):
        k = self.konto(budget_min={"schultag": 20, "frei": 20}, gaming_min={"schultag": 60, "frei": 60})
        film, spiel = {"id": "yt", "zeit": "zaehlt"}, {"id": "s", "zeit": "gaming"}
        for _ in range(20):
            k.tick(FREI, film, 60)
        self.assertFalse(k.darf_starten(spiel, FREI)[0])
        self.assertEqual(k.gaming_rest_s(FREI), 0)

    def test_bonus_gilt_fuer_beide(self):
        k = self.konto(gaming_min={"schultag": 10, "frei": 10})
        spiel = {"id": "s", "zeit": "gaming"}
        for _ in range(10):
            k.tick(FREI, spiel, 60)
        self.assertFalse(k.darf_starten(spiel, FREI)[0])
        k.bonus(FREI, 15)
        self.assertTrue(k.darf_starten(spiel, FREI)[0])

    def test_nur_eigenes_limit(self):
        k = self.konto(budget_min={"schultag": 90, "frei": 90})
        app = {"id": "kk", "name": "Klassenkiste", "zeit": "frei", "limit_min": {"schultag": 5}}
        for _ in range(5):
            k.tick(FREI, app, 60)
        self.assertEqual(k.zustand["genutzt_s"], 0, "kostet keine Bildschirmzeit")
        ok, grund, _ = k.darf_starten(app, FREI)
        self.assertFalse(ok)
        self.assertIn("Klassenkiste", grund)
        self.assertTrue(k.darf_starten({"id": "x", "zeit": "frei"}, FREI)[0], "kein Limit bleibt frei")

    def test_regeln_pruefen(self):
        with self.assertRaises(ValueError):
            zeitkonto.pruefe_regeln(zeitkonto.neue_regeln({"gaming_min": {"schultag": -1, "frei": 0}}))
        with self.assertRaises(ValueError):
            zeitkonto.pruefe_regeln(zeitkonto.neue_regeln({"bundesland": "XX"}))


class Ferien(unittest.TestCase):
    def test_feiertage(self):
        self.assertEqual(ferien.ostersonntag(2027), date(2027, 3, 28))
        sh = [n for _, n in ferien.feiertage("SH", 2027)]
        self.assertIn("Karfreitag", sh)
        self.assertNotIn("Fronleichnam", sh, "Fronleichnam nur in BW, BY, HE, NW, RP, SL")
        self.assertIn("Fronleichnam", [n for _, n in ferien.feiertage("BY", 2027)])
        self.assertTrue(all(t.weekday() < 5 for t, _ in ferien.feiertage("BY", 2027)), "nur Werktage")

    def test_zeitraeume_ab_heute(self):
        z = ferien.zeitraeume("BW", date(2026, 11, 23), mit_feiertagen=False)
        self.assertIn(["2026-12-23", "2027-01-09"], z)
        self.assertIn(["2027-07-29", "2027-09-11"], z, "Sommerferien sind dabei")
        self.assertFalse(any(bis < "2026-11-23" for _, bis in z), "Vergangenes nicht")
        with self.assertRaises(ValueError):
            ferien.zeitraeume("", date(2026, 11, 23))

    def test_zusammenfuehren_behaelt_eigene(self):
        eigen = [["2027-05-14", "2027-05-14"], ["2026-01-02", "2026-01-03"]]
        neu = ferien.zusammenfuehren(eigen, [["2026-12-23", "2027-01-09"]], date(2026, 11, 23))
        self.assertEqual(neu, [["2026-12-23", "2027-01-09"], ["2027-05-14", "2027-05-14"]])


class ImHub(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-46-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(MITTWOCH)
        self.hub = neuer_hub(self.ordner, self.uhr)

    def test_eingebaute_spiele_ausschalten(self):
        self.assertIn("spiel-snake", [k["id"] for k in self.hub.kacheln()])
        self.assertEqual(self.hub.app("spiel-snake")["zeit"], "gaming", "Spiele zählen zur Gaming-Zeit")
        self.hub.einstellungen_aendern({"spielzimmer": {"spiel-snake": {"aktiv": False}, "spiel-malen": {"zeit": "zaehlt"}}})
        self.assertNotIn("spiel-snake", [k["id"] for k in self.hub.kacheln()])
        ok, grund = self.hub.starte("spiel-snake")
        self.assertFalse(ok)
        self.assertIn("ausgeschaltet", grund)
        self.assertEqual(self.hub.app("spiel-malen")["zeit"], "zaehlt")
        self.assertIn("spielzimmer", self.hub.eltern_daten())

    def test_eingebaute_spiele_pruefen(self):
        for falsch in ({"spiel-gibtsnicht": {}}, {"spiel-snake": {"name": "X"}}, {"spiel-snake": {"zeit": "immer"}},
                       {"spiel-snake": {"bewegung": "ja"}}):
            with self.assertRaises(ValueError, msg=falsch):
                self.hub.einstellungen_aendern({"spielzimmer": falsch})

    def test_retro_spiele_werden_gaming(self):
        self.assertEqual(self.hub.app("games")["zeit"], "gaming")

    def test_bewegungspause_je_angebot(self):
        f = self.hub.familie
        self.hub.einstellungen_aendern({"familie": dict(self.hub.familie.einstellungen(),
                                                        bewegungspause={"aktiv": True, "nach_min": 10, "dauer_min": 2})})
        snake = dict(self.hub.app("spiel-snake"), bewegung=False)
        for _ in range(13):
            f._bewegung(f.einstellungen(), self.uhr(), snake, 60, True)
        self.assertIsNone(f.pause_bis, "ausgeschaltet: keine Pause")
        malen = dict(self.hub.app("spiel-malen"), bewegung=True)      # kostet keine Zeit, Pause trotzdem gewünscht
        for _ in range(11):
            f._bewegung(f.einstellungen(), self.uhr(), malen, 60, True)
        self.assertIsNotNone(f.pause_bis)

    def test_erinnerung_nicht_in_den_ferien(self):
        heute = MITTWOCH.date().isoformat()
        self.hub.einstellungen_aendern({"zeit": {"ferien": [[heute, heute]]}})
        fam = dict(self.hub.familie.einstellungen(), erinnerungen=[
            {"zeit": "15:00", "text": "Sportsachen!", "tage": [], "wann": "schule"},
            {"zeit": "15:00", "text": "Ferien-Spaß!", "tage": [], "wann": "ferien"}])
        self.hub.einstellungen_aendern({"familie": fam})
        self.hub.familie._erinnerungen(self.hub.familie.einstellungen(), MITTWOCH, heute)
        texte = [m["text"] for m in self.hub.familie.offene_meldungen()]
        self.assertIn("Ferien-Spaß!", texte)
        self.assertNotIn("Sportsachen!", texte)
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"familie": dict(fam, erinnerungen=[{"zeit": "15:00", "text": "x", "wann": "nie"}])})

    def test_ferien_eintragen_und_automatisch(self):
        self.hub.einstellungen_aendern({"zeit": {"ferien": [["2026-11-30", "2026-11-30"]]}})   # eigener Tag
        a = self.hub.ferien_eintragen("BW", feiertage=True, auto=True)
        regeln = self.hub._regeln()
        self.assertEqual(regeln["bundesland"], "BW")
        self.assertIn(["2026-12-23", "2027-01-09"], regeln["ferien"])
        self.assertIn(["2026-11-30", "2026-11-30"], regeln["ferien"], "eigene Einträge bleiben")
        self.assertIn(["2027-11-01", "2027-11-01"], regeln["ferien"], "Allerheiligen 2027 (BW) als Feiertag")
        self.assertNotIn(["2027-05-27", "2027-05-27"], regeln["ferien"], "Fronleichnam liegt in den Pfingstferien")
        self.assertGreater(a["neu"], 10)
        # Automatik: ein gelöschter Zeitraum kommt am nächsten Tag wieder
        zeit = dict(self.hub.einstellungen["zeit"], ferien=[z for z in regeln["ferien"] if z[0] != "2026-12-23"])
        self.hub.einstellungen_aendern({"zeit": zeit})
        self.uhr.jetzt += timedelta(days=1)
        self.hub.ferien_auffrischen()
        self.assertIn(["2026-12-23", "2027-01-09"], self.hub._regeln()["ferien"])
        with self.assertRaises(ValueError):
            self.hub.ferien_eintragen("")


if __name__ == "__main__":
    unittest.main()
