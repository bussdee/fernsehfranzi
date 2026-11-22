"""install/install.sh: Teilstücke unter denselben Shell-Regeln wie auf dem Gerät (set -euo pipefail).

Am 21.11. brach install.sh beim Erzeugen des Entsperr-Codes ab (tr | head unter pipefail).
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def teil(anfang, ende="^fi$"):
    with open(os.path.join(REPO, "install", "install.sh"), encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"(?ms)^%s.*?%s" % (anfang, ende), text)
    return m.group(0)


class InstallSh(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-install-")
        self.addCleanup(shutil.rmtree, self.ordner, True)

    def lauf(self, skript, **umgebung):
        hilfen = teil(r"ohne_nullbytes\(\) \{", "^}$")
        voll = "set -euo pipefail\nBENUTZER=$(id -un)\n%s\n%s\necho FERTIG\n" % (hilfen, skript)
        return subprocess.run(["bash", "-c", voll], capture_output=True, text=True,
                              env=dict(os.environ, **umgebung))

    def test_es_kiosk_und_entsperrcode_unter_pipefail(self):
        datei = os.path.join(self.ordner, "es_settings.cfg")
        with open(datei, "w") as f:
            f.write('<?xml version="1.0"?>\n<config>\n<string name="UIMode" value="Full" />\n'
                    '<string name="UIMode_passkey" value="uuddlrlrba" />\n</config>\n')
        ergebnis = self.lauf(teil(r'if \[ -f "\$ES_SETTINGS" \]; then'), ES_SETTINGS=datei)
        self.assertIn("FERTIG", ergebnis.stdout, ergebnis.stderr)
        with open(datei) as f:
            inhalt = f.read()
        self.assertIn('name="UIMode" value="Kiosk"', inhalt)
        code = re.search(r'name="UIMode_passkey" value="([^"]*)"', inhalt).group(1)
        self.assertRegex(code, r"^[udlrab]{10}$")
        self.assertNotEqual(code, "uuddlrlrba")
        # zweiter Lauf: Code bleibt (idempotent)
        self.lauf(teil(r'if \[ -f "\$ES_SETTINGS" \]; then'), ES_SETTINGS=datei)
        with open(datei) as f:
            self.assertIn(code, f.read())

    def test_n64_einstellungen_ersetzen_und_ergaenzen(self):
        datei = os.path.join(self.ordner, "retroarch-core-options.cfg")
        with open(datei, "w") as f:
            f.write('mupen64plus-next-aspect = "4:3"\nmupen64plus-next-EnableCopyColorToRDRAM = "Sync"\n'
                    'mupen64plus-next-EnableCopyDepthToRDRAM = "Software"')          # ohne Zeilenende am Schluss
        for _ in range(2):                                                      # zweimal: idempotent
            ergebnis = self.lauf(teil(r'if \[ -f "\$RA_KERN" \]; then'), RA_KERN=datei, CODE=REPO)
            self.assertIn("FERTIG", ergebnis.stdout, ergebnis.stderr)
        with open(datei) as f:
            zeilen = f.read().splitlines()
        self.assertEqual(zeilen, ['mupen64plus-next-aspect = "4:3"', 'mupen64plus-next-EnableCopyColorToRDRAM = "Async"',
                                  'mupen64plus-next-EnableCopyDepthToRDRAM = "Off"', 'mupen64plus-next-FrameDuping = "True"'])

    def test_rollback_kennt_die_neuen_dateien(self):
        with open(os.path.join(REPO, "install", "rollback.sh"), encoding="utf-8") as f:
            rueck = f.read()
        for muster in ("neu.txt", "/etc/udev/hwdb.d/", ".config/labwc/rc.xml", "/etc/NetworkManager/conf.d/",
                       "retroarch-core-options.cfg", "systemd-hwdb update"):
            self.assertIn(muster, rueck)

    def test_keine_pipe_mit_head_auf_urandom(self):
        with open(os.path.join(REPO, "install", "install.sh"), encoding="utf-8") as f:
            for nr, zeile in enumerate(f, 1):
                if not zeile.lstrip().startswith("#"):
                    self.assertNotRegex(zeile, r"/dev/urandom\s*\|", "Zeile %d: SIGPIPE unter pipefail" % nr)


if __name__ == "__main__":
    unittest.main()
