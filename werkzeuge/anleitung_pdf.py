#!/usr/bin/env python3
"""Anleitung als PDF erzeugen: docs/anleitung/anleitung.html -> web/anleitung.pdf (über Chromium aus Playwright).

    .venv/bin/python werkzeuge/anleitung_pdf.py      (oder: make anleitung)

Schreibt daneben web/anleitung.quelle (SHA-256 der HTML-Datei) - der Test prüft damit, dass das PDF zur
aktuellen Fassung passt. Die Eltern-Seite verlinkt das PDF.
"""
import hashlib
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUELLE = os.path.join(REPO, "docs", "anleitung", "anleitung.html")
ZIEL = os.path.join(REPO, "web", "anleitung.pdf")
# 3.2.1: zweite Anleitung für das Kind (Spiele, Bass, Retro-Tricks - nichts zum Verstellen)
KINDER_QUELLE = os.path.join(REPO, "docs", "anleitung", "kinder.html")
KINDER_ZIEL = os.path.join(REPO, "web", "kinder-anleitung.pdf")


def pruefsumme():
    """Prüfsumme beider Quellen (eine Zeile) - passt das PDF zur aktuellen Fassung?"""
    h = hashlib.sha256()
    for pfad in (QUELLE, KINDER_QUELLE):
        with open(pfad, "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def main():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for quelle, ziel, titel in ((QUELLE, ZIEL, "Anleitung"), (KINDER_QUELLE, KINDER_ZIEL, "Deine Anleitung")):
            seite = browser.new_page()
            seite.goto("file://" + quelle)
            seite.pdf(path=ziel, format="A4", print_background=True, display_header_footer=True,
                      header_template="<span></span>",
                      footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#888">'
                                      'FernsehFranzi – ' + titel + ' · Seite <span class="pageNumber"></span> von '
                                      '<span class="totalPages"></span></div>',
                      margin={"top": "14mm", "bottom": "16mm", "left": "14mm", "right": "14mm"})
            seite.close()
            print("%s (%d KB)" % (os.path.relpath(ziel, REPO), os.path.getsize(ziel) // 1024))
        browser.close()
    with open(os.path.join(REPO, "web", "anleitung.quelle"), "w") as f:
        f.write(pruefsumme() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
