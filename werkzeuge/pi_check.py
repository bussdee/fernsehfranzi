#!/usr/bin/env python3
"""Vorher-/Nachher-Prüfung des Fernseh-Pi. Ändert auf dem Gerät nichts.

    python3 werkzeuge/pi_check.py vor  --host BENUTZER@GERAET --pfad ~/familyhub
    python3 werkzeuge/pi_check.py nach --host BENUTZER@GERAET --pfad ~/familyhub [--version 2.4.0]

`vor` liest den Zustand (Dienste, Ports, Speicher, Version, Server-Antwort) per ssh,
prüft die Voraussetzungen und speichert einen Schnappschuss unter `.local/pi-check/`.
`nach` liest erneut und vergleicht mit dem letzten Schnappschuss.
Rückgabewert 1 bei einem einzigen roten Punkt: Stoppsignal, kein Vorschlag.

Nur Standardbibliothek. Auf dem Gerät läuft ausschließlich ein lesendes Python-Skript.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHNAPPSCHUSS_DIR = os.path.join(REPO, ".local", "pi-check")
LETZTER_VOR = os.path.join(SCHNAPPSCHUSS_DIR, "letzter-vor.json")

# Dienste, deren Zustand vorher und nachher verglichen wird.
DIENSTE = [
    "familyhub-server.service",
    "familyhub-cec.service",
    "fernsehfranzi-server.service",
    "fernsehfranzi-eingabe.service",
    "fernsehfranzi-retropie.service",
    "lightdm.service",
    "ssh.service",
]
MIN_SPEICHER_MIB = 150
MIN_PLATTE_MIB = 1024

# Läuft auf dem Gerät (python3 -), nur lesend. Gibt eine JSON-Zeile aus.
FERNSKRIPT = r'''
import json, os, subprocess, sys
pfad = os.path.expanduser(sys.argv[1])
dienste = sys.argv[2:]

def lauf(*befehl):
    try:
        r = subprocess.run(befehl, capture_output=True, text=True, timeout=10)
        return r.returncode, r.stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as fehler:
        return 127, str(fehler)

def lies(datei):
    try:
        with open(datei) as f:
            return f.read().strip()
    except OSError:
        return None

z = {}
z["boot_id"] = lies("/proc/sys/kernel/random/boot_id")
z["uptime_s"] = float((lies("/proc/uptime") or "0").split()[0])
z["dienste"] = {d: lauf("systemctl", "is-active", d)[1] or "unbekannt" for d in dienste}
rc, aus = lauf("systemctl", "--failed", "--plain", "--no-legend", "--no-pager")
z["fehlgeschlagen"] = sorted(l.split()[0] for l in aus.splitlines() if l.strip()) if rc == 0 else []
rc, aus = lauf("ss", "-ltnH")
ports = set()
for zeile in aus.splitlines():
    teile = zeile.split()
    if len(teile) >= 4:
        ports.add(teile[3])
z["ports"] = sorted(ports)
mem = {}
for zeile in (lies("/proc/meminfo") or "").splitlines():
    name, _, wert = zeile.partition(":")
    mem[name] = int(wert.split()[0]) if wert.split() else 0
z["speicher_verfuegbar_mib"] = mem.get("MemAvailable", 0) // 1024
st = os.statvfs("/")
z["platte_frei_mib"] = st.f_bavail * st.f_frsize // (1024 * 1024)
z["version"] = lies(os.path.join(pfad, "VERSION"))
z["hub_ordner"] = os.path.isdir(pfad)
rc, aus = lauf("curl", "-sf", "--max-time", "3", "http://127.0.0.1:8765/api/status")   # 3.0
if rc != 0:
    rc, aus = lauf("curl", "-sf", "--max-time", "3", "http://127.0.0.1:8765/status")   # 2.x
z["server_status"] = aus if rc == 0 else None
z["cec_client_anzahl"] = len(lauf("pgrep", "-x", "cec-client")[1].split())
z["chromium_laeuft"] = lauf("pgrep", "-x", "chromium")[0] == 0
# 4.1: Kiosk-Tastenkürzel, Sondertasten, Bluetooth-Helfer, WLAN-Energiesparen
iw = next((b for b in ("/usr/sbin/iw", "/sbin/iw") if os.path.exists(b)), "iw")
z["stand_41"] = {"labwc_kiosk": os.path.isfile(os.path.expanduser("~/.config/labwc/rc.xml")),
                 "tasten_hwdb": os.path.isfile("/etc/udev/hwdb.d/90-fernsehfranzi-tastatur.hwdb"),
                 "bt_helfer": os.path.isfile("/usr/local/lib/fernsehfranzi/bt-helfer"),
                 "wlan_sparen": lauf(iw, "dev", "wlan0", "get", "power_save")[1].strip()}
print(json.dumps(z))
'''


def erhebe(host, pfad):
    """Liest den Zustand des Geräts. Wirft RuntimeError, wenn ssh scheitert."""
    befehl = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host,
              "python3", "-", pfad] + DIENSTE
    try:
        r = subprocess.run(befehl, input=FERNSKRIPT, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise RuntimeError("ssh antwortet nicht (60 s)")
    if r.returncode != 0:
        raise RuntimeError("ssh/Erhebung fehlgeschlagen (Code %d): %s" % (r.returncode, r.stderr.strip()))
    zeilen = [z for z in r.stdout.splitlines() if z.startswith("{")]
    if not zeilen:
        raise RuntimeError("keine Antwort vom Gerät: %r" % r.stdout[:200])
    zustand = json.loads(zeilen[-1])
    zustand["host"] = host
    zustand["pfad"] = pfad
    zustand["zeit"] = datetime.now().isoformat(timespec="seconds")
    return zustand


def pruefe_vor(z):
    """Liste von (stufe, text); stufe ist 'ok', 'warn' oder 'rot'."""
    p = []
    m = z["speicher_verfuegbar_mib"]
    p.append(("ok" if m >= MIN_SPEICHER_MIB else "rot",
              "Arbeitsspeicher verfügbar: %d MiB (mind. %d)" % (m, MIN_SPEICHER_MIB)))
    d = z["platte_frei_mib"]
    p.append(("ok" if d >= MIN_PLATTE_MIB else "rot",
              "Platte frei: %d MiB (mind. %d)" % (d, MIN_PLATTE_MIB)))
    p.append(("ok" if z["hub_ordner"] else "warn",
              "Hub-Ordner %s %s" % (z["pfad"], "vorhanden" if z["hub_ordner"] else "fehlt (Erstinstallation?)")))
    p.append(("ok", "Version auf dem Gerät: %s" % (z["version"] or "keine VERSION-Datei")))
    if z["fehlgeschlagen"]:
        p.append(("warn", "Schon vorher fehlgeschlagene Units: " + ", ".join(z["fehlgeschlagen"])))
    else:
        p.append(("ok", "Keine fehlgeschlagenen Units"))
    for dienst, stand in sorted(z["dienste"].items()):
        p.append(("ok", "%s: %s" % (dienst, stand)))
    p.append(("ok" if z["cec_client_anzahl"] <= 1 else "rot",
              "cec-client läuft %d-mal (höchstens 1)" % z["cec_client_anzahl"]))
    return p


def pruefe_nach(vor, nach, erwartete_version=None, neustart_erlaubt=False, neue_ports=(), abgeloest=()):
    """Vergleicht zwei Zustände. erwartete_version None = nicht prüfen."""
    p = []
    if vor["host"] != nach["host"]:
        p.append(("rot", "Schnappschuss gehört zu %s, nicht zu %s" % (vor["host"], nach["host"])))
    neu_gestartet = vor["boot_id"] != nach["boot_id"]
    if neu_gestartet:
        p.append(("ok" if neustart_erlaubt else "rot",
                  "Gerät wurde neu gestartet" + ("" if neustart_erlaubt else " (nicht angekündigt)")))
    else:
        p.append(("ok", "Kein Neustart des Geräts"))
    for dienst, stand_vor in sorted(vor["dienste"].items()):
        stand_nach = nach["dienste"].get(dienst, "unbekannt")
        if stand_vor == "active" and stand_nach != "active" and dienst in abgeloest:
            p.append(("ok", "%s abgelöst (jetzt %s)" % (dienst, stand_nach)))
        elif stand_vor == "active" and stand_nach != "active":
            p.append(("rot", "%s war aktiv, ist jetzt %s" % (dienst, stand_nach)))
        elif stand_vor != stand_nach:
            p.append(("warn", "%s: %s → %s" % (dienst, stand_vor, stand_nach)))
        else:
            p.append(("ok", "%s: %s" % (dienst, stand_nach)))
    neu_fehl = sorted(set(nach["fehlgeschlagen"]) - set(vor["fehlgeschlagen"]))
    if neu_fehl:
        p.append(("rot", "Neu fehlgeschlagene Units: " + ", ".join(neu_fehl)))
    else:
        p.append(("ok", "Keine neu fehlgeschlagenen Units"))
    ports_vor, ports_nach = set(vor["ports"]), set(nach["ports"])
    for port in sorted(ports_nach - ports_vor):
        p.append(("ok" if port in neue_ports else "rot", "Neuer lauschender Port: %s" % port))
    for port in sorted(ports_vor - ports_nach):
        p.append(("rot", "Port lauscht nicht mehr: %s" % port))
    if ports_vor == ports_nach:
        p.append(("ok", "Lauschende Ports unverändert (%d)" % len(ports_nach)))
    status = nach["server_status"]
    try:
        antwort = json.loads(status) if status else None
    except ValueError:
        antwort = None
    if isinstance(antwort, dict) and "running" in antwort:
        p.append(("ok", "Server 127.0.0.1:8765 antwortet: %s" % status))
    elif vor["server_status"]:
        p.append(("rot", "Server 127.0.0.1:8765 antwortet nicht mehr (vorher: %s)" % vor["server_status"]))
    else:
        p.append(("warn", "Server 127.0.0.1:8765 antwortet nicht (vorher auch nicht)"))
    p.append(("ok" if nach["cec_client_anzahl"] <= 1 else "rot",
              "cec-client läuft %d-mal (höchstens 1)" % nach["cec_client_anzahl"]))
    if vor["chromium_laeuft"] and not nach["chromium_laeuft"]:
        p.append(("warn", "Chromium lief vorher, jetzt nicht (direkt nach dem Neustart normal – in 1–2 min noch einmal prüfen)"))
    s41 = nach.get("stand_41")
    if s41 and str(nach.get("version") or "") >= "4.1":
        for schluessel, text in (("labwc_kiosk", "Kiosk ohne Tastenkürzel (labwc)"), ("tasten_hwdb", "Sondertasten der Tastatur umgelegt"),
                                 ("bt_helfer", "Bluetooth-Helfer installiert")):
            p.append(("ok" if s41.get(schluessel) else "warn", text + ("" if s41.get(schluessel) else " – fehlt")))
        sparen = s41.get("wlan_sparen", "")
        p.append(("ok" if "off" in sparen else "warn", "WLAN-Energiesparen: %s" % (sparen or "nicht lesbar (Kabel?)")))
    if erwartete_version is not None:
        p.append(("ok" if nach["version"] == erwartete_version else "rot",
                  "Version auf dem Gerät: %s (erwartet %s)" % (nach["version"], erwartete_version)))
    m = nach["speicher_verfuegbar_mib"]
    p.append(("ok" if m >= MIN_SPEICHER_MIB else "rot", "Arbeitsspeicher verfügbar: %d MiB" % m))
    return p


ZEICHEN = {"ok": "✓", "warn": "⚠", "rot": "✗"}


def berichte(titel, punkte):
    print(titel)
    for stufe, text in punkte:
        print("  %s %s" % (ZEICHEN[stufe], text))
    rot = sum(1 for s, _ in punkte if s == "rot")
    warn = sum(1 for s, _ in punkte if s == "warn")
    print("Ergebnis: %s (%d rot, %d Hinweise)" % ("ROT – nicht weitermachen" if rot else "grün", rot, warn))
    return 1 if rot else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("modus", choices=["vor", "nach"])
    ap.add_argument("--host", required=True, help="BENUTZER@GERAET (aus config/pi.mk)")
    ap.add_argument("--pfad", required=True, help="Hub-Ordner auf dem Gerät")
    ap.add_argument("--version", default=None, help="nach: erwartete Version (sonst nicht geprüft)")
    ap.add_argument("--neustart-erlaubt", action="store_true", help="nach: Neustart war angekündigt")
    ap.add_argument("--neuer-port", action="append", default=[], help="nach: angemeldeter neuer Port, z. B. 127.0.0.1:8765")
    ap.add_argument("--abgeloest", action="append", default=[], help="nach: Dienst darf aus sein (Umstellung)")
    a = ap.parse_args(argv)
    try:
        zustand = erhebe(a.host, a.pfad)
    except RuntimeError as fehler:
        print("✗ %s" % fehler)
        return 1
    os.makedirs(SCHNAPPSCHUSS_DIR, exist_ok=True)
    if a.modus == "vor":
        datei = os.path.join(SCHNAPPSCHUSS_DIR, "vor-%s.json" % zustand["zeit"].replace(":", ""))
        for ziel in (datei, LETZTER_VOR):
            with open(ziel, "w") as f:
                json.dump(zustand, f, indent=1, ensure_ascii=False)
        code = berichte("pi-check vor · %s · %s" % (a.host, zustand["zeit"]), pruefe_vor(zustand))
        print("Schnappschuss: %s" % os.path.relpath(datei, REPO))
        return code
    if not os.path.exists(LETZTER_VOR):
        print("✗ Kein Schnappschuss von 'vor' vorhanden – zuerst: make pi-check-vor")
        return 1
    with open(LETZTER_VOR) as f:
        vor = json.load(f)
    with open(os.path.join(SCHNAPPSCHUSS_DIR, "nach-%s.json" % zustand["zeit"].replace(":", "")), "w") as f:
        json.dump(zustand, f, indent=1, ensure_ascii=False)
    return berichte("pi-check nach · %s · %s (vor: %s)" % (a.host, zustand["zeit"], vor["zeit"]),
                    pruefe_nach(vor, zustand, a.version, a.neustart_erlaubt, set(a.neuer_port),
                                set(a.abgeloest)))


if __name__ == "__main__":
    sys.exit(main())
