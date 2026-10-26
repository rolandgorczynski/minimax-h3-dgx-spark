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
| Idun – Die geraubten Äpfel | 12 | [Text](idun-aepfel-12.txt) | [JSON](idun-aepfel-12.json) |
| Loki – Die Wette in der Schmiede | 12 | [Text](loki-zwergenschmiede-12.txt) | [JSON](loki-zwergenschmiede-12.json) |
| Eisenhans – Der goldene Brunnen | 14 | [Text](eisenhans-goldbrunnen-14.txt) | [JSON](eisenhans-goldbrunnen-14.json) |
| Das tapfere Schneiderlein – Sieben auf einen Streich | 12 | [Text](schneiderlein-riesen-12.txt) | [JSON](schneiderlein-riesen-12.json) |
| Der Rattenfänger – Der gebrochene Handel | 12 | [Text](rattenfaenger-hameln-12.txt) | [JSON](rattenfaenger-hameln-12.json) |
| Die Heinzelmännchen – Die Nacht der Erbsen | 8 | [Text](heinzelmaennchen-erbsen-8.txt) | [JSON](heinzelmaennchen-erbsen-8.json) |
| Frau Holle – Zwei Wege durch den Brunnen | 12 | [Text](frau-holle-zwei-wege-12.txt) | [JSON](frau-holle-zwei-wege-12.json) |
| Das Wasser des Lebens – Vor Mitternacht | 12 | [Text](wasser-des-lebens-12.txt) | [JSON](wasser-des-lebens-12.json) |
| Tischchen deck dich – Die gestohlenen Wundergaben | 12 | [Text](tischchen-wundergaben-12.txt) | [JSON](tischchen-wundergaben-12.json) |
| Hans mein Igel – Der Reiter auf dem Hahn | 14 | [Text](hans-mein-igel-14.txt) | [JSON](hans-mein-igel-14.json) |
| Die vier kunstreichen Brüder – Gemeinsam gegen den Drachen | 12 | [Text](vier-kunstreiche-brueder-12.txt) | [JSON](vier-kunstreiche-brueder-12.json) |
| Das Fürchten lernen – Drei Nächte im Spukschloss | 14 | [Text](fuerchten-drei-naechte-14.txt) | [JSON](fuerchten-drei-naechte-14.json) |
| Der Teufel mit den drei goldenen Haaren – Drei Fragen an die Hölle | 16 | [Text](drei-goldene-haare-16.txt) | [JSON](drei-goldene-haare-16.json) |
| Das kalte Herz – Der Preis des Reichtums | 18 | [Text](kaltes-herz-18.txt) | [JSON](kaltes-herz-18.json) |
| Zwerg Nase – Das verlorene Gesicht | 14 | [Text](zwerg-nase-14.txt) | [JSON](zwerg-nase-14.json) |
| Die treuen Frauen von Weinsberg – Was wir tragen können | 8 | [Text](weinsberg-worttreue-8.txt) | [JSON](weinsberg-worttreue-8.json) |
| Kalif Storch – Das vergessene Zauberwort | 12 | [Text](kalif-storch-12.txt) | [JSON](kalif-storch-12.json) |
| Das Gespensterschiff – Die Toten an Deck | 16 | [Text](gespensterschiff-16.txt) | [JSON](gespensterschiff-16.json) |
| Der kleine Muck – Die gestohlenen Zauberschuhe | 14 | [Text](kleiner-muck-14.txt) | [JSON](kleiner-muck-14.json) |
| Hänsel und Gretel – Hinter dem süßen Haus | 16 | [Text](haensel-gretel-16.txt) | [JSON](haensel-gretel-16.json) |
| Rapunzel – Der Turm ohne Tür | 16 | [Text](rapunzel-turm-16.txt) | [JSON](rapunzel-turm-16.json) |
| Rumpelstilzchen – Drei Tage für einen Namen | 14 | [Text](rumpelstilzchen-14.txt) | [JSON](rumpelstilzchen-14.json) |
| Dornröschen – Hundert Jahre hinter den Dornen | 12 | [Text](dornroeschen-12.txt) | [JSON](dornroeschen-12.json) |
| König Drosselbart – Der Mann in der Verkleidung | 14 | [Text](koenig-drosselbart-14.txt) | [JSON](koenig-drosselbart-14.json) |
| Sechse kommen durch die ganze Welt – Jeder kann etwas Unmögliches | 14 | [Text](sechse-welt-14.txt) | [JSON](sechse-welt-14.json) |
| Theseus – Der Faden durch die Finsternis | 10 | [Text](theseus-faden-10.txt) | [JSON](theseus-faden-10.json) |
| Dädalus und Ikarus – Zwischen Meer und Sonne | 12 | [Text](daedalus-ikarus-12.txt) | [JSON](daedalus-ikarus-12.json) |
| Perseus – Der Blick im Schild | 12 | [Text](perseus-spiegelschild-12.txt) | [JSON](perseus-spiegelschild-12.json) |
| Orpheus – Nicht zurückblicken | 10 | [Text](orpheus-rueckblick-10.txt) | [JSON](orpheus-rueckblick-10.json) |
| Herakles – Der Löwe, den keine Waffe trifft | 10 | [Text](herakles-nemea-10.txt) | [JSON](herakles-nemea-10.json) |
| Reise zum Mittelpunkt der Erde – Das Meer unter dem Vulkan | 18 | [Text](reise-erdmittelpunkt-18.txt) | [JSON](reise-erdmittelpunkt-18.json) |
| In 80 Tagen um die Welt – Der gewonnene Tag | 14 | [Text](achtzig-tage-14.txt) | [JSON](achtzig-tage-14.json) |
| 20.000 Meilen unter den Meeren – Angriff auf die Nautilus | 12 | [Text](nautilus-angriff-12.txt) | [JSON](nautilus-angriff-12.json) |
| Die Schatzinsel – Das leere Loch | 12 | [Text](schatzinsel-leeres-loch-12.txt) | [JSON](schatzinsel-leeres-loch-12.json) |
| Robinson Crusoe – Die ersten Tage allein | 10 | [Text](robinson-erste-tage-10.txt) | [JSON](robinson-erste-tage-10.json) |
| Alice im Wunderland – Zu groß für die kleine Tür | 12 | [Text](alice-kleine-tuer-12.txt) | [JSON](alice-kleine-tuer-12.json) |
| Der goldene Vogel – Der Rat des Fuchses | 14 | [Text](goldener-vogel-14.txt) | [JSON](goldener-vogel-14.json) |
| Die weiße Schlange – Wer die Tiere versteht | 14 | [Text](weisse-schlange-14.txt) | [JSON](weisse-schlange-14.json) |
| Die zertanzten Schuhe – Der Weg unter dem Bett | 12 | [Text](zertanzte-schuhe-12.txt) | [JSON](zertanzte-schuhe-12.json) |
| Die Sterntaler – Das letzte Stück Brot | 8 | [Text](sterntaler-8.txt) | [JSON](sterntaler-8.json) |
| Jorinde und Joringel – Die Blume gegen den Bann | 12 | [Text](jorinde-joringel-12.txt) | [JSON](jorinde-joringel-12.json) |
| Fundevogel – Wenn du mich nicht verlässt | 12 | [Text](fundevogel-versprechen-12.txt) | [JSON](fundevogel-versprechen-12.json) |
| Das blaue Licht – Der Ausweg aus dem Brunnen | 10 | [Text](blaues-licht-brunnen-10.txt) | [JSON](blaues-licht-brunnen-10.json) |
| Die Kristallkugel – Das Ei im Feuervogel | 16 | [Text](kristallkugel-16.txt) | [JSON](kristallkugel-16.json) |
