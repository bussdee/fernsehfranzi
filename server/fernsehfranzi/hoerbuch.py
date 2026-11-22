"""FernsehFranzi 3.3 - Hörbücher aus einem Ordner im Netzwerk (FileBrowser-Freigabelink).

Die Eltern geben im FileBrowser einen Ordner frei ("Teilen", unbefristet, ohne Passwort) und tragen den
Link als Adresse der Hörbuch-App ein, z. B. ``http://server:8080/share/AbCdEf12``. Der Fernseher liest
darüber nur: Ordnerliste und MP3-Dateien. Der Server reicht beides durch (Chromium spricht nur mit
127.0.0.1, die Whitelist bleibt unberührt, Spulen geht über Range-Anfragen).

FileBrowser 2.x, öffentliche Schnittstelle:
    GET <basis>/api/public/share/<hash>/<pfad>   -> JSON {"isDir": true, "items": [...]}
    GET <basis>/api/public/dl/<hash>/<pfad>?inline=true   -> Datei (mit Range)
"""
import json
import re
import urllib.request
from urllib.parse import quote, urlsplit

AUDIO = (".mp3", ".m4a", ".m4b", ".ogg", ".opus", ".aac", ".wav", ".flac")
BILD = (".jpg", ".jpeg", ".png", ".webp")
VIDEO = (".mp4", ".m4v", ".webm", ".mkv", ".mov")          # 4.0: Video-Player (am Pi 3 am besten H.264 in .mp4)
COVER_NAMEN = ("cover", "folder", "front", "album", "albumart")       # bevorzugt (ohne Endung)
FREIGABE = re.compile(r"^(?P<basis>.*?)/share/(?P<hash>[A-Za-z0-9_-]{4,64})(?P<unter>/.*)?$")
ZEITLIMIT_S = 15


class HoerbuchFehler(ValueError):
    pass


def pruefe_freigabe(url):
    """Fehlertext oder None - für die Katalogprüfung."""
    teile = urlsplit(url)
    if teile.scheme not in ("http", "https") or not teile.netloc:
        return "muss eine http(s)-Adresse sein (FileBrowser-Freigabelink)"
    if not FREIGABE.match(teile.path):
        return "muss ein FileBrowser-Freigabelink sein (…/share/…)"
    return None


def _zerlege(url):
    teile = urlsplit(url)
    treffer = FREIGABE.match(teile.path)
    if teile.scheme not in ("http", "https") or not teile.netloc or not treffer:
        raise HoerbuchFehler("Die Hörbuch-Adresse ist kein FileBrowser-Freigabelink.")
    wurzel = "%s://%s%s" % (teile.scheme, teile.netloc, treffer.group("basis"))
    unter = (treffer.group("unter") or "").strip("/")
    return wurzel, treffer.group("hash"), unter


def sauberer_pfad(pfad):
    """Relativer Pfad innerhalb der Freigabe: kein "..", keine führenden Schrägstriche."""
    teile = [t for t in str(pfad or "").replace("\\", "/").split("/") if t not in ("", ".")]
    if any(t == ".." for t in teile):
        raise HoerbuchFehler("Ungültiger Pfad.")
    return "/".join(teile)


def _voll(url, pfad):
    wurzel, kennung, unter = _zerlege(url)
    rel = "/".join(t for t in (unter, sauberer_pfad(pfad)) if t)
    return wurzel, kennung, quote(rel, safe="/")


def _natuerlich(name):
    """'Folge 2' vor 'Folge 10'."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def _eintraege(url, pfad, oeffne):
    wurzel, kennung, rel = _voll(url, pfad)
    adresse = "%s/api/public/share/%s/%s" % (wurzel, kennung, rel)
    try:
        with oeffne(urllib.request.Request(adresse, headers={"Accept": "application/json"}),
                    timeout=ZEITLIMIT_S) as antwort:
            return json.loads(antwort.read().decode("utf-8")).get("items") or []
    except (OSError, ValueError) as fehler:
        raise HoerbuchFehler("Der Hörbuch-Ordner ist gerade nicht erreichbar (%s)." % fehler) from None


def cover_in(url, pfad="", oeffne=urllib.request.urlopen):
    """4.0: Cover-Bild eines Ordners (cover.jpg, folder.jpg … oder das erste Bild) - Pfad oder None."""
    pfad = sauberer_pfad(pfad)
    bilder = sorted((str(e.get("name", "")) for e in _eintraege(url, pfad, oeffne)
                     if not e.get("isDir") and str(e.get("name", "")).lower().endswith(BILD)), key=_natuerlich)
    if not bilder:
        return None
    bevorzugt = [b for b in bilder if b.rsplit(".", 1)[0].lower() in COVER_NAMEN]
    return "/".join(t for t in (pfad, (bevorzugt or bilder)[0]) if t)


def bild_adresse(url, pfad):
    pfad = sauberer_pfad(pfad)
    if not pfad.lower().endswith(BILD):
        raise HoerbuchFehler("Nur Bilder.")
    wurzel, kennung, rel = _voll(url, pfad)
    return "%s/api/public/dl/%s/%s?inline=true" % (wurzel, kennung, rel)


def liste(url, pfad="", oeffne=urllib.request.urlopen, endungen=AUDIO):
    """Ordner und Audiodateien unter ``pfad`` (relativ zur Freigabe)."""
    pfad = sauberer_pfad(pfad)
    daten = {"items": _eintraege(url, pfad, oeffne)}
    ordner, titel = [], []
    for eintrag in daten.get("items") or []:
        name = str(eintrag.get("name", ""))
        if not name or name.startswith("."):
            continue
        weg = "/".join(t for t in (pfad, name) if t)
        if eintrag.get("isDir"):
            ordner.append({"name": name, "pfad": weg})
        elif name.lower().endswith(endungen):
            titel.append({"name": name, "pfad": weg, "groesse": int(eintrag.get("size") or 0)})
    ordner.sort(key=lambda e: _natuerlich(e["name"]))
    titel.sort(key=lambda e: _natuerlich(e["name"]))
    eltern = pfad.rsplit("/", 1)[0] if "/" in pfad else ("" if pfad else None)
    bilder = [str(e.get("name", "")) for e in daten["items"] if not e.get("isDir") and str(e.get("name", "")).lower().endswith(BILD)]
    bevorzugt = [b for b in bilder if b.rsplit(".", 1)[0].lower() in COVER_NAMEN]
    cover = "/".join(t for t in (pfad, (bevorzugt or sorted(bilder, key=_natuerlich) or [""])[0]) if t) if bilder else None
    return {"pfad": pfad, "eltern": eltern, "ordner": ordner, "titel": titel, "cover": cover}


def datei_adresse(url, pfad, endungen=AUDIO):
    pfad = sauberer_pfad(pfad)
    if not pfad.lower().endswith(endungen):
        raise HoerbuchFehler("Nur Audio- bzw. Videodateien.")
    wurzel, kennung, rel = _voll(url, pfad)
    return "%s/api/public/dl/%s/%s?inline=true" % (wurzel, kennung, rel)
