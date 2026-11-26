"""Franzis Bilder für die Weboberfläche vorbereiten (nur am Entwicklungsrechner, braucht Pillow).

Quelle: die gezeichneten Einzelteile in Graustufen (512 × 512 auf der Franzi-Schablone), Abgabe-Ordner (nicht versioniert).
Ziel:   web/bilder/franzi/ – Körper und Arme je Farbe eingefärbt (nur das Gehäuse; Bildschirm, Weiß und farbige
        Stellen bleiben), Augen und Münder unverändert. Aufruf aus dem Projektordner:
        python3 werkzeuge/franzi_bilder.py .local/bilder/abgabe
"""
import os
import sys

from PIL import Image, ImageOps

FARBEN = {"grau": None, "orange": "#ff7a59", "blau": "#4f8df5", "gruen": "#3fb37a", "lila": "#9b6bdc", "gold": "gold"}
GEFAERBT = ["koerper", "arm-links-oben", "arm-links-unten", "arm-rechts-oben", "arm-rechts-unten",
            # 6.9.53: Antennen-Blinken (das leuchtende Kügelchen bleibt rot/grün, der Rest wird mit eingefärbt)
            "anim-antennen-blinken-gruen_01a", "anim-antennen-blinken-gruen_01b", "anim-antennen-blinken-rot_01a", "anim-antennen-blinken-rot_01b"]
GESICHT = None    # alle franzi-augen-*/franzi-mund-* aus der Abgabe (Namen klein, „Zunge-raus“ -> „zunge-raus“)


GOLD = ("#2a1600", "#c98a12", "#ffe48a")      # 6.9.57: Deluxe-Gold - dunkles Bernstein, sattes Gold, helle Glanzlichter


def einfaerben(im, farbe):
    if not farbe:
        return im
    a = im.getchannel("A")
    rgb = im.convert("RGB")
    maske = Image.new("L", im.size, 0)
    px, m = rgb.load(), maske.load()
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            r, g, b = px[x, y]
            if max(r, g, b) - min(r, g, b) > 12:      # schon farbig (z. B. Zunge): bleibt
                m[x, y] = 255
    if farbe == "gold":                       # Metall statt Farbe: mehr Kontrast, warme Schatten, helle Kanten
        hell = ImageOps.autocontrast(im.convert("L"), cutoff=1)
        bunt = ImageOps.colorize(hell, GOLD[0], GOLD[2], mid=GOLD[1], blackpoint=30, whitepoint=255, midpoint=190).convert("RGBA")
    else:
        bunt = ImageOps.colorize(im.convert("L"), "#000000", "#ffffff", mid=farbe, blackpoint=20, whitepoint=250, midpoint=150).convert("RGBA")
    bunt = Image.composite(im, bunt, maske)
    bunt.putalpha(a)
    return bunt


def main(quelle, ziel="web/bilder/franzi"):
    import glob
    os.makedirs(ziel, exist_ok=True)
    quellen = {t: os.path.join(quelle, "franzi-%s_grau.png" % t) for t in GEFAERBT if not t.startswith("anim-")}
    for t in GEFAERBT:
        if t.startswith("anim-"):
            quellen[t.replace("anim-antennen-blinken-", "antenne-").replace("_01", "-")] = os.path.join(quelle, "franzi-%s.png" % t)
    for pfad in sorted(glob.glob(os.path.join(quelle, "franzi-augen-*_grau.png")) + glob.glob(os.path.join(quelle, "franzi-mund-*_grau.png"))):
        quellen[os.path.basename(pfad)[len("franzi-"):-len("_grau.png")].lower()] = pfad
    for teil, pfad in quellen.items():
        im = Image.open(pfad).convert("RGBA")
        if im.size != (512, 512):
            raise SystemExit("%s ist nicht 512 × 512" % teil)
        for name, farbe in (FARBEN.items() if teil in GEFAERBT or teil.startswith("antenne-") else [("", None)]):
            datei = os.path.join(ziel, "%s%s.png" % (teil, "-" + name if name else ""))
            einfaerben(im, farbe).save(datei, optimize=True)
    print("fertig:", len(os.listdir(ziel)), "Dateien in", ziel)


if __name__ == "__main__":
    main(*sys.argv[1:])
