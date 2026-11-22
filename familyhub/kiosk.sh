#!/bin/bash
# FernsehFranzi v2 - Kiosk-Supervisor
#
# Wird beim Desktop-Login gestartet (install/familyhub-kiosk.desktop)
# und haelt den Chromium-Kiosk am Leben:
#   - Chromium beendet (Absturz, EXIT-Taste = Alt+F4) -> sofort neu starten
#   - laeuft gerade EmulationStation (der Games-Server hat Chromium
#     dafuer beendet) -> warten, bis RetroPie beendet ist, dann neu starten
#
# Seit 2.5: --enable-spatial-navigation - Pfeiltasten der Fernbedienung springen auf
# jeder Webseite (Plex, Kavita, Dashboard) von Link zu Link, OK klickt. Die Startseite
# faengt ihre Pfeiltasten selbst ab und bleibt unveraendert.
# Seit 2.5.2: Erweiterung fernbedienung/ - Plex belegt die Pfeile selbst (Lautstaerke);
# die Erweiterung haelt sie dort von Plex fern, damit das Springen auch in Plex klappt.
#
# Eigenes Chromium-Profil (.kiosk-profile): verhindert, dass der
# chromium-browser-Wrapper neue Fenster an eine alte, abgestuerzte
# Sitzung weiterleitet ("Wird in einer aktuellen Browsersitzung
# geoeffnet" + Broken Pipes aus v1).
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$DIR/logs/kiosk.log"

# Raspberry Pi OS: neuere Versionen kennen nur "chromium", aeltere
# "chromium-browser" - beide Namen werden probiert.
CHROMIUM="$(command -v chromium || command -v chromium-browser || true)"

mkdir -p "$DIR/logs"

# Nach dem Boot Desktop kurz atmen lassen, bis X sicher steht.
sleep 3

FLAG="/tmp/familyhub-games"

spiel_aktiv() {
  pgrep -f "emulationstation" > /dev/null 2>&1 && return 0
  if [ -e "$FLAG" ]; then
    # Marke nur 60 s lang ernst nehmen (falls der Server abgestuerzt ist)
    alter=$(( $(date +%s) - $(stat -c %Y "$FLAG" 2>/dev/null || echo 0) ))
    [ "$alter" -lt 60 ] && return 0
  fi
  return 1
}

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"
}

log "Kiosk-Supervisor gestartet (PID $$)."
# Seit 2.5.4: Nach einem Update (neue kiosk.sh) laedt sich die Schleife beim naechsten
# Chromium-Neustart selbst neu - neue Chromium-Schalter wirken ohne Geraete-Neustart.
SELBST="$(readlink -f "${BASH_SOURCE[0]}")"
SELBST_STAND="$(stat -c %Y "$SELBST" 2>/dev/null || echo 0)"

if [ -z "$CHROMIUM" ]; then
  log "FEHLER: weder chromium noch chromium-browser gefunden."
  exit 1
fi

while true; do
  "$CHROMIUM" \
    --kiosk \
    --start-fullscreen \
    --window-position=0,0 \
    --noerrdialogs \
    --disable-infobars \
    --no-first-run \
    --hide-crash-restore-bubble \
    --password-store=basic \
    --check-for-update-interval=31536000 \
    --enable-spatial-navigation \
    --load-extension="$DIR/fernbedienung" \
    --user-data-dir="$DIR/.kiosk-profile" \
    "file://$DIR/index.html" >> "$LOG" 2>&1

  log "Chromium beendet (Exit-Code $?)."

  if [ "$(stat -c %Y "$SELBST" 2>/dev/null || echo 0)" != "$SELBST_STAND" ]; then
    log "kiosk.sh wurde aktualisiert - lade neu."
    exec "$SELBST"
  fi

  # Laeuft RetroPie oder wird es gerade gestartet? Dann warten - Chromium
  # startet nur diese Schleife, nie der Server. Der Games-Server legt beim
  # Start die Marke $FLAG an (und loescht sie nach dem Ende von ES); so gibt
  # es keine Luecke mehr zwischen "Chromium beendet" und "ES laeuft".
  # Hinweis: pgrep -f noetig, Prozessnamen sind auf 15 Zeichen begrenzt.
  while spiel_aktiv; do
    sleep 1
  done

  log "RetroPie ist zu Ende - Startseite wird neu gestartet (Vollbild)."
  sleep 2
done
