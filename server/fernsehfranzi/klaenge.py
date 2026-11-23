"""FernsehFranzi 5.2 - Klang-Archiv: eigene, vom Programm erzeugte Klänge (keine fremden Dateien, keine Lizenzen).

Jeder Klang ist ein kleines Rezept aus Tönen mit Klangfarbe und Hüllkurve. Der Server rechnet daraus einmal eine WAV-Datei
(22 kHz, mono) und spielt sie mit pw-play auf dem aktuellen Ausgang. Die Eltern-Seite holt dieselbe Datei zum Probehören.

Wählbar je Erinnerung, je Telegram-Kontakt, für Nachrichten der Eltern und für die Schule (Klassenkiste, Morgen-Check).
"""
import io
import math
import os
import random
import struct
import tempfile
import wave

RATE = 22050
STANDARD = "gong"
STUMM = "stumm"

# id -> (Name, Symbol, Rezept). Ein Rezept ist eine Liste von Tönen: (Beginn s, Frequenz Hz, Dauer s, Klangfarbe, Lautstärke)
# Klangfarben: glocke, xylo, harfe, sinus, blech, chip, gliss (Frequenz -> Zielfrequenz), rauschen, gong
C4, D4, E4, F4, G4, A4, H4 = 261.63, 293.66, 329.63, 349.23, 392.0, 440.0, 493.88
C5, D5, E5, F5, G5, A5, H5, C6, E6, G6 = 523.25, 587.33, 659.25, 698.46, 783.99, 880.0, 987.77, 1046.5, 1318.5, 1568.0

ARCHIV = {
    "gong": ("Gong", "🔔", [(0, G5, .35, "gong", 1), (.3, H5, .35, "gong", 1), (.6, 1175, .9, "gong", 1)]),
    "glocke": ("Glöckchen", "🛎️", [(0, 1400, 1.4, "glocke", 1), (.45, 1400, 1.4, "glocke", .8)]),
    "xylophon": ("Xylophon", "🎶", [(0, C5, .3, "xylo", 1), (.14, E5, .3, "xylo", 1), (.28, G5, .3, "xylo", 1), (.42, C6, .6, "xylo", 1)]),
    "harfe": ("Harfe", "🪕", [(i * .07, f, 1.2, "harfe", .8) for i, f in enumerate((C4, E4, G4, C5, E5, G5, C6))]),
    "spieluhr": ("Spieluhr", "🎠", [(t, f, .7, "glocke", .7) for t, f in ((0, E6), (.25, C6), (.5, G5), (.75, C6), (1.0, E6), (1.25, G6))]),
    "fanfare": ("Fanfare", "🎺", [(0, G4, .16, "blech", 1), (.18, G4, .16, "blech", 1), (.36, C5, .55, "blech", 1), (.95, E5, .25, "blech", 1),
                                 (1.2, C5, .7, "blech", 1)]),
    "vogel": ("Vogelzwitschern", "🐦", [(t, 2200 + d, .12, "gliss", .7) for t, d in ((0, 900), (.16, 1200), (.32, 700), (.75, 1300), (.9, 800))]),
    "tropfen": ("Wassertropfen", "💧", [(0, 600, .12, "gliss", 1), (.35, 750, .12, "gliss", .8), (.6, 520, .14, "gliss", .9)]),
    "klingel": ("Fahrradklingel", "🚲", [(0, 2600, .5, "glocke", .9), (.12, 2600, .9, "glocke", .9)]),
    "sternschnuppe": ("Sternschnuppe", "🌠", [(0, 2400, .9, "gliss", .6)] + [(.15 + i * .1, f, .5, "xylo", .4)
                                                                          for i, f in enumerate((G6, E6, C6, G5, E5))]),
    "marimba": ("Marimba", "🪘", [(0, G4, .5, "xylo", 1), (.2, C5, .8, "xylo", 1)]),
    "levelup": ("Level geschafft", "🕹️", [(i * .08, f, .09, "chip", .6) for i, f in enumerate((C5, E5, G5, C6, E6, G6))]),
    "trommel": ("Trommelwirbel", "🥁", [(i * .045, 0, .05, "rauschen", .25 + i * .02) for i in range(18)] + [(.85, 0, .35, "rauschen", 1)]),
    "ufo": ("Ufo", "🛸", [(0, 700, 1.3, "ufo", .7)]),
    "sanft": ("Sanft", "🌙", [(0, A4, 1.2, "sinus", .5), (.4, E5, 1.4, "sinus", .4)]),
}
GLISS_ZIEL = {"vogel": 1.6, "tropfen": 2.6, "sternschnuppe": .25}


def liste():
    """Für die Eltern-Seite: [{id, name, symbol}] plus „ohne Ton“."""
    return [{"id": k, "name": n, "symbol": s} for k, (n, s, _) in ARCHIV.items()] + [{"id": STUMM, "name": "Ohne Ton", "symbol": "🔇"}]


EIGEN = "eigen:"          # 6.0: eigener Klang aus dem Klang-Ordner der Eltern, z. B. "eigen:Hupe.mp3"
EIGEN_ENDUNGEN = (".mp3", ".ogg", ".oga", ".opus", ".wav", ".flac", ".m4a")


def eigen_pfad(klang):
    """Pfad innerhalb des Klang-Ordners oder None (kein eigener Klang / ungültig)."""
    if not isinstance(klang, str) or not klang.startswith(EIGEN) or len(klang) > 220:
        return None
    pfad = klang[len(EIGEN):]
    teile = [t for t in pfad.replace("\\", "/").split("/") if t not in ("", ".")]
    if not teile or ".." in teile or not pfad.lower().endswith(EIGEN_ENDUNGEN):
        return None
    return "/".join(teile)


def gueltig(klang, leer_erlaubt=True):
    return (leer_erlaubt and klang in (None, "")) or klang in ARCHIV or klang == STUMM or eigen_pfad(klang) is not None


def pruefe(klang, wo="Klang"):
    if not gueltig(klang):
        raise ValueError("%s: unbekannter Klang." % wo)
    return klang or None


def _probe(art, freq, t, dauer, ziel):
    if art == "rauschen":
        return random.uniform(-1, 1) * math.exp(-t * 18)
    if art == "gliss":
        f = freq * (ziel ** (t / dauer))
        return math.sin(2 * math.pi * f * t) * math.exp(-t * 6)
    if art == "ufo":
        f = freq + 180 * math.sin(2 * math.pi * 7 * t) + 300 * t
        return math.sin(2 * math.pi * f * t) * min(1, (dauer - t) * 4)
    w = 2 * math.pi * freq * t
    if art == "glocke":                                  # unharmonische Teiltöne, langer Ausklang
        return (math.sin(w) + .5 * math.sin(2.76 * w) + .25 * math.sin(5.4 * w)) / 1.75 * math.exp(-t * 3.2)
    if art == "gong":
        return math.sin(w) * max(0.0, 1 - t / dauer) ** 1.5
    if art == "xylo":
        return (math.sin(w) + .3 * math.sin(4 * w)) / 1.3 * math.exp(-t * 9)
    if art == "harfe":                                   # gezupft: Obertöne klingen schneller ab
        return (math.sin(w) * math.exp(-t * 3) + .4 * math.sin(2 * w) * math.exp(-t * 6) + .2 * math.sin(3 * w) * math.exp(-t * 9)) / 1.6
    if art == "blech":
        return sum(math.sin(k * w) / k for k in range(1, 7)) / 2.2 * min(1, t * 30) * min(1, (dauer - t) * 12)
    if art == "chip":                                    # Rechteck wie bei alten Spielkonsolen
        return (1 if math.sin(w) >= 0 else -1) * .6
    return math.sin(w) * math.exp(-t * 2.2)              # sinus


def erzeuge(klang):
    """WAV-Bytes eines Klangs (deterministisch: gleiches Rezept, gleiche Datei)."""
    if klang not in ARCHIV:
        raise ValueError("Unbekannter Klang.")
    random.seed(klang)
    rezept = ARCHIV[klang][2]
    laenge = max(b + d for b, _, d, _, _ in rezept) + .05
    proben = [0.0] * int(RATE * laenge)
    ziel = GLISS_ZIEL.get(klang, 1.5)
    for beginn, freq, dauer, art, laut in rezept:
        start, anzahl = int(RATE * beginn), int(RATE * dauer)
        for i in range(anzahl):
            t = i / RATE
            huelle = min(1.0, i / 120.0, (anzahl - i) / 300.0)   # ohne Knacken an Anfang und Ende
            proben[start + i] += laut * huelle * _probe(art, freq, t, dauer, ziel)
    spitze = max(1e-6, max(abs(p) for p in proben))
    faktor = 0.55 * 32767 / spitze
    roh = b"".join(struct.pack("<h", int(p * faktor)) for p in proben)
    puffer = io.BytesIO()
    with wave.open(puffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(roh)
    return puffer.getvalue()


def datei(klang):
    """Pfad zur WAV-Datei (einmal erzeugt, im Temp-Ordner)."""
    if klang not in ARCHIV:
        klang = STANDARD
    pfad = os.path.join(tempfile.gettempdir(), "fernsehfranzi-klang52-%s-%d.wav" % (klang, os.getuid()))
    if not os.path.exists(pfad):
        tmp = pfad + ".neu"
        with open(tmp, "wb") as f:
            f.write(erzeuge(klang))
        os.replace(tmp, pfad)
    return pfad


def alle_vorbereiten():
    """Beim Start im Hintergrund: alle Klänge einmal rechnen, damit der erste Ton sofort kommt."""
    for k in ARCHIV:
        try:
            datei(k)
        except OSError:
            pass
