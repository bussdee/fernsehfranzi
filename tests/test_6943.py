"""6.9.43: Franzi aus den gezeichneten Ebenen - alle Teile, die gemeinsam.js zusammensetzt, liegen im Web-Ordner."""
import os
import re
import unittest

REPO = os.path.join(os.path.dirname(__file__), "..")
JS = open(os.path.join(REPO, "web", "js", "gemeinsam.js"), encoding="utf-8").read()
ORDNER = os.path.join(REPO, "web", "bilder", "franzi")


class FranziBilder(unittest.TestCase):
    def test_alle_teile_da(self):
        teile = re.search(r"const FRANZI_TEILE = \{(.*?)\n\};", JS, re.S).group(1)
        farben = re.findall(r'"(\w+)"', re.search(r"const FRANZI_FARBEN = \[(.*?)\];", JS).group(1))
        self.assertEqual(farben[0], "grau", "Level 1 ist grau")
        arme = set(re.findall(r'"((?:links|rechts)-(?:oben|unten))"', teile))
        augen = set(re.findall(r'augen: "([\w-]+)"', teile))
        muender = set(re.findall(r'mund: "([\w-]+)"', teile))
        self.assertTrue(arme and augen and muender)
        fehlt = [n for n in ["koerper-%s" % f for f in farben] + ["arm-%s-%s" % (a, f) for a in arme for f in farben] +
                 ["augen-%s" % a for a in augen] + ["mund-%s" % m for m in muender]
                 if not os.path.isfile(os.path.join(ORDNER, n + ".png"))]
        self.assertEqual(fehlt, [])

    def test_bilder_sind_512_quadrate(self):
        for name in os.listdir(ORDNER):
            with open(os.path.join(ORDNER, name), "rb") as f:
                kopf = f.read(24)
            self.assertEqual(kopf[:8], b"\x89PNG\r\n\x1a\n", name)
            self.assertEqual((int.from_bytes(kopf[16:20], "big"), int.from_bytes(kopf[20:24], "big")), (512, 512), name)


if __name__ == "__main__":
    unittest.main()
