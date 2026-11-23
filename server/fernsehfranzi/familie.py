"""FernsehFranzi 3.1 - Familie und Lernen.

Läuft im Takt des Hubs (``Familie.tick`` alle 5 s) und nutzt dessen Wege nach draußen:
``hub.melde`` (Startseite), ``hub.auftrag`` (kiosk.py: Hinweis/Seite), ``hub.system.retroarch``
(Hinweis im Spiel) und ``hub.cec_befehl`` (eingabe.py: Fernseher aus).

* Nachricht ans TV, Erinnerungen zu festen Zeiten
* Schlafenszeit (Vorwarnung, dann Startseite und Fernseher aus), Fernseher aus bei Zeitende
* Gute-Nacht-Modus (Hörspiel, Bildschirm gedimmt, nach X min Fernseher aus)
* Bewegungspause nach langer Nutzung am Stück
* Lernzeit verdient Spielzeit
* Übungs-Tagebuch der Bass-Ecke, Sticker-Album
"""
import collections
import copy
import logging
import os
import random
from datetime import datetime, timedelta

from . import daten, klaenge, zeitkonto

log = logging.getLogger("fernsehfranzi.familie")

VORGABE = {
    # [{"zeit": "19:00", "text": "Zähneputzen!", "tage": [0..6], "wann": "immer"}] - 4.6: wann = immer / schule (nicht in
    # den Ferien) / ferien (nur in den Ferien)
    "erinnerungen": [],
    # 5.2: Klang für Nachrichten der Eltern (Eltern-Seite, Elternbereich); None = Gong. Erinnerungen haben ihren eigenen.
    "klang_nachricht": None,
    "tv_aus_bei_zeitende": False,
    # 3.4: Gute Nacht (Hörbuch-App "gute-nacht") öffnet sich zu Beginn der Nachtruhe von selbst, wenn an
    "gute_nacht": {"automatisch": False},
    "bewegungspause": {"aktiv": False, "nach_min": 45, "dauer_min": 2},
    # Lernbonus (3.1.1 strenger): nur aktive Minuten (genug Tastendrücke) zählen, alle check_min Minuten
    # „Bist du noch da?“ - erst nach bestandener Prüfung wird die Zeit gutgeschrieben.
    "lernbonus": {"aktiv": False, "lernen_min": 20, "bonus_min": 10, "max_bonus_min": 30,
                  "tasten_pro_minute": 3, "check_min": 10},
    "bass_bibliotheken": {"unterricht": "", "backing": ""},
    # Hörbücher (3.3): Sleep-Timer muss bei jedem PLAY gewählt werden; längste Wahl stellen die Eltern ein
    "hoerbuch": {"schlaf_max_min": 60},
}
WARN_MIN = (10, 5, 1)
ERINNERUNG_WANN = ("immer", "schule", "ferien")
WIEDERHOLEN_S = 5 * 60          # unbestätigte Erinnerungen/Nachrichten (Entscheidung 8.4: alle 5 min, ohne Ende)
MELDUNGEN_MAX = 30
CHECK_FRIST_S = 90
CHECK_TASTEN = {"LEFT": "←", "RIGHT": "→", "UP": "↑", "DOWN": "↓"}
BASS_LEERLAUF_S = 20 * 60      # Üben braucht keine Fernbedienung - aber nicht stundenlang ohne jede Eingabe

STICKER = [
    # id, Name, Symbol, Bedingung (Text für das Album)
    ("snake-10", "Schlangenbeschwörer", "🐍", "10 Punkte in Snake"),
    ("snake-30", "Snake-Profi", "🏆", "30 Punkte in Snake"),
    ("memory", "Gedächtnis-Ass", "🧠", "Ein Memory geschafft"),
    ("memory-gross", "Memory-Meister", "🎖️", "Das große Memory geschafft"),
    ("drei-schwer", "Unschlagbar", "⭐", "Den Fernseher auf „Schwer“ besiegt"),
    ("echo-8", "Farben-Gedächtnis", "🌈", "8 Runden Farben-Echo"),
    ("maler-1", "Künstlerin", "🎨", "Erstes Bild gespeichert"),
    ("maler-10", "Galerie", "🖼️", "10 Bilder gespeichert"),
    ("bass-1", "Erste Bass-Stunde", "🎸", "Zum ersten Mal in der Bass-Ecke geübt"),
    ("bass-60", "Eine Stunde Bass", "🎵", "Insgesamt 60 Minuten geübt"),
    ("bass-3tage", "Drei Tage dran", "🔥", "3 Tage hintereinander geübt"),
    ("bass-7tage", "Eine ganze Woche", "💪", "7 Tage hintereinander geübt"),
    ("griffbrett-20", "Griffbrett-Kennerin", "🎯", "20 Töne auf dem Griffbrett gefunden"),
    ("rhythmus", "Im Takt", "🥁", "Rhythmus-Spiel mit mindestens 80 % Treffern"),
    ("gehoer-10", "Gutes Gehör", "👂", "10 Gehör-Aufgaben richtig"),
    ("lernen-60", "Fleißig gelernt", "📚", "Eine Stunde gelernt"),
    ("pause", "Bewegungs-Held", "🤸", "Eine Bewegungspause mitgemacht"),
    ("duell", "Duell-Sieg", "🤝", "Ein Spiel zu zweit gewonnen"),
    ("einmaleins", "Rechen-Ass", "✖️", "10 Einmaleins-Aufgaben am Stück richtig"),
    ("uhr", "Uhr-Profi", "🕰️", "10 Uhrzeiten richtig gelesen"),
    ("englisch", "English Star", "🇬🇧", "20 englische Wörter richtig"),
]
STICKER_IDS = {s[0] for s in STICKER}
# Erfolge, die die Spiele melden: id -> (Schwelle, Sticker-id)
ERFOLGE = {
    "snake": [(10, "snake-10"), (30, "snake-30")],
    "memory": [(1, "memory")], "memory-gross": [(1, "memory-gross")],
    "drei-schwer": [(1, "drei-schwer")], "echo": [(8, "echo-8")],
    "griffbrett": [(20, "griffbrett-20")], "rhythmus": [(80, "rhythmus")], "gehoer": [(10, "gehoer-10")],
    "duell": [(1, "duell")], "pause": [(1, "pause")],
    "einmaleins": [(10, "einmaleins")], "uhr": [(10, "uhr")], "englisch": [(20, "englisch")],
}


def _uhr(text):
    return datetime.strptime(text, "%H:%M").time()


def pruefe(familie):
    """Wirft ValueError bei ungültigen Einstellungen (Eltern-Seite zeigt den Text)."""
    if not isinstance(familie, dict):
        raise ValueError("familie muss ein Objekt sein.")
    unbekannt = set(familie) - set(VORGABE)
    if unbekannt:
        raise ValueError("Unbekannte Felder: %s" % ", ".join(sorted(unbekannt)))
    for nr, e in enumerate(familie.get("erinnerungen", []), 1):
        if not isinstance(e, dict) or not str(e.get("text", "")).strip() or len(e["text"]) > 120:
            raise ValueError("Erinnerung %d: Text fehlt oder ist zu lang." % nr)
        _uhr(e.get("zeit", ""))
        if not all(isinstance(t, int) and 0 <= t <= 6 for t in e.get("tage", [])):
            raise ValueError("Erinnerung %d: Tage 0 (Mo) bis 6 (So)." % nr)
        if e.get("wann", "immer") not in ERINNERUNG_WANN:
            raise ValueError("Erinnerung %d: immer, nicht in den Ferien oder nur in den Ferien." % nr)
        klaenge.pruefe(e.get("klang"), "Erinnerung %d" % nr)
    klaenge.pruefe(familie.get("klang_nachricht"), "Nachrichten der Eltern")
    if len(familie.get("erinnerungen", [])) > 30:
        raise ValueError("Höchstens 30 Erinnerungen.")
    g = familie.get("gute_nacht", VORGABE["gute_nacht"])
    if not isinstance(g, dict) or set(g) - {"automatisch"} or not isinstance(g.get("automatisch", False), bool):
        raise ValueError("Gute Nacht: nur „automatisch“ (ja/nein).")
    b = familie.get("bewegungspause", VORGABE["bewegungspause"])
    if not 10 <= int(b.get("nach_min", 45)) <= 240 or not 1 <= int(b.get("dauer_min", 2)) <= 15:
        raise ValueError("Bewegungspause: nach 10–240 min, Dauer 1–15 min.")
    hb = familie.get("hoerbuch", VORGABE["hoerbuch"])
    if not isinstance(hb, dict) or not isinstance(hb.get("schlaf_max_min", 60), int) or \
            not 5 <= hb.get("schlaf_max_min", 60) <= 180:
        raise ValueError("Hörbücher: längster Sleep-Timer 5 bis 180 Minuten.")
    lb = familie.get("lernbonus", VORGABE["lernbonus"])
    if not 5 <= int(lb.get("lernen_min", 20)) <= 120 or not 1 <= int(lb.get("bonus_min", 10)) <= 60 \
            or not 0 <= int(lb.get("max_bonus_min", 30)) <= 240:
        raise ValueError("Lernbonus: lernen 5–120, Bonus 1–60, höchstens 0–240 min.")
    if not 1 <= int(lb.get("tasten_pro_minute", 3)) <= 30 or not 3 <= int(lb.get("check_min", 10)) <= 60:
        raise ValueError("Lernbonus: 1–30 Tastendrücke pro Minute, Prüfung alle 3–60 Minuten.")
    for adresse in (familie.get("bass_bibliotheken") or {}).values():
        if adresse and not str(adresse).startswith(("http://", "https://")):
            raise ValueError("Bass-Bibliothek: Adresse muss mit http:// oder https:// beginnen.")


class Familie:
    def __init__(self, hub):
        self.hub = hub
        self.zustand = daten.lies_json(hub._pfad("familie.json"), {}) or {}
        self.zustand.setdefault("sticker", {})          # id -> Datum
        self.zustand.setdefault("bass_tage", {})        # "JJJJ-MM-TT" -> Sekunden
        self.zustand.setdefault("erfolge", {})          # id -> bester Wert / Summe
        self.zustand.setdefault("lern_s", 0)
        self.zustand.setdefault("lern_datum", "")
        self.zustand.setdefault("lern_bonus_min", 0)
        self.zustand.setdefault("lern_offen_s", 0)       # aktiv gelernt, aber noch nicht bestätigt
        self.zustand.setdefault("lern_verworfen_s", 0)   # durch verpasste Prüfung verfallen (für die Eltern)
        self.zustand.setdefault("zeichnungen_gesehen", 0.0)
        self.zustand.setdefault("meldungen", [])          # 3.4: Erinnerungen/Nachrichten bis OK (mit „gesehen“)
        self.erledigt = set()             # "erinnerung:JJJJ-MM-TT:HH:MM:text" usw. (pro Tag)
        self.am_stueck_s = 0              # zählende Nutzung ohne Pause
        self.pause_bis = None
        self._wiederholt = hub.monoton()
        self.zuletzt_gespeichert = hub.monoton()
        self.tastendruecke = collections.deque(maxlen=400)   # Monotonzeit jedes Tastendrucks
        self.check = None                                     # {"taste", "bis"} während „Bist du noch da?“

    # ------------------------------------------------------------ Einstellungen
    def einstellungen(self):
        e = copy.deepcopy(VORGABE)
        for k, v in (self.hub.einstellungen.get("familie") or {}).items():
            if isinstance(v, dict):
                e[k].update(v)
            else:
                e[k] = v
        return e

    def speichern(self, sofort=False):
        if sofort or self.hub.monoton() - self.zuletzt_gespeichert >= 30:
            daten.schreibe_json(self.hub._pfad("familie.json"), self.zustand)
            self.zuletzt_gespeichert = self.hub.monoton()

    # ------------------------------------------------------------ Nachricht ans TV
    def nachricht(self, text, quelle="Nachricht von Mama oder Papa", bleibt=False, chat=None, symbol=None, medium=None,
                  klang=None):
        """bleibt=True (Eltern-Nachricht, Erinnerung): steht, bis sie am Fernseher mit OK bestätigt wird, und kommt
        alle 5 Minuten wieder. Sonst ein kurzer Hinweis."""
        text = str(text or "").strip()[:140]
        if not text:
            raise ValueError("Die Nachricht ist leer.")
        # ohne Emojis: Plex-Seiten und RetroArch haben auf dem Gerät keine Emoji-Schrift
        voll = "%s: %s" % (quelle, text) if quelle else text
        if bleibt:
            jetzt = self.hub.uhr()
            with self.hub.lock:
                liste = self.zustand["meldungen"]
                nr = max([m["nr"] for m in liste] + [0]) + 1
                liste.append({"nr": nr, "text": text, "quelle": quelle or "", "zeit": jetzt.isoformat(timespec="seconds"),
                              "gesehen": None, "chat": chat, "symbol": symbol, "medium": medium, "klang": klang})
                del liste[:-MELDUNGEN_MAX]
            self._wiederholt = self.hub.monoton()        # nächste Wiederholung 5 min nach dieser Meldung
            self.speichern(sofort=True)
        self._zeigen(voll, klang)
        log.info("Nachricht ans TV: %s", text)

    def _zeigen(self, voll, klang=None):
        if not self.hub.still():                    # Gute-Nacht-Modus/Fernseher aus: kein Gong, kein Hinweis
            if not self.nachrichten_leise():        # 4.4: in Sperrzeiten ohne Gong (einstellbar), sichtbar bleibt sie
                self.hub.klang_spielen(klang)       # hörbar überall - auch wenn sie gerade nicht hinschaut (5.2: mit Klang)
            self.hub.auftrag("hinweis", text=voll)
            laeuft, _ = self.hub.system.retropie_zustand()
            if laeuft:
                self.hub.system.retroarch("SHOW_MSG " + voll)
        self.hub.melde(voll)

    def nachrichten_leise(self):
        """4.4: In einer Sperrzeit kommen Nachrichten ohne Ton (Eltern-Seite → Telegram, Vorgabe an)."""
        return bool(self.hub.telegram.einstellungen().get("sperrzeit_still", True)) and self.hub.telegram._sperrzeit_jetzt()

    def offene_meldungen(self):
        """Unbestätigte Nachrichten. 4.4: Nachrichten von Freunden, die nur außerhalb der Sperrzeiten gelesen werden
        dürfen, bleiben in der Sperrzeit verborgen (sie zählen nur, siehe gezaehlt_gesperrt)."""
        gesperrt = self.hub.telegram.gesperrte_chats()
        return [m for m in self.zustand["meldungen"] if not m.get("gesehen") and m.get("chat") not in gesperrt]

    def sichtbare_meldungen(self, anzahl=20):
        gesperrt = self.hub.telegram.gesperrte_chats()
        return [m for m in self.zustand["meldungen"][-anzahl:] if m.get("chat") not in gesperrt]

    def gezaehlt_gesperrt(self):
        """Neue Freunde-Nachrichten, die gerade nicht gelesen werden dürfen (wartend + unbestätigt verborgen)."""
        gesperrt = self.hub.telegram.gesperrte_chats()
        verborgen = sum(1 for m in self.zustand["meldungen"] if not m.get("gesehen") and m.get("chat") in gesperrt)
        return verborgen + len(self.hub.telegram.wartend)

    def meldungen_gesehen(self, nummern):
        jetzt = self.hub.uhr().isoformat(timespec="seconds")
        neu = []
        with self.hub.lock:
            for m in self.zustand["meldungen"]:
                if m["nr"] in nummern and not m.get("gesehen"):
                    m["gesehen"] = jetzt
                    neu.append(dict(m))
        self.speichern(sofort=True)
        if neu:
            self.hub.telegram.gelesen(neu)          # 4.4: „✔ gelesen“ an den Absender (Eltern)

    def _wiederholen(self):
        if self.hub.monoton() - self._wiederholt < WIEDERHOLEN_S:
            return
        self._wiederholt = self.hub.monoton()
        offen = self.offene_meldungen()
        if not offen or self.hub.still():
            return
        m = offen[-1]
        self._zeigen(("%s: %s" % (m["quelle"], m["text"]) if m["quelle"] else m["text"]) +
                     (" (+%d weitere)" % (len(offen) - 1) if len(offen) > 1 else ""), m.get("klang"))

    # ------------------------------------------------------------ Takt
    def tick(self, jetzt, app, sekunden, aktiv):
        e = self.einstellungen()
        heute = jetzt.date().isoformat()
        self.erledigt = {x for x in self.erledigt if heute in x}
        self._erinnerungen(e, jetzt, heute)
        self._wiederholen()
        self._bewegung(e, jetzt, app, sekunden, aktiv)
        self._lernen(e, jetzt, app, sekunden, aktiv)
        self._bass(jetzt, app, sekunden)
        self.speichern()

    def _einmal(self, schluessel):
        if schluessel in self.erledigt:
            return False
        self.erledigt.add(schluessel)
        return True

    def _erinnerungen(self, e, jetzt, heute):
        ferien = None
        for er in e["erinnerungen"]:
            tage = er.get("tage") or list(range(7))
            if jetzt.weekday() not in tage:
                continue
            wann = er.get("wann", "immer")
            if wann != "immer":
                if ferien is None:
                    ferien = zeitkonto.in_ferien(jetzt.date(), self.hub._regeln())
                if (wann == "schule") == ferien:
                    continue
            zeit = datetime.combine(jetzt.date(), _uhr(er["zeit"]))
            if zeit <= jetzt < zeit + timedelta(minutes=2) and \
                    self._einmal("erinnerung:%s:%s:%s" % (heute, er["zeit"], er["text"])):
                self.nachricht(er["text"], quelle="Erinnerung", bleibt=True, klang=er.get("klang"))

    def zeitende(self):
        """Vom Hub, wenn das Tagesbudget aufgebraucht ist (nach dem Speichern und Zurück)."""
        if self.einstellungen()["tv_aus_bei_zeitende"]:
            self.hub.cec_befehl("standby")

    # ------------------------------------------------------------ Bewegungspause
    def _bewegung(self, e, jetzt, app, sekunden, aktiv):
        b = e["bewegungspause"]
        if self.pause_bis:
            if jetzt >= self.pause_bis:
                self.pause_bis = None
                self.hub.melde("Pause geschafft – weiter geht's!")
                self.erfolg("pause", 1)
            return
        # 4.6: je Angebot einstellbar („bewegung“); ohne Angabe gilt sie für alles, was Zeit kostet
        zaehlt = bool(app) and bool(app.get("bewegung", zeitkonto.zaehlt(app)))
        if zaehlt and aktiv:
            self.am_stueck_s += sekunden
        elif not zaehlt:
            self.am_stueck_s = max(0, self.am_stueck_s - sekunden * 3)   # Startseite/Plex = Erholung
        if b.get("aktiv") and self.am_stueck_s >= int(b.get("nach_min", 45)) * 60:
            self.am_stueck_s = 0
            dauer = int(b.get("dauer_min", 2))
            self.pause_bis = jetzt + timedelta(minutes=dauer)
            self.nachricht("Zeit für eine Bewegungspause! %d Minuten Hampelmann, Strecken, Hüpfen." % dauer,
                           quelle="Bewegungspause")
            laeuft, _ = self.hub.system.retropie_zustand()
            # 4.2.1: Nur wenn der Browser woanders ist (Webseite, Desktop-App), zur Startseite wechseln. Läuft etwas auf der
            # Startseite selbst (YouTube, Video, Hörbuch, Spiel), legt sie die Pause darüber und hält den Film nur an -
            # ein Neuladen hätte den Player geschlossen, der Film begann danach von vorn.
            if not laeuft and not self._auf_startseite():
                self.hub.auftrag("startseite", eltern=False, pause=dauer * 60)

    def _auf_startseite(self):
        aktuell = self.hub.aktuell
        if aktuell == "internet":
            return False
        return (self.hub.app(aktuell) or {}).get("typ") not in ("web", "desktop") if aktuell else True

    def in_pause(self):
        return self.pause_bis is not None

    def pause_rest(self, jetzt):
        """Sekunden bis zum Ende der Bewegungspause (0 = keine Pause)."""
        if not self.pause_bis:
            return 0
        return max(0, int((self.pause_bis - jetzt).total_seconds()))

    # ------------------------------------------------------------ Lernen verdient Spielzeit
    def tasten(self, namen):
        """Tastendrücke (von eingabe.py und der Startseite): für aktive Minuten und die Prüfung."""
        jetzt = self.hub.monoton()
        for name in namen[:60]:
            self.tastendruecke.append(jetzt)
            if self.check:
                name = str(name).upper()
                folge, stand = self.check["folge"], self.check["stand"]
                if name == folge[stand]:
                    self.check["stand"] += 1
                    if self.check["stand"] == len(folge):
                        self._check_bestanden()
                else:
                    self.check["stand"] = 1 if name == folge[0] else 0   # falsch: von vorn

    def _aktiv_genug(self, lb):
        grenze = self.hub.monoton() - 60
        return sum(1 for t in self.tastendruecke if t >= grenze) >= int(lb.get("tasten_pro_minute", 3))

    def _check_starten(self):
        """Drei zufällige Pfeile in Folge - beim normalen Navigieren trifft man das kaum aus Versehen."""
        folge = [random.choice(sorted(CHECK_TASTEN)) for _ in range(3)]
        while len(set(folge)) == 1:
            folge = [random.choice(sorted(CHECK_TASTEN)) for _ in range(3)]
        self.check = {"folge": folge, "stand": 0, "bis": self.hub.monoton() + CHECK_FRIST_S}
        self.nachricht("Bist du noch beim Lernen? Drück nacheinander %s" % " ".join(CHECK_TASTEN[t] for t in folge),
                       quelle="Lern-Check")
        log.info("Lern-Check: %s", folge)

    def _check_bestanden(self):
        self.check = None
        z = self.zustand
        z["lern_s"] += z["lern_offen_s"]
        z["erfolge"]["lernen_s"] = z["erfolge"].get("lernen_s", 0) + z["lern_offen_s"]
        z["lern_offen_s"] = 0
        self.hub.melde("Prima, weiter so!")
        self.hub.auftrag("hinweis", text="Prima, weiter so!")
        if z["erfolge"]["lernen_s"] >= 3600:
            self.sticker("lernen-60")
        self._bonus_gutschreiben()
        self.speichern(sofort=True)

    def _check_verpasst(self):
        self.check = None
        z = self.zustand
        log.info("Lern-Check verpasst: %d s verworfen.", z["lern_offen_s"])
        z["lern_verworfen_s"] += z["lern_offen_s"]
        z["lern_offen_s"] = 0
        self.nachricht("Die letzten Minuten zählen nicht als Lernzeit. Lern weiter, dann zählt es wieder!",
                       quelle="Lern-Check")
        self.speichern(sofort=True)

    def _bonus_gutschreiben(self):
        lb = self.einstellungen()["lernbonus"]
        if not lb.get("aktiv"):
            return
        verdient = (self.zustand["lern_s"] // (int(lb["lernen_min"]) * 60)) * int(lb["bonus_min"])
        verdient = min(verdient, int(lb["max_bonus_min"]))
        neu = verdient - self.zustand["lern_bonus_min"]
        if neu > 0:
            self.zustand["lern_bonus_min"] = verdient
            self.hub.bonus_minuten(neu, "Super gelernt! +%d Minuten Spielzeit." % neu)

    def _lernen(self, e, jetzt, app, sekunden, aktiv):
        heute = jetzt.date().isoformat()
        z = self.zustand
        if z["lern_datum"] != heute:
            z.update(lern_datum=heute, lern_s=0, lern_bonus_min=0, lern_offen_s=0, lern_verworfen_s=0)
            self.check = None
        if self.check:
            if self.hub.monoton() >= self.check["bis"]:
                self._check_verpasst()
            return                                   # während der Prüfung zählt nichts
        lb = e["lernbonus"]
        if not app or not app.get("lernen") or not self._aktiv_genug(lb):
            return
        z["lern_offen_s"] += sekunden
        if z["lern_offen_s"] >= int(lb.get("check_min", 10)) * 60:
            self._check_starten()

    def lernstand(self):
        z = self.zustand
        return {"bestaetigt_min": z["lern_s"] // 60, "offen_min": z["lern_offen_s"] // 60,
                "verworfen_min": z["lern_verworfen_s"] // 60, "bonus_min": z["lern_bonus_min"],
                "check_laeuft": bool(self.check)}

    # ------------------------------------------------------------ Bass-Tagebuch
    def _bass(self, jetzt, app, sekunden):
        if not app or app.get("id") != "spiel-bass":
            return
        if self.hub.monoton() - self.hub.letzte_eingabe > BASS_LEERLAUF_S:
            return
        tag = jetzt.date().isoformat()
        tage = self.zustand["bass_tage"]
        tage[tag] = tage.get(tag, 0) + sekunden
        self.sticker("bass-1")
        if sum(tage.values()) >= 3600:
            self.sticker("bass-60")
        serie = self.bass_serie(jetzt.date())
        if serie >= 3:
            self.sticker("bass-3tage")
        if serie >= 7:
            self.sticker("bass-7tage")

    def bass_serie(self, heute):
        """Tage hintereinander mit mindestens 5 Minuten Üben (heute zählt, sobald erreicht)."""
        tage, serie, tag = self.zustand["bass_tage"], 0, heute
        if tage.get(tag.isoformat(), 0) < 300:
            tag -= timedelta(days=1)
        while tage.get(tag.isoformat(), 0) >= 300:
            serie += 1
            tag -= timedelta(days=1)
        return serie

    def bass_tagebuch(self, heute=None):
        heute = heute or self.hub.uhr().date()
        tage = self.zustand["bass_tage"]
        letzte = [(heute - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
        return {"tage": [{"datum": t, "minuten": tage.get(t, 0) // 60} for t in letzte],
                "serie": self.bass_serie(heute), "gesamt_min": sum(tage.values()) // 60}

    # ------------------------------------------------------------ Sticker
    def _alle_sticker(self):
        """Eingebaute und eigene Sticker der Eltern (3.5)."""
        eigene = [(s["id"], s["name"], s["symbol"], s.get("bedingung", ""))
                  for s in (self.hub.einstellungen.get("sticker_eigen") or [])]
        return STICKER + eigene

    def sticker(self, sticker_id):
        alle = self._alle_sticker()
        if sticker_id not in {s[0] for s in alle} or sticker_id in self.zustand["sticker"]:
            return False
        self.zustand["sticker"][sticker_id] = self.hub.uhr().date().isoformat()
        name = next(s[1] for s in alle if s[0] == sticker_id)
        self.hub.melde("Neuer Sticker: %s!" % name)
        self.speichern(sofort=True)
        log.info("Sticker: %s", sticker_id)
        return True

    def erfolg(self, art, wert):
        """Ein Spiel meldet einen Erfolg (Punkte, Runden, Treffer …)."""
        if art not in ERFOLGE or not isinstance(wert, (int, float)) or isinstance(wert, bool):
            raise ValueError("Unbekannter Erfolg.")
        wert = max(0, min(int(wert), 100000))
        if art in ("griffbrett", "gehoer", "uhr", "englisch"):        # Summen über alle Tage
            wert = self.zustand["erfolge"].get(art, 0) + wert
        self.zustand["erfolge"][art] = max(self.zustand["erfolge"].get(art, 0), wert)
        neu = [sid for schwelle, sid in ERFOLGE[art] if self.zustand["erfolge"][art] >= schwelle and self.sticker(sid)]
        self.speichern(sofort=True)
        return neu

    def zeichnung_gespeichert(self, anzahl):
        if anzahl >= 1:
            self.sticker("maler-1")
        if anzahl >= 10:
            self.sticker("maler-10")

    def album(self):
        return [{"id": sid, "name": name, "symbol": symbol, "bedingung": bedingung,
                 "seit": self.zustand["sticker"].get(sid)} for sid, name, symbol, bedingung in self._alle_sticker()]

    # ------------------------------------------------------------ Eltern: neue Zeichnungen
    def zeichnungen_gesehen(self, zeitpunkt):
        self.zustand["zeichnungen_gesehen"] = float(zeitpunkt)
        self.speichern(sofort=True)


def lese_gamelists(wurzeln, roms):
    """„Zuletzt gespielt“ und Favoriten aus den Spielelisten von EmulationStation.

    Rückgabe: Liste von {system, name, rom (relativ zu roms/system), zuletzt, anzahl, favorit}.
    Nur Spiele, deren Datei wirklich unter roms/<system>/ liegt.
    """
    import xml.etree.ElementTree as ET
    spiele = {}
    for wurzel in wurzeln:
        if not os.path.isdir(wurzel):
            continue
        for system in sorted(os.listdir(wurzel)):
            datei = os.path.join(wurzel, system, "gamelist.xml")
            if not os.path.isfile(datei):
                continue
            try:
                baum = ET.parse(datei)
            except ET.ParseError as fehler:
                log.warning("Spieleliste %s nicht lesbar: %s", datei, fehler)
                continue
            for spiel in baum.getroot().iter("game"):
                pfad = (spiel.findtext("path") or "").strip()
                rom = os.path.normpath(os.path.join(roms, system, pfad))
                if not rom.startswith(os.path.join(roms, system) + os.sep) or not os.path.isfile(rom):
                    continue
                schluessel = (system, os.path.relpath(rom, os.path.join(roms, system)))
                zuletzt = (spiel.findtext("lastplayed") or "").strip()
                eintrag = spiele.setdefault(schluessel, {
                    "system": system, "rom": schluessel[1],
                    "name": (spiel.findtext("name") or os.path.splitext(os.path.basename(pfad))[0]).strip(),
                    "zuletzt": "", "anzahl": 0, "favorit": False})
                eintrag["zuletzt"] = max(eintrag["zuletzt"], zuletzt)
                eintrag["anzahl"] = max(eintrag["anzahl"], int((spiel.findtext("playcount") or "0").strip() or 0))
                eintrag["favorit"] = eintrag["favorit"] or (spiel.findtext("favorite") or "").strip() == "true"
    return list(spiele.values())


def zuletzt_gespielt(spiele, anzahl=6):
    favoriten = [s for s in spiele if s["favorit"]]
    zuletzt = sorted((s for s in spiele if s["zuletzt"]), key=lambda s: s["zuletzt"], reverse=True)
    ergebnis = []
    for s in favoriten + zuletzt:
        if s not in ergebnis:
            ergebnis.append(s)
    return ergebnis[:anzahl]

