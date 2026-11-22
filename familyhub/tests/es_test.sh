#!/bin/bash
# ES-Probelauf VOR dem Umstellen: startet EmulationStation genau so, wie es
# server.py spaeter tut (X11 ueber XWayland, Sitzungs-Umgebung). Erfordert eine
# laufende Desktop-Sitzung (der Fernseher zeigt dann ES). Per ssh ausfuehrbar.
# Danach: ein Spiel starten, spielen, beenden (Start -> Quit) und Log ansehen.
RT="/run/user/$(id -u)"
D=$(find /tmp/.X11-unix -maxdepth 1 -name 'X[0-9]*' -printf '%f\n' 2>/dev/null | head -n 1 | sed 's/^X/:/')
[ -z "$D" ] && { echo "Kein X-Socket in /tmp/.X11-unix - ist die Desktop-Sitzung (labwc) an?"; exit 1; }
echo "Starte EmulationStation auf DISPLAY=$D (Strg+C bricht ab) ..."
env -u WAYLAND_DISPLAY -u XDG_SESSION_TYPE \
  DISPLAY="$D" XDG_RUNTIME_DIR="$RT" DBUS_SESSION_BUS_ADDRESS="unix:path=$RT/bus" \
  SDL_VIDEODRIVER=x11 TERM=linux emulationstation
echo "ES beendet. Letzte Zeilen des Emulator-Logs:"
tail -15 /dev/shm/runcommand.log 2>/dev/null
