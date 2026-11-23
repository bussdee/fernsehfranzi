"""FernsehFranzi 3.5 - YouTube-Bereich.

Die Eltern legen Kategorien an und speichern darin Videos oder Playlists (Link einfügen). Der Fernseher spielt sie in
einem eigenen Player (youtube-nocookie-Einbettung, gesteuert über die IFrame-API) - nur das Video, ohne YouTube-Seite.

Einstellungen (einstellungen.json, Feld "youtube"):
    {"kategorien": [{"name": "Musik", "eintraege": [{"art": "video", "id": "dQw4w9WgXcQ", "titel": "…"},
                                                     {"art": "playlist", "id": "PL…", "titel": "…"}]}]}
"""
import json
import re
import urllib.request
from urllib.parse import parse_qs, quote, urlsplit

VIDEO = re.compile(r"[A-Za-z0-9_-]{11}\Z")
PLAYLIST = re.compile(r"[A-Za-z0-9_-]{10,64}\Z")
KATEGORIEN_MAX = 12
EINTRAEGE_MAX = 60
VIDEOS_MAX = 200


def link_lesen(link):
    """YouTube-Link -> ("video"|"playlist", id). Wirft ValueError mit verständlichem Text."""
    teile = urlsplit(str(link or "").strip())
    host = (teile.hostname or "").lower()
    if not host.endswith(("youtube.com", "youtu.be", "youtube-nocookie.com")):
        raise ValueError("Das ist kein YouTube-Link.")
    abfrage = parse_qs(teile.query)
    liste = (abfrage.get("list") or [""])[0]
    video = (abfrage.get("v") or [""])[0]
    pfad = [p for p in teile.path.split("/") if p]
    if host.endswith("youtu.be") and pfad:
        video = pfad[0]
    elif pfad and pfad[0] in ("shorts", "embed", "live") and len(pfad) > 1:
        video = pfad[1]
    if pfad and pfad[0] == "playlist" and PLAYLIST.match(liste):
        return "playlist", liste
    if VIDEO.match(video):
        return "video", video
    if PLAYLIST.match(liste):
        return "playlist", liste
    raise ValueError("In dem Link steckt kein Video und keine Playlist.")


def titel_holen(art, kennung, oeffne=urllib.request.urlopen):
    """Titel und Vorschaubild über YouTube-oEmbed (ohne Schlüssel). Bei Fehlern ein Ersatztitel."""
    seite = ("https://www.youtube.com/watch?v=%s" % kennung if art == "video"
             else "https://www.youtube.com/playlist?list=%s" % kennung)
    try:
        with oeffne("https://www.youtube.com/oembed?format=json&url=" + quote(seite, safe=""), timeout=10) as a:
            d = json.loads(a.read().decode("utf-8"))
        return str(d.get("title") or "")[:120], str(d.get("thumbnail_url") or "")[:300]
    except (OSError, ValueError):
        return ("Playlist " if art == "playlist" else "Video ") + kennung, ""


def playlist_videos(kennung, oeffne=urllib.request.urlopen):
    """4.0.1: Videos einer öffentlichen Playlist (ohne API-Schlüssel, aus der Playlist-Seite). Unser Player spielt sie dann
    selbst nacheinander ab - die YouTube-eigene Playlist-Einbettung lief nicht zuverlässig."""
    anfrage = urllib.request.Request("https://www.youtube.com/playlist?list=%s&hl=de" % quote(kennung, safe=""),
                                     headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "de"})
    try:
        with oeffne(anfrage, timeout=15) as a:
            seite = a.read(3_000_000).decode("utf-8", "replace")
    except OSError as fehler:
        raise ValueError("YouTube ist gerade nicht erreichbar (%s)." % fehler) from None
    gesehen, videos = set(), []
    for v in re.findall(r'"playlistVideoRenderer":\{"videoId":"([A-Za-z0-9_-]{11})"', seite) or \
            re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', seite):
        if v not in gesehen:
            gesehen.add(v)
            videos.append(v)
    return videos[:VIDEOS_MAX]


def pruefe(y):
    if not isinstance(y, dict) or set(y) - {"kategorien"}:
        raise ValueError("YouTube: unbekannte Felder.")
    kategorien = y.get("kategorien", [])
    if not isinstance(kategorien, list) or len(kategorien) > KATEGORIEN_MAX:
        raise ValueError("Höchstens %d Kategorien." % KATEGORIEN_MAX)
    namen = set()
    for k in kategorien:
        name = str((k or {}).get("name", "")).strip()
        if not name or len(name) > 30 or set(k) - {"name", "eintraege", "aktiv"}:
            raise ValueError("Kategorie: Name fehlt (höchstens 30 Zeichen).")
        if not isinstance(k.get("aktiv", True), bool):                 # 6.0: Kategorie vorübergehend aus
            raise ValueError("Kategorie „%s“: an oder aus." % name)
        if name in namen:
            raise ValueError("Kategorie „%s“ gibt es zweimal." % name)
        namen.add(name)
        eintraege = k.get("eintraege", [])
        if not isinstance(eintraege, list) or len(eintraege) > EINTRAEGE_MAX:
            raise ValueError("Kategorie „%s“: höchstens %d Einträge." % (name, EINTRAEGE_MAX))
        for e in eintraege:
            if not isinstance(e, dict) or set(e) - {"art", "id", "titel", "bild", "videos"}:
                raise ValueError("Kategorie „%s“: unbekannte Felder." % name)
            muster = VIDEO if e.get("art") == "video" else PLAYLIST if e.get("art") == "playlist" else None
            if muster is None or not muster.match(str(e.get("id", ""))):
                raise ValueError("Kategorie „%s“: ungültiger Eintrag." % name)
            videos = e.get("videos", [])
            if not isinstance(videos, list) or len(videos) > VIDEOS_MAX or not all(isinstance(v, str) and VIDEO.match(v) for v in videos):
                raise ValueError("Kategorie „%s“: ungültige Videoliste." % name)
            bild = str(e.get("bild", ""))
            if bild and not re.match(r"https://i\d?\.ytimg\.com/", bild):
                raise ValueError("Vorschaubild nur von ytimg.com.")
    return y
