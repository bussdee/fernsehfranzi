"""4.4 im Browser: Foto von Telegram in den Nachrichten ansehen und ins Album übernehmen, Fotoalbum (⭐, Bildschirmschoner),
Malen-Galerie mit Schicken/Löschen."""
import base64
import os
import shutil
import sys
import tempfile
import threading
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import web  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_v3_server import MITTWOCH, Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

# 2×2 Pixel JPEG (rot)
JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/"
    "yQALCAACAAIBAREA/8wABgAQEAX/2gAIAQEAAD8A0s8g/9k=")


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class FotoalbumImBrowser(unittest.TestCase):
    def test_foto_ins_album_und_bildschirmschoner(self):
        ordner = tempfile.mkdtemp(prefix="ff-foto-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(MITTWOCH))
        hub.einstellungen_aendern({"fotoalbum": {"erlaubt": True}})
        os.makedirs(os.path.join(ordner, "medien"))
        name = "m1763470000-abc123.jpg"
        with open(os.path.join(ordner, "medien", name), "wb") as f:
            f.write(JPEG)
        hub.familie.nachricht("Schau mal!", quelle="Papa", bleibt=True, chat=111, symbol="💬", medium={"art": "foto", "datei": name})
        zeichnungen = os.path.join(ordner, "zeichnungen")
        server = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), zeichnungen, ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            seite = browser.new_page(viewport={"width": 1600, "height": 900})
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            seite.goto("http://127.0.0.1:8765/")
            seite.wait_for_selector("#meldungen .meldung-foto")         # Foto groß in der Meldung
            seite.click("#meldungen button")
            seite.click(".kachel[data-id=spiel-nachrichten]")
            seite.wait_for_selector(".nachricht.gewaehlt")
            self.assertIn("📷 Schau mal!", seite.inner_text(".nachrichten-liste"))
            seite.keyboard.press("Enter")
            seite.wait_for_selector("img.medium-gross")
            self.assertIn("⭐ Ins Album", seite.inner_text(".medium-ansicht"))
            seite.keyboard.press("Enter")                                # ⭐ Ins Album
            for _ in range(30):
                if hub.album_liste():
                    break
                seite.wait_for_timeout(100)
            self.assertEqual(len(hub.album_liste()), 1)
            seite.keyboard.press("Escape")
            seite.keyboard.press("Escape")
            seite.keyboard.press("Escape")
            seite.wait_for_timeout(400)
            seite.click(".kachel[data-id=spiel-fotoalbum]")
            seite.wait_for_selector(".fa-raster .fa-kachel")
            seite.keyboard.press("ArrowDown")                            # ins Raster
            seite.keyboard.press("Enter")                                # Menü des Album-Bildes
            seite.wait_for_selector(".fa-menue")
            seite.keyboard.press("Enter")                                # ⭐ zeigen
            seite.wait_for_selector(".fa-stern")
            self.assertEqual(hub.fotoalbum()["auswahl"], ["album:" + hub.album_liste()[0]["datei"]])
            seite.keyboard.press("ArrowUp")                              # zur Leiste
            for _ in range(2):                                           # Album · Bilder · Bildschirmschoner
                seite.keyboard.press("ArrowRight")
            seite.keyboard.press("Enter")
            for _ in range(30):
                if hub.fotoalbum()["bildschirmschoner"]:
                    break
                seite.wait_for_timeout(100)
            self.assertTrue(hub.fotoalbum()["bildschirmschoner"])
            seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "fotoalbum.png"))
            seite.keyboard.press("Escape")
            seite.wait_for_timeout(300)
            seite.evaluate("() => { window.__ffTest = true; }")
            urls = seite.evaluate("""async () => { const fa = await (await fetch('/api/fotoalbum')).json(); return fa.auswahl; }""")
            self.assertEqual(len(urls), 1)
            self.assertEqual(fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()
