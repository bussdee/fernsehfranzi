"""6.9.57: Antennen blinken kurz a/b, Rot/Grün als Rückmeldung (franziBlinken), Gold-Deluxe mit Glanzstreifen."""
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


class Antennen(unittest.TestCase):
    def test_blinken_und_glanz(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("kein Playwright")
        from fernsehfranzi import web
        from test_spiele_wie_am_geraet import port_frei
        if not port_frei(8765):
            self.skipTest("Port 8765 belegt")
        ordner = tempfile.mkdtemp(prefix="ff-6957-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(datetime(2026, 11, 28, 15)))
        hub.einstellungen["franzi"] = {"aktiv": True}
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
            s.wait_for_selector(".kachel")
            r = s.evaluate("""async () => {
                const g = await import("/js/gemeinsam.js");
                const box = document.createElement("div"); document.body.append(box);
                const gold = g.franzi("froh", "", {farbe: "gold"}), grau = g.franzi("genervt", "", {farbe: "grau"});
                box.append(gold, grau);
                const sicht = (f, sel) => getComputedStyle(f.querySelector(sel)).display;
                const vorher = [gold.className, sicht(gold, ".f-ant-a.f-ant-gruen"), sicht(gold, ".f-ant-a.f-ant-rot"), sicht(grau, ".f-ant-a.f-ant-rot")];
                g.franziBlinken("rot");
                const neu = g.franzi("froh", "", {farbe: "grau"}); box.append(neu);
                return {vorher, nachher: [gold.className, sicht(gold, ".f-ant-a.f-ant-rot"), sicht(gold, ".f-ant-a.f-ant-gruen")],
                        neu: neu.className, antennen: gold.querySelectorAll(".f-antenne image").length,
                        glanzGold: gold.querySelectorAll(".f-glanz mask image").length, glanzGrau: grau.querySelectorAll(".f-glanz").length};
            }""")
            self.assertIn("f-licht-gruen", r["vorher"][0])
            self.assertEqual(r["vorher"][1:], ["inline", "none", "inline"])
            self.assertIn("f-blink-rot", r["nachher"][0])
            self.assertEqual(r["nachher"][1:], ["inline", "none"])
            self.assertIn("f-blink-rot", r["neu"], "neu gezeichnete Franzi übernimmt das laufende Blinken")
            self.assertEqual(r["antennen"], 4)
            self.assertGreaterEqual(r["glanzGold"], 2)
            self.assertEqual(r["glanzGrau"], 0)
            s.wait_for_timeout(1500)
            self.assertEqual(s.locator(".f-blink-rot").count(), 0)
            gold = s.evaluate("""async () => {
                const im = new Image(); im.src = "/bilder/franzi/koerper-gold.png"; await im.decode();
                const c = document.createElement("canvas"); c.width = im.width; c.height = im.height;
                const x = c.getContext("2d"); x.drawImage(im, 0, 0);
                const d = x.getImageData(0, 0, c.width, c.height).data; let r = 0, b = 0, n = 0; const hell = [];
                for (let i = 0; i < d.length; i += 16) if (d[i + 3] > 200) { r += d[i]; b += d[i + 2]; n++; hell.push(d[i] + d[i + 1] + d[i + 2]); }
                hell.sort((p, q) => p - q);
                return {warm: (r - b) / n, kontrast: hell[Math.floor(hell.length * .98)] - hell[Math.floor(hell.length * .3)]};
            }""")
            self.assertGreater(gold["warm"], 60, "Gold muss deutlich warm sein, nicht cremeweiß")
            self.assertGreater(gold["kontrast"], 150, "Metall braucht Kontrast")
            self.assertEqual(fehler, [])
            b.close()


if __name__ == "__main__":
    unittest.main()
