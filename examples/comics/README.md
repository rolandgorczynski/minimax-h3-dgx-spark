# Sysop-Comics vollständig in ComfyUI

Zwei Workflows mit dem vorhandenen FLUX.2 Klein 9B BF16, Qwen3 8B und FLUX2 VAE.
Keine zusätzlichen Dienste, API-Schlüssel oder Python-Pakete.

## Installation

```bash
./scripts/install_comics.sh
docker restart minimax-h3-comfyui
```

Browser mit Strg+F5 neu laden. Unter **Workflows → Comics** erscheinen:

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

**02_Sysop_Gesamtgeschichte_9B** enthält einen gemeinsamen Editor:

1. Originalartikel in **artikel** einfügen, **comic_art** und **anzahl_kacheln** (1–12) wählen.
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
bleibt erhalten. Änderungen an Artikel, Stil, Kachelanzahl oder Seed erfordern
einen neuen Plan. Das Generieren ersetzt niemals stillschweigend den geprüften Plan.
Der normale ComfyUI-Ausführen-Knopf wiederholt die zuletzt gewählte Aktion;
für den Ablauf die beiden Schaltflächen im Editor verwenden.

Workflow speichern, um Artikel, korrigierte Szenen, Kachelrevisionen und
Vorschauen zu behalten. Reine Textkorrekturen setzen nur die Beschriftung neu;
Änderungen an einer Szenenbeschreibung zeichnen diese Szene neu.
Titel, Spaltenzahl und Signatur lassen sich unabhängig ändern.
Die Gesamtgeschichte darf maximal 16000 Zeichen enthalten. Das Sprachmodell
kann Details verändern; Szenen und Aussagen vor Veröffentlichung prüfen.

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
Es gibt eine Sprechblase pro Kachel; ein leeres Dialogfeld lässt sie weg.
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
