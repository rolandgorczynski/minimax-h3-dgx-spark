# Redaktionelle Aufnahme von Geschichten und Kategorien

Verbindliche Projektregel seit 25. Oktober 2026: Neue Vorlagen, Geschichten und Kategorien werden in der Zusammenarbeit mit Codex redaktionell angebunden. Ein lokales Sprachmodell ersetzt diese inhaltliche Arbeit nicht. Es gibt keinen automatischen kostenpflichtigen externen Modellaufruf.

## Inhaltliche Arbeit

Codex liest die tatsächlich gespeicherte Textgrundlage, bestimmt die menschliche Grundfrage und formuliert eine begründbare Lehre, Erkenntnis oder ausdrücklich offene Frage. Das ist eine Deutung, keine Inhaltsnacherzählung. Ein kurzer tatsächlicher Textausschnitt belegt jede Deutung. Varianten werden getrennt, spätere Ereignisse und fremde Fassungen nicht ergänzt. Historische Wertungen werden nicht unbesehen zu heutigen allgemeinen Aussagen.

Der Comic bekommt einen überschaubaren Umfang: empfohlen werden 6–18 Kacheln je Einzelgeschichte, normalerweise etwa zwölf. Längere Stoffe werden als Serie mit kurzen Folgen empfohlen; die Erkenntnis darf nicht einer starren freien Kachelvorgabe geopfert werden. Bei einer Serie werden 6–12 Kacheln je Folge angestrebt. Kurze Stoffe werden nicht mit erfundenen Nebenhandlungen aufgebläht.

Neue Kategorien werden aus den tatsächlichen Stoffen gebildet und nachvollziehbar zugeordnet. Titel, Herkunft, verwendete Fassung und Rechtehinweise bleiben Teil der Quelle. Eine Kategorie ersetzt keine Einzelprüfung der Geschichte.

## Technische Übernahme

Redaktionelle Ergebnisse liegen in `examples/comics/sinnanalysen/`. Jedes Manifest benennt die Quelle und ihren Text-Hash. Ein Import prüft zuerst sämtliche Einträge: aktuelle Textgrundlage, vollständige Deutungsfelder, Kachelrahmen und tatsächlich vorhandene Belege. Erst dann wird der gemeinsame Cache aktualisiert. Dabei werden weder bestehende Comics noch Skripte oder Story-Versionen umgeschrieben.

```bash
python3 scripts/import_comic_meanings.py examples/comics/sinnanalysen/0000-0024.json --apply
```

Der Zugangsschlüssel wird aus der lokalen Umgebung gelesen und nicht ausgegeben. Ohne `--apply` wird nichts geschrieben. Das Dashboard zeigt den Fortschritt unter **1 · Skript → Vorarbeit für Geschichten und Quellen**. Redaktionell ausgewertete Quellen zeigen Grundfrage, Lehre oder offene Frage, Beleg und Umfang.

Neue Dashboard-Skriptplanungen setzen eine redaktionell ausgewertete Grundlage voraus. Fehlt sie oder wurde der Ausgangstext geändert, wird das ausdrücklich gemeldet. Es beginnt keine lokale Ersatzdeutung. Zusätzliche Gestaltungswünsche ersetzen eine vorhandene redaktionelle Lehre ebenfalls nicht. Die Skripterstellung darf danach die eingerichteten lokalen Modelle zur Ausarbeitung und technischen Prüfung verwenden; die freigegebene Kernaussage bleibt verbindlich.

Neue Vorlagen werden auf Auftrag im Gespräch angebunden. Das Dashboard stellt keine automatische Verbindung zu dieser Codex-Sitzung her. Noch nicht ausgewertete Einträge bleiben als offen sichtbar.

## Daten und Sicherung

Die produktiven Ergebnisse stehen im vorhandenen SQLite-Integrationszustand `narrative-library-cache`. Der Zustand der Vorarbeit steht unter `narrative-library-state`. Beide liegen im bereits gesicherten Docker-Datenverzeichnis. Die exportierten Ausgangstexte für die laufende Redaktion liegen unter `/home/jee/docker-data/comic-sinnanalyse-redaktion/`. Die Manifeste im Git-Repository dokumentieren die redaktionelle Arbeit unabhängig von der Datenbank.

## Quellen für später zurückstellen

Die Auswahl enthält zunächst die 373 bereits redaktionell ausgewerteten Quellen. Die übrigen 627 bleiben vollständig auf der Warteliste gespeichert, erscheinen aber weder in der Vorlagenauswahl noch im Umfang der aktuellen Vorarbeit. Alle bereits redaktionell ausgewerteten Quellen bleiben verfügbar. Neue Themen oder Kategorien können unabhängig davon hinzukommen.

Die Zurückstellung liegt getrennt von den Quellentexten im Studio-Datensatz `source-catalog-deferred`. Quellen-IDs, Auswertungen, vorhandene Skripte und Comics werden nicht geändert oder gelöscht. Der Import und bestehende Quellenverweise können weiterhin auf den vollständigen Katalog zugreifen.

Die genaue Liste steht in [source-availability.json](../examples/comics/source-availability.json). Vom Projektverzeichnis aus:

```bash
# Gespeicherte Liste anwenden; keine Generierung starten:
python3 scripts/configure_comic_source_availability.py --apply

# Alle zurückgestellten Quellen wieder freigeben:
python3 scripts/configure_comic_source_availability.py --restore --apply
```

Ohne `--apply` wird nur die geplante Anzahl ausgegeben. Das Skript verweigert die Zurückstellung bereits redaktionell bearbeiteter Quellen. Spätere Freigaben erfolgen redaktionell über Codex; es gibt keinen automatischen Ersatzlauf mit einem lokalen Modell.
