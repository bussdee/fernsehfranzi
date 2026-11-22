"""Emojis auf dem Fernseh-Pi: Er hat keine Emoji-Schrift - die Startseite bringt ihre eigene mit.

Am 21.11. fehlten auf dem Gerät Memory-Bilder und ⭕ (Drei Gewinnt), weil fc-list dort kein
Zeichen ab U+1F000 kennt. Jedes Emoji in web/ und in Server-Texten muss in web/fonts/emoji.ttf stehen.
"""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "werkzeuge"))

import emoji_schrift  # noqa: E402

try:
    from fontTools.ttLib import TTFont
except ImportError:
    TTFont = None

PFEILE_UND_TEXT = set("←↑→↓⌫")     # hat das Gerät in normalen Schriften (gemessen)


@unittest.skipIf(TTFont is None, "fonttools fehlt – make venv")
class EmojiSchrift(unittest.TestCase):
    def test_jedes_emoji_ist_in_der_mitgelieferten_schrift(self):
        cmap = TTFont(os.path.join(REPO, "web", "fonts", "emoji.ttf")).getBestCmap()
        fehlen = sorted(z for z in emoji_schrift.emojis_in_web() - PFEILE_UND_TEXT if ord(z) not in cmap)
        self.assertEqual(fehlen, [], "werkzeuge/emoji_schrift.py neu ausführen")

    def test_startseite_laedt_die_schrift(self):
        with open(os.path.join(REPO, "web", "css", "start.css"), encoding="utf-8") as f:
            css = f.read()
        self.assertIn('url("/fonts/emoji.ttf")', css)
        self.assertIn('"FF Emoji"', css.split("\nbody {", 1)[1].split("}", 1)[0])

    def test_meldungen_ans_tv_ohne_emoji(self):
        """Hinweise erscheinen auch in Plex und in RetroArch - dort gibt es keine Emoji-Schrift."""
        with open(os.path.join(REPO, "server", "fernsehfranzi", "familie.py"), encoding="utf-8") as f:
            quelltext = f.read()
        for zeile in quelltext.splitlines():
            if "nachricht(" in zeile or "melde(" in zeile:
                self.assertFalse(any(emoji_schrift.ist_emoji(z) for z in zeile), zeile)


if __name__ == "__main__":
    unittest.main()
