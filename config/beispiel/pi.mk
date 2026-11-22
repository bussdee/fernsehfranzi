# Zielgerät für make deploy und make pi-check-* (VORLAGE).
# Kopieren nach config/pi.mk und anpassen. config/pi.mk ist nicht im Repository.
PI_HOST := BENUTZER@GERAET
# Hub-Ordner auf dem Gerät (die systemd-Units von v2.4 erwarten ~/familyhub).
PI_PATH := ~/familyhub
# RetroPie-Weg: A = Konsolenwechsel (Vorgabe), B = Desktop fürs Spielen beenden.
RETROPIE_WEG := A

# Admin-Konto für Deploys (sudo mit Passwort) – trägt make admin-einrichten selbst ein:
# ADMIN_HOST := ADMIN@GERAET
