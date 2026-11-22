#!/usr/bin/env python3
"""Funktionstest: Raeumliche Navigation in familyhub-v2/index.html (v2.3).

Deterministisch: Jede Pruefung fuehrt selbst zu einer definierten
Startkachel (Anker Home=plex / End=f-galerie) und drueckt dann die
Taste. Getestet werden Pfeile, Anschlag am Rand (Klasse + Endet),
Tab/Shift+Tab-Reihenfolge, Home/End, Ziffern-Direktwahl und Overlays
in zwei Layouts: 1920x1080 (Spielzimmer 6 in einer Reihe) und
800x600 (Spielzimmer 3x2).

Pfadunabhaengig: Die Startseite wird relativ zu diesem Skript
gesucht (../index.html).

Voraussetzung (einmalig):
    pip install playwright
    python3 -m playwright install chromium

Ausfuehren:
    python3 tests/test_nav.py
"""
import os

from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
URL = "file://" + os.path.abspath(os.path.join(BASE, "..", "index.html"))
FEHLER = []
JS_FEHLER = []


def pruefe(name, ist, soll):
    ok = ist == soll
    print(("  OK   " if ok else "  FEHL ") + f"{name}: ist={ist!r}" + ("" if ok else f" soll={soll!r}"))
    if not ok:
        FEHLER.append(name)


def run_suite(page, breite, hoehe, sz_breit):
    print(f"\n=== Viewport {breite}x{hoehe} (Spielzimmer: {'6er-Reihe' if sz_breit else '3x2'}) ===")

    def sel():
        return page.evaluate("() => (document.querySelector('.selected')||{}).id || '(keine)'")

    def anschlag_aktiv():
        return page.evaluate("() => !!document.querySelector('.anschlag')")

    def check(name, tasten, soll_id, rand=False):
        for t in tasten:
            page.keyboard.press(t)
            page.wait_for_timeout(45)
        pruefe(name, sel(), soll_id)
        if rand:
            pruefe(name + " [Anschlag]", anschlag_aktiv(), True)
            page.wait_for_timeout(450)
            pruefe(name + " [Endet]", anschlag_aktiv(), False)
        else:
            pruefe(name + " [kein Anschlag]", anschlag_aktiv(), False)

    # ---------- Block A: App-Grid 2x2 (Anker: Home -> plex)
    check("Startposition", ["Home"], "plex")
    check("Rechts von Plex", ["Home", "ArrowRight"], "games")
    check("Runter von Plex", ["Home", "ArrowDown"], "family")
    check("Links von Plex (Rand)", ["Home", "ArrowLeft"], "plex", rand=True)
    check("Hoch von Plex (Rand)", ["Home", "ArrowUp"], "plex", rand=True)
    check("Rechts von Games (Rand)", ["Home", "ArrowRight", "ArrowRight"], "games", rand=True)
    check("Hoch von Games (Rand)", ["Home", "ArrowRight", "ArrowUp"], "games", rand=True)
    check("Runter von Games -> Books", ["Home", "ArrowRight", "ArrowDown"], "books")
    check("Links von Books -> Familie", ["Home", "ArrowRight", "ArrowDown", "ArrowLeft"], "family")
    check("Rechts von Books (Rand)", ["Home", "ArrowRight", "ArrowDown", "ArrowRight"], "books", rand=True)
    check("Runter von Books",
          ["Home", "ArrowRight", "ArrowDown", "ArrowDown"],
          "f-witz" if sz_breit else "f-ttt")
    check("Runter von Familie",
          ["Home", "ArrowDown", "ArrowDown"],
          "f-memory" if sz_breit else "f-snake")
    check("Hoch von Familie -> Plex", ["Home", "ArrowDown", "ArrowUp"], "plex")

    # ---------- Block B: Spielzimmer (Anker: End -> f-galerie)
    if sz_breit:
        # 6 Kacheln in einer Reihe
        check("Links von Galerie -> Witz", ["End", "ArrowLeft"], "f-witz")
        check("5x Links bis Snake", ["End"] + ["ArrowLeft"] * 5, "f-snake")
        check("Links von Snake (Rand)", ["ArrowLeft"], "f-snake", rand=True)
        check("Hoch von Snake -> Familie (Kachel darueber)", ["ArrowUp"], "family")
        check("Hoch von Memory -> Familie (Kachel darueber)", ["Home", "ArrowDown", "ArrowDown", "ArrowUp"], "family")
        check("Hoch von TTT -> Familie (Kachel darueber)", ["Home", "ArrowDown", "ArrowDown", "ArrowRight", "ArrowUp"], "family")
        check("Hoch von Malen -> Books (Kachel darueber)", ["Home", "ArrowDown", "ArrowDown", "ArrowRight", "ArrowRight", "ArrowRight", "ArrowUp"], "books")
        check("Hoch von Witz -> Books", ["End", "ArrowLeft", "ArrowUp"], "books")
        check("Hoch von Galerie -> Books", ["End", "ArrowUp"], "books")
        check("Runter von Witz (Rand)", ["End", "ArrowLeft", "ArrowDown"], "f-witz", rand=True)
    else:
        # 3x2: oben snake memory ttt, unten mal witz galerie
        check("Links von Galerie -> Witz", ["End", "ArrowLeft"], "f-witz")
        check("2x Links bis Malen", ["End", "ArrowLeft", "ArrowLeft"], "f-mal")
        check("Links von Malen (Rand)", ["ArrowLeft"], "f-mal", rand=True)
        check("Hoch von Malen -> Snake", ["ArrowUp"], "f-snake")
        check("Runter von Galerie (Rand)", ["End", "ArrowDown"], "f-galerie", rand=True)
        check("Hoch von Galerie -> TTT (Kachel darueber)", ["End", "ArrowUp"], "f-ttt")
        check("Hoch von Snake -> Familie",
              ["Home", "ArrowDown", "ArrowDown", "ArrowUp"], "family")
        check("Spielzimmer-Reihe 1 durchlaufen",
              ["Home", "ArrowDown", "ArrowDown", "ArrowRight", "ArrowRight"], "f-ttt")
        check("Rechts von TTT (Rand)",
              ["ArrowRight"], "f-ttt", rand=True)
        check("Runter von TTT -> Galerie", ["ArrowDown"], "f-galerie")
        check("Runter von Memory -> Witz",
              ["Home", "ArrowDown", "ArrowDown", "ArrowRight", "ArrowDown"], "f-witz")
        check("Runter von Witz (Rand)",
              ["Home", "ArrowDown", "ArrowDown", "ArrowRight", "ArrowDown", "ArrowDown"], "f-witz", rand=True)

    # ---------- Block C: Tab / Shift+Tab / Home / End
    check("Tab: Plex -> Games", ["Home", "Tab"], "games")
    check("Tab: Games -> Familie", ["Home", "Tab", "Tab"], "family")
    check("Tab: Familie -> Books", ["Home", "Tab", "Tab", "Tab"], "books")
    check("Tab: Books -> Snake (DOM-Reihenfolge)", ["Home", "Tab", "Tab", "Tab", "Tab"], "f-snake")
    check("Tab von Galerie (Wrap)", ["End", "Tab"], "plex")
    check("Shift+Tab von Plex (Wrap)", ["Home", "Shift+Tab"], "f-galerie")
    check("Home", ["End", "Home"], "plex")
    check("End", ["Home", "End"], "f-galerie")

    # ---------- Block D: Ziffern-Direktwahl + Overlays
    page.keyboard.press("5")
    page.wait_for_timeout(250)
    pruefe("Taste 5 oeffnet Snake", page.evaluate("() => !document.getElementById('ov-snake').hidden"), True)
    pruefe("Snake-Kachel markiert", sel(), "f-snake")
    page.keyboard.press("Escape")
    page.wait_for_timeout(150)
    pruefe("Escape schliesst Snake", page.evaluate("() => document.getElementById('ov-snake').hidden"), True)
    pruefe("Auswahl bleibt auf Snake", sel(), "f-snake")

    page.keyboard.press("End")
    page.wait_for_timeout(100)
    page.keyboard.press("Enter")
    page.wait_for_timeout(250)
    pruefe("Enter oeffnet Galerie", page.evaluate("() => !document.getElementById('ov-galerie').hidden"), True)
    page.keyboard.press("Escape")
    page.wait_for_timeout(150)
    pruefe("Escape schliesst Galerie", page.evaluate("() => document.getElementById('ov-galerie').hidden"), True)

    page.keyboard.press("8")
    page.wait_for_timeout(250)
    pruefe("Taste 8 oeffnet Malen", page.evaluate("() => !document.getElementById('ov-malen').hidden"), True)
    page.keyboard.press("Escape")
    page.wait_for_timeout(150)
    pruefe("Escape schliesst Malen", page.evaluate("() => document.getElementById('ov-malen').hidden"), True)


with sync_playwright() as p:
    # wie im Kiosk (kiosk.sh): Pfeiltasten springen auf Webseiten von Link zu Link
    browser = p.chromium.launch(args=["--enable-spatial-navigation"])
    for breite, hoehe, sz_breit in [(1920, 1080, True), (800, 600, False)]:
        page = browser.new_page(viewport={"width": breite, "height": hoehe})
        page.on("pageerror", lambda e: JS_FEHLER.append(str(e)))
        page.goto(URL)
        page.wait_for_timeout(700)
        run_suite(page, breite, hoehe, sz_breit)
        page.close()
    browser.close()

print("\n================ ERGEBNIS ================")
if JS_FEHLER:
    print("JS-Laufzeitfehler:")
    for f in JS_FEHLER:
        print("  -", f)
if FEHLER:
    print(f"{len(FEHLER)} FEHLGESCHLAGENE PRUEFUNGEN:")
    for f in FEHLER:
        print("  -", f)
    raise SystemExit(1)
print("Alle Navigationspruefungen bestanden, keine JS-Fehler.")
