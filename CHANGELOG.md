# Changelog

Alle nennenswerten Änderungen an FernsehFranzi. Versionsquelle ist die Datei `VERSION`.

## 6.0.0 – Neue Startseite „Zuhause“, neues Aussehen mit Franzi, neue Eltern-Seite, Mikro-Spiele (24.11.2026)

- **Neue Startseite „Zuhause + Bereiche“:** oben der Gruß mit Uhr, Wetter und der Restzeit als Balken; darunter
  ⭐ bis zu 6 Lieblinge, ▶ „Weiter, wo du warst“ (zuletzt benutzt) und je eine Kachel pro Bereich (Spiele, Filme, Musik,
  Lernen, Mein Zimmer, Retro). OK öffnet einen Bereich als Raster, STOP führt zurück. Freie Kacheln zuerst, gesperrte am
  Ende mit kurzem Grund auf der Kachel. Unten der Name der gewählten Kachel mit einem Satz und die Tasten mit Symbolen.
  Die drei Ansichten von 5.0 (Konsole, Seitenleiste, Karussell) entfallen dafür.
- **Eltern-Seite mit fünf Reitern:** Heute · Zeit · Inhalte · Familie · Gerät statt Menü mit 16 Kacheln. Jeder Bereich ist
  eine kurze Zeile mit Stand und klappt mit einem Tipp auf; lange Erklärungen stehen hinter „ℹ️“. Auf „Heute“ stehen
  Sperren und Auszeit nebeneinander, die Auszeit-Minuten klappen erst beim Antippen auf; die Statistik liegt unten auf
  „Heute“. Alte Lesezeichen führen weiter.
- **Klare Farben:** Blau, Grün, Lila, Rot, Schwarz und hell Hellblau, Mint, Rosa, Sonnengelb, Weiß – jede färbt Hintergrund,
  Leiste, Rahmen und Kacheln deutlich anders. „Gestalten“ zeigt eine Vorschau. Abends wird nur eine helle Farbe zu ihrer
  dunklen Schwester, eine dunkle Wahl bleibt (bisher sprang abends alles auf ein Abend-Design, deshalb ließ sich die Farbe
  scheinbar nicht ändern). Die alten Namen werden beim Start einmal umgestellt.
- **Spiele und Seiten am Fernseher:** jede Überschrift mit Symbol, Bedienhinweise größer und lesbar, Auswahl („Wie
  schnell?“, „Gegen wen?“ …) als große Karten, Gutschein-Ziffernblock größer, die großen Start-Kacheln farbig.
- **Fotoalbum:** „▶ Diashow jetzt“ startet den Bildschirmschoner mit den ausgesuchten Bildern sofort.
- **Eigene Klänge** aus einem freigegebenen Ordner, wählbar wie die eingebauten (höchstens 10 s, 4 MB).
- **YouTube-Kategorien** lassen sich vorübergehend ausschalten; die Videos bleiben gespeichert.
- **Neues Aussehen:** 3D-Bilder statt flacher Emojis (Fluent Emoji von Microsoft, MIT-Lizenz), zu jeder Farbe ein ruhiges
  Hintergrundbild mit Motiv (Weltraum, Wald, Zaubernacht, Abendrot, Himmel, Wiese, Zuckerwatte, Strand, Winter), Kacheln
  gleiten beim Öffnen eines Bereichs herein, das Bild der gewählten Kachel hüpft kurz. Alle Bewegungen nutzen nur
  transform und opacity, damit der Pi 3 flüssig bleibt.
- **Maskottchen Franzi:** ein kleiner Fernseher mit Gesicht. Franzi winkt auf der Startseite, schläft bei der Sperre,
  jubelt bei Siegen und staunt auf leeren Seiten.
- **Mikro-Spiele neu gestaltet:** Lautstärke-Rakete mit Himmel bis zum Mond, Flamme, Lautstärke-Balken und großem
  Countdown; Klatsch-Rhythmus mit Taktlinie und den eigenen Klatschern als Punkte; Ton-Treffer und Singen mit der Stimme als
  Linie, grünem Zielband und Ring zum Halten; Stimmgerät mit großem Zeiger.
- **YouTube-Reihenfolge:** Kategorien und Videos lassen sich auf der Eltern-Seite mit ↑ ↓ verschieben.
- **Kinder-News nur aus eigenen RSS-Adressen:** Die fest eingebaute Quellen-Auswahl ist entfernt. Die Eltern tragen bis zu
  10 RSS-Adressen selbst ein; ohne Adresse gibt es keine Kachel. Bisher eingeschaltete Quellen werden nicht übernommen.

## 5.3.0 – Wartungsmodus beim Ausliefern (23.11.2026)

- **Vorwarnung:** Nach der zweiten Bestätigung von `make v3-deploy` läuft am Fernseher oben rechts 10 Sekunden ein
  Countdown („Gleich kommt ein Update – schnell speichern!“), über Spielen und Playern. Im Retro-Spiel erscheint der
  Hinweis im Spiel, über Plex und Webseiten als Hinweis. Bis dahin geht noch alles.
- **Wartungsmodus:** Danach zeigt der Fernseher einen Warnbildschirm („Bitte jetzt nichts drücken und nicht ausschalten!“).
  Keine Taste wirkt, nichts lässt sich starten – auch nach dem Neustart des Geräts.
- **Automatisch aus:** Ist `make v3-pruefen` grün, schaltet es den Wartungsmodus ab („Fertig – weiter geht's!“). Bei Rot
  bleibt er an; von Hand mit `make v3-wartung-aus`. Spätestens nach 45 Minuten endet er von selbst.
- Technik: eine Datei `wartung.json` im Datenordner (`ab`, `bis`); `make v3-pruefen` löscht nur diese Datei.
- **Nachrichten von der Eltern-Seite mit Absender:** Über dem Nachrichtenfeld steht „Von“ mit den Eltern-Kontakten aus
  Telegram. Am Fernseher steht dann deren Symbol und Name (z. B. „🐼 Papa: …“) statt „Nachricht von Mama oder Papa“, und es
  klingt ihr Klang. Jedes Handy merkt sich seine Wahl.

## 5.2.0 – Klang-Archiv: eigener Klang je Erinnerung, Kontakt und Schule (23.11.2026)

- **Klang-Archiv** mit 15 eigenen, vom Fernseher selbst erzeugten Klängen (keine fremden Dateien): Gong, Glöckchen,
  Xylophon, Harfe, Spieluhr, Fanfare, Vogelzwitschern, Wassertropfen, Fahrradklingel, Sternschnuppe, Marimba,
  Level geschafft, Trommelwirbel, Ufo und Sanft, dazu „Ohne Ton“.
- **Wählbar** je Erinnerung, je Telegram-Kontakt (z. B. Vogelzwitschern für die beste Freundin), für Nachrichten von Mama
  oder Papa und für die Schule (Neues aus der Klassenkiste, Morgen-Check). Ohne Wahl bleibt es beim Gong. Auch die
  Wiederholung alle 5 Minuten kommt mit dem gewählten Klang.
- **Probehören:** ▶ spielt den Klang am Handy, 📺 am Fernseher.

## 5.1.0 – Auszeit mit Countdown (23.11.2026)

- **Auszeit:** Unter „Jetzt sperren“ gibt es auf der Eltern-Seite (Heute) den Knopf „⏳ Auszeit“: 5, 10, 15, 30 oder 60
  Minuten oder eine eigene Zahl (bis 240). Alles wird gesperrt, laufende Apps und Spiele enden, und am Fernseher steht nur
  ein großer Countdown. Danach ist der Fernseher von selbst wieder frei („Die Auszeit ist vorbei – weiter geht's!“).
  Während einer Auszeit kann man verlängern (+5, +10, +15 min) oder sie früher beenden. Die Auszeit gibt es auch im
  Elternbereich am Fernseher und per Telegram (`/auszeit 15`); sie übersteht einen Neustart des Geräts.

## 5.0.0 – Designs und Ansichten, Wetter, Schule, Geschichten & Rätsel, Kinder-News (23.11.2026)

- **Farben und Ansichten:** Unter „Gestalten“ wählt das Kind jetzt zwei Dinge. Bei den Farben gibt es zu den dunklen
  Designs vier helle: ☀️ Sonnentag, 🍭 Zuckerwatte, 🌼 Blumenwiese und 🌈 Regenbogen. Bei der Ansicht, also der Aufteilung
  der Startseite, gibt es 🎮 Konsole (wie bisher), 📋 Seitenleiste (Bereiche links, Kacheln als Raster) und 🎠 Karussell
  (die gewählte Kachel groß in der Mitte). Die Bedienung bleibt überall gleich. Die Eltern legen fest, welche Farben und
  Ansichten es gibt. Mit der Abend-Automatik wird die Startseite ab einer Uhrzeit von selbst dunkel. Spiele, Player und der
  Elternbereich bleiben immer dunkel.
- **Wetter:** Oben rechts steht das Wetter in einer Zeile mit Symbol, Temperatur und „Regen ab 16:15“ oder „trocken ab 18:00“.
  Die Kachel „Wetter“ zeigt dazu die nächsten zwölf Stunden, fünf Tage, „Wann können wir raus?“ (trockene Zeiten bei
  Tageslicht), einen Anzieh-Tipp und bei trockenem Wetter ein Spiel für draußen aus den Kinderwelten. Die Daten kommen von
  Open-Meteo, ohne Konto und ohne Schlüssel, nach denselben Regen-Regeln wie im Familien Dashboard. Den Ort suchen die Eltern
  einmal auf der Eltern-Seite.
- **Schule (Klassenkiste):** Die Kachel „Schule“ zeigt die heutigen Stunden mit Ausfall und Vertretung, die offenen
  Hausaufgaben, Termine, Klassennachrichten und den nächsten Schultag. Der Fernseher liest nur, mit der Anmeldung des
  Kindes: Er hakt nichts ab und markiert nichts als gelesen. Neue Hausaufgaben, Nachrichten und Ausfälle meldet er einmal,
  am Fernseher und auf Wunsch per Telegram an die Eltern. Abends kommt der Morgen-Check: erste Stunde und Hausaufgaben bis
  morgen.
- **Geschichten & Rätsel (Kinderwelten):** Die Inhalte der Familienfabrik erscheinen als eigene Seite: Geschichten und frei
  lesbare Bücher kapitelweise in großer Schrift zum Selberlesen, die Kinder-News der Familienfabrik, Spiele für draußen und
  das Rätsel des Tages. Alles wird nur gelesen und braucht keine Anmeldung.
- **Kinder-News:** Es erscheinen nur Quellen, die die Eltern einzeln einschalten (logo!, Duda.news, Kruschel, Kleine
  Kinderzeitung). Ab Werk sind alle aus. Gezeigt werden Überschrift und kurzer Text, ohne Links und Bilder.
- Alle neuen Seiten starten ausgeschaltet und erscheinen erst, wenn die Eltern sie einschalten (Menü → Aussehen, Wetter &
  Schule).

## 4.6.0 – Gaming-Zeit, alles ein- und ausschaltbar, Ferien per Knopf, Karaoke im Takt (23.11.2026)

- **Bildschirmzeit und Gaming-Zeit:** Neben der Bildschirmzeit des Tages gibt es eine Gaming-Zeit als Teil davon (Vorgabe
  45 / 75 Minuten). Ist sie aufgebraucht, gehen Spiele nicht mehr, Filme und Lernen aber schon. Bonus und Lernbonus gelten
  für beide. Retro-Spiele und die Spiele im Spielzimmer (Snake, Memory, Drei Gewinnt, Farben-Echo, Zu zweit, Mit Handys
  spielen) zählen jetzt zur Gaming-Zeit.
- **Vier Zeitarten je App:** Bildschirmzeit · Gaming-Zeit · nur eigenes Limit (kostet keine Bildschirmzeit, hat aber eine
  eigene Höchstgrenze) · kein Limit. Sperrzeiten gelten weiter für alle.
- **Alles ein- und ausschaltbar:** Auch die eingebauten Spiele und Kacheln (Snake, Malen, Nachrichten, Wecker, Karaoke …)
  stehen jetzt unter Menü → Apps & Kacheln, mit Schalter, Zeitart, Limit, Sperrzeiten und Bewegungspause.
- **Bewegungspause je Angebot:** Für jede App und jedes Spiel einzeln an oder aus (z. B. bei Spielen ja, beim Film nein).
- **Erinnerungen mit Ferien-Schalter:** immer · nicht in den Ferien (Sportsachen, Training) · nur in den Ferien.
- **Ferien per Knopf:** Bundesland wählen, „📅 Ferien eintragen“ – die amtlichen Ferien der Kultusministerkonferenz und
  auf Wunsch die gesetzlichen Feiertage stehen für die kommenden Schuljahre drin, mit „jedes Jahr automatisch“ auch
  künftige. Kein fremder Dienst; neue Schuljahre kommen mit den Updates. Eigene freie Tage bleiben erhalten.
- **Karaoke markiert die gesungene Zeile:** Die Zeitmarken je Zeile aus der Klassenkiste kommen jetzt mit; die aktuelle
  Zeile leuchtet und steht in der Mitte, „[Refrain]“ erscheint als Überschrift. Bisher lief der Text nur gleichmäßig über
  die Liedlänge und passte deshalb nicht zum Gesang. Lieder ohne Marken laufen wie bisher.

## 4.5.0 – Eltern-Seite neu sortiert, mit richtigem Menü (23.11.2026)

- **Eltern-Seite am Handy neu aufgebaut:** Unten liegen nur noch drei Knöpfe – 🏠 Heute, ⚙️ Menü, 📊 Statistik. Das Menü
  sortiert alle Einstellungen in vier Gruppen (Alltag · Familie und Kontakte · Was es am Fernseher gibt · Technik und
  Hilfe) mit zwölf klar benannten Bereichen statt langer Sammelseiten. Jede Kachel zeigt kurz den Stand, orange heißt:
  Hier fehlt etwas (z. B. Speicher voll, Ordner fehlt).
- **Zurück funktioniert wie gewohnt:** „‹ Menü“ oben im Bereich und die Zurück-Taste bzw. Wischgeste des Handys führen
  zurück ins Menü; Lesezeichen alter Reiter landen am passenden neuen Ort.
- Bluetooth-Kopfhörer-Schalter von „Heute“ nach „Gerät & Ton“ verschoben, damit „Heute“ übersichtlich bleibt.
- Handbuch, Anleitung und Bilder auf das neue Menü umgestellt.

## 4.4.0 – Fotos und Sprachnachrichten, Telegram für Eltern, Fotoalbum, Karaoke, Mikro-Spiele (23.11.2026)

- **Fotos, Sprachnachrichten, Musik und Videos per Telegram:** Sie erscheinen groß am Fernseher (Ton und Video spielen
  einmal von selbst). In der Kachel Nachrichten öffnet OK sie wieder; Fotos lassen sich mit „⭐ Ins Album“ behalten.
  Recht je Kontakt („Fotos, Sprachnachrichten und Videos erlaubt“, Eltern immer). Nach 7 Tagen löscht der Pi sie selbst.
- **Befehle für Eltern im Chat mit dem Bot:** `/status`, `/zeit 15|30|frei`, `/sperren`, `/freigeben`, `/gutenacht`,
  `/aus`, `/foto` (Bild vom Fernseher aufs Handy), `/bericht`, `/hilfe` – nur von Eltern-Kontakten.
- **Meldungen an die Eltern** (je Elternteil abschaltbar): Spielzeit aufgebraucht, Nachrichten mit Freunden, Gutschein
  eingelöst, Wecker aus, „✔ gelesen“, dazu der **Tagesbericht** am Abend (Uhrzeit einstellbar).
- **Sperrzeiten:** Nachrichten der Eltern kommen auch in Sperrzeiten an und lassen sich beantworten, aber ohne Gong
  (abschaltbar). Nachrichten von Freunden zählen in der Sperrzeit nur in der Glocke mit; lesen und antworten erst danach.
- **Bilder schicken:** Gemalte Bilder und Album-Fotos lassen sich an freigegebene Kontakte schicken (Malen → Galerie,
  Fotoalbum).
- **🖼️ Fotoalbum:** Neue Kachel (wenn die Eltern es erlauben). Das Kind wählt Bilder aus einem Foto-Ordner der Eltern
  (FileBrowser-Freigabe), aus seinem Album und aus seinen Zeichnungen (⭐) und schaltet sie selbst als
  Bildschirmschoner ein – z. B. wenn Freunde zu Besuch sind.
- **Speicherplatz des Kindes:** Die Eltern stellen ein Limit für Zeichnungen und Album ein; ist es voll, muss das Kind
  erst alte Bilder löschen (Fotoalbum oder Malen-Galerie). Das Album ist Teil der Sicherung.
- **🎤 Karaoke** mit den Liedern der Klassenkiste: eigener Player für den Fernseher (großer Text im Takt des Liedes,
  Musik, Pause, Spulen, Mikro-Sterne). Der Fernseher nutzt die bestehende Anmeldung in der Klassenkiste-Kachel und liest
  nur; die Anmeldung bleibt im Speicher des Pi und geht nie an einen Browser.
- **Neue Mikro-Spiele im Spielraum:** Lautstärke-Rakete und Klatsch-Rhythmus. Mikro-Spiele gehen auch ganz ohne Handy.
- **Wecker repariert:** Am klingelnden Wecker war jede Taste außer STOP „Schlummern“ – auch die Pfeile, mit denen man
  „Aus“ wählen wollte. Jetzt wählen die Pfeile zwischen „Noch 5 Minuten“ und „Wecker aus“, OK bestätigt, STOP schaltet aus.

## 4.3.0 – Mit Handys spielen, Telegram für Freunde, Bluetooth-Kopfhörer (23.11.2026)

- **📱 Mit Handys spielen:** Neue Kachel im Bereich Spiele (nur wenn die Eltern es auf der Eltern-Seite unter
  „Mehr → Handy-Spiele“ erlauben; Vorgabe aus). Der Fernseher zeigt einen QR-Code, jeder scannt ihn und spielt am
  eigenen Handy mit, das Kind mit der Fernbedienung. Fünf eigene Spiele:
  - **Buzzer-Runde** – wer zuerst drückt, darf antworten,
  - **Familien-Quizrennen** – richtige Antworten bringen die Figur voran (Gemischt, Einmaleins, Englisch, eure eigenen
    Quizfragen; „Ich bin noch klein“ gibt mehr Zeit),
  - **Malen & Raten** – einer malt am Handy, der Fernseher zeigt es live, die anderen raten,
  - **Raumschiff-Rettung** – gemeinsam: jedes Handy hat einen Teil des Handbuchs oder der Schalter,
  - **Ton-Treffer** – der Fernseher spielt eine Tonfolge, der Spieler am Zug singt sie ins USB-Mikro am Fernseher
    (Handy-Mikrofone gehen im Browser nur über HTTPS).
  Der Zugang fürs Heimnetz (Port 8767) ist nur offen, solange am Fernseher ein Spiel läuft, und kann nur das Spiel.
  Der Raum schließt bei Sperrzeit, Zeitende oder nach zwei Stunden. Nichts über die Mitspieler wird gespeichert.
  QR-Codes erzeugt der Pi selbst (`server/fernsehfranzi/qr.py`, nur Standardbibliothek).
- **Telegram mit Absender und Empfänger:** Am Fernseher steht groß, von wem eine Nachricht kommt (Symbol und Name).
  „Nachricht schreiben“ fragt „An wen?“. Grenzen je Kontakt: Eltern dürfen alles; neue Kontakte (z. B. eine Freundin)
  starten streng – empfangen ja, das Kind darf ihnen erst nach Freigabe schreiben, eigene Texte je Kontakt, Nachrichten
  auf Wunsch nur außerhalb der Sperrzeiten (sie warten bis danach). Die Eltern lesen den Verlauf je Kontakt mit
  (Eltern-Seite → Mehr → Telegram); der Verlauf ist nicht in der Sicherung.
- **🎧 Bluetooth-Kopfhörer:** Verbindet sich ein Kopfhörer, wechselt der Ton dorthin, danach zurück zu HDMI bzw. Klinke
  (wie am Handy). Dritte Tonwahl im Elternbereich und auf der Eltern-Seite, Automatik abschaltbar.
- **Installationsanleitung** für einen frisch aufgesetzten Pi: `docs/INSTALLATION.md`.
- Handbuch, Anleitungen, Kurzanleitung und README mit den Neuerungen; neue Bildschirmfotos.

## 4.2.1 – Bewegungspause unterbricht den Film nicht mehr (22.11.2026)

- **Bewegungspause:** Läuft ein Film (YouTube, eigene Videos), ein Hörbuch oder ein Spiel der Startseite, legt sich die
  Pause jetzt darüber und hält nur an. Danach geht es an derselben Stelle weiter. Vorher lud die Startseite neu, der
  Player wurde geschlossen und der Film begann von vorn. Auf fremden Webseiten wechselt der Fernseher wie bisher zur
  Startseite.
- **YouTube merkt sich die Stelle** bei langen Videos (ab 10 Minuten): Beim nächsten Öffnen läuft das Video dort weiter
  („Weiter ab 25:00“), `0` startet von vorn.
- **Handbuch und Kurzanleitung:** `web/handbuch.pdf` (Buch mit Umschlag, Inhaltsverzeichnis mit Seitenzahlen, drei
  Teilen und Anhang, viele Bildschirmfotos) und `web/kurzanleitung.pdf` (eine DIN-A4-Seite für neben den Fernseher).
  Beide auf der Eltern-Seite unter „Mehr → Gerät“. Erzeugt mit `make anleitung`, Bilder mit `make bildschirmfotos`.
- Bewegungspause auf der Startseite zeigte unten „null“ – behoben.
- **Eigene Videos:** Denselben Film im Ordner wieder öffnen = an der gemerkten Stelle weiter (bisher nur über
  „Weiterschauen“).

## 4.2.0 – Scraper, mehr RAM für Retro-Spiele, Eltern-Seite aufgeräumt (22.11.2026)

- **Bilder für Retro-Spiele (Scraper):** Eltern-Seite → Mehr → „Retro-Spiele: Bilder“ → „Bilder für neue Spiele holen“
  (nach dem Hochladen neuer ROMs), außerdem jede Nacht um 4 Uhr. Quelle: die freien Spielbilder des libretro-Projekts,
  ohne Konto und ohne Installation; holt nur, was fehlt, und lässt Gespielt/Favoriten/eigene Namen unangetastet. Läuft
  als eigener Dienst (`fernsehfranzi-scraper.service`), nie während RetroPie läuft. EmulationStations eigener Scraper bleibt
  im Kiosk-Modus aus.
- **Mehr RAM für Retro-Spiele:** Solange RetroPie läuft, ist Chromium jetzt **ganz aus** (gibt 400–600 MiB frei; 4.1 hatte
  nur eine leere Seite gezeigt – zu wenig für Zelda/N64). Danach startet die Startseite neu („Willkommen zurück!“, auf dem
  Pi 3 dauert das einige Sekunden).
- **Bildschirmfoto wird angezeigt** (die Sicherheitsregel der Eltern-Seite blockierte das Bild; betraf auch die
  Vorschau der Zeichnungen).
- **Lange Listen klappen ein** („… weitere anzeigen“): Nachrichten und Erinnerungen, Gutscheine, eingelöste Gutscheine,
  Zeitstrahl der Statistik, Internetseiten, Sticker.

## 4.1.1 – C64-Tasten und Amiga (22.11.2026)

- **C64:** Feuer lag nur auf B – jetzt **A = Feuer** (wie in der Kinder-Anleitung), Y/X = Leertaste, Start = F1,
  LB = anderer Joystick-Anschluss. Beim Start eines C64-Spiels aus FernsehFranzi blendet RetroArch die Tasten ein.
  Eingespielt mit `make retro-einrichten`.
- **Amiga:** Amiberry startete gar nicht (Bibliothek libserialport0 fehlte) → `make amiga-bibliothek`. CD32-Spiele aus
  ZIPs werden entpackt und starten fest als CD32 (`make retro-einrichten`) – erst, wenn die CD32-Kickstart-ROMs da sind
  (vorerst nicht: keine ROMs, die CD32-Spiele bleiben unverändert).

## 4.1.0 – Das finale Update (22.11.2026)

- **Bluetooth-Tastatur (iPazzPort):** Sondertasten belegt (am Gerät mitgelesen): Home = Startseite, Zurück = STOP,
  Lupe = Nachrichten, Menü = Elternbereich, Lautstärke/Stumm (auch im Retro-Spiel, mit der Höchstgrenze der Eltern),
  ⏮ ⏭ = voriger/nächster Titel bzw. Video. Chromium führt Zurück/Home/Menü nicht mehr selbst aus (hwdb im Kernel).
- **Kiosk-Lücke geschlossen:** Mit einer echten Tastatur öffneten Strg+Alt+T und Super+Enter ein Terminal (labwc-Kürzel).
  Der Kiosk hat jetzt eine eigene labwc-Konfiguration ohne Kürzel und mit leeren Menüs.
- **Nachrichten: eigene Texte** mit der Tastatur schreiben (Enter senden, STOP abbrechen, höchstens 300 Zeichen,
  Pfeile bewegen keinen Cursor). Eltern-Seite → Telegram: „Eigene Texte erlauben“ (an).
- **YouTube:** Untertitel von Anfang an aus, `U` schaltet sie ein/aus. Im Pause-Bild steht die gelieferte Qualität.
- **Retro-Spiele flüssiger:** Solange RetroPie läuft, zeigt Chromium eine skriptlose Seite und gibt Speicher frei
  (vorher ~600 MiB und ein Drittel eines Kerns, Swap auf der SD-Karte). N64 mit sparsameren Einstellungen
  (Bildpuffer-Kopien, Bilder doppeln – Werte aus dem Kern am Gerät gelesen).
- **WLAN-Energiesparen aus** (der Pi hängt im WLAN, nicht am Kabel) – weniger Aussetzer bei Videos.
- **Eltern-Seite:** 📷 „Was läuft gerade?“ (Bild vom Fernseher, am TV erscheint kurz „📷“), **Bluetooth** (suchen,
  koppeln, trennen, entfernen – ohne SSH, nur die Eltern), **Sicherung** herunterladen/einspielen (ohne PIN und Token,
  alter Stand wird vorher auf dem Pi gesichert).
- `make v3-pruefen` prüft die 4.1-Teile mit; Anleitungen (Eltern und Kind) auf 4.1.

## 4.0.1 – YouTube-Playlisten (22.11.2026)

- **Playlisten spielen jetzt:** Beim Hinzufügen liest der Pi die Videos der Playlist aus, der Player spielt sie selbst
  nacheinander (Titel mit 1/n, → und ← blättern). Schon gespeicherte Playlisten werden beim ersten Öffnen am TV
  nachträglich ausgelesen. Die YouTube-eigene Playlist-Einbettung lief nicht zuverlässig.
- Eltern-Seite: Die YouTube-App zeigt nicht mehr fälschlich „nicht eingerichtet“ (sie braucht keine Startadresse).

## 4.0.0 – Statistik, Sonnenaufgang, Telegram, Video-Player und mehr (Nacht zum 22.11.2026)

- **Nutzungs-Statistik** auf der Eltern-Seite (neuer Reiter): je App und Stunde, Heute/7/30 Tage, meistgenutzte Apps
  (offen und aktiv), Tageszeit, jeder Tag, Zeitstrahl eines Tages, eingelöste Gutscheine. Daten bleiben auf dem Pi (62 Tage).
- **Sonnenaufgang** vor dem Wecken: Der Fernseher geht 5–30 Minuten vorher an und wird von schwarz über rot/orange zu
  warmweiß (je Wecker einstellbar, Kind und Eltern).
- **Sternen-Abwehr** (unter „Zu zweit“): gemeinsam oder allein gegen Wellen von Außerirdischen. STOP schließt jetzt auch
  das Quiz-Duell (blieb vorher hängen).
- **Startseite selbst gestalten** (Kachel „Gestalten“): Lieblinge ⭐ vorne in „Start“, sechs Hintergründe.
- **Hörbuch-Player mit Covern** (cover.jpg/folder.jpg oder erstes Bild im Ordner), groß beim Abspielen.
- **Musik-Akademie: Aufnehmen und anhören** (Mikro oder USB-Audio wie der Rock-Band-Adapter), nur lokal, höchstens drei.
- **Telegram:** Nachrichten erlaubter Chats erscheinen am TV (bleiben bis OK), das Kind antwortet mit vorbereiteten Texten.
  Neue Chats „Erlauben“ auf der Eltern-Seite; der Bot-Token wird nie an den Browser zurückgegeben.
- **Plex mit Kinderprofil:** Name auf der Eltern-Seite (Apps → Plex); kiosk.py wählt das Profil in der Auswahl.
- **Memory mit eigenen Bildern** (ab 6 gemalten Bildern aus „Malen“).
- **Eigener Video-Player** aus einer FileBrowser-Freigabe (neue App „🎬 Video-Ordner“): Ordner mit Cover, Weiterschauen,
  Spulen; am Pi 3 am besten H.264-.mp4 bis 720p.

## 3.5.0 – Gutscheine, Wecker, YouTube-Bereich, Musik-Akademie, neue Startseite (21.11.2026)

Zusammen mit 3.4 ausgeliefert.

- **Gutschein-Codes:** Eltern erstellen und drucken 6-stellige Codes (normal: +Minuten, nur außerhalb der Sperrzeiten;
  besonders: so viele Minuten geht alles, auch nachts, nichts zählt). Einmal einlösbar, gegen Raten gebremst.
- **Wecker** „wie im Handy“: Das Kind stellt Weckzeit, Tage, Ton und Lautstärke am Fernseher ein; Eltern setzen Grenzen
  (erlaubt, frühestens, höchste Lautstärke), den Weckton-Ordner (FileBrowser) und können die Wecker bearbeiten.
  Zur Weckzeit Fernseher an (CEC „on“ + Eingang), Ton wird lauter, OK schlummern, STOP aus; Gute-Nacht-Ruhe endet.
- **YouTube-Bereich:** Kategorien mit Videos/Playlists (Link einfügen, Titel per oEmbed). Eigener Player
  (youtube-nocookie, IFrame-API, controls aus): Fokus nie im Video, Pause und Ende verdeckt – keine Vorschläge, keine Suche.
- **Musik-Akademie** statt Bass-Ecke: Bass (alles bisher), Gitarre (Stimmgerät, Akkord-Bilder, Wechsel-Trainer), Keyboard
  (Klaviatur, Akkorde, Nachspielen mit Mikro), Singen (Ton treffen, Tonleiter), Song-Suche auf ultimate-guitar.com.
- **Neue Startseite im Konsolen-Stil:** Bereiche-Leiste (Start, Spiele, Lernen, Musik, Filme & YouTube, Retro), großer Titel
  der gewählten Kachel, je Bereich eine Reihe (die gewählte groß). Bereich je App auf der Eltern-Seite wählbar.
- Eltern-Seite: Gutscheine (Mehr), Wecker (Regeln), YouTube-Bereich (Apps), Reiter „Musik“.
- **Nachrichten-Kachel mit Glocke:** neue und alte Nachrichten/Erinnerungen wie am Handy, Glocke mit Zahl oben rechts.
- **Mehr Inhalte:** 30 neue Witze, 35 neue Englisch-Wörter, Lernspiele „Rechnen“ (bis 20/100, geteilt) und „Wissens-Quiz“.
- **Eltern erweitern:** eigene Witze und Quizfragen, eigene Sticker (von Hand vergeben).

## 3.4.0 – Neues Zeitmanagement, Gute Nacht mit Hörbüchern, Erinnerungen bis OK (21.11.2026)

- **Zeitarten je App:** „frei“ (kein Timer) oder „Timer“ (allgemeiner Tages-Timer), optional **höchstens X min**
  (Schultag / freier Tag) zusätzlich. Games behält seine Grenze. Die alte Unterscheidung „zählt nicht / zählt nie“ entfällt.
- **Sperrzeiten statt Zeitfenster und Schlafenszeit:** frei anlegbar (Name, von–bis auch über Mitternacht, Wochentage,
  „nicht in den Ferien“, „Nachtruhe“). Gelten für **alle** Apps, außer eine App ist dort erlaubt (je Sperrzeit oder „immer“).
  Wirken jetzt auch **während der Nutzung**: Hinweis 10/5/1 min vorher, dann wird die App beendet (Retro speichert).
- **Beginn der Nachtruhe:** „Gute Nacht automatisch“ öffnet den Player mit Sleep-Frage (ohne Wahl: Alarm nach 5/15/25 min,
  nach 30 min Countdown, dann Fernseher aus) – sonst 15-s-Countdown mit **Fernseher aus / an / Gute Nacht**.
- **Gute Nacht = Hörbuch-Player** (ersetzt die Hörbücher-Kachel und die Plex-Gute-Nacht): immer erlaubt, auch beim
  Mittagsschlaf; öffnet direkt mit „Weiterhören“ und Sleep-Frage. „🌙 Gute Nacht starten“ auf der Eltern-Seite.
- **Einschlafbild:** sehr dunkler, langsam animierter Sternenhimmel mit Mondsichel, Sternschnuppen und einem Vogel
  (10 Bilder/s, hellste Stelle ~45 %). **Im Gute-Nacht-Modus keine Töne** (kein Gong, kein Countdown, keine Warnungen).
- **Erinnerungen und Nachrichten bleiben stehen, bis OK** gedrückt wird; alle 5 min wieder (mit Gong, auch in Plex und
  im Retro-Spiel), nicht im Gute-Nacht-Modus. Eltern-Seite zeigt „gesehen um …“.
- **Gesperrte Kacheln nur grau mit Symbol** (⏳ 🌙 🏫 🚫 🔒 🕐 ⚙️) statt Text.
- Übernahme der 3.3-Daten beim ersten Start (Zeitfenster/Schlafenszeit → „Nacht“ und „Schule“, Hörbücher → Gute Nacht,
  Stand „Weiterhören“ bleibt), Hinweis „Bitte Zeitregeln prüfen“ auf der Eltern-Seite.
- Eltern-Seite: Regeln mit Timer, Sperrzeiten, Gute Nacht; Apps mit Zeitart, höchstens-Minuten, „erlaubt in“.

## 3.3.0 – Hörbücher mit Sleep-Timer, neue Eltern-Seite (21.11.2026)

- **Hörbücher-Player** (Kachel „Hörbücher“, ersetzt die Plex-Hörspiele-Kachel): spielt MP3s aus einem Ordner im Heimnetz –
  die Eltern tragen einen FileBrowser-Freigabelink ein (nur lesen, nichts am Server ändern). Ordner = Hörbücher,
  Dateien = Wiedergabeliste (natürlich sortiert), „Weiterhören“ an der gemerkten Stelle, ⏪/⏩ 30 s.
  **Bei jedem PLAY muss die Sleep-Zeit gewählt werden**; nach 30 s wird das Bild schwarz, am Ende leiser werden,
  anhalten, Stelle merken, Fernseher aus (CEC). Zählt nie zur Zeit; zur Schlafenszeit kein Gong/Abschalten mittendrin.
  Längster Sleep-Timer einstellbar (Vorgabe 60 min). Dateien kommen über den Server (Range/Spulen), die Whitelist bleibt zu.
- Damit kann **Plex auf „zählt zur Spielzeit“** stehen (Zeitfenster gilt – nachts keine Filme/Partymusik).
- **Eltern-Seite am Handy neu:** Leiste unten (Heute · Regeln · Apps · Bass · Mehr), echte Felder statt
  „a | b | c“-Zeilen (Uhrzeit, Wochentage antippen, Datum für Ferien, Song-Karten), speichert von selbst mit
  „Gespeichert ✔“, Fehler rot am Feld, Apps als aufklappbare Karten, neue App oder Hörbuch-Ordner anlegen, Wochenbalken.
- Anleitungen: Hörbücher (Eltern und Kind), neue Eltern-Seite, Plex mit Limit.

## 3.2.2 – Retro: Amiga, C64, Scraper; Ton-Vorgabe HDMI (21.11.2026)

- **Amiga-Spiele starten:** Amiberry sucht die Kickstart-ROMs in `~/RetroPie/BIOS/amiga` unter `kick13.rom` usw. – sie lagen
  nur als `Kickstart 1.3.rom` in `BIOS`, Amiberry nahm deshalb den AROS-Ersatz. Neu: `make retro-einrichten-plan` /
  `make retro-einrichten` (zwei Rückfragen, nur Kiosk-Benutzer) kopiert sie unter den richtigen Namen.
  CD32-Spiele brauchen zusätzlich CD32-ROMs (Anleitung B4a).
- **C64:** Kassetten im Schnelllauf laden (`vice_autoloadwarp`), Tastenbelegung in beiden Anleitungen.
- „+Start Amiberry.sh“ (alle Amiberry-Einstellungen) aus der Spieleliste nach `~/RetroPie/eltern/`.
- EXIT/Guide im Amiga-Spiel beenden nur das Spiel (wie bei RetroArch), nicht ganz RetroPie.
- **Scraper wieder erreichbar:** mit dem Entsperr-Code in EmulationStation freischalten; der Kiosk-Modus kommt bei jedem
  RetroPie-Start von selbst zurück (vorher erst beim nächsten Deploy).
- **Ton-Vorgabe HDMI** statt Klinke (das Gerät läuft meist über den Fernseher); ROT/GRÜN und die gespeicherte Wahl bleiben.

## 3.2.1 – Kinder-Anleitung, Retro-Kiosk (21.11.2026)

- **Anleitung für das Kind** (PDF, 7 Seiten, große Schrift): Fernbedienung, Controller, Spielzimmer, Bass-Ecke, Lernen,
  Retro-Spiele mit allen Tricks (Schnellspeichern Xbox+RB, Laden Xbox+LB, Speicherplatz Xbox+←/→, Spiel-Menü Xbox+X,
  Beenden Xbox+Start) – ohne PIN, Einstellungen oder Ausschalten. Verlinkt auf der Eltern-Seite.
- **Retro-Spiele ohne „Blödsinn“:** RetroArch-Kiosk-Modus (keine Einstellungen im Spielmenü) und EmulationStation-Kiosk-Modus
  (kein Neustart/Herunterfahren/Einstellungen) mit zufälligem Entsperr-Code statt des bekannten Konami-Codes.
  Xbox-Taste in der Spieleliste führt zur Startseite (im Spiel bleibt sie die Hotkey-Taste).
- install.sh: Entsperr-Code ohne `tr | head` (brach unter `pipefail` ab, erster Deploy von 3.2.1 am 21.11.); Test mit
  denselben Shell-Regeln wie am Gerät. Deploy-Meldung: Rückweg führt auf den Stand vor dem Deploy (nicht 2.5).
- kiosk.py wartet beim Hochfahren bis zu 45 s auf Chromium (der Pi 3 braucht nach dem Start länger als 5 s);
  ein abgebrochener Aufruf beim Herunterfahren wird nicht mehr als Fehler geloggt.

## 3.2.0 – Lernspiele, Hörspiele, Eltern-Seite übersichtlicher (21.11.2026)

- **Lernspiele** (neue Kachel im Spielzimmer, eigene Entwürfe): Einmaleins (Reihe wählbar oder gemischt, Serie),
  Uhr lesen (analoge Uhr, volle/halbe/Viertel/5 Minuten), Englisch (Wörter mit Bildern, Farben, Zahlen).
  Zählen als Lernen (Lernbonus mit Lern-Check), drei neue Sticker.
- **Hörspiel-Ecke** als eigene Kachel (zählt nie zur Zeit); Adresse trägt ihr auf der Eltern-Seite ein.
  Vorhandene Kataloge bekommen sie einmal ergänzt.
- **Apps selbst anlegen und löschen** auf der Eltern-Seite (Name, Adresse, Zählweise, Symbol, Lernangebot ja/nein).
- **Whitelist vervollständigen ohne Mitschnitt am Gerät:** kiosk.py meldet, welche Seiten der Browser lädt und welche
  die Whitelist blockiert. Die Eltern-Seite zeigt sie mit „Erlauben“ (einzeln oder alle blockierten).
- **Eltern-Seite übersichtlicher:** Sprungleiste (Heute, Zeit & Regeln, Apps, Internet, Bilder & Sticker, System),
  Bestätigung nach jedem Speichern, Fehler deutlich sichtbar.
- **Elternbereich am Fernseher** in beschrifteten Reihen (Zeit, Fernseher, Einstellungen, Gerät; ↑ ↓ zwischen den Reihen)
  und mit der Adresse der Eltern-Seite fürs Handy.
- **Ton bleibt, wo er hingehört:** Vorgabe Klinke; der Server prüft alle 30 s, ob der gewählte Ausgang noch Standard ist,
  und stellt ihn sonst zurück – ein USB-Gerät (Mikrofon) kann ihn nicht umstellen.
- **Anleitung als PDF** (Teil A für die Familie, Teil B Technik), verlinkt auf der Eltern-Seite und schon auf der
  Anmeldeseite; Quelle `docs/anleitung/anleitung.html`, neu erzeugen mit `make anleitung`.
- **Admin-Konto statt vollem sudo:** `make admin-einrichten` legt ein Admin-Konto an (Name/Passwort tippt der Admin),
  prüft es und nimmt erst dann dem Kiosk-Benutzer das volle sudo; Deploys und Installationen laufen danach über das
  Admin-Konto (`ADMIN_HOST` in config/pi.mk, sudo mit Passwort). Zurück mit `make admin-zurueck`.
- **YouTube-Links der Bass-Ecke** öffnen als reiner Player (youtube-nocookie, ohne Kommentare und Empfehlungen);
  die nötigen YouTube-Hosts kommen automatisch in die Whitelist. Videos starten ohne extra Tastendruck.
- **YouTube flüssig auf dem Pi 3:** Die Erweiterung meldet YouTube „nur H.264, höchstens 30 fps und 720p“ – dann liefert
  YouTube ein Format, das der Pi in Hardware dekodiert (vorher VP9/AV1, ruckelig).
- **Lautstärke am Pi regeln:** GELB, dann ↑/↓ (Controller: Back halten + ↑/↓), auch in Plex und im Spiel, mit Anzeige.
  Die Lautstärketasten der TV-Fernbedienung kommen beim Pi nicht an (nur am Fernseher selbst). Höchstlautstärke auf der
  Eltern-Seite; leiser/lauter auch dort und im Elternbereich.
- **Gong** bei Nachrichten, Erinnerungen, Schlafenszeit, Lern-Check und Zeitwarnungen – überall hörbar.
- **Spieltöne lauter**, Farben-Echo spielt zu jeder Farbe einen eigenen Ton (A-Dur), so lang wie das Leuchten –
  man kann nach Gehör spielen.
- **Bass-Ecke mit Mikrofon:** Griffbrett-Trainer „mit dem Bass“ (das Mikro erkennt den gespielten Ton) und
  „Nachspielen“ (Ton anhören, auf dem Bass nachspielen). Getestet mit einem simulierten Mikrofon in Chromium.
- Neu: `make retro-plan` / `make retro-erweitern` – C64 (lr-vice) und Amiga (Amiberry) über RetroPie-Setup nachinstallieren
  (zwei Rückfragen). Am Gerät liegen 17 C64- und 4 Amiga-Spiele, die bisher nicht angezeigt werden.

## 3.1.1 – EXIT führt in Plex zurück zum Launcher (21.11.2026)

- **EXIT auf der Fernbedienung** führt auf Webseiten (Plex, Kavita, Klassenkiste …) wieder direkt zur Startseite – wie in 2.x.
  In 3.0/3.1 war es dort „Browser zurück“ und blieb in Plex hängen. Eine Ebene zurück in Plex: STOP.
  Jeder EXIT-Druck steht jetzt im Log der Eingabe.

### Ebenfalls in 3.1.1

- **Lernbonus nur für echtes Lernen:** Eine Lern-App nur zu öffnen bringt nichts mehr. Es zählen nur aktive Minuten
  (mindestens 3 Tastendrücke pro Minute, einstellbar). Alle 10 Minuten fragt der Fernseher mitten in der Lernseite
  „Bist du noch beim Lernen? Drück nacheinander ← ↑ →“ (zufällige Folge, 90 s Zeit). Erst danach wird die Zeit
  gutgeschrieben, sonst verfällt sie. Die Eltern-Seite zeigt bestätigte, offene und verfallene Minuten.
  eingabe.py und die Startseite melden dafür alle 5 s die gedrückten Tasten.
- GRÜN („Klinke“) wählt immer die eingebaute Klinke – auch mit angeschlossener USB-Soundkarte (Mikrofon fürs Stimmgerät).

## 3.1.0 – Bass lernen, Familie, Spiele zu zweit (21.11.2026)

- **Bass-Ecke ausgebaut:** Stimmgerät mit Mikrofon (und Mithören), Tempo-Trainer (alle 4 Takte +2 bis zum Ziel),
  Rhythmus-Spiel (OK im Takt, Trefferquote), Gehörbildung (höher/tiefer, welche Saite), Tabs lesen (Quiz),
  Übungs-Tagebuch mit Serie, Plex-Bibliotheken „Bass-Unterricht“ und „Backing Tracks“ direkt aus der Bass-Ecke.
- **Nachricht ans TV** von der Eltern-Seite – erscheint überall (Startseite, Plex, RetroPie-Spiel).
- **Erinnerungen** zu festen Zeiten und Tagen · **Schlafenszeit** mit Vorwarnung, danach Startseite und Fernseher aus ·
  **Fernseher aus bei Zeitende** (wählbar) – Fernseher aus über HDMI-CEC (eingabe.py).
- **Gute-Nacht-Modus:** Hörspiel aus Plex, Bild gedimmt, nach X Minuten Fernseher aus; zählt nie zur Zeit.
- **Bewegungspause** nach langer Spielzeit am Stück, mit Übungen und Countdown (wählbar, Vorgabe aus).
- **Lernzeit verdient Spielzeit** (Klassenkiste, Kinderwelten, Bass-Ecke): einstellbar, mit Tageshöchstwert.
- **Sticker-Album** mit 18 Stickern aus Spielen, Malen, Bass, Lernen und Bewegungspausen.
- **Zu zweit:** Ballduell, Snake-Duell, Quiz-Duell – zweiter Controller bekommt eigene Tasten (W A S D, F).
- **Zuletzt gespielt / Lieblingsspiele** aus RetroPie als eigene Reihe, startet das Spiel direkt (Unit fernsehfranzi-spiel).
- **Spiele auf dem Gerät repariert:** Dem Fernseh-Pi fehlt jede Emoji-Schrift – Memory-Bilder, ⭕ in Drei Gewinnt und
  alle Symbole waren unsichtbar. Die Startseite bringt jetzt einen Ausschnitt aus Noto Color Emoji (OFL 1.1, 119 KB) mit,
  geprüft in einem Browser ohne Emoji-Schrift für alle Spiele (`tests/test_spiele_wie_am_geraet.py`). Der Fernseher
  spielt in Drei Gewinnt jetzt mit 🔵 (vorher ⭕, rot wie ❌). Meldungen ans TV ohne Emojis (Plex/RetroArch).
- Kachel öffnete sich nach Mausklick + Enter ein zweites Mal – behoben.
- Kinderwelten-Adresse korrigiert (`https://app.familienfabrik.at/`); ein vorhandener Katalog wird beim Start angepasst.
- **Bildschirmschoner** mit den eigenen Zeichnungen · Eltern-Seite markiert **neue Zeichnungen**.
- Systemteil: Unit `fernsehfranzi-spiel.service` + Helfer `spiel-start`, sudo-Regel ergänzt, Chromium erlaubt das
  Mikrofon nur für die Startseite. `install.sh` entfernt Nullbytes nach Stromausfall und schreibt mit `sync`.

## 3.0.0 – Neuer Aufbau (21.11.2026)

Neuer Aufbau neben 2.5 (`familyhub/` bleibt bis zur Umstellung unverändert):

- **Server** (`server/fernsehfranzi/`, nur Standardbibliothek): Startseite unter `http://127.0.0.1:8765/`, Kiosk-API
  (POST + Token + Herkunftsprüfung), App-Katalog `apps.json`, Datenordner `~/fernsehfranzi-daten` mit Schema-Migration,
  Übernahme der 2.x-Einstellungen, Adressen, Ton und Zeichnungen.
- **Zeitkonto**: Tagesbudget, RetroPie-Grenze, Zeitfenster, Warnungen bei 10/5/1 min – auf der Startseite, in jeder
  Webseite (Hinweis über die DevTools-Pipe) und im RetroArch-Spiel; bei Zeitende Spielstand speichern, dann zurück.
  Leerlauf zählt nicht; Internet ohne Eingabe → nach 10 min zurück. Plex und Dashboard zählen nie, Lernen nicht.
- **Elternbereich** (BLAU oder Back+Start lang): PIN als PBKDF2-Hash mit wachsender Sperre; Bonuszeit, „heute ohne
  Limit“, Fernseher sperren, Ton, Linux-Desktop (nur am TV, zurück nach 20 min), Neustart/Aus, PIN ändern.
  **Eltern-Seite im Heimnetz** (Handy/PC, Vorgabe aus, Port einstellbar): Zeitregeln, Apps, Whitelist mit Export
  für Pi-hole/Fritzbox, Zeichnungen, Bass-Songs, Wochenübersicht.
- **Browser-Whitelist** als Chromium-Richtlinie (Vorgabe an) und Kiosk-Härtung (keine DevTools, Downloads, Dateidialoge …).
- **Neue Startseite** mit Restzeit, gesperrten Kacheln mit Grund; Kacheln **Klassenkiste** und **Kinderwelten** neu.
- **Spielzimmer**: Snake (Tempostufen, weich, Eingabepuffer), Memory (3 Größen, zu zweit), Drei Gewinnt (3 Stufen,
  zu zweit), Malen mit Galerie (Füllen, Rückgängig, Pinsel), Witz, **Farben-Echo** (neu), **Bass-Ecke** (neu: Stimmen,
  Metronom, Griffbrett-Trainer, Songs mit Video/Tabs/Backing Track von den Eltern).
- **eingabe.py** ersetzt cec_keys.py: Fernbedienung und Controller (Xbox, 8BitDo per Bluetooth …) als Tastatur,
  EXIT lang / Guide = Zur Startseite, Pfeile navigieren immer.
- **kiosk.py** ersetzt kiosk.sh: Chromium über die DevTools-Pipe (kein offener Port), Seiten wechseln ohne Neustart,
  Desktop-Apps, lädt sich nach Updates selbst neu. Taskleiste/Desktop laufen nicht mehr hinter dem Kiosk.
- `install/install.sh` (mit Sicherung) und `install/rollback.sh`; `make v3-plan|v3-deploy|v3-pruefen|v3-rollback`.
- Die Richtlinie „DevTools aus“ ist vorerst nicht gesetzt: ungeprüft, ob sie die Steuer-Pipe von kiosk.py sperrt.

## 2.5.4 – Kiosk lädt Updates selbst (21.11.2026)

- **Fehler behoben:** Neue Chromium-Schalter aus `kiosk.sh` wirkten erst nach einem Neustart des Geräts, weil
  die Kiosk-Schleife weiterlief. Deshalb war die Plex-Erweiterung aus 2.5.2/2.5.3 auf dem Gerät nie aktiv –
  in Plex fing Plex die Pfeile weiter ab. Jetzt lädt sich `kiosk.sh` nach dem Chromium-Neustart beim Deploy selbst neu.
  (Einmalig nötig: ein Neustart des Geräts, damit diese neue Schleife überhaupt läuft.)

## 2.5.3 – Plex: Pfeile navigieren immer, Player über eigene Tasten (21.11.2026)

- **Die Pfeiltasten navigieren in Plex immer**, auch wenn Musik oder ein Film läuft (vorher übernahm der
  Player die Pfeile für Lautstärke und Spulen, sobald etwas lief – auch bei der kleinen Musikleiste).
- Den Player steuern die eigenen Tasten der Fernbedienung: **PLAY/PAUSE** = Abspielen/Pause,
  **Vorlauf** = 30 s vor, **Rücklauf** = 10 s zurück. STOP bleibt bei Plex (zurück/schließen).
  Im Suchfeld wird „p“ normal getippt.

## 2.5.2 – Fernbedienung in Plex (21.11.2026)

- **Pfeiltasten in Plex:** Plex belegt die Pfeile auf der fertigen Oberfläche selbst (hoch/runter = Lautstärke)
  und blockierte damit das Springen von 2.5.1. Eine kleine lokale Chromium-Erweiterung
  (`familyhub/fernbedienung/`, nur für Plex: Port 32400 `/web/` und `app.plex.tv`) hält die Pfeile von Plex fern,
  sodass Chromium von Element zu Element springt; OK klickt auch auf Kacheln ohne eigenen Link.
  Läuft ein Video, behält der Plex-Player seine Tasten (Spulen, Lautstärke). Im Suchfeld bewegen ← → den Cursor.
- Wirkt nach dem nächsten Neustart des Geräts (kiosk.sh).

## 2.5.1 – Ton und Fernbedienung auf Webseiten (21.11.2026)

- **Ton umschalten repariert:** `pactl` statt `wpctl`. Auf dem Gerät stürzt `wpctl set-default` ab
  (WirePlumber 0.4.13 zu PipeWire 1.2.7) – die Farbtasten wirkten deshalb schon in 2.4 nicht.
- **Fernbedienung auf Webseiten:** Chromium läuft mit `--enable-spatial-navigation`. Pfeile springen in Plex,
  Kavita und im Dashboard von Link zu Link, OK klickt. Die Startseite fängt ihre Pfeiltasten selbst ab und
  verhält sich wie bisher (Test). Wirkt nach dem nächsten Neustart des Geräts (kiosk.sh läuft als Schleife).

## 2.5.0 – Hotfix: RetroPie auf der Konsole, Ton per Taste (20.11.2026)

- **RetroPie startet wieder Spiele.** EmulationStation läuft jetzt auf einer eigenen Konsole (tty8)
  als systemd-Unit `fernsehfranzi-retropie.service`, mit echtem Terminal und eigener Login-Sitzung,
  ohne X11/Wayland und ohne Display-Variablen. Vorher scheiterte jedes Spiel, weil RetroArch
  weder Terminal noch Grafik bekam.
- Die Startseite bleibt während des Spielens offen und ist nach dem Beenden sofort wieder da
  (Konsolenwechsel statt Chromium-Neustart). Der Controller wirkt in dieser Zeit nicht auf die Startseite.
- Der Server startet RetroPie nur noch über eine eng begrenzte sudo-Regel und beendet keinen Chromium mehr.
- **Ton umschalten per Taste mit Anzeige:** ROT = Fernseher (HDMI), GRÜN = Klinke – jetzt überall,
  auch in Plex und im Spiel. Ein kurzer Ton auf dem neuen Ausgang bestätigt die Wahl,
  die Startseite zeigt sie an. Die Wahl bleibt nach einem Neustart erhalten.
- Fernbedienung in EmulationStation: Pfeile, OK, STOP (zurück), PAUSE (Menü).
- Aktionen am Server nur noch per POST; Anfragen von Webseiten fremder Herkunft werden abgewiesen.
- Die Fußzeile zeigt die Version, die der Server aus `VERSION` liest.
- Ausliefern richtet den Systemteil mit Sicherung ein (`install/system.sh`); `make rollback` nimmt
  Code und Systemteil zurück; `make pi-probe` startet einen Probelauf ohne Dateien zu schreiben.
- Rückfallweg B (Desktop fürs Spielen beenden) vorbereitet und per `RETROPIE_WEG=B` wählbar; Vorgabe ist Weg A.
- Die Startseite erkennt ein Spiel auch dann, wenn sie während des Spielens nicht nachgefragt hat
  (`/status` meldet die Startmarke der Unit) – sonst käme nach dem Spielen fälschlich „nicht gestartet“.
- Die Status-Abfrage alle 2 s schreibt nicht mehr ins Server-Log (sonst ~43 000 Zeilen am Tag).
- `system.sh`: Eine Warnung von `systemd-analyze verify` bricht den Systemschritt nicht mehr halb ab.
- Probelauf: `WorkingDirectory=~` in Anführungszeichen – Bash hatte daraus unter sudo `/root` gemacht
  (erster Probelauf am 21.11. endete mit `status=200/CHDIR`, bevor EmulationStation startete).
- EXIT ohne installierte Unit beendet nur noch Prozesse namens `emulationstation` (`pkill -x` statt `-f`).

## 2.4.0 – Fundament (20.11.2026)

Basis ist die bestehende Version 2.4 (`familyhub/`), unverändert im Verhalten.

- Version 2.4 in das Repository übernommen (Ordner `familyhub/`, Aufbau wie auf dem Gerät).
- Persönliche Werte aus `index.html` herausgelöst: Name, Untertitel, Adressen von Plex,
  Familien Dashboard und Kavita sowie Geburtstage stehen jetzt in `config/einstellungen.js`
  (nicht im Repository, Vorlage `config/beispiel/einstellungen.js`). Fehlt eine Adresse,
  zeigt die Kachel einen freundlichen Hinweis statt einer Fehlerseite.
- `VERSION` als einzige Versionsquelle; ein Test prüft, dass Startseite und Server dieselbe Version nennen.
- `Makefile`: `check` (Python, JavaScript, shellcheck, systemd-Units, sudoers, JSON, Suche nach
  privaten Daten), `test` (Unittests, Oberflächentests mit Playwright, Navigationstest aus 2.4),
  `pi-check-vor`/`pi-check-nach` (lesender Vorher-/Nachher-Vergleich des Geräts),
  `deploy-plan` (Trockenlauf) und `deploy` (zwei Rückfragen am Terminal, Sicherung, Protokoll).
- Neue Tests unter `tests/`: Server-Endpunkte, Startseite mit und ohne Konfiguration,
  Vergleichslogik der Geräteprüfung, Repository-Regeln.
- Kleine Korrekturen an Prüfskripten aus 2.4 (shellcheck-Warnungen), Hinweis im Test-README,
  dass der alte Server-Smoke-Test jeden Chromium des Rechners beendet.
- systemd-Units ohne Ausführungsrecht.
