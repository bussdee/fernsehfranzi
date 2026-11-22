"""Server 3.0 (server/fernsehfranzi/kern.py, web.py) mit Systemattrappe und Testuhr."""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))

from fernsehfranzi import kern, web  # noqa: E402
import logging  # noqa: E402

# Eigene Log-Ausgabe der Tests: nicht über Handler anderer Testmodule (deren Dateien sind schon weg).
_log = logging.getLogger("fernsehfranzi")
_log.propagate = False
_log.addHandler(logging.NullHandler())

MITTWOCH = datetime(2026, 11, 18, 15, 0)


class Attrappe:
    """Ersetzt fernsehfranzi.system.System - merkt sich jeden Aufruf."""

    def __init__(self):
        self.aufrufe, self.laeuft, self.marke, self.retroarch_an = [], False, 0, False

    def retropie_zustand(self):
        return self.laeuft, self.marke

    def retropie(self, aktion):
        self.aufrufe.append(("retropie", aktion))
        if aktion == "start":
            self.laeuft, self.marke = True, self.marke + 1
        else:
            self.laeuft = False
        return True

    def spiel(self, aktion):
        self.aufrufe.append(("spiel", aktion))
        if aktion == "start":
            self.laeuft, self.marke = True, self.marke + 1
        else:
            self.laeuft = False
        return True

    def retroarch(self, befehl):
        self.aufrufe.append(("retroarch", befehl))
        return True

    def retroarch_laeuft(self):
        return self.retroarch_an

    def ton_setzen(self, ziel):
        self.aufrufe.append(("ton", ziel))
        return True, "senke-" + ziel

    def bestaetigungston(self, name):
        self.aufrufe.append(("piep", name))

    def geraet(self, aktion):
        self.aufrufe.append(("geraet", aktion))
        return True

    def richtlinie(self):
        self.aufrufe.append(("richtlinie",))
        return True

    def scraper(self):
        self.aufrufe.append(("scraper",))
        return True

    def ton_wache(self, ziel):
        self.aufrufe.append(("wache", ziel))
        return False

    def gong(self):
        self.aufrufe.append(("gong",))

    lautstaerke_wert = 40

    def lautstaerke(self, schritt=0, hoechstens=100):
        self.lautstaerke_wert = max(0, min(hoechstens, self.lautstaerke_wert + schritt))
        self.aufrufe.append(("lautstaerke", self.lautstaerke_wert))
        return self.lautstaerke_wert

    stumm = False

    def stumm_umschalten(self):
        self.stumm = not self.stumm
        self.aufrufe.append(("stumm", self.stumm))
        return self.stumm

    def lautstaerke_setzen(self, prozent):
        vorher, self.lautstaerke_wert = self.lautstaerke_wert, prozent
        self.aufrufe.append(("lautstaerke_setzen", prozent))
        return vorher


class Uhr:
    def __init__(self, jetzt):
        self.jetzt, self.mono = jetzt, 1000.0

    def __call__(self):
        return self.jetzt

    def monoton(self):
        return self.mono

    def weiter(self, sekunden):
        self.jetzt += timedelta(seconds=sekunden)
        self.mono += sekunden


def neuer_hub(ordner, uhr, system=None):
    return kern.Hub(ordner, system or Attrappe(), version="3.0.0-test", uhr=uhr,
                    monoton=uhr.monoton, uhr_sicher=lambda: True)


class TonAusgang(unittest.TestCase):
    """GRÜN = eingebaute Klinke - auch wenn eine USB-Soundkarte (Mikrofon) angeschlossen ist."""

    def test_klinke_ist_nie_die_usb_karte(self):
        from fernsehfranzi import system
        senken = ["alsa_output.usb-C-Media_USB_Audio_Device-00.analog-stereo",
                  "alsa_output.platform-3f00b840.mailbox.stereo-fallback",
                  "alsa_output.platform-3f902000.hdmi.hdmi-stereo"]
        self.assertEqual(system.waehle_ausgang(senken, "klinke"), [senken[1]])
        self.assertEqual(system.waehle_ausgang(senken, "hdmi"), [senken[2]])
        self.assertEqual(system.waehle_ausgang(senken[:1] + senken[2:], "klinke"), [])

    def test_wache_stellt_nach_usb_geraet_zurueck(self):
        from fernsehfranzi import system
        s = system.System()
        aufrufe = []
        senken = ["alsa_output.usb-Mikro-00.analog-stereo", "alsa_output.platform-3f00b840.mailbox.stereo-fallback"]
        s.ton_ausgaenge = lambda: senken
        s.ton_aktuell = lambda: senken[0]                       # USB-Gerät hat sich vorgedrängelt
        s._run = lambda befehl, **k: aufrufe.append(befehl) or type("E", (), {"returncode": 0, "stdout": ""})()
        self.assertTrue(s.ton_wache("klinke"))
        self.assertEqual(aufrufe, [["pactl", "set-default-sink", senken[1]]])
        s.ton_aktuell = lambda: senken[1]
        aufrufe.clear()
        self.assertFalse(s.ton_wache("klinke"))
        self.assertEqual(aufrufe, [])


class HubLogik(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-hub-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(MITTWOCH)
        self.hub = neuer_hub(self.ordner, self.uhr)

    def spiele(self, minuten, eingabe=True):
        for _ in range(int(minuten * 60 / 5)):
            self.uhr.weiter(5)
            if eingabe:
                self.hub.eingabe()
            self.hub.tick(5)

    def test_token_datei_nur_fuer_den_benutzer(self):
        pfad = os.path.join(self.ordner, "kiosk-token")
        self.assertEqual(os.stat(pfad).st_mode & 0o777, 0o600)
        with open(pfad) as f:
            self.assertEqual(f.read(), self.hub.token)

    def test_web_app_ohne_adresse_startet_nicht(self):
        ok, meldung = self.hub.starte("plex")
        self.assertFalse(ok)
        self.assertIn("noch nicht eingerichtet", meldung)

    def test_web_app_wird_zum_kiosk_auftrag(self):
        apps = self.hub.eltern_daten()["apps"]
        plex = next(a for a in apps if a["id"] == "plex")
        plex["start"] = "http://plex.example:32400/web/"
        self.hub.katalog_aendern(apps)
        ok, _ = self.hub.starte("plex")
        self.assertTrue(ok)
        auftraege, _ = self.hub.auftraege_nach(0)
        self.assertEqual(auftraege[-1]["art"], "oeffne")
        self.assertEqual(auftraege[-1]["url"], "http://plex.example:32400/web/")

    def test_retropie_zaehlt_und_endet_mit_speichern(self):
        system = self.hub.system
        self.assertTrue(self.hub.starte("games")[0])
        system.retroarch_an = True
        kern.time.sleep, alt = (lambda s: None), kern.time.sleep
        try:
            self.spiele(48)
        finally:
            kern.time.sleep = alt
        befehle = [a[1] for a in system.aufrufe if a[0] == "retroarch"]
        self.assertIn("SHOW_MSG Noch 10 Minuten!", befehle)
        self.assertIn("SHOW_MSG Noch 1 Minute!", befehle)
        self.assertLess(befehle.index("SAVE_STATE"), befehle.index("QUIT"))
        self.assertIn(("retropie", "stop"), system.aufrufe)
        ok, grund = self.hub.starte("games")
        self.assertFalse(ok)
        self.assertIn("aufgebraucht", grund)

    def test_leerlauf_zaehlt_nicht(self):
        self.hub.starte("spiel-snake")
        self.spiele(10, eingabe=False)
        self.assertEqual(self.hub.status()["rest_min"], 90 - 3)   # nur die ersten 3 min zählen

    def test_internet_ohne_eingabe_zurueck(self):
        self.hub.kiosk_ort("https://irgendwo.example/seite")
        self.assertEqual(self.hub.aktuell, "internet")
        self.spiele(11, eingabe=False)
        auftraege, _ = self.hub.auftraege_nach(0)
        self.assertIn("startseite", [a["art"] for a in auftraege])

    def test_plex_frei_zaehlt_nicht(self):
        apps = self.hub.eltern_daten()["apps"]
        plex = next(a for a in apps if a["id"] == "plex")
        plex["start"] = "http://plex.example:32400/web/"
        self.hub.katalog_aendern(apps)
        self.hub.kiosk_ort("http://plex.example:32400/web/index.html#!/media")
        self.assertEqual(self.hub.aktuell, "plex")
        self.spiele(30)
        self.assertEqual(self.hub.status()["rest_min"], 90)

    def test_pin_erst_am_tv_dann_nur_mit_alter_pin(self):
        self.assertFalse(self.hub.pin_festlegen("482913")[0])            # nicht vom LAN
        self.assertTrue(self.hub.pin_festlegen("482913", erster_start_am_tv=True)[0])
        self.assertFalse(self.hub.pin_festlegen("111111", alt="000000")[0])
        token, _ = self.hub.eltern_anmelden("482913")
        self.assertTrue(self.hub.sitzung_gueltig(token))
        self.uhr.weiter(16 * 60)
        self.assertFalse(self.hub.sitzung_gueltig(token), "Sitzung läuft nach 15 min ab")
        with open(os.path.join(self.ordner, "pin.json")) as f:
            self.assertNotIn("482913", f.read())

    def test_sperre_blockiert_alles(self):
        self.hub.sperren("Abendessen!")
        self.assertFalse(self.hub.starte("spiel-witz")[0])
        self.assertTrue(all(not k["frei"] for k in self.hub.kacheln()))
        self.assertEqual(self.hub.status()["gesperrt"]["text"], "Abendessen!")
        self.hub.entsperren()
        self.assertTrue(self.hub.starte("spiel-witz")[0])

    def test_einstellungen_werden_geprueft(self):
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"zeit": {"budget_min": {"schultag": -5, "frei": 10}}})
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"unbekannt": 1})
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"eltern_lan": {"aktiv": True, "port": 80}})
        self.hub.einstellungen_aendern({"zeit": {"budget_min": {"schultag": 60, "frei": 120}}})
        self.assertEqual(self.hub.status()["rest_min"], 60)
        neu = neuer_hub(self.ordner, self.uhr)        # überlebt einen Neustart
        self.assertEqual(neu.status()["rest_min"], 60)

    def test_browser_whitelist_mit_startadressen(self):
        apps = self.hub.eltern_daten()["apps"]
        plex = next(a for a in apps if a["id"] == "plex")
        plex["start"] = "http://198.51.100.7:32400/web/"
        plex["domains"] = ["plex.tv"]
        self.hub.katalog_aendern(apps)
        with open(os.path.join(self.ordner, "whitelist-richtlinie.json")) as f:
            wunsch = json.load(f)
        self.assertTrue(wunsch["aktiv"], "Vorgabe: Sperre an (strengster Zustand)")
        self.assertIn("198.51.100.7", wunsch["domains"])
        self.assertIn("plex.tv", wunsch["domains"])
        self.assertIn(("richtlinie",), self.hub.system.aufrufe)

    def test_bass_songs_nur_von_den_eltern(self):
        songs = [{"titel": "Seven Nation Army", "video": "https://www.youtube.com/watch?v=beispiel123",
                  "tab": "https://tabs.ultimate-guitar.com/tab/beispiel"}]
        self.hub.einstellungen_aendern({"bass": songs})
        self.assertEqual(self.hub.bass_songs(), [{"nr": 0, "titel": "Seven Nation Army", "arten": ["video", "tab"]}])
        self.assertEqual(kern.youtube_player("https://www.youtube.com/watch?v=wGpnT_nU724"),
                         "https://www.youtube-nocookie.com/embed/wGpnT_nU724?autoplay=1&rel=0&modestbranding=1&playsinline=1")
        self.assertEqual(kern.youtube_player("https://tabs.ultimate-guitar.com/x"), "https://tabs.ultimate-guitar.com/x")
        self.assertFalse(self.hub.bass_oeffne(0, "backing")[0])
        self.assertFalse(self.hub.bass_oeffne(5, "video")[0])
        self.assertTrue(self.hub.bass_oeffne(0, "video")[0])
        auftrag = self.hub.auftraege_nach(0)[0][-1]
        self.assertEqual((auftrag["art"], auftrag["url"]), ("oeffne", kern.youtube_player(songs[0]["video"])))
        self.assertIn("youtube-nocookie.com/embed/beispiel123", auftrag["url"])
        # Video aus der Bass-Ecke zählt nicht zur Zeit
        self.hub.kiosk_ort(auftrag["url"])
        self.assertEqual(self.hub.aktuell, "spiel-bass")
        with open(os.path.join(self.ordner, "whitelist-richtlinie.json")) as f:
            erlaubt = json.load(f)["domains"]
        for host in ("www.youtube-nocookie.com", "googlevideo.com", "ytimg.com"):
            self.assertIn(host, erlaubt)
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"bass": [{"titel": "x", "video": "javascript:alert(1)"}]})

    def test_gute_nacht_wird_einmal_ergaenzt(self):
        apps = [a for a in self.hub.eltern_daten()["apps"] if a["id"] != "gute-nacht"]
        kern.daten.schreibe_json(os.path.join(self.ordner, "apps.json"), apps)
        e = self.hub.einstellungen
        e.pop("katalog_ergaenzt", None)
        kern.daten.schreibe_json(os.path.join(self.ordner, "einstellungen.json"), e)
        neu = neuer_hub(self.ordner, self.uhr)
        self.assertIsNotNone(neu.app("gute-nacht"), "ergänzt")
        neu.katalog_aendern([a for a in neu.eltern_daten()["apps"] if a["id"] != "gute-nacht"])
        self.assertIsNone(neuer_hub(self.ordner, self.uhr).app("gute-nacht"), "gelöscht bleibt gelöscht")

    def test_domains_aus_dem_kiosk(self):
        self.hub.kiosk_domains([{"host": "cdn.klassenkiste.example", "anzahl": 3, "blockiert": 2},
                                {"host": "böse host", "anzahl": 1}])
        d = self.hub.eltern_daten()["domains"]
        self.assertEqual(d["cdn.klassenkiste.example"]["blockiert"], 2)
        self.assertNotIn("böse host", d)
        self.hub.domains_erlauben(["cdn.klassenkiste.example"])
        self.assertIn("cdn.klassenkiste.example", self.hub.einstellungen["whitelist"]["zusatz"])

    def test_falsche_kinderwelten_adresse_wird_korrigiert(self):
        apps = self.hub.eltern_daten()["apps"]
        next(a for a in apps if a["id"] == "kinderwelten")["start"] = "https://apps.familienfabrik.at/"
        kern.daten.schreibe_json(os.path.join(self.ordner, "apps.json"), apps)
        neu = neuer_hub(self.ordner, self.uhr)
        self.assertEqual(neu.app("kinderwelten")["start"], "https://app.familienfabrik.at/")
        with open(os.path.join(self.ordner, "apps.json")) as f:
            self.assertNotIn("apps.familienfabrik", f.read())

    def test_bonus(self):
        self.hub.starte("spiel-snake")
        self.spiele(90)
        self.assertFalse(self.hub.starte("spiel-snake")[0])
        self.hub.bonus("15")
        self.assertTrue(self.hub.starte("spiel-snake")[0])
        self.assertIn("mehr Zeit", self.hub.status()["meldung"]["text"])

    def test_lautstaerke_mit_hoechstwert(self):
        self.hub.einstellungen_aendern({"ton": {"ziel": "klinke", "max": 50}})
        self.assertEqual(self.hub.lautstaerke("lauter"), 45)
        self.assertEqual(self.hub.lautstaerke("lauter"), 50)
        self.assertEqual(self.hub.lautstaerke("lauter"), 50, "nie über den Höchstwert der Eltern")
        self.assertIn("höchste Stufe", self.hub.status()["meldung"]["text"])
        self.assertEqual(self.hub.lautstaerke("leiser"), 45)
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"ton": {"ziel": "klinke", "max": 5}})
        with self.assertRaises(ValueError):
            self.hub.lautstaerke("ganz laut")

    def test_bildschirmfoto_ueber_den_kiosk(self):
        import base64
        jpeg = b"\xff\xd8\xff\xe0" + b"x" * 100

        def kiosk():                                              # wie kiosk.py: Auftrag abholen, Bild liefern
            for _ in range(50):
                fotos = [a for a in self.hub.auftraege if a["art"] == "foto"]
                if fotos:
                    self.hub.foto_empfangen(fotos[-1]["foto"], base64.b64encode(jpeg).decode())
                    return
                time.sleep(0.02)
        threading.Thread(target=kiosk, daemon=True).start()
        bild, grund = self.hub.bildschirmfoto(warten_s=3)
        self.assertEqual((bild, grund), (jpeg, ""))
        self.assertIn("📷", self.hub.status()["meldung"]["text"], "das Kind sieht, dass geschaut wurde")
        self.assertEqual(self.hub.bildschirmfoto(warten_s=0.2), (None, "Der Fernseher antwortet gerade nicht."))
        self.assertFalse(self.hub.foto_empfangen(1, base64.b64encode(jpeg).decode()), "zu spätes Foto zählt nicht")
        threading.Timer(0.1, lambda: self.hub.foto_empfangen(3, "kein-bild!")).start()
        self.assertEqual(self.hub.bildschirmfoto(warten_s=3), (None, "Das Bild war kaputt."))
        self.hub.system.laeuft = True                             # RetroPie: kein Foto
        self.assertIn("Retro-Spiel", self.hub.bildschirmfoto(warten_s=0.2)[1])

    def test_bluetooth_nur_mit_gueltiger_adresse(self):
        aufrufe = []

        def bt(aktion, mac=""):
            aufrufe.append((aktion, mac))
            if aktion == "liste":
                return True, "1E:5B:5D:5D:BF:F8\tiPazzPort Bluetooth\tja\t80\nkaputt\n"
            if aktion == "suchen":
                return True, "1E:5B:5D:5D:BF:F8\tiPazzPort Bluetooth\nAA:BB:CC:DD:EE:FF\tKopfhörer\n"
            return aktion != "koppeln", "Failed to pair"
        self.hub.system.bluetooth = bt
        self.assertEqual(self.hub.bluetooth_liste(), [{"mac": "1E:5B:5D:5D:BF:F8", "name": "iPazzPort Bluetooth",
                                                       "verbunden": True, "akku": 80}])
        self.assertEqual(self.hub.bluetooth_aktion("suchen"), {"gefunden": [{"mac": "AA:BB:CC:DD:EE:FF", "name": "Kopfhörer"}]})
        self.assertEqual(len(self.hub.bluetooth_aktion("trennen", "aa:bb:cc:dd:ee:ff")["geraete"]), 1)
        self.assertIn(("trennen", "AA:BB:CC:DD:EE:FF"), aufrufe)
        with self.assertRaisesRegex(ValueError, "Kopplungsmodus"):
            self.hub.bluetooth_aktion("koppeln", "AA:BB:CC:DD:EE:FF")
        for aktion, mac in (("koppeln", "AA:BB:CC:DD:EE:FF; rm -rf /"), ("koppeln", ""), ("loeschen", "AA:BB:CC:DD:EE:FF")):
            vorher = len(aufrufe)
            with self.assertRaises(ValueError):
                self.hub.bluetooth_aktion(aktion, mac)
            self.assertEqual(len(aufrufe), vorher, "ungültig: der Helfer wird gar nicht aufgerufen")

    def test_bt_helfer_prueft_selbst(self):
        import subprocess
        helfer = os.path.join(REPO, "system", "bt-helfer")
        for argumente in (["koppeln", "AA:BB:CC:DD:EE:FF;id"], ["koppeln"], ["power", "off"], ["entfernen", "../x"]):
            ergebnis = subprocess.run(["/bin/bash", helfer] + argumente, capture_output=True, text=True,
                                      env={"PATH": "/nonexistent"})       # ohne bluetoothctl: darf gar nicht so weit kommen
            self.assertEqual(ergebnis.returncode, 2, argumente)
        with open(os.path.join(REPO, "system", "sudoers.d", "fernsehfranzi"), encoding="utf-8") as f:
            self.assertIn("/usr/local/lib/fernsehfranzi/bt-helfer", f.read())

    def test_stumm_taste(self):
        self.assertEqual(self.hub.lautstaerke("stumm"), 0)
        self.assertIn("Ton aus", self.hub.status()["meldung"]["text"])
        self.assertEqual(self.hub.lautstaerke("stumm"), 1)
        self.assertIn("Ton an", self.hub.status()["meldung"]["text"])

    def test_gong_bei_zeitwarnung(self):
        self.hub.starte("spiel-snake")
        self.spiele(81)
        self.assertIn(("gong",), self.hub.system.aufrufe)

    def test_ton_vorgabe_hdmi_und_wache(self):
        self.assertEqual(self.hub.status()["ton"], "hdmi")
        self.spiele(1)
        self.assertIn(("wache", "hdmi"), self.hub.system.aufrufe)

    def test_ton_merkt_sich_die_wahl(self):
        self.hub.ton_setzen("klinke")
        self.assertIn(("piep", "senke-klinke"), self.hub.system.aufrufe)
        self.assertEqual(neuer_hub(self.ordner, self.uhr).status()["ton"], "klinke")

    def test_wochenuebersicht(self):
        self.hub.starte("spiel-snake")
        self.spiele(20)
        self.uhr.weiter(24 * 3600)
        self.hub.tick(5)
        woche = self.hub.eltern_daten()["woche"]
        self.assertEqual(woche["2026-11-18"]["genutzt_min"], 20)


class Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ordner = tempfile.mkdtemp(prefix="ff-http-")
        cls.uhr = Uhr(MITTWOCH)
        cls.hub = neuer_hub(cls.ordner, cls.uhr)
        cls.hub.pin_festlegen("482913", erster_start_am_tv=True)
        web_ordner = os.path.join(REPO, "web")
        zeichnungen = os.path.join(cls.ordner, "zeichnungen")
        cls.kiosk = web.baue_server(web.KioskHandler, cls.hub, web_ordner, zeichnungen, ("127.0.0.1", 0))
        cls.lan = web.baue_server(web.LanHandler, cls.hub, web_ordner, zeichnungen, ("127.0.0.1", 0))
        for server in (cls.kiosk, cls.lan):
            threading.Thread(target=server.serve_forever, daemon=True).start()
        cls.basis = "http://127.0.0.1:%d" % cls.kiosk.server_address[1]
        cls.lan_basis = "http://127.0.0.1:%d" % cls.lan.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.kiosk.shutdown()
        cls.lan.shutdown()
        shutil.rmtree(cls.ordner, True)

    def hole(self, pfad, daten=None, kopf=None, basis=None):
        kopf = dict(kopf or {})
        if daten is not None:
            kopf["Content-Type"] = "application/json"
            daten = json.dumps(daten).encode()
        anfrage = urllib.request.Request((basis or self.basis) + pfad, data=daten, headers=kopf)
        try:
            with urllib.request.urlopen(anfrage, timeout=10) as antwort:
                return antwort.status, antwort.read(), dict(antwort.headers)
        except urllib.error.HTTPError as fehler:
            return fehler.code, fehler.read(), dict(fehler.headers)

    def token(self):
        return {"X-FF-Token": self.hub.token}

    def test_startseite_bekommt_token(self):
        code, inhalt, kopf = self.hole("/")
        self.assertEqual(code, 200)
        self.assertIn(self.hub.token.encode(), inhalt)
        self.assertIn("frame-ancestors 'none'", kopf.get("Content-Security-Policy", ""))

    def test_post_ohne_token_oder_fremde_herkunft(self):
        self.assertEqual(self.hole("/api/start", {"id": "spiel-witz"})[0], 403)
        kopf = dict(self.token(), Origin="http://plex.example:32400")
        self.assertEqual(self.hole("/api/start", {"id": "spiel-witz"}, kopf)[0], 403)
        self.assertEqual(self.hole("/api/start", {"id": "spiel-witz"}, self.token())[0], 200)

    def test_keine_wirkung_per_get(self):
        self.assertEqual(self.hole("/api/start")[0], 404)
        self.assertEqual(self.hole("/api/zurueck")[0], 404)

    def test_status_und_apps(self):
        status = json.loads(self.hole("/api/status")[1])
        self.assertEqual(status["version"], "3.0.0-test")
        apps = json.loads(self.hole("/api/apps")[1])["apps"]
        self.assertIn("spiel-snake", [a["id"] for a in apps])

    def test_pfad_ausbruch(self):
        for pfad in ("/../server/fernsehfranzi/kern.py", "/%2e%2e/VERSION", "/zeichnung/../pin.json"):
            self.assertEqual(self.hole(pfad)[0], 404, pfad)

    def test_eltern_mit_pin(self):
        self.assertEqual(self.hole("/api/eltern/daten")[0], 401)
        code, inhalt, _ = self.hole("/api/eltern/anmelden", {"pin": "482913"}, self.token())
        self.assertEqual(code, 200)
        eltern = {"X-FF-Eltern": json.loads(inhalt)["token"]}
        code, inhalt, _ = self.hole("/api/eltern/daten", kopf=eltern)
        self.assertEqual(code, 200)
        self.assertIn("regeln", json.loads(inhalt))
        code, inhalt, _ = self.hole("/api/eltern/whitelist?format=pihole", kopf=eltern)
        self.assertIn(b"Pi-hole", inhalt)

    def test_lan_ton_und_lautstaerke_mit_pin(self):
        self.assertEqual(self.hole("/api/eltern/lautstaerke", {"richtung": "lauter"}, basis=self.lan_basis)[0], 401)
        code, inhalt, _ = self.hole("/api/eltern/anmelden", {"pin": "482913"}, basis=self.lan_basis)
        eltern = {"X-FF-Eltern": json.loads(inhalt)["token"]}
        self.assertEqual(self.hole("/api/eltern/lautstaerke", {"richtung": "lauter"}, eltern, basis=self.lan_basis)[0], 200)
        self.assertEqual(self.hole("/api/eltern/ton", {"ziel": "klinke"}, eltern, basis=self.lan_basis)[0], 200)
        self.assertEqual(self.hole("/api/audio", {"ziel": "klinke"}, eltern, basis=self.lan_basis)[0], 404)

    def test_lan_nur_eltern(self):
        self.assertEqual(self.hole("/", basis=self.lan_basis)[0], 200)
        for pfad in ("/api/status", "/api/apps", "/index.html", "/js/start.js"):
            self.assertEqual(self.hole(pfad, basis=self.lan_basis)[0], 404, pfad)
        self.assertEqual(self.hole("/api/start", {"id": "spiel-witz"}, basis=self.lan_basis)[0], 404)
        # erste PIN gibt es im LAN nicht, Ändern nur mit alter PIN
        code, _, _ = self.hole("/api/eltern/pin", {"neu": "111111", "alt": "000000"}, basis=self.lan_basis)
        self.assertEqual(code, 403)
        code, _, _ = self.hole("/api/eltern/anmelden", {"pin": "482913"},
                               {"Origin": "http://boese.example"}, basis=self.lan_basis)
        self.assertEqual(code, 403)

    def test_kiosk_auftraege_nur_mit_token(self):
        self.assertEqual(self.hole("/api/kiosk/auftraege?nach=0")[0], 403)
        self.hole("/api/zurueck", {}, self.token())
        code, inhalt, _ = self.hole("/api/kiosk/auftraege?nach=0", kopf=self.token())
        self.assertIn("startseite", [a["art"] for a in json.loads(inhalt)["auftraege"]])


if __name__ == "__main__":
    unittest.main()
