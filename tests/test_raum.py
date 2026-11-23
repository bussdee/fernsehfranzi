"""4.3 Spielraum: QR-Code, Raum, Spieler und die fünf Handy-Spiele (reine Logik mit Testuhr)."""
import os
import random
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))

from fernsehfranzi import qr, raum  # noqa: E402

try:
    import cv2
    import numpy
except ImportError:
    cv2 = None


class Uhr:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def weiter(self, s):
        self.t += s


def neuer_raum(handys=2, **kw):
    uhr = Uhr()
    r = raum.Raum("Kind", monoton=uhr, zufall=random.Random(7), **kw)
    geheim = {}
    for n in range(handys):
        sid, g = r.beitreten("Spieler%d" % n)
        geheim[sid] = g
    return r, uhr, geheim


class QrCode(unittest.TestCase):
    @unittest.skipIf(cv2 is None, "OpenCV fehlt (nur zum Prüfen am PC)")
    def test_lesbar_alle_versionen(self):
        erkenner = cv2.QRCodeDetector()
        for text in ["http://fernseher.beispiel:8767/mitspielen?r=AbCdEfGhIjKlMnOp", "Grüße äöü", "x" * 213, "A"]:
            m = qr.matrix(text)
            g, s, rand = len(m), 6, 4
            bild = numpy.full(((g + 2 * rand) * s,) * 2, 255, numpy.uint8)
            for y, zeile in enumerate(m):
                for x, d in enumerate(zeile):
                    if d:
                        bild[(y + rand) * s:(y + rand + 1) * s, (x + rand) * s:(x + rand + 1) * s] = 0
            gelesen, _, _ = erkenner.detectAndDecode(bild)
            self.assertEqual(gelesen, text)

    def test_svg_und_grenzen(self):
        self.assertTrue(qr.svg("http://x").startswith("<svg"))
        self.assertEqual(len(qr.matrix("A")), 21)
        with self.assertRaises(ValueError):
            qr.matrix("x" * 214)


class RaumUndSpieler(unittest.TestCase):
    def test_beitreten_namen_symbole_grenzen(self):
        r, _, _ = neuer_raum(0)
        sid, geheim = r.beitreten("  Papa\n ", "🐼")
        self.assertEqual(r.spieler[sid]["name"], "Papa")
        self.assertEqual(r.spieler[sid]["symbol"], "🐼")
        sid2, _ = r.beitreten("papa", "🐼")
        self.assertEqual(r.spieler[sid2]["name"], "papa 2")
        self.assertNotEqual(r.spieler[sid2]["symbol"], "🐼")
        self.assertEqual(r.spieler_von(geheim), sid)
        self.assertIsNone(r.spieler_von("falsch"))
        with self.assertRaises(ValueError):
            r.beitreten("   ")
        for n in range(4):
            r.beitreten("X%d" % n)
        with self.assertRaisesRegex(ValueError, "voll"):
            r.beitreten("Zu viel")
        self.assertEqual(len(r.code), 4)
        self.assertGreaterEqual(len(r.token), 16)

    def test_zu_wenige_spieler(self):
        r, _, _ = neuer_raum(0)
        with self.assertRaisesRegex(ValueError, "Handy"):
            r.starte("malen")
        with self.assertRaises(ValueError):
            r.starte("gibtsnicht")
        self.assertFalse(next(s for s in r.tv_zustand()["spiele"] if s["id"] == "buzzer")["geht"])


class Spiele(unittest.TestCase):
    def test_buzzer(self):
        r, uhr, _ = neuer_raum(2)
        a, b = [s["id"] for s in r.handys()]
        r.starte("buzzer")
        self.assertEqual(r.zustand_fuer(a)["ansicht"], "buzzer")
        r.aktion(a, {"art": "buzz"})
        r.aktion(b, {"art": "buzz"})                              # zu spät
        self.assertEqual(r.zustand_fuer(a)["ansicht"], "wahl")
        self.assertEqual(r.zustand_fuer(b)["ansicht"], "warten")
        spiel = r.spiel
        falsch = next(i for i, o in enumerate(spiel.optionen) if o != spiel.richtig)
        r.aktion(a, {"art": "wahl", "index": falsch})            # falsch -> a gesperrt, Buzzer wieder offen
        self.assertEqual(spiel.phase, "frage")
        self.assertEqual(r.zustand_fuer(a)["ansicht"], "warten")
        r.aktion(b, {"art": "buzz"})
        r.aktion(b, {"art": "wahl", "index": spiel.optionen.index(spiel.richtig)})
        self.assertEqual(r.spieler[b]["punkte"], 1)
        self.assertEqual(spiel.phase, "aufloesung")
        uhr.weiter(6)
        r.tick()
        self.assertEqual(spiel.nr, 1)
        r.tv_aktion({"art": "spieler", "daten": {"art": "buzz"}})  # das Kind am Fernseher buzzert
        self.assertEqual(spiel.buzzer_von, "tv")
        self.assertEqual(r.tv_zustand()["tv_spieler"]["ansicht"], "wahl")
        for _ in range(40):                                       # bis zum Ende durchlaufen lassen
            uhr.weiter(30)
            r.tick()
        self.assertIsNone(r.spiel)
        self.assertEqual(r.zustand_fuer(a)["ansicht"], "ergebnis")

    def test_quizrennen_schnellster_zwei_felder_und_ziel(self):
        r, uhr, _ = neuer_raum(2)
        a, b = [s["id"] for s in r.handys()]
        r.starte("quiz", paket="einmaleins")
        spiel = r.spiel
        for runde in range(20):
            if not r.spiel:
                break
            gut = spiel.optionen.index(spiel.richtig)
            uhr.weiter(1)
            r.aktion(a, {"art": "wahl", "index": gut})
            uhr.weiter(1)
            r.aktion(b, {"art": "wahl", "index": gut})
            r.tv_aktion({"art": "spieler", "daten": {"art": "wahl", "index": (gut + 1) % 4}})
            r.tick()
            if runde == 0:
                self.assertEqual(spiel.felder[a], 2, "schnellste richtige Antwort: zwei Felder")
                self.assertEqual(spiel.felder[b], 1)
                self.assertEqual(spiel.felder["tv"], 0)
            uhr.weiter(6)
            r.tick()
        self.assertIsNone(r.spiel)
        self.assertIn("Im Ziel", r.letztes["text"])
        self.assertEqual(r.letztes["rangliste"][0]["id"], a)

    def test_quiz_leicht_hat_mehr_zeit_und_eigene_fragen(self):
        eigene = [{"frage": "Wie heißt unser Hund?", "richtig": "Bello", "falsch": ["Rex", "Lumpi", "Hasso"]}]
        r, uhr, _ = neuer_raum(1, eigene_fragen=eigene)
        sid = r.handys()[0]["id"]
        r.spieler[sid]["leicht"] = True
        r.starte("quiz", paket="eigene")
        self.assertEqual(r.spiel.frage, "Wie heißt unser Hund?")
        uhr.weiter(18)
        r.aktion(sid, {"art": "wahl", "index": r.spiel.optionen.index("Bello")})
        self.assertIn(sid, r.spiel.antworten, "leicht: nach 18 s noch erlaubt")

    def test_malen_und_raten(self):
        r, uhr, _ = neuer_raum(2)
        r.starte("malen")
        spiel = r.spiel
        maler = spiel.maler
        anderer = next(s["id"] for s in r.handys() if s["id"] != maler)
        self.assertEqual(r.zustand_fuer(maler)["ansicht"], "malen")
        self.assertEqual(r.zustand_fuer(maler)["wort"], spiel.wort)
        self.assertNotIn("wort", r.zustand_fuer(anderer))
        r.aktion(maler, {"art": "striche", "striche": [{"p": [10, 10, 500, 500, 9999, -5], "f": "#111111", "d": 6, "neu": True}]})
        self.assertEqual(spiel.striche[0]["p"], [10, 10, 500, 500, 1000, 0])
        r.aktion(anderer, {"art": "striche", "striche": [{"p": [1, 1]}]})       # nur der Maler malt
        self.assertEqual(len(spiel.striche), 1)
        r.aktion(anderer, {"art": "wahl", "index": spiel.optionen.index(spiel.wort)})
        r.tv_aktion({"art": "spieler", "daten": {"art": "wahl", "index": spiel.optionen.index(spiel.wort)}})
        r.tick()                                                  # alle haben geraten
        self.assertEqual(spiel.phase, "aufloesung")
        self.assertEqual(r.spieler[anderer]["punkte"], 3)
        self.assertEqual(r.spieler["tv"]["punkte"], 2)
        self.assertEqual(r.spieler[maler]["punkte"], 2)
        self.assertEqual(len(spiel.striche_ab(0)), 1)

    def test_raumschiff_gemeinsam(self):
        r, uhr, _ = neuer_raum(2)
        r.starte("raumschiff", stufe=2)
        spiel = r.spiel
        alle_knoepfe = sorted(k for ks in spiel.knoepfe.values() for k in ks)
        self.assertEqual(alle_knoepfe, sorted(a for a, _ in raum.AKTIONEN_RS), "jeder Schalter genau einmal")
        self.assertEqual(spiel.handbuch["tv"], [], "Handbuch nur auf den Handys")
        self.assertEqual(sum(len(h) for h in spiel.handbuch.values()), 16)
        for _ in range(8):
            richtig = spiel.regeln[spiel.stoerung]
            wer = next(s for s, ks in spiel.knoepfe.items() if richtig in ks)
            andere = next(s for s, ks in spiel.knoepfe.items() if richtig not in ks and ks) if len(spiel.knoepfe) > 1 else None
            if andere:                                          # fremder Schalter zählt nicht
                r.aktion(andere, {"art": "knopf", "id": richtig})
                self.assertEqual(spiel.phase, "stoerung")
            if wer == "tv":
                r.tv_aktion({"art": "spieler", "daten": {"art": "knopf", "id": richtig}})
            else:
                r.aktion(wer, {"art": "knopf", "id": richtig})
            if r.spiel:
                uhr.weiter(3)
                r.tick()
        self.assertIsNone(r.spiel)
        self.assertIn("Gerettet", r.letztes["text"])

    def test_raumschiff_verloren_durch_zeit(self):
        r, uhr, _ = neuer_raum(1)
        r.starte("raumschiff")
        for _ in range(3):
            uhr.weiter(31)
            r.tick()
            uhr.weiter(3)
            r.tick()
        self.assertIsNone(r.spiel)
        self.assertIn("notlanden", r.letztes["text"])

    def test_ton_treffer(self):
        r, uhr, geheim = neuer_raum(2)
        a, b = [s["id"] for s in r.handys()]
        r.starte("ton")
        spiel = r.spiel
        self.assertEqual(spiel.saenger, spiel.reihe[0])
        self.assertEqual(len(r.tv_zustand()["tv"]["folge"]), 3)
        r.tv_aktion({"art": "bereit"})
        self.assertEqual(spiel.phase, "singen")
        saenger = spiel.saenger
        r.tv_aktion({"art": "ton_ergebnis", "treffer": [True, True, True]})
        self.assertEqual(r.spieler[saenger]["punkte"], 5, "3 Treffer + 2 für alle richtig")
        zuhoerer = next(s for s in (a, b) if s != saenger)
        self.assertEqual(r.zustand_fuer(zuhoerer)["ansicht"], "daumen")
        r.aktion(zuhoerer, {"art": "daumen"})
        r.aktion(zuhoerer, {"art": "daumen"})                     # nur einmal
        self.assertEqual(r.spieler[saenger]["punkte"], 6)
        uhr.weiter(7)
        r.tick()
        self.assertEqual(spiel.phase, "vorspielen")
        self.assertNotEqual(spiel.saenger, saenger)
        r.tv_aktion({"art": "kein_mikro"})
        self.assertIsNone(r.spiel)
        self.assertIn("Mikrofon", r.letztes["text"])

    def test_rakete_und_klatsch(self):
        """4.4: Mikro-Spiele - der Fernseher misst und meldet, die anderen geben Daumen."""
        r, uhr, _ = neuer_raum(1)
        a = r.handys()[0]["id"]
        r.starte("rakete")
        spiel = r.spiel
        self.assertEqual(spiel.phase, "countdown")
        uhr.weiter(3.1)
        r.tick()
        self.assertEqual(spiel.phase, "messen")
        dran = spiel.dran
        r.tv_aktion({"art": "ergebnis", "hoehe": 734})
        self.assertEqual(r.spieler[dran]["punkte"], 7)
        self.assertEqual(r.tv_zustand()["tv"]["rekord"], 734)
        anderer = a if dran == "tv" else "tv"
        if anderer == "tv":
            r.tv_aktion({"art": "spieler", "daten": {"art": "daumen"}})
        else:
            r.aktion(anderer, {"art": "daumen"})
        self.assertEqual(r.spieler[dran]["punkte"], 8)
        r.zur_lobby()
        r.starte("klatsch")
        spiel = r.spiel
        self.assertEqual(len(spiel.abstaende), 3, "Runde 1: vier Klatscher")
        r.tv_aktion({"art": "bereit"})
        dran = spiel.dran
        r.tv_aktion({"art": "ergebnis", "treffer": 4})
        self.assertEqual(r.spieler[dran]["punkte"], 6, "alle im Takt: 4 + 2")
        uhr.weiter(7)
        r.tick()
        self.assertEqual(spiel.phase, "vorspielen")
        uhr.weiter(1)
        r.tv_aktion({"art": "bereit"})
        uhr.weiter(20)
        r.tick()                                               # nichts gemeldet -> 0 Treffer, weiter
        self.assertEqual(spiel.phase, "daumen")
        r.tv_aktion({"art": "kein_mikro"})
        self.assertIsNone(r.spiel)


if __name__ == "__main__":
    unittest.main()
