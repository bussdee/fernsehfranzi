#!/bin/bash
# FernsehFranzi - Systemteil von 2.5 zuruecknehmen. Laeuft als root auf dem Geraet.
#   rollback-system.sh <sicherungsordner aus system.sh>
# Entfernt Unit, Helfer und sudo-Regel und stellt es_input.cfg aus der Sicherung her.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "rollback-system.sh muss als root laufen." >&2; exit 1; }
SICHERUNG="${1:-}"

systemctl stop fernsehfranzi-retropie.service 2>/dev/null || true
rm -f /etc/systemd/system/fernsehfranzi-retropie.service /etc/sudoers.d/fernsehfranzi \
      /usr/local/lib/fernsehfranzi/vt.sh /etc/systemd/system/fernsehfranzi-retropie.service.d/weg-b.conf
rmdir /etc/systemd/system/fernsehfranzi-retropie.service.d 2>/dev/null || true
rmdir /usr/local/lib/fernsehfranzi 2>/dev/null || true
systemctl daemon-reload
visudo -c > /dev/null

if [ -n "$SICHERUNG" ] && [ -f "$SICHERUNG/es_input.cfg" ]; then
  cp -a "$SICHERUNG/es_input.cfg" /opt/retropie/configs/all/emulationstation/es_input.cfg
  echo "es_input.cfg aus $SICHERUNG wiederhergestellt."
fi
echo "Systemteil 2.5 entfernt."
