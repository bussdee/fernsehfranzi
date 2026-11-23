"""FernsehFranzi 5.0 - Schule: Stundenplan, Hausaufgaben, Termine und Klassennachrichten aus der Klassenkiste.

Nur lesen: Der Fernseher ruft ausschließlich GET-Schnittstellen der Klassenkiste auf, mit der Anmeldung des Kindes aus
dem Kiosk-Profil (wie Karaoke seit 4.4). Er hakt nichts ab, markiert nichts als gelesen und schreibt nichts.

Alle 15 Minuten (wenn eingeschaltet) holt er den Stand. Was neu ist (Hausaufgabe, Klassennachricht, Ausfall oder
Vertretung), meldet er einmal: als Nachricht am Fernseher und, wenn gewünscht, per Telegram an die Eltern. Beim ersten
Abruf merkt er sich nur den Stand, damit nicht alles Alte auf einmal kommt. Abends kommt der „Morgen-Check“: erste
Stunde und Hausaufgaben bis morgen (nur vor einem Schultag).
"""
import logging
import re
import threading
import time
from datetime import datetime, timedelta

from . import daten, klaenge, zeitkonto

log = logging.getLogger("fernsehfranzi.schule")

ABFRAGE_S = 15 * 60
FEHLER_PAUSE_S = 5 * 60
VORGABE = {"aktiv": False, "tv_hinweis": True, "telegram": True, "morgen_check": True, "morgen_check_um": "18:00",
           "klang": None, "klang_morgen": None}        # 5.2: Klänge für Neues aus der Schule und den Morgen-Check
FELDER = set(VORGABE)
UHRZEIT = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]\Z")
TEXT_MAX = 600
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def einstellungen(roh):
    return dict(VORGABE, **{k: v for k, v in (roh or {}).items() if k in FELDER})


def pruefe(roh):
    if not isinstance(roh, dict) or set(roh) - FELDER:
        raise ValueError("Schule: unbekannte Felder.")
    s = einstellungen(roh)
    for feld in ("aktiv", "tv_hinweis", "telegram", "morgen_check"):
        if not isinstance(s[feld], bool):
            raise ValueError("Schule: %s ja oder nein." % feld)
    if not isinstance(s["morgen_check_um"], str) or not UHRZEIT.match(s["morgen_check_um"]):
        raise ValueError("Schule: Uhrzeit des Morgen-Checks als HH:MM.")
    klaenge.pruefe(s["klang"], "Schule")
    klaenge.pruefe(s["klang_morgen"], "Morgen-Check")
    return s


def _t(wert, n=200):
    return re.sub(r"\s+", " ", str(wert or "")).strip()[:n]


def _absatz(wert, n=TEXT_MAX):
    """Mehrzeiliger Text ohne HTML-Reste (die Klassenkiste speichert Klartext; sicher ist sicher)."""
    text = re.sub(r"<[^>]{0,200}>", "", str(wert or ""))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:n] + ("…" if len(text) > n else "")


def _datum(text):
    try:
        return datetime.strptime(str(text)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _uhr(text):
    m = re.match(r"(\d{1,2}):(\d{2})", str(text or ""))
    return "%02d:%s" % (int(m.group(1)), m.group(2)) if m else None


def tag_text(tag, heute):
    if tag == heute:
        return "heute"
    if tag == heute + timedelta(days=1):
        return "morgen"
    if tag and 1 < (tag - heute).days < 7:
        return WOCHENTAGE[tag.weekday()]
    return tag.strftime("%d.%m.") if tag else ""


def naechster_schultag(heute, regeln):
    """Der nächste Montag-Freitag nach heute, der nicht in den eingetragenen Ferien liegt (höchstens drei Wochen weit)."""
    tag = heute
    for _ in range(21):
        tag += timedelta(days=1)
        if tag.weekday() < 5 and not zeitkonto.in_ferien(tag, regeln):
            return tag
    return None


def hausaufgaben(roh, heute):
    """Offene Hausaufgaben (nicht erledigt, nicht überfällig), nach Fälligkeit."""
    aus = []
    for h in roh if isinstance(roh, list) else []:
        if not isinstance(h, dict) or h.get("completed_at") or h.get("class_archived_at"):
            continue
        faellig = _datum(h.get("due_date"))
        if faellig and faellig < heute:
            continue
        aus.append({"id": _t(h.get("id"), 40), "fach": _t(h.get("subject"), 60), "titel": _t(h.get("title"), 160),
                    "text": _absatz(h.get("description"), 400), "faellig": faellig.isoformat() if faellig else None,
                    "faellig_text": tag_text(faellig, heute) if faellig else "", "klasse": _t(h.get("class_name"), 60),
                    "bis_morgen": bool(faellig and faellig <= heute + timedelta(days=1))})
    aus.sort(key=lambda h: (h["faellig"] is None, h["faellig"] or ""))
    return aus[:30]


def nachrichten(roh, heute):
    aus = []
    for m in roh if isinstance(roh, list) else []:
        if not isinstance(m, dict) or not m.get("id"):
            continue
        tag = _datum(m.get("created_at"))
        aus.append({"id": _t(m.get("id"), 40), "titel": _t(m.get("title"), 160), "text": _absatz(m.get("body")),
                    "von": _t(m.get("author_name"), 80), "klasse": _t(m.get("class_name"), 60),
                    "datum": tag.isoformat() if tag else None, "datum_text": tag_text(tag, heute) if tag else "",
                    "angeheftet": bool(m.get("pinned")), "nur_fuer_mich": bool(m.get("target_student_id"))})
    aus.sort(key=lambda m: (not m["angeheftet"], -(int(m["datum"].replace("-", "")) if m["datum"] else 0)))
    return aus[:20]


def termine(roh, heute):
    aus = []
    for e in roh if isinstance(roh, list) else []:
        tag = _datum(e.get("event_date")) if isinstance(e, dict) else None
        if not tag or tag < heute:
            continue
        aus.append({"titel": _t(e.get("title"), 160), "datum": tag.isoformat(), "tag_text": tag_text(tag, heute),
                    "uhr": _uhr(e.get("event_time")), "klasse": _t(e.get("class_name"), 60),
                    "von_schule": bool(e.get("von_schule"))})
    return aus[:8]


def stunden_heute(uebersicht):
    aus = []
    for s in uebersicht.get("today_lessons") or []:
        if not isinstance(s, dict):
            continue
        aus.append({"nr": s.get("period") if isinstance(s.get("period"), int) else None, "fach": _t(s.get("subject"), 60),
                    "raum": _t(s.get("room"), 30), "von": _uhr(s.get("start")), "bis": _uhr(s.get("end")),
                    "laeuft": bool(s.get("laeuft")), "faellt_aus": bool(s.get("cancelled")), "geaendert": bool(s.get("changed"))})
    aus.sort(key=lambda s: s["nr"] or 0)
    frei = [_t(f.get("label"), 80) for f in uebersicht.get("today_free") or [] if isinstance(f, dict)]
    return aus, frei


def stunden_am(plan, tag):
    """Stunden einer Klasse an einem Tag aus /api/timetable?week=… - mit Ausfall, Vertretung und Raumwechsel."""
    aus, frei = [], []
    if not isinstance(plan, dict) or not tag:
        return aus, frei
    wochentag = tag.weekday() + 1
    for k in plan.get("classes") or []:
        if not isinstance(k, dict):
            continue
        for c in k.get("closures") or []:
            von, bis = _datum(c.get("date_from")), _datum(c.get("date_to"))
            if von and bis and von <= tag <= bis:
                frei.append(_t(c.get("label"), 80) or "frei")
        if frei:
            continue
        zeiten = k.get("lesson_times") if isinstance(k.get("lesson_times"), dict) else {}
        aenderung = {o.get("period"): o for o in k.get("overrides") or []
                     if isinstance(o, dict) and _datum(o.get("override_date")) == tag}
        for s in k.get("slots") or []:
            if not isinstance(s, dict) or s.get("weekday") != wochentag:
                continue
            nr = s.get("period")
            o = aenderung.get(nr) or {}
            z = zeiten.get(str(nr)) or {}
            fach = o.get("subject") if o.get("kind") == "substitution" and o.get("subject") else s.get("subject")
            raum = o.get("room") if o.get("kind") == "room_change" and o.get("room") else s.get("room")
            aus.append({"nr": nr if isinstance(nr, int) else None, "fach": _t(fach, 60), "raum": _t(raum, 30),
                        "von": _uhr(z.get("start") if isinstance(z, dict) else None),
                        "faellt_aus": o.get("kind") == "cancelled", "geaendert": o.get("kind") in ("substitution", "room_change")})
    aus.sort(key=lambda s: s["nr"] or 0)
    return aus, frei


def ausfaelle(stunden, tag):
    """Schlüssel der Ausfälle und Änderungen (für „neu“)."""
    return ["%s:%s:%s" % (tag.isoformat(), s["nr"], "aus" if s["faellt_aus"] else "anders")
            for s in stunden if s["faellt_aus"] or s["geaendert"]]


def morgen_satz(stunden, frei, aufgaben, tag, heute):
    wann = tag_text(tag, heute).capitalize()
    if frei:
        return "%s ist schulfrei (%s)." % (wann, frei[0])
    teile = []
    echte = [s for s in stunden if not s["faellt_aus"]]
    if echte:
        erste = echte[0]
        teile.append("%s: %s. Stunde %s%s" % (wann, erste["nr"] or 1, erste["fach"] or "Unterricht",
                                             " um %s" % erste["von"] if erste["von"] else ""))
    if any(s["faellt_aus"] for s in stunden):
        teile.append("%d Stunde(n) fallen aus" % sum(1 for s in stunden if s["faellt_aus"]))
    bis = [a for a in aufgaben if a["faellig"] and _datum(a["faellig"]) <= tag]
    if bis:
        teile.append("Hausaufgaben bis dahin: %s" % ", ".join(a["fach"] or a["titel"] for a in bis[:4]))
    elif echte:
        teile.append("keine Hausaufgaben offen")
    return (" · ".join(teile) + ".") if teile else ""


class Schule:
    def __init__(self, hub):
        self.hub = hub
        self.pfad = hub._pfad("schule.json")
        self.zustand = daten.lies_json(self.pfad, {}) or {}
        self.zustand.setdefault("bekannt", None)          # {"hausaufgaben": [...], "nachrichten": [...], "ausfaelle": [...]}
        self.zustand.setdefault("morgen_check", "")        # Datum, an dem er zuletzt kam
        self.stand, self.geholt, self.fehler, self._laeuft = None, 0.0, "", False
        self._lock = threading.Lock()

    def einstellungen(self):
        return einstellungen(self.hub.einstellungen.get("schule"))

    def bereit(self):
        return self.einstellungen()["aktiv"] and bool(self.hub.klassenkiste_basis())

    # ------------------------------------------------------------ Holen
    def holen(self):
        heute = self.hub.uhr().date()
        regeln = self.hub._regeln()
        morgen = naechster_schultag(heute, regeln)
        try:
            uebersicht = self.hub.klassenkiste_json("/api/overview") or {}
            aufgaben = hausaufgaben(self.hub.klassenkiste_json("/api/homework/mine"), heute)
            post = nachrichten(self.hub.klassenkiste_json("/api/messages"), heute)
            plan = self.hub.klassenkiste_json("/api/timetable?week=%s" % morgen.isoformat()) if morgen else {}
        except ValueError as fehler:
            with self._lock:
                self.fehler, self.geholt = str(fehler), time.time()
            log.info("Schule: %s", fehler)
            return None
        heute_stunden, heute_frei = stunden_heute(uebersicht if isinstance(uebersicht, dict) else {})
        morgen_stunden, morgen_frei = stunden_am(plan, morgen)
        stand = {"heute": heute.isoformat(), "stunden": heute_stunden, "frei": heute_frei,
                 "hausaufgaben": aufgaben, "nachrichten": post,
                 "termine": termine((uebersicht or {}).get("next_events") if isinstance(uebersicht, dict) else [], heute),
                 "morgen": {"datum": morgen.isoformat() if morgen else None, "name": tag_text(morgen, heute) if morgen else "",
                            "stunden": morgen_stunden, "frei": morgen_frei,
                            "satz": morgen_satz(morgen_stunden, morgen_frei, aufgaben, morgen, heute) if morgen else ""},
                 "ungelesen": (uebersicht or {}).get("unread_messenger", 0) if isinstance(uebersicht, dict) else 0}
        neu = self._neues(stand, heute, morgen)
        with self._lock:
            self.stand, self.geholt, self.fehler = stand, time.time(), ""
        if neu:
            self._melden(neu)
        return stand

    def _neues(self, stand, heute, morgen):
        """Was seit dem letzten Abruf dazugekommen ist. Beim ersten Mal nur merken."""
        jetzt = {"hausaufgaben": [h["id"] for h in stand["hausaufgaben"]],
                 "nachrichten": [m["id"] for m in stand["nachrichten"]],
                 "ausfaelle": ausfaelle(stand["stunden"], heute) + (ausfaelle(stand["morgen"]["stunden"], morgen) if morgen else [])}
        alt = self.zustand.get("bekannt")
        neu = []
        if isinstance(alt, dict):
            for h in stand["hausaufgaben"]:
                if h["id"] not in alt.get("hausaufgaben", []):
                    neu.append(("hausaufgabe", "Neue Hausaufgabe%s: %s%s" % (
                        " in " + h["fach"] if h["fach"] else "", h["titel"],
                        " (bis %s)" % h["faellig_text"] if h["faellig_text"] else "")))
            for m in stand["nachrichten"]:
                if m["id"] not in alt.get("nachrichten", []):
                    neu.append(("nachricht", "Neue Nachricht von %s: %s" % (m["von"] or "der Klasse", m["titel"] or m["text"][:80])))
            for schluessel in jetzt["ausfaelle"]:
                if schluessel not in alt.get("ausfaelle", []):
                    tag, nr, art = schluessel.split(":")
                    t = _datum(tag)
                    neu.append(("ausfall", "%s fällt die %s. Stunde aus" % (tag_text(t, heute).capitalize(), nr) if art == "aus"
                                else "%s ändert sich die %s. Stunde (Vertretung oder anderer Raum)" % (tag_text(t, heute).capitalize(), nr)))
        # Gemerkt wird alles, was noch aktuell ist (alte Ausfälle fallen von selbst heraus)
        bekannt = {}
        for k in jetzt:
            alte = [x for x in (alt.get(k, []) if isinstance(alt, dict) and k != "ausfaelle" else []) if x not in jetzt[k]]
            bekannt[k] = (jetzt[k] + alte)[:300]
        self.zustand["bekannt"] = bekannt
        daten.schreibe_json(self.pfad, self.zustand)
        return neu

    def _melden(self, neu):
        s = self.einstellungen()
        texte = [t for _, t in neu][:5]
        if len(neu) > 5:
            texte.append("und %d weitere" % (len(neu) - 5))
        text = " · ".join(texte)
        if s["tv_hinweis"]:
            try:
                self.hub.familie.nachricht(text, quelle="Klassenkiste", bleibt=True, symbol="🏫", klang=s["klang"])
            except ValueError:
                pass
        if s["telegram"]:
            self.hub.telegram.melde_eltern("schule", "🏫 Klassenkiste: " + text)
        log.info("Schule neu: %s", text)

    # ------------------------------------------------------------ Takt
    def tick(self, jetzt, gleich=False):
        if not self.bereit() or self._laeuft:
            return
        pause = FEHLER_PAUSE_S if self.fehler else ABFRAGE_S
        if self.stand is None and not self.fehler:
            pause = 0
        if time.time() - self.geholt >= pause:
            self._starten(gleich)
        self._morgen_check(jetzt)

    def _starten(self, gleich=False):
        def lauf():
            try:
                self.holen()
            except Exception:   # noqa: BLE001 - die Schule darf den Takt nie stören
                log.exception("Schule")
            finally:
                self._laeuft = False
        self._laeuft = True
        if gleich:
            lauf()
        else:
            threading.Thread(target=lauf, daemon=True, name="schule").start()

    def _morgen_check(self, jetzt):
        s = self.einstellungen()
        if not s["morgen_check"] or not self.stand or jetzt.strftime("%H:%M") < s["morgen_check_um"]:
            return
        heute = jetzt.date().isoformat()
        if self.zustand.get("morgen_check") == heute or self.stand.get("heute") != heute:
            return
        m = self.stand["morgen"]
        if not m.get("datum") or _datum(m["datum"]) != jetzt.date() + timedelta(days=1) or not m.get("satz"):
            return                     # nur am Abend vor einem Schultag
        self.zustand["morgen_check"] = heute
        daten.schreibe_json(self.pfad, self.zustand)
        try:
            self.hub.familie.nachricht(m["satz"], quelle="Morgen-Check", bleibt=True, symbol="🎒", klang=s["klang_morgen"])
        except ValueError:
            pass
        if s["telegram"]:
            self.hub.telegram.melde_eltern("schule", "🎒 " + m["satz"])

    # ------------------------------------------------------------ Für Fernseher und Eltern
    def fuer_tv(self):
        s = self.einstellungen()
        if not s["aktiv"]:
            return {"aktiv": False}
        if not self.hub.klassenkiste_basis():
            return {"aktiv": True, "stand": None, "fehler": "Die Klassenkiste-Kachel ist nicht eingerichtet."}
        with self._lock:
            stand, geholt, fehler = self.stand, self.geholt, self.fehler
        return {"aktiv": True, "stand": stand, "fehler": fehler,
                "zeit": datetime.fromtimestamp(geholt).strftime("%H:%M") if geholt else None}

    def jetzt_holen(self):
        """Eltern-Seite: „Jetzt abrufen“ (blockiert bis die Klassenkiste antwortet)."""
        if not self.hub.klassenkiste_basis():
            raise ValueError("Die Klassenkiste-Kachel ist nicht eingerichtet.")
        stand = self.holen()
        if stand is None:
            raise ValueError(self.fehler or "Die Klassenkiste antwortet gerade nicht.")
        return {"hausaufgaben": len(stand["hausaufgaben"]), "nachrichten": len(stand["nachrichten"]),
                "stunden": len(stand["stunden"]), "morgen": stand["morgen"]["satz"]}
