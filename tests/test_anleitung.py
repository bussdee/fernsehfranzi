"""Anleitung (PDF) für die Familie: vorhanden, aktuell, auf der Eltern-Seite verlinkt und ohne private Daten."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "werkzeuge"))

import anleitung_pdf  # noqa: E402


class Anleitung(unittest.TestCase):
    def test_pdf_passt_zur_html_fassung(self):
        pdf = os.path.join(REPO, "web", "anleitung.pdf")
        self.assertTrue(os.path.getsize(pdf) > 20000)
        with open(os.path.join(REPO, "web", "anleitung.quelle")) as f:
            self.assertEqual(f.read().strip(), anleitung_pdf.pruefsumme(), "make anleitung ausführen")

    def test_verlinkt_und_im_heimnetz_erreichbar(self):
        with open(os.path.join(REPO, "web", "js", "eltern-handy.js"), encoding="utf-8") as f:   # 3.3: neue Eltern-Seite
            inhalt = f.read()
        self.assertGreaterEqual(inhalt.count('"/anleitung.pdf"'), 2)
        self.assertIn('"/kinder-anleitung.pdf"', inhalt)
        with open(os.path.join(REPO, "server", "fernsehfranzi", "web.py"), encoding="utf-8") as f:
            self.assertIn('("/anleitung.pdf", "/kinder-anleitung.pdf")', f.read())

    def test_kinder_anleitung_ohne_verstellen(self):
        with open(anleitung_pdf.KINDER_QUELLE, encoding="utf-8") as f:
            text = f.read()
        for stichwort in ("Schnell speichern", "Xbox</span> + <span class=\"taste\">RB", "LB", "Spiel beenden", "GELB"):
            self.assertIn(stichwort, text)
        for verboten in ("PIN", "Einstellungen", "Entsperr", "Herunterfahren", "passkey", "Elternbereich"):
            self.assertNotIn(verboten, text, "nichts, womit man etwas verstellen kann")
        self.assertTrue(os.path.getsize(anleitung_pdf.KINDER_ZIEL) > 20000)

    def test_beschreibt_die_wichtigen_dinge(self):
        with open(anleitung_pdf.QUELLE, encoding="utf-8") as f:
            text = f.read()
        for stichwort in ("Elternbereich", "Eltern-Seite", "PIN vergessen", "Lern-Check", "Bass-Song", "Nachricht",
                          "Nachtruhe", "Sperrzeit", "Gute Nacht", "make v3-deploy", "make admin-einrichten", "Stecker"):
            self.assertIn(stichwort, text)


if __name__ == "__main__":
    unittest.main()
