"""Server-Kern 3.0 (server/fernsehfranzi): Daten, Katalog, PIN, Zeitkonto, Whitelist."""
import copy
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))

from fernsehfranzi import daten, katalog, pin, whitelist, zeitkonto  # noqa: E402

SPIEL = {"id": "games", "name": "Games", "typ": "konsole", "start": "fernsehfranzi-retropie.service",
         "zeit": "zaehlt", "limit_min": {"schultag": 45, "frei": 75}, "eingabe": "tasten", "domains": [], "aktiv": True}
SNAKE = {"id": "snake", "name": "Snake", "typ": "web", "start": "http://127.0.0.1:8765/spiele/snake",
         "zeit": "zaehlt"}
PLEX = {"id": "plex", "name": "Plex", "typ": "web", "start": "", "zeit": "frei"}
GUTE_NACHT = {"id": "gute-nacht", "name": "Gute Nacht", "typ": "hoerbuch", "start": "", "zeit": "frei", "sperr_erlaubt": "alle"}
# Mittwoch, 18.11.2026, 15:00 (Schultag, im Fenster)
MITTWOCH = datetime(2026, 11, 18, 15, 0)
SAMSTAG = datetime(2026, 11, 21, 10, 0)


class Daten(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-daten-")

    def test_atomar_schreiben_und_lesen(self):
        pfad = os.path.join(self.ordner, "x.json")
        daten.schreibe_json(pfad, {"ä": 1})
        self.assertEqual(daten.lies_json(pfad), {"ä": 1})
        self.assertEqual([n for n in os.listdir(self.ordner) if n.startswith(".tmp-")], [])

    def test_kaputte_datei_wird_beiseitegelegt(self):
        pfad = os.path.join(self.ordner, "x.json")
        with open(pfad, "w") as datei:
            datei.write("{kaputt")
        with self.assertLogs("fernsehfranzi.daten", "ERROR"):
            self.assertEqual(daten.lies_json(pfad, vorgabe={"v": 1}), {"v": 1})
        self.assertTrue(any(n.startswith("x.json.kaputt-") for n in os.listdir(self.ordner)))

    def test_migration_idempotent_und_protokolliert(self):
        with open(os.path.join(self.ordner, "einstellungen.json"), "w") as datei:
            json.dump({"name": "x"}, datei)
        erst = daten.lade_einstellungen(self.ordner)
        self.assertEqual(erst["schema"], daten.SCHEMA_VERSION)
        self.assertEqual(erst["name"], "x")
        self.assertIn("whitelist", erst)
        zweit = daten.lade_einstellungen(self.ordner)
        self.assertEqual(erst, zweit)
        with open(os.path.join(self.ordner, "migration.log")) as datei:
            self.assertEqual(len(datei.read().splitlines()), 1)
        self.assertTrue(os.path.exists(os.path.join(self.ordner, "einstellungen.json.vor-schema-1")))

    def test_neueres_schema_wird_nicht_angefasst(self):
        with self.assertRaises(ValueError):
            daten.migriere({"schema": daten.SCHEMA_VERSION + 1})

    def test_datenordner_aus_umgebung(self):
        alt = os.environ.get("FERNSEHFRANZI_DATEN")
        os.environ["FERNSEHFRANZI_DATEN"] = os.path.join(self.ordner, "d")
        try:
            self.assertEqual(daten.datenordner(), os.path.join(self.ordner, "d"))
            self.assertEqual(os.stat(os.path.join(self.ordner, "d")).st_mode & 0o777, 0o700)
        finally:
            if alt is None:
                del os.environ["FERNSEHFRANZI_DATEN"]
            else:
                os.environ["FERNSEHFRANZI_DATEN"] = alt


class Katalog(unittest.TestCase):
    def test_vorgabe_ist_gueltig_und_ohne_adressen(self):
        sortiert = katalog.pruefe_katalog(copy.deepcopy(katalog.VORGABE))
        self.assertEqual([e["id"] for e in sortiert],
                         ["gute-nacht", "plex", "youtube", "games", "familie", "buecher", "klassenkiste", "kinderwelten"])
        for eintrag in katalog.VORGABE:
            if eintrag["id"] in ("plex", "familie", "buecher", "gute-nacht"):
                self.assertEqual(eintrag["start"], "", "keine Heimnetz-Adressen im Code (Regel 20)")
        oeffentlich = {e["id"]: e["start"] for e in katalog.VORGABE if e["start"].startswith("https://")}
        self.assertEqual(oeffentlich, {"klassenkiste": "https://klassenkiste.eu/",
                                       "kinderwelten": "https://app.familienfabrik.at/"})
        self.assertTrue(all(e["zeit"] == "frei" for e in katalog.VORGABE if e["id"] in ("plex", "familie", "gute-nacht")))
        self.assertEqual(next(e for e in katalog.VORGABE if e["id"] == "gute-nacht")["sperr_erlaubt"], "alle")

    def test_kacheln_ohne_start_sind_nicht_eingerichtet(self):
        kacheln = {k["id"]: k for k in katalog.kacheln(copy.deepcopy(katalog.VORGABE))}
        self.assertFalse(kacheln["plex"]["eingerichtet"])
        self.assertTrue(kacheln["games"]["eingerichtet"])

    def test_fehler_werden_gesammelt(self):
        schlecht = [
            {"id": "Gross", "name": "", "typ": "app", "zeit": "immer"},
            {"id": "web1", "name": "W", "typ": "web", "start": "file:///etc/passwd", "zeit": "frei"},
            {"id": "k", "name": "K", "typ": "konsole", "start": "/bin/bash", "zeit": "zaehlt"},
            {"id": "web1", "name": "W2", "typ": "web", "zeit": "frei", "domains": ["nicht gültig"]},
        ]
        with self.assertRaises(katalog.KatalogFehler) as fang:
            katalog.pruefe_katalog(schlecht)
        text = str(fang.exception)
        for teil in ("id fehlt", "typ muss", "zeit muss", "http(s)", "Konsolen-Apps", "doppelt", "Domain"):
            self.assertIn(teil, text)

    def test_inaktive_app_wird_nicht_gezeigt(self):
        eintraege = copy.deepcopy(katalog.VORGABE)
        eintraege[0]["aktiv"] = False
        self.assertNotIn("plex", [k["id"] for k in katalog.kacheln(eintraege)])


class Pin(unittest.TestCase):
    def setUp(self):
        self.eintrag = pin.hash_erzeugen("482913", iterationen=1000)

    def test_hash_enthaelt_keine_pin(self):
        self.assertNotIn("482913", json.dumps(self.eintrag))
        self.assertTrue(pin.pin_stimmt("482913", self.eintrag))
        self.assertFalse(pin.pin_stimmt("482914", self.eintrag))

    def test_salz_ist_zufaellig(self):
        self.assertNotEqual(self.eintrag["hash"], pin.hash_erzeugen("482913", iterationen=1000)["hash"])

    def test_ungueltige_pin(self):
        for falsch in ("12", "abcdef", "123456789", 123456):
            with self.assertRaises(ValueError):
                pin.hash_erzeugen(falsch)
            self.assertFalse(pin.pin_stimmt(falsch, self.eintrag))

    def test_sperre_waechst(self):
        sperre = pin.Sperre()
        jetzt = 1000.0
        for _ in range(4):
            ok, meldung = sperre.pruefe("000000", self.eintrag, jetzt)
            self.assertFalse(ok)
            self.assertIn("Noch", meldung)
        ok, meldung = sperre.pruefe("000000", self.eintrag, jetzt)
        self.assertIn("1 Minuten", meldung)
        # gesperrt: auch die richtige PIN hilft nicht
        self.assertFalse(sperre.pruefe("482913", self.eintrag, jetzt + 30)[0])
        ok, meldung = sperre.pruefe("000000", self.eintrag, jetzt + 61)
        self.assertIn("2 Minuten", meldung)
        self.assertTrue(sperre.pruefe("482913", self.eintrag, jetzt + 61 + 121)[0])
        self.assertEqual(sperre.zustand["fehler"], 0)

    def test_sperre_hoechstens_eine_stunde(self):
        sperre = pin.Sperre({"fehler": 20, "gesperrt_bis": 0})
        sperre.pruefe("000000", self.eintrag, 0)
        self.assertEqual(sperre.zustand["gesperrt_bis"], pin.SPERRE_MAX_S)


class Zeitkonto(unittest.TestCase):
    def spiele(self, konto, app, start, minuten, schritt=30):
        ereignisse, jetzt = [], start
        for _ in range(int(minuten * 60 / schritt)):
            jetzt += timedelta(seconds=schritt)
            ereignisse += konto.tick(jetzt, app, schritt)
        return ereignisse, jetzt

    def test_tagesart(self):
        regeln = zeitkonto.neue_regeln({"ferien": [["2026-12-21", "2027-01-06"]]})
        self.assertEqual(zeitkonto.tagesart(MITTWOCH.date(), regeln), "schultag")
        self.assertEqual(zeitkonto.tagesart(SAMSTAG.date(), regeln), "frei")
        self.assertEqual(zeitkonto.tagesart(datetime(2026, 12, 22).date(), regeln), "frei")
        self.assertEqual(zeitkonto.tagesart(datetime(2027, 1, 7).date(), regeln), "schultag")

    def test_freie_app_ohne_timer_aber_mit_sperrzeit(self):
        konto = zeitkonto.Zeitkonto()
        self.assertEqual(konto.tick(MITTWOCH, PLEX, 30), [])
        self.assertEqual(konto.zustand["genutzt_s"], 0)
        self.assertEqual(konto.darf_starten(PLEX, MITTWOCH), (True, "", ""))
        ok, grund, art = konto.darf_starten(PLEX, MITTWOCH.replace(hour=23))      # Nacht
        self.assertEqual((ok, art), (False, "nacht"))
        self.assertIn("wieder ab 08:00", grund)
        # Gute Nacht: in allen Sperrzeiten erlaubt, auch ohne gestellte Uhr
        self.assertEqual(konto.darf_starten(GUTE_NACHT, MITTWOCH.replace(hour=23), uhr_sicher=False), (True, "", ""))

    def test_leerlauf_zaehlt_nicht(self):
        konto = zeitkonto.Zeitkonto()
        konto.tick(MITTWOCH, SNAKE, 30, aktiv=False)
        self.assertEqual(konto.rest_s(MITTWOCH), 90 * 60)

    def test_uhrsprung_zaehlt_hoechstens_eine_minute(self):
        konto = zeitkonto.Zeitkonto()
        konto.tick(MITTWOCH, SNAKE, 3600)
        self.assertEqual(konto.zustand["genutzt_s"], 60)

    def test_retropie_grenze_schultag(self):
        konto = zeitkonto.Zeitkonto()
        ereignisse, jetzt = self.spiele(konto, SPIEL, MITTWOCH, 45)
        self.assertEqual([e for e in ereignisse if e[0] == "warnung"],
                         [("warnung", 10), ("warnung", 5), ("warnung", 1)])
        self.assertIn(("kulanz", 2), ereignisse)
        self.assertEqual(konto.darf_starten(SPIEL, jetzt)[0], False)
        # Snake zählt aufs Gesamtbudget (90), RetroPie-Grenze betrifft es nicht
        self.assertTrue(konto.darf_starten(SNAKE, jetzt)[0])
        self.assertEqual(konto.rest_s(jetzt, SNAKE), 45 * 60)

    def test_kulanz_dann_schluss(self):
        konto = zeitkonto.Zeitkonto()
        _, jetzt = self.spiele(konto, SPIEL, MITTWOCH, 45)
        ereignisse, _ = self.spiele(konto, SPIEL, jetzt, 1.5)
        self.assertNotIn(("schluss", "games"), ereignisse)
        ereignisse, _ = self.spiele(konto, SPIEL, jetzt + timedelta(minutes=1.5), 1)
        self.assertIn(("schluss", "games"), ereignisse)

    def test_sperrzeiten_und_unsichere_uhr(self):
        konto = zeitkonto.Zeitkonto()
        ok, grund, art = konto.darf_starten(SNAKE, MITTWOCH.replace(hour=13))
        self.assertEqual((ok, art), (False, "schule"))
        self.assertIn("Schule – wieder ab 14:00", grund)
        self.assertTrue(konto.darf_starten(SNAKE, SAMSTAG)[0])                  # Schule nur Mo-Fr
        self.assertEqual(konto.darf_starten(SNAKE, MITTWOCH, uhr_sicher=False)[2], "uhr")
        erlaubt = dict(SNAKE, sperr_erlaubt=["Schule"])
        self.assertTrue(konto.darf_starten(erlaubt, MITTWOCH.replace(hour=13))[0])

    def test_sperrzeit_ueber_mitternacht_und_ferien(self):
        regeln = zeitkonto.neue_regeln({"ferien": [["2026-12-21", "2027-01-06"]]})
        konto = zeitkonto.Zeitkonto(regeln)
        nacht = [s["name"] for s, _ in zeitkonto.aktive_sperrzeiten(datetime(2026, 11, 19, 2, 0), regeln)]
        self.assertEqual(nacht, ["Nacht"])                                       # vom Vortag 19:30 bis 08:00
        self.assertEqual(zeitkonto.aktive_sperrzeiten(datetime(2026, 11, 19, 8, 0), regeln)[0][0]["name"], "Schule")
        self.assertTrue(konto.darf_starten(SNAKE, datetime(2026, 12, 22, 10, 0))[0])    # Ferien: keine Schule
        self.assertEqual([s["name"] for s, _ in zeitkonto.naechste_sperrzeiten(datetime(2026, 11, 18, 19, 25), regeln, 600)],
                         ["Nacht"])
        self.assertEqual([s["name"] for s, _ in zeitkonto.begonnene_sperrzeiten(datetime(2026, 11, 18, 19, 31), regeln, 300)],
                         ["Nacht"])

    def test_regeln_pruefen(self):
        regeln = zeitkonto.neue_regeln()
        zeitkonto.pruefe_regeln(regeln)
        for kaputt in ({"name": "", "von": "19:00", "bis": "07:00", "tage": [0]},
                       {"name": "X", "von": "19:00", "bis": "19:00", "tage": [0]},
                       {"name": "X", "von": "19:00", "bis": "07:00", "tage": []},
                       {"name": "Nacht", "von": "19:00", "bis": "07:00", "tage": [0]}):
            with self.assertRaises(ValueError):
                zeitkonto.pruefe_regeln(dict(regeln, sperrzeiten=regeln["sperrzeiten"] + [kaputt]))

    def test_alte_regeln_werden_sperrzeiten(self):
        zeit, retro = zeitkonto.alte_regeln_uebernehmen(
            {"budget_min": {"schultag": 60, "frei": 120}, "retropie_max_min": {"schultag": 30, "frei": 60},
             "fenster": {"schultag": ["14:00", "19:30"], "frei": ["09:00", "20:00"]}},
            {"aktiv": True, "zeit": "19:00"})
        self.assertEqual(retro, {"schultag": 30, "frei": 60})
        nacht, schule = zeit["sperrzeiten"]
        self.assertEqual((nacht["von"], nacht["bis"], nacht["nacht"]), ("19:00", "09:00", True))
        self.assertEqual((schule["von"], schule["bis"], schule["tage"], schule["ferien_frei"]),
                         ("09:00", "14:00", [0, 1, 2, 3, 4], True))
        zeitkonto.pruefe_regeln(zeitkonto.neue_regeln(zeit))

    def test_neuer_tag_neues_konto(self):
        konto = zeitkonto.Zeitkonto()
        self.spiele(konto, SPIEL, MITTWOCH, 45)
        morgen = MITTWOCH + timedelta(days=1)
        self.assertEqual(konto.rest_s(morgen, SPIEL), 45 * 60)

    def test_bonus_und_ohne_limit(self):
        konto = zeitkonto.Zeitkonto()
        _, jetzt = self.spiele(konto, SNAKE, MITTWOCH, 90)
        self.assertFalse(konto.darf_starten(SNAKE, jetzt)[0])
        konto.bonus(jetzt, 15)
        self.assertEqual(konto.rest_s(jetzt, SNAKE), 15 * 60)
        with self.assertRaises(ValueError):
            konto.bonus(jetzt, 1000)
        konto.heute_ohne_limit(jetzt)
        self.assertIsNone(konto.rest_s(jetzt, SNAKE))
        self.assertTrue(konto.darf_starten(SNAKE, jetzt)[0])

    def test_eigenes_app_limit(self):
        konto = zeitkonto.Zeitkonto()
        app = dict(SNAKE, limit_min={"schultag": 20, "frei": 40})
        _, jetzt = self.spiele(konto, app, MITTWOCH, 20)
        self.assertFalse(konto.darf_starten(app, jetzt)[0])
        self.assertTrue(konto.darf_starten(SPIEL, jetzt)[0])

    def test_zustand_ist_speicherbar(self):
        konto = zeitkonto.Zeitkonto()
        self.spiele(konto, SPIEL, MITTWOCH, 10)
        wieder = zeitkonto.Zeitkonto(zustand=json.loads(json.dumps(konto.zustand)))
        self.assertEqual(wieder.rest_s(MITTWOCH, SPIEL), 35 * 60)

    def test_unbekannte_regel(self):
        with self.assertRaises(ValueError):
            zeitkonto.neue_regeln({"budjet_min": {}})


class Whitelist(unittest.TestCase):
    def katalog(self):
        eintraege = copy.deepcopy(katalog.VORGABE)[:4]      # nur die Heimnetz-Apps
        eintraege[0]["domains"] = ["plex.example", "*.cdn.example"]
        eintraege[2]["domains"] = ["Plex.Example"]
        eintraege[3]["aktiv"] = False
        eintraege[3]["domains"] = ["inaktiv.example"]
        return eintraege

    def test_sammeln(self):
        domains = whitelist.sammle(self.katalog(), zusatz=["schule.example"], system=False)
        self.assertEqual(sorted(domains), ["*.cdn.example", "plex.example", "schule.example"])

    def test_lernseiten_sind_in_der_vorgabe_erlaubt(self):
        domains = whitelist.sammle(copy.deepcopy(katalog.VORGABE), system=False)
        self.assertIn("klassenkiste.eu", domains)
        self.assertIn("familienfabrik.at", domains)

    def test_ungueltiger_zusatz(self):
        with self.assertRaises(ValueError):
            whitelist.sammle([], zusatz=["http://x"])

    def test_exporte(self):
        domains = whitelist.sammle(self.katalog(), system=False)
        pihole = whitelist.export_pihole(domains)
        self.assertIn("plex.example\n", pihole)
        self.assertIn(r"(\.|^)cdn\.example$", pihole)
        self.assertEqual(sorted(whitelist.export_fritzbox(domains).split()), ["cdn.example", "plex.example"])


if __name__ == "__main__":
    unittest.main()
