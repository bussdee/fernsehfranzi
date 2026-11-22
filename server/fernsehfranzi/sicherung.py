"""FernsehFranzi 4.1 - Sicherung zum Herunterladen und Einspielen (Eltern-Seite).

Eine ZIP-Datei mit allem, was FernsehFranzi über das Kind und die Familie weiß: Einstellungen (Apps, Zeitregeln, Wecker,
YouTube …), Zeitkonto, Statistik, Gutscheine, Familie (Nachrichten, Sticker, Bass-Tagebuch), Hörbuch-Stände und die
gemalten Bilder.

Nicht in der Sicherung: der Telegram-Bot-Token, die Eltern-PIN (pin.json), der Kiosk-Schlüssel und Protokolle.
Beim Einspielen bleiben PIN und Token des Geräts erhalten. Vorher legt das Gerät selbst eine Sicherung des alten Stands an
(sicherungen/vor-einspielen-<zeit>.zip, die letzten drei bleiben).
"""
import io
import json
import os
import re
import zipfile

DATEIEN = ("apps.json", "einstellungen.json", "familie.json", "gutscheine.json", "hoerbuch.json", "nutzung.json",
           "woche.json", "zeitkonto.json", "domains.json")
ZEICHNUNG = re.compile(r"zeichnungen/[A-Za-z0-9._-]+\.png\Z")
INFO = "fernsehfranzi-sicherung.json"
ZIP_MAX = 40 * 1024 * 1024
ENTPACKT_MAX = 80 * 1024 * 1024
EIGENE_BEHALTEN = 3


class SicherungsFehler(ValueError):
    pass


def _ohne_geheimes(einstellungen_roh):
    einst = json.loads(einstellungen_roh)
    if isinstance(einst.get("telegram"), dict):
        einst["telegram"] = dict(einst["telegram"], token="")
    return json.dumps(einst, ensure_ascii=False, indent=1).encode("utf-8")


def erstellen(ordner, version, zeit):
    """ZIP als Bytes."""
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(INFO, json.dumps({"version": version, "zeit": zeit,
                                     "hinweis": "Ohne PIN und ohne Telegram-Token."}, ensure_ascii=False))
        for name in DATEIEN:
            pfad = os.path.join(ordner, name)
            if not os.path.isfile(pfad):
                continue
            with open(pfad, "rb") as f:
                inhalt = f.read()
            z.writestr(name, _ohne_geheimes(inhalt) if name == "einstellungen.json" else inhalt)
        bilder = os.path.join(ordner, "zeichnungen")
        if os.path.isdir(bilder):
            for name in sorted(os.listdir(bilder)):
                if ZEICHNUNG.match("zeichnungen/" + name) and os.path.isfile(os.path.join(bilder, name)):
                    z.write(os.path.join(bilder, name), "zeichnungen/" + name)
    return puffer.getvalue()


def pruefen(daten):
    """ZIP-Bytes prüfen -> {name: bytes}. Wirft SicherungsFehler mit verständlichem Text."""
    if not daten or len(daten) > ZIP_MAX:
        raise SicherungsFehler("Die Datei ist leer oder zu groß.")
    try:
        z = zipfile.ZipFile(io.BytesIO(daten))
        eintraege = z.infolist()
    except zipfile.BadZipFile:
        raise SicherungsFehler("Das ist keine Sicherung von FernsehFranzi (keine ZIP-Datei).") from None
    namen = {e.filename for e in eintraege}
    if INFO not in namen or "einstellungen.json" not in namen:
        raise SicherungsFehler("Das ist keine Sicherung von FernsehFranzi.")
    if sum(e.file_size for e in eintraege) > ENTPACKT_MAX:
        raise SicherungsFehler("Die Sicherung ist zu groß.")
    inhalt = {}
    for e in eintraege:
        if e.is_dir():
            continue
        if e.filename != INFO and e.filename not in DATEIEN and not ZEICHNUNG.match(e.filename):
            raise SicherungsFehler("Unbekannte Datei in der Sicherung: %s" % e.filename[:60])
        roh = z.read(e)
        if e.filename.endswith(".json"):
            try:
                json.loads(roh.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                raise SicherungsFehler("%s in der Sicherung ist beschädigt." % e.filename) from None
        elif not roh.startswith(b"\x89PNG"):
            raise SicherungsFehler("%s ist kein Bild." % e.filename[:60])
        inhalt[e.filename] = roh
    return inhalt


def _schreibe(pfad, roh):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    neu = pfad + ".ff-neu"
    with open(neu, "wb") as f:
        f.write(roh)
        f.flush()
        os.fsync(f.fileno())
    os.replace(neu, pfad)


def eigene_sicherung(ordner, version, zeit):
    """Vor dem Einspielen: alter Stand nach sicherungen/ (die letzten EIGENE_BEHALTEN bleiben)."""
    ziel = os.path.join(ordner, "sicherungen")
    os.makedirs(ziel, exist_ok=True)
    name = "vor-einspielen-%s.zip" % re.sub(r"[^0-9]", "", zeit)[:14]
    _schreibe(os.path.join(ziel, name), erstellen(ordner, version, zeit))
    alte = sorted(n for n in os.listdir(ziel) if n.startswith("vor-einspielen-") and n.endswith(".zip"))
    for n in alte[:-EIGENE_BEHALTEN]:
        os.remove(os.path.join(ziel, n))
    return name


def einspielen(ordner, inhalt, telegram_token):
    """Geprüften Inhalt schreiben. PIN, Kiosk-Schlüssel und der Telegram-Token des Geräts bleiben."""
    einst = json.loads(inhalt["einstellungen.json"].decode("utf-8"))
    if isinstance(einst.get("telegram"), dict):
        einst["telegram"]["token"] = telegram_token or ""
        if not einst["telegram"]["token"]:
            einst["telegram"]["aktiv"] = False
    inhalt = dict(inhalt, **{"einstellungen.json": json.dumps(einst, ensure_ascii=False, indent=1).encode("utf-8")})
    for name, roh in inhalt.items():
        if name != INFO:
            _schreibe(os.path.join(ordner, name), roh)
