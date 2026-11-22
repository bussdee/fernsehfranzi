# FernsehFranzi
# Ausliefern auf den Fernseh-Pi ist durch zwei Rückfragen geschützt, die ein Mensch eintippt.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Zielgerät: config/pi.mk (nicht im Repository, Vorlage config/beispiel/pi.mk).
-include config/pi.mk
PI_HOST ?=
PI_PATH ?= ~/familyhub
# RetroPie-Weg: A = Konsolenwechsel (Vorgabe), B = Desktop fürs Spielen beenden. Aufruf z. B.:
#   make pi-probe RETROPIE_WEG=B   ·   make deploy RETROPIE_WEG=B
RETROPIE_WEG ?= A
export PI_HOST PI_PATH RETROPIE_WEG

VENV   := .venv
PY     := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
SHELLCHECK := $(if $(wildcard $(VENV)/bin/shellcheck),$(VENV)/bin/shellcheck,shellcheck)
VERSION := $(shell tr -d '[:space:]' < VERSION)

PY_DATEIEN := $(shell git ls-files --cached --others --exclude-standard -- '*.py')
SH_DATEIEN := $(shell git ls-files --cached --others --exclude-standard -- '*.sh')
UNITS      := $(wildcard familyhub/install/*.service system/*.service)
SUDOERS    := $(wildcard familyhub/install/sudoers.d/* system/sudoers.d/*)
JSON       := $(shell git ls-files --cached --others --exclude-standard -- '*.json')
TMP        := $(shell mktemp -d -u /tmp/fernsehfranzi-check.XXXXXX)

.PHONY: help venv check test deploy-plan deploy rollback pi-probe pi-check-vor pi-check-nach _pi_host \
        v3-lokal v3-plan v3-deploy v3-pruefen v3-rollback retro-plan retro-erweitern retro-einrichten-plan retro-einrichten amiga-bibliothek-plan amiga-bibliothek admin-plan admin-einrichten admin-zurueck anleitung bildschirmfotos

help:
	@echo ""
	@echo "FernsehFranzi $(VERSION)"
	@echo ""
	@echo "  make venv           Werkzeuge lokal einrichten (.venv: Playwright, shellcheck)"
	@echo "  make check          Statische Prüfungen (Python, JS, Shell, Units, sudoers, JSON, private Daten)"
	@echo "  make test           Unittests + Oberflächentests (Playwright)"
	@echo ""
	@echo "  make pi-check-vor   Zustand des Fernseh-Pi lesen und sichern (ändert nichts)"
	@echo "  make pi-check-nach  Mit dem letzten 'vor' vergleichen (ändert nichts)"
	@echo "  make deploy-plan    Trockenlauf: was würde übertragen/gelöscht (ändert nichts)"
	@echo "  make deploy         Ausliefern – fragt ZWEIMAL"
	@echo "  make pi-probe       Probelauf RetroPie auf tty8 (keine Dateien) – fragt ZWEIMAL"
	@echo "                      Rückfallweg: make pi-probe RETROPIE_WEG=B · make deploy RETROPIE_WEG=B"
	@echo "  make rollback SICHERUNG=.local/pi-sicherung/vor-deploy-…  – fragt ZWEIMAL"
	@echo ""
	@echo "  FernsehFranzi 3.0 (Umstellung von 2.5):"
	@echo "  make v3-lokal       Server 3.0 lokal starten: http://127.0.0.1:8765/ (Daten in /tmp)"
	@echo "  make v3-plan        Trockenlauf der Umstellung (ändert nichts)"
	@echo "  make v3-deploy      Umstellen – fragt ZWEIMAL, danach Gerät einmal neu starten"
	@echo "  make v3-pruefen     Nach dem Neustart: Nachprüfung (ändert nichts)"
	@echo "  make v3-rollback SICHERUNG=/var/backups/fernsehfranzi/v3-…  – zurück auf 2.5, fragt ZWEIMAL"
	@echo "  make retro-plan     Was für C64/Amiga in RetroPie fehlt (ändert nichts)"
	@echo "  make retro-erweitern  C64 + Amiga nachinstallieren – fragt ZWEIMAL"
	@echo "  make retro-einrichten-plan / retro-einrichten  Kickstarts, C64-Schnelllauf, CD32 entpacken – fragt ZWEIMAL"
	@echo "  make amiga-bibliothek-plan / amiga-bibliothek  fehlende Bibliothek für Amiberry (apt) – fragt ZWEIMAL"
	@echo "  make admin-einrichten Admin-Konto anlegen, Kiosk-Benutzer ohne volles sudo – fragt je Schritt ZWEIMAL"
	@echo "  make anleitung      Anleitungen als PDF neu erzeugen · make bildschirmfotos  Bilder für README/Doku (docs/bilder)"
	@echo ""

venv:
	@test -x $(VENV)/bin/python || python3 -m venv $(VENV)
	@$(VENV)/bin/pip install -q --upgrade pip
	@$(VENV)/bin/pip install -q playwright shellcheck-py fonttools
	@$(VENV)/bin/python -m playwright install chromium
	@echo "✅ Werkzeuge in $(VENV)"

check:
	@echo "▶ Python kompilieren"
	@mkdir -p $(TMP) && PYTHONPYCACHEPREFIX=$(TMP)/pyc python3 -m py_compile $(PY_DATEIEN) && echo "  ✓ $(words $(PY_DATEIEN)) Dateien"
	@echo "▶ JavaScript (node --check)"
	@python3 tests/werkzeug_js.py $(TMP)/js familyhub/index.html
	@for f in familyhub/fernbedienung/*.js fernbedienung/*.js config/beispiel/*.js $(wildcard config/*.js); do node --check "$$f" || exit 1; echo "  ✓ $$f"; done
	@for f in web/js/*.js web/js/spiele/*.js; do node --input-type=module --check < "$$f" || { echo "  ✗ $$f"; exit 1; }; done; echo "  ✓ web/js (ES-Module)"
	@python3 -m py_compile system/richtlinie system/spiel-start && echo "  ✓ system/richtlinie, system/spiel-start"
	@echo "▶ Shell (shellcheck, ab Warnung)"
	@$(SHELLCHECK) --severity=warning $(SH_DATEIEN) && echo "  ✓ $(words $(SH_DATEIEN)) Skripte"
	@echo "▶ systemd-Units (systemd-analyze verify)"
	@mkdir -p $(TMP)/units
	@for u in $(UNITS); do \
	  test ! -x "$$u" || { echo "  ✗ $$u ist ausführbar markiert"; exit 1; }; \
	  r=$(TMP)/units/$$(basename $$u); sed -e 's|@BENUTZER@|family|g' -e 's|@HOME@|/home/family|g' "$$u" > "$$r"; \
	  out=$$(LC_ALL=C systemd-analyze verify "$$r" 2>&1 | grep -F "$$(basename $$u)" \
	        | grep -v -E "Command /(usr/local/lib/fernsehfranzi|usr/bin/emulationstation|home/).* is not executable" || true); \
	  if [ -n "$$out" ]; then echo "$$out"; exit 1; fi; echo "  ✓ $$u"; done
	@echo "▶ sudoers (visudo -c)"
	@mkdir -p $(TMP)
	@for s in $(SUDOERS); do sed 's|@BENUTZER@|family|g' "$$s" > $(TMP)/sudoers; visudo -c -f $(TMP)/sudoers > /dev/null || { echo "  ✗ $$s"; exit 1; }; echo "  ✓ $$s"; done
	@echo "▶ JSON"
	@if [ -n "$(JSON)" ]; then for j in $(JSON); do python3 -m json.tool "$$j" > /dev/null || { echo "  ✗ $$j"; exit 1; }; done; echo "  ✓ $(words $(JSON)) Dateien"; else echo "  – keine JSON-Dateien"; fi
	@echo "▶ Private Daten in versionierten Dateien"
	@python3 tests/pruefe_privat.py
	@rm -rf $(TMP)
	@echo "✅ check grün"

test:
	@echo "▶ Unittests (tests/)"
	@$(PY) -m unittest discover -s tests -p 'test_*.py'
	@echo "▶ Navigationstest aus v2.4 (familyhub/tests/test_nav.py)"
	@$(PY) familyhub/tests/test_nav.py | tail -n 2
	@echo "✅ test grün"

_pi_host:
	@test -n "$(PI_HOST)" || { echo "❌ PI_HOST fehlt – config/pi.mk anlegen (Vorlage: config/beispiel/pi.mk)"; exit 1; }

pi-check-vor: _pi_host
	@python3 werkzeuge/pi_check.py vor --host "$(PI_HOST)" --pfad "$(PI_PATH)"

pi-check-nach: _pi_host
	@python3 werkzeuge/pi_check.py nach --host "$(PI_HOST)" --pfad "$(PI_PATH)" $(if $(PI_CHECK_VERSION),--version $(PI_CHECK_VERSION))

deploy-plan: _pi_host
	@bash werkzeuge/deploy.sh plan

deploy: _pi_host check test
	@bash werkzeuge/deploy.sh los

rollback: _pi_host
	@bash werkzeuge/deploy.sh zurueck "$(SICHERUNG)"

pi-probe: _pi_host
	@bash werkzeuge/deploy.sh probe

# ---------------------------------------------------------------- FernsehFranzi 3.0
V3_PATH ?= ~/fernsehfranzi
ADMIN_HOST ?=
export V3_PATH ADMIN_HOST

v3-lokal:
	@mkdir -p /tmp/fernsehfranzi-lokal
	@cd server && FERNSEHFRANZI_DATEN=/tmp/fernsehfranzi-lokal python3 -m fernsehfranzi

v3-plan: _pi_host
	@bash werkzeuge/deploy_v3.sh plan

v3-deploy: _pi_host check test
	@bash werkzeuge/deploy_v3.sh los

v3-pruefen: _pi_host
	@python3 werkzeuge/pi_check.py nach --host "$(PI_HOST)" --pfad "$(V3_PATH)" --version "$(VERSION)" \
	  --neustart-erlaubt --abgeloest familyhub-server.service --abgeloest familyhub-cec.service

v3-rollback: _pi_host
	@bash werkzeuge/deploy_v3.sh zurueck "$(SICHERUNG)"

# ---------------------------------------------------------------- RetroPie erweitern (C64, Amiga)
retro-plan: _pi_host
	@bash werkzeuge/retro_erweitern.sh plan

retro-erweitern: _pi_host
	@bash werkzeuge/retro_erweitern.sh los

retro-einrichten-plan: _pi_host
	@bash werkzeuge/retro_erweitern.sh einrichten-plan

retro-einrichten: _pi_host
	@bash werkzeuge/retro_erweitern.sh einrichten

amiga-bibliothek-plan: _pi_host
	@bash werkzeuge/retro_erweitern.sh amiga-bibliothek-plan

amiga-bibliothek: _pi_host
	@bash werkzeuge/retro_erweitern.sh amiga-bibliothek

# ---------------------------------------------------------------- Admin-Konto (volles sudo des Kiosk-Benutzers weg)
admin-plan: _pi_host
	@bash werkzeuge/admin_einrichten.sh plan

admin-einrichten: _pi_host
	@bash werkzeuge/admin_einrichten.sh los

admin-zurueck: _pi_host
	@bash werkzeuge/admin_einrichten.sh zurueck

# ---------------------------------------------------------------- Anleitung (PDF für die Eltern-Seite)
anleitung:
	@$(PY) werkzeuge/anleitung_pdf.py

# ---------------------------------------------------------------- Bildschirmfotos (README, docs/bilder)
bildschirmfotos:
	@$(PY) werkzeuge/bildschirmfotos.py
