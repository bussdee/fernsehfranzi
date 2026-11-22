"""4.2 Scraper: Bilder aus libretro-thumbnails (Attrappe statt GitHub), Namen finden, Spieleliste ergänzen ohne Verluste."""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import scraper  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 30
BILDER = {"Named_Boxarts": ["Great Giana Sisters, The (Europe)", "Track _ Field (USA, Europe)", "Arkanoid (Europe)"],
          "Named_Titles": ["Zoid (Europe)"], "Named_Snaps": ["Pitfall (1984)(Activision)", "Giana Sisters (1987)(Rainbow Arts)"]}


class GitHub:
    """Antwortet wie api.github.com (Bäume) und raw.githubusercontent.com (Bilder)."""
    def __init__(self):
        self.abrufe = []

    def __call__(self, anfrage, timeout=30):
        url = anfrage.full_url
        self.abrufe.append(url)
        if "/git/trees/master" in url:
            daten = {"tree": [{"path": o, "type": "tree", "sha": "sha-" + o} for o in BILDER] + [{"path": "README.md", "type": "blob"}]}
        elif "/git/trees/sha-" in url:
            ordner = url.rsplit("sha-", 1)[1]
            daten = {"tree": [{"path": n + ".png", "type": "blob"} for n in BILDER[ordner]]}
        else:
            ordner, name = urllib.parse.unquote(url).rsplit("/", 2)[-2:]
            if name[:-4] not in BILDER.get(ordner, []):
                raise OSError("404")
            return io.BytesIO(PNG)
        return io.BytesIO(json.dumps(daten).encode())


class Scraper(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-scr-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.roms = os.path.join(self.ordner, "roms")
        self.listen = os.path.join(self.ordner, "gamelists")
        self.bilder = os.path.join(self.ordner, "images")
        self.daten = os.path.join(self.ordner, "daten")
        os.makedirs(os.path.join(self.roms, "c64", "TEMP"))
        os.makedirs(self.daten)
        for n in ("Giana Sisters.tap", "Track & Field (1983)(Konami).zip", "Pitfall (1984)(Activision).zip",
                  "Tron (19xx)(THS).zip", "Arkanoid.tap", "liesmich.txt", ".versteckt.tap"):
            open(os.path.join(self.roms, "c64", n), "wb").close()
        os.makedirs(os.path.join(self.listen, "c64"))
        with open(os.path.join(self.listen, "c64", "gamelist.xml"), "w", encoding="utf-8") as f:   # schon gespielt, eigener Name
            f.write('<?xml version="1.0"?>\n<gameList>\n\t<game>\n\t\t<path>./Arkanoid.tap</path>\n\t\t<name>Arkanoid!</name>\n'
                    '\t\t<playcount>7</playcount>\n\t\t<favorite>true</favorite>\n\t</game>\n</gameList>\n')
        self.github = GitHub()

    def lauf(self, retro=False):
        return scraper.laufen(self.roms, self.listen, self.bilder, self.daten, oeffne=self.github, laeuft_retro=lambda: retro)

    def test_namen_finden(self):
        self.assertEqual(scraper.passendes_bild("Giana Sisters", BILDER), ("Named_Snaps", "Giana Sisters (1987)(Rainbow Arts)"))
        self.assertEqual(scraper.passendes_bild("Track & Field (1983)(Konami)", BILDER), ("Named_Boxarts", "Track _ Field (USA, Europe)"))
        self.assertEqual(scraper.passendes_bild("Pitfall (1984)(Activision)", BILDER), ("Named_Snaps", "Pitfall (1984)(Activision)"))
        self.assertEqual(scraper.passendes_bild("Great Giana Sisters", BILDER)[1], "Great Giana Sisters, The (Europe)")
        self.assertIsNone(scraper.passendes_bild("Tron (19xx)(THS)", BILDER))
        self.assertEqual(scraper.vereinfacht("AmigaCD32_DerClou"), scraper.vereinfacht("Clou!, Der"))
        self.assertEqual(scraper.schoener_name("Great Giana Sisters, The (Europe) [cr]"), "The Great Giana Sisters")

    def test_bilder_holen_und_liste_ergaenzen(self):
        s = self.lauf()
        self.assertFalse(s["laeuft"])
        c64 = s["systeme"]["c64"]
        self.assertEqual((c64["gesamt"], c64["neu"], c64["ohne"]), (5, 4, ["Tron"]))
        wurzel = ET.parse(os.path.join(self.listen, "c64", "gamelist.xml")).getroot()
        spiele = {g.findtext("path"): g for g in wurzel.iter("game")}
        self.assertEqual(spiele["./Arkanoid.tap"].findtext("name"), "Arkanoid!", "eigener Name bleibt")
        self.assertEqual(spiele["./Arkanoid.tap"].findtext("playcount"), "7", "gespielt bleibt")
        self.assertEqual(spiele["./Arkanoid.tap"].findtext("favorite"), "true")
        self.assertEqual(spiele["./Track & Field (1983)(Konami).zip"].findtext("name"), "Track & Field")
        bild = spiele["./Giana Sisters.tap"].findtext("image")
        self.assertEqual(bild, "~/.emulationstation/downloaded_images/c64/Giana Sisters-image.png")
        with open(os.path.join(self.bilder, "c64", "Giana Sisters-image.png"), "rb") as f:
            self.assertEqual(f.read(), PNG)
        self.assertNotIn("./liesmich.txt", spiele)
        self.assertNotIn("./.versteckt.tap", spiele)
        with open(os.path.join(self.daten, "scraper.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["systeme"]["c64"]["neu"], 4)

    def test_zweiter_lauf_holt_nichts_neu_und_nutzt_den_cache(self):
        self.lauf()
        for g in ET.parse(os.path.join(self.listen, "c64", "gamelist.xml")).getroot().iter("game"):   # Bilder „wirklich da“
            bild = g.findtext("image")
            if bild:
                ziel = os.path.join(self.bilder, "c64", os.path.basename(bild))
                g.find("image").text = ziel
        baum = ET.parse(os.path.join(self.listen, "c64", "gamelist.xml"))
        for g in baum.getroot().iter("game"):
            if g.findtext("image"):
                g.find("image").text = os.path.join(self.bilder, "c64", os.path.basename(g.findtext("image")))
        baum.write(os.path.join(self.listen, "c64", "gamelist.xml"))
        vorher = len(self.github.abrufe)
        s = self.lauf()
        self.assertEqual(s["systeme"]["c64"]["neu"], 0)
        self.assertEqual(s["systeme"]["c64"]["ohne"], ["Tron"])
        self.assertFalse([u for u in self.github.abrufe[vorher:] if "api.github.com" in u], "Bilderliste aus dem Cache")

    def test_nicht_wenn_retropie_laeuft(self):
        s = self.lauf(retro=True)
        self.assertIn("RetroPie läuft", s["fehler"])
        self.assertEqual(self.github.abrufe, [])
        self.assertFalse(os.path.exists(os.path.join(self.bilder, "c64")))


class ScraperImHub(unittest.TestCase):
    def test_knopf_und_nachts(self):
        ordner = tempfile.mkdtemp(prefix="ff-scr-hub-")
        self.addCleanup(shutil.rmtree, ordner, True)
        uhr = Uhr(datetime(2026, 11, 23, 3, 59, 50))
        hub = neuer_hub(ordner, uhr)
        self.assertTrue(hub.scraper_starten())
        self.assertIn(("scraper",), hub.system.aufrufe)
        hub.system.laeuft = True
        with self.assertRaisesRegex(ValueError, "RetroPie läuft"):
            hub.scraper_starten()
        hub.system.laeuft = False
        hub.system.aufrufe.clear()
        hub.tick(5)
        self.assertNotIn(("scraper",), hub.system.aufrufe, "vor 4 Uhr nicht")
        uhr.weiter(15)
        hub.tick(5)
        uhr.weiter(60)
        hub.tick(5)
        self.assertEqual(hub.system.aufrufe.count(("scraper",)), 1, "um 4 Uhr genau einmal")


if __name__ == "__main__":
    unittest.main()
