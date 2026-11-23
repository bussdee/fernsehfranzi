#!/usr/bin/env python3
"""Anleitungen als PDF erzeugen (über Chromium aus Playwright):

    docs/anleitung/anleitung.html     -> web/anleitung.pdf          Anleitung für die Familie (kompakt)
    docs/anleitung/kinder.html        -> web/kinder-anleitung.pdf   Anleitung für das Kind
    docs/anleitung/handbuch*.html     -> web/handbuch.pdf           4.2.1: das große Handbuch (Umschlag, Inhalt mit Seitenzahlen)
    docs/anleitung/kurzanleitung.html -> web/kurzanleitung.pdf      4.2.1: eine DIN-A4-Seite für neben den Fernseher

Das Handbuch entsteht in zwei Durchläufen: Erst wird der Innenteil gedruckt und mit pdftotext nachgesehen, auf welcher
Seite jede Kapitel-Marke (@@kNN@@) steht; diese Seitenzahlen kommen ins Inhaltsverzeichnis, dann wird neu gedruckt.
Der Umschlag (ohne Seitenzahl) wird mit pdfunite davorgesetzt. Beides stammt aus poppler-utils.

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
HANDBUCH_QUELLE = os.path.join(REPO, "docs", "anleitung", "handbuch.html")
UMSCHLAG_QUELLE = os.path.join(REPO, "docs", "anleitung", "handbuch-umschlag.html")
HANDBUCH_ZIEL = os.path.join(REPO, "web", "handbuch.pdf")
KURZ_QUELLE = os.path.join(REPO, "docs", "anleitung", "kurzanleitung.html")
KURZ_ZIEL = os.path.join(REPO, "web", "kurzanleitung.pdf")
QUELLEN = (QUELLE, KINDER_QUELLE, HANDBUCH_QUELLE, UMSCHLAG_QUELLE, KURZ_QUELLE)


def pruefsumme():
    """Prüfsumme aller Quellen (eine Zeile) - passen die PDFs zur aktuellen Fassung?"""
    h = hashlib.sha256()
    for pfad in QUELLEN:
        with open(pfad, "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def fusszeile(titel):
    return ('<div style="font-size:8px;width:100%;text-align:center;color:#888;font-family:DejaVu Sans,sans-serif">'
            'FernsehFranzi – ' + titel + ' · Seite <span class="pageNumber"></span> von <span class="totalPages"></span></div>')


def kapitel_seiten(pdf):
    """{"k01": 3, …}: auf welcher Seite steht welche Kapitel-Marke?"""
    import re
    import subprocess
    text = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    seiten = {}
    for nr, seite in enumerate(text.split("\f"), 1):
        for marke in re.findall(r"@@(k\d\d)@@", seite):
            seiten.setdefault(marke, nr)
    return seiten


def handbuch(browser, tmp):
    import subprocess
    innen = os.path.join(tmp, "innen.pdf")
    umschlag = os.path.join(tmp, "umschlag.pdf")
    seite = browser.new_page()
    seite.goto("file://" + HANDBUCH_QUELLE)
    seite.evaluate("document.fonts.ready")
    optionen = dict(format="A4", print_background=True, display_header_footer=True, header_template="<span></span>",
                    footer_template=fusszeile("Das Handbuch"), prefer_css_page_size=True)
    seite.pdf(path=innen, **optionen)
    seiten = kapitel_seiten(innen)
    fehlt = [k for k in seite.evaluate("[...document.querySelectorAll('.toc li[data-k]')].map(l => l.dataset.k)") if k not in seiten]
    if fehlt:
        raise SystemExit("Kapitel-Marken nicht gefunden: %s" % ", ".join(fehlt))
    seite.evaluate("""(s) => document.querySelectorAll('.toc li[data-k]').forEach(l => {
        l.querySelector('.s').textContent = s[l.dataset.k]; })""", seiten)
    seite.pdf(path=innen, **optionen)
    if kapitel_seiten(innen) != seiten:
        raise SystemExit("Seitenzahlen haben sich beim zweiten Druck verschoben.")
    seite.close()
    seite = browser.new_page()
    seite.goto("file://" + UMSCHLAG_QUELLE)
    seite.pdf(path=umschlag, format="A4", print_background=True, prefer_css_page_size=True)
    seite.close()
    subprocess.run(["pdfunite", umschlag, innen, HANDBUCH_ZIEL], check=True)


def main():
    import shutil
    import tempfile
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp(prefix="ff-anleitung-")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for quelle, ziel, titel in ((QUELLE, ZIEL, "Anleitung"), (KINDER_QUELLE, KINDER_ZIEL, "Deine Anleitung")):
                seite = browser.new_page()
                seite.goto("file://" + quelle)
                seite.pdf(path=ziel, format="A4", print_background=True, display_header_footer=True,
                          header_template="<span></span>", footer_template=fusszeile(titel),
                          margin={"top": "14mm", "bottom": "16mm", "left": "14mm", "right": "14mm"})
                seite.close()
            handbuch(browser, tmp)
            seite = browser.new_page()
            seite.goto("file://" + KURZ_QUELLE)
            seite.emulate_media(media="print")
            seite.set_viewport_size({"width": 794, "height": 1123})          # A4 bei 96 dpi
            if seite.evaluate("(() => { const b = document.querySelector('.blatt'); return b.scrollHeight > b.clientHeight + 1; })()"):
                raise SystemExit("Die Kurzanleitung passt nicht auf eine Seite (docs/anleitung/kurzanleitung.html kürzen).")
            seite.pdf(path=KURZ_ZIEL, format="A4", print_background=True, prefer_css_page_size=True)
            seite.close()
            browser.close()
    finally:
        shutil.rmtree(tmp, True)
    for ziel in (ZIEL, KINDER_ZIEL, HANDBUCH_ZIEL, KURZ_ZIEL):
        print("%s (%d KB)" % (os.path.relpath(ziel, REPO), os.path.getsize(ziel) // 1024))
    with open(os.path.join(REPO, "web", "anleitung.quelle"), "w") as f:
        f.write(pruefsumme() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
