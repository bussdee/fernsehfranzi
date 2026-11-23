"""Das Gehirn von FernsehFranzi 3.0 (docs/ENTWICKLUNG.md, „Wer besitzt was“).

``Hub`` hält Einstellungen, App-Katalog, Zeitkonto, PIN und Eltern-Sitzungen und entscheidet,
was gestartet werden darf. Es kennt keine HTTP-Details (siehe ``web.py``) und ruft das Gerät nur
über ``system`` auf - in Tests eine Attrappe, Uhr und Monotonuhr sind ebenfalls einsetzbar.

Besitzer (docs/ENTWICKLUNG.md, „Wer besitzt was“): RetroPie startet/stoppt nur der Hub (über ``system``), Chromium und
Desktop-Apps steuert ``kiosk.py`` - der Hub legt ihm dafür Aufträge in eine Warteschlange.
"""
import base64
import copy
import json
import logging
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from . import daten, design as design_mod, klaenge as klaenge_mod, kinderwelten as kinderwelten_mod, news as news_mod, schule as schule_mod, wetter as wetter_mod, ferien as ferien_mod, qr, raum as raum_mod, system as system_mod, sicherung as sicherung_mod, telegram as telegram_mod, familie as familie_mod, gutschein as gutschein_mod, hoerbuch, nutzung as nutzung_mod, katalog as katalog_mod, wecker as wecker_mod, youtube as youtube_mod, pin as pin_mod, whitelist, zeitkonto

log = logging.getLogger("fernsehfranzi.hub")

TICK_S = 5
KOPFHOERER_S = 5                       # 4.3: so oft wird nach einem Bluetooth-Kopfhörer geschaut (pactl, billig)
SPEICHERN_S = 30
LEERLAUF_S = 180            # ohne Eingabe zählt nichts
WARN_SPERRE_MIN = (1, 5, 10)   # Hinweise vor Beginn einer Sperrzeit (kleinste zuerst prüfen: nur einer je Takt)
INTERNET_LEERLAUF_S = 600   # im Internet nach 10 min ohne Eingabe zurück zur Startseite
SITZUNG_S = 15 * 60         # Eltern-Sitzung läuft nach 15 min ohne Aktion ab
START_URL = "http://127.0.0.1:8765/"

# Spielzimmer-Spiele gehören zum Katalog wie Apps (Zeitkonto: Malen zählt nicht).
SPIELZIMMER = [
    {"id": "spiel-snake", "name": "Snake", "zeit": "gaming"},
    {"id": "spiel-memory", "name": "Memory", "zeit": "gaming"},
    {"id": "spiel-drei", "name": "Drei Gewinnt", "zeit": "gaming"},
    {"id": "spiel-echo", "name": "Farben-Echo", "zeit": "gaming"},
    {"id": "spiel-malen", "name": "Malen", "zeit": "frei"},
    {"id": "spiel-witz", "name": "Witz", "zeit": "frei"},
    {"id": "spiel-bass", "name": "Musik-Akademie", "zeit": "frei", "lernen": True},   # 3.5 (vorher Bass-Ecke); Lernen zählt nicht
    {"id": "spiel-duell", "name": "Zu zweit", "zeit": "gaming"},                 # 3.1: Spiele für zwei
    {"id": "spiel-sticker", "name": "Sticker", "zeit": "frei"},                  # 3.1: Sticker-Album
    {"id": "spiel-lernen", "name": "Lernspiele", "zeit": "frei", "lernen": True},  # 3.2: Einmaleins, Uhr, Englisch
    {"id": "spiel-gutschein", "name": "Gutschein", "zeit": "frei", "sperr_erlaubt": "alle"},   # 3.5: immer einlösbar
    {"id": "spiel-wecker", "name": "Wecker", "zeit": "frei", "sperr_erlaubt": "alle"},         # 3.5: selbst einstellen
    {"id": "spiel-nachrichten", "name": "Nachrichten", "zeit": "frei", "sperr_erlaubt": "alle"},   # 3.5: alte und neue
    {"id": "spiel-gestalten", "name": "Gestalten", "zeit": "frei", "sperr_erlaubt": "alle"},       # 4.0: Startseite selbst gestalten
    {"id": "spiel-handys", "name": "Mit Handys spielen", "zeit": "gaming"},     # 4.3: Spielraum (nur wenn die Eltern es erlauben)
    {"id": "spiel-fotoalbum", "name": "Fotoalbum", "zeit": "frei"},             # 4.4: Bilder auswählen, Bildschirmschoner
    {"id": "spiel-karaoke", "name": "Karaoke", "zeit": "frei"},                 # 4.4: Lieder der Klassenkiste (wenn eingerichtet)
    # 5.0: Seiten mit Inhalten von außen (nur lesen) - erscheinen erst, wenn die Eltern sie eingeschaltet haben
    {"id": "spiel-wetter", "name": "Wetter", "zeit": "frei", "sperr_erlaubt": "alle"},
    {"id": "spiel-schule", "name": "Schule", "zeit": "frei", "sperr_erlaubt": "alle", "lernen": True},
    {"id": "spiel-kinderwelten", "name": "Geschichten & Rätsel", "zeit": "frei", "lernen": True},
    {"id": "spiel-news", "name": "Kinder-News", "zeit": "frei"},
]
HANDYSPIELE_PORT = 8767
KK_LIED = re.compile(r"[A-Za-z0-9_-]{1,64}")
KK_ANMELDEN = ("Dafür muss die Klassenkiste am Fernseher angemeldet sein: einmal die Kachel „Klassenkiste“ öffnen "
               "und anmelden, dann hier nochmal versuchen.")
SPEICHER_VORGABE_MB = 200                  # 4.4: Platz für Zeichnungen und Album des Kindes (die Eltern stellen ihn ein)
ALBUM_NAME = re.compile(r"a[0-9]{10}-[a-z0-9]{6}\.(jpg|png)\Z")
ZEICHNUNG_NAME = re.compile(r"zeichnung-[0-9]{8}-[0-9]{6}(-[0-9]+)?\.png\Z")
FOTO_AUSWAHL = re.compile(r"(album|ordner|zeichnung):[^\x00-\x1f]{1,400}\Z")
GUTE_NACHT_ID = "gute-nacht"        # 3.4: die Hörbuch-App "Gute Nacht" (Katalog), auch automatisch zur Nachtruhe
ALTE_RETRO_GRENZE = {"schultag": 45, "frei": 75}
BASS_ARTEN = ("video", "tab", "backing")
BASS_MAX = 200
EINSTELLUNGEN_FELDER = {"name": str, "untertitel": str, "geburtstage": list, "zeit": dict,
                        "whitelist": dict, "eltern_lan": dict, "ton": dict, "desktop": dict, "bass": list,
                        "familie": dict, "wecker": dict,
                        "youtube": dict, "inhalte": dict, "sticker_eigen": list,
                        "startseite": dict, "telegram": dict, "handyspiele": dict, "speicher": dict, "fotoalbum": dict,
                        "spielzimmer": dict, "design": dict, "wetter": dict, "schule": dict, "kinderwelten": dict,
                        "news": dict, "klaenge": dict}
ROMS = os.path.expanduser("~/RetroPie/roms")
GAMELISTS = [os.path.expanduser("~/.emulationstation/gamelists"),
             "/opt/retropie/configs/all/emulationstation/gamelists"]


def uhr_ist_sicher():
    """Pi 3 ohne Echtzeituhr: erst nach NTP-Abgleich (systemd-timesyncd) gilt die Uhr."""
    return os.path.exists("/run/systemd/timesync/synchronized")


C64_HINWEIS = "SHOW_MSG C64: A = Feuer   Y = Leertaste   Start = F1   LB = anderer Joystick"

class Hub:
    def __init__(self, ordner, system, version="unbekannt", uhr=datetime.now,
                 monoton=time.monotonic, uhr_sicher=uhr_ist_sicher):
        self.ordner, self.system, self.version = ordner, system, version
        self.uhr, self.monoton, self.uhr_sicher = uhr, monoton, uhr_sicher
        self.lock = threading.RLock()
        self.einstellungen = daten.lade_einstellungen(ordner)
        self.einstellungen.setdefault("eltern_lan", {"aktiv": False, "port": 8766})
        self.einstellungen.setdefault("desktop", {"befehle": []})
        self.einstellungen.setdefault("ton", {"ziel": None})
        self._retro_grenze_34 = self._uebernehme_34()
        if design_mod.migriere(self.einstellungen):              # 6.0: klare Farbnamen
            log.info("6.0: Farben der Startseite auf die neuen Namen umgestellt.")
            daten.schreibe_json(self._pfad("einstellungen.json"), self.einstellungen)
        self.katalog = self._lade_katalog()
        self.konto = zeitkonto.Zeitkonto(self._regeln(),
                                         daten.lies_json(self._pfad("zeitkonto.json"), {}) or {})
        self.pin_daten = daten.lies_json(self._pfad("pin.json"), {}) or {}
        self.sperre = pin_mod.Sperre(self.pin_daten.setdefault("sperre", {"fehler": 0, "gesperrt_bis": 0}))
        self.token = secrets.token_urlsafe(24)
        token_datei = self._pfad("kiosk-token")
        with open(os.open(token_datei, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as datei:
            datei.write(self.token)
        self.sitzungen = {}                       # eltern-token -> ablauf (monoton)
        self.aktuell = None                       # id der laufenden App/des Spiels
        self.letzte_eingabe = self.monoton()
        self.auftraege, self.auftrag_nr = [], 0   # für kiosk.py
        self.auftrag_neu = threading.Condition(self.lock)
        self._foto = {"nr": 0, "bild": None, "fehler": ""}   # 4.1: Bildschirmfoto für die Eltern-Seite
        self._foto_neu = threading.Condition(threading.Lock())
        self.prozess_neustart = lambda: os._exit(0)          # 4.1: nach dem Einspielen startet systemd den Server neu
        self.meldung = {"nr": 0, "text": ""}      # für die Startseite
        # Vorgabe HDMI (Fernseher, seit 3.2.2 - so wird das Gerät meist genutzt); Klinke z. B. für die Party-Anlage.
        # Die Wahl mit ROT/GRÜN bleibt gespeichert und wird bewacht (ton_wache)
        self.ton = {"ziel": self.einstellungen["ton"].get("ziel") or "hdmi", "nr": 0}
        self._ton_geprueft = self.monoton()
        # 4.3: Bluetooth-Kopfhörer - verbindet sich einer, wechselt der Ton dorthin (wie am Handy) und danach zurück.
        # Gespeichert bleibt die Wahl HDMI/Klinke; der Kopfhörer gilt nur, solange er verbunden ist.
        self.kopfhoerer = []                      # verbundene Bluetooth-Senken (zuletzt gesehen)
        self._kopfhoerer_geprueft = 0.0
        self.gesperrt = self.einstellungen.get("gesperrt")   # {"text": ...} oder None
        self._zuletzt_gespeichert = self.monoton()
        self._retropie_vorher = False
        self.cec = {"nr": 0, "befehl": None}      # für eingabe.py (z. B. Fernseher aus)
        self._hoerbuch_spielt_bis = 0             # 3.3: Hörbuch spielt (Nachtruhe wartet auf den Sleep-Timer)
        self._dunkel_bis = 0                      # 3.4: Einschlafbild ist zu sehen
        self.nachtruhe = False                    # 3.4: Fernseher ist für die Nacht aus - bis zur nächsten Taste still
        self._sperr_erledigt = set()              # "Name@Beginn" - Umschalten zu Beginn einer Sperrzeit nur einmal
        self.familie = familie_mod.Familie(self)
        self.gutscheine = gutschein_mod.Gutscheine(self._pfad("gutscheine.json"))
        self.nutzung = nutzung_mod.Nutzung(self._pfad("nutzung.json"), self.monoton)   # 4.0: Statistik
        self._cover_cache = {}
        self._yt_versucht = set()
        self.telegram = telegram_mod.Telegram(self)      # 4.0: Nachrichten der Familie per Telegram
        self.telegram.neu_starten()
        self._wecker_erledigt = set()
        self.wetter = wetter_mod.Wetter(self)                    # 5.0: Wetter und Regenzeiten
        self.schule = schule_mod.Schule(self)                    # 5.0: Klassenkiste (nur lesen)
        self.kinderwelten = kinderwelten_mod.Kinderwelten(self)  # 5.0: Familienfabrik (nur lesen)
        self.news = news_mod.News(self)                          # Kinder-News (nur RSS-Adressen der Eltern)
        self.wecker_laeuft = None                 # 3.5: {"nr", "ton", "laut", "seit", "vorher"} solange es klingelt
        self.raum = None                          # 4.3: offener Spielraum (Handy-Spiele) oder None
        self._kk = {"nr": 0, "cookie": None, "fehler": "", "zeit": 0.0}   # 4.4: Anmeldung der Klassenkiste (nur im Speicher)
        self._kk_neu = threading.Condition(threading.Lock())
        self._raum_lock = threading.RLock()
        self._schlummer = None                    # (Zeitpunkt, Wecker-Eintrag)
        self._sonder_vorher = False
        if self.uhr_sicher():
            self.ferien_auffrischen()             # 4.6: neue Schuljahre kommen mit dem Update

    # ------------------------------------------------------------ Hilfen
    def _pfad(self, name):
        return os.path.join(self.ordner, name)

    def _regeln(self):
        return zeitkonto.neue_regeln(self.einstellungen.get("zeit") or {})

    def _uebernehme_34(self):
        """3.3 -> 3.4, einmalig: Zeitfenster/Schlafenszeit -> Sperrzeiten, Plex-Gute-Nacht entfällt.
        Rückgabe: alte RetroPie-Grenze (für die Games-App) oder None, wenn schon übernommen."""
        if self.einstellungen.get("schema_zeit") == 34:
            return None
        familie = dict(self.einstellungen.get("familie") or {})
        schlaf = familie.pop("schlafenszeit", None)
        familie.pop("gute_nacht", None)
        zeit_alt = dict(self.einstellungen.get("zeit") or {})
        if "fenster" not in zeit_alt and "sperrzeiten" not in zeit_alt:
            zeit_alt["fenster"] = {"schultag": ["14:00", "19:30"], "frei": ["08:00", "20:00"]}   # alte Vorgabe
        zeit, retro = zeitkonto.alte_regeln_uebernehmen(zeit_alt, schlaf)
        familie["gute_nacht"] = {"automatisch": bool(schlaf and schlaf.get("aktiv"))}
        self.einstellungen.update(zeit=zeit, familie=familie, schema_zeit=34, zeit_pruefen=True)
        daten.schreibe_json(self._pfad("einstellungen.json"), self.einstellungen)
        log.info("3.4: Zeitregeln übernommen (Sperrzeiten %s).", ", ".join(s["name"] for s in zeit["sperrzeiten"]))
        return retro or dict(ALTE_RETRO_GRENZE)

    def _lade_katalog(self):
        eintraege = daten.lies_json(self._pfad("apps.json"))
        if eintraege is None:
            eintraege = copy.deepcopy(katalog_mod.VORGABE)
            daten.schreibe_json(self._pfad("apps.json"), eintraege)
        korrigiert = False
        for eintrag in eintraege if isinstance(eintraege, list) else []:
            neu = katalog_mod.ADRESS_KORREKTUREN.get(eintrag.get("start")) if isinstance(eintrag, dict) else None
            if neu:
                log.info("Katalog: Adresse von %s korrigiert -> %s", eintrag.get("id"), neu)
                eintrag["start"], korrigiert = neu, True
        # 3.3: "Hörspiele" (Plex-Adresse) wird zur Hörbuch-App mit eigenem Player. Eine Plex-Adresse ist kein
        # Freigabelink - sie fällt weg, die Eltern tragen den FileBrowser-Link ein.
        for eintrag in eintraege if isinstance(eintraege, list) else []:
            if isinstance(eintrag, dict) and eintrag.get("id") == "hoerspiele" and eintrag.get("typ") == "web":
                start = eintrag.get("start", "")
                eintrag.update(typ="hoerbuch", name="Hörbücher" if eintrag.get("name") == "Hörspiele" else eintrag.get("name"),
                               start=start if start and not hoerbuch.pruefe_freigabe(start) else "", domains=[])
                log.info("Katalog: Hörspiele -> Hörbuch-Player (Adresse %s).", "übernommen" if eintrag["start"] else "neu eintragen")
                korrigiert = True
        # 3.4: Zeitarten und Sperrzeiten; Hörbücher-Kachel wird zur Gute-Nacht-App
        if self._retro_grenze_34 is not None and isinstance(eintraege, list):
            hat_gute_nacht = any(isinstance(e, dict) and e.get("id") == GUTE_NACHT_ID for e in eintraege)
            for eintrag in eintraege:
                if not isinstance(eintrag, dict):
                    continue
                alt = eintrag.get("zeit")
                if alt == "nie":
                    eintrag["zeit"] = "frei"
                if "sperr_erlaubt" not in eintrag:
                    # bisher: was zählte, galt nur im Zeitfenster; alles andere ging auch vormittags
                    eintrag["sperr_erlaubt"] = [] if alt == "zaehlt" else ["Schule"]
                if eintrag.get("typ") == "konsole" and "limit_min" not in eintrag:
                    eintrag["limit_min"] = self._retro_grenze_34
                if eintrag.get("id") == "hoerspiele" and eintrag.get("typ") == "hoerbuch" and not hat_gute_nacht:
                    eintrag.update(id=GUTE_NACHT_ID, name="Gute Nacht", symbol="mond", farbe="#2b2f6b",
                                   zeit="frei", sperr_erlaubt="alle", reihenfolge=5)
                    hat_gute_nacht = True
                    stand = daten.lies_json(self._pfad("hoerbuch.json")) or {}
                    if "hoerspiele" in stand:
                        stand[GUTE_NACHT_ID] = stand.pop("hoerspiele")
                        daten.schreibe_json(self._pfad("hoerbuch.json"), stand)
            korrigiert = True
            log.info("3.4: Katalog übernommen (Zeitarten, Sperrzeiten, Gute Nacht).")
        # 3.2: neue Vorgabe-Apps einmal ergänzen
        ergaenzt = self.einstellungen.setdefault("katalog_ergaenzt", [])
        vorhanden = {e.get("id") for e in eintraege if isinstance(e, dict)} if isinstance(eintraege, list) else set()
        for app_id in katalog_mod.NACHTRAEGLICH:
            if app_id not in ergaenzt:
                ergaenzt.append(app_id)
                if app_id not in vorhanden and isinstance(eintraege, list):
                    eintraege.append(copy.deepcopy(next(e for e in katalog_mod.VORGABE if e["id"] == app_id)))
                    log.info("Katalog: %s ergänzt.", app_id)
                korrigiert = True
                daten.schreibe_json(self._pfad("einstellungen.json"), self.einstellungen)
        # 4.6: Retro-Spiele zählen zur Gaming-Zeit (einmal; die Eltern können es danach wieder ändern)
        if not self.einstellungen.get("gaming_46") and isinstance(eintraege, list):
            self.einstellungen["gaming_46"] = True
            for eintrag in eintraege:
                if isinstance(eintrag, dict) and eintrag.get("typ") == "konsole" and eintrag.get("zeit") == "zaehlt":
                    eintrag["zeit"] = "gaming"
                    log.info("4.6: %s zählt jetzt zur Gaming-Zeit.", eintrag.get("id"))
            korrigiert = True
            daten.schreibe_json(self._pfad("einstellungen.json"), self.einstellungen)
        if korrigiert:
            daten.schreibe_json(self._pfad("apps.json"), eintraege)
        try:
            return katalog_mod.pruefe_katalog(eintraege)
        except katalog_mod.KatalogFehler as fehler:
            log.error("apps.json ungültig, Vorgabe gilt:\n%s", fehler)
            return katalog_mod.pruefe_katalog(copy.deepcopy(katalog_mod.VORGABE))

    def app(self, app_id):
        for eintrag in self.katalog:
            if eintrag["id"] == app_id:
                return eintrag
        for eintrag in self.spielzimmer():
            if eintrag["id"] == app_id:
                return eintrag
        return None

    def spielzimmer(self):
        """4.6: eingebaute Spiele und Kacheln mit den Einstellungen der Eltern (an/aus, Zeitart, Limit, Sperrzeiten,
        Bewegungspause)."""
        eigen = self.einstellungen.get("spielzimmer") or {}
        return [dict(e, **eigen.get(e["id"], {})) for e in SPIELZIMMER]

    # ------------------------------------------------------------ Hörbücher (3.3)
    def _hoerbuch_app(self, app_id):
        app = self.app(app_id)
        if not app or app.get("typ") not in ("hoerbuch", "video"):
            raise ValueError("Diese Hörbuch-App gibt es nicht.")
        if not app.get("start"):
            raise ValueError("Die Hörbücher sind noch nicht eingerichtet. Bitte Mama oder Papa fragen.")
        return app

    def hoerbuch_laeuft(self):
        """Spielt gerade ein Hörbuch? (Der Player meldet sich alle 15 s, solange er spielt.)"""
        app = self.app(self.aktuell) if self.aktuell else None
        return bool(app) and app.get("typ") == "hoerbuch" and self.monoton() < self._hoerbuch_spielt_bis

    def hoerbuch_liste(self, app_id, pfad=""):
        app = self._hoerbuch_app(app_id)
        ergebnis = hoerbuch.liste(app["start"], pfad,
                                  endungen=hoerbuch.VIDEO if app["typ"] == "video" else hoerbuch.AUDIO)
        ergebnis["stand"] = (daten.lies_json(self._pfad("hoerbuch.json")) or {}).get(app_id)
        ergebnis["schlaf_max_min"] = int(self.familie.einstellungen()["hoerbuch"].get("schlaf_max_min", 60))
        return ergebnis

    def hoerbuch_cover(self, app_id, ordner):
        """4.0: Adresse des Cover-Bilds eines Ordners (eine Stunde zwischengespeichert) oder None."""
        app = self._hoerbuch_app(app_id)
        schluessel = (app_id, hoerbuch.sauberer_pfad(ordner))
        treffer = self._cover_cache.get(schluessel)
        if treffer is None or self.monoton() - treffer[1] > 3600:
            try:
                treffer = (hoerbuch.cover_in(app["start"], ordner), self.monoton())
            except hoerbuch.HoerbuchFehler:
                treffer = (None, self.monoton())
            self._cover_cache[schluessel] = treffer
        return hoerbuch.bild_adresse(app["start"], treffer[0]) if treffer[0] else None

    def hoerbuch_datei(self, app_id, pfad):
        app = self._hoerbuch_app(app_id)
        return hoerbuch.datei_adresse(app["start"], pfad, hoerbuch.VIDEO if app["typ"] == "video" else hoerbuch.AUDIO)

    def still(self):
        """Gute-Nacht-Modus: Hörbuch spielt, Einschlafbild oder Fernseher für die Nacht aus - dann keine Töne
        (kein Gong, kein Countdown), Erinnerungen warten bis morgen (Entscheidung 9.3)."""
        return self.nachtruhe or self.hoerbuch_laeuft() or self.monoton() < self._dunkel_bis

    def hoerbuch_stand(self, app_id, ordner, titel, sekunde, spielt=False, dunkel=False):
        """Wo das Kind aufgehört hat (je App): beim nächsten Öffnen „Weiterhören“."""
        self._hoerbuch_app(app_id)
        self._hoerbuch_spielt_bis = self.monoton() + 60 if spielt else 0
        self._dunkel_bis = self.monoton() + 60 if dunkel else 0
        if not titel:
            return None
        stand = {"ordner": hoerbuch.sauberer_pfad(ordner), "titel": hoerbuch.sauberer_pfad(titel),
                 "sekunde": max(0, int(sekunde)), "zeit": self.uhr().isoformat(timespec="seconds")}
        with self.lock:
            alle = daten.lies_json(self._pfad("hoerbuch.json")) or {}
            alle[app_id] = stand
            daten.schreibe_json(self._pfad("hoerbuch.json"), alle)
        return stand

    def hoerbuch_schlaf_ende(self):
        """Sleep-Timer abgelaufen: Wiedergabe ist aus, Bild ist schwarz - jetzt den Fernseher ausschalten."""
        # Kein zurueck(): die Startseite wäre hell, falls der Fernseher CEC ignoriert. Das Bild bleibt schwarz.
        log.info("Hörbuch: Sleep-Timer abgelaufen - Fernseher aus.")
        self._hoerbuch_spielt_bis = 0
        self.nachtruhe = True
        self.cec_befehl("standby")

    # ------------------------------------------------------------ Wecker (3.5)
    def wecker(self):
        return wecker_mod.einstellungen(self.einstellungen.get("wecker"))

    def wecker_toene(self):
        """Wecktöne aus dem FileBrowser-Ordner (nur die Dateien in der obersten Ebene)."""
        link = self.wecker()["toene"]
        if not link:
            return []
        try:
            return [t["pfad"] for t in hoerbuch.liste(link, "")["titel"]]
        except hoerbuch.HoerbuchFehler as fehler:
            log.warning("Wecktöne: %s", fehler)
            return []

    def wecker_ton_adresse(self, pfad):
        link = self.wecker()["toene"]
        if not link:
            raise ValueError("Es ist kein Weckton-Ordner eingerichtet.")
        return hoerbuch.datei_adresse(link, pfad)

    def wecker_liste_setzen(self, liste):
        """Vom Kind am Fernseher: nur die Wecker selbst - die Grenzen der Eltern gelten (frühestens, Lautstärke)."""
        w = self.wecker()
        w["liste"] = liste
        self.einstellungen_aendern({"wecker": w})

    def _wecker_takt(self, jetzt):
        w = self.wecker()
        faellig = wecker_mod.faellig(w, jetzt, self._wecker_erledigt)
        if self._schlummer and jetzt >= self._schlummer[0]:
            faellig.append(self._schlummer[1])
            self._schlummer = None
        if faellig and not self.wecker_laeuft:
            self._klingeln(w, faellig[0], jetzt)
        for eintrag, minuten in wecker_mod.sonnenaufgang_faellig(w, jetzt, self._wecker_erledigt):
            log.info("Wecker %s: Sonnenaufgang (%d min).", eintrag["zeit"], minuten)
            self.nachtruhe, self._dunkel_bis, self._hoerbuch_spielt_bis = False, 0, 0
            self.cec_befehl("an")
            self.auftrag("sonne", minuten=minuten)
        if len(self._wecker_erledigt) > 50:
            self._wecker_erledigt = set(list(self._wecker_erledigt)[-20:])

    def _klingeln(self, w, eintrag, jetzt):
        log.info("Wecker %s klingelt.", eintrag["zeit"])
        self.nachtruhe, self._dunkel_bis, self._hoerbuch_spielt_bis = False, 0, 0     # morgens: wach
        laeuft, _ = self.system.retropie_zustand()
        if laeuft:
            self._retro_beenden()
        self.cec_befehl("an")
        laut = wecker_mod.lautstaerke(w, eintrag)
        vorher = self.system.lautstaerke_setzen(laut)
        self.wecker_laeuft = {"nr": eintrag["nr"], "zeit": eintrag["zeit"], "ton": eintrag.get("ton") or "",
                              "laut": laut, "seit": jetzt.isoformat(timespec="seconds"), "vorher": vorher}
        self.auftrag("wecker")
        with self.lock:
            self.aktuell = None

    def wecker_aktion(self, aktion):
        """Vom Weckbildschirm: schlummern (5 min) oder aus."""
        if aktion not in ("schlummern", "aus"):
            raise ValueError("aktion muss schlummern oder aus sein.")
        laeuft = self.wecker_laeuft
        if not laeuft:
            return
        self.wecker_laeuft = None
        if laeuft.get("vorher") is not None:
            self.system.lautstaerke_setzen(laeuft["vorher"])
        if aktion == "aus":
            self.telegram.melde_eltern("wecker", "⏰ Der Wecker (%s Uhr) wurde ausgeschaltet." % laeuft.get("zeit", "?"))
        if aktion == "schlummern":
            eintrag = next((e for e in self.wecker()["liste"] if e["nr"] == laeuft["nr"]), None)
            if eintrag:
                self._schlummer = (self.uhr() + timedelta(minutes=wecker_mod.SCHLUMMERN_MIN), eintrag)
        log.info("Wecker: %s.", aktion)

    # ------------------------------------------------------------ Musik-Akademie: Song-Suche (3.5)
    def musik_suche(self, text):
        from urllib.parse import quote_plus
        text = " ".join(str(text or "").split())[:60]
        if len(text) < 2:
            raise ValueError("Bitte mindestens zwei Buchstaben.")
        self.auftrag("oeffne", url=UG_SUCHE % quote_plus(text), app="spiel-bass")
        with self.lock:
            self.aktuell = "spiel-bass"
            self.letzte_eingabe = self.monoton()
        log.info("Musik-Akademie: Suche %r", text)
        return True, "Ich suche „%s“ …" % text

    # ------------------------------------------------------------ YouTube-Bereich (3.5)
    def youtube(self):
        return copy.deepcopy(self.einstellungen.get("youtube") or {"kategorien": []})

    def youtube_fuer_tv(self):
        """Für den Fernseher: Playlisten ohne Videoliste (vor 4.0.1 gespeichert) einmal nachträglich auslesen."""
        y = self.youtube()
        geaendert = False
        for k in y["kategorien"]:
            for e in k["eintraege"]:
                if e["art"] == "playlist" and not e.get("videos") and e["id"] not in self._yt_versucht:
                    self._yt_versucht.add(e["id"])            # je Playlist nur einmal pro Start versuchen
                    try:
                        e["videos"] = youtube_mod.playlist_videos(e["id"])
                        geaendert = geaendert or bool(e["videos"])
                    except ValueError as fehler:
                        log.warning("YouTube-Playlist %s: %s", e["id"], fehler)
        if geaendert:
            self.einstellungen_aendern({"youtube": y})
        # 6.0: ausgeschaltete Kategorien sieht das Kind nicht (sie bleiben gespeichert)
        return dict(y, kategorien=[k for k in y["kategorien"] if k.get("aktiv", True)])

    def youtube_eintrag(self, kategorie, link):
        """Eltern: Link einfügen -> Video/Playlist mit Titel in die Kategorie (wird angelegt, wenn neu)."""
        art, kennung = youtube_mod.link_lesen(link)
        titel, bild = youtube_mod.titel_holen(art, kennung)
        y = self.youtube()
        name = str(kategorie or "").strip() or "Videos"
        kat = next((k for k in y["kategorien"] if k["name"] == name), None)
        if kat is None:
            kat = {"name": name, "eintraege": []}
            y["kategorien"].append(kat)
        if any(e["id"] == kennung for e in kat["eintraege"]):
            raise ValueError("Ist schon in „%s“." % name)
        eintrag = {"art": art, "id": kennung, "titel": titel}
        if bild:
            eintrag["bild"] = bild
        if art == "playlist":
            eintrag["videos"] = youtube_mod.playlist_videos(kennung)
            if not eintrag["videos"]:
                raise ValueError("In der Playlist sind keine Videos zu finden (privat oder leer?).")
        kat["eintraege"].append(eintrag)
        self.einstellungen_aendern({"youtube": y})
        return eintrag

    # ------------------------------------------------------------ Gutscheine (3.5)
    def gutschein_einloesen(self, code):
        """Rückgabe (ok, Meldung fürs Kind)."""
        jetzt = self.uhr()
        with self.lock:
            eintrag, fehler = self.gutscheine.pruefen(code, jetzt.timestamp())
            if eintrag is None:
                log.info("Gutschein abgewiesen: %s", fehler)
                return False, fehler
            if eintrag["art"] == "normal":
                if zeitkonto.aktive_sperrzeiten(jetzt, self.konto.regeln) and not self.konto.sonder_aktiv(jetzt):
                    return False, "Diesen Gutschein kannst du einlösen, wenn gerade keine Pause ist."
                self.konto.bonus_frei(jetzt, eintrag["minuten"])
                text = "Gutschein eingelöst: %d Minuten mehr Spielzeit!" % eintrag["minuten"]
            else:
                self.konto.sonder_frei(jetzt, eintrag["minuten"])
                text = "Besonderer Gutschein: %d Minuten geht alles!" % eintrag["minuten"]
            self.gutscheine.einloesen(eintrag, jetzt)
            self.speichere_konto()
        log.info("Gutschein %s eingelöst (%s, %d min).", eintrag["code"], eintrag["art"], eintrag["minuten"])
        self.telegram.melde_eltern("gutschein", "🎟️ " + text)
        self.melde(text)
        return True, text

    def _sonder_ende(self, jetzt, laeuft):
        """Besonderer Gutschein abgelaufen: eine App, die jetzt gesperrt wäre, wird beendet."""
        aktiv = self.konto.sonder_aktiv(jetzt)
        if self._sonder_vorher and not aktiv:
            app = self.app("games" if laeuft else self.aktuell) if (laeuft or self.aktuell) else None
            if app is not None and self.konto.sperre_fuer(app, jetzt):
                log.info("Gutschein abgelaufen - %s ist gesperrt und wird beendet.", app["id"])
                if laeuft:
                    self._retro_beenden()
                self.zurueck()
                self.melde("Der Gutschein ist abgelaufen.")
        self._sonder_vorher = aktiv

    # ------------------------------------------------------------ Gute Nacht und Nachtruhe (3.4)
    def gute_nacht_starten(self, automatisch=False):
        """Öffnet den Gute-Nacht-Player auf dem Fernseher (Eltern-Seite, Elternbereich, Beginn der Nachtruhe)."""
        app = self._hoerbuch_app(GUTE_NACHT_ID)          # wirft ValueError, wenn nicht eingerichtet
        laeuft, _ = self.system.retropie_zustand()
        if laeuft:
            self._retro_beenden()
        self.auftrag("dimmen", stufe=0)
        self.auftrag("gute_nacht", automatisch=bool(automatisch))
        with self.lock:
            self.aktuell = app["id"]
            self.letzte_eingabe = self.monoton()
        log.info("Gute Nacht gestartet (%s).", "automatisch" if automatisch else "von Hand")
        return True

    def nacht_wahl(self, wahl):
        """Countdown zu Beginn der Nachtruhe: aus (Fernseher aus), an (Startseite) oder gute-nacht."""
        if wahl not in ("aus", "an", "gute-nacht"):
            raise ValueError("wahl muss aus, an oder gute-nacht sein.")
        log.info("Nachtruhe: %s", wahl)
        if wahl == "aus":
            self.nachtruhe = True
            self.cec_befehl("standby")
        elif wahl == "gute-nacht":
            self.gute_nacht_starten()

    def _retro_beenden(self):
        if self.system.retroarch_laeuft():
            self.system.retroarch("SAVE_STATE")      # Spielstand sichern, dann beenden
            time.sleep(2)
            self.system.retroarch("QUIT")
            time.sleep(2)
        self.system.retropie("stop")
        self.system.spiel("stop")

    def _sperrzeiten(self, jetzt, app, laeuft):
        """Sperrzeiten während der Nutzung: vorher 10/5/1 min Hinweis, zu Beginn nicht erlaubte App beenden;
        zu Beginn der Nachtruhe Gute Nacht (automatisch) oder der Countdown mit drei Knöpfen."""
        regeln = self.konto.regeln
        if app and not self.still():
            for s, beginn in zeitkonto.naechste_sperrzeiten(jetzt, regeln, 10 * 60 + 30):
                if zeitkonto.erlaubt_in(app, s):
                    continue
                rest = (beginn - jetzt).total_seconds()
                for minuten in WARN_SPERRE_MIN:
                    schluessel = "warn:%s@%s:%d" % (s["name"], beginn.isoformat(), minuten)
                    if rest <= minuten * 60 and schluessel not in self._sperr_erledigt:
                        self._sperr_erledigt.add(schluessel)
                        self._warne("In %d %s: %s." % (minuten, "Minute" if minuten == 1 else "Minuten",
                                                       "Nachtruhe" if s.get("nacht") else s["name"]), laeuft)
                        break
        for s, beginn in zeitkonto.begonnene_sperrzeiten(jetzt, regeln, 5 * 60):
            schluessel = "%s@%s" % (s["name"], beginn.isoformat())
            if schluessel in self._sperr_erledigt:
                continue
            self._sperr_erledigt.add(schluessel)
            erlaubt = app is not None and zeitkonto.erlaubt_in(app, s)
            if app is not None and not erlaubt:
                log.info("Sperrzeit %s beginnt - %s wird beendet.", s["name"], app.get("id"))
                if laeuft:
                    self._retro_beenden()
                self.zurueck()
            if not s.get("nacht"):
                if app is not None and not erlaubt:
                    self.melde("Jetzt ist %s – die App macht Pause." % s["name"])
                continue
            if erlaubt or self.still():
                continue                                       # z. B. Gute Nacht läuft schon
            gute_nacht = self.app(GUTE_NACHT_ID)
            if self.familie.einstellungen()["gute_nacht"].get("automatisch") and gute_nacht and gute_nacht.get("start"):
                self.gute_nacht_starten(automatisch=True)
            else:
                self.auftrag("nacht")                          # Startseite: 15-s-Countdown mit drei Knöpfen
        if len(self._sperr_erledigt) > 200:
            self._sperr_erledigt = set(list(self._sperr_erledigt)[-100:])

    def cec_befehl(self, befehl):
        """eingabe.py führt ihn aus (holt ihn mit dem Status ab): 'standby' = Fernseher aus."""
        with self.lock:
            self.cec = {"nr": self.cec["nr"] + 1, "befehl": befehl}
        log.info("CEC-Befehl: %s", befehl)

    def bonus_minuten(self, minuten, text):
        with self.lock:
            self.konto.bonus_frei(self.uhr(), minuten)
            self.speichere_konto()
        self.melde(text)

    def melde(self, text):
        with self.lock:
            self.meldung = {"nr": self.meldung["nr"] + 1, "text": text}
        log.info("Meldung: %s", text)

    def auftrag(self, art, **werte):
        with self.lock:
            self.auftrag_nr += 1
            self.auftraege.append(dict(werte, nr=self.auftrag_nr, art=art))
            self.auftraege = self.auftraege[-50:]
            self.auftrag_neu.notify_all()

    # ------------------------------------------------------------ 4.1: Bildschirmfoto (Eltern-Seite)
    FOTO_MAX = 3_000_000

    def bildschirmfoto(self, warten_s=8.0):
        """JPEG des Fernsehbilds über kiosk.py (DevTools). Rückgabe (bytes, "") oder (None, Grund).
        Nur das Chromium-Bild - läuft RetroPie, gibt es kein Foto. Danach erscheint am Fernseher kurz „📷“."""
        if self.system.retropie_zustand()[0]:
            return None, "Gerade läuft ein Retro-Spiel – davon kann der Pi kein Foto machen."
        with self._foto_neu:
            self._foto = {"nr": self._foto["nr"] + 1, "bild": None, "fehler": ""}
            nr = self._foto["nr"]
        self.auftrag("foto", foto=nr)
        ende = time.monotonic() + warten_s
        with self._foto_neu:
            while self._foto["nr"] == nr and self._foto["bild"] is None and not self._foto["fehler"]:
                rest = ende - time.monotonic()
                if rest <= 0:
                    return None, "Der Fernseher antwortet gerade nicht."
                self._foto_neu.wait(rest)
            bild, fehler = self._foto["bild"], self._foto["fehler"]
        if bild is None:
            return None, fehler or "Kein Bild."
        text = "📷 Mama oder Papa haben kurz auf den Fernseher geschaut."
        self.melde(text)
        self.auftrag("hinweis", text=text)
        return bild, ""

    def foto_empfangen(self, nr, bild_b64="", fehler=""):
        """kiosk.py liefert das Foto (base64-JPEG) oder einen Grund."""
        bild = None
        if not fehler:
            try:
                bild = base64.b64decode(str(bild_b64), validate=True)
            except (ValueError, TypeError):
                fehler = "Das Bild war kaputt."
            else:
                if not bild.startswith(b"\xff\xd8") or len(bild) > self.FOTO_MAX:
                    bild, fehler = None, "Das Bild war kaputt."
        with self._foto_neu:
            if nr != self._foto["nr"]:
                return False                      # zu spät - die Eltern-Seite hat schon aufgegeben
            self._foto.update(bild=bild, fehler=str(fehler)[:200])
            self._foto_neu.notify_all()
        return True

    def auftraege_nach(self, nr, warten_s=0.0):
        """Aufträge mit Nummer > nr (kiosk.py fragt so ab, wartet höchstens warten_s)."""
        with self.lock:
            if warten_s and not any(a["nr"] > nr for a in self.auftraege):
                self.auftrag_neu.wait(timeout=warten_s)
            return [a for a in self.auftraege if a["nr"] > nr], self.auftrag_nr

    # ------------------------------------------------------------ Status und Kacheln
    def status(self):
        jetzt = self.uhr()
        laeuft, marke = self.system.retropie_zustand()
        with self.lock:
            rest = self.konto.rest_s(jetzt)
            return {
                "version": self.version, "uhr_sicher": bool(self.uhr_sicher()),
                "name": self.einstellungen.get("name", ""),
                "untertitel": self.einstellungen.get("untertitel", ""),
                "aktuell": "games" if laeuft else self.aktuell,
                "aktuell_typ": "konsole" if laeuft else
                ("web" if self.aktuell == "internet" else (self.app(self.aktuell) or {}).get("typ", "spiel")
                 if self.aktuell else None),
                "running": laeuft, "retropie_start": marke,
                "rest_min": None if rest is None else rest // 60,
                "budget_min": None if rest is None else self.konto.budget_s(jetzt) // 60,     # 6.0: für den Balken
                "ton": self.ton["ziel"], "ton_nummer": self.ton["nr"], "kopfhoerer": bool(self.kopfhoerer),
                "meldung": dict(self.meldung), "gesperrt": self.gesperrt_anzeige(jetzt), "wartung": self.wartung(),
                "pin_gesetzt": bool(self.pin_daten.get("hash")),
                "cec": dict(self.cec), "pause": self.familie.in_pause(),
                "pause_rest": self.familie.pause_rest(jetzt),
                "still": self.still(), "nachtruhe": self.nachtruhe,
                "wecker": {k: v for k, v in self.wecker_laeuft.items() if k != "vorher"} if self.wecker_laeuft else None,
                "freunde_spaeter": self.familie.gezaehlt_gesperrt(),
                "meldungen": [{k: m.get(k) for k in ("nr", "text", "quelle", "zeit", "symbol", "medium")}
                              for m in self.familie.offene_meldungen()],
            }

    def kacheln(self):
        jetzt = self.uhr()
        sicher = bool(self.uhr_sicher())
        with self.lock:
            ergebnis = []
            handyspiele = bool((self.einstellungen.get("handyspiele") or {}).get("aktiv"))
            fotoalbum = bool((self.einstellungen.get("fotoalbum") or {}).get("erlaubt"))
            karaoke = bool(self.klassenkiste_basis())
            bedingt = {"spiel-handys": handyspiele, "spiel-fotoalbum": fotoalbum, "spiel-karaoke": karaoke,   # 5.0: Seiten von außen
                       "spiel-wetter": self.wetter.einstellungen()["aktiv"], "spiel-schule": self.schule.bereit(),
                       "spiel-kinderwelten": self.kinderwelten.einstellungen()["aktiv"], "spiel-news": self.news.aktiv()}
            for kachel in katalog_mod.kacheln(self.katalog) + [
                    dict(e, typ="spiel", eingerichtet=True) for e in self.spielzimmer()
                    if e.get("aktiv", True) and bedingt.get(e["id"], True)]:
                app = self.app(kachel["id"])
                ok, grund, art = self.konto.darf_starten(app, jetzt, uhr_sicher=sicher)
                if self.gesperrt:
                    ok, grund, art = False, self.gesperrt.get("text") or "Der Fernseher ist gerade gesperrt.", "eltern"
                ergebnis.append(dict(kachel, frei=ok, grund=grund, sperre=art, zaehlt=zeitkonto.zaehlt(app)))
            return ergebnis

    # ------------------------------------------------------------ Starten und Zurück
    def starte(self, app_id):
        """Rückgabe (ok, kindgerechte Meldung)."""
        app = self.app(app_id)
        if app is None:
            return False, "Diese App gibt es nicht."
        if app.get("aktiv", True) is False:
            return False, "%s ist gerade ausgeschaltet. Bitte Mama oder Papa fragen." % app["name"]
        if (self.wartung() or {}).get("rest_s"):
            return False, "Der Fernseher wird gerade aktualisiert. Bitte warten."
        if self.gesperrt:
            return False, self.gesperrt.get("text") or "Der Fernseher ist gerade gesperrt."
        ok, grund, _ = self.konto.darf_starten(app, self.uhr(), uhr_sicher=bool(self.uhr_sicher()))
        if not ok:
            return False, grund
        typ, start = app.get("typ"), app.get("start", "")
        if typ in ("web", "desktop", "konsole", "hoerbuch", "video") and not start:
            return False, "%s ist noch nicht eingerichtet. Bitte Mama oder Papa fragen." % app["name"]
        if typ == "konsole":
            if not self.system.retropie("start"):
                return False, "RetroPie startet gerade nicht. Bitte Mama oder Papa holen."
        elif typ == "web":
            self.auftrag("oeffne", url=start, app=app_id, profil=app.get("plex_profil", ""))
        elif typ == "desktop":
            self.auftrag("desktop", befehl=start, app=app_id)
        with self.lock:
            self.aktuell = app_id
            self.letzte_eingabe = self.monoton()
        self._zuletzt_merken(app_id)
        log.info("Start: %s", app_id)
        return True, "%s startet ..." % app["name"]

    # ------------------------------------------------------------ 6.0: „Weiter, wo du warst“ auf der Startseite
    ZULETZT_MAX = 8
    OHNE_ZULETZT = ("spiel-gestalten", "spiel-gutschein", "spiel-wecker", "spiel-nachrichten")

    def _zuletzt_merken(self, app_id):
        if app_id in self.OHNE_ZULETZT:
            return
        pfad = self._pfad("zuletzt.json")
        liste = [x for x in (daten.lies_json(pfad, []) or []) if isinstance(x, str) and x != app_id]
        daten.schreibe_json(pfad, ([app_id] + liste)[:self.ZULETZT_MAX])

    def zuletzt(self):
        """Zuletzt gestartete Apps und Spiele (neueste zuerst), nur solche, die es noch gibt."""
        liste = daten.lies_json(self._pfad("zuletzt.json"), []) or []
        return [x for x in liste if isinstance(x, str) and self.app(x) is not None][:self.ZULETZT_MAX]

    def ort(self, app_id):
        """Die Startseite meldet ein Spielzimmer-Spiel (oder None = zurück auf der Startseite)."""
        with self.lock:
            if app_id is None or self.app(app_id) is not None:
                self.aktuell = app_id

    def kiosk_ort(self, url):
        """kiosk.py meldet die Adresse im Browser: daraus folgt die App (für das Zeitkonto)."""
        with self.lock:
            if not url or url.startswith(START_URL):
                if self.aktuell and (self.app(self.aktuell) or {}).get("typ") == "web":
                    self.aktuell = None
                return
            for app in self.katalog:
                start = app.get("start", "")
                if app.get("typ") == "web" and start and _gleicher_ursprung(url, start):
                    self.aktuell = app["id"]
                    return
            if self.aktuell == "spiel-bass" and any(
                    _gleicher_ursprung(url, link) for link in self._bass_links()):
                return      # Video/Tabs/Backing aus der Musik-Akademie: zählt nicht
            if self.aktuell == "spiel-bass" and (urlsplit(url).hostname or "").endswith("ultimate-guitar.com"):
                return      # Song-Suche der Musik-Akademie
            self.aktuell = "internet"

    def zurueck(self, eltern=False):
        """„Zur Startseite“ - von überall (langes EXIT, Guide-Taste, Zeitende)."""
        laeuft, _ = self.system.retropie_zustand()
        if laeuft:
            self.system.retropie("stop")
            self.system.spiel("stop")
        self.auftrag("dimmen", stufe=0)
        self.auftrag("startseite", eltern=bool(eltern))
        with self.lock:
            self.aktuell = None
        return True

    # ------------------------------------------------------------ Bass-Ecke
    def _bass_links(self):
        for song in self.einstellungen.get("bass") or []:
            for art in BASS_ARTEN:
                if song.get(art):
                    yield song[art]
                    if youtube_player(song[art]) != song[art]:
                        yield youtube_player(song[art])
        for adresse in self.familie.einstellungen()["bass_bibliotheken"].values():
            if adresse:
                yield adresse

    def bass_bibliothek(self, art):
        """Plex-Bibliotheken der Bass-Ecke (Unterricht, Backing Tracks) - von den Eltern eingetragen."""
        adresse = self.familie.einstellungen()["bass_bibliotheken"].get(art)
        if not adresse:
            return False, "Diese Bibliothek ist noch nicht eingerichtet."
        self.auftrag("oeffne", url=adresse, app="spiel-bass")
        with self.lock:
            self.aktuell = "spiel-bass"
        return True, "Öffnet ..."

    # ------------------------------------------------------------ Retro: zuletzt gespielt
    def retro_spiele(self):
        return familie_mod.zuletzt_gespielt(familie_mod.lese_gamelists(GAMELISTS, ROMS))

    def retro_starten(self, system, rom):
        """Nur Spiele aus den Spielelisten - die Datei muss unter ~/RetroPie/roms/<system>/ liegen."""
        bekannt = {(s["system"], s["rom"]) for s in familie_mod.lese_gamelists(GAMELISTS, ROMS)}
        if (system, rom) not in bekannt:
            return False, "Dieses Spiel gibt es nicht."
        ok, grund, _ = self.konto.darf_starten(self.app("games"), self.uhr(), uhr_sicher=bool(self.uhr_sicher()))
        if self.gesperrt:
            ok, grund = False, self.gesperrt.get("text") or "Der Fernseher ist gerade gesperrt."
        if not ok:
            return False, grund
        daten.schreibe_json(self._pfad("spiel-start.json"), {"system": system, "rom": rom})
        if not self.system.spiel("start"):
            return False, "Das Spiel startet gerade nicht. Bitte Mama oder Papa holen."
        with self.lock:
            self.aktuell = "games"
        if system == "c64":                       # 4.1.1: welche Taste was macht - im Spiel eingeblendet
            for sekunden in (15, 35):
                zeit = threading.Timer(sekunden, self.system.retroarch, args=(C64_HINWEIS,))
                zeit.daemon = True
                zeit.start()
        return True, "Los geht's!"

    def bass_songs(self):
        return [{"nr": i, "titel": song.get("titel", ""), "arten": [a for a in BASS_ARTEN if song.get(a)]}
                for i, song in enumerate(self.einstellungen.get("bass") or [])]

    def bass_oeffne(self, nr, art):
        """Nur Links, die die Eltern eingetragen haben - das Kind kann keine Adresse eingeben."""
        songs = self.einstellungen.get("bass") or []
        if art not in BASS_ARTEN or not isinstance(nr, int) or not 0 <= nr < len(songs) or not songs[nr].get(art):
            return False, "Diesen Link gibt es nicht."
        if self.gesperrt:
            return False, self.gesperrt.get("text") or "Der Fernseher ist gerade gesperrt."
        self.auftrag("oeffne", url=youtube_player(songs[nr][art]), app="spiel-bass")
        with self.lock:
            self.aktuell = "spiel-bass"
            self.letzte_eingabe = self.monoton()
        return True, "%s öffnet ..." % songs[nr].get("titel", "Song")

    # ------------------------------------------------------------ Domains aus dem Kiosk (Whitelist, 3.2)
    def kiosk_domains(self, eintraege):
        """kiosk.py meldet geladene und von der Richtlinie blockierte Hosts. Gespeichert für die Eltern-Seite."""
        import re as _re
        jetzt = self.uhr().isoformat(timespec="seconds")
        with self.lock:
            bekannt = daten.lies_json(self._pfad("domains.json"), {}) or {}
            for e in eintraege[:200]:
                host = str(e.get("host", "")).lower()[:253]
                if not _re.fullmatch(r"[a-z0-9.-]+", host) or host in ("127.0.0.1", "localhost"):
                    continue
                d = bekannt.setdefault(host, {"anzahl": 0, "blockiert": 0, "apps": []})
                d["anzahl"] += int(e.get("anzahl", 1))
                d["blockiert"] += int(e.get("blockiert", 0))
                d["zuletzt"] = jetzt
                app = self.aktuell or "startseite"
                if app not in d["apps"]:
                    d["apps"] = (d["apps"] + [app])[-5:]
            if len(bekannt) > 500:     # die ältesten wegwerfen
                for host in sorted(bekannt, key=lambda h: bekannt[h].get("zuletzt", ""))[:len(bekannt) - 500]:
                    del bekannt[host]
            daten.schreibe_json(self._pfad("domains.json"), bekannt)

    def domains_erlauben(self, hosts):
        w = dict(self.einstellungen.get("whitelist") or {})
        zusatz = list(w.get("zusatz", []))
        for host in hosts:
            if host not in zusatz:
                zusatz.append(host)
        w["zusatz"] = zusatz
        self.einstellungen_aendern({"whitelist": w})

    # ------------------------------------------------------------ 4.4: Speicherplatz des Kindes, Album, Fotoalbum
    def _ordner_groesse(self, ordner):
        try:
            return sum(os.path.getsize(os.path.join(ordner, n)) for n in os.listdir(ordner)
                       if os.path.isfile(os.path.join(ordner, n)))
        except OSError:
            return 0

    def speicher_status(self):
        limit = int((self.einstellungen.get("speicher") or {}).get("limit_mb", SPEICHER_VORGABE_MB))
        belegt = self._ordner_groesse(self._pfad("zeichnungen")) + self._ordner_groesse(self._pfad("album"))
        return {"belegt_mb": round(belegt / 1048576, 1), "limit_mb": limit, "voll": belegt >= limit * 1048576}

    def speicher_pruefen(self, dazu_bytes=0):
        s = self.speicher_status()
        if s["voll"] or s["belegt_mb"] + dazu_bytes / 1048576 > s["limit_mb"]:
            raise ValueError("Dein Speicher ist voll (%d MB). Lösch erst ein paar alte Bilder im Fotoalbum." % s["limit_mb"])

    def album_liste(self):
        ordner = self._pfad("album")
        namen = sorted((n for n in os.listdir(ordner) if ALBUM_NAME.fullmatch(n)), reverse=True) if os.path.isdir(ordner) else []
        return [{"datei": n, "url": "/album/" + n} for n in namen]

    def album_pfad(self, name):
        pfad = self._pfad(os.path.join("album", str(name)))
        return pfad if ALBUM_NAME.fullmatch(str(name or "")) and os.path.isfile(pfad) else None

    def album_uebernehmen(self, datei):
        """Ein Foto von Telegram ins Album des Kindes (bleibt, zählt zum Speicherplatz)."""
        quelle = self.telegram.medium_pfad(datei)
        if not quelle or not quelle.endswith(".jpg"):
            raise ValueError("Dieses Foto ist nicht mehr da.")
        self.speicher_pruefen(os.path.getsize(quelle))
        os.makedirs(self._pfad("album"), exist_ok=True)
        name = "a" + os.path.basename(quelle)[1:]
        import shutil
        shutil.copyfile(quelle, self._pfad(os.path.join("album", name)))
        log.info("Album: %s übernommen.", name)
        return name

    def kind_datei_loeschen(self, art, name):
        """Das Kind löscht eigene Bilder (Album oder Zeichnung), z. B. wenn der Speicher voll ist."""
        if art == "album" and self.album_pfad(name):
            os.remove(self.album_pfad(name))
        elif art == "zeichnung" and ZEICHNUNG_NAME.fullmatch(str(name or "")) and os.path.isfile(self._pfad(os.path.join("zeichnungen", name))):
            os.remove(self._pfad(os.path.join("zeichnungen", name)))
        else:
            raise ValueError("Dieses Bild gibt es nicht.")
        auswahl = [a for a in self.fotoalbum()["auswahl"] if a != "%s:%s" % (art, name)]
        self.fotoalbum_kind({"auswahl": auswahl}, intern=True)
        log.info("Kind hat %s %s gelöscht.", art, name)

    def fotoalbum(self):
        f = dict({"erlaubt": False, "ordner": "", "bildschirmschoner": False, "auswahl": []}, **(self.einstellungen.get("fotoalbum") or {}))
        return f

    def fotoalbum_kind(self, aenderung, intern=False):
        """Das Kind wählt Bilder aus (⭐) und schaltet den Bildschirmschoner ein oder aus - nur, wenn erlaubt."""
        f = self.fotoalbum()
        if not intern and not f["erlaubt"]:
            raise ValueError("Das Fotoalbum ist noch nicht eingeschaltet. Frag Mama oder Papa.")
        if "bildschirmschoner" in aenderung:
            f["bildschirmschoner"] = bool(aenderung["bildschirmschoner"])
        if "auswahl" in aenderung:
            auswahl = aenderung["auswahl"]
            if not isinstance(auswahl, list) or len(auswahl) > 300 or not all(isinstance(a, str) and FOTO_AUSWAHL.fullmatch(a) for a in auswahl):
                raise ValueError("Ungültige Auswahl.")
            f["auswahl"] = list(dict.fromkeys(auswahl))
        with self.lock:
            self.einstellungen["fotoalbum"] = f
            daten.schreibe_json(self._pfad("einstellungen.json"), self.einstellungen)
        return f

    def fotoalbum_ordner_liste(self, pfad):
        f = self.fotoalbum()
        if not f["erlaubt"] or not f["ordner"]:
            raise ValueError("Es ist noch kein Foto-Ordner eingerichtet.")
        return hoerbuch.liste(f["ordner"], pfad, endungen=hoerbuch.BILD)

    def fotoalbum_bild_adresse(self, pfad):
        f = self.fotoalbum()
        if not f["erlaubt"] or not f["ordner"]:
            raise ValueError("Es ist noch kein Foto-Ordner eingerichtet.")
        return hoerbuch.bild_adresse(f["ordner"], pfad)

    def bild_teilen(self, art, name, chat):
        """4.4: Das Kind schickt ein eigenes Bild (Zeichnung oder Album) an einen freigegebenen Kontakt."""
        if art == "zeichnung" and ZEICHNUNG_NAME.fullmatch(str(name or "")):
            pfad = self._pfad(os.path.join("zeichnungen", name))
        else:
            pfad = self.album_pfad(name) if art == "album" else None
        if not pfad or not os.path.isfile(pfad):
            raise ValueError("Dieses Bild gibt es nicht.")
        ziel = next((c for c in self.telegram.schreibbar() if c["id"] == chat), None)
        if ziel is None:
            raise ValueError("Diesem Kontakt kannst du nicht schreiben.")
        with open(pfad, "rb") as f:
            roh = f.read()
        kind = self.einstellungen.get("name") or "FernsehFranzi"
        if not self.telegram.sende_bild(ziel["id"], roh, os.path.basename(pfad), "🎨 Von %s" % kind):
            raise ValueError("Das Bild ist gerade nicht angekommen. Versuch es später nochmal.")
        self.telegram._merke(ziel["id"], "raus", "🎨 Bild geschickt")
        if not ziel["eltern"]:
            self.telegram.melde_eltern("freunde", "%s hat %s %s ein Bild geschickt." % (kind, ziel["symbol"], ziel["name"]))
        return ziel["name"]

    # ------------------------------------------------------------ 4.4: Karaoke mit den Liedern der Klassenkiste
    KK_COOKIE_S = 600

    def klassenkiste_basis(self):
        """https://<host> der Klassenkiste-Kachel (wenn eingerichtet und aktiv), sonst ""."""
        app = next((a for a in self.katalog if a.get("id") == "klassenkiste" and a.get("aktiv", True) and a.get("start")), None)
        if not app:
            return ""
        teile = urlsplit(app["start"])
        sicher = teile.scheme == "https" or (teile.scheme == "http" and teile.hostname in ("127.0.0.1", "localhost"))   # http nur für Tests
        return "%s://%s" % (teile.scheme, teile.netloc) if sicher and teile.netloc else ""

    def kk_anmeldung_empfangen(self, nr, cookie="", fehler=""):
        with self._kk_neu:
            if nr == self._kk["nr"]:
                self._kk.update(cookie=str(cookie or "")[:8000] or None, fehler=str(fehler or "")[:200], zeit=self.monoton())
            self._kk_neu.notify_all()

    def _kk_cookie(self, neu=False, warten_s=6.0):
        basis = self.klassenkiste_basis()
        if not basis:
            raise ValueError("Die Klassenkiste ist nicht eingerichtet.")
        with self._kk_neu:
            if not neu and self._kk["cookie"] and self.monoton() - self._kk["zeit"] < self.KK_COOKIE_S:
                return basis, self._kk["cookie"]
            self._kk = {"nr": self._kk["nr"] + 1, "cookie": None, "fehler": "", "zeit": 0.0}
            nr = self._kk["nr"]
        self.auftrag("kk_anmeldung", kk=nr, adresse=basis)
        ende = time.monotonic() + warten_s
        with self._kk_neu:
            while self._kk["nr"] == nr and not self._kk["zeit"]:
                rest = ende - time.monotonic()
                if rest <= 0:
                    raise ValueError("Der Fernseher antwortet gerade nicht. Bitte nochmal versuchen.")
                self._kk_neu.wait(rest)
            if not self._kk["cookie"]:
                raise ValueError(self._kk["fehler"] or KK_ANMELDEN)
            return basis, self._kk["cookie"]

    # ------------------------------------------------------------ 5.0: Designs der Startseite
    def startseite_anzeige(self):
        st = self.einstellungen.get("startseite") or {"lieblinge": [], "thema": "blau"}
        return dict(st, design=design_mod.fuer_startseite(self.einstellungen.get("design"), st, self.uhr()))

    def startseite_setzen(self, d):
        """Vom Kind (Meine Startseite): Lieblinge und Design - nur ein Design, das die Eltern erlaubt haben."""
        if not isinstance(d, dict):
            raise ValueError("Startseite: ungültige Angaben.")
        thema = design_mod.neu(d.get("thema", "blau"))
        alt = design_mod.neu((self.einstellungen.get("startseite") or {}).get("thema", "blau"))
        erlaubt = design_mod.einstellungen(self.einstellungen.get("design"))
        if thema != alt and thema not in erlaubt["erlaubt"]:
            raise ValueError("Dieses Design haben Mama oder Papa ausgeschaltet.")
        ansicht = d.get("ansicht", (self.einstellungen.get("startseite") or {}).get("ansicht", "konsole"))
        if ansicht != (self.einstellungen.get("startseite") or {}).get("ansicht", "konsole") and ansicht not in erlaubt["ansichten"]:
            raise ValueError("Diese Ansicht haben Mama oder Papa ausgeschaltet.")
        self.einstellungen_aendern({"startseite": {"lieblinge": d.get("lieblinge", []), "thema": thema, "ansicht": ansicht}})

    def klassenkiste_json(self, pfad):
        """GET an die Klassenkiste mit der Anmeldung des Kindes (5.0: auch für die Schul-Seite). Nur lesen."""
        if not pfad.startswith("/api/") or any(z in pfad for z in "\r\n #"):
            raise ValueError("Ungültige Abfrage.")
        for neu in (False, True):
            basis, cookie = self._kk_cookie(neu=neu)
            anfrage = urllib.request.Request(basis + pfad,
                                             headers={"Cookie": cookie, "Accept": "application/json", "User-Agent": "FernsehFranzi"})
            try:
                with urllib.request.urlopen(anfrage, timeout=15) as antwort:
                    return json.loads(antwort.read(8 * 1024 * 1024).decode("utf-8"))
            except urllib.error.HTTPError as fehler:
                if fehler.code in (401, 403) and not neu:
                    continue
                raise ValueError(KK_ANMELDEN if fehler.code in (401, 403) else "Die Klassenkiste antwortet gerade nicht (%s)." % fehler.code) from None
            except (OSError, ValueError) as fehler:
                raise ValueError("Die Klassenkiste ist gerade nicht erreichbar (%s)." % fehler) from None
        return None

    def karaoke_liste(self):
        """Lieder mit Text aus der Klassenkiste (nur lesen, mit der Anmeldung des Kindes)."""
        daten = self.klassenkiste_json("/api/playlists/karaoke") or {}
        lieder = []
        for s in (daten.get("songs") or [])[:500]:
            kennung = str(s.get("id", ""))
            if not KK_LIED.fullmatch(kennung) or not str(s.get("lyrics") or "").strip():
                continue
            lieder.append({"id": kennung, "titel": str(s.get("title") or "")[:120], "liste": str(s.get("playlist") or "")[:80],
                           "dauer": s.get("duration") if isinstance(s.get("duration"), int) else None,
                           "text": str(s.get("lyrics"))[:20000], "musik": bool(s.get("src")),
                           "marken": _karaoke_marken(s.get("marken"))})
        return lieder

    def karaoke_musik(self, kennung):
        """(Adresse, Kopfzeilen) für die Musik eines Liedes - der Server reicht sie mit Range durch."""
        if not KK_LIED.fullmatch(str(kennung or "")):
            raise ValueError("Unbekanntes Lied.")
        basis, cookie = self._kk_cookie()
        return "%s/api/playlists/song/%s/stream" % (basis, kennung), {"Cookie": cookie, "User-Agent": "FernsehFranzi"}

    # ------------------------------------------------------------ 4.3: Spielraum (Handy-Spiele)
    def handyspiele(self):
        hs = self.einstellungen.get("handyspiele") or {}
        return {"aktiv": bool(hs.get("aktiv")), "port": int(hs.get("port", HANDYSPIELE_PORT))}

    def _eigene_ip(self):
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("192.0.2.1", 9))      # Testnetz-Adresse: es wird nichts gesendet, nur die Route gewählt
                return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"

    def raum_oeffnen(self):
        """Neuer Spielraum (oder der offene). Nur wenn die Eltern Handy-Spiele erlaubt haben und die App gerade geht."""
        if not self.handyspiele()["aktiv"]:
            raise ValueError("Handy-Spiele sind ausgeschaltet. Mama oder Papa können sie auf der Eltern-Seite einschalten.")
        ok, grund, _ = self.konto.darf_starten(self.app("spiel-handys"), self.uhr(), uhr_sicher=bool(self.uhr_sicher()))
        if not ok or self.gesperrt:
            raise ValueError(grund if not ok else (self.gesperrt.get("text") or "Der Fernseher ist gerade gesperrt."))
        with self._raum_lock:
            if self.raum is None:
                quiz = (self.einstellungen.get("inhalte") or {}).get("quiz") or []
                self.raum = raum_mod.Raum(self.einstellungen.get("name") or "Fernseher", eigene_fragen=quiz,
                                          monoton=self.monoton)
                log.info("Spielraum geöffnet (Code %s).", self.raum.code)
            return self.raum_tv()

    def raum_adresse(self):
        return "http://%s:%d" % (self._eigene_ip(), self.handyspiele()["port"])

    def raum_tv(self, striche_ab=None):
        with self._raum_lock:
            if self.raum is None:
                raise ValueError("Es ist gerade kein Spielraum offen.")
            self.raum.tick()                       # der Fernseher fragt oft - so laufen Zeiten und Runden flüssig
            z = self.raum.tv_zustand()
            adresse = self.raum_adresse()
            z["adresse"], z["qr"] = adresse, qr.svg("%s/mitspielen?r=%s" % (adresse, self.raum.token))
            if striche_ab is not None and isinstance(self.raum.spiel, raum_mod.MalenRaten):
                z["striche"] = self.raum.spiel.striche_ab(striche_ab)
            return z

    def raum_tv_aktion(self, daten):
        with self._raum_lock:
            if self.raum is None:
                raise ValueError("Es ist gerade kein Spielraum offen.")
            self.raum.tv_aktion(daten if isinstance(daten, dict) else {})

    # Handys (über den eigenen Server im Heimnetz, siehe web.RaumHandler)
    def raum_beitreten(self, schluessel, name, symbol, leicht):
        with self._raum_lock:
            r = self.raum
            if r is None or not schluessel or not (secrets.compare_digest(str(schluessel), r.token) or
                                                     str(schluessel).upper() == r.code):
                raise ValueError("Diesen Spielraum gibt es nicht (mehr). Bitte den QR-Code am Fernseher neu scannen.")
            sid, geheim = r.beitreten(name, symbol, leicht)
            log.info("Spielraum: %s ist dabei.", r.spieler[sid]["name"])
            return {"geheim": geheim, "id": sid}

    def raum_spieler(self, geheim):
        with self._raum_lock:
            sid = self.raum.spieler_von(geheim) if self.raum else None
            if sid is None:
                raise ValueError("Du bist nicht (mehr) im Spielraum.")
            return sid

    def raum_zustand(self, geheim):
        with self._raum_lock:
            sid = self.raum_spieler(geheim)
            self.raum.tick()
            return self.raum.zustand_fuer(sid)

    def raum_aktion(self, geheim, daten):
        with self._raum_lock:
            sid = self.raum_spieler(geheim)
            self.raum.aktion(sid, daten if isinstance(daten, dict) else {})
            zustand = self.raum.zustand_fuer(sid)
        with self.lock:
            self.letzte_eingabe = self.monoton()    # am Handy wird gespielt = aktiv (fürs Zeitkonto)
        return zustand

    def raum_schliessen(self, grund=""):
        with self._raum_lock:
            if self.raum is not None:
                log.info("Spielraum geschlossen%s.", (" (%s)" % grund) if grund else "")
            self.raum = None
        if grund:
            self.auftrag("hinweis", text=grund)

    def raum_tick(self):
        with self._raum_lock:
            if self.raum is None:
                return
            if self.monoton() - self.raum.geoeffnet > raum_mod.RAUM_MAX_S:
                grund = "Die Handy-Spiele sind nach zwei Stunden beendet."
            elif not self.handyspiele()["aktiv"]:
                grund = "Handy-Spiele wurden ausgeschaltet."
            else:
                ok, grund, _ = self.konto.darf_starten(self.app("spiel-handys"), self.uhr(), uhr_sicher=bool(self.uhr_sicher()))
                grund = None if ok and not self.gesperrt else (grund or "Der Fernseher ist gerade gesperrt.")
            if grund is None:
                try:
                    self.raum.tick()
                except Exception:   # noqa: BLE001 - ein Spielfehler darf den Takt nie stören
                    log.exception("Spielraum")
                return
        self.raum_schliessen(grund)

    def lan_adressen(self):
        """Adressen der Eltern-Seite fürs Handy (Name im Heimnetz und IP), nur wenn sie an ist."""
        import socket
        lan = self.einstellungen.get("eltern_lan") or {}
        if not lan.get("aktiv"):
            return []
        port = lan.get("port", 8766)
        adressen = ["http://%s.%s:%d" % (socket.gethostname(), "local", port)]   # Name im Heimnetz (mDNS)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("192.0.2.1", 9))      # Testnetz-Adresse: es wird nichts gesendet, nur die Route gewählt
                adressen.append("http://%s:%d" % (s.getsockname()[0], port))
        except OSError:
            pass
        return adressen

    def eingabe(self, tasten=None):
        with self.lock:
            self.letzte_eingabe = self.monoton()
            if tasten:
                self.nachtruhe = False           # jemand ist wach und drückt Tasten
        if tasten:
            self.familie.tasten(tasten)

    # ------------------------------------------------------------ Zeitkonto (alle 5 s)
    def tick(self, sekunden=TICK_S):
        jetzt = self.uhr()
        self._auszeit_takt(jetzt)                  # 5.1: Auszeit vorbei -> frei
        if self.konto.zustand.get("datum") not in (None, jetzt.date().isoformat()):
            self.woche_fortschreiben()             # neuer Tag: gestern in die Wochenübersicht
            self.ferien_auffrischen()
        laeuft, _ = self.system.retropie_zustand()
        with self.lock:
            if self._retropie_vorher and not laeuft and self.aktuell == "games":
                self.aktuell = None
            self._retropie_vorher = laeuft
            app_id = "games" if laeuft else self.aktuell
            app = self.app(app_id) if app_id != "internet" else \
                {"id": "internet", "name": "Internet", "typ": "web", "zeit": "zaehlt"}
            ruhig = self.monoton() - self.letzte_eingabe
            ereignisse = self.konto.tick(jetzt, app, sekunden, aktiv=ruhig < LEERLAUF_S)
            internet_ruhig = app_id == "internet" and ruhig >= INTERNET_LEERLAUF_S
        self.familie.tick(jetzt, app, sekunden, aktiv=ruhig < LEERLAUF_S)
        self.telegram.tick()                       # 4.3: wartende Nachrichten nach der Sperrzeit zeigen
        self.raum_tick()                           # 4.3: Spielraum (Zeit, Sperrzeiten, Spielablauf)
        self.nutzung.zaehle(jetzt, app_id, sekunden, ruhig < LEERLAUF_S or self.hoerbuch_laeuft())
        if not self.konto.sonder_aktiv(jetzt):
            self._sperrzeiten(jetzt, app, laeuft)
        self._sonder_ende(jetzt, laeuft)
        self._wecker_takt(jetzt)
        self._scraper_nachts(jetzt, laeuft)
        self.wetter.tick()                         # 5.0: im Hintergrund, höchstens alle 30 min
        self.schule.tick(jetzt)                    # 5.0: Klassenkiste alle 15 min, Morgen-Check am Abend
        for art, wert in ereignisse:
            if art == "warnung":
                self._warne("Noch %d %s!" % (wert, "Minute" if wert == 1 else "Minuten"), laeuft)
            elif art == "kulanz":
                self._warne("Die Zeit ist um - noch %d Minuten zum Speichern und Beenden." % wert, laeuft)
            elif art == "schluss":
                self._beende_wegen_zeit(laeuft)
        if internet_ruhig:
            log.info("Internet ohne Eingabe - zurück zur Startseite.")
            self.zurueck()
        if self.monoton() - self._zuletzt_gespeichert >= SPEICHERN_S:
            self.speichere_konto()
        if self.monoton() - self._kopfhoerer_geprueft >= KOPFHOERER_S:
            self._kopfhoerer_geprueft = self.monoton()
            try:
                self.kopfhoerer_pruefen()
            except Exception:   # noqa: BLE001 - Ton darf den Takt nie stören
                log.exception("Kopfhörer")
        if self.monoton() - self._ton_geprueft >= 30:
            self._ton_geprueft = self.monoton()
            try:
                self.system.ton_wache(self.ton["ziel"])
            except Exception:   # noqa: BLE001 - Ton darf den Takt nie stören
                log.exception("Ton-Wache")

    def _warne(self, text, retropie):
        if self.still():
            return                       # Gute-Nacht-Modus: keine Töne, nichts einblenden
        self.system.gong()
        self.melde(text)
        self.auftrag("hinweis", text=text)
        if retropie:
            self.system.retroarch("SHOW_MSG " + text)

    def _beende_wegen_zeit(self, retropie):
        self.melde("Für heute ist die Spielzeit vorbei. Freie Apps gehen noch.")
        self.telegram.melde_eltern("zeit", "Die Spielzeit für heute ist aufgebraucht.")
        if retropie:
            self._retro_beenden()
        self.zurueck()
        self.familie.zeitende()

    def statistik(self):
        """4.0: Nutzung der letzten 31 Tage mit Namen und Farben der Apps (für die Eltern-Seite)."""
        namen = {e["id"]: {"name": e["name"], "farbe": e.get("farbe", ""), "zeit": e.get("zeit", "frei"),
                           "lernen": bool(e.get("lernen"))} for e in self.katalog + SPIELZIMMER}
        namen["internet"] = {"name": "Internet", "farbe": "#607d8b", "zeit": "zaehlt", "lernen": False}
        gutscheine = [c for c in self.gutscheine.liste() if c.get("eingeloest")]
        return {"tage": self.nutzung.auszug(31), "apps": namen, "gutscheine": gutscheine,
                "woche": daten.lies_json(self._pfad("woche.json"), {}) or {}}

    # ------------------------------------------------------------ 4.2: Bilder für Retro-Spiele (Scraper)
    SCRAPER_NACHTS = (4, 0)          # jede Nacht um 4 Uhr nach neuen Spielen schauen (holt nur, was fehlt)

    def scraper_status(self):
        try:
            with open(self._pfad("scraper.json"), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {"laeuft": False, "start": None, "ende": None, "systeme": {}, "fehler": ""}

    def scraper_starten(self):
        if self.system.retropie_zustand()[0]:
            raise ValueError("RetroPie läuft gerade – bitte erst zur Startseite, dann noch einmal.")
        if self.scraper_status().get("laeuft") and time.time() - (self.scraper_status().get("start") or 0) < 3600:
            raise ValueError("Die Bilder werden gerade schon geholt.")
        if not self.system.scraper():
            raise ValueError("Der Scraper startet gerade nicht (Logs: journalctl -u fernsehfranzi-scraper).")
        log.info("Scraper gestartet.")
        return True

    def _scraper_nachts(self, jetzt, retro_laeuft):
        if retro_laeuft or (jetzt.hour, jetzt.minute) < self.SCRAPER_NACHTS or jetzt.hour > self.SCRAPER_NACHTS[0]:
            return
        if getattr(self, "_scraper_tag", None) == jetzt.date():
            return
        self._scraper_tag = jetzt.date()
        try:
            self.scraper_starten()
        except ValueError as fehler:
            log.info("Scraper nachts nicht gestartet: %s", fehler)

    # ------------------------------------------------------------ 4.1: Bluetooth (Eltern-Seite; das Kind koppelt nicht)
    BT_AKTIONEN = ("suchen", "koppeln", "verbinden", "trennen", "entfernen")
    BT_MAC = re.compile(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}\Z")

    def bluetooth_liste(self):
        ok, aus = self.system.bluetooth("liste")
        if not ok:
            raise ValueError("Bluetooth antwortet nicht: %s" % aus.strip()[-200:])
        geraete = []
        for zeile in aus.splitlines():
            teile = (zeile.split("\t") + ["", "", "", ""])[:4]
            if self.BT_MAC.match(teile[0]):
                geraete.append({"mac": teile[0], "name": teile[1][:60] or teile[0], "verbunden": teile[2] == "ja",
                                "akku": int(teile[3]) if teile[3].isdigit() else None})
        return geraete

    def bluetooth_aktion(self, aktion, mac=""):
        if aktion not in self.BT_AKTIONEN:
            raise ValueError("Unbekannte Bluetooth-Aktion.")
        mac = str(mac or "").upper()
        if aktion != "suchen" and not self.BT_MAC.match(mac):
            raise ValueError("Ungültige Geräte-Adresse.")
        ok, aus = self.system.bluetooth(aktion, "" if aktion == "suchen" else mac)
        if aktion == "suchen":
            if not ok:
                raise ValueError("Suchen ging nicht: %s" % aus.strip()[-200:])
            gekoppelt = {g["mac"] for g in self.bluetooth_liste()}
            neu = []
            for zeile in aus.splitlines():
                teile = (zeile.split("\t") + [""])[:2]
                if self.BT_MAC.match(teile[0]) and teile[0] not in gekoppelt:
                    neu.append({"mac": teile[0], "name": teile[1][:60] or teile[0]})
            return {"gefunden": neu}
        if not ok:
            raise ValueError({"koppeln": "Koppeln ging nicht – ist das Gerät im Kopplungsmodus?",
                              "verbinden": "Verbinden ging nicht – ist das Gerät an?"}.get(aktion, "Das ging nicht.")
                             + " (%s)" % aus.strip()[-160:])
        log.info("Bluetooth: %s %s.", aktion, mac)
        return {"geraete": self.bluetooth_liste()}

    # ------------------------------------------------------------ 4.1: Sicherung (Eltern-Seite)
    def sicherung_erstellen(self):
        self.speichere_konto()
        self.familie.speichern(sofort=True)
        with self.lock:
            return sicherung_mod.erstellen(self.ordner, self.version, self.uhr().isoformat(timespec="seconds"))

    def sicherung_einspielen(self, roh):
        """Prüfen, alten Stand sichern, dann schreiben und den Server neu starten (systemd startet ihn wieder).
        Geschrieben wird erst kurz nach der Antwort an die Eltern-Seite, unter der Sperre und direkt vor dem Neustart -
        so kann der laufende Server die eingespielten Dateien nicht mehr überschreiben."""
        inhalt = sicherung_mod.pruefen(roh)
        zeit = self.uhr().isoformat(timespec="seconds")
        with self.lock:
            self.speichere_konto()
            self.familie.speichern(sofort=True)
            alt = sicherung_mod.eigene_sicherung(self.ordner, self.version, zeit)
        token = (self.einstellungen.get("telegram") or {}).get("token", "")

        def los():
            with self.lock:
                sicherung_mod.einspielen(self.ordner, inhalt, token)
                log.warning("Sicherung eingespielt (alter Stand: sicherungen/%s) - Server startet neu.", alt)
                self.prozess_neustart()
        threading.Timer(1.0, los).start()
        bilder = sum(1 for n in inhalt if n.startswith("zeichnungen/"))
        return "Sicherung wird eingespielt (%d Bilder). Der Fernseher lädt gleich neu. Alter Stand: %s" % (bilder, alt)

    def speichere_konto(self):
        self.nutzung.speichern()
        with self.lock:
            daten.schreibe_json(self._pfad("zeitkonto.json"), self.konto.zustand)
            self._zuletzt_gespeichert = self.monoton()

    # ------------------------------------------------------------ Ton
    def lautstaerke(self, richtung):
        """Lauter/leiser (GELB + Pfeile, Controller Back + Pfeile, Tastatur). Höchstwert stellen die Eltern ein.
        4.1: "stumm" schaltet den Ton aus und wieder an (Stumm-Taste der Tastatur)."""
        if richtung == "stumm":
            stumm = self.system.stumm_umschalten()
            if stumm is None:
                return None
            text = "🔇 Ton aus" if stumm else "🔊 Ton an"
            self.melde(text)
            self.auftrag("hinweis", text=text)
            if self.system.retropie_zustand()[0]:
                self.system.retroarch("SHOW_MSG " + text)
            return 0 if stumm else 1
        schritt = {"lauter": 5, "leiser": -5}.get(richtung)
        if schritt is None:
            raise ValueError("richtung muss lauter, leiser oder stumm sein.")
        hoechstens = int((self.einstellungen.get("ton") or {}).get("max", 100))
        wert = self.system.lautstaerke(schritt, hoechstens)
        if wert is None:
            return None
        text = "Lautstärke: %d %%" % wert + (" (höchste Stufe)" if wert >= hoechstens and schritt > 0 else "")
        self.melde(text)
        self.auftrag("hinweis", text=text)
        laeuft, _ = self.system.retropie_zustand()
        if laeuft:
            self.system.retroarch("SHOW_MSG " + text)
        return wert

    def ton_setzen(self, ziel):
        if ziel not in ("hdmi", "klinke", "kopfhoerer"):
            raise ValueError("ziel muss hdmi, klinke oder kopfhoerer sein")
        if ziel == "kopfhoerer" and not system_mod.waehle_ausgang(self.system.ton_ausgaenge(), "kopfhoerer"):
            raise ValueError("Kein Bluetooth-Kopfhörer verbunden.")
        ok, name = self.system.ton_setzen(ziel)
        if ok:
            self.system.bestaetigungston(name)
            with self.lock:
                self.ton = {"ziel": ziel, "nr": self.ton["nr"] + 1}
                if ziel != "kopfhoerer":              # gespeichert wird nur HDMI/Klinke (der Kopfhörer kommt und geht)
                    self.einstellungen["ton"] = dict(self.einstellungen.get("ton") or {}, ziel=ziel)
                    daten.schreibe_json(self._pfad("einstellungen.json"), self.einstellungen)
        return ok, name

    def kopfhoerer_pruefen(self):
        """4.3: Neu verbundener Bluetooth-Kopfhörer -> Ton dorthin; getrennt -> zurück auf die gespeicherte Wahl.
        Wählen die Eltern bei verbundenem Kopfhörer HDMI/Klinke, bleibt das so, bis er sich neu verbindet."""
        jetzt = system_mod.waehle_ausgang(self.system.ton_ausgaenge(), "kopfhoerer")
        neu = [s for s in jetzt if s not in self.kopfhoerer]
        weg = self.kopfhoerer and not jetzt
        self.kopfhoerer = jetzt
        automatisch = (self.einstellungen.get("ton") or {}).get("kopfhoerer_auto", True)
        if neu and automatisch and self.ton["ziel"] != "kopfhoerer":
            ok, _ = self.system.ton_setzen("kopfhoerer")
            if ok:
                with self.lock:
                    self.ton = {"ziel": "kopfhoerer", "nr": self.ton["nr"] + 1}
                log.info("Kopfhörer verbunden: %s", neu[0])
        elif weg and self.ton["ziel"] == "kopfhoerer":
            ziel = (self.einstellungen.get("ton") or {}).get("ziel") or "hdmi"
            ok, _ = self.system.ton_setzen(ziel)
            with self.lock:
                self.ton = {"ziel": ziel, "nr": self.ton["nr"] + 1}
            log.info("Kopfhörer getrennt - Ton zurück auf %s (%s).", ziel, "ok" if ok else "fehlgeschlagen")

    # ------------------------------------------------------------ Eltern
    def pin_gesetzt(self):
        return bool(self.pin_daten.get("hash"))

    def eltern_anmelden(self, pin):
        """Rückgabe (token oder None, meldung)."""
        if not self.pin_gesetzt():
            return None, "Es ist noch keine PIN festgelegt."
        with self.lock:
            ok, meldung = self.sperre.pruefe(pin, self.pin_daten["hash"], time.time())
            daten.schreibe_json(self._pfad("pin.json"), self.pin_daten)
            if not ok:
                log.warning("Eltern-Anmeldung abgewiesen: %s", meldung)
                return None, meldung
            token = secrets.token_urlsafe(24)
            self.sitzungen[token] = self.monoton() + SITZUNG_S
        log.info("Eltern angemeldet.")
        return token, ""

    def sitzung_gueltig(self, token):
        with self.lock:
            ablauf = self.sitzungen.get(token or "")
            if not ablauf or ablauf < self.monoton():
                self.sitzungen.pop(token or "", None)
                return False
            self.sitzungen[token] = self.monoton() + SITZUNG_S
            return True

    def abmelden(self, token):
        with self.lock:
            self.sitzungen.pop(token or "", None)

    def pin_festlegen(self, neu, alt=None, erster_start_am_tv=False):
        """Erste PIN nur am Fernseher (ohne alte), danach nur mit der alten PIN."""
        with self.lock:
            if self.pin_gesetzt():
                if not pin_mod.pin_stimmt(alt or "", self.pin_daten["hash"]):
                    return False, "Die alte PIN stimmt nicht."
            elif not erster_start_am_tv:
                return False, "Die erste PIN wird am Fernseher festgelegt."
            try:
                self.pin_daten["hash"] = pin_mod.hash_erzeugen(neu)
            except ValueError as fehler:
                return False, str(fehler)
            self.sperre.zustand.update(fehler=0, gesperrt_bis=0)
            daten.schreibe_json(self._pfad("pin.json"), self.pin_daten)
            self.sitzungen.clear()
        log.info("Eltern-PIN festgelegt.")
        return True, "PIN gespeichert."

    def eltern_daten(self):
        jetzt = self.uhr()
        with self.lock:
            z = self.konto._tag(jetzt)
            einst = copy.deepcopy(self.einstellungen)
            if (einst.get("telegram") or {}).get("token"):
                einst["telegram"]["token"] = telegram_mod.VERSTECKT    # Token nie zurück an den Browser
            if isinstance(einst.get("telegram"), dict):              # 4.3: Kontakte mit allen Feldern (alte = Eltern)
                einst["telegram"]["chats"] = telegram_mod.einstellungen(einst["telegram"])["chats"]
            return {
                "version": self.version,
                "telegram_unbekannt": list(self.telegram.unbekannt),
                "telegram_verlauf": self.telegram.verlauf_fuer_eltern(),
                "ton_jetzt": self.ton["ziel"], "kopfhoerer": bool(self.kopfhoerer),
                "speicher": self.speicher_status(), "album": self.album_liste(),
                "telegram_meldungen": dict(telegram_mod.MELDUNG_ARTEN),
                "einstellungen": einst,
                "regeln": self._regeln(), "apps": copy.deepcopy(self.katalog),
                "spielzimmer": copy.deepcopy(self.spielzimmer()),           # 4.6: eingebaute Spiele und Kacheln
                "bundeslaender": ferien_mod.LAENDER, "ferien_bekannt_bis": ferien_mod.bekannt_bis(),
                "klaenge": klaenge_mod.liste(),                          # 5.2: Klang-Archiv
                # 5.0: Designs, Wetter, Schule, Kinderwelten, Kinder-News (vollständig, mit Vorgaben)
                "design": dict(design_mod.einstellungen(einst.get("design")),
                               alle=[{"id": k, "name": n, "hell": h, "abends": sw if h else k} for k, n, h, sw in design_mod.DESIGNS],
                               alle_ansichten=[{"id": k, "name": n} for k, n in design_mod.ANSICHTEN],
                               ),
                "wetter": dict(wetter_mod.einstellungen(einst.get("wetter")), jetzt=self.wetter.fuer_tv()),
                "schule": dict(schule_mod.einstellungen(einst.get("schule")), eingerichtet=bool(self.klassenkiste_basis()),
                               stand=self.schule.fuer_tv()),
                "kinderwelten": kinderwelten_mod.einstellungen(einst.get("kinderwelten")),
                "news": self.news.fuer_eltern(),
                "heute": {"genutzt_min": z["genutzt_s"] // 60, "retropie_min": z["retropie_s"] // 60,
                          "apps_min": {k: v // 60 for k, v in z["app_s"].items()},
                          "bonus_min": z["bonus_min"], "ohne_limit": z["ohne_limit"],
                          "gaming_min": z["gaming_s"] // 60,
                          "gaming_rest_min": None if self.konto.gaming_rest_s(jetzt) is None
                          else self.konto.gaming_rest_s(jetzt) // 60,
                          "rest_min": None if self.konto.rest_s(jetzt) is None
                          else self.konto.rest_s(jetzt) // 60,
                          "tagesart": zeitkonto.tagesart(jetzt.date(), self._regeln())},
                "woche": daten.lies_json(self._pfad("woche.json"), {}) or {},
                "gesperrt": self.gesperrt_anzeige(jetzt),
                "familie": self.familie.einstellungen(),
                "bass_tagebuch": self.familie.bass_tagebuch(jetzt.date()),
                "sticker": self.familie.album(),
                "lernen_heute_min": self.familie.zustand["lern_s"] // 60
                if self.familie.zustand["lern_datum"] == jetzt.date().isoformat() else 0,
                "lernstand": self.familie.lernstand(),
                "domains": daten.lies_json(self._pfad("domains.json"), {}) or {},
                "adressen": self.lan_adressen(),
                "zeichnungen_gesehen": self.familie.zustand["zeichnungen_gesehen"],
                "meldungen": list(reversed(self.familie.zustand["meldungen"][-10:])),
                "zeit_pruefen": bool(self.einstellungen.get("zeit_pruefen")),
                "gutscheine": self.gutscheine.liste(),
                "wecker": self.wecker(),
                "youtube": self.youtube(),
                "sonder_bis": self.konto.zustand.get("sonder_bis") if self.konto.sonder_aktiv(jetzt) else None,
                "sperrzeiten_jetzt": [s["name"] for s, _ in zeitkonto.aktive_sperrzeiten(jetzt, self._regeln())],
            }

    def einstellungen_aendern(self, aenderungen):
        """Nur bekannte Felder mit passendem Typ. Zeitregeln werden vorher geprüft."""
        if not isinstance(aenderungen, dict):
            raise ValueError("Einstellungen müssen ein Objekt sein.")
        with self.lock:
            neu = copy.deepcopy(self.einstellungen)
            for feld, wert in aenderungen.items():
                typ = EINSTELLUNGEN_FELDER.get(feld)
                if typ is None or not isinstance(wert, typ):
                    raise ValueError("Unbekanntes oder falsches Feld: %s" % feld)
                neu[feld] = wert
            regeln = zeitkonto.neue_regeln(neu.get("zeit") or {})
            zeitkonto.pruefe_regeln(regeln)
            _pruefe_bass(neu.get("bass") or [])
            familie_mod.pruefe(neu.get("familie") or {})
            if "wecker" in neu:
                neu["wecker"] = wecker_mod.pruefe(neu["wecker"])
            if "youtube" in neu:
                youtube_mod.pruefe(neu["youtube"])
            _pruefe_inhalte(neu.get("inhalte") or {})
            _pruefe_startseite(neu.get("startseite") or {})
            kl = neu.get("klaenge") or {}
            if set(kl) - {"ordner"} or not isinstance(kl.get("ordner", ""), str) or \
                    (kl.get("ordner") and hoerbuch.pruefe_freigabe(kl["ordner"])):
                raise ValueError("Klang-Ordner " + (hoerbuch.pruefe_freigabe(kl.get("ordner", "")) or "ungültig."))
            for feld, pruefung in (("design", design_mod.pruefe), ("wetter", wetter_mod.pruefe), ("schule", schule_mod.pruefe),
                                   ("kinderwelten", kinderwelten_mod.pruefe), ("news", news_mod.pruefe)):
                if feld in aenderungen:
                    neu[feld] = pruefung(neu[feld])
            if "telegram" in aenderungen:
                t = dict(neu["telegram"])
                if t.get("token") == telegram_mod.VERSTECKT:      # Eltern-Seite zeigt den Token nie - alten behalten
                    t["token"] = (self.einstellungen.get("telegram") or {}).get("token", "")
                neu["telegram"] = telegram_mod.pruefe(t)
            _pruefe_sticker_eigen(neu.get("sticker_eigen") or [])
            whitelist.sammle(self.katalog, (neu.get("whitelist") or {}).get("zusatz", []))
            sp = neu.get("speicher") or {}
            if set(sp) - {"limit_mb"} or not (isinstance(sp.get("limit_mb", SPEICHER_VORGABE_MB), int) and
                                                10 <= sp.get("limit_mb", SPEICHER_VORGABE_MB) <= 5000):
                raise ValueError("Speicherplatz: 10 bis 5000 MB.")
            fa = neu.get("fotoalbum") or {}
            if set(fa) - {"erlaubt", "ordner", "bildschirmschoner", "auswahl"} or not isinstance(fa.get("erlaubt", False), bool) \
                    or not isinstance(fa.get("bildschirmschoner", False), bool) or not isinstance(fa.get("auswahl", []), list):
                raise ValueError("Fotoalbum: unbekannte oder ungültige Felder.")
            if fa.get("ordner") and hoerbuch.pruefe_freigabe(fa["ordner"]):
                raise ValueError("Foto-Ordner " + hoerbuch.pruefe_freigabe(fa["ordner"]))
            _pruefe_spielzimmer(neu.get("spielzimmer") or {})
            hs = neu.get("handyspiele") or {}
            if set(hs) - {"aktiv", "port"} or not isinstance(hs.get("aktiv", False), bool) or \
                    not (isinstance(hs.get("port", HANDYSPIELE_PORT), int) and 1024 < hs.get("port", HANDYSPIELE_PORT) < 65536):
                raise ValueError("Handy-Spiele: aktiv (ja/nein) und port (1025-65535).")
            lan = neu.get("eltern_lan") or {}

            ton = neu.get("ton") or {}
            if "max" in ton and (not isinstance(ton["max"], int) or not 20 <= ton["max"] <= 100):
                raise ValueError("Höchstlautstärke: 20 bis 100 %.")
            if not isinstance(ton.get("kopfhoerer_auto", True), bool):
                raise ValueError("Kopfhörer automatisch: ja oder nein.")
            if ton.get("ziel") not in (None, "hdmi", "klinke"):
                raise ValueError("Ton: Fernseher oder Klinke.")
            if not isinstance(lan.get("aktiv", False), bool) or \
                    not (isinstance(lan.get("port", 8766), int) and 1024 < lan.get("port", 8766) < 65536):
                raise ValueError("eltern_lan: aktiv (true/false) und port (1025-65535).")
            if "zeit" in aenderungen:
                neu.pop("zeit_pruefen", None)        # die Eltern haben die Regeln angesehen
            self.einstellungen = neu
            self.konto.regeln = regeln
            daten.schreibe_json(self._pfad("einstellungen.json"), neu)
        log.info("Einstellungen geändert: %s", ", ".join(sorted(aenderungen)))
        if "telegram" in aenderungen:
            self.telegram.neu_starten()
        if {"whitelist", "bass", "familie", "youtube"} & set(aenderungen):
            self.richtlinie_aktualisieren()

    # ------------------------------------------------------------ Ferien des Bundeslandes (4.6)
    def ferien_eintragen(self, land, feiertage=True, auto=False):
        """Ferien (und Feiertage) des Landes ab heute eintragen; eigene Einträge bleiben, Vergangenes fällt weg."""
        if land not in ferien_mod.LAENDER:
            raise ValueError("Bitte zuerst das Bundesland wählen.")
        heute = self.uhr().date()
        with self.lock:
            zeit = copy.deepcopy(self.einstellungen.get("zeit") or {})
            vorher = {tuple(z) for z in zeit.get("ferien", [])}
            zeit["ferien"] = ferien_mod.zusammenfuehren(zeit.get("ferien", []),
                                                        ferien_mod.zeitraeume(land, heute, bool(feiertage)), heute)
            zeit.update(bundesland=land, ferien_feiertage=bool(feiertage), ferien_auto=bool(auto))
            self.einstellungen_aendern({"zeit": zeit})
            neu = len({tuple(z) for z in zeit["ferien"]} - vorher)
        return {"neu": neu, "ferien": zeit["ferien"], "bekannt_bis": ferien_mod.bekannt_bis(),
                "land": ferien_mod.LAENDER[land]}

    def ferien_auffrischen(self):
        """Mit „jedes Jahr automatisch“: beim Start und an jedem neuen Tag fehlende Ferien ergänzen (neue Schuljahre
        kommen mit den Updates). Ändert die Regeln still, ohne den Hinweis „Regeln prüfen“ zu löschen."""
        regeln = self._regeln()
        if not regeln.get("ferien_auto") or regeln.get("bundesland") not in ferien_mod.LAENDER:
            return
        heute = self.uhr().date()
        try:
            neu = ferien_mod.zusammenfuehren(regeln["ferien"], ferien_mod.zeitraeume(
                regeln["bundesland"], heute, regeln.get("ferien_feiertage", True)), heute)
        except (OSError, ValueError) as fehler:
            log.warning("Ferien automatisch: %s", fehler)
            return
        if neu == regeln["ferien"]:
            return
        with self.lock:
            zeit = dict(self.einstellungen.get("zeit") or {}, ferien=neu)
            self.einstellungen["zeit"] = zeit
            self.konto.regeln = zeitkonto.neue_regeln(zeit)
            daten.schreibe_json(self._pfad("einstellungen.json"), self.einstellungen)
        log.info("Ferien automatisch aufgefrischt (%d Zeiträume).", len(neu))

    def katalog_aendern(self, eintraege):
        geprueft = katalog_mod.pruefe_katalog(eintraege)   # wirft KatalogFehler
        with self.lock:
            self.katalog = geprueft
            daten.schreibe_json(self._pfad("apps.json"), geprueft)
        log.info("App-Katalog geändert (%d Einträge).", len(geprueft))
        self.richtlinie_aktualisieren()

    def bonus(self, art):
        with self.lock:
            if art == "ohne_limit":
                self.konto.heute_ohne_limit(self.uhr())
            else:
                self.konto.bonus(self.uhr(), int(art))
            self.speichere_konto()
        self.melde("Mama oder Papa haben dir mehr Zeit geschenkt!")

    def sperren(self, text):
        with self.lock:
            self.gesperrt = {"text": (text or "Der Fernseher macht jetzt Pause.")[:120]}
            self.einstellungen["gesperrt"] = self.gesperrt
            daten.schreibe_json(self._pfad("einstellungen.json"), self.einstellungen)
        self.zurueck()

    # ------------------------------------------------------------ 5.3: Wartungsmodus beim Ausliefern
    # make v3-deploy legt nach der zweiten Bestätigung wartung.json in den Datenordner ({"ab": …, "bis": …}, Unix-Zeit),
    # make v3-pruefen löscht sie, wenn alles grün ist. Bis "ab" läuft eine Vorwarnung (Countdown in der Ecke, damit das Kind
    # noch speichern kann), danach: Warnbildschirm über allem, keine Taste, kein Start. Sicherheit: höchstens bis "bis"
    # (der Deploy setzt 45 Minuten), danach gilt die Datei nicht mehr.
    WARTUNG_MAX_S = 2 * 3600
    WARTUNG_VORWARNUNG_MAX_S = 60

    def wartung(self):
        """None, {"vorwarnung_s": …} (läuft noch, nichts gesperrt) oder {"rest_s": …} (gesperrt). Liest die Datei
        höchstens alle 2 Sekunden."""
        jetzt = time.time()
        if jetzt - getattr(self, "_wartung_gelesen", 0) >= 2:
            self._wartung_gelesen = jetzt
            roh = daten.lies_json(self._pfad("wartung.json"), None)
            roh = roh if isinstance(roh, dict) else {}
            bis, ab = roh.get("bis"), roh.get("ab")
            self._wartung_bis = min(float(bis), jetzt + self.WARTUNG_MAX_S) if isinstance(bis, (int, float)) else None
            self._wartung_ab = min(float(ab), jetzt + self.WARTUNG_VORWARNUNG_MAX_S) if isinstance(ab, (int, float)) else None
        bis, ab = getattr(self, "_wartung_bis", None), getattr(self, "_wartung_ab", None)
        if not bis or jetzt >= bis:
            self._wartung_gemeldet = False
            return None
        if ab and jetzt < ab:
            if not getattr(self, "_wartung_gemeldet", False):          # einmal: auch im Retro-Spiel ankündigen
                self._wartung_gemeldet = True
                text = "Gleich kommt ein Update - jetzt schnell speichern!"
                self.melde(text)
                self.auftrag("hinweis", text=text)                     # auch über Plex und Webseiten
                try:
                    if self.system.retropie_zustand()[0]:
                        self.system.retroarch("SHOW_MSG " + text)
                except Exception:   # noqa: BLE001 - die Vorwarnung darf nichts stören
                    log.exception("Vorwarnung")
            return {"vorwarnung_s": int(ab - jetzt) + 1}
        return {"rest_s": int(bis - jetzt)}

    # ------------------------------------------------------------ 5.3: Nachricht von der Eltern-Seite mit Absender
    def eltern_nachricht(self, text, von=None):
        """von = Chat-Nummer eines Eltern-Kontakts aus Telegram: dann steht dessen Symbol und Name am Fernseher und es
        klingt sein Klang. Ohne Absender wie bisher „Nachricht von Mama oder Papa“ mit dem Klang für Eltern-Nachrichten."""
        if von not in (None, ""):
            kontakt = next((c for c in self.telegram.einstellungen()["chats"] if c["id"] == von and c["eltern"]), None)
            if not kontakt:
                raise ValueError("Unbekannter Absender.")
            return self.familie.nachricht(text, quelle=kontakt["name"], bleibt=True, symbol=kontakt["symbol"],
                                          klang=kontakt.get("klang") or self.familie.einstellungen().get("klang_nachricht"))
        return self.familie.nachricht(text, bleibt=True, klang=self.familie.einstellungen().get("klang_nachricht"))

    # ------------------------------------------------------------ 5.2: Klang am Fernseher probehören
    def klang_testen(self, klang):
        if klang not in klaenge_mod.ARCHIV and not klaenge_mod.eigen_pfad(klang):
            raise ValueError("Unbekannter Klang.")
        self.klang_spielen(klang, warten=True)

    # ------------------------------------------------------------ 6.0: eigene Klänge aus einem Ordner der Eltern
    KLANG_MAX_BYTES = 4 * 1024 * 1024

    def klaenge_ordner(self):
        return str((self.einstellungen.get("klaenge") or {}).get("ordner") or "")

    def klaenge_eigen(self):
        """[{id, name}] der Audiodateien im Klang-Ordner (oberste Ebene)."""
        link = self.klaenge_ordner()
        if not link:
            return []
        try:
            titel = hoerbuch.liste(link, "")["titel"]
        except hoerbuch.HoerbuchFehler as fehler:
            raise ValueError("Der Klang-Ordner ist gerade nicht erreichbar (%s)." % fehler) from None
        return [{"id": klaenge_mod.EIGEN + t["pfad"], "name": t["name"].rsplit(".", 1)[0]} for t in titel
                if t["name"].lower().endswith(klaenge_mod.EIGEN_ENDUNGEN)][:200]

    def klang_eigen_adresse(self, klang):
        pfad = klaenge_mod.eigen_pfad(klang)
        link = self.klaenge_ordner()
        if not pfad or not link:
            raise ValueError("Unbekannter Klang.")
        return hoerbuch.datei_adresse(link, pfad, endungen=klaenge_mod.EIGEN_ENDUNGEN)

    def _eigene_klangdatei(self, klang):
        """Lokale Kopie eines eigenen Klangs (einmal heruntergeladen, höchstens 4 MB)."""
        import hashlib
        adresse = self.klang_eigen_adresse(klang)
        endung = os.path.splitext(klaenge_mod.eigen_pfad(klang))[1].lower()
        ordner = self._pfad("klang-cache")
        os.makedirs(ordner, exist_ok=True)
        pfad = os.path.join(ordner, hashlib.sha1(adresse.encode()).hexdigest()[:20] + endung)
        if not os.path.exists(pfad):
            with urllib.request.urlopen(urllib.request.Request(adresse, headers={"User-Agent": "FernsehFranzi"}), timeout=15) as a:
                inhalt = a.read(self.KLANG_MAX_BYTES + 1)
            if len(inhalt) > self.KLANG_MAX_BYTES:
                raise ValueError("Der Klang ist zu groß (höchstens 4 MB).")
            with open(pfad + ".neu", "wb") as f:
                f.write(inhalt)
            os.replace(pfad + ".neu", pfad)
        return pfad

    def klang_spielen(self, klang, warten=False):
        """Klang aus dem Archiv oder eigener Klang; geht ein eigener nicht, kommt der Gong."""
        if not klaenge_mod.eigen_pfad(klang):
            self.system.gong(klang)
            return

        def lauf():
            try:
                self.system.gong_datei(self._eigene_klangdatei(klang))
            except (OSError, ValueError) as fehler:
                log.warning("Eigener Klang %s: %s", klang, fehler)
                self.system.gong()
                if warten:
                    raise ValueError(str(fehler)) from None
        if warten:
            lauf()
        else:
            threading.Thread(target=lauf, daemon=True, name="klang").start()

    # ------------------------------------------------------------ 5.1: Auszeit = Sperre mit Countdown
    AUSZEIT_MAX_MIN = 240

    def auszeit(self, minuten):
        """Alles gesperrt, am Fernseher nur ein Countdown; danach von selbst wieder frei. Erneut aufgerufen verlängert sie
        sich (bei laufender Auszeit ab dem bisherigen Ende)."""
        if isinstance(minuten, bool) or not isinstance(minuten, int) or not 1 <= minuten <= self.AUSZEIT_MAX_MIN:
            raise ValueError("Auszeit: 1 bis %d Minuten." % self.AUSZEIT_MAX_MIN)
        jetzt = self.uhr().replace(microsecond=0)
        with self.lock:
            alt = self.auszeit_bis()
            start = alt if alt and alt > jetzt else jetzt
            bis = min(start + timedelta(minutes=minuten), jetzt + timedelta(minutes=self.AUSZEIT_MAX_MIN))
            neu = not self.gesperrt
            self.gesperrt = {"text": "Auszeit – gleich geht es weiter.", "auszeit": True, "bis": bis.isoformat()}
            self.einstellungen["gesperrt"] = self.gesperrt
            daten.schreibe_json(self._pfad("einstellungen.json"), self.einstellungen)
        log.info("Auszeit bis %s", bis.strftime("%H:%M:%S"))
        if neu:
            self.zurueck()
        return {"bis": bis.strftime("%H:%M"), "rest_s": int((bis - jetzt).total_seconds())}

    def auszeit_bis(self):
        g = self.gesperrt or {}
        if not g.get("auszeit"):
            return None
        try:
            return datetime.fromisoformat(g["bis"])
        except (KeyError, TypeError, ValueError):
            return None

    def _auszeit_takt(self, jetzt):
        bis = self.auszeit_bis()
        if bis and jetzt >= bis:
            log.info("Auszeit vorbei.")
            self.entsperren("Die Auszeit ist vorbei – weiter geht's!")

    def gesperrt_anzeige(self, jetzt=None):
        """Für Startseite und Eltern-Seite: Sperre mit der Restzeit einer Auszeit in Sekunden."""
        if not self.gesperrt:
            return None
        bis = self.auszeit_bis()
        if not bis:
            return dict(self.gesperrt)
        rest = max(0, int((bis - (jetzt or self.uhr())).total_seconds()))
        return dict(self.gesperrt, rest_s=rest, bis_uhr=bis.strftime("%H:%M"))

    def entsperren(self, meldung="Der Fernseher ist wieder frei."):
        with self.lock:
            self.gesperrt = None
            self.einstellungen.pop("gesperrt", None)
            daten.schreibe_json(self._pfad("einstellungen.json"), self.einstellungen)
        self.melde(meldung)

    def richtlinie_aktualisieren(self):
        """Browser-Whitelist (Kap. 12, zweite Schicht) an Chromium geben: Wunschliste schreiben,
        root-Helfer prüft und setzt sie als Richtlinie. Startadressen der Web-Apps sind immer erlaubt."""
        from urllib.parse import urlsplit
        with self.lock:
            w = self.einstellungen.get("whitelist") or {}
            domains = whitelist.sammle(self.katalog, w.get("zusatz", []))
            starts = [app.get("start", "") for app in self.katalog if app.get("typ") == "web"]
            links = list(self._bass_links())
            for adresse in starts + links:
                host = urlsplit(adresse).hostname
                if host and host not in domains:
                    domains.append(host)
            domains += [d for d in UG_DOMAINS if d not in domains]
            youtube_bereich = any(a.get("typ") == "youtube" and a.get("aktiv", True) for a in self.katalog)
            if youtube_bereich or any(youtube_player(l) != l for l in links):
                domains += [d for d in YOUTUBE_DOMAINS if d not in domains]
            daten.schreibe_json(self._pfad("whitelist-richtlinie.json"),
                                {"aktiv": bool(w.get("browser_sperre", True)), "domains": domains})
        return self.system.richtlinie()

    def whitelist_export(self, format_):
        domains = whitelist.sammle(self.katalog, (self.einstellungen.get("whitelist") or {}).get("zusatz", []))
        if format_ == "pihole":
            return whitelist.export_pihole(domains)
        if format_ == "fritzbox":
            return whitelist.export_fritzbox(domains)
        return "\n".join(domains) + "\n"

    def woche_fortschreiben(self):
        """Einmal pro Tag: gestrige Nutzung in die Wochenübersicht (7 Tage)."""
        with self.lock:
            z = self.konto.zustand
            if not z.get("datum"):
                return
            woche = daten.lies_json(self._pfad("woche.json"), {}) or {}
            woche[z["datum"]] = {"genutzt_min": z.get("genutzt_s", 0) // 60,
                                 "retropie_min": z.get("retropie_s", 0) // 60}
            for alt in sorted(woche)[:-7]:
                del woche[alt]
            daten.schreibe_json(self._pfad("woche.json"), woche)


# YouTube (Bass-Songs): als reinen Player öffnen - ohne Kommentare, Empfehlungen, Werbe-Seite; leichter für den Pi 3.
YOUTUBE_ID = re.compile(r"^(?:https?://)?(?:www\.|m\.)?(?:youtube\.com/watch\?(?:.*&)?v=|youtu\.be/)([A-Za-z0-9_-]{11})")
# Ohne diese Hosts bleibt der Player bei aktiver Browser-Whitelist schwarz (Video-Server, Bilder, Skripte).
# 3.5: Song-Suche der Musik-Akademie (Akkorde/Tabs) - nur diese Seite, nur aus der Akademie heraus
UG_DOMAINS = ["www.ultimate-guitar.com", "ultimate-guitar.com", "tabs.ultimate-guitar.com"]
UG_SUCHE = "https://www.ultimate-guitar.com/search.php?search_type=title&value=%s"
YOUTUBE_DOMAINS = ["www.youtube-nocookie.com", "www.youtube.com", "youtube.com", "googlevideo.com", "ytimg.com",
                   "ggpht.com", "gstatic.com", "googleapis.com"]


def youtube_player(url):
    treffer = YOUTUBE_ID.match(url or "")
    if not treffer:
        return url
    return "https://www.youtube-nocookie.com/embed/%s?autoplay=1&rel=0&modestbranding=1&playsinline=1" % treffer.group(1)


def _gleicher_ursprung(url, start):
    from urllib.parse import urlsplit
    a, b = urlsplit(url), urlsplit(start)
    return (a.scheme, a.hostname, a.port) == (b.scheme, b.hostname, b.port)


def _pruefe_bass(songs):
    from urllib.parse import urlsplit
    if len(songs) > BASS_MAX:
        raise ValueError("Höchstens %d Bass-Songs." % BASS_MAX)
    for nr, song in enumerate(songs, 1):
        if not isinstance(song, dict) or not str(song.get("titel", "")).strip():
            raise ValueError("Bass-Song %d: Titel fehlt." % nr)
        if len(song["titel"]) > 80:
            raise ValueError("Bass-Song %d: Titel zu lang." % nr)
        for art in BASS_ARTEN:
            adresse = song.get(art, "")
            if adresse and (not isinstance(adresse, str) or urlsplit(adresse).scheme not in ("http", "https")
                            or not urlsplit(adresse).hostname):
                raise ValueError("Bass-Song %d (%s): keine gültige http(s)-Adresse." % (nr, song["titel"]))
        unbekannt = set(song) - {"titel"} - set(BASS_ARTEN)
        if unbekannt:
            raise ValueError("Bass-Song %d: unbekannte Felder %s." % (nr, ", ".join(sorted(unbekannt))))


def _text(wert, wo, laenge=120):
    if not isinstance(wert, str) or not wert.strip() or len(wert) > laenge:
        raise ValueError("%s: Text fehlt oder ist länger als %d Zeichen." % (wo, laenge))


def _pruefe_inhalte(inhalte):
    """3.5: eigene Witze und Quizfragen der Eltern."""
    if not isinstance(inhalte, dict) or set(inhalte) - {"witze", "quiz"}:
        raise ValueError("Inhalte: unbekannte Felder.")
    witze, quiz = inhalte.get("witze", []), inhalte.get("quiz", [])
    if not isinstance(witze, list) or not isinstance(quiz, list) or len(witze) > 200 or len(quiz) > 200:
        raise ValueError("Höchstens 200 Witze und 200 Quizfragen.")
    for nr, w in enumerate(witze, 1):
        if not isinstance(w, dict) or set(w) - {"frage", "pointe"}:
            raise ValueError("Witz %d: unbekannte Felder." % nr)
        _text(w.get("frage"), "Witz %d" % nr)
        _text(w.get("pointe"), "Witz %d (Pointe)" % nr)
    for nr, q in enumerate(quiz, 1):
        if not isinstance(q, dict) or set(q) - {"frage", "richtig", "falsch"}:
            raise ValueError("Quizfrage %d: unbekannte Felder." % nr)
        _text(q.get("frage"), "Quizfrage %d" % nr)
        _text(q.get("richtig"), "Quizfrage %d (richtig)" % nr, 60)
        falsch = q.get("falsch")
        if not isinstance(falsch, list) or len(falsch) != 3:
            raise ValueError("Quizfrage %d: genau drei falsche Antworten." % nr)
        for f in falsch:
            _text(f, "Quizfrage %d (falsch)" % nr, 60)


def _pruefe_sticker_eigen(sticker):
    """3.5: eigene Sticker der Eltern (vergeben von Hand auf der Eltern-Seite)."""
    if not isinstance(sticker, list) or len(sticker) > 30:
        raise ValueError("Höchstens 30 eigene Sticker.")
    ids = set()
    for nr, s in enumerate(sticker, 1):
        if not isinstance(s, dict) or set(s) - {"id", "name", "symbol", "bedingung"}:
            raise ValueError("Sticker %d: unbekannte Felder." % nr)
        if not re.fullmatch(r"eigen-[a-z0-9]{1,12}", str(s.get("id", ""))) or s["id"] in ids:
            raise ValueError("Sticker %d: ungültige Kennung." % nr)
        ids.add(s["id"])
        _text(s.get("name"), "Sticker %d" % nr, 30)
        _text(s.get("symbol"), "Sticker %d (Symbol)" % nr, 8)
        if s.get("bedingung"):
            _text(s["bedingung"], "Sticker %d (wofür)" % nr, 80)


THEMEN = design_mod.KENNUNGEN                # 5.0: helle und dunkle Designs (vorher nur dunkle Hintergründe)


def _karaoke_marken(marken):
    """4.6.1: Zeitmarken der Klassenkiste (Sekunde je gesungener Zeile, null = ohne Marke) - nur Zahlen oder null."""
    if not isinstance(marken, list) or not 0 < len(marken) <= 2000:
        return None
    aus = [round(float(m), 2) if isinstance(m, (int, float)) and not isinstance(m, bool) and 0 <= m < 36000 else None
           for m in marken]
    return aus if any(m is not None for m in aus) else None


SPIELZIMMER_FELDER = {"aktiv", "zeit", "limit_min", "sperr_erlaubt", "bewegung"}


def _pruefe_spielzimmer(eigen):
    """4.6: Einstellungen der Eltern zu den eingebauten Spielen und Kacheln - dieselben Regeln wie im App-Katalog."""
    ids = {e["id"]: e for e in SPIELZIMMER}
    for app_id, werte in eigen.items():
        if app_id not in ids:
            raise ValueError("Unbekanntes Spiel: %s" % app_id)
        if not isinstance(werte, dict) or set(werte) - SPIELZIMMER_FELDER:
            raise ValueError("%s: nur %s." % (ids[app_id]["name"], ", ".join(sorted(SPIELZIMMER_FELDER))))
        probe = dict(ids[app_id], typ="web", start="", **werte)
        fehler = katalog_mod._pruefe_eintrag(probe, 1)
        if fehler:
            raise ValueError(fehler[0].replace("App '%s'" % app_id, ids[app_id]["name"]))


def _pruefe_startseite(st):
    """4.0: vom Kind gestaltet - Lieblinge (App-Kennungen) und Hintergrund."""
    if not isinstance(st, dict) or set(st) - {"lieblinge", "thema", "ansicht"}:
        raise ValueError("Startseite: unbekannte Felder.")
    lieblinge = st.get("lieblinge", [])
    if not isinstance(lieblinge, list) or len(lieblinge) > 12 or not all(
            isinstance(x, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,31}", x) for x in lieblinge):
        raise ValueError("Startseite: höchstens 12 Lieblinge.")
    if st.get("thema", "blau") not in THEMEN:
        raise ValueError("Startseite: unbekanntes Design.")
    if st.get("ansicht", "konsole") not in design_mod.ANSICHT_IDS:
        raise ValueError("Startseite: unbekannte Ansicht.")

