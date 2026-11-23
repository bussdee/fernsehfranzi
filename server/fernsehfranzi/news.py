"""FernsehFranzi - Kinder-News: nur RSS-Adressen, die die Eltern selbst eintragen.

Ab Werk steht keine Adresse drin, also gibt es keine Kachel (Grundsatz 6). Gezeigt werden Überschrift, ein kurzer Text und
das Datum - als reiner Text, ohne Links, Bilder oder fremdes HTML.
"""
import logging
import re
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html import unescape

log = logging.getLogger("fernsehfranzi.news")

MAX_FEEDS = 10
MAX_LAENGE = 500
CACHE_S = 60 * 60
MAX_BYTES = 2 * 1024 * 1024
JE_QUELLE = 15


def _gueltig(url):
    if not isinstance(url, str) or not url.strip() or len(url) > MAX_LAENGE:
        return False
    teile = urllib.parse.urlsplit(url.strip())
    return teile.scheme in ("http", "https") and bool(teile.hostname) and not re.search(r"\s", url.strip())


def einstellungen(roh):
    """Ältere Stände (feste Quellen-Liste) werden still verworfen: dann ist einfach keine Adresse eingetragen."""
    roh = roh or {}
    feeds = roh.get("feeds") if isinstance(roh.get("feeds"), list) else []
    aus = []
    for f in feeds:
        if _gueltig(f) and f.strip() not in aus:
            aus.append(f.strip())
    return {"feeds": aus[:MAX_FEEDS]}


def pruefe(roh):
    if not isinstance(roh, dict) or set(roh) - {"feeds"} or not isinstance(roh.get("feeds", []), list):
        raise ValueError("Kinder-News: bitte nur eine Liste von RSS-Adressen.")
    feeds = roh.get("feeds", [])
    if len(feeds) > MAX_FEEDS:
        raise ValueError(f"Kinder-News: höchstens {MAX_FEEDS} RSS-Adressen.")
    falsch = [f for f in feeds if not _gueltig(f)]
    if falsch:
        raise ValueError(f"Kinder-News: keine gültige Adresse (http:// oder https://): {str(falsch[0])[:80]}")
    return einstellungen(roh)


def _name(url):
    return urllib.parse.urlsplit(url).hostname.removeprefix("www.")


def _text(wert, n):
    wert = unescape(re.sub(r"<[^>]{0,500}>", " ", unescape(str(wert or ""))))
    wert = re.sub(r"\s+", " ", wert).strip()
    return wert[:n] + ("…" if len(wert) > n else "")


def lies_feed(roh, quelle):
    """RSS 2.0 -> [{titel, text, datum, quelle}] (höchstens JE_QUELLE). Der Name kommt aus dem Kanal-Titel des Feeds."""
    wurzel = ET.fromstring(roh)
    kanal = _text(wurzel.findtext("channel/title"), 60)
    if kanal:
        quelle = dict(quelle, name=kanal)
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
        return bool(self.einstellungen()["feeds"])

    def _netz(self, url):
        anfrage = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FernsehFranzi)"})
        with urllib.request.urlopen(anfrage, timeout=15) as antwort:
            return antwort.read(MAX_BYTES)

    def _quelle(self, url):
        with self._lock:
            treffer = self._cache.get(url)
        if treffer and time.time() - treffer[0] < CACHE_S:
            return treffer[1]
        try:
            eintraege = lies_feed(self._holer(url), {"name": _name(url)})
        except (OSError, ValueError, ET.ParseError) as fehler:
            log.warning("Kinder-News %s: %s", _name(url), fehler)
            return treffer[1] if treffer else None
        with self._lock:
            self._cache[url] = (time.time(), eintraege)
        return eintraege

    def liste(self):
        feeds = self.einstellungen()["feeds"]
        if not feeds:
            raise ValueError("Kinder-News sind ausgeschaltet.")
        eintraege, quellen, fehlen = [], [], []
        for url in feeds:
            e = self._quelle(url)
            if e is None:
                fehlen.append(_name(url))
            else:
                eintraege.extend(e)
                quellen.append(e[0]["quelle"] if e else _name(url))
        eintraege.sort(key=lambda e: -e["zeit"])
        return {"eintraege": eintraege[:40], "quellen": quellen, "fehlen": fehlen}

    def fuer_eltern(self):
        return self.einstellungen()
