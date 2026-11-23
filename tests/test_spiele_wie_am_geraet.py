"""Spiele in einem Browser ohne Emoji-Schrift - so wie Chromium auf dem Fernseh-Pi.

Chromium startet mit einer eigenen fontconfig-Konfiguration, die nur DejaVu kennt (keine Emojis).
Für Memory-Karten und Drei-Gewinnt-Felder fragt der Test Chromium (CSS.getPlatformFontsForNode),
mit welcher Schrift wirklich gezeichnet wurde: Es muss die mitgelieferte Emoji-Schrift sein.
Bildschirmfotos landen in .local/bildschirm/ zum Anschauen.
"""
import os
import shutil
import socket
import sys
import tempfile
import threading
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import web  # noqa: E402
from test_v3_server import MITTWOCH, Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

DEJAVU = "/usr/share/fonts/truetype/dejavu"
FOTOS = os.path.join(REPO, ".local", "bildschirm")


def port_frei(port):
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(os.path.isdir(DEJAVU), "DejaVu-Schriften fehlen")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class WieAmGeraet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ordner = tempfile.mkdtemp(prefix="ff-geraet-")
        conf = os.path.join(cls.ordner, "fonts.conf")
        with open(conf, "w") as f:
            f.write('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig>'
                    '<dir>%s</dir><cachedir>%s/cache</cachedir></fontconfig>' % (DEJAVU, cls.ordner))
        cls.hub = neuer_hub(cls.ordner, Uhr(MITTWOCH))
        cls.server = web.baue_server(web.KioskHandler, cls.hub, os.path.join(REPO, "web"),
                                     os.path.join(cls.ordner, "zeichnungen"), ("127.0.0.1", 8765))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(env=dict(os.environ, FONTCONFIG_FILE=conf),
                                             args=["--enable-spatial-navigation"])
        os.makedirs(FOTOS, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.ordner, True)

    def seite(self):
        seite = self.browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
        self.addCleanup(seite.close)
        self.fehler = []
        seite.on("pageerror", lambda e: self.fehler.append(str(e)))
        seite.goto("http://127.0.0.1:8765/")
        seite.wait_for_selector(".kachel")
        seite.evaluate("""async () => { await document.fonts.load('16px "FF Emoji"', '🎬'); await document.fonts.ready; }""")
        seite.wait_for_timeout(200)
        self.cdp = seite.context.new_cdp_session(seite)
        self.cdp.send("DOM.enable")
        self.cdp.send("CSS.enable")
        return seite

    def schriften(self, selektor):
        wurzel = self.cdp.send("DOM.getDocument", {"depth": -1})["root"]["nodeId"]
        knoten = self.cdp.send("DOM.querySelectorAll", {"nodeId": wurzel, "selector": selektor})["nodeIds"]
        namen = set()
        for k in knoten:
            for f in self.cdp.send("CSS.getPlatformFontsForNode", {"nodeId": k})["fonts"]:
                namen.add(f["familyName"])
        return namen

    def emoji_ohne_schrift(self, seite):
        """Alle Elemente, deren eigener Text ein Emoji enthält, aber nicht mit der Emoji-Schrift gezeichnet wird."""
        seite.evaluate("""() => {
            const emoji = /[\\u{1F000}-\\u{1FAFF}\\u{2600}-\\u{27BF}\\u{2B00}-\\u{2BFF}]/u;
            document.querySelectorAll('[data-ff-emoji]').forEach(e => e.removeAttribute('data-ff-emoji'));
            let n = 0;
            for (const e of document.querySelectorAll('body *')) {
                const eigen = [...e.childNodes].filter(k => k.nodeType === 3).map(k => k.textContent).join('');
                if (emoji.test(eigen) && e.getClientRects().length) e.setAttribute('data-ff-emoji', n++);
            }
        }""")
        wurzel = self.cdp.send("DOM.getDocument", {"depth": -1})["root"]["nodeId"]
        knoten = self.cdp.send("DOM.querySelectorAll", {"nodeId": wurzel, "selector": "[data-ff-emoji]"})["nodeIds"]
        falsch = []
        for k in knoten:
            namen = {f["familyName"] for f in self.cdp.send("CSS.getPlatformFontsForNode", {"nodeId": k})["fonts"]}
            if "Noto Color Emoji" not in namen:
                falsch.append(self.cdp.send("DOM.getOuterHTML", {"nodeId": k})["outerHTML"][:120])
        return falsch

    def rundgang(self, seite, kachel, tasten, foto, warten=400):
        seite.wait_for_function("k => window.FernsehFranzi && FernsehFranzi.zeige(k)", arg=kachel)
        seite.locator("[data-id=%s]" % kachel).click()
        seite.wait_for_selector(".overlay")
        for taste in tasten:
            if isinstance(taste, int):
                seite.wait_for_timeout(taste)
            else:
                seite.keyboard.press(taste)
        seite.wait_for_timeout(warten)
        seite.screenshot(path=os.path.join(FOTOS, foto))
        self.assertEqual(self.emoji_ohne_schrift(seite), [], foto)
        self.assertEqual(self.fehler, [], foto)
        seite.keyboard.press("Escape")
        seite.keyboard.press("Escape")
        seite.keyboard.press("Escape")
        seite.wait_for_timeout(200)

    def test_alle_spiele_rundgang(self):
        seite = self.seite()
        self.assertEqual(self.emoji_ohne_schrift(seite), [], "Startseite")
        self.rundgang(seite, "spiel-snake", ["Enter", 1200, "ArrowDown", 600, "ArrowLeft", 600], "snake.png")
        self.rundgang(seite, "spiel-memory", ["ArrowRight", "ArrowRight", "Enter", "Enter", "ArrowRight", "Enter"],
                      "memory-zu-zweit-gross.png", 200)
        self.rundgang(seite, "spiel-drei", ["ArrowRight", "ArrowRight", "Enter", "Enter", "ArrowRight", "Enter"],
                      "drei-schwer.png", 800)
        self.rundgang(seite, "spiel-echo", ["Enter", 2500], "farben-echo.png")
        self.rundgang(seite, "spiel-malen", ["Enter", "ArrowRight", "ArrowRight", "ArrowRight", "2", "ArrowDown",
                                             "ArrowDown", "Enter", "0"], "malen-menue.png")
        self.rundgang(seite, "spiel-witz", ["Enter"], "witz.png")
        self.rundgang(seite, "spiel-sticker", ["ArrowRight"], "sticker.png")
        for nr, (name, schritte) in enumerate([
                ("bass-menue", []), ("bass-metronom", ["ArrowRight", "ArrowRight", "Enter"]),
                ("bass-griffbrett", ["ArrowRight"] * 5 + ["Enter", "ArrowUp", "ArrowRight"]),
                ("bass-gehoer", ["ArrowRight"] * 6 + ["Enter"]), ("bass-tabs", ["ArrowRight"] * 7 + ["Enter"]),
                ("bass-tagebuch", ["ArrowRight"] * 9 + ["Enter", 500])]):
            self.rundgang(seite, "spiel-bass", schritte, "%s.png" % name)
        for name, schritte in [("lernen-einmaleins", ["Enter", "Enter", "Enter"]),
                               ("lernen-uhr", ["ArrowRight", "Enter", "ArrowRight", "ArrowRight", "Enter"]),
                               ("lernen-englisch", ["ArrowRight", "ArrowRight", "Enter", "Enter"])]:
            self.rundgang(seite, "spiel-lernen", schritte, "%s.png" % name)
        for name, schritte in [("duell-ball", ["Enter", 800, "w", "ArrowDown"]),
                               ("duell-snake", ["ArrowRight", "Enter", 600, "s"]),
                               ("duell-quiz", ["ArrowRight", "ArrowRight", "Enter", 300, "f", "ArrowRight"]),
                               ("duell-sterne", ["ArrowLeft", "Enter", 600, "ArrowLeft", "Enter", "d", "f", 900])]:
            self.rundgang(seite, "spiel-duell", schritte, "%s.png" % name)

    def test_gegenprobe_dieser_browser_hat_keine_emoji_schrift(self):
        seite = self.seite()
        seite.evaluate("""() => { const s = document.createElement('span'); s.id = 'probe';
            s.style.fontFamily = 'sans-serif'; s.textContent = '🐶⭕'; document.body.append(s); }""")
        self.assertNotIn("Noto Color Emoji", self.schriften("#probe"))

    def test_memory_bilder_sichtbar(self):
        seite = self.seite()
        seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-memory')")
        seite.locator("[data-id=spiel-memory]").click()
        seite.keyboard.press("Enter")                       # Klein, allein
        seite.wait_for_selector(".karte")
        seite.evaluate("document.querySelectorAll('.karte').forEach(k => k.classList.add('offen'))")
        seite.wait_for_timeout(300)
        seite.screenshot(path=os.path.join(FOTOS, "memory-wie-am-geraet.png"))
        self.assertEqual(self.schriften(".karte span"), {"Noto Color Emoji"})
        self.assertEqual(self.fehler, [])

    def test_drei_gewinnt_x_und_o_sichtbar(self):
        seite = self.seite()
        seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-drei')")
        seite.locator("[data-id=spiel-drei]").click()
        seite.keyboard.press("Enter")                       # Fernseher leicht
        seite.wait_for_selector(".drei-feld .zelle")
        seite.keyboard.press("Enter")                       # X in die Mitte
        seite.wait_for_function("[...document.querySelectorAll('.zelle')].some(z => z.textContent === '🔵')")
        seite.screenshot(path=os.path.join(FOTOS, "drei-gewinnt-wie-am-geraet.png"))
        self.assertEqual(self.schriften(".drei-feld .zelle"), {"Noto Color Emoji"})

    def test_kachel_symbole_und_sticker_sichtbar(self):
        seite = self.seite()
        seite.screenshot(path=os.path.join(FOTOS, "startseite-wie-am-geraet.png"))
        # 6.0: Kachel-Symbole sind 3D-Bilder (web/icons); jedes muss wirklich geladen sein, sonst Emoji-Schrift
        kaputt = seite.evaluate("""() => [...document.querySelectorAll('.kachel .symbol img.icon')]
            .filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src)""")
        self.assertEqual(kaputt, [])
        self.assertGreater(seite.locator(".kachel .symbol img.icon").count(), 5)
        if seite.locator(".kachel .symbol .als-text").count():
            self.assertIn("Noto Color Emoji", self.schriften(".kachel .symbol .als-text"))
        seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-sticker')")
        seite.locator("[data-id=spiel-sticker]").click()
        seite.wait_for_selector(".karte")
        self.assertEqual(self.schriften(".karte span"), {"Noto Color Emoji"})


if __name__ == "__main__":
    unittest.main()
