"""6.8.12: Animations-Stufe aus / sparsam / hoch in der Design-Einstellung."""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
from fernsehfranzi import design  # noqa: E402


class AnimationsStufe(unittest.TestCase):
    def test_vorgabe_sparsam(self):
        self.assertEqual(design.einstellungen({})["animation"], "sparsam")
        st = design.fuer_startseite({}, {}, datetime.datetime(2026, 11, 24, 12, 0))
        self.assertEqual(st["animation"], "sparsam")

    def test_stufen(self):
        for w in ("aus", "sparsam", "hoch"):
            self.assertEqual(design.pruefe({"animation": w})["animation"], w)
        with self.assertRaises(ValueError):
            design.pruefe({"animation": "turbo"})


if __name__ == "__main__":
    unittest.main()
