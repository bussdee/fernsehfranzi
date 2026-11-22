"""Datenablage von FernsehFranzi 3.0.

Code und Daten sind getrennt (Grundsatz 14, docs/ENTWICKLUNG.md): Die Daten liegen in einem eigenen Ordner
(Vorgabe ``~/fernsehfranzi-daten``, änderbar über ``FERNSEHFRANZI_DATEN``) und überleben jedes Update.

- Jede Datei wird atomar geschrieben (temporäre Datei + ``os.replace``), ein Stromausfall
  hinterlässt also entweder den alten oder den neuen Stand, nie eine halbe Datei.
- ``einstellungen.json`` trägt eine Schema-Version. ``migriere`` bringt alte Stände
  schrittweise auf den aktuellen, ist wiederholbar (idempotent) und protokolliert jeden Schritt.
"""
import json
import logging
import os
import tempfile
from datetime import datetime

log = logging.getLogger("fernsehfranzi.daten")

SCHEMA_VERSION = 1


def datenordner():
    """Ordner für alle Daten. Wird bei Bedarf angelegt (nur für den Benutzer lesbar)."""
    ordner = os.environ.get("FERNSEHFRANZI_DATEN") or os.path.expanduser("~/fernsehfranzi-daten")
    os.makedirs(ordner, mode=0o700, exist_ok=True)
    return ordner


def schreibe_json(pfad, objekt):
    """Atomar schreiben: erst in eine temporäre Datei daneben, dann umbenennen."""
    ordner = os.path.dirname(os.path.abspath(pfad))
    os.makedirs(ordner, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=ordner)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as datei:
            json.dump(objekt, datei, ensure_ascii=False, indent=2, sort_keys=True)
            datei.write("\n")
            datei.flush()
            os.fsync(datei.fileno())
        os.replace(tmp, pfad)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def lies_json(pfad, vorgabe=None):
    """JSON lesen. Fehlt die Datei, kommt ``vorgabe``.

    Eine kaputte Datei wird nicht überschrieben, sondern mit Zeitstempel beiseitegelegt
    und geloggt (Regel 15: nichts still verschlucken). Danach gilt die Vorgabe.
    """
    try:
        with open(pfad, encoding="utf-8") as datei:
            return json.load(datei)
    except FileNotFoundError:
        return vorgabe
    except (ValueError, UnicodeDecodeError) as fehler:
        kaputt = "%s.kaputt-%s" % (pfad, datetime.now().strftime("%Y%m%d-%H%M%S"))
        os.replace(pfad, kaputt)
        log.error("%s war nicht lesbar (%s) und liegt jetzt unter %s.", pfad, fehler, kaputt)
        return vorgabe


# ---------------------------------------------------------------- Migration
def _von_0_auf_1(daten):
    """Schema 0 = Einstellungen ohne Versionsfeld (Vorstufe). Fehlende Bereiche anlegen."""
    daten.setdefault("zeit", {})
    daten.setdefault("whitelist", {"zusatz": [], "browser_sperre": True})
    return daten


SCHRITTE = {0: _von_0_auf_1}


def migriere(daten, protokoll=None):
    """Einstellungen auf ``SCHEMA_VERSION`` bringen. Rückgabe (daten, geändert).

    Ein Stand aus einer *neueren* Version wird nicht angefasst (ValueError), damit ein
    Zurückrollen des Codes keine Daten verdirbt.
    """
    protokoll = protokoll if protokoll is not None else []
    if not isinstance(daten, dict):
        raise ValueError("Einstellungen müssen ein JSON-Objekt sein.")
    version = daten.get("schema", 0)
    if not isinstance(version, int) or version < 0:
        raise ValueError("Ungültige Schema-Version: %r" % (version,))
    if version > SCHEMA_VERSION:
        raise ValueError("Einstellungen stammen von einer neueren Version (Schema %d > %d)."
                         % (version, SCHEMA_VERSION))
    geaendert = False
    while version < SCHEMA_VERSION:
        daten = SCHRITTE[version](daten)
        version += 1
        daten["schema"] = version
        eintrag = "Schema %d -> %d" % (version - 1, version)
        protokoll.append(eintrag)
        log.info("Migration der Einstellungen: %s", eintrag)
        geaendert = True
    return daten, geaendert


def lade_einstellungen(ordner=None):
    """Einstellungen laden, migrieren und bei Änderung (mit Sicherung) zurückschreiben."""
    ordner = ordner or datenordner()
    pfad = os.path.join(ordner, "einstellungen.json")
    daten = lies_json(pfad, vorgabe={"schema": SCHEMA_VERSION, "zeit": {},
                                     "whitelist": {"zusatz": [], "browser_sperre": True}})
    protokoll = []
    daten, geaendert = migriere(daten, protokoll)
    if geaendert:
        if os.path.exists(pfad):
            with open(pfad, encoding="utf-8") as alt:
                sicherung = pfad + ".vor-schema-%d" % SCHEMA_VERSION
                if not os.path.exists(sicherung):
                    with open(sicherung, "w", encoding="utf-8") as datei:
                        datei.write(alt.read())
        schreibe_json(pfad, daten)
        with open(os.path.join(ordner, "migration.log"), "a", encoding="utf-8") as datei:
            for eintrag in protokoll:
                datei.write("%s %s\n" % (datetime.now().isoformat(timespec="seconds"), eintrag))
    elif not os.path.exists(pfad):
        schreibe_json(pfad, daten)
    return daten
