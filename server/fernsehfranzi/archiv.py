"""FernsehFranzi 6.9.41 - Archiv-Ordner für Filme und Musik aus dem Heimnetz (FileBrowser-Freigaben).

Die Eltern tragen je einen Freigabelink für Filme und für Musik ein. Im Elternbereich erscheint der Inhalt der obersten
Ebene (Filme/Serien bzw. Alben/Lieder als Ordner oder Dateien); jeder Eintrag wird einzeln freigegeben. Am Fernseher
zeigen die Kacheln „Filme“ und „Musik“ nur die freigegebenen Einträge (Player: video.js bzw. hoerbuch.js).

Filme können eine **Belohnung** sein: ``frei`` = zählt nicht zum Zeitlimit, ``sperre`` = auch in Sperrzeiten erlaubt
(z. B. ein Film am Wochenende morgens). Alles ab Werk aus (CONTRACT 6): ohne Ordner und ohne Freigabe keine Kachel.

Einstellung (einstellungen["archiv"]): {"video": {"ordner": link, "freigaben": {pfad: {"frei": bool, "sperre": bool}}},
                                        "musik": {"ordner": link, "freigaben": {pfad: {}}}}
"""
from . import hoerbuch

ARTEN = {"video": {"app": "archiv-video", "name": "Filme", "endungen": hoerbuch.VIDEO, "typ": "video"},
         "musik": {"app": "archiv-musik", "name": "Musik", "endungen": hoerbuch.AUDIO, "typ": "hoerbuch"}}
APP_ART = {a["app"]: art for art, a in ARTEN.items()}
FREIGABEN_MAX = 500
FLAGGEN = ("frei", "sperre")


def einstellungen(e):
    e = e if isinstance(e, dict) else {}
    erg = {}
    for art in ARTEN:
        x = e.get(art) if isinstance(e.get(art), dict) else {}
        fr = x.get("freigaben") if isinstance(x.get("freigaben"), dict) else {}
        erg[art] = {"ordner": str(x.get("ordner") or ""),
                    "freigaben": {str(p): {f: bool((v or {}).get(f)) for f in FLAGGEN} if art == "video" else {}
                                  for p, v in fr.items()}}
    return erg


def pruefe(e, freigabe_fehler):
    """Eingabe der Eltern prüfen. freigabe_fehler(link) -> Fehlertext oder None."""
    if not isinstance(e, dict) or set(e) - set(ARTEN):
        raise ValueError("Archiv: ungültige Angaben.")
    for art, x in e.items():
        name = ARTEN[art]["name"]
        if not isinstance(x, dict) or set(x) - {"ordner", "freigaben"}:
            raise ValueError("Archiv %s: ungültige Angaben." % name)
        link = x.get("ordner", "")
        if not isinstance(link, str) or (link and freigabe_fehler(link)):
            raise ValueError("Archiv-Ordner %s %s" % (name, (freigabe_fehler(link) if isinstance(link, str) else None) or "ungültig."))
        fr = x.get("freigaben", {})
        if not isinstance(fr, dict) or len(fr) > FREIGABEN_MAX:
            raise ValueError("Archiv %s: zu viele oder ungültige Freigaben." % name)
        for pfad, v in fr.items():
            if hoerbuch.sauberer_pfad(pfad) != pfad or "/" in pfad or not pfad:
                raise ValueError("Archiv %s: ungültiger Eintrag „%s“." % (name, pfad))
            if not isinstance(v, dict) or set(v) - set(FLAGGEN) or any(not isinstance(b, bool) for b in v.values()):
                raise ValueError("Archiv %s: ungültige Angaben zu „%s“." % (name, pfad))
            if art == "musik" and any(v.values()):
                raise ValueError("Archiv Musik: Belohnungen gibt es nur bei Filmen.")
    return e


def oberster(pfad):
    """Oberster Eintrag eines Pfads ("Film A/CD1/x.mp4" -> "Film A")."""
    return hoerbuch.sauberer_pfad(pfad).split("/", 1)[0]


def als_belohnung(app, flaggen):
    """Die App, wie sie für einen Belohnungs-Film gilt (frei: kein Limit; sperre: auch in Sperrzeiten)."""
    neu = dict(app)
    if (flaggen or {}).get("frei"):
        neu["zeit"] = "frei"
        neu.pop("limit_min", None)
    if (flaggen or {}).get("sperre"):
        neu["sperr_erlaubt"] = "alle"
    return neu
