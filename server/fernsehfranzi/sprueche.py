"""FernsehFranzi 6.9.61 - Was Franzi auf der Startseite sagt.

Grund-Sprüche kommen immer aus der Lage (Wetter, Aufgaben, Routinen, geschafft oder nicht geschafft) - freundlich, nie
beschämend. Weitere Arten (Witze, Ordnungs-Tipps, Schule und Kleidung) schalten die Eltern einzeln ein, dazu eigene Texte.
Keine fremden Quellen. Einstellung im Feld "franzi" → "sprueche":
    {"witze": false, "ordnung": false, "schule": false, "eigene": [{"text": "...", "anlass": "immer"}]}
"""
import random

ARTEN = ("witze", "ordnung", "schule")
ANLAESSE = {"immer": "immer", "morgens": "morgens", "abends": "abends", "schule": "vor einem Schultag",
            "wochenende": "am Wochenende", "geschafft": "wenn etwas geschafft ist", "witz": "als Witz"}
EIGENE_MAX, TEXT_MAX = 40, 120
VORGABE = {"witze": False, "ordnung": False, "schule": False, "eigene": []}

WETTER = {
    "sonne": ["Die Sonne scheint! Gehst du heute raus?", "So ein schönes Wetter – perfekt zum Spielen draußen!"],
    "regen": ["Es regnet … gut, dass wir es hier gemütlich haben.", "Pitsch, patsch! Vergiss die Regenjacke nicht."],
    "schnee": ["Schnee! Baust du einen Schneemann für mich?", "Brrr, alles weiß draußen – zieh dich warm an!"],
    "kalt": ["Ganz schön kalt heute – Mütze auf!", "Kalt draußen! Ein warmer Kakao wäre jetzt was."],
}
ZEIT = {
    "morgens": ["Guten Morgen! Hast du gut geschlafen?", "Ein neuer Tag – ich freu mich drauf!"],
    "mittags": ["Na, wie war dein Tag bis jetzt?", "Zeit für eine kleine Pause!"],
    "abends": ["Bald ist Schlafenszeit … aber erst noch ein bisschen Zeit für uns.", "Was war heute das Schönste?"],
}
ROUTINE_JETZT = ["Jetzt ist {name}-Zeit! Noch {offen} – wir schaffen das!", "Los geht's mit {name}! Ich mach mit.",
                 "{name}: nur noch {offen}, dann haben wir es!"]
ROUTINE_GESCHAFFT = ["{name} geschafft – super gemacht! 💛", "Juhu, {name} ist fertig! Ich bin stolz auf dich."]
ROUTINE_NICHT = ["{name} hat heute nicht ganz geklappt – morgen schaffen wir das zusammen!",
                 "Nicht schlimm wegen {name} – morgen ist ein neuer Tag."]
AUFGABE = ["Ich würde heute auch gern helfen: {text}!", "Hast du schon an „{text}“ gedacht? Ich helfe mit!"]
STERN = ["Ein Stern! Du bist toll! ⭐", "Wow, schon wieder ein Stern – ich platze vor Freude!"]
WITZE = [
    "Was macht ein Pirat am Computer? Er drückt die Enter-Taste! ⚓",
    "Warum können Geister so schlecht lügen? Weil man durch sie hindurchsieht! 👻",
    "Was ist grün und klopft an die Tür? Ein Klopfsalat! 🥬",
    "Wie nennt man einen Bumerang, der nicht zurückkommt? Stock! 🪵",
    "Was sitzt auf dem Baum und schreit „Aha“? Ein Uhu mit Sprachfehler! 🦉",
    "Was ist braun, klebrig und läuft durch die Wüste? Ein Karamel! 🐪",
    "Warum gehen Ameisen nicht in die Kirche? Weil sie Insekten sind! 🐜",
    "Was liegt am Strand und spricht undeutlich? Eine Nuschel! 🐚",
    "Welcher Fernseher ist der lustigste? Na ich! 📺",
    "Was macht eine Wolke, wenn es juckt? Sie sucht einen Wolkenkratzer! ☁️",
]
ORDNUNG = ["Tipp: Erst die Spielsachen in die Kiste, dann das nächste Spiel – dann bleibt's gemütlich!",
           "Weißt du was? Wenn jedes Spielzeug einen festen Platz hat, findest du alles sofort.",
           "Zehn Sachen wegräumen dauert nur zwei Minuten – wetten?", "Ein aufgeräumter Schreibtisch macht Hausaufgaben leichter!"]
SCHULE = ["Morgen ist Schule! Mein Outfit: {kleid}. Und was ziehst du an?", "Hast du deinen Ranzen schon gepackt?",
          "Morgen Schule! Früh ins Bett, dann sind wir fit.", "Ich bin gespannt, was du morgen in der Schule erlebst!"]
WOCHENENDE = ["Wochenende! Was machen wir Schönes?", "Kein Wecker morgen – hurra!"]


def einstellungen(roh):
    d = dict(VORGABE, **{k: v for k, v in (roh or {}).items() if k in VORGABE})
    d["eigene"] = [dict(e) for e in d.get("eigene") or [] if isinstance(e, dict) and str(e.get("text") or "").strip()]
    return d


def pruefe(roh):
    if roh is None:
        return
    if not isinstance(roh, dict) or set(roh) - set(VORGABE):
        raise ValueError("Franzis Sprüche: unbekannte Felder.")
    for a in ARTEN:
        if not isinstance(roh.get(a, False), bool):
            raise ValueError("Franzis Sprüche: an oder aus.")
    eigene = roh.get("eigene", [])
    if not isinstance(eigene, list) or len(eigene) > EIGENE_MAX:
        raise ValueError("Franzis Sprüche: höchstens %d eigene Texte." % EIGENE_MAX)
    for e in eigene:
        if not isinstance(e, dict) or set(e) - {"text", "anlass"} or e.get("anlass", "immer") not in ANLAESSE:
            raise ValueError("Franzis Sprüche: eigener Text unvollständig.")
        if not isinstance(e.get("text"), str) or len(e["text"].strip()) > TEXT_MAX:      # leer = gerade angelegt
            raise ValueError("Franzis Sprüche: eigener Text 1 bis %d Zeichen." % TEXT_MAX)


def _tageszeit(jetzt):
    return "morgens" if jetzt.hour < 11 else "mittags" if jetzt.hour < 17 else "abends"


def kandidaten(einst, jetzt, lage):
    """Alle Sätze, die gerade passen - [(gewicht, text, gesicht)]. lage: wetter, routine (laufend: name/offen),
    geschafft (Name einer heute geschafften Liste), nicht_geschafft, aufgaben (offene Texte), lob (Stern gerade eben),
    schule_morgen, wochenende, kleid (Name eines Kleidungsstücks)."""
    s = einstellungen(einst)
    aus = []
    r = lage.get("routine")
    if r:
        offen = "1 Sache" if r["offen"] == 1 else "%d Sachen" % r["offen"]
        aus += [(6, t.format(name=r["name"], offen=offen), "jubel") for t in ROUTINE_JETZT]
    if lage.get("lob"):
        aus += [(5, t, "verliebt") for t in STERN]
    if lage.get("geschafft"):
        aus += [(4, t.format(name=lage["geschafft"]), "verliebt") for t in ROUTINE_GESCHAFFT]
    if lage.get("nicht_geschafft"):
        aus += [(3, t.format(name=lage["nicht_geschafft"]), "froh") for t in ROUTINE_NICHT]
    for text in (lage.get("aufgaben") or [])[:3]:
        aus += [(2, t.format(text=text), "frech") for t in AUFGABE]
    if lage.get("wetter") in WETTER:
        aus += [(2, t, {"sonne": "jubel", "regen": "muede", "schnee": "staunen", "kalt": "grummelig"}[lage["wetter"]])
                for t in WETTER[lage["wetter"]]]
    zeit = _tageszeit(jetzt)
    aus += [(1, t, "froh") for t in ZEIT[zeit]]
    if lage.get("wochenende"):
        aus += [(1, t, "jubel") for t in WOCHENENDE]
    if s["witze"]:
        aus += [(1, t, "frech") for t in WITZE]
    if s["ordnung"]:
        aus += [(1, t, "froh") for t in ORDNUNG]
    if s["schule"] and lage.get("schule_morgen"):
        aus += [(2, t.format(kleid=lage.get("kleid") or "Lieblingssachen"), "froh") for t in SCHULE]
    for e in s["eigene"]:
        a = e.get("anlass", "immer")
        passt = a == "immer" or a == zeit or (a == "schule" and lage.get("schule_morgen")) or \
            (a == "wochenende" and lage.get("wochenende")) or (a == "geschafft" and (lage.get("geschafft") or lage.get("lob"))) or \
            (a == "witz" and s["witze"])
        if passt:
            aus.append((3, e["text"].strip(), "frech" if a == "witz" else "froh"))
    return aus


def waehle(einst, jetzt, lage, zufall=None):
    """Ein Satz für jetzt (mit Gewicht gewürfelt) - {"text", "gesicht"} oder None."""
    k = kandidaten(einst, jetzt, lage)
    if not k:
        return None
    z = zufall or random
    gewicht, text, gesicht = z.choices(k, weights=[g for g, *_ in k])[0]
    return {"text": text, "gesicht": gesicht}
