"""3.5 YouTube-Bereich: Links lesen, Kategorien prüfen, Whitelist/CSP - und der Player im Browser (mit YouTube-Attrappe:
Fokus nie im Video, Pause und Ende verdeckt, danach das nächste Video)."""
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.request
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from fernsehfranzi import web, youtube  # noqa: E402
from test_spiele_wie_am_geraet import port_frei  # noqa: E402
from test_v3_server import Uhr, neuer_hub  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

NACHMITTAG = datetime(2026, 11, 18, 15, 0)

# Nachgebaute IFrame-API: legt ein iframe an, meldet Zustände, merkt sich Befehle
YT_ATTRAPPE = """
window.__yt = { befehle: [], spieler: null };
window.YT = { PlayerState: { ENDED: 0, PLAYING: 1, PAUSED: 2, BUFFERING: 3 },
  Player: function (ziel, opt) {
    const f = document.createElement('iframe'); f.id = typeof ziel === 'string' ? ziel : ziel.id; f.src = 'about:blank';
    (typeof ziel === 'string' ? document.getElementById(ziel) : ziel).replaceWith(f);
    const self = this; let zustand = -1; window.__yt.spieler = self; window.__yt.opt = opt;
    const melde = (s) => { zustand = s; opt.events.onStateChange({ data: s, target: self }); };
    this.getIframe = () => f; this.getPlayerState = () => zustand; this.getCurrentTime = () => 20;
    this.playVideo = () => { window.__yt.befehle.push('play'); melde(1); };
    this.pauseVideo = () => { window.__yt.befehle.push('pause'); melde(2); };
    this.seekTo = (s) => window.__yt.befehle.push('seek ' + s);
    this.destroy = () => { window.__yt.befehle.push('destroy'); f.remove(); };
    this.getVideoData = () => ({ title: 'Titel' });
    this.getPlaybackQuality = () => 'hd720';
    this.unloadModule = (m) => window.__yt.befehle.push('aus ' + m);
    this.loadModule = (m) => window.__yt.befehle.push('an ' + m);
    this.setOption = () => {};
    this.ende = () => melde(0);
    setTimeout(() => opt.events.onReady({ target: self }), 10);
  } };
setTimeout(() => window.onYouTubeIframeAPIReady && window.onYouTubeIframeAPIReady(), 0);
"""


class Links(unittest.TestCase):
    def test_link_lesen(self):
        for link, erwartet in (
                ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", ("video", "dQw4w9WgXcQ")),
                ("https://youtu.be/dQw4w9WgXcQ?t=10", ("video", "dQw4w9WgXcQ")),
                ("https://www.youtube.com/shorts/dQw4w9WgXcQ", ("video", "dQw4w9WgXcQ")),
                ("https://www.youtube.com/playlist?list=PLabcdefghijk", ("playlist", "PLabcdefghijk")),
                ("https://m.youtube.com/watch?v=dQw4w9WgXcQ&list=PLabcdefghijk", ("video", "dQw4w9WgXcQ"))):
            self.assertEqual(youtube.link_lesen(link), erwartet, link)
        for falsch in ("https://vimeo.com/123", "https://www.youtube.com/@kanal", "javascript:alert(1)"):
            with self.assertRaises(ValueError):
                youtube.link_lesen(falsch)

    def test_playlist_auslesen(self):
        import io
        html = ('{"playlistVideoRenderer":{"videoId":"aaaaaaaaaaa","x":1} ... {"playlistVideoRenderer":{"videoId":"bbbbbbbbbbb"}'
                ' {"playlistVideoRenderer":{"videoId":"aaaaaaaaaaa"} "videoId":"zzzzzzzzzzz"')
        gesehen = []
        def oeffne(anfrage, timeout):
            gesehen.append(anfrage.full_url)
            return io.BytesIO(html.encode())
        self.assertEqual(youtube.playlist_videos("PLabcdefghijk", oeffne), ["aaaaaaaaaaa", "bbbbbbbbbbb"])
        self.assertTrue(gesehen[0].startswith("https://www.youtube.com/playlist?list=PLabcdefghijk"))

    def test_kategorien_pruefen(self):
        youtube.pruefe({"kategorien": [{"name": "Musik", "eintraege": [{"art": "video", "id": "dQw4w9WgXcQ", "titel": "x"}]}]})
        for falsch in ({"kategorien": [{"name": "", "eintraege": []}]},
                       {"kategorien": [{"name": "A", "eintraege": [{"art": "video", "id": "zu-kurz", "titel": "x"}]}]},
                       {"kategorien": [{"name": "A", "eintraege": [{"art": "video", "id": "dQw4w9WgXcQ", "bild": "https://boese.example/x.jpg"}]}]}):
            with self.assertRaises(ValueError):
                youtube.pruefe(falsch)


class Hub(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="ff-yt-")
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.hub = neuer_hub(self.ordner, Uhr(NACHMITTAG))
        alt, youtube.titel_holen = youtube.titel_holen, lambda art, k: ("Titel " + k, "https://i.ytimg.com/vi/%s/hqdefault.jpg" % k)
        self.addCleanup(setattr, youtube, "titel_holen", alt)
        alt2, youtube.playlist_videos = youtube.playlist_videos, lambda k: ["aaaaaaaaaaa", "bbbbbbbbbbb"]
        self.addCleanup(setattr, youtube, "playlist_videos", alt2)

    def test_eintrag_mit_titel_in_neuer_kategorie(self):
        e = self.hub.youtube_eintrag("Musik", "https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual((e["art"], e["titel"]), ("video", "Titel dQw4w9WgXcQ"))
        self.assertEqual(self.hub.youtube()["kategorien"][0]["name"], "Musik")
        with self.assertRaisesRegex(ValueError, "schon"):
            self.hub.youtube_eintrag("Musik", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_playlist_bekommt_ihre_videos_auch_nachtraeglich(self):
        e = self.hub.youtube_eintrag("Bass", "https://www.youtube.com/playlist?list=PLabcdefghijk")
        self.assertEqual(e["videos"], ["aaaaaaaaaaa", "bbbbbbbbbbb"])
        y = self.hub.youtube()                                    # wie vor 4.0.1 gespeichert: ohne Videoliste
        del y["kategorien"][0]["eintraege"][0]["videos"]
        self.hub.einstellungen_aendern({"youtube": y})
        self.assertEqual(self.hub.youtube_fuer_tv()["kategorien"][0]["eintraege"][0]["videos"], ["aaaaaaaaaaa", "bbbbbbbbbbb"])
        self.assertIn("videos", self.hub.youtube()["kategorien"][0]["eintraege"][0], "gespeichert")

    def test_kachel_und_whitelist(self):
        kachel = next(k for k in self.hub.kacheln() if k["id"] == "youtube")
        self.assertTrue(kachel["eingerichtet"])
        self.assertTrue(self.hub.starte("youtube")[0])
        self.assertFalse([a for a in self.hub.auftraege if a["art"] == "oeffne"], "kein Browser-Wechsel")
        self.hub.richtlinie_aktualisieren()
        with open(os.path.join(self.ordner, "whitelist-richtlinie.json")) as f:
            domains = json.load(f)["domains"]
        self.assertIn("www.youtube-nocookie.com", domains)


@unittest.skipIf(sync_playwright is None, "Playwright fehlt – make venv")
@unittest.skipUnless(port_frei(8765), "Port 8765 belegt (läuft make v3-lokal?)")
class PlayerImBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ordner = tempfile.mkdtemp(prefix="ff-yt-")
        cls.hub = neuer_hub(cls.ordner, Uhr(NACHMITTAG))
        cls.hub.einstellungen_aendern({"youtube": {"kategorien": [{"name": "Musik", "eintraege": [
            {"art": "video", "id": "aaaaaaaaaaa", "titel": "Erstes Lied"},
            {"art": "video", "id": "bbbbbbbbbbb", "titel": "Zweites Lied"},
            {"art": "playlist", "id": "PLabcdefghijk", "titel": "Liste", "videos": ["ccccccccccc", "ddddddddddd"]}]}]}})
        cls.server = web.baue_server(web.KioskHandler, cls.hub, os.path.join(REPO, "web"),
                                     os.path.join(cls.ordner, "zeichnungen"), ("127.0.0.1", 8765))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.ordner, True)

    def test_player_sicher(self):
        seite = self.browser.new_page(viewport={"width": 1600, "height": 900})
        fehler = []
        seite.on("pageerror", lambda e: fehler.append(str(e)))
        seite.route("https://www.youtube.com/iframe_api", lambda r: r.fulfill(body=YT_ATTRAPPE, content_type="text/javascript"))
        with urllib.request.urlopen("http://127.0.0.1:8765/") as a:
            csp = a.headers["Content-Security-Policy"]
        self.assertIn("frame-src https://www.youtube-nocookie.com", csp)
        seite.goto("http://127.0.0.1:8765/")
        seite.wait_for_selector(".kachel")                                # echte Sicherheitsrichtlinie: kein Warten per Skript
        seite.evaluate("FernsehFranzi.zeige('youtube')")
        seite.click(".kachel[data-id=youtube]")
        seite.wait_for_selector(".yt-kategorie")
        seite.keyboard.press("Enter")
        seite.wait_for_selector(".yt-video")
        seite.keyboard.press("Enter")
        seite.wait_for_selector(".yt-buehne iframe")
        seite.wait_for_function("() => window.__yt && window.__yt.befehle.includes('play')")
        opt = seite.evaluate("window.__yt.opt")
        self.assertEqual(opt["host"], "https://www.youtube-nocookie.com")
        for schluessel, wert in (("controls", 0), ("disablekb", 1), ("rel", 0), ("fs", 0)):
            self.assertEqual(opt["playerVars"][schluessel], wert)
        self.assertTrue(seite.is_hidden(".yt-deckel"))
        # Fokus ins Video zwingen: die Seite holt ihn zurück
        seite.evaluate("document.querySelector('.yt-buehne iframe').focus()")
        seite.wait_for_function("() => document.activeElement.tagName !== 'IFRAME'", timeout=3000)
        self.assertEqual(seite.evaluate("getComputedStyle(document.querySelector('.yt-buehne iframe')).pointerEvents"), "none")
        self.assertIn("aus captions", seite.evaluate("window.__yt.befehle"), "Untertitel von Anfang an aus")
        self.assertEqual(opt["playerVars"]["cc_load_policy"], 0)
        seite.keyboard.press("u")
        seite.wait_for_function("() => window.__yt.befehle.includes('an captions')")
        seite.keyboard.press("u")
        seite.wait_for_function("() => window.__yt.befehle.filter(b => b === 'aus captions').length >= 2")
        seite.keyboard.press("Enter")                                  # Pause -> eigener Deckel über „Weitere Videos“
        seite.wait_for_selector(".yt-deckel:not([hidden])")
        self.assertIn("720p", seite.inner_text(".yt-deckel"))
        seite.keyboard.press("Enter")
        seite.wait_for_selector(".yt-deckel", state="hidden")
        seite.evaluate("window.__yt.spieler.ende()")                   # Ende -> sofort verdeckt, dann das nächste Video
        self.assertTrue(seite.evaluate("document.querySelector('.yt-buehne').classList.contains('ende')"))
        seite.wait_for_function("() => document.querySelector('.overlay-kopf h2').textContent.includes('Zweites Lied')")
        seite.evaluate("window.__yt.spieler.ende()")                   # Ende von Video 2 -> die Playlist beginnt
        seite.wait_for_function("() => document.querySelector('.overlay-kopf h2').textContent.includes('Liste (1/2)')")
        self.assertEqual(seite.evaluate("window.__yt.opt.videoId"), "ccccccccccc", "einzelnes Video, keine YouTube-Playlist")
        self.assertNotIn("list", seite.evaluate("window.__yt.opt.playerVars"))
        seite.wait_for_function("() => window.__yt.befehle.filter(b => b === 'play').length >= 3")
        seite.keyboard.press("ArrowRight")                             # nächstes Video der Playlist
        seite.wait_for_function("() => document.querySelector('.overlay-kopf h2').textContent.includes('Liste (2/2)')")
        self.assertEqual(seite.evaluate("window.__yt.opt.videoId"), "ddddddddddd")
        seite.keyboard.press("Escape")
        seite.wait_for_selector(".yt-video")
        self.assertEqual(fehler, [])

    def test_bewegungspause_haelt_den_film_nur_an_und_merkt_die_stelle(self):
        """4.2.1: Die Bewegungspause schloss den Film (Startseite neu geladen), danach begann er von vorn."""
        from datetime import timedelta
        attrappe = (YT_ATTRAPPE.replace("this.getCurrentTime = () => 20;",
                                        "this.getCurrentTime = () => (window.__yt.t ?? 20); this.getDuration = () => 2400;")
                    .replace("this.getVideoData = () => ({ title: 'Titel' });",
                             "this.getVideoData = () => ({ title: 'Titel', video_id: opt.videoId });"))
        seite = self.browser.new_page(viewport={"width": 1600, "height": 900})
        self.addCleanup(seite.close)
        fehler = []
        seite.on("pageerror", lambda e: fehler.append(str(e)))
        seite.route("https://www.youtube.com/iframe_api", lambda r: r.fulfill(body=attrappe, content_type="text/javascript"))
        seite.goto("http://127.0.0.1:8765/")
        seite.evaluate("localStorage.clear()")
        seite.wait_for_selector(".kachel")
        seite.evaluate("FernsehFranzi.zeige('youtube')")
        seite.click(".kachel[data-id=youtube]")
        seite.wait_for_selector(".yt-kategorie")
        seite.keyboard.press("Enter")
        seite.wait_for_selector(".yt-video")
        seite.keyboard.press("Enter")
        seite.wait_for_function("() => window.__yt && window.__yt.befehle.includes('play')")
        seite.evaluate("window.__yt.t = 1500")                        # 25 Minuten im Film
        nachrichten_vorher = len(seite.evaluate("window.__yt.befehle"))

        self.hub.familie.pause_bis = self.hub.uhr() + timedelta(seconds=3)
        seite.wait_for_selector(".pause-ebene", timeout=5000)
        self.hub.familie.pause_bis = None                              # Testuhr steht - sonst käme die Pause erneut
        befehle = seite.evaluate("window.__yt.befehle")[nachrichten_vorher:]
        self.assertIn("pause", befehle)
        self.assertNotIn("destroy", befehle, "der Film bleibt offen")
        self.assertEqual(seite.locator(".yt-buehne iframe").count(), 1)
        self.assertIn("genau hier weiter", seite.inner_text(".pause-ebene"))
        self.assertNotIn("null", seite.inner_text(".pause-ebene"))
        vor_ende = len(seite.evaluate("window.__yt.befehle"))
        seite.wait_for_selector(".pause-ebene", state="detached", timeout=8000)
        self.assertIn("play", seite.evaluate("window.__yt.befehle")[vor_ende:], "nach der Pause läuft der Film weiter")
        self.assertEqual(seite.locator(".yt-buehne iframe").count(), 1)

        # Die Stelle ist gemerkt: STOP und wieder öffnen -> ab 25:00 weiter, 0 = von vorn
        seite.keyboard.press("Escape")
        seite.wait_for_selector(".yt-video")
        seite.keyboard.press("Enter")
        seite.wait_for_function("() => window.__yt.opt.playerVars.start === 1500")
        seite.wait_for_function("() => window.__yt.befehle.filter(b => b === 'play').length >= 3")
        seite.keyboard.press("0")
        seite.wait_for_function("() => window.__yt.befehle.includes('seek 0')")
        self.assertEqual(fehler, [])

    def test_bewegungspause_auf_der_startseite_ohne_null(self):
        """4.2.1: Ohne Film darunter stand unten in der Pause „null“."""
        from datetime import timedelta
        seite = self.browser.new_page(viewport={"width": 1600, "height": 900})
        self.addCleanup(seite.close)
        seite.goto("http://127.0.0.1:8765/")
        seite.wait_for_selector(".kachel")
        self.hub.familie.pause_bis = self.hub.uhr() + timedelta(seconds=60)
        self.addCleanup(setattr, self.hub.familie, "pause_bis", None)
        seite.wait_for_selector(".pause-ebene", timeout=5000)
        text = seite.inner_text(".pause-ebene")
        self.assertIn("Bewegungspause", text)
        self.assertNotIn("null", text)
        self.assertNotIn("genau hier weiter", text)


if __name__ == "__main__":
    unittest.main()
