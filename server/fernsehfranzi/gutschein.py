"""FernsehFranzi 3.5 - Gutschein-Codes.

Die Eltern legen 6-stellige Codes an und drucken sie aus; das Kind löst sie am Fernseher ein.
- "normal":    +X Minuten auf den allgemeinen Timer, nur außerhalb von Sperrzeiten einlösbar
- "besonders": X Minuten lang gehen alle Apps (auch in Sperrzeiten) und nichts zählt
Jeder Code gilt einmal. Gegen Raten: nach 5 falschen Codes 10 Minuten Pause.
Datei: gutscheine.json im Datenordner.
"""
import secrets

from . import daten

ARTEN = ("normal", "besonders")
FEHLER_MAX = 5
PAUSE_S = 10 * 60
HOECHSTENS = 100            # offene Codes


class Gutscheine:
    def __init__(self, pfad):
        self.pfad = pfad
        self.daten = daten.lies_json(pfad, {}) or {}
        self.daten.setdefault("codes", [])
        self.daten.setdefault("fehler", 0)
        self.daten.setdefault("pause_bis", 0)

    def _speichern(self):
        daten.schreibe_json(self.pfad, self.daten)

    def liste(self):
        return [dict(c) for c in self.daten["codes"]]

    def erstellen(self, art, minuten, anzahl, jetzt):
        if art not in ARTEN:
            raise ValueError("Art muss normal oder besonders sein.")
        if not isinstance(minuten, int) or isinstance(minuten, bool) or not 5 <= minuten <= 240:
            raise ValueError("Minuten: 5 bis 240.")
        if not isinstance(anzahl, int) or not 1 <= anzahl <= 20:
            raise ValueError("Anzahl: 1 bis 20.")
        offen = [c for c in self.daten["codes"] if not c.get("eingeloest")]
        if len(offen) + anzahl > HOECHSTENS:
            raise ValueError("Höchstens %d offene Gutscheine." % HOECHSTENS)
        vorhanden = {c["code"] for c in self.daten["codes"]}
        neu = []
        while len(neu) < anzahl:
            code = "%06d" % secrets.randbelow(10 ** 6)
            if code in vorhanden or len(set(code)) == 1:          # keine Wiederholung, kein 000000
                continue
            vorhanden.add(code)
            neu.append({"code": code, "art": art, "minuten": minuten,
                        "erstellt": jetzt.isoformat(timespec="seconds"), "eingeloest": None})
        self.daten["codes"].extend(neu)
        self._speichern()
        return neu

    def loeschen(self, code):
        self.daten["codes"] = [c for c in self.daten["codes"] if c["code"] != code or c.get("eingeloest")]
        self._speichern()

    def pruefen(self, code, sekunden):
        """Rückgabe: (eintrag oder None, fehlermeldung). Zählt Fehlversuche. sekunden = Uhrzeit als Zahl (überlebt
        einen Neustart, anders als die Monotonuhr)."""
        if sekunden < self.daten["pause_bis"]:
            return None, "Zu viele falsche Codes – probier es in ein paar Minuten nochmal."
        code = "".join(z for z in str(code or "") if z.isdigit())
        eintrag = next((c for c in self.daten["codes"] if c["code"] == code), None)
        if eintrag is None or len(code) != 6:
            self.daten["fehler"] += 1
            if self.daten["fehler"] >= FEHLER_MAX:
                self.daten["fehler"], self.daten["pause_bis"] = 0, sekunden + PAUSE_S
            self._speichern()
            return None, "Diesen Gutschein gibt es nicht."
        if eintrag.get("eingeloest"):
            return None, "Dieser Gutschein wurde schon eingelöst."
        return eintrag, ""

    def einloesen(self, eintrag, jetzt):
        eintrag["eingeloest"] = jetzt.isoformat(timespec="seconds")
        self.daten["fehler"] = 0
        self._speichern()
