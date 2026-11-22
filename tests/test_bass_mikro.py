"""Bass-Ecke mit Mikrofon: Tonerkennung (tonhoehe/naechsterTon) und „Nachspielen“ mit einem simulierten Mikrofon.

Chromium bekommt über --use-file-for-fake-audio-capture eine WAV-Datei als Mikrofon (ein gezupftes A, 55 Hz).
"""
import math
import os
import shutil
import socket
import struct
import sys
import tempfile
import threading
import unittest
import wave

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import web  # noqa: E402
from test_v3_server import MITTWOCH, Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def port_frei(port):
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def bass_wav(pfad, hz, sekunden=8, rate=48000):
    """Gezupfter Basston mit Obertönen, immer wieder neu angeschlagen."""
    with wave.open(pfad, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        daten = bytearray()
        for i in range(int(sekunden * rate)):
            t = (i % rate) / rate                       # jede Sekunde neu angeschlagen
            huelle = math.exp(-2.5 * t)
            wert = sum(math.sin(2 * math.pi * hz * k * i / rate) / k for k in (1, 2, 3, 4))
            daten += struct.pack("<h", int(9000 * huelle * wert))
        w.writeframes(bytes(daten))


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt")
class BassMikro(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ordner = tempfile.mkdtemp(prefix="ff-mikro-")
        cls.wav = os.path.join(cls.ordner, "a-saite.wav")
        bass_wav(cls.wav, 55.0)
        cls.hub = neuer_hub(cls.ordner, Uhr(MITTWOCH))
        cls.server = web.baue_server(web.KioskHandler, cls.hub, os.path.join(REPO, "web"),
                                     os.path.join(cls.ordner, "zeichnungen"), ("127.0.0.1", 8765))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(args=[
            "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
            "--use-file-for-fake-audio-capture=%s" % cls.wav, "--autoplay-policy=no-user-gesture-required"])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.ordner, True)

    def seite(self):
        kontext = self.browser.new_context(viewport={"width": 1600, "height": 900}, bypass_csp=True,
                                           permissions=["microphone"])
        self.addCleanup(kontext.close)
        seite = kontext.new_page()
        seite.goto("http://127.0.0.1:8765/")
        seite.wait_for_selector(".kachel")
        return seite

    def test_tonerkennung_bassbereich(self):
        seite = self.seite()
        ergebnis = seite.evaluate("""async () => {
            const m = await import('/js/spiele/bass.js');
            const rate = 48000, n = 4096, aus = {};
            for (const [name, hz] of [['E', 41.2], ['A', 55], ['D', 73.42], ['G', 98], ['C', 65.41], ['F#', 46.25]]) {
                const p = new Float32Array(n);
                for (let i = 0; i < n; i++) {
                    p[i] = [1, 2, 3, 4].reduce((s, k) => s + Math.sin(2 * Math.PI * hz * k * i / rate) / k, 0) * 0.3
                           + (Math.random() - 0.5) * 0.02;
                }
                const gefunden = m.tonhoehe(p, rate);
                aus[name] = gefunden ? m.naechsterTon(gefunden).name : null;
            }
            aus.stille = m.tonhoehe(new Float32Array(n), rate);
            aus.passt = m.tonPasst(110, 'A') && !m.tonPasst(110, 'C');
            return aus; }""")
        self.assertEqual(ergebnis, {"E": "E", "A": "A", "D": "D", "G": "G", "C": "C", "F#": "F#",
                                    "stille": None, "passt": True})

    def test_nachspielen_hoert_das_mikrofon(self):
        seite = self.seite()
        seite.locator("[data-id=spiel-bass]").click()
        seite.wait_for_selector(".knopfreihe")
        seite.keyboard.press("Enter")                                   # 3.5 Musik-Akademie: erst „Bass“
        seite.wait_for_selector("text=Bass – was möchtest du üben?")
        texte = seite.locator(".knopfreihe .knopf").all_text_contents()
        index = next(i for i, t in enumerate(texte) if "Nachspielen" in t)
        for _ in range(index):
            seite.keyboard.press("ArrowRight")
        seite.keyboard.press("Enter")
        seite.wait_for_function("""() => document.body.innerText.includes('Ich höre A') ||
                                         document.getElementById('hinweis').textContent.includes('das war A')""",
                                timeout=15000)


if __name__ == "__main__":
    unittest.main()
