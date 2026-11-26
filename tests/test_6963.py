"""6.9.63: Zimmer zum Anfassen - ← → wählt Gegenstände, OK löst ihre Funktion aus (Überraschung, Pflege, Spiel)."""
import os
import shutil
import sys
import tempfile
import threading
import unittest
from datetime import datetime

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))
from test_v3_server import Uhr, neuer_hub  # noqa: E402


class Anfassen(unittest.TestCase):
    def test_anfassen(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("kein Playwright")
        from fernsehfranzi import web
        from test_spiele_wie_am_geraet import port_frei
        if not port_frei(8765):
            self.skipTest("Port 8765 belegt")
        ordner = tempfile.mkdtemp(prefix="ff-6963-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(datetime(2026, 11, 28, 15)))
        hub.einstellungen["franzi"] = {"aktiv": True}
        hub.franzi_stand(besuch=True)
        for d in ("moebel-aquarium", "moebel-spielkiste"):
            hub.franzi_schenken(d)
        z = hub.franzi_zustand
        z["zimmer"]["raum-zimmer"] = {"moebel-bett": [16, 17, 1], "moebel-aquarium": [50, 30, 2], "moebel-spielkiste": [80, 4, 3]}
        srv = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            s = b.new_page(viewport={"width": 1280, "height": 720})
            fehler = []
            s.on("pageerror", lambda e: fehler.append(str(e)))
            s.goto("http://127.0.0.1:8765/#spiel-franzi")
            s.wait_for_selector(".fz-raum")
            s.wait_for_timeout(700)
            for _ in range(20):
                if s.locator(".gewaehlt:has-text('anfassen')").count():
                    break
                s.keyboard.press("ArrowDown")
            s.keyboard.press("Enter")
            s.wait_for_selector('.fz-ding[data-ding="moebel-bett"].fz-einrichten')        # links zuerst
            s.keyboard.press("ArrowRight")
            s.wait_for_selector('.fz-ding[data-ding="moebel-aquarium"].fz-einrichten')
            s.keyboard.press("Enter")
            s.wait_for_selector('.fz-ding[data-ding="moebel-aquarium"].fz-effekt .fz-fische.schnell')
            s.wait_for_timeout(500)
            s.screenshot(path=os.path.join(REPO, ".local", "bildschirm", "6963-anfassen.png"))
            s.keyboard.press("ArrowRight")
            s.keyboard.press("Enter")
            s.wait_for_selector('.fz-ding[data-ding="moebel-spielkiste"] img[src*="offen"]')
            s.keyboard.press("ArrowLeft"); s.keyboard.press("ArrowLeft")                   # zum Bett: OK = schlafen legen
            s.keyboard.press("Enter")
            s.wait_for_timeout(800)
            self.assertIsNotNone(hub.franzi_zustand.get("schlaeft_seit"))
            s.keyboard.press("Escape")
            s.wait_for_timeout(300)
            self.assertEqual(s.locator(".fz-ding.fz-einrichten").count(), 0)
            self.assertEqual(fehler, [])
            b.close()


if __name__ == "__main__":
    unittest.main()
