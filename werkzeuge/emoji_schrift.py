#!/usr/bin/env python3
"""Emoji-Schrift für die Weboberfläche erzeugen (seit 3.1).

Der Fernseh-Pi hat keine Emoji-Schrift (am 21.11. gemessen: fc-list kennt kein Zeichen ab U+1F000) - ohne sie zeigt Chromium Memory-Bilder, ⭕ usw. nicht an.
Dieses Werkzeug sucht alle Emojis in web/ und schneidet sie aus Noto Color Emoji (SIL Open Font
License 1.1) aus. Ergebnis: web/fonts/emoji.ttf (klein), die Startseite lädt sie per @font-face.

    .venv/bin/python werkzeuge/emoji_schrift.py [--quelle /usr/share/fonts/truetype/noto/NotoColorEmoji.ttf]

Nach jeder Änderung an Emojis in web/ neu ausführen; der Test tests/test_emoji.py prüft es.
"""
import argparse
import glob
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIEL = os.path.join(REPO, "web", "fonts", "emoji.ttf")
QUELLE = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


def ist_emoji(zeichen):
    c = ord(zeichen)
    return (0x1F000 <= c <= 0x1FAFF or 0x2600 <= c <= 0x27BF or 0x2B00 <= c <= 0x2BFF
            or 0x2190 <= c <= 0x21FF or 0x2300 <= c <= 0x23FF or c in (0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122))


def emojis_in_web():
    gefunden = set()
    for muster in ("web/**/*.js", "web/**/*.html", "web/**/*.css", "server/fernsehfranzi/*.py"):
        for pfad in glob.glob(os.path.join(REPO, muster), recursive=True):
            with open(pfad, encoding="utf-8") as f:
                gefunden.update(z for z in f.read() if ist_emoji(z))
    return gefunden


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quelle", default=QUELLE)
    a = ap.parse_args(argv)
    from fontTools import subset
    from fontTools.ttLib import TTFont
    vorhanden = set(TTFont(a.quelle).getBestCmap())
    zeichen = sorted(ord(z) for z in emojis_in_web())
    nimm = [c for c in zeichen if c in vorhanden] + [0xFE0F, 0x200D]
    fehlen = [chr(c) for c in zeichen if c not in vorhanden]
    os.makedirs(os.path.dirname(ZIEL), exist_ok=True)
    optionen = subset.Options()
    optionen.layout_features = ["*"]
    optionen.notdef_outline = False
    optionen.drop_tables = []           # CBDT/CBLC (Farbbilder) behalten
    schrift = subset.load_font(a.quelle, optionen)
    s = subset.Subsetter(optionen)
    s.populate(unicodes=nimm)
    s.subset(schrift)
    subset.save_font(schrift, ZIEL, optionen)
    print("%d Emojis -> %s (%d KB)" % (len(nimm) - 2, os.path.relpath(ZIEL, REPO), os.path.getsize(ZIEL) // 1024))
    if fehlen:
        print("Nicht in der Quelle (bleiben Text): %s" % " ".join(fehlen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
