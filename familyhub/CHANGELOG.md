# Changelog
## v2.4
- Kiosk startet `chromium` oder `chromium-browser` (je nach System)
- ES-Start mit Sitzungs-Umgebung (XDG_RUNTIME_DIR, D-Bus): behebt RetroArch-Absturz "Ladebild, dann zurueck zu ES" und fehlenden Ton
- X11-Display wird automatisch gefunden (XWayland unter labwc), Wayland-Variablen werden nicht vererbt
- Ton: ROT = HDMI, GRUEN = Klinke (wpctl), Wahl wird gespeichert; keine amixer-Eingriffe mehr
- EXIT beendet je nach Lage Spiel / ES / Fenster; unbekannte CEC-Tasten werden geloggt
- Scheitert ES sofort, bleibt der Hub offen (vorher schwarzer Bildschirm)
- Apps oeffnen standardmaessig im selben Vollbild-Fenster (CONFIG.appsAlsPopup)
- kiosk.sh/server.py: Marke /tmp/familyhub-games statt blindem 3-s-Warten, schnellere und sichere Rueckkehr
- CEC-Dienst wartet 8 s nach dem Boot (HDMI/TV bereit)
- install.sh: labwc-Autostart automatisch angepasst (mit Sicherung), alte Dienste abgeloest, tests/pi_check.sh
## v2.3 / v2.3.1
Navigation, Spielzimmer, Galerie, Controller (siehe v2.3-Dokumentation).
