"""Eltern-PIN (Grundsatz 9, docs/ENTWICKLUNG.md).

- Gespeichert wird nur ein PBKDF2-SHA256-Hash mit zufälligem Salz, nie die PIN selbst.
- Vergleich in konstanter Zeit.
- Nach 5 Fehlversuchen wächst die Sperre: 1, 2, 4, 8 ... Minuten, höchstens 60.
- Die PIN legen die Eltern beim ersten Start selbst fest; es gibt keine Vorgabe-PIN.
"""
import hashlib
import hmac
import os
import re

ITERATIONEN = 120_000          # bremst Durchprobieren; auf dem Pi 3 unter 1 s
PIN_FORM = re.compile(r"\d{4,8}\Z")
FREIE_VERSUCHE = 5
SPERRE_MAX_S = 3600


def pin_gueltig(pin):
    return isinstance(pin, str) and bool(PIN_FORM.match(pin))


def hash_erzeugen(pin, salz=None, iterationen=ITERATIONEN):
    """Rückgabe ein Eintrag für die Datenablage (enthält keine PIN)."""
    if not pin_gueltig(pin):
        raise ValueError("Die PIN muss aus 4 bis 8 Ziffern bestehen.")
    salz = salz or os.urandom(16)
    wert = hashlib.pbkdf2_hmac("sha256", pin.encode(), salz, iterationen)
    return {"verfahren": "pbkdf2-sha256", "iterationen": iterationen,
            "salz": salz.hex(), "hash": wert.hex()}


def pin_stimmt(pin, eintrag):
    if not pin_gueltig(pin) or not isinstance(eintrag, dict):
        return False
    if eintrag.get("verfahren") != "pbkdf2-sha256":
        return False
    try:
        salz = bytes.fromhex(eintrag["salz"])
        erwartet = bytes.fromhex(eintrag["hash"])
        iterationen = int(eintrag["iterationen"])
    except (KeyError, ValueError, TypeError):
        return False
    wert = hashlib.pbkdf2_hmac("sha256", pin.encode(), salz, iterationen)
    return hmac.compare_digest(wert, erwartet)


class Sperre:
    """Fehlversuche zählen. Zustand ist ein dict, damit der Server ihn speichern kann
    (ein Neustart hebt die Sperre nicht auf)."""

    def __init__(self, zustand=None):
        self.zustand = zustand if zustand is not None else {"fehler": 0, "gesperrt_bis": 0}

    def gesperrt_fuer(self, jetzt):
        """Restsekunden der Sperre (0 = frei)."""
        return max(0, int(self.zustand.get("gesperrt_bis", 0) - jetzt + 0.999))

    def pruefe(self, pin, eintrag, jetzt):
        """Rückgabe (ok, meldung). Während einer Sperre wird die PIN gar nicht geprüft."""
        rest = self.gesperrt_fuer(jetzt)
        if rest:
            return False, "Zu viele Versuche. Bitte in %d Minuten noch einmal." % ((rest + 59) // 60)
        if pin_stimmt(pin, eintrag):
            self.zustand.update(fehler=0, gesperrt_bis=0)
            return True, ""
        self.zustand["fehler"] = self.zustand.get("fehler", 0) + 1
        ueber = self.zustand["fehler"] - FREIE_VERSUCHE
        if ueber >= 0:
            dauer = min(SPERRE_MAX_S, 60 * (2 ** ueber))
            self.zustand["gesperrt_bis"] = jetzt + dauer
            return False, "Falsche PIN. Gesperrt für %d Minuten." % (dauer // 60)
        return False, "Falsche PIN. Noch %d Versuche." % (FREIE_VERSUCHE - self.zustand["fehler"])
