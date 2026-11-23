#!/usr/bin/env python3
"""Ferien der Bundesländer für FernsehFranzi (4.6) aus der Ferienliste der Klassenkiste übernehmen.

Die Klassenkiste liest einmal im Jahr die amtlichen Tabellen „Ferien im Schuljahr“ der Kultusministerkonferenz ein und
legt sie als ``api/routes/ferien_daten.php`` ab. Dieses Werkzeug LIEST diese Datei nur (an der Klassenkiste ändert sich
nichts) und schreibt daraus ``server/fernsehfranzi/ferien_daten.json``. Der Fernseher fragt nie einen fremden Dienst.

Jährlich, nachdem die Klassenkiste ein neues Schuljahr übernommen hat:
    python3 werkzeuge/ferien_uebernehmen.py <Pfad zu ferien_daten.php der Klassenkiste>
und die Ausgabe (je Schuljahr die Zahl der Länder und Zeiträume) ansehen.
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIEL = os.path.join(REPO, "server", "fernsehfranzi", "ferien_daten.json")
LAENDER = ("BW", "BY", "BE", "BB", "HB", "HH", "HE", "MV", "NI", "NW", "RP", "SL", "SN", "ST", "SH", "TH")

SCHULJAHR = re.compile(r"'(\d{4}/\d{2})' => \['stand' => '([^']*)', 'quelle' => '([^']*)'")
LAND = re.compile(r"'([A-Z]{2})' => \['roh' => .*?'zeitraeume' => \[(.*?)\]\]\],?\s*$", re.M)
ZEITRAUM = re.compile(r"\['[a-z]+', '([^']+)', '(\d{4}-\d{2}-\d{2})', '(\d{4}-\d{2}-\d{2})'")


def lies(php):
    with open(php, encoding="utf-8") as f:
        text = f.read()
    stellen = [(m.start(), m.group(1), m.group(2), m.group(3)) for m in SCHULJAHR.finditer(text)]
    if not stellen:
        raise SystemExit("Keine Schuljahre gefunden – ist das die ferien_daten.php der Klassenkiste?")
    daten = {}
    for nr, (anfang, sj, stand, quelle) in enumerate(stellen):
        ende = stellen[nr + 1][0] if nr + 1 < len(stellen) else len(text)
        laender = {}
        for m in LAND.finditer(text, anfang, ende):
            laender[m.group(1)] = [[name, von, bis] for name, von, bis in ZEITRAUM.findall(m.group(2))]
        fehlt = set(LAENDER) - set(laender)
        if fehlt:
            raise SystemExit("Schuljahr %s: es fehlen %s" % (sj, ", ".join(sorted(fehlt))))
        for land, liste in laender.items():
            if not liste or any(bis < von for _, von, bis in liste):
                raise SystemExit("Schuljahr %s, %s: Zeiträume leer oder Ende vor Beginn." % (sj, land))
        daten[sj] = {"stand": stand, "quelle": quelle, "laender": laender}
    return daten


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    daten = lies(sys.argv[1])
    with open(ZIEL, "w", encoding="utf-8") as f:
        json.dump({"quelle": "Kultusministerkonferenz, Ferien im Schuljahr (über die Ferienliste der Klassenkiste)",
                   "schuljahre": daten}, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    for sj, d in daten.items():
        print("%s (Stand %s): %d Länder, %d Zeiträume" % (sj, d["stand"], len(d["laender"]),
                                                         sum(len(x) for x in d["laender"].values())))
    print("->", os.path.relpath(ZIEL, REPO))


if __name__ == "__main__":
    main()
