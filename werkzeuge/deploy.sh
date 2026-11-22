#!/bin/bash
# FernsehFranzi – Ausliefern auf den Fernseh-Pi. Aufruf nur über `make deploy`.
#
#   werkzeuge/deploy.sh plan     Trockenlauf: zeigt, was übertragen und gelöscht würde (ändert nichts)
#   werkzeuge/deploy.sh los      Ausliefern mit ZWEI Rückfragen, die ein Mensch am Terminal beantwortet
#   werkzeuge/deploy.sh zurueck <sicherung>   Code aus einer Sicherung zurück + Systemteil entfernen (ZWEI Rückfragen)
#   werkzeuge/deploy.sh probe    Probelauf RetroPie auf tty8 als vorübergehende Unit (ZWEI Rückfragen)
#
# Erwartet PI_HOST und PI_PATH in der Umgebung (aus config/pi.mk, über das Makefile).
# Ablauf von "los": Plan zeigen → Bestätigung 1 → pi-check vor → Sicherung des Hub-Ordners
# vom Gerät nach .local/ (nur lesend) → Bestätigung 2 → rsync → Dienste neu starten →
# pi-check nach → Protokoll .local/DEPLOY-<version>.md
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

: "${PI_HOST:?PI_HOST fehlt – config/pi.mk anlegen (Vorlage: config/beispiel/pi.mk)}"
: "${PI_PATH:?PI_PATH fehlt – config/pi.mk anlegen (Vorlage: config/beispiel/pi.mk)}"
VERSION="$(tr -d '[:space:]' < VERSION)"
# RetroPie-Weg: A = Konsolenwechsel (Vorgabe), B = Desktop fürs Spielen beenden (Rückfallweg).
RETROPIE_WEG="${RETROPIE_WEG:-A}"
case "$RETROPIE_WEG" in A|B) ;; *) echo "❌ RETROPIE_WEG muss A oder B sein."; exit 2 ;; esac
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=10)
# Dienste, die nach dem Übertragen neu gestartet werden (v2.4-Namen).
NEUSTART_DIENSTE=(familyhub-server.service familyhub-cec.service)

# Was auf dem Gerät entsteht und dort bleiben muss: nie übertragen, nie löschen.
AUSSCHLUESSE=(
  --exclude '/logs/'
  --exclude '/zeichnungen/'
  --exclude '/.kiosk-profile/'
  --exclude '/config/'
  --exclude '/audio.txt'
  --exclude '__pycache__/'
  --exclude '*.pyc'
)

rsync_hub() {  # $@ = zusätzliche rsync-Optionen
  rsync -az --delete "${AUSSCHLUESSE[@]}" -e "${SSH[*]}" "$@" familyhub/ "$PI_HOST:$PI_PATH/"
}

zeige_plan() {
  echo "=== Trockenlauf: familyhub/ → $PI_HOST:$PI_PATH/ (Version $VERSION) ==="
  echo "    Ausgeschlossen (bleibt auf dem Gerät): logs/ zeichnungen/ .kiosk-profile/ config/ audio.txt"
  local plan
  plan="$(rsync_hub --dry-run --itemize-changes)"
  if [ -z "$plan" ]; then
    echo "    (keine Änderungen am Hub-Ordner)"
  else
    printf '%s\n' "$plan" | sed 's/^/    /'
  fi
  echo ""
  echo "    Löschungen: $(printf '%s\n' "$plan" | grep -c '^\*deleting' || true)"
  echo "    Zusätzlich: VERSION → $PI_PATH/VERSION"
  if "${SSH[@]}" "$PI_HOST" "test -e $PI_PATH/config/einstellungen.js"; then
    echo "    config/einstellungen.js: auf dem Gerät vorhanden – bleibt unverändert"
  elif [ -f config/einstellungen.js ]; then
    echo "    config/einstellungen.js: fehlt auf dem Gerät – wird einmalig angelegt"
  else
    echo "    config/einstellungen.js: fehlt hier und auf dem Gerät – Kacheln zeigen dann einen Hinweis"
  fi
  if [ -f familyhub/install/system.sh ]; then
    echo "    Danach als root: install/system.sh $RETROPIE_WEG (RetroPie-Unit tty8, Helfer, sudo-Regel, ES-Tastatur; mit Sicherung)"
    if [ "$RETROPIE_WEG" = B ]; then
      echo "    RetroPie-Weg B: Desktop wird fürs Spielen beendet, Rückkehr zur Startseite dauert 15–25 s."
    else
      echo "    RetroPie-Weg A: Konsolenwechsel, Startseite bleibt offen."
    fi
  fi
  echo "    Danach neu gestartet: ${NEUSTART_DIENSTE[*]}"
  echo "    Danach Startseite neu laden: Chromium wird beendet, kiosk.sh startet ihn sofort neu."
  echo "    kiosk.sh lädt sich nach dem Chromium-Neustart selbst neu (ab 2.5.4; vor 2.5.4 nur nach Geräte-Neustart)."
}

frage() {  # $1 = Text. Liest bewusst vom Terminal, nicht aus einer Pipe.
  local antwort
  if ! { exec 3</dev/tty; } 2>/dev/null; then
    echo "❌ Kein Terminal – die Bestätigung muss ein Mensch eintippen. Abgebrochen."
    exit 1
  fi
  read -r -u 3 -p "$1 [ja/NEIN] " antwort
  exec 3<&-
  if [ "$antwort" != "ja" ]; then
    echo "❌ Abgebrochen."
    exit 1
  fi
}

case "${1:-}" in
  plan)
    zeige_plan
    ;;
  los)
    zeige_plan
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║  ⚠️   AUSLIEFERN AUF $PI_HOST (Version $VERSION)"
    echo "║  Der Fernseh-Pi ist das Gerät eines Kindes – kein Testserver.        ║"
    echo "║  Voraussetzung: make check und make test grün (eben gelaufen).       ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    frage "❓ BESTÄTIGUNG 1/2: Plan gelesen, lokale Version geprüft und freigegeben?"

    ZEIT="$(date +%Y%m%d-%H%M%S)"
    PROTOKOLL=".local/DEPLOY-$VERSION.md"
    mkdir -p .local
    VOR_AUSGABE="$(python3 werkzeuge/pi_check.py vor --host "$PI_HOST" --pfad "$PI_PATH")" || {
      printf '%s\n' "$VOR_AUSGABE"; echo "❌ pi-check vor ist rot – nichts übertragen."; exit 1; }
    printf '%s\n' "$VOR_AUSGABE"

    SICHERUNG=".local/pi-sicherung/vor-deploy-$VERSION-$ZEIT"
    mkdir -p "$SICHERUNG"
    echo "Sichere $PI_PATH vom Gerät nach $SICHERUNG (ohne .kiosk-profile) ..."
    rsync -a --exclude '/.kiosk-profile/' -e "${SSH[*]}" "$PI_HOST:$PI_PATH/" "$SICHERUNG/"
    test -n "$(ls -A "$SICHERUNG")" || { echo "❌ Sicherung ist leer – nichts übertragen."; exit 1; }
    echo "Sicherung: $(find "$SICHERUNG" -type f | wc -l) Dateien."

    frage "❓ BESTÄTIGUNG 2/2: Jetzt auf den Fernseh-Pi übertragen und Dienste neu starten?"

    rsync_hub
    rsync -az -e "${SSH[*]}" VERSION "$PI_HOST:$PI_PATH/VERSION"
    if [ -f config/einstellungen.js ]; then
      "${SSH[@]}" "$PI_HOST" "mkdir -p $PI_PATH/config"
      rsync -az --ignore-existing -e "${SSH[*]}" config/einstellungen.js "$PI_HOST:$PI_PATH/config/einstellungen.js"
    fi
    SYSTEM_OK=1
    if [ -f familyhub/install/system.sh ]; then
      if ! "${SSH[@]}" "$PI_HOST" "sudo -n bash $PI_PATH/install/system.sh $RETROPIE_WEG"; then
        echo "❌ Systemteil (install/system.sh) fehlgeschlagen."
        SYSTEM_OK=0
      fi
    fi
    NEUSTART_OK=1
    if ! "${SSH[@]}" "$PI_HOST" "sudo -n systemctl restart ${NEUSTART_DIENSTE[*]}"; then
      echo "❌ Neustart der Dienste fehlgeschlagen (sudo/systemctl). Zustand wird geprüft."
      NEUSTART_OK=0
    fi
    # Neue Startseite laden: kiosk.sh (Besitzer von Chromium) startet ihn sofort neu.
    if ! "${SSH[@]}" "$PI_HOST" "pkill -x chromium"; then
      echo "⚠ Chromium lief nicht oder ließ sich nicht beenden – Startseite ggf. per Neustart laden."
    fi
    sleep 12   # cec-Dienst wartet 8 s nach dem Start, Chromium braucht einige Sekunden

    NACH_CODE=0
    NACH_AUSGABE="$(python3 werkzeuge/pi_check.py nach --host "$PI_HOST" --pfad "$PI_PATH" --version "$VERSION")" || NACH_CODE=$?
    printf '%s\n' "$NACH_AUSGABE"

    {
      echo "# Deploy $VERSION"
      echo ""
      echo "- Zeit: $ZEIT"
      echo "- Ziel: \`$PI_HOST:$PI_PATH\`"
      echo "- Commit: \`$(git rev-parse --short HEAD)\`$(git diff --quiet HEAD -- familyhub VERSION || echo ' (mit nicht committeten Änderungen!)')"
      echo "- Sicherung: \`$SICHERUNG\`"
      echo "- Systemteil: $([ "$SYSTEM_OK" = 1 ] && echo ja || echo 'NEIN – Fehler') (RetroPie-Weg $RETROPIE_WEG)"
      echo "- Dienste neu gestartet: $([ "$NEUSTART_OK" = 1 ] && echo ja || echo 'NEIN – Fehler')"
      echo ""
      echo "## pi-check vor"; echo '```'; printf '%s\n' "$VOR_AUSGABE"; echo '```'
      echo "## pi-check nach"; echo '```'; printf '%s\n' "$NACH_AUSGABE"; echo '```'
    } > "$PROTOKOLL"
    echo "Protokoll: $PROTOKOLL"

    if [ "$NACH_CODE" != 0 ] || [ "$NEUSTART_OK" != 1 ] || [ "$SYSTEM_OK" != 1 ]; then
      echo "❌ Nachprüfung ROT. Nicht herumprobieren. Zurückrollen:"
      echo "   cd $REPO && make rollback SICHERUNG=$SICHERUNG"
      exit 1
    fi
    echo "✅ Ausgeliefert: $VERSION"
    echo "   Zurück, falls am Fernseher etwas nicht stimmt: cd $REPO && make rollback SICHERUNG=$SICHERUNG"
    ;;
  zurueck)
    SICHERUNG="${2:-}"
    if [ -z "$SICHERUNG" ] || [ ! -f "$SICHERUNG/server.py" ]; then
      echo "❌ Sicherung fehlt oder unvollständig: '$SICHERUNG'"
      echo "   Vorhanden:"; ls -d .local/pi-sicherung/vor-deploy-* 2>/dev/null | sed 's/^/     /'
      exit 1
    fi
    echo "=== Zurückrollen auf $PI_HOST:$PI_PATH aus $SICHERUNG ==="
    rsync -az --delete "${AUSSCHLUESSE[@]}" --dry-run --itemize-changes -e "${SSH[*]}" \
      "$SICHERUNG/" "$PI_HOST:$PI_PATH/" | sed 's/^/    /'
    echo "    Außerdem: Systemteil 2.5 entfernen (Unit, Helfer, sudo-Regel), es_input.cfg aus der"
    echo "    letzten Gerätesicherung (/var/backups/fernsehfranzi), Dienste neu starten."
    frage "❓ BESTÄTIGUNG 1/2: Plan gelesen – zurückrollen?"
    frage "❓ BESTÄTIGUNG 2/2: Jetzt auf dem Fernseh-Pi zurückrollen?"
    GERAET_SICHERUNG="$("${SSH[@]}" "$PI_HOST" "ls -d /var/backups/fernsehfranzi/* 2>/dev/null | tail -n 1" || true)"
    if "${SSH[@]}" "$PI_HOST" "test -f $PI_PATH/install/rollback-system.sh"; then
      "${SSH[@]}" "$PI_HOST" "sudo -n bash $PI_PATH/install/rollback-system.sh '$GERAET_SICHERUNG'" \
        || echo "⚠ rollback-system.sh meldete einen Fehler"
    fi
    # --delete nimmt auch die VERSION-Datei weg, falls die Sicherung keine hatte.
    rsync -az --delete "${AUSSCHLUESSE[@]}" -e "${SSH[*]}" "$SICHERUNG/" "$PI_HOST:$PI_PATH/"
    "${SSH[@]}" "$PI_HOST" "sudo -n systemctl restart ${NEUSTART_DIENSTE[*]}" || echo "❌ Neustart der Dienste fehlgeschlagen"
    sleep 12
    python3 werkzeuge/pi_check.py nach --host "$PI_HOST" --pfad "$PI_PATH" || true
    echo "Zurückgerollt aus $SICHERUNG. Ergebnis oben prüfen und berichten."
    ;;
  probe)
    echo "=== Probelauf RetroPie auf $PI_HOST, Weg $RETROPIE_WEG ==="
    echo "    Startet EmulationStation als vorübergehende Unit auf tty8 (keine Datei wird geschrieben)."
    if [ "$RETROPIE_WEG" = B ]; then
      echo "    Weg B: Der Desktop wird dafür beendet und danach neu gestartet (15–25 s)."
    fi
    echo "    Am Fernseher: Spiel starten, spielen, beenden, dann ES beenden (Start > Quit oder EXIT)."
    echo "    Danach springt der Fernseher zurück zur Startseite. Abbruch hier: Strg+C."
    frage "❓ BESTÄTIGUNG 1/2: Probelauf auf dem Fernseh-Pi starten?"
    frage "❓ BESTÄTIGUNG 2/2: Fernseher ist an und der Controller steckt – jetzt starten?"
    # -tt: Strg+C erreicht das Skript auf dem Gerät (es räumt dann auf).
    "${SSH[@]}" -tt "$PI_HOST" "sudo -n bash -c $(printf '%q' "$(cat familyhub/install/retropie_probe.sh)") probe ${PI_HOST%%@*} $RETROPIE_WEG"
    ;;
  *)
    echo "Aufruf: werkzeuge/deploy.sh plan|los|zurueck <sicherung>|probe (über make)"
    exit 2
    ;;
esac
