"""FernsehFranzi 4.0 - Telegram: Nachrichten der Familie ans TV, das Kind antwortet mit vorbereiteten Texten.

Einstellungen (einstellungen.json, Feld "telegram"; der Token steht nur auf dem Gerät, nie im Repo):
    {"aktiv": true, "token": "123:ABC…", "chats": [{"id": 123456, "name": "Papa"}],
     "antworten": ["👍 Okay!", "Komme gleich!", …], "eigene_texte": true}
4.1: Mit "eigene_texte" darf das Kind auch selbst getippte Texte schicken (Tastatur, höchstens 300 Zeichen).
Nur Nachrichten aus erlaubten Chats kommen an. Unbekannte Chats werden gemerkt (Eltern-Seite: „Erlauben“).
Abgerufen wird per Long-Polling (getUpdates) in einem eigenen Thread - keine offene Tür nach außen.
"""
import json
import logging
import threading
import time
import urllib.error
import urllib.request

log = logging.getLogger("fernsehfranzi.telegram")

BASIS = "https://api.telegram.org"          # Tests setzen hier eine Attrappe ein
VORGABE = {"aktiv": False, "token": "", "chats": [], "antworten": [
    "👍 Okay!", "Komme gleich!", "Bin fertig!", "Ich hab dich lieb ❤️", "Kannst du kurz kommen?", "Gute Nacht 🌙"],
    "eigene_texte": True}
EIGENER_TEXT_MAX = 300
VERSTECKT = "••••••••"                       # so zeigt die Eltern-Seite einen gesetzten Token
SENDEN_ABSTAND_S = 10
SENDEN_PRO_TAG = 40


def einstellungen(gespeichert):
    t = dict(VORGABE)
    t.update(gespeichert or {})
    return t


def pruefe(t):
    if not isinstance(t, dict) or set(t) - set(VORGABE):
        raise ValueError("Telegram: unbekannte Felder.")
    t = einstellungen(t)
    if not isinstance(t["aktiv"], bool):
        raise ValueError("Telegram: an/aus muss ja/nein sein.")
    if t["token"] and (not isinstance(t["token"], str) or ":" not in t["token"] or len(t["token"]) > 100):
        raise ValueError("Telegram: Der Bot-Token sieht nicht richtig aus (Zahl:Buchstaben von @BotFather).")
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

    def empfangen(self, nachricht):
        chat = nachricht.get("chat") or {}
        text = str(nachricht.get("text") or "").strip()
        if not text or text.startswith("/"):
            return
        erlaubt = {c["id"]: c["name"] for c in self.einstellungen()["chats"]}
        if chat.get("id") not in erlaubt:
            name = " ".join(x for x in (chat.get("first_name"), chat.get("last_name")) if x) or chat.get("title") or "?"
            self.unbekannt = ([u for u in self.unbekannt if u["id"] != chat.get("id")] +
                              [{"id": chat.get("id"), "name": str(name)[:30], "text": text[:60]}])[-5:]
            log.info("Telegram: Nachricht aus unbekanntem Chat abgewiesen.")
            return
        self.hub.familie.nachricht(text, quelle=erlaubt[chat["id"]], bleibt=True, chat=chat["id"])

    # ------------------------------------------------------------ Senden (Antwort des Kindes)
    def senden(self, text, chat=None):
        t = self.einstellungen()
        if not self.aktiv():
            raise ValueError("Telegram ist nicht eingerichtet.")
        text = str(text or "").strip()
        if text not in t["antworten"]:
            if not t["eigene_texte"]:
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
        ziele = [c for c in t["chats"] if chat is None or c["id"] == chat] or t["chats"]
        for c in ziele:
            self._aufruf("sendMessage", {"chat_id": c["id"], "text": "%s: %s" % (name, text)}, timeout=15)
        self._gesendet.append(jetzt)
        log.info("Telegram: Antwort an %d Chat(s).", len(ziele))
        return [c["name"] for c in ziele]
