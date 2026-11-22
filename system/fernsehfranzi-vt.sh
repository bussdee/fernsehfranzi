#!/bin/sh
# FernsehFranzi - Konsole wechseln (laeuft als root aus fernsehfranzi-retropie.service).
#   vt.sh hin <N>   aktive Konsole merken, dann auf Konsole N wechseln
#   vt.sh zurueck   zur gemerkten Konsole zurueck (Vorgabe: 7, der Desktop)
set -eu
MERKER=/run/fernsehfranzi-vt
DESKTOP_VORGABE=7

case "${1:-}" in
  hin)
    ziel="${2:?Konsole fehlt}"
    aktiv="$(cat /sys/class/tty/tty0/active)"
    aktiv="${aktiv#tty}"
    if [ "$aktiv" != "$ziel" ]; then
      echo "$aktiv" > "$MERKER"
    fi
    chvt "$ziel"
    ;;
  zurueck)
    ziel="$(cat "$MERKER" 2>/dev/null || echo "$DESKTOP_VORGABE")"
    rm -f "$MERKER"
    chvt "$ziel"
    ;;
  *)
    echo "Aufruf: vt.sh hin <N> | zurueck" >&2
    exit 2
    ;;
esac
