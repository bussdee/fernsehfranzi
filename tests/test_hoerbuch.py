"""3.3 Hörbücher: FileBrowser-Freigabe, Durchreichen mit Range, Sleep-Timer, Schlafenszeit - und der Player im Browser."""
import io
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import threading
import unittest
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import hoerbuch, katalog, web  # noqa: E402
from test_v3_server import MITTWOCH, Uhr, neuer_hub  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

KENNUNG = "AbCd1234"


def wav(sekunden=20, rate=8000):
    """Kurzes stilles WAV (reicht zum Abspielen im Testbrowser)."""
    daten = b"\x00\x00" * int(sekunden * rate)
    kopf = b"RIFF" + struct.pack("<I", 36 + len(daten)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    return kopf + b"data" + struct.pack("<I", len(daten)) + daten


# 1×1-Pixel-PNG als Cover
PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c63f8cfc0f01f0005000201a5f5d2f30000000049454e44ae426082")

# Ordnerbaum der Attrappe: Ordner = dict, Datei = bytes
BAUM = {
    "Bibi Blocksberg": {"Folge 10.wav": wav(), "Folge 2.wav": wav(), "Folge 1.wav": wav(), "bild.png": PNG, "cover.png": PNG},
    "Die drei ??? Kids": {"01 Teil Eins.wav": wav()},
    "Einzeln.wav": wav(),
    ".versteckt": {},
}


def finde(pfad):
    knoten = BAUM
    for teil in [t for t in pfad.split("/") if t]:
        if not isinstance(knoten, dict) or teil not in knoten:
            return None
        knoten = knoten[teil]
    return knoten


class FileBrowserAttrappe(BaseHTTPRequestHandler):
    """Öffentliche Freigabe-Schnittstelle von FileBrowser 2.x (nur das, was der Fernseher braucht)."""
    anfragen = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        FileBrowserAttrappe.anfragen.append((self.path, self.headers.get("Range")))
        pfad = unquote(self.path.split("?")[0])
        m = re.match(r"^/api/public/(share|dl)/%s(/.*)?$" % KENNUNG, pfad)
        knoten = finde(m.group(2) or "") if m else None
        if knoten is None:
            self.send_response(404)
            self.end_headers()
            return
        if m.group(1) == "share":
            items = [{"name": n, "isDir": isinstance(v, dict), "size": 0 if isinstance(v, dict) else len(v)}
                     for n, v in knoten.items()]
            inhalt = json.dumps({"isDir": True, "items": items}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(inhalt)))
            self.end_headers()
            self.wfile.write(inhalt)
            return
        bereich = re.match(r"bytes=(\d+)-(\d*)", self.headers.get("Range") or "")
        if bereich:
            von = int(bereich.group(1))
            bis = int(bereich.group(2)) if bereich.group(2) else len(knoten) - 1
            teil = knoten[von:bis + 1]
            self.send_response(206)
            self.send_header("Content-Range", "bytes %d-%d/%d" % (von, von + len(teil) - 1, len(knoten)))
        else:
            teil = knoten
            self.send_response(200)
        self.send_header("Content-Type", "image/png" if pfad.endswith(".png") else "audio/wav")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(teil)))
        self.end_headers()
        self.wfile.write(teil)


def starte_attrappe():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FileBrowserAttrappe)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, "http://127.0.0.1:%d/share/%s" % (server.server_address[1], KENNUNG)


def medientaste(seite, taste):
    """Playwright kennt die Medientasten nicht - am Gerät kommen sie über uinput (KEY_PLAY -> MediaPlay)."""
    seite.evaluate("t => document.dispatchEvent(new KeyboardEvent('keydown', {key: t, bubbles: true}))", taste)


def hoerbuch_app(start):
    """3.4: die Gute-Nacht-App (Hörbuch-Player, frei, in allen Sperrzeiten erlaubt)."""
    return {"id": "gute-nacht", "name": "Gute Nacht", "typ": "hoerbuch", "start": start, "zeit": "frei",
            "sperr_erlaubt": "alle", "eingabe": "tasten", "domains": [], "aktiv": True, "symbol": "mond", "reihenfolge": 5}


class Freigabe(unittest.TestCase):
    def test_link_pruefen(self):
        self.assertIsNone(hoerbuch.pruefe_freigabe("http://server:8080/share/AbCd1234"))
        self.assertIsNone(hoerbuch.pruefe_freigabe("http://server:8080/files/share/AbCd1234/Unterordner"))
        self.assertIsNotNone(hoerbuch.pruefe_freigabe("http://server:32400/web/"))
        self.assertIsNotNone(hoerbuch.pruefe_freigabe("file:///share/AbCd1234"))

    def test_pfad_bleibt_in_der_freigabe(self):
        self.assertEqual(hoerbuch.sauberer_pfad("/a//b/./c/"), "a/b/c")
        with self.assertRaises(hoerbuch.HoerbuchFehler):
            hoerbuch.sauberer_pfad("a/../../etc")

    def test_liste_sortiert_natuerlich_und_nur_audio(self):
        antwort = {"items": [{"name": "Folge 10.mp3", "isDir": False}, {"name": "Folge 2.mp3", "isDir": False},
                             {"name": "cover.jpg", "isDir": False}, {"name": "CD 2", "isDir": True},
                             {"name": ".DS_Store", "isDir": False}]}
        gesehen = []

        def oeffne(anfrage, timeout):
            gesehen.append(anfrage.full_url)
            return io.BytesIO(json.dumps(antwort).encode())
        d = hoerbuch.liste("http://s:8080/share/AbCd1234/Hörspiele", "Bibi Blocksberg", oeffne)
        self.assertEqual(gesehen, ["http://s:8080/api/public/share/AbCd1234/H%C3%B6rspiele/Bibi%20Blocksberg"])
        self.assertEqual([t["name"] for t in d["titel"]], ["Folge 2.mp3", "Folge 10.mp3"])
        self.assertEqual(d["ordner"], [{"name": "CD 2", "pfad": "Bibi Blocksberg/CD 2"}])
        self.assertEqual(d["eltern"], "")

    def test_nicht_erreichbar_gibt_verstaendlichen_fehler(self):
        def oeffne(anfrage, timeout):
            raise OSError("Verbindung abgelehnt")
        with self.assertRaisesRegex(hoerbuch.HoerbuchFehler, "nicht erreichbar"):
            hoerbuch.liste("http://s:8080/share/AbCd1234", "", oeffne)

    def test_datei_adresse(self):
        self.assertEqual(hoerbuch.datei_adresse("http://s:8080/share/AbCd1234", "Bibi/Folge 1.mp3"),
                         "http://s:8080/api/public/dl/AbCd1234/Bibi/Folge%201.mp3?inline=true")
        with self.assertRaises(hoerbuch.HoerbuchFehler):
            hoerbuch.datei_adresse("http://s:8080/share/AbCd1234", "geheim.txt")


class Katalog(unittest.TestCase):
    def test_typ_hoerbuch(self):
        katalog.pruefe_katalog([hoerbuch_app("http://s:8080/share/AbCd1234")])
        katalog.pruefe_katalog([hoerbuch_app("")])            # noch nicht eingerichtet ist erlaubt
        with self.assertRaisesRegex(katalog.KatalogFehler, "Freigabelink"):
            katalog.pruefe_katalog([hoerbuch_app("http://s:32400/web/")])

    def test_alte_hoerspiele_kachel_wird_gute_nacht(self):
        ordner = tempfile.mkdtemp(prefix="ff-hb-")
        self.addCleanup(shutil.rmtree, ordner, True)
        alt = [{"id": "hoerspiele", "name": "Hörspiele", "typ": "web", "start": "http://s:32400/web/#!/media/x",
                "zeit": "nie", "eingabe": "tasten", "domains": [], "aktiv": True, "symbol": "musik", "reihenfolge": 70}]
        with open(os.path.join(ordner, "apps.json"), "w") as f:
            json.dump(alt, f)
        hub = neuer_hub(ordner, Uhr(MITTWOCH))
        self.assertIsNone(hub.app("hoerspiele"))
        app = hub.app("gute-nacht")                                    # 3.3 Player -> 3.4 Gute Nacht
        self.assertEqual((app["typ"], app["name"], app["start"], app["sperr_erlaubt"]),
                         ("hoerbuch", "Gute Nacht", "", "alle"))
        ok, meldung = hub.starte("gute-nacht")
        self.assertFalse(ok)
        self.assertIn("noch nicht eingerichtet", meldung)


class HubUndSchlafenszeit(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-hb-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.attrappe, start = starte_attrappe()
        self.addCleanup(self.attrappe.shutdown)
        self.uhr = Uhr(datetime(2026, 11, 18, 19, 20))            # Nachtruhe (Vorgabe) ab 19:30
        self.hub = neuer_hub(self.ordner, self.uhr)
        self.hub.katalog_aendern([hoerbuch_app(start)])

    def test_zaehlt_nie_und_startet_ohne_auftrag(self):
        ok, _ = self.hub.starte("gute-nacht")
        self.assertTrue(ok)
        self.assertFalse([a for a in self.hub.auftraege if a.get("art") == "oeffne"])
        self.uhr.weiter(30 * 60)                                  # 19:50 = Nachtruhe
        self.assertTrue(next(k for k in self.hub.kacheln() if k["id"] == "gute-nacht")["frei"])

    def test_liste_und_weiterhoeren(self):
        d = self.hub.hoerbuch_liste("gute-nacht")
        self.assertEqual([o["name"] for o in d["ordner"]], ["Bibi Blocksberg", "Die drei ??? Kids"])
        self.assertEqual(d["schlaf_max_min"], 60)
        self.assertIsNone(d["stand"])
        self.hub.hoerbuch_stand("gute-nacht", "Bibi Blocksberg", "Bibi Blocksberg/Folge 2.wav", 125)
        self.assertEqual(self.hub.hoerbuch_liste("gute-nacht")["stand"]["sekunde"], 125)

    def test_nachtruhe_wartet_auf_den_sleep_timer(self):
        self.hub.starte("gute-nacht")
        self.hub.hoerbuch_stand("gute-nacht", "", "Einzeln.wav", 10, spielt=True)
        for _ in range(12):                      # 19:20 -> 19:32, der Player meldet sich weiter
            self.uhr.weiter(60)
            self.hub.hoerbuch_stand("gute-nacht", "", "Einzeln.wav", 10, spielt=True)
            self.hub.tick(60)
        self.assertNotIn(("gong",), self.hub.system.aufrufe)
        self.assertEqual(self.hub.cec["befehl"], None)
        self.assertNotIn("nacht", [a["art"] for a in self.hub.auftraege])
        self.assertEqual(self.hub.aktuell, "gute-nacht")
        self.hub.hoerbuch_schlaf_ende()
        self.assertEqual(self.hub.cec["befehl"], "standby")
        self.assertEqual(self.hub.aktuell, "gute-nacht")          # kein Zurück: das Bild bleibt dunkel
        self.assertTrue(self.hub.still())

    def test_einschlafbild_ist_still(self):
        self.hub.starte("gute-nacht")
        self.hub.hoerbuch_stand("gute-nacht", "", "", 0, dunkel=True)
        self.assertTrue(self.hub.still())
        self.hub.familie.nachricht("Huhu", bleibt=True)
        self.assertNotIn(("gong",), self.hub.system.aufrufe)

    def test_andere_app_zur_nachtruhe_beendet(self):
        self.hub.katalog_aendern([hoerbuch_app(self.hub.app("gute-nacht")["start"]),
                                  {"id": "plex", "name": "Plex", "typ": "web", "start": "http://plex.example:32400/web/",
                                   "zeit": "frei", "sperr_erlaubt": [], "eingabe": "tasten", "domains": [], "aktiv": True}])
        self.hub.starte("plex")
        for _ in range(12):
            self.uhr.weiter(60)
            self.hub.eingabe(["ENTER"])
            self.hub.tick(60)
        self.assertIsNone(self.hub.aktuell)
        self.assertIn("nacht", [a["art"] for a in self.hub.auftraege])
        self.assertFalse(self.hub.starte("plex")[0])


class Durchreichen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ordner = tempfile.mkdtemp(prefix="ff-hb-")
        cls.attrappe, start = starte_attrappe()
        cls.hub = neuer_hub(cls.ordner, Uhr(MITTWOCH))
        cls.hub.katalog_aendern([hoerbuch_app(start)])
        cls.server = web.baue_server(web.KioskHandler, cls.hub, os.path.join(REPO, "web"),
                                     os.path.join(cls.ordner, "zeichnungen"), ("127.0.0.1", 0))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.basis = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.attrappe.shutdown()
        shutil.rmtree(cls.ordner, True)

    def test_liste(self):
        with urllib.request.urlopen(self.basis + "/api/hoerbuch/liste?app=gute-nacht&pfad=Bibi%20Blocksberg") as a:
            d = json.load(a)
        self.assertEqual([t["name"] for t in d["titel"]], ["Folge 1.wav", "Folge 2.wav", "Folge 10.wav"])

    def test_cover(self):
        with urllib.request.urlopen(self.basis + "/api/hoerbuch/cover?app=gute-nacht&pfad=Bibi%20Blocksberg") as a:
            self.assertEqual((a.headers["Content-Type"], a.read()), ("image/png", PNG))
        with self.assertRaises(urllib.error.HTTPError) as fehler:
            urllib.request.urlopen(self.basis + "/api/hoerbuch/cover?app=gute-nacht&pfad=Die%20drei%20%3F%3F%3F%20Kids")
        self.assertEqual(fehler.exception.code, 404)
        self.assertEqual(hoerbuch.cover_in(self.hub.app("gute-nacht")["start"], "Bibi Blocksberg"), "Bibi Blocksberg/cover.png",
                         "cover.* geht vor anderen Bildern")

    def test_datei_mit_range(self):  # noqa: D102
        anfrage = urllib.request.Request(self.basis + "/api/hoerbuch/datei?app=gute-nacht&pfad=Einzeln.wav",
                                         headers={"Range": "bytes=10-19"})
        with urllib.request.urlopen(anfrage) as a:
            self.assertEqual(a.status, 206)
            self.assertEqual(a.headers["Content-Range"], "bytes 10-19/%d" % len(BAUM["Einzeln.wav"]))
            self.assertEqual(a.read(), BAUM["Einzeln.wav"][10:20])

    def test_kein_ausbruch_und_keine_fremden_dateien(self):
        for pfad in ("../geheim.wav", "Bibi%20Blocksberg/cover.jpg"):
            with self.assertRaises(urllib.error.HTTPError) as fehler:
                urllib.request.urlopen(self.basis + "/api/hoerbuch/datei?app=gute-nacht&pfad=" + pfad)
            self.assertEqual(fehler.exception.code, 400)


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class PlayerImBrowser(unittest.TestCase):
    """Echter Chromium: Ordner öffnen, PLAY fragt die Sleep-Zeit, Bild wird schwarz, Timer schaltet ab."""

    @classmethod
    def setUpClass(cls):
        cls.ordner = tempfile.mkdtemp(prefix="ff-hb-")
        cls.attrappe, start = starte_attrappe()
        cls.uhr = Uhr(MITTWOCH)
        cls.hub = neuer_hub(cls.ordner, cls.uhr)
        cls.hub.katalog_aendern([hoerbuch_app(start)])
        cls.server = web.baue_server(web.KioskHandler, cls.hub, os.path.join(REPO, "web"),
                                     os.path.join(cls.ordner, "zeichnungen"), ("127.0.0.1", 8765))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.attrappe.shutdown()
        shutil.rmtree(cls.ordner, True)

    def test_einschlafen(self):
        seite = self.browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
        fehler = []
        seite.on("pageerror", lambda e: fehler.append(str(e)))
        seite.add_init_script("window.__ffHoerbuch = { schwarzS: 2, minuteMs: 3000 };")
        seite.goto("http://127.0.0.1:%d/" % self.server.server_address[1])
        seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('gute-nacht')")
        seite.wait_for_selector(".kachel[data-id=gute-nacht]")
        seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('gute-nacht')")
        seite.click(".kachel[data-id=gute-nacht]")
        seite.wait_for_selector(".hb-eintrag")
        seite.wait_for_selector(".hb-eintrag img.hb-cover")                     # Bibi hat ein Cover, die drei ??? nicht
        self.assertEqual(seite.locator(".hb-eintrag .hb-name").all_inner_texts(), ["Bibi Blocksberg", "Die drei ??? Kids"])
        self.assertEqual(seite.locator(".hb-eintrag .hb-symbol-klein").count(), 1)
        self.assertEqual(seite.locator(".hb-eintrag").all_inner_texts()[2], "🎵 Einzeln")
        seite.keyboard.press("Enter")                                   # Ordner öffnen
        seite.wait_for_selector("text=🎵 Folge 1")
        self.assertEqual(seite.locator(".hb-eintrag").all_inner_texts(),
                         ["⬆ Zurück", "🎵 Folge 1", "🎵 Folge 2", "🎵 Folge 10"])
        seite.keyboard.press("ArrowDown")
        medientaste(seite, "MediaPlay")                               # PLAY -> erst die Sleep-Zeit
        seite.wait_for_selector(".hb-wahl:not([hidden])")
        self.assertIn("5 min", seite.inner_text(".hb-wahl"))
        seite.keyboard.press("ArrowLeft")
        seite.keyboard.press("ArrowLeft")
        seite.keyboard.press("ArrowLeft")                               # 30 -> 20 -> 15 -> 10 min ...
        seite.keyboard.press("ArrowLeft")                               # ... -> 5 min (= 15 s im Test)
        seite.keyboard.press("Enter")
        seite.wait_for_function("() => document.querySelector('.hb-titel').textContent === 'Folge 1'")
        seite.wait_for_selector(".hb-schwarz:not([hidden])", timeout=6000)    # nach 2 s schwarz
        seite.keyboard.press("ArrowDown")                               # weckt nur
        self.assertTrue(seite.is_hidden(".hb-schwarz"))
        seite.keyboard.press("p")                                       # PAUSE
        seite.wait_for_function("() => document.querySelector('.hb-zeit').textContent.includes('angehalten')",
                                timeout=3000)                       # Anzeige läuft im Sekundentakt
        medientaste(seite, "MediaPlay")                               # wieder PLAY -> wieder fragen
        seite.wait_for_selector(".hb-wahl:not([hidden])")
        for _ in range(4):
            seite.keyboard.press("ArrowLeft")
        seite.keyboard.press("Enter")                                   # 5 min = 15 s, Lieder je 20 s
        seite.wait_for_function("() => !document.querySelector('.hb-zeit').textContent.includes('angehalten')",
                                timeout=3000)
        seite.wait_for_function("() => document.querySelector('.hb-zeit').textContent.includes('angehalten')",
                                timeout=30000)
        seite.wait_for_timeout(500)
        self.assertEqual(self.hub.cec["befehl"], "standby")             # Fernseher aus
        self.assertFalse(seite.is_hidden(".hb-schwarz"))
        self.assertTrue(self.hub.hoerbuch_liste("gute-nacht")["stand"])
        self.assertEqual(fehler, [])
        os.makedirs(os.path.join(REPO, ".local", "bildschirm"), exist_ok=True)
        seite.keyboard.press("ArrowUp")
        seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "hoerbuch.png"))


if __name__ == "__main__":
    unittest.main()
