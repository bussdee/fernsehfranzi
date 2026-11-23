"""4.0 Telegram: Nachrichten erlaubter Chats ans TV, unbekannte gemerkt, Antworten nur vorbereitet, Token nie zurück."""
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

from fernsehfranzi import telegram, web  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

TOKEN = "123456:TESTtoken"


class TelegramAttrappe(BaseHTTPRequestHandler):
    warteschlange, gesendet = [], []

    def log_message(self, *a):
        pass

    def do_POST(self):
        daten = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if not self.path.startswith("/bot%s/" % TOKEN):
            antwort = {"ok": False, "description": "Unauthorized"}
        elif self.path.endswith("/getUpdates"):
            neu = [u for u in TelegramAttrappe.warteschlange if u["update_id"] >= daten.get("offset", 0)]
            if not neu:
                time.sleep(0.2)
            antwort = {"ok": True, "result": neu}
        else:
            TelegramAttrappe.gesendet.append(daten)
            antwort = {"ok": True, "result": {}}
        inhalt = json.dumps(antwort).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(inhalt)))
        self.end_headers()
        self.wfile.write(inhalt)


class Telegram(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), TelegramAttrappe)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        alt, telegram.BASIS = telegram.BASIS, "http://127.0.0.1:%d" % self.server.server_address[1]
        self.addCleanup(setattr, telegram, "BASIS", alt)
        TelegramAttrappe.warteschlange, TelegramAttrappe.gesendet = [], []
        self.ordner = tempfile.mkdtemp(prefix="ff-tg-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(datetime(2026, 11, 18, 15, 0)))
        self.addCleanup(lambda: self.hub.einstellungen_aendern({"telegram": {"aktiv": False, "token": TOKEN}}))

    def einschalten(self):
        self.hub.einstellungen_aendern({"telegram": {"aktiv": True, "token": TOKEN, "chats": [{"id": 111, "name": "Papa"}]}})

    def warte(self, bedingung):
        for _ in range(60):
            if bedingung():
                return True
            time.sleep(0.1)
        return False

    def test_nachricht_erlaubter_chat_kommt_an_unbekannter_nicht(self):
        TelegramAttrappe.warteschlange = [
            {"update_id": 1, "message": {"chat": {"id": 111, "first_name": "Sebastian"}, "text": "Essen ist fertig!"}},
            {"update_id": 2, "message": {"chat": {"id": 999, "first_name": "Fremd"}, "text": "Hallo"}},
            {"update_id": 3, "message": {"chat": {"id": 111}, "text": "/start"}}]
        self.einschalten()
        self.assertTrue(self.warte(lambda: self.hub.telegram.unbekannt))
        meldungen = self.hub.familie.zustand["meldungen"]
        self.assertEqual([(m["quelle"], m["text"], m["chat"]) for m in meldungen], [("Papa", "Essen ist fertig!", 111)])
        self.assertEqual(self.hub.telegram.unbekannt[0]["id"], 999)
        self.assertEqual(self.hub.eltern_daten()["telegram_unbekannt"][0]["name"], "Fremd")

    def test_antworten_nur_vorbereitet_und_gebremst(self):
        self.einschalten()
        self.assertEqual(self.hub.telegram.senden("👍 Okay!", 111), ["Papa"])
        self.assertEqual(TelegramAttrappe.gesendet[-1]["chat_id"], 111)
        self.assertIn("👍 Okay!", TelegramAttrappe.gesendet[-1]["text"])
        with self.assertRaisesRegex(ValueError, "Einen Moment"):
            self.hub.telegram.senden("Komme gleich!")
        self.hub.telegram._gesendet.clear()
        self.assertEqual(self.hub.telegram.senden("  Ich bin\nim Garten  "), ["Papa"], "4.1: eigene Texte")
        self.assertEqual(TelegramAttrappe.gesendet[-1]["text"].split(": ", 1)[1], "Ich bin im Garten")
        self.hub.telegram._gesendet.clear()
        with self.assertRaisesRegex(ValueError, "300"):
            self.hub.telegram.senden("x" * 301)
        with self.assertRaisesRegex(ValueError, "leer"):
            self.hub.telegram.senden("   ")
        t = dict(self.hub.einstellungen["telegram"], eigene_texte=False)
        self.hub.einstellungen_aendern({"telegram": t})
        with self.assertRaisesRegex(ValueError, "vorbereiteten"):
            self.hub.telegram.senden("irgendwas Freies")

    def test_token_nie_zurueck_an_den_browser(self):
        self.einschalten()
        einst = self.hub.eltern_daten()["einstellungen"]["telegram"]
        self.assertEqual(einst["token"], telegram.VERSTECKT)
        einst["chats"].append({"id": 222, "name": "Mama"})
        self.hub.einstellungen_aendern({"telegram": einst})              # Eltern-Seite speichert mit „••••“
        self.assertEqual(self.hub.einstellungen["telegram"]["token"], TOKEN, "alter Token bleibt")
        with self.assertRaises(ValueError):
            self.hub.einstellungen_aendern({"telegram": {"aktiv": True, "token": "kaputt"}})

    # ------------------------------------------------------------ 4.3: Kontakte mit Grenzen, Verlauf
    def freundin(self, **werte):
        lena = {"id": 333, "name": "Lena", "symbol": "🦄", "eltern": False, "darf_schreiben": False,
                "eigene_texte": False, "nur_freizeit": True}
        lena.update(werte)
        self.hub.einstellungen_aendern({"telegram": {"aktiv": True, "token": TOKEN, "chats": [
            {"id": 111, "name": "Papa"}, lena]}})

    def test_alte_kontakte_sind_eltern_und_neue_streng(self):
        self.einschalten()
        papa = self.hub.telegram.einstellungen()["chats"][0]
        self.assertTrue(papa["eltern"] and papa["darf_schreiben"] and papa["eigene_texte"])
        self.assertFalse(papa["nur_freizeit"])
        self.assertTrue(self.hub.eltern_daten()["einstellungen"]["telegram"]["chats"][0]["eltern"])
        with self.assertRaisesRegex(ValueError, "unbekannte Felder"):
            self.hub.einstellungen_aendern({"telegram": {"aktiv": True, "token": TOKEN,
                                                         "chats": [{"id": 1, "name": "X", "admin": True}]}})

    def test_absender_mit_symbol_und_verlauf(self):
        self.freundin()
        self.hub.telegram.empfangen({"chat": {"id": 333}, "text": "Kommst du raus?"})
        m = self.hub.familie.zustand["meldungen"][-1]
        self.assertEqual((m["quelle"], m["symbol"], m["chat"]), ("Lena", "🦄", 333))
        self.assertEqual(self.hub.status()["meldungen"][-1]["symbol"], "🦄")
        verlauf = self.hub.eltern_daten()["telegram_verlauf"]
        self.assertEqual(verlauf[0]["name"], "Lena")
        self.assertEqual(verlauf[0]["nachrichten"][-1]["richtung"], "rein")

    def test_freundin_wartet_in_der_sperrzeit(self):
        self.freundin()
        self.hub.uhr.jetzt = datetime(2026, 11, 18, 21, 0)                 # Nachtruhe (Vorgabe)
        self.hub.telegram.empfangen({"chat": {"id": 333}, "text": "Gute Nacht!"})
        self.hub.telegram.empfangen({"chat": {"id": 111}, "text": "Schlaf gut"})
        quellen = [m["quelle"] for m in self.hub.familie.zustand["meldungen"]]
        self.assertEqual(quellen, ["Papa"], "Eltern immer, die Freundin wartet")
        self.assertTrue(self.hub.eltern_daten()["telegram_verlauf"][0]["nachrichten"][-1].get("wartet") or
                        self.hub.eltern_daten()["telegram_verlauf"][1]["nachrichten"][-1].get("wartet"))
        self.hub.telegram.tick()
        self.assertEqual(len(self.hub.familie.zustand["meldungen"]), 1, "in der Sperrzeit bleibt sie liegen")
        self.hub.uhr.jetzt = datetime(2026, 11, 19, 15, 0)
        self.hub.telegram.tick()
        self.assertEqual([m["quelle"] for m in self.hub.familie.zustand["meldungen"]], ["Papa", "Lena"])

    def test_kind_schreibt_nur_freigegebenen_kontakten(self):
        self.freundin()
        tv = self.hub.telegram.fuer_tv()
        self.assertEqual([k["name"] for k in tv["kontakte"]], ["Papa"], "Lena noch nicht zum Schreiben freigegeben")
        with self.assertRaisesRegex(ValueError, "nicht schreiben"):
            self.hub.telegram.senden("👍 Okay!", 333)
        self.freundin(darf_schreiben=True)
        self.assertEqual(self.hub.telegram.senden("👍 Okay!", 333), ["Lena"])
        self.assertEqual(TelegramAttrappe.gesendet[-1]["chat_id"], 333)
        self.hub.telegram._gesendet.clear()
        with self.assertRaisesRegex(ValueError, "vorbereiteten"):
            self.hub.telegram.senden("Treffen wir uns?", 333)           # eigene Texte an Lena aus
        self.freundin(darf_schreiben=True, eigene_texte=True)
        self.assertEqual(self.hub.telegram.senden("Treffen wir uns?", 333), ["Lena"])
        self.hub.telegram._gesendet.clear()
        self.assertEqual(self.hub.telegram.senden("Komme gleich!"), ["Papa"], "ohne Empfänger: nur an die Eltern")
        raus = [n for v in self.hub.eltern_daten()["telegram_verlauf"] if v["name"] == "Lena" for n in v["nachrichten"]]
        self.assertEqual([n["text"] for n in raus if n["richtung"] == "raus"], ["👍 Okay!", "Treffen wir uns?"])
        self.assertTrue(self.hub.telegram.fuer_tv()["kontakte"][1]["eigene_texte"])

    @unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
    @unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
    def test_eigenen_text_am_fernseher_tippen(self):
        self.einschalten()
        server = web.baue_server(web.KioskHandler, self.hub, os.path.join(REPO, "web"),
                                 os.path.join(self.ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            seite = browser.new_page(viewport={"width": 1600, "height": 900})
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            seite.goto("http://127.0.0.1:8765/")
            seite.click(".kachel[data-id=spiel-nachrichten]")
            seite.wait_for_selector(".nachricht.schreiben.gewaehlt")
            seite.keyboard.press("Enter")                                   # „Nachricht schreiben“
            seite.wait_for_selector("text=⌨️ Eigenen Text tippen")
            seite.keyboard.press("Enter")                                   # erster Eintrag: eigener Text
            seite.wait_for_selector(".nachricht.tippen")
            seite.keyboard.type("Hallo Papa!x")
            seite.keyboard.press("Backspace")
            for pfeil in ("ArrowLeft", "ArrowUp", "ArrowDown"):              # Pfeile tun nichts, kein Cursor
                seite.keyboard.press(pfeil)
            self.assertEqual(seite.inner_text(".nachricht.tippen .nachricht-text span"), "Hallo Papa!")
            seite.keyboard.press("Enter")
            self.assertTrue(self.warte(lambda: TelegramAttrappe.gesendet and "Hallo Papa!" in TelegramAttrappe.gesendet[-1]["text"]))
            seite.wait_for_selector(".nachricht.tippen", state="detached")
            self.assertEqual(fehler, [])
            browser.close()
    @unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
    @unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
    def test_an_wen_am_fernseher(self):
        """4.3: „Nachricht schreiben“ fragt nach dem Empfänger; an Lena nur vorbereitete Antworten."""
        self.freundin(darf_schreiben=True)
        server = web.baue_server(web.KioskHandler, self.hub, os.path.join(REPO, "web"),
                                 os.path.join(self.ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.hub.telegram.empfangen({"chat": {"id": 333}, "text": "Hallo!"})
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            seite = browser.new_page(viewport={"width": 1600, "height": 900})
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            seite.goto("http://127.0.0.1:8765/")
            seite.wait_for_selector("#meldungen")
            self.assertIn("🦄 Lena:", seite.inner_text("#meldungen"))
            seite.click("#meldungen button")
            seite.click(".kachel[data-id=spiel-nachrichten]")
            seite.wait_for_selector(".nachricht.schreiben.gewaehlt")
            self.assertIn("🦄 Lena", seite.inner_text(".nachrichten-liste"))
            seite.keyboard.press("Enter")
            seite.wait_for_selector("text=An wen?")
            seite.keyboard.press("ArrowDown")
            seite.keyboard.press("Enter")
            seite.wait_for_selector("text=An 🦄 Lena")
            self.assertNotIn("Eigenen Text", seite.inner_text(".nachrichten-liste"))
            seite.keyboard.press("Enter")                                   # „👍 Okay!“
            self.assertTrue(self.warte(lambda: any(g.get("chat_id") == 333 for g in TelegramAttrappe.gesendet)))
            self.assertTrue(self.warte(lambda: any(g.get("chat_id") == 111 and "Lena" in g.get("text", "") for g in TelegramAttrappe.gesendet)),
                            "4.4: Papa bekommt eine Meldung, wenn das Kind einem Freund schreibt")
            self.assertEqual(fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()
