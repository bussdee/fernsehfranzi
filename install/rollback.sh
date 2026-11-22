#!/bin/bash
# FernsehFranzi 3.0 - zurück auf den Stand vor install.sh. Läuft als root.
#
#   rollback.sh <sicherungsordner>      z. B. /var/backups/fernsehfranzi/v3-20261121-200000
#
# Stellt alle gesicherten Dateien wieder her, entfernt was es vorher nicht gab, stellt die Dienste
# (familyhub-* an, fernsehfranzi-* aus) wie vorher. Der Datenordner ~/fernsehfranzi-daten bleibt
# erhalten (Daten überleben, Grundsatz 14, docs/ENTWICKLUNG.md). Danach: Gerät neu starten.
set -euo pipefail

[ "$(id -u)" = 0 ] || { echo "rollback.sh muss als root laufen." >&2; exit 1; }
SICHERUNG="${1:?Aufruf: rollback.sh <sicherungsordner>}"
[ -f "$SICHERUNG/dienste.txt" ] || { echo "$SICHERUNG ist keine Sicherung von install.sh." >&2; exit 2; }

systemctl disable --now fernsehfranzi-eingabe.service fernsehfranzi-server.service 2>/dev/null || true

for datei in /etc/systemd/system/fernsehfranzi-server.service /etc/systemd/system/fernsehfranzi-eingabe.service \
             /etc/systemd/system/fernsehfranzi-retropie.service /etc/sudoers.d/fernsehfranzi \
             /usr/local/lib/fernsehfranzi/vt.sh /usr/local/lib/fernsehfranzi/richtlinie \
             /etc/systemd/system/fernsehfranzi-spiel.service /usr/local/lib/fernsehfranzi/spiel-start \
             /usr/local/lib/fernsehfranzi/bt-helfer /etc/systemd/system/fernsehfranzi-scraper.service \
             /etc/chromium/policies/managed/fernsehfranzi.json \
             /etc/chromium/policies/managed/fernsehfranzi-whitelist.json; do
  if [ -e "$SICHERUNG$datei" ]; then
    cp -a "$SICHERUNG$datei" "$datei"
  else
    rm -f "$datei"
  fi
done
# Dateien, die install.sh nur verändert hat: aus der Sicherung zurück
while IFS= read -r -d '' gesichert; do
  ziel="${gesichert#"$SICHERUNG"}"
  case "$ziel" in
    /etc/xdg/labwc/autostart|*/.config/labwc/autostart|*/es_input.cfg|*/es_settings.cfg|*/retroarch.cfg) cp -a "$gesichert" "$ziel" ;;
  esac
done < <(find "$SICHERUNG" -type f -print0)

# Dateien, die install.sh neu angelegt hat (seit 4.1 in neu.txt): wieder entfernen
if [ -f "$SICHERUNG/neu.txt" ]; then
  while IFS= read -r datei; do
    case "$datei" in
      /etc/udev/hwdb.d/90-fernsehfranzi-*|*/.config/labwc/rc.xml|*/.config/labwc/menu.xml|\
      /etc/NetworkManager/conf.d/90-fernsehfranzi-*|/usr/local/lib/fernsehfranzi/*) rm -f "$datei" ;;
    esac
  done < "$SICHERUNG/neu.txt"
fi
while IFS= read -r -d '' gesichert; do
  ziel="${gesichert#"$SICHERUNG"}"
  case "$ziel" in
    /etc/udev/hwdb.d/*|*/.config/labwc/rc.xml|*/.config/labwc/menu.xml|/etc/NetworkManager/conf.d/*|\
    */retroarch-core-options.cfg) cp -a "$gesichert" "$ziel" ;;
  esac
done < <(find "$SICHERUNG" -type f -print0)
systemd-hwdb update 2>/dev/null && udevadm trigger --subsystem-match=input --action=change 2>/dev/null || true
visudo -c > /dev/null
systemctl daemon-reload
while read -r dienst zustand; do
  case "$dienst:$zustand" in
    familyhub-*:enabled) systemctl enable --now "$dienst.service" ;;
  esac
done < "$SICHERUNG/dienste.txt"
echo "Zurückgerollt aus $SICHERUNG. Bitte das Gerät neu starten."
