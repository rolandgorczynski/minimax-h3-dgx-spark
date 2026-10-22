# Polnische Facebook-Plakate

Der Workflow `workflows/01_Plakat_Facebook_PL.json` erzeugt PNG-Dateien mit
1080 × 1350 Pixeln. FLUX.2 Klein 9B BF16 zeichnet die Illustration direkt im lokalen
ComfyUI auf dem Spark. Ein eigener Knoten setzt polnische Veranstaltungstexte,
das unveränderte Logo und bei Bedarf einen Partnerstreifen darüber. Die Berechnung
nutzt keine Cloud. Diese Anleitung ist deutsch; die Vorlagen erzeugen weiterhin
polnische Plakate.

## Installation

Erforderlich sind eine bestehende ComfyUI-Installation und diese lokalen Modelle:

- `models/diffusion_models/flux-2-klein-9b-bf16.safetensors`
- `models/text_encoders/qwen_3_8b.safetensors`
- `models/vae/flux2-vae.safetensors`

Auf dem dokumentierten Spark wurden sie aus einer vorhandenen lokalen 9B-Kopie
vorbereitet. Der Workflow enthält die Standardknoten **UNETLoader**,
**CLIPLoader** mit Typ `flux2` und **VAELoader**. Der Hauptknoten nutzt ComfyUI zur
Textkodierung, `Flux2Scheduler`, Euler-Abtastung mit vier Schritten und
VAE-Dekodierung. Er ruft keinen externen Bilderzeugungsdienst über HTTP auf.

Im Projektverzeichnis ausführen:

```bash
./scripts/install_posters.sh
docker compose up -d
```

Läuft ComfyUI bereits, nach der Aktualisierung der Knoten
`docker restart minimax-h3-comfyui` ausführen. Der Installer kopiert Knoten, Logo und
Workflows in das persistente Datenverzeichnis. Geänderte vorhandene Vorlagen werden
vorher unter `user/default/workflow-backups/<Datum>/` gesichert. Andere Projekte
bleiben unverändert.

Zusätzliche Pakete, `flux-klein-spark`, das Netz `hycanvas-ai` oder ein API-Schlüssel
sind nicht erforderlich. Die ältere Datei `user/default/dgx-posters.json` wird nicht
mehr gelesen. `docker-compose.posters.yml` bleibt eine leere Ergänzungsdatei zur
Kompatibilität mit bisherigen Compose-Aufrufen. Nach einem Update eine der drei
aktuellen Vorlagen neu öffnen, damit die lokalen Modelle angeschlossen sind.
Ältere Kopien ohne Modellverbindungen zeigen einen Hinweis statt einen externen
Dienst aufzurufen.

## Verwendung

1. ComfyUI öffnen und die Seite neu laden. Unter der Workflow-Auswahl den Ordner
   `Plakaty` und die Vorlage `01_Plakat_Facebook_PL` wählen.
2. Veranstalter, Titel, Themen und Vortragende, Datum, Uhrzeit und Ort eingeben.
3. Die gewünschte Illustration beschreiben. Das Beschreibungsfeld akzeptiert auch polnische Texte.
4. **Ausführen** anklicken. Die fertige PNG-Datei erscheint in der Vorschau und unter `output/plakaty/`.

Das Logo ist im Knoten `Load Image` vorbereitet und kann durch eine eigene PNG-Datei
ersetzt werden. Für den optionalen Partnerstreifen einen zweiten `Load Image`-Knoten
hinzufügen, dessen Ausgang `IMAGE` mit `belka` und `MASK` mit `maska_belki` verbinden.
Empfohlen ist ein waagerechter Streifen mit einem Seitenverhältnis von mindestens
6:1. Ohne Streifen steht der Platz für den Inhalt zur Verfügung.

Für ein eigenes Foto `generuj_obraz` deaktivieren und `IMAGE` mit
`wlasna_ilustracja` verbinden. Dann wird kein Bild generiert; die Modellknoten können
getrennt werden. Ein anderer Startwert erzeugt eine neue Illustration. Unveränderte
Aufrufe können den ComfyUI-Zwischenspeicher verwenden.

Das Datum hat das Format `JJJJ-MM-TT`; der Wochentag wird berechnet. Texte werden
unverändert übernommen, Namen und Inhalte nicht automatisch korrigiert. Bei zu
langem Text erscheint eine Meldung, statt Text abzuschneiden. Die Illustration wird
auf einen breiten Ausschnitt zugeschnitten; wichtige Motive nahe der Mitte anordnen.
Die Vorlage hat eine feste Gestaltung und übernimmt keine beliebigen Anordnungen
aus Referenzbildern. Die PNG-Datei enthält den Workflow ohne API-Schlüssel und kann
wieder in ComfyUI gezogen werden. Die Ausgabe ist ein Rasterbild; Texte lassen sich
über die Workflow-Felder ändern.

[Quelle des Logos](https://github.com/rolandgorczynski/rkgm/blob/main/RadaKobietGminyMirsk-transparent.png).

## Vorbereiteter Partnerstreifen und Wappen von Mirsk

Unter `Plakaty` die Vorlage `02_Plakat_Facebook_PL_belka_herb` öffnen. Die
Originaldateien für Partnerstreifen und Wappen sind bereits angeschlossen.
`pokaz_belke` und `pokaz_herb` schalten beide Elemente unabhängig voneinander.
Das Wappen mit der Beschriftung „Gmina Mirsk“ steht im Kopfbereich, der Streifen
am unteren Rand. Ohne Streifen bleibt mehr Platz für die Illustration.

Die Dateien werden bei der Installation kopiert und während der Erzeugung nicht
aus dem Internet geladen. Eigene Dateien in den jeweiligen `Load Image`-Knoten
hochladen. Die bisherige Vorlage bleibt verfügbar.

Quellen: [Partnerstreifen](https://github.com/rolandgorczynski/rkgm/blob/main/belka.jpeg),
[Wappen](https://github.com/rolandgorczynski/rkgm/blob/main/HerbMirsk.jpeg).

## Dritte Vorlage: Bild hochladen, analysieren und zum Plakat machen

Das Modell zur Bildanalyse einmalig herunterladen:

```bash
./scripts/download_poster_vision.sh
./scripts/install_posters.sh
docker restart minimax-h3-comfyui
```

Unter `Plakaty` die Vorlage `03_Plakat_z_obrazka_Vision_PL` öffnen. Im vorhandenen
Referenzbildknoten `Wgraj obrazek referencyjny` die Funktion zum Hochladen einer Datei
wählen und ein Bild vom eigenen Rechner öffnen. Es handelt sich um den üblichen
ComfyUI-Knoten `Load Image`. Ein Beispielbild ist vorbereitet. Für den Zugriff auf
das hochgeladene Bild wird keine Internetverbindung benötigt.

Das lokale Modell [SmolVLM-500M-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM-500M-Instruct)
erzeugt intern eine englische Szenenbeschreibung für FLUX. Es ist auf die Revision
`a7da5b986cb59b408707209984f360a5f4ad7e47` festgelegt und liegt unter
`models/vision/SmolVLM-500M-Instruct`. Während der Analyse lädt es nichts nach.
Es läuft auf der CPU und wird anschließend aus dem Speicher entfernt. Verwendet
werden die vorhandenen Bibliotheken Transformers, PyTorch und Pillow. Details
können übersehen oder Gegenstände falsch erkannt werden.

Das Ergebnis erscheint in der Vorschau des Bildanalyseknotens und ist mit
`opis_z_obrazu` verbunden. Es ersetzt die manuelle Eingabe `opis_ilustracji` im
Hauptknoten. Mit `poprawiony_opis` lässt sich die Modellantwort durch eigenen Text
ersetzen. Bleibt das Feld leer, wird die Beschreibung automatisch erzeugt.

Veranstaltungsdaten weiterhin getrennt auf Polnisch eintragen. Logo, Wappen und
Partnerstreifen werden als Originaldateien eingesetzt. Um zuerst nur die
Beschreibung zu prüfen, den Plakat-Hauptknoten mit **Strg+M** deaktivieren, die
Bildanalyse ausführen und den Hauptknoten anschließend wieder aktivieren.

Der ältere Knoten `DGXImageURL` bleibt für gespeicherte Projekte kompatibel, wird
in dieser dritten Vorlage aber nicht verwendet. Er akzeptiert öffentliche
HTTP-/HTTPS-Adressen und den lokalen ComfyUI-Endpunkt `/view`; die Grenzen liegen
bei 20 MB und 20 Megapixeln.

## Vorhandene 9B-Gewichte für ComfyUI vorbereiten

Die Gewichte müssen nicht erneut geladen werden; ein eigener FLUX-Dienst ist nicht
nötig. Liegt das Modell als Diffusers-Modellstand mit `transformer/` und
`text_encoder/` vor, native ComfyUI-Dateien vorbereiten:

```bash
python3 scripts/prepare_poster_9b.py /pfad/zum/Modellstand/FLUX.2-klein-9B /pfad/zu/ComfyUI/models
./scripts/install_posters.sh
```

Das Skript verwendet ausschließlich die Python-Standardbibliothek. Es verbindet
Teildateien, ordnet Tensornamen dem ComfyUI-Format zu, verbindet Q/K/V und passt die
Reihenfolge von Skalierung und Verschiebung der abschließenden Modulation an.
Die Gewichte bleiben ohne Quantisierung in BF16. Etwa 35 GB zusätzlicher Speicher
werden benötigt; Quelldateien und bereits vorhandene Zieldateien werden nicht
überschrieben. Der erforderliche FLUX2-VAE wird auch von der 4B-Variante verwendet.
Nach der Installation die Modellliste aktualisieren und den aktuellen Workflow öffnen.
