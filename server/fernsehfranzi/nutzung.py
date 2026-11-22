"""FernsehFranzi 4.0 - Nutzungs-Statistik: was wurde wann wie lange benutzt (für die Eltern-Seite).

Gespeichert wird in nutzung.json je Tag, App und Stunde: offen-Sekunden und aktive Sekunden (mit Tastendruck).
62 Tage, danach wird weggeworfen. Schreiben höchstens alle 60 s (die SD-Karte soll lange halten).
    {"2026-11-22": {"spiel-snake": {"15": [600, 540]}, "gute-nacht": {"19": [1800, 60]}}}
"""
from . import daten

TAGE = 62


class Nutzung:
    def __init__(self, pfad, monoton):
        self.pfad, self.monoton = pfad, monoton
        self.daten = daten.lies_json(pfad, {}) or {}
        self._gespeichert = monoton()

    def zaehle(self, jetzt, app_id, sekunden, aktiv):
        if not app_id or sekunden <= 0:
            return
        sekunden = min(int(sekunden), 60)
        stunde = self.daten.setdefault(jetzt.date().isoformat(), {}).setdefault(app_id, {}).setdefault(
            "%02d" % jetzt.hour, [0, 0])
        stunde[0] += sekunden
        if aktiv:
            stunde[1] += sekunden
        if self.monoton() - self._gespeichert >= 60:
            self.speichern()

    def speichern(self):
        for alt in sorted(self.daten)[:-TAGE]:
            del self.daten[alt]
        daten.schreibe_json(self.pfad, self.daten)
        self._gespeichert = self.monoton()

    def auszug(self, tage=31):
        return {tag: self.daten[tag] for tag in sorted(self.daten)[-tage:]}
