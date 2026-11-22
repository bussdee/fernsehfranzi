"""FernsehFranzi 3.5 - Wecker „wie im Handy“.

Einstellungen (einstellungen.json, Feld "wecker"):
    {"aktiv": true,            # Eltern: Wecker überhaupt erlaubt
     "fruehestens": "06:00",   # Eltern: keine Weckzeit davor
     "max_laut": 60,           # Eltern: höchste Lautstärke (Prozent)
     "toene": "",              # Eltern: FileBrowser-Freigabelink des Ordners mit Wecktönen
     "liste": [{"nr": 1, "zeit": "07:00", "tage": [0,1,2,3,4], "ton": "Lieblingslied.mp3", "laut": 50, "an": true}]}
Die Liste stellt das Kind am Fernseher ein (und die Eltern auf der Eltern-Seite).
"""
from datetime import datetime, timedelta

from . import hoerbuch

VORGABE = {"aktiv": True, "fruehestens": "06:00", "max_laut": 60, "toene": "", "liste": []}
HOECHSTENS = 5
SCHLUMMERN_MIN = 5
SONNE_WAHL = (0, 5, 10, 15, 20, 30)          # 4.0: Minuten Sonnenaufgang vor dem Wecken (0 = aus)


def _uhr(text, wo):
    try:
        return datetime.strptime(str(text), "%H:%M").time()
    except ValueError:
        raise ValueError("%s: Uhrzeit fehlt." % wo) from None


def einstellungen(gespeichert):
    w = dict(VORGABE)
    w.update(gespeichert or {})
    w["liste"] = [dict(x) for x in w.get("liste") or []]
    return w


def pruefe(w):
    """Wirft ValueError mit verständlichem Text."""
    if not isinstance(w, dict) or set(w) - set(VORGABE):
        raise ValueError("Wecker: unbekannte Felder.")
    w = einstellungen(w)
    if not isinstance(w["aktiv"], bool):
        raise ValueError("Wecker: an/aus muss ja/nein sein.")
    frueh = _uhr(w["fruehestens"], "Frühestens")
    if not isinstance(w["max_laut"], int) or isinstance(w["max_laut"], bool) or not 10 <= w["max_laut"] <= 100:
        raise ValueError("Wecker: höchste Lautstärke 10 bis 100 %.")
    if w["toene"] and hoerbuch.pruefe_freigabe(w["toene"]):
        raise ValueError("Wecktöne: %s." % hoerbuch.pruefe_freigabe(w["toene"]))
    if not isinstance(w["liste"], list) or len(w["liste"]) > HOECHSTENS:
        raise ValueError("Höchstens %d Wecker." % HOECHSTENS)
    nummern = set()
    for e in w["liste"]:
        if not isinstance(e, dict) or set(e) - {"nr", "zeit", "tage", "ton", "laut", "an", "sonne"}:
            raise ValueError("Wecker: unbekannte Felder.")
        nr = e.get("nr")
        if not isinstance(nr, int) or nr in nummern or not 0 < nr < 1000:
            raise ValueError("Wecker: Nummer fehlt oder doppelt.")
        nummern.add(nr)
        zeit = _uhr(e.get("zeit"), "Wecker %d" % nr)
        if zeit < frueh:
            raise ValueError("Wecker %s: frühestens %s Uhr." % (e["zeit"], w["fruehestens"]))
        if not e.get("tage") or not all(isinstance(t, int) and 0 <= t <= 6 for t in e["tage"]):
            raise ValueError("Wecker %s: mindestens ein Wochentag." % e["zeit"])
        if e.get("ton"):
            hoerbuch.sauberer_pfad(e["ton"])
            if not e["ton"].lower().endswith(hoerbuch.AUDIO):
                raise ValueError("Weckton muss eine Audiodatei sein.")
        laut = e.get("laut", w["max_laut"])
        if not isinstance(laut, int) or isinstance(laut, bool) or not 5 <= laut <= 100:
            raise ValueError("Wecker %s: Lautstärke 5 bis 100 %%." % e["zeit"])
        if e.get("sonne", 0) not in SONNE_WAHL:
            raise ValueError("Wecker %s: Sonnenaufgang 0, 5, 10, 15, 20 oder 30 Minuten." % e["zeit"])
        if not isinstance(e.get("an", True), bool):
            raise ValueError("Wecker: an/aus muss ja/nein sein.")
    return w


def faellig(w, jetzt, erledigt):
    """Wecker, die jetzt klingeln sollen (innerhalb von 2 Minuten nach der Weckzeit, je Tag einmal)."""
    if not w["aktiv"]:
        return []
    ergebnis = []
    for e in w["liste"]:
        if not e.get("an", True) or jetzt.weekday() not in e.get("tage", []):
            continue
        zeit = datetime.combine(jetzt.date(), _uhr(e["zeit"], "Wecker"))
        schluessel = "wecker:%s:%d:%s" % (jetzt.date().isoformat(), e["nr"], e["zeit"])
        if zeit <= jetzt < zeit + timedelta(minutes=2) and schluessel not in erledigt:
            erledigt.add(schluessel)
            ergebnis.append(e)
    return ergebnis


def sonnenaufgang_faellig(w, jetzt, erledigt):
    """Wecker, deren Sonnenaufgang jetzt beginnt (Weckzeit minus „sonne“ Minuten)."""
    if not w["aktiv"]:
        return []
    ergebnis = []
    for e in w["liste"]:
        minuten = int(e.get("sonne", 0) or 0)
        if not minuten or not e.get("an", True):
            continue
        weck = datetime.combine(jetzt.date(), _uhr(e["zeit"], "Wecker"))
        beginn = weck - timedelta(minutes=minuten)
        if weck.weekday() not in e.get("tage", []):
            continue
        schluessel = "sonne:%s:%d:%s" % (weck.date().isoformat(), e["nr"], e["zeit"])
        if beginn <= jetzt < beginn + timedelta(minutes=2) and schluessel not in erledigt:
            erledigt.add(schluessel)
            ergebnis.append((e, minuten))
    return ergebnis


def lautstaerke(w, eintrag):
    return min(int(w["max_laut"]), int(eintrag.get("laut", w["max_laut"])))
