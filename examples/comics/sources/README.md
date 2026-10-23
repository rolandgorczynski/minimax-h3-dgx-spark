# Zehn Heldensagen als Comic-Quellen

Die zehn Einträge werden einzeln im Quellenmenü auswählbar. Sie sind neu formulierte
Inhaltsgrundlagen zu alten, gemeinfreien Stoffen; moderne Übersetzungen, Filme und
Illustrationen werden nicht übernommen. Quellenlinks belegen Werk oder Stoff,
sie geben keine Nutzungslizenz für moderne Webseiten.

Die Auswahl verbindet deutsche mittelalterliche Heldensage mit zwei Episoden des
angelsächsischen Beowulf. Sie ist keine Sammlung von zehn historisch belegten
Ereignissen aus einer einheitlichen germanischen Epoche.

| Nr. | Quelle | Schwerpunkt |
|---|---|---|
| 1 | [Siegfried – Mut vor dem Drachen](https://www.blb-karlsruhe.de/sammlungen/unesco-weltdokumentenerbe-nibelungenlied/unesco-weltdokumentenerbe) | Mut und eigene Grenzen |
| 2 | [Hildebrand – Den eigenen Sohn erkennen](https://kdih.badw.de/datenbank/untergruppe/29/2) | Wiedererkennen und Versöhnung |
| 3 | [Dietrich und Hildebrand – Niemand muss allein bestehen](https://digi.ub.uni-heidelberg.de/de/bpd/glanzlichter/oberdeutsche/henfflin/cpg67.html) | Freundschaft und Hilfe annehmen |
| 4 | [Wolfdietrich – Die Gefährten nicht vergessen](https://www.retrobibliothek.de/retrobib/seite.html?id=136637) | Treue nach erlittenem Unrecht |
| 5 | [Walther und Hildegund – Gemeinsam in die Freiheit](https://digital.blb-karlsruhe.de/download/pdf/3250.pdf) | Zusammenhalt und Ende der Gewalt |
| 6 | [Kudrun – Ungebrochen und zur Versöhnung fähig](https://www.arlima.net/il/kudrun.html) | Standhaftigkeit und Friedenswille |
| 7 | [Hagen – Von der Greifeninsel zurück](https://www.stine.uni-hamburg.de/scripts/mgrqispi.dll?APPNAME=CampusNet&ARGUMENTS=-N000000000000001%2C-N000698%2C-N0%2C-N387604139827109%2C-N387604139873110%2C-N0%2C-N0%2C-N0&PRGNAME=COURSEDETAILS) | Gemeinschaft und Überlebensmut |
| 8 | [Wieland – Freiheit durch Können](https://de.wikisource.org/wiki/Karl_Joseph_Simrock) | Können, Geduld und Ausbruch |
| 9 | [Beowulf – In der Nacht standhalten](https://www.gutenberg.org/cache/epub/981/pg981-images.html) | Verantwortung und Zivilcourage |
| 10 | [Beowulf und Wiglaf – Treue, wenn es schwer wird](https://www.gutenberg.org/cache/epub/981/pg981-images.html) | Beistand und Verantwortung trotz Verlust |

Jede Textgrundlage nennt Herkunft, Ausschnitt, Ende und Abgrenzung. Gerade die
jüngere versöhnliche Hildebrand-Fassung, die verschiedenen Wolfdietrich-Fassungen
und Wielands ausgewähltes Fluchtmotiv sind ausdrücklich gekennzeichnet.
Tragische Enden werden nicht durch erfundene glückliche Schlüsse ersetzt.

## Einspielen

```bash
python3 scripts/import_comic_sources.py examples/comics/sources/germanische-heldensagen-10.json
python3 scripts/import_comic_sources.py examples/comics/sources/germanische-heldensagen-10.json --apply
```

Der erste Aufruf prüft und zeigt die geplante Ergänzung. Der zweite ergänzt den
Katalog. Vorhandene Einträge und selbst bearbeitete Quellen bleiben erhalten.
Ein erneuter Import fügt keine Duplikate hinzu. Eine Sicherung des vorherigen
Katalogs liegt im Datenvolume unter `catalog-backups/`. Es werden keine
Comic-Aufträge gestartet und keine externen Seiten abgerufen.

Im Dashboard den Quellenbereich erneut öffnen beziehungsweise die Seite mit
Strg+F5 neu laden. Eine der zehn Vorlagen wählen, Stil und Kacheln einstellen,
dann das Skript erstellen. Weitere Einträge lassen sich später ergänzen.

## Rechte

Der Schutz mittelalterlicher Originalstoffe ist in Deutschland abgelaufen.
Für alte Übertragungen ist die jeweilige Urheberschaft maßgeblich. Die hier
gespeicherten deutschen Inhaltsgrundlagen sind neu formuliert. Sie enthalten
keine wörtlichen Übernahmen aus heutigen Nacherzählungen. Für selbst später
ergänzte Texte und Bilder deren Rechte separat beachten. Grundlage:
[§ 64 UrhG](https://www.gesetze-im-internet.de/urhg/__64.html) und
[§ 69 UrhG](https://www.gesetze-im-internet.de/urhg/__69.html).
