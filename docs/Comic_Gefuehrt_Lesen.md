# Geführt lesen und dieselben Seiten als Buch exportieren

Die Leseansicht verwendet vorhandene, bereits beschriftete Kacheln. Sie benötigt
weder ein LLM noch eine neue Bilderzeugung und verändert keine gespeicherten
ComfyUI-Workflows.

## Vorschau im Dashboard

1. Eine fertige Comic-Ausgabe auswählen.
2. Neben den Download- und Teilen-Schaltflächen **Geführt lesen · Seiten ordnen**
   öffnen.
3. Eine Kachel anklicken oder **Weiter** verwenden. **Ganze Seite** kehrt zur
   Übersicht zurück; **Zurück** geht zum vorherigen Panel.
4. Unter **Vorschau → Handy** die schmale Ansicht prüfen.

Die Navigationsbereiche entstehen aus denselben geometrischen Daten wie die
Seitenvorlage. Es gibt keine fehleranfällige nachträgliche Bilderkennung. Jeder
Bereich umfasst die komplette beschriftete Kachel, einschließlich Erzählerkasten
und Sprechblasen. Die Handyansicht simuliert eine schmale Darstellung im Browser;
sie ersetzt keinen Test auf einem tatsächlichen Kindle-Gerät.

## Leseordnung bearbeiten

Unter **Seiten und Lesereihenfolge bearbeiten** lassen sich Seiten ziehen oder
mit Pfeilen verschieben. **Auslassen** entfernt eine Seite aus der Lesefassung,
aber löscht keine Zeichnung. Mindestens eine Seite muss erhalten bleiben.
**Alle Seiten und Reihenfolgen wiederherstellen** setzt die Auswahl zurück.

Die Pfeile bei den Kacheln ändern die Reihenfolge der Vergrößerungen innerhalb
der aktuellen Seite. Sie verschieben die Zeichnungen nicht auf der Seite.
**Leseordnung speichern** übernimmt die Einstellungen getrennt von der
Originalausgabe. Nicht gespeicherte Änderungen werden beim Schließen verworfen.
Die Versionsprüfung verhindert das Überschreiben einer inzwischen anderweitig
geänderten Leseordnung.

Jede Ausgabe hat ihre eigene Leseordnung. Weitere Serienfolgen übernehmen die
Seitenvorlage wie bisher; eine Reihenfolge aus einer anderen Folge wird wegen
der abweichenden Szenen nicht blind übernommen. Einzelne Bilder weiterhin über
**Ein Bild korrigieren**, Sprechblasen über **Sprechblasen positionieren** ändern.
Ein freier Editor zum Hochladen, Einfügen oder Zuschneiden ganzer Fremdseiten
ist hier nicht enthalten.

## Gemeinsamer Buchexport

Im Buchbereich **Buchlayout → Seitenvorlage und gespeicherte Leseordnung
übernehmen** wählen. Bei neuen Vorlagen ist dies die Voreinstellung. Die
Alternative **Einzelkacheln / einfaches Druckraster** erhält den bisherigen Ablauf.

Der Export sichert eine Momentaufnahme der Bilder und Leseordnung. Spätere
Änderungen an der Vorschau verändern einen bereits gestarteten Export nicht.

- Das EPUB enthält die gestalteten Comic-Seiten und pro Kachel einen eigenen
  Kindle-Panel-Zoombereich mit eindeutiger Reihenfolge und vollständigem Bild.
- Die Taschenbuch-PDF verwendet dieselben Comic-Seiten, passend ins Druckformat
  eingepasst. Mindestseitenzahl, Bildauflösung und Schriftgröße werden weiterhin
  geprüft. Zu kleine Schrift wird nicht durch bloße Bildskalierung freigegeben;
  die Druckdatei bleibt dann ein gekennzeichneter Entwurf.
- Das **Kindle-Create-Seitenpaket** enthält hochauflösende `comic-0001.png` usw.,
  eine Beschreibung der Navigationsbereiche und Importhinweise.
- Im Unterordner **Buchseiten** stehen zusätzlich fortlaufend nummerierte
  JPEG-Seiten der vollständigen EPUB-Buchfassung: einschließlich Titelbild,
  Buchtitel, Impressum, Vorwort und Nachwort, soweit ausgefüllt.

Vorwort, Nachwort und Umschlag bleiben eigenständige Buchbestandteile. Die
Seitenvorlage betrifft die eigentlichen Comic-Seiten. Druckränder und Buchformat
können zusätzliche Ränder verursachen; Bilder und Texte werden nicht beschnitten.

## Weiter mit Kindle Create

ZIP entpacken und für die vollständige Buchfassung die Dateien im Ordner
**Buchseiten** in numerischer Reihenfolge als neues Comic-Projekt importieren.
Alternativ nur die hochauflösenden Comic-PNGs wählen und die Buchbestandteile
selbst ergänzen. Nicht beide Fassungen gleichzeitig importieren.

Panels erkennen lassen und die Bereiche sowie Reihenfolge visuell kontrollieren.
`navigation.json` ist unsere Beschreibung der Comic-Navigationsbereiche und kein
von Kindle Create automatisch importiertes Projektformat. Bei manuell geänderter
Reihenfolge diese im Kindle-Create-Projekt ebenfalls einstellen.

Projekt als KCB sichern und in Kindle Create als KPF exportieren. Unser Programm
erzeugt keine KPF-Datei, steuert Kindle Create nicht fern und veröffentlicht
nichts bei Amazon. EPUB und Druck-PDF vor Veröffentlichung in den dafür vorgesehenen
Amazon-Vorschautools prüfen. Eine automatische Annahme durch KDP ist nicht bestätigt.

Die Umsetzung orientiert sich an der offiziellen
[Kindle-Create-Anleitung für Comics](https://kdp.amazon.com/de_DE/help/topic/GJMRD9F78MS9F43R)
und den [KDP-Angaben zu Panel View](https://kdp.amazon.com/en_US/help/topic/G9GSTY4LTRT39D4Z).

## Lokale Schnittstellen

- `GET /jobs/<ID>/reader`: Seitengeometrie, Navigationsbereiche, aktuelle Leseordnung
  und Version.
- `GET /jobs/<ID>/reader/pages/<Seite>.png`: zusammengesetzte Seite, ohne
  Originaldateien zu verändern.
- `PUT /jobs/<ID>/reader`: `version`, `page_order` und optional `panel_orders`.
  Seiten- und Kachelnummern beginnen hier bei 1. Jede Seite darf nur einmal
  vorkommen; jede Panelreihenfolge muss genau die Kacheln dieser Seite enthalten.
- Buchangaben: `layout_mode: "template"` übernimmt Vorlage und Leseordnung;
  `layout_mode: "legacy"` erhält die bisherige Einzelkachel-Ausgabe.

Die Schnittstellen verwenden denselben optionalen API-Token wie das Dashboard.
