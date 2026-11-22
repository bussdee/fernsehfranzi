#!/bin/bash
# Vorab-Check direkt auf dem Pi (am besten im Terminal AM Pi, nicht per ssh,
# weil dann auch Sitzungsvariablen sichtbar sind). Aendert nichts.
ok()   { echo "  [OK]    $*"; }
warn() { echo "  [FEHLT] $*"; FEHLER=1; }
FEHLER=0
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

echo "== Programme"
for p in emulationstation retroarch cec-client wpctl pgrep pkill; do
  command -v "$p" > /dev/null && ok "$p" || warn "$p nicht installiert"
done
command -v chromium > /dev/null && ok "chromium" || \
  { command -v chromium-browser > /dev/null && ok "chromium-browser" || warn "kein Chromium"; }
python3 -c "import evdev" 2>/dev/null && ok "python3-evdev" || warn "python3-evdev"

echo "== Sitzung"
echo "  XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-?}  WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-?}  DISPLAY=${DISPLAY:-?}"
compgen -G '/tmp/.X11-unix/X[0-9]*' > /dev/null \
  && ok "X-Socket: $(ls /tmp/.X11-unix | tr '\n' ' ')" \
  || warn "kein X-Socket in /tmp/.X11-unix (XWayland/X11 laeuft nicht - ES kann nicht starten)"
RT="/run/user/$(id -u)"
[ -S "$RT/bus" ] && ok "D-Bus der Sitzung ($RT/bus)" || warn "kein D-Bus unter $RT/bus"

echo "== Ton (wpctl)"
if wpctl status 2>/dev/null | sed -n '/Sinks:/,/Sources:/p' | grep -E '[0-9]+\.' ; then
  wpctl status | sed -n '/Sinks:/,/Sources:/p' | grep -qi hdmi && ok "HDMI-Ausgang vorhanden" || warn "kein HDMI-Ausgang in der Liste (TV an?)"
else
  warn "wpctl liefert keine Ausgaenge (PipeWire laeuft?)"
fi

echo "== Dienste"
for d in familyhub-server familyhub-cec; do
  systemctl is-active --quiet $d && ok "$d aktiv" || warn "$d nicht aktiv (journalctl -u $d -n 30)"
done
curl -s --max-time 3 http://127.0.0.1:8765/status | grep -q running && ok "Games-Server antwortet" || warn "Games-Server antwortet nicht"
systemctl is-enabled --quiet cec-keys.service 2>/dev/null && warn "cec-keys.service ist noch aktiv (Doppelstart!)"
[ "$(pgrep -fc cec_keys.py)" -le 1 ] && ok "cec_keys.py nur einmal" || warn "cec_keys.py laeuft mehrfach"
[ "$(pgrep -xc cec-client)" -le 1 ] && ok "cec-client nur einmal" || warn "cec-client laeuft mehrfach (alter Prozess: sudo pkill -x cec-client; sudo systemctl restart familyhub-cec)"
pgrep -f "games_launcher.py|familyhub/familyhub.py" > /dev/null && warn "alte Hub-Prozesse laufen noch (bis zum Neustart ok)"

echo "== Autostart"
grep -n "kiosk.sh\|chromium\|familyhub" "$HOME/.config/labwc/autostart" 2>/dev/null | grep -v '^\S*:#' | sed 's/^/  /'
[ -f "$HOME/.config/autostart/familyhub-kiosk.desktop" ] && [ -d "$HOME/.config/labwc" ] && warn "kiosk.desktop + labwc-Autostart = Doppelstart"

echo
[ $FEHLER = 0 ] && echo "Alles in Ordnung." || echo "Bitte die [FEHLT]-Punkte beheben."
