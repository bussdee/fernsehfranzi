"""FernsehFranzi 5.0 - Wetter und Regenzeiten (Open-Meteo, ohne Schlüssel und ohne Konto).

Die Regeln sind dieselben wie im Familien Dashboard:
- Eine Viertelstunde (wo es sie gibt) oder Stunde gilt ab 0,1 mm als nass. Der Satz oben sagt, ob es gerade regnet und
  wann es aufhört oder wann es anfängt („Regen ab 15:15“, „Trocken bis 18:00“), gerechnet für die nächsten 24 Stunden.
- Ein Trockenfenster ist eine Strecke trockener Stunden (unter 0,1 mm und unter 55 % Regenwahrscheinlichkeit) zwischen
  Sonnenauf- und -untergang, die mindestens 1,5 Stunden dauert. Am heutigen Tag zählt nur, was noch kommt.

Der Fernseher fragt höchstens alle 30 Minuten nach, im Hintergrund. Ohne Netz bleibt die letzte Antwort stehen,
mit dem Hinweis, wie alt sie ist.
"""
import json
import logging
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

log = logging.getLogger("fernsehfranzi.wetter")

NASS_MM = 0.1
NASS_PROZENT = 55
MINDEST_STUNDEN = 1.5
SONNIG_BIS_WOLKEN = 40
ABFRAGE_S = 30 * 60
VERALTET_S = 3 * 3600
VORGABE = {"aktiv": False, "ort": None, "kopf": True, "draussen": True}
FELDER = set(VORGABE)
ENDPUNKT = "https://api.open-meteo.com/v1/forecast"
ORTSSUCHE = "https://geocoding-api.open-meteo.com/v1/search"

# WMO-Wettercodes -> (Symbol am Tag, Symbol nachts, kindgerechter Text)
CODES = {
    0: ("☀️", "🌙", "Sonnig"), 1: ("🌤️", "🌙", "Fast nur Sonne"), 2: ("⛅", "☁️", "Ein paar Wolken"),
    3: ("☁️", "☁️", "Bewölkt"), 45: ("🌫️", "🌫️", "Nebel"), 48: ("🌫️", "🌫️", "Nebel mit Raureif"),
    51: ("🌦️", "🌧️", "Nieselregen"), 53: ("🌦️", "🌧️", "Nieselregen"), 55: ("🌧️", "🌧️", "Starker Niesel"),
    56: ("🌧️", "🌧️", "Glatter Niesel"), 57: ("🌧️", "🌧️", "Glatter Niesel"),
    61: ("🌦️", "🌧️", "Leichter Regen"), 63: ("🌧️", "🌧️", "Regen"), 65: ("🌧️", "🌧️", "Starker Regen"),
    66: ("🌧️", "🌧️", "Eisregen"), 67: ("🌧️", "🌧️", "Eisregen"),
    71: ("🌨️", "🌨️", "Leichter Schnee"), 73: ("🌨️", "🌨️", "Schnee"), 75: ("❄️", "❄️", "Viel Schnee"),
    77: ("🌨️", "🌨️", "Schneegriesel"), 80: ("🌦️", "🌧️", "Regenschauer"), 81: ("🌧️", "🌧️", "Regenschauer"),
    82: ("⛈️", "⛈️", "Heftige Schauer"), 85: ("🌨️", "🌨️", "Schneeschauer"), 86: ("❄️", "❄️", "Schneeschauer"),
    95: ("⛈️", "⛈️", "Gewitter"), 96: ("⛈️", "⛈️", "Gewitter mit Hagel"), 99: ("⛈️", "⛈️", "Gewitter mit Hagel"),
}
TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def einstellungen(roh):
    return dict(VORGABE, **{k: v for k, v in (roh or {}).items() if k in FELDER})


def pruefe(roh):
    if not isinstance(roh, dict) or set(roh) - FELDER:
        raise ValueError("Wetter: unbekannte Felder.")
    w = einstellungen(roh)
    for feld in ("aktiv", "kopf", "draussen"):
        if not isinstance(w[feld], bool):
            raise ValueError("Wetter: %s ja oder nein." % feld)
    ort = w["ort"]
    if ort is not None:
        if not isinstance(ort, dict) or set(ort) - {"name", "lat", "lon"} or not isinstance(ort.get("name"), str) \
                or not 0 < len(ort["name"]) <= 80 or not all(isinstance(ort.get(k), (int, float)) for k in ("lat", "lon")) \
                or not (-90 <= ort["lat"] <= 90 and -180 <= ort["lon"] <= 180):
            raise ValueError("Wetter: Ort mit Name, Breite und Länge.")
    if w["aktiv"] and not ort:
        raise ValueError("Wetter: bitte zuerst einen Ort suchen und antippen.")
    return w


def symbol(code, tag=True):
    s = CODES.get(int(code) if isinstance(code, (int, float)) else -1, ("🌡️", "🌡️", "Wetter"))
    return s[0] if tag else s[1]


def beschreibung(code):
    return CODES.get(int(code) if isinstance(code, (int, float)) else -1, ("", "", "Wetter"))[2]


def _zeit(text):
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M")
    except (TypeError, ValueError):
        return None


def _wert(liste, i, vorgabe=0):
    try:
        w = liste[i]
    except (IndexError, TypeError):
        return vorgabe
    return vorgabe if w is None else w


def uhr(t):
    return t.strftime("%H:%M")


def wann(t, jetzt):
    """„15:15“ heute, „morgen 07:00“, sonst „Donnerstag 09:00“."""
    if t.date() == jetzt.date():
        return uhr(t)
    if t.date() == jetzt.date() + timedelta(days=1):
        return "morgen " + uhr(t)
    return "%s %s" % (TAGE[t.weekday()], uhr(t))


def regen_satz(api, jetzt):
    """Satz über die nächsten 24 Stunden - Viertelstunden, wo vorhanden (DWD-Modell), sonst Stunden."""
    m15 = api.get("minutely_15") or {}
    zeiten, werte = m15.get("time") or [], m15.get("precipitation") or []
    if not zeiten or not werte:
        h = api.get("hourly") or {}
        zeiten, werte = h.get("time") or [], h.get("precipitation") or []
    reihe = []
    for i, t in enumerate(zeiten):
        z = _zeit(t)
        if z is None or z < jetzt - timedelta(hours=1):
            continue
        reihe.append((z, _wert(werte, i) >= NASS_MM))
        if z > jetzt + timedelta(hours=24):
            break
    # der Eintrag, in dem „jetzt“ liegt, ist der letzte, der nicht nach jetzt beginnt
    jetzt_i = max([i for i, (z, _) in enumerate(reihe) if z <= jetzt] or [0])
    reihe = reihe[jetzt_i:]
    if not reihe:
        return {"nass": None, "text": ""}
    if reihe[0][1]:
        ende = next((z for z, nass in reihe if not nass), None)
        return {"nass": True, "bis": ende.isoformat() if ende else None,
                "text": "Es regnet – trocken ab %s" % wann(ende, jetzt) if ende else "Es regnet noch lange"}
    anfang = next((z for z, nass in reihe if nass), None)
    if anfang:
        return {"nass": False, "ab": anfang.isoformat(), "text": "Regen ab %s" % wann(anfang, jetzt)}
    return {"nass": False, "text": "Kein Regen in Sicht"}


def _stunden(api):
    h = api.get("hourly") or {}
    aus = []
    for i, t in enumerate(h.get("time") or []):
        z = _zeit(t)
        if z is None:
            continue
        aus.append({"zeit": z, "temp": _wert(h.get("temperature_2m"), i), "gefuehlt": _wert(h.get("apparent_temperature"), i),
                    "mm": _wert(h.get("precipitation"), i), "prozent": _wert(h.get("precipitation_probability"), i),
                    "wolken": _wert(h.get("cloud_cover"), i), "code": _wert(h.get("weather_code"), i),
                    "wind": _wert(h.get("wind_speed_10m"), i)})
    return aus


def _nass(st):
    return st["mm"] >= NASS_MM or st["prozent"] >= NASS_PROZENT


def trockenfenster(auf, unter, stunden, jetzt):
    """Trockene Strecken zwischen Sonnenauf- und -untergang, ab 1,5 Stunden, am heutigen Tag nur ab jetzt."""
    if not auf or not unter or unter <= auf:
        return []
    tags = [st for st in stunden if st["zeit"] < unter and st["zeit"] + timedelta(hours=1) >= auf]
    fenster, lauf = [], []

    def abschliessen():
        if not lauf:
            return
        von, bis = max(lauf[0]["zeit"], auf), min(lauf[-1]["zeit"] + timedelta(hours=1), unter)
        laeuft = von <= jetzt < bis
        if laeuft:
            von = jetzt
        elif bis < jetzt:
            return
        dauer = (bis - von).total_seconds() / 3600
        if dauer >= MINDEST_STUNDEN:
            wolken = sum(s["wolken"] for s in lauf) / len(lauf)
            fenster.append({"von": von.isoformat(timespec="minutes"), "bis": bis.isoformat(timespec="minutes"),
                            "von_text": uhr(von), "bis_text": uhr(bis), "stunden": round(dauer * 2) / 2,
                            "sonnig": wolken < SONNIG_BIS_WOLKEN, "jetzt": laeuft,
                            "gefuehlt": round(min(s["gefuehlt"] for s in lauf))})

    for st in tags:
        if _nass(st):
            abschliessen()
            lauf = []
            continue
        if lauf and st["zeit"] != lauf[-1]["zeit"] + timedelta(hours=1):
            abschliessen()
            lauf = []
        lauf.append(st)
    abschliessen()
    return fenster


def anzieh_tipp(gefuehlt, nass, code):
    if isinstance(code, (int, float)) and int(code) in (71, 73, 75, 77, 85, 86):
        teile = ["Schneeanzug oder Winterjacke", "Mütze und Handschuhe"]
    elif gefuehlt < 0:
        teile = ["Winterjacke", "Mütze, Schal und Handschuhe"]
    elif gefuehlt < 8:
        teile = ["Warme Jacke", "Mütze"]
    elif gefuehlt < 15:
        teile = ["Jacke"]
    elif gefuehlt < 21:
        teile = ["Pulli oder dünne Jacke"]
    else:
        teile = ["T-Shirt", "Trinkflasche"]
    if nass:
        teile.append("Regenjacke und Gummistiefel")
    return " · ".join(teile)


def auswerten(api, jetzt):
    """Antwort von Open-Meteo -> Daten für Kopfzeile und Wetter-Seite."""
    c = api.get("current") or {}
    d = api.get("daily") or {}
    stunden = _stunden(api)
    tage = []
    for i, t in enumerate(d.get("time") or []):
        try:
            datum = datetime.strptime(t, "%Y-%m-%d")
        except (TypeError, ValueError):
            continue
        auf, unter = _zeit(_wert(d.get("sunrise"), i, "")), _zeit(_wert(d.get("sunset"), i, ""))
        tage.append({"datum": t, "name": "Heute" if datum.date() == jetzt.date() else
                     "Morgen" if datum.date() == jetzt.date() + timedelta(days=1) else TAGE[datum.weekday()],
                     "code": _wert(d.get("weather_code"), i), "symbol": symbol(_wert(d.get("weather_code"), i)),
                     "text": beschreibung(_wert(d.get("weather_code"), i)),
                     "max": round(_wert(d.get("temperature_2m_max"), i)), "min": round(_wert(d.get("temperature_2m_min"), i)),
                     "regen": _wert(d.get("precipitation_probability_max"), i),
                     "auf": uhr(auf) if auf else None, "unter": uhr(unter) if unter else None,
                     "fenster": trockenfenster(auf, unter, stunden, jetzt)})
    tag = bool(c.get("is_day", 1))
    regen = regen_satz(api, jetzt)
    naechste = [{"uhr": uhr(s["zeit"]), "temp": round(s["temp"]), "prozent": s["prozent"], "mm": s["mm"],
                 "symbol": symbol(s["code"], 6 <= s["zeit"].hour < 20), "nass": _nass(s)}
                for s in stunden if jetzt - timedelta(minutes=59) <= s["zeit"] <= jetzt + timedelta(hours=12)][:12]
    gefuehlt = c.get("apparent_temperature", c.get("temperature_2m", 10))
    regen_bald = bool(regen.get("nass")) or any(s["nass"] for s in naechste[:6])
    fenster = [dict(f, tag=t["name"]) for t in tage[:2] for f in t["fenster"]]
    return {"temp": round(c.get("temperature_2m", 0)), "gefuehlt": round(gefuehlt), "code": c.get("weather_code"),
            "symbol": symbol(c.get("weather_code"), tag), "text": beschreibung(c.get("weather_code")),
            "wind": round(c.get("wind_speed_10m", 0)), "regen": regen, "stunden": naechste, "tage": tage[:5],
            "fenster": fenster[:4], "naechstes_fenster": fenster[0] if fenster else None,
            "anziehen": anzieh_tipp(gefuehlt, regen_bald, c.get("weather_code")),
            "draussen_gut": bool(fenster and fenster[0]["jetzt"] and gefuehlt >= 0)}


class Wetter:
    """Holt das Wetter im Hintergrund und hält die letzte Antwort."""

    def __init__(self, hub):
        self.hub = hub
        self.roh, self.geholt, self.fehler, self._ort = None, 0.0, "", None
        self._laeuft = False
        self._lock = threading.Lock()

    def einstellungen(self):
        return einstellungen(self.hub.einstellungen.get("wetter"))

    def adresse(self, ort):
        q = {"latitude": "%.4f" % ort["lat"], "longitude": "%.4f" % ort["lon"], "timezone": "auto", "forecast_days": 5,
             "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,is_day",
             "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
             "hourly": "temperature_2m,apparent_temperature,precipitation_probability,precipitation,weather_code,cloud_cover,wind_speed_10m",
             "minutely_15": "precipitation"}
        return ENDPUNKT + "?" + urllib.parse.urlencode(q)

    def holen(self):
        """Eine Abfrage (blockiert bis zu 15 s) - im Takt nur über tick() im Hintergrund."""
        w = self.einstellungen()
        if not w["aktiv"] or not w["ort"]:
            return
        try:
            anfrage = urllib.request.Request(self.adresse(w["ort"]), headers={"User-Agent": "FernsehFranzi"})
            with urllib.request.urlopen(anfrage, timeout=15) as antwort:
                daten = json.loads(antwort.read().decode("utf-8"))
            with self._lock:
                self.roh, self.geholt, self.fehler, self._ort = daten, time.time(), "", dict(w["ort"])
        except (OSError, ValueError) as fehler:
            with self._lock:
                self.fehler = "Das Wetter ist gerade nicht erreichbar."
            log.warning("Wetter: %s", fehler)

    def tick(self, sofort=False):
        w = self.einstellungen()
        if not w["aktiv"] or not w["ort"] or self._laeuft:
            return
        if not sofort and self._ort == w["ort"] and time.time() - self.geholt < ABFRAGE_S:
            return
        if not sofort and self.fehler and time.time() - self.geholt < 300 and self._ort == w["ort"]:
            return

        def lauf():
            try:
                self.holen()
            finally:
                self._laeuft = False
        self._laeuft = True
        if sofort == "gleich":       # Tests: ohne Thread
            lauf()
        else:
            threading.Thread(target=lauf, daemon=True, name="wetter").start()

    def fuer_tv(self):
        w = self.einstellungen()
        if not w["aktiv"] or not w["ort"]:
            return {"aktiv": False}
        with self._lock:
            roh, geholt, fehler, ort = self.roh, self.geholt, self.fehler, self._ort
        if not roh or ort != w["ort"]:
            return {"aktiv": True, "ort": w["ort"]["name"], "kopf": w["kopf"], "draussen": w["draussen"], "daten": None,
                    "fehler": fehler or "Das Wetter wird geholt …"}
        try:
            daten = auswerten(roh, self.hub.uhr())
        except (TypeError, ValueError, KeyError) as e:
            log.warning("Wetter auswerten: %s", e)
            return {"aktiv": True, "ort": w["ort"]["name"], "kopf": w["kopf"], "draussen": w["draussen"], "daten": None,
                    "fehler": "Das Wetter ist gerade nicht lesbar."}
        alt = time.time() - geholt
        return {"aktiv": True, "ort": w["ort"]["name"], "kopf": w["kopf"], "draussen": w["draussen"], "daten": daten,
                "stand": datetime.fromtimestamp(geholt).strftime("%H:%M"),
                "fehler": ("Stand %s – gerade keine neue Vorhersage." % datetime.fromtimestamp(geholt).strftime("%H:%M"))
                if alt > VERALTET_S else ""}


def orte_suchen(text):
    """Ortssuche für die Eltern-Seite (Open-Meteo Geocoding)."""
    text = str(text or "").strip()
    if not 2 <= len(text) <= 60:
        raise ValueError("Bitte mindestens zwei Buchstaben eingeben.")
    q = urllib.parse.urlencode({"name": text, "count": 8, "language": "de", "format": "json"})
    try:
        anfrage = urllib.request.Request(ORTSSUCHE + "?" + q, headers={"User-Agent": "FernsehFranzi"})
        with urllib.request.urlopen(anfrage, timeout=10) as antwort:
            daten = json.loads(antwort.read().decode("utf-8"))
    except (OSError, ValueError):
        raise ValueError("Die Ortssuche antwortet gerade nicht.") from None
    aus = []
    for r in daten.get("results") or []:
        if not isinstance(r.get("latitude"), (int, float)) or not isinstance(r.get("longitude"), (int, float)):
            continue
        teile = [r.get("name"), r.get("admin1"), r.get("country")]
        aus.append({"name": str(r.get("name") or "")[:80], "lat": round(r["latitude"], 4), "lon": round(r["longitude"], 4),
                    "zusatz": ", ".join(str(t) for t in teile[1:] if t)[:120]})
    return aus
