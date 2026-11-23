"""FernsehFranzi 5.0 - Kinder-News: nur Quellen, die die Eltern einzeln freigeschaltet haben.

Die Liste der Quellen steht fest im Code (keine freien Adressen). Ab Werk ist jede Quelle aus (Grundsatz 6). Gezeigt
werden Überschrift, ein kurzer Text und das Datum - als reiner Text, ohne Links, Bilder oder fremdes HTML.
"""
import logging
import re
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html import unescape

log = logging.getLogger("fernsehfranzi.news")

QUELLEN = (
    {"id": "logo", "name": "logo! (ZDF)", "url": "https://www.zdf.de/rss/zdf/kinder/logo",
     "info": "Kindernachrichten von ZDF und KiKA, für 8 bis 12 Jahre."},
    {"id": "duda", "name": "Duda.news", "url": "https://www.duda.news/feed/",
     "info": "Kinderseite des Kölner Stadt-Anzeigers."},
    {"id": "kruschel", "name": "Kruschel", "url": "https://www.kruschel.de/rss",
     "info": "Kinderzeitung der VRM (Mainz), ab 7 Jahren."},
    {"id": "kleine", "name": "Kleine Kinderzeitung", "url": "https://kinderzeitung.kleinezeitung.at/feed/",
     "info": "Kinderzeitung der Kleinen Zeitung (Österreich)."},
)
IDS = tuple(q["id"] for q in QUELLEN)
CACHE_S = 60 * 60
MAX_BYTES = 2 * 1024 * 1024
JE_QUELLE = 15


def einstellungen(roh):
    roh = roh or {}
    quellen = roh.get("quellen") if isinstance(roh.get("quellen"), dict) else {}
    return {"quellen": {i: bool(quellen.get(i, False)) for i in IDS}}


def pruefe(roh):
    if not isinstance(roh, dict) or set(roh) - {"quellen"} or not isinstance(roh.get("quellen", {}), dict) \
            or set(roh.get("quellen", {})) - set(IDS) or not all(isinstance(v, bool) for v in roh.get("quellen", {}).values()):
        raise ValueError("Kinder-News: nur die bekannten Quellen, je an oder aus.")
    return einstellungen(roh)


def _text(wert, n):
    wert = unescape(re.sub(r"<[^>]{0,500}>", " ", unescape(str(wert or ""))))
    wert = re.sub(r"\s+", " ", wert).strip()
    return wert[:n] + ("…" if len(wert) > n else "")


def lies_feed(roh, quelle):
    """RSS 2.0 -> [{titel, text, datum, quelle}] (höchstens JE_QUELLE)."""
    wurzel = ET.fromstring(roh)
    aus = []
    for item in wurzel.iter("item"):
        titel = _text(item.findtext("title"), 160)
        if not titel:
            continue
        datum = None
        try:
            datum = parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError, IndexError):
            datum = None
        aus.append({"titel": titel, "text": _text(item.findtext("description"), 360),
                    "datum": datum.strftime("%d.%m.") if datum else "", "zeit": datum.timestamp() if datum else 0,
                    "quelle": quelle["name"]})
        if len(aus) >= JE_QUELLE:
            break
    return aus


class News:
    def __init__(self, hub, holer=None):
        self.hub = hub
        self._cache, self._lock = {}, threading.Lock()
        self._holer = holer or self._netz

    def einstellungen(self):
        return einstellungen(self.hub.einstellungen.get("news"))

    def aktiv(self):
        return any(self.einstellungen()["quellen"].values())

    def _netz(self, url):
        anfrage = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FernsehFranzi)"})
        with urllib.request.urlopen(anfrage, timeout=15) as antwort:
            return antwort.read(MAX_BYTES)

    def _quelle(self, q):
        with self._lock:
            treffer = self._cache.get(q["id"])
        if treffer and time.time() - treffer[0] < CACHE_S:
            return treffer[1]
        try:
            eintraege = lies_feed(self._holer(q["url"]), q)
        except (OSError, ValueError, ET.ParseError) as fehler:
            log.warning("Kinder-News %s: %s", q["id"], fehler)
            return treffer[1] if treffer else None
        with self._lock:
            self._cache[q["id"]] = (time.time(), eintraege)
        return eintraege

    def liste(self):
        an = self.einstellungen()["quellen"]
        quellen = [q for q in QUELLEN if an[q["id"]]]
        if not quellen:
            raise ValueError("Kinder-News sind ausgeschaltet.")
        eintraege, fehlen = [], []
        for q in quellen:
            e = self._quelle(q)
            if e is None:
                fehlen.append(q["name"])
            else:
                eintraege.extend(e)
        eintraege.sort(key=lambda e: -e["zeit"])
        return {"eintraege": eintraege[:40], "quellen": [q["name"] for q in quellen],
                "fehlen": fehlen}

    def fuer_eltern(self):
        an = self.einstellungen()["quellen"]
        return [dict(q, an=an[q["id"]]) for q in QUELLEN]
