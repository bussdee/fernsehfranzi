"""Zeitkonto (neu in 3.4) - reine Logik, mit Testuhr prüfbar.

Gezählt wird auf dem Server. Der Server ruft ``tick`` regelmäßig auf (z. B. alle 5 s) und
speichert ``konto.zustand`` alle 30 s; ein Neustart ändert am Konto nichts.

Modell 3.4:
- Je App ``zeit``: "frei" (kein Timer) oder "zaehlt" (allgemeiner Tages-Timer ``budget_min``).
  Optional ``limit_min``: höchstens X min am Tag - Zahl oder {"schultag": X, "frei": Y} - zusätzlich zum
  allgemeinen Timer (Entscheidung 8.1). Alter Wert "nie" gilt wie "frei".
- ``sperrzeiten``: Liste {name, von, bis, tage, ferien_frei, nacht}. Darf über Mitternacht gehen; gehört zu dem Tag,
  an dem sie beginnt. In einer Sperrzeit ist jede App gesperrt, außer sie erlaubt sie (``sperr_erlaubt``:
  Liste von Namen oder "alle"). Gilt für alle Apps, auch freie.

4.6: ``zeit`` kann auch "gaming" sein: Die Minuten zählen zum allgemeinen Timer (Bildschirmzeit) UND zur Gaming-Zeit
``gaming_min`` (je Tagesart) - Gaming ist ein Teil der Bildschirmzeit. Eine freie App mit ``limit_min`` hat nur ihr eigenes
Limit („nur eigenes Limit“). Bonus der Eltern und Lernbonus gelten für beide Töpfe. ``bundesland`` und ``ferien_auto``:
Ferien des Landes per Knopf bzw. von selbst (siehe ferien.py).
"""
import copy
from datetime import date, datetime, time as uhrzeit, timedelta

VORGABE_REGELN = {
    "budget_min": {"schultag": 90, "frei": 150},
    "gaming_min": {"schultag": 45, "frei": 75},        # 4.6: Teil der Bildschirmzeit für Apps mit zeit "gaming"
    "bundesland": "",                                   # 4.6: für „Ferien eintragen“ (z. B. "SH")
    "ferien_auto": False,                               # 4.6: neue Ferien des Landes von selbst übernehmen
    "ferien_feiertage": True,                           # 4.6: gesetzliche Feiertage gleich mit eintragen
    "sperrzeiten": [
        {"name": "Nacht", "von": "19:30", "bis": "08:00", "tage": [0, 1, 2, 3, 4, 5, 6], "ferien_frei": False, "nacht": True},
        {"name": "Schule", "von": "08:00", "bis": "14:00", "tage": [0, 1, 2, 3, 4], "ferien_frei": True, "nacht": False},
    ],
    "wochenende": [5, 6],          # date.weekday(): 5 = Samstag, 6 = Sonntag
    "ferien": [],                  # [["2026-12-21", "2027-01-06"], ...] jeweils einschließlich
    "warnungen_min": [10, 5, 1],
    "kulanz_min": 2,
}
SPERR_FELDER = {"name", "von", "bis", "tage", "ferien_frei", "nacht"}


def neue_regeln(aenderungen=None):
    regeln = copy.deepcopy(VORGABE_REGELN)
    for schluessel, wert in (aenderungen or {}).items():
        if schluessel not in regeln:
            raise ValueError("Unbekannte Zeitregel: %s" % schluessel)
        regeln[schluessel] = wert
    return regeln


def alte_regeln_uebernehmen(zeit, schlafenszeit=None):
    """3.3 -> 3.4: Zeitfenster (und Schlafenszeit) werden zu Sperrzeiten; retropie_max_min liefert der Aufrufer
    an die Games-App weiter. Gibt (neue zeit-Regeln, retropie_max oder None) zurück."""
    zeit = dict(zeit or {})
    retro = zeit.pop("retropie_max_min", None)
    fenster = zeit.pop("fenster", None)
    if fenster is not None and "sperrzeiten" not in zeit:
        schul_von, schul_bis = fenster.get("schultag", ["14:00", "19:30"])
        frei_von, _ = fenster.get("frei", ["08:00", "20:00"])
        nacht_ab = schul_bis
        if schlafenszeit and schlafenszeit.get("aktiv") and schlafenszeit.get("zeit"):
            nacht_ab = min(schul_bis, schlafenszeit["zeit"])
        zeit["sperrzeiten"] = [
            {"name": "Nacht", "von": nacht_ab, "bis": frei_von, "tage": list(range(7)), "ferien_frei": False, "nacht": True},
            {"name": "Schule", "von": frei_von, "bis": schul_von, "tage": [0, 1, 2, 3, 4], "ferien_frei": True, "nacht": False},
        ]
    return zeit, retro


def tagesart(tag, regeln):
    """'schultag' oder 'frei' (Wochenende und Ferien)."""
    if tag.weekday() in regeln["wochenende"]:
        return "frei"
    return "frei" if in_ferien(tag, regeln) else "schultag"


def in_ferien(tag, regeln):
    return any(date.fromisoformat(von) <= tag <= date.fromisoformat(bis) for von, bis in regeln["ferien"])


def _uhr(text):
    stunde, minute = text.split(":")
    return uhrzeit(int(stunde), int(minute))


def zaehlt(app):
    """Zieht diese App vom allgemeinen Timer ab? (Bildschirmzeit und Gaming-Zeit; freie Apps und "nie" nicht)"""
    return bool(app) and app.get("zeit") in ("zaehlt", "gaming")


def ist_gaming(app):
    return bool(app) and app.get("zeit") == "gaming"


def hat_limit(app):
    """Hat die App eine eigene Höchstgrenze (an irgendeiner Tagesart)?"""
    limit = (app or {}).get("limit_min")
    return bool(limit.get("schultag") or limit.get("frei")) if isinstance(limit, dict) else bool(limit)


def begrenzt(app):
    """Wird für diese App überhaupt gezählt? (Timer, Gaming oder nur eigenes Limit)"""
    return zaehlt(app) or hat_limit(app)


def ist_retropie(app):
    return bool(app) and app.get("typ") == "konsole"


def limit_heute(app, art):
    """Höchstens-Minuten dieser App für die Tagesart (oder None)."""
    limit = (app or {}).get("limit_min")
    if isinstance(limit, dict):
        return limit.get(art)
    return limit


def erlaubt_in(app, sperrzeit):
    erlaubt = (app or {}).get("sperr_erlaubt") or []
    return erlaubt == "alle" or sperrzeit["name"] in erlaubt


def _sperr_bereiche(sperrzeit, tag, regeln):
    """Zeiträume (beginn, ende) dieser Sperrzeit, die am Kalendertag ``tag`` beginnen."""
    if tag.weekday() not in sperrzeit.get("tage", range(7)):
        return []
    if sperrzeit.get("ferien_frei") and in_ferien(tag, regeln):
        return []
    beginn = datetime.combine(tag, _uhr(sperrzeit["von"]))
    ende = datetime.combine(tag, _uhr(sperrzeit["bis"]))
    if ende <= beginn:
        ende += timedelta(days=1)          # über Mitternacht
    return [(beginn, ende)]


def aktive_sperrzeiten(jetzt, regeln):
    """[(sperrzeit, ende)] - alle, die gerade gelten (auch die vom Vortag, die über Mitternacht reichen)."""
    ergebnis = []
    for s in regeln["sperrzeiten"]:
        for tag in (jetzt.date() - timedelta(days=1), jetzt.date()):
            for beginn, ende in _sperr_bereiche(s, tag, regeln):
                if beginn <= jetzt < ende:
                    ergebnis.append((s, ende))
    return ergebnis


def naechste_sperrzeiten(jetzt, regeln, innerhalb_s):
    """[(sperrzeit, beginn)] - beginnen in den nächsten ``innerhalb_s`` Sekunden (oder haben eben begonnen: Sekunden < 0
    zählen nicht)."""
    ergebnis = []
    for s in regeln["sperrzeiten"]:
        for tag in (jetzt.date(), jetzt.date() + timedelta(days=1)):
            for beginn, _ in _sperr_bereiche(s, tag, regeln):
                if 0 < (beginn - jetzt).total_seconds() <= innerhalb_s:
                    ergebnis.append((s, beginn))
    return ergebnis


def begonnene_sperrzeiten(jetzt, regeln, vor_hoechstens_s):
    """[(sperrzeit, beginn)] - haben vor höchstens ``vor_hoechstens_s`` Sekunden begonnen (für das Umschalten zu Beginn)."""
    ergebnis = []
    for s in regeln["sperrzeiten"]:
        for tag in (jetzt.date() - timedelta(days=1), jetzt.date()):
            for beginn, ende in _sperr_bereiche(s, tag, regeln):
                if 0 <= (jetzt - beginn).total_seconds() < vor_hoechstens_s and jetzt < ende:
                    ergebnis.append((s, beginn))
    return ergebnis


def sperrzeit_symbol(sperrzeit):
    if sperrzeit.get("nacht"):
        return "nacht"
    return "schule" if "schul" in sperrzeit.get("name", "").lower() else "sperrzeit"


class Zeitkonto:
    def __init__(self, regeln=None, zustand=None):
        self.regeln = regeln or neue_regeln()
        self.zustand = zustand if zustand is not None else {}

    # ------------------------------------------------------------ Tageswechsel
    def _tag(self, jetzt):
        heute = jetzt.date().isoformat()
        if self.zustand.get("datum") != heute:
            sonder = self.zustand.get("sonder_bis")             # Gutschein über Mitternacht bleibt gültig
            self.zustand.clear()
            self.zustand.update(datum=heute, genutzt_s=0, retropie_s=0, app_s={}, bonus_min=0, gaming_s=0,
                                ohne_limit=False, gewarnt=[], ende_seit=None, sonder_bis=sonder)
        self.zustand.setdefault("gaming_s", 0)                 # Stand von vor 4.6 (am Tag des Updates)
        return self.zustand

    # ------------------------------------------------------------ Besonderer Gutschein (3.5)
    def sonder_frei(self, jetzt, minuten):
        """X Minuten lang: alle Apps erlaubt (auch in Sperrzeiten), nichts zählt."""
        z = self._tag(jetzt)
        ab = max(jetzt, datetime.fromisoformat(z["sonder_bis"])) if z.get("sonder_bis") else jetzt
        z["sonder_bis"] = (ab + timedelta(minutes=int(minuten))).isoformat(timespec="seconds")
        z["ende_seit"] = None

    def sonder_aktiv(self, jetzt):
        bis = self._tag(jetzt).get("sonder_bis")
        return bool(bis) and jetzt < datetime.fromisoformat(bis)

    # ------------------------------------------------------------ Abfragen
    def budget_s(self, jetzt):
        z = self._tag(jetzt)
        art = tagesart(jetzt.date(), self.regeln)
        return (self.regeln["budget_min"][art] + z["bonus_min"]) * 60

    def gaming_budget_s(self, jetzt):
        z = self._tag(jetzt)
        art = tagesart(jetzt.date(), self.regeln)
        return (self.regeln["gaming_min"][art] + z["bonus_min"]) * 60

    def gaming_rest_s(self, jetzt):
        z = self._tag(jetzt)
        if z["ohne_limit"]:
            return None
        return max(0, min(self.gaming_budget_s(jetzt) - z["gaming_s"], self.budget_s(jetzt) - z["genutzt_s"]))

    def rest_s(self, jetzt, app=None):
        """Restzeit in Sekunden des allgemeinen Timers (bzw. für ``app``: dazu Gaming-Zeit und eigene Höchstgrenze).
        None = ohne Limit (oder eine App, für die nichts zählt)."""
        z = self._tag(jetzt)
        if z["ohne_limit"]:
            return None
        if app is not None and not begrenzt(app):
            return None
        rest = self.budget_s(jetzt) - z["genutzt_s"] if app is None or zaehlt(app) else 24 * 3600
        if ist_gaming(app):
            rest = min(rest, self.gaming_budget_s(jetzt) - z["gaming_s"])
        if app is not None:
            limit = limit_heute(app, tagesart(jetzt.date(), self.regeln))
            if limit:
                rest = min(rest, limit * 60 - z["app_s"].get(app["id"], 0))
        return max(0, rest)

    def sperre_fuer(self, app, jetzt):
        """Die Sperrzeit, die diese App gerade sperrt (oder None)."""
        if self.sonder_aktiv(jetzt):
            return None
        for s, ende in aktive_sperrzeiten(jetzt, self.regeln):
            if not erlaubt_in(app, s):
                return s, ende
        return None

    def darf_starten(self, app, jetzt, uhr_sicher=True):
        """(ok, grund, art) - grund ist ein kindgerechter Text, art das Symbol der Kachel:
        zeit · nacht · schule · sperrzeit · uhr."""
        frei = not begrenzt(app)
        if not uhr_sicher:
            # Pi 3 ohne Echtzeituhr: solange die Zeit nicht feststeht, gilt die strengere Regel - nur Apps, die
            # nie gesperrt sind (frei und in allen Sperrzeiten erlaubt), gehen schon.
            if frei and ((app or {}).get("sperr_erlaubt") == "alle" or not self.regeln["sperrzeiten"]):
                return True, "", ""
            return False, "Einen Moment, die Uhr stellt sich noch.", "uhr"
        gesperrt = self.sperre_fuer(app, jetzt)
        if gesperrt:
            s, ende = gesperrt
            return False, "%s – wieder ab %s Uhr." % (s["name"], ende.strftime("%H:%M")), sperrzeit_symbol(s)
        if frei or self.sonder_aktiv(jetzt):
            return True, "", ""
        if self._tag(jetzt)["ohne_limit"]:
            return True, "", ""
        if self.rest_s(jetzt, app) <= 0:
            if zaehlt(app) and self.budget_s(jetzt) - self._tag(jetzt)["genutzt_s"] <= 0:
                return False, "Für heute ist die Zeit aufgebraucht.", "zeit"
            if ist_gaming(app) and self.gaming_rest_s(jetzt) <= 0:
                return False, "Die Spielzeit für heute ist aufgebraucht – Filme, Lernen und Malen gehen noch.", "zeit"
            return False, "Für %s ist die Zeit heute aufgebraucht." % app.get("name", "diese App"), "zeit"
        return True, "", ""

    # ------------------------------------------------------------ Zählen
    def tick(self, jetzt, app, sekunden, aktiv=True):
        """``sekunden`` seit dem letzten Aufruf in ``app`` verbracht.

        aktiv=False: keine Eingabe (Leerlauf) - dann zählt nichts.
        Rückgabe: Liste von Ereignissen, z. B. ("warnung", 5) oder ("schluss", app_id).
        """
        z = self._tag(jetzt)
        ereignisse = []
        if not begrenzt(app) or not aktiv or sekunden <= 0 or self.sonder_aktiv(jetzt):
            return ereignisse
        sekunden = min(sekunden, 60)     # Uhrsprung (z. B. NTP nach dem Start) nicht mitzählen
        if zaehlt(app):
            z["genutzt_s"] += sekunden
        if ist_gaming(app):
            z["gaming_s"] += sekunden
        z["app_s"][app["id"]] = z["app_s"].get(app["id"], 0) + sekunden
        if ist_retropie(app):
            z["retropie_s"] += sekunden
        rest = self.rest_s(jetzt, app)
        if rest is None:
            return ereignisse
        for minuten in sorted(self.regeln["warnungen_min"], reverse=True):
            schluessel = "%s:%d" % (app["id"], minuten)
            if rest <= minuten * 60 and schluessel not in z["gewarnt"]:
                z["gewarnt"].append(schluessel)
                ereignisse.append(("warnung", minuten))
        if rest <= 0:
            if z["ende_seit"] is None:
                z["ende_seit"] = jetzt.isoformat(timespec="seconds")
                ereignisse.append(("kulanz", self.regeln["kulanz_min"]))
            elif (jetzt - datetime.fromisoformat(z["ende_seit"])).total_seconds() \
                    >= self.regeln["kulanz_min"] * 60:
                ereignisse.append(("schluss", app["id"]))
        return ereignisse

    # ------------------------------------------------------------ Eltern
    def bonus(self, jetzt, minuten):
        z = self._tag(jetzt)
        if minuten not in (15, 30):
            raise ValueError("Bonus gibt es als 15 oder 30 Minuten.")
        z["bonus_min"] += minuten
        z["ende_seit"] = None
        z["gewarnt"] = []

    def bonus_frei(self, jetzt, minuten):
        """Bonus ohne feste Stufen (Lernbonus 3.1): zählt wie Eltern-Bonus, hebt das Zeitende auf."""
        z = self._tag(jetzt)
        z["bonus_min"] += int(minuten)
        z["ende_seit"] = None
        z["gewarnt"] = []

    def heute_ohne_limit(self, jetzt):
        z = self._tag(jetzt)
        z["ohne_limit"] = True
        z["ende_seit"] = None


def pruefe_regeln(regeln):
    """Wirft ValueError mit verständlichem Text (Eltern-Seite zeigt ihn am Feld)."""
    for art in ("schultag", "frei"):
        wert = regeln["budget_min"].get(art)
        if not isinstance(wert, int) or isinstance(wert, bool) or not 0 <= wert <= 24 * 60:
            raise ValueError("Spielzeit %s: 0 bis 1440 Minuten." % ("Schultag" if art == "schultag" else "freier Tag"))
    for art in ("schultag", "frei"):
        wert = (regeln.get("gaming_min") or {}).get(art)
        if not isinstance(wert, int) or isinstance(wert, bool) or not 0 <= wert <= 24 * 60:
            raise ValueError("Gaming-Zeit %s: 0 bis 1440 Minuten." % ("Schultag" if art == "schultag" else "freier Tag"))
    if regeln.get("bundesland") not in ("", "BW", "BY", "BE", "BB", "HB", "HH", "HE", "MV", "NI", "NW", "RP", "SL", "SN",
                                        "ST", "SH", "TH"):
        raise ValueError("Unbekanntes Bundesland.")
    if not isinstance(regeln.get("ferien_auto"), bool) or not isinstance(regeln.get("ferien_feiertage"), bool):
        raise ValueError("Ferien automatisch / Feiertage: ja oder nein.")
    namen = set()
    if not isinstance(regeln["sperrzeiten"], list) or len(regeln["sperrzeiten"]) > 12:
        raise ValueError("Höchstens 12 Sperrzeiten.")
    for nr, s in enumerate(regeln["sperrzeiten"], 1):
        if not isinstance(s, dict) or set(s) - SPERR_FELDER:
            raise ValueError("Sperrzeit %d: unbekannte Felder." % nr)
        name = str(s.get("name", "")).strip()
        if not name or len(name) > 30:
            raise ValueError("Sperrzeit %d: Name fehlt (höchstens 30 Zeichen)." % nr)
        if name in namen:
            raise ValueError("Sperrzeit „%s“ gibt es zweimal." % name)
        namen.add(name)
        for feld in ("von", "bis"):
            try:
                datetime.strptime(str(s.get(feld, "")), "%H:%M")
            except ValueError:
                raise ValueError("Sperrzeit „%s“: Uhrzeit %s fehlt." % (name, feld)) from None
        if s["von"] == s["bis"]:
            raise ValueError("Sperrzeit „%s“: Beginn und Ende sind gleich." % name)
        if not s.get("tage") or not all(isinstance(t, int) and 0 <= t <= 6 for t in s["tage"]):
            raise ValueError("Sperrzeit „%s“: mindestens ein Wochentag." % name)
        for feld in ("ferien_frei", "nacht"):
            if not isinstance(s.get(feld, False), bool):
                raise ValueError("Sperrzeit „%s“: %s muss ja/nein sein." % (name, feld))
    for von, bis in regeln["ferien"]:
        datetime.strptime(von, "%Y-%m-%d")
        datetime.strptime(bis, "%Y-%m-%d")
        if bis < von:
            raise ValueError("Ferien %s bis %s: Ende liegt vor dem Beginn." % (von, bis))
    if not all(isinstance(m, int) and 0 < m <= 60 for m in regeln["warnungen_min"]):
        raise ValueError("Warnungen: Minuten von 1 bis 60.")
    if not isinstance(regeln["kulanz_min"], int) or not 0 <= regeln["kulanz_min"] <= 15:
        raise ValueError("Kulanz: 0 bis 15 Minuten.")
