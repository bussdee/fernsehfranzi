#!/usr/bin/env python3
"""Bildschirmfotos für README und Doku erzeugen: docs/bilder/*.png (über Chromium aus Playwright).

    .venv/bin/python werkzeuge/bildschirmfotos.py      (oder: make bildschirmfotos)

Läuft komplett lokal mit Beispieldaten in einem temporären Ordner (keine persönlichen Werte, kein Gerät):
Startseite, Spiele, Eltern-Seite am Handy. Port 8765 muss frei sein (kein make v3-lokal nebenher).
"""
import base64
import os
import shutil
import sys
import tempfile
import threading
from datetime import datetime, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import web  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ZIEL = os.path.join(REPO, "docs", "bilder")
PIN = "482913"
MITTWOCH = datetime(2026, 11, 18, 15, 30)
with open(os.path.join(REPO, "VERSION")) as f:
    VERSION = f.read().strip()


def beispiel_hub(ordner):
    hub = neuer_hub(ordner, Uhr(MITTWOCH))
    hub.version = VERSION
    apps = hub.eltern_daten()["apps"]
    for a in apps:   # Beispiel-Adressen, damit die Kacheln eingerichtet aussehen
        if a["id"] == "plex":
            a["start"] = "http://medien.beispiel:32400/web/"
        elif a["id"] == "buecher":
            a["start"] = "http://medien.beispiel:5000/"
        elif a["id"] in ("familie", "gute-nacht"):   # brauchen Adressen aus dem Heimnetz
            a["aktiv"] = False
    hub.katalog_aendern(apps)
    hub.einstellungen.pop("zeit_pruefen", None)       # Hinweis nach einem Update, hier nicht gewollt
    hub.pin_festlegen(PIN, erster_start_am_tv=True)
    for tag, app, stunde, sek in ((0, "spiel-snake", 14, 1200), (0, "youtube", 15, 1500), (0, "buecher", 13, 900),
                                  (1, "spiel-bass", 17, 1200), (1, "games", 16, 2700), (1, "gute-nacht", 19, 1800),
                                  (2, "plex", 17, 3000), (2, "spiel-memory", 15, 900)):
        jetzt = hub.uhr().replace(hour=stunde) - timedelta(days=tag)
        for _ in range(sek // 60):
            hub.nutzung.zaehle(jetzt, app, 60, True)
    return hub


def tv_seite(browser):
    seite = browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
    seite.goto("http://127.0.0.1:8765/")
    seite.wait_for_selector(".kachel")
    seite.evaluate("""async () => { await document.fonts.load('16px "FF Emoji"', '🎬'); await document.fonts.ready; }""")
    seite.wait_for_timeout(600)
    return seite


def foto(seite, name):
    pfad = os.path.join(ZIEL, name)
    seite.screenshot(path=pfad)
    print("  ✓ docs/bilder/%s (%d KB)" % (name, os.path.getsize(pfad) // 1024))
    return pfad


def collage(browser, bilder, name, spalten, breite, hintergrund="#0b1020"):
    """Mehrere Bilder nebeneinander auf einer Seite und davon ein Foto (ohne Bildbibliothek)."""
    teile = "".join('<img src="data:image/png;base64,%s">' % base64.b64encode(open(b, "rb").read()).decode()
                    for b in bilder)
    html = ("<html><body style='margin:0;background:%s'><div style='display:grid;grid-template-columns:repeat(%d,1fr);"
            "gap:24px;padding:24px;width:%dpx;box-sizing:border-box'>%s</div>"
            "<style>img{width:100%%;border-radius:14px;display:block}</style></body></html>") % (hintergrund, spalten, breite, teile)
    seite = browser.new_page(viewport={"width": breite, "height": 400})
    seite.set_content(html)
    seite.wait_for_timeout(300)
    pfad = os.path.join(ZIEL, name)
    seite.screenshot(path=pfad, full_page=True)
    seite.close()
    print("  ✓ docs/bilder/%s (%d KB)" % (name, os.path.getsize(pfad) // 1024))


def main():
    os.makedirs(ZIEL, exist_ok=True)
    ordner = tempfile.mkdtemp(prefix="ff-fotos-")
    roh = os.path.join(ordner, "roh")
    os.makedirs(roh)
    hub = beispiel_hub(ordner)
    kiosk = web.baue_server(web.KioskHandler, hub, os.path.join(REPO, "web"),
                            os.path.join(ordner, "zeichnungen"), ("127.0.0.1", 8765))
    lan = web.baue_server(web.LanHandler, hub, os.path.join(REPO, "web"),
                          os.path.join(ordner, "zeichnungen"), ("127.0.0.1", 0))
    for s in (kiosk, lan):
        threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()

            # Startseite und die Bereiche
            seite = tv_seite(browser)
            foto(seite, "startseite.png")
            seite.keyboard.press("ArrowDown")
            seite.wait_for_timeout(500)
            foto(seite, "startseite-spiele.png")
            seite.close()

            # Spiele
            spiele = []
            for kachel, tasten, name in (("spiel-snake", ["Enter", 1500, "ArrowDown", 700, "ArrowLeft", 700], "snake"),
                                         ("spiel-drei", ["Enter", 500, "Enter", 900], "drei"),
                                         ("spiel-malen", ["Enter", 600] + ["ArrowRight"] * 14 + ["ArrowDown"] * 6 + ["3"] + ["ArrowLeft"] * 14 + ["5"] + ["ArrowUp"] * 6 + ["6"] + ["ArrowRight"] * 7 + ["ArrowDown"] * 3, "malen"),
                                         ("spiel-memory", ["Enter", 600], "memory")):
                seite = tv_seite(browser)
                seite.locator("[data-id=%s]" % kachel).click()
                seite.wait_for_selector(".overlay")
                for t in tasten:
                    seite.wait_for_timeout(t) if isinstance(t, int) else seite.keyboard.press(t)
                if name == "memory":
                    seite.evaluate("document.querySelectorAll('.karte').forEach((k, i) => i % 3 || k.classList.add('offen'))")
                    seite.wait_for_timeout(400)
                pfad = os.path.join(roh, name + ".png")
                seite.screenshot(path=pfad)
                spiele.append(pfad)
                seite.close()
            collage(browser, spiele, "spielzimmer.png", 2, 1600)

            # Eltern-Seite am Handy (die Nachricht erst jetzt, am TV bliebe sie bis OK stehen)
            hub.familie.nachricht("Essen ist gleich fertig!", bleibt=True)
            url = "http://127.0.0.1:%d/" % lan.server_address[1]
            handy = []
            seite = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
                                     device_scale_factor=2)
            seite.goto(url)
            seite.fill(".eh-pin", PIN)
            seite.click("text=Anmelden")
            seite.wait_for_selector(".eh-leiste")
            for name in ("Heute", "Regeln", "Statistik"):
                seite.click(".eh-leiste >> text=" + name)
                seite.wait_for_timeout(500)
                seite.evaluate("window.scrollTo(0, 0)")
                pfad = os.path.join(roh, "eltern-%s.png" % name.lower())
                seite.screenshot(path=pfad)
                handy.append(pfad)
            seite.close()
            collage(browser, handy, "eltern-seite.png", 3, 1400)
            browser.close()
    finally:
        for s in (kiosk, lan):
            s.shutdown()
            s.server_close()
        shutil.rmtree(ordner, True)


if __name__ == "__main__":
    main()
