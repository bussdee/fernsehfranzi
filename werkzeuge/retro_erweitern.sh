#!/bin/bash
# FernsehFranzi – RetroPie um C64 (lr-vice) und Amiga (Amiberry) erweitern. Aufruf nur über make.
#
#   werkzeuge/retro_erweitern.sh plan   zeigt, was installiert würde (ändert nichts)
#   werkzeuge/retro_erweitern.sh los    installiert über RetroPie-Setup – ZWEI Rückfragen, die Eltern antworten
#   werkzeuge/retro_erweitern.sh einrichten-plan / einrichten   (seit 3.2.2) Feinschliff nach der Installation,
#                                       ebenfalls mit ZWEI Rückfragen, nur als Kiosk-Benutzer, kein root:
#     - Kickstart-ROMs unter den Namen, die Amiberry erwartet (kick12/13/20/31.rom), nach ~/RetroPie/BIOS/amiga
#       kopieren (Original bleibt liegen). Ohne sie nimmt Amiberry den AROS-Ersatz - daran starben die Spiele.
#     - C64 (lr-vice): Kassetten (.tap) im Schnelllauf laden (vice_autoloadwarp) statt 3-8 Minuten Echtzeit.
#     - "+Start Amiberry.sh" aus der Spieleliste nehmen (öffnet sonst alle Amiberry-Einstellungen) nach
#       ~/RetroPie/eltern/ - für Eltern weiter von Hand startbar.
#     - (seit 4.1.1) Amiga-CD32-Spiele, die als ZIP vorliegen, entpacken: Amiberry kann CDs nicht aus ZIPs lesen.
#       Die Spuren kommen nach roms/amiga/.cd32/<Spiel>/, in der Liste steht "<Spiel> (CD32).cue", das ZIP wandert
#       nach ~/RetroPie/roms-archiv/amiga/ (nichts wird gelöscht). Jedes Spiel startet fest als CD32.
#   werkzeuge/retro_erweitern.sh amiga-bibliothek-plan / amiga-bibliothek   (seit 4.1.1)
#       Amiberry startete gar nicht: Die Bibliothek libserialport0 fehlte (ldd: "not found"). Installiert sie über
#       das Admin-Konto (apt, ZWEI Rückfragen, Passwort tippt der Admin).
#
# Gemessen am 21.11.: ~/RetroPie/roms/c64 (17 Spiele) und roms/amiga (4 Spiele) haben Spiele, aber keinen
# Emulator; Kickstart-ROMs liegen in ~/RetroPie/BIOS. RetroPie-Setup legt die Systeme in EmulationStation
# selbst an. Dauer: vorgefertigte Pakete wenige Minuten, sonst Bauen aus dem Quelltext (bis ~1 h auf dem Pi 3).
# Danach RetroPie einmal starten: C64 und Amiga erscheinen als neue Konsolen.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
: "${PI_HOST:?PI_HOST fehlt – config/pi.mk}"
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=10)
KIOSK="${PI_HOST%%@*}"
PAKETE=(lr-vice amiberry)

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

plan() {
  echo "=== RetroPie erweitern auf $PI_HOST ==="
  "${SSH[@]}" "$PI_HOST" 'for s in c64 amiga; do printf "  %-6s %3s Spiele\n" "$s" "$(find ~/RetroPie/roms/$s -maxdepth 2 -type f | wc -l)"; done
    printf "  Kickstart-ROMs: %s\n" "$(ls ~/RetroPie/BIOS | grep -ci kickstart)"
    printf "  Platz frei: %s\n" "$(df -h / | awk "NR==2{print \$4}")"
    grep -q "<name>c64</name>" /etc/emulationstation/es_systems.cfg && echo "  c64 schon in EmulationStation" || echo "  c64 fehlt in EmulationStation"
    grep -q "<name>amiga</name>" /etc/emulationstation/es_systems.cfg && echo "  amiga schon in EmulationStation" || echo "  amiga fehlt in EmulationStation"'
  echo "  Installiert würde (RetroPie-Setup, als root): ${PAKETE[*]}"
  echo "  Fernsehen geht währenddessen weiter; RetroPie bitte nicht starten, bis es fertig ist."
}

# Läuft als Kiosk-Benutzer auf dem Pi. Jeder Schritt nur, wenn nötig (zweiter Lauf ändert nichts).
EINRICHTEN_REMOTE='
set -eu
modus="$1"
tu() { if [ "$modus" = los ]; then "$@"; fi; }
bios="$HOME/RetroPie/BIOS"
for paar in 1.2:kick12 1.3:kick13 2.0:kick20 3.1:kick31; do
  quelle="$bios/Kickstart ${paar%%:*}.rom"; ziel="$bios/amiga/${paar##*:}.rom"
  if [ -f "$ziel" ]; then echo "  = ${paar##*:}.rom schon da"
  elif [ -f "$quelle" ]; then echo "  + Kickstart ${paar%%:*} -> amiga/${paar##*:}.rom"; tu cp -n "$quelle" "$ziel"
  else echo "  - Kickstart ${paar%%:*}.rom fehlt in BIOS (übersprungen)"; fi
done
opt="${RA_OPT:-/opt/retropie/configs/all/retroarch-core-options.cfg}"
q="$(printf "\042")"                      # Anführungszeichen (das ganze Skript steht in einfachen)
haenge_an() { printf "%s\n" "$2" >> "$1"; }
# C64 (lr-vice): Schnelllauf beim Laden; seit 4.1.1 Tasten wie in der Kinder-Anleitung (A = Feuer wie überall „OK“,
# Y/X = Leertaste, Start = F1, LB = anderer Joystick-Anschluss). Vorher war Feuer nur auf B - das fand niemand.
for paar in "vice_autoloadwarp:enabled:Schnelllauf beim Laden" "vice_mapper_a:JOYSTICK_FIRE:A = Feuer" \
            "vice_mapper_y:RETROK_SPACE:Y = Leertaste" "vice_mapper_x:RETROK_SPACE:X = Leertaste" \
            "vice_mapper_start:RETROK_F1:Start = F1" "vice_mapper_l:SWITCH_JOYPORT:LB = anderer Joystick-Anschluss"; do
  schl="${paar%%:*}"; rest="${paar#*:}"; wert="${rest%%:*}"; text="${rest#*:}"
  zeile="$schl = ${q}${wert}${q}"
  if grep -qxF "$zeile" "$opt" 2>/dev/null; then echo "  = C64: $text"
  else
    echo "  + C64: $text"
    if grep -q "^$schl " "$opt" 2>/dev/null; then tu sed -i "s|^$schl = .*|$zeile|" "$opt"
    else tu haenge_an "$opt" "$zeile"; fi
  fi
done
# 4.1.1: CD32-Spiele aus ZIPs entpacken (Amiberry liest CDs nicht aus ZIPs)
roms="$HOME/RetroPie/roms/amiga"; archiv="$HOME/RetroPie/roms-archiv/amiga"
emu="${EMU_CFG:-/opt/retropie/configs/all/emulators.cfg}"
cue_umschreiben() {   # $1 Quelle, $2 Ziel, $3 Präfix für die Spuren (relativ zur neuen .cue)
  while IFS= read -r l || [ -n "$l" ]; do
    l="${l%$(printf "
")}"
    case "$l" in
      FILE*) rest="${l#*$q}"; datei="${rest%%$q*}"; nach="${rest#*$q}"
             printf "FILE %s%s%s%s
" "$q" "$3${datei##*/}" "$q" "$nach" ;;
      *) printf "%s
" "$l" ;;
    esac
  done < "$1" > "$2"
}
emulator_setzen() {   # $1 Schlüssel, $2 Emulator (runcommand: Spiel startet immer mit diesem Emulator)
  touch "$emu"
  if grep -q "^$1 = " "$emu"; then sed -i "s|^$1 = .*|$1 = $q$2$q|" "$emu"; else printf "%s = %s%s%s
" "$1" "$q" "$2" "$q" >> "$emu"; fi
}
cd32="$(ls "$HOME/RetroPie/BIOS/amiga" 2>/dev/null | grep -ciE "cd32|40060" || true)"
if [ "$cd32" -ge 2 ]; then echo "  = CD32-Kickstart (ROM + Extended) liegt in BIOS/amiga"
else echo "  ! CD32-Kickstart fehlt in ~/RetroPie/BIOS/amiga - CD32-Spiele bleiben unverändert (ZIP), bis die ROMs da sind"; fi
for z in "$roms"/*.zip "$roms"/*.ZIP; do
  [ "$cd32" -ge 2 ] || break
  [ -f "$z" ] || continue
  cue="$(unzip -Z1 "$z" 2>/dev/null | grep -iE "[.]cue$" | head -n 1 || true)"
  [ -n "$cue" ] || continue
  name="$(basename "$z")"; name="${name%.*}"; name="${name#AmigaCD32_}"
  neu="$roms/$name (CD32).cue"
  schluessel="amiga_$(printf "%s" "$name (CD32)" | tr -cd "A-Za-z0-9_-")"
  if [ -f "$neu" ]; then echo "  = CD32: $name schon entpackt"; continue; fi
  echo "  + CD32: $name entpacken (einige Minuten), ZIP -> ~/RetroPie/roms-archiv/amiga/, startet als CD32"
  tu mkdir -p "$roms/.cd32/$name" "$archiv"
  tu unzip -q -j -o "$z" -x "*.jpg" "*.JPG" "*Thumbs.db" -d "$roms/.cd32/$name"
  tu cue_umschreiben "$roms/.cd32/$name/${cue##*/}" "$neu" ".cd32/$name/"
  tu emulator_setzen "$schluessel" "amiberry-cd32"
  tu mv -n "$z" "$archiv/"
done
gui="$HOME/RetroPie/roms/amiga/+Start Amiberry.sh"
if [ -f "$gui" ]; then echo "  + "+Start Amiberry.sh" aus der Spieleliste -> ~/RetroPie/eltern/"
  tu mkdir -p ~/RetroPie/eltern; tu mv -n "$gui" ~/RetroPie/eltern/
else echo "  = Amiberry-Einstellungen nicht in der Spieleliste"; fi
tu sync
'

einrichten() {
  "${SSH[@]}" "$PI_HOST" "bash -s -- $1" <<<"$EINRICHTEN_REMOTE"
}

retro_laeuft() {
  # nicht "pgrep -f ...": das findet die eigene SSH-Befehlszeile (am 21.11. so passiert). Prozessnamen sind
  # auf 15 Zeichen gekürzt ("emulationstatio").
  "${SSH[@]}" "$PI_HOST" 'systemctl is-active --quiet fernsehfranzi-retropie.service fernsehfranzi-spiel.service ||
    pgrep -x retroarch >/dev/null || pgrep -x amiberry >/dev/null || pgrep -x emulationstatio >/dev/null'
}

case "${1:-}" in
  plan) plan ;;
  einrichten-plan)
    echo "=== Retro-Feinschliff auf $PI_HOST (Vorschau, ändert nichts) ==="
    einrichten plan
    ;;
  einrichten)
    echo "=== Retro-Feinschliff auf $PI_HOST ==="
    einrichten plan
    if retro_laeuft; then
      echo "❌ RetroPie/ein Spiel läuft gerade (RetroArch würde die Einstellungen beim Beenden überschreiben)."
      echo "   Bitte erst zur Startseite (EXIT), dann noch einmal."
      exit 1
    fi
    frage "❓ BESTÄTIGUNG 1/2: Diese Änderungen auf dem Fernseh-Pi vornehmen?"
    frage "❓ BESTÄTIGUNG 2/2: RetroPie läuft nicht – jetzt ausführen?"
    einrichten los
    echo "✅ Fertig. Amiga-Spiele (Disketten) und C64-Kassetten jetzt in RetroPie testen."
    ;;
  amiga-bibliothek-plan|amiga-bibliothek)
    echo "=== Amiberry: fehlende Bibliotheken auf $PI_HOST ==="
    fehlt="$("${SSH[@]}" "$PI_HOST" 'ldd /opt/retropie/emulators/amiberry/amiberry | grep "not found" || true')"
    if [ -z "$fehlt" ]; then echo "  = Amiberry hat alle Bibliotheken – nichts zu tun."; exit 0; fi
    echo "$fehlt" | sed 's/^/  fehlt: /'
    case "$fehlt" in *libserialport*) ;; *) echo "❌ Unerwartete Bibliothek – bitte die Ausgabe in den Chat, nichts installiert."; exit 1 ;; esac
    echo "  Installiert würde (apt, über das Admin-Konto): libserialport0 (rund 100 KB, braucht nur libc6)"
    [ "$1" = amiga-bibliothek ] || exit 0
    : "${ADMIN_HOST:?ADMIN_HOST fehlt – config/pi.mk}"
    frage "❓ BESTÄTIGUNG 1/2: libserialport0 auf dem Fernseh-Pi installieren?"
    frage "❓ BESTÄTIGUNG 2/2: Jetzt ausführen (Admin-Passwort folgt)?"
    ssh -tt -o ConnectTimeout=10 "$ADMIN_HOST" "sudo apt-get install -y --no-install-recommends libserialport0" \
      || { echo "❌ Installation fehlgeschlagen – Ausgabe oben bitte in den Chat."; exit 1; }
    "${SSH[@]}" "$PI_HOST" 'ldd /opt/retropie/emulators/amiberry/amiberry | grep "not found"' \
      && { echo "❌ Es fehlt immer noch etwas (siehe oben)."; exit 1; }
    echo "✅ Amiberry startet wieder. Als Nächstes: make retro-einrichten (CD32-Spiele entpacken)."
    ;;
  los)
    plan
    frage "❓ BESTÄTIGUNG 1/2: Diese Pakete auf dem Fernseh-Pi installieren?"
    frage "❓ BESTÄTIGUNG 2/2: Internet ist da, RetroPie läuft gerade nicht – jetzt starten?"
    for paket in "${PAKETE[@]}"; do
      echo "=== $paket ==="
      # erst vorgefertigtes Paket, sonst aus dem Quelltext bauen
      # RetroPie-Setup richtet für den Benutzer ein, der sudo aufruft (SUDO_USER) - über das Admin-Konto
      # deshalb ausdrücklich für den Kiosk-Benutzer.
      if [ -n "${ADMIN_HOST:-}" ]; then
        ziel=(ssh -tt -o ConnectTimeout=10 "$ADMIN_HOST")
        rp="sudo env SUDO_USER=$KIOSK /home/$KIOSK/RetroPie-Setup/retropie_packages.sh"
      else
        ziel=("${SSH[@]}" -tt "$PI_HOST")
        rp="sudo -n /home/$KIOSK/RetroPie-Setup/retropie_packages.sh"
      fi
      "${ziel[@]}" "$rp $paket install_bin || $rp $paket" \
        || { echo "❌ $paket fehlgeschlagen – Ausgabe oben bitte in den Chat."; exit 1; }
      "${ziel[@]}" "$rp $paket configure" || true
    done
    "${SSH[@]}" "$PI_HOST" sync
    echo "✅ Fertig. RetroPie starten: C64 und Amiga sollten als neue Konsolen erscheinen."
    ;;
  *) echo "Aufruf: werkzeuge/retro_erweitern.sh plan|los|einrichten-plan|einrichten|amiga-bibliothek-plan|amiga-bibliothek (über make)"; exit 2 ;;
esac
