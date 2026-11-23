"""FernsehFranzi 4.3 - QR-Codes für den Spielraum (Handys scannen den Code am Fernseher).

Nur Python-Standardbibliothek (Grundsatz 13, docs/ENTWICKLUNG.md): Byte-Modus, Fehlerkorrektur M, Versionen 1 bis 10
(bis 213 Zeichen - eine Adresse im Heimnetz braucht etwa 50). Aufbau nach ISO/IEC 18004: Datenbits, Reed-Solomon über
GF(256), Verschränken der Blöcke, Funktionsmuster, Zickzack-Platzierung, die günstigste der acht Masken,
Format- und Versionsinformation.

    matrix(text)  -> Liste von Zeilen mit True (dunkel) / False
    svg(text)     -> SVG-Text (mit Ruhezone), zum Einbetten in die Startseite
"""

KORREKTUR_M = 0                      # Formatbits: L=1, M=0, Q=3, H=2
EC_JE_BLOCK = [None, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26]
BLOECKE = [None, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5]
AUSRICHTUNG = [None, [], [6, 18], [6, 22], [6, 26], [6, 30], [6, 34], [6, 22, 38], [6, 24, 42], [6, 26, 46],
               [6, 28, 50]]
VERSION_MAX = 10


# ---------------------------------------------------------------- Galois-Feld und Reed-Solomon
def _mal(x, y):
    z = 0
    for i in range(7, -1, -1):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def _teiler(grad):
    ergebnis = [0] * (grad - 1) + [1]
    wurzel = 1
    for _ in range(grad):
        for j in range(grad):
            ergebnis[j] = _mal(ergebnis[j], wurzel)
            if j + 1 < grad:
                ergebnis[j] ^= ergebnis[j + 1]
        wurzel = _mal(wurzel, 0x02)
    return ergebnis


def _rest(daten, teiler):
    ergebnis = [0] * len(teiler)
    for b in daten:
        faktor = b ^ ergebnis.pop(0)
        ergebnis.append(0)
        for i, t in enumerate(teiler):
            ergebnis[i] ^= _mal(t, faktor)
    return ergebnis


# ---------------------------------------------------------------- Größen
def _roh_module(version):
    ergebnis = (16 * version + 128) * version + 64
    if version >= 2:
        anzahl = version // 7 + 2
        ergebnis -= (25 * anzahl - 10) * anzahl - 55
        if version >= 7:
            ergebnis -= 36
    return ergebnis


def _datenbytes(version):
    return _roh_module(version) // 8 - EC_JE_BLOCK[version] * BLOECKE[version]


def _version_fuer(laenge):
    for v in range(1, VERSION_MAX + 1):
        kopf = 4 + (8 if v < 10 else 16)
        if kopf + 8 * laenge <= 8 * _datenbytes(v):
            return v
    raise ValueError("Text zu lang für einen QR-Code (höchstens %d Zeichen)." % (_datenbytes(VERSION_MAX) - 3))


# ---------------------------------------------------------------- Bits und Codewörter
def _codewoerter(daten, version):
    bits = []

    def schreibe(wert, laenge):
        bits.extend((wert >> i) & 1 for i in range(laenge - 1, -1, -1))

    schreibe(0b0100, 4)                                   # Byte-Modus
    schreibe(len(daten), 8 if version < 10 else 16)
    for b in daten:
        schreibe(b, 8)
    kapazitaet = 8 * _datenbytes(version)
    schreibe(0, min(4, kapazitaet - len(bits)))           # Abschluss
    schreibe(0, (-len(bits)) % 8)
    fuell = 0xEC
    while len(bits) < kapazitaet:
        schreibe(fuell, 8)
        fuell ^= 0xEC ^ 0x11
    bytes_ = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]

    # in Blöcke teilen, Fehlerkorrektur anhängen, verschränken
    bloecke, ec_laenge = BLOECKE[version], EC_JE_BLOCK[version]
    roh = _roh_module(version) // 8
    kurze = bloecke - roh % bloecke
    kurz_laenge = roh // bloecke
    teiler = _teiler(ec_laenge)
    liste, k = [], 0
    for i in range(bloecke):
        n = kurz_laenge - ec_laenge + (0 if i < kurze else 1)
        teil = bytes_[k:k + n]
        k += n
        ec = _rest(teil, teiler)
        if i < kurze:
            teil = teil + [0]                              # Platzhalter, damit alle Blöcke gleich lang sind
        liste.append(teil + ec)
    ergebnis = []
    for i in range(len(liste[0])):
        for j, block in enumerate(liste):
            if i != kurz_laenge - ec_laenge or j >= kurze:
                ergebnis.append(block[i])
    return ergebnis


# ---------------------------------------------------------------- Matrix
class _Matrix:
    def __init__(self, version):
        self.version = version
        self.groesse = 17 + 4 * version
        self.m = [[False] * self.groesse for _ in range(self.groesse)]
        self.funktion = [[False] * self.groesse for _ in range(self.groesse)]

    def setze(self, x, y, dunkel):
        self.m[y][x] = bool(dunkel)
        self.funktion[y][x] = True

    def funktionsmuster(self):
        g = self.groesse
        for i in range(g):                                 # Taktlinien
            self.setze(6, i, i % 2 == 0)
            self.setze(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (g - 4, 3), (3, g - 4)):   # Suchmuster mit Trennrand
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < g and 0 <= y < g:
                        self.setze(x, y, max(abs(dx), abs(dy)) not in (2, 4))
        pos = AUSRICHTUNG[self.version]
        for i, ax in enumerate(pos):                       # Ausrichtungsmuster
            for j, ay in enumerate(pos):
                if (i == 0 and j == 0) or (i == 0 and j == len(pos) - 1) or (i == len(pos) - 1 and j == 0):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self.setze(ax + dx, ay + dy, max(abs(dx), abs(dy)) != 1)
        self.format(0)                                     # Platz reservieren
        if self.version >= 7:
            rest = self.version
            for _ in range(12):
                rest = (rest << 1) ^ ((rest >> 11) * 0x1F25)
            bits = self.version << 12 | rest
            for i in range(18):
                a, b = g - 11 + i % 3, i // 3
                bit = (bits >> i) & 1
                self.setze(a, b, bit)
                self.setze(b, a, bit)

    def format(self, maske):
        daten = KORREKTUR_M << 3 | maske
        rest = daten
        for _ in range(10):
            rest = (rest << 1) ^ ((rest >> 9) * 0x537)
        bits = (daten << 10 | rest) ^ 0x5412
        bit = lambda i: (bits >> i) & 1             # noqa: E731
        g = self.groesse
        for i in range(6):
            self.setze(8, i, bit(i))
        self.setze(8, 7, bit(6))
        self.setze(8, 8, bit(7))
        self.setze(7, 8, bit(8))
        for i in range(9, 15):
            self.setze(14 - i, 8, bit(i))
        for i in range(8):
            self.setze(g - 1 - i, 8, bit(i))
        for i in range(8, 15):
            self.setze(8, g - 15 + i, bit(i))
        self.setze(8, g - 8, True)                         # immer dunkel

    def daten(self, codewoerter):
        g, i = self.groesse, 0
        rechts = g - 1
        while rechts >= 1:
            if rechts == 6:
                rechts = 5
            for senkrecht in range(g):
                for j in range(2):
                    x = rechts - j
                    aufwaerts = ((rechts + 1) & 2) == 0
                    y = g - 1 - senkrecht if aufwaerts else senkrecht
                    if not self.funktion[y][x] and i < len(codewoerter) * 8:
                        self.m[y][x] = bool((codewoerter[i >> 3] >> (7 - (i & 7))) & 1)
                        i += 1
            rechts -= 2

    def maskiere(self, maske):
        formeln = [lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0,
                   lambda x, y: (x + y) % 3 == 0, lambda x, y: (x // 3 + y // 2) % 2 == 0,
                   lambda x, y: x * y % 2 + x * y % 3 == 0, lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
                   lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0]
        f = formeln[maske]
        for y in range(self.groesse):
            for x in range(self.groesse):
                if not self.funktion[y][x] and f(x, y):
                    self.m[y][x] = not self.m[y][x]

    def strafe(self):
        """Strafpunkte nach der Norm (N1 bis N4) - wählt die am besten lesbare Maske."""
        g, m, punkte = self.groesse, self.m, 0
        for linien in (m, [list(s) for s in zip(*m)]):
            for zeile in linien:
                lauf, farbe = 1, zeile[0]
                for wert in zeile[1:]:
                    if wert == farbe:
                        lauf += 1
                    else:
                        punkte += lauf - 2 if lauf >= 5 else 0
                        lauf, farbe = 1, wert
                punkte += lauf - 2 if lauf >= 5 else 0
                text = "".join("1" if w else "0" for w in zeile)
                punkte += 40 * (text.count("10111010000") + text.count("00001011101"))
        for y in range(g - 1):
            for x in range(g - 1):
                if m[y][x] == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                    punkte += 3
        dunkel = sum(sum(z) for z in m)
        punkte += abs(dunkel * 20 - g * g * 10) // (g * g) * 10
        return punkte


def matrix(text):
    daten = list(str(text).encode("utf-8"))
    version = _version_fuer(len(daten))
    codewoerter = _codewoerter(daten, version)
    beste = None
    for maske in range(8):
        q = _Matrix(version)
        q.funktionsmuster()
        q.daten(codewoerter)
        q.maskiere(maske)
        q.format(maske)
        punkte = q.strafe()
        if beste is None or punkte < beste[0]:
            beste = (punkte, q)
    return beste[1].m


def svg(text, rand=4):
    m = matrix(text)
    g = len(m) + 2 * rand
    pfad = "".join("M%d %dh1v1h-1z" % (x + rand, y + rand) for y, zeile in enumerate(m) for x, d in enumerate(zeile) if d)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" shape-rendering="crispEdges">'
            '<rect width="%d" height="%d" fill="#fff"/><path d="%s" fill="#000"/></svg>') % (g, g, g, g, pfad)
