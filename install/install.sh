#!/bin/bash
# FernsehFranzi 3.0 - Systemteil einrichten. Läuft als root auf dem Gerät, wiederholbar (idempotent).
#
#   install.sh <benutzer>     z. B. install.sh family   (Code liegt in ~<benutzer>/fernsehfranzi)
#
# Vorher wird alles gesichert, was ersetzt oder geändert wird: /var/backups/fernsehfranzi/v3-<zeit>/
# Zurück: install/rollback.sh <sicherungsordner>
#
# Schritte:
#   1  Sicherung
#   2  Daten aus 2.x übernehmen (Name, Adressen, Ton, Zeichnungen) - als Kiosk-Benutzer
#   3  Units, Konsolen-Helfer, Richtlinien-Helfer, sudo-Regel
#   4  Chromium-Richtlinie (Kiosk-Härtung)
#   5  labwc: Kiosk statt Desktop/Taskleiste (Autostart), kiosk.py statt kiosk.sh
#   6  EmulationStation: Fernbedienung als Tastatur · RetroArch: Netzwerkbefehle (Zeitwarnung, Speichern)
#   7  Dienste umstellen: familyhub-* aus, fernsehfranzi-* an
# Danach: Gerät einmal neu starten (labwc-Sitzung mit dem neuen Kiosk).
set -euo pipefail

[ "$(id -u)" = 0 ] || { echo "install.sh muss als root laufen." >&2; exit 1; }
BENUTZER="${1:?Aufruf: install.sh <benutzer>}"
HOME_B="$(getent passwd "$BENUTZER" | cut -d: -f6)"
[ -n "$HOME_B" ] && [ -d "$HOME_B" ] || { echo "Benutzer $BENUTZER unbekannt." >&2; exit 2; }
CODE="$HOME_B/fernsehfranzi"
DATEN="$HOME_B/fernsehfranzi-daten"
[ -f "$CODE/VERSION" ] || { echo "$CODE/VERSION fehlt - erst den Code übertragen." >&2; exit 2; }
ALT="$HOME_B/familyhub"
LABWC_SYS=/etc/xdg/labwc/autostart
LABWC_BEN="$HOME_B/.config/labwc/autostart"
ES_INPUT=/opt/retropie/configs/all/emulationstation/es_input.cfg
ES_SETTINGS=/opt/retropie/configs/all/emulationstation/es_settings.cfg
RA_CFG=/opt/retropie/configs/all/retroarch.cfg
RICHTLINIEN=/etc/chromium/policies/managed
MARKE="#FernsehFranzi3:"
HWDB=/etc/udev/hwdb.d/90-fernsehfranzi-tastatur.hwdb
NM_WLAN=/etc/NetworkManager/conf.d/90-fernsehfranzi-wlan.conf
RA_KERN=/opt/retropie/configs/all/retroarch-core-options.cfg
LABWC_RC="$HOME_B/.config/labwc/rc.xml"
LABWC_MENU="$HOME_B/.config/labwc/menu.xml"

ohne_nullbytes() {  # Reste eines Stromausfalls (Dateiende voller \0) entfernen
  if [ -f "$1" ] && [ "$(tr -cd '\000' < "$1" | wc -c)" != 0 ]; then
    tr -d '\000' < "$1" > "$1.ff-neu" && cat "$1.ff-neu" > "$1" && rm -f "$1.ff-neu"
    echo "   Nullbytes entfernt: $1"
  fi
}

ersetze() {  # Platzhalter in Vorlagen füllen
  sed -e "s|@BENUTZER@|$BENUTZER|g" -e "s|@HOME@|$HOME_B|g" "$1"
}

echo "1/7 Sicherung ..."
SICHERUNG="/var/backups/fernsehfranzi/v3-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$SICHERUNG"
for datei in /etc/systemd/system/familyhub-server.service /etc/systemd/system/familyhub-cec.service \
             /etc/systemd/system/fernsehfranzi-server.service /etc/systemd/system/fernsehfranzi-eingabe.service \
             /etc/systemd/system/fernsehfranzi-retropie.service /etc/sudoers.d/fernsehfranzi \
             /usr/local/lib/fernsehfranzi/vt.sh /usr/local/lib/fernsehfranzi/richtlinie \
             /etc/systemd/system/fernsehfranzi-spiel.service /usr/local/lib/fernsehfranzi/spiel-start \
             /usr/local/lib/fernsehfranzi/bt-helfer /etc/systemd/system/fernsehfranzi-scraper.service \
             "$LABWC_SYS" "$LABWC_BEN" "$ES_INPUT" "$ES_SETTINGS" "$RA_CFG" \
             "$RICHTLINIEN/fernsehfranzi.json" "$RICHTLINIEN/fernsehfranzi-whitelist.json" \
             "$HWDB" "$LABWC_RC" "$LABWC_MENU" "$NM_WLAN" "$RA_KERN"; do
  if [ -e "$datei" ]; then
    mkdir -p "$SICHERUNG$(dirname "$datei")"
    cp -a "$datei" "$SICHERUNG$datei"
  else
    echo "$datei" >> "$SICHERUNG/neu.txt"     # gab es vorher nicht -> rollback.sh entfernt sie wieder
  fi
done
for dienst in familyhub-server familyhub-cec fernsehfranzi-server fernsehfranzi-eingabe; do
  echo "$dienst $(systemctl is-enabled "$dienst" 2>/dev/null || echo fehlt)" >> "$SICHERUNG/dienste.txt"
done
echo "   $SICHERUNG"

echo "2/7 Daten übernehmen ..."
install -d -m 0700 -o "$BENUTZER" -g "$BENUTZER" "$DATEN"
if [ -d "$ALT" ]; then
  runuser -u "$BENUTZER" -- env FERNSEHFRANZI_DATEN="$DATEN" PYTHONDONTWRITEBYTECODE=1 \
    python3 -c "import sys; sys.path.insert(0, '$CODE/server'); from fernsehfranzi import uebernahme; print('\n'.join(uebernahme.uebernehme('$ALT')))" \
    | sed 's/^/   /'
  # Browser-Profil aus 2.x übernehmen (Anmeldungen bei Plex & Co. bleiben erhalten)
  if [ -d "$ALT/.kiosk-profile" ] && [ ! -e "$DATEN/chromium-profil" ]; then
    runuser -u "$BENUTZER" -- cp -a "$ALT/.kiosk-profile" "$DATEN/chromium-profil"
    rm -f "$DATEN/chromium-profil/SingletonLock" "$DATEN/chromium-profil/SingletonSocket" \
          "$DATEN/chromium-profil/SingletonCookie"
    echo "   Browser-Profil übernommen (Anmeldungen bleiben)."
  fi
fi

echo "3/7 Units, Helfer, sudo-Regel ..."
install -d -m 0755 /usr/local/lib/fernsehfranzi
install -m 0755 -o root -g root "$CODE/system/fernsehfranzi-vt.sh" /usr/local/lib/fernsehfranzi/vt.sh
install -m 0755 -o root -g root "$CODE/system/spiel-start" /usr/local/lib/fernsehfranzi/spiel-start
install -m 0755 -o root -g root "$CODE/system/bt-helfer" /usr/local/lib/fernsehfranzi/bt-helfer
ersetze "$CODE/system/richtlinie" > /usr/local/lib/fernsehfranzi/richtlinie
chown root:root /usr/local/lib/fernsehfranzi/richtlinie
chmod 0755 /usr/local/lib/fernsehfranzi/richtlinie
for unit in fernsehfranzi-server fernsehfranzi-eingabe fernsehfranzi-retropie fernsehfranzi-spiel fernsehfranzi-scraper; do
  ersetze "$CODE/system/$unit.service" > "/etc/systemd/system/$unit.service"
  chmod 0644 "/etc/systemd/system/$unit.service"
done
REGEL="$(mktemp)"
ersetze "$CODE/system/sudoers.d/fernsehfranzi" > "$REGEL"
visudo -c -f "$REGEL" > /dev/null
install -m 0440 -o root -g root "$REGEL" /etc/sudoers.d/fernsehfranzi
rm -f "$REGEL"
visudo -c > /dev/null
systemctl daemon-reload
for unit in fernsehfranzi-server fernsehfranzi-eingabe fernsehfranzi-retropie fernsehfranzi-spiel fernsehfranzi-scraper; do
  systemd-analyze verify "/etc/systemd/system/$unit.service" || echo "   Warnung: verify meldet etwas für $unit" >&2
done

echo "4/7 Chromium-Richtlinie ..."
install -d -m 0755 "$RICHTLINIEN"
install -m 0644 -o root -g root "$CODE/system/chromium/fernsehfranzi.json" "$RICHTLINIEN/fernsehfranzi.json"

echo "5/7 labwc: Kiosk statt Desktop ..."
if [ -f "$LABWC_SYS" ]; then
  # Desktop und Taskleiste nicht mehr automatisch (der Elternbereich startet sie für den Linux-Desktop)
  sed -i -E "/^$MARKE/! s~^(/usr/bin/lwrespawn /usr/bin/(pcmanfm --desktop|wf-panel-pi).*)$~$MARKE \1~" "$LABWC_SYS"
fi
install -d -m 0755 -o "$BENUTZER" -g "$BENUTZER" "$(dirname "$LABWC_BEN")"
touch "$LABWC_BEN"
ohne_nullbytes "$LABWC_BEN"
[ -z "$(tail -c 1 "$LABWC_BEN")" ] || echo >> "$LABWC_BEN"   # letzte Zeile abschließen
# alte Kiosk-Zeile (kiosk.sh) auskommentieren, kiosk.py einmalig eintragen
sed -i -E "/^$MARKE/! s~^([^#].*familyhub/kiosk\.sh.*)$~$MARKE \1~" "$LABWC_BEN"
if ! grep -q "fernsehfranzi/kiosk/kiosk.py" "$LABWC_BEN"; then
  printf '\n# FernsehFranzi 3.0 - Kiosk\nFERNSEHFRANZI_DATEN=%s /usr/bin/python3 %s/kiosk/kiosk.py &\n' "$DATEN" "$CODE" >> "$LABWC_BEN"
fi
chown "$BENUTZER:$BENUTZER" "$LABWC_BEN"
# 4.1: keine Tastenkürzel der Arbeitsfläche (sonst Terminal mit Strg+Alt+T / Super+Enter), leere Menüs
install -m 0644 -o "$BENUTZER" -g "$BENUTZER" "$CODE/system/labwc/rc.xml" "$LABWC_RC"
install -m 0644 -o "$BENUTZER" -g "$BENUTZER" "$CODE/system/labwc/menu.xml" "$LABWC_MENU"
echo "   labwc: Kiosk-Tastenkürzel (keine), leere Menüs"
# 4.1: Sondertasten der Bluetooth-Tastatur (Zurück/Home/Suche/Menü) umlegen
install -d -m 0755 /etc/udev/hwdb.d
install -m 0644 -o root -g root "$CODE/system/udev/90-fernsehfranzi-tastatur.hwdb" "$HWDB"
systemd-hwdb update && udevadm trigger --subsystem-match=input --action=change || echo "   Warnung: hwdb-Aktualisierung meldet etwas" >&2
echo "   Tastatur: Sondertasten umgelegt (wirkt sofort bzw. nach dem Neustart)"

echo "6/7 EmulationStation und RetroArch ..."
if [ -f "$ES_INPUT" ]; then
  runuser -u "$BENUTZER" -- python3 "$CODE/install/es_tastatur.py" "$ES_INPUT" | sed 's/^/   /'
fi
if [ -f "$RA_CFG" ]; then
  ohne_nullbytes "$RA_CFG"
  [ -z "$(tail -c 1 "$RA_CFG")" ] || echo >> "$RA_CFG"
  # Netzwerkbefehle für Zeitwarnung im Spiel (SHOW_MSG), Spielstand sichern und Beenden
  if grep -q '^network_cmd_enable' "$RA_CFG"; then
    sed -i 's/^network_cmd_enable.*/network_cmd_enable = "true"/' "$RA_CFG"
  else
    echo 'network_cmd_enable = "true"' >> "$RA_CFG"
  fi
  echo "   RetroArch: network_cmd_enable = true"
  # Kiosk-Modus: im Spielmenü nur Weiterspielen/Speichern/Laden/Beenden - keine Einstellungen verstellbar
  if grep -q '^kiosk_mode_enable' "$RA_CFG"; then
    sed -i 's/^kiosk_mode_enable.*/kiosk_mode_enable = "true"/' "$RA_CFG"
  else
    echo 'kiosk_mode_enable = "true"' >> "$RA_CFG"
  fi
  echo "   RetroArch: Kiosk-Modus an"
fi
if [ -f "$ES_SETTINGS" ]; then
  ohne_nullbytes "$ES_SETTINGS"
  # EmulationStation-Kiosk: kein Neustart/Herunterfahren/Einstellungen im Menü (Zurück: EXIT, Xbox-Taste)
  if grep -q 'name="UIMode"' "$ES_SETTINGS"; then
    sed -i 's|<string name="UIMode" value="[^"]*" />|<string name="UIMode" value="Kiosk" />|' "$ES_SETTINGS"
  else
    sed -i 's|</config>|<string name="UIMode" value="Kiosk" />\n</config>|' "$ES_SETTINGS"
  fi
  # Entsperr-Code: nicht der bekannte Konami-Code, sondern zufällig (u d l r a b), einmal gesetzt
  if grep -q 'name="UIMode_passkey" value="uuddlrlrba"' "$ES_SETTINGS" || ! grep -q 'name="UIMode_passkey"' "$ES_SETTINGS"; then
    # nicht "tr < /dev/urandom | head": unter pipefail bricht das ab (SIGPIPE) - am 21.11. so passiert
    CODE_ES="$(python3 -c "import secrets; print(''.join(secrets.choice('udlrab') for _ in range(10)))")"
    if grep -q 'name="UIMode_passkey"' "$ES_SETTINGS"; then
      sed -i "s|<string name=\"UIMode_passkey\" value=\"[^\"]*\" />|<string name=\"UIMode_passkey\" value=\"$CODE_ES\" />|" "$ES_SETTINGS"
    else
      sed -i "s|</config>|<string name=\"UIMode_passkey\" value=\"$CODE_ES\" />\n</config>|" "$ES_SETTINGS"
    fi
    echo "   EmulationStation-Entsperrcode (Steuerkreuz u/d/l/r + A/B, gut aufheben): $CODE_ES"
  fi
  chown "$BENUTZER:$BENUTZER" "$ES_SETTINGS"
  echo "   EmulationStation: Kiosk-Modus an"
fi

# 4.1: N64 für den Pi 3 (nur wenn gerade kein Spiel läuft - RetroArch schreibt die Datei beim Beenden zurück)
if [ -f "$RA_KERN" ]; then
  if pgrep -x retroarch > /dev/null; then
    echo "   Warnung: Ein Retro-Spiel läuft - N64-Einstellungen diesmal übersprungen (beim nächsten Deploy)." >&2
  else
    ohne_nullbytes "$RA_KERN"
    [ -z "$(tail -c 1 "$RA_KERN")" ] || echo >> "$RA_KERN"
    grep -E '^mupen64plus-next-' "$CODE/system/retroarch/n64-pi3.cfg" | while IFS= read -r zeile; do
      schluessel="${zeile%% =*}"
      if grep -q "^$schluessel " "$RA_KERN"; then
        sed -i "s|^$schluessel .*|$zeile|" "$RA_KERN"
      else
        echo "$zeile" >> "$RA_KERN"
      fi
    done
    chown "$BENUTZER:$BENUTZER" "$RA_KERN"
    echo "   RetroArch: N64-Einstellungen für den Pi 3"
  fi
fi

# 4.1: WLAN-Energiesparen aus (wirkt nach dem Neustart; NetworkManager wird hier NICHT neu gestartet - SSH bliebe sonst hängen)
if [ -d /etc/NetworkManager/conf.d ]; then
  install -m 0644 -o root -g root "$CODE/system/networkmanager/90-fernsehfranzi-wlan.conf" "$NM_WLAN"
  echo "   WLAN: Energiesparen aus (nach dem Neustart)"
fi

echo "7/7 Dienste umstellen ..."
for dienst in familyhub-server familyhub-cec; do
  if systemctl list-unit-files "$dienst.service" > /dev/null 2>&1; then
    systemctl disable --now "$dienst.service" 2>/dev/null || true
  fi
done
systemctl enable --now fernsehfranzi-server.service fernsehfranzi-eingabe.service
sync   # alles sicher auf die SD-Karte (Strom aus direkt danach verlor am 21.11. Daten)
echo ""
echo "Fertig. Sicherung: $SICHERUNG"
echo "Bitte das Gerät einmal neu starten – sauber mit: sudo systemctl reboot (nicht Strom ziehen)."
