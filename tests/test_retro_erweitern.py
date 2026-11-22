"""werkzeuge/retro_erweitern.sh: der Feinschliff-Teil, der auf dem Pi läuft - hier in einem Schein-HOME ausgeführt.

4.1.1: Amiga-CD32-Spiele lagen als ZIP vor; Amiberry liest CDs nicht aus ZIPs. Sie werden entpackt, die .cue zeigt auf
die Spuren in .cd32/<Spiel>/, das ZIP wandert ins Archiv, und runcommand startet das Spiel fest als CD32.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def remote_skript():
    with open(os.path.join(REPO, "werkzeuge", "retro_erweitern.sh"), encoding="utf-8") as f:
        return re.search(r"EINRICHTEN_REMOTE='(.*?)\n'\n", f.read(), re.S).group(1)


@unittest.skipUnless(shutil.which("unzip"), "unzip fehlt")
class Einrichten(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="ff-retro-")
        self.addCleanup(shutil.rmtree, self.home, True)
        self.roms = os.path.join(self.home, "RetroPie", "roms", "amiga")
        os.makedirs(self.roms)
        self.bios = os.path.join(self.home, "RetroPie", "BIOS", "amiga")
        os.makedirs(self.bios)
        with zipfile.ZipFile(os.path.join(self.roms, "AmigaCD32_DerClou.zip"), "w") as z:   # wie am Gerät: Ordner + Cover
            z.writestr("Amiga CD32 - Der Clou/Der Clou.cue", 'FILE "Der Clou.img" BINARY\r\n  TRACK 01 MODE1/2352\r\n')
            z.writestr("Amiga CD32 - Der Clou/Der Clou.img", b"\0" * 64)
            z.writestr("Amiga CD32 - Der Clou/Cover/Der Clou-Cover.jpg", b"jpg")
        with zipfile.ZipFile(os.path.join(self.roms, "Pizzaconnection.zip"), "w") as z:    # Disketten bleiben ZIP
            z.writestr("Pizza Connection Disk1.adf", b"\0" * 16)
        self.emu = os.path.join(self.home, "emulators.cfg")
        self.opt = os.path.join(self.home, "core-options.cfg")

    def lauf(self, modus):
        return subprocess.run(["bash", "-c", remote_skript(), "-", modus], capture_output=True, text=True,
                              env=dict(os.environ, HOME=self.home, EMU_CFG=self.emu, RA_OPT=self.opt))

    def cd32_roms(self):
        for name in ("CD32 Kickstart 3.1 (40.060).rom", "CD32 Extended-ROM (40.060).rom"):
            open(os.path.join(self.bios, name), "wb").close()

    def test_ohne_cd32_roms_bleibt_alles(self):
        e = self.lauf("los")
        self.assertEqual(e.returncode, 0, e.stderr)
        self.assertIn("CD32-Spiele bleiben unverändert", e.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.roms, "AmigaCD32_DerClou.zip")))
        self.assertFalse(os.path.exists(os.path.join(self.roms, ".cd32")))

    def test_plan_aendert_nichts(self):
        self.cd32_roms()
        e = self.lauf("plan")
        self.assertEqual(e.returncode, 0, e.stderr)
        self.assertIn("CD32: DerClou entpacken", e.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.roms, "AmigaCD32_DerClou.zip")))
        self.assertFalse(os.path.exists(self.emu))

    def test_cd32_entpacken_und_fest_als_cd32(self):
        self.cd32_roms()
        for _ in range(2):                                         # zweiter Lauf ändert nichts
            e = self.lauf("los")
            self.assertEqual(e.returncode, 0, e.stderr + e.stdout)
        cue = os.path.join(self.roms, "DerClou (CD32).cue")
        with open(cue, encoding="utf-8", newline="") as f:
            self.assertEqual(f.read().splitlines()[0], 'FILE ".cd32/DerClou/Der Clou.img" BINARY')
        self.assertTrue(os.path.isfile(os.path.join(self.roms, ".cd32", "DerClou", "Der Clou.img")))
        self.assertFalse(os.path.exists(os.path.join(self.roms, ".cd32", "DerClou", "Der Clou-Cover.jpg")))
        self.assertFalse(os.path.exists(os.path.join(self.roms, "AmigaCD32_DerClou.zip")))
        self.assertTrue(os.path.isfile(os.path.join(self.home, "RetroPie", "roms-archiv", "amiga", "AmigaCD32_DerClou.zip")))
        self.assertTrue(os.path.isfile(os.path.join(self.roms, "Pizzaconnection.zip")), "Disketten-ZIP bleibt")
        with open(self.emu) as f:
            self.assertEqual(f.read(), 'amiga_DerClouCD32 = "amiberry-cd32"\n')   # Schlüssel wie runcommand (clean_name)
        self.assertNotIn("entpacken", e.stdout, "zweiter Lauf: nichts mehr zu tun")

    def test_c64_tasten_wie_in_der_kinder_anleitung(self):
        with open(self.opt, "w") as f:
            f.write('vice_mapper_x = "RETROK_SPACE"\nvice_mapper_a = "---"\nvice_mapper_start = "---"')
        for _ in range(2):
            self.assertEqual(self.lauf("los").returncode, 0)
        with open(self.opt) as f:
            zeilen = f.read().splitlines()
        for erwartet in ('vice_mapper_a = "JOYSTICK_FIRE"', 'vice_mapper_y = "RETROK_SPACE"', 'vice_mapper_start = "RETROK_F1"',
                         'vice_mapper_l = "SWITCH_JOYPORT"', 'vice_autoloadwarp = "enabled"', 'vice_mapper_x = "RETROK_SPACE"'):
            self.assertEqual(zeilen.count(erwartet), 1, erwartet)
        with open(os.path.join(REPO, "docs", "anleitung", "kinder.html"), encoding="utf-8") as f:
            anleitung = f.read()
        self.assertIn('<span class="taste">A</span> = Feuer', anleitung)


if __name__ == "__main__":
    unittest.main()
