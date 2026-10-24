# Mehr Wow – experimentelle Regiefassungen

Der Experimentmodus erzeugt aus einer fertigen, gegebenenfalls bereits
korrigierten Comic-Ausgabe eine eigene Variante. Ziel sind ein stärkerer
emotionaler Bogen, verständliche Konflikte, Vorbereitung und Wendepunkte,
prägnante Dialoge sowie abwechslungsreicher Bildrhythmus. Mehr Blut oder Wut
allein ersetzt diese Arbeit nicht.

## Bedienung

1. Unter **Erzeugte Ausgaben** die gewünschte aktuelle Fassung wählen. Nach
   Bildkorrekturen oder neuer Beschriftung deren gespeicherte Ausgabe verwenden.
   Ungespeicherte Änderungen im Storyeditor gehören noch nicht zur Bildausgabe.
2. **Mehr Wow · Experiment** anklicken.
3. Den Spielraum wählen:
   - **Dramaturgie und Dialoge frei zuspitzen:** Handlungskern und Figuren bleiben,
     Ereignisse, Szenen, Wendepunkte, Erzählertexte und Dialoge dürfen sich ändern.
   - **Nur Bildinszenierung verstärken:** Handlung, Reihenfolge und Wortlaut der
     Erzählertexte und Sprechblasen bleiben erhalten. Die Bilder werden neu inszeniert.
4. Entscheiden, ob das bisherige Ergebnis der Geschichte erhalten bleiben soll.
   Bei reiner Inszenierung bleibt es immer erhalten. In der freien Fassung kann
   ausdrücklich auch ein anderer Schluss erlaubt werden.
5. Regler von **0 bis 3** wählen: Spannung, Wut/emotionale Reibung, Action,
   Blut/sichtbare Konsequenzen, Dialoge mit Biss und filmische Bildwirkung.
   0 bedeutet keine zusätzliche Verstärkung, 1 fein, 2 deutlich, 3 radikal.
   Vorlagen sind **Mehr Sog**, **Wut & Action**, **Mehr Herz** und **Düstere Härte**.
6. Eine eigene Regieanweisung ergänzen, zum Beispiel:

   > Weniger erklären. Ria soll eine echte Entscheidung treffen müssen. Erst
   > eine stille Nahaufnahme, dann ein harter Wechsel in die Totale. Mehr Wut
   > zwischen den Figuren, aber keine zusätzlichen Verletzungen. Der Schluss
   > soll nachhallen und die bisherige Auflösung erhalten.

7. **Experiment als neue Ausgabe erzeugen** anklicken. Erst dieser Klick startet
   den Auftrag. Er plant eine neue Fassung und zeichnet alle Kacheln neu.
8. Die mit **Experiment** markierte Ausgabe auswählen und prüfen. Unter
   **Regie und Änderungen des Experiments** stehen der Regieplan und die
   Änderungen je Kachel. **Original / Basis öffnen** wechselt zur vorherigen
   Ausgabe, sofern sie noch in der Auswahl vorhanden ist.

Eine überzeugende Wirkung ist subjektiv und muss am Ergebnis geprüft werden.
Der Modus ist ausdrücklich experimentell. Ein Versuch kann auch schlechter
werden als seine Basis; diese bleibt deshalb separat verfügbar. Die neue
Fassung kann ihrerseits die Basis für ein weiteres Experiment sein.

## Was bleibt geschützt?

- Originaldateien, Originaltext, Originalausgabe und deren gespeicherte Story.
- Figurenbibliothek, Figuren-IDs und vorhandene private Referenzbilder.
- Feedback der Basis und die bestehenden Lernregeln; das Experiment schreibt
  keine eigene Bewertung oder automatischen Erfahrungen in die Basis zurück.
- Gespeicherte ComfyUI-Workflows und Veröffentlichungsziele.

Die Kachelanzahl und der Bildstil stammen aus der ausgewählten Ausgabe.
Es gibt einen neuen Auftrag mit eigenem Seed, eigenen Dateien und einem
Snapshot der Basis. Die Originalzeichnungen werden in dessen privaten
Checkpoints gesichert. Die Neufassung braucht danach keine Dateien der Basis
zum Rendern mehr. Ein gespeicherter Versionsabdruck verhindert, dass unbemerkt
auf einer inzwischen geänderten Basis gestartet wird.

Die Variante erhält keine Zuordnung zur bisherigen Story-ID oder zur
kanonischen Serienfolge. Vorhandene Serienangaben bleiben als Herkunft unter
`based_on_series` dokumentiert. Wer die Variante später als verbindliche Story
nutzen will, übernimmt sie ausdrücklich mit den vorhandenen Importfunktionen.

## Prüfungen und Ablauf

1. Aktuelle Szenen, Dialoge, Figurenreferenzen und Rohbilder sichern.
2. Ausgewählte Originalkacheln als Bildtafel analysieren und einen Regieplan
   entwickeln. Die Bildtafel ist eine Stichprobe, keine vollständige Bildprüfung.
   Falls das lokale Bildmodell nicht verfügbar ist, erfolgt eine protokollierte
   Textanalyse als Ersatz.
3. Szenen in Abschnitten mit höchstens sechs Kacheln schreiben.
4. Je Abschnitt Motivation, Ursache und Wirkung, Kontinuität, Sprecher und
   Schlusswirkung prüfen; bei Befunden einmal nachbessern. Bleiben konkrete
   Fehler, stoppt der Auftrag vor der Bilderzeugung.
5. Die vorhandene Deutschprüfung und die Layoutprüfung anwenden. Zu lange,
   nicht passende Texte oder unbekannte Figuren-IDs werden abgewiesen.
6. Neue Bilder mit den übernommenen Figurenreferenzen zeichnen und als
   eigenständige Ausgabe exportieren. Die abschließende Sichtprüfung erfolgt
   durch dich, einschließlich Sprechblasenpositionen und Lesbarkeit.

Koordinaten und geschützte Bereiche der alten Bilder werden nicht auf neue
Kompositionen übertragen. Neue Blasen erhalten die normalen Ausgangspositionen.
Bei reiner Inszenierung bleiben dabei Wortlaut, Sprecher und Blasenstil erhalten.
Nach dem Zeichnen lassen sich die Blasen wie gewohnt verschieben.

Die freie Fassung wird als fiktionale Experimentvariante gekennzeichnet. Sie ist
keine faktentreue journalistische Überarbeitung und keine Behauptung über eine
historisch überlieferte Originalhandlung. Das gilt auch bei einer realen oder
historischen Textgrundlage. Veröffentlichung erst nach redaktioneller Prüfung.

Alle Modellaufrufe verwenden die bereits konfigurierten lokalen Modelle.
Es wird kein externer Modellanbieter hinzugefügt.

## API und Dateien

Bestehende Bearer-Authentifizierung verwenden.

- `GET /jobs/<id>/experiment-options`: Basisversion, Titel, Anzahl und Regler.
- `POST /jobs/<id>/experiment`: eigene Variante mit `version`, `mode`
  (`rewrite` oder `staging`), `keep_ending`, `levels` und optional `notes` starten.
- `levels` enthält `tension`, `anger`, `action`, `blood`, `dialogue`, `visuals`,
  jeweils als ganze Zahl von 0 bis 3.
- Ein laufendes Experiment derselben Basis verhindert einen parallelen
  Doppelauftrag. Nach Abschluss oder Fehler ist ein weiterer Versuch möglich.

`experiment-input.json` enthält den Snapshot und die Regieeinstellungen.
`experiment-report.json` dokumentiert Basis-ID, Versionsabdruck, Regieplan,
Änderungsgründe und Prüfhinweise. Unter `reports/` stehen Modellantworten und
Sprachentscheidungen. Fertige Varianten enthalten die üblichen Comic-,
Einzelkachel-, Teilseiten- und PDF-Dateien sowie das Gesamtpaket.

## Erzählweisen mit bekannten Vorbildern

Zusätzlich zum Bildstil gibt es im Experimentdialog **Erzählweise / Vorbild**:

| Auswahl | Redaktioneller Schwerpunkt |
|---|---|
| Passend zur Geschichte | Ziel, Widerstand, Entscheidung und Konsequenz aus der eigenen Vorlage entwickeln |
| Emotionales Abenteuer · Vorbild One Piece | Persönlicher Wunsch, Bindung, Rückschlag und emotional eingelöster Höhepunkt |
| Abenteuer & Humor · Vorbild Asterix | Verständliches Abenteuerziel, unterschiedliche Stimmen, vorbereitete komische Zuspitzung und Schluss-Pointe |
| Düstere Spannung · Vorbild Batman | Offene Frage, sichtbare Hinweise, innere Unsicherheit, folgenschwere Entscheidung und nachhallender Schluss |

Das sind selbst formulierte Erzählwerkzeuge, abgeleitet aus bekannten Reihen.
Sie verändern nicht automatisch den vorhandenen Zeichenstil. Namen, Figuren,
Kostüme und konkrete Handlungen der Vorbilder werden nicht in die Regieanweisung
übernommen. Eigene Figuren und Welt bleiben die Grundlage. Die Auswahl löst
keinen Download oder Trainingslauf aus; Modellgewichte bleiben unverändert.

Die Regieplanung muss jetzt konkret benennen:

- Was die Hauptfigur will.
- Was bei einem Scheitern auf dem Spiel steht.
- Welches Hindernis ihr entgegensteht.
- Welche Entscheidung den Verlauf verändert.
- Welche Ereignisfolgen verbindlich bleiben, etwa Tod, Verletzungen oder
  Veränderungen an Kleidung und Gegenständen.
- Was die einzelnen Abschnitte erzählen und welche Veränderung sie bewirken.

Ein verbindlicher Plan verteilt Einstieg, Ziel, Druck, Wendung, Entscheidung und
Konsequenz auf die tatsächliche Kachelanzahl. Bei kurzen Comics werden Aufgaben
zusammengefasst; umfangreiche Comics erhalten entsprechend größere Bereiche.
Jede neue Kachel muss ihre konkrete Veränderung und ihr Bildmittel benennen.
Die Prüfung betrachtet die tatsächliche Szene, nicht nur diese Selbstauskunft.
Bewusste Ruhe ist zulässig; bedeutungslose Wiederholung soll korrigiert werden.
Der vollständige Plan steht im Änderungsbericht.

Für eine andere Dramaturgie **Dramaturgie und Dialoge frei zuspitzen** wählen.
Bei **nur Bildkomposition** bleiben Handlung und Wortlaut festgeschrieben; die
Erzählmechaniken dürfen dort nur vorhandene Inhalte stärker sichtbar machen.

Diese Vorgaben ersetzen keine Sichtprüfung der generierten Bilder. Zusätzliche
Gliedmaßen, verwechselte Figuren oder ein nach seinem Tod wieder aktiver Drache
sind konkrete Fehler. Die letzten beiden betreffen außerdem die Kontinuität,
die der Plan ausdrücklich führen muss. Anatomiefehler können weiterhin über
**Ein Bild korrigieren** in einer neuen Ausgabe gezielt überarbeitet werden.

### Quellen und Herleitung

Die Auswahl ist keine aktuelle Weltrangliste und kein offizielles Erfolgsrezept.
Offizielle Verlagsbeschreibungen und dokumentierte Reichweite dienen als
Referenz; die operativen Regeln sind eigene redaktionelle Ableitungen.

- **One Piece:** Shueisha dokumentiert für 2022 eine weltweite Auflage von
  510 Millionen Exemplaren. [Verlagschronik](https://www.shueisha.co.jp/history/detail/2022.html).
  Die offizielle Veröffentlichung *Episode of EASTBLUE* beschreibt Träume,
  gemeinsame Reisen und emotionale Bindungen als zentrale Motive.
  [Offizielle Produktbeschreibung](https://avex.jp/onepiece/products/detail.php?artist_cd=OPLCX&id=1016296).
- **Asterix:** Hachette nennt 400 Millionen verkaufte Alben und beschreibt die
  Verbindung von wiederkehrenden Figuren und neuen Abenteuerreisen.
  [Verlagsbeschreibung](https://www.hachette.com/actualite/asterix-et-obelix-repartent-en-voyage-le-23-octobre/).
  Eine weitere offizielle Albumvorstellung verbindet ein scheinbar positives
  Versprechen mit verborgenen Absichten.
  [L’Iris blanc](https://www.hachette.com/actualite/liris-blanc-le-nouvel-album-dasterix-aux-editions-albert-rene/).
- **Batman:** DC beschreibt in *Gotham Nocturne* Ermittlungen, schleichende
  Bedrohung und innere Konflikte.
  [Offizielle Albumseite](https://www.dc.com/graphic-novels/detective-comics-2016/batman-detective-comics-vol-1-gotham-nocturne-overture).
  Sichtbare Hinweise, Beweise und Rätsel stehen im *Mystery Casebook* im Vordergrund.
  [Offizielle Beschreibung](https://www.dc.com/graphic-novels/batmans-mystery-casebook).

## Zur vorherigen Fassung zurückkehren

Bei einer ausgewählten Experiment-Ausgabe steht **← Vorherige Fassung** direkt
bei den Download-, Teilen- und Sprechblasen-Schaltflächen. Der Wechsel ist schon
während des Experiments und auch nach einem Fehler möglich. Er öffnet die
unveränderte unmittelbare Basis, ohne etwas neu zu zeichnen oder die Variante
zu löschen. Ein laufender Auftrag läuft dabei weiter. Über die Auswahlliste
kann jederzeit wieder zum Experiment gewechselt werden. Bei mehreren aufeinander
aufbauenden Experimenten führt der Knopf jeweils eine Stufe zurück.

## Feste Texte: Widersprüche und Stilhinweise trennen

Bei **nur Bildkomposition** haben Handlung und Wortlaut Vorrang vor Intensität,
Erzählvorbild und Regieplan. Vor der Prüfung werden die Bildbeschreibungen deshalb
noch einmal eigenständig aus der Originalhandlung, den festen Erzählertexten und
Sprechblasen entworfen. Die widersprüchliche Experimentbeschreibung wird dafür
nicht wieder als Vorlage verwendet. Jede Kachel zeigt genau einen Zeitpunkt.
Ein bereits bezwungener Gegner wird nach dem Kampf gezeigt, nicht erneut mitten
im Angriff. Die festen Texte und Sprecher werden dabei nicht geändert.

Die anschließende Prüfung trennt:

- **Belegte Widersprüche:** falscher Bildzeitpunkt, widersprüchliche Ereignisse,
  falsche Identitäten oder Sprecher, gebrochene Kontinuität, falsches Ende oder
  nicht lesbare Beschriftung. Der Befund muss die betroffene Kachel und einen
  vorhandenen Bildtext wörtlich nennen. Bei Bild-Text-Konflikten muss zusätzlich
  der passende Erzähler- oder Sprechblasentext belegt werden.
- **Optionale Regievorschläge:** mehr Subtext, weniger erklärende Texte, stärkere
  Bildwirkung oder andere persönliche Stilpräferenzen. Sie werden im Bericht
  unter **Optionale Regievorschläge** angezeigt und brechen den Auftrag nicht ab.

Eine sichtbare Figur braucht keine Sprechblase. Leere Figurenzustände sind kein
Fehler, solange Aussehen und Kleidung unverändert aus den Profilen folgen.
Bei einem belegten verbleibenden Bild-Text-Konflikt korrigiert der feste Modus
gezielt die betreffende Bildbeschreibung. Bleibt danach ein belegter Widerspruch,
stoppt die Erzeugung weiterhin vor dem Zeichnen. Modellprüfungen bleiben fehlbar;
die abschließende Sichtprüfung wird dadurch nicht ersetzt.

Bei einem fehlgeschlagenen Experiment lautet die Schaltfläche
**Experiment erneut versuchen**. Sie öffnet die bisherigen Einstellungen und
verwendet die erhaltene Basis für einen neuen eigenen Versuch. Erst ein weiterer
Klick auf **Experiment als neue Ausgabe erzeugen** startet diesen Versuch.

Nicht belegbare Kritikerbehauptungen bleiben als ausdrücklich unbelegte Hinweise
im Bericht sichtbar. Sie lösen keine Bildkorrektur und keinen Abbruch aus.
Die Anpassung fester Texte ändert ausschließlich Bildbeschreibungen; gespeicherte
Figurenzustände bleiben erhalten.
