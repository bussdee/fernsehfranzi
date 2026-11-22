#!/usr/bin/env python3
"""Ergaenzt in EmulationStation eine Tastatur-Belegung fuer die TV-Fernbedienung (seit 2.5).

Die Fernbedienung erscheint als Tastatur (cec_keys.py): Pfeile, OK = Enter,
STOP = Escape, PAUSE = P. Ohne Tastatur-Eintrag in es_input.cfg laesst sich ES
damit nicht bedienen. Idempotent: Gibt es schon eine Tastatur-Belegung, bleibt
alles unveraendert. Die Datei wird vorher vom Aufrufer gesichert.

    python3 es_tastatur.py [pfad/zu/es_input.cfg]
"""
import os
import sys
import xml.etree.ElementTree as ET

STANDARD = "/opt/retropie/configs/all/emulationstation/es_input.cfg"

# SDL2-Tastencodes
BELEGUNG = [
    ("up", 1073741906),        # Pfeil hoch
    ("down", 1073741905),      # Pfeil runter
    ("left", 1073741904),      # Pfeil links
    ("right", 1073741903),     # Pfeil rechts
    ("a", 13),                 # OK = Enter
    ("b", 27),                 # STOP = Escape
    ("start", 112),            # PAUSE = p (Menue)
    ("pageup", 1073742093),    # Ruecklauf
    ("pagedown", 1073742094),  # Vorlauf
]


def ergaenze(pfad):
    baum = ET.parse(pfad)
    wurzel = baum.getroot()
    if wurzel.tag != "inputList":
        raise SystemExit("Unerwarteter Aufbau von %s (kein inputList)" % pfad)
    if any(k.get("type") == "keyboard" for k in wurzel.findall("inputConfig")):
        print("ES: Tastatur-Belegung schon vorhanden - unveraendert.")
        return False
    eintrag = ET.SubElement(wurzel, "inputConfig",
                            {"type": "keyboard", "deviceName": "Keyboard", "deviceGUID": "-1"})
    for name, code in BELEGUNG:
        ET.SubElement(eintrag, "input", {"name": name, "type": "key", "id": str(code), "value": "1"})
    ET.indent(baum, space="  ")
    neu = pfad + ".neu"
    baum.write(neu, encoding="unicode", xml_declaration=True)
    ET.parse(neu)   # Kontrolle: wieder lesbar
    os.replace(neu, pfad)
    print("ES: Tastatur-Belegung fuer die Fernbedienung ergaenzt.")
    return True


if __name__ == "__main__":
    ergaenze(sys.argv[1] if len(sys.argv) > 1 else STANDARD)
