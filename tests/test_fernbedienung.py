"""Erweiterung familyhub/fernbedienung: Pfeile in Plex bewegen den Fokus statt der Lautstärke.

Eine Plex-Attrappe (belegt die Pfeile wie Plex selbst) läuft lokal auf Port 32400 unter /web/.
Chromium startet mit denselben Schaltern wie im Kiosk (kiosk.sh).
"""
import functools
import http.server
import os
import shutil
import socket
import tempfile
import threading
import unittest

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERWEITERUNG = os.path.join(REPO, "fernbedienung")          # 3.x (2.5: familyhub/fernbedienung)

ATTRAPPE = """<!doctype html><html><body>
<div id="lautstaerke">50</div>
<a id="film1" href="#f1" style="display:block;margin:30px">Film 1</a>
<a id="film2" href="#f2" style="display:block;margin:30px">Film 2</a>
<div id="kachel" tabindex="0" style="display:block;margin:30px;width:200px;height:40px"
     onclick="document.title='kachel-geklickt'">Kachel (div)</div>
<input id="suche" type="search" value="abc">
<video id="video" muted loop></video>
<script>
  // wie Plex: Pfeile hoch/runter = Lautstaerke, mit preventDefault
  document.addEventListener("keydown", (e) => {
    const l = document.getElementById("lautstaerke");
    if (e.key === "ArrowUp") { l.textContent = +l.textContent + 10; e.preventDefault(); }
    if (e.key === "ArrowDown") { l.textContent = +l.textContent - 10; e.preventDefault(); }
  });
</script></body></html>"""


def freier_port_32400():
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # wie der Testserver
        try:
            s.bind(("127.0.0.1", 32400))
            return True
        except OSError:
            return False


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(freier_port_32400(), "Port 32400 belegt")
class PlexFernbedienung(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ordner = tempfile.mkdtemp(prefix="ff-plex-")
        os.makedirs(os.path.join(cls.ordner, "web"))
        with open(os.path.join(cls.ordner, "web", "index.html"), "w") as f:
            f.write(ATTRAPPE)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=cls.ordner)
        handler.log_message = lambda *a: None
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 32400), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.profil = tempfile.mkdtemp(prefix="ff-profil-")
        cls.kontext = cls.pw.chromium.launch_persistent_context(
            cls.profil, headless=True, channel="chromium",   # neuer Headless-Modus kann Erweiterungen
            args=["--enable-spatial-navigation", "--load-extension=" + ERWEITERUNG,
                  "--disable-extensions-except=" + ERWEITERUNG])

    @classmethod
    def tearDownClass(cls):
        cls.kontext.close()
        cls.pw.stop()
        cls.server.shutdown()
        shutil.rmtree(cls.ordner, True)
        shutil.rmtree(cls.profil, True)

    def seite(self):
        seite = self.kontext.new_page()
        self.addCleanup(seite.close)
        seite.goto("http://127.0.0.1:32400/web/index.html")
        seite.wait_for_timeout(300)
        seite.focus("#film1")
        return seite

    def aktiv(self, seite):
        return seite.evaluate("document.activeElement.id")

    def test_pfeile_springen_statt_lautstaerke(self):
        seite = self.seite()
        seite.keyboard.press("ArrowDown")
        self.assertEqual(seite.text_content("#lautstaerke"), "50", "Plex darf die Pfeile nicht bekommen")
        self.assertEqual(self.aktiv(seite), "film2")
        seite.keyboard.press("ArrowDown")
        self.assertEqual(self.aktiv(seite), "kachel")
        seite.keyboard.press("ArrowUp")
        self.assertEqual(self.aktiv(seite), "film2")
        self.assertEqual(seite.text_content("#lautstaerke"), "50", "Plex darf die Pfeile nicht bekommen")

    def test_ok_klickt_auch_auf_div(self):
        seite = self.seite()
        seite.focus("#kachel")
        seite.keyboard.press("Enter")
        self.assertEqual(seite.title(), "kachel-geklickt")

    def test_suchfeld_cursor_bleibt(self):
        seite = self.seite()
        seite.focus("#suche")
        seite.keyboard.press("End")
        seite.keyboard.press("ArrowLeft")
        self.assertEqual(seite.evaluate("document.getElementById('suche').selectionStart"), 2)

    def lade_medium(self, seite, stil, spielen=True):
        """Echtes, spulbares Medium ohne Datei: 60 s Stille als WAV (Plex spielt Musik und Filme
        über ein Medienelement), mit gegebener Größe/Lage."""
        seite.evaluate("""async ([stil, spielen]) => {
            const rate = 8000, n = rate * 60, puffer = new ArrayBuffer(44 + n), d = new DataView(puffer);
            const txt = (o, t) => { for (let i = 0; i < t.length; i++) d.setUint8(o + i, t.charCodeAt(i)); };
            txt(0, 'RIFF'); d.setUint32(4, 36 + n, true); txt(8, 'WAVEfmt '); d.setUint32(16, 16, true);
            d.setUint16(20, 1, true); d.setUint16(22, 1, true); d.setUint32(24, rate, true);
            d.setUint32(28, rate, true); d.setUint16(32, 1, true); d.setUint16(34, 8, true);
            txt(36, 'data'); d.setUint32(40, n, true); new Uint8Array(puffer, 44).fill(128);
            const v = document.getElementById('video'); v.setAttribute('style', stil);
            v.src = URL.createObjectURL(new Blob([puffer], {type: 'audio/wav'}));
            await new Promise((ok) => v.addEventListener('loadedmetadata', ok, {once: true}));
            if (spielen) await v.play(); }""", [stil, spielen])

    def drueck(self, seite, taste):
        """Medientaste so senden, wie sie aus der Fernbedienungs-Brücke ankommt."""
        seite.evaluate("""(taste) => document.activeElement.dispatchEvent(
            new KeyboardEvent('keydown', {key: taste, bubbles: true, cancelable: true}))""", taste)

    def test_pfeile_navigieren_auch_im_film(self):
        """Gewünscht: Pfeile navigieren IMMER, auch bei großem, laufendem Video."""
        seite = self.seite()
        self.lade_medium(seite, "position:fixed;left:0;top:0;width:100vw;height:100vh;pointer-events:none")
        seite.focus("#film1")
        seite.keyboard.press("ArrowDown")
        self.assertEqual(seite.text_content("#lautstaerke"), "50")
        self.assertEqual(self.aktiv(seite), "film2")

    def test_pfeile_navigieren_bei_musik(self):
        seite = self.seite()
        self.lade_medium(seite, "position:fixed;left:0;bottom:0;width:100vw;height:80px")
        seite.focus("#film1")
        seite.keyboard.press("ArrowDown")
        self.assertEqual(seite.text_content("#lautstaerke"), "50")
        self.assertEqual(self.aktiv(seite), "film2")

    def test_play_pause_und_spulen_mit_eigenen_tasten(self):
        seite = self.seite()
        self.lade_medium(seite, "display:none")
        zeit = "document.getElementById('video').currentTime"
        pausiert = "document.getElementById('video').paused"
        self.drueck(seite, "MediaPlayPause")
        self.assertTrue(seite.evaluate(pausiert))
        self.drueck(seite, "p")                      # PAUSE-Taste der Fernbedienung
        seite.wait_for_function("!document.getElementById('video').paused", timeout=3000)
        vorher = seite.evaluate(zeit)
        self.drueck(seite, "MediaFastForward")
        self.assertGreaterEqual(seite.evaluate(zeit), vorher + 29)
        self.drueck(seite, "MediaRewind")
        self.assertGreaterEqual(seite.evaluate(zeit), vorher + 19)
        self.assertLess(seite.evaluate(zeit), vorher + 25)

    def test_p_in_der_suche_wird_getippt(self):
        seite = self.seite()
        self.lade_medium(seite, "display:none")
        seite.focus("#suche")
        seite.keyboard.press("End")
        seite.keyboard.type("p")
        self.assertEqual(seite.input_value("#suche"), "abcp")
        self.assertFalse(seite.evaluate("document.getElementById('video').paused"))

    def test_andere_seiten_unberuehrt(self):
        """Nur Plex (Port 32400, /web/ oder app.plex.tv) - Kavita & Co. behalten ihre Tasten."""
        import json
        with open(os.path.join(ERWEITERUNG, "manifest.json")) as f:
            skript = json.load(f)["content_scripts"][0]
        self.assertEqual(skript["include_globs"],
                         ["http://*:32400/web/*", "https://*:32400/web/*", "https://app.plex.tv/*"])
        self.assertEqual(skript["run_at"], "document_start")


if __name__ == "__main__":
    unittest.main()


def _freier_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(shutil.which("openssl"), "openssl fehlt")
class YouTubeFluessig(unittest.TestCase):
    """youtube.js: auf YouTube-Seiten kein VP9/AV1, höchstens 30 fps -> YouTube liefert H.264 (Pi 3 dekodiert es in Hardware)."""

    @classmethod
    def setUpClass(cls):
        import ssl
        import subprocess
        cls.ordner = tempfile.mkdtemp(prefix="ff-yt-")
        schluessel, zert = os.path.join(cls.ordner, "s.pem"), os.path.join(cls.ordner, "z.pem")
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj",
                        "/CN=www.youtube-nocookie.com", "-keyout", schluessel, "-out", zert],
                       check=True, capture_output=True)
        os.makedirs(os.path.join(cls.ordner, "embed"))
        with open(os.path.join(cls.ordner, "embed", "test.html"), "w") as f:
            f.write("<!doctype html><title>Player</title><video></video>")
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=cls.ordner)
        handler.log_message = lambda *a: None
        cls.port = _freier_port()
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", cls.port), handler)
        kontext = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        kontext.load_cert_chain(zert, schluessel)
        cls.server.socket = kontext.wrap_socket(cls.server.socket, server_side=True)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.profil = tempfile.mkdtemp(prefix="ff-yt-profil-")
        cls.kontext = cls.pw.chromium.launch_persistent_context(
            cls.profil, headless=True, channel="chromium", ignore_https_errors=True,
            args=["--load-extension=" + ERWEITERUNG, "--disable-extensions-except=" + ERWEITERUNG,
                  "--host-resolver-rules=MAP www.youtube-nocookie.com:443 127.0.0.1:%d" % cls.port,
                  "--ignore-certificate-errors"])

    @classmethod
    def tearDownClass(cls):
        cls.kontext.close()
        cls.pw.stop()
        cls.server.shutdown()
        shutil.rmtree(cls.ordner, True)
        shutil.rmtree(cls.profil, True)

    def test_nur_h264_bis_30_fps(self):
        seite = self.kontext.new_page()
        self.addCleanup(seite.close)
        seite.goto("https://www.youtube-nocookie.com/embed/test.html")
        ergebnis = seite.evaluate("""() => ({
            vp9: MediaSource.isTypeSupported('video/webm; codecs="vp9"'),
            vp09: MediaSource.isTypeSupported('video/webm; codecs="vp09.00.10.08"'),
            av1: MediaSource.isTypeSupported('video/mp4; codecs="av01.0.05M.08"'),
            h264: MediaSource.isTypeSupported('video/mp4; codecs="avc1.4d401f"'),
            h264_60: MediaSource.isTypeSupported('video/mp4; codecs="avc1.4d401f"; framerate=60'),
            h264_1080: MediaSource.isTypeSupported('video/mp4; codecs="avc1.640028"; width=1920; height=1080'),
            ton: MediaSource.isTypeSupported('audio/mp4; codecs="mp4a.40.2"'),
            element: document.querySelector('video').canPlayType('video/webm; codecs="vp9"') })""")
        self.assertEqual(ergebnis, {"vp9": False, "vp09": False, "av1": False, "h264": True, "h264_60": False,
                                    "h264_1080": False, "ton": True, "element": ""})
