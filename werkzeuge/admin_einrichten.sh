#!/bin/bash
# FernsehFranzi – eigenes Admin-Konto auf dem Fernseh-Pi, danach dem Kiosk-Benutzer das volle sudo nehmen.
# Aufruf nur über make (make admin-plan · make admin-einrichten · make admin-zurueck).
#
# Warum: Der Kiosk-Benutzer (lightdm-Autologin, Chromium, Server) durfte bisher ALLES als root ohne Passwort
# (/etc/sudoers.d/010_pi-nopasswd + Gruppe sudo). Wer den Kiosk knackt, hätte das ganze Gerät.
# Danach gilt:
#   - Kiosk-Benutzer: nur noch die enge Regel /etc/sudoers.d/fernsehfranzi (RetroPie, Neustart, Whitelist …)
#   - Admin-Konto:    sudo MIT Passwort; Deploys laufen über dieses Konto, das Passwort tippt der Admin
#
# Ablauf von "los" (jeder Teil fragt ZWEIMAL, Name und Passwort tippt der Admin selbst):
#   1  Admin-Konto anlegen (adduser fragt das Passwort ab) und in die Gruppen sudo und adm aufnehmen
#   2  SSH-Schlüssel des Kiosk-Benutzers übernehmen (gleicher Schlüssel vom Rechner aus)
#   3  Probe: Admin meldet sich an und sudo klappt mit Passwort – sonst Abbruch, nichts weiter geändert
#   4  Kiosk-Benutzer: 010_pi-nopasswd sichern und entfernen, aus der Gruppe sudo nehmen
#   5  ADMIN_HOST in config/pi.mk eintragen (Deploys nutzen es)
# Zurück: make admin-zurueck (stellt 010_pi-nopasswd und die Gruppe wieder her; das Konto bleibt).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
: "${PI_HOST:?PI_HOST fehlt – config/pi.mk}"
KIOSK="${PI_HOST%%@*}"
GERAET="${PI_HOST#*@}"
SSH=(ssh -o ConnectTimeout=10)
SICHERUNG=/var/backups/fernsehfranzi/sudo-vorher

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

lies_name() {
  local name
  exec 3</dev/tty
  read -r -u 3 -p "Name des neuen Admin-Kontos (klein, z. B. fernsehadmin): " name
  exec 3<&-
  [[ "$name" =~ ^[a-z][a-z0-9-]{2,31}$ ]] || { echo "❌ Ungültiger Name (a-z, 0-9, -; 3–32 Zeichen)." >&2; exit 2; }
  [ "$name" != "$KIOSK" ] && [ "$name" != root ] || { echo "❌ Bitte einen eigenen Namen wählen." >&2; exit 2; }
  echo "$name"
}

case "${1:-}" in
  plan)
    echo "=== Admin-Konto für $GERAET ==="
    "${SSH[@]}" -o BatchMode=yes "$PI_HOST" "sudo -n ls /etc/sudoers.d/; getent group sudo; ls /home" | sed 's/^/    /'
    echo "    Danach: Admin-Konto mit sudo (Passwort), Kiosk-Benutzer $KIOSK nur noch mit der engen Regel."
    echo "    Wichtig: make retro-erweitern vorher laufen lassen, wenn C64/Amiga gewünscht sind (geht auch danach über das Admin-Konto)."
    ;;
  los)
    NAME="$(lies_name)"
    ADMIN="$NAME@$GERAET"
    echo "=== Schritt 1–2: Konto $NAME anlegen, Schlüssel übernehmen ==="
    frage "❓ BESTÄTIGUNG 1/2: Admin-Konto $NAME auf $GERAET anlegen?"
    frage "❓ BESTÄTIGUNG 2/2: Du tippst gleich das NEUE Passwort zweimal ein (gut merken!) – weiter?"
    "${SSH[@]}" -tt "$PI_HOST" "id $NAME >/dev/null 2>&1 || sudo -n adduser --gecos '' $NAME"
    "${SSH[@]}" -o BatchMode=yes "$PI_HOST" "sudo -n usermod -aG sudo,adm $NAME \
      && sudo -n install -d -m 0700 -o $NAME -g $NAME /home/$NAME/.ssh \
      && sudo -n install -m 0600 -o $NAME -g $NAME ~/.ssh/authorized_keys /home/$NAME/.ssh/authorized_keys \
      && sync"
    echo "=== Schritt 3: Probe – bitte das Passwort von $NAME eingeben ==="
    if ! "${SSH[@]}" -tt "$ADMIN" "sudo -v && sudo -l >/dev/null && echo ADMIN-OK" | tee /dev/stderr | grep -q ADMIN-OK; then
      echo "❌ Probe fehlgeschlagen – volles sudo von $KIOSK bleibt unverändert."
      exit 1
    fi
    echo "=== Schritt 4: Kiosk-Benutzer $KIOSK das volle sudo nehmen ==="
    frage "❓ BESTÄTIGUNG 1/2: 010_pi-nopasswd sichern und entfernen, $KIOSK aus der Gruppe sudo nehmen?"
    frage "❓ BESTÄTIGUNG 2/2: Die Probe mit $NAME war erfolgreich – jetzt umstellen?"
    "${SSH[@]}" -tt "$ADMIN" "sudo install -d -m 0700 $SICHERUNG \
      && sudo cp -a /etc/sudoers.d/010_pi-nopasswd $SICHERUNG/ \
      && sudo rm -f /etc/sudoers.d/010_pi-nopasswd \
      && sudo gpasswd -d $KIOSK sudo \
      && sudo visudo -c >/dev/null && sync && echo UMGESTELLT"
    if "${SSH[@]}" -o BatchMode=yes "$PI_HOST" "sudo -n true" 2>/dev/null; then
      echo "⚠ $KIOSK hat noch volles sudo – bitte Ausgabe oben prüfen."
    else
      echo "✅ $KIOSK hat kein volles sudo mehr (die enge Regel für den Server bleibt)."
    fi
    if ! grep -q '^ADMIN_HOST' config/pi.mk 2>/dev/null; then
      printf '\n# Admin-Konto für Deploys (sudo mit Passwort), eingerichtet mit make admin-einrichten\nADMIN_HOST := %s\n' "$ADMIN" >> config/pi.mk
      echo "config/pi.mk: ADMIN_HOST := $ADMIN eingetragen."
    fi
    ;;
  zurueck)
    : "${ADMIN_HOST:?ADMIN_HOST fehlt in config/pi.mk}"
    frage "❓ BESTÄTIGUNG 1/2: Dem Kiosk-Benutzer $KIOSK das volle sudo zurückgeben?"
    frage "❓ BESTÄTIGUNG 2/2: Wirklich? (Sicherheitslücke wie vorher)"
    "${SSH[@]}" -tt "$ADMIN_HOST" "sudo install -m 0440 -o root -g root $SICHERUNG/010_pi-nopasswd /etc/sudoers.d/010_pi-nopasswd \
      && sudo usermod -aG sudo $KIOSK && sudo visudo -c >/dev/null && sync && echo ZURUECK"
    ;;
  *) echo "Aufruf: werkzeuge/admin_einrichten.sh plan|los|zurueck (über make)"; exit 2 ;;
esac
