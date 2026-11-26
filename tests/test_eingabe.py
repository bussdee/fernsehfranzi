"""eingabe/eingabe.py: Entscheidungslogik für Fernbedienung und Controller (ohne Geräte, mit Testuhr)."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "eingabe"))

import eingabe  # noqa: E402


class Uhr:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


class Logik(unittest.TestCase):
    def setUp(self):
        self.aktionen, self.uhr = [], Uhr()
        self.logik = eingabe.Logik(self.aktionen.append, uhr=self.uhr)

    def lage(self, **status):
        self.logik.status = dict({"running": False, "aktuell": None}, **status)

    def test_pfeile_und_ok_werden_tasten(self):
        self.logik.cec_druck(0x01)
        self.logik.cec_los()
        self.logik.cec_druck(0x00)
        self.assertEqual(self.aktionen, [("halte", "UP"), ("loslassen",), ("halte", "ENTER")])

    def test_exit_kurz_auf_startseite_ist_escape(self):
        self.logik.cec_druck(eingabe.CEC_EXIT)
        self.uhr.t += 0.3
        self.logik.cec_los()
        self.assertEqual(self.aktionen, [("taste", "ESC")])

    def test_exit_kurz_auf_webseite_zum_launcher(self):
        """Wie in 2.x: EXIT in Plex führt zur Startseite (21.11.: „Exit funktioniert in Plex nicht“)."""
        self.lage(aktuell="plex", aktuell_typ="web")
        self.logik.cec_druck(eingabe.CEC_EXIT)
        self.logik.cec_los()
        self.assertEqual(self.aktionen, [("server", "/api/zurueck", {})])

    def test_exit_lang_zur_startseite_auch_ohne_loslassen(self):
        self.lage(aktuell="plex", aktuell_typ="web")
        self.logik.cec_druck(eingabe.CEC_EXIT)
        self.uhr.t += 1.0
        self.logik.takt()
        self.assertEqual(self.aktionen, [])
        self.uhr.t += 0.6
        self.logik.takt()
        self.assertEqual(self.aktionen, [("server", "/api/zurueck", {})])
        self.logik.cec_los()                       # spätes Loslassen löst nichts zusätzlich aus
        self.assertEqual(len(self.aktionen), 1)

    def test_exit_in_retroarch_beendet_das_spiel(self):
        self.lage(running=True, retroarch=True, aktuell="games")
        self.logik.cec_druck(eingabe.CEC_EXIT)
        self.logik.cec_los()
        self.assertEqual(self.aktionen, [("retroarch_beenden",)])

    def test_amiberry_zaehlt_als_laufendes_spiel(self):
        class Ergebnis:
            def __init__(self, code): self.returncode = code
        aufrufe = []
        def lauf(befehl, **_):
            aufrufe.append(befehl)
            return Ergebnis(0 if befehl[-1] == "amiberry" else 1)
        self.assertTrue(eingabe.emulator_laeuft(lauf))
        self.assertIn(["pgrep", "-x", "amiberry"], aufrufe)
        self.assertFalse(eingabe.emulator_laeuft(lambda befehl, **_: Ergebnis(1)))

    def test_exit_in_emulationstation_zur_startseite(self):
        self.lage(running=True, retroarch=False, aktuell="games")
        self.logik.cec_druck(eingabe.CEC_EXIT)
        self.logik.cec_los()
        self.assertEqual(self.aktionen, [("server", "/api/zurueck", {})])

    def test_gelb_und_pfeile_regeln_die_lautstaerke(self):
        self.logik.cec_druck(eingabe.CEC_GELB)
        self.logik.cec_druck(0x01)
        self.logik.cec_druck(0x02)
        self.uhr.t += 5                                    # nach 4 s wieder normale Pfeile
        self.logik.cec_druck(0x01)
        self.assertEqual(self.aktionen, [("server", "/api/lautstaerke", {"richtung": "lauter"}),
                                         ("server", "/api/lautstaerke", {"richtung": "lauter"}),
                                         ("server", "/api/lautstaerke", {"richtung": "leiser"}),
                                         ("halte", "UP")])

    def test_tastatur_sondertasten(self):
        for n in ("VOLUMEUP", "VOLUMEDOWN", "MUTE", "F20", "F22"):
            self.logik.tastatur(n)
        self.assertEqual(self.aktionen, [("server", "/api/lautstaerke", {"richtung": "lauter"}),
                                         ("server", "/api/lautstaerke", {"richtung": "leiser"}),
                                         ("server", "/api/lautstaerke", {"richtung": "stumm"}),
                                         ("server", "/api/zurueck", {}),
                                         ("server", "/api/zurueck", {"eltern": True})])

    def test_tastatur_home_im_spiel_beendet_das_spiel(self):
        self.lage(running=True, retroarch=True)
        self.logik.tastatur("F20")
        self.lage(running=True, retroarch=False)
        self.logik.tastatur("F20")
        self.assertEqual(self.aktionen, [("retroarch_beenden",), ("server", "/api/zurueck", {})])

    def test_hwdb_legt_die_sondertasten_um(self):
        with open(os.path.join(REPO, "system", "udev", "90-fernsehfranzi-tastatur.hwdb"), encoding="utf-8") as f:
            regeln = [z for z in f.read().splitlines() if z and not z.startswith("#")]
        self.assertEqual(regeln[0], "evdev:input:b0005v04E8p7021*")
        self.assertEqual(sorted(z.strip() for z in regeln[1:]), ["KEYBOARD_KEY_70065=f22", "KEYBOARD_KEY_c0221=f21",
                                                                 "KEYBOARD_KEY_c0223=f20", "KEYBOARD_KEY_c0224=esc"])
        self.assertTrue(all(z.startswith(" ") for z in regeln[1:]), "hwdb: Eigenschaften mit Leerzeichen einrücken")

    def test_labwc_kiosk_ohne_tastenkuerzel(self):
        import xml.etree.ElementTree as ET
        ns = {"o": "http://openbox.org/3.4/rc"}
        wurzel = ET.parse(os.path.join(REPO, "system", "labwc", "rc.xml")).getroot()
        tasten = wurzel.findall("o:keyboard/o:keybind", ns)
        self.assertIsNone(wurzel.find("o:keyboard/o:default", ns), "keine eingebauten Kürzel (Terminal!)")
        self.assertEqual([k.get("key") for k in tasten], ["C-A-S-F12"])
        self.assertEqual([a.get("name") for a in tasten[0]], ["Reconfigure"])
        menue = ET.parse(os.path.join(REPO, "system", "labwc", "menu.xml")).getroot()
        self.assertEqual([len(m) for m in menue], [0, 0, 0])

    def test_controller_back_und_pfeile_lautstaerke(self):
        self.logik.pad_richtung("UP", gehalten={"BACK"})
        self.logik.pad_richtung("UP")
        self.assertEqual(self.aktionen, [("server", "/api/lautstaerke", {"richtung": "lauter"}), ("taste", "UP")])

    def test_farbtasten(self):
        self.logik.cec_druck(eingabe.CEC_ROT)
        self.logik.cec_druck(eingabe.CEC_GRUEN)
        self.logik.cec_druck(eingabe.CEC_BLAU)
        self.assertEqual(self.aktionen, [("server", "/api/audio", {"ziel": "hdmi"}),
                                         ("server", "/api/audio", {"ziel": "klinke"}),
                                         ("server", "/api/zurueck", {"eltern": True})])

    def test_farbtasten_im_farben_echo(self):
        self.lage(aktuell="spiel-echo", aktuell_typ="spiel")
        for code in (eingabe.CEC_ROT, eingabe.CEC_GRUEN, eingabe.CEC_GELB, eingabe.CEC_BLAU):
            self.logik.cec_druck(code)
        self.assertEqual(self.aktionen, [("taste", "F9"), ("taste", "F10"), ("taste", "F11"), ("taste", "F12")])

    def test_controller_im_hub(self):
        self.logik.pad_knopf("A", True, {"A"})
        self.logik.pad_knopf("A", False, set())
        self.logik.pad_knopf("B", True, {"B"})
        self.logik.pad_richtung("LEFT")
        self.logik.pad_knopf("RB", True, {"RB"})
        self.assertEqual(self.aktionen, [("taste", "ENTER"), ("taste", "ESC"), ("taste", "LEFT"),
                                         ("taste", "FASTFORWARD")])

    def test_xbox_taste_in_der_spieleliste_zur_startseite(self):
        self.lage(running=True, retroarch=False, aktuell="games")
        self.logik.pad_knopf("GUIDE", True, {"GUIDE"})
        self.assertEqual(self.aktionen, [("server", "/api/zurueck", {})])

    def test_controller_in_retropie_bleibt_nativ(self):
        self.lage(running=True, retroarch=True, aktuell="games")
        self.logik.pad_knopf("A", True, {"A"})
        self.logik.pad_richtung("UP")
        self.logik.pad_knopf("GUIDE", True, {"GUIDE"})   # Guide ist dort Hotkey-Taste (Guide+Start)
        self.assertEqual(self.aktionen, [])

    def test_guide_im_hub_zur_startseite(self):
        self.lage(aktuell="plex", aktuell_typ="web")
        self.logik.pad_knopf("GUIDE", True, {"GUIDE"})
        self.assertEqual(self.aktionen, [("server", "/api/zurueck", {})])

    def test_back_allein_tut_nichts(self):
        self.logik.pad_knopf("BACK", True, {"BACK"})
        self.logik.pad_knopf("START", True, {"BACK", "START"})
        self.assertEqual(self.aktionen, [])

    def test_fernseher_aus_nur_bei_neuem_befehl(self):
        self.logik.neuer_status({"running": False, "cec": {"nr": 3, "befehl": "standby"}})
        self.assertEqual(self.aktionen, [], "alter Befehl beim Start wird nicht wiederholt")
        self.logik.neuer_status({"running": False, "cec": {"nr": 4, "befehl": "standby"}})
        self.logik.neuer_status({"running": False, "cec": {"nr": 4, "befehl": "standby"}})
        self.assertEqual(self.aktionen, [("cec", "standby")])
        self.logik.neuer_status({"running": False, "cec": {"nr": 5, "befehl": "an"}})      # 3.5: Wecker
        self.assertEqual(self.aktionen[-1], ("cec", "an"))

    def test_zweiter_controller(self):
        self.logik.pad_richtung("UP", spieler=2)
        self.logik.pad_knopf("A", True, {"A"}, spieler=2)
        self.logik.pad_knopf("B", True, {"B"}, spieler=2)
        self.logik.pad_knopf("GUIDE", True, {"GUIDE"}, spieler=2)
        self.assertEqual(self.aktionen, [("taste", "W"), ("taste", "F"), ("taste", "G"),
                                         ("server", "/api/zurueck", {})])

    def test_cec_zeilen(self):
        self.assertEqual(eingabe.DRUCK.search("TRAFFIC: [ 1234] >> 04:44:0d").group(1), "0d")
        self.assertTrue(eingabe.LOS.search("TRAFFIC: [ 1300] >> 04:45"))



class CecZustand(unittest.TestCase):
    """6.1: Fernseher aus/an mit Abfrage des Zustands ("pow 0") - ohne echtes CEC."""

    def ausgabe(self, antworten):
        import threading
        a = eingabe.Ausgabe.__new__(eingabe.Ausgabe)
        a.strom, a.strom_neu, a.cec_pruefung = None, threading.Event(), False
        befehle, gemeldet = [], []

        class Stdin:
            def write(self, text):
                befehle.append(text.strip())
                if text.strip() == "pow 0":
                    a.strom_gemeldet(antworten.pop(0))

            def flush(self):
                pass

        a.cec_client = type("C", (), {"stdin": Stdin()})()
        a.server = lambda pfad, daten=None, methode="POST": gemeldet.append((pfad, daten))
        return a, befehle, gemeldet

    def setUp(self):
        self.vorher, eingabe.CEC_WARTEN_S = eingabe.CEC_WARTEN_S, 0
        self.addCleanup(setattr, eingabe, "CEC_WARTEN_S", self.vorher)

    def test_antwort_wird_erkannt(self):
        self.assertEqual(eingabe.STROM.search("power status: standby").group(1), "standby")
        self.assertEqual(eingabe.STROM.search("power status: on\n").group(1), "on")

    def test_test_klappt(self):
        a, befehle, gemeldet = self.ausgabe(["standby", "on"])
        a._cec_test()
        self.assertEqual(befehle, ["standby 0", "pow 0", "on 0", "as", "pow 0"])
        self.assertEqual(gemeldet, [("/api/geraet/cec-test", {"aus": True, "an": True})])

    def test_fernseher_bleibt_aus(self):
        a, _, gemeldet = self.ausgabe(["standby", "standby"])
        a._cec_test()
        self.assertEqual(gemeldet[0][1], {"aus": True, "an": False})

    def test_wecker_lernt_nur_wenn_vorher_aus(self):
        a, befehle, gemeldet = self.ausgabe(["on"])
        a._an_und_lernen()
        self.assertEqual(befehle, ["pow 0", "on 0", "as"])
        self.assertEqual(gemeldet, [], "war schon an - nichts gelernt")
        a, _, gemeldet = self.ausgabe(["standby", "on"])
        a._an_und_lernen()
        self.assertEqual(gemeldet, [("/api/geraet/cec-test", {"aus": True, "an": True})])


if __name__ == "__main__":
    unittest.main()
