"""5.2: Klang-Archiv - eigene Klänge je Erinnerung, Telegram-Kontakt, Nachrichten der Eltern und Schule."""
import io
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.request
import wave

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import klaenge, web  # noqa: E402
from test_v3_server import MITTWOCH, Uhr, neuer_hub  # noqa: E402


class Archiv(unittest.TestCase):
    def test_jeder_klang_ist_eine_kurze_wav(self):
        self.assertGreaterEqual(len(klaenge.ARCHIV), 12)
        for k in klaenge.ARCHIV:
            with wave.open(io.BytesIO(klaenge.erzeuge(k))) as w:
                dauer = w.getnframes() / w.getframerate()
                self.assertTrue(0.3 < dauer < 3.0, (k, dauer))
                self.assertEqual((w.getnchannels(), w.getsampwidth()), (1, 2))
        self.assertEqual(klaenge.erzeuge("vogel"), klaenge.erzeuge("vogel"), "immer gleich (kein Zufall)")
        self.assertIn("stumm", [k["id"] for k in klaenge.liste()])
        with self.assertRaises(ValueError):
            klaenge.erzeuge("../etc/passwd")


class ImHub(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-52-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(MITTWOCH)
        self.hub = neuer_hub(self.ordner, self.uhr)
        self.toene = lambda: [a for a in self.hub.system.aufrufe if a[0] == "gong"]

    def test_erinnerung_mit_klang(self):
        fam = dict(self.hub.familie.einstellungen(), erinnerungen=[
            {"zeit": "15:00", "text": "Zähne putzen!", "tage": [], "klang": "harfe"},
            {"zeit": "15:00", "text": "Leise!", "tage": [], "klang": "stumm"}])
        self.hub.einstellungen_aendern({"familie": fam})
        self.hub.familie._erinnerungen(self.hub.familie.einstellungen(), MITTWOCH, MITTWOCH.date().isoformat())
        self.assertIn(("gong", "harfe"), self.toene())
        self.assertIn(("gong", "stumm"), self.toene(), "stumm wird erst beim Abspielen geschluckt")
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"familie": dict(fam, erinnerungen=[{"zeit": "15:00", "text": "x", "klang": "laser"}])})

    def test_wiederholung_behaelt_den_klang(self):
        self.hub.familie.nachricht("Essen!", bleibt=True, klang="fanfare")
        self.hub.system.aufrufe.clear()
        self.hub.familie._wiederholt -= 10 * 60
        self.hub.familie._wiederholen()
        self.assertEqual(self.toene(), [("gong", "fanfare")])

    def test_eltern_nachricht_und_kontakt(self):
        self.hub.einstellungen_aendern({"familie": dict(self.hub.familie.einstellungen(), klang_nachricht="glocke")})
        self.assertEqual(self.hub.familie.einstellungen()["klang_nachricht"], "glocke")
        tg = {"aktiv": True, "token": "123:abc", "chats": [
            {"id": 7, "name": "Lena", "symbol": "🦄", "eltern": False, "darf_schreiben": True, "eigene_texte": False,
             "nur_freizeit": False, "medien": False, "klang": "vogel"}]}
        self.hub.einstellungen_aendern({"telegram": tg})
        self.assertEqual(self.hub.telegram.einstellungen()["chats"][0]["klang"], "vogel")
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"telegram": dict(tg, chats=[dict(tg["chats"][0], klang="quietsch")])})

    def test_schule_klaenge_pruefen(self):
        self.hub.einstellungen_aendern({"schule": {"klang": "xylophon", "klang_morgen": "spieluhr"}})
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"schule": {"klang": "nix"}})

    def test_am_fernseher_probehoeren(self):
        self.hub.klang_testen("ufo")
        self.assertEqual(self.toene(), [("gong", "ufo")])
        with self.assertRaises(ValueError):
            self.hub.klang_testen("stumm")
        self.assertIn("klaenge", self.hub.eltern_daten())

    def test_datei_ueber_die_eltern_seite(self):
        server = web.baue_server(web.LanHandler, self.hub, os.path.join(REPO, "web"), os.path.join(self.ordner, "z"), ("127.0.0.1", 0))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with urllib.request.urlopen("http://127.0.0.1:%d/api/klang?id=marimba" % server.server_address[1], timeout=5) as a:
            self.assertEqual(a.headers["Content-Type"], "audio/wav")
            self.assertTrue(a.read(4) == b"RIFF")


class EigeneKlaenge(unittest.TestCase):
    """6.0: eigene Klänge aus einem FileBrowser-Ordner der Eltern."""
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-60k-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(MITTWOCH))

    def test_pruefen(self):
        self.assertTrue(klaenge.gueltig("eigen:Hupe.mp3"))
        for falsch in ("eigen:../geheim.mp3", "eigen:", "eigen:bild.png", "eigen:" + "x" * 300 + ".mp3"):
            self.assertFalse(klaenge.gueltig(falsch), falsch)
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"klaenge": {"ordner": "http://kein-filebrowser.example/irgendwas"}})

    def test_liste_und_abspielen(self):
        from unittest import mock
        from fernsehfranzi import hoerbuch
        self.hub.einstellungen_aendern({"klaenge": {"ordner": "http://server:8080/share/AbCd1234"}})
        liste = {"titel": [{"name": "Hupe.mp3", "pfad": "Hupe.mp3"}, {"name": "Lied.flac", "pfad": "Lied.flac"},
                           {"name": "Video.mp4", "pfad": "Video.mp4"}]}

        class Antwort(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        with mock.patch.object(hoerbuch, "liste", return_value=liste):
            self.assertEqual([k["id"] for k in self.hub.klaenge_eigen()], ["eigen:Hupe.mp3", "eigen:Lied.flac"])
        with mock.patch("urllib.request.urlopen", return_value=Antwort(b"ID3" + b"0" * 100)) as auf:
            self.hub.klang_testen("eigen:Hupe.mp3")
            self.hub.klang_testen("eigen:Hupe.mp3")
            self.assertEqual(auf.call_count, 1, "einmal geladen, danach aus dem Zwischenspeicher")
        self.assertEqual(self.hub.system.aufrufe[-1][0], "gong_datei")
        with mock.patch("urllib.request.urlopen", return_value=Antwort(b"0" * (5 * 1024 * 1024))):
            self.hub.klang_testen("eigen:Lied.flac")             # 6.8.11: lange Klänge (5 MB) gehen jetzt
        self.assertEqual(self.hub.system.aufrufe[-1][0], "gong_datei")

        class Riesig(Antwort):                                    # mehr als 50 MB, ohne sie wirklich anzulegen
            def read(self, n=-1):
                return b"0" * n
        with mock.patch("urllib.request.urlopen", return_value=Riesig()):
            with self.assertRaisesRegex(ValueError, "zu groß"):
                self.hub.klang_testen("eigen:Hupe2.mp3")
        self.assertEqual(self.hub.system.aufrufe[-1], ("gong",), "geht der eigene nicht, kommt der Gong")


if __name__ == "__main__":
    unittest.main()
