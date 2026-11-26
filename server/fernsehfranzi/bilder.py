"""FernsehFranzi 6.9.42 - eigene Bilder der Eltern (zuerst: Hintergründe der Startseite).

Nur Standardbibliothek: Format und Größe werden aus dem Dateikopf gelesen (PNG, JPEG, WebP), nichts wird umgerechnet.
Die Bilder liegen in den Gerätedaten (``bilder/hintergruende/``) und überleben jedes Update. Hochladen geht nur über die
Eltern-Seite (PIN); der Fernseher liest sie nur.
"""
import os
import re
import struct

HINTERGRUND_MAX_BYTES = 6 * 1024 * 1024        # ein Foto vom Handy passt, der Pi 3 zeigt es ohne Mühe
HINTERGRUND_MIN = (800, 450)
HINTERGRUND_HOECHSTENS = 3000 * 3000           # Pixel - größere Bilder kosten den Pi 3 zu viel Speicher
HINTERGRUND_ANZAHL = 20
NAME = re.compile(r"\Ahg-[0-9a-f]{12}\.(png|jpg|webp)\Z")
TYPEN = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}


def art_und_groesse(daten):
    """(endung, breite, hoehe) aus dem Dateikopf, sonst ValueError."""
    if daten[:8] == b"\x89PNG\r\n\x1a\n" and daten[12:16] == b"IHDR":
        b, h = struct.unpack(">II", daten[16:24])
        return "png", b, h
    if daten[:3] == b"\xff\xd8\xff":
        i = 2
        while i + 9 < len(daten):
            if daten[i] != 0xFF:
                i += 1
                continue
            marke = daten[i + 1]
            if marke in (0xD8, 0x01) or 0xD0 <= marke <= 0xD7:
                i += 2
                continue
            laenge = struct.unpack(">H", daten[i + 2:i + 4])[0]
            if marke in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, b = struct.unpack(">HH", daten[i + 5:i + 9])
                return "jpg", b, h
            i += 2 + laenge
        raise ValueError("Das JPEG-Bild ist beschädigt.")
    if daten[:4] == b"RIFF" and daten[8:12] == b"WEBP":
        kopf = daten[12:16]
        if kopf == b"VP8X":
            b = 1 + int.from_bytes(daten[24:27], "little")
            h = 1 + int.from_bytes(daten[27:30], "little")
            return "webp", b, h
        if kopf == b"VP8 ":
            b, h = struct.unpack("<HH", daten[26:30])
            return "webp", b & 0x3FFF, h & 0x3FFF
        if kopf == b"VP8L":
            bits = int.from_bytes(daten[21:25], "little")
            return "webp", (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    raise ValueError("Bitte ein Bild als PNG, JPEG oder WebP.")


def pruefe_hintergrund(daten):
    """Endung oder ValueError mit verständlichem Text."""
    if len(daten) > HINTERGRUND_MAX_BYTES:
        raise ValueError("Das Bild ist zu groß (höchstens %d MB)." % (HINTERGRUND_MAX_BYTES // 1024 // 1024))
    endung, b, h = art_und_groesse(daten)
    if b < HINTERGRUND_MIN[0] or h < HINTERGRUND_MIN[1]:
        raise ValueError("Das Bild ist zu klein (mindestens %d × %d Pixel, am besten 1920 × 1080)." % HINTERGRUND_MIN)
    if b * h > HINTERGRUND_HOECHSTENS:
        raise ValueError("Das Bild hat zu viele Pixel (%d × %d) – bitte auf höchstens 1920 × 1080 verkleinern." % (b, h))
    return endung


def liste(ordner):
    try:
        return sorted(n for n in os.listdir(ordner) if NAME.match(n))
    except FileNotFoundError:
        return []


# ------------------------------------------------------------ 6.9.52: Bild-Plätze (eigene Bilder statt der Vorgaben)
# Platz = Datei unter web/bilder/ ; (Name, Gruppe, Mindestgröße, Seitenverhältnis, durchsichtig nötig)
BILDPLATZ_MAX_BYTES = 6 * 1024 * 1024
BILDPLAETZE = {
    "raeume/raum-1.jpg": ("Kinderzimmer (Raum 1)", "Räume", (1200, 990), 1600 / 1320, False),
    "raeume/raum-2.jpg": ("Sonnenzimmer (Raum 2)", "Räume", (1200, 990), 1600 / 1320, False),
    "raeume/raum-3.jpg": ("Proberaum (Raum 3)", "Räume", (1200, 990), 1600 / 1320, False),
    "raeume/raum-garten.jpg": ("Garten", "Räume", (1200, 990), 1600 / 1320, False),
    "raeume/raum-kueche.jpg": ("Küche (Raum 4)", "Räume", (1200, 990), 1600 / 1320, False),
    "raeume/raum-spiel.jpg": ("Spielzimmer", "Räume", (1200, 990), 1600 / 1320, False),
    "postkarten/rueckseite.png": ("Rückseite (für alle)", "Postkarten", (900, 600), 1.5, False),
    "postkarten/marke-1.png": ("Briefmarke 1", "Postkarten", (120, 150), None, True),
    "postkarten/marke-2.png": ("Briefmarke 2", "Postkarten", (120, 150), None, True),
}
for _k, _n in (("berge", "Berge"), ("billigurlaub", "Billigurlaub"), ("erholung", "Erholungsurlaub"), ("strand", "Strand"),
               ("thailand", "Thailand"), ("tirol", "Tirol"), ("wildwasser", "Wildwasser")):
    BILDPLAETZE["postkarten/%s.jpg" % _k] = ("Postkarte %s" % _n, "Postkarten", (900, 600), 1.5, False)
for _t in ("offen", "zu", "bogen", "gross", "herz", "dizzy", "muede", "sauer"):
    BILDPLAETZE["franzi/augen-%s.png" % _t] = ("Augen „%s“" % _t, "Franzi (Augen und Münder)", (512, 512), 1.0, True)
for _t in ("laecheln", "lachen", "klein", "staunen", "grimmig", "sauer", "zunge-raus"):
    BILDPLAETZE["franzi/mund-%s.png" % _t] = ("Mund „%s“" % _t, "Franzi (Augen und Münder)", (512, 512), 1.0, True)


def durchsichtig(daten):
    """PNG mit Alpha-Kanal (Farbtyp 4/6) oder tRNS-Block."""
    return daten[:8] == b"\x89PNG\r\n\x1a\n" and (daten[25] in (4, 6) or b"tRNS" in daten[:4096])


def pruefe_bildplatz(platz, daten):
    """Endung des Bildes oder ValueError mit verständlichem Text."""
    if platz not in BILDPLAETZE:
        raise ValueError("Diesen Bild-Platz gibt es nicht.")
    name, _, (mb, mh), verhaeltnis, alpha = BILDPLAETZE[platz]
    if len(daten) > BILDPLATZ_MAX_BYTES:
        raise ValueError("Das Bild ist zu groß (höchstens 6 MB).")
    endung, b, h = art_und_groesse(daten)
    if b < mb or h < mh:
        raise ValueError("Das Bild ist zu klein: mindestens %d × %d Pixel." % (mb, mh))
    if b * h > HINTERGRUND_HOECHSTENS:
        raise ValueError("Das Bild hat zu viele Pixel – bitte verkleinern.")
    if verhaeltnis and abs(b / h - verhaeltnis) / verhaeltnis > 0.06:
        raise ValueError("Das Seitenverhältnis passt nicht (wie die Schablone: %s)." %
                         ("quadratisch" if verhaeltnis == 1.0 else "%d × %d" % (mb, mh)))
    if alpha and not (endung == "png" and durchsichtig(daten)):
        raise ValueError("Hier braucht es ein PNG mit durchsichtigem Hintergrund.")
    return endung
