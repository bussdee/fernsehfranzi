"""HTTP-Schicht von FernsehFranzi 3.0.

Zwei Server, gleiche Logik (``kern.Hub``):

* **Kiosk** auf ``127.0.0.1:8765`` (Grundsatz 10, docs/ENTWICKLUNG.md): Startseite, Kiosk-API, Elternbereich am TV.
  Aktionen nur per POST mit Token (steht in der ausgelieferten Startseite) und ohne fremde Herkunft.
* **Eltern-Seite im Heimnetz** (nur wenn im Elternbereich eingeschaltet, Port einstellbar):
  liefert ausschließlich die Eltern-Seite und ``/api/eltern/*``. Ohne PIN-Sitzung geht nichts,
  die Kiosk-API ist dort nicht erreichbar.
"""
import base64
import binascii
import json
import logging
import mimetypes
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from . import hoerbuch as hoerbuch_mod, katalog as katalog_mod, kinderwelten as kinderwelten_mod, klaenge as klaenge_mod, sicherung as sicherung_mod, wetter as wetter_mod

log = logging.getLogger("fernsehfranzi.web")

JSON_MAX = 64 * 1024
BILD_MAX = 5 * 1024 * 1024
ZEICHNUNG = re.compile(r"[A-Za-z0-9._-]+\.png\Z")
KIOSK_URSPRUNG = "http://127.0.0.1:8765"


class Antwort(Exception):
    def __init__(self, code, daten):
        super().__init__(code)
        self.code, self.daten = code, daten


class Basis(BaseHTTPRequestHandler):
    hub = None              # kern.Hub
    web_ordner = None       # Ordner mit index.html, eltern.html, css/, js/
    zeichnungen = None
    lan = False             # True = Eltern-Seite im Heimnetz
    server_version = "FernsehFranzi"
    sys_version = ""

    # ------------------------------------------------------------ Antworten
    def sende(self, code, inhalt, typ, kopf=None):
        self.send_response(code)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(inhalt)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for name, wert in (kopf or {}).items():
            self.send_header(name, wert)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(inhalt)

    def json(self, daten, code=200):
        self.sende(code, json.dumps(daten, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def log_message(self, fmt, *args):
        pfad = urlsplit(self.path).path
        if args[1:2] == ("200",) and pfad in ("/api/status", "/api/apps", "/api/kiosk/auftraege",
                                              "/api/kiosk/ort", "/api/eingabe"):
            return
        log.info("%s %s", self.client_address[0], fmt % args)

    # ------------------------------------------------------------ Eingang
    def lies_json(self, grenze=JSON_MAX):
        try:
            laenge = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            laenge = 0
        if laenge > grenze:
            raise Antwort(413, {"ok": False, "fehler": "Zu groß."})
        if laenge == 0:
            return {}
        try:
            daten = json.loads(self.rfile.read(laenge).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise Antwort(400, {"ok": False, "fehler": "Kein gültiges JSON."})
        if not isinstance(daten, dict):
            raise Antwort(400, {"ok": False, "fehler": "JSON-Objekt erwartet."})
        return daten

    def eigener_ursprung(self):
        if self.lan:
            host = self.headers.get("Host", "")
            return {"http://" + host}
        return {KIOSK_URSPRUNG}

    def pruefe_post(self):
        """Fremde Herkunft (z. B. eine Webseite in Plex) wird immer abgewiesen."""
        origin = self.headers.get("Origin")
        if origin is not None and origin not in self.eigener_ursprung():
            log.warning("Fremde Herkunft abgewiesen: %s %s", origin, self.path)
            raise Antwort(403, {"ok": False, "fehler": "Nicht erlaubt."})
        if not self.lan and self.headers.get("X-FF-Token") != self.hub.token:
            raise Antwort(403, {"ok": False, "fehler": "Token fehlt."})

    def eltern_pflicht(self):
        if not self.hub.sitzung_gueltig(self.headers.get("X-FF-Eltern")):
            raise Antwort(401, {"ok": False, "fehler": "Bitte zuerst die PIN eingeben."})

    # ------------------------------------------------------------ Dateien
    def datei(self, relativ, ersetze_token=False):
        wurzel = os.path.realpath(self.web_ordner)
        pfad = os.path.realpath(os.path.join(wurzel, relativ))
        if not pfad.startswith(wurzel + os.sep) or not os.path.isfile(pfad):
            raise Antwort(404, {"ok": False, "fehler": "Nicht gefunden."})
        with open(pfad, "rb") as f:
            inhalt = f.read()
        if ersetze_token:
            inhalt = inhalt.replace(b"__FF_TOKEN__", self.hub.token.encode())
        typ = mimetypes.guess_type(pfad)[0] or "application/octet-stream"
        if typ.startswith("text/") or typ in ("application/javascript", "text/javascript"):
            typ += "; charset=utf-8"
        kopf = {"Content-Security-Policy":
                "default-src 'self'; img-src 'self' data: blob: https://i.ytimg.com https://i9.ytimg.com; "   # blob: 4.2 (Bildschirmfoto, Zeichnungen)
                "style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; media-src 'self' blob:; "
                # 3.5 YouTube-Bereich: nur der eingebettete Player (nocookie) und sein Steuer-Skript
                "script-src 'self' https://www.youtube.com https://s.ytimg.com; "
                "frame-src https://www.youtube-nocookie.com"} if pfad.endswith(".html") else {}
        self.sende(200, inhalt, typ, kopf)

    # ------------------------------------------------------------ Verteiler
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        self._verteile("GET")

    def do_POST(self):
        self._verteile("POST")

    def _verteile(self, methode):
        teile = urlsplit(self.path)
        pfad, abfrage = teile.path, parse_qs(teile.query)
        try:
            if methode == "POST":
                self.pruefe_post()
            ziel = self.routen().get((methode, pfad))
            if ziel is None:
                if methode == "GET" and not pfad.startswith("/api/"):
                    return self.statisch(pfad)
                raise Antwort(404, {"ok": False, "fehler": "Unbekannter Pfad."})
            ziel(abfrage)
        except (BrokenPipeError, ConnectionResetError):
            return              # Gegenstelle schon weg (z. B. Chromium beim Herunterfahren) - kein Fehler
        except Antwort as antwort:
            self.json(antwort.daten, antwort.code)
        except katalog_mod.KatalogFehler as fehler:
            self.json({"ok": False, "fehler": "Katalog ungültig", "details": fehler.fehler}, 400)
        except ValueError as fehler:
            self.json({"ok": False, "fehler": str(fehler)}, 400)
        except Exception:   # noqa: BLE001 - nie mit offenem Socket abstürzen, immer loggen
            log.exception("Fehler bei %s %s", methode, self.path)
            self.json({"ok": False, "fehler": "Interner Fehler."}, 500)

    # ------------------------------------------------------------ Eltern (beide Server)
    def eltern_routen(self):
        h = self.hub
        return {
            ("POST", "/api/eltern/anmelden"): lambda q: self._anmelden(),
            ("POST", "/api/eltern/abmelden"): lambda q: (h.abmelden(self.headers.get("X-FF-Eltern")),
                                                       self.json({"ok": True})),
            ("POST", "/api/eltern/pin"): lambda q: self._pin(),
            ("GET", "/api/eltern/daten"): lambda q: (self.eltern_pflicht(), self.json(h.eltern_daten())),
            ("POST", "/api/eltern/einstellungen"): lambda q: self._eltern(
                lambda d: h.einstellungen_aendern(d.get("einstellungen"))),
            ("POST", "/api/eltern/apps"): lambda q: self._eltern(lambda d: h.katalog_aendern(d.get("apps"))),
            ("POST", "/api/eltern/gutscheine"): lambda q: self._gutscheine_neu(),
            ("POST", "/api/eltern/sticker-vergeben"): lambda q: self._eltern(
                lambda d: h.familie.sticker(str(d.get("id", ""))) or None),
            ("POST", "/api/eltern/youtube-eintrag"): lambda q: self._youtube_eintrag(),
            ("GET", "/api/eltern/statistik"): lambda q: (self.eltern_pflicht(), self.json(h.statistik())),
            ("GET", "/api/eltern/bildschirm"): lambda q: self._bildschirm(),
            ("GET", "/api/eltern/sicherung"): lambda q: self._sicherung(),
            ("GET", "/api/eltern/scraper"): lambda q: (self.eltern_pflicht(), self.json(h.scraper_status())),
            ("POST", "/api/eltern/scraper"): lambda q: self._eltern(lambda d: h.scraper_starten()),
            ("GET", "/api/eltern/bluetooth"): lambda q: self._bluetooth_liste(),
            ("POST", "/api/eltern/bluetooth"): lambda q: self._eltern_ergebnis(
                lambda d: h.bluetooth_aktion(str(d.get("aktion", "")), str(d.get("mac", "")))),
            ("POST", "/api/eltern/sicherung-einspielen"): lambda q: self._sicherung_einspielen(),
            ("GET", "/api/eltern/wecker-toene"): lambda q: (self.eltern_pflicht(), self.json({"toene": h.wecker_toene()})),
            ("POST", "/api/eltern/gutschein-loeschen"): lambda q: self._eltern(
                lambda d: h.gutscheine.loeschen(str(d.get("code", "")))),
            # 5.0: Wetter-Ort suchen, Klassenkiste jetzt abrufen
            ("GET", "/api/eltern/wetter/orte"): lambda q: (self.eltern_pflicht(),
                                                            self.json({"orte": wetter_mod.orte_suchen(q.get("q", [""])[0])})),
            ("POST", "/api/eltern/schule/abrufen"): lambda q: self._eltern_ergebnis(lambda d: h.schule.jetzt_holen()),
            ("POST", "/api/eltern/ferien-eintragen"): lambda q: self._eltern_ergebnis(lambda d: h.ferien_eintragen(
                str(d.get("land", "")), d.get("feiertage") is not False, d.get("auto") is True)),
            ("POST", "/api/eltern/bonus"): lambda q: self._eltern(lambda d: h.bonus(_bonus_art(d))),
            ("POST", "/api/eltern/sperre"): lambda q: self._eltern(
                lambda d: h.entsperren() if d.get("frei") else h.sperren(d.get("text", ""))),
            # 5.2: Klang-Archiv - Datei zum Probehören (ohne Anmeldung: sie ist für alle gleich) und Probe am Fernseher
            ("GET", "/api/klang"): lambda q: self._klang(q.get("id", [""])[0]),
            ("GET", "/api/eltern/klaenge-eigen"): lambda q: (self.eltern_pflicht(), self.json({"klaenge": h.klaenge_eigen()})),
            ("POST", "/api/eltern/klang-test"): lambda q: self._eltern(lambda d: h.klang_testen(d.get("klang"))),
            ("POST", "/api/eltern/auszeit"): lambda q: self._eltern_ergebnis(lambda d: h.auszeit(d.get("minuten"))),   # 5.1
            ("POST", "/api/eltern/geraet"): lambda q: self._eltern(lambda d: h.system.geraet(
                _wahl(d.get("aktion"), ("neustart", "aus")))),
            ("POST", "/api/eltern/zeichnung-loeschen"): lambda q: self._eltern(self._zeichnung_loeschen),
            ("GET", "/api/eltern/zeichnungen"): lambda q: (self.eltern_pflicht(),
                                                         self.json({"zeichnungen": self._zeichnungen()})),
            ("POST", "/api/eltern/desktop"): lambda q: self._eltern(lambda d: self._desktop()),
            ("POST", "/api/eltern/nachricht"): lambda q: self._eltern(lambda d: h.eltern_nachricht(d.get("text"), d.get("von"))),
            ("POST", "/api/eltern/gute-nacht"): lambda q: self._eltern(lambda d: h.gute_nacht_starten()),
            ("POST", "/api/eltern/fernseher-aus"): lambda q: self._eltern(lambda d: h.cec_befehl("standby")),
            ("POST", "/api/eltern/ton"): lambda q: self._eltern(
                lambda d: h.ton_setzen(_wahl(str(d.get("ziel")), ("hdmi", "klinke", "kopfhoerer")))[0]),
            ("POST", "/api/eltern/lautstaerke"): lambda q: self._eltern(
                lambda d: h.lautstaerke(_wahl(str(d.get("richtung")), ("lauter", "leiser")))),
            ("POST", "/api/eltern/domains-erlauben"): lambda q: self._eltern(
                lambda d: h.domains_erlauben([str(x) for x in (d.get("hosts") or [])][:50])),
            ("POST", "/api/eltern/zeichnungen-gesehen"): lambda q: self._eltern(
                lambda d: h.familie.zeichnungen_gesehen(float(d.get("zeit", 0)))),
            ("GET", "/api/eltern/whitelist"): lambda q: self._whitelist(q),
        }

    def _anmelden(self):
        token, meldung = self.hub.eltern_anmelden(str(self.lies_json().get("pin", "")))
        if token is None:
            raise Antwort(403, {"ok": False, "fehler": meldung})
        self.json({"ok": True, "token": token})

    def _pin(self):
        daten = self.lies_json()
        ok, meldung = self.hub.pin_festlegen(str(daten.get("neu", "")), alt=daten.get("alt"),
                                             erster_start_am_tv=not self.lan)
        self.json({"ok": ok, "meldung": meldung}, 200 if ok else 403)

    def _bildschirm(self):
        self.eltern_pflicht()
        bild, grund = self.hub.bildschirmfoto()
        if bild is None:
            raise Antwort(503, {"ok": False, "fehler": grund})
        self.sende(200, bild, "image/jpeg")

    def _sicherung(self):
        self.eltern_pflicht()
        name = "fernsehfranzi-sicherung-%s.zip" % self.hub.uhr().strftime("%Y-%m-%d")
        self.sende(200, self.hub.sicherung_erstellen(), "application/zip",
                   {"Content-Disposition": 'attachment; filename="%s"' % name})

    def _sicherung_einspielen(self):
        self.eltern_pflicht()
        try:
            laenge = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            laenge = 0
        if not 0 < laenge <= sicherung_mod.ZIP_MAX:
            raise Antwort(413, {"ok": False, "fehler": "Die Datei ist leer oder zu groß."})
        self.json({"ok": True, "meldung": self.hub.sicherung_einspielen(self.rfile.read(laenge))})

    def _foto(self):
        d = self.lies_json(grenze=4_500_000)
        self.json({"ok": self.hub.foto_empfangen(int(d.get("nr", 0)), d.get("bild", ""), str(d.get("fehler", "")))})

    def _telegram_senden(self):
        d = self.lies_json()
        chat = d.get("chat")
        an = self.hub.telegram.senden(str(d.get("text", "")), chat if isinstance(chat, int) else None)
        self.json({"ok": True, "meldung": "Gesendet an %s ✔" % ", ".join(an)})

    def _startseite(self):
        d = self.lies_json()                        # nur einmal lesen (der Körper ist danach leer)
        self.hub.startseite_setzen(d)
        self.json({"ok": True})

    def _youtube_eintrag(self):
        self.eltern_pflicht()
        d = self.lies_json()
        self.json({"ok": True, "eintrag": self.hub.youtube_eintrag(d.get("kategorie"), d.get("link"))})

    def _gutscheine_neu(self):
        self.eltern_pflicht()
        d = self.lies_json()
        neu = self.hub.gutscheine.erstellen(str(d.get("art", "")), d.get("minuten"), d.get("anzahl", 1), self.hub.uhr())
        self.json({"ok": True, "neu": neu})

    def _eltern(self, aktion):
        self.eltern_pflicht()
        ergebnis = aktion(self.lies_json())
        self.json({"ok": ergebnis is not False})

    def _bluetooth_liste(self):
        """Antwortet Bluetooth nicht, zeigt die Eltern-Seite den Grund (kein Fehler-Status für die ganze Seite)."""
        self.eltern_pflicht()
        try:
            self.json({"geraete": self.hub.bluetooth_liste()})
        except (ValueError, OSError, AttributeError) as fehler:
            self.json({"geraete": [], "fehler": str(fehler) or "Bluetooth antwortet nicht."})

    def _eltern_ergebnis(self, aktion):
        """Wie _eltern, gibt aber das Ergebnis (dict) mit zurück."""
        self.eltern_pflicht()
        self.json(dict(aktion(self.lies_json()) or {}, ok=True))

    def _klang(self, kennung):
        """5.2/6.0: Klang zum Probehören - aus dem Archiv (erzeugt) oder ein eigener aus dem Klang-Ordner (durchgereicht)."""
        if klaenge_mod.eigen_pfad(kennung):
            return self._durchreichen(self.hub.klang_eigen_adresse(kennung), klaenge_mod.eigen_pfad(kennung))
        self.sende(200, klaenge_mod.erzeuge(kennung), "audio/wav", {"Cache-Control": "max-age=86400"})

    def _whitelist(self, abfrage):
        self.eltern_pflicht()
        format_ = (abfrage.get("format") or ["liste"])[0]
        text = self.hub.whitelist_export(_wahl(format_, ("liste", "pihole", "fritzbox")))
        self.sende(200, text.encode("utf-8"), "text/plain; charset=utf-8",
                   {"Content-Disposition": 'attachment; filename="fernsehfranzi-%s.txt"' % format_})

    def _desktop(self):
        """Linux-Desktop nur am Fernseher und nur mit PIN (kiosk.py wechselt, zurück nach 20 min)."""
        if self.lan:
            raise ValueError("Der Linux-Desktop lässt sich nur am Fernseher öffnen.")
        self.hub.auftrag("desktop_modus")

    def _zeichnungen(self):
        try:
            namen = [n for n in os.listdir(self.zeichnungen) if ZEICHNUNG.fullmatch(n)]
        except FileNotFoundError:
            return []
        namen.sort(key=lambda n: os.path.getmtime(os.path.join(self.zeichnungen, n)), reverse=True)
        return [{"datei": n, "url": "/zeichnung/" + n,
                 "zeit": os.path.getmtime(os.path.join(self.zeichnungen, n))} for n in namen[:200]]

    def _zeichnung_loeschen(self, daten):
        name = os.path.basename(str(daten.get("datei", "")))
        if not ZEICHNUNG.fullmatch(name):
            raise ValueError("Ungültiger Dateiname.")
        pfad = os.path.join(self.zeichnungen, name)
        if os.path.isfile(pfad):
            os.remove(pfad)
            log.info("Zeichnung gelöscht: %s", name)


class KioskHandler(Basis):
    def routen(self):
        h = self.hub
        r = {
            ("GET", "/api/status"): lambda q: self.json(h.status()),
            ("GET", "/api/apps"): lambda q: self.json({"apps": h.kacheln()}),
            ("POST", "/api/start"): lambda q: self._start(),
            ("POST", "/api/ort"): lambda q: (h.ort(self.lies_json().get("app")), self.json({"ok": True})),
            ("POST", "/api/zurueck"): lambda q: (h.zurueck(bool(self.lies_json().get("eltern"))),
                                                self.json({"ok": True})),
            ("POST", "/api/eingabe"): lambda q: self._eingabe(),
            ("POST", "/api/audio"): lambda q: self._ton(),
            ("POST", "/api/lautstaerke"): lambda q: self._lautstaerke(),
            ("GET", "/api/zeichnungen"): lambda q: self.json({"zeichnungen": self._zeichnungen()}),
            ("POST", "/api/zeichnung"): lambda q: self._zeichnung_speichern(),
            ("GET", "/api/kiosk/auftraege"): lambda q: self._auftraege(q),
            ("GET", "/api/bass"): lambda q: self.json({
                "songs": h.bass_songs(), "tagebuch": h.familie.bass_tagebuch(),
                "bibliotheken": [k for k, v in h.familie.einstellungen()["bass_bibliotheken"].items() if v]}),
            ("POST", "/api/bass/oeffne"): lambda q: self._bass(),
            ("POST", "/api/bass/bibliothek"): lambda q: self._ergebnis(
                *h.bass_bibliothek(str(self.lies_json().get("art", "")))),
            ("GET", "/api/sticker"): lambda q: self.json({"sticker": h.familie.album()}),
            ("POST", "/api/erfolg"): lambda q: self._erfolg(),
            ("GET", "/api/retro"): lambda q: self.json({"spiele": h.retro_spiele()}),
            ("POST", "/api/retro/start"): lambda q: self._retro(),
            ("POST", "/api/gutschein"): lambda q: self._ergebnis(*h.gutschein_einloesen(str(self.lies_json().get("code", "")))),
            ("POST", "/api/nacht"): lambda q: (h.nacht_wahl(str(self.lies_json().get("wahl", ""))),
                                               self.json({"ok": True})),
            ("POST", "/api/meldungen/gesehen"): lambda q: (h.familie.meldungen_gesehen(
                [int(n) for n in (self.lies_json().get("nummern") or [])][:50]), self.json({"ok": True})),
            ("POST", "/api/kiosk/ort"): lambda q: (h.kiosk_ort(str(self.lies_json().get("url", ""))),
                                                  self.json({"ok": True})),
            ("POST", "/api/kiosk/domains"): lambda q: self._domains(),
            ("POST", "/api/kiosk/foto"): lambda q: self._foto(),
            ("POST", "/api/kiosk/kk-anmeldung"): lambda q: self._kk_anmeldung(),
            ("GET", "/api/karaoke"): lambda q: self.json({"lieder": h.karaoke_liste()}),
            ("GET", "/api/karaoke/musik"): lambda q: self._karaoke_musik(q),
            # 3.3 Hörbücher: Liste und Dateien kommen über den Server (Chromium spricht nur mit 127.0.0.1)
            ("GET", "/api/hoerbuch/liste"): lambda q: self._hoerbuch_liste(q),
            ("GET", "/api/hoerbuch/datei"): lambda q: self._hoerbuch_datei(q),
            ("GET", "/api/hoerbuch/cover"): lambda q: self._hoerbuch_cover(q),
            ("POST", "/api/hoerbuch/stand"): lambda q: self._hoerbuch_stand(),
            ("GET", "/api/youtube"): lambda q: self.json(h.youtube_fuer_tv()),
            ("GET", "/api/startseite"): lambda q: self.json(dict(h.startseite_anzeige(), zuletzt=h.zuletzt())),
            # 5.0: Wetter, Schule (Klassenkiste), Kinderwelten (Familienfabrik), Kinder-News - alles nur lesen
            ("GET", "/api/wetter"): lambda q: self.json(h.wetter.fuer_tv()),
            ("GET", "/api/schule"): lambda q: self.json(h.schule.fuer_tv()),
            ("GET", "/api/kinderwelten"): lambda q: self.json(h.kinderwelten.uebersicht()),
            ("GET", "/api/kinderwelten/geschichten"): lambda q: self.json({"eintraege": h.kinderwelten.geschichten()}),
            ("GET", "/api/kinderwelten/geschichte"): lambda q: self.json(h.kinderwelten.geschichte(q.get("a", [""])[0])),
            ("GET", "/api/kinderwelten/buecher"): lambda q: self.json({"eintraege": h.kinderwelten.buecher()}),
            ("GET", "/api/kinderwelten/kapitel"): lambda q: self.json(h.kinderwelten.kapitel(
                q.get("a", [""])[0], _ganzzahl(q.get("n", ["1"])[0]))),
            ("GET", "/api/kinderwelten/news"): lambda q: self.json({"eintraege": h.kinderwelten.news()}),
            ("GET", "/api/kinderwelten/draussen"): lambda q: self.json({"eintraege": h.kinderwelten.draussen()}),
            ("GET", "/api/kinderwelten/beitrag"): lambda q: self.json(h.kinderwelten.beitrag(q.get("a", [""])[0])),
            ("GET", "/api/kinderwelten/raetsel"): lambda q: self.json(h.kinderwelten.raetsel(h.uhr().date())),
            ("GET", "/api/kinderwelten/bild"): lambda q: self._durchreichen(kinderwelten_mod.bild_adresse(q.get("u", [""])[0]),
                                                                            q.get("u", [""])[0], {"User-Agent": "FernsehFranzi"}),
            ("GET", "/api/news"): lambda q: self.json(h.news.liste()),
            ("POST", "/api/startseite"): lambda q: self._startseite(),
            ("GET", "/api/telegram"): lambda q: self.json(h.telegram.fuer_tv()),
            ("POST", "/api/telegram/senden"): lambda q: self._telegram_senden(),
            # 4.4: Speicherplatz, Album, Fotoalbum, Bilder teilen
            ("GET", "/api/speicher"): lambda q: self.json(h.speicher_status()),
            ("GET", "/api/album"): lambda q: self.json({"bilder": h.album_liste(), "speicher": h.speicher_status()}),
            ("POST", "/api/album/uebernehmen"): lambda q: self.json({"ok": True, "datei": h.album_uebernehmen(self.lies_json().get("datei"))}),
            ("POST", "/api/kind/loeschen"): lambda q: (lambda d: (h.kind_datei_loeschen(str(d.get("art")), str(d.get("name"))),
                                                                  self.json({"ok": True, "speicher": h.speicher_status()})))(self.lies_json()),
            ("GET", "/api/fotoalbum"): lambda q: self.json(dict(h.fotoalbum(), ordner=bool(h.fotoalbum()["ordner"]))),
            ("POST", "/api/fotoalbum"): lambda q: self.json(dict(h.fotoalbum_kind(self.lies_json()), ordner=bool(h.fotoalbum()["ordner"]))),
            ("GET", "/api/fotoalbum/liste"): lambda q: self._fotoalbum_liste(q),
            ("GET", "/api/fotoalbum/bild"): lambda q: self._durchreichen(h.fotoalbum_bild_adresse(q.get("pfad", [""])[0]), q.get("pfad", [""])[0]),
            ("POST", "/api/bild/teilen"): lambda q: (lambda d: self.json({"ok": True, "meldung": "Geschickt an %s ✔" % h.bild_teilen(
                str(d.get("art")), str(d.get("name")), d.get("chat") if isinstance(d.get("chat"), int) else None)}))(self.lies_json()),
            # 4.3: Spielraum - der Fernseher als Tafel (die Handys kommen über RaumHandler im Heimnetz)
            ("POST", "/api/raum/oeffnen"): lambda q: self.json(h.raum_oeffnen()),
            ("GET", "/api/raum/tv"): lambda q: self.json(h.raum_tv(_zahl_oder_none(q.get("striche_ab", [None])[0]))),
            ("POST", "/api/raum/tv-aktion"): lambda q: (h.raum_tv_aktion(self.lies_json()), self.json({"ok": True})),
            ("POST", "/api/raum/schliessen"): lambda q: (h.raum_schliessen(), self.json({"ok": True})),
            ("GET", "/api/inhalte"): lambda q: self.json(h.einstellungen.get("inhalte") or {"witze": [], "quiz": []}),
            ("GET", "/api/meldungen"): lambda q: self.json({"meldungen": list(reversed(h.familie.sichtbare_meldungen(20))),
                                                            "freunde_spaeter": h.familie.gezaehlt_gesperrt()}),
            ("POST", "/api/musik/suche"): lambda q: self._ergebnis(*h.musik_suche(self.lies_json().get("text"))),
            ("GET", "/api/wecker"): lambda q: self.json({"wecker": {k: v for k, v in h.wecker().items() if k != "toene"},
                                                         "toene": h.wecker_toene(), "laeuft": h.status()["wecker"]}),
            ("POST", "/api/wecker"): lambda q: (h.wecker_liste_setzen(self.lies_json().get("liste")), self.json({"ok": True})),
            ("GET", "/api/wecker/ton"): lambda q: self._durchreichen(h.wecker_ton_adresse(q.get("pfad", [""])[0]),
                                                                     q.get("pfad", [""])[0]),
            ("POST", "/api/wecker/aktion"): lambda q: (h.wecker_aktion(str(self.lies_json().get("aktion", ""))),
                                                       self.json({"ok": True})),
            ("POST", "/api/hoerbuch/schlaf-ende"): lambda q: (h.hoerbuch_schlaf_ende(), self.json({"ok": True})),
        }
        r.update(self.eltern_routen())
        return r

    def _fotoalbum_liste(self, q):
        try:
            self.json(self.hub.fotoalbum_ordner_liste(q.get("pfad", [""])[0]))
        except hoerbuch_mod.HoerbuchFehler as fehler:
            self.json({"ok": False, "fehler": str(fehler)}, 502)

    def album_bild(self, pfad):
        voll = self.hub.album_pfad(os.path.basename(pfad))
        if not voll:
            raise Antwort(404, {"ok": False})
        with open(voll, "rb") as f:
            self.sende(200, f.read(), "image/png" if voll.endswith(".png") else "image/jpeg")

    def medium(self, pfad):
        """4.4: Foto, Sprachnachricht, Musik oder Video von Telegram (nur Dateien aus <daten>/medien)."""
        voll = self.hub.telegram.medium_pfad(os.path.basename(pfad))
        if not voll:
            raise Antwort(404, {"ok": False, "fehler": "Diese Nachricht ist nicht mehr da (nach 7 Tagen gelöscht)."})
        typ = {"jpg": "image/jpeg", "ogg": "audio/ogg", "mp3": "audio/mpeg", "mp4": "video/mp4", "m4a": "audio/mp4"}[voll.rsplit(".", 1)[1]]
        with open(voll, "rb") as f:
            self.sende(200, f.read(), typ)

    def statisch(self, pfad):
        if pfad in ("/", "/index.html"):
            return self.datei("index.html", ersetze_token=True)
        if pfad.startswith("/medien/"):
            return self.medium(pfad)
        if pfad.startswith("/album/"):
            return self.album_bild(pfad)
        if pfad.startswith("/zeichnung/"):
            name = os.path.basename(pfad)
            voll = os.path.join(self.zeichnungen, name)
            if ZEICHNUNG.fullmatch(name) and os.path.isfile(voll):
                with open(voll, "rb") as f:
                    return self.sende(200, f.read(), "image/png")
            raise Antwort(404, {"ok": False})
        return self.datei(pfad.lstrip("/"))

    # ------------------------------------------------------------ Hörbücher
    def _hoerbuch_liste(self, q):
        try:
            self.json(self.hub.hoerbuch_liste(q.get("app", [""])[0], q.get("pfad", [""])[0]))
        except hoerbuch_mod.HoerbuchFehler as fehler:
            self.json({"ok": False, "fehler": str(fehler)}, 502)

    def _hoerbuch_cover(self, q):
        adresse = self.hub.hoerbuch_cover(q.get("app", [""])[0], q.get("pfad", [""])[0])
        if not adresse:
            raise Antwort(404, {"ok": False})
        self._durchreichen(adresse, adresse.split("?")[0])

    def _hoerbuch_stand(self):
        d = self.lies_json()
        self.json({"ok": True, "stand": self.hub.hoerbuch_stand(
            str(d.get("app", "")), str(d.get("ordner", "")), str(d.get("titel", "")), int(d.get("sekunde") or 0),
            d.get("spielt") is True, d.get("dunkel") is True)})

    def _hoerbuch_datei(self, q):
        """Audiodatei durchreichen - mit Range (Spulen, Weiterhören an der gemerkten Stelle)."""
        self._durchreichen(self.hub.hoerbuch_datei(q.get("app", [""])[0], q.get("pfad", [""])[0]), q.get("pfad", [""])[0])

    def _kk_anmeldung(self):
        if self.headers.get("X-FF-Token") != self.hub.token:
            raise Antwort(403, {"ok": False})
        d = self.lies_json(grenze=20_000)
        self.hub.kk_anmeldung_empfangen(int(d.get("nr") or 0), d.get("cookie", ""), d.get("fehler", ""))
        self.json({"ok": True})

    def _karaoke_musik(self, q):
        adresse, kopf = self.hub.karaoke_musik(q.get("id", [""])[0])
        self._durchreichen(adresse, "lied.mp3", kopf)

    def _durchreichen(self, adresse, pfad, zusatz=None):
        kopf = dict(zusatz or {})
        if self.headers.get("Range"):
            kopf["Range"] = self.headers["Range"]
        try:
            antwort = urllib.request.urlopen(urllib.request.Request(adresse, headers=kopf), timeout=20)
        except urllib.error.HTTPError as fehler:
            if fehler.code == 416:
                self.send_response(416)
                self.send_header("Content-Range", fehler.headers.get("Content-Range", "bytes */0"))
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            raise Antwort(502, {"ok": False, "fehler": "Hörbuch-Datei nicht erreichbar (%s)." % fehler.code})
        except OSError as fehler:
            raise Antwort(502, {"ok": False, "fehler": "Hörbuch-Datei nicht erreichbar (%s)." % fehler})
        with antwort:
            self.send_response(antwort.status)
            typ = antwort.headers.get("Content-Type", "")
            if not typ.startswith(("audio/", "image/")):
                typ = mimetypes.guess_type(pfad)[0] or "audio/mpeg"
            self.send_header("Content-Type", typ)
            for name in ("Content-Length", "Content-Range"):
                if antwort.headers.get(name):
                    self.send_header(name, antwort.headers[name])
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if self.command == "HEAD":
                return
            while True:
                block = antwort.read(64 * 1024)
                if not block:
                    break
                self.wfile.write(block)

    def _start(self):
        ok, meldung = self.hub.starte(str(self.lies_json().get("id", "")))
        self.json({"ok": ok, "meldung": meldung}, 200 if ok else 409)

    def _eingabe(self):
        tasten = self.lies_json().get("tasten") or []
        if not isinstance(tasten, list):
            raise ValueError("tasten muss eine Liste sein.")
        self.hub.eingabe([str(t)[:16] for t in tasten[:60]])
        self.json({"ok": True})

    def _domains(self):
        if self.headers.get("X-FF-Token") != self.hub.token:
            raise Antwort(403, {"ok": False})
        eintraege = self.lies_json().get("domains") or []
        if not isinstance(eintraege, list):
            raise ValueError("domains muss eine Liste sein.")
        self.hub.kiosk_domains([e for e in eintraege if isinstance(e, dict)])
        self.json({"ok": True})

    def _ergebnis(self, ok, meldung):
        self.json({"ok": ok, "meldung": meldung}, 200 if ok else 409)

    def _erfolg(self):
        daten = self.lies_json()
        neu = self.hub.familie.erfolg(str(daten.get("art", "")), daten.get("wert"))
        self.json({"ok": True, "neu": neu})

    def _retro(self):
        daten = self.lies_json()
        self._ergebnis(*self.hub.retro_starten(str(daten.get("system", "")), str(daten.get("rom", ""))))

    def _bass(self):
        daten = self.lies_json()
        ok, meldung = self.hub.bass_oeffne(daten.get("nr"), daten.get("art"))
        self.json({"ok": ok, "meldung": meldung}, 200 if ok else 409)

    def _lautstaerke(self):
        wert = self.hub.lautstaerke(str(self.lies_json().get("richtung", "")))
        self.json({"ok": wert is not None, "lautstaerke": wert}, 200 if wert is not None else 500)

    def _ton(self):
        ziel = self.lies_json().get("ziel")
        if ziel not in ("hdmi", "klinke", "kopfhoerer"):
            raise ValueError("ziel muss hdmi, klinke oder kopfhoerer sein.")
        ok, name = self.hub.ton_setzen(ziel)
        self.json({"ok": ok, "ziel": ziel, "name": name}, 200 if ok else 500)

    def _auftraege(self, abfrage):
        if self.headers.get("X-FF-Token") != self.hub.token:
            raise Antwort(403, {"ok": False})
        try:
            nach = int((abfrage.get("nach") or ["0"])[0])
            warten = min(25.0, float((abfrage.get("warten") or ["0"])[0]))
        except ValueError:
            raise Antwort(400, {"ok": False})
        auftraege, letzte = self.hub.auftraege_nach(nach, warten)
        self.json({"auftraege": auftraege, "letzte": letzte})

    def _zeichnung_speichern(self):
        daten = self.lies_json(BILD_MAX)
        bild = str(daten.get("bild", ""))
        praefix = "data:image/png;base64,"
        try:
            if not bild.startswith(praefix):
                raise ValueError
            png = base64.b64decode(bild[len(praefix):], validate=True)
            if not png.startswith(b"\x89PNG"):
                raise ValueError
        except (ValueError, binascii.Error):
            raise Antwort(400, {"ok": False, "fehler": "Das Bild konnte nicht gelesen werden."})
        self.hub.speicher_pruefen(len(png))            # 4.4: Speicherplatz des Kindes (die Eltern stellen ihn ein)
        os.makedirs(self.zeichnungen, exist_ok=True)
        stamm = datetime.now().strftime("zeichnung-%Y%m%d-%H%M%S")
        name, nr = stamm + ".png", 2
        while os.path.exists(os.path.join(self.zeichnungen, name)):
            name, nr = "%s-%d.png" % (stamm, nr), nr + 1
        with open(os.path.join(self.zeichnungen, name), "wb") as f:
            f.write(png)
        log.info("Zeichnung gespeichert: %s", name)
        self.hub.familie.zeichnung_gespeichert(len(self._zeichnungen()))
        self.json({"ok": True, "datei": name})


class LanHandler(Basis):
    lan = True

    def routen(self):
        return self.eltern_routen()

    def statisch(self, pfad):
        if pfad in ("/", "/eltern", "/eltern.html"):
            return self.datei("eltern.html")
        if pfad in ("/anleitung.pdf", "/kinder-anleitung.pdf", "/handbuch.pdf", "/kurzanleitung.pdf"):   # Anleitungen (enthalten nichts Privates)
            return self.datei(pfad.lstrip("/"))
        if pfad.startswith(("/css/", "/js/eltern", "/js/gemeinsam", "/fonts/")):
            return self.datei(pfad.lstrip("/"))
        if pfad.startswith("/medien/") and self.hub.sitzung_gueltig(self.headers.get("X-FF-Eltern")):
            return self.medium(pfad)
        if pfad.startswith("/album/") and self.hub.sitzung_gueltig(self.headers.get("X-FF-Eltern")):
            return self.album_bild(pfad)
        if pfad.startswith("/zeichnung/") and self.hub.sitzung_gueltig(self.headers.get("X-FF-Eltern")):
            name = os.path.basename(pfad)
            voll = os.path.join(self.zeichnungen, name)
            if ZEICHNUNG.fullmatch(name) and os.path.isfile(voll):
                with open(voll, "rb") as f:
                    return self.sende(200, f.read(), "image/png")
        raise Antwort(404, {"ok": False, "fehler": "Nicht gefunden."})


class RaumHandler(Basis):
    """4.3: Handys im Heimnetz - nur die Mitspiel-Seite und /api/raum/*, sonst nichts (keine Startseite, keine
    Eltern-Seite). Läuft nur, solange am Fernseher ein Spielraum offen ist und die Eltern Handy-Spiele erlaubt haben.
    Beitreten braucht den Schlüssel aus dem QR-Code (oder den Raumcode), danach weist sich jedes Handy mit seinem
    eigenen Geheimnis aus (X-FF-Spieler)."""
    lan = True

    def routen(self):
        h = self.hub
        geheim = lambda: self.headers.get("X-FF-Spieler", "")       # noqa: E731
        return {
            ("POST", "/api/raum/beitreten"): lambda q: self._beitreten(),
            ("GET", "/api/raum/zustand"): lambda q: self.json(h.raum_zustand(geheim())),
            ("POST", "/api/raum/aktion"): lambda q: self.json(h.raum_aktion(geheim(), self.lies_json(grenze=200_000))),
        }

    def _beitreten(self):
        d = self.lies_json()
        self.json(self.hub.raum_beitreten(d.get("schluessel"), d.get("name", ""), d.get("symbol", ""), bool(d.get("leicht"))))

    def statisch(self, pfad):
        if self.hub.raum is None:
            raise Antwort(404, {"ok": False, "fehler": "Gerade ist kein Spielraum offen."})
        if pfad in ("/", "/mitspielen"):
            return self.datei("mitspielen.html")
        if pfad in ("/js/mitspielen.js", "/css/mitspielen.css"):
            return self.datei(pfad.lstrip("/"))
        raise Antwort(404, {"ok": False, "fehler": "Nicht gefunden."})


def _zahl_oder_none(wert):
    try:
        return max(0, int(wert)) if wert is not None else None
    except ValueError:
        return None


def _bonus_art(daten):
    return _wahl(str(daten.get("art")), ("15", "30", "ohne_limit"))


def _ganzzahl(wert):
    try:
        return int(wert)
    except (TypeError, ValueError):
        raise ValueError("Bitte eine Zahl.") from None


def _wahl(wert, erlaubt):
    if wert not in erlaubt:
        raise ValueError("Erlaubt: %s" % ", ".join(erlaubt))
    return wert


def baue_server(handler, hub, web_ordner, zeichnungen, adresse):
    klasse = type(handler.__name__, (handler,), {"hub": hub, "web_ordner": web_ordner,
                                                 "zeichnungen": zeichnungen})
    server = ThreadingHTTPServer(adresse, klasse)
    server.daemon_threads = True
    return server
