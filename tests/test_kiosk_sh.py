"""familyhub/kiosk.sh: lädt sich nach einem Update selbst neu (ohne Geräte-Neustart).

Am 21.11. lief Chromium nach zwei Deploys noch mit den alten Schaltern, weil die
kiosk.sh-Schleife erst beim Neustart des Geräts neu gelesen wurde.
"""
import os
import shutil
import subprocess
import tempfile
import time
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class KioskNeuLaden(unittest.TestCase):
    def test_neue_kiosk_sh_wird_nach_chromium_ende_geladen(self):
        ordner = tempfile.mkdtemp(prefix="ff-kiosk-")
        self.addCleanup(shutil.rmtree, ordner, True)
        bin_ = os.path.join(ordner, "bin")
        os.makedirs(bin_)
        with open(os.path.join(bin_, "chromium"), "w") as f:   # Attrappe: endet nach 1 s
            f.write("#!/bin/sh\necho \"$@\" >> \"$(dirname \"$0\")/../aufrufe\"\nsleep 1\n")
        os.chmod(os.path.join(bin_, "chromium"), 0o755)
        kiosk = os.path.join(ordner, "kiosk.sh")
        shutil.copy(os.path.join(REPO, "familyhub", "kiosk.sh"), kiosk)
        os.chmod(kiosk, 0o755)
        umgebung = dict(os.environ, PATH=bin_ + os.pathsep + os.environ["PATH"])
        prozess = subprocess.Popen([kiosk], env=umgebung, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(prozess.kill)
        time.sleep(4.5)                                   # sleep 3 + erster Chromium-Lauf
        with open(kiosk, encoding="utf-8") as f:
            neu = f.read().replace("--enable-spatial-navigation", "--enable-spatial-navigation --NEUER-SCHALTER")
        os.remove(kiosk)                                  # wie rsync: neue Datei
        with open(kiosk, "w", encoding="utf-8") as f:
            f.write(neu)
        os.chmod(kiosk, 0o755)
        os.utime(kiosk, (time.time() + 5, time.time() + 5))
        frist = time.time() + 20
        aufrufe = ""
        while time.time() < frist and "--NEUER-SCHALTER" not in aufrufe:
            time.sleep(0.5)
            with open(os.path.join(ordner, "aufrufe")) as f:
                aufrufe = f.read()
        self.assertIn("--NEUER-SCHALTER", aufrufe)
        with open(os.path.join(ordner, "logs", "kiosk.log")) as f:
            self.assertIn("kiosk.sh wurde aktualisiert - lade neu.", f.read())


if __name__ == "__main__":
    unittest.main()
