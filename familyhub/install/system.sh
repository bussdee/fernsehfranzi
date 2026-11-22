#!/bin/bash
# FernsehFranzi - Systemteil einrichten (seit 2.5). Laeuft als root auf dem Geraet,
# aufgerufen von `make deploy` nach dem Uebertragen. Wiederholbar (idempotent).
#
# Richtet ein: RetroPie-Unit (tty8), Konsolen-Helfer, enge sudo-Regel,
# Tastatur-Belegung fuer die Fernbedienung in EmulationStation.
# Vorher wird gesichert, was ersetzt wird: /var/backups/fernsehfranzi/<zeit>/
# Zurueck: install/rollback-system.sh <sicherungsordner>
#
#   system.sh [A|B]   A = Konsolenwechsel, Desktop laeuft weiter (Vorgabe)
#                     B = Desktop fuer das Spielen beenden (Rueckfallweg, Drop-in weg-b.conf)
set -euo pipefail

HUB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ "$(id -u)" = 0 ] || { echo "system.sh muss als root laufen." >&2; exit 1; }
BENUTZER="$(stat -c %U "$HUB")"
ES_INPUT=/opt/retropie/configs/all/emulationstation/es_input.cfg
DROPIN_DIR=/etc/systemd/system/fernsehfranzi-retropie.service.d
WEG="${1:-A}"
case "$WEG" in A|B) ;; *) echo "Weg muss A oder B sein, nicht '$WEG'." >&2; exit 2 ;; esac

SICHERUNG="/var/backups/fernsehfranzi/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$SICHERUNG"
for datei in /etc/systemd/system/fernsehfranzi-retropie.service /etc/sudoers.d/fernsehfranzi \
             /usr/local/lib/fernsehfranzi/vt.sh "$ES_INPUT" "$DROPIN_DIR/weg-b.conf"; do
  if [ -e "$datei" ]; then cp -a "$datei" "$SICHERUNG/"; fi
done
echo "Sicherung: $SICHERUNG"

echo "1/4 sudo-Regel pruefen und einrichten ..."
visudo -c -f "$HUB/install/sudoers.d/fernsehfranzi"
install -m 0440 -o root -g root "$HUB/install/sudoers.d/fernsehfranzi" /etc/sudoers.d/fernsehfranzi
visudo -c > /dev/null

echo "2/4 Konsolen-Helfer und RetroPie-Unit ..."
install -d -m 0755 /usr/local/lib/fernsehfranzi
install -m 0755 -o root -g root "$HUB/install/fernsehfranzi-vt.sh" /usr/local/lib/fernsehfranzi/vt.sh
install -m 0644 -o root -g root "$HUB/install/fernsehfranzi-retropie.service" /etc/systemd/system/fernsehfranzi-retropie.service
if [ "$WEG" = B ]; then
  echo "   Weg B: Desktop wird fuer das Spielen beendet (Drop-in weg-b.conf)."
  install -D -m 0644 -o root -g root "$HUB/install/fernsehfranzi-retropie-weg-b.conf" "$DROPIN_DIR/weg-b.conf"
else
  echo "   Weg A: Konsolenwechsel, Desktop laeuft weiter."
  if [ -e "$DROPIN_DIR/weg-b.conf" ]; then
    rm -f -- "$DROPIN_DIR/weg-b.conf"
    rmdir --ignore-fail-on-non-empty "$DROPIN_DIR"
  fi
fi
systemctl daemon-reload
if ! systemd-analyze verify /etc/systemd/system/fernsehfranzi-retropie.service; then
  echo "   Warnung: systemd-analyze verify meldet etwas (siehe oben) - die Unit ist trotzdem installiert." >&2
fi

echo "3/4 EmulationStation: Fernbedienung als Tastatur ..."
if [ -f "$ES_INPUT" ]; then
  runuser -u "$BENUTZER" -- python3 "$HUB/install/es_tastatur.py" "$ES_INPUT"
else
  echo "   $ES_INPUT fehlt - uebersprungen (ES fragt beim ersten Start nach der Belegung)."
fi

echo "4/4 Fertig (Weg $WEG). Sicherung: $SICHERUNG"
