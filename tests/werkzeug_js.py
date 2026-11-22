#!/usr/bin/env python3
"""Zieht die eingebetteten <script>-Blöcke aus HTML-Dateien und prüft sie mit `node --check`.

    python3 tests/werkzeug_js.py <arbeitsordner> datei.html [...]
"""
import os
import re
import subprocess
import sys

SKRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S | re.I)


def bloecke(html):
    return [m.group(1) for m in SKRIPT.finditer(html)]


def main(argv):
    ordner, dateien = argv[0], argv[1:]
    os.makedirs(ordner, exist_ok=True)
    fehler = 0
    for datei in dateien:
        with open(datei, encoding="utf-8") as f:
            teile = bloecke(f.read())
        for nr, js in enumerate(teile, 1):
            ziel = os.path.join(ordner, "%s.%d.js" % (os.path.basename(datei), nr))
            with open(ziel, "w", encoding="utf-8") as f:
                f.write(js)
            r = subprocess.run(["node", "--check", ziel], capture_output=True, text=True)
            if r.returncode:
                fehler += 1
                print("  ✗ %s, Skriptblock %d:\n%s" % (datei, nr, r.stderr))
            else:
                print("  ✓ %s, Skriptblock %d (%d Zeilen)" % (datei, nr, js.count("\n")))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
