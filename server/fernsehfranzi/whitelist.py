"""Whitelist für Fritzbox und Pi-hole.

Eine Liste, eine Quelle: Domains aus dem App-Katalog + von den Eltern ergänzte Domains +
Systemdomains. Welche Domains Plex & Co. wirklich brauchen, lässt sich per DNS-Mitschnitt
am Gerät ermitteln - hier stehen deshalb keine geratenen Einträge.
"""
from .katalog import DOMAIN, pruefe_katalog

# Systemdomains: nur Zeit (der Pi 3 hat keine Echtzeituhr). Paketquellen nur im Wartungsfall.
# Debian-Vorgabe von systemd-timesyncd - bei Bedarf am Gerät gegen einen DNS-Mitschnitt prüfen.
SYSTEM = ["*.debian.pool.ntp.org"]


def sammle(katalog, zusatz=(), system=True):
    """Sortierte, doppelfreie Domainliste. Ungültige Zusatz-Einträge -> ValueError."""
    domains = set(SYSTEM) if system else set()
    for app in pruefe_katalog(katalog):
        if app.get("aktiv", True):
            domains.update(d.lower() for d in app.get("domains", []))
    for eintrag in zusatz:
        domain = str(eintrag).strip().lower()
        if not DOMAIN.match(domain):
            raise ValueError("Ungültige Domain: %r" % eintrag)
        domains.add(domain)
    return sorted(domains, key=lambda d: (d.lstrip("*.").split(".")[::-1], d))


def export_pihole(domains):
    """Pi-hole: exakte Domains als Liste, Platzhalter als Regex-Zeile (Allow-Regex)."""
    zeilen = ["# FernsehFranzi - erlaubte Domains für Pi-hole"]
    for domain in domains:
        if domain.startswith("*."):
            basis = domain[2:].replace(".", r"\.")
            zeilen.append(r"(\.|^)%s$" % basis)
        else:
            zeilen.append(domain)
    return "\n".join(zeilen) + "\n"


def export_fritzbox(domains):
    """Fritzbox-Kindersicherung („erlaubte Internetseiten“): eine Domain pro Zeile, ohne Platzhalter.
    Ein Platzhalter wird als Basisdomain eingetragen. Ob die Fritzbox Unterdomains damit
    mitfreigibt, muss an der echten Box geprüft werden."""
    gesehen = []
    for domain in domains:
        domain = domain[2:] if domain.startswith("*.") else domain
        if domain not in gesehen:
            gesehen.append(domain)
    return "\n".join(gesehen) + "\n"
