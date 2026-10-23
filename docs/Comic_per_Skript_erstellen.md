# Comic per Skript erstellen – Projektanweisungen und Ablauf

## Ziel und Aufgabenteilung

Der Nutzer liefert eine Geschichte oder einen Artikel und wählt Comic-Stil sowie
frei gewählte Kachelanzahl. Der Assistent arbeitet daraus eine stimmige Bildgeschichte aus:
Szenen, Bildkompositionen, Erzählertexte, Figuren und gegebenenfalls Sprechblasen.
Der Nutzer kann den Szenenplan prüfen und bearbeiten. Das Skript übernimmt danach
die lokale Bilderzeugung, das Seitenlayout und den Export.

Der redaktionelle Skriptmodus erwartet ein fertiges **Storyboard als JSON**. Ein
Rohartikel allein genügt nicht. Dieser Modus benutzt keinen lokalen LLM zum
Erfinden oder Umschreiben der Geschichte. Er ist vom selbstständig Geschichten
erfindenden Comic-Automaten zu unterscheiden.

## Verbindliche Projektregeln

- Antworten, Dokumentation, Geschichten, Überschriften, Erzählertexte und Sprechblasen auf Deutsch verfassen.
- Bilder ausschließlich mit den vorhandenen lokalen ComfyUI-Modellen erzeugen. Keine externen Bildmodelle oder Cloud-Dienste einsetzen.
- Bestehende gespeicherte ComfyUI-Workflows und die gemeinsame Figurenbibliothek erhalten. Neue Vorlagen und private Figurenkopien pro Auftrag sind zulässig.
- Den vorhandenen Dienst in seinem eigenen Compose-Projekt `comic-automation` verwenden. Für jeden neuen Comic einen eigenen Auftrag anlegen.
- Zuerst eine klare Geschichte planen, dann Bilder erzeugen. Jede Kachel erzählt einen eigenen Moment; Wiederholungen vermeiden.
- Figuren über stabile IDs, Beschreibungen und Referenzbilder wiedererkennbar halten. Einer Figur ihre eigene Sprechblase über die Sprecher-ID zuordnen.
- Stilwechsel und einzelne Bildkorrekturen dürfen den ausgearbeiteten Szenenplan nicht ersetzen.
- Sachartikel nicht durch erfundene Tatsachen oder Originalzitate ergänzen. Zeitbezüge des Artikels erhalten; unbekannte Angaben als unbekannt behandeln.
- Personen ohne Originalvorlage als symbolische Darstellung kennzeichnen. Sysop als Erzähler nicht versehentlich zum Beteiligten oder Zeugen machen.
- Bilder und Text vor einer redaktionellen Freigabe tatsächlich ansehen. Ein erfolgreicher Skriptlauf ist keine automatische visuelle oder journalistische Prüfung.

## Gestalterische Leitlinien

Die Geschichte soll emotional verständlich und bildlich abwechslungsreich sein.
Nahaufnahmen, ruhige Räume, Gegenstände und unterschiedliche Perspektiven gezielt
verwenden. Gerade bei Verlust oder Trauer können leere Räume und ein unbeantwortetes
Telefon mehr ausdrücken als eine zusätzliche Figur. Gewalt zurückhaltend behandeln.

Kompositionen konkret und positiv beschreiben, etwa „Architekturaufnahme eines
verlassenen Krankenhausflurs“. Lange Listen verbotener Personen vermeiden: Das
Bildmodell kann erwähnte Personen trotz einer Verneinung zeichnen. Jede Kachel
nur mit den dort benötigten Figuren belegen. Leere Szenen erhalten `characters: []`.

Texte separat setzen lassen. Das Bildmodell soll keine Erzählerkästen oder
Sprechblasen zeichnen. Lesbarkeit und korrekte Sprecherzuordnung sind wichtiger
als möglichst viel Text in einer Kachel. Generierte Beschriftungen auf Akten oder
Ausweisen sind dekorativ und dürfen nicht als Faktenquelle verwendet werden.

## Dateien und Dienste

| Bestandteil | Ort oder Adresse |
|---|---|
| Projektverzeichnis auf dem Host | `/home/jee/docker/minimax-h3-dgx-spark` |
| Einziger Aufruf für den vollständigen Export | `scripts/render_editorial_comic.py` |
| Seitenlayout und Erzähler-Porträt | `scripts/layout_editorial_comic.py` |
| Redaktioneller Renderer im Dienst | `automation/comics/editorial.py` |
| Compose-Datei | `docker-compose.comic-automation.yml` |
| Workflow-Vorlage | `examples/comics/workflows/04_Comic_Automat_9B.json` |
| Vollständiges Beispiel | `examples/comics/editorial/marius-dick/storyboard.json` |
| Artikel zum Beispiel | `examples/comics/editorial/marius-dick/article.txt` |
| ComfyUI | `http://192.168.1.224:8188` |
| Comic-Automat und Downloads | `http://192.168.1.224:8090` |
| Standardcontainer des Automaten | `comic-automation-comic-automation-1` |

Die Netzwerkadressen beschreiben die eingerichtete lokale Umgebung. Auf einem
anderen Rechner müssen Adresse und gegebenenfalls Containername angepasst werden.

## Voraussetzungen

Auf dem Host werden Python 3 mit Pillow, Zugriff auf Docker und das Repository
benötigt. ComfyUI sowie der Comic-Automat müssen laufen. Die lokalen Bildmodelle:

- `flux-2-klein-9b-bf16.safetensors`
- `qwen_3_8b.safetensors`
- `flux2-vae.safetensors`

Bei bereits eingerichteter Umgebung genügt der Skriptaufruf. Für eine neue
Installation siehe [vollständige Automationsanleitung](../automation/comics/README.md#installation-und-start).
Der Installationshelfer startet ComfyUI neu und ist kein notwendiger Schritt für
jeden Comic.

## Storyboard vorbereiten

Das vollständige Beispiel als Vorlage verwenden und für eine neue Geschichte
kopieren. Neben dem Originalartikel enthält es folgende Angaben:

| Feld | Bedeutung |
|---|---|
| `title` | Deutscher Comictitel |
| `article` | Originalgeschichte beziehungsweise bereitgestellter Artikel |
| `style` | Unterstützter Stil, etwa `Großstadt-Noir (düster)` |
| `seed` | Fester Startwert zur reproduzierbaren Bilderzeugung |
| `signature` | Signatur oder Hinweis auf symbolische Darstellung und Quellenstand |
| `characters` | Private Figurenprofile mit stabilen IDs, Aussehen und Kleidung |
| `library_ids` | IDs zusätzlich verwendeter Figuren aus der vorhandenen Bibliothek |
| `scenes` | Eine Szene pro Kachel; die Länge bestimmt die Kachelanzahl |
| `revisions` | Optional neue Bildvariante pro Kachel, mit nullbasiertem Index |
| `reference_overrides` | Optional eingebettete Referenzbilder für bekannte Figuren |
| `narrator_badge` | Optionales Sysop-Porträt neben dem Erzählertext |

Jede Szene enthält:

```json
{
  "heading": "Ein unerwarteter Fund",
  "story": "Markus steht links an der Treppe. In seiner Hand liegt ein geöffneter Brief. Nahaufnahme im kühlen Morgenlicht.",
  "dialog": "Auf der letzten Stufe lag ein Brief ohne Absender.",
  "characters": ["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
  "bubbles": [
    {
      "speaker": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "text": "Wer hat ihn hier hingelegt?",
      "expression": "normal"
    }
  ]
}
```

Die Beispiel-ID muss im Figurenprofil des eigenen Storyboards existieren.
`dialog` ist der Erzählertext; gesprochene Worte gehören nach `bubbles`.
Ohne gesprochene Worte `bubbles: []` setzen. Für das Erzähler-Porträt benötigt die
aktuelle Layoutfunktion die Sysop-ID als ersten Eintrag in `library_ids` und ein
zugehöriges eingebettetes PNG unter `reference_overrides`, wie im vollständigen
Marius-Beispiel. Ohne dieses Porträt `narrator_badge` weglassen oder auf `false` setzen.

## Sofort einen vollständigen Comic erzeugen

Auf dem Docker-Host im Projektverzeichnis:

```bash
cd /home/jee/docker/minimax-h3-dgx-spark
python3 scripts/render_editorial_comic.py \
  examples/comics/editorial/marius-dick/storyboard.json
```

Jeder Aufruf ohne `--job` erzeugt einen neuen Auftrag. Das Skript:

1. Prüft Eingabe und legt eine Auftrags-ID an.
2. Übergibt den festen Szenenplan an den lokalen Renderer.
3. Erzeugt bei Bedarf private Figurenreferenzen und die Kachelbilder.
4. Setzt die Texte sowie gegebenenfalls das Sysop-Porträt.
5. Erstellt Teilseiten mit bis zu vier Kacheln und eine PDF.
6. Überträgt das Layout in den eigenen Auftrag und erzeugt das Downloadpaket.
7. Schließt den Auftrag ab und bereinigt dessen temporäre ComfyUI-Dateien.
8. Lädt das ZIP auf den Host und gibt Ausgabeort sowie Downloadlinks aus.

## Empfohlener Ablauf mit Sichtprüfung und Korrekturen

Zunächst als bearbeitbaren Entwurf rendern:

```bash
python3 scripts/render_editorial_comic.py meine-geschichte.json --draft
```

Die ausgegebene Auftrags-ID aufbewahren. Danach Bilder, Beschriftungen und Seiten
prüfen und das Storyboard bei Bedarf ändern. Den offenen Auftrag erneut ausführen:

```bash
python3 scripts/render_editorial_comic.py meine-geschichte.json \
  --job AUFTRAGS_ID --draft
```

`AUFTRAGS_ID` durch die ausgegebenen 32 kleinen Hexadezimalzeichen ersetzen.
Unveränderte Kacheln können aus dem Zwischenspeicher übernommen werden. Eine neue
Bildbeschreibung ändert die betreffende Illustration. Für einen neuen Bildversuch
bei gleicher Beschreibung beispielsweise den Wert für die erste Kachel erhöhen:

```json
"revisions": {"0": 2}
```

Zum Abschließen denselben Auftrag ohne `--draft` aufrufen:

```bash
python3 scripts/render_editorial_comic.py meine-geschichte.json \
  --job AUFTRAGS_ID \
  --review "Alle Kacheln auf Bildinhalt, Lesbarkeit und Texttreue geprüft."
```

Diesen Prüfvermerk nur verwenden, wenn die Prüfung tatsächlich erfolgt ist.
Standardmäßig vermerkt das Skript ausdrücklich, dass es keine visuelle Prüfung
vorgenommen hat. Abgeschlossene Aufträge werden nicht erneut gerendert. Für eine
weitere Fassung ohne `--job` einen neuen Auftrag anlegen. Auch grundlegende
Änderungen an Stil, Startwert, Kachelanzahl oder Bibliotheksauswahl benötigen im
aktuellen Skriptmodus einen neuen Auftrag.

## Ergebnisse

Standardverzeichnis auf dem Host:

```text
diagnostics/comics/<Auftrags-ID>/
```

| Datei | Inhalt |
|---|---|
| `comic.png` | Alle Kacheln als Gesamtbild |
| `pages/01.png` und weitere | Teilseiten mit bis zu vier Kacheln |
| `comic.pdf` | Mehrseitige PDF |
| `panels/` | Einzelkacheln und Illustrationen |
| `workflow.json` | Bearbeitbarer Workflow mit Figurenreferenzen |
| `editorial-source.json` | Übergebener redaktioneller Szenenplan |
| `story.json` | Geschichte und Titel |
| `report.json` | Prüfhinweise und Exportbericht |
| `comic-bundle.zip` | Zusammengehörende Dateien als Paket |
| `render-job.json` | Lokale Auftrags-ID und Pfad zur Eingabedatei |

Downloadadressen folgen diesem Muster:

```text
http://192.168.1.224:8090/jobs/<Auftrags-ID>/artifacts/comic.png
http://192.168.1.224:8090/jobs/<Auftrags-ID>/artifacts/comic.pdf
http://192.168.1.224:8090/jobs/<Auftrags-ID>/artifacts/comic-bundle.zip
```

Der Workflow reproduziert Illustrationen und Beschriftungen. Die zusätzlichen
Erzähler-Porträts und Teilseiten werden durch das Layoutskript ergänzt; dieser
Zusatzschritt ist im exportierten Workflow dokumentiert.

## Optionen und Fehlerbehebung

```bash
python3 scripts/render_editorial_comic.py --help
```

- `--output VERZEICHNIS`: eigener Ausgabeort; ein fremdes nicht leeres Verzeichnis wird abgelehnt.
- `--base-url URL`: Adresse des Comic-Automaten.
- `--container NAME`: Name des bereits laufenden Automationscontainers.
- `COMIC_AUTOMATION_URL` und `COMIC_AUTOMATION_CONTAINER`: entsprechende Umgebungsvariablen.
- `COMIC_AUTOMATION_API_TOKEN`: falls die HTTP-API mit einem Zugangsschlüssel geschützt ist.

Bei einem Abbruch vor dem Abschluss mit derselben `--job`-ID fortsetzen. Bei
Fehlern im Seitenlayout wird der Auftrag nicht abgeschlossen. Bei einem bereits
abgeschlossenen Auftrag dessen Downloadlinks verwenden oder für eine neue Fassung
einen neuen Auftrag anlegen. Ein voller Kachelcache ist nicht dauerhaft garantiert,
etwa nach Neustart oder Bereinigung von ComfyUI.

## Weiterführende Anleitungen

- [Comic-Studio mit Figuren und Sprechblasen](../examples/comics/README.md)
- [Comic-Automat, Installation und technische Details](../automation/comics/README.md)
- [Hauptdokumentation](../README.md)

## Ressourcen sparen durch lokale Vorarbeit

[Getestete lokale Arbeitsteilung mit Quellenaufbereitung und Bildprüfung](Comic_Lokale_Arbeitsteilung.md).
Mit `--local-check` ergänzt der Renderaufruf eine lokale Bildvorprüfung und bleibt
immer als Entwurf offen. Der freigegebene Szenenplan wird dabei nicht geändert.

## Geschichten im Browser verwalten

Auf der [Redaktionsseite](http://192.168.1.224:8090/) können Storyboards importiert,
gespeichert und bearbeitet werden. Jede Erzeugung legt eine neue Ausgabe an.
Der Stilwechsel erhält den Szenenplan. **Storyboard herunterladen** liefert die
bearbeitete JSON für den hier beschriebenen Skriptablauf.

Verfügbar sind elf Bildstile: die bisherigen fünf sowie Graphic Novel realistisch,
Holzschnitt / Linolschnitt, Retro-Zeitungscomic, Europäischer Abenteuercomic,
Science-Fiction / Cyberpunk und Warme Alltagsillustration.
Die [Verwaltungsanleitung](../automation/comics/README.md#geschichten-auf-der-redaktionsseite-verwalten)
beschreibt auch das Löschen und den separaten automatischen Geschichtenautor.


## Artikel ohne JSON im Dashboard beginnen

Für den einfachen Browserablauf genügt: Titel und Artikel eingeben, Stil und
Kachelanzahl wählen, **Szenen erstellen** anklicken und die lokale Vorplanung
prüfen. Danach zeichnet **Comic erzeugen** den bestätigten Plan. Ein JSON-Import
ist für diesen Einstieg nicht erforderlich. Der Skriptablauf selbst erwartet
weiterhin das fertige Storyboard; es kann unter **Erweiterte Optionen** exportiert
werden. Der dortige lokale Zugangsschlüssel gehört zum Dashboard und nicht zu
ChatGPT oder OpenAI.

## Dieselben Comics anhand einer Bewertung verbessern

An einer bewerteten Ausgabe gibt es die Aktion **Diesen Comic anhand meiner
Bewertung verbessern**. Sie übernimmt den oben gewählten Bildstil und behält die
Kachelanzahl der bewerteten Ausgabe. Die ursprüngliche Geschichte und ihre
Figurenreferenzen bleiben erhalten. Das Ergebnis ist eine neue Ausgabe mit einem
Änderungsbericht; die bisherige Ausgabe bleibt verfügbar.

Bei einem Stilwechsel werden alle Bilder neu gezeichnet. Sonst können unveränderte
Illustrationen übernommen werden. **Neue Geschichte erfinden** ist eine getrennte
Aktion und erstellt eine andere Handlung.
