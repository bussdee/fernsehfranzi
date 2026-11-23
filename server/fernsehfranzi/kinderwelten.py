"""FernsehFranzi 5.0 - Kinderwelten (Familienfabrik) als eigene Seite am Fernseher.

Quelle ist die öffentliche Schnittstelle des Portals (dieselbe, aus der die Kinderwelten-App liest), ohne Anmeldung
und nur lesend: Geschichten und frei lesbare Bücher kapitelweise zum Selberlesen, Kinder-News der Familienfabrik,
Spiele für draußen und das Rätsel des Tages. Texte kommen als HTML; der Server macht daraus schlichte Absätze
(Überschrift, Absatz, Aufzählung), die Startseite setzt nur Text - kein fremdes HTML auf dem Fernseher.
Bilder holt der Server (nur von familienfabrik.at/bilder/) und reicht sie durch.
"""
import json
import logging
import re
import threading
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

log = logging.getLogger("fernsehfranzi.kinderwelten")

BASIS = "https://familienfabrik.at/api"
BILD_PRAEFIX = "https://familienfabrik.at/bilder/"
ADRESSE = re.compile(r"[a-z0-9][a-z0-9-]{0,159}\Z")
CACHE_S = 30 * 60
MAX_BYTES = 2 * 1024 * 1024
VORGABE = {"aktiv": False, "geschichten": True, "buecher": True, "news": True, "draussen": True, "raetsel": True}
FELDER = set(VORGABE)
TEILE = ("geschichten", "buecher", "news", "draussen", "raetsel")


def einstellungen(roh):
    return dict(VORGABE, **{k: v for k, v in (roh or {}).items() if k in FELDER})


def pruefe(roh):
    if not isinstance(roh, dict) or set(roh) - FELDER or not all(isinstance(v, bool) for v in roh.values()):
        raise ValueError("Kinderwelten: nur Schalter (ja/nein) für aktiv, " + ", ".join(TEILE) + ".")
    return einstellungen(roh)


class _Bloecke(HTMLParser):
    """HTML -> [{"art": "h"|"p"|"li"|"zitat", "text": ...}]; alles andere (Links, Bilder, Skripte) fällt weg."""
    ARTEN = {"h1": "h", "h2": "h", "h3": "h", "h4": "h", "p": "p", "li": "li", "blockquote": "zitat", "div": "p"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.bloecke, self.art, self.puffer, self.still = [], "p", [], 0

    def _fertig(self):
        text = re.sub(r"\s+", " ", "".join(self.puffer)).strip()
        if text:
            self.bloecke.append({"art": self.art, "text": text[:4000]})
        self.puffer = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "iframe", "noscript"):
            self.still += 1
        elif tag in self.ARTEN:
            self._fertig()
            self.art = self.ARTEN[tag]
        elif tag == "br":
            self.puffer.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "iframe", "noscript"):
            self.still = max(0, self.still - 1)
        elif tag in self.ARTEN:
            self._fertig()
            self.art = "p"

    def handle_data(self, data):
        if not self.still:
            self.puffer.append(data)


def bloecke(html):
    p = _Bloecke()
    p.feed(str(html or ""))
    p.close()
    p._fertig()
    return p.bloecke[:400]


def bild(roh):
    """Bild-Adresse über den eigenen Server (nur Bilder der Familienfabrik)."""
    url = (roh or {}).get("url") if isinstance(roh, dict) else None
    if not isinstance(url, str) or not url.startswith(BILD_PRAEFIX) or ".." in url:
        return None
    return "/api/kinderwelten/bild?u=" + urllib.parse.quote(url[len(BILD_PRAEFIX):], safe="")


def bild_adresse(teil):
    teil = str(teil or "")
    if not re.fullmatch(r"[0-9]{4}/[0-9]{2}/[a-zA-Z0-9_-]{1,80}\.(webp|jpg|jpeg|png)", teil):
        raise ValueError("Unbekanntes Bild.")
    return BILD_PRAEFIX + teil


def _t(wert, n=200):
    return re.sub(r"\s+", " ", str(wert or "")).strip()[:n]


class Kinderwelten:
    def __init__(self, hub, holer=None):
        self.hub = hub
        self._cache, self._lock = {}, threading.Lock()
        self._holer = holer or self._netz

    def einstellungen(self):
        return einstellungen(self.hub.einstellungen.get("kinderwelten"))

    def _netz(self, weg):
        anfrage = urllib.request.Request(BASIS + weg, headers={"User-Agent": "FernsehFranzi", "Accept": "application/json"})
        with urllib.request.urlopen(anfrage, timeout=15) as antwort:
            return json.loads(antwort.read(MAX_BYTES).decode("utf-8"))

    def _hole(self, weg):
        with self._lock:
            treffer = self._cache.get(weg)
        if treffer and time.time() - treffer[0] < CACHE_S:
            return treffer[1]
        try:
            daten = self._holer(weg)
        except (OSError, ValueError) as fehler:
            log.warning("Kinderwelten %s: %s", weg, fehler)
            if treffer:                       # lieber alt als gar nicht
                return treffer[1]
            raise ValueError("Die Kinderwelten sind gerade nicht erreichbar.") from None
        with self._lock:
            self._cache[weg] = (time.time(), daten)
            if len(self._cache) > 200:
                for alt in sorted(self._cache, key=lambda k: self._cache[k][0])[:50]:
                    del self._cache[alt]
        return daten

    def _pflicht(self, teil):
        e = self.einstellungen()
        if not e["aktiv"] or not e.get(teil, True):
            raise ValueError("Das haben Mama oder Papa ausgeschaltet.")

    # ------------------------------------------------------------ Übersicht
    def uebersicht(self):
        e = self.einstellungen()
        if not e["aktiv"]:
            return {"aktiv": False}
        return {"aktiv": True, "teile": [t for t in TEILE if e[t]]}

    def geschichten(self):
        self._pflicht("geschichten")
        d = self._hole("/geschichten?kinder=1&anzahl=100")
        return [{"adresse": g["adresse"], "titel": _t(g.get("titel"), 120), "reihe": _t(g.get("reihe"), 80),
                 "lesezeit": g.get("lesezeit") if isinstance(g.get("lesezeit"), int) else None,
                 "anriss": _t(g.get("anriss"), 300), "bild": bild(g.get("bild"))}
                for g in (d.get("eintraege") or []) if isinstance(g, dict) and ADRESSE.match(str(g.get("adresse", "")))]

    def geschichte(self, adresse):
        self._pflicht("geschichten")
        if not ADRESSE.match(str(adresse or "")):
            raise ValueError("Unbekannte Geschichte.")
        g = self._hole("/geschichte/" + adresse)
        return {"titel": _t(g.get("titel"), 160), "reihe": _t(g.get("reihe"), 80), "bild": bild(g.get("bild")),
                "bloecke": bloecke(g.get("text"))}

    def buecher(self):
        self._pflicht("buecher")
        d = self._hole("/buecher")
        aus = []
        for r in d.get("reihen") or []:
            for b in r.get("baende") or [] if isinstance(r, dict) else []:
                if isinstance(b, dict) and b.get("lesen_frei") and ADRESSE.match(str(b.get("adresse", ""))):
                    aus.append({"adresse": b["adresse"], "titel": _t(b.get("titel"), 120), "reihe": _t(b.get("reihe"), 80),
                                "band": b.get("band") if isinstance(b.get("band"), int) else None, "bild": bild(b.get("cover"))})
        return aus

    def kapitel(self, adresse, nummer):
        self._pflicht("buecher")
        if not ADRESSE.match(str(adresse or "")) or not isinstance(nummer, int) or not 1 <= nummer <= 200:
            raise ValueError("Unbekanntes Kapitel.")
        k = self._hole("/kapitel/%s/%d" % (adresse, nummer))
        return {"buch": _t(k.get("buch"), 120), "titel": _t(k.get("titel"), 160),
                "nummer": k.get("nummer") if isinstance(k.get("nummer"), int) else nummer,
                "von": k.get("von") if isinstance(k.get("von"), int) else None, "bloecke": bloecke(k.get("text"))}

    def _beitraege(self, weg):
        d = self._hole(weg)
        return [{"adresse": n["adresse"], "titel": _t(n.get("titel"), 160), "anriss": _t(n.get("anriss"), 300),
                 "datum": _t(n.get("datum_lang"), 40), "bild": bild(n.get("bild"))}
                for n in (d.get("eintraege") or []) if isinstance(n, dict) and ADRESSE.match(str(n.get("adresse", "")))]

    def news(self):
        self._pflicht("news")
        return self._beitraege("/neuigkeiten?kinder=1&ohne=klassische-kinderspiele&anzahl=20")

    def draussen(self):
        self._pflicht("draussen")
        return self._beitraege("/neuigkeiten?kinder=1&kategorie=klassische-kinderspiele&anzahl=50")

    def beitrag(self, adresse):
        e = self.einstellungen()
        if not e["aktiv"] or not (e["news"] or e["draussen"]):
            raise ValueError("Das haben Mama oder Papa ausgeschaltet.")
        if not ADRESSE.match(str(adresse or "")):
            raise ValueError("Unbekannter Beitrag.")
        b = self._hole("/beitrag/" + adresse)
        return {"titel": _t(b.get("titel"), 160), "datum": _t(b.get("datum_lang"), 40), "bild": bild(b.get("bild")),
                "bloecke": bloecke(b.get("text"))}

    def raetsel(self, tag):
        """Rätsel und Spruch des Tages - jeden Tag ein anderes (nach dem Datum gewählt)."""
        self._pflicht("raetsel")
        d = self._hole("/tagesinhalte")
        raetsel = [r for r in d.get("raetsel") or [] if isinstance(r, dict) and r.get("frage")]
        sprueche = [s for s in d.get("sprueche") or [] if isinstance(s, str)]
        nr = tag.toordinal()
        r = raetsel[nr % len(raetsel)] if raetsel else None
        return {"spruch": _t(sprueche[nr % len(sprueche)], 160) if sprueche else "",
                "raetsel": {"frage": _t(r.get("frage"), 300),
                            "antwort": _t((r.get("antworten") or [""])[0], 60).capitalize(),
                            "tipp": _t(r.get("tipp"), 20)} if r else None}
