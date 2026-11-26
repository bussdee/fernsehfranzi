"""FernsehFranzi 6.2 - Mein Tag: Routinen-Listen, die die Eltern anlegen und das Kind am Fernseher abhakt.

Einstellungen (einstellungen.json, Feld "meintag"):
    {"aktiv": false,                      # ab Werk aus (Grundsatz 6)
     "routinen": [{"nr": 1, "name": "Morgen", "symbol": "☀️",
                   "zeit": "06:45",       # ab hier gilt die Liste (und kommt die Erinnerung)
                   "fertig": "07:30",     # bis dahin soll sie geschafft sein (Zeit-Scheibe „noch 10 Minuten“)
                   "tage": [0, 1, 2, 3, 4], "wann": "schule",      # immer | schule (nicht in den Ferien) | ferien
                   "erinnern": true, "klang": "glocke",
                   "schritte": [{"text": "Zähne putzen", "symbol": "🦷", "timer": 120}]}]}
Zustand des Tages (meintag.json im Datenordner): {"datum": "JJJJ-MM-TT", "erledigt": {"1": [0, 2]}, "geschafft": {"1": "07:12"}}
Das Kind kann nur abhaken - nichts an den Listen ändern (Grundsatz 7).

6.3: Ranzen-Check und Ämter (im selben Feld):
    "ranzen": {"aktiv": false, "immer": ["Federmäppchen"], "faecher": [{"fach": "Sport", "sachen": ["Turnbeutel"]}]}
              -> Packliste für den nächsten Schultag aus dem Stundenplan der Klassenkiste (nur lesen)
    "aufgaben": [{"nr": 1, "text": "Zimmer aufräumen", "symbol": "🧹", "tage": [5], "sterne": 2}]
              -> das Kind meldet „erledigt“, die Eltern bestätigen (Eltern-Seite oder Telegram /ja 1) -> Sterne
Zustand dazu: "ranzen": {"fuer": "JJJJ-MM-TT", "erledigt": ["Turnbeutel"]} (gilt bis zu diesem Schultag),
"aufgaben": {"1": {"stand": "wartet|ja|nein", "zeit": "HH:MM"}} (je Tag), "sterne": 12, "sterne_tage": {"JJJJ-MM-TT": 3}.

6.4: Belohnung - "verdient" (alle je verdienten Sterne, bestimmt das Level), "sterne" (Kontostand, sinkt beim Tausch),
"franzi": {"farbe", "hut", "brille", "extra"} (was Franzi trägt), "listen_tage" (geschaffte Listen je Tag, Wochenrückblick),
"getauscht": {"JJJJ-MM-TT": Minuten}. Sterne gibt es für bestätigte Aufgaben, jede geschaffte Liste und den gepackten Ranzen.
Einstellung "tausch": {"aktiv": false, "minuten": 5, "max_tag": 30} - Sterne gegen Spielzeit, ab Werk aus.

6.5: Lesen üben - Einstellung "lesen": {"aktiv": false, "ziel_min": 10}. Beim Vorlesen misst die Startseite nur den Pegel des
USB-Mikros (keine Aufnahme, keine Spracherkennung) und meldet die Sekunden, in denen vorgelesen wurde. Zustand
"lesepass": {"JJJJ-MM-TT": Minuten}; ist das Ziel des Tages erreicht, gibt es einen Stempel und einen Stern (einmal je Tag).
"""
from datetime import datetime, timedelta

from . import klaenge

VORGABE = {"aktiv": False, "routinen": [], "ranzen": {}, "aufgaben": [], "tausch": {}, "lesen": {}}
LESEN_VORGABE = {"aktiv": False, "ziel_min": 10}
LESEPASS_TAGE = 60
LESEN_MAX_S = 2 * 60 * 60                  # eine Meldung höchstens 2 Stunden
RANZEN_VORGABE = {"aktiv": False, "immer": [], "faecher": []}
AUFGABEN_MAX = 12
STERNE_TAGE = 21
TAUSCH_VORGABE = {"aktiv": False, "minuten": 5, "max_tag": 30}
LEVEL_STERNE = 10                        # alle 10 verdienten Sterne ein Level
# (Level, Art, Kennung, Name) - die Bilder zeichnet gemeinsam.js (franzi)
# 6.9.37: Level schalten nur bei Level 2-4 Sachen frei (danach gibt es neue Räume bei Franzi, alles andere im Shop)
SACHEN = [(2, "hut", "muetze", "Mütze"), (3, "farbe", "blau", "Blau"), (4, "brille", "sonne", "Sonnenbrille")]
FRANZI_ARTEN = ("farbe", "hut", "brille", "extra")
HOECHSTENS = 6
SCHRITTE_MAX = 12
TIMER_WAHL = (0, 30, 60, 90, 120, 180, 300, 600, 900)   # Sekunden; 120 = Zahnputz-Timer, 6.8.9: 10 und 15 min (Abendbrot)
WANN = ("immer", "schule", "ferien")
ROUTINE_FELDER = {"nr", "name", "symbol", "zeit", "fertig", "tage", "wann", "erinnern", "klang", "schritte", "musik",   # 6.8.10: musik
                  "oeffnen"}                                                                                  # 6.9.58
# 6.9.58: Routinen deutlicher auslösen - Erinnerung zu Beginn und danach alle WIEDER_MIN Minuten, bis die Liste geschafft ist
# (höchstens WIEDER_MAX-mal); zur Uhrzeit „fertig“ einmal an die Eltern, wenn sie nicht geschafft wurde.
WIEDER_MIN, WIEDER_MAX = 10, 4


def _uhr(text, wo):
    try:
        return datetime.strptime(str(text), "%H:%M").time()
    except ValueError:
        raise ValueError("%s: Uhrzeit fehlt." % wo) from None


def _kurz(wert, n, wo, pflicht=True):
    if not isinstance(wert, str) or (pflicht and not wert.strip()) or len(wert) > n:
        raise ValueError("%s: Text fehlt oder ist zu lang (höchstens %d Zeichen)." % (wo, n))
    return wert.strip()


def einstellungen(gespeichert):
    m = dict(VORGABE)
    m.update(gespeichert or {})
    m["routinen"] = [dict(r, schritte=[dict(s) for s in r.get("schritte") or []]) for r in m.get("routinen") or []]
    ranzen = dict(RANZEN_VORGABE)
    ranzen.update(m.get("ranzen") or {})
    ranzen["immer"] = list(ranzen.get("immer") or [])
    ranzen["faecher"] = [dict(f, sachen=list(f.get("sachen") or [])) for f in ranzen.get("faecher") or [] if isinstance(f, dict)]
    m["ranzen"] = ranzen
    m["aufgaben"] = [dict(a) for a in m.get("aufgaben") or []]
    tausch = dict(TAUSCH_VORGABE)
    tausch.update(m.get("tausch") or {})
    m["tausch"] = tausch
    lesen = dict(LESEN_VORGABE)
    lesen.update(m.get("lesen") or {})
    m["lesen"] = lesen
    return m


def _sachen(liste, wo, n=10):
    if not isinstance(liste, list) or len(liste) > n:
        raise ValueError("%s: höchstens %d Sachen." % (wo, n))
    return [_kurz(x, 40, wo) for x in liste]


def _zahl(wert, von, bis):
    return isinstance(wert, int) and not isinstance(wert, bool) and von <= wert <= bis


def _pruefe_extra(m):
    le = m["lesen"]
    if set(le) - set(LESEN_VORGABE) or not isinstance(le["aktiv"], bool) or not _zahl(le["ziel_min"], 2, 60):
        raise ValueError("Lesen üben: an/aus und Ziel 2 bis 60 Minuten.")
    t = m["tausch"]
    if set(t) - set(TAUSCH_VORGABE) or not isinstance(t["aktiv"], bool) or not _zahl(t["minuten"], 1, 30) \
            or not _zahl(t["max_tag"], 0, 240):
        raise ValueError("Sterne tauschen: an/aus, 1 bis 30 Minuten je Stern, höchstens 0 bis 240 Minuten am Tag.")
    r = m["ranzen"]
    if set(r) - set(RANZEN_VORGABE) or not isinstance(r["aktiv"], bool):
        raise ValueError("Ranzen-Check: unbekannte Felder.")
    r["immer"] = _sachen(r["immer"], "Ranzen: immer dabei")
    if len(r["faecher"]) > 20:
        raise ValueError("Ranzen-Check: höchstens 20 Fächer.")
    for f in r["faecher"]:
        if set(f) - {"fach", "sachen"}:
            raise ValueError("Ranzen-Check: unbekannte Felder bei einem Fach.")
        f["fach"] = _kurz(f.get("fach"), 40, "Ranzen: Fach")
        f["sachen"] = _sachen(f["sachen"], "Ranzen: %s" % f["fach"], 8)
    if len(m["aufgaben"]) > AUFGABEN_MAX:
        raise ValueError("Höchstens %d Aufgaben." % AUFGABEN_MAX)
    nummern = set()
    for a in m["aufgaben"]:
        if set(a) - {"nr", "text", "symbol", "tage", "sterne"}:
            raise ValueError("Aufgaben: unbekannte Felder.")
        nr = a.get("nr")
        if not isinstance(nr, int) or isinstance(nr, bool) or nr in nummern or not 0 < nr < 1000:
            raise ValueError("Aufgaben: Nummer fehlt oder doppelt.")
        nummern.add(nr)
        a["text"] = _kurz(a.get("text"), 60, "Aufgabe")
        a["symbol"] = _kurz(a.get("symbol", "") or "", 8, "Symbol", pflicht=False)
        if not a.get("tage") or not isinstance(a["tage"], list) or \
                not all(isinstance(t, int) and not isinstance(t, bool) and 0 <= t <= 6 for t in a["tage"]):
            raise ValueError("Aufgabe „%s“: mindestens ein Wochentag." % a["text"])
        if a.get("sterne", 1) not in (1, 2, 3, 4, 5) or isinstance(a.get("sterne", 1), bool):
            raise ValueError("Aufgabe „%s“: 1 bis 5 Sterne." % a["text"])


def pruefe(m):
    """Wirft ValueError mit verständlichem Text (die Eltern-Seite zeigt ihn am Feld)."""
    if not isinstance(m, dict) or set(m) - set(VORGABE):
        raise ValueError("Mein Tag: unbekannte Felder.")
    m = einstellungen(m)
    if not isinstance(m["aktiv"], bool):
        raise ValueError("Mein Tag: an/aus muss ja/nein sein.")
    if not isinstance(m["routinen"], list) or len(m["routinen"]) > HOECHSTENS:
        raise ValueError("Mein Tag: höchstens %d Listen." % HOECHSTENS)
    nummern = set()
    for r in m["routinen"]:
        if not isinstance(r, dict) or set(r) - ROUTINE_FELDER:
            raise ValueError("Mein Tag: unbekannte Felder in einer Liste.")
        nr = r.get("nr")
        if not isinstance(nr, int) or isinstance(nr, bool) or nr in nummern or not 0 < nr < 1000:
            raise ValueError("Mein Tag: Nummer fehlt oder doppelt.")
        nummern.add(nr)
        r["name"] = _kurz(r.get("name"), 30, "Name der Liste")
        r["symbol"] = _kurz(r.get("symbol", "") or "", 8, "Symbol", pflicht=False)
        wo = "Liste „%s“" % r["name"]
        beginn, fertig = _uhr(r.get("zeit"), wo + ", ab"), _uhr(r.get("fertig"), wo + ", fertig um")
        if fertig <= beginn:
            raise ValueError("%s: „fertig um“ muss nach dem Beginn liegen." % wo)
        if not r.get("tage") or not isinstance(r["tage"], list) or \
                not all(isinstance(t, int) and not isinstance(t, bool) and 0 <= t <= 6 for t in r["tage"]):
            raise ValueError("%s: mindestens ein Wochentag." % wo)
        if r.get("wann", "immer") not in WANN:
            raise ValueError("%s: immer, nicht in den Ferien oder nur in den Ferien." % wo)
        if not isinstance(r.get("erinnern", False), bool):
            raise ValueError("%s: Erinnerung ja/nein." % wo)
        if not isinstance(r.get("oeffnen", True), bool):
            raise ValueError("%s: von selbst öffnen ja/nein." % wo)
        klaenge.pruefe(r.get("klang"), wo)
        klaenge.pruefe(r.get("musik"), wo + ", Musik beim Timer")      # 6.8.10: leer = Zahnputz-Lied, „stumm“ = ohne
        schritte = r.get("schritte")
        if not isinstance(schritte, list) or not 0 < len(schritte) <= SCHRITTE_MAX:
            raise ValueError("%s: 1 bis %d Schritte." % (wo, SCHRITTE_MAX))
        for s in schritte:
            if not isinstance(s, dict) or set(s) - {"text", "symbol", "timer"}:
                raise ValueError("%s: unbekannte Felder in einem Schritt." % wo)
            s["text"] = _kurz(s.get("text"), 60, wo + ", Schritt")
            s["symbol"] = _kurz(s.get("symbol", "") or "", 8, "Symbol", pflicht=False)
            if s.get("timer", 0) not in TIMER_WAHL or isinstance(s.get("timer", 0), bool):
                raise ValueError("%s: Timer 0, ½, 1, 1½, 2, 3, 5, 10 oder 15 Minuten." % wo)
    _pruefe_extra(m)
    return m


def gilt_heute(r, tag, ferien):
    if tag.weekday() not in r.get("tage", []):
        return False
    wann = r.get("wann", "immer")
    return wann == "immer" or (wann == "ferien") == bool(ferien)


def zustand_fuer(zustand, tag):
    """Neuer Tag = leere Liste (abgehakt wird jeden Tag neu)."""
    """Ranzen (gilt bis zum Schultag) und Sterne überleben den Tageswechsel."""
    if not isinstance(zustand, dict) or zustand.get("datum") != tag.isoformat():
        alt = zustand if isinstance(zustand, dict) else {}
        zustand = {"datum": tag.isoformat(), "erledigt": {}, "geschafft": {}, "aufgaben": {},
                   "sterne": int(alt.get("sterne", 0) or 0), "sterne_tage": dict(alt.get("sterne_tage") or {}),
                   "verdient": int(alt.get("verdient", alt.get("sterne", 0)) or 0), "franzi": dict(alt.get("franzi") or {}),
                   "listen_tage": dict(alt.get("listen_tage") or {}), "getauscht": dict(alt.get("getauscht") or {}),
                   "lesepass": dict(alt.get("lesepass") or {}), "sammeltage": alt.get("sammeltage"),
                   "ranzen": alt.get("ranzen") if (alt.get("ranzen") or {}).get("fuer", "") >= tag.isoformat() else {}}
    for k, v in (("erledigt", {}), ("geschafft", {}), ("aufgaben", {}), ("sterne", 0), ("sterne_tage", {}), ("ranzen", {}),
                 ("franzi", {}), ("listen_tage", {}), ("getauscht", {}), ("lesepass", {})):
        zustand.setdefault(k, v)
    zustand.setdefault("verdient", int(zustand["sterne"]))
    # 6.9.44: Tage, an denen das Kind Sterne gesammelt hat (für Räume, die nicht an einem Tag freizuschalten sind).
    # Altdaten: aus der Tagesliste (die letzten 21 Tage) übernommen.
    if not isinstance(zustand.get("sammeltage"), int):
        zustand["sammeltage"] = sum(1 for v in zustand["sterne_tage"].values() if v > 0)
    return zustand


def _alte_weg(tage):
    for alt in sorted(tage)[:-STERNE_TAGE]:
        del tage[alt]


def sterne_geben(z, jetzt, anzahl):
    """6.4: verdiente Sterne - Kontostand, Level und Tagesliste."""
    tag = jetzt.date().isoformat()
    z["sterne"] = int(z["sterne"]) + anzahl
    z["verdient"] = int(z["verdient"]) + anzahl
    if anzahl > 0 and not z["sterne_tage"].get(tag):
        z["sammeltage"] = int(z.get("sammeltage") or 0) + 1             # 6.9.44: erster Stern heute
    z["sterne_tage"][tag] = z["sterne_tage"].get(tag, 0) + anzahl
    _alte_weg(z["sterne_tage"])
    if anzahl > 0:
        z["letzter_stern"] = jetzt.isoformat(timespec="seconds")      # 6.9.59: Franzi freut sich (Herzaugen im Menü)


def level(verdient):
    return 1 + int(verdient) // LEVEL_STERNE


def franzi_setzen(z, art, kennung):
    """Das Kind zieht Franzi etwas an (oder aus: kennung leer). Nur, was es schon freigespielt hat."""
    if art not in FRANZI_ARTEN:
        raise ValueError("Das gibt es für Franzi nicht.")
    if kennung:
        sache = next((x for x in SACHEN if x[1] == art and x[2] == kennung), None)
        if sache is None or level(z["verdient"]) < sache[0]:
            raise ValueError("Das gibt es erst ab Level %d." % sache[0] if sache else "Das gibt es für Franzi nicht.")
        z["franzi"][art] = kennung
    else:
        z["franzi"].pop(art, None)
    return z


def lesen_melden(m, jetzt, zustand, sekunden):
    """6.5: So lange wurde gerade vorgelesen. Rückgabe (zustand, neuer_stempel: bool)."""
    if not m["aktiv"] or not m["lesen"]["aktiv"]:
        raise ValueError("Lesen üben ist gerade ausgeschaltet.")
    if not _zahl(sekunden, 0, LESEN_MAX_S):
        raise ValueError("Die Lesezeit stimmt nicht.")
    z = zustand_fuer(zustand, jetzt.date())
    tag = jetzt.date().isoformat()
    vorher = z["lesepass"].get(tag, 0)
    jetzt_min = round(vorher + sekunden / 60, 1)
    z["lesepass"][tag] = jetzt_min
    for alt in sorted(z["lesepass"])[:-LESEPASS_TAGE]:
        del z["lesepass"][alt]
    ziel = m["lesen"]["ziel_min"]
    if vorher < ziel <= jetzt_min:
        sterne_geben(z, jetzt, 1)
        return z, True
    return z, False


def lesepass(m, jetzt, z):
    ziel = m["lesen"]["ziel_min"]
    tag = jetzt.date().isoformat()
    tage = [(jetzt.date() - timedelta(days=13 - i)) for i in range(14)]
    return {"ziel_min": ziel, "heute_min": z["lesepass"].get(tag, 0), "stempel_heute": z["lesepass"].get(tag, 0) >= ziel,
            "stempel": sum(1 for v in z["lesepass"].values() if v >= ziel),
            "tage": [{"tag": t.isoformat(), "kurz": "MDMDFSS"[t.weekday()], "stempel": z["lesepass"].get(t.isoformat(), 0) >= ziel}
                     for t in tage]}


def tauschen(m, jetzt, zustand):
    """Ein Stern gegen Spielzeit (nur wenn die Eltern es eingeschaltet haben). Rückgabe (zustand, minuten)."""
    t = m["tausch"]
    z = zustand_fuer(zustand, jetzt.date())
    if not m["aktiv"] or not t["aktiv"]:
        raise ValueError("Sterne tauschen ist gerade ausgeschaltet.")
    if z["sterne"] < 1:
        raise ValueError("Dafür brauchst du einen Stern.")
    tag = jetzt.date().isoformat()
    schon = z["getauscht"].get(tag, 0)
    if schon + t["minuten"] > t["max_tag"]:
        raise ValueError("Für heute ist genug getauscht – morgen wieder!")
    z["sterne"] -= 1
    z["getauscht"][tag] = schon + t["minuten"]
    _alte_weg(z["getauscht"])
    return z, t["minuten"]


def packliste(m, morgen):
    """6.3: Sachen für den nächsten Schultag. morgen = Schule-Stand „morgen“ ({datum, name, stunden, frei}) oder None."""
    r = m["ranzen"]
    if not m["aktiv"] or not r["aktiv"] or not isinstance(morgen, dict) or not morgen.get("datum") or morgen.get("frei"):
        return None
    faecher = []
    for s in morgen.get("stunden") or []:
        if not s.get("faellt_aus") and s.get("fach") and s["fach"] not in faecher:
            faecher.append(s["fach"])
    if not faecher:
        return None
    sachen = [{"text": x, "fach": ""} for x in r["immer"]]
    for fach in faecher:
        for f in r["faecher"]:
            if f["fach"].casefold() == fach.casefold() or fach.casefold().startswith(f["fach"].casefold()):
                for x in f["sachen"]:
                    if all(x.casefold() != y["text"].casefold() for y in sachen):
                        sachen.append({"text": x, "fach": fach})
    return {"fuer": morgen["datum"], "name": morgen.get("name", ""), "faecher": faecher, "sachen": sachen} if sachen else None


def aufgaben_heute(m, tag):
    return [a for a in m["aufgaben"] if tag.weekday() in a.get("tage", [])] if m["aktiv"] else []


def heute(m, jetzt, ferien, zustand, morgen=None):
    """Listen von heute mit Stand und „Zeit-Scheibe“ - für Fernseher und Eltern-Seite (6.3: dazu Ranzen und Aufgaben)."""
    if not m["aktiv"]:
        return {"aktiv": False, "routinen": [], "aktuell": None, "ranzen": None, "aufgaben": [], "sterne": 0,
                "franzi": dict((zustand or {}).get("franzi") or {}) if isinstance(zustand, dict) else {}}
    z = zustand_fuer(zustand, jetzt.date())
    liste = []
    for r in sorted((r for r in m["routinen"] if gilt_heute(r, jetzt.date(), ferien)), key=lambda r: r["zeit"]):
        beginn = datetime.combine(jetzt.date(), _uhr(r["zeit"], "ab"))
        fertig = datetime.combine(jetzt.date(), _uhr(r["fertig"], "fertig"))
        erledigt = sorted(i for i in z["erledigt"].get(str(r["nr"]), []) if 0 <= i < len(r["schritte"]))
        rest = int((fertig - jetzt).total_seconds())
        liste.append({"nr": r["nr"], "name": r["name"], "symbol": r.get("symbol", ""), "zeit": r["zeit"], "fertig": r["fertig"],
                      "musik": r.get("musik") or "",
                      "schritte": [dict(s, erledigt=i in erledigt) for i, s in enumerate(r["schritte"])],
                      "anzahl": len(r["schritte"]), "erledigt": len(erledigt),
                      "geschafft": z["geschafft"].get(str(r["nr"])),
                      "puenktlich": bool(z.get("puenktlich", {}).get(str(r["nr"]))),
                      "laeuft": beginn <= jetzt < fertig,
                      "rest_s": max(0, rest), "dauer_s": int((fertig - beginn).total_seconds()),
                      "vorbei": jetzt >= fertig})
    # Aktuell: die laufende Liste, sonst die nächste noch nicht geschaffte, sonst die letzte
    aktuell = next((r["nr"] for r in liste if r["laeuft"]), None) or \
        next((r["nr"] for r in liste if not r["vorbei"] and not r["geschafft"]), None) or \
        (liste[-1]["nr"] if liste else None)
    ranzen = packliste(m, morgen)
    if ranzen:
        gepackt = set(z["ranzen"].get("erledigt", [])) if z["ranzen"].get("fuer") == ranzen["fuer"] else set()
        for x in ranzen["sachen"]:
            x["erledigt"] = x["text"] in gepackt
        ranzen["erledigt"] = sum(1 for x in ranzen["sachen"] if x["erledigt"])
    aufgaben = [dict(a, stand=(z["aufgaben"].get(str(a["nr"])) or {}).get("stand"))
                for a in aufgaben_heute(m, jetzt.date())]
    stufe = level(z["verdient"])
    tag = jetzt.date().isoformat()
    t = m["tausch"]
    woche = None
    if jetzt.weekday() == 6:                             # Sonntag: „Das hast du diese Woche geschafft“
        tage = [(jetzt.date() - timedelta(days=i)).isoformat() for i in range(7)]
        woche = {"sterne": sum(z["sterne_tage"].get(x, 0) for x in tage),
                 "listen": sum(z["listen_tage"].get(x, 0) for x in tage)}
    return {"aktiv": True, "routinen": liste, "aktuell": aktuell, "ranzen": ranzen, "aufgaben": aufgaben,
            "sterne": z["sterne"], "sterne_heute": z["sterne_tage"].get(tag, 0),
            "verdient": z["verdient"], "level": stufe, "naechstes_bei": stufe * LEVEL_STERNE, "sammeltage": z["sammeltage"],
            "sachen": [{"level": lv, "art": art, "id": k, "name": n, "frei": stufe >= lv, "an": z["franzi"].get(art) == k}
                       for lv, art, k, n in SACHEN],
            "franzi": dict(z["franzi"]), "woche": woche,
            "lesen": lesepass(m, jetzt, z) if m["lesen"]["aktiv"] else None,
            "tausch": {"minuten": t["minuten"], "rest_min": max(0, t["max_tag"] - z["getauscht"].get(tag, 0))} if t["aktiv"] else None}


def ranzen_abhaken(m, jetzt, zustand, morgen, nr, an):
    liste = packliste(m, morgen)
    if not liste or not isinstance(nr, int) or isinstance(nr, bool) or not 0 <= nr < len(liste["sachen"]):
        raise ValueError("Diese Sache gibt es auf der Packliste nicht.")
    z = zustand_fuer(zustand, jetzt.date())
    if z["ranzen"].get("fuer") != liste["fuer"]:
        z["ranzen"] = {"fuer": liste["fuer"], "erledigt": []}
    erledigt = [x for x in z["ranzen"]["erledigt"] if x != liste["sachen"][nr]["text"]]
    if an:
        erledigt.append(liste["sachen"][nr]["text"])
    z["ranzen"]["erledigt"] = erledigt
    fertig = all(x["text"] in erledigt for x in liste["sachen"])
    if fertig and an and not z["ranzen"].get("stern"):
        z["ranzen"]["stern"] = True                     # 6.4: gepackter Ranzen = ein Stern (einmal je Schultag)
        sterne_geben(z, jetzt, 1)
    return z, fertig and an


def aufgabe_melden(m, jetzt, zustand, nr):
    """Das Kind sagt „erledigt“. Rückgabe (zustand, aufgabe)."""
    a = next((a for a in aufgaben_heute(m, jetzt.date()) if a["nr"] == nr), None)
    if a is None:
        raise ValueError("Diese Aufgabe gibt es heute nicht.")
    z = zustand_fuer(zustand, jetzt.date())
    if (z["aufgaben"].get(str(nr)) or {}).get("stand") == "ja":
        raise ValueError("Diese Aufgabe ist schon bestätigt.")
    z["aufgaben"][str(nr)] = {"stand": "wartet", "zeit": jetzt.strftime("%H:%M")}
    return z, a


def aufgabe_bestaetigen(m, jetzt, zustand, nr, ja):
    """Die Eltern sagen ja (Sterne) oder nein (noch nicht ganz). Rückgabe (zustand, aufgabe)."""
    a = next((a for a in aufgaben_heute(m, jetzt.date()) if a["nr"] == nr), None)
    z = zustand_fuer(zustand, jetzt.date())
    if a is None or (z["aufgaben"].get(str(nr)) or {}).get("stand") != "wartet":
        raise ValueError("Zu dieser Aufgabe wartet gerade keine Meldung.")
    z["aufgaben"][str(nr)] = {"stand": "ja" if ja else "nein", "zeit": jetzt.strftime("%H:%M")}
    if ja:
        sterne_geben(z, jetzt, int(a.get("sterne", 1)))
    return z, a


def abhaken(m, jetzt, ferien, zustand, nr, schritt, an):
    """Rückgabe (zustand, geschafft_jetzt: Routine oder None). Wirft ValueError bei falschen Angaben."""
    r = next((r for r in m["routinen"] if r["nr"] == nr), None) if m["aktiv"] else None
    if r is None or not gilt_heute(r, jetzt.date(), ferien):
        raise ValueError("Diese Liste gibt es heute nicht.")
    if not isinstance(schritt, int) or isinstance(schritt, bool) or not 0 <= schritt < len(r["schritte"]):
        raise ValueError("Diesen Schritt gibt es nicht.")
    z = zustand_fuer(zustand, jetzt.date())
    erledigt = set(z["erledigt"].get(str(nr), []))
    vorher_fertig = len(erledigt) >= len(r["schritte"])
    if an:
        erledigt.add(schritt)
    else:
        erledigt.discard(schritt)
    z["erledigt"][str(nr)] = sorted(erledigt)
    jetzt_fertig = len(erledigt) >= len(r["schritte"])
    if jetzt_fertig and not vorher_fertig and str(nr) not in z["geschafft"]:
        z["geschafft"][str(nr)] = jetzt.strftime("%H:%M")
        tag = jetzt.date().isoformat()
        z["listen_tage"][tag] = z["listen_tage"].get(tag, 0) + 1
        _alte_weg(z["listen_tage"])
        puenktlich = jetzt <= datetime.combine(jetzt.date(), _uhr(r["fertig"], "fertig"))
        sterne_geben(z, jetzt, 2 if puenktlich else 1)  # 6.4: geschaffte Liste = ein Stern; 6.8.9: bis „fertig um“ +1 Bonus
        z.setdefault("puenktlich", {})[str(nr)] = puenktlich
        return z, r
    return z, None


def erinnerungen_faellig(m, jetzt, ferien, erledigt, zustand=None):
    """Listen, die jetzt erinnern sollen: zu Beginn (2 Minuten Spielraum) und - solange nicht geschafft - alle WIEDER_MIN
    Minuten wieder (6.9.58). Rückgabe [(routine, offen)] mit offen = Zahl der noch offenen Schritte (None = Beginn)."""
    if not m["aktiv"]:
        return []
    z = zustand_fuer(zustand, jetzt.date())
    aus = []
    for r in m["routinen"]:
        if not r.get("erinnern") or not gilt_heute(r, jetzt.date(), ferien):
            continue
        beginn = datetime.combine(jetzt.date(), _uhr(r["zeit"], "ab"))
        fertig = datetime.combine(jetzt.date(), _uhr(r["fertig"], "fertig"))
        if not beginn <= jetzt < fertig or z["geschafft"].get(str(r["nr"])):
            continue
        runde = int((jetzt - beginn).total_seconds() // 60) // WIEDER_MIN
        if runde > WIEDER_MAX or (jetzt - beginn - timedelta(minutes=runde * WIEDER_MIN)) >= timedelta(minutes=2):
            continue
        schluessel = "meintag:%s:%d:%s:%d" % (jetzt.date().isoformat(), r["nr"], r["zeit"], runde)
        if schluessel in erledigt:
            continue
        erledigt.add(schluessel)
        offen = len(r["schritte"]) - len(z["erledigt"].get(str(r["nr"]), []))
        aus.append((r, None if runde == 0 else max(0, offen)))
    return aus


def nicht_geschafft(m, jetzt, ferien, erledigt, zustand=None):
    """6.9.58: Listen mit Erinnerung, deren „fertig“ gerade vorbei ist (10 Minuten Spielraum, je Tag einmal) und die nicht
    geschafft wurden - für eine Nachricht an die Eltern. Rückgabe [(routine, erledigt, anzahl)]."""
    if not m["aktiv"]:
        return []
    z = zustand_fuer(zustand, jetzt.date())
    aus = []
    for r in m["routinen"]:
        if not r.get("erinnern") or not gilt_heute(r, jetzt.date(), ferien):
            continue
        fertig = datetime.combine(jetzt.date(), _uhr(r["fertig"], "fertig"))
        schluessel = "meintag-offen:%s:%d" % (jetzt.date().isoformat(), r["nr"])
        if fertig <= jetzt < fertig + timedelta(minutes=10) and schluessel not in erledigt and not z["geschafft"].get(str(r["nr"])):
            erledigt.add(schluessel)
            aus.append((r, len(z["erledigt"].get(str(r["nr"]), [])), len(r["schritte"])))
    return aus


def laufende_liste(m, jetzt, ferien, zustand=None):
    """6.9.58: die gerade laufende, noch nicht geschaffte Liste - für die Startseite (Kachel hervorheben, Mein Tag von selbst
    öffnen). None, wenn keine läuft."""
    if not m["aktiv"]:
        return None
    z = zustand_fuer(zustand, jetzt.date())
    for r in sorted((r for r in m["routinen"] if gilt_heute(r, jetzt.date(), ferien)), key=lambda r: r["zeit"]):
        beginn = datetime.combine(jetzt.date(), _uhr(r["zeit"], "ab"))
        fertig = datetime.combine(jetzt.date(), _uhr(r["fertig"], "fertig"))
        if beginn <= jetzt < fertig and not z["geschafft"].get(str(r["nr"])):
            return {"nr": r["nr"], "name": r["name"], "symbol": r.get("symbol", ""), "oeffnen": r.get("oeffnen", True) is not False,
                    "schluessel": "%s-%d-%s" % (jetzt.date().isoformat(), r["nr"], r["zeit"]),
                    "runde": int((jetzt - beginn).total_seconds() // 60) // WIEDER_MIN,
                    "offen": max(0, len(r["schritte"]) - len(z["erledigt"].get(str(r["nr"]), []))), "anzahl": len(r["schritte"]),
                    "rest_min": int((fertig - jetzt).total_seconds() // 60)}
    return None