/* Witz: bleibt, wie er ist - erst die Frage, OK zeigt die Pointe, OK der nächste Witz. */
import { el } from "../gemeinsam.js";
import { kopf, ton } from "./kern.js";

const WITZE = [
  ["Was macht ein Pirat am Computer?", "Er drückt die Enter-Taste!"],
  ["Welches Tier kann am besten springen?", "Das Känguru – es hat immer Sprungfedern dabei."],
  ["Was ist grün und klopft an die Tür?", "Ein Klopfsalat!"],
  ["Warum können Geister so schlecht lügen?", "Weil man durch sie hindurchsieht."],
  ["Was sagt der große Stift zum kleinen Stift?", "Wachs-mal-Stift!"],
  ["Wie nennt man einen Bumerang, der nicht zurückkommt?", "Stock."],
  ["Was ist rot und schlecht für die Zähne?", "Ein Ziegelstein."],
  ["Warum summen Bienen?", "Weil sie den Text vergessen haben."],
  ["Was macht eine Wolke mit Juckreiz?", "Sie fliegt zum Wolkenkratzer."],
  ["Welcher Fisch ist der berühmteste?", "Der Stockfisch – der steht in jedem Lexikon."],
  ["Was liegt am Strand und spricht undeutlich?", "Eine Nuschel!"],
  ["Was ist orange und läuft durch den Wald?", "Eine Wanderine."],
  ["Warum ist die Tomate rot geworden?", "Weil sie die Salatsoße gesehen hat!"],
  ["Wie heißt der Bruder von Elvis?", "Zwölfis."],
  ["Was ist weiß und springt im Wald herum?", "Ein Jumpignon."],
  ["Was sitzt auf dem Baum und ruft „Aha!“?", "Ein Uhu, der gerade etwas verstanden hat."],
  ["Was ist ein Keks unter einem Baum?", "Ein schattiges Plätzchen."],
  ["Warum gehen Ameisen nicht in die Kirche?", "Weil sie In-Sekten sind."],
  ["Was macht ein Clown im Büro?", "Faxen!"],
  ["Was ist gelb und kann nicht schwimmen?", "Ein Bagger. Warum? Weil er nur einen Arm hat!"],
  ["Treffen sich zwei Kerzen. Fragt die eine:", "„Ist Wasser gefährlich?“ – „Davon kannst du ausgehen!“"],
  ["Wie nennt man ein Schaf ohne Beine?", "Eine Wolke."],
  ["Was sagt die Null zur Acht?", "Schicker Gürtel!"],
  ["Was ist braun, klebrig und läuft durch die Wüste?", "Ein Karamel."],
  /* 3.5: mehr Witze, damit es sich nicht so schnell wiederholt */
  ["Was ist grün und hüpft von Blatt zu Blatt?", "Ein Springkraut."],
  ["Warum hat der Elefant so große Ohren?", "Weil der Weihnachtsmann ihm keine Mütze schenkt."],
  ["Was macht ein Hai im Computer?", "Er surft im Netz."],
  ["Wie nennt man einen dicken Vogel?", "Eine Mampfmeise."],
  ["Was ist das Lieblingsessen von Vampiren?", "Blutorangen."],
  ["Was sagt ein Igel, wenn er einen Kaktus umarmt?", "„Mama, bist du das?“"],
  ["Warum tragen Golfer zwei Hosen?", "Falls sie ein Loch im Eins haben."],
  ["Welcher Bus ist über den Ozean gefahren?", "Kolumbus."],
  ["Was ist ein Cowboy ohne Pferd?", "Ein Sattelschlepper."],
  ["Was macht ein Schneemann im Sommer?", "Er schwitzt sich weg."],
  ["Wie heißt ein Hund, der zaubern kann?", "Labracadabrador."],
  ["Was ist gelb und schaut durchs Schlüsselloch?", "Eine Spannane."],
  ["Was sagt der Ozean zum Strand?", "Gar nichts – er winkt nur."],
  ["Warum können Seeräuber keinen Kreis zeichnen?", "Weil sie Pi raten."],
  ["Was macht eine Kuh, wenn sie Musik hört?", "Sie muht-tiert mit."],
  ["Welche Tiere sind am besten in Mathe?", "Die Rechenwürmer."],
  ["Was ist durchsichtig und riecht nach Möhren?", "Ein Häschenpups."],
  ["Wohin geht ein Fisch, wenn er Geld braucht?", "Zur Sparkasse am Meeresgrund."],
  ["Warum ist der Fußballplatz nass?", "Weil die Spieler dribbeln."],
  ["Was ist schwarz-weiß und hüpft auf und ab?", "Ein Pinguin auf dem Trampolin."],
  ["Was macht ein Pferd am Computer?", "Es klickt mit den Hufen."],
  ["Was ist ein Lieblingsfach von Schlangen?", "Zisch-Kunde."],
  ["Wie nennt man einen Löwen, der Klavier spielt?", "Ein Brüll-Konzert."],
  ["Was liegt im Gras und macht „Muh“?", "Eine Kuh im Liegestuhl."],
  ["Was ist rund und lacht?", "Eine Kicher-Erbse."],
  ["Warum gehen Bienen nicht in den Kindergarten?", "Weil sie schon summen können."],
  ["Was macht ein Pirat beim Camping?", "Er schlägt sein Zelt mit Arrr-beit auf."],
  ["Was ist grün und läuft weg?", "Ein Fluchtsalat."],
  ["Welcher Ritter trinkt am liebsten Tee?", "Sir Kamille."],
  ["Was ist klein, grün und dreieckig?", "Ein kleines grünes Dreieck."],
];

export default {
  symbol: "😄",
  oeffne(box, api) {
    const { inhalt, punkte } = kopf(box, "Witz", "OK Weiter · STOP Zurück");
    let i = Math.floor(Math.random() * WITZE.length), pointe = false;
    /* 3.5: eigene Witze der Eltern dazu (Eltern-Seite → Mehr → Eigene Inhalte) */
    api?.hole("/api/inhalte").then((d) => {
      for (const w of d.witze || []) WITZE.push([w.frage, w.pointe]);
    }).catch(() => {});
    const frage = el("div"), antwort = el("div", { class: "pointe" });
    inhalt.append(el("div", { class: "witz" }, frage, antwort));
    function zeige() {
      frage.textContent = WITZE[i][0];
      antwort.textContent = pointe ? WITZE[i][1] : "…";
      punkte.textContent = `Witz ${i + 1} von ${WITZE.length}`;
    }
    zeige();
    return {
      taste(t) {
        if (t === "Enter" || t === " " || t === "ArrowRight") {
          if (!pointe) { pointe = true; ton("ok"); } else { pointe = false; i = (i + 1) % WITZE.length; ton("bewegen"); }
          zeige();
          return true;
        }
        if (t === "ArrowLeft") { pointe = false; i = (i + WITZE.length - 1) % WITZE.length; zeige(); return true; }
        return false;
      },
      schliesse() {},
    };
  },
};
