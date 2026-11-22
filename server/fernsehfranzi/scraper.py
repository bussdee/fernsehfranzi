"""FernsehFranzi 4.2 - Bilder für Retro-Spiele holen („Scraper“), ohne Konto und ohne große Installation.

Im Kiosk-Modus blendet EmulationStation seinen eigenen Scraper aus (das Kind soll dort nichts verstellen). Dieser
Scraper läuft stattdessen auf Knopfdruck von der Eltern-Seite (und nachts von selbst) als eigener Dienst
(fernsehfranzi-scraper.service, als Kiosk-Benutzer) - der Server selbst darf ~/.emulationstation nicht beschreiben.

Quelle: die freien Spielbilder des libretro-Projekts (github.com/libretro-thumbnails, eine Ablage je System:
Named_Boxarts = Hülle, Named_Titles = Titelbild, Named_Snaps = Bild aus dem Spiel). Die Dateinamen dort folgen
No-Intro bzw. TOSEC - genau so heißen die meisten ROMs. Erst wird der genaue Name gesucht, dann ein vereinfachter
(ohne Klammern, Groß-/Kleinschreibung, „The“).

Ergebnis: Bild nach ~/.emulationstation/downloaded_images/<system>/<rom>-image.png und in der Spieleliste
~/.emulationstation/gamelists/<system>/gamelist.xml <image> (und <name> ohne Klammern, wenn noch keiner da ist).
Vorhandene Einträge (gespielt, Favorit, Beschreibung …) bleiben unangetastet. Läuft RetroPie, wird nichts geschrieben
(EmulationStation überschreibt die Spielelisten beim Beenden).

    python3 -m fernsehfranzi.scraper          (so startet ihn der Dienst)
"""
import json
import logging
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

log = logging.getLogger("fernsehfranzi.scraper")

# EmulationStation-System -> libretro-thumbnails-Ablage
SYSTEME = {
    "c64": "Commodore_-_64", "amiga": "Commodore_-_Amiga", "nes": "Nintendo_-_Nintendo_Entertainment_System",
    "fds": "Nintendo_-_Family_Computer_Disk_System", "snes": "Nintendo_-_Super_Nintendo_Entertainment_System",
    "n64": "Nintendo_-_Nintendo_64", "gb": "Nintendo_-_Game_Boy", "gbc": "Nintendo_-_Game_Boy_Color",
    "gba": "Nintendo_-_Game_Boy_Advance", "megadrive": "Sega_-_Mega_Drive_-_Genesis",
    "genesis": "Sega_-_Mega_Drive_-_Genesis", "mastersystem": "Sega_-_Master_System_-_Mark_III",
    "gamegear": "Sega_-_Game_Gear", "sega32x": "Sega_-_32X", "segacd": "Sega_-_Mega-CD_-_Sega_CD",
    "sg-1000": "Sega_-_SG-1000", "dreamcast": "Sega_-_Dreamcast", "psx": "Sony_-_PlayStation",
    "pcengine": "NEC_-_PC_Engine_-_TurboGrafx_16", "neogeo": "SNK_-_Neo_Geo", "ngp": "SNK_-_Neo_Geo_Pocket",
    "ngpc": "SNK_-_Neo_Geo_Pocket_Color", "atari2600": "Atari_-_2600", "atari5200": "Atari_-_5200",
    "atari7800": "Atari_-_7800", "atari800": "Atari_-_8-bit", "atarilynx": "Atari_-_Lynx",
    "amstradcpc": "Amstrad_-_CPC", "zxspectrum": "Sinclair_-_ZX_Spectrum", "msx": "Microsoft_-_MSX",
    "coleco": "Coleco_-_ColecoVision", "vectrex": "GCE_-_Vectrex", "channelf": "Fairchild_-_Channel_F",
    "fba": "FBNeo_-_Arcade_Games", "arcade": "MAME", "mame-libretro": "MAME",
}
ORDNER = ("Named_Boxarts", "Named_Titles", "Named_Snaps")
API = "https://api.github.com/repos/libretro-thumbnails/%s/git/trees/%s"
ROH = "https://raw.githubusercontent.com/libretro-thumbnails/%s/master/%s/%s.png"
KEINE_ROMS = {".txt", ".cfg", ".xml", ".srm", ".sav", ".state", ".png", ".jpg", ".jpeg", ".sh", ".lpl", ".nfo",
              ".bin", ".img", ".sub", ".ccd"}           # .bin/.img gehören zu .cue-Spielen
CACHE_TAGE = 14
BILD_MAX = 3 * 1024 * 1024
KOPF = {"User-Agent": "FernsehFranzi-Scraper", "Accept": "application/vnd.github+json"}


def libretro_name(rom_name):
    """libretro ersetzt diese Zeichen im Dateinamen durch _."""
    return re.sub(r'[&*/:`<>?\\|"]', "_", rom_name)


def vereinfacht(name):
    """'Great Giana Sisters, The (Europe) [cr]' -> 'thegreatgianasisters'."""
    name = re.sub(r"^(Amiga)?CD32[ _-]+", "", name, flags=re.I)          # „AmigaCD32_DerClou“
    name = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", name)
    m = re.match(r"^(.*), (the|der|die|das)\s*$", name.strip(), re.I)
    if m:
        name = m.group(2) + " " + m.group(1)
    name = re.sub(r"\s(&|_|and|und)\s", " ", " %s " % name.lower())         # „Track & Field“ = „Track _ Field“
    return re.sub(r"[^a-z0-9]", "", name)


def schluessel(name):
    """Vergleichsformen: mit Artikel vorn und ohne Artikel („Great Giana Sisters“ = „Great Giana Sisters, The“)."""
    voll = vereinfacht(name)
    return {voll, re.sub(r"^(the|der|die|das)", "", voll)} - {""}


def schoener_name(rom_name):
    """Name für die Spieleliste: ohne Klammern, 'Giana Sisters, The' -> 'The Giana Sisters'."""
    name = re.sub(r"\s*(\([^)]*\)|\[[^\]]*\])", "", rom_name).strip() or rom_name
    m = re.match(r"^(.*), (The|Der|Die|Das)$", name)
    return "%s %s" % (m.group(2), m.group(1)) if m else name


def _hole_json(url, oeffne):
    with oeffne(urllib.request.Request(url, headers=KOPF), timeout=30) as antwort:
        return json.loads(antwort.read().decode("utf-8"))


def bildnamen(ablage, cache_ordner, oeffne=urllib.request.urlopen, jetzt=time.time):
    """{ordner: [namen ohne .png]} einer Ablage - 14 Tage zwischengespeichert (GitHub erlaubt 60 Abfragen/Stunde)."""
    cache = os.path.join(cache_ordner, ablage + ".json")
    try:
        if jetzt() - os.path.getmtime(cache) < CACHE_TAGE * 86400:
            with open(cache, encoding="utf-8") as f:
                return json.load(f)
    except (OSError, ValueError):
        pass
    wurzel = _hole_json(API % (ablage, "master"), oeffne)
    namen = {}
    for eintrag in wurzel.get("tree", []):
        if eintrag.get("type") == "tree" and eintrag.get("path") in ORDNER:
            unter = _hole_json(API % (ablage, eintrag["sha"]), oeffne)
            namen[eintrag["path"]] = sorted(e["path"][:-4] for e in unter.get("tree", [])
                                            if e.get("type") == "blob" and e["path"].endswith(".png"))
    os.makedirs(cache_ordner, exist_ok=True)
    with open(cache + ".neu", "w", encoding="utf-8") as f:
        json.dump(namen, f)
    os.replace(cache + ".neu", cache)
    return namen


def verzeichnis(namen):
    """Einmal je System: {ordner: (Menge der Namen, {Vergleichsform: [Namen]})} - schnell genug für den Pi 3."""
    index = {}
    for ordner in ORDNER:
        formen = {}
        for n in namen.get(ordner, ()):
            for k in schluessel(n):
                formen.setdefault(k, []).append(n)
        index[ordner] = (set(namen.get(ordner, ())), formen)
    return index


def passendes_bild(rom_name, namen, index=None):
    """(ordner, name) oder None. Erst genauer Name, dann vereinfacht - Hülle vor Titelbild vor Spielbild."""
    index = index or verzeichnis(namen)
    genau = libretro_name(rom_name)
    for ordner in ORDNER:
        if genau in index[ordner][0]:
            return ordner, genau
    ziel = schluessel(rom_name)
    for ordner in ORDNER:
        treffer = sorted({n for k in ziel for n in index[ordner][1].get(k, ())},
                         key=lambda n: ("(Europe)" not in n and "(Germany)" not in n, "[" in n, len(n), n))
        if treffer:
            return ordner, treffer[0]
    return None


def roms_von(ordner):
    """Spiele eines Systems (relativ, nur oberste Ebene, ohne versteckte Ordner)."""
    if not os.path.isdir(ordner):
        return []
    return sorted(n for n in os.listdir(ordner) if not n.startswith((".", "+")) and os.path.isfile(os.path.join(ordner, n))
                  and os.path.splitext(n)[1].lower() not in KEINE_ROMS)


def _lies_liste(datei):
    try:
        return ET.parse(datei).getroot()
    except (OSError, ET.ParseError):
        return ET.Element("gameList")


def _schreibe_liste(datei, wurzel):
    ET.indent(wurzel, space="\t")
    os.makedirs(os.path.dirname(datei), exist_ok=True)
    with open(datei + ".ff-neu", "wb") as f:
        f.write(b'<?xml version="1.0"?>\n')
        f.write(ET.tostring(wurzel, encoding="utf-8"))
        f.write(b"\n")
    os.replace(datei + ".ff-neu", datei)


def system_bearbeiten(system, roms, gamelists, bilder, cache, oeffne=urllib.request.urlopen):
    """Ein System: fehlende Bilder holen und eintragen. Rückgabe {gesamt, neu, ohne: [Spiele ohne Bild]}."""
    datei = os.path.join(gamelists, system, "gamelist.xml")
    wurzel = _lies_liste(datei)
    eintraege = {(g.findtext("path") or "").strip(): g for g in wurzel.iter("game")}
    spiele = roms_von(os.path.join(roms, system))
    ergebnis = {"gesamt": len(spiele), "neu": 0, "ohne": []}
    offen = []
    for rom in spiele:
        g = eintraege.get("./" + rom)
        bild = (g.findtext("image") or "").strip() if g is not None else ""
        if bild and os.path.isfile(os.path.expanduser(bild)):
            continue
        offen.append(rom)
    if not offen:
        return ergebnis
    namen = bildnamen(SYSTEME[system], cache, oeffne)
    index = verzeichnis(namen)
    geaendert = False
    for rom in offen:
        basis = os.path.splitext(rom)[0]
        treffer = passendes_bild(basis, namen, index)
        if not treffer:
            ergebnis["ohne"].append(schoener_name(basis))
            continue
        ziel = os.path.join(bilder, system, basis + "-image.png")
        try:
            url = ROH % (SYSTEME[system], treffer[0], urllib.parse.quote(treffer[1]))
            with oeffne(urllib.request.Request(url, headers={"User-Agent": KOPF["User-Agent"]}), timeout=30) as a:
                inhalt = a.read(BILD_MAX + 1)
            if not inhalt.startswith(b"\x89PNG") or len(inhalt) > BILD_MAX:
                raise ValueError("kein PNG")
        except (OSError, ValueError) as fehler:
            log.warning("Bild für %s/%s nicht geholt: %s", system, rom, fehler)
            ergebnis["ohne"].append(schoener_name(basis))
            continue
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(ziel, "wb") as f:
            f.write(inhalt)
        g = eintraege.get("./" + rom)
        if g is None:
            g = ET.SubElement(wurzel, "game")
            ET.SubElement(g, "path").text = "./" + rom
            eintraege["./" + rom] = g
        if not (g.findtext("name") or "").strip():
            (g.find("name") if g.find("name") is not None else ET.SubElement(g, "name")).text = schoener_name(basis)
        (g.find("image") if g.find("image") is not None else ET.SubElement(g, "image")).text = \
            "~/.emulationstation/downloaded_images/%s/%s-image.png" % (system, basis)
        ergebnis["neu"] += 1
        geaendert = True
    if geaendert:
        _schreibe_liste(datei, wurzel)
    return ergebnis


def retro_laeuft():
    aktiv = subprocess.run(["systemctl", "is-active", "--quiet", "fernsehfranzi-retropie.service",
                            "fernsehfranzi-spiel.service"]).returncode == 0
    return aktiv or subprocess.run(["pgrep", "-x", "emulationstatio"], capture_output=True).returncode == 0


def laufen(roms, gamelists, bilder, daten, oeffne=urllib.request.urlopen, laeuft_retro=retro_laeuft, jetzt=time.time):
    """Alle Systeme mit Spielen. Fortschritt in <daten>/scraper.json (die Eltern-Seite zeigt ihn)."""
    status_datei = os.path.join(daten, "scraper.json")
    status = {"laeuft": True, "start": int(jetzt()), "ende": None, "systeme": {}, "fehler": ""}

    def speichern():
        with open(status_datei + ".neu", "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False)
        os.replace(status_datei + ".neu", status_datei)

    if laeuft_retro():
        status.update(laeuft=False, ende=int(jetzt()), fehler="RetroPie läuft gerade – bitte erst zur Startseite.")
        speichern()
        return status
    speichern()
    for system in sorted(s for s in SYSTEME if roms_von(os.path.join(roms, s))):
        if laeuft_retro():
            status["fehler"] = "RetroPie wurde gestartet – abgebrochen, der Rest kommt beim nächsten Mal."
            break
        try:
            status["systeme"][system] = system_bearbeiten(system, roms, gamelists, bilder,
                                                          os.path.join(daten, "scraper-cache"), oeffne)
        except (OSError, ValueError) as fehler:
            log.warning("Scraper %s: %s", system, fehler)
            status["systeme"][system] = {"gesamt": len(roms_von(os.path.join(roms, system))), "neu": 0, "ohne": [],
                                         "fehler": "Bilderliste nicht erreichbar (%s)" % str(fehler)[:80]}
        speichern()
    status.update(laeuft=False, ende=int(jetzt()))
    speichern()
    return status


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    home = os.path.expanduser("~")
    daten = os.environ.get("FERNSEHFRANZI_DATEN", os.path.join(home, "fernsehfranzi-daten"))
    s = laufen(os.path.join(home, "RetroPie", "roms"), os.path.join(home, ".emulationstation", "gamelists"),
               os.path.join(home, ".emulationstation", "downloaded_images"), daten)
    log.info("Scraper fertig: %s neue Bilder. %s", sum(x.get("neu", 0) for x in s["systeme"].values()), s["fehler"])


if __name__ == "__main__":
    main()
