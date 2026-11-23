"""FernsehFranzi 4.6 - Ferien und Feiertage des Bundeslandes mit einem Knopf.

Die Ferien stammen aus den amtlichen Tabellen der Kultusministerkonferenz (``ferien_daten.json``, erzeugt mit
``werkzeuge/ferien_uebernehmen.py`` aus der Ferienliste der Klassenkiste). Abgefragt wird kein fremder Dienst; neue
Schuljahre kommen mit den Updates. Die gesetzlichen Feiertage rechnet der Fernseher selbst (nur landesweite, nur
Montag bis Freitag - Samstag und Sonntag sind ohnehin frei).
"""
import json
import os
from datetime import date, timedelta

LAENDER = {
    "BW": "Baden-Württemberg", "BY": "Bayern", "BE": "Berlin", "BB": "Brandenburg", "HB": "Bremen", "HH": "Hamburg",
    "HE": "Hessen", "MV": "Mecklenburg-Vorpommern", "NI": "Niedersachsen", "NW": "Nordrhein-Westfalen",
    "RP": "Rheinland-Pfalz", "SL": "Saarland", "SN": "Sachsen", "ST": "Sachsen-Anhalt", "SH": "Schleswig-Holstein",
    "TH": "Thüringen",
}
_DATEI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ferien_daten.json")
_daten = None


def daten():
    global _daten
    if _daten is None:
        with open(_DATEI, encoding="utf-8") as f:
            _daten = json.load(f)
    return _daten


def ostersonntag(jahr):
    """Gaußsche Osterformel (gregorianisch)."""
    a, b, c = jahr % 19, jahr // 100, jahr % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    monat, tag = divmod(h + l - 7 * m + 114, 31)
    return date(jahr, monat, tag + 1)


def feiertage(land, jahr):
    """[(datum, name)] der landesweiten gesetzlichen Feiertage an Werktagen."""
    o = ostersonntag(jahr)
    liste = [
        (date(jahr, 1, 1), "Neujahr", None), (o - timedelta(days=2), "Karfreitag", None),
        (o + timedelta(days=1), "Ostermontag", None), (date(jahr, 5, 1), "Tag der Arbeit", None),
        (o + timedelta(days=39), "Christi Himmelfahrt", None), (o + timedelta(days=50), "Pfingstmontag", None),
        (date(jahr, 10, 3), "Tag der Deutschen Einheit", None), (date(jahr, 12, 25), "1. Weihnachtstag", None),
        (date(jahr, 12, 26), "2. Weihnachtstag", None),
        (date(jahr, 1, 6), "Heilige Drei Könige", {"BW", "BY", "ST"}),
        (date(jahr, 3, 8), "Internationaler Frauentag", {"BE", "MV"}),
        (o + timedelta(days=60), "Fronleichnam", {"BW", "BY", "HE", "NW", "RP", "SL"}),
        (date(jahr, 8, 15), "Mariä Himmelfahrt", {"SL"}),
        (date(jahr, 9, 20), "Weltkindertag", {"TH"}),
        (date(jahr, 10, 31), "Reformationstag", {"BB", "HB", "HH", "MV", "NI", "SN", "ST", "SH", "TH"}),
        (date(jahr, 11, 1), "Allerheiligen", {"BW", "BY", "NW", "RP", "SL"}),
    ]
    buss = date(jahr, 11, 22)
    while buss.weekday() != 2:                       # Buß- und Bettag (Sachsen): Mittwoch vor dem 23. November
        buss -= timedelta(days=1)
    liste.append((buss, "Buß- und Bettag", {"SN"}))
    return sorted((tag, name) for tag, name, nur in liste if (nur is None or land in nur) and tag.weekday() < 5)


def zeitraeume(land, ab, mit_feiertagen=True):
    """[[von, bis], ...] (ISO-Daten) aller bekannten Ferien (und Feiertage) des Landes, die am Tag ``ab`` oder später
    enden - nach Datum sortiert, ohne doppelte."""
    if land not in LAENDER:
        raise ValueError("Bitte ein Bundesland wählen.")
    aus = set()
    jahre = set()
    for sj, d in daten()["schuljahre"].items():
        for _, von, bis in d["laender"].get(land, []):
            if bis >= ab.isoformat():
                aus.add((von, bis))
                jahre.update({int(von[:4]), int(bis[:4])})
    if mit_feiertagen and jahre:
        for jahr in range(min(jahre), max(jahre) + 1):
            for tag, _ in feiertage(land, jahr):
                if tag >= ab and not any(von <= tag.isoformat() <= bis for von, bis in aus):
                    aus.add((tag.isoformat(), tag.isoformat()))
    return [list(z) for z in sorted(aus)]


def bekannt_bis():
    """Letzter Tag, für den Ferien bekannt sind (für den Hinweis auf der Eltern-Seite)."""
    letzte = [bis for d in daten()["schuljahre"].values() for liste in d["laender"].values() for _, _, bis in liste]
    return max(letzte) if letzte else None


def zusammenfuehren(vorhanden, neu, heute):
    """Eigene Einträge der Eltern bleiben; Vergangenes (vor ``heute`` beendet) fällt weg; doppelte nur einmal."""
    alle = {tuple(z) for z in vorhanden if z[1] >= heute.isoformat()} | {tuple(z) for z in neu}
    return [list(z) for z in sorted(alle)]
