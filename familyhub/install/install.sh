#!/bin/bash
# FernsehFranzi v2.4 - Installation (Raspberry Pi OS, labwc/Wayland oder X11, RetroPie)
#
# Voraussetzung: Paket liegt in /home/family/familyhub (hier entpackt).
# Das Skript ist wiederholbar (idempotent) und sichert, was es aendert.
set -euo pipefail

HUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "FamilyHub-Verzeichnis: $HUB_DIR"

if [ "$HUB_DIR" != "/home/family/familyhub" ]; then
  echo ""
  echo "ACHTUNG: Das Verzeichnis ist $HUB_DIR"
  echo "Die Units erwarten /home/family/familyhub. Bei anderem Benutzer/Ort"
  echo "zuerst die Pfade in install/*.service anpassen."
  read -r -p "Trotzdem fortfahren? [j/N] " antwort
  case "$antwort" in j|J|y|Y) ;; *) exit 1 ;; esac
fi

echo "1/6 Abhaengigkeiten (python3-evdev, cec-utils) ..."
for paket in python3-evdev cec-utils; do
  dpkg -s "$paket" > /dev/null 2>&1 || sudo apt-get install -y "$paket"
done

echo "2/6 uinput-Modul dauerhaft laden ..."
if ! grep -qs "^uinput$" /etc/modules-load.d/*.conf 2>/dev/null; then
  echo uinput | sudo tee /etc/modules-load.d/familyhub-uinput.conf > /dev/null
fi
sudo modprobe uinput 2>/dev/null || true

echo "3/6 alte Dienste abloesen, neue Units installieren ..."
# WICHTIG: logs/ als Benutzer anlegen, bevor die root-Dienste starten - sonst
# legt cec_keys.py (root) den Ordner an und server.py (family) kann nicht loggen.
mkdir -p "$HUB_DIR/logs"
# Alte Prozesse der Vorversion (laufen bis zum Neustart weiter und blockieren
# Port 8765 bzw. den CEC-Adapter):
sudo pkill -f games_launcher.py 2>/dev/null || true
sudo pkill -f cec_keys.py 2>/dev/null || true
sudo pkill -x cec-client 2>/dev/null || true
pkill -f "familyhub/familyhub.py" 2>/dev/null || true
# Eigene Zwischenloesung vom Entwicklungstag (falls vorhanden) - sonst liefen
# zwei CEC-Clients gleichzeitig und blockieren sich.
for alt in cec-keys.service retropie-launch.service; do
  sudo systemctl disable --now "$alt" 2>/dev/null || true
done
sudo cp "$HUB_DIR/install/familyhub-server.service" /etc/systemd/system/
sudo cp "$HUB_DIR/install/familyhub-cec.service" /etc/systemd/system/
sudo systemctl daemon-reload

echo "4/6 Dienste aktivieren ..."
sudo systemctl enable familyhub-server.service familyhub-cec.service
sudo systemctl restart familyhub-server.service familyhub-cec.service

echo "5/6 Kiosk-Autostart einrichten ..."
chmod +x "$HUB_DIR/kiosk.sh" "$HUB_DIR/install/labwc_autostart.py" "$HUB_DIR"/tests/*.sh 2>/dev/null || true
if [ -d "$HOME/.config/labwc" ] || pgrep -x labwc > /dev/null 2>&1; then
  echo "   labwc-Sitzung erkannt."
  python3 "$HUB_DIR/install/labwc_autostart.py" \
    "$HOME/.config/labwc/autostart" "$HUB_DIR/kiosk.sh"
  # Doppelstart vermeiden: kein zweiter Eintrag ueber ~/.config/autostart
  rm -f "$HOME/.config/autostart/familyhub-kiosk.desktop"
else
  echo "   X11/lxsession-Sitzung: XDG-Autostart-Eintrag."
  mkdir -p "$HOME/.config/autostart"
  cp "$HUB_DIR/install/familyhub-kiosk.desktop" "$HOME/.config/autostart/"
fi

echo "6/6 Zusammenfassung ..."
echo ""
echo "Fertig. Wichtig:"
echo " - Ton: ROT = HDMI, GRUEN = Klinke (Fernbedienung). Die Wahl bleibt gespeichert."
echo " - Alte Autostart-Zeilen wurden NICHT geloescht, nur auskommentiert;"
echo "   Sicherung: ~/.config/labwc/autostart.vor-familyhub"
echo " - Weitere alte Starter in ~/.config/autostart bitte selbst pruefen:"
ls "$HOME/.config/autostart" 2>/dev/null | sed 's/^/     /' || true
echo ""
echo "Vor dem Neustart pruefen:   bash $HUB_DIR/tests/pi_check.sh"
echo "Dann:                       sudo reboot"
