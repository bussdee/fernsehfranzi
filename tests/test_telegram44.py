"""4.4 Telegram: Fotos/Sprache/Videos ans TV, Befehle und Meldungen für die Eltern, Tagesbericht, Album,
Speicherplatz des Kindes, Bilder teilen, Fotoalbum."""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import telegram  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

TOKEN = "123456:TESTtoken"
JPEG = b"\xff\xd8\xff\xe0" + b"x" * 2000
PNG = b"\x89PNG\r\n\x1a\n" + b"y" * 3000


class Attrappe(BaseHTTPRequestHandler):
    gesendet, bilder, dateien = [], [], {}

    def log_message(self, *a):
        pass

    def antworte(self, daten, roh=None):
        inhalt = roh if roh is not None else json.dumps(daten).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(inhalt)))
        self.end_headers()
        self.wfile.write(inhalt)

    def do_GET(self):
        weg = self.path.split("/file/bot%s/" % TOKEN, 1)
        if len(weg) == 2 and weg[1] in Attrappe.dateien:
            return self.antworte(None, Attrappe.dateien[weg[1]])
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        roh = self.rfile.read(int(self.headers["Content-Length"]))
        if self.path.endswith("/sendPhoto"):
            Attrappe.bilder.append(roh)
            return self.antworte({"ok": True, "result": {}})
        daten = json.loads(roh)
        if self.path.endswith("/getUpdates"):
            time.sleep(0.2)
            return self.antworte({"ok": True, "result": []})
        if self.path.endswith("/getFile"):
            weg = {"F1": "photos/f1.jpg", "V1": "voice/v1.oga", "GROSS": "photos/riesig.jpg"}.get(daten["file_id"])
            groesse = 30_000_000 if daten["file_id"] == "GROSS" else 100
            return self.antworte({"ok": True, "result": {"file_path": weg, "file_size": groesse}})
        Attrappe.gesendet.append(daten)
        return self.antworte({"ok": True, "result": {}})


class Telegram44(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Attrappe)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        alt, telegram.BASIS = telegram.BASIS, "http://127.0.0.1:%d" % self.server.server_address[1]
        self.addCleanup(setattr, telegram, "BASIS", alt)
        Attrappe.gesendet, Attrappe.bilder = [], []
        Attrappe.dateien = {"photos/f1.jpg": JPEG, "voice/v1.oga": b"OggS" + b"z" * 500}
        self.ordner = tempfile.mkdtemp(prefix="ff-tg44-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(datetime(2026, 11, 18, 15, 0))
        self.hub = neuer_hub(self.ordner, self.uhr)
        self.hub.einstellungen_aendern({"telegram": {"aktiv": True, "token": TOKEN, "chats": [
            {"id": 111, "name": "Papa"},
            {"id": 333, "name": "Lena", "symbol": "🦄", "eltern": False, "darf_schreiben": True, "eigene_texte": False,
             "nur_freizeit": False, "medien": False}]}})
        self.addCleanup(lambda: self.hub.einstellungen_aendern({"telegram": {"aktiv": False, "token": TOKEN}}))
        self.tg = self.hub.telegram

    def warte(self, bedingung):
        for _ in range(50):
            if bedingung():
                return True
            time.sleep(0.05)
        return False

    def test_foto_und_sprache_kommen_ans_tv(self):
        self.tg.empfangen({"chat": {"id": 111}, "photo": [{"file_id": "F0", "width": 90, "height": 90, "file_size": 10},
                                                           {"file_id": "F1", "width": 1280, "height": 960, "file_size": 100}],
                           "caption": "Schau mal!"})
        m = self.hub.familie.zustand["meldungen"][-1]
        self.assertEqual((m["text"], m["medium"]["art"]), ("Schau mal!", "foto"))
        pfad = self.tg.medium_pfad(m["medium"]["datei"])
        with open(pfad, "rb") as f:
            self.assertEqual(f.read(), JPEG)
        self.tg.empfangen({"chat": {"id": 111}, "voice": {"file_id": "V1", "file_size": 504}})
        m = self.hub.familie.zustand["meldungen"][-1]
        self.assertEqual(m["medium"]["art"], "sprache")
        self.assertIn("Sprachnachricht", m["text"])
        self.assertEqual(self.hub.status()["meldungen"][-1]["medium"]["art"], "sprache")
        self.assertIsNone(self.tg.medium_pfad("../einstellungen.json"))

    def test_freundin_ohne_medienrecht_nur_text_und_zu_gross(self):
        self.tg.empfangen({"chat": {"id": 333}, "photo": [{"file_id": "F1", "width": 100, "height": 100, "file_size": 100}],
                           "caption": "Hallo"})
        m = self.hub.familie.zustand["meldungen"][-1]
        self.assertEqual((m["text"], m["medium"]), ("Hallo", None))
        self.tg.empfangen({"chat": {"id": 333}, "photo": [{"file_id": "F1", "width": 100, "height": 100, "file_size": 100}]})
        self.assertEqual(len(self.hub.familie.zustand["meldungen"]), 1, "ohne Recht und ohne Text: nichts")
        self.tg.empfangen({"chat": {"id": 111}, "photo": [{"file_id": "GROSS", "width": 100, "height": 100, "file_size": 100}],
                           "caption": "Riesig"})
        self.assertIsNone(self.hub.familie.zustand["meldungen"][-1]["medium"], "zu groß: nur der Text")

    def test_aufraeumen_nach_sieben_tagen(self):
        self.tg.empfangen({"chat": {"id": 111}, "photo": [{"file_id": "F1", "width": 100, "height": 100, "file_size": 100}]})
        name = self.hub.familie.zustand["meldungen"][-1]["medium"]["datei"]
        self.assertEqual(self.tg.aufraeumen(time.time() + 6 * 86400), 0)
        self.assertEqual(self.tg.aufraeumen(time.time() + 8 * 86400), 1)
        self.assertIsNone(self.tg.medium_pfad(name))

    def test_befehle_nur_von_eltern(self):
        self.tg.empfangen({"chat": {"id": 333}, "text": "/zeit frei"})
        self.assertFalse(self.hub.konto.zustand.get("ohne_limit"), "Freunde können nichts steuern")
        self.tg.empfangen({"chat": {"id": 111}, "text": "/status"})
        self.assertTrue(self.warte(lambda: any("Übrig heute" in g.get("text", "") for g in Attrappe.gesendet)))
        self.tg.empfangen({"chat": {"id": 111}, "text": "/zeit 30"})
        self.assertTrue(self.warte(lambda: any("Erledigt" in g.get("text", "") for g in Attrappe.gesendet)))
        self.tg.empfangen({"chat": {"id": 111}, "text": "/sperren Essen!"})
        self.assertEqual(self.hub.gesperrt["text"], "Essen!")
        self.tg.empfangen({"chat": {"id": 111}, "text": "/freigeben"})
        self.assertIsNone(self.hub.gesperrt)
        self.tg.empfangen({"chat": {"id": 111}, "text": "/quatsch"})
        self.assertTrue(self.warte(lambda: any("kenne ich nicht" in g.get("text", "") for g in Attrappe.gesendet)))
        self.assertEqual(len(self.hub.familie.zustand["meldungen"]), 0, "Befehle erscheinen nicht am Fernseher")

    def test_meldungen_an_eltern_abschaltbar_und_bericht(self):
        self.tg.empfangen({"chat": {"id": 333}, "text": "Kommst du raus?"})
        self.assertTrue(self.warte(lambda: any(g["chat_id"] == 111 and "Lena" in g["text"] for g in Attrappe.gesendet)))
        self.hub.familie.meldungen_gesehen([self.hub.familie.zustand["meldungen"][-1]["nr"]])
        einst = self.hub.eltern_daten()["einstellungen"]["telegram"]
        einst["chats"][0]["meldungen"] = {"freunde": False}
        self.hub.einstellungen_aendern({"telegram": einst})
        Attrappe.gesendet.clear()
        self.tg.empfangen({"chat": {"id": 333}, "text": "Noch was"})
        time.sleep(0.3)
        self.assertFalse(any(g["chat_id"] == 111 for g in Attrappe.gesendet), "abgeschaltet")
        self.uhr.jetzt = datetime(2026, 11, 18, 19, 31)
        self.tg.tick()
        self.assertTrue(self.warte(lambda: any("Tagesbericht" in g.get("text", "") for g in Attrappe.gesendet)))
        anzahl = len(Attrappe.gesendet)
        self.tg.tick()
        time.sleep(0.2)
        self.assertEqual(len(Attrappe.gesendet), anzahl, "nur einmal am Tag")
        with self.assertRaises(ValueError):
            einst["chats"][0]["meldungen"] = {"gibtsnicht": True}
            self.hub.einstellungen_aendern({"telegram": einst})

    def test_gelesen_an_eltern(self):
        self.tg.empfangen({"chat": {"id": 111}, "text": "Essen ist fertig"})
        Attrappe.gesendet.clear()
        self.hub.familie.meldungen_gesehen([self.hub.familie.zustand["meldungen"][-1]["nr"]])
        self.assertTrue(self.warte(lambda: any("gelesen" in g.get("text", "") for g in Attrappe.gesendet)))

    def test_album_speicherplatz_teilen(self):
        self.tg.empfangen({"chat": {"id": 111}, "photo": [{"file_id": "F1", "width": 100, "height": 100, "file_size": 100}]})
        datei = self.hub.familie.zustand["meldungen"][-1]["medium"]["datei"]
        name = self.hub.album_uebernehmen(datei)
        self.assertEqual(self.hub.album_liste()[0]["datei"], name)
        self.assertEqual(self.hub.bild_teilen("album", name, 333), "Lena")
        self.assertTrue(Attrappe.bilder and b"form-data" in Attrappe.bilder[-1] and JPEG in Attrappe.bilder[-1])
        with self.assertRaisesRegex(ValueError, "nicht schreiben"):
            self.hub.bild_teilen("album", name, 999)
        # Speicher voll: nichts Neues, erst löschen
        os.makedirs(os.path.join(self.ordner, "zeichnungen"), exist_ok=True)
        with open(os.path.join(self.ordner, "zeichnungen", "zeichnung-20261118-150000.png"), "wb") as f:
            f.write(PNG * 4000)                                   # ~12 MB
        self.hub.einstellungen_aendern({"speicher": {"limit_mb": 10}})
        self.assertTrue(self.hub.speicher_status()["voll"])
        with self.assertRaisesRegex(ValueError, "voll"):
            self.hub.album_uebernehmen(datei)
        self.hub.kind_datei_loeschen("zeichnung", "zeichnung-20261118-150000.png")
        self.assertFalse(self.hub.speicher_status()["voll"])
        self.hub.kind_datei_loeschen("album", name)
        self.assertEqual(self.hub.album_liste(), [])
        with self.assertRaises(ValueError):
            self.hub.kind_datei_loeschen("zeichnung", "../einstellungen.json")
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"speicher": {"limit_mb": 1}})

    def test_fotoalbum_kind_waehlt_eltern_erlauben(self):
        with self.assertRaisesRegex(ValueError, "nicht eingeschaltet"):
            self.hub.fotoalbum_kind({"bildschirmschoner": True})
        self.hub.einstellungen_aendern({"fotoalbum": {"erlaubt": True, "ordner": "http://server:8080/share/AbCd1234"}})
        f = self.hub.fotoalbum_kind({"bildschirmschoner": True, "auswahl": ["ordner:Urlaub/strand.jpg", "album:a1.jpg"]})
        self.assertTrue(f["bildschirmschoner"])
        self.assertEqual(len(f["auswahl"]), 2)
        with self.assertRaises(ValueError):
            self.hub.fotoalbum_kind({"auswahl": ["boese:../x"]})
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"fotoalbum": {"erlaubt": True, "ordner": "http://kein-freigabelink"}})

    def test_sperrzeit_eltern_leise_freunde_nur_gezaehlt(self):
        """4.4 (Wunsch der Eltern): Eltern-Nachrichten kommen in Sperrzeiten an und sind beantwortbar, aber ohne Ton; Nachrichten
        von Freunden zählen nur und sind erst nach der Sperrzeit lesbar und beantwortbar."""
        einst = self.hub.eltern_daten()["einstellungen"]["telegram"]
        einst["chats"][1].update(nur_freizeit=True)
        self.hub.einstellungen_aendern({"telegram": einst})
        self.uhr.jetzt = datetime(2026, 11, 18, 21, 0)              # Nachtruhe
        gong_vorher = len([a for a in self.hub.system.aufrufe if a[0] == "gong"])
        self.tg.empfangen({"chat": {"id": 111}, "text": "Schlaf gut!"})
        self.tg.empfangen({"chat": {"id": 333}, "text": "Bist du noch wach?"})
        self.assertEqual(len([a for a in self.hub.system.aufrufe if a[0] == "gong"]), gong_vorher, "kein Ton in der Sperrzeit")
        s = self.hub.status()
        self.assertEqual([m["quelle"] for m in s["meldungen"]], ["Papa"], "Eltern sichtbar")
        self.assertEqual(s["freunde_spaeter"], 1, "Freundin nur gezählt")
        self.assertEqual([k["name"] for k in self.tg.fuer_tv()["kontakte"]], ["Papa"], "Freundin in der Sperrzeit nicht anschreibbar")
        with self.assertRaisesRegex(ValueError, "nicht schreiben"):
            self.tg.senden("👍 Okay!", 333)
        self.assertEqual(self.tg.senden("👍 Okay!", 111), ["Papa"], "Eltern antworten geht")
        self.uhr.jetzt = datetime(2026, 11, 19, 15, 0)
        self.tg.tick()
        s = self.hub.status()
        self.assertEqual(s["freunde_spaeter"], 0)
        self.assertIn("Lena", [m["quelle"] for m in s["meldungen"]])
        # Schalter aus: auch in der Sperrzeit mit Ton
        einst = self.hub.eltern_daten()["einstellungen"]["telegram"]
        einst["sperrzeit_still"] = False
        self.hub.einstellungen_aendern({"telegram": einst})
        self.uhr.jetzt = datetime(2026, 11, 19, 21, 0)
        self.tg.empfangen({"chat": {"id": 111}, "text": "Licht aus"})
        self.assertGreater(len([a for a in self.hub.system.aufrufe if a[0] == "gong"]), gong_vorher)


if __name__ == "__main__":
    unittest.main()
