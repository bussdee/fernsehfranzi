"""FernsehFranzi 5.0 - Designs der Startseite.

Das Kind wählt sein Design am Fernseher („Meine Startseite“). Die Eltern legen fest, welche Designs es gibt und ob abends
automatisch ein dunkles Design kommt (Abend-Automatik). Spiele, Player und der Elternbereich bleiben in jedem Design
dunkel: Sie sind Spielflächen, keine Startseite.
"""
import re

# (Kennung, Name, hell?) - die ersten sechs gibt es seit 4.0 als „Hintergrund“
DESIGNS = (
    ("weltall", "🌌 Weltall", False), ("ozean", "🌊 Ozean", False), ("wald", "🌲 Wald", False),
    ("sonne", "🌅 Sonnenuntergang", False), ("bonbon", "🍬 Bonbon", False), ("nacht", "🌙 Nacht", False),
    ("himmel", "☀️ Sonnentag", True), ("zuckerwatte", "🍭 Zuckerwatte", True), ("wiese", "🌼 Blumenwiese", True),
    ("regenbogen", "🌈 Regenbogen", True),
)
KENNUNGEN = tuple(k for k, _, _ in DESIGNS)
# 5.0: Ansichten = Aufteilung der Startseite (unabhängig von den Farben). Bedienung überall gleich: ↑ ↓ Bereich, ← → Kachel.
ANSICHTEN = (("konsole", "🎮 Konsole"), ("seitenleiste", "📋 Seitenleiste"), ("karussell", "🎠 Karussell"))
ANSICHT_IDS = tuple(k for k, _ in ANSICHTEN)
HELL = frozenset(k for k, _, h in DESIGNS if h)
DUNKEL = tuple(k for k, _, h in DESIGNS if not h)
VORGABE = {"erlaubt": list(KENNUNGEN), "ansichten": list(ANSICHT_IDS), "abend_aktiv": False, "abend_ab": "19:00", "morgen_ab": "06:30", "abend_design": "weltall"}
FELDER = set(VORGABE)
UHRZEIT = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]\Z")


def einstellungen(roh):
    """Vollständige Design-Einstellung (fehlende Felder mit Vorgabe)."""
    return dict(VORGABE, **{k: v for k, v in (roh or {}).items() if k in FELDER})


def pruefe(roh):
    if not isinstance(roh, dict) or set(roh) - FELDER:
        raise ValueError("Design: unbekannte Felder.")
    d = einstellungen(roh)
    if not isinstance(d["erlaubt"], list) or not d["erlaubt"] or any(x not in KENNUNGEN for x in d["erlaubt"]) \
            or len(set(d["erlaubt"])) != len(d["erlaubt"]):
        raise ValueError("Design: mindestens ein Design muss erlaubt sein.")
    if not isinstance(d["ansichten"], list) or not d["ansichten"] or any(x not in ANSICHT_IDS for x in d["ansichten"]) \
            or len(set(d["ansichten"])) != len(d["ansichten"]):
        raise ValueError("Design: mindestens eine Ansicht muss erlaubt sein.")
    if not isinstance(d["abend_aktiv"], bool):
        raise ValueError("Design: Abend-Automatik ja oder nein.")
    for feld in ("abend_ab", "morgen_ab"):
        if not isinstance(d[feld], str) or not UHRZEIT.match(d[feld]):
            raise ValueError("Design: Uhrzeit als HH:MM.")
    if d["abend_design"] not in DUNKEL:
        raise ValueError("Design: abends nur ein dunkles Design.")
    return d


def ist_abend(d, jetzt):
    """Zwischen abend_ab und morgen_ab (über Mitternacht)."""
    if not d["abend_aktiv"]:
        return False
    hm = jetzt.strftime("%H:%M")
    ab, bis = d["abend_ab"], d["morgen_ab"]
    return (hm >= ab or hm < bis) if ab > bis else (ab <= hm < bis)


def jetzt_design(roh, gewaehlt, jetzt):
    """Das Design, das die Startseite gerade zeigt: abends das Abend-Design, sonst die Wahl des Kindes (wenn erlaubt)."""
    d = einstellungen(roh)
    if ist_abend(d, jetzt):
        return d["abend_design"]
    if gewaehlt in d["erlaubt"]:
        return gewaehlt
    return d["erlaubt"][0]


def jetzt_ansicht(roh, gewaehlt):
    d = einstellungen(roh)
    return gewaehlt if gewaehlt in d["ansichten"] else d["ansichten"][0]


def fuer_startseite(roh, startseite, jetzt):
    d = einstellungen(roh)
    gewaehlt = (startseite or {}).get("thema", "weltall")
    aktuell = jetzt_design(d, gewaehlt, jetzt)
    return {"designs": [{"id": k, "name": n, "hell": h} for k, n, h in DESIGNS if k in d["erlaubt"]],
            "ansichten": [{"id": k, "name": n} for k, n in ANSICHTEN if k in d["ansichten"]],
            "ansicht": jetzt_ansicht(d, (startseite or {}).get("ansicht", "konsole")),
            "jetzt": aktuell, "hell": aktuell in HELL, "abend": ist_abend(d, jetzt),
            "abend_ab": d["abend_ab"] if d["abend_aktiv"] else None}
