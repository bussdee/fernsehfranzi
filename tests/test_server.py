"""server.py im eigenen Thread auf einem freien Port, in einer Kopie.

Systemaufrufe (systemctl, sudo, pactl, pw-play) werden ersetzt: Der Test startet nie
wirklich RetroPie und schaltet keinen Ton am Entwicklungsrechner.
"""
import base64
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACTL_SINKS = ("69\talsa_output.platform-3f00b840.mailbox.stereo-fallback\tPipeWire\ts16le 2ch 48000Hz\tSUSPENDED\n"
               "70\talsa_output.platform-3f902000.hdmi.hdmi-stereo\tPipeWire\ts32le 2ch 48000Hz\tSUSPENDED\n")
HDMI = "alsa_output.platform-3f902000.hdmi.hdmi-stereo"
KLINKE = "alsa_output.platform-3f00b840.mailbox.stereo-fallback"
# Kleinstes gültiges PNG (1×1 Pixel).
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAwS2OUAAAAABJRU5ErkJggg==")


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ordner = tempfile.mkdtemp(prefix="ff-server-")
        shutil.copy(os.path.join(REPO, "familyhub", "server.py"), cls.ordner)
        spec = importlib.util.spec_from_file_location("ff_server_test", os.path.join(cls.ordner, "server.py"))
        with open(os.path.join(cls.ordner, "VERSION"), "w") as f:
            f.write("9.8.7\n")
        cls.modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.modul)
        cls.aufrufe = []
        cls.startmarke = 0
        cls.antwort_code = 0

        class Ergebnis:
            def __init__(self, code, ausgabe=""):
                self.returncode, self.stdout, self.stderr = code, ausgabe, "fehler" if code else ""

        def falsches_run(befehl, *args, **kwargs):
            cls.aufrufe.append(list(befehl))
            if befehl[:2] == [cls.modul.SYSTEMCTL, "show"]:
                return Ergebnis(0, "ActiveState=inactive\nActiveEnterTimestampMonotonic=%d\n"
                                % cls.startmarke)
            if befehl[:2] == ["sudo", "-n"]:
                return Ergebnis(cls.antwort_code)
            if befehl[:3] == ["pactl", "list", "short"]:
                return Ergebnis(0, PACTL_SINKS)
            if befehl[:2] == ["pactl", "get-sink-volume"]:
                return Ergebnis(0, "Volume: front-left: 3932 /   6% / -73.31 dB,   front-right: 3932 /   6%\n")
            if befehl[0] == "wpctl":
                raise AssertionError("wpctl darf nicht mehr benutzt werden (stuerzt am Geraet ab)")
            return Ergebnis(0)

        cls.echtes_run = cls.modul.subprocess.run       # 4.1: danach zurücksetzen (es ist das globale subprocess-Modul)
        cls.modul.subprocess.run = falsches_run
        cls.modul.bestaetigungston = lambda sink: cls.aufrufe.append(["ton", sink])
        cls.httpd = cls.modul.ReusableThreadingHTTPServer(("127.0.0.1", 0), cls.modul.Handler)
        cls.basis = "http://127.0.0.1:%d" % cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.modul.subprocess.run = cls.echtes_run
        cls.httpd.shutdown()
        cls.httpd.server_close()
        for handler in list(cls.modul.log.handlers) + list(__import__("logging").getLogger().handlers):
            handler.close()
        shutil.rmtree(cls.ordner, ignore_errors=True)

    def hole(self, pfad, daten=None, origin=None):
        kopf = {"Content-Type": "application/json"} if daten is not None else {}
        if origin:
            kopf["Origin"] = origin
        anfrage = urllib.request.Request(self.basis + pfad, data=daten, headers=kopf)
        try:
            with urllib.request.urlopen(anfrage, timeout=5) as antwort:
                return antwort.status, antwort.read()
        except urllib.error.HTTPError as fehler:
            return fehler.code, fehler.read()

    def test_status(self):
        code, inhalt = self.hole("/status")
        self.assertEqual(code, 200)
        status = json.loads(inhalt)
        self.assertEqual(status["version"], "9.8.7")
        self.assertIs(status["running"], False)
        self.assertEqual(status["retropie_start"], 0)

    def test_startmarke_wird_gemeldet(self):
        type(self).startmarke = 123456789
        try:
            status = json.loads(self.hole("/status")[1])
        finally:
            type(self).startmarke = 0
        self.assertEqual(status["retropie_start"], 123456789)

    def test_status_abfrage_nicht_im_log(self):
        log = os.path.join(self.ordner, "logs", "server.log")
        for handler in self.modul.log.handlers + self.modul.logging.getLogger().handlers:
            handler.flush()
        def zaehle():
            with open(log) as datei:
                return datei.read().count('"GET /status')
        vorher = zaehle()
        self.hole("/status")
        self.hole("/status")
        for handler in self.modul.logging.getLogger().handlers:
            handler.flush()
        self.assertEqual(zaehle(), vorher)

    def test_retropie_start_ueber_sudo_regel(self):
        type(self).antwort_code = 0
        code, inhalt = self.hole("/api/retropie", b"{}", origin="null")
        self.assertEqual(code, 200, inhalt)
        self.assertIn(["sudo", "-n", "/usr/bin/systemctl", "start", "--no-block",
                       "fernsehfranzi-retropie.service"], self.aufrufe)

    def test_retropie_fehler_wird_gemeldet(self):
        type(self).antwort_code = 1
        try:
            code, inhalt = self.hole("/api/retropie", b"{}")
        finally:
            type(self).antwort_code = 0
        self.assertEqual(code, 500)
        self.assertIn("Mama oder Papa", json.loads(inhalt)["meldung"])

    def test_fremde_herkunft_abgewiesen(self):
        for pfad in ("/api/retropie", "/api/audio"):
            code, _ = self.hole(pfad, json.dumps({"ziel": "hdmi"}).encode(), origin="http://plex.example")
            self.assertEqual(code, 403, pfad)

    def test_keine_wirkung_per_get(self):
        self.assertEqual(self.hole("/games")[0], 404)
        self.assertEqual(self.hole("/api/retropie")[0], 404)
        self.assertEqual(self.hole("/api/audio?ziel=hdmi")[0], 404)

    def test_ton_umschalten_mit_anzeige(self):
        vorher = json.loads(self.hole("/status")[1])["ton_nummer"]
        code, inhalt = self.hole("/api/audio", json.dumps({"ziel": "hdmi"}).encode())
        self.assertEqual(code, 200, inhalt)
        self.assertIn(["pactl", "set-default-sink", HDMI], self.aufrufe)
        self.assertIn(["pactl", "set-sink-mute", HDMI, "0"], self.aufrufe)
        self.assertIn(["pactl", "set-sink-volume", HDMI, "50%"], self.aufrufe)   # 6 % war zu leise
        self.assertIn(["ton", HDMI], self.aufrufe)
        status = json.loads(self.hole("/status")[1])
        self.assertEqual((status["ton"], status["ton_nummer"]), ("hdmi", vorher + 1))
        code, _ = self.hole("/api/audio", json.dumps({"ziel": "klinke"}).encode(), origin="null")
        self.assertEqual(code, 200)
        self.assertIn(["pactl", "set-default-sink", KLINKE], self.aufrufe)

    def test_unbekannter_pfad(self):
        self.assertEqual(self.hole("/gibtsnicht")[0], 404)
        self.assertEqual(self.hole("/gibtsnicht", b"{}")[0], 404)

    def test_audio_ziel_wird_geprueft(self):
        code, inhalt = self.hole("/api/audio", json.dumps({"ziel": "lautsprecher"}).encode())
        self.assertEqual(code, 400)
        self.assertFalse(json.loads(inhalt)["ok"])
        self.assertEqual(self.hole("/api/audio", b"kein json")[0], 400)

    def test_zeichnung_speichern_auflisten_ausliefern(self):
        bild = "data:image/png;base64," + base64.b64encode(PNG).decode()
        code, inhalt = self.hole("/api/zeichnung", json.dumps({"bild": bild}).encode())
        self.assertEqual(code, 200, inhalt)
        datei = json.loads(inhalt)["datei"]
        code, inhalt = self.hole("/api/zeichnungen")
        self.assertIn(datei, [z["datei"] for z in json.loads(inhalt)["zeichnungen"]])
        code, inhalt = self.hole("/zeichnung/" + datei)
        self.assertEqual((code, inhalt), (200, PNG))

    def test_zeichnung_ungueltig(self):
        self.assertEqual(self.hole("/api/zeichnung", json.dumps({"bild": "data:text/plain;base64,AA=="}).encode())[0], 400)
        self.assertEqual(self.hole("/api/zeichnung", b"kein json")[0], 400)

    def test_zeichnung_kein_pfadausbruch(self):
        self.assertEqual(self.hole("/zeichnung/..%2F..%2Fserver.py")[0], 404)
        self.assertEqual(self.hole("/zeichnung/../server.py")[0], 404)


if __name__ == "__main__":
    unittest.main()
