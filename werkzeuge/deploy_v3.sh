#!/bin/bash
# FernsehFranzi 3.0 – Umstellung und Ausliefern auf den Fernseh-Pi. Aufruf nur über make.
#
#   werkzeuge/deploy_v3.sh plan              Trockenlauf (ändert nichts)
#   werkzeuge/deploy_v3.sh los               Ausliefern mit ZWEI Rückfragen am Terminal (die Eltern antworten)
#   werkzeuge/deploy_v3.sh zurueck <ordner>  install/rollback.sh auf dem Gerät (ZWEI Rückfragen)
#
# Code nach ~/fernsehfranzi (V3_PATH), Daten bleiben in ~/fernsehfranzi-daten (nie übertragen, nie gelöscht).
# Die 2.x-Installation ~/familyhub bleibt liegen (Rückweg), ihre Dienste werden abgeschaltet.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
: "${PI_HOST:?PI_HOST fehlt – config/pi.mk}"
V3_PATH="${V3_PATH:-~/fernsehfranzi}"
BENUTZER="${PI_HOST%%@*}"
VERSION="$(tr -d '[:space:]' < VERSION)"
case "$VERSION" in
  3.*|4.*) ;;                     # 4.0 nutzt denselben Weg (gleicher Aufbau, gleiche Daten)
  *) echo "❌ VERSION ist $VERSION – dieses Werkzeug liefert 3.x und 4.x aus."; exit 2 ;;
esac
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=10)
# Root-Schritte: über das Admin-Konto (sudo mit Passwort, seit make admin-einrichten), sonst wie bisher
# über den Kiosk-Benutzer (sudo -n, nur solange er noch volles sudo hat).
ADMIN_HOST="${ADMIN_HOST:-}"
als_root() {   # $1 = Befehl (Pfade absolut, ~ wäre beim Admin dessen Home)
  if [ -n "$ADMIN_HOST" ]; then
    echo "    (als root über $ADMIN_HOST – bitte dessen Passwort eingeben)"
    ssh -tt -o ConnectTimeout=10 "$ADMIN_HOST" "sudo $1"
  else
    "${SSH[@]}" "$PI_HOST" "sudo -n $1"
  fi
}
TEILE=(VERSION server web kiosk eingabe fernbedienung system install)

rsync_v3() {
  rsync -az --delete --relative --exclude '__pycache__/' --exclude '*.pyc' -e "${SSH[*]}" "$@" \
    "${TEILE[@]}" "$PI_HOST:$V3_PATH/"
}

zeige_plan() {
  echo "=== FernsehFranzi $VERSION → $PI_HOST:$V3_PATH/ ==="
  echo "    Übertragen: ${TEILE[*]}"
  rsync_v3 --dry-run --itemize-changes | grep -v '^\.' | sed 's/^/    /' | tail -n 40 || true
  echo ""
  echo "    Danach als root: install/install.sh $BENUTZER"
  echo "      – Sicherung nach /var/backups/fernsehfranzi/v3-<zeit> (Rückweg: make v3-rollback)"
  echo "      – Daten aus ~/familyhub übernehmen (Name, Adressen, Ton, Zeichnungen)"
  echo "      – Units fernsehfranzi-server/-eingabe, sudo-Regel, Chromium-Richtlinie, labwc-Autostart,"
  echo "        ES-Tastatur, RetroArch-Netzwerkbefehle; familyhub-server/-cec werden abgeschaltet"
  echo "      – 4.1: labwc ohne Tastenkürzel (kein Terminal per Tastatur), Sondertasten der BT-Tastatur (hwdb),"
  echo "        Bluetooth-Helfer + eine Zeile mehr in der sudo-Regel, N64-Einstellungen, WLAN-Energiesparen aus"
  echo "      – 4.2: Dienst fernsehfranzi-scraper (Bilder für Retro-Spiele) + eine Zeile mehr in der sudo-Regel"
  echo "    Danach: Gerät EINMAL sauber neu starten (sudo systemctl reboot), dann: make v3-pruefen"
}

frage() {
  local antwort
  if ! { exec 3</dev/tty; } 2>/dev/null; then
    echo "❌ Kein Terminal – die Bestätigung muss ein Mensch eintippen. Abgebrochen."
    exit 1
  fi
  read -r -u 3 -p "$1 [ja/NEIN] " antwort
  exec 3<&-
  [ "$antwort" = "ja" ] || { echo "❌ Abgebrochen."; exit 1; }
}

case "${1:-}" in
  plan)
    zeige_plan
    ;;
  los)
    zeige_plan
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║  ⚠️   UMSTELLUNG AUF FERNSEHFRANZI $VERSION – $PI_HOST"
    echo "║  Der Fernseh-Pi ist das Gerät eines Kindes – kein Testserver.        ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    frage "❓ BESTÄTIGUNG 1/2: Plan gelesen, lokale Version geprüft und freigegeben?"
    ZEIT="$(date +%Y%m%d-%H%M%S)"
    mkdir -p .local
    VOR="$(python3 werkzeuge/pi_check.py vor --host "$PI_HOST" --pfad "$V3_PATH")" || {
      printf '%s\n' "$VOR"; echo "❌ pi-check vor ist rot – nichts übertragen."; exit 1; }
    printf '%s\n' "$VOR"
    SICHERUNG=".local/pi-sicherung/vor-v3-$ZEIT"
    mkdir -p "$SICHERUNG"
    rsync -a --exclude '/.kiosk-profile/' -e "${SSH[*]}" "$PI_HOST:~/familyhub/" "$SICHERUNG/familyhub/" || true
    echo "Sicherung (lokal): $SICHERUNG"
    frage "❓ BESTÄTIGUNG 2/2: Jetzt übertragen und auf FernsehFranzi $VERSION umstellen?"
    "${SSH[@]}" "$PI_HOST" "mkdir -p $V3_PATH"
    rsync_v3                       # direkt davor: Code auf dem Gerät = geprüfter Stand aus dem Repository
    CODE_ABS="$("${SSH[@]}" "$PI_HOST" "cd $V3_PATH && pwd")"
    INSTALL_OK=1
    als_root "bash $CODE_ABS/install/install.sh $BENUTZER" | tee ".local/INSTALL-$VERSION-$ZEIT.log" || INSTALL_OK=0
    sleep 8
    NACH_CODE=0
    NACH="$(python3 werkzeuge/pi_check.py nach --host "$PI_HOST" --pfad "$V3_PATH" --version "$VERSION" \
            --abgeloest familyhub-server.service --abgeloest familyhub-cec.service)" || NACH_CODE=$?
    printf '%s\n' "$NACH"
    {
      echo "# Umstellung auf $VERSION"; echo ""
      echo "- Zeit: $ZEIT · Ziel: \`$PI_HOST:$V3_PATH\` · Commit: \`$(git rev-parse --short HEAD)\`"
      echo "- Systemteil: $([ "$INSTALL_OK" = 1 ] && echo ja || echo 'NEIN – Fehler') (Log: .local/INSTALL-$VERSION-$ZEIT.log)"
      echo "## pi-check vor"; echo '```'; printf '%s\n' "$VOR"; echo '```'
      echo "## pi-check nach"; echo '```'; printf '%s\n' "$NACH"; echo '```'
    } > ".local/DEPLOY-$VERSION.md"
    GERAET_SICHERUNG="$("${SSH[@]}" "$PI_HOST" "ls -d /var/backups/fernsehfranzi/v3-* 2>/dev/null | tail -n 1" || true)"
    if [ "$INSTALL_OK" != 1 ] || [ "$NACH_CODE" != 0 ]; then
      echo "❌ Nicht grün. Nicht herumprobieren – zurück auf den Stand vor diesem Deploy:"
      echo "   cd $REPO && make v3-rollback SICHERUNG=$GERAET_SICHERUNG"
      exit 1
    fi
    echo "✅ Übertragen und eingerichtet: $VERSION"
    echo "   Jetzt das Gerät EINMAL sauber neu starten:  ssh -t ${ADMIN_HOST:-$PI_HOST} sudo systemctl reboot"
    echo "   (nicht Strom ziehen), danach:  cd $REPO && make v3-pruefen"
    echo "   Zurück auf den Stand vor diesem Deploy, falls etwas nicht stimmt:  cd $REPO && make v3-rollback SICHERUNG=$GERAET_SICHERUNG"
    ;;
  zurueck)
    ORDNER="${2:?Sicherungsordner auf dem Gerät fehlt (/var/backups/fernsehfranzi/v3-…)}"
    case "$ORDNER" in /var/backups/fernsehfranzi/v3-*) ;; *) echo "❌ Kein v3-Sicherungsordner: $ORDNER"; exit 2 ;; esac
    echo "=== Zurück auf 2.5: $PI_HOST, Sicherung $ORDNER ==="
    frage "❓ BESTÄTIGUNG 1/2: Zurückrollen auf den Stand vor der Umstellung?"
    frage "❓ BESTÄTIGUNG 2/2: Jetzt auf dem Fernseh-Pi zurückrollen?"
    CODE_ABS="$("${SSH[@]}" "$PI_HOST" "cd $V3_PATH && pwd")"
    als_root "bash $CODE_ABS/install/rollback.sh '$ORDNER'"
    echo "Bitte das Gerät neu starten, danach: make pi-check-nach"
    ;;
  *)
    echo "Aufruf: werkzeuge/deploy_v3.sh plan|los|zurueck <ordner> (über make)"
    exit 2
    ;;
esac
