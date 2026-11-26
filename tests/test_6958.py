"""6.9.58: Morgen-/Abend-Routinen deutlicher auslösen - Erinnerung wiederholt, bis geschafft; Eltern-Nachricht, wenn nicht
geschafft; laufende Liste im Status (Kachel leuchtet, Mein Tag öffnet von selbst)."""
import copy
import os
import shutil
import sys
import tempfile
import threading
import unittest
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import meintag  # noqa: E402
from test_62 import LISTE, MORGEN  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402


class ImHub(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-6958-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(MORGEN)                                  # 06:40, Liste ab 06:45 bis 07:30
        self.hub = neuer_hub(self.ordner, self.uhr)
        self.hub.einstellungen_aendern({"meintag": copy.deepcopy(LISTE)})
        self.texte = []
        alt = self.hub.familie.nachricht
        self.hub.familie.nachricht = lambda text, **k: (self.texte.append(text), alt(text, **k))
        self.eltern = []
        self.hub.telegram.melde_eltern = lambda art, text: self.eltern.append((art, text))

    def takt_bis(self, minuten):
        for _ in range(minuten * 2):                           # Takt alle 30 Sekunden
            self.uhr.weiter(30)
            self.hub._meintag_takt(self.uhr())

    def test_wiederholt_bis_geschafft(self):
        self.assertIsNone(self.hub.status()["routine"], "vor Beginn läuft nichts")
        self.takt_bis(6)                                        # 06:46
        self.assertEqual(self.texte, ["Morgen – los geht's!"])
        r = self.hub.status()["routine"]
        self.assertEqual((r["nr"], r["offen"], r["anzahl"], r["oeffnen"], r["runde"]), (1, 2, 2, True, 0))
        self.takt_bis(10)                                       # 06:56
        self.assertEqual(self.texte[1:], ["Morgen – noch 2 Sachen offen!"])
        self.assertEqual(self.hub.status()["routine"]["runde"], 1)
        self.hub.meintag_abhaken(1, 0)
        self.takt_bis(10)                                       # 07:06
        self.assertEqual(self.texte[2:], ["Morgen – noch 1 Sache offen!"])
        self.hub.meintag_abhaken(1, 1)                          # geschafft
        self.assertIsNone(self.hub.status()["routine"])
        self.takt_bis(40)                                       # bis 07:46
        self.assertEqual(len(self.texte), 3, "geschafft: keine Erinnerung mehr")
        self.assertFalse([t for a, t in self.eltern if "nicht geschafft" in t])

    def test_eltern_wenn_nicht_geschafft(self):
        self.takt_bis(60)                                       # 07:40
        self.assertEqual(len(self.texte), 5, "Beginn + 4 Wiederholungen (06:45 … 07:25)")
        offen = [t for a, t in self.eltern if a == "meintag" and "nicht geschafft" in t]
        self.assertEqual(offen, ["⏰ Morgen nicht geschafft (0 von 2 erledigt, fertig um 07:30 Uhr)."])
        self.assertIsNone(self.hub.status()["routine"])

    def test_ohne_erinnern_still_aber_sichtbar(self):
        m = copy.deepcopy(LISTE)
        m["routinen"][0]["erinnern"] = False
        m["routinen"][0]["oeffnen"] = False
        self.hub.einstellungen_aendern({"meintag": m})
        self.takt_bis(60)
        self.assertEqual(self.texte, [])
        self.assertEqual(self.eltern, [])

    def test_oeffnen_wird_geprueft(self):
        m = copy.deepcopy(LISTE)
        m["routinen"][0]["oeffnen"] = "ja"
        with self.assertRaises(ValueError):
            meintag.pruefe(m)


class AmFernseher(unittest.TestCase):
    def test_mein_tag_oeffnet_von_selbst(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("kein Playwright")
        from fernsehfranzi import web
        from test_spiele_wie_am_geraet import port_frei
        if not port_frei(8765):
            self.skipTest("Port 8765 belegt")
        ordner = tempfile.mkdtemp(prefix="ff-6958w-")
        self.addCleanup(shutil.rmtree, ordner, True)
        uhr = Uhr(datetime(2026, 11, 18, 6, 50))
        hub = neuer_hub(ordner, uhr)
        hub.einstellungen_aendern({"meintag": copy.deepcopy(LISTE)})
        srv = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"), os.path.join(ordner, "z"), ("127.0.0.1", 8765))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            s = b.new_page(viewport={"width": 1280, "height": 720})
            fehler = []
            s.on("pageerror", lambda e: fehler.append(str(e)))
            s.goto("http://127.0.0.1:8765/")
            s.wait_for_selector(".overlay .mt-kopf, .overlay h2:has-text('Morgen'), .overlay:has-text('Anziehen')", timeout=15000)
            s.keyboard.press("Escape")
            s.wait_for_selector('.kachel.routine-jetzt .kachel-hinweis.routine:has-text("Morgen · 2")')   # Kachel oder ihr Ordner
            s.wait_for_timeout(5000)                            # gleiche Runde: nicht noch einmal öffnen
            self.assertEqual(s.locator(".overlay:has-text('Anziehen')").count(), 0)
            self.assertEqual(fehler, [])
            b.close()


if __name__ == "__main__":
    unittest.main()
