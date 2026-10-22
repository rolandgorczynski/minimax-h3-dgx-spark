# Sysop-Comics vollständig in ComfyUI

Drei Workflows mit dem vorhandenen FLUX.2 Klein 9B BF16, Qwen3 8B und FLUX2 VAE.
Keine zusätzlichen Dienste, API-Schlüssel oder Python-Pakete.

Für den separaten Comic-Automaten und den wiederholbaren Export eines redaktionell
erstellten Storyboards siehe die [Automationsanleitung](../../automation/comics/README.md).
Dieser zusätzliche Skriptmodus benötigt den laufenden Automationscontainer und
Pillow auf dem Host:

```bash
python3 scripts/render_editorial_comic.py examples/comics/editorial/marius-dick/storyboard.json
```

Er erzeugt Comic, Teilseiten, PDF und ZIP mit Workflow unter
`diagnostics/comics/<Auftrags-ID>/`. Mit `--draft` bleibt der Auftrag bearbeitbar;
mit `--job <Auftrags-ID>` lässt er sich nach Änderungen erneut rendern. Artikel und
Szenen werden in diesem Modus unverändert übernommen.

## Installation

```bash
./scripts/install_comics.sh
docker restart minimax-h3-comfyui
```

Browser mit Strg+F5 neu laden. Unter **Workflows → Comics** erscheinen:

- **03_Comic_Studio_9B**: Empfohlener Einstieg. Ein Editor für Artikel, Figuren mit eigenen Bild-Uploads, Szenen und mehrere Sprechblasen. Kein separater Sysop-Bildknoten.
- **01_Sysop_Comic_9B**: Kachelanzahl wählen und für jede Kachel Szene und Dialog schreiben.
- **02_Sysop_Gesamtgeschichte_9B**: Artikel einfügen, Stil und Anzahl wählen, Szenen planen und prüfen, dann Comic und einzelne Bildvarianten generieren.

Die Modelle müssen bereits in ComfyUI vorhanden sein:

```text
models/diffusion_models/flux-2-klein-9b-bf16.safetensors
models/text_encoders/qwen_3_8b.safetensors
models/vae/flux2-vae.safetensors
```

Zur Übernahme vorhandener 9B-Dateien siehe [Plakat-Anleitung](../posters/README.md).
Der Installer sichert geänderte vorhandene Vorlagen vor dem Aktualisieren in
`user/default/workflow-backups/`. Er verändert keine anderen Projekte.

## Artikel → Szenen prüfen → Comic

**03_Comic_Studio_9B** enthält einen gemeinsamen Editor. Der bisherige
**02_Sysop_Gesamtgeschichte_9B** funktioniert ebenfalls weiter:

1. Originalartikel in das große Feld **Originalartikel / Gesamtgeschichte** einfügen, **comic_art** und **anzahl_kacheln** (1–12) wählen.
2. **1 · Szenen planen** anklicken. Qwen3 erstellt pro Kachel eine eigene Szene
   und einen Erzählertext. In diesem Schritt werden keine Bilder generiert.
3. Die Szenen und Texte direkt im Editor prüfen und korrigieren.
4. **2 · Weiter: Comic generieren** anklicken. FLUX zeichnet den geprüften Plan.
5. Unter jeder Szene erscheint eine Vorschau. Szenen oder Texte ändern und
   erneut **Weiter** anklicken; unveränderte Bilder werden wiederverwendet.
   **Kachel N neu zeichnen** erzeugt gezielt eine neue Bildvariante dieser Kachel.

Es gibt nur eine Stilauswahl: klassischer Comic, Großstadt-Noir (düster),
Ligne claire, Manga Schwarzweiß oder Aquarell-Reportage. Sie steuert Planung
und Bilder. Großstadt-Noir zeigt Sysop als Erzähler-Silhouette im dunklen Mantel.
Der [Beispielartikel](articles/marius-dick.txt) ist unverifiziertes Ausgangsmaterial;
seine Zeitangaben werden aus dem Artikel übernommen.

Die Planung verwendet keine vorgegebenen Standardszenen. Die Eingabesprache
bleibt erhalten. Der Bildstil lässt sich auch nach dem Planen ändern; Szenen und Texte bleiben erhalten.
**Weiter** zeichnet die Bilder im neu gewählten Stil. Änderungen an Artikel,
Kachelanzahl oder Seed erfordern
einen neuen Plan. Das Generieren ersetzt niemals stillschweigend den geprüften Plan.
Der normale ComfyUI-Ausführen-Knopf wiederholt die zuletzt gewählte Aktion;
für den Ablauf die beiden Schaltflächen im Editor verwenden.

Workflow speichern, um Artikel, korrigierte Szenen, Kachelrevisionen und
Vorschauen zu behalten. Reine Textkorrekturen setzen nur die Beschriftung neu;
Änderungen an einer Szenenbeschreibung zeichnen diese Szene neu.
Titel, Spaltenzahl und Signatur lassen sich unabhängig ändern.
Die Gesamtgeschichte darf maximal 16000 Zeichen enthalten. Das Sprachmodell
kann Details verändern; Szenen und Aussagen vor Veröffentlichung prüfen.

## Figuren über mehrere Storys wiederverwenden

Im Artikel-Editor **Figurenbibliothek** öffnen. Unter **Figur anlegen / bearbeiten**
Name, alternative Namen (zum Beispiel Markus und Marcus), festes Aussehen,
Standardkleidung und optionale Kleidungsvarianten eintragen. Eine Variante steht
pro Zeile als `Winter: blauer Mantel`. **Figur dauerhaft speichern** schreibt den
Steckbrief auf den Server. Bei **jeder Figur** stehen direkt **Bild 1** und **Bild 2**
zum Hochladen bereit: Gesicht, Ganzkörper oder eine andere Ansicht (je maximal 12 MB).
Auch beim Anlegen sind die Upload-Felder sichtbar; ein ausgefüllter Steckbrief wird
vor dem Upload gespeichert.

Sysop wird einmalig mit der vorhandenen Sysop-Bildreferenz angelegt. Eigene Änderungen
an ihm bleiben erhalten. Ein Upload bei einer bereits ausgewählten Figur übernimmt
das neue Bild auch in die geöffnete Story; andere gespeicherte Storys behalten ihre
bisherigen Bilder. Die Figurenbeschreibungen bleiben dabei unverändert und sind bei
Bedarf an das neue Bild anzupassen. Im Artikel-Workflow sind die Bilder aus der
Figurenbibliothek maßgeblich; der bisherige separate Sysop-Bildknoten wird dafür
nicht zusätzlich als Referenz an das Modell übergeben.

**Für diese Story übernehmen** oder das Häkchen neben einer Bibliotheksfigur
kopiert sie in die aktuelle Geschichte. Bis zu acht Figuren können ausgewählt
werden. Die Planung erhält ihre festen Beschreibungen und alternativen Namen.
Unter jeder geplanten Kachel zeigen Häkchen, welche Figuren dort vorkommen.
Anfangs erfolgt die Zuordnung anhand ihrer Namen; sie ist manuell korrigierbar.
Nur die zugeordneten Figurenbeschreibungen und Referenzbilder gehen in die
Bilderzeugung dieser Kachel ein. **Sysop ist ebenfalls eine Bibliotheksfigur**: Er
ist anfangs ausgewählt und kann wie jede andere Figur bearbeitet oder abgewählt werden.

**Kleidung nur für diese Story** und die Auswahl einer Kleidungsvariante verändern
die Bibliotheksfigur nicht. Bei einer neuen Story lassen sich dieselben Figuren
wieder auswählen. Artikel-, Stil- und Szenenänderungen entfernen die Figuren nicht.
Ein Stilwechsel ändert die zeichnerische Darstellung; die Identitätsvorgaben bleiben.
Bereits geprüfte Szenen werden beim Auswählen von Figuren nicht gelöscht. Für einen
neuen Szenenentwurf mit diesen Figuren ausdrücklich **Szenen planen** verwenden.

Jede Story speichert eine Kopie ihrer Figuren. Änderungen in der Bibliothek wirken
erst mit **Aktuelle Bibliotheksversion übernehmen** auf die geöffnete Story.
Ältere Referenzbilder bleiben für gespeicherte Storys erhalten. Die Bibliothek liegt
unter `user/default/dgx-comics/characters/`, die Bilder unter `references/` darin.
Diesen Ordner bei Backups mit sichern; ein exportierter Workflow enthält die
Figurenbeschreibungen und Bildverweise, nicht die Bilddateien selbst.

Referenzbilder verbessern die Wiedererkennbarkeit. Die generativen Modelle können
Gesichtsdetails und Kleidung trotzdem verändern; eine pixelgenaue Identität ist
nicht garantiert. Beschreibungen und Referenzen auf wenige klare Merkmale begrenzen.

## Doppelte Figuren löschen

Neben jeder Bibliotheksfigur steht **Löschen: Name**. Bei gleichen Namen helfen
Bildvorschau und die angezeigte kurze ID, die Einträge auseinanderzuhalten.
Nach dem Klick den ausgewählten Eintrag mit **Löschen bestätigen** entfernen
oder **Abbrechen** wählen. Die Löschung betrifft nur den Bibliothekseintrag:
Gespeicherte Figurenkopien, Sprechblasen und Referenzbilder älterer Storys bleiben
verwendbar. Auch eine in der geöffneten Story ausgewählte Kopie bleibt erhalten;
bei Bedarf dort zusätzlich **Aus dieser Story entfernen** verwenden.

Ein gelöschter Sysop wird nicht automatisch neu angelegt. Intern werden entfernte
Steckbriefe unter `user/default/dgx-comics/characters/archived/` aufbewahrt;
ihre Bilddateien bleiben für bereits gespeicherte Storys verfügbar.

## Eigene Sprechblasen für jede Figur

Im Artikel-Editor unterstützt jede Kachel bis zu sechs getrennte Sprechblasen.
**Sprechblase hinzufügen**, **Sprecher** auswählen und den Text eingeben.
Bibliotheksfiguren werden über ihre feste ID zugeordnet; mit **Andere Figur**
kann auch ein nur in dieser Szene vorkommender Sprecher benannt werden.
Eine sprechende Bibliotheksfigur wird in der Kachel automatisch mit berücksichtigt.

Benannte Originaldialoge wie `Markus: "Nein! Nein!" Verbrecher: "Halt die Klappe!"`
werden bei der Planung getrennt übernommen. Bei manuell bearbeiteten Szenen kann
**Benannte Dialoge aus Szene übernehmen** sie ebenfalls in separate Blasen kopieren.
Dabei bleiben Szene und bisheriger Text erhalten; den Erzählertext bei Bedarf
anschließend kürzen, damit die Aussagen nicht doppelt erscheinen.

Die Vorschau wird ohne Bildmodell mit den tatsächlich verwendeten Schriften erzeugt.
Gelben Rahmen ziehen = Blase verschieben; gelbe Ecke unten rechts = Größe ändern;
roten Punkt ziehen = Spitze zum Sprecher richten. Mit den Pfeiltasten lassen sich
fokussierte Griffe ebenfalls bewegen; Positionen sind zusätzlich in Prozent editierbar.
Die Spitzen zunächst am erzeugten Bild kontrollieren: Figurenpositionen werden nicht
automatisch erkannt. Auf einer grauen Fläche lässt sich die Beschriftung schon vor
der ersten Bilderzeugung vorbereiten.

**Sprechen**, **Schreien** und **Flüstern** verändern die Gestaltung der Blase.
Der Sprechername kann zur eindeutigen Zuordnung angezeigt oder ausgeblendet werden.
Der **Erzählerkasten** ist davon getrennt und hat keine Sprechblasenspitze.
Alle Texte, Sprecher, Größen und Positionen werden mit dem Workflow gespeichert.
Mit **Weiter: Comic generieren** wird die fertige Beschriftung in die Einzelbilder
und den Gesamtcomic übernommen. Text- und Positionskorrekturen verwenden die
vorhandene Illustration erneut. Änderungen an Figuren oder Szenen können dagegen
neue Illustrationen erfordern. Zu lange Texte werden bereits vor der Bildgenerierung
abgelehnt; dann die Blase vergrößern oder den Text kürzen.
Ältere Pläne mit nur einem Dialogfeld behalten ihre bisherige Darstellung.

## Jede Kachel selbst schreiben

Im ersten Workflow **anzahl_kacheln** auf 1–12 einstellen. Darunter erscheinen
pro Kachel **Szene / Handlung** und **Sprechblase (optional)**.
Die Szene beschreibt das sichtbare Geschehen, der Dialog wird separat gesetzt.
Bei verringerter Kachelanzahl bleiben die ausgeblendeten Einträge gespeichert.
Mehr Kacheln erfordern entsprechend ausgefüllte Szenenbeschreibungen.
Die Einzelgeschichte darf 4000, der Dialog 400 Zeichen haben; passt der Text
nicht in die Sprechblase, erscheint eine Fehlermeldung vor der Bilderzeugung.

## Sysop als gemeinsame Figur

Der linke **Load Image**-Knoten enthält einen Ausschnitt aus dem vom Benutzer
bereitgestellten [Comic-Beispiel](https://github.com/rolandgorczynski/komiks/blob/main/k1.jpg).
Er dient als Figuren- und Stilreferenz und lässt sich per Upload ersetzen.
Die Figurenbeschreibung ist ebenfalls editierbar. Jede Kachel verwendet dasselbe
Referenzbild: ComfyUI kodiert es mit dem VAE und übergibt das Referenz-Latent an
FLUX.2. Dafür werden weder LoRAs noch weitere Erweiterungspakete installiert.
Gesicht, Kleidung, Requisiten und Posen können zwischen Bildern abweichen;
eine pixelgenaue Figurenidentität ist nicht garantiert.

Die Szene wird einzeln generiert. Sprechblasen, Nummern, Titel und Signatur werden
anschließend mit Schriftdateien aus dem vorhandenen Einladungsmodul gesetzt.
Die manuelle Vorlage hat ein einfaches Dialogfeld pro Kachel; der Artikel-Editor
unterstützt mehrere sprechergebundene Sprechblasen und einen getrennten Erzählerkasten.
**spalten** wählt 1–4 Spalten. Eine unvollständige letzte Zeile bleibt weiß.

## Ergebnisse

Unter `output/comics/` liegen (beim Artikel-Workflow mit Präfix `artikel`):

- `sysop_00001.png`: zusammengesetzter Comic mit eingebettetem Workflow.
- `sysop_00001_panels/01_art.png`: unveränderte erzeugte Illustration.
- `sysop_00001_panels/01_panel.png`: Kachel mit Nummer und Sprechblase.
- `sysop_00001_panels/story.json`: tatsächlich verwendete Szenen, Dialoge und Einstellungen.

Weitere Läufe erhalten neue Nummern. Schon fertige Kacheln bleiben auch nach
Abbruch oder einem Fehler in einer späteren Kachel erhalten. Sie werden nicht
automatisch fortgesetzt. Das finale PNG kann zurück auf ComfyUI gezogen werden;
das Referenzbild muss auf dem Server weiter vorhanden sein.

Falls die Eingabefelder nicht erscheinen, Strg+F5 verwenden. Die Szenendaten
bleiben zusätzlich als JSON im Workflow gespeichert. Alle Modellberechnungen
laufen lokal; nach der Modellinstallation ist kein Internetzugang erforderlich.

Der Artikel-Workflow hält unveränderte Illustrationen zusätzlich unter
`output/comics/.panel-cache/` vor. Die Wiederverwendung berücksichtigt Szene,
Stil, Referenzbild, Modellkonfiguration, Seed und Kachelrevision.

## Selbstständig Comics erstellen

Der [Comic-Automat](../../automation/comics/README.md) läuft in einem separaten
Docker-Compose-Projekt und verwendet die eigene Vorlage **04_Comic_Automat_9B**.
Er entwickelt Geschichten und Figuren, prüft seine Entwürfe, generiert Comics und
exportiert die Ergebnisse über eine HTTP-Auftrags-API. Bestehende Workflows bleiben unverändert.
