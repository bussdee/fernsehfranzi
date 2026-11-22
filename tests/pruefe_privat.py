#!/usr/bin/env python3
"""Sucht in allen versionierten (und neuen, nicht ignorierten) Dateien nach privaten Daten. Siehe docs/ENTWICKLUNG.md, „Private Daten“.

Geprüft werden
- private IPv4-Adressen (Bereiche nach RFC 1918) und mDNS-Hostnamen,
- E-Mail-Adressen,
- die persönlichen Werte aus config/einstellungen.js und config/pi.mk (falls vorhanden),
- Wörter aus .local/private-woerter.txt (falls vorhanden, eines pro Zeile).

Rückgabewert 1 bei einem Fund.
"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIESE_DATEI = os.path.relpath(os.path.abspath(__file__), REPO)

MUSTER = [
    ("private IP-Adresse", re.compile(r"\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")),
    ("mDNS-Hostname", re.compile(r"\b[a-z0-9][a-z0-9-]*\.local\b(?!/)", re.I)),
    # systemd-Instanzen wie getty@tty1.service sind keine Adressen.
    ("E-Mail-Adresse", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.(?!service\b|socket\b|target\b|timer\b|mount\b)[a-z]{2,}\b", re.I)),
]


def versionierte_dateien():
    r = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                       cwd=REPO, capture_output=True, text=True, check=True)
    return [p for p in r.stdout.split("\0") if p and os.path.isfile(os.path.join(REPO, p))]


def private_werte():
    """Persönliche Werte aus der nicht versionierten Konfiguration."""
    werte = set()
    pfad = os.path.join(REPO, "config", "einstellungen.js")
    if os.path.exists(pfad):
        with open(pfad, encoding="utf-8") as f:
            text = f.read()
        for schluessel in ("name", "untertitel"):
            m = re.search(r"\b%s\s*:\s*\"([^\"]+)\"" % schluessel, text)
            if m:
                werte.update(w for w in re.split(r"\W+", m.group(1)) if len(w) >= 4 and w.lower() != "edition")
        for url in re.findall(r"https?://([^/:\"]+)", text):
            werte.add(url)
        for m in re.finditer(r"name\s*:\s*\"([^\"]+)\"", text):
            werte.add(m.group(1))
    pfad = os.path.join(REPO, "config", "pi.mk")
    if os.path.exists(pfad):
        with open(pfad, encoding="utf-8") as f:
            for zeile in f:
                m = re.match(r"\s*PI_HOST\s*:?=\s*(\S+)", zeile)
                if m:
                    # Nur der Gerätename; der Benutzername ist oft ein Allerweltswort.
                    werte.add(m.group(1).split("@")[-1])
    pfad = os.path.join(REPO, ".local", "private-woerter.txt")
    if os.path.exists(pfad):
        with open(pfad, encoding="utf-8") as f:
            werte.update(z.strip() for z in f if z.strip() and not z.startswith("#"))
    return sorted(werte)


def pruefe(dateien, werte, basis=REPO):
    funde = []
    muster = list(MUSTER)
    if werte:
        muster.append(("persönlicher Wert", re.compile(
            r"\b(?:%s)\b" % "|".join(re.escape(w) for w in werte), re.I)))
    for pfad in dateien:
        if pfad == DIESE_DATEI:
            continue
        try:
            with open(os.path.join(basis, pfad), encoding="utf-8") as f:
                zeilen = f.read().splitlines()
        except (UnicodeDecodeError, OSError):
            continue   # Binärdateien
        for nr, zeile in enumerate(zeilen, 1):
            for art, rx in muster:
                for m in rx.finditer(zeile):
                    funde.append((pfad, nr, art, m.group(0)))
    return funde


def main():
    werte = private_werte()
    dateien = versionierte_dateien()
    funde = pruefe(dateien, werte)
    for pfad, nr, art, treffer in funde:
        # Den Treffer selbst nicht ausgeben, wenn er ein persönlicher Wert ist (Logs/CI).
        zeige = "***" if art == "persönlicher Wert" else treffer
        print("  ✗ %s:%d: %s (%s)" % (pfad, nr, art, zeige))
    if funde:
        print("  %d Fund(e) – private Werte gehören nach config/ oder .local/." % len(funde))
        return 1
    print("  ✓ %d Dateien, %d persönliche Werte aus config/ geprüft, nichts gefunden" % (len(dateien), len(werte)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
