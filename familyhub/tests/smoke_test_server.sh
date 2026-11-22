#!/bin/bash
# Smoke-Test fuer den v2-Games-Server - pfadunabhaengig und sicher.
#
# Getestet werden beide Pfade des X-Preflights und die Endpunkte.
#
# Sicherheitshinweis gegenueber der Entwicklungsfassung: Der echte
# X-Socket (/tmp/.X11-unix/X0) wird NICHT angetastet. Fall A simuliert
# eine fehlende Desktop-Sitzung stattdessen ueber DISPLAY=:99 - der
# Server prueft dann /tmp/.X11-unix/X99 und muss ablehnen.
#
# Ausfuehren:  bash tests/smoke_test_server.sh
set -u

PAKET="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SMOKE="$(mktemp -d /tmp/familyhub-smoke.XXXXXX)"
cleanup() { [ -n "${SRV:-}" ] && kill "$SRV" 2>/dev/null; wait "${SRV:-0}" 2>/dev/null; rm -rf "$SMOKE"; }
trap cleanup EXIT

echo "Paket: $PAKET"
rm -rf "${SMOKE:?}"/*
cp -r "$PAKET/." "$SMOKE/"
rm -rf "$SMOKE/logs" "$SMOKE/.kiosk-profile" "$SMOKE/docs" "$SMOKE/tests"

echo ""
echo "=== Fall A: kein X-Socket auf Anzeige :99 (Preflight muss ablehnen) ==="
cd "$SMOKE" || exit 1
DISPLAY=:99 python3 server.py > /dev/null 2>&1 &
SRV=$!
sleep 1.5

A_GAMES=$(curl -s http://127.0.0.1:8765/games)
A_STATUS=$(curl -s http://127.0.0.1:8765/status)
A_404=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/gibtsnicht)

echo "--- /games (Auszug):"
echo "$A_GAMES" | grep -o "<h1>[^<]*</h1>"
echo "$A_GAMES" | grep -o "Kein X-Server[^<]*" | head -1
echo "--- /status: $A_STATUS"
echo "--- 404-Check: $A_404"
echo "--- server.log:"
grep -E "abgelehnt|verweigert" "$SMOKE/logs/server.log" | head -3

kill $SRV 2>/dev/null; wait $SRV 2>/dev/null

echo ""
echo "=== Fall B: X-Socket vorhanden (Startversuch, ES fehlt auf dem Entwicklungsrechner) ==="
rm -rf "$SMOKE/logs"
cd "$SMOKE" || exit 1
python3 server.py > /dev/null 2>&1 &
SRV=$!
sleep 1.5

B_GAMES=$(curl -s http://127.0.0.1:8765/games)
echo "--- /games (Auszug):"
echo "$B_GAMES" | grep -o "<h1>[^<]*</h1>"
sleep 2
echo "--- server.log:"
grep -E "angeordnet|fehlgeschlagen|verweigert" "$SMOKE/logs/server.log" | tail -3
if [ ! -e /tmp/.X11-unix/X0 ]; then
  echo "--- Hinweis: Auf diesem Rechner gibt es keinen X-Socket - Fall B"
  echo "    verhaelt sich dann korrekt wie Fall A (Preflight-Verweigerung)."
fi

kill $SRV 2>/dev/null; wait $SRV 2>/dev/null
echo ""
echo "=== Fertig ==="
