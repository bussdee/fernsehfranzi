"""Übernahme aus Version 2.x in den Datenordner von 3.0 (einmalig, wiederholbar ohne Schaden).

Aufruf (als Kiosk-Benutzer, von install/install.sh):
    python3 -m fernsehfranzi.uebernahme <alter-hub-ordner>

Übernimmt aus ``<alt>/config/einstellungen.js``: Name, Untertitel, Geburtstage und die Adressen von
Plex, Familien Dashboard und Kavita (in den App-Katalog). Außerdem die Ton-Wahl (audio.txt) und
die Kinderzeichnungen. Vorhandene 3.0-Daten werden nie überschrieben.
"""
import copy
import json
import logging
import os
import re
import shutil
import sys

from . import daten, katalog

log = logging.getLogger("fernsehfranzi.uebernahme")
LINK_ZU_APP = {"plex": "plex", "familie": "familie", "buecher": "buecher"}


def lies_js_einstellungen(text):
    """``window.FERNSEHFRANZI_EINSTELLUNGEN = { ... };`` -> dict (JS-Objektschreibweise, tolerant)."""
    treffer = re.search(r"=\s*(\{.*\})\s*;?\s*$", text, re.S)
    if not treffer:
        raise ValueError("Kein Einstellungsobjekt gefunden.")
    roh = treffer.group(1)
    roh = re.sub(r"/\*.*?\*/", "", roh, flags=re.S)                    # Blockkommentare
    roh = re.sub(r"(?m)^\s*//.*$", "", roh)                            # Zeilenkommentare
    roh = re.sub(r"(?m)([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', roh)   # Schlüssel in ""
    roh = re.sub(r"'([^'\\]*)'", r'"\1"', roh)                         # 'text' -> "text"
    roh = re.sub(r",(\s*[}\]])", r"\1", roh)                           # Komma am Ende
    return json.loads(roh)


def uebernehme(alt, ordner=None):
    ordner = ordner or daten.datenordner()
    bericht = []
    pfad_e = os.path.join(ordner, "einstellungen.json")
    pfad_k = os.path.join(ordner, "apps.json")
    js = os.path.join(alt, "config", "einstellungen.js")
    if os.path.exists(pfad_e):
        bericht.append("einstellungen.json gibt es schon - unverändert.")
    elif os.path.exists(js):
        with open(js, encoding="utf-8") as f:
            alt_e = lies_js_einstellungen(f.read())
        neu = daten.lade_einstellungen(ordner)
        for feld in ("name", "untertitel", "geburtstage"):
            if alt_e.get(feld):
                neu[feld] = alt_e[feld]
        ton = _lies(os.path.join(alt, "audio.txt"))
        if ton in ("hdmi", "klinke"):
            neu["ton"] = {"ziel": ton}
        daten.schreibe_json(pfad_e, neu)
        bericht.append("Einstellungen übernommen (Name, Untertitel, Geburtstage, Ton).")
        if not os.path.exists(pfad_k):
            eintraege = copy.deepcopy(katalog.VORGABE)
            links = alt_e.get("links") or {}
            for link, app_id in LINK_ZU_APP.items():
                adresse = links.get(link, "")
                if isinstance(adresse, str) and adresse.startswith(("http://", "https://")) \
                        and "SERVER-ADRESSE" not in adresse:
                    next(e for e in eintraege if e["id"] == app_id)["start"] = adresse
            daten.schreibe_json(pfad_k, katalog.pruefe_katalog(eintraege))
            bericht.append("App-Katalog mit den bisherigen Adressen angelegt.")
    else:
        bericht.append("Keine alte config/einstellungen.js - Vorgaben gelten.")

    alt_z = os.path.join(alt, "zeichnungen")
    neu_z = os.path.join(ordner, "zeichnungen")
    if os.path.isdir(alt_z):
        os.makedirs(neu_z, exist_ok=True)
        anzahl = 0
        for name in os.listdir(alt_z):
            if name.endswith(".png") and not os.path.exists(os.path.join(neu_z, name)):
                shutil.copy2(os.path.join(alt_z, name), neu_z)
                anzahl += 1
        bericht.append("%d Zeichnungen übernommen." % anzahl)
    return bericht


def _lies(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


if __name__ == "__main__":
    for zeile in uebernehme(sys.argv[1]):
        print(zeile)
