#!/usr/bin/env python3
"""Bildschirmfotos für README und Doku erzeugen: docs/bilder/*.png (über Chromium aus Playwright).

    .venv/bin/python werkzeuge/bildschirmfotos.py      (oder: make bildschirmfotos)

Läuft komplett lokal mit Beispieldaten in einem temporären Ordner (keine persönlichen Werte, kein Gerät):
Startseite, Spiele, Eltern-Seite am Handy. Port 8765 muss frei sein (kein make v3-lokal nebenher).
Dazu die Bilder fürs Handbuch in docs/bilder/buch/ (Kacheln, Elternbereich, Bewegungspause, Nachricht).
"""
import base64
import json
import os
import shutil
import sys
import tempfile
import threading
from datetime import datetime, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import kinderwelten as kinderwelten_mod, schule as schule_mod, web  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ZIEL = os.path.join(REPO, "docs", "bilder")
BUCH = os.path.join(ZIEL, "buch")
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
    hub.einstellungen_aendern({"youtube": {"kategorien": [
        {"name": "Tiere", "eintraege": [{"art": "video", "id": "aaaaaaaaaaa", "titel": "Pinguine im Eis"},
                                        {"art": "video", "id": "bbbbbbbbbbb", "titel": "Ein Tag im Zoo"}]},
        {"name": "Musik", "eintraege": [{"art": "video", "id": "ccccccccccc", "titel": "Bass für Anfänger"}]},
        {"name": "Basteln", "eintraege": [{"art": "video", "id": "ddddddddddd", "titel": "Papierflieger"}]}]}})
    hub.einstellungen.pop("zeit_pruefen", None)       # Hinweis nach einem Update, hier nicht gewollt
    # 6.0: „Zuhause“ mit Lieblingen und „Weiter, wo du warst“
    hub.einstellungen_aendern({"startseite": {"lieblinge": ["youtube", "spiel-snake", "spiel-malen", "spiel-memory", "buecher", "spiel-lernen"],
                                              "thema": "blau"}})
    for app in ("spiel-drei", "spiel-witz", "spiel-bass"):
        hub._zuletzt_merken(app)
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


def _im_handbuch():
    """Namen der Bilder, die das Handbuch und die Anleitungen wirklich zeigen."""
    import glob
    import re
    namen = set()
    for datei in glob.glob(os.path.join(REPO, "docs", "anleitung", "*.html")):
        with open(datei, encoding="utf-8") as f:
            namen.update(re.findall(r"bilder/buch/([a-z0-9-]+\.png)", f.read()))
    return namen


IM_HANDBUCH = _im_handbuch()
ZWISCHEN = tempfile.mkdtemp(prefix="ff-fotos-zwischen-")     # 5.0: Zwischenbilder (nur für Collagen) nicht ins Repo


def foto(seite, name, ordner=None):
    if ordner == BUCH and name not in IM_HANDBUCH:
        ordner = ZWISCHEN
    pfad = os.path.join(ordner or ZIEL, name)
    seite.screenshot(path=pfad)
    if ordner != ZWISCHEN:
        print("  ✓ %s (%d KB)" % (os.path.relpath(pfad, REPO), os.path.getsize(pfad) // 1024))
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


def buch_bilder(browser, hub, lan_url):
    """Bilder fürs Handbuch: einzelne Kacheln, Elternbereich am TV, Bewegungspause, Nachricht, Eltern-Seite."""
    os.makedirs(BUCH, exist_ok=True)
    gelesen = lambda: hub.familie.meldungen_gesehen([m["nr"] for m in hub.familie.offene_meldungen()])  # noqa: E731
    gelesen()
    for kachel, tasten, name in (("spiel-nachrichten", [], "nachrichten"), ("spiel-gutschein", [], "gutschein"),
                                 ("spiel-wecker", [], "wecker"), ("spiel-gestalten", [], "gestalten"),
                                 ("spiel-sticker", [], "sticker"), ("spiel-bass", [], "musik-akademie"),
                                 ("spiel-lernen", [], "lernspiele"), ("spiel-duell", [], "zu-zweit"),
                                 ("spiel-echo", ["Enter", 900], "farben-echo"), ("spiel-witz", [], "witz"),
                                 ("youtube", [], "youtube"), ("youtube", ["Enter", 500], "youtube-videos")):
        seite = tv_seite(browser)
        seite.wait_for_function("k => window.FernsehFranzi && FernsehFranzi.zeige(k)", arg=kachel)
        seite.locator("[data-id=%s]" % kachel).click()
        seite.wait_for_selector(".overlay")
        seite.wait_for_timeout(700)
        for t in tasten:
            seite.wait_for_timeout(t) if isinstance(t, int) else seite.keyboard.press(t)
        foto(seite, name + ".png", BUCH)
        seite.close()
    # 6.0: der Bereich „Filme & Musik“ als Raster
    seite = tv_seite(browser)
    seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('youtube')")
    seite.evaluate("FernsehFranzi.zuhause(); document.querySelector('.kachel[data-id=ordner-filme]').click()")
    seite.wait_for_timeout(600)
    foto(seite, "bereich-filme.png", BUCH)
    seite.close()
    # Elternbereich am Fernseher: PIN, dann die Knöpfe
    seite = browser.new_page(viewport={"width": 1600, "height": 900}, bypass_csp=True)
    seite.goto("http://127.0.0.1:8765/#eltern")
    seite.wait_for_timeout(1200)
    foto(seite, "elternbereich-pin.png", BUCH)
    for ziffer in PIN:
        seite.keyboard.press(ziffer)
    seite.keyboard.press("Enter")
    seite.wait_for_timeout(1000)
    foto(seite, "elternbereich.png", BUCH)
    seite.close()
    # Bewegungspause über der Startseite
    hub.familie.pause_bis = hub.uhr() + timedelta(minutes=2)
    seite = tv_seite(browser)
    seite.wait_for_selector(".pause-ebene", timeout=6000)
    seite.wait_for_timeout(1500)
    foto(seite, "bewegungspause.png", BUCH)
    hub.familie.pause_bis = None
    seite.close()
    # Nachricht der Eltern (bleibt bis OK)
    hub.familie.nachricht("Essen ist gleich fertig! Bitte Hände waschen.", bleibt=True)
    seite = tv_seite(browser)
    seite.wait_for_timeout(2500)
    foto(seite, "nachricht.png", BUCH)
    seite.close()
    gelesen()
    # Eltern-Seite: Menü und einige Bereiche
    seite = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
    seite.goto(lan_url)
    seite.fill(".eh-pin", PIN)
    seite.click("text=Anmelden")
    seite.wait_for_selector(".eh-leiste")
    seite.wait_for_timeout(400)
    foto(seite, "eltern-menue.png", BUCH)                        # 6.0: „Heute“ (Dateiname bleibt fürs Handbuch)
    for reiter, bereich in (("Zeit", "zeit"), ("Familie", "telegram"), ("Inhalte", "apps")):
        seite.click(".eh-leiste >> text=" + reiter)
        seite.click(".eh-abschnitt[data-bereich=%s] .eh-abschnitt-kopf" % bereich)
        seite.wait_for_selector(".eh-abschnitt.offen[data-bereich=%s] .eh-abschnitt-inhalt" % bereich)
        seite.wait_for_timeout(500)
        seite.evaluate("(b) => document.querySelector(`.eh-abschnitt[data-bereich='${b}']`).scrollIntoView()", bereich)
        foto(seite, "eltern-%s.png" % bereich, BUCH)
    seite.close()


def handy_bilder(browser, hub):
    """4.3: Handy-Spiele - Lobby mit QR-Code, Spiele am Fernseher, Ansichten am Handy (Beispieladresse statt echter)."""
    hub.einstellungen_aendern({"handyspiele": {"aktiv": True}})
    hub.raum_adresse = lambda: "http://fernseher:8767"
    hub.raum_oeffnen()
    papa = hub.raum_beitreten(hub.raum.token, "Papa", "🐼", False)
    hub.raum_beitreten(hub.raum.token, "Mama", "🦊", False)
    raum_server = web.baue_server(web.RaumHandler, hub, os.path.join(REPO, "web"), os.path.join(hub.ordner, "z"), ("127.0.0.1", 0))
    threading.Thread(target=raum_server.serve_forever, daemon=True).start()
    tv = tv_seite(browser)
    tv.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-handys')")
    tv.locator("[data-id=spiel-handys]").click()
    tv.wait_for_selector(".hs-qr svg")
    tv.wait_for_timeout(800)
    lobby = foto(tv, "handys-lobby.png", BUCH)
    handy = browser.new_page(viewport={"width": 390, "height": 760}, is_mobile=True, has_touch=True, device_scale_factor=2)
    handy.goto("http://127.0.0.1:%d/mitspielen" % raum_server.server_address[1])
    handy.evaluate("(g) => sessionStorage.setItem('ff-raum', JSON.stringify({schluessel: '', geheim: g}))", papa["geheim"])
    handy.goto("http://127.0.0.1:%d/mitspielen" % raum_server.server_address[1])
    bilder_tv, bilder_handy = [lobby], []
    for spiel, opt, zeichen in (("quiz", {"paket": "gemischt"}, ".hs-bahn"), ("raumschiff", {"stufe": 1}, ".hs-lampe"),
                                ("ton", {}, ".hs-leiter")):
        hub.raum_tv_aktion(dict({"art": "start", "spiel": spiel}, **opt))
        tv.wait_for_selector(zeichen)
        tv.wait_for_timeout(900)
        bilder_tv.append(foto(tv, "handys-%s.png" % spiel, BUCH))
        if spiel != "ton":
            handy.wait_for_timeout(1500)
            bilder_handy.append(foto(handy, "handy-%s.png" % spiel, BUCH))
        hub.raum_tv_aktion({"art": "lobby"})
    for spiel, zeichen in (("rakete", ".hs-himmel"), ("klatsch", ".hs-takt")):
        hub.raum_tv_aktion({"art": "start", "spiel": spiel})
        try:
            tv.wait_for_selector(zeichen, timeout=8000)
        except Exception:
            print("FEHLT", spiel, tv.inner_text(".overlay")[:300])
            raise
        tv.wait_for_timeout(700)
        foto(tv, "handys-%s.png" % spiel, BUCH)
        hub.raum_tv_aktion({"art": "lobby"})
    hub.raum_tv_aktion({"art": "start", "spiel": "buzzer", "paket": "gemischt"})
    handy.wait_for_selector(".buzzer")
    handy.wait_for_timeout(500)
    bilder_handy.insert(0, foto(handy, "handy-buzzer.png", BUCH))
    hub.raum_tv_aktion({"art": "lobby"})
    handy.close()
    tv.close()
    raum_server.shutdown()
    raum_server.server_close()
    hub.raum_schliessen()
    collage(browser, bilder_tv, "handyspiele.png", 2, 1600)
    collage(browser, bilder_handy, "handyspiele-handy.png", 3, 1300)


def beispielfoto(browser, farbe1, farbe2, symbol):
    """Ein JPEG-Beispielbild (Verlauf mit großem Symbol) - keine echten Fotos in der Doku."""
    s = browser.new_page(viewport={"width": 800, "height": 600})
    s.set_content("<body style='margin:0;height:100vh;display:flex;align-items:center;justify-content:center;"
                  "background:linear-gradient(135deg,%s,%s);font-size:260px'>%s</body>" % (farbe1, farbe2, symbol))
    roh = s.screenshot(type="jpeg", quality=80)
    s.close()
    return roh


def aussen_bilder(browser, hub):
    """5.0: helles Design, Wetter, Schule, Geschichten & Rätsel - mit festen Beispieldaten (kein Netz, keine echten Inhalte)."""
    import time
    from test_50 import open_meteo
    uhr_vorher = hub.uhr.jetzt
    hub.uhr.jetzt = hub.uhr.jetzt.replace(hour=14, minute=10)
    ort = {"name": "Musterstadt", "lat": 50.1, "lon": 8.6}
    hub.einstellungen_aendern({"wetter": {"aktiv": True, "ort": ort}, "kinderwelten": {"aktiv": True}})
    hub.wetter.roh, hub.wetter._ort, hub.wetter.geholt = open_meteo(hub.uhr()), dict(ort), time.time()
    hub.wetter.tick = lambda *a, **k: None
    geschichte = {"titel": "Der Drache, der nicht fliegen wollte", "reihe": "Beispielgeschichten",
                  "text": "<p>Hoch oben auf dem Berg wohnte ein kleiner Drache namens Fridolin. Alle anderen Drachen flogen "
                          "jeden Morgen eine Runde um den Gipfel. Nur Fridolin blieb lieber am Boden und sammelte bunte Steine.</p>"
                          "<p>„Warum fliegst du nicht mit?“, fragte seine Freundin, die Eule Ottilie.</p>"
                          "<p>Fridolin zuckte mit den Flügeln. „Von da oben sieht man die schönen Steine doch gar nicht!“</p>"}
    daten = {"/geschichten?kinder=1&anzahl=100": {"eintraege": [
        {"adresse": "drache", "titel": geschichte["titel"], "reihe": "Beispielgeschichten", "lesezeit": 4},
        {"adresse": "laterne", "titel": "Die Laterne im Nebel", "reihe": "Beispielgeschichten", "lesezeit": 6},
        {"adresse": "schneckenrennen", "titel": "Das große Schneckenrennen", "reihe": "Beispielgeschichten", "lesezeit": 3}]},
        "/geschichte/drache": geschichte}
    hub.kinderwelten = kinderwelten_mod.Kinderwelten(hub, holer=lambda weg: daten[weg])
    heute = hub.uhr().date()
    hub.klassenkiste_basis = lambda: "https://klassenkiste.beispiel"
    hub.einstellungen_aendern({"schule": {"aktiv": True}})
    hub.schule.tick = lambda *a, **k: None
    hub.schule.stand = {"heute": heute.isoformat(), "frei": [], "ungelesen": 0,
                        "stunden": schule_mod.stunden_heute({"today_lessons": [
                            {"period": 1, "subject": "Deutsch", "room": "12", "start": "08:00", "end": "08:45"},
                            {"period": 2, "subject": "Mathe", "room": "12", "start": "08:50", "end": "09:35"},
                            {"period": 3, "subject": "Sachkunde", "room": "Bio", "start": "09:55", "end": "10:40", "changed": True},
                            {"period": 4, "subject": "Kunst", "start": "10:45", "end": "11:30", "cancelled": True}]})[0],
                        "hausaufgaben": [], "nachrichten": [], "termine": [],
                        "morgen": {"datum": None, "name": "", "frei": [], "stunden": [], "satz": ""}}
    hub.schule.geholt = time.time()
    try:
        hub.startseite_setzen({"lieblinge": [], "thema": "hellblau"})
        seite = tv_seite(browser)
        seite.wait_for_selector("#wetter-kopf:not([hidden])", timeout=6000)
        seite.wait_for_timeout(500)
        foto(seite, "startseite-hell.png", BUCH)
        seite.close()
        for thema in ("rosa", "mint"):                           # 6.0: zwei weitere Farben für die Übersicht im README
            hub.startseite_setzen({"lieblinge": [], "thema": thema})
            seite = tv_seite(browser)
            seite.wait_for_timeout(500)
            foto(seite, "farbe-%s.png" % thema, ZWISCHEN)
            seite.close()
        hub.startseite_setzen({"lieblinge": [], "thema": "blau"})
        for kachel, tasten, name in (("spiel-wetter", [], "wetter"), ("spiel-schule", [], "schule"),
                                     ("spiel-kinderwelten", [], "geschichten"), ("spiel-kinderwelten", ["Enter", 1200], "lesen")):
            seite = tv_seite(browser)
            seite.wait_for_function("k => window.FernsehFranzi && FernsehFranzi.zeige(k)", arg=kachel)
            seite.locator("[data-id=%s]" % kachel).click()
            seite.wait_for_selector(".overlay")
            seite.wait_for_timeout(1200)
            for t in tasten:
                seite.wait_for_timeout(t) if isinstance(t, int) else seite.keyboard.press(t)
            foto(seite, name + ".png", BUCH)
            seite.close()
        b = lambda n: os.path.join(BUCH, n + ".png")  # noqa: E731
        collage(browser, [b("startseite-hell"), os.path.join(ZWISCHEN, "farbe-mint.png"), os.path.join(ZWISCHEN, "farbe-rosa.png")],
                "designs.png", 3, 1800, "#ffffff")
        collage(browser, [b("wetter"), b("schule"), b("lesen")], "wetter-schule-geschichten.png", 3, 1800)
    finally:
        hub.uhr.jetzt = uhr_vorher
        hub.einstellungen_aendern({"wetter": {"aktiv": False, "ort": ort}, "kinderwelten": {"aktiv": False}, "schule": {"aktiv": False}})


def medien_bilder(browser, hub):
    """4.4: Foto-Nachricht, Fotoalbum, Karaoke (mit einem Beispiel-Lied), Lautstärke-Rakete und Klatsch-Rhythmus."""
    import http.server
    os.makedirs(os.path.join(hub.ordner, "medien"), exist_ok=True)
    namen = []
    for n, (f1, f2, sym) in enumerate((("#4facfe", "#00f2fe", "🏖️"), ("#43e97b", "#38f9d7", "🐶"), ("#fa709a", "#fee140", "🎂"))):
        name = "m%010d-beisp%d.jpg" % (1763470000 + n, n)
        with open(os.path.join(hub.ordner, "medien", name), "wb") as f:
            f.write(beispielfoto(browser, f1, f2, sym))
        namen.append(name)
    hub.einstellungen_aendern({"fotoalbum": {"erlaubt": True}})
    for name in namen[1:]:
        hub.album_uebernehmen(name)
    hub.fotoalbum_kind({"auswahl": ["album:" + hub.album_liste()[0]["datei"]]})
    hub.familie.nachricht("Schöne Grüße vom Strand!", quelle="Oma", bleibt=True, chat=1, symbol="👵", medium={"art": "foto", "datei": namen[0]})
    seite = tv_seite(browser)
    seite.wait_for_selector("#meldungen .meldung-foto")
    seite.wait_for_timeout(800)
    foto(seite, "nachricht-foto.png", BUCH)
    seite.click("#meldungen button")
    hub.familie.meldungen_gesehen([m["nr"] for m in hub.familie.offene_meldungen()])
    seite.close()
    seite = tv_seite(browser)
    seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-fotoalbum')")
    seite.locator("[data-id=spiel-fotoalbum]").click()
    seite.wait_for_selector(".fa-kachel img")
    seite.keyboard.press("ArrowDown")
    seite.wait_for_timeout(900)
    foto(seite, "fotoalbum.png", BUCH)
    seite.close()

    class Lieder(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            inhalt = json.dumps({"songs": [
                {"id": "b1", "title": "Bruder Jakob", "playlist": "Kinderlieder", "duration": 40, "src": "",
                 "lyrics": "Bruder Jakob, Bruder Jakob,\nschläfst du noch? Schläfst du noch?\n\nHörst du nicht die Glocken?\n"
                           "Hörst du nicht die Glocken?\nDing, dang, dong. Ding, dang, dong."},
                {"id": "b2", "title": "Alle meine Entchen", "playlist": "Kinderlieder", "duration": 30, "src": "", "lyrics": "Alle meine Entchen"},
                {"id": "b3", "title": "Der Mond ist aufgegangen", "playlist": "Abendlieder", "duration": 60, "src": "", "lyrics": "Der Mond ist aufgegangen"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(inhalt)))
            self.end_headers()
            self.wfile.write(inhalt)
    lieder = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Lieder)
    threading.Thread(target=lieder.serve_forever, daemon=True).start()
    apps = hub.eltern_daten()["apps"]
    next(a for a in apps if a["id"] == "klassenkiste")["start"] = "http://127.0.0.1:%d/" % lieder.server_address[1]
    hub.katalog_aendern(apps)
    hub._kk.update(cookie="beispiel", zeit=hub.monoton() + 10 ** 6)
    seite = tv_seite(browser)
    seite.wait_for_function("window.FernsehFranzi && FernsehFranzi.zeige('spiel-karaoke')")
    seite.locator("[data-id=spiel-karaoke]").click()
    seite.wait_for_selector(".ka-eintrag.gewaehlt")
    foto(seite, "karaoke-liste.png", BUCH)
    seite.keyboard.press("Enter")
    seite.wait_for_selector(".ka-text")
    seite.wait_for_timeout(1500)
    foto(seite, "karaoke.png", BUCH)
    seite.close()
    lieder.shutdown()
    lieder.server_close()


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
            seite.evaluate("document.querySelector('.kachel[data-id=ordner-spiele]').click()")   # 6.0: Bereich „Spiele“
            seite.wait_for_timeout(600)
            foto(seite, "startseite-spiele.png")
            seite.close()

            # Spiele
            spiele = []
            for kachel, tasten, name in (("spiel-snake", ["Enter", 1500, "ArrowDown", 700, "ArrowLeft", 700], "snake"),
                                         ("spiel-drei", ["Enter", 500, "Enter", 900], "drei"),
                                         ("spiel-malen", ["Enter", 600] + ["ArrowRight"] * 14 + ["ArrowDown"] * 6 + ["3"] + ["ArrowLeft"] * 14 + ["5"] + ["ArrowUp"] * 6 + ["6"] + ["ArrowRight"] * 7 + ["ArrowDown"] * 3, "malen"),
                                         ("spiel-memory", ["Enter", 600], "memory")):
                seite = tv_seite(browser)
                seite.wait_for_function("k => window.FernsehFranzi && FernsehFranzi.zeige(k)", arg=kachel)
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
            for name, datei in (("Heute", "heute"), ("Zeit", "zeit"), ("Inhalte", "inhalte")):   # 6.0: Reiter
                seite.click(".eh-leiste >> text=" + name)
                seite.wait_for_timeout(500)
                seite.evaluate("window.scrollTo(0, 0)")
                pfad = os.path.join(roh, "eltern-%s.png" % datei)
                seite.screenshot(path=pfad)
                handy.append(pfad)
            seite.close()
            collage(browser, handy, "eltern-seite.png", 3, 1400)
            buch_bilder(browser, hub, url)
            handy_bilder(browser, hub)
            medien_bilder(browser, hub)
            aussen_bilder(browser, hub)
            browser.close()
    finally:
        for s in (kiosk, lan):
            s.shutdown()
            s.server_close()
        shutil.rmtree(ordner, True)
        shutil.rmtree(ZWISCHEN, True)


if __name__ == "__main__":
    main()
