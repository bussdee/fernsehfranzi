#!/bin/bash
# FernsehFranzi - Probelauf RetroPie auf tty8. Laeuft als root auf dem Geraet.
# Startet EmulationStation genau so wie die spaetere Unit, aber als voruebergehende
# Unit (systemd-run): Es wird keine Datei auf dem Geraet geschrieben.
# Danach ein Spiel starten, spielen, beenden, ES beenden (Start > Quit oder EXIT).
# Die Rueckkehr zur Startseite steckt in der Unit selbst (ExecStopPost) - sie klappt
# auch dann, wenn die ssh-Verbindung abreisst.
#   Aufruf vom Rechner: make pi-probe [RETROPIE_WEG=B]
#   Auf dem Geraet:     retropie_probe.sh <benutzer> [A|B]
#   Weg B beendet fuer den Probelauf den Desktop und startet ihn danach neu.
set -u
[ "$(id -u)" = 0 ] || { echo "Probelauf muss als root laufen." >&2; exit 1; }
BENUTZER="${1:-family}"
WEG="${2:-A}"
UNIT=fernsehfranzi-probe
vorher="$(cat /sys/class/tty/tty0/active)"; vorher="${vorher#tty}"

zurueck() {
  systemctl stop "$UNIT" 2>/dev/null
  chvt "$vorher"
  if [ "$WEG" = B ]; then systemctl start --no-block lightdm.service; fi
}
trap 'zurueck; exit 130' INT TERM HUP

WEG_B=()
if [ "$WEG" = B ]; then
  WEG_B=(-p Conflicts=lightdm.service -p After=lightdm.service
         -p "ExecStopPost=+/usr/bin/systemctl start --no-block lightdm.service")
fi

echo "Probelauf Weg $WEG: EmulationStation auf tty8 (Desktop ist auf tty$vorher). Abbruch: Strg+C."
chvt 8
systemd-run --unit="$UNIT" --wait --collect --uid="$BENUTZER" \
  -p PAMName=login -p TTYPath=/dev/tty8 \
  -p StandardInput=tty-force -p StandardOutput=tty -p StandardError=journal \
  -p TTYReset=yes -p TTYVHangup=yes -p TTYVTDisallocate=yes -p RuntimeMaxSec=1800 \
  -p "WorkingDirectory=~" -E TERM=linux \
  -p "ExecStopPost=+/bin/chvt $vorher" "${WEG_B[@]}" \
  -p "UnsetEnvironment=DISPLAY WAYLAND_DISPLAY SDL_VIDEODRIVER" \
  /usr/bin/emulationstation
code=$?
chvt "$vorher"
echo ""
echo "Probelauf beendet (Code $code). Zurueck auf tty$vorher."
echo "--- Journal (letzte 15 Zeilen):"
journalctl -u "$UNIT" -n 15 --no-pager 2>/dev/null
echo "--- /dev/shm/runcommand.log (letzte 20 Zeilen):"
tail -n 20 /dev/shm/runcommand.log 2>/dev/null || echo "(keins - kein Spiel gestartet)"
