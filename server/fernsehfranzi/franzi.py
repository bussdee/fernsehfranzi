"""FernsehFranzi 6.9 - Franzi als Haustier (eigener Entwurf) und der Sterne-Shop.

Ruhe im Alltag: Franzi stirbt nie, nichts geht verloren, sie macht kein schlechtes Gewissen und schreit nicht nach
Aufmerksamkeit. Ihre Werte sinken langsam (nachts kaum) und werden erst beim Anschauen berechnet - kein Takt im Hintergrund.

Einstellung (einstellungen["franzi"], Eltern): aktiv, abenteuer_tage, preise {item: sterne}, angebote [...].
Zustand (franzi.json, Server): werte, stand (Zeitpunkt der Werte), naehe, zuege, tagebuch, besitz, angezogen, zimmer,
raum, abenteuer, start, letzter_besuch, gekauft (Angebote je Woche).
Sterne liegen weiter im Mein-Tag-Zustand (verdient dort, ausgegeben hier).
"""
from datetime import datetime, timedelta

WERTE = ("hunger", "sauber", "energie", "glueck")      # 100 = satt / sauber / ausgeschlafen / glücklich
# 6.9.59 („in ~1 Tag leer“): je wache Stunde - von 100 auf fast 0 an einem Tag (~14 wache Stunden)
ABBAU_STUNDE = {"hunger": 7.0, "sauber": 5.0, "energie": 6.0, "glueck": 5.5}
# Fernsehzeit des Kindes (Spiele, Filme, Musik) kostet Franzi zusätzlich - je Stunde
TV_STUNDE = {"hunger": 3.0, "sauber": 1.0, "energie": 5.0, "glueck": 0.0}
NACHT = (21, 7)                                         # nachts sinkt fast nichts (und die Energie steigt)
NACHT_FAKTOR = 0.25
ZUEGE = ("verschmust", "verspielt", "neugierig", "stolz", "wild")
TYP_AB_TAGEN = 14
TYPEN = {
    frozenset(("verschmust", "verspielt")): "Kuschel-Clown", frozenset(("verschmust", "neugierig")): "Träumerin",
    frozenset(("verschmust", "stolz")): "Prinzessin", frozenset(("verschmust", "wild")): "Wirbel-Kuschlerin",
    frozenset(("verspielt", "neugierig")): "Entdeckerin", frozenset(("verspielt", "stolz")): "Siegerin",
    frozenset(("verspielt", "wild")): "Wirbelwind", frozenset(("neugierig", "stolz")): "Professorin",
    frozenset(("neugierig", "wild")): "Abenteurerin", frozenset(("stolz", "wild")): "Rockstar",
}
TAGEBUCH_MAX = 200
VORGABE = {"aktiv": False, "abenteuer_tage": 4, "preise": {}, "angebote": [], "geburtstag": "",
           "sprueche": {}}                       # 6.9.61: was Franzi sagt (sprueche.py)   # 6.9.10: TT.MM. des Kindes (freiwillig)
ANGEBOT_ARTEN = ("minuten", "wochenende", "sperrzeit", "frei")
ANGEBOTE_MAX = 12

# Katalog: id, art, name, symbol, Vorgabe-Preis (Sterne), von Anfang an da?
ARTEN = ("spiel", "raum", "kleidung", "spielzeug", "moebel")
KATALOG = [
    ("spiel-fangen", "spiel", "Sterne fangen", "🌟", 0, True),
    ("spiel-memory", "spiel", "Memory", "🃏", 8, False),
    ("spiel-dreigewinnt", "spiel", "Drei gewinnt", "❌", 10, False),
    ("spiel-simon", "spiel", "Farben-Echo", "🎨", 6, False),
    ("spiel-snake", "spiel", "Snake", "🐍", 8, False),
    ("spiel-stimme", "spiel", "Mit Franzi singen", "🎤", 10, False),      # 6.9.13: die Stimm-Spiele
    ("spiel-huepfen", "spiel", "Franzi hüpft", "🦘", 12, False),          # 6.9.14: Jump'n'Run
    ("raum-zimmer", "raum", "Kinderzimmer", "🛏️", 0, True),
    ("raum-hell", "raum", "Sonnenzimmer", "🌅", 0, False),                # 6.9.44: Raum 2 (gezeichnet)
    ("raum-probe", "raum", "Proberaum", "🥁", 0, False),                  # 6.9.53: Raum 3 (gezeichnet, Bühne mit Schlagzeug)
    ("raum-garten", "raum", "Garten", "🌻", 15, False),
    ("raum-kueche", "raum", "Küche", "🍳", 12, False),                    # 6.9.58: gezeichnet (Raum 4)
    ("raum-spiel", "raum", "Spielzimmer", "🧸", 0, False),                # 6.9.58: gezeichnet
    ("raum-bad", "raum", "Badezimmer", "🛁", 10, False),
    ("kleid-schleife", "kleidung", "Schleife", "🎀", 3, False),
    ("kleid-krone", "kleidung", "Krone", "👑", 12, False),
    ("kleid-zauberhut", "kleidung", "Zauberhut", "🎩", 6, False),
    ("kleid-schal", "kleidung", "Schal", "🧣", 4, False),
    ("kleid-brille", "kleidung", "Sonnenbrille", "🕶️", 4, False),
    ("kleid-muetze", "kleidung", "Bommelmütze", "🧢", 3, False),            # 6.9.12
    ("kleid-rundbrille", "kleidung", "Runde Brille", "👓", 3, False),
    ("kleid-taucher", "kleidung", "Taucherbrille", "🤿", 6, False),
    ("kleid-stern", "kleidung", "Sternchen", "⭐", 2, False),
    ("kleid-blume", "kleidung", "Blume im Haar", "🌸", 3, False),
    ("kleid-blau", "kleidung", "Farbe Blau", "🔵", 8, False),
    ("kleid-gruen", "kleidung", "Farbe Grün", "🟢", 8, False),
    ("kleid-lila", "kleidung", "Farbe Lila", "🟣", 8, False),
    ("kleid-gold", "kleidung", "Goldene Franzi", "🟡", 0, False),         # 6.9.59: nur Level 10
    ("franzi-wachsen-1", "kleidung", "Franzi wächst", "🌱", 0, False),     # 6.9.59: Level 10 - kleiner Körper (Bild folgt)
    ("franzi-wachsen-2", "kleidung", "Franzi wächst weiter", "🌳", 0, False),   # Level 20
    ("spielzeug-ball", "spielzeug", "Ball", "⚽", 0, True),
    ("spielzeug-teddy", "spielzeug", "Teddy", "🧸", 5, False),
    ("spielzeug-drachen", "spielzeug", "Drachen", "🪁", 6, False),
    ("spielzeug-rakete", "spielzeug", "Rakete", "🚀", 9, False),
    ("moebel-bett", "moebel", "Bett", "🛏️", 0, True),
    ("moebel-pflanze", "moebel", "Pflanze", "🪴", 3, False),
    ("moebel-lampe", "moebel", "Sofa", "🛋️", 4, False),          # 6.9.36: das Symbol war immer ein Sofa
    ("moebel-bild", "moebel", "Bild", "🖼️", 3, False),
    ("moebel-aquarium", "moebel", "Aquarium", "🐠", 10, False),
    ("spielzeug-schaukel", "spielzeug", "Schaukel", "🎠", 8, False),       # 6.9.59: nicht mehr „Rutsche“ (die gibt es eigens)
    ("moebel-badeente", "moebel", "Badeente", "🦆", 3, False),             # 6.9.9: passt ins Bad
    ("spielzeug-ballon", "spielzeug", "Luftballon", "🎈", 2, False),        # 6.9.12
    ("spielzeug-puzzle", "spielzeug", "Puzzle", "🧩", 4, False),
    ("spielzeug-gitarre", "spielzeug", "Gitarre", "🎸", 7, False),
    ("moebel-regal", "moebel", "Bücherregal", "📚", 4, False),
    ("spielzeug-musikbox", "spielzeug", "Musikbox", "🎶", 15, False),     # 6.9.50: Musik aus dem Musik-Archiv, Franzi tanzt
    # 6.9.55: Gegenstände passend zu den Räumen (gezeichnet in dinge.js, nur im passenden Raum aufstellbar - NUR_IN)
    ("moebel-mikrofon", "moebel", "Mikrofon", "🎤", 8, False),
    ("spielzeug-keyboard", "spielzeug", "Keyboard", "🎹", 12, False),
    ("moebel-verstaerker", "moebel", "Verstärker", "🔊", 7, False),
    ("moebel-discokugel", "moebel", "Discokugel", "🪩", 9, False),
    ("moebel-gartenzwerg", "moebel", "Gartenzwerg", "🧙", 5, False),
    ("spielzeug-planschbecken", "spielzeug", "Planschbecken", "🏊", 10, False),
    ("moebel-blumenbeet", "moebel", "Blumenbeet", "🌷", 6, False),
    ("spielzeug-sandkasten", "spielzeug", "Sandkasten", "🏖️", 9, False),
    ("moebel-sessel", "moebel", "Sessel", "🛋️", 8, False),
    ("moebel-stehlampe", "moebel", "Stehlampe", "💡", 6, False),
    ("moebel-teppich", "moebel", "Teppich", "🟪", 5, False),
    ("moebel-spielkiste", "moebel", "Spielzeugkiste", "🧸", 6, False),
    ("moebel-nachttisch", "moebel", "Nachttisch", "🕯️", 5, False),
    # 6.9.58: Küche und Spielzimmer
    ("moebel-esstisch", "moebel", "Esstisch", "🪑", 8, False),
    ("moebel-obstkorb", "moebel", "Obstkorb", "🧺", 4, False),
    ("spielzeug-kuchen", "spielzeug", "Geburtstagskuchen", "🎂", 6, False),
    ("spielzeug-schaukelpferd", "spielzeug", "Schaukelpferd", "🐴", 10, False),
    ("spielzeug-zelt", "spielzeug", "Spielzelt", "⛺", 9, False),
    ("spielzeug-rutsche", "spielzeug", "Rutsche", "🛝", 12, False),
    # 6.9.59: neu gezeichnet
    ("spielzeug-trommel", "spielzeug", "Trommel", "🥁", 6, False),
    ("spielzeug-hase", "spielzeug", "Plüschhase", "🐰", 5, False),
    ("spielzeug-kreisel", "spielzeug", "Kreisel", "🌀", 3, False),
    ("spielzeug-zug", "spielzeug", "Holzeisenbahn", "🚂", 7, False),
    ("spielzeug-buch", "spielzeug", "Bilderbuch", "📖", 3, False),
    ("moebel-girlande", "moebel", "Girlande", "🎊", 4, False),
    ("moebel-rahmen", "moebel", "Bilderrahmen", "🖼️", 3, False),
    ("moebel-kissen", "moebel", "Kissen", "🛌", 3, False),
    ("moebel-hochbeet", "moebel", "Hochbeet", "🥕", 8, False),
]
KATALOG_IDS = {k[0] for k in KATALOG}
# 6.9.37: Franzis Level schalten nur bei Level 2-4 Gegenstände frei, danach je Level einen neuen Raum.
# Diese Dinge gibt es nur als Level-Belohnung (nicht im Shop); alles andere nur im Shop.
LEVEL_BELOHNUNG = [(2, "raum-hell"), (3, "raum-probe"), (4, "raum-garten"), (5, "raum-kueche"), (6, "raum-spiel"), (7, "raum-bad"),
                   (10, "kleid-gold"), (10, "franzi-wachsen-1"), (20, "franzi-wachsen-2")]
# 6.9.59: Level bringen nur noch Räume und die goldene Franzi, die bei Level 10 und 20 wächst - lange Ziel
# 6.9.44: Räume brauchen außer dem Level auch Sammeltage (Tage mit mindestens einem Stern) - Raum 3 dauert 1-2 Wochen,
# auch wenn an einem Tag viele Sterne kommen
MIN_TAGE = {"raum-hell": 4, "raum-probe": 10, "raum-garten": 15, "raum-kueche": 20, "raum-spiel": 25, "raum-bad": 30}
NUR_LEVEL = {item: lv for lv, item in LEVEL_BELOHNUNG}
KLEIDUNG_IDS = {k[0] for k in KATALOG if k[1] == "kleidung"}
# 6.9.12: an welcher Stelle ein Kleidungsstück sitzt - ein neues ersetzt das alte an derselben Stelle
KLEIDUNG_TEIL = {"kleid-krone": "hut", "kleid-zauberhut": "hut", "kleid-muetze": "hut", "kleid-brille": "brille",
                 "kleid-rundbrille": "brille", "kleid-taucher": "brille", "kleid-schleife": "extra", "kleid-schal": "extra",
                 "kleid-stern": "extra", "kleid-blume": "extra", "kleid-blau": "farbe", "kleid-gruen": "farbe",
                 "kleid-lila": "farbe", "kleid-gold": "farbe",
                 "franzi-wachsen-1": "groesse", "franzi-wachsen-2": "groesse"}
PREIS_MAX = 999

AKTIONEN = {
    #            hunger sauber energie glueck  nähe  zug
    "fuettern":  (35, -4, 0, 4, 1, None),
    "waschen":   (0, 45, -3, 2, 1, "stolz"),
    "streicheln": (0, 0, 0, 12, 2, "verschmust"),
    "schlafen":  (-3, 0, 45, 3, 1, None),
    "ball":      (-6, -5, -10, 15, 1, "verspielt"),
}
SPIEL_ZUG = {"spiel-fangen": "wild", "spiel-memory": "neugierig", "spiel-dreigewinnt": "neugierig",
             "spiel-simon": "neugierig", "spiel-snake": "wild", "spiel-stimme": "verspielt", "spiel-huepfen": "wild",
             "spiel-bass": "verspielt"}
# 6.9.59: Spiele, die ein Gegenstand im Zimmer startet (Mikrofon, Gitarre)
SPIEL_DURCH = {"spiel-stimme": ("moebel-mikrofon",), "spiel-bass": ("spielzeug-gitarre", "spielzeug-keyboard"),
               "spiel-simon": ("spielzeug-trommel",), "spiel-memory": ("spielzeug-puzzle",)}
# 6.9.60: Gegenstände im aktuellen Raum verstärken die Pflege (Obstkorb beim Füttern, Kuscheltiere beim Streicheln …)
DING_BONUS = {"fuettern": (("moebel-obstkorb", "moebel-esstisch", "spielzeug-kuchen"), "hunger", 8),
              "streicheln": (("spielzeug-teddy", "spielzeug-hase", "moebel-kissen"), "glueck", 6),
              "schlafen": (("moebel-bett", "moebel-kissen", "moebel-nachttisch"), "energie", 8),
              "waschen": (("moebel-badeente",), "sauber", 8),
              "ball": (("spielzeug-rutsche", "spielzeug-schaukel", "spielzeug-sandkasten"), "glueck", 6)}
# 6.9.13: diese Spielzimmer-Kacheln verschwinden aus dem Spiele-Bereich, solange Franzi eingeschaltet ist
UMGEZOGEN = ("spiel-memory", "spiel-drei", "spiel-echo", "spiel-snake", "spiel-stimme", "spiel-huepfen")


def _zahl(wert, von, bis):
    return isinstance(wert, int) and not isinstance(wert, bool) and von <= wert <= bis


def _tag_monat(text):
    """„07.03.“ oder „7.3.“ -> (7, 3), sonst None."""
    teile = [t for t in str(text).strip().split(".") if t]
    if len(teile) != 2 or not all(t.isdigit() for t in teile):
        return None
    tag, monat = int(teile[0]), int(teile[1])
    try:
        datetime(2024, monat, tag)                      # Schaltjahr: 29.02. ist erlaubt
    except ValueError:
        return None
    return tag, monat


def einstellungen(roh):
    d = dict(VORGABE, **{k: v for k, v in (roh or {}).items() if k in VORGABE})
    d["preise"] = {k: v for k, v in (d.get("preise") or {}).items() if k in KATALOG_IDS and _zahl(v, 0, PREIS_MAX)}
    return d


def pruefe(roh):
    if not isinstance(roh, dict) or set(roh) - set(VORGABE):
        raise ValueError("Franzi: unbekannte Felder.")
    d = einstellungen(roh)
    if not isinstance(d["aktiv"], bool):
        raise ValueError("Franzi: an oder aus.")
    from . import sprueche
    sprueche.pruefe(roh.get("sprueche"))
    if not _zahl(d["abenteuer_tage"], 1, 60):
        raise ValueError("Franzi: Abenteuer-Pause 1 bis 60 Tage.")
    g = d["geburtstag"]
    if not isinstance(g, str) or (g and not _tag_monat(g)):
        raise ValueError("Franzi: Geburtstag als TT.MM. (z. B. 07.03.) oder leer.")
    preise = roh.get("preise", {})
    if not isinstance(preise, dict) or any(k not in KATALOG_IDS or not _zahl(v, 0, PREIS_MAX) for k, v in preise.items()):
        raise ValueError("Franzi: Preise 0 bis %d Sterne." % PREIS_MAX)
    if not isinstance(d["angebote"], list) or len(d["angebote"]) > ANGEBOTE_MAX:
        raise ValueError("Franzi: höchstens %d Angebote." % ANGEBOTE_MAX)
    nummern = set()
    for a in d["angebote"]:
        if not isinstance(a, dict) or set(a) - {"nr", "name", "symbol", "art", "minuten", "preis", "pro_woche", "aktiv", "von", "bis"}:
            raise ValueError("Franzi: Angebot unvollständig.")
        if not _zahl(a.get("nr"), 1, 9999) or a["nr"] in nummern:
            raise ValueError("Franzi: Angebot-Nummer doppelt.")
        nummern.add(a["nr"])
        if not isinstance(a.get("name"), str) or not 1 <= len(a["name"].strip()) <= 60:
            raise ValueError("Franzi: Angebot braucht einen Namen (bis 60 Zeichen).")
        if a.get("art") not in ANGEBOT_ARTEN:
            raise ValueError("Franzi: unbekannte Angebots-Art.")
        if a["art"] != "frei" and not _zahl(a.get("minuten"), 1, 240):
            raise ValueError("Franzi: Spielzeit 1 bis 240 Minuten.")
        if not _zahl(a.get("preis"), 1, PREIS_MAX):
            raise ValueError("Franzi: Preis 1 bis %d Sterne." % PREIS_MAX)
        if not _zahl(a.get("pro_woche", 1), 0, 50):
            raise ValueError("Franzi: höchstens 50 je Woche (0 = unbegrenzt).")
        if not isinstance(a.get("aktiv", True), bool) or not isinstance(a.get("symbol", "🎁"), str) or len(a.get("symbol", "🎁")) > 8:
            raise ValueError("Franzi: Angebot an/aus und Symbol prüfen.")
    return d


def preis(einst, item):
    return einst["preise"].get(item, next(k[4] for k in KATALOG if k[0] == item))


# ------------------------------------------------------------------ Zustand
def neu(jetzt):
    return {"werte": {w: 80.0 for w in WERTE}, "stand": jetzt.isoformat(timespec="seconds"), "naehe": 10,
            "zuege": {z: 0 for z in ZUEGE}, "tagebuch": [], "besitz": [k[0] for k in KATALOG if k[5]],
            "angezogen": [], "zimmer": {"raum-zimmer": {"moebel-bett": [16, 17, 1], "spielzeug-ball": [76, 3, 2]}}, "raum": "raum-zimmer", "abenteuer": None,
            "start": jetzt.date().isoformat(), "letzter_besuch": jetzt.isoformat(timespec="seconds"), "gekauft": {}}


def _vollstaendig(z, jetzt):
    if not isinstance(z, dict) or "werte" not in z:
        z = neu(jetzt)
        notiere(z, jetzt, "hallo", "Hallo! Ich bin Franzi. Schön, dass du da bist!")
    basis = neu(jetzt)
    for k, v in basis.items():
        z.setdefault(k, v)
    for w in WERTE:
        z["werte"].setdefault(w, 80.0)
    for g in ZUEGE:
        z["zuege"].setdefault(g, 0)
    for raum, plaetze in list((z.get("zimmer") or {}).items()):        # 6.9.36: alte Platznamen umziehen
        if any(isinstance(v, str) for v in plaetze.values()):           # 6.9.54: feste Plätze -> freie Lage [x, y, Reihenfolge]
            neu_ = {}
            for n, (p, i) in enumerate(plaetze.items()):
                p = ALTE_PLAETZE.get(p, p)
                if isinstance(i, str) and p in PLATZ_LAGE:
                    neu_[i] = [*PLATZ_LAGE[p], n + 1]
            z["zimmer"][raum] = neu_
    return z


def notiere(z, jetzt, art, text):
    z["tagebuch"].append({"zeit": jetzt.isoformat(timespec="minutes"), "art": art, "text": text})
    del z["tagebuch"][:-TAGEBUCH_MAX]


def _nacht(stunde):
    ab, bis = NACHT
    return stunde >= ab or stunde < bis


def altern(z, jetzt):
    """Werte bis jetzt fortschreiben (stundenweise, nachts kaum Abbau, Energie steigt im Schlaf)."""
    try:
        stand = datetime.fromisoformat(z["stand"])
    except (KeyError, TypeError, ValueError):
        stand = jetzt
    if stand > jetzt:
        stand = jetzt
    t = stand
    while t < jetzt:
        schritt = min(timedelta(hours=1), jetzt - t)
        h = schritt.total_seconds() / 3600
        nacht = _nacht(t.hour)
        for w in WERTE:
            ab = ABBAU_STUNDE[w] * h * (NACHT_FAKTOR if nacht else 1)
            if w == "energie" and nacht:
                ab = -8 * h                                     # schläft und tankt auf
            z["werte"][w] = max(0.0, min(100.0, z["werte"][w] - ab))
        t += schritt
        if (jetzt - t).days > 30:                               # sehr lange weg: Rest auf einmal
            t = jetzt
    z["stand"] = jetzt.isoformat(timespec="seconds")
    return z


def fernsehzeit(zustand, jetzt, minuten):
    """6.9.59: Das Kind war `minuten` aktiv am Fernseher - Franzi hat mitgemacht und wird hungrig und müde."""
    z = altern(_vollstaendig(zustand, jetzt), jetzt)
    for w in WERTE:
        z["werte"][w] = max(0.0, min(100.0, z["werte"][w] - TV_STUNDE[w] * minuten / 60))
    return z


def _bis(z, feld, jetzt):
    try:
        return bool(z.get(feld)) and datetime.fromisoformat(z[feld]) > jetzt
    except (TypeError, ValueError):
        return False


def stimmung(z, jetzt):
    w = z["werte"]
    if z.get("abenteuer"):
        return "unterwegs"
    if _bis(z, "genervt_bis", jetzt):                     # 6.9.45: braucht kurz ihre Ruhe (geht von selbst vorbei)
        return "genervt"
    if _bis(z, "grummelig_bis", jetzt):                   # 6.9.45: wurde geweckt
        return "grummelig"
    if _nacht(jetzt.hour):
        return "schlaefrig" if w["energie"] < 90 else "vertraeumt"
    if w["energie"] < 25:
        return "muede"
    if w["hunger"] < 25:
        return "hungrig"
    if w["sauber"] < 25:
        return "schmutzig"
    if w["glueck"] < 30:
        return "gelangweilt"
    if w["glueck"] < 45 and w["hunger"] < 45:
        return "trotzig"
    if z["naehe"] >= 60 and w["glueck"] >= 70:
        return "anhaenglich"
    return "froehlich"


SAETZE = {
    "unterwegs": "Ich bin auf Abenteuerreise!",
    "schlaefrig": "Uaaah … es ist schon spät. Gute Nacht!",
    "vertraeumt": "Ich träume von Sternen …",
    "muede": "Ich bin so müde … bringst du mich ins Bett?",
    "hungrig": "Mein Bauch knurrt!",
    "schmutzig": "Ich glaube, ich brauche ein Bad.",
    "gelangweilt": "Spielst du mit mir?",
    "trotzig": "Hmpf. Erst Essen, dann Spaß!",
    "anhaenglich": "Ich hab dich lieb!",
    "froehlich": "Schön, dass du da bist!",
    "genervt": "Ich brauche gerade ein bisschen Ruhe … gleich bin ich wieder da!",
    "grummelig": "Gähn … ich hab so schön geschlafen.",
}


def typ(z, jetzt):
    try:
        tage = (jetzt.date() - datetime.fromisoformat(z["start"]).date()).days
    except (KeyError, TypeError, ValueError):
        return None
    if tage < TYP_AB_TAGEN or sum(z["zuege"].values()) < 10:
        return None
    zwei = sorted(ZUEGE, key=lambda g: (-z["zuege"][g], ZUEGE.index(g)))[:2]
    return TYPEN[frozenset(zwei)]


EREIGNISSE_TAG = [("schmetterling", "🦋", "Ein Schmetterling ist zum Fenster hereingeflogen!"),
                  ("stein", "🪨", "Ich hab einen seltsamen, glitzernden Stein gefunden!"),
                  ("bild", "🖼️", "Ich hab ein Bild für dich gemalt!"),
                  ("blume", "🌼", "Schau mal, eine Blume – für dich!"),
                  ("feder", "🪶", "Eine bunte Feder lag vor der Tür!")]
EREIGNISSE_NACHT = [("geist", "👻", "Psst … ein kleiner, freundlicher Geist hat Hallo gesagt."),
                    ("sternschnuppe", "🌠", "Ich hab eine Sternschnuppe gesehen und mir was gewünscht!")]
EREIGNIS_CHANCE = 35                                    # Prozent je Tag - selten, damit es besonders bleibt


def ereignis(z, jetzt):
    """6.9.5: höchstens ein kleines Ereignis am Tag (aus dem Datum berechnet - kein Zufall im Hintergrund)."""
    tag = jetzt.date().isoformat()
    alt = z.get("ereignis") or {}
    if alt.get("tag") == tag:
        return None
    zahl = (jetzt.toordinal() * 7919 + len(z.get("tagebuch", []))) % 100
    if zahl >= EREIGNIS_CHANCE:
        z["ereignis"] = {"tag": tag}
        return None
    liste = EREIGNISSE_NACHT if _nacht(jetzt.hour) else EREIGNISSE_TAG
    art, symbol, text = liste[zahl % len(liste)]
    z["ereignis"] = {"tag": tag, "art": art, "symbol": symbol, "text": text}
    notiere(z, jetzt, "ereignis", text)
    return text


WETTER_SATZ = {"regen": "Es regnet – gut, dass ich mein Regencape habe!", "schnee": "Schnee! Ich will einen Schneemann bauen!",
               "sonne": "Die Sonne scheint – herrlich!", "kalt": "Brr, ist das kalt draußen. Gut, dass ich einen Schal habe!",
               "warm_pi": "Puh, mir ist ganz warm ums Herz – mein Fernseher-Kopf glüht ein bisschen!"}


def wetter_art(daten):
    """Aus der Wetter-Auswertung (wetter.auswerten) ein Wort für Franzi."""
    if not daten:
        return None
    code = daten.get("code") or 0
    if code in (71, 73, 75, 77, 85, 86):
        return "schnee"
    if 51 <= code <= 67 or 80 <= code <= 82 or code >= 95:
        return "regen"
    gefuehlt = daten.get("gefuehlt")
    if gefuehlt is not None and gefuehlt <= 2:
        return "kalt"
    if code in (0, 1) and (daten.get("symbol") or "") not in ("🌙",):
        return "sonne"
    return None


# 6.9.49: Abenteuer mit Postkarten (gezeichnet, web/bilder/postkarten/<karte>.jpg): Ziel, „Grüße aus …“, Grüße je Ziel
ABENTEUER = [
    ("berge", "in die Berge", "aus den Bergen", ["Hier oben ist die Luft so frisch! Ich hab einen Steinbock getroffen – der war gar nicht scheu.",
                                                 "Ich bin ganz weit hinaufgewandert. Von hier kann man fast bis zu dir sehen!"]),
    ("billigurlaub", "in den Billigurlaub", "aus dem Billigurlaub", ["Der Wohnwagen quietscht ein bisschen, aber das Meer ist wunderschön!",
                                                                    "Mein Liegestuhl wackelt. Macht nichts – mit dir wär's noch schöner!"]),
    ("erholung", "in den Erholungsurlaub", "aus dem Erholungsurlaub", ["Ich liege am Pool und trinke Saft mit Schirmchen. Herrlich!",
                                                                      "Ich entspanne mich ganz doll – dann hab ich wieder viel Kraft zum Spielen!"]),
    ("strand", "ans Meer", "vom Strand", ["Eine Robbe hat mir mein Essen geklaut! Ich musste so lachen.",
                                          "Ich hab Muscheln gesammelt – die schönste bringe ich dir mit!"]),
    ("thailand", "nach Thailand", "aus Thailand", ["Hier ist es warm und das Wasser ist türkis. Ich hab eine Kokosnuss getrunken!",
                                                   "Mit einem langen Boot sind wir zu den Felsen gefahren. So aufregend!"]),
    ("tirol", "nach Tirol", "aus Tirol", ["Die Berge spiegeln sich im See. So schön ruhig hier!",
                                          "Ich hab im See die Füße ins Wasser gehalten – brrr, kalt!"]),
    ("wildwasser", "zum Wildwasser-Rafting", "vom Wildwasser", ["Wir sind mit dem Schlauchboot durch die Wellen gesaust – ich bin ganz nass!",
                                                                "Platsch! Das war wild. Zum Glück hatte ich eine Schwimmweste an."]),
]
POSTKARTEN_MAX = 60
MARKEN = 2


def _postkarte(z, jetzt):
    """Ein neues Abenteuer: Ziel und Postkarte wählen (nicht zweimal hintereinander dieselbe)."""
    zuletzt = (z.get("postkarten") or [{}])[-1].get("karte")
    wahl = [a for a in ABENTEUER if a[0] != zuletzt] or ABENTEUER
    karte, ort, gruss_aus, texte = wahl[jetzt.toordinal() % len(wahl)]
    eintrag = {"karte": karte, "ort": ort, "gruss_aus": gruss_aus, "text": texte[jetzt.toordinal() // len(wahl) % len(texte)],
               "datum": jetzt.date().isoformat(), "marke": 1 + jetzt.toordinal() % MARKEN}
    z["postkarten"] = ((z.get("postkarten") or []) + [eintrag])[-POSTKARTEN_MAX:]
    return eintrag


def besuch(einst, zustand, jetzt):
    """Das Kind öffnet Franzi: Werte fortschreiben, nach langer Pause Abenteuer/Rückkehr, Gedächtnis-Sätze."""
    z = altern(_vollstaendig(zustand, jetzt), jetzt)
    satz = None
    try:
        zuletzt = datetime.fromisoformat(z["letzter_besuch"])
    except (KeyError, TypeError, ValueError):
        zuletzt = jetzt
    weg = jetzt - zuletzt
    if z.get("abenteuer"):
        ort = z["abenteuer"]["ort"]
        z["abenteuer"] = None
        for w in WERTE:
            z["werte"][w] = max(z["werte"][w], 70.0)
        satz = "Ich bin zurück von meiner Reise %s! Ich hab dir eine Postkarte mitgebracht." % ort
        notiere(z, jetzt, "reise", "Zurück von der Abenteuerreise %s." % ort)
    elif weg >= timedelta(days=einst["abenteuer_tage"]):
        karte = _postkarte(z, jetzt)                       # 6.9.49: mit Postkarte (landet im Album)
        ort = karte["ort"]
        z["abenteuer"] = {"ort": ort, "seit": zuletzt.isoformat(timespec="minutes"), "postkarte": karte}
        for w in WERTE:
            z["werte"][w] = max(z["werte"][w], 70.0)
        satz = "Franzi ist auf Abenteuerreise %s gegangen – sie hat eine Postkarte geschickt. Drück OK, dann kommt sie heim!" % ort
        notiere(z, jetzt, "reise", "Auf Abenteuerreise %s gegangen." % ort)
    elif weg >= timedelta(days=2):
        satz = "Du warst %d Tage weg – ich hab in der Zeit ein Bild für dich gemalt!" % weg.days
        notiere(z, jetzt, "wieder", "Nach %d Tagen wieder zusammen." % weg.days)
    if not z.get("abenteuer"):
        neu_e = ereignis(z, jetzt)
        satz = satz or neu_e
    z["letzter_besuch"] = jetzt.isoformat(timespec="seconds")
    if z.get("level_neu") and not z.get("abenteuer"):    # 6.9.37: ein neues Level ist wichtiger als Gruß oder Ereignis
        satz = level_satz(z)
        z.pop("level_neu", None)
    if z.get("geschenk_neu") and not satz:
        satz = "Ein Geschenk von Mama oder Papa: %s! 🎁" % z["geschenk_neu"]
    z.pop("geschenk_neu", None)                          # einmal gesagt reicht
    return z, satz


RAUM_BONUS = {("raum-kueche", "fuettern"): ("hunger", 15), ("raum-bad", "waschen"): ("sauber", 20),
              ("raum-garten", "ball"): ("glueck", 10), ("raum-zimmer", "schlafen"): ("energie", 10),
              ("raum-spiel", "streicheln"): ("glueck", 12)}


# 6.9.45: Franzi hat auch mal genug - freundlich, ohne Strafe (keine Werte gehen verloren) und von selbst vorbei
GENERVT_MIN = 3
OFT_FENSTER_S, OFT_WARNUNG, OFT_GENERVT = 60, 4, 6      # dasselbe so oft in einer Minute: erst Hinweis, dann genervt
VOLL = 95                                               # Wert so voll, dass es nichts mehr bringt
UNNOETIG_FENSTER_S, UNNOETIG_GENERVT = 300, 3           # dreimal „unnötig“ in 5 Minuten -> genervt
WERT_VON = {"fuettern": "hunger", "waschen": "sauber", "schlafen": "energie"}
SCHLAF_NACH_MIN = 20                                    # so lange schläft sie nach „schlafen legen“


def _reaktion(z, text, gesicht):
    z["reaktion"] = {"text": text, "gesicht": gesicht}


def _genug(z, jetzt, aktion):
    """Prüft, ob Franzi diese Pflege gerade nicht mag. True = nichts tun (Reaktion steht in z["reaktion"])."""
    if _bis(z, "genervt_bis", jetzt):
        _reaktion(z, "Ich brauche gerade ein bisschen Ruhe … gleich bin ich wieder da!", "genervt")
        return True
    jetzt_s = jetzt.isoformat(timespec="seconds")
    liste = [x for x in (z.get("pflege_zuletzt") or []) if isinstance(x, list) and len(x) == 2
             and (jetzt - datetime.fromisoformat(x[1])).total_seconds() < UNNOETIG_FENSTER_S]
    liste.append([aktion, jetzt_s])
    z["pflege_zuletzt"] = liste[-20:]
    gleich = sum(1 for a, t in liste if a == aktion and (jetzt - datetime.fromisoformat(t)).total_seconds() < OFT_FENSTER_S)
    # geweckt: nachts oder kurz nach dem Schlafenlegen
    geschlafen = z.get("schlaeft_seit")
    schlaeft = aktion != "schlafen" and (_nacht(jetzt.hour) or (geschlafen and (jetzt - datetime.fromisoformat(geschlafen)) < timedelta(minutes=SCHLAF_NACH_MIN)))
    if schlaeft and not _bis(z, "grummelig_bis", jetzt):
        z["grummelig_bis"] = (jetzt + timedelta(minutes=GENERVT_MIN)).isoformat(timespec="seconds")
        z.pop("schlaeft_seit", None)
        _reaktion(z, "Gähn … du hast mich geweckt. Ich bin noch ganz verschlafen.", "grummelig")
        return False
    if gleich >= OFT_GENERVT:
        z["genervt_bis"] = (jetzt + timedelta(minutes=GENERVT_MIN)).isoformat(timespec="seconds")
        _reaktion(z, "Puh, jetzt reicht's aber! Lass mich kurz in Ruhe, ja?", "genervt")
        return True
    w = z["werte"]
    unnoetig = (WERT_VON.get(aktion) and w[WERT_VON[aktion]] >= VOLL) or all(w[x] >= VOLL for x in WERTE)
    if unnoetig:
        z["unnoetig"] = [t for t in (z.get("unnoetig") or []) if (jetzt - datetime.fromisoformat(t)).total_seconds() < UNNOETIG_FENSTER_S] + [jetzt_s]
        if len(z["unnoetig"]) >= UNNOETIG_GENERVT:
            z["genervt_bis"] = (jetzt + timedelta(minutes=GENERVT_MIN)).isoformat(timespec="seconds")
            z["unnoetig"] = []
            _reaktion(z, "Mir geht's doch richtig gut! Jetzt brauche ich mal Ruhe.", "genervt")
        else:
            _reaktion(z, {"fuettern": "Ich bin pappsatt!", "waschen": "Ich bin doch schon blitzsauber!",
                          "schlafen": "Ich bin gar nicht müde!"}.get(aktion, "Danke, mir geht's super!"), "grummelig")
        return True
    if gleich >= OFT_WARNUNG:
        _reaktion(z, "Nicht so viel auf einmal – mir wird ganz schwindelig!", "schwindelig")
    return False


def pflegen(einst, zustand, jetzt, aktion):
    """Füttern, waschen, streicheln, schlafen legen, mit dem Ball spielen."""
    if aktion not in AKTIONEN:
        raise ValueError("Das kann Franzi nicht.")
    z = altern(_vollstaendig(zustand, jetzt), jetzt)
    if z.get("abenteuer"):
        z, _ = besuch(einst, z, jetzt)
    if aktion == "ball" and "spielzeug-ball" not in z["besitz"]:
        raise ValueError("Dafür fehlt der Ball.")
    z.pop("reaktion", None)
    if _genug(z, jetzt, aktion):
        return z
    if aktion == "schlafen":
        z["schlaeft_seit"] = jetzt.isoformat(timespec="seconds")
    plus = list(AKTIONEN[aktion])
    bonus = RAUM_BONUS.get((z["raum"], aktion))
    if bonus:                                            # 6.9.9: im passenden Raum wirkt es stärker
        plus[WERTE.index(bonus[0])] += bonus[1]
    dinge, wert, extra = DING_BONUS.get(aktion, ((), None, 0))
    im_raum = (z.get("zimmer") or {}).get(z["raum"]) or {}
    if wert and any(x in im_raum for x in dinge):           # 6.9.60: passender Gegenstand steht im Raum
        plus[WERTE.index(wert)] += extra
    for w, p in zip(WERTE, plus[:4]):
        z["werte"][w] = max(0.0, min(100.0, z["werte"][w] + p))
    z["naehe"] = min(100, z["naehe"] + plus[4])
    if plus[5]:
        z["zuege"][plus[5]] += 1
    z["letzter_besuch"] = jetzt.isoformat(timespec="seconds")
    return z


def gespielt(zustand, jetzt, spiel, punkte=0):
    """Ein Minispiel ist zu Ende: Franzi freut sich (keine Sterne - Minispiele machen nur Spaß)."""
    z = altern(_vollstaendig(zustand, jetzt), jetzt)
    if spiel not in SPIEL_ZUG or (spiel not in z["besitz"] and not any(x in z["besitz"] for x in SPIEL_DURCH.get(spiel, ()))):
        raise ValueError("Dieses Spiel gibt es bei Franzi (noch) nicht.")
    z["werte"]["glueck"] = min(100.0, z["werte"]["glueck"] + 12)
    z["werte"]["energie"] = max(0.0, z["werte"]["energie"] - 10)      # 6.9.59: Spielen macht müde, hungrig und schmutzig
    z["werte"]["hunger"] = max(0.0, z["werte"]["hunger"] - 6)
    z["werte"]["sauber"] = max(0.0, z["werte"]["sauber"] - 4)
    z["naehe"] = min(100, z["naehe"] + 1)
    z["zuege"][SPIEL_ZUG[spiel]] += 1
    z["zuege"]["verspielt"] += 1
    lieb = z.setdefault("spiele", {})
    lieb[spiel] = lieb.get(spiel, 0) + 1
    if lieb[spiel] == 1:
        notiere(z, jetzt, "spiel", "Zum ersten Mal %s gespielt." % next((k[2] for k in KATALOG if k[0] == spiel),
                                                                        {"spiel-bass": "Gitarre"}.get(spiel, "ein Spiel")))
    rekord = z.setdefault("rekorde", {})
    if isinstance(punkte, int) and punkte > rekord.get(spiel, 0):
        rekord[spiel] = punkte
    return z


def anziehen(zustand, jetzt, item, an):
    z = _vollstaendig(zustand, jetzt)
    if item not in KLEIDUNG_IDS or item not in z["besitz"]:
        raise ValueError("Das hat Franzi nicht im Schrank.")
    teil = KLEIDUNG_TEIL.get(item)
    z["angezogen"] = [x for x in z["angezogen"] if x != item and (not an or KLEIDUNG_TEIL.get(x) != teil)] + ([item] if an else [])
    del z["angezogen"][:-4]
    return z


def raum_wechseln(zustand, jetzt, raum):
    z = _vollstaendig(zustand, jetzt)
    if not raum.startswith("raum-") or raum not in z["besitz"]:
        raise ValueError("Diesen Raum hat Franzi noch nicht.")
    z["raum"] = raum
    return z


# 6.9.36: feste Platzarten - hinten auf dem Boden (Großes), vorne neben Franzi (Kleines), Wand, Fensterbrett.
# Welcher Gegenstand wohin passt, entscheidet der Fernseher (franzi.js); der Server prüft nur den Namen.
PLAETZE = ("hinten-links", "hinten-rechts", "vorne-links", "vorne-rechts", "wand-links", "wand-rechts", "fenster")
# 6.9.54: Gegenstände stehen frei im Raum: [x (Mitte, % der Breite), y (Unterkante, % der Höhe von unten), Reihenfolge]
PLATZ_LAGE = {"hinten-links": (16, 17), "hinten-rechts": (84, 17), "vorne-links": (26, 3), "vorne-rechts": (74, 3),
              "wand-links": (38, 55), "wand-rechts": (86, 70), "fenster": (22, 45)}
LAGE_X, LAGE_Y = (3, 97), (0, 80)
# 6.9.55: Gegenstände, die nur in bestimmte Räume passen (sonst überall)
NUR_IN = {"moebel-mikrofon": ("raum-probe",), "spielzeug-keyboard": ("raum-probe",), "moebel-verstaerker": ("raum-probe",),
          "moebel-discokugel": ("raum-probe",), "moebel-gartenzwerg": ("raum-garten",), "spielzeug-planschbecken": ("raum-garten",),
          "moebel-blumenbeet": ("raum-garten",), "spielzeug-sandkasten": ("raum-garten",), "moebel-sessel": ("raum-hell",),
          "moebel-stehlampe": ("raum-hell",), "moebel-teppich": ("raum-hell", "raum-zimmer"), "moebel-spielkiste": ("raum-zimmer",),
          "moebel-nachttisch": ("raum-zimmer",), "moebel-esstisch": ("raum-kueche",), "moebel-obstkorb": ("raum-kueche",),
          "spielzeug-kuchen": ("raum-kueche",), "spielzeug-schaukelpferd": ("raum-spiel", "raum-zimmer"),
          "spielzeug-zelt": ("raum-spiel",), "spielzeug-rutsche": ("raum-spiel", "raum-garten"),
          "moebel-hochbeet": ("raum-garten",)}
ALTE_PLAETZE = {"links": "hinten-links", "rechts": "hinten-rechts", "mitte": "vorne-links", "wand": "wand-rechts", "fenster": "fenster"}


def setzen(zustand, jetzt, item, x, y):
    """6.9.54: Möbel/Spielzeug frei im aktuellen Raum hinstellen (zuletzt gestellt = ganz vorne, z. B. Teddy aufs Bett)."""
    z = _vollstaendig(zustand, jetzt)
    if item not in z["besitz"] or not str(item).startswith(("moebel-", "spielzeug-")):
        raise ValueError("Das hat Franzi nicht.")
    if NUR_IN.get(item) and z["raum"] not in NUR_IN[item]:
        raise ValueError("Das passt nicht in diesen Raum.")
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (x, y)):
        raise ValueError("Wohin damit?")
    x = round(max(LAGE_X[0], min(LAGE_X[1], float(x))), 1)
    y = round(max(LAGE_Y[0], min(LAGE_Y[1], float(y))), 1)
    raum = z["zimmer"].setdefault(z["raum"], {})
    oben = max([v[2] for v in raum.values() if isinstance(v, list) and len(v) == 3] + [0])
    raum[item] = [x, y, oben + 1]
    return z


def wegraeumen(zustand, jetzt, item):
    z = _vollstaendig(zustand, jetzt)
    z["zimmer"].setdefault(z["raum"], {}).pop(item, None)
    return z


# ------------------------------------------------------------------ Shop
def _woche(jetzt):
    j, w, _ = jetzt.isocalendar()
    return "%d-W%02d" % (j, w)


def kaufen(einst, zustand, sterne, jetzt, item):
    """Item gegen Sterne. Rückgabe (zustand, preis). sterne = aktueller Kontostand (Mein Tag)."""
    z = _vollstaendig(zustand, jetzt)
    if item not in KATALOG_IDS:
        raise ValueError("Das gibt es im Shop nicht.")
    if item in z["besitz"]:
        raise ValueError("Das hast du schon.")
    if item in NUR_LEVEL:
        raise ValueError("Das gibt es nicht zu kaufen – Franzi bekommt es mit Level %d." % NUR_LEVEL[item])
    p = preis(einst, item)
    if sterne < p:
        raise ValueError("Dafür brauchst du %d Sterne – du hast %d." % (p, sterne))
    z["besitz"].append(item)
    name = next(k[2] for k in KATALOG if k[0] == item)
    notiere(z, jetzt, "neu", "Neu: %s!" % name)
    return z, p


def level_belohnen(zustand, jetzt, level, sammeltage=None):
    """6.9.37: was Franzi mit ihrem Level (aus Mein Tag) bekommt - landet einmal im Besitz, mit Tagebuch-Eintrag.
    Rückgabe (zustand, Liste neuer Namen). Idempotent: schon Vorhandenes (auch geschenkt) zählt nicht doppelt."""
    z = _vollstaendig(zustand, jetzt)
    neu_ = []
    for lv, item in LEVEL_BELOHNUNG:
        if level >= lv and item not in z["besitz"] and (sammeltage is None or sammeltage >= MIN_TAGE.get(item, 0)):
            z["besitz"].append(item)
            if item.startswith("franzi-wachsen"):           # 6.9.59: Wachsen gilt sofort (kein Anziehen nötig)
                z["angezogen"] = [x for x in z.get("angezogen", []) if KLEIDUNG_TEIL.get(x) != "groesse"] + [item]
            name = next(k[2] for k in KATALOG if k[0] == item)
            notiere(z, jetzt, "level", "Level %d geschafft: %s!" % (lv, name))
            neu_.append(name)
            z["level_neu"] = {"level": lv, "namen": (z.get("level_neu") or {}).get("namen", []) + [name]}
    return z, neu_


def level_satz(z):
    """6.9.37: Franzi sagt beim nächsten Besuch, was das neue Level gebracht hat (einmal)."""
    ln = z.get("level_neu")
    if not ln:
        return None
    n = ln["namen"]
    liste = n[0] if len(n) == 1 else ", ".join(n[:-1]) + " und " + n[-1]
    return "Level %d! Neu für uns: %s! 🎉" % (ln["level"], liste)


def schenken(zustand, jetzt, item, von="Mama oder Papa"):
    """6.9.11: Geschenk der Eltern - kostet keine Sterne, landet mit Tagebuch-Eintrag bei Franzi."""
    z = _vollstaendig(zustand, jetzt)
    if item not in KATALOG_IDS:
        raise ValueError("Das gibt es nicht.")
    if item in z["besitz"]:
        raise ValueError("Das hat Franzi schon.")
    z["besitz"].append(item)
    name = next(k[2] for k in KATALOG if k[0] == item)
    notiere(z, jetzt, "geschenk", "Geschenk von %s: %s!" % (von, name))
    z["geschenk_neu"] = name
    return z, name


def angebot_einloesen(einst, zustand, sterne, jetzt, nr, sperrzeit_jetzt=False):
    """Eltern-Angebot gegen Sterne. Rückgabe (zustand, angebot, preis)."""
    z = _vollstaendig(zustand, jetzt)
    a = next((x for x in einst["angebote"] if x.get("nr") == nr and x.get("aktiv", True)), None)
    if a is None:
        raise ValueError("Dieses Angebot gibt es gerade nicht.")
    if a["art"] == "wochenende" and jetzt.weekday() < 5:
        raise ValueError("Das gibt es nur am Wochenende.")
    woche = _woche(jetzt)
    gekauft = z["gekauft"].setdefault(woche, {})
    for alt in sorted(z["gekauft"])[:-4]:
        del z["gekauft"][alt]
    schon = gekauft.get(str(nr), 0)
    if a.get("pro_woche", 1) and schon >= a.get("pro_woche", 1):
        raise ValueError("Diese Woche schon eingelöst – nächste Woche wieder!")
    if sterne < a["preis"]:
        raise ValueError("Dafür brauchst du %d Sterne – du hast %d." % (a["preis"], sterne))
    gekauft[str(nr)] = schon + 1
    notiere(z, jetzt, "angebot", "Eingelöst: %s." % a["name"])
    return z, a, a["preis"]


def geburtstag_heute(einst, jetzt):
    tm = _tag_monat(einst.get("geburtstag") or "")
    return bool(tm and tm == (jetzt.day, jetzt.month))


def erinnerung(z, jetzt):
    """6.9.10: ein Satz aus Franzis Gedächtnis (wechselt stündlich) - oder None."""
    saetze = []
    spiele = z.get("spiele") or {}
    if spiele:
        lieb = max(spiele, key=spiele.get)
        name = next((k[2] for k in KATALOG if k[0] == lieb), None)
        if name and spiele[lieb] >= 3:
            saetze.append("Weißt du was? %s ist unser Lieblingsspiel!" % name)
    t = typ(z, jetzt)
    if t:
        saetze.append("Ich glaube, ich bin eine richtige %s!" % t)
    neu_e = [e for e in z.get("tagebuch", []) if e.get("art") == "neu"]
    if neu_e:
        saetze.append("Danke nochmal für: %s" % neu_e[-1]["text"].replace("Neu: ", "").rstrip("!"))
    try:
        tage = (jetzt.date() - datetime.fromisoformat(z["start"]).date()).days
    except (KeyError, TypeError, ValueError):
        tage = 0
    if tage >= 7:
        saetze.append("Wir kennen uns schon %d Tage – schön, dass es dich gibt!" % tage)
    return saetze[jetzt.hour % len(saetze)] if saetze else None


def fuer_tv(einst, z, jetzt, sterne, satz=None, wetter=None, warm=False, sammeltage=0, reaktion=None, musik=False):
    w = {k: round(v) for k, v in z["werte"].items()}
    s = stimmung(z, jetzt)
    if not satz and z.get("geschenk_neu"):
        satz = "Ein Geschenk von Mama oder Papa: %s! 🎁" % z["geschenk_neu"]
    if not satz and geburtstag_heute(einst, jetzt) and not z.get("abenteuer"):
        satz = "Alles Gute zum Geburtstag! 🎂 Heute feiern wir!"
    if not satz and s == "froehlich" and jetzt.minute % 3 == 0:
        satz = erinnerung(z, jetzt)
    if not satz and s == "froehlich":
        satz = WETTER_SATZ["warm_pi"] if warm else WETTER_SATZ.get(wetter)
    woche = z["gekauft"].get(_woche(jetzt), {})
    return {
        "aktiv": einst["aktiv"], "werte": w, "stimmung": s, "satz": satz or SAETZE[s], "naehe": z["naehe"],
        "typ": typ(z, jetzt), "abenteuer": z.get("abenteuer"), "sterne": sterne,
        "angezogen": z["angezogen"], "raum": z["raum"], "zimmer": z["zimmer"].get(z["raum"], {}),
        "besitz": z["besitz"], "rekorde": z.get("rekorde", {}),
        "tagebuch": list(reversed(z["tagebuch"][-20:])),
        "katalog": [{"id": k[0], "art": k[1], "name": k[2], "symbol": k[3], "preis": preis(einst, k[0]),
                     "hat": k[0] in z["besitz"], "level": NUR_LEVEL.get(k[0]), "tage": MIN_TAGE.get(k[0]),
                     "nur_in": list(NUR_IN.get(k[0], ()))} for k in KATALOG],
        "sammeltage": sammeltage, "reaktion": reaktion,
        "postkarten": list(reversed(z.get("postkarten") or [])), "kind": einst.get("_kind", ""),
        "musikbox": bool(musik and "spielzeug-musikbox" in z["besitz"]), "musik_da": bool(musik),     # 6.9.50
        "angebote": [{"nr": a["nr"], "name": a["name"], "symbol": a.get("symbol", "🎁"), "art": a["art"],
                      "minuten": a.get("minuten"), "preis": a["preis"], "pro_woche": a.get("pro_woche", 1),
                      "noch": (max(0, a.get("pro_woche", 1) - woche.get(str(a["nr"]), 0)) if a.get("pro_woche", 1) else None)}
                     for a in einst["angebote"] if a.get("aktiv", True)],
        "nacht": _nacht(jetzt.hour), "wetter": wetter,
        "ereignis": (z.get("ereignis") or {}).get("symbol") and z["ereignis"] if (z.get("ereignis") or {}).get("tag") == jetzt.date().isoformat() else None,
    }
