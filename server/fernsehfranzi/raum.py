"""FernsehFranzi 4.3 - Spielraum: Mehrspieler-Spiele mit Handys (QR-Code am Fernseher).

Der Fernseher ist die große Tafel, jedes Handy ein Controller. Das Kind spielt mit der Fernbedienung als eigener
Spieler („tv“) mit. Der Server führt den Spielstand (die Handys und der Fernseher fragen ihn ab, keine WebSockets).
Nichts wird über Spieler gespeichert: Alles lebt nur, solange der Raum offen ist.

Handys bekommen eine fertige Ansicht (``zustand_fuer``), z. B. {"ansicht": "wahl", "optionen": [...]}, und schicken
Aktionen zurück. Der Fernseher bekommt je Spiel eine eigene Ansicht (``tv_zustand``).

Spiele (eigene Entwürfe):
  buzzer      Buzzer-Runde: Wer zuerst drückt, darf antworten.
  quiz        Familien-Quizrennen: Alle antworten, richtige Antworten bringen die Figur voran.
  malen       Malen & Raten: Einer malt am Handy, die anderen raten (Auswahl aus vier).
  raumschiff  Raumschiff-Rettung: Jeder hat einen Teil des Handbuchs oder der Schalter - nur gemeinsam.
  ton         Ton-Treffer: Der Fernseher spielt eine Tonfolge, der Spieler am Zug singt sie ins USB-Mikro am Fernseher.
              (Handy-Mikrofone gehen im Browser nur über HTTPS - im Heimnetz am Pi nicht möglich.)
"""
import random
import secrets
import time

MAX_SPIELER = 6
NAME_MAX = 16
SYMBOLE = ["🦊", "🐼", "🐸", "🦄", "🐯", "🐙", "🐧", "🦁", "🐨", "🐵", "🐲", "🐝"]
FARBEN = ["#e4574b", "#3f8de0", "#3bb36b", "#f2b630", "#a259d9", "#e0739f", "#2bb5b0", "#f08a3c"]
CODE_ZEICHEN = "ABCDEFGHJKLMNPQRSTUVWXYZ"
RAUM_MAX_S = 2 * 3600
WEG_S = 30
SPIELE = {"buzzer": "Buzzer-Runde", "quiz": "Familien-Quizrennen", "malen": "Malen & Raten",
          "raumschiff": "Raumschiff-Rettung", "ton": "Ton-Treffer", "rakete": "Lautstärke-Rakete",
          "klatsch": "Klatsch-Rhythmus"}
QUIZ_PAKETE = {"gemischt": "Gemischt", "einmaleins": "Einmaleins", "englisch": "Englisch", "eigene": "Eure Fragen"}

# ---------------------------------------------------------------- Inhalte
FRAGEN = [
    ("Wie viele Beine hat eine Spinne?", "8", ["6", "10", "4"]),
    ("Welche Farbe entsteht aus Blau und Gelb?", "Grün", ["Lila", "Orange", "Braun"]),
    ("Welcher Planet ist der Sonne am nächsten?", "Merkur", ["Venus", "Mars", "Erde"]),
    ("Wie heißt das größte Säugetier?", "Blauwal", ["Elefant", "Giraffe", "Nashorn"]),
    ("Wie viele Minuten hat eine Stunde?", "60", ["100", "30", "50"]),
    ("Welches Tier legt Eier?", "Huhn", ["Hund", "Katze", "Pferd"]),
    ("Wie viele Tage hat ein Schaltjahr?", "366", ["365", "364", "360"]),
    ("Welches Instrument hat Tasten?", "Klavier", ["Geige", "Trommel", "Flöte"]),
    ("Wie viele Kontinente gibt es?", "7", ["5", "9", "6"]),
    ("Welches Tier kann am schnellsten laufen?", "Gepard", ["Pferd", "Hase", "Strauß"]),
    ("Was ist gefrorenes Wasser?", "Eis", ["Dampf", "Nebel", "Tau"]),
    ("Wie viele Ecken hat ein Würfel?", "8", ["6", "12", "4"]),
    ("Welche Jahreszeit kommt nach dem Winter?", "Frühling", ["Sommer", "Herbst", "Winter"]),
    ("Wie viele Farben hat ein Regenbogen?", "7", ["5", "6", "9"]),
    ("Woraus machen Bienen Honig?", "Nektar", ["Wasser", "Blättern", "Pollen"]),
    ("Welches Tier ist ein Säugetier?", "Delfin", ["Hai", "Forelle", "Krake"]),
    ("Wie heißt der höchste Berg der Welt?", "Mount Everest", ["Zugspitze", "Mont Blanc", "Kilimandscharo"]),
    ("Wie viele Spieler hat eine Fußballmannschaft auf dem Feld?", "11", ["10", "9", "12"]),
    ("Welche Form hat ein Stoppschild?", "Achteck", ["Kreis", "Dreieck", "Quadrat"]),
    ("Wie nennt man ein Baby-Pferd?", "Fohlen", ["Kalb", "Lamm", "Ferkel"]),
    ("Was brauchen Pflanzen zum Wachsen?", "Licht", ["Lärm", "Zucker", "Sand"]),
    ("In welchem Land stehen die Pyramiden von Gizeh?", "Ägypten", ["Italien", "Mexiko", "China"]),
    ("Wie viele Zähne hat ein Erwachsener normalerweise?", "32", ["20", "28", "40"]),
    ("Welches Tier schläft im Winter?", "Igel", ["Fuchs", "Reh", "Spatz"]),
    ("Welcher Vogel kann nicht fliegen?", "Pinguin", ["Adler", "Taube", "Möwe"]),
    ("Was zeigt ein Kompass an?", "Norden", ["Uhrzeit", "Wetter", "Höhe"]),
    ("Welche Note liegt zwischen C und E?", "D", ["F", "H", "G"]),
    ("Was ist die Hauptstadt von Deutschland?", "Berlin", ["München", "Hamburg", "Köln"]),
    ("Wie viele Seiten hat ein Dreieck?", "3", ["4", "5", "6"]),
    ("Was trinkt ein Kälbchen?", "Milch", ["Saft", "Tee", "Wasser"]),
]
ENGLISCH = [("Hund", "dog"), ("Katze", "cat"), ("Haus", "house"), ("rot", "red"), ("blau", "blue"), ("grün", "green"),
            ("Apfel", "apple"), ("Buch", "book"), ("Sonne", "sun"), ("Mond", "moon"), ("Baum", "tree"), ("Vogel", "bird"),
            ("Fisch", "fish"), ("Milch", "milk"), ("Schule", "school"), ("Freund", "friend"), ("eins", "one"),
            ("zwei", "two"), ("drei", "three"), ("zehn", "ten"), ("Wasser", "water"), ("Auto", "car"),
            ("Tisch", "table"), ("Stuhl", "chair"), ("Mutter", "mother"), ("Vater", "father"), ("gelb", "yellow"),
            ("schwarz", "black"), ("weiß", "white"), ("Pferd", "horse")]
WOERTER = ["Haus", "Katze", "Sonne", "Baum", "Auto", "Fisch", "Blume", "Ball", "Hund", "Mond", "Stern", "Apfel",
           "Banane", "Schiff", "Flugzeug", "Brille", "Schneemann", "Regenschirm", "Pizza", "Eis", "Herz",
           "Schmetterling", "Schnecke", "Rakete", "Burg", "Krone", "Gitarre", "Uhr", "Schlüssel", "Kerze", "Wolke",
           "Regenbogen", "Spinne", "Elefant", "Giraffe", "Maus", "Käse", "Zelt", "Fahrrad", "Zug", "Tasse", "Lampe",
           "Buch", "Stuhl", "Drache", "Pinguin", "Kaktus", "Pilz", "Geschenk", "Ritter", "Schlange", "Igel", "Ente",
           "Leiter", "Brücke", "Kuchen", "Hut", "Schuh", "Fenster", "Insel"]
FARBEN_RS = [("rot", "🔴"), ("blau", "🔵"), ("gelb", "🟡"), ("grün", "🟢")]
ZEICHEN_RS = [("Blitz", "⚡"), ("Feuer", "🔥"), ("Eis", "❄️"), ("Strahlung", "☢️")]
AKTIONEN_RS = [("reparieren", "🔧 Reparieren"), ("loeschen", "🧯 Löschen"), ("aufladen", "🔋 Aufladen"),
               ("kuehlen", "💧 Kühlen"), ("funken", "🛰️ Funken"), ("luke", "🚪 Luke zu")]
TONLEITER = [60, 62, 64, 65, 67, 69, 71, 72]
SILBEN = ["do", "re", "mi", "fa", "sol", "la", "ti", "do"]


def _sauber(text, laenge):
    text = " ".join(str(text or "").split())
    return "".join(z for z in text if z.isprintable())[:laenge]


# ---------------------------------------------------------------- Raum
class Raum:
    def __init__(self, tv_name="Fernseher", eigene_fragen=(), monoton=time.monotonic, zufall=None):
        self.monoton = monoton
        self.zufall = zufall or random.Random()
        self.code = "".join(secrets.choice(CODE_ZEICHEN) for _ in range(4))
        self.token = secrets.token_urlsafe(12)
        self.geoeffnet = monoton()
        self.spieler = {"tv": {"id": "tv", "name": _sauber(tv_name, NAME_MAX) or "Fernseher", "symbol": "📺",
                               "farbe": FARBEN[0], "geheim": None, "zuletzt": monoton(), "punkte": 0, "leicht": True}}
        self.eigene_fragen = [(q["frage"], q["richtig"], list(q["falsch"])) for q in eigene_fragen
                              if isinstance(q, dict) and q.get("frage") and q.get("richtig") and len(q.get("falsch", [])) == 3]
        self.spiel = None
        self.letztes = None                 # Ergebnis des letzten Spiels (Rangliste)
        self.version = 0

    def jetzt(self):
        return self.monoton()

    def geaendert(self):
        self.version += 1

    # ---------------------------------------------------------- Spieler
    def handys(self):
        return [s for s in self.spieler.values() if s["id"] != "tv"]

    def alle(self):
        return list(self.spieler.values())

    def beitreten(self, name, symbol="", leicht=False):
        if len(self.handys()) >= MAX_SPIELER:
            raise ValueError("Der Raum ist voll (höchstens %d Handys)." % MAX_SPIELER)
        name = _sauber(name, NAME_MAX)
        if not name:
            raise ValueError("Bitte einen Namen eingeben.")
        vergeben = {s["name"].lower() for s in self.alle()}
        basis, n = name, 2
        while name.lower() in vergeben:
            name = "%s %d" % (basis[:NAME_MAX - 2], n)
            n += 1
        belegt = {s["symbol"] for s in self.alle()}
        if symbol not in SYMBOLE or symbol in belegt:
            symbol = next((s for s in SYMBOLE if s not in belegt), SYMBOLE[0])
        sid = "s%d" % (len(self.spieler) + self.version + 1)
        while sid in self.spieler:
            sid += "x"
        farbe = FARBEN[len(self.spieler) % len(FARBEN)]
        geheim = secrets.token_urlsafe(16)
        self.spieler[sid] = {"id": sid, "name": name, "symbol": symbol, "farbe": farbe, "geheim": geheim,
                             "zuletzt": self.jetzt(), "punkte": 0, "leicht": bool(leicht)}
        self.geaendert()
        if self.spiel:
            self.spiel.dazu(sid)
        return sid, geheim

    def spieler_von(self, geheim):
        if not geheim:
            return None
        for s in self.handys():
            if secrets.compare_digest(s["geheim"], str(geheim)):
                s["zuletzt"] = self.jetzt()
                return s["id"]
        return None

    def oeffentlich(self, s):
        return {"id": s["id"], "name": s["name"], "symbol": s["symbol"], "farbe": s["farbe"], "punkte": s["punkte"],
                "da": s["id"] == "tv" or self.jetzt() - s["zuletzt"] < WEG_S}

    # ---------------------------------------------------------- Spiele
    def starte(self, name, **optionen):
        klassen = KLASSEN
        if name not in klassen:
            raise ValueError("Dieses Spiel gibt es nicht.")
        klasse = klassen[name]
        if len(self.alle()) < klasse.MINDESTENS or len(self.handys()) < klasse.HANDYS_MIN:
            raise ValueError(klasse.ZU_WENIG)
        for s in self.alle():
            s["punkte"] = 0
        self.spiel = klasse(self, **optionen)
        self.letztes = None
        self.geaendert()

    def zur_lobby(self):
        self.spiel = None
        self.geaendert()

    def beenden(self):
        rangliste = sorted((self.oeffentlich(s) for s in self.alle()), key=lambda s: -s["punkte"])
        self.letztes = {"spiel": self.spiel.NAME if self.spiel else "", "rangliste": rangliste,
                        "text": getattr(self.spiel, "schluss", "") if self.spiel else ""}
        self.spiel = None
        self.geaendert()

    def tick(self):
        if self.spiel:
            self.spiel.tick()

    # ---------------------------------------------------------- Ansichten
    def zustand_fuer(self, sid):
        s = self.spieler[sid]
        basis = {"version": self.version, "ich": self.oeffentlich(s), "raum": self.code}
        if self.spiel:
            ansicht = self.spiel.fuer_spieler(sid)
            basis.update(spiel=self.spiel.NAME, **ansicht)
        elif self.letztes:
            platz = next((i + 1 for i, r in enumerate(self.letztes["rangliste"]) if r["id"] == sid), None)
            basis.update(ansicht="ergebnis", titel=self.letztes["spiel"], platz=platz,
                         rangliste=self.letztes["rangliste"], text=self.letztes["text"])
        else:
            basis.update(ansicht="warten", titel="Du bist dabei!", text="Gleich geht's los – schau auf den Fernseher.")
        return basis

    def tv_zustand(self):
        z = {"version": self.version, "code": self.code, "spieler": [self.oeffentlich(s) for s in self.alle()],
             "spiele": [{"id": k, "name": v, "geht": len(self.alle()) >= KLASSEN[k].MINDESTENS and
                         len(self.handys()) >= KLASSEN[k].HANDYS_MIN} for k, v in SPIELE.items()],
             "pakete": QUIZ_PAKETE, "eigene_fragen": len(self.eigene_fragen)}
        if self.spiel:
            z.update(spiel=self.spiel.ID, titel=self.spiel.NAME, tv=self.spiel.fuer_tv(),
                     tv_spieler=self.spiel.fuer_spieler("tv"))
        elif self.letztes:
            z.update(ergebnis=self.letztes)
        return z

    def aktion(self, sid, daten):
        if self.spiel and isinstance(daten, dict):
            self.spiel.aktion(sid, daten)
            self.geaendert()

    def tv_aktion(self, daten):
        art = daten.get("art")
        if art == "start":
            optionen = {}
            if daten.get("paket") in QUIZ_PAKETE:
                optionen["paket"] = daten["paket"]
            if daten.get("stufe") in (1, 2):
                optionen["stufe"] = daten["stufe"]
            self.starte(str(daten.get("spiel")), **optionen)
        elif art == "lobby":
            self.zur_lobby()
        elif art == "spieler":                         # das Kind am Fernseher spielt mit der Fernbedienung
            self.aktion("tv", daten.get("daten") or {})
        elif self.spiel:
            self.spiel.tv_aktion(daten)
            self.geaendert()


# ---------------------------------------------------------------- Spiel-Grundlage
class Spiel:
    ID, NAME, MINDESTENS, HANDYS_MIN = "", "", 2, 1
    ZU_WENIG = "Dafür braucht es mindestens zwei Spieler (ein Handy und den Fernseher)."

    def __init__(self, raum):
        self.raum = raum
        self.z = raum.zufall
        self.phase = "start"
        self.seit = raum.jetzt()
        self.schluss = ""

    def jetzt(self):
        return self.raum.jetzt()

    def wechsel(self, phase):
        self.phase = phase
        self.seit = self.jetzt()
        self.raum.geaendert()

    def vorbei(self, sekunden):
        return self.jetzt() - self.seit >= sekunden

    def rest(self, sekunden):
        return max(0, int(round(sekunden - (self.jetzt() - self.seit))))

    def punkte(self, sid, n):
        if sid in self.raum.spieler:
            self.raum.spieler[sid]["punkte"] += n

    def name(self, sid):
        s = self.raum.spieler.get(sid)
        return "%s %s" % (s["symbol"], s["name"]) if s else "?"

    def dazu(self, sid):
        """Ein Handy kommt während des Spiels dazu (die meisten Spiele lassen es ab der nächsten Runde mitspielen)."""

    def tick(self):
        pass

    def tv_aktion(self, daten):
        pass

    def fuer_tv(self):
        return {"phase": self.phase}

    def fuer_spieler(self, sid):
        return {"ansicht": "warten", "titel": self.NAME, "text": "Schau auf den Fernseher."}

    def aktion(self, sid, daten):
        pass


def _mische(z, richtig, falsch):
    optionen = [richtig] + list(falsch)[:3]
    z.shuffle(optionen)
    return optionen


def _frage_paket(raum, paket, anzahl):
    z = raum.zufall
    if paket == "einmaleins":
        fragen = []
        for _ in range(anzahl):
            a, b = z.randint(2, 10), z.randint(2, 10)
            richtig = a * b
            falsch = set()
            while len(falsch) < 3:
                f = richtig + z.choice([-a, a, -b, b, -1, 1, 10, -10])
                if f > 0 and f != richtig:
                    falsch.add(f)
            fragen.append(("Was ist %d × %d?" % (a, b), str(richtig), [str(f) for f in falsch]))
        return fragen
    if paket == "englisch":
        paare = z.sample(ENGLISCH, min(anzahl, len(ENGLISCH)))
        fragen = []
        for de, en in paare:
            falsch = z.sample([e for _, e in ENGLISCH if e != en], 3)
            fragen.append(("Was heißt „%s“ auf Englisch?" % de, en, falsch))
        return fragen
    if paket == "eigene" and raum.eigene_fragen:
        pool = list(raum.eigene_fragen)
    else:
        pool = list(FRAGEN) + list(raum.eigene_fragen)
    z.shuffle(pool)
    return pool[:anzahl]


# ---------------------------------------------------------------- Buzzer-Runde
class Buzzer(Spiel):
    ID, NAME = "buzzer", SPIELE["buzzer"]
    FRAGEN_ANZAHL, FRAGE_S, ANTWORT_S, AUFLOESUNG_S = 10, 25, 12, 5

    def __init__(self, raum, paket="gemischt"):
        super().__init__(raum)
        self.fragen = _frage_paket(raum, paket, self.FRAGEN_ANZAHL)
        self.nr = -1
        self.naechste()

    def naechste(self):
        self.nr += 1
        if self.nr >= len(self.fragen):
            self.schluss = "Alle Fragen geschafft!"
            self.raum.beenden()
            return
        frage, richtig, falsch = self.fragen[self.nr]
        self.frage, self.richtig = frage, richtig
        self.optionen = _mische(self.z, richtig, falsch)
        self.buzzer_von, self.gesperrt, self.ergebnis = None, set(), None
        self.wechsel("frage")

    def tick(self):
        if self.phase == "frage" and self.vorbei(self.FRAGE_S):
            self.ergebnis = {"richtig": None, "text": "Keiner wusste es."}
            self.wechsel("aufloesung")
        elif self.phase == "antwort" and self.vorbei(self.ANTWORT_S):
            self.falsch(self.buzzer_von, "zu langsam")
        elif self.phase == "aufloesung" and self.vorbei(self.AUFLOESUNG_S):
            self.naechste()

    def falsch(self, sid, warum="falsch"):
        self.gesperrt.add(sid)
        if set(self.raum.spieler) <= self.gesperrt:
            self.ergebnis = {"richtig": None, "text": "Keiner hatte recht."}
            self.wechsel("aufloesung")
        else:
            self.letzter_fehler = "%s: %s" % (self.name(sid), warum)
            self.buzzer_von = None
            self.wechsel("frage")

    def aktion(self, sid, d):
        if d.get("art") == "buzz" and self.phase == "frage" and sid not in self.gesperrt:
            self.buzzer_von = sid
            self.wechsel("antwort")
        elif d.get("art") == "wahl" and self.phase == "antwort" and sid == self.buzzer_von:
            i = d.get("index")
            if isinstance(i, int) and 0 <= i < len(self.optionen):
                if self.optionen[i] == self.richtig:
                    self.punkte(sid, 1)
                    self.ergebnis = {"richtig": sid, "text": "%s hat recht!" % self.name(sid)}
                    self.wechsel("aufloesung")
                else:
                    self.falsch(sid)

    def fuer_tv(self):
        return {"phase": self.phase, "nr": self.nr + 1, "von": len(self.fragen), "frage": self.frage,
                "optionen": self.optionen if self.phase != "frage" else [],
                "richtig": self.richtig if self.phase == "aufloesung" else None,
                "buzzer": self.name(self.buzzer_von) if self.buzzer_von else "",
                "gesperrt": [self.name(s) for s in self.gesperrt],
                "ergebnis": self.ergebnis, "rest": self.rest(self.FRAGE_S if self.phase == "frage" else
                                                             self.ANTWORT_S if self.phase == "antwort" else self.AUFLOESUNG_S)}

    def fuer_spieler(self, sid):
        if self.phase == "frage":
            if sid in self.gesperrt:
                return {"ansicht": "warten", "titel": "Diesmal nicht", "text": "Die anderen dürfen noch buzzern."}
            return {"ansicht": "buzzer", "titel": "Frage %d" % (self.nr + 1), "text": self.frage}
        if self.phase == "antwort":
            if sid == self.buzzer_von:
                return {"ansicht": "wahl", "titel": "Du darfst!", "text": self.frage, "optionen": self.optionen,
                        "rest": self.rest(self.ANTWORT_S)}
            return {"ansicht": "warten", "titel": "%s antwortet …" % self.name(self.buzzer_von), "text": self.frage}
        return {"ansicht": "warten", "titel": (self.ergebnis or {}).get("text", ""),
                "text": "Richtig: %s" % self.richtig}


# ---------------------------------------------------------------- Familien-Quizrennen
class Quizrennen(Spiel):
    ID, NAME, MINDESTENS = "quiz", SPIELE["quiz"], 1
    ZU_WENIG = "Dafür braucht es mindestens ein Handy."
    ZIEL, FRAGE_S, LEICHT_S, AUFLOESUNG_S, FRAGEN_MAX = 8, 15, 23, 5, 16

    def __init__(self, raum, paket="gemischt"):
        super().__init__(raum)
        self.paket = paket
        self.fragen = _frage_paket(raum, paket, self.FRAGEN_MAX)
        self.felder = {sid: 0 for sid in raum.spieler}
        self.nr = -1
        self.naechste()

    def dazu(self, sid):
        self.felder.setdefault(sid, 0)

    def zeit_fuer(self, sid):
        return self.LEICHT_S if self.raum.spieler.get(sid, {}).get("leicht") else self.FRAGE_S

    def naechste(self):
        self.nr += 1
        sieger = [s for s, f in self.felder.items() if f >= self.ZIEL]
        if sieger or self.nr >= len(self.fragen):
            self.schluss = "Im Ziel: " + ", ".join(self.name(s) for s in sieger) if sieger else "Alle Fragen geschafft!"
            self.raum.beenden()
            return
        self.frage, self.richtig, falsch = self.fragen[self.nr]
        self.optionen = _mische(self.z, self.richtig, falsch)
        self.antworten = {}                     # sid -> (index, Sekunden)
        self.ergebnis = None
        self.wechsel("frage")

    def tick(self):
        if self.phase == "frage":
            alle = [s for s in self.felder if s in self.raum.spieler]
            fertig = all(s in self.antworten for s in alle)
            if fertig or self.vorbei(max(self.zeit_fuer(s) for s in alle)):
                self.aufloesen()
        elif self.phase == "aufloesung" and self.vorbei(self.AUFLOESUNG_S):
            self.naechste()

    def aufloesen(self):
        richtig = [(t, s) for s, (i, t) in self.antworten.items() if self.optionen[i] == self.richtig]
        richtig.sort()
        for n, (_, s) in enumerate(richtig):
            schritte = 2 if n == 0 and len(self.felder) > 1 else 1
            self.felder[s] = min(self.ZIEL, self.felder[s] + schritte)
            self.punkte(s, schritte)
        self.ergebnis = {"richtig": [s for _, s in richtig], "schnellster": richtig[0][1] if richtig else None}
        self.wechsel("aufloesung")

    def aktion(self, sid, d):
        if d.get("art") == "wahl" and self.phase == "frage" and sid not in self.antworten and sid in self.felder:
            i = d.get("index")
            if isinstance(i, int) and 0 <= i < len(self.optionen) and not self.vorbei(self.zeit_fuer(sid)):
                self.antworten[sid] = (i, self.jetzt() - self.seit)

    def fuer_tv(self):
        return {"phase": self.phase, "nr": self.nr + 1, "frage": self.frage, "optionen": self.optionen,
                "richtig": self.richtig if self.phase == "aufloesung" else None, "ziel": self.ZIEL,
                "bahn": [dict(self.raum.oeffentlich(self.raum.spieler[s]), feld=f)
                         for s, f in self.felder.items() if s in self.raum.spieler],
                "geantwortet": [self.name(s) for s in self.antworten],
                "ergebnis": self.ergebnis, "rest": self.rest(self.FRAGE_S if self.phase == "frage" else self.AUFLOESUNG_S)}

    def fuer_spieler(self, sid):
        if self.phase == "frage" and sid in self.felder:
            if sid in self.antworten:
                return {"ansicht": "warten", "titel": "Antwort gegeben ✔", "text": "Warte auf die anderen …",
                        "gewaehlt": self.optionen[self.antworten[sid][0]]}
            return {"ansicht": "wahl", "titel": "Frage %d" % (self.nr + 1), "text": self.frage,
                    "optionen": self.optionen, "rest": self.rest(self.zeit_fuer(sid))}
        if self.phase == "aufloesung":
            gut = sid in (self.ergebnis or {}).get("richtig", [])
            return {"ansicht": "warten", "titel": "Richtig! 🎉" if gut else "Leider nicht",
                    "text": "Richtig war: %s · Feld %d von %d" % (self.richtig, self.felder.get(sid, 0), self.ZIEL)}
        return {"ansicht": "warten", "titel": self.NAME, "text": "Ab der nächsten Frage bist du dabei."}


# ---------------------------------------------------------------- Malen & Raten
class MalenRaten(Spiel):
    ID, NAME = "malen", SPIELE["malen"]
    ZU_WENIG = "Dafür braucht es mindestens ein Handy zum Malen und einen zweiten Spieler zum Raten."
    RUNDE_S, AUFLOESUNG_S, PUNKTE_MAX = 75, 5, 6000

    def __init__(self, raum):
        super().__init__(raum)
        handys = [s["id"] for s in raum.handys()]
        self.reihe = handys * (2 if len(handys) <= 2 else 1)
        self.z.shuffle(self.reihe)
        self.benutzt = set()
        self.runde = -1
        self.naechste()

    def naechste(self):
        self.runde += 1
        while self.runde < len(self.reihe) and self.reihe[self.runde] not in self.raum.spieler:
            self.runde += 1
        if self.runde >= len(self.reihe):
            self.schluss = "Toll gemalt!"
            self.raum.beenden()
            return
        self.maler = self.reihe[self.runde]
        frei = [w for w in WOERTER if w not in self.benutzt]
        self.wort = self.z.choice(frei)
        self.benutzt.add(self.wort)
        self.optionen = _mische(self.z, self.wort, self.z.sample([w for w in WOERTER if w != self.wort], 3))
        self.striche, self.punkte_anzahl = [], 0
        self.geraten = {}                       # sid -> richtig?
        self.reihenfolge = []
        self.wechsel("malen")

    def ratende(self):
        return [s for s in self.raum.spieler if s != self.maler]

    def tick(self):
        if self.phase == "malen":
            if self.vorbei(self.RUNDE_S) or (self.ratende() and all(s in self.geraten for s in self.ratende())):
                self.punkte(self.maler, len(self.reihenfolge))
                self.wechsel("aufloesung")
        elif self.phase == "aufloesung" and self.vorbei(self.AUFLOESUNG_S):
            self.naechste()

    def aktion(self, sid, d):
        art = d.get("art")
        if self.phase != "malen":
            return
        if sid == self.maler and art == "striche":
            for strich in d.get("striche", [])[:20]:
                punkte = strich.get("p") if isinstance(strich, dict) else None
                if not isinstance(punkte, list) or self.punkte_anzahl + len(punkte) // 2 > self.PUNKTE_MAX:
                    continue
                zahlen = [max(0, min(1000, int(v))) for v in punkte if isinstance(v, (int, float))][:400]
                farbe = strich.get("f") if strich.get("f") in FARBEN + ["#111111", "#ffffff"] else "#111111"
                dicke = max(2, min(40, int(strich.get("d", 8)))) if isinstance(strich.get("d", 8), (int, float)) else 8
                self.striche.append({"p": zahlen, "f": farbe, "d": dicke, "neu": bool(strich.get("neu"))})
                self.punkte_anzahl += len(zahlen) // 2
        elif sid == self.maler and art == "loeschen":
            self.striche, self.punkte_anzahl = [{"leer": True}], 0
        elif sid != self.maler and art == "wahl" and sid not in self.geraten:
            i = d.get("index")
            if isinstance(i, int) and 0 <= i < len(self.optionen):
                gut = self.optionen[i] == self.wort
                self.geraten[sid] = gut
                if gut:
                    self.reihenfolge.append(sid)
                    self.punkte(sid, max(1, 4 - len(self.reihenfolge)))

    def fuer_tv(self, ab=0):
        return {"phase": self.phase, "runde": self.runde + 1, "von": len(self.reihe), "maler": self.name(self.maler),
                "striche_anzahl": len(self.striche), "optionen": self.optionen,
                "wort": self.wort if self.phase == "aufloesung" else None,
                "geraten": [self.name(s) for s in self.reihenfolge],
                "rest": self.rest(self.RUNDE_S if self.phase == "malen" else self.AUFLOESUNG_S)}

    def striche_ab(self, ab):
        return self.striche[max(0, int(ab)):]

    def fuer_spieler(self, sid):
        if self.phase == "malen":
            if sid == self.maler:
                return {"ansicht": "malen", "titel": "Du malst!", "wort": self.wort, "rest": self.rest(self.RUNDE_S),
                        "farben": ["#111111"] + FARBEN[:6]}
            if sid in self.geraten:
                return {"ansicht": "warten", "titel": "Richtig! 🎉" if self.geraten[sid] else "Daneben 🙈",
                        "text": "Warte, bis alle geraten haben."}
            return {"ansicht": "wahl", "titel": "Was malt %s?" % self.name(self.maler), "text": "Schau auf den Fernseher!",
                    "optionen": self.optionen, "rest": self.rest(self.RUNDE_S)}
        return {"ansicht": "warten", "titel": "Es war: %s" % self.wort, "text": "Nächste Runde gleich …"}


# ---------------------------------------------------------------- Raumschiff-Rettung (gemeinsam)
class Raumschiff(Spiel):
    ID, NAME = "raumschiff", SPIELE["raumschiff"]
    ZU_WENIG = "Dafür braucht es mindestens ein Handy und einen zweiten Spieler."
    ZIEL, LEBEN, PAUSE_S = 8, 3, 2

    def __init__(self, raum, stufe=1):
        super().__init__(raum)
        self.stufe = stufe
        self.zeit_s = 30 if stufe == 1 else 40
        aktionen = [a for a, _ in AKTIONEN_RS]
        if stufe == 1:
            self.regeln = {(f, None): self.z.choice(aktionen) for f, _ in FARBEN_RS}
        else:
            self.regeln = {(f, s): self.z.choice(aktionen) for f, _ in FARBEN_RS for s, _ in ZEICHEN_RS}
        teilnehmer = [s["id"] for s in raum.alle()]
        handys = [s["id"] for s in raum.handys()]
        self.handbuch = {sid: [] for sid in teilnehmer}
        regeln = list(self.regeln.items())
        self.z.shuffle(regeln)
        for n, regel in enumerate(regeln):                  # Handbuch nur auf die Handys (den Fernseher sehen alle)
            self.handbuch[handys[n % len(handys)]].append(regel)
        self.knoepfe = {sid: [] for sid in teilnehmer}
        reihum = list(teilnehmer)
        self.z.shuffle(reihum)
        for n, (a, _) in enumerate(AKTIONEN_RS):
            self.knoepfe[reihum[n % len(reihum)]].append(a)
        self.leben, self.gerettet = self.LEBEN, 0
        self.meldung = ""
        self.neue_stoerung()

    def neue_stoerung(self):
        farbe = self.z.choice(FARBEN_RS)[0]
        zeichen = self.z.choice(ZEICHEN_RS)[0] if self.stufe == 2 else None
        self.stoerung = (farbe, zeichen)
        self.wechsel("stoerung")

    def text_regel(self, schluessel, aktion):
        farbe, zeichen = schluessel
        f = dict(FARBEN_RS)[farbe]
        teil = "%s %s" % (f, farbe.upper()) + (" + %s %s" % (dict(ZEICHEN_RS)[zeichen], zeichen) if zeichen else "")
        return "%s → %s" % (teil, dict(AKTIONEN_RS)[aktion])

    def ergebnis(self, gut, text):
        if gut:
            self.gerettet += 1
        else:
            self.leben -= 1
        self.meldung = text
        if self.gerettet >= self.ZIEL:
            for s in self.raum.spieler:
                self.punkte(s, self.gerettet)
            self.schluss = "🚀 Gerettet! Das ganze Team hat es geschafft."
            self.raum.beenden()
        elif self.leben <= 0:
            for s in self.raum.spieler:
                self.punkte(s, self.gerettet)
            self.schluss = "💥 Das Raumschiff musste notlanden – nochmal?"
            self.raum.beenden()
        else:
            self.wechsel("pause")

    def tick(self):
        if self.phase == "stoerung" and self.vorbei(self.zeit_s):
            self.ergebnis(False, "⏰ Zu spät!")
        elif self.phase == "pause" and self.vorbei(self.PAUSE_S):
            self.neue_stoerung()

    def aktion(self, sid, d):
        if d.get("art") == "knopf" and self.phase == "stoerung" and d.get("id") in self.knoepfe.get(sid, []):
            richtig = self.regeln[self.stoerung]
            if d["id"] == richtig:
                self.ergebnis(True, "✅ %s hat es repariert!" % self.name(sid))
            else:
                self.ergebnis(False, "❌ Falscher Schalter (%s)" % dict(AKTIONEN_RS)[d["id"]])

    def fuer_tv(self):
        farbe, zeichen = self.stoerung
        return {"phase": self.phase, "farbe": farbe, "farbe_symbol": dict(FARBEN_RS)[farbe],
                "zeichen": zeichen, "zeichen_symbol": dict(ZEICHEN_RS).get(zeichen, ""), "leben": self.leben,
                "gerettet": self.gerettet, "ziel": self.ZIEL, "meldung": self.meldung, "stufe": self.stufe,
                "rest": self.rest(self.zeit_s if self.phase == "stoerung" else self.PAUSE_S)}

    def fuer_spieler(self, sid):
        knoepfe = [{"id": a, "text": dict(AKTIONEN_RS)[a]} for a in self.knoepfe.get(sid, [])]
        handbuch = [self.text_regel(k, a) for k, a in sorted(self.handbuch.get(sid, []), key=lambda r: (r[0][0], r[0][1] or ""))]
        return {"ansicht": "knoepfe", "titel": "🚀 Raumschiff-Rettung", "knoepfe": knoepfe, "handbuch": handbuch,
                "aktiv": self.phase == "stoerung", "text": self.meldung if self.phase == "pause" else
                "Lest euch gegenseitig vor, was im Handbuch steht!", "rest": self.rest(self.zeit_s)}


# ---------------------------------------------------------------- Ton-Treffer (USB-Mikro am Fernseher)
class TonTreffer(Spiel):
    ID, NAME, MINDESTENS, HANDYS_MIN = "ton", SPIELE["ton"], 1, 0
    ZU_WENIG = "Dafür braucht es mindestens einen Spieler."
    RUNDEN, DAUMEN_S, SINGEN_S = 3, 6, 25

    def __init__(self, raum):
        super().__init__(raum)
        self.reihe = [s["id"] for s in raum.alle()]
        self.runde, self.zug = 0, -1
        self.daumen = set()
        self.naechster()

    def naechster(self):
        self.zug += 1
        if self.zug >= len(self.reihe):
            self.zug, self.runde = 0, self.runde + 1
        if self.runde >= self.RUNDEN:
            self.schluss = "Was für Stimmen! 🎤"
            self.raum.beenden()
            return
        self.saenger = self.reihe[self.zug]
        if self.saenger not in self.raum.spieler:
            return self.naechster()
        laenge = 3 + self.runde
        i = self.z.randint(0, 4)
        folge = [i]
        for _ in range(laenge - 1):
            i = max(0, min(len(TONLEITER) - 1, i + self.z.choice([-2, -1, 1, 1, 2])))
            folge.append(i)
        self.folge = folge
        self.treffer, self.daumen = None, set()
        self.wechsel("vorspielen")

    def tick(self):
        if self.phase == "singen" and self.vorbei(self.SINGEN_S + 5):
            self.treffer = []                    # der Fernseher hat nichts gemeldet
            self.wechsel("daumen")
        elif self.phase == "daumen" and self.vorbei(self.DAUMEN_S):
            self.naechster()

    def tv_aktion(self, d):
        art = d.get("art")
        if art == "bereit" and self.phase == "vorspielen":
            self.wechsel("singen")
        elif art == "ton_ergebnis" and self.phase == "singen":
            treffer = [bool(t) for t in (d.get("treffer") or [])][:len(self.folge)]
            self.treffer = treffer
            self.punkte(self.saenger, sum(treffer) + (2 if treffer and all(treffer) and len(treffer) == len(self.folge) else 0))
            self.wechsel("daumen")
        elif art == "kein_mikro":
            self.schluss = "Kein Mikrofon gefunden – Ton-Treffer braucht das USB-Mikro am Fernseher."
            self.raum.beenden()

    def aktion(self, sid, d):
        if d.get("art") == "daumen" and self.phase == "daumen" and sid != self.saenger and sid not in self.daumen:
            self.daumen.add(sid)
            self.punkte(self.saenger, 1)

    def fuer_tv(self):
        return {"phase": self.phase, "runde": self.runde + 1, "runden": self.RUNDEN, "saenger": self.name(self.saenger),
                "folge": [{"midi": TONLEITER[i], "silbe": SILBEN[i], "stufe": i} for i in self.folge],
                "treffer": self.treffer, "daumen": len(self.daumen), "singen_s": self.SINGEN_S,
                "rest": self.rest(self.SINGEN_S if self.phase == "singen" else self.DAUMEN_S)}

    def fuer_spieler(self, sid):
        if self.phase == "daumen" and sid != self.saenger:
            return {"ansicht": "daumen", "titel": "Wie hat %s gesungen?" % self.name(self.saenger),
                    "gegeben": sid in self.daumen, "text": "Daumen hoch gibt einen Extrapunkt!"}
        if sid == self.saenger and self.phase in ("vorspielen", "singen"):
            return {"ansicht": "warten", "titel": "🎤 Du bist dran!",
                    "text": "Hör gut zu und sing die Töne ins Mikro am Fernseher." if self.phase == "vorspielen"
                    else "Jetzt singen! Ganz nah ans Mikro."}
        return {"ansicht": "warten", "titel": "%s singt" % self.name(self.saenger), "text": "Psst … zuhören!"}


# ---------------------------------------------------------------- 4.4: weitere Mikro-Spiele (USB-Mikro am Fernseher)
class MikroRunde(Spiel):
    """Reihum ist ein Spieler dran: vorbereiten (der Fernseher spielt vor oder zählt herunter), messen (der Fernseher
    hört zu und meldet das Ergebnis), danach dürfen die anderen am Handy einen Daumen geben."""
    MINDESTENS, HANDYS_MIN, RUNDEN, MESSEN_S, DAUMEN_S = 1, 0, 2, 12, 6
    VORBEREITEN = "vorspielen"

    def __init__(self, raum):
        super().__init__(raum)
        self.reihe = [s["id"] for s in raum.alle()]
        self.runde, self.zug = 0, -1
        self.daumen, self.ergebnis = set(), None
        self.naechster()

    def neue_aufgabe(self):
        pass

    def naechster(self):
        self.zug += 1
        if self.zug >= len(self.reihe):
            self.zug, self.runde = 0, self.runde + 1
        if self.runde >= self.RUNDEN:
            self.schluss = self.SCHLUSS
            self.raum.beenden()
            return
        self.dran = self.reihe[self.zug]
        if self.dran not in self.raum.spieler:
            return self.naechster()
        self.daumen, self.ergebnis = set(), None
        self.neue_aufgabe()
        self.wechsel(self.VORBEREITEN)

    def tick(self):
        if self.phase == "messen" and self.vorbei(self.MESSEN_S + 5):
            self.auswerten({})
        elif self.phase == "daumen" and self.vorbei(self.DAUMEN_S):
            self.naechster()

    def tv_aktion(self, d):
        if d.get("art") == "bereit" and self.phase == self.VORBEREITEN:
            self.wechsel("messen")
        elif d.get("art") == "ergebnis" and self.phase == "messen":
            self.auswerten(d)
        elif d.get("art") == "kein_mikro":
            self.schluss = "Kein Mikrofon gefunden – dieses Spiel braucht das USB-Mikro am Fernseher."
            self.raum.beenden()

    def aktion(self, sid, d):
        if d.get("art") == "daumen" and self.phase == "daumen" and sid != self.dran and sid not in self.daumen:
            self.daumen.add(sid)
            self.punkte(self.dran, 1)

    def fuer_spieler(self, sid):
        if self.phase == "daumen" and sid != self.dran:
            return {"ansicht": "daumen", "titel": "%s: %s" % (self.name(self.dran), (self.ergebnis or {}).get("text", "")),
                    "gegeben": sid in self.daumen, "text": "Daumen hoch gibt einen Extrapunkt!"}
        if sid == self.dran and self.phase in (self.VORBEREITEN, "messen"):
            return {"ansicht": "warten", "titel": "🎤 Du bist dran!", "text": self.HINWEIS_DRAN}
        return {"ansicht": "warten", "titel": "%s ist dran" % self.name(self.dran), "text": "Schau auf den Fernseher!"}


class Rakete(MikroRunde):
    """Lautstärke-Rakete: drei Sekunden Countdown, dann so laut und so lange wie möglich - die Rakete steigt."""
    ID, NAME = "rakete", SPIELE["rakete"]
    SCHLUSS = "🚀 Was für ein Lärm!"
    HINWEIS_DRAN = "Gleich ganz laut ins Mikro am Fernseher – Aaaaah!"
    VORBEREITEN = "countdown"
    MESSEN_S = 5

    def tick(self):
        if self.phase == "countdown" and self.vorbei(3):
            self.wechsel("messen")
        else:
            super().tick()

    def auswerten(self, d):
        hoehe = d.get("hoehe")
        hoehe = max(0, min(1000, int(hoehe))) if isinstance(hoehe, (int, float)) else 0
        self.punkte(self.dran, hoehe // 100)
        rekord = max([hoehe] + [getattr(self, "rekord", 0)])
        self.rekord = rekord
        self.ergebnis = {"hoehe": hoehe, "text": "%d Meter hoch!" % hoehe, "rekord": hoehe >= rekord and hoehe > 0}
        self.wechsel("daumen")

    def fuer_tv(self):
        return {"phase": self.phase, "runde": self.runde + 1, "runden": self.RUNDEN, "dran": self.name(self.dran),
                "messen_s": self.MESSEN_S, "ergebnis": self.ergebnis, "rekord": getattr(self, "rekord", 0),
                "daumen": len(self.daumen), "rest": self.rest(3 if self.phase == "countdown" else
                                                             self.MESSEN_S if self.phase == "messen" else self.DAUMEN_S)}


class Klatsch(MikroRunde):
    """Klatsch-Rhythmus: Der Fernseher klopft einen Rhythmus vor, der Spieler klatscht ihn nach."""
    ID, NAME = "klatsch", SPIELE["klatsch"]
    SCHLUSS = "👏 Super Rhythmus!"
    HINWEIS_DRAN = "Hör zu und klatsch den Rhythmus nach – nah am Mikro am Fernseher."
    RUNDEN, EINHEIT_MS = 3, 300

    def neue_aufgabe(self):
        anzahl = 4 + self.runde
        self.abstaende = [self.z.choice([1, 1, 2]) for _ in range(anzahl - 1)]       # in Achteln (300 ms)

    def auswerten(self, d):
        treffer = d.get("treffer")
        treffer = max(0, min(len(self.abstaende) + 1, int(treffer))) if isinstance(treffer, (int, float)) else 0
        anzahl = len(self.abstaende) + 1
        self.punkte(self.dran, treffer + (2 if treffer == anzahl else 0))
        self.ergebnis = {"treffer": treffer, "von": anzahl, "text": "%d von %d Klatschern im Takt" % (treffer, anzahl)}
        self.wechsel("daumen")

    def fuer_tv(self):
        return {"phase": self.phase, "runde": self.runde + 1, "runden": self.RUNDEN, "dran": self.name(self.dran),
                "abstaende": self.abstaende, "einheit_ms": self.EINHEIT_MS, "ergebnis": self.ergebnis,
                "daumen": len(self.daumen), "messen_s": self.MESSEN_S,
                "rest": self.rest(self.MESSEN_S if self.phase == "messen" else self.DAUMEN_S)}


KLASSEN = {"buzzer": Buzzer, "quiz": Quizrennen, "malen": MalenRaten, "raumschiff": Raumschiff, "ton": TonTreffer,
           "rakete": Rakete, "klatsch": Klatsch}
