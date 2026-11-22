"""3.1: Familie und Lernen (server/fernsehfranzi/familie.py) mit Systemattrappe und Testuhr."""
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import familie, kern  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

SAMSTAG_ABEND = datetime(2026, 11, 21, 18, 0)


class Familie(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-familie-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(SAMSTAG_ABEND)
        self.hub = neuer_hub(self.ordner, self.uhr)

    def setze(self, **familie_werte):
        self.hub.einstellungen_aendern({"familie": familie_werte})

    def laufe(self, minuten, eingabe=True, check_beantworten=False, tasten=("ENTER", "ENTER")):
        for _ in range(int(minuten * 60 / 5)):
            self.uhr.weiter(5)
            if eingabe:
                self.hub.eingabe(list(tasten))
            if check_beantworten and self.hub.familie.check:
                self.hub.eingabe(list(self.hub.familie.check["folge"]))
            self.hub.tick(5)

    def hinweise(self):
        return [a["text"] for a in self.hub.auftraege_nach(0)[0] if a["art"] == "hinweis"]

    def test_nachricht_ueberall(self):
        self.hub.system.laeuft = True
        self.hub.familie.nachricht("Essen ist fertig!")
        self.assertIn("Essen ist fertig!", self.hub.status()["meldung"]["text"])
        self.assertTrue(any("Essen ist fertig!" in h for h in self.hinweise()))
        self.assertTrue(any(a[0] == "retroarch" and "Essen" in a[1] for a in self.hub.system.aufrufe))
        self.assertIn(("gong",), self.hub.system.aufrufe, "Nachricht ist hörbar")
        with self.assertRaises(ValueError):
            self.hub.familie.nachricht("   ")

    def test_erinnerung_bleibt_bis_ok_und_kommt_alle_5_minuten(self):
        self.setze(erinnerungen=[{"zeit": "18:02", "text": "Zähneputzen!", "tage": [5]}])
        self.laufe(6)
        self.assertEqual(sum("Zähneputzen!" in h for h in self.hinweise()), 1)
        offen = self.hub.status()["meldungen"]
        self.assertEqual([m["text"] for m in offen], ["Zähneputzen!"])
        self.laufe(5)                                               # 18:07: wieder, mit Gong
        self.assertEqual(sum("Zähneputzen!" in h for h in self.hinweise()), 2)
        self.hub.familie.meldungen_gesehen([offen[0]["nr"]])
        self.assertEqual(self.hub.status()["meldungen"], [])
        self.assertTrue(self.hub.eltern_daten()["meldungen"][0]["gesehen"])
        self.laufe(11)
        self.assertEqual(sum("Zähneputzen!" in h for h in self.hinweise()), 2, "bestätigt: keine Wiederholung")

    def test_im_gute_nacht_modus_still(self):
        self.hub.nachtruhe = True
        self.hub.familie.nachricht("Schlaf gut", bleibt=True)
        self.assertNotIn(("gong",), self.hub.system.aufrufe)
        self.assertEqual(self.hinweise(), [])
        self.assertEqual(len(self.hub.status()["meldungen"]), 1, "wartet bis morgen")
        self.laufe(11, eingabe=False)
        self.assertNotIn(("gong",), self.hub.system.aufrufe)
        self.hub.eingabe(["ENTER"])                                  # wach: wieder normal
        self.assertFalse(self.hub.nachtruhe)

    def test_erinnerung_nur_an_ihren_tagen(self):
        self.setze(erinnerungen=[{"zeit": "18:02", "text": "Montags!", "tage": [0]}])
        self.laufe(6)
        self.assertFalse(any("Montags!" in h for h in self.hinweise()))

    def nachtruhe_um(self, uhrzeit):
        regeln = self.hub.eltern_daten()["regeln"]
        regeln["sperrzeiten"][0].update(von=uhrzeit)                # "Nacht"
        self.hub.einstellungen_aendern({"zeit": regeln})

    def test_nachtruhe_warnt_beendet_und_fragt(self):
        self.nachtruhe_um("18:15")
        self.hub.starte("spiel-snake")
        self.laufe(17)
        texte = self.hinweise()
        for minuten in ("10 Minuten", "5 Minuten", "1 Minute"):
            self.assertTrue(any(minuten in t and "Nachtruhe" in t for t in texte), minuten)
        arten = [a["art"] for a in self.hub.auftraege_nach(0)[0]]
        self.assertIn("startseite", arten)
        self.assertEqual(arten.count("nacht"), 1, "Countdown mit drei Knöpfen genau einmal")
        self.assertIsNone(self.hub.aktuell)
        self.assertFalse(self.hub.starte("spiel-snake")[0])

    def test_nachtruhe_mit_automatischer_gute_nacht(self):
        katalog = self.hub.eltern_daten()["apps"]
        next(a for a in katalog if a["id"] == "gute-nacht")["start"] = "http://server:8080/share/AbCd1234"
        self.hub.katalog_aendern(katalog)
        self.setze(gute_nacht={"automatisch": True})
        self.nachtruhe_um("18:15")
        self.laufe(16)
        gn = [a for a in self.hub.auftraege_nach(0)[0] if a["art"] == "gute_nacht"]
        self.assertEqual(len(gn), 1)
        self.assertTrue(gn[0]["automatisch"])
        self.assertEqual(self.hub.aktuell, "gute-nacht")
        self.assertTrue(self.hub.starte("gute-nacht")[0], "Gute Nacht geht in der Nachtruhe")
        self.assertEqual(self.hub.status()["rest_min"], 150, "Gute Nacht zählt nicht zur Zeit")

    def test_nacht_wahl(self):
        self.hub.nacht_wahl("aus")
        self.assertEqual(self.hub.status()["cec"]["befehl"], "standby")
        self.assertTrue(self.hub.still())
        with self.assertRaises(ValueError):
            self.hub.nacht_wahl("vielleicht")

    def test_bewegungspause(self):
        self.setze(bewegungspause={"aktiv": True, "nach_min": 20, "dauer_min": 2})
        self.hub.starte("spiel-snake")
        self.laufe(21)
        self.assertTrue(self.hub.status()["pause"])
        self.assertTrue(any("Bewegungspause" in h for h in self.hinweise()))
        pausen = [a for a in self.hub.auftraege_nach(0)[0] if a.get("pause")]
        self.assertEqual(pausen[-1]["pause"], 120)
        self.laufe(3)
        self.assertFalse(self.hub.status()["pause"])
        self.assertIn("pause", self.hub.familie.zustand["sticker"])

    def lernbonus(self, **werte):
        lb = {"aktiv": True, "lernen_min": 20, "bonus_min": 10, "max_bonus_min": 20,
              "tasten_pro_minute": 3, "check_min": 10}
        lb.update(werte)
        self.setze(lernbonus=lb)

    def test_lernen_verdient_spielzeit_mit_obergrenze(self):
        self.lernbonus()
        vorher = self.hub.status()["rest_min"]
        self.hub.starte("klassenkiste")
        self.laufe(43, check_beantworten=True)
        self.assertEqual(self.hub.status()["rest_min"], vorher + 20)
        self.laufe(25, check_beantworten=True)              # Obergrenze erreicht
        self.assertEqual(self.hub.status()["rest_min"], vorher + 20)

    def test_lernen_ohne_einstellung_kein_bonus(self):
        vorher = self.hub.status()["rest_min"]
        self.hub.starte("klassenkiste")
        self.laufe(25, check_beantworten=True)
        self.assertEqual(self.hub.status()["rest_min"], vorher)

    def test_nur_starten_und_nichts_tun_zaehlt_nicht(self):
        """Lern-App nur öffnen und liegen lassen bringt keine Minute."""
        self.lernbonus()
        self.hub.starte("klassenkiste")
        self.laufe(40, eingabe=False)
        self.assertEqual(self.hub.familie.lernstand()["offen_min"], 0)
        self.assertEqual(self.hub.familie.lernstand()["bestaetigt_min"], 0)

    def test_ab_und_zu_eine_taste_reicht_nicht(self):
        """Eine Taste pro Minute (z. B. um den Leerlauf zu umgehen) ist kein Lernen."""
        self.lernbonus(tasten_pro_minute=3)
        self.hub.starte("klassenkiste")
        for _ in range(30):
            self.hub.eingabe(["RIGHT"])
            self.laufe(1, eingabe=False)
        self.assertEqual(self.hub.familie.lernstand()["offen_min"], 0)

    def test_pruefung_verpasst_minuten_verfallen(self):
        self.lernbonus()
        vorher = self.hub.status()["rest_min"]
        self.hub.starte("klassenkiste")
        self.laufe(11)                                       # 10 aktive Minuten -> Prüfung
        self.assertIsNotNone(self.hub.familie.check)
        self.assertTrue(any("Bist du noch beim Lernen" in h for h in self.hinweise()))
        self.laufe(2, tasten=("ENTER", "ESC"))               # weiter tippen, aber nicht die Folge
        self.assertIsNone(self.hub.familie.check)
        stand = self.hub.familie.lernstand()
        self.assertEqual(stand["bestaetigt_min"], 0)
        self.assertGreaterEqual(stand["verworfen_min"], 10)
        self.assertEqual(self.hub.status()["rest_min"], vorher)

    def test_pruefung_bestanden_minuten_zaehlen(self):
        self.lernbonus(lernen_min=10, bonus_min=5)
        vorher = self.hub.status()["rest_min"]
        self.hub.starte("klassenkiste")
        self.laufe(11)
        self.assertEqual(self.hub.status()["rest_min"], vorher, "vor der Prüfung noch kein Bonus")
        folge = self.hub.familie.check["folge"]
        self.hub.eingabe([folge[0], "ENTER"])                # unterbrochen: zählt nicht
        self.assertIsNotNone(self.hub.familie.check)
        self.hub.eingabe(list(folge))
        self.assertIsNone(self.hub.familie.check)
        self.assertEqual(self.hub.familie.lernstand()["bestaetigt_min"], 10)
        self.assertEqual(self.hub.status()["rest_min"], vorher + 5)

    def test_bass_tagebuch_und_serie(self):
        f = self.hub.familie
        heute = SAMSTAG_ABEND.date()
        for tage_zurueck in (1, 2):
            f.zustand["bass_tage"][(heute - timedelta(days=tage_zurueck)).isoformat()] = 600
        self.hub.starte("spiel-bass")
        self.laufe(6)
        buch = f.bass_tagebuch(heute)
        self.assertEqual(buch["serie"], 3)
        self.assertEqual(buch["tage"][-1]["minuten"], 6)
        for sticker in ("bass-1", "bass-3tage"):
            self.assertIn(sticker, f.zustand["sticker"])

    def test_bass_ohne_eingabe_zaehlt_hoechstens_20_minuten(self):
        self.hub.starte("spiel-bass")
        self.laufe(40, eingabe=False)
        self.assertLessEqual(self.hub.familie.bass_tagebuch()["tage"][-1]["minuten"], 20)

    def test_sticker_aus_erfolgen(self):
        f = self.hub.familie
        self.assertEqual(f.erfolg("snake", 12), ["snake-10"])
        self.assertEqual(f.erfolg("snake", 5), [])
        self.assertEqual(f.erfolg("griffbrett", 15), [])
        self.assertEqual(f.erfolg("griffbrett", 5), ["griffbrett-20"])      # Summe über alle Male
        with self.assertRaises(ValueError):
            f.erfolg("gibtsnicht", 1)
        album = {s["id"]: s for s in f.album()}
        self.assertTrue(album["snake-10"]["seit"])
        self.assertIsNone(album["snake-30"]["seit"])
        self.assertIn("Neuer Sticker", self.hub.status()["meldung"]["text"])

    def test_einstellungen_werden_geprueft(self):
        for falsch in ({"erinnerungen": [{"zeit": "25:00", "text": "x"}]},
                       {"gute_nacht": {"url": "http://x"}},
                       {"schlafenszeit": {"aktiv": True, "zeit": "20:00"}},
                       {"bewegungspause": {"aktiv": True, "nach_min": 1, "dauer_min": 2}},
                       {"unbekannt": 1}):
            with self.assertRaises(ValueError, msg=falsch):
                self.hub.einstellungen_aendern({"familie": falsch})

    def test_zustand_ueberlebt_neustart(self):
        self.hub.familie.erfolg("memory", 1)
        neu = neuer_hub(self.ordner, self.uhr)
        self.assertIn("memory", neu.familie.zustand["sticker"])


class RetroZuletzt(unittest.TestCase):
    def setUp(self):
        self.wurzel = tempfile.mkdtemp(prefix="ff-retro-")
        self.addCleanup(shutil.rmtree, self.wurzel, True)
        self.roms = os.path.join(self.wurzel, "roms")
        listen = os.path.join(self.wurzel, "gamelists")
        os.makedirs(os.path.join(self.roms, "nes"))
        os.makedirs(os.path.join(listen, "nes"))
        for name in ("Mario.zip", "Zelda.zip", "Tetris.zip"):
            open(os.path.join(self.roms, "nes", name), "w").close()
        with open(os.path.join(listen, "nes", "gamelist.xml"), "w") as f:
            f.write("""<gameList>
<game><path>./Mario.zip</path><name>Mario</name><lastplayed>20261120T180000</lastplayed><playcount>4</playcount></game>
<game><path>./Zelda.zip</path><name>Zelda</name><lastplayed>20261121T090000</lastplayed></game>
<game><path>./Tetris.zip</path><name>Tetris</name><favorite>true</favorite></game>
<game><path>../../../etc/passwd</path><name>Böse</name><lastplayed>20991231T000000</lastplayed></game>
<game><path>./Fehlt.zip</path><name>Fehlt</name><lastplayed>20261121T100000</lastplayed></game>
</gameList>""")
        self.listen = listen

    def test_favoriten_dann_zuletzt_nur_echte_dateien(self):
        spiele = familie.lese_gamelists([self.listen], self.roms)
        namen = [s["name"] for s in familie.zuletzt_gespielt(spiele)]
        self.assertEqual(namen, ["Tetris", "Zelda", "Mario"])

    def test_start_nur_aus_der_liste(self):
        ordner = tempfile.mkdtemp(prefix="ff-retro-hub-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(SAMSTAG_ABEND))
        alt = (kern.ROMS, kern.GAMELISTS)
        kern.ROMS, kern.GAMELISTS = self.roms, [self.listen]
        try:
            self.assertFalse(hub.retro_starten("nes", "../../../etc/passwd")[0])
            self.assertTrue(hub.retro_starten("nes", "Zelda.zip")[0])
        finally:
            kern.ROMS, kern.GAMELISTS = alt
        self.assertIn(("spiel", "start"), hub.system.aufrufe)
        with open(os.path.join(ordner, "spiel-start.json")) as f:
            self.assertIn("Zelda.zip", f.read())


if __name__ == "__main__":
    unittest.main()
