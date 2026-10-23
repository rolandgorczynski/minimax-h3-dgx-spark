# Comic-Produktion: lokale Vorarbeit und redaktionelle Qualität

## Ergebnis der Überprüfung

Die ursprüngliche Empfehlung gilt mit Einschränkungen: Lokale Modelle können
Vorarbeit und Bildbeobachtung übernehmen. Eine gleichwertige Dramaturgie oder
zuverlässige semantische Textfreigabe wurde nicht nachgewiesen. Im Praxistest
lieferten sogar zwei lokale Textprüfer Fehlalarme. Deshalb verändern die neuen
Hilfsfunktionen weder die Geschichte noch das freigegebene Storyboard und erteilen
keine automatische Freigabe.

Die Erweiterung betrifft den redaktionellen Skriptmodus. Der bereits vorhandene
selbstständig schreibende Comic-Automat bleibt ein separater Ablauf.

## Aufgabenverteilung

| Aufgabe | Zuständigkeit | Absicherung |
|---|---|---|
| Quellenabsätze für die Vorbereitung auswählen | Lokales Textmodell | Modell wählt vorhandene Absatznummern; das Skript kopiert die Originalstellen. |
| Quellenstellen übernehmen | Python | Originaltext samt Start- und Endposition; keine vom Modell nacherzählten Zitate. |
| Einstieg, Schluss, Dramaturgie und emotionale Verdichtung | Redaktion beziehungsweise Assistent im Gespräch | Ein zusammenhängender redaktioneller Durchgang. |
| Figuren- und Sprecher-IDs, Datenstruktur und Textgrenzen prüfen | Python und bestehende ComfyUI-Vorprüfung | Feste Regeln; kein Modellurteil nötig. |
| Bilder erzeugen, beschriften, Seiten und PDF bauen | Lokales ComfyUI und Skripte | Bestehender Produktionsablauf. |
| Personen und sichtbare Abweichungen im Bild beobachten | Lokales Bildmodell | Nur Prüfhinweise, keine automatische Korrektur. |
| Semantische Textfreigabe | Redaktion | Lokaler Modellvergleich standardmäßig deaktiviert. |
| Endgültige visuelle Prüfung | Nutzer oder Assistent mit Bildansicht | Auftrag bleibt mit `--local-check` offen. |

Bildbeschreibungen automatisch umschreiben oder Bilder auf bloßen Modellverdacht
neu generieren ist bewusst nicht Bestandteil dieser Erweiterung. Die vorhandene
Bildsprache bleibt so erhalten.

## Praxistest vom 23. Oktober 2026

Getestet wurde am vorhandenen Marius-Comic auf der lokalen Umgebung, ohne externe
Modellaufrufe. Es handelt sich um eine kleine Stichprobe, nicht um einen allgemeinen
Qualitätsnachweis.

| Test | Beobachtung | Konsequenz |
|---|---|---|
| Freie Quellenextraktion mit `qwen2.5:14b-instruct` | Zwei von neun angeblich wörtlichen Belegen waren verändert. | Keine frei erzeugten Modellzitate übernehmen. |
| Absatzauswahl mit eingeschränktem JSON-Schema | 18 unterschiedliche Quellenabsätze übernommen, keine ungültige Absatznummer. Etwa 31 Sekunden im Test. | Originalstellen werden vom Skript eingesetzt; Modellüberschriften bleiben ungeprüfte Vorschläge. |
| Absichtlich falsches Alter und falscher Heimweg | Lokaler Textprüfer erkannte den Widerspruch; zunächst war sein Beleg umformuliert. | Quellenbezug über vorhandene Absatznummern herstellen. |
| Korrekte Erzählertexte | `qwen2.5:14b-instruct` und `qwen3.6:35b-a3b` meldeten zulässige Kürzungen oder Formulierungen als Fehler. | Semantischer Textvergleich nicht als Standard aktivieren. |
| Student mit Einkaufstasche | `gemma3:27b` erkannte eine Person und die Einkaufstasche. | Als Vorprüfung brauchbar. |
| Leerer Krankenhausflur | `gemma3:27b` erkannte null Personen und meldete keine Abweichung. | Als Vorprüfung brauchbar. |
| Verworfene Flurillustration mit zusätzlichen Personen | Modell erkannte den Widerspruch zur leeren Sollszene; zählte sechs statt der visuell erkennbaren fünf Personen. | Genaue Personenzahl und Bildurteile nicht als verlässlich behandeln. |

Die beiden korrekten Bilder benötigten zuletzt rund zwölf beziehungsweise dreizehn
Sekunden für die lokale Bildbeobachtung. Die verworfene Flurillustration rund
14 Sekunden. Die Zeiten enthalten die jeweilige lokale Anfrage und hängen vom
Ladezustand und der Auslastung ab.

## 1. Artikel lokal vorbereiten

Auf dem Docker-Host im Repository:

```bash
python3 scripts/comic_local_assistant.py vorbereiten \
  examples/comics/editorial/marius-dick/article.txt \
  --output diagnostics/meine-geschichte/quellenpaket.json
```

Das Paket enthält ausgewählte Originalabsätze, Positionen im Originaltext,
Quellenprüfsumme sowie getrennt gekennzeichnete Modellvorschläge. Die Auswahl kann
wichtige Aspekte auslassen; die Themenüberschriften und offenen Fragen sind nicht
unabhängig bestätigt. Den Originalartikel beim redaktionellen Entwurf weiterhin
bereithalten.

## 2. Szenen redaktionell ausarbeiten

Artikel und Quellenpaket im Gespräch verwenden. Der Assistent erstellt Titel,
Figuren, Erzählbogen und die Szenen als Storyboard. Vor dem Rendern prüfen und
gegebenenfalls bearbeiten. Einzelheiten stehen unter
[Comic per Skript erstellen](Comic_per_Skript_erstellen.md).

## 3. Lokal rendern und Bilder vorprüfen

```bash
python3 scripts/render_editorial_comic.py meine-geschichte.json --local-check
```

Der Ablauf rendert zuerst die Bilder und erstellt das Layout. Anschließend laufen
formale Prüfungen und die lokale Bildbeobachtung. Der zusätzliche Bericht
`local-review.json` liegt im Ausgabeordner, im Auftrag und im ZIP-Paket.

`--local-check` lässt den Auftrag **immer bearbeitbar**, auch wenn das Modell keine
Probleme meldet. Ein leerer Prüfbericht ist keine Freigabe. Der Szenenplan wird
weder überschrieben noch durch eine Modellantwort ersetzt. Nur strittige Kacheln
müssen danach im Gespräch erneut besprochen werden.

Nach tatsächlicher Sichtprüfung ohne `--local-check` abschließen:

```bash
python3 scripts/render_editorial_comic.py meine-geschichte.json \
  --job AUFTRAGS_ID \
  --review "Kacheln auf Bildinhalt, Texttreue und Lesbarkeit geprüft."
```

Ändert sich das Storyboard, werden zugehörige ältere lokale Prüfberichte beim
Upload nicht als aktuelle Prüfung übernommen. Vor dem Abschluss nach Änderungen
gegebenenfalls erneut mit `--local-check` prüfen.

## Bestehende Bilder prüfen, ohne neu zu rendern

```bash
python3 scripts/comic_local_assistant.py pruefen meine-geschichte.json \
  --panels diagnostics/comics/AUFTRAGS_ID/panels \
  --output diagnostics/meine-geschichte/pruefhinweise.json
```

Ohne `--panels` läuft standardmäßig ausschließlich die formale Prüfung, ohne
Textmodellaufruf. Für Untersuchungen ist `--text-review` verfügbar. Dieser
experimentelle Textvergleich bleibt wegen der beobachteten Fehlalarme ausgeschaltet
und ist keine Empfehlung zur automatischen Freigabe.

## Lokale Modelle und Ressourcen

Standardmodelle:

- Quellenaufbereitung: `qwen2.5:14b-instruct`.
- Bildbeobachtung: `gemma3:27b`.
- Experimenteller Textvergleich: `qwen3.6:35b-a3b`.

Es werden nur installierte lokale Ollama-Modelle verwendet. Der gemeinsame Client
verweigert öffentliche Serveradressen, Weiterleitungen und als Cloud-Modelle
gekennzeichnete Modelle. Er lädt keine Modelle herunter und besitzt keinen
externen Ersatzdienst.

Konfiguration über `COMIC_LOCAL_OLLAMA_URL` (Standard `http://127.0.0.1:11434`),
`COMIC_LOCAL_TEXT_MODEL`, `COMIC_LOCAL_VISION_MODEL` und `COMIC_LOCAL_REVIEW_MODEL`.
Beim eigenständigen Hilfsskript sind alternativ `--ollama-url`, `--text-model`,
`--vision-model` und `--review-model` möglich.

Die eigenen Schritte laufen nacheinander: Vorbereitung, Rendering, Bildprüfung.
Ollama erhält `keep_alive: 0`, damit die jeweils verwendeten Modelle nach einer
Anfrage entladen werden. Das kann erneutes Laden kosten, begrenzt aber den
verbleibenden Modellbestand im Speicher. Andere Prozesse auf dem Spark werden
nicht angehalten; dies ist keine globale Reservierung des Rechners.

Ergebnisse werden unter `diagnostics/comics/local-model-cache/` anhand von
Modell-Prüfsumme, Anfrage, Schema und aufbereitetem Bild zwischengespeichert.
Identische Prüfungen benötigen dadurch keine erneute Generierung. Geänderte
Anfragen oder Modellgewichte erhalten einen anderen Schlüssel. Die Bildprüfung
verwendet eine verkleinerte Kopie; die exportierten Originalbilder bleiben erhalten.
Porträts für im Comic nicht verwendete Figuren werden nicht mehr erzeugt.

Technische Grundlagen: [Strukturierte Ausgaben in Ollama](https://docs.ollama.com/capabilities/structured-outputs)
und [Speicherverwaltung mit `keep_alive`](https://docs.ollama.com/faq).
Ein JSON-Schema begrenzt das Antwortformat; es bestätigt nicht die inhaltliche Richtigkeit.
