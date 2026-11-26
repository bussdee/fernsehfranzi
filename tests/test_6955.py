"""6.9.55: Gegenstände je Raum (gezeichnet), nur im passenden Raum aufstellbar."""
import os
import re
import sys
import unittest
from datetime import datetime

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "server"))
from fernsehfranzi import franzi  # noqa: E402

TAG = datetime(2026, 11, 28, 15)
EIN = franzi.einstellungen({"aktiv": True})


class Dinge(unittest.TestCase):
    def test_jedes_raum_ding_hat_zeichnung_und_groesse(self):
        dinge = open(os.path.join(REPO, "web", "js", "spiele", "dinge.js"), encoding="utf-8").read()
        franzi_js = open(os.path.join(REPO, "web", "js", "spiele", "franzi.js"), encoding="utf-8").read()
        gezeichnet = set(re.findall(r'^  "([a-z-]+)": svg\(', dinge, re.M))
        for item, raeume in franzi.NUR_IN.items():
            self.assertIn(item, franzi.KATALOG_IDS, item)
            png = os.path.exists(os.path.join(REPO, "web", "bilder", "dinge", item + ".png"))   # 6.9.59: gezeichnete Bilder
            self.assertTrue(item in gezeichnet or png, item)
            self.assertIn('"%s": [' % item, franzi_js, "Größe in DING fehlt: " + item)
            for r in raeume:
                self.assertIn(r, franzi.KATALOG_IDS, r)

    def test_nur_im_passenden_raum(self):
        z, _ = franzi.besuch(EIN, {}, TAG)
        z["besitz"] += ["moebel-mikrofon", "raum-probe"]
        with self.assertRaises(ValueError):
            franzi.setzen(z, TAG, "moebel-mikrofon", 30, 10)            # im Kinderzimmer nicht
        z = franzi.raum_wechseln(z, TAG, "raum-probe")
        z = franzi.setzen(z, TAG, "moebel-mikrofon", 30, 10)
        self.assertIn("moebel-mikrofon", z["zimmer"]["raum-probe"])
        tv = franzi.fuer_tv(EIN, z, TAG, 0)
        self.assertEqual(next(k for k in tv["katalog"] if k["id"] == "moebel-mikrofon")["nur_in"], ["raum-probe"])


if __name__ == "__main__":
    unittest.main()
