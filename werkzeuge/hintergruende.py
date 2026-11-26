#!/usr/bin/env python3
"""FernsehFranzi 6.0 - zeichnet die Hintergrund-Motive (eins je Farbe) als kleine SVG-Dateien nach web/hintergrund/.

Die Motive liegen am Rand und unten, damit die Kacheln lesbar bleiben, und sind ruhig (keine Bewegung, Pi 3).
Zufall mit festem Startwert: jeder Lauf erzeugt dieselben Dateien.  Aufruf: python3 werkzeuge/hintergruende.py
"""
import math
import os
import random

ZIEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "hintergrund")
B, H = 1600, 900


def svg(inhalt):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {B} {H}" preserveAspectRatio="xMidYMax slice">'
            + "".join(inhalt) + "</svg>\n")


def sterne(r, n, farbe="#fff", gross=2.2, deckkraft=(.25, .8), oben=1.0):
    aus = []
    for _ in range(n):
        x, y = r.uniform(0, B), r.uniform(0, H * oben) ** 1.15 / (H * oben) ** .15
        aus.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r.uniform(.6, gross):.1f}" fill="{farbe}" '
                   f'opacity="{r.uniform(*deckkraft):.2f}"/>')
    return aus


def funkeln(x, y, s, farbe, deckkraft=.8):
    return (f'<path d="M{x} {y - s}Q{x} {y} {x + s} {y}Q{x} {y} {x} {y + s}Q{x} {y} {x - s} {y}Q{x} {y} {x} {y - s}Z" '
            f'fill="{farbe}" opacity="{deckkraft}"/>')


def huegel(y, hoehe, farbe, r, wellen=3, deckkraft=1.0):
    pts = []
    phase = r.uniform(0, 6.28)
    for i in range(0, B + 1, 40):
        pts.append(f"{i},{y - hoehe * (0.5 + 0.5 * math.sin(i / B * math.pi * wellen + phase)):.0f}")
    return f'<polygon points="0,{H} {" ".join(pts)} {B},{H}" fill="{farbe}" opacity="{deckkraft}"/>'


def berge(y, spitzen, farbe, r, deckkraft=1.0):
    pts, x = [f"0,{y}"], 0
    while x < B:
        x += r.uniform(120, 260)
        pts.append(f"{x:.0f},{y - r.uniform(*spitzen):.0f}")
        x += r.uniform(80, 180)
        pts.append(f"{x:.0f},{y - r.uniform(0, spitzen[0] * .5):.0f}")
    return f'<polygon points="0,{H} {" ".join(pts)} {B},{y} {B},{H}" fill="{farbe}" opacity="{deckkraft}"/>'


def wolke(x, y, s, farbe="#fff", deckkraft=.75):
    teile = [(0, 0, 1), (-.9, .25, .7), (.9, .25, .75), (-.4, -.35, .7), (.45, -.3, .65)]
    kreise = "".join(f'<circle cx="{x + dx * 60 * s:.0f}" cy="{y + dy * 60 * s:.0f}" r="{rr * 50 * s:.0f}"/>'
                     for dx, dy, rr in teile)
    return f'<g fill="{farbe}" opacity="{deckkraft}">{kreise}<rect x="{x - 90 * s:.0f}" y="{y:.0f}" ' \
           f'width="{180 * s:.0f}" height="{45 * s:.0f}" rx="{22 * s:.0f}"/></g>'


def baum(x, y, s, farbe):
    return (f'<g fill="{farbe}"><rect x="{x - 4 * s:.0f}" y="{y - 20 * s:.0f}" width="{8 * s:.0f}" height="{22 * s:.0f}"/>'
            f'<polygon points="{x},{y - 120 * s:.0f} {x - 38 * s:.0f},{y - 20 * s:.0f} {x + 38 * s:.0f},{y - 20 * s:.0f}"/>'
            f'<polygon points="{x},{y - 150 * s:.0f} {x - 28 * s:.0f},{y - 70 * s:.0f} {x + 28 * s:.0f},{y - 70 * s:.0f}"/></g>')


def herz(x, y, s, farbe, deckkraft):
    return (f'<path transform="translate({x:.0f} {y:.0f}) scale({s:.2f})" d="M0 8C-10-8-30 0-18 16L0 32L18 16C30 0 10-8 0 8Z" '
            f'fill="{farbe}" opacity="{deckkraft:.2f}"/>')


def blume(x, y, s, farbe, mitte="#ffe27a"):
    blaetter = "".join(f'<circle cx="{x + math.cos(a) * 7 * s:.1f}" cy="{y + math.sin(a) * 7 * s:.1f}" r="{5 * s:.1f}"/>'
                       for a in [i * math.pi * 2 / 5 for i in range(5)])
    return f'<g fill="{farbe}">{blaetter}</g><circle cx="{x}" cy="{y}" r="{4 * s:.1f}" fill="{mitte}"/>'


def flocke(x, y, s, farbe, deckkraft):
    linien = "".join(f'<line x1="{x}" y1="{y}" x2="{x + math.cos(a) * s:.1f}" y2="{y + math.sin(a) * s:.1f}"/>'
                     for a in [i * math.pi / 3 for i in range(6)])
    return f'<g stroke="{farbe}" stroke-width="{max(1.5, s / 7):.1f}" stroke-linecap="round" opacity="{deckkraft:.2f}">{linien}</g>'


def weltraum(r):
    return svg(sterne(r, 140) + [
        '<circle cx="960" cy="105" r="52" fill="#5b7fd6" opacity=".55"/>',
        '<circle cx="945" cy="92" r="52" fill="#8fb0ff" opacity=".18"/>',
        '<ellipse cx="960" cy="105" rx="92" ry="18" fill="none" stroke="#b9cbff" stroke-width="6" opacity=".35" '
        'transform="rotate(-18 960 105)"/>',
        '<circle cx="1180" cy="60" r="16" fill="#c78bff" opacity=".35"/>',
        funkeln(760, 60, 14, "#fff", .7), funkeln(1120, 775, 12, "#fff", .5)])


def wald(r):
    teile = sterne(r, 40, "#d8ff8a", 2.6, (.25, .7), .55)
    teile += [huegel(800, 110, "#0c3a1f", r, 2, .9), huegel(860, 70, "#082c17", r, 3)]
    for x in list(range(30, 360, 70)) + list(range(1260, 1600, 70)):
        teile.append(baum(x + r.uniform(-15, 15), 870 + r.uniform(-10, 10), r.uniform(.8, 1.25), "#06240f"))
    return svg(teile)


def zaubernacht(r):
    teile = sterne(r, 110, "#fff", 2.0)
    teile += ['<circle cx="980" cy="100" r="54" fill="#fff3c4" opacity=".85"/>',
              '<circle cx="1004" cy="85" r="49" fill="#1a0d2e"/>']
    for _ in range(9):
        teile.append(funkeln(r.uniform(40, B - 40), r.uniform(40, H - 60), r.uniform(8, 18), "#e7c6ff", r.uniform(.35, .75)))
    teile.append(huegel(880, 50, "#170a29", r, 2, .9))
    return svg(teile)


def abendrot(r):
    return svg(['<circle cx="1250" cy="640" r="180" fill="#ffb15c" opacity=".22"/>',
                '<circle cx="1250" cy="640" r="120" fill="#ffcf7a" opacity=".25"/>',
                berge(760, (120, 260), "#3d1414", r, .85), berge(840, (60, 140), "#260a0a", r)]
               + sterne(r, 25, "#ffe0c2", 1.6, (.2, .5), .35))


def schwarz(r):
    return svg(sterne(r, 60, "#fff", 1.4, (.12, .35)))


def himmel(r):
    teile = [wolke(760, 120, .7), wolke(1040, 60, .55), wolke(30, 470, .6, deckkraft=.55), wolke(1300, 820, 1.3, deckkraft=.6),
             wolke(260, 830, 1.0, deckkraft=.55)]
    teile += ['<g transform="translate(1200 90) scale(.7)" opacity=".7"><path d="M0 0C-40 0-50 50 0 90C50 50 40 0 0 0Z" fill="#ff8a65"/>'
              '<path d="M0 0C-14 0-18 50 0 90C18 50 14 0 0 0Z" fill="#ffd54f"/>'
              '<rect x="-12" y="102" width="24" height="18" rx="3" fill="#8d6e63"/>'
              '<line x1="-9" y1="88" x2="-9" y2="103" stroke="#8d6e63" stroke-width="2"/>'
              '<line x1="9" y1="88" x2="9" y2="103" stroke="#8d6e63" stroke-width="2"/></g>']
    return svg(teile)


def wiese(r):
    teile = [huegel(820, 90, "#7fdcaa", r, 2, .7), huegel(870, 60, "#5fcf93", r, 3, .8), wolke(1100, 80, .6, deckkraft=.7),
             '<circle cx="880" cy="95" r="48" fill="#fff6a8" opacity=".75"/>']
    farben = ["#ff8fb1", "#ffffff", "#b39dff", "#ffb74d"]
    for _ in range(26):
        x = r.choice([r.uniform(20, 520), r.uniform(1080, 1580)])
        teile.append(blume(round(x), round(r.uniform(830, 890)), r.uniform(.9, 1.6), r.choice(farben)))
    return svg(teile)


def zuckerwatte(r):
    teile = ['<g fill="none" stroke-width="22" opacity=".28">'
             + "".join(f'<path d="M1080 900A330 330 0 0 1 1740 900" stroke="{f}" transform="translate(0 {i * 22})"/>'
                       for i, f in enumerate(["#ff6b9a", "#ffb15c", "#ffe066", "#7fdcaa", "#7fb6ff", "#b39dff"])) + "</g>",
             wolke(820, 100, .7), wolke(1120, 60, .5), wolke(300, 860, 1.0, deckkraft=.5)]
    for _ in range(14):
        teile.append(herz(r.choice([r.uniform(30, 480), r.uniform(1120, 1570)]), r.uniform(60, 820), r.uniform(.5, 1.1),
                          "#ff5c95", r.uniform(.2, .45)))
    return svg(teile)


def strand(r):
    strahlen = "".join(f'<line x1="{960 + math.cos(a) * 74:.0f}" y1="{110 + math.sin(a) * 74:.0f}" '
                       f'x2="{960 + math.cos(a) * 104:.0f}" y2="{110 + math.sin(a) * 104:.0f}"/>'
                       for a in [i * math.pi / 6 for i in range(12)])
    wellen = "".join(f'<path d="M0 {y} ' + " ".join(f"Q{x + 50} {y - 18} {x + 100} {y} T{x + 200} {y}" for x in range(0, B, 200))
                     + f' V{H} H0Z" fill="{f}" opacity="{o}"/>'
                     for y, f, o in ((800, "#4fc3f7", .45), (845, "#29b6f6", .5)))
    return svg(['<circle cx="960" cy="110" r="60" fill="#ffb300" opacity=".55"/>',
                f'<g stroke="#ff9800" stroke-width="9" stroke-linecap="round" opacity=".45">{strahlen}</g>',
                wellen, wolke(720, 70, .55, deckkraft=.7)])


def winter(r):
    teile = [huegel(830, 80, "#ffffff", r, 2, .9), huegel(880, 50, "#e8eef7", r, 3)]
    for _ in range(30):
        teile.append(flocke(round(r.uniform(20, B - 20)), round(r.uniform(30, 780)), r.uniform(7, 18), "#8fa3c2", r.uniform(.25, .55)))
    return svg(teile)


def rock(r):
    """6.7: Bühne mit Lautsprechern, Scheinwerfern und Gitarre (die Flammen bewegt die Startseite selbst)."""
    kegel = "".join(f'<path d="M{x} 0 L{x - 160} {H} L{x + 160} {H}Z" fill="#ff5a36" opacity=".07"/>' for x in (300, 800, 1300))
    boxen = "".join(f'<rect x="{x}" y="640" width="150" height="200" rx="10" fill="#1a0808"/>'
                    f'<circle cx="{x + 75}" cy="700" r="38" fill="#2b0f0f" stroke="#4a1a14" stroke-width="6"/>'
                    f'<circle cx="{x + 75}" cy="790" r="26" fill="#2b0f0f" stroke="#4a1a14" stroke-width="5"/>' for x in (40, 1410))
    gitarre = ('<g transform="translate(1250 520) rotate(-30)" opacity=".55"><rect x="-6" y="-220" width="12" height="200" fill="#3a1410"/>'
               '<path d="M0 -20 C-70 -20 -80 60 -40 80 C-90 120 -60 200 0 200 C60 200 90 120 40 80 C80 60 70 -20 0 -20Z" fill="#7a1f16"/>'
               '<circle cx="0" cy="90" r="16" fill="#1a0808"/></g>')
    return svg([kegel, '<rect x="0" y="840" width="1600" height="60" fill="#1f0a08"/>', boxen, gitarre]
               + sterne(r, 20, "#ffb199", 1.6, (.15, .4), .4))


def unterwasser(r):
    """6.7: Meeresgrund mit Seegras, Steinen, Muscheln und Fisch-Schatten (die Blasen steigen auf der Startseite)."""
    teile = ['<path d="M0 820 C 300 790 600 830 900 805 S 1400 790 1600 815 V900 H0Z" fill="#c9a96b" opacity=".35"/>']
    for x in list(range(30, 400, 55)) + list(range(1200, 1600, 60)):
        h = r.uniform(120, 300)
        teile.append(f'<path d="M{x} 900 C{x - 30} {900 - h * .4} {x + 30} {900 - h * .7} {x} {900 - h}" stroke="#2e8b57" '
                     f'stroke-width="{r.uniform(8, 14):.0f}" fill="none" stroke-linecap="round" opacity=".55"/>')
    for x, y in ((520, 850), (1050, 860), (760, 870)):
        teile.append(f'<ellipse cx="{x}" cy="{y}" rx="{r.uniform(30, 60):.0f}" ry="22" fill="#3b5560" opacity=".6"/>')
    for x, y, s in ((300, 260, 1), (1150, 180, .8), (900, 420, .6)):
        teile.append(f'<path d="M{x} {y} q{40 * s} {-25 * s} {80 * s} 0 q{-40 * s} {25 * s} {-80 * s} 0Z M{x + 80 * s} {y} '
                     f'l{20 * s} {-14 * s} v{28 * s}Z" fill="#0d3b5c" opacity=".45"/>')
    return svg(teile + [funkeln(1450, 120, 30, "#bff4ff", .25)])


def raumstation(r):
    """6.7: Planet mit Ring, Raumstation und viele Sterne."""
    station = ('<g transform="translate(1180 240)" opacity=".7"><rect x="-40" y="-18" width="80" height="36" rx="8" fill="#9aa7bd"/>'
               '<rect x="-150" y="-12" width="90" height="24" fill="#2f5aa8"/><rect x="60" y="-12" width="90" height="24" fill="#2f5aa8"/>'
               '<rect x="-60" y="-3" width="120" height="6" fill="#c9d3e3"/><circle cx="0" cy="0" r="8" fill="#ffd54f"/></g>')
    return svg(['<circle cx="260" cy="760" r="210" fill="#5b3fa8" opacity=".55"/>',
                '<ellipse cx="260" cy="760" rx="330" ry="60" fill="none" stroke="#c6a8ff" stroke-width="10" opacity=".35"/>',
                '<circle cx="1420" cy="760" r="70" fill="#2a8c8c" opacity=".45"/>', station]
               + sterne(r, 140, "#fff", 2.0, (.2, .7)))


MOTIVE = {"rock": rock, "unterwasser": unterwasser, "raumstation": raumstation,"blau": weltraum, "gruen": wald, "lila": zaubernacht, "rot": abendrot, "schwarz": schwarz,
          "hellblau": himmel, "mint": wiese, "rosa": zuckerwatte, "gelb": strand, "weiss": winter}


def main():
    os.makedirs(ZIEL, exist_ok=True)
    for name, f in MOTIVE.items():
        pfad = os.path.join(ZIEL, name + ".svg")
        with open(pfad, "w", encoding="utf-8") as d:
            d.write(f(random.Random(name)))
        print(f"  ✓ web/hintergrund/{name}.svg ({os.path.getsize(pfad) // 1024 + 1} KB)")


if __name__ == "__main__":
    main()
