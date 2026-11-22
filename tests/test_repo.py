"""Repository-Regeln: Versionsquelle, ausgelagerte private Werte, Datenschutz-Scan."""
import os
import re
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HIER)
sys.path.insert(0, HIER)
import pruefe_privat  # noqa: E402


def lies(*teile):
    with open(os.path.join(REPO, *teile), encoding="utf-8") as f:
        return f.read()


class Version(unittest.TestCase):
    def test_version_format(self):
        self.assertRegex(lies("VERSION").strip(), r"^\d+\.\d+\.\d+$")

    def test_keine_feste_version_in_seite_und_server(self):
        """Regel 23: Server liest VERSION, die Startseite zeigt, was der Server meldet."""
        html = lies("familyhub", "index.html")
        self.assertIn('<span class="footer-brand" id="version">FAMILY HUB</span>', html)
        self.assertNotRegex(html, r"FAMILY HUB &middot; V\d")
        server = lies("familyhub", "server.py")
        self.assertIn("VERSION = lies_version()", server)
        self.assertNotRegex(server, r"log\.info\(\"[^\"]*v\d+\.\d+")

    def test_changelog_nennt_version(self):
        self.assertIn("## %s" % lies("VERSION").strip(), lies("CHANGELOG.md"))


class PrivateWerteAusgelagert(unittest.TestCase):
    def setUp(self):
        self.html = lies("familyhub", "index.html")

    def test_konfiguration_wird_geladen(self):
        self.assertIn('<script src="config/einstellungen.js"></script>', self.html)
        self.assertLess(self.html.index('src="config/einstellungen.js"'), self.html.index("const CONFIG"))

    def test_keine_festen_adressen_ausser_localhost(self):
        for url in re.findall(r"https?://[^\s\"'<>]+", self.html):
            self.assertTrue(url.startswith("http://127.0.0.1:"), url)

    def test_app_kacheln_ohne_ziel(self):
        kacheln = re.findall(r'<a class="tile [^"]+" id="(\w+)" tabindex="-1"\s+href="([^"]*)"( data-link="(\w+)")?', self.html)
        ziele = {k[0]: (k[1], k[3]) for k in kacheln}
        self.assertEqual(ziele["plex"], ("#", "plex"))
        self.assertEqual(ziele["family"], ("#", "familie"))
        self.assertEqual(ziele["books"], ("#", "buecher"))
        self.assertEqual(ziele["games"][0], "#")
        self.assertIn('data-aktion="retropie"', self.html)

    def test_vorlage_hat_alle_schluessel_ohne_echte_werte(self):
        vorlage = lies("config", "beispiel", "einstellungen.js")
        for schluessel in ("name:", "untertitel:", "plex:", "familie:", "buecher:", "geburtstage:"):
            self.assertIn(schluessel, vorlage)
        self.assertIn('name: ""', vorlage)
        self.assertIn("window.FERNSEHFRANZI_EINSTELLUNGEN", vorlage)

    def test_private_konfiguration_ist_ignoriert(self):
        gitignore = lies(".gitignore")
        self.assertIn("/config/*", gitignore)
        self.assertIn("!/config/beispiel/", gitignore)


class RetroPieAufDerKonsole(unittest.TestCase):
    """Regel 11: kein X11/Wayland-Zwang, keine Display-Variablen, kein SDL_VIDEODRIVER."""

    def test_kiosk_mit_spatial_navigation(self):
        kiosk = lies("familyhub", "kiosk.sh")
        self.assertIn("--enable-spatial-navigation", kiosk)
        self.assertIn('--load-extension="$DIR/fernbedienung"', kiosk)
        self.assertTrue(os.path.isfile(os.path.join(REPO, "familyhub", "fernbedienung", "manifest.json")))

    def test_exit_beendet_nur_emulationstation_selbst(self):
        """pkill -f emulationstation traf beim Probelauf am 21.11. auch dessen ssh/sudo-Hülle."""
        cec = lies("familyhub", "cec_keys.py")
        self.assertNotIn('"pkill", "-f", "emulationstation"', cec)
        self.assertIn('"pkill", "-x", "emulationstation"', cec)

    def test_keine_tilde_hinter_gleichheitszeichen_in_skripten(self):
        """Bash macht aus `X=~` als Argument das Home des Aufrufers (unter sudo: /root).
        So scheiterte der erste Probelauf (status=200/CHDIR). `~` gehört in Anführungszeichen."""
        import glob
        import re
        for pfad in glob.glob(os.path.join(REPO, "familyhub", "install", "*.sh")) + \
                glob.glob(os.path.join(REPO, "werkzeuge", "*.sh")):
            with open(pfad, encoding="utf-8") as datei:
                zeilen = datei.readlines()
            for nr, zeile in enumerate(zeilen, 1):
                if zeile.lstrip().startswith("#"):
                    continue
                self.assertNotRegex(zeile, r"(^|\s)[A-Za-z_][A-Za-z0-9_.]*=~", "%s:%d" % (pfad, nr))
        self.assertIn('-p "WorkingDirectory=~"', lies("familyhub", "install", "retropie_probe.sh"))

    def test_server_ohne_x11_und_ohne_chromium_beenden(self):
        server = lies("familyhub", "server.py")
        for verboten in ("DISPLAY", "XAUTHORITY", "pkill", "SDL_VIDEODRIVER\"]", "/games"):
            self.assertNotIn(verboten, server, verboten)

    def test_unit(self):
        unit = lies("familyhub", "install", "fernsehfranzi-retropie.service")
        for zeile in ("User=family", "PAMName=login", "TTYPath=/dev/tty8", "StandardInput=tty-force",
                      "ExecStart=/usr/bin/emulationstation",
                      "UnsetEnvironment=DISPLAY WAYLAND_DISPLAY SDL_VIDEODRIVER",
                      "ExecStartPre=+/usr/local/lib/fernsehfranzi/vt.sh hin 8",
                      "ExecStopPost=+/usr/local/lib/fernsehfranzi/vt.sh zurueck"):
            self.assertIn(zeile + "\n", unit)
        self.assertNotRegex(unit, r"(?m)^Environment=.*(DISPLAY|SDL_VIDEODRIVER)")

    def test_sudo_regel_passt_zum_server(self):
        regel = lies("familyhub", "install", "sudoers.d", "fernsehfranzi")
        server = lies("familyhub", "server.py")
        self.assertIn('befehl = ["sudo", "-n", SYSTEMCTL, "start", "--no-block", RETROPIE_UNIT]', server)
        self.assertIn('SYSTEMCTL = "/usr/bin/systemctl"', server)
        self.assertIn("NOPASSWD: /usr/bin/systemctl start --no-block fernsehfranzi-retropie.service,", regel)
        self.assertNotRegex(regel, r"NOPASSWD:\s*ALL")


class RueckfallwegB(unittest.TestCase):
    """Weg B (Desktop fürs Spielen beenden) ist vorbereitet und nur auf Wunsch aktiv."""

    def test_dropin(self):
        dropin = lies("familyhub", "install", "fernsehfranzi-retropie-weg-b.conf")
        for zeile in ("Conflicts=lightdm.service", "After=lightdm.service",
                      "ExecStopPost=+/usr/bin/systemctl start --no-block lightdm.service"):
            self.assertIn(zeile + "\n", dropin)
        self.assertIn("die Startseite kommt gleich", dropin)

    def test_system_sh_waehlt_weg(self):
        system = lies("familyhub", "install", "system.sh")
        self.assertIn('WEG="${1:-A}"', system)
        self.assertIn('if [ "$WEG" = B ]; then', system)
        self.assertIn("weg-b.conf", lies("familyhub", "install", "rollback-system.sh"))

    def test_deploy_und_probe_reichen_weg_durch(self):
        deploy = lies("werkzeuge", "deploy.sh")
        self.assertIn('RETROPIE_WEG="${RETROPIE_WEG:-A}"', deploy)
        self.assertIn("install/system.sh $RETROPIE_WEG", deploy)
        self.assertIn('probe ${PI_HOST%%@*} $RETROPIE_WEG"', deploy)
        self.assertIn("RETROPIE_WEG ?= A", lies("Makefile"))


class Datenschutzscan(unittest.TestCase):
    """Der Scan muss Funde melden (rot) und saubere Dateien durchlassen (grün)."""

    def scanne(self, inhalt, werte=()):
        with tempfile.TemporaryDirectory() as ordner:
            with open(os.path.join(ordner, "datei.txt"), "w", encoding="utf-8") as f:
                f.write(inhalt)
            return [f[2] for f in pruefe_privat.pruefe(["datei.txt"], list(werte), basis=ordner)]

    # Beispielwerte zusammengesetzt, damit diese Datei den Scan selbst besteht.
    def test_findet_private_adresse(self):
        self.assertEqual(self.scanne("url = http://192." + "168.1.5:8088"), ["private IP-Adresse"])
        self.assertEqual(self.scanne("10." + "0.0.7"), ["private IP-Adresse"])

    def test_findet_mdns_namen_und_mail(self):
        self.assertEqual(self.scanne("ssh kiste." + "local"), ["mDNS-Hostname"])
        self.assertEqual(self.scanne("kontakt: jemand" + "@beispiel.de"), ["E-Mail-Adresse"])

    def test_findet_persoenlichen_wert(self):
        self.assertEqual(self.scanne("Hallo Kim!", ["Kim"]), ["persönlicher Wert"])

    def test_laesst_sauberes_durch(self):
        sauber = ("Server auf http://127.0.0.1:8765, Ordner ~/.local/share, "
                  "Unit getty@tty2.service, font-family: system-ui, Version 2.4.0")
        self.assertEqual(self.scanne(sauber, ["Kim"]), [])

    def test_repository_ist_sauber(self):
        funde = pruefe_privat.pruefe(pruefe_privat.versionierte_dateien(), pruefe_privat.private_werte())
        self.assertEqual(funde, [], "private Daten gefunden (make check zeigt sie)")


if __name__ == "__main__":
    unittest.main()
