# Comics mit beliebig vielen Kacheln als Buch exportieren

Die feste Grenze von zwölf Kacheln ist entfernt. Jede positive ganze Kachelanzahl
ist zulässig; Quelltext, Arbeitsspeicher, Speicherplatz und Rechenzeit müssen
weiterhin ausreichen. Der Ausgangstext muss genug Inhalt für die gewünschte Zahl
unterschiedlicher Szenen haben. Figuren- und Textlängengrenzen einzelner Felder
sind von der Kachelanzahl unabhängig.

Große Szenenpläne werden in Abschnitten mit höchstens acht Kacheln erstellt und
in Seiten mit je zwölf Szenen bearbeitet. Verdeckte Szenen bleiben beim Wechseln
und Speichern erhalten. Große Bildaufträge werden in Einzelkacheln ausgeführt;
bereits fertige Schritte werden über die vorhandenen Checkpoints fortgesetzt.
Vorprüfungen und Sprachprüfungen erfolgen ebenfalls abschnittsweise.

`comic.png` ist bei mehr als zwölf Kacheln eine entsprechend beschriftete Vorschau
der ersten zwölf. Alle Kacheln bleiben in `panels/` und den vollständigen
Teilseiten unter `pages/` erhalten. EPUB und Taschenbuch enthalten den ganzen
Comic. Bei großen Comics wird der vollständige Workflow nicht in jede einzelne
Kachel und Teilseite kopiert; er bleibt als Datei und in der Gesamtvorschau
enthalten. Nummern über 99 werden beim Teilen numerisch sortiert und für den
öffentlichen Bildexport mit gleich breiten Ziffern benannt.

## Bedienung im Dashboard

1. Eine fertige Comic-Ausgabe auswählen.
2. **Buch exportieren: EPUB & Taschenbuch** öffnen.
3. Buchtitel und Autor oder Pseudonym eintragen. Beide Angaben sind für den Export
   erforderlich; es wird kein Autorenname fest einprogrammiert.
4. Optional Untertitel, Verlag, ISBN für das Taschenbuch, Impressum und eigene
   Texte für Anfang und Ende eintragen. Überschriften sind frei änderbar.
5. Titelbild aus einer vorhandenen Kachel wählen; dafür wird nach Möglichkeit die
   unbeschriftete Zeichnung verwendet. Bei Bedarf einen Klappentext
   für die Rückseite eintragen.
6. Druckformat, Druckart und Kacheln pro Druckseite wählen.
7. **Buchangaben speichern** sichert nur die Angaben. **EPUB und Taschenbuch
   erstellen** startet den CPU-Export ohne LLM oder neue Bildgenerierung.
8. Prüfhinweise lesen und die gewünschten Dateien herunterladen.

Die Buchangaben gehören zur ausgewählten Comic-Ausgabe und bleiben nach einem
Neuladen erhalten. Der Export erzeugt einen eigenen Auftrag mit eigenen Dateien.
Die ursprüngliche Geschichte, Figurenbibliothek, Zeichnungen und gespeicherten
ComfyUI-Workflows bleiben erhalten. Ein späterer Export verwendet die dann im
Buchformular eingetragenen Angaben.

## Dateien

| Datei | Verwendung |
|---|---|
| `comic.epub` | Kindle-Manuskript als EPUB 3 mit festem Layout |
| `ebook-cover.jpg` | Separates Kindle-Titelbild, 1600 × 2560 Pixel |
| `taschenbuch-inhalt.pdf` | Buchblock im gewählten Druckformat, ohne Beschnitt |
| `taschenbuch-umschlag.pdf` | Rückseite, Rücken und Vorderseite in einer PDF mit Beschnitt |
| `buchpruefung.json` | Seitenzahlen, Maße, Qualitäts- und Prüfergebnisse |
| `KDP-Anleitung.txt` | Zu den Dateien passende Hinweise für KDP |
| `buchpaket.zip` | Alle Buchdateien zusammen; bei KDP die einzelnen Dateien hochladen |

Wenn die Druckprüfung Hindernisse findet, heißen die beiden Druck-PDFs
stattdessen `taschenbuch-inhalt-ENTWURF.pdf` und
`taschenbuch-umschlag-ENTWURF.pdf`. Das EPUB wird trotzdem erstellt. Ein Entwurf
wird nicht als druckfertig ausgegeben. Es werden keine vielen leeren Seiten
angehängt, um die Mindestseitenzahl künstlich zu erreichen. Bei ungerader
Seitenzahl wird genau eine Abschlussseite für die Bindung ergänzt.

## Kindle-EPUB

Das EPUB enthält einen unkomprimierten ersten `mimetype`-Eintrag, einen
Container, Paketmetadaten mit Titel, Autor und Sprache Deutsch, eine Navigation,
ein Titelbild sowie eine XHTML-Seite je Buchseite. Die Comic-Kacheln werden als
JPEG eingebettet. Festes Layout, Comic-Metadaten, Links-nach-rechts-Leserichtung
und Kindle-Regionen zur Vergrößerung sind gesetzt. Texte für Vorwort, Impressum
und Nachwort werden bei Bedarf auf mehrere Seiten verteilt. Private Workflows,
Figurenreferenzen und technische PNG-Textmetadaten sind nicht Teil des EPUB.

Die Containerstruktur, XML-Dateien und internen Verweise werden beim Export
geprüft. Die erzeugte technische Testausgabe wurde zusätzlich mit EPUBCheck 5.4.0
ohne Fehler oder Warnungen geprüft. Das ersetzt die abschließende Kontrolle in
Kindle Previewer und der KDP-Vorschau nicht. Die Annahme eines konkreten Buches
durch Amazon wird durch diese Software nicht behauptet oder simuliert.

## Taschenbuch und Druckprüfung

Unterstützt werden zunächst:

- **6 × 9 Zoll** beziehungsweise 15,24 × 22,86 cm.
- **8,5 × 11 Zoll** beziehungsweise 21,59 × 27,94 cm.
- Weißes Papier mit Premiumfarbe, Standardfarbe oder schwarzer Druckfarbe.
- Eine oder zwei Kacheln untereinander oder vier Kacheln im Raster pro Druckseite.

Der Buchblock hat genau das gewählte Endformat und keinen Beschnitt. Innenränder
richten sich nach der tatsächlichen Seitenzahl; bei umfangreichem Vor- oder
Nachwort wird der Satz mit dem erforderlichen größeren Bundsteg erneut berechnet.
Schrift im Buchsatz ist eingebettet. Comic-Bilder werden auf 300 dpi für die
gewählte Druckgröße aufbereitet. Liegt die tatsächliche Auflösung der vorhandenen
Kachel darunter, nennt der Bericht die rechnerische Ursprungsauflösung ausdrücklich:
Hochskalieren erzeugt keine neuen Bilddetails. Vor dem Verkauf eine Druckprobe
prüfen. Für die Seitenzahl des Taschenbuchs gelten weiterhin die KDP-Grenzen,
auch wenn die Software keine feste Kachelgrenze hat.

Die Druckprüfung berücksichtigt unter anderem:

- Mindestens 24 Seiten für Premiumfarbe und Schwarzweiß; mindestens 72 für
  Standardfarbe.
- Höchstens 828 Seiten bei 6 × 9 Zoll mit Premiumfarbe oder Schwarzweiß,
  höchstens 600 bei Standardfarbe. Bei 8,5 × 11 Zoll höchstens 590 Seiten für
  Premiumfarbe und Schwarzweiß, 600 für Standardfarbe.
- Mindestens sieben Punkt für die aus den Kacheln abgeleitete Beschriftung.
  Vier kleine Kacheln auf einer kleinen Druckseite können deshalb einen
  Druckentwurf statt einer freigegebenen Druckdatei ergeben.
- Das KDP-Dateilimit von 650 MB je Druck-PDF.

Der Umschlag umfasst die Rückseite, den anhand von Seitenzahl und Papierart
berechneten Rücken und die Vorderseite. Außen werden 0,125 Zoll Beschnitt
berücksichtigt. Unter 80 Seiten wird kein Rückentext gesetzt. Die Rückseite hat
Platz für den automatisch von KDP gesetzten Barcode. Es wird keine ISBN erfunden.
Die ISBN kann vorab eingetragen oder während der Einrichtung bei KDP festgelegt
werden. Die Angaben bei KDP müssen zu Format, Papierart, Titel, Autor und
Seitenzahl der Exportdateien passen.

## KDP: Prüfung und Veröffentlichung

Der Stand der hinterlegten Maß- und Seitenregeln wurde am **23. Oktober 2026**
gegen die folgenden offiziellen Quellen geprüft:

- [Kindle-Comics mit festem Layout](https://kdp.amazon.com/en_US/help/topic/G9GSTY4LTRT39D4Z)
- [Taschenbuch-Dateivorgaben](https://kdp.amazon.com/en_US/help/topic/G201857950)
- [Formate, Beschnitt und Ränder](https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6)
- [Umschlag und Rückenberechnung](https://kdp.amazon.com/en_US/help/topic/G201953020)
- [Inhaltsvorgaben und Angaben zu KI-generierten Inhalten](https://kdp.amazon.com/en_US/help/topic/G200672390)

Die Software meldet nichts bei Amazon an und veröffentlicht nichts. Kontoangaben,
Veröffentlichungsrechte, ISBN-Auswahl, Angaben zu KI-generierten Bildern und die
abschließende Freigabe erfolgen bei KDP. Eine formell korrekte Datei ist keine
Zusage der inhaltlichen Annahme durch Amazon.

## API

| Aufruf | Zweck |
|---|---|
| `GET /jobs/<COMIC-ID>/book-settings` | Gespeicherte Angaben, Kachelzahl, letzter Buchauftrag |
| `PUT /jobs/<COMIC-ID>/book-settings` | Buchangaben ohne Export speichern |
| `POST /jobs/<COMIC-ID>/book-export` | Eigenen Buchauftrag anlegen |
| `GET /jobs/<BUCHAUFTRAG-ID>` | Fortschritt, Prüfbericht und Downloadadressen |

Die Buch-POST- und PUT-Anfragen verwenden dieselben Felder wie das Formular:
`title`, `subtitle`, `author`, `publisher`, `isbn`, `imprint`, `front_heading`,
`front_text`, `back_heading`, `back_text`, `blurb`, `trim`, `ink`,
`panels_per_page` und `cover_panel`. `cover_panel` zählt ab null. Buchaufträge
erscheinen nicht als zusätzliche Comic-Ausgaben in der Auswahl. Ihr Fortschritt
und ihre Downloads bleiben beim zugehörigen Comic im Buchbereich erreichbar.

Die Dateien werden im bestehenden Automationsvolume gespeichert. Der Build
installiert ReportLab für den PDF-Satz und fontTools für eine lesbare statische
Buchschrift aus der mitgelieferten variablen Schrift. Beides sind lokale
CPU-Werkzeuge; es werden keine externen Modelle verwendet.
