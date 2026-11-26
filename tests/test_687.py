"""6.8.7: Fotoalbum als Mosaik (Miniaturen im Originalformat, ohne Neuaufbau beim Blättern), Diashow nur von Hand."""
import os
import shutil
import struct
import sys
import tempfile
import threading
import unittest
import zlib
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import web  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def png(breite, hoehe, farbe):
    """kleines gültiges PNG (eine Farbe) - nur Standardbibliothek"""
    zeile = b"\x00" + bytes(farbe) * breite
    roh = zlib.compress(zeile * hoehe)
    teil = lambda art, d: struct.pack(">I", len(d)) + art + d + struct.pack(">I", zlib.crc32(art + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + teil(b"IHDR", struct.pack(">IIBBBBB", breite, hoehe, 8, 2, 0, 0, 0))
            + teil(b"IDAT", roh) + teil(b"IEND", b""))


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class Fotoalbum687(unittest.TestCase):
    def test_mosaik_ohne_neuaufbau_und_diashow(self):
        ordner = tempfile.mkdtemp(prefix="ff-687-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(datetime(2026, 11, 18, 15, 0)))
        os.makedirs(os.path.join(ordner, "album"))
        for i, (b, h, f) in enumerate(((400, 200, (220, 60, 60)), (150, 300, (60, 160, 220)), (240, 240, (60, 200, 90)))):
            with open(os.path.join(ordner, "album", "a17634700%02d-abc12%d.png" % (i, i)), "wb") as d:
                d.write(png(b, h, f))
        alle = ["album:" + b["datei"] for b in hub.album_liste()]
        hub.einstellungen_aendern({"fotoalbum": {"erlaubt": True, "auswahl": alle, "bildschirmschoner": True}})
        server = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "zeichnungen"), ("127.0.0.1", 8765))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            seite = browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            seite.goto("http://127.0.0.1:8765/")
            seite.wait_for_selector(".kachel")
            seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-fotoalbum')")
            seite.click("[data-id=spiel-fotoalbum]")
            seite.wait_for_function("document.querySelectorAll('.fa-kachel.fa-foto canvas').length === 3")
            formate = seite.evaluate("[...document.querySelectorAll('.fa-kachel.fa-foto')].map(k => { const r = k.getBoundingClientRect(); return +(r.width / r.height).toFixed(2); })")
            # das Album zeigt das neueste Foto zuerst: quadratisch, hoch, quer
            self.assertAlmostEqual(formate[0], 1.0, delta=0.1)
            self.assertAlmostEqual(formate[1], 0.5, delta=0.1, msg="hoch bleibt hoch")
            self.assertAlmostEqual(formate[2], 2.0, delta=0.15, msg="quer bleibt quer")
            seite.evaluate("document.querySelectorAll('.fa-kachel canvas').forEach((c, i) => { c.__merke = i; })")
            seite.keyboard.press("ArrowDown")
            seite.keyboard.press("ArrowRight")
            seite.keyboard.press("ArrowRight")
            seite.wait_for_selector(".fa-kachel.gewaehlt")
            self.assertEqual(seite.evaluate("[...document.querySelectorAll('.fa-kachel canvas')].map(c => c.__merke)"), [0, 1, 2],
                             "Blättern baut nichts neu auf (kein schwarzer Moment)")
            self.assertEqual(seite.locator(".fa-kachel.mit-stern").count(), 3)
            self.assertNotIn("Bildschirmschoner", seite.inner_text(".fa-leiste"))
            seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "687-mosaik.png"))
            seite.keyboard.press("ArrowUp")
            seite.keyboard.press("ArrowRight")                    # Album · Bilder · ▶ Diashow
            seite.keyboard.press("ArrowRight")
            seite.keyboard.press("Enter")
            seite.wait_for_selector("#schoner .dia-bild.an")
            seite.wait_for_timeout(1500)
            seite.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "687-diashow.png"))   # 6.9.22
            self.assertEqual(seite.locator("#schoner img").count(), 0, "Leinwand statt großer Bilder")
            seite.keyboard.press("Escape")
            seite.wait_for_selector("#schoner", state="detached")
            self.assertEqual(fehler, [])
            browser.close()


if __name__ == "__main__":
    unittest.main()
