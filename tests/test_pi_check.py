"""Vergleichslogik von werkzeuge/pi_check.py – grüner und roter Fall."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "werkzeuge"))
import pi_check  # noqa: E402

VOR = {
    "host": "nutzer@geraet", "pfad": "~/familyhub", "zeit": "2026-11-20T19:00:00",
    "boot_id": "a", "uptime_s": 100.0,
    "dienste": {"familyhub-server.service": "active", "familyhub-cec.service": "active",
                "fernsehfranzi-retropie.service": "inactive"},
    "fehlgeschlagen": [], "ports": ["0.0.0.0:22", "127.0.0.1:8765"],
    "speicher_verfuegbar_mib": 400, "platte_frei_mib": 40000, "version": "2.4.0", "hub_ordner": True,
    "server_status": '{"running": false, "pid": null}', "cec_client_anzahl": 1, "chromium_laeuft": True,
}


def stufen(punkte):
    return [s for s, _ in punkte]


class Nach(unittest.TestCase):
    def test_unveraendert_ist_gruen(self):
        punkte = pi_check.pruefe_nach(VOR, copy.deepcopy(VOR), "2.4.0")
        self.assertNotIn("rot", stufen(punkte))

    def test_dienst_ausgefallen_ist_rot(self):
        nach = copy.deepcopy(VOR)
        nach["dienste"]["familyhub-server.service"] = "failed"
        nach["fehlgeschlagen"] = ["familyhub-server.service"]
        punkte = pi_check.pruefe_nach(VOR, nach)
        self.assertEqual(stufen(punkte).count("rot"), 2)

    def test_neuer_port_nur_angemeldet_gruen(self):
        nach = copy.deepcopy(VOR)
        nach["ports"].append("0.0.0.0:8766")
        self.assertIn("rot", stufen(pi_check.pruefe_nach(VOR, nach)))
        self.assertNotIn("rot", stufen(pi_check.pruefe_nach(VOR, nach, neue_ports={"0.0.0.0:8766"})))

    def test_verschwundener_port_ist_rot(self):
        nach = copy.deepcopy(VOR)
        nach["ports"] = ["0.0.0.0:22"]
        self.assertIn("rot", stufen(pi_check.pruefe_nach(VOR, nach)))

    def test_falsche_version_und_neustart(self):
        nach = copy.deepcopy(VOR)
        nach["version"] = "2.3.0"
        self.assertIn("rot", stufen(pi_check.pruefe_nach(VOR, nach, "2.4.0")))
        nach = copy.deepcopy(VOR)
        nach["boot_id"] = "b"
        self.assertIn("rot", stufen(pi_check.pruefe_nach(VOR, nach)))
        self.assertNotIn("rot", stufen(pi_check.pruefe_nach(VOR, nach, neustart_erlaubt=True)))

    def test_server_antwortet_nicht_mehr(self):
        nach = copy.deepcopy(VOR)
        nach["server_status"] = None
        self.assertIn("rot", stufen(pi_check.pruefe_nach(VOR, nach)))

    def test_zwei_cec_clients_rot(self):
        nach = copy.deepcopy(VOR)
        nach["cec_client_anzahl"] = 2
        self.assertIn("rot", stufen(pi_check.pruefe_nach(VOR, nach)))


class Vor(unittest.TestCase):
    def test_gruen(self):
        self.assertNotIn("rot", stufen(pi_check.pruefe_vor(VOR)))

    def test_zu_wenig_speicher_rot(self):
        z = dict(VOR, speicher_verfuegbar_mib=100)
        self.assertIn("rot", stufen(pi_check.pruefe_vor(z)))


if __name__ == "__main__":
    unittest.main()
