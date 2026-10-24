# Comic-Seitenvorlagen

Im Dashboard unter **Bildstil → Seitenvorlage** stehen 33 Vorlagen mit nummerierten
Vorschaubildern zur Wahl. Der Gruppenfilter hilft beim Vergleichen. Zeichenstil
und Seitenaufteilung sind unabhängig voneinander.

## Bedienung

1. Geschichte öffnen oder neu anlegen.
2. **Seitenvorlage** aufklappen und eine Vorschau anklicken.
3. **Speichern** oder anschließend den normalen Erstellungsablauf verwenden.

Ein Vorlagenwechsel löscht weder Szenen noch Figuren oder Dialoge und startet
keine Bilderzeugung. Vorhandene Comic-Ausgaben bleiben erhalten. Die Auswahl
wird beim nächsten Erzeugen der Ausgabe verwendet.

## Auswahl

- **Klassisch:** bisheriges Layout, Einzelbild, zwei nebeneinander, Viererraster,
  sechs Kacheln hoch oder quer.
- **Zeitungscomic:** Dreierstrip.
- **Filmisch:** zwei, drei oder vier breite Einstellungen, lange Ruhe in der
  Mitte, großes Schlussbild.
- **Dramatisch:** großer Auftakt oder Schluss, Panorama mit Details, fünf Kacheln
  mit hervorgehobener Mitte, Anfang oder Ende.
- **Dynamisch:** wechselnde Gewichte, verschiedene Zwei-/Dreierfolgen, sechs
  Kacheln mit wechselnden Akzenten.
- **Album:** sieben bis neun Kacheln mit unterschiedlichen Rhythmen und großen
  Akzenten sowie regelmäßige Acht- und Neunerraster.
- **Webcomic:** vier oder sechs Kacheln untereinander.

Die Zahl an der Vorschau gibt die Kacheln **pro Seite** an. Sie verändert nicht
die Gesamtzahl der Szenen. Weitere Kacheln setzen dasselbe Muster auf weiteren
Seiten fort; die letzte Seite darf weniger Kacheln enthalten. Leserichtung ist
links nach rechts, dann von oben nach unten.

## Serien

Eine neue Folge übernimmt `page_template` aus ihrer ausgewählten Basisgeschichte
oder Comic-Ausgabe. Das gilt auch bei der übernächsten Fortsetzung. Im Editor
lässt sich die Auswahl je Folge ändern. Änderungen einer Folge wirken nicht
rückwirkend auf andere Folgen oder bereits erzeugte Comics.

## Ausgaben und Grenzen

- `comic.png` zeigt bei einer neuen Vorlage deren erste Seite.
- `pages/01.png`, `pages/02.png` usw. enthalten die vollständige Bildfolge.
- `comic.pdf` und das Comic-Paket enthalten alle Vorlagenseiten.
- Beim Teilen auf Substack oder X werden für diese Vorlagen die vollständigen
  Seiten in numerischer Reihenfolge angeboten.
- **Bisheriges Layout** erhält das bisherige Verhalten einschließlich Übersicht.
- EPUB und KDP-Taschenbuch verwenden weiterhin ihre eigenen Bucheinstellungen;
  diese Vorlagenauswahl ersetzt deren Druckformat und Kacheln-pro-Seite nicht.

Die Vorlagen setzen bereits beschriftete Kacheln zusammen. Keine Kachel wird
beschnitten oder unter ihre ursprüngliche Pixelgröße verkleinert. Unterschiedliche
Seitenverhältnisse können deshalb freie Ränder enthalten. Es handelt sich um
eigene geometrische Seitenlayouts; Canva-Dateien werden nicht importiert.

API: `GET /page-templates` liefert IDs, deutsche Bezeichnungen, Gruppen und
normalisierte Kachelrechtecke. In der Storydefinition steht die Auswahl in
`payload.page_template`, zum Beispiel `six_action`. Bei automatischen Aufträgen
ist `page_template` ebenfalls optional. Ohne Angabe gilt `standard`.

Die Anordnung erfordert keine LLM- oder GPU-Aufrufe und verändert keine gespeicherten
ComfyUI-Workflows. Die Vorlagenauswahl allein startet keinen Auftrag.
