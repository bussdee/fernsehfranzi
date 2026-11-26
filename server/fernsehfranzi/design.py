"""FernsehFranzi 5.0 - Farben und Ansichten der Startseite.

Das Kind wählt Farbe und Ansicht am Fernseher („Gestalten“). Die Eltern legen fest, was es gibt, und ob abends automatisch
dunkel wird. 6.0: klare Farben in Paaren (dunkel / hell); abends wird nur eine helle Farbe durch ihre dunkle Schwester
ersetzt, eine dunkle Wahl bleibt. Spiele, Player und der Elternbereich bleiben in jeder Farbe dunkel.
"""
import re

# (Kennung, Name, hell?, Schwester) - 6.0
DESIGNS = (
    ("blau", "🔵 Blau", False, "hellblau"), ("gruen", "🟢 Grün", False, "mint"), ("lila", "🟣 Lila", False, "rosa"),
    ("rot", "🔴 Rot", False, "gelb"), ("schwarz", "⚫ Schwarz", False, "weiss"),
    ("hellblau", "🌤️ Hellblau", True, "blau"), ("mint", "🍃 Mint", True, "gruen"), ("rosa", "🌸 Rosa", True, "lila"),
    ("gelb", "🌞 Sonnengelb", True, "rot"), ("weiss", "⚪ Weiß", True, "schwarz"),
    # 6.7: Welten - Farbe, Hintergrund, Bewegung und Franzi-Ausstattung in einem Paket (dunkel, bleiben auch abends)
    ("rock", "🎸 Rock", False, "rock"), ("unterwasser", "🐠 Unterwasser", False, "unterwasser"),
    ("raumstation", "🚀 Raumstation", False, "raumstation"),
    # 6.9.46: gezeichnete Hintergründe (Bilder in web/hintergrund/*.jpg), dunkel, bleiben auch abends
    ("berge", "🏔️ Berge", False, "berge"), ("liebe", "❤️ Liebe", False, "liebe"),
    ("system", "💻 System", False, "system"), ("weltraum", "🌌 Weltraum", False, "weltraum"),
)
WELTEN = ("rock", "unterwasser", "raumstation")
BILD_DESIGNS = ("berge", "liebe", "system", "weltraum")
KENNUNGEN = tuple(k for k, _, _, _ in DESIGNS)
SCHWESTER = {k: sw for k, _, _, sw in DESIGNS}
# Namen bis 5.3 -> 6.0 (einmalig umgezogen; alte Werte werden auch beim Lesen noch verstanden)
ALT = {"weltall": "blau", "ozean": "blau", "wald": "gruen", "sonne": "rot", "bonbon": "lila", "nacht": "schwarz",
       "himmel": "hellblau", "zuckerwatte": "rosa", "wiese": "mint", "regenbogen": "gelb"}
ANSICHTEN = (("konsole", "🎮 Konsole"), ("seitenleiste", "📋 Seitenleiste"), ("karussell", "🎠 Karussell"))
ANSICHT_IDS = tuple(k for k, _ in ANSICHTEN)
HELL = frozenset(k for k, _, h, _ in DESIGNS if h)
DUNKEL = tuple(k for k, _, h, _ in DESIGNS if not h)
VORGABE = {"erlaubt": list(KENNUNGEN), "ansichten": list(ANSICHT_IDS), "abend_aktiv": False, "abend_ab": "19:00", "morgen_ab": "06:30",
           "animation": "sparsam", "hintergruende": {}, "hintergrund_ordner": ""}   # 6.9.42: eigenes Bild je Farbe
ANIMATIONEN = ("aus", "sparsam", "hoch")   # 6.8.12: aus = still, sparsam = Pi 3, hoch = flüssig (Pi 5)
FELDER = set(VORGABE) | {"abend_design"}     # abend_design: bis 5.3, wird nicht mehr gebraucht (abends: dunkle Schwester)
UHRZEIT = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]\Z")
BILDNAME = re.compile(r"\Ahg-[0-9a-f]{12}\.(png|jpg|webp)\Z")


def neu(kennung):
    """Farbe in der Kennung von 6.0 (alte Namen werden übersetzt)."""
    return ALT.get(kennung, kennung)


def einstellungen(roh):
    """Vollständige Design-Einstellung (fehlende Felder mit Vorgabe, alte Farbnamen übersetzt)."""
    d = dict(VORGABE, **{k: v for k, v in (roh or {}).items() if k in VORGABE})
    if isinstance(d["erlaubt"], list):
        d["erlaubt"] = list(dict.fromkeys(neu(x) for x in d["erlaubt"]))
    return d


def migriere(einst):
    """Einmalig beim Start (6.0): alte Farbnamen in einstellungen.json umstellen. Rückgabe: ob sich etwas geändert hat."""
    geaendert = False
    st = einst.get("startseite")
    if isinstance(st, dict) and st.get("thema") in ALT:
        st["thema"] = ALT[st["thema"]]
        geaendert = True
    d = einst.get("design")
    if isinstance(d, dict):
        if isinstance(d.get("erlaubt"), list) and any(x in ALT for x in d["erlaubt"]):
            d["erlaubt"] = list(dict.fromkeys(neu(x) for x in d["erlaubt"]))
            geaendert = True
        if "abend_design" in d:
            del d["abend_design"]
            geaendert = True
        # 6.9.46: die neuen gezeichneten Hintergründe einmalig zu einer gespeicherten Auswahl dazunehmen
        if isinstance(d.get("erlaubt"), list) and not einst.get("migration_6946"):
            d["erlaubt"] = list(dict.fromkeys(d["erlaubt"] + list(BILD_DESIGNS)))
            geaendert = True
    if not einst.get("migration_6946"):              # nur einmal (danach entscheiden die Eltern)
        einst["migration_6946"] = True
        geaendert = True
    return geaendert


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
    if d["animation"] not in ANIMATIONEN:
        raise ValueError("Design: Animationen aus, sparsam oder hoch.")
    hg = d["hintergruende"]
    if not isinstance(hg, dict) or any(k not in KENNUNGEN or not isinstance(v, str) or not BILDNAME.match(v) for k, v in hg.items()):
        raise ValueError("Design: eigener Hintergrund ungültig.")
    if not isinstance(d["hintergrund_ordner"], str):
        raise ValueError("Design: Bilder-Ordner ungültig.")
    return d


def ist_abend(d, jetzt):
    """Zwischen abend_ab und morgen_ab (über Mitternacht)."""
    if not d["abend_aktiv"]:
        return False
    hm = jetzt.strftime("%H:%M")
    ab, bis = d["abend_ab"], d["morgen_ab"]
    return (hm >= ab or hm < bis) if ab > bis else (ab <= hm < bis)


def jetzt_design(roh, gewaehlt, jetzt):
    """Das Design, das die Startseite gerade zeigt: die Wahl des Kindes (wenn erlaubt), abends eine helle Farbe als ihre
    dunkle Schwester (6.0)."""
    d = einstellungen(roh)
    gewaehlt = neu(gewaehlt)
    farbe = gewaehlt if gewaehlt in d["erlaubt"] else d["erlaubt"][0]
    if ist_abend(d, jetzt) and farbe in HELL:
        return SCHWESTER[farbe]
    return farbe


def jetzt_ansicht(roh, gewaehlt):
    d = einstellungen(roh)
    return gewaehlt if gewaehlt in d["ansichten"] else d["ansichten"][0]


def fuer_startseite(roh, startseite, jetzt):
    d = einstellungen(roh)
    gewaehlt = neu((startseite or {}).get("thema", "blau"))
    aktuell = jetzt_design(d, gewaehlt, jetzt)
    return {"designs": [{"id": k, "name": n, "hell": h, "abends": SCHWESTER[k] if h else k}
                        for k, n, h, _ in DESIGNS if k in d["erlaubt"]],
            "gewaehlt": gewaehlt,
            "ansichten": [{"id": k, "name": n} for k, n in ANSICHTEN if k in d["ansichten"]],
            "ansicht": jetzt_ansicht(d, (startseite or {}).get("ansicht", "konsole")),
            "jetzt": aktuell, "hell": aktuell in HELL, "abend": ist_abend(d, jetzt),
            "abend_ab": d["abend_ab"] if d["abend_aktiv"] else None,
            "animation": d["animation"] if d["animation"] in ANIMATIONEN else "sparsam",
            # 6.9.42: eigenes Bild der Eltern für diese Farbe (sonst das gezeichnete Motiv)
            "bild": ("/api/hintergrund?datei=" + d["hintergruende"][aktuell]) if isinstance(d["hintergruende"], dict)
                    and aktuell in d["hintergruende"] else None}
