#!/usr/bin/env python3
"""Passt ~/.config/labwc/autostart fuer den FamilyHub an (idempotent).

- sichert die Datei einmalig (autostart.vor-familyhub)
- deaktiviert (kommentiert) alte Startzeilen, die mit dem Hub kollidieren:
  cec_keys.py (jetzt systemd), games_launcher.py (jetzt server.py),
  familyhub.py (altes Tk-Dashboard), chromium (jetzt kiosk.sh),
  wpctl set-default (Ton-Wahl macht jetzt der Hub, die Sink-ID wechselt)
- fuegt die kiosk.sh-Zeile hinzu, falls sie fehlt
Aufruf: labwc_autostart.py <autostart-datei> <kiosk.sh-pfad>
"""
import os
import re
import shutil
import sys

datei, kiosk = sys.argv[1], sys.argv[2]
MUSTER = re.compile(r"cec_keys\.py|games_launcher\.py|familyhub\.py|chromium|wpctl\s+set-default")
MARKE = "# [FamilyHub v2.4 deaktiviert] "

zeilen = open(datei, encoding="utf-8").read().splitlines() if os.path.exists(datei) else []
if zeilen and not os.path.exists(datei + ".vor-familyhub"):
    shutil.copy(datei, datei + ".vor-familyhub")

ergebnis, i = [], 0
while i < len(zeilen):
    block = [zeilen[i]]
    while block[-1].rstrip().endswith("\\") and i + 1 < len(zeilen):
        i += 1
        block.append(zeilen[i])
    i += 1
    text = "\n".join(block)
    if (not block[0].lstrip().startswith("#") and MUSTER.search(text)
            and "kiosk.sh" not in text):
        ergebnis.extend(MARKE + zeile for zeile in block)
    else:
        ergebnis.extend(block)

if not any("kiosk.sh" in z and not z.lstrip().startswith("#") for z in ergebnis):
    if ergebnis and ergebnis[-1].strip():
        ergebnis.append("")
    ergebnis += ["# FernsehFranzi Family Hub (Kiosk-Supervisor)", kiosk + " &"]

os.makedirs(os.path.dirname(datei), exist_ok=True)
open(datei, "w", encoding="utf-8").write("\n".join(ergebnis) + "\n")
print("labwc-Autostart angepasst:", datei)
