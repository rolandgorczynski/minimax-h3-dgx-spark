# Formatvorlage für ein Comic-Skript

Diese Vorlage beschreibt ein gut prüfbares Eingabeformat für deine nächste
Testgeschichte. Im neuen [Quellengenerator](Comic_Quellengenerator.md) wird diese Struktur direkt
als Storyboard übernommen. Im gewöhnlichen Feld „Geschichte / Artikel“
verarbeitet die Software das eingefügte Skript weiterhin als Ausgangstext
und erstellt daraus einen Szenenplan. Kachelgrenzen, Seitenwünsche
und Regieanweisungen müssen deshalb im erzeugten Plan kontrolliert werden.

## 1. Angaben zur gesamten Geschichte

Am Anfang einmal angeben:

- **Titel** der Geschichte.
- **Autor** oder Pseudonym.
- **Kachelanzahl** als positive ganze Zahl. Dieselbe Zahl im Dashboard wählen.
- **Bildstil** als gemeinsame Beschreibung für alle Kacheln. Im Dashboard den
  dazu passenden verfügbaren Stil auswählen. Die Stilbeschreibung im Text
  ersetzt die dortige Auswahl nicht automatisch.
- **Stimmung und Farbwelt**, zum Beispiel warme Aquarellfarben und ruhiges Licht.
- **Erzähler**, falls vorhanden: Name und Erzählperspektive. Angeben, ob er nur
  als Erzählerkasten erscheint oder auch sichtbar im Bild stehen soll.

Ein gewünschtes Buchformat oder eine Seitenaufteilung darf zusätzlich angegeben
werden. Das ist zunächst eine Gestaltungsabsicht. Der aktuelle Buchexport bietet
6 × 9 und 8,5 × 11 Zoll sowie eine, zwei oder vier Kacheln pro Druckseite.
Eine frei gesetzte A4-Seite mit unterschiedlich großen Panels wird dadurch
noch nicht automatisch erzeugt.

## 2. Figuren vor den Kacheln definieren

Jede wiederkehrende Figur erhält einen eindeutigen Namen. Diesen Namen überall
gleich schreiben, auch bei Dialogen. Keine wechselnden Bezeichnungen wie
„Markus“, „der Junge“ und „Marcus“ für dieselbe Figur verwenden.

Pro Figur angeben:

- **Name**.
- **Aussehen:** Alter oder Altersbereich, Gesicht, Haare und wichtige Merkmale.
- **Kleidung:** Farben und wiederkehrende Kleidungsstücke.
- **Persönlichkeit und Vorgeschichte:** kurz, soweit für die Geschichte wichtig.
- **Gesinnung:** optional; darf ausdrücklich „nicht festgelegt“ sein.
- **Kontinuität:** Was bleibt gleich? Welche Änderungen passieren ab welcher Kachel?

Eine Figur, die zunächst nur zu hören ist, behält ihren eigentlichen Namen.
Beispiel: Sprecher „Ria“, Sichtbarkeit „außerhalb des Bildes“; keine zusätzliche
Figur mit dem Namen „Unbekannte Stimme“ anlegen.

Ein vorhandenes Referenzbild über die Figurenverwaltung zuordnen. Ein Dateiname
im Skript allein lädt noch kein Bild hoch.

## 3. Jede Kachel getrennt beschreiben

Die Kacheln durchgehend nummerieren: **KACHEL 1**, **KACHEL 2** und so weiter.
Auch bei einer neuen gewünschten Buchseite nicht wieder bei 1 beginnen.

Für jede Kachel dieselben Felder benutzen:

```text
KACHEL 1: Kurzer Szenentitel
Gewünschte Buchseite: 1 (optional)
Ort und Zeit: ...
Sichtbare Figuren: ...
Bildbeschreibung: ...
Erzählertext: ... / keiner
Dialog 1:
  Sprecher: ...
  Sprechweise: normal / schreiend / flüsternd
  Sichtbarkeit: im Bild / außerhalb des Bildes
  Text: „...“
Kontinuität / Änderung: ... / keine
```

Bei weiteren Sprechblasen „Dialog 2“, „Dialog 3“ ergänzen. Ohne Gespräch
„Dialoge: keine“ schreiben. Die Reihenfolge der Dialoge ist die Lesereihenfolge.
Sprechweise und Sichtbarkeit sind Regieangaben und sollen nicht als Text in der
Blase stehen. Die genannten Feldnamen und Werte sind Schreibkonventionen;
sie sind aktuell keine verbindlich ausgewerteten Importbefehle.

## 4. Regeln für Bildbeschreibung und Text

- Pro Kachel einen klar darstellbaren Moment beschreiben. Mehrere aufeinander
  folgende Handlungen auf mehrere Kacheln verteilen.
- Einstellungsgröße, Handlung und wichtige Positionen nennen. Bei einem Gespräch
  möglichst die zuerst sprechende Figur links und die antwortende rechts setzen.
- Platz für Sprechblasen vorsehen. Gesichter und wichtige Handlungen sollen frei
  bleiben. Genaue Positionen können später im Sprechblaseneditor korrigiert werden.
- Den gemeinsamen Bildstil nicht in einzelnen Kacheln durch andere Stile ersetzen.
- Deutsche Bildbeschreibungen genügen. Keine zusätzlichen englischen
  Prompt-Dopplungen und keine Midjourney-Parameter wie `--ar` oder `--v` verwenden.
- Erzählertext und Gespräch getrennt halten. Ein Gespräch nicht zusätzlich im
  Erzählerkasten wiederholen.
- Nur tatsächlich gesprochene Worte in die Dialogtexte schreiben. Gedanken,
  Schilder und Briefe bei Bedarf ausdrücklich als solche kennzeichnen.
- Als Richtwert höchstens zwei kurze Sprechblasen mit jeweils etwa 10–20 Wörtern
  pro Kachel planen. Das ist keine technische Garantie; der Platz hängt auch von
  Bild, Schrift und Exportgröße ab.
- Erzählertexte knapp halten, möglichst ein kurzer Satz und höchstens 130 Zeichen
  passend zur aktuellen Szenenplanung.
- Wenn ein Gespräch mehr Raum braucht, zusätzliche Kacheln vorsehen, statt eine
  kleinere Schrift zu verlangen.
- Änderungen an Haaren, Kleidung, Verletzungen oder Gegenständen ausdrücklich
  nennen. Ohne Änderung gilt der bisherige Zustand weiter.

## 5. Vollständiges kurzes Beispiel

```text
TITEL: Das Licht im Treppenhaus
AUTOR: Mein Pseudonym
KACHELANZAHL: 2
BILDSTIL: Europäischer Comic mit klaren Konturen und sanften Aquarellflächen.
STIMMUNG UND FARBWELT: Ruhig und geheimnisvoll; kühles Blau, warmes Fensterlicht.
ERZÄHLER: Neutraler Erzähler, nur in Erzählerkästen, keine sichtbare Figur.

FIGUREN

Name: Markus
Aussehen: 17 Jahre, schmales Gesicht, kurze braune Locken, Sommersprossen.
Kleidung: Dunkelgrüne Jacke, grauer Pullover, schwarze Jeans.
Persönlichkeit und Vorgeschichte: Neugierig, hilft nach der Schule im Haus aus.
Gesinnung: Nicht festgelegt.
Kontinuität: Gesicht, Frisur und Kleidung bleiben in beiden Kacheln gleich.

Name: Ria
Aussehen: 18 Jahre, rundes Gesicht, kurze schwarze Haare, runde Brille.
Kleidung: Gelber Regenmantel, dunkelblaue Hose.
Persönlichkeit und Vorgeschichte: Aufmerksam, kennt Markus aus der Nachbarschaft.
Gesinnung: Nicht festgelegt.
Kontinuität: Gesicht, Frisur und Kleidung bleiben in beiden Kacheln gleich.

KACHEL 1: Ein Geräusch
Ort und Zeit: Treppenhaus eines alten Wohnhauses, früher Abend.
Sichtbare Figuren: Markus.
Bildbeschreibung: Halbtotale. Markus steht links auf dem Treppenabsatz und
schaut zur geschlossenen Dachbodentür rechts oben. Warmes Licht fällt durch
ein Fenster. Oberhalb seiner Schulter bleibt Platz für eine Sprechblase.
Erzählertext: Im Treppenhaus war es plötzlich still geworden.
Dialog 1:
  Sprecher: Markus
  Sprechweise: normal
  Sichtbarkeit: im Bild
  Text: „Ria? Hast du das auch gehört?“
Kontinuität / Änderung: Keine.

KACHEL 2: Die Antwort
Ort und Zeit: Derselbe Treppenabsatz, unmittelbar danach.
Sichtbare Figuren: Markus, Ria.
Bildbeschreibung: Halbtotale aus leicht verändertem Winkel. Ria steht links
neben Markus, der rechts zur Dachbodentür blickt. Ria hält eine kleine
Taschenlampe in ihrer rechten Hand. Über beiden bleibt Platz für die Blasen.
Erzählertext: Keiner.
Dialog 1:
  Sprecher: Ria
  Sprechweise: flüsternd
  Sichtbarkeit: im Bild
  Text: „Ja. Es kam vom Dachboden.“
Dialog 2:
  Sprecher: Markus
  Sprechweise: normal
  Sichtbarkeit: im Bild
  Text: „Dann sehen wir gemeinsam nach.“
Kontinuität / Änderung: Ria trägt jetzt sichtbar eine kleine Taschenlampe.
```

## 6. Deinen Test durchführen

1. Skript mit diesen Angaben schreiben und vollständig in „Geschichte / Artikel“
   einfügen. Das Feld ist aktuell auf 16.000 Zeichen begrenzt.
2. Titel, verfügbaren Stil und passende Kachelanzahl im Dashboard einstellen.
3. „Szenen erstellen“ klicken.
4. Prüfen, ob jede gewünschte Kachel vorhanden ist, Sprecher richtig zugeordnet
   sind und keine Regieanweisung im gesprochenen Text steht.
5. Szenen bei Bedarf korrigieren und erst danach die Comic-Bilder erzeugen.

Autor sowie Texte für Buchanfang und Buchende später zusätzlich im Buchformular
eintragen. Angaben im Skript werden derzeit nicht automatisch in diese Felder
übernommen.
