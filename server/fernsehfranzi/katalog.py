"""App-Katalog ``apps.json`` (docs/ENTWICKLUNG.md, „Wer besitzt was“).

Jede Kachel der Startseite ist ein Eintrag. Der Katalog liegt im Datenordner und wird vom
Elternbereich gepflegt. ``pruefe_katalog`` lehnt ungültige Einträge mit verständlichen
Meldungen ab, statt sie still zu verwerfen.

Adressen im Heimnetz (Plex, Kavita, Dashboard) stehen nie im Code: Diese Vorgabe-Einträge haben einen
leeren ``start`` und sind deshalb inaktiv, bis die Eltern sie einrichten. Öffentliche Lernseiten
(Klassenkiste, Kinderwelten) sind mit ihrer Adresse vorbelegt.
"""
import re
from urllib.parse import urlsplit

from . import hoerbuch

TYPEN = ("web", "desktop", "konsole", "hoerbuch", "youtube", "video")   # hoerbuch (3.3): Player auf der Startseite, start = Freigabelink
ZEIT = ("zaehlt", "gaming", "frei", "nie")   # "nie" = zählt nie (Plex, Dashboard - Grundsatz 8); 4.6: "gaming" = Teil der
                                            # Bildschirmzeit mit eigener Gaming-Zeit
EINGABE = ("tasten", "maus")
BEREICHE = ("", "start", "spiele", "lernen", "musik", "filme", "retro")   # 3.5: Startseite (leer = automatisch)
KENNUNG = re.compile(r"[a-z][a-z0-9-]{0,31}\Z")
FARBE = re.compile(r"#[0-9a-fA-F]{6}\Z")
DOMAIN = re.compile(r"(?=.{1,253}\Z)(\*\.)?([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\Z")
# Konsolen-Apps sind feste systemd-Units mit eigener sudo-Regel - kein freier Befehl.
KONSOLE_UNITS = ("fernsehfranzi-retropie.service",)

# 3.4: zeit "frei" (kein Timer) / "zaehlt" (allgemeiner Timer); limit_min = höchstens X min (Zahl oder je Tagesart);
# sperr_erlaubt = Sperrzeiten, in denen die App trotzdem geht (Liste von Namen oder "alle").
VORGABE = [
    {"id": "plex", "name": "Plex", "typ": "web", "start": "", "zeit": "frei", "sperr_erlaubt": [], "eingabe": "tasten",
     "domains": [], "aktiv": True, "symbol": "film", "farbe": "#e5a00d", "reihenfolge": 10},
    {"id": "games", "name": "Games", "typ": "konsole", "start": "fernsehfranzi-retropie.service",
     "zeit": "gaming", "limit_min": {"schultag": 45, "frei": 75}, "sperr_erlaubt": [], "eingabe": "tasten",
     "domains": [], "aktiv": True, "symbol": "spiel", "farbe": "#e4002b", "reihenfolge": 20},
    {"id": "familie", "name": "Familie", "typ": "web", "start": "", "zeit": "frei", "sperr_erlaubt": "alle",
     "eingabe": "tasten", "domains": [], "aktiv": True, "symbol": "haus", "farbe": "#2e7d32", "reihenfolge": 30},
    {"id": "buecher", "name": "Bücher", "typ": "web", "start": "", "zeit": "frei", "sperr_erlaubt": [], "eingabe": "tasten",
     "domains": [], "aktiv": True, "symbol": "buch", "farbe": "#1565c0", "reihenfolge": 40},
    # Öffentliche Lernangebote. Lernen zählt nicht zur Zeit (änderbar).
    {"id": "klassenkiste", "name": "Klassenkiste", "typ": "web", "start": "https://klassenkiste.eu/",
     "zeit": "frei", "sperr_erlaubt": [], "lernen": True, "eingabe": "tasten", "domains": ["klassenkiste.eu"],
     "aktiv": True, "symbol": "lernen", "farbe": "#00897b", "reihenfolge": 50},
    {"id": "kinderwelten", "name": "Kinderwelten", "typ": "web", "start": "https://app.familienfabrik.at/",
     "zeit": "frei", "sperr_erlaubt": [], "lernen": True, "eingabe": "tasten", "domains": ["familienfabrik.at"],
     "aktiv": True, "symbol": "stern", "farbe": "#f57c00", "reihenfolge": 60},
    # 3.4: Gute Nacht = Hörbuch-Player mit Sleep-Timer, jederzeit (auch Mittagsschlaf); Freigabelink tragen die Eltern ein
    {"id": "gute-nacht", "name": "Gute Nacht", "typ": "hoerbuch", "start": "", "zeit": "frei", "sperr_erlaubt": "alle",
     "eingabe": "tasten", "domains": [], "aktiv": True, "symbol": "mond", "farbe": "#2b2f6b", "reihenfolge": 5},
    # 3.5: YouTube-Bereich - Videos/Playlists, die die Eltern in Kategorien speichern (eigener Player, nur das Video)
    {"id": "youtube", "name": "YouTube", "typ": "youtube", "start": "", "zeit": "zaehlt", "sperr_erlaubt": [],
     "eingabe": "tasten", "domains": [], "aktiv": True, "symbol": "video", "farbe": "#c4302b", "reihenfolge": 15},
]
# Vorgabe-Apps, die nach der ersten Einrichtung dazugekommen sind: werden einmal ergänzt
# (löschen die Eltern sie danach, bleiben sie weg). "hoerspiele" (3.2/3.3) wurde in 3.4 zu "gute-nacht".
NACHTRAEGLICH = {"gute-nacht": "3.4", "youtube": "3.5"}
SYMBOLE = ("film", "spiel", "haus", "buch", "lernen", "musik", "malen", "web", "stern", "mond", "tier", "ball", "video")


# Korrekturen an früheren Vorgabe-Adressen (werden beim Laden einmalig übernommen).
ADRESS_KORREKTUREN = {"https://apps.familienfabrik.at/": "https://app.familienfabrik.at/"}


class KatalogFehler(ValueError):
    """Sammelt alle Fehler eines Katalogs (eine Meldung pro Zeile)."""

    def __init__(self, fehler):
        super().__init__("\n".join(fehler))
        self.fehler = fehler


def _pruefe_eintrag(eintrag, nr):
    fehler = []
    wo = "Eintrag %d" % nr
    if not isinstance(eintrag, dict):
        return ["%s: muss ein Objekt sein." % wo]
    kennung = eintrag.get("id")
    if not isinstance(kennung, str) or not KENNUNG.match(kennung):
        fehler.append("%s: id fehlt oder ist ungültig (a-z, 0-9, -; höchstens 32 Zeichen)." % wo)
    else:
        wo = "App '%s'" % kennung
    name = eintrag.get("name")
    if not isinstance(name, str) or not name.strip() or len(name) > 40:
        fehler.append("%s: name fehlt oder ist länger als 40 Zeichen." % wo)
    typ = eintrag.get("typ")
    if typ not in TYPEN:
        fehler.append("%s: typ muss %s sein." % (wo, " / ".join(TYPEN)))
    start = eintrag.get("start", "")
    if not isinstance(start, str):
        fehler.append("%s: start muss Text sein." % wo)
    elif start:
        if typ == "web":
            teile = urlsplit(start)
            if teile.scheme not in ("http", "https") or not teile.netloc:
                fehler.append("%s: start muss eine http(s)-Adresse sein." % wo)
        elif typ == "youtube":
            fehler.append("%s: YouTube braucht keine Adresse (Videos auf der Eltern-Seite → YouTube)." % wo)
        elif typ in ("hoerbuch", "video") and hoerbuch.pruefe_freigabe(start):
            fehler.append("%s: Adresse %s." % (wo, hoerbuch.pruefe_freigabe(start)))
        elif typ == "konsole" and start not in KONSOLE_UNITS:
            fehler.append("%s: Konsolen-Apps dürfen nur %s starten." % (wo, ", ".join(KONSOLE_UNITS)))
        elif typ == "desktop" and (start.startswith("-") or "\n" in start):
            fehler.append("%s: start ist kein gültiger Befehl." % wo)
    if eintrag.get("zeit") not in ZEIT:
        fehler.append("%s: zeit muss %s sein." % (wo, " / ".join(ZEIT)))
    limit = eintrag.get("limit_min")
    werte = list(limit.values()) if isinstance(limit, dict) else [limit]
    if limit is not None and (isinstance(limit, dict) and set(limit) - {"schultag", "frei"} or
                              not all(w is None or (isinstance(w, int) and not isinstance(w, bool) and 0 < w <= 600)
                                      for w in werte)):
        fehler.append("%s: höchstens-Minuten müssen 1 bis 600 sein." % wo)
    profil = eintrag.get("plex_profil", "")
    if not isinstance(profil, str) or len(profil) > 40:
        fehler.append("%s: Plex-Profil höchstens 40 Zeichen." % wo)
    if eintrag.get("bereich", "") not in BEREICHE:
        fehler.append("%s: bereich muss %s sein (leer = automatisch)." % (wo, " / ".join(b for b in BEREICHE if b)))
    erlaubt = eintrag.get("sperr_erlaubt", [])
    if erlaubt != "alle" and (not isinstance(erlaubt, list) or
                              not all(isinstance(n, str) and 0 < len(n) <= 30 for n in erlaubt)):
        fehler.append("%s: sperr_erlaubt muss eine Liste von Sperrzeiten oder \"alle\" sein." % wo)
    if eintrag.get("eingabe", "tasten") not in EINGABE:
        fehler.append("%s: eingabe muss %s sein." % (wo, " / ".join(EINGABE)))
    domains = eintrag.get("domains", [])
    if not isinstance(domains, list):
        fehler.append("%s: domains muss eine Liste sein." % wo)
    else:
        for domain in domains:
            if not isinstance(domain, str) or not DOMAIN.match(domain.lower()):
                fehler.append("%s: Domain %r ist ungültig." % (wo, domain))
    if not isinstance(eintrag.get("lernen", False), bool):
        fehler.append("%s: lernen muss true oder false sein." % wo)
    if not isinstance(eintrag.get("aktiv", True), bool):
        fehler.append("%s: aktiv muss true oder false sein." % wo)
    if not isinstance(eintrag.get("bewegung", True), bool):
        fehler.append("%s: bewegung (Bewegungspause) muss true oder false sein." % wo)
    symbol = eintrag.get("symbol", "")
    if symbol and symbol not in SYMBOLE:
        fehler.append("%s: symbol muss eines von %s sein." % (wo, ", ".join(SYMBOLE)))
    farbe = eintrag.get("farbe")
    if farbe is not None and (not isinstance(farbe, str) or not FARBE.match(farbe)):
        fehler.append("%s: farbe muss die Form #rrggbb haben." % wo)
    reihenfolge = eintrag.get("reihenfolge", 0)
    if not isinstance(reihenfolge, int) or isinstance(reihenfolge, bool):
        fehler.append("%s: reihenfolge muss eine ganze Zahl sein." % wo)
    return fehler


def pruefe_katalog(katalog):
    """Gibt den Katalog sortiert zurück oder wirft KatalogFehler mit allen Problemen."""
    if not isinstance(katalog, list):
        raise KatalogFehler(["Der Katalog muss eine Liste sein."])
    fehler, gesehen = [], set()
    for nr, eintrag in enumerate(katalog, 1):
        fehler += _pruefe_eintrag(eintrag, nr)
        kennung = eintrag.get("id") if isinstance(eintrag, dict) else None
        if isinstance(kennung, str):
            if kennung in gesehen:
                fehler.append("App '%s': id kommt doppelt vor." % kennung)
            gesehen.add(kennung)
    if fehler:
        raise KatalogFehler(fehler)
    return sorted(katalog, key=lambda e: (e.get("reihenfolge", 0), e["id"]))


def kacheln(katalog):
    """Was die Startseite zeigt: aktive Einträge; ohne ``start`` mit Hinweis statt Ziel."""
    ergebnis = []
    for eintrag in pruefe_katalog(katalog):
        if not eintrag.get("aktiv", True):
            continue
        ergebnis.append({
            "id": eintrag["id"], "name": eintrag["name"], "typ": eintrag["typ"],
            "symbol": eintrag.get("symbol", ""), "farbe": eintrag.get("farbe", ""),
            "eingerichtet": bool(eintrag.get("start")) or eintrag["typ"] == "youtube",
            "lernen": bool(eintrag.get("lernen")), "bereich": eintrag.get("bereich", ""),
        })
    return ergebnis
