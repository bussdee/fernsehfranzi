"""5.0: Designs (hell/dunkel, Abend-Automatik), Wetter (Regeln wie im Familien Dashboard), Schule aus der Klassenkiste
(nur lesen, Meldungen, Morgen-Check), Kinderwelten (Familienfabrik, nur lesen) und Kinder-News (nur freigeschaltete Quellen)."""
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import design, kinderwelten, news, schule, wetter  # noqa: E402
from test_karaoke import kiosk_attrappe  # noqa: E402
from test_v3_server import MITTWOCH, Uhr, neuer_hub  # noqa: E402


class Designs(unittest.TestCase):
    def test_abends_wird_nur_hell_dunkel(self):
        d = {"abend_aktiv": True, "abend_ab": "19:00", "morgen_ab": "06:30"}
        self.assertEqual(design.jetzt_design(d, "hellblau", datetime(2026, 11, 18, 15, 0)), "hellblau")
        self.assertEqual(design.jetzt_design(d, "hellblau", datetime(2026, 11, 18, 19, 30)), "blau", "dunkle Schwester")
        self.assertEqual(design.jetzt_design(d, "rosa", datetime(2026, 11, 19, 6, 0)), "lila")
        self.assertEqual(design.jetzt_design(d, "rot", datetime(2026, 11, 18, 21, 0)), "rot", "dunkle Wahl bleibt")
        self.assertEqual(design.jetzt_design(d, "hellblau", datetime(2026, 11, 19, 6, 30)), "hellblau")
        self.assertEqual(design.jetzt_design({"erlaubt": ["mint"]}, "blau", datetime(2026, 11, 18, 12)), "mint",
                         "nicht (mehr) erlaubt: die erste erlaubte")

    def test_alte_namen(self):
        self.assertEqual(design.jetzt_design({}, "sonne", datetime(2026, 11, 18, 12)), "rot")
        einst = {"startseite": {"thema": "zuckerwatte"}, "design": {"erlaubt": ["weltall", "himmel"], "abend_design": "nacht"}}
        self.assertTrue(design.migriere(einst))
        self.assertEqual(einst, {"startseite": {"thema": "rosa"}, "design": {"erlaubt": ["blau", "hellblau"]}})
        self.assertFalse(design.migriere(einst), "nur einmal")

    def test_pruefen(self):
        for falsch in ({"erlaubt": []}, {"erlaubt": ["gibtsnicht"]}, {"abend_ab": "25:00"}, {"farbe": "rot"}):
            with self.assertRaises(ValueError, msg=falsch):
                design.pruefe(falsch)
        self.assertNotIn("abend_design", design.pruefe({"abend_design": "nacht"}), "Feld von 5.x wird still entfernt")

    def test_im_hub_kind_waehlt_nur_erlaubte(self):
        ordner = tempfile.mkdtemp(prefix="ff-50d-")
        self.addCleanup(shutil.rmtree, ordner, True)
        uhr = Uhr(MITTWOCH)
        hub = neuer_hub(ordner, uhr)
        hub.startseite_setzen({"lieblinge": [], "thema": "rosa"})
        a = hub.startseite_anzeige()
        self.assertEqual((a["design"]["jetzt"], a["design"]["hell"]), ("rosa", True))
        hub.einstellungen_aendern({"design": {"erlaubt": ["blau", "hellblau"], "abend_aktiv": True, "abend_ab": "18:00"}})
        with self.assertRaisesRegex(ValueError, "ausgeschaltet"):
            hub.startseite_setzen({"lieblinge": [], "thema": "mint"})
        hub.startseite_setzen({"lieblinge": ["spiel-snake"], "thema": "hellblau"})
        uhr.jetzt = datetime(2026, 11, 18, 18, 5)
        a = hub.startseite_anzeige()
        self.assertEqual((a["design"]["jetzt"], a["design"]["hell"], a["design"]["gewaehlt"]), ("blau", False, "hellblau"))
        self.assertEqual([x["id"] for x in a["design"]["designs"]], ["blau", "hellblau"])

    def test_alte_einstellungen_beim_start(self):
        ordner = tempfile.mkdtemp(prefix="ff-50m-")
        self.addCleanup(shutil.rmtree, ordner, True)
        with open(os.path.join(ordner, "einstellungen.json"), "w") as f:
            json.dump({"startseite": {"lieblinge": [], "thema": "sonne"}, "design": {"abend_design": "nacht", "abend_aktiv": True}}, f)
        hub = neuer_hub(ordner, Uhr(MITTWOCH))
        self.assertEqual(hub.einstellungen["startseite"]["thema"], "rot")
        self.assertNotIn("abend_design", hub.einstellungen["design"])

    def test_ansichten(self):
        ordner = tempfile.mkdtemp(prefix="ff-50a-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(MITTWOCH))
        self.assertEqual(hub.startseite_anzeige()["design"]["ansicht"], "konsole", "Vorgabe wie bisher")
        hub.startseite_setzen({"lieblinge": [], "thema": "blau", "ansicht": "karussell"})
        self.assertEqual(hub.startseite_anzeige()["design"]["ansicht"], "karussell")
        hub.einstellungen_aendern({"design": {"ansichten": ["konsole", "seitenleiste"]}})
        self.assertEqual(hub.startseite_anzeige()["design"]["ansicht"], "konsole", "nicht mehr erlaubt: die erste erlaubte")
        hub.startseite_setzen({"lieblinge": [], "thema": "blau", "ansicht": "seitenleiste"})
        with self.assertRaisesRegex(ValueError, "ausgeschaltet"):
            hub.startseite_setzen({"lieblinge": [], "thema": "blau", "ansicht": "karussell"})
        with self.assertRaises(ValueError):
            hub.einstellungen_aendern({"design": {"ansichten": []}})
        with self.assertRaises(ValueError):
            hub.einstellungen_aendern({"startseite": {"ansicht": "kreis"}})


def open_meteo(jetzt):
    """Kleine Antwort im Format von Open-Meteo: trocken bis 16:00, dann Regen bis 18:00."""
    tag = jetzt.date()
    stunden = [datetime(tag.year, tag.month, tag.day) + timedelta(hours=h) for h in range(48)]
    mm = [0.0] * 48
    for h in (16, 17):
        mm[h] = 1.2
    m15 = [datetime(tag.year, tag.month, tag.day) + timedelta(minutes=15 * i) for i in range(48 * 4)]
    m15_mm = [1.0 if 16 * 4 + 1 <= i < 18 * 4 else 0.0 for i in range(48 * 4)]
    f = "%Y-%m-%dT%H:%M"
    return {
        "current": {"temperature_2m": 6.4, "apparent_temperature": 3.1, "weather_code": 2, "wind_speed_10m": 12, "is_day": 1},
        "hourly": {"time": [s.strftime(f) for s in stunden], "temperature_2m": [6] * 48, "apparent_temperature": [3] * 48,
                   "precipitation": mm, "precipitation_probability": [80 if x else 10 for x in mm], "weather_code": [61 if x else 2 for x in mm],
                   "cloud_cover": [20] * 48, "wind_speed_10m": [10] * 48},
        "minutely_15": {"time": [s.strftime(f) for s in m15], "precipitation": m15_mm},
        "daily": {"time": [tag.isoformat(), (tag + timedelta(days=1)).isoformat()], "weather_code": [61, 2],
                  "temperature_2m_max": [7.2, 9], "temperature_2m_min": [1, 2], "precipitation_probability_max": [80, 10],
                  "sunrise": [tag.isoformat() + "T07:30", (tag + timedelta(days=1)).isoformat() + "T07:31"],
                  "sunset": [tag.isoformat() + "T16:30", (tag + timedelta(days=1)).isoformat() + "T16:29"]},
    }


class Wetter(unittest.TestCase):
    def test_regen_satz_viertelstunden(self):
        jetzt = datetime(2026, 11, 18, 14, 10)
        self.assertEqual(wetter.regen_satz(open_meteo(jetzt), jetzt)["text"], "Regen ab 16:15")
        waehrend = datetime(2026, 11, 18, 16, 40)
        r = wetter.regen_satz(open_meteo(waehrend), waehrend)
        self.assertTrue(r["nass"])
        self.assertEqual(r["text"], "Es regnet – trocken ab 18:00")

    def test_trockenfenster_nur_bei_tageslicht_und_ab_jetzt(self):
        jetzt = datetime(2026, 11, 18, 14, 10)
        d = wetter.auswerten(open_meteo(jetzt), jetzt)
        heute = d["tage"][0]["fenster"]
        self.assertEqual(len(heute), 1)
        self.assertTrue(heute[0]["jetzt"], "läuft gerade")
        self.assertEqual((heute[0]["von_text"], heute[0]["bis_text"]), ("14:10", "16:00"))
        morgen = d["tage"][1]["fenster"]
        self.assertEqual((morgen[0]["von_text"], morgen[0]["bis_text"]), ("07:31", "16:29"), "Sonnenauf- bis -untergang")
        self.assertIn("Jacke", d["anziehen"])
        self.assertIn("Regenjacke", d["anziehen"], "Regen in den nächsten Stunden")
        self.assertEqual(d["temp"], 6)

    def test_kurzes_fenster_zaehlt_nicht(self):
        jetzt = datetime(2026, 11, 18, 15, 10)            # bis 16:00 trocken = 50 min
        self.assertEqual(wetter.auswerten(open_meteo(jetzt), jetzt)["tage"][0]["fenster"], [])

    def test_pruefen_und_im_hub(self):
        with self.assertRaises(ValueError):
            wetter.pruefe({"aktiv": True})                 # ohne Ort
        with self.assertRaises(ValueError):
            wetter.pruefe({"ort": {"name": "X", "lat": 99, "lon": 0}})
        ordner = tempfile.mkdtemp(prefix="ff-50w-")
        self.addCleanup(shutil.rmtree, ordner, True)
        uhr = Uhr(datetime(2026, 11, 18, 14, 10))
        hub = neuer_hub(ordner, uhr)
        self.assertNotIn("spiel-wetter", [k["id"] for k in hub.kacheln()], "aus: keine Kachel")
        hub.einstellungen_aendern({"wetter": {"aktiv": True, "ort": {"name": "Musterstadt", "lat": 50.1, "lon": 8.6}}})
        self.assertIn("spiel-wetter", [k["id"] for k in hub.kacheln()])
        self.assertIn("latitude=50.1000", hub.wetter.adresse({"lat": 50.1, "lon": 8.6}))
        hub.wetter.roh, hub.wetter._ort, hub.wetter.geholt = open_meteo(uhr()), {"name": "Musterstadt", "lat": 50.1, "lon": 8.6}, \
            __import__("time").time()
        t = hub.wetter.fuer_tv()
        self.assertEqual(t["daten"]["regen"]["text"], "Regen ab 16:15")
        self.assertEqual(t["ort"], "Musterstadt")


class Klassenkiste(BaseHTTPRequestHandler):
    anfragen = []
    hausaufgaben = []
    nachrichten = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        Klassenkiste.anfragen.append((self.command, self.path))
        if self.headers.get("Cookie") != "PHPSESSID=kind123":
            self.send_response(401)
            self.end_headers()
            return
        weg = self.path.split("?")[0]
        if weg == "/api/overview":
            daten = {"role": "student", "unread_messenger": 0,
                     "today_lessons": [{"period": 1, "subject": "Deutsch", "room": "12", "start": "08:00", "end": "08:45",
                                        "cancelled": False, "changed": False},
                                       {"period": 6, "subject": "Kunst", "room": "", "start": "12:30", "end": "13:15",
                                        "cancelled": True, "changed": False}],
                     "today_free": [],
                     "next_events": [{"title": "Wandertag", "event_date": "2026-11-20", "event_time": None, "class_name": "3b"}]}
        elif weg == "/api/homework/mine":
            daten = Klassenkiste.hausaufgaben
        elif weg == "/api/messages":
            daten = Klassenkiste.nachrichten
        elif weg == "/api/timetable":
            daten = {"week_start": "2026-11-16", "classes": [{
                "class_name": "3b", "lesson_times": {"1": {"start": "08:00", "end": "08:45"}},
                "slots": [{"weekday": 4, "period": 1, "subject": "Sport", "room": "Halle"},
                          {"weekday": 4, "period": 2, "subject": "Mathe", "room": "12"}],
                "overrides": [{"override_date": "2026-11-19", "period": 2, "kind": "cancelled"}], "closures": []}]}
        else:
            self.send_response(404)
            self.end_headers()
            return
        inhalt = json.dumps(daten).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(inhalt)))
        self.end_headers()
        self.wfile.write(inhalt)

    def do_POST(self):
        Klassenkiste.anfragen.append(("POST", self.path))
        self.send_response(405)
        self.end_headers()


class Schule(unittest.TestCase):
    def setUp(self):
        self.kk = ThreadingHTTPServer(("127.0.0.1", 0), Klassenkiste)
        threading.Thread(target=self.kk.serve_forever, daemon=True).start()
        self.addCleanup(self.kk.server_close)
        self.addCleanup(self.kk.shutdown)
        Klassenkiste.anfragen = []
        Klassenkiste.hausaufgaben = [
            {"id": "h1", "subject": "Mathe", "title": "Seite 12", "description": "Nr. 1-3", "due_date": "2026-11-19", "class_name": "3b"},
            {"id": "h0", "subject": "Deutsch", "title": "Alt", "due_date": "2026-11-10"},                      # überfällig
            {"id": "h9", "subject": "Sachkunde", "title": "Fertig", "due_date": "2026-11-25", "completed_at": "2026-11-17"}]
        Klassenkiste.nachrichten = [{"id": "m1", "title": "Elternabend", "body": "<b>Am</b> Montag\num 19 Uhr", "author_name": "Frau Lehrerin",
                                     "class_name": "3b", "created_at": "2026-11-17 10:00:00", "pinned": 0}]
        self.ordner = tempfile.mkdtemp(prefix="ff-50s-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.uhr = Uhr(MITTWOCH)
        self.hub = neuer_hub(self.ordner, self.uhr)
        apps = self.hub.eltern_daten()["apps"]
        next(a for a in apps if a["id"] == "klassenkiste")["start"] = "http://127.0.0.1:%d/" % self.kk.server_address[1]
        self.hub.katalog_aendern(apps)
        self.stopp = threading.Event()
        self.addCleanup(self.stopp.set)
        threading.Thread(target=kiosk_attrappe, args=(self.hub, self.stopp), daemon=True).start()
        self.telegram = []
        self.hub.telegram.melde_eltern = lambda art, text: self.telegram.append((art, text))

    def test_aus_keine_kachel_und_kein_abruf(self):
        self.assertNotIn("spiel-schule", [k["id"] for k in self.hub.kacheln()])
        self.hub.schule.tick(self.uhr(), gleich=True)
        self.assertEqual(Klassenkiste.anfragen, [])

    def test_lesen_melden_und_morgen_check(self):
        self.hub.einstellungen_aendern({"schule": {"aktiv": True}})
        self.assertIn("spiel-schule", [k["id"] for k in self.hub.kacheln()])
        self.hub.schule.tick(self.uhr(), gleich=True)
        st = self.hub.schule.fuer_tv()["stand"]
        self.assertEqual([h["id"] for h in st["hausaufgaben"]], ["h1"], "ohne überfällige und erledigte")
        self.assertTrue(st["hausaufgaben"][0]["bis_morgen"])
        self.assertEqual(st["nachrichten"][0]["text"], "Am Montag\num 19 Uhr", "ohne HTML")
        self.assertTrue(st["stunden"][1]["faellt_aus"])
        self.assertEqual(st["termine"][0]["tag_text"], "Freitag")
        self.assertEqual([s["fach"] for s in st["morgen"]["stunden"]], ["Sport", "Mathe"])
        self.assertIn("1. Stunde Sport um 08:00", st["morgen"]["satz"])
        self.assertIn("Hausaufgaben bis dahin: Mathe", st["morgen"]["satz"])
        self.assertEqual(self.hub.familie.offene_meldungen(), [], "erster Abruf: nur merken")
        self.assertTrue(all(m == "GET" for m, _ in Klassenkiste.anfragen), "nur lesen")
        # Neues kommt dazu -> genau einmal gemeldet
        Klassenkiste.hausaufgaben.append({"id": "h2", "subject": "Englisch", "title": "Vokabeln", "due_date": "2026-11-24"})
        self.hub.schule.holen()
        meldungen = self.hub.familie.offene_meldungen()
        self.assertEqual(len(meldungen), 1)
        self.assertIn("Neue Hausaufgabe in Englisch: Vokabeln", meldungen[0]["text"])
        self.assertEqual(self.telegram[0][0], "schule")
        self.hub.schule.holen()
        self.assertEqual(len(self.hub.familie.offene_meldungen()), 1, "nicht doppelt")
        # Morgen-Check um 18:00 (Vorgabe), nur einmal
        self.uhr.jetzt = datetime(2026, 11, 18, 18, 1)
        self.hub.schule._morgen_check(self.uhr())
        self.hub.schule._morgen_check(self.uhr())
        texte = [m["text"] for m in self.hub.familie.offene_meldungen()]
        self.assertEqual(sum("Sport" in t for t in texte), 1)
        self.assertNotIn("PHPSESSID", json.dumps(self.hub.eltern_daten()))

    def test_ferien_kein_morgen_check(self):
        self.hub.einstellungen_aendern({"schule": {"aktiv": True}, "zeit": {"ferien": [["2026-11-19", "2026-11-20"]]}})
        self.hub.schule.holen()
        self.assertEqual(self.hub.schule.stand["morgen"]["datum"], "2026-11-23", "nächster Schultag nach den Ferien")
        self.uhr.jetzt = datetime(2026, 11, 18, 18, 1)
        self.hub.schule._morgen_check(self.uhr())
        self.assertEqual(self.hub.familie.offene_meldungen(), [], "morgen ist kein Schultag")

    def test_pruefen(self):
        for falsch in ({"aktiv": "ja"}, {"morgen_check_um": "7 Uhr"}, {"x": 1}):
            with self.assertRaises(ValueError):
                schule.pruefe(falsch)


class Kinderwelten(unittest.TestCase):
    DATEN = {
        "/geschichten?kinder=1&anzahl=100": {"eintraege": [
            {"adresse": "apfelkuchen", "titel": "Das Geheimnis", "reihe": "BausL", "lesezeit": 6,
             "bild": {"url": "https://familienfabrik.at/bilder/2026/08/ca3abfdd8bfd5516.webp"}},
            {"adresse": "../boese", "titel": "x"}, {"adresse": "fremd", "titel": "y", "bild": {"url": "https://boese.example/x.png"}}]},
        "/geschichte/apfelkuchen": {"titel": "Das Geheimnis",
                                    "text": "<h2>Kapitel</h2><p>Es war <b>einmal</b>.</p><script>alert(1)</script><ul><li>Eins</li></ul>"},
        "/tagesinhalte": {"sprueche": ["Moin!"], "raetsel": [{"frage": "Was wird nass?", "antworten": ["handtuch"], "tipp": "🛁"}]},
    }

    def setUp(self):
        ordner = tempfile.mkdtemp(prefix="ff-50k-")
        self.addCleanup(shutil.rmtree, ordner, True)
        self.hub = neuer_hub(ordner, Uhr(MITTWOCH))
        self.abrufe = []

        def holer(weg):
            self.abrufe.append(weg)
            if weg not in self.DATEN:
                raise OSError("nicht da")
            return self.DATEN[weg]
        self.hub.kinderwelten = kinderwelten.Kinderwelten(self.hub, holer=holer)

    def test_aus_und_an(self):
        self.assertNotIn("spiel-kinderwelten", [k["id"] for k in self.hub.kacheln()])
        with self.assertRaisesRegex(ValueError, "ausgeschaltet"):
            self.hub.kinderwelten.geschichten()
        self.hub.einstellungen_aendern({"kinderwelten": {"aktiv": True, "raetsel": False}})
        self.assertIn("spiel-kinderwelten", [k["id"] for k in self.hub.kacheln()])
        self.assertNotIn("raetsel", self.hub.kinderwelten.uebersicht()["teile"])
        g = self.hub.kinderwelten.geschichten()
        self.assertEqual([x["adresse"] for x in g], ["apfelkuchen", "fremd"])
        self.assertEqual(g[0]["bild"], "/api/kinderwelten/bild?u=2026%2F08%2Fca3abfdd8bfd5516.webp")
        self.assertIsNone(g[1]["bild"], "fremde Bilder nie")
        self.hub.kinderwelten.geschichten()
        self.assertEqual(self.abrufe.count("/geschichten?kinder=1&anzahl=100"), 1, "zwischengespeichert")

    def test_text_ohne_html(self):
        self.hub.einstellungen_aendern({"kinderwelten": {"aktiv": True}})
        b = self.hub.kinderwelten.geschichte("apfelkuchen")["bloecke"]
        self.assertEqual(b, [{"art": "h", "text": "Kapitel"}, {"art": "p", "text": "Es war einmal."}, {"art": "li", "text": "Eins"}])
        with self.assertRaises(ValueError):
            self.hub.kinderwelten.geschichte("../etc")
        with self.assertRaises(ValueError):
            kinderwelten.bild_adresse("../../geheim.php")
        self.assertTrue(kinderwelten.bild_adresse("2026/08/abc.webp").startswith("https://familienfabrik.at/bilder/"))

    def test_raetsel_des_tages(self):
        self.hub.einstellungen_aendern({"kinderwelten": {"aktiv": True}})
        r = self.hub.kinderwelten.raetsel(MITTWOCH.date())
        self.assertEqual((r["spruch"], r["raetsel"]["antwort"]), ("Moin!", "Handtuch"))


RSS = b"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>T</title>
<item><title>Neue &amp; gute Nachricht</title><description>&lt;p&gt;Text mit &lt;a href="x"&gt;Link&lt;/a&gt;&lt;/p&gt;</description>
<pubDate>Sun, 22 Nov 2026 10:00:00 +0100</pubDate></item>
<item><title>Aeltere</title><pubDate>Fri, 20 Nov 2026 10:00:00 +0100</pubDate></item></channel></rss>"""


class YoutubeKategorien(unittest.TestCase):
    def test_kategorie_voruebergehend_aus(self):
        ordner = tempfile.mkdtemp(prefix="ff-60y-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(MITTWOCH))
        video = {"art": "video", "id": "aaaaaaaaaaa", "titel": "Pinguine"}
        hub.einstellungen_aendern({"youtube": {"kategorien": [{"name": "Tiere", "eintraege": [video]},
                                                              {"name": "Musik", "eintraege": [video], "aktiv": False}]}})
        self.assertEqual([k["name"] for k in hub.youtube_fuer_tv()["kategorien"]], ["Tiere"], "aus = am Fernseher unsichtbar")
        self.assertEqual(len(hub.youtube()["kategorien"]), 2, "bleibt gespeichert")
        with self.assertRaises(ValueError):
            hub.einstellungen_aendern({"youtube": {"kategorien": [{"name": "X", "eintraege": [], "aktiv": "nein"}]}})

    def test_reihenfolge_bleibt(self):
        ordner = tempfile.mkdtemp(prefix="ff-60r-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(MITTWOCH))
        v = lambda i, t: {"art": "video", "id": i * 11, "titel": t}
        hub.einstellungen_aendern({"youtube": {"kategorien": [
            {"name": "Musik", "eintraege": [v("c", "Drei"), v("a", "Eins"), v("b", "Zwei")]}, {"name": "Tiere", "eintraege": []}]}})
        tv = hub.youtube_fuer_tv()["kategorien"]
        self.assertEqual([k["name"] for k in tv], ["Musik", "Tiere"], "Kategorien in der Reihenfolge der Eltern")
        self.assertEqual([e["titel"] for e in tv[0]["eintraege"]], ["Drei", "Eins", "Zwei"], "Videos in der Reihenfolge der Eltern")


class KinderNews(unittest.TestCase):
    def test_nur_eingetragene_rss_adressen(self):
        ordner = tempfile.mkdtemp(prefix="ff-50n-")
        self.addCleanup(shutil.rmtree, ordner, True)
        hub = neuer_hub(ordner, Uhr(MITTWOCH))
        geholt = []
        hub.news = news.News(hub, holer=lambda url: geholt.append(url) or RSS)
        self.assertFalse(hub.news.aktiv(), "ab Werk keine Adresse")
        self.assertFalse(hasattr(news, "QUELLEN"), "keine fest eingebauten Quellen")
        self.assertNotIn("spiel-news", [k["id"] for k in hub.kacheln()])
        with self.assertRaises(ValueError):
            hub.news.liste()
        for falsch in ({"quellen": {"logo": True}}, {"feeds": ["ftp://x.de/rss"]}, {"feeds": ["kein link"]},
                       {"feeds": ["https://a.de/%d" % i for i in range(11)]}):
            with self.assertRaises(ValueError):
                hub.einstellungen_aendern({"news": falsch})
        self.assertEqual(news.einstellungen({"quellen": {"logo": True}}), {"feeds": []}, "alter Stand wird still verworfen")
        hub.einstellungen_aendern({"news": {"feeds": ["https://www.beispiel.de/feed", "https://www.beispiel.de/feed"]}})
        self.assertEqual(hub.news.fuer_eltern(), {"feeds": ["https://www.beispiel.de/feed"]}, "doppelte fallen weg")
        self.assertIn("spiel-news", [k["id"] for k in hub.kacheln()])
        l = hub.news.liste()
        self.assertEqual(geholt, ["https://www.beispiel.de/feed"])
        self.assertEqual(l["eintraege"][0]["titel"], "Neue & gute Nachricht")
        self.assertEqual(l["eintraege"][0]["text"], "Text mit Link", "ohne HTML und ohne Links")
        self.assertEqual(l["eintraege"][0]["datum"], "22.11.")


if __name__ == "__main__":
    unittest.main()
