"""FernsehFranzi 4.0 - Telegram: Nachrichten der Familie ans TV, das Kind antwortet mit vorbereiteten Texten.

Einstellungen (einstellungen.json, Feld "telegram"; der Token steht nur auf dem Gerät, nie im Repo):
    {"aktiv": true, "token": "123:ABC…", "chats": [{"id": 123456, "name": "Papa"}],
     "antworten": ["👍 Okay!", "Komme gleich!", …], "eigene_texte": true}
4.1: Mit "eigene_texte" darf das Kind auch selbst getippte Texte schicken (Tastatur, höchstens 300 Zeichen).
Nur Nachrichten aus erlaubten Chats kommen an. Unbekannte Chats werden gemerkt (Eltern-Seite: „Erlauben“).
Abgerufen wird per Long-Polling (getUpdates) in einem eigenen Thread - keine offene Tür nach außen.

4.3: Kontakte mit Grenzen. Je Chat: "symbol" (Emoji am TV), "eltern" (darf alles), "darf_schreiben" (das Kind kann
diesem Kontakt schreiben), "eigene_texte" (frei getippte Texte an ihn), "nur_freizeit" (seine Nachrichten warten in
Sperrzeiten, bis die Sperrzeit vorbei ist). Alte Einträge ohne diese Felder sind Eltern (so waren sie gemeint).
Neue Kontakte legt die Eltern-Seite streng an (empfangen ja, schreiben aus). Ein- und ausgehende Nachrichten stehen je
Kontakt im Verlauf (telegram-verlauf.json, die letzten 50 je Kontakt, höchstens 30 Tage) - die Eltern lesen mit.
Der Verlauf ist nicht in der Sicherung.

4.4: Fotos, Sprachnachrichten, Musik und kurze Videos kommen ans TV (Recht je Kontakt "medien"; Eltern dürfen immer).
Gespeichert in <daten>/medien/, nach MEDIEN_TAGE Tagen (und über MEDIEN_MAX_MB) löscht der Pi sie selbst. Was das
Kind ins Album übernimmt, wandert nach <daten>/album/ und bleibt (zählt zum Speicherplatz des Kindes).
"""
import json
import logging
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.request
from datetime import timedelta

from . import daten as daten_mod, zeitkonto

log = logging.getLogger("fernsehfranzi.telegram")

BASIS = "https://api.telegram.org"          # Tests setzen hier eine Attrappe ein
VORGABE = {"aktiv": False, "token": "", "chats": [], "antworten": [
    "👍 Okay!", "Komme gleich!", "Bin fertig!", "Ich hab dich lieb ❤️", "Kannst du kurz kommen?", "Gute Nacht 🌙"],
    "eigene_texte": True, "bericht_uhr": "19:30", "sperrzeit_still": True}
EIGENER_TEXT_MAX = 300
VERSTECKT = "••••••••"                       # so zeigt die Eltern-Seite einen gesetzten Token
SENDEN_ABSTAND_S = 10
SENDEN_PRO_TAG = 40
KONTAKT_FELDER = {"id", "name", "symbol", "eltern", "darf_schreiben", "eigene_texte", "nur_freizeit", "medien", "meldungen"}
KONTAKT_ALT = {"symbol": "💬", "eltern": True, "darf_schreiben": True, "eigene_texte": True, "nur_freizeit": False,
               "medien": True}
KONTAKT_NEU = {"symbol": "💬", "eltern": False, "darf_schreiben": False, "eigene_texte": False, "nur_freizeit": True,
               "medien": False}
MELDUNG_ARTEN = {"zeit": "Spielzeit aufgebraucht, Sperrzeit beginnt", "freunde": "Nachrichten mit Freunden",
                 "gutschein": "Gutschein eingelöst", "wecker": "Wecker ausgeschaltet", "gelesen": "Nachricht gelesen",
                 "bericht": "Tagesbericht am Abend", "schule": "Klassenkiste: Neues und Morgen-Check"}
MEDIEN_TAGE = 7
MEDIEN_MAX_MB = 200
DATEI_MAX = 20 * 1024 * 1024                 # mehr gibt die Bot-Schnittstelle ohnehin nicht heraus
MEDIUM_NAME = re.compile(r"m[0-9]{10}-[a-z0-9]{6}\.(jpg|ogg|mp3|mp4|m4a)\Z")
MEDIEN_TEXT = {"foto": "📷 Foto", "sprache": "🎙️ Sprachnachricht", "musik": "🎵 Musik", "video": "🎬 Video"}
VERLAUF_MAX = 50
VERLAUF_TAGE = 30


def kontakt(c):
    """Ein Chat mit allen Feldern. Fehlt "eltern", ist es ein Eintrag von vor 4.3 = Eltern."""
    voll = dict(KONTAKT_ALT if "eltern" not in c else KONTAKT_NEU)
    voll.update(c)
    return voll


def einstellungen(gespeichert):
    t = dict(VORGABE)
    t.update(gespeichert or {})
    t["chats"] = [kontakt(c) for c in t["chats"] if isinstance(c, dict)] if isinstance(t["chats"], list) else t["chats"]
    return t


def pruefe(t):
    if not isinstance(t, dict) or set(t) - set(VORGABE):
        raise ValueError("Telegram: unbekannte Felder.")
    t = einstellungen(t)
    if not isinstance(t["aktiv"], bool):
        raise ValueError("Telegram: an/aus muss ja/nein sein.")
    if t["token"] and (not isinstance(t["token"], str) or ":" not in t["token"] or len(t["token"]) > 100):
        raise ValueError("Telegram: Der Bot-Token sieht nicht richtig aus (Zahl:Buchstaben von @BotFather).")
    if not isinstance(t["bericht_uhr"], str) or not re.fullmatch(r"([01][0-9]|2[0-3]):[0-5][0-9]", t["bericht_uhr"]):
        raise ValueError("Telegram: Uhrzeit des Tagesberichts als HH:MM.")
    if not isinstance(t["sperrzeit_still"], bool):
        raise ValueError("Telegram: „in Sperrzeiten ohne Ton“ muss ja/nein sein.")
    if not isinstance(t["eigene_texte"], bool):
        raise ValueError("Telegram: eigene Texte muss ja/nein sein.")
    if t["aktiv"] and not t["token"]:
        raise ValueError("Telegram: Bitte zuerst den Bot-Token eintragen.")
    if not isinstance(t["chats"], list) or len(t["chats"]) > 10:
        raise ValueError("Telegram: höchstens 10 Chats.")
    for c in t["chats"]:
        if not isinstance(c, dict) or not isinstance(c.get("id"), int) or not str(c.get("name", "")).strip() \
                or len(str(c["name"])) > 30:
            raise ValueError("Telegram: Chat braucht eine Nummer und einen Namen.")
        if set(c) - KONTAKT_FELDER:
            raise ValueError("Telegram: unbekannte Felder bei %s." % str(c["name"])[:30])
        if not all(isinstance(c[f], bool) for f in ("eltern", "darf_schreiben", "eigene_texte", "nur_freizeit", "medien")):
            raise ValueError("Telegram: Die Schalter bei %s müssen ja/nein sein." % c["name"])
        if "meldungen" in c and (not isinstance(c["meldungen"], dict) or set(c["meldungen"]) - set(MELDUNG_ARTEN) or
                                 not all(isinstance(v, bool) for v in c["meldungen"].values())):
            raise ValueError("Telegram: Meldungen bei %s sind ungültig." % c["name"])
        if not isinstance(c["symbol"], str) or not c["symbol"].strip() or len(c["symbol"]) > 8:
            raise ValueError("Telegram: Symbol bei %s fehlt oder ist zu lang." % c["name"])
    if len({c["id"] for c in t["chats"]}) != len(t["chats"]):
        raise ValueError("Telegram: Jeder Chat nur einmal.")
    if not isinstance(t["antworten"], list) or len(t["antworten"]) > 12 or \
            not all(isinstance(a, str) and a.strip() and len(a) <= 60 for a in t["antworten"]):
        raise ValueError("Telegram: höchstens 12 Antworten, je höchstens 60 Zeichen.")
    return t


class Telegram:
    def __init__(self, hub):
        self.hub = hub
        self.unbekannt = []               # [{"id", "name", "text"}] - für die Eltern-Seite
        self._versatz = 0
        self._gesendet = []               # Zeitpunkte (monoton) - gegen zu viele Nachrichten
        self._lauf = None
        self._halt = threading.Event()
        self._sperre = threading.Lock()
        self._verlauf_pfad = os.path.join(hub.ordner, "telegram-verlauf.json")
        gespeichert = daten_mod.lies_json(self._verlauf_pfad, {}) or {}
        self.verlauf = gespeichert.get("kontakte", {}) if isinstance(gespeichert, dict) else {}
        self.wartend = gespeichert.get("wartend", []) if isinstance(gespeichert, dict) else []
        jetzt = hub.uhr()                         # nach einem Neustart am Abend nicht gleich noch einen Bericht
        self._bericht_tag = jetzt.date().isoformat() if jetzt.strftime("%H:%M") >= self.einstellungen()["bericht_uhr"] else None

    def einstellungen(self):
        return einstellungen(self.hub.einstellungen.get("telegram"))

    def aktiv(self):
        t = self.einstellungen()
        return bool(t["aktiv"] and t["token"])

    # ------------------------------------------------------------ Thread
    def neu_starten(self):
        self._halt.set()
        if self._lauf and self._lauf.is_alive():
            self._lauf.join(timeout=2)
        self._halt = threading.Event()
        if self.aktiv():
            self._lauf = threading.Thread(target=self._schleife, args=(self._halt,), daemon=True, name="telegram")
            self._lauf.start()

    def _aufruf(self, methode, daten, timeout=40):
        t = self.einstellungen()
        anfrage = urllib.request.Request("%s/bot%s/%s" % (BASIS, t["token"], methode),
                                         data=json.dumps(daten).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
            ergebnis = json.loads(antwort.read().decode("utf-8"))
        if not ergebnis.get("ok"):
            raise OSError(ergebnis.get("description", "Telegram-Fehler"))
        return ergebnis.get("result")

    def _schleife(self, halt):
        pause = 1
        while not halt.is_set():
            try:
                for u in self._aufruf("getUpdates", {"offset": self._versatz, "timeout": 25}) or []:
                    self._versatz = max(self._versatz, int(u.get("update_id", 0)) + 1)
                    self.empfangen(u.get("message") or {})
                pause = 1
            except (OSError, ValueError) as fehler:
                log.warning("Telegram: %s", str(fehler).replace(self.einstellungen()["token"], "…"))
                halt.wait(pause)
                pause = min(pause * 2, 300)

    # ------------------------------------------------------------ 4.3: Kontakte, Verlauf, Freizeit
    def kontakt_von(self, chat_id):
        return next((c for c in self.einstellungen()["chats"] if c["id"] == chat_id), None)

    def schreibbar(self):
        """Kontakte, denen das Kind schreiben darf. 4.4: Freunde mit „nur außerhalb der Sperrzeiten“ in Sperrzeiten nicht."""
        sperre = self._sperrzeit_jetzt()
        return [c for c in self.einstellungen()["chats"]
                if c["eltern"] or (c["darf_schreiben"] and not (c["nur_freizeit"] and sperre))]

    def gesperrte_chats(self):
        """4.4: Freunde, deren Nachrichten gerade (Sperrzeit) nicht gelesen werden dürfen - nur gezählt."""
        if not self._sperrzeit_jetzt():
            return set()
        return {c["id"] for c in self.einstellungen()["chats"] if not c["eltern"] and c["nur_freizeit"]}

    def _sperrzeit_jetzt(self):
        jetzt = self.hub.uhr()
        return bool(zeitkonto.aktive_sperrzeiten(jetzt, self.hub.konto.regeln)) and not self.hub.konto.sonder_aktiv(jetzt)

    def _speichern(self):
        daten_mod.schreibe_json(self._verlauf_pfad, {"kontakte": self.verlauf, "wartend": self.wartend})

    def _merke(self, chat_id, richtung, text, wartet=False, medium=None):
        grenze = (self.hub.uhr() - timedelta(days=VERLAUF_TAGE)).isoformat(timespec="seconds")
        with self._sperre:
            liste = [e for e in self.verlauf.get(str(chat_id), []) if e.get("zeit", "") >= grenze]
            eintrag = {"zeit": self.hub.uhr().isoformat(timespec="seconds"), "richtung": richtung, "text": text[:EIGENER_TEXT_MAX]}
            if wartet:
                eintrag["wartet"] = True
            if medium:
                eintrag["medium"] = medium
            liste.append(eintrag)
            self.verlauf[str(chat_id)] = liste[-VERLAUF_MAX:]
            self._speichern()

    def verlauf_fuer_eltern(self):
        namen = {str(c["id"]): c for c in self.einstellungen()["chats"]}
        return [{"id": int(k), "name": namen[k]["name"], "symbol": namen[k]["symbol"], "nachrichten": list(v)}
                for k, v in self.verlauf.items() if k in namen and v]

    def fuer_tv(self):
        t = self.einstellungen()
        return {"aktiv": self.aktiv(), "antworten": t["antworten"], "eigene_texte": t["eigene_texte"],
                "kontakte": [{"id": c["id"], "name": c["name"], "symbol": c["symbol"],
                              "eigene_texte": bool(t["eigene_texte"] and (c["eltern"] or c["eigene_texte"]))}
                             for c in self.schreibbar()]}

    def _zeigen(self, c, text, medium=None):
        self.hub.familie.nachricht(text, quelle=c["name"], bleibt=True, chat=c["id"], symbol=c["symbol"], medium=medium)

    # ------------------------------------------------------------ 4.4: Meldungen und Befehle für die Eltern
    def melde_eltern(self, art, text):
        """Kurze Meldung an alle Eltern-Kontakte, die diese Art nicht abgeschaltet haben (im Hintergrund)."""
        if not self.aktiv():
            return []
        ziele = [c for c in self.einstellungen()["chats"] if c["eltern"] and (c.get("meldungen") or {}).get(art, True)]

        def senden():
            for c in ziele:
                try:
                    self._aufruf("sendMessage", {"chat_id": c["id"], "text": "📺 " + text}, timeout=15)
                except (OSError, ValueError) as fehler:
                    log.warning("Telegram-Meldung: %s", str(fehler).replace(self.einstellungen()["token"], "…"))
        if ziele:
            threading.Thread(target=senden, daemon=True, name="telegram-meldung").start()
        return [c["name"] for c in ziele]

    def gelesen(self, meldungen):
        """Das Kind hat Nachrichten am Fernseher bestätigt: dem Absender (Eltern) Bescheid geben."""
        for m in meldungen:
            c = self.kontakt_von(m.get("chat"))
            if c and c["eltern"] and (c.get("meldungen") or {}).get("gelesen", True) and self.aktiv():
                text = "✔ gelesen: „%s“" % str(m.get("text", ""))[:60]
                threading.Thread(target=self._aufruf_sicher, args=("sendMessage", {"chat_id": c["id"], "text": text}),
                                 daemon=True).start()

    def _aufruf_sicher(self, methode, daten):
        try:
            self._aufruf(methode, daten, timeout=15)
        except (OSError, ValueError) as fehler:
            log.warning("Telegram: %s", str(fehler).replace(self.einstellungen()["token"], "…"))

    HILFE = ("Befehle für Eltern:\n/status – Restzeit und was gerade läuft\n/zeit 15 · /zeit 30 · /zeit frei\n"
             "/sperren [Text] · /freigeben\n/gutenacht – Gute Nacht starten\n/aus – Fernseher aus\n"
             "/foto – Bild vom Fernseher\n/bericht – Tagesbericht jetzt")

    def antwort(self, c, text):
        self._aufruf_sicher("sendMessage", {"chat_id": c["id"], "text": text})

    def befehl(self, c, text):
        """Befehl eines Eltern-Kontakts (nur Eltern, siehe empfangen)."""
        teile = text.split(None, 1)
        name, rest = teile[0].lower().split("@")[0], (teile[1].strip() if len(teile) > 1 else "")
        h = self.hub
        try:
            if name in ("/start", "/hilfe", "/help"):
                return self.antwort(c, self.HILFE)
            if name == "/status":
                return self.antwort(c, self.status_text())
            if name == "/zeit":
                art = {"15": "15", "30": "30", "frei": "ohne_limit", "ohne": "ohne_limit"}.get(rest.lower())
                if not art:
                    return self.antwort(c, "So geht's: /zeit 15, /zeit 30 oder /zeit frei")
                h.bonus(art)
                return self.antwort(c, "✅ Erledigt. " + self.status_text(kurz=True))
            if name == "/sperren":
                h.sperren(rest or "Der Fernseher macht jetzt Pause.")
                return self.antwort(c, "🔒 Der Fernseher ist gesperrt.")
            if name == "/freigeben":
                h.entsperren()
                return self.antwort(c, "🔓 Der Fernseher ist wieder frei.")
            if name == "/gutenacht":
                h.gute_nacht_starten()
                return self.antwort(c, "🌙 Gute Nacht ist gestartet.")
            if name == "/aus":
                h.cec_befehl("standby")
                return self.antwort(c, "📴 Der Fernseher geht aus.")
            if name == "/foto":
                bild, fehler = h.bildschirmfoto()
                if bild is None:
                    return self.antwort(c, "📷 " + fehler)
                return self.sende_bild(c["id"], bild, "bild.jpg", "📷 So sieht der Fernseher gerade aus.")
            if name == "/bericht":
                return self.antwort(c, self.bericht_text())
            return self.antwort(c, "Diesen Befehl kenne ich nicht.\n\n" + self.HILFE)
        except ValueError as fehler:
            return self.antwort(c, "⚠️ " + str(fehler))

    def status_text(self, kurz=False):
        s = self.hub.status()
        rest = "ohne Limit" if s["rest_min"] is None else "%d Minuten" % s["rest_min"]
        zeilen = ["⏳ Übrig heute: %s" % rest]
        if kurz:
            return zeilen[0]
        app = self.hub.app(s["aktuell"]) if s["aktuell"] not in (None, "internet") else None
        zeilen.append("▶️ Gerade: %s" % (app["name"] if app else "Internet" if s["aktuell"] == "internet" else "Startseite"))
        if s["gesperrt"]:
            zeilen.append("🔒 Gesperrt: %s" % s["gesperrt"].get("text", ""))
        zeilen.append("🔊 Ton: %s" % {"hdmi": "Fernseher", "klinke": "Klinke", "kopfhoerer": "Kopfhörer"}.get(s["ton"], s["ton"]))
        return "\n".join(zeilen)

    def bericht_text(self):
        jetzt = self.hub.uhr()
        tag = self.hub.nutzung.auszug(1).get(jetzt.date().isoformat(), {})
        namen = {e["id"]: e["name"] for e in self.hub.katalog}
        from . import kern as kern_mod                          # Spielzimmer-Namen (zur Laufzeit, kein Kreis beim Laden)
        namen.update({e["id"]: e["name"] for e in kern_mod.SPIELZIMMER})
        summen = sorted(((sum(w[0] for w in stunden.values()) // 60, app) for app, stunden in tag.items()), reverse=True)
        d = self.hub.eltern_daten()["heute"]
        zeilen = ["📊 Tagesbericht %s" % jetzt.strftime("%d.%m."),
                  "⏳ Mit Timer gespielt: %d min (Retro %d min), übrig: %s" % (
                      d["genutzt_min"], d["retropie_min"], "ohne Limit" if d["rest_min"] is None else "%d min" % d["rest_min"])]
        if summen:
            zeilen.append("📺 Am meisten: " + ", ".join("%s %d min" % (namen.get(a, a), m) for m, a in summen[:5] if m))
        else:
            zeilen.append("📺 Heute lief nichts.")
        return "\n".join(zeilen)

    def sende_bild(self, chat_id, roh, dateiname, text=""):
        """Ein Bild an einen Chat schicken (multipart/form-data, nur Standardbibliothek)."""
        grenze = "----FF" + secrets.token_hex(12)
        teile = []
        for name, wert in (("chat_id", str(chat_id)), ("caption", text[:900])):
            teile.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (grenze, name, wert)).encode())
        typ = "image/png" if dateiname.endswith(".png") else "image/jpeg"
        teile.append(("--%s\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
                      % (grenze, dateiname, typ)).encode() + roh + b"\r\n")
        teile.append(("--%s--\r\n" % grenze).encode())
        anfrage = urllib.request.Request("%s/bot%s/sendPhoto" % (BASIS, self.einstellungen()["token"]), data=b"".join(teile),
                                         headers={"Content-Type": "multipart/form-data; boundary=" + grenze})
        try:
            with urllib.request.urlopen(anfrage, timeout=30) as a:
                if not json.loads(a.read().decode()).get("ok"):
                    raise OSError("Telegram hat das Bild abgelehnt.")
        except (OSError, ValueError) as fehler:
            log.warning("Telegram-Bild: %s", str(fehler).replace(self.einstellungen()["token"], "…"))
            return False
        return True

    def bericht_takt(self, jetzt):
        """Einmal am Tag zur eingestellten Uhrzeit den Tagesbericht an die Eltern (die ihn nicht abgeschaltet haben)."""
        if not self.aktiv():
            return
        uhr = self.einstellungen()["bericht_uhr"]
        heute = jetzt.date().isoformat()
        if jetzt.strftime("%H:%M") >= uhr and self._bericht_tag != heute:
            self._bericht_tag = heute
            self.melde_eltern("bericht", self.bericht_text())

    # ------------------------------------------------------------ 4.4: Fotos, Sprache, Musik, Videos
    @property
    def medien_ordner(self):
        return os.path.join(self.hub.ordner, "medien")

    def medium_pfad(self, name):
        if not MEDIUM_NAME.fullmatch(str(name or "")):
            return None
        pfad = os.path.join(self.medien_ordner, name)
        return pfad if os.path.isfile(pfad) else None

    @staticmethod
    def medium_von(nachricht):
        """(art, file_id, endung, größe) aus einer Telegram-Nachricht oder None."""
        if nachricht.get("photo"):
            fotos = [p for p in nachricht["photo"] if isinstance(p, dict) and (p.get("file_size") or 0) <= DATEI_MAX]
            passend = [p for p in fotos if max(p.get("width", 0), p.get("height", 0)) <= 1600] or fotos
            if passend:
                p = max(passend, key=lambda x: x.get("width", 0) * x.get("height", 0))
                return "foto", p.get("file_id"), "jpg", p.get("file_size") or 0
        for feld, art, endung in (("voice", "sprache", "ogg"), ("audio", "musik", "mp3"), ("video", "video", "mp4"),
                                  ("video_note", "video", "mp4")):
            d = nachricht.get(feld)
            if isinstance(d, dict) and d.get("file_id"):
                if feld == "audio" and str(d.get("mime_type", "")).endswith(("mp4", "m4a", "aac")):
                    endung = "m4a"
                return art, d["file_id"], endung, d.get("file_size") or 0
        return None

    def _herunterladen(self, file_id, endung):
        info = self._aufruf("getFile", {"file_id": file_id}, timeout=20) or {}
        weg = str(info.get("file_path") or "")
        if not weg or (info.get("file_size") or 0) > DATEI_MAX or ".." in weg:
            raise ValueError("Datei zu groß oder nicht abrufbar.")
        adresse = "%s/file/bot%s/%s" % (BASIS, self.einstellungen()["token"], weg)
        with urllib.request.urlopen(adresse, timeout=60) as antwort:
            roh = antwort.read(DATEI_MAX + 1)
        if len(roh) > DATEI_MAX:
            raise ValueError("Datei zu groß.")
        os.makedirs(self.medien_ordner, exist_ok=True)
        name = "m%010d-%s.%s" % (int(time.time()), secrets.token_hex(3), endung)
        with open(os.path.join(self.medien_ordner, name), "wb") as f:
            f.write(roh)
        self.aufraeumen()
        return name

    def aufraeumen(self, jetzt=None):
        """Medien älter als MEDIEN_TAGE löschen, dann die ältesten, bis höchstens MEDIEN_MAX_MB übrig sind."""
        if not os.path.isdir(self.medien_ordner):
            return 0
        jetzt = jetzt or time.time()
        dateien = sorted((os.path.getmtime(os.path.join(self.medien_ordner, n)), n) for n in os.listdir(self.medien_ordner)
                         if MEDIUM_NAME.fullmatch(n))
        geloescht, summe = 0, sum(os.path.getsize(os.path.join(self.medien_ordner, n)) for _, n in dateien)
        for zeit, n in dateien:
            pfad = os.path.join(self.medien_ordner, n)
            if jetzt - zeit > MEDIEN_TAGE * 86400 or summe > MEDIEN_MAX_MB * 1024 * 1024:
                summe -= os.path.getsize(pfad)
                os.remove(pfad)
                geloescht += 1
        return geloescht

    def tick(self):
        """Wartende Nachrichten (nur_freizeit) zeigen, sobald keine Sperrzeit mehr gilt; Tagesbericht; Aufräumen."""
        jetzt = self.hub.uhr()
        self.bericht_takt(jetzt)
        if getattr(self, "_aufgeraeumt", None) != jetzt.date():
            self._aufgeraeumt = jetzt.date()
            self.aufraeumen()
        if not self.wartend or self._sperrzeit_jetzt():
            return
        with self._sperre:
            jetzt, self.wartend = self.wartend, []
            self._speichern()
        for w in jetzt:
            c = self.kontakt_von(w.get("chat"))
            if c:
                self._zeigen(c, w.get("text", ""), w.get("medium"))

    def empfangen(self, nachricht):
        chat = nachricht.get("chat") or {}
        text = str(nachricht.get("text") or nachricht.get("caption") or "").strip()
        medium = self.medium_von(nachricht)
        if text.startswith("/"):
            c = self.kontakt_von(chat.get("id"))
            if c and c["eltern"]:
                self.befehl(c, text)
            return
        if not text and not medium:
            return
        c = self.kontakt_von(chat.get("id"))
        if c is None:
            name = " ".join(x for x in (chat.get("first_name"), chat.get("last_name")) if x) or chat.get("title") or "?"
            self.unbekannt = ([u for u in self.unbekannt if u["id"] != chat.get("id")] +
                              [{"id": chat.get("id"), "name": str(name)[:30], "text": text[:60]}])[-5:]
            log.info("Telegram: Nachricht aus unbekanntem Chat abgewiesen.")
            return
        datei = None
        if medium:
            art, file_id, endung, _ = medium
            if not (c["eltern"] or c["medien"]):
                log.info("Telegram: %s darf keine Fotos/Medien schicken - nur der Text kommt an.", c["name"])
                medium = None
            else:
                try:
                    datei = self._herunterladen(file_id, endung)
                except (OSError, ValueError) as fehler:
                    log.warning("Telegram: Medium nicht geladen (%s).", str(fehler).replace(self.einstellungen()["token"], "…"))
                    medium = None
            text = text or ("%s von %s" % (MEDIEN_TEXT[art], c["name"]) if medium else "")
            if not text:
                return
        medium = {"art": medium[0], "datei": datei} if medium and datei else None
        if c["nur_freizeit"] and not c["eltern"] and self._sperrzeit_jetzt():
            self._merke(c["id"], "rein", text, wartet=True, medium=medium)
            with self._sperre:
                self.wartend = (self.wartend + [{"chat": c["id"], "text": text[:140], "medium": medium}])[-20:]
                self._speichern()
            log.info("Telegram: Nachricht von %s wartet bis nach der Sperrzeit.", c["name"])
            return
        self._merke(c["id"], "rein", text, medium=medium)
        self._zeigen(c, text, medium)
        if not c["eltern"]:
            self.melde_eltern("freunde", "%s %s hat geschrieben: %s" % (c["symbol"], c["name"], text[:120]))

    # ------------------------------------------------------------ Senden (Antwort des Kindes)
    def senden(self, text, chat=None):
        """chat=None: an die Eltern-Kontakte (wie bis 4.2 „an die Familie“). Sonst nur an einen erlaubten Kontakt."""
        t = self.einstellungen()
        if not self.aktiv():
            raise ValueError("Telegram ist nicht eingerichtet.")
        if chat is None:
            ziele = [c for c in t["chats"] if c["eltern"]]
            if not ziele:
                raise ValueError("Bitte zuerst aussuchen, an wen die Nachricht geht.")
        else:
            ziele = [c for c in self.schreibbar() if c["id"] == chat]
            if not ziele:
                raise ValueError("Diesem Kontakt kannst du nicht schreiben.")
        text = str(text or "").strip()
        if text not in t["antworten"]:
            if not t["eigene_texte"] or not all(c["eltern"] or c["eigene_texte"] for c in ziele):
                raise ValueError("Nur die vorbereiteten Antworten.")
            text = " ".join(text.split())                       # Zeilenumbrüche/Steuerzeichen raus
            text = "".join(z for z in text if z.isprintable())
            if not text:
                raise ValueError("Die Nachricht ist leer.")
            if len(text) > EIGENER_TEXT_MAX:
                raise ValueError("Höchstens %d Zeichen." % EIGENER_TEXT_MAX)
        jetzt = time.monotonic()
        self._gesendet = [x for x in self._gesendet if jetzt - x < 86400]
        if self._gesendet and jetzt - self._gesendet[-1] < SENDEN_ABSTAND_S:
            raise ValueError("Einen Moment – gleich kannst du wieder schreiben.")
        if len(self._gesendet) >= SENDEN_PRO_TAG:
            raise ValueError("Für heute sind genug Nachrichten verschickt.")
        name = self.hub.einstellungen.get("name") or "FernsehFranzi"
        for c in ziele:
            self._aufruf("sendMessage", {"chat_id": c["id"], "text": "%s: %s" % (name, text)}, timeout=15)
            self._merke(c["id"], "raus", text)
            if not c["eltern"]:
                self.melde_eltern("freunde", "%s an %s %s: %s" % (name, c["symbol"], c["name"], text[:120]))
        self._gesendet.append(jetzt)
        log.info("Telegram: Antwort an %d Chat(s).", len(ziele))
        return [c["name"] for c in ziele]
