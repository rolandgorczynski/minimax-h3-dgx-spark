# Redaktionelle Skriptproben

Diese Skripte werden von Codex auf Grundlage der gespeicherten Quelle und ihrer freigegebenen Sinnanalyse geschrieben. Es gibt weder einen lokalen Ersatzlauf noch einen Bildauftrag. Der konkrete Bildstil wird erst in Schritt 2 gewählt.

## Die Bremer Stadtmusikanten

- Umfang: **10 Kacheln**, entsprechend der redaktionellen Empfehlung.
- [Lesbares vollständiges Skript](bremer-stadtmusikanten-10.txt).
- [Bearbeitbare Studio-Definition](bremer-stadtmusikanten-10.json).
- [Technische Beschriftungsprüfung](bremer-stadtmusikanten-10-beschriftungspruefung.json): keine Warnungen oder ungelösten Kacheln.
- Im Studio: **2 · Comic erzeugen → Gespeichertes Skript auswählen → Die Bremer Stadtmusikanten · Skriptprobe**.
- Skriptkontrolle und Änderungen über **← Skript prüfen**. Danach in Schritt 2 Stil und Seitenvorlage wählen.

Der Schluss vermittelt die Kernaussage durch die Entscheidung der Tiere: Ihr gemeinsames Zuhause ist wichtiger als das ursprünglich geplante Ziel Bremen. Neue Dialoge sind freie Adaption, keine Originalzitate. Die Tiere behalten Aussehen und Ausstattung. Tierpyramide, Schlafplätze, Türwechsel und Zustände sind je Kachel festgeschrieben. Erzählerkästen wiederholen die gesprochenen Sätze nicht.

Import aus dem Projektverzeichnis:

```bash
# Inhalt, Umfang, Sprecherzuordnung und Beschriftung technisch prüfen:
python3 scripts/import_comic_script.py examples/comics/skriptproben/bremer-stadtmusikanten-10.json

# Als neue Geschichte übernehmen; keine Bilder erzeugen:
python3 scripts/import_comic_script.py examples/comics/skriptproben/bremer-stadtmusikanten-10.json --apply
```

Der Import prüft die aktive Quelle und die aktuelle Umfangsempfehlung. Ein erneuter Aufruf erkennt dieselbe Skriptkennung und verändert die gespeicherte Geschichte nicht. Frühere Geschichten werden niemals überschrieben.

## Weitere vorbereitete Skripte

Alle folgenden Skripte sind bereits als eigene bearbeitbare Geschichten unter **2 · Comic erzeugen** verfügbar. Der Bildstil ist jeweils noch offen.

| Skript | Kacheln | Lesefassung | Studio-Definition |
|---|---:|---|---|
| Der kleine Prinz | 12 | [Text](kleiner-prinz-12.txt) | [JSON](kleiner-prinz-12.json) |
| Die Bremer Stadtmusikanten | 10 | [Text](bremer-stadtmusikanten-10.txt) | [JSON](bremer-stadtmusikanten-10.json) |
| Eine Weihnachtsgeschichte | 14 | [Text](weihnachtsgeschichte-14.txt) | [JSON](weihnachtsgeschichte-14.json) |
| Siegfried – Mut vor dem Drachen | 8 | [Text](siegfried-drache-8.txt) | [JSON](siegfried-drache-8.json) |
| Hildebrand – Den eigenen Sohn erkennen | 12 | [Text](hildebrand-heimkehr-12.txt) | [JSON](hildebrand-heimkehr-12.json) |
| Dietrich und Hildebrand – Niemand muss allein bestehen | 14 | [Text](dietrich-sigenot-14.txt) | [JSON](dietrich-sigenot-14.json) |
| Wolfdietrich – Die Gefährten nicht vergessen | 12 | [Text](wolfdietrich-treue-12.txt) | [JSON](wolfdietrich-treue-12.json) |
| Walther und Hildegund – Gemeinsam in die Freiheit | 14 | [Text](walther-hildegund-14.txt) | [JSON](walther-hildegund-14.json) |
| Kudrun – Ungebrochen und zur Versöhnung fähig | 14 | [Text](kudrun-versoehnung-14.txt) | [JSON](kudrun-versoehnung-14.json) |
| Hagen – Von der Greifeninsel zurück | 10 | [Text](hagen-greifeninsel-10.txt) | [JSON](hagen-greifeninsel-10.json) |
| Wieland – Freiheit durch Können | 10 | [Text](wieland-handwerk-10.txt) | [JSON](wieland-handwerk-10.json) |
| Beowulf – In der Nacht standhalten | 10 | [Text](beowulf-grendel-10.txt) | [JSON](beowulf-grendel-10.json) |
| Beowulf und Wiglaf – Treue, wenn es schwer wird | 12 | [Text](beowulf-wiglaf-12.txt) | [JSON](beowulf-wiglaf-12.json) |
| Thor – Der gestohlene Hammer | 12 | [Text](thor-gestohlener-hammer-12.txt) | [JSON](thor-gestohlener-hammer-12.json) |
| Thor – Die unmöglichen Prüfungen | 14 | [Text](thor-utgard-14.txt) | [JSON](thor-utgard-14.json) |
| Tyr – Die Hand als Pfand | 12 | [Text](tyr-fenrir-12.txt) | [JSON](tyr-fenrir-12.json) |
| Hermod – Neun Nächte bis Hel | 12 | [Text](hermod-hel-12.txt) | [JSON](hermod-hel-12.json) |
| Die getreue Alte | 14 | [Text](getreue-alte-14.txt) | [JSON](getreue-alte-14.json) |
