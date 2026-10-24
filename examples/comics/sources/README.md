# Quellenpakete für Comics

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

## Weitere 30 Vorlagen: deutsche Märchen, Mythen und Abenteuer

Die folgenden zwei Pakete ergänzen die bisherigen 23 Katalogeinträge auf insgesamt 53.
Alle Einträge enthalten eigene deutsche Inhaltsfassungen, historische Quellenlinks,
Begleittexte für Beiträge sowie konkrete Handlungsgrenzen und Kontinuitätshinweise.
Bei langen Romanen wird ein zusammenhängender Ausschnitt statt des vollständigen
Romans adaptiert. Die Hinweise sind Planungsgrundlagen, keine Garantie für fehlerfreie
Modellbilder.

### Zehn deutsche Märchen und Sagen für Comics

Datei: [deutsche-maerchen-sagen-naechste-10.json](deutsche-maerchen-sagen-naechste-10.json)

| Vorlage | Historischer Quellenbeleg |
|---|---|
| Frau Holle – Zwei Wege durch den Brunnen | [Ausgangstext](https://de.wikisource.org/wiki/Frau_Holle_(1857)) |
| Das Wasser des Lebens – Vor Mitternacht | [Ausgangstext](https://de.wikisource.org/wiki/Das_Wasser_des_Lebens_(1857)) |
| Tischchen deck dich – Die gestohlenen Wundergaben | [Ausgangstext](https://de.wikisource.org/wiki/Tischchen_deck_dich,_Goldesel,_und_Knüppel_aus_dem_Sack_(1857)) |
| Hans mein Igel – Der Reiter auf dem Hahn | [Ausgangstext](https://de.wikisource.org/wiki/Hans_mein_Igel_(1857)) |
| Die vier kunstreichen Brüder – Gemeinsam gegen den Drachen | [Ausgangstext](https://de.wikisource.org/wiki/Die_vier_kunstreichen_Brüder_(1857)) |
| Das Fürchten lernen – Drei Nächte im Spukschloss | [Ausgangstext](https://de.wikisource.org/wiki/Mährchen_von_einem,_der_auszog_das_Fürchten_zu_lernen_(1857)) |
| Der Teufel mit den drei goldenen Haaren – Drei Fragen an die Hölle | [Ausgangstext](https://de.wikisource.org/wiki/Der_Teufel_mit_den_drei_goldenen_Haaren_(1857)) |
| Das kalte Herz – Der Preis des Reichtums | [Ausgangstext](https://de.wikisource.org/wiki/Das_kalte_Herz/Zweite_Abteilung) |
| Zwerg Nase – Das verlorene Gesicht | [Ausgangstext](https://de.wikisource.org/wiki/Der_Zwerg_Nase) |
| Die treuen Frauen von Weinsberg – Was wir tragen können | [Ausgangstext](https://de.wikisource.org/wiki/Die_Weiber_zu_Weinsperg) |

```bash
python3 scripts/import_comic_sources.py examples/comics/sources/deutsche-maerchen-sagen-naechste-10.json
python3 scripts/import_comic_sources.py examples/comics/sources/deutsche-maerchen-sagen-naechste-10.json --apply
```

### Zwanzig weitere Märchen, Mythen und Abenteuer für Comics

Datei: [abenteuer-mythen-weitere-20.json](abenteuer-mythen-weitere-20.json)

| Vorlage | Historischer Quellenbeleg |
|---|---|
| Kalif Storch – Das vergessene Zauberwort | [Ausgangstext](https://de.wikisource.org/wiki/Die_Geschichte_von_Kalif_Storch) |
| Das Gespensterschiff – Die Toten an Deck | [Ausgangstext](https://de.wikisource.org/wiki/Die_Geschichte_von_dem_Gespensterschiff) |
| Der kleine Muck – Die gestohlenen Zauberschuhe | [Ausgangstext](https://de.wikisource.org/wiki/Die_Geschichte_von_dem_kleinen_Muck) |
| Hänsel und Gretel – Hinter dem süßen Haus | [Ausgangstext](https://de.wikisource.org/wiki/Hänsel_und_Grethel_(1857)) |
| Rapunzel – Der Turm ohne Tür | [Ausgangstext](https://de.wikisource.org/wiki/Rapunzel_(1857)) |
| Rumpelstilzchen – Drei Tage für einen Namen | [Ausgangstext](https://de.wikisource.org/wiki/Rumpelstilzchen_(1857)) |
| Dornröschen – Hundert Jahre hinter den Dornen | [Ausgangstext](https://de.wikisource.org/wiki/Dornröschen_(1857)) |
| König Drosselbart – Der Mann in der Verkleidung | [Ausgangstext](https://de.wikisource.org/wiki/König_Drosselbart_(1857)) |
| Sechse kommen durch die ganze Welt – Jeder kann etwas Unmögliches | [Ausgangstext](https://de.wikisource.org/wiki/Sechse_kommen_durch_die_ganze_Welt_(1857)) |
| Theseus – Der Faden durch die Finsternis | [Ausgangstext](https://www.gutenberg.org/ebooks/3327) |
| Dädalus und Ikarus – Zwischen Meer und Sonne | [Ausgangstext](https://www.gutenberg.org/ebooks/3327) |
| Perseus – Der Blick im Schild | [Ausgangstext](https://www.gutenberg.org/ebooks/3327) |
| Orpheus – Nicht zurückblicken | [Ausgangstext](https://www.gutenberg.org/ebooks/3327) |
| Herakles – Der Löwe, den keine Waffe trifft | [Ausgangstext](https://www.gutenberg.org/ebooks/3327) |
| Reise zum Mittelpunkt der Erde – Das Meer unter dem Vulkan | [Ausgangstext](https://www.gutenberg.org/ebooks/4791) |
| In 80 Tagen um die Welt – Der gewonnene Tag | [Ausgangstext](https://www.gutenberg.org/ebooks/20973) |
| 20.000 Meilen unter den Meeren – Angriff auf die Nautilus | [Ausgangstext](https://www.gutenberg.org/ebooks/5097) |
| Die Schatzinsel – Das leere Loch | [Ausgangstext](https://www.gutenberg.org/ebooks/120) |
| Robinson Crusoe – Die ersten Tage allein | [Ausgangstext](https://www.gutenberg.org/ebooks/521) |
| Alice im Wunderland – Zu groß für die kleine Tür | [Ausgangstext](https://www.gutenberg.org/ebooks/11) |

```bash
python3 scripts/import_comic_sources.py examples/comics/sources/abenteuer-mythen-weitere-20.json
python3 scripts/import_comic_sources.py examples/comics/sources/abenteuer-mythen-weitere-20.json --apply
```

Der Import ergänzt nur fehlende IDs und sichert den vorherigen Katalog. Wiederholte
Aufrufe erzeugen keine doppelten Einträge. Vorhandene Bearbeitungen bleiben erhalten.
Es werden weder Modelle aufgerufen noch Comics erzeugt oder ComfyUI-Workflows geändert.
Nach dem Import das Quellenmenü neu öffnen oder die Dashboard-Seite neu laden.

Die Gemeinfreiheit bezieht sich auf die historischen Originaltexte beziehungsweise
die genannten alten Bearbeitungen in Deutschland. Die englischen und französischen
Belege werden hier ausschließlich durch eigene deutsche Inhaltsfassungen erschlossen;
keine moderne deutsche Übersetzung oder fremde Illustration wird übernommen.

## Weitere 20 Vorlagen: Grimm, Andersen und Abenteuerklassiker

[maerchen-klassiker-weitere-20.json](maerchen-klassiker-weitere-20.json) ergänzt den
Katalog von 53 auf 73 Einträge. Zehn Grimm-Märchen, fünf Andersen-Geschichten und
fünf klassische Abenteuer bringen weitere Tonlagen hinzu: Rettung, Rätsel, Spuk,
Satire, Naturentdeckung und frühe Science-Fiction. Tragische oder offene Enden
bleiben erhalten. Längere Werke sind auf ausdrücklich benannte Episoden begrenzt.

| Vorlage | Historischer Quellenbeleg |
|---|---|
| Der goldene Vogel – Der Rat des Fuchses | [Ausgangstext](https://de.wikisource.org/wiki/Der_goldene_Vogel_(1857)) |
| Die weiße Schlange – Wer die Tiere versteht | [Ausgangstext](https://de.wikisource.org/wiki/Die_weiße_Schlange_(1857)) |
| Die zertanzten Schuhe – Der Weg unter dem Bett | [Ausgangstext](https://de.wikisource.org/wiki/Die_zertanzten_Schuhe_(1857)) |
| Die Sterntaler – Das letzte Stück Brot | [Ausgangstext](https://de.wikisource.org/wiki/Die_Sternthaler_(1857)) |
| Jorinde und Joringel – Die Blume gegen den Bann | [Ausgangstext](https://de.wikisource.org/wiki/Jorinde_und_Joringel_(1857)) |
| Fundevogel – Wenn du mich nicht verlässt | [Ausgangstext](https://de.wikisource.org/wiki/Fundevogel_(1857)) |
| Das blaue Licht – Der Ausweg aus dem Brunnen | [Ausgangstext](https://de.wikisource.org/wiki/Das_blaue_Licht_(1857)) |
| Die Kristallkugel – Das Ei im Feuervogel | [Ausgangstext](https://de.wikisource.org/wiki/Die_Krystallkugel_(1857)) |
| Die drei Federn – Der unterschätzte Weg | [Ausgangstext](https://de.wikisource.org/wiki/Die_drei_Federn_(1857)) |
| Die Gänsemagd – Die vertauschte Braut | [Ausgangstext](https://de.wikisource.org/wiki/Die_Gänsemagd_(1857)) |
| Die Schneekönigin – Wärme im Eispalast | [Ausgangstext](https://www.gutenberg.org/ebooks/1597) |
| Des Kaisers neue Kleider – Was niemand sehen darf | [Ausgangstext](https://www.gutenberg.org/ebooks/1597) |
| Der Tannenbaum – Immer erst morgen | [Ausgangstext](https://www.gutenberg.org/ebooks/1597) |
| Der Schatten – Der Diener wird zum Herrn | [Ausgangstext](https://www.gutenberg.org/ebooks/1597) |
| Das Mädchen mit den Schwefelhölzern – Ein Licht nach dem anderen | [Ausgangstext](https://www.gutenberg.org/ebooks/1597) |
| Die Zeitmaschine – Der erste Blick auf das Jahr 802701 | [Ausgangstext](https://www.gutenberg.org/ebooks/35) |
| Rikki-Tikki-Tavi – Der Wächter des Gartens | [Ausgangstext](https://www.gutenberg.org/ebooks/236) |
| Der kopflose Reiter – Die letzte Brücke | [Ausgangstext](https://www.gutenberg.org/ebooks/41) |
| Der geheime Garten – Die Tür hinter dem Efeu | [Ausgangstext](https://www.gutenberg.org/ebooks/113) |
| Der Zauberer von Oz – Hinter dem Vorhang | [Ausgangstext](https://www.gutenberg.org/ebooks/55) |

```bash
python3 scripts/import_comic_sources.py examples/comics/sources/maerchen-klassiker-weitere-20.json
python3 scripts/import_comic_sources.py examples/comics/sources/maerchen-klassiker-weitere-20.json --apply
```

Alle Inhaltsfassungen und Begleittexte sind auf Deutsch neu formuliert. Die
Gemeinfreiheit bezieht sich auf die historischen Stoffe und Originaltexte in
Deutschland, nicht auf moderne Übersetzungen, Verfilmungen oder Illustrationen.
Der Import sichert den bisherigen Katalog, ergänzt nur fehlende IDs und startet
keinen Comic-Lauf. Nach dem Import die Quellenansicht neu öffnen.

## Katalog auf 1.000 Vorlagen ergänzen

[bechstein-sagen-bis-1000.json](bechstein-sagen-bis-1000.json) ergänzt die bisherigen
73 Vorlagen um 927 eigenständige nummerierte Sagen aus Ludwig Bechsteins
**Deutschem Sagenbuch** (zuerst 1853). Die historischen deutschen Erzähltexte sind
vollständig als Textgrundlage hinterlegt. Anders als die zuvor redigierten Pakete
sind dies **keine eigens geschriebenen Zusammenfassungen**. Der kurze Begleittext
ist ein Auszug aus dem jeweiligen historischen Erzähltext.

Die Texte wurden aus einem einzigen Sammelexport der Digitalen Bibliothek von
TextGrid gewonnen: [Sammlung kf14.0](https://textgridrep.org/browse/kf14.0).
Kein Abruf von 927 einzelnen Webseiten und kein Modellaufruf waren nötig.
Vorworte, bloße Metadaten, zu lange oder zu kurze Texte sowie erkannte bereits
vorhandene Stoffe wurden nicht übernommen. Alle aufgenommenen Titel und IDs
sind eindeutig. Die Auswahl ist strukturell geprüft, nicht für jeden einzelnen
Stoff dramaturgisch redigiert; Varianten und historische Aussagen vor einer
Veröffentlichung am konkreten Comic prüfen.

### Herkunft und Rechte

Ludwig Bechstein starb 1860. Sein historischer Originaltext ist in Deutschland
gemeinfrei. Grundlage dieser Transkription ist der Druck Meersburg und Leipzig
1930. Transkriptionsnachweis: **TextGrid und www.editura.de, Digitale Bibliothek**,
[CC BY 3.0 DE](https://creativecommons.org/licenses/by/3.0/de/).
Diese Lizenz betrifft den annotierten Datenbestand, nicht den gemeinfreien
literarischen Originaltext. XML-Auszeichnung, editorische Fußnoten, Seitenmarken
und Bilder wurden entfernt; Leerraum wurde normalisiert. Moderne Bearbeitungen
oder fremde Illustrationen sind nicht Bestandteil des Pakets.

[Maschinenlesbarer Herkunftsnachweis](../../../docs/comic-quellen-bechstein-nachweis.json)
nennt Archiv-Prüfsumme, ausgewählte TextGrid-IDs, Sagenummern, Einzelprüfsummen
und Ausschlussgründe. Die individuellen Quellenbelege stehen auch in jedem
Dashboard-Eintrag.

### Import und erneute Erstellung

```bash
python3 scripts/import_comic_sources.py examples/comics/sources/bechstein-sagen-bis-1000.json
python3 scripts/import_comic_sources.py examples/comics/sources/bechstein-sagen-bis-1000.json --apply
```

Der Import ergänzt nur fehlende IDs und sichert den bisherigen Katalog.
Er überschreibt keine bearbeiteten Quellen und startet keine Comic-Erstellung.
Ein zweiter Import ergänzt nichts. Im Dashboard die Quellenansicht neu laden.

Der Offline-Generator kann das Paket aus dem TextGrid-Sammelexport erneut
aufbauen. Die genaue Archiv-Adresse steht im Herkunftsnachweis; einmal lokal
herunterladen und anschließend ausführen:

```bash
python3 scripts/build_comic_legend_pack.py /pfad/zum/textgrid-export.zip
```

Der Generator führt selbst keine Netz- oder Modellaufrufe aus. Er ergänzt die
mitgelieferten Quellpakete und drei eingebauten Vorlagen rechnerisch auf 1.000;
bei zu wenigen vollständigen Texten bricht er ab, statt Platzhalter anzulegen.
Das bereits erzeugte Paket ist direkt importierbar, auch ohne erneuten Download.

## Kategorien und Suche im Dashboard

Die Quellenansicht bietet kombinierbare Filter für Thema und Sammlung sowie eine
Suche nach Titel, Autor und Stichwort. Alphabetische Gruppen und Trefferzahlen
machen auch den großen Katalog übersichtlich. Die automatische Themenzuordnung
ist eine Orientierung und kann unter den Quellendaten verändert und gespeichert
werden. Eigene Kategorien erscheinen danach ebenfalls im Filter.

Die Standardthemen sind:

- Heldensagen und Mythen
- Märchen und Verwandlungen
- Geister und Spuk
- Drachen und Ungeheuer
- Schätze und verborgene Orte
- Teufel und Zauberei
- Heilige und Legenden
- Historische Sagen
- Abenteuer und Entdeckungen
- Fabeln und Tiergeschichten
- Liebe und Treue
- Regionale Sagen

Eigene, noch nicht thematisch eingeordnete Quellen erscheinen bei **Eigene
Vorlagen**. Sammlungen wie Bechsteins Sagenbuch, Grimm, Andersen, Hauff oder
nordische Mythen werden getrennt gefiltert. Die Einordnung startet keine Modelle,
ändert keine Geschichten oder Bilder und verändert beim Lesen keine gespeicherten
Quelltexte. Ein bearbeiteter Entwurf bleibt beim Filtern oder Neuladen erhalten.
