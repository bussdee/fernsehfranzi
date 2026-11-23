"""Start: ``python3 -m fernsehfranzi`` (systemd-Unit fernsehfranzi-server.service, Kiosk-Benutzer)."""
import logging
import os
import threading
import time

from . import daten, kern, klaenge, system, web

CODE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def lies_version():
    try:
        with open(os.path.join(CODE, "VERSION")) as datei:
            return datei.read().strip()
    except OSError:
        return "unbekannt"


def main():
    ordner = daten.datenordner()
    os.makedirs(os.path.join(ordner, "logs"), exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s",
                        handlers=[logging.FileHandler(os.path.join(ordner, "logs", "server.log")),
                                  logging.StreamHandler()])
    log = logging.getLogger("fernsehfranzi")
    hub = kern.Hub(ordner, system.System(), version=lies_version())
    web_ordner = os.path.join(CODE, "web")
    zeichnungen = os.path.join(ordner, "zeichnungen")
    kiosk = web.baue_server(web.KioskHandler, hub, web_ordner, zeichnungen, ("127.0.0.1", 8765))
    log.info("FernsehFranzi %s - Startseite auf http://127.0.0.1:8765/", hub.version)

    lan_zustand = {"server": None, "port": None}

    def lan_abgleichen():
        """Eltern-Seite im Heimnetz an/aus, sobald es im Elternbereich geändert wird (nur mit PIN)."""
        lan = hub.einstellungen.get("eltern_lan") or {}
        soll = lan.get("port") if lan.get("aktiv") and hub.pin_gesetzt() else None
        if soll == lan_zustand["port"]:
            return
        if lan_zustand["server"] is not None:
            lan_zustand["server"].shutdown()
            lan_zustand["server"].server_close()
            log.info("Eltern-Seite im Heimnetz beendet.")
            lan_zustand.update(server=None, port=None)
        if soll:
            try:
                eltern = web.baue_server(web.LanHandler, hub, web_ordner, zeichnungen, ("0.0.0.0", soll))
            except OSError as fehler:
                log.error("Eltern-Seite nicht startbar (Port %s): %s", soll, fehler)
                return
            threading.Thread(target=eltern.serve_forever, daemon=True).start()
            lan_zustand.update(server=eltern, port=soll)
            log.info("Eltern-Seite im Heimnetz auf Port %s", soll)

    raum_zustand = {"server": None, "port": None}

    def raum_abgleichen():
        """4.3: Server für die Handys nur, solange am Fernseher ein Spielraum offen ist (und Handy-Spiele erlaubt sind)."""
        hs = hub.handyspiele()
        soll = hs["port"] if hs["aktiv"] and hub.raum is not None else None
        if soll == raum_zustand["port"]:
            return
        if raum_zustand["server"] is not None:
            raum_zustand["server"].shutdown()
            raum_zustand["server"].server_close()
            log.info("Spielraum im Heimnetz beendet.")
            raum_zustand.update(server=None, port=None)
        if soll:
            try:
                server = web.baue_server(web.RaumHandler, hub, web_ordner, zeichnungen, ("0.0.0.0", soll))
            except OSError as fehler:
                log.error("Spielraum nicht startbar (Port %s): %s", soll, fehler)
                return
            threading.Thread(target=server.serve_forever, daemon=True).start()
            raum_zustand.update(server=server, port=soll)
            log.info("Spielraum im Heimnetz auf Port %s", soll)

    def raum_wache():
        while True:
            time.sleep(1)
            try:
                raum_abgleichen()
            except Exception:   # noqa: BLE001
                log.exception("Spielraum-Server")

    ziel = hub.ton["ziel"]          # gespeicherte Wahl, sonst HDMI
    if ziel:
        def ton_wiederherstellen():
            for _ in range(30):
                if hub.system.ton_setzen(ziel)[0]:
                    return
                time.sleep(2)
            log.warning("Ton: letzte Wahl (%s) nicht setzbar.", ziel)
        threading.Thread(target=ton_wiederherstellen, daemon=True).start()

    def takt():
        while True:
            time.sleep(kern.TICK_S)
            try:
                hub.tick()
                lan_abgleichen()
            except Exception:   # noqa: BLE001
                log.exception("Fehler im Zeitkonto-Takt")
    lan_abgleichen()
    threading.Thread(target=hub.richtlinie_aktualisieren, daemon=True).start()
    threading.Thread(target=klaenge.alle_vorbereiten, daemon=True, name="klaenge").start()   # 5.2: Klang-Archiv vorrechnen
    threading.Thread(target=takt, daemon=True).start()
    threading.Thread(target=raum_wache, daemon=True).start()
    try:
        kiosk.serve_forever()
    finally:
        hub.speichere_konto()


if __name__ == "__main__":
    main()
