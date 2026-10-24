<div align="center">

<img src="assets/icon.svg" alt="MiniMax H3 auf DGX Spark" width="120" />

### MiniMax H3 mit Bild und Ton auf einem einzelnen DGX Spark / GB10

Erprobte Bereitstellung von ComfyUI und MiniMax H3 für Text-zu-Video und Bild-zu-Video
mit Ton auf NVIDIA DGX Spark / GB10: ARM64, 128 GB gemeinsamer Arbeitsspeicher.
Die Modellberechnung und ihre Abhängigkeiten laufen in Docker-Containern.

[Schnellstart](docs/2026-08-04_MiniMaxH3_Erstes_Video.md) ·
[Fehlerbehebung](docs/Fehlerbehebung.md) ·
[Mehrteilige Videos](docs/2026-08-04_MiniMaxH3_Mehrteilige_Videos.md)

[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-1683c4?style=flat)](LICENSE)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-v0.30.0-32b643?style=flat)](https://github.com/comfyanonymous/ComfyUI)
[![Docker](https://img.shields.io/badge/Docker-compose-7e35d5?style=flat)](docker-compose.yml)

**Dokumentationssprache: Deutsch**

</div>

## Überblick

Dieses Repository beschreibt den Betrieb auf einem einzelnen NVIDIA DGX Spark / GB10
mit Blackwell SM121, aarch64 und etwa 121–128 GB gemeinsamem Arbeitsspeicher.
Die H3-Modellgewichte belegen etwa 42,5 GB. Grundlage der dokumentierten Konfiguration
sind NGC PyTorch 25.11 und ComfyUI v0.30.0. Modelle sowie Ein- und Ausgaben liegen
auf einem persistent eingebundenen NVMe-Laufwerk.

| Aufgabe | Ergebnis |
|---|---|
| MiniMax H3 bereitstellen | Containerumgebung und vier erforderliche Modelldateien mit fortsetzbarem Download |
| Erstes Video mit Ton erzeugen | Vollständiges Beispiel für die HTTP-API; im dokumentierten Test etwa 2–5 Minuten pro kurzem Film |
| Mehrere Abschnitte verbinden | Anleitung für acht Abschnitte mit je fünf Sekunden und einen Film mit 40 Sekunden |
| Comics ausarbeiten und rendern | Bearbeitbare Szenen, Figurenreferenzen, lokale Bilderzeugung und PDF-/ZIP-Ausgabe |

## Funktionen

- Auf dem Host werden DGX OS, Treiber, Docker und NVIDIA Container Toolkit benötigt.
  ComfyUI und Modellabhängigkeiten bleiben im Container; das angepasste NGC-PyTorch bleibt erhalten.
- Video-VAE in FP16 mit etwa 5,21 GB und Audio-VAE in FP32 mit etwa 0,605 GB erzeugen Bild und Ton gemeinsam.
- Hauptmodell: FL2VA pruned INT8 convrot mit etwa 21,0 GB; Textkodierer:
  Qwen3-VL-32B NVFP4 AWQ mit etwa 15,7 GB.
- Unter `scripts/` liegen Werkzeuge für Speicherinitialisierung, Vorprüfung,
  Downloads, Modellprüfung, Status und Diagnosedaten.
- Ergänzende Anleitungen behandeln Fehlerbehebung, Leistungsmessungen,
  Architektur, Einladungen, Plakate und Comics.

## Schnellstart

### 1. ComfyUI-Quelltext bereitstellen

Der Quelltext des Ursprungsprojekts wird separat heruntergeladen:

```bash
./scripts/prepare_comfyui_src.sh    # Lädt v0.30.0 nach comfyui-src/
```

### 2. Speicher initialisieren und Umgebung prüfen

```bash
make init DATA_ROOT=/mnt/<NVMe-Laufwerk>/minimax-h3
make preflight
make gpu-check
```

`make init` erzeugt `.env` und die Datenverzeichnisse. Die GPU-Prüfung sollte
`torch.cuda.is_available() = True` und `NVIDIA GB10` melden.
Während der Videoerzeugung andere große Modellcontainer wie Qwen oder vLLM
anhalten, damit der gemeinsame Arbeitsspeicher ausreicht.

### 3. Abbild bauen, Modelle laden und starten

```bash
make build
make download       # Vier benötigte Dateien, etwa 42,5 GB; Download fortsetzbar
make verify-models
make up && make logs
curl http://127.0.0.1:8188/system_stats
```

Auf die ComfyUI-Startmeldung mit Port 8188 warten. Der letzte Aufruf muss HTTP 200
liefern. Bei Verbindungsproblemen zu Hugging Face kann in `.env`
`HF_ENDPOINT=https://hf-mirror.com` gesetzt werden. Falls eine Anmeldung nötig ist,
`HF_TOKEN` ergänzen; Zugangsdaten nicht in Git einchecken.

### 4. torchaudio passend zu NGC-PyTorch kompilieren

Der H3-Audio-VAE benötigt `torchaudio`. Die dokumentierte NGC-PyTorch-Version
`2.10.0a0+b558c986e8.nv25.11` ist mit den üblichen vorgefertigten PyPI-Paketen
nicht ABI-kompatibel. Der Quelltextstand `87ff22e49ed0` vom 13. September 2025
ließ sich in der dokumentierten Umgebung erfolgreich bauen:

```bash
curl -L -o /tmp/torchaudio-src.tar.gz \
  https://codeload.github.com/pytorch/audio/tar.gz/87ff22e49ed0
docker cp /tmp/torchaudio-src.tar.gz minimax-h3-comfyui:/tmp/
docker exec minimax-h3-comfyui bash -c '
  cd /tmp && tar xzf torchaudio-src.tar.gz
  pip install --no-build-isolation --no-deps /tmp/audio-87ff22e49ed0
  python -c "import torchaudio; print(torchaudio.__version__)"
'
docker commit minimax-h3-comfyui local/minimax-h3-comfyui:v0.30.0-ta
```

Die getestete torchaudio-Version meldet `2.8.0a0`. Das neue Abbild muss beim
Neuerstellen des Containers auch ausgewählt werden. Einzelheiten zur dauerhaften
Installation und zum Einstiegspunkt stehen in der [Fehlerbehebung](docs/Fehlerbehebung.md).

### 5. Erstes Video mit Ton erzeugen

Die [Anleitung für das erste Video](docs/2026-08-04_MiniMaxH3_Erstes_Video.md)
enthält ein ausführbares Beispiel für die HTTP-API. Die wesentlichen Knoten sind:

```text
UNETLoader + CLIPLoader + zwei VAELoader für Video und Audio
→ MiniMaxH3SigmaShift → MiniMaxH3ImageToVideo
→ KSampler → VAEDecode und VAEDecodeAudio
→ CreateVideo / SaveVideo und SaveAudio
```

| Parameter | Wert | Erläuterung |
|---|---|---|
| `length` | 96 ≈ 4 s / 124 ≈ 5 s / 362 ≈ 15 s | 24 Bilder pro Sekunde; dokumentierte Obergrenze 15 s |
| `width×height` | 608×352 bis 1216×672 | Etwa 0,2 bis 0,8 Megapixel |
| `steps/cfg` | 20 / 1.0 | Dokumentierte H3-Einstellung mit `euler/simple` |
| Bild und Ton | SaveVideo + SaveAudio | Anschließend zusammenführen und Lautheit mit `loudnorm` normalisieren |

Für Bild-zu-Video das Referenzbild unter `<NVMe>/minimax-h3/input/` ablegen und
`LoadImage` mit `MiniMaxH3ImageToVideo.first_frame` verbinden.

## Dokumentierte Leistungsmessungen

Die folgenden Werte stammen aus den GB10-Tests vom 4. August 2026 und sind keine
neue Messung der jeweils installierten Umgebung.

| Aufgabe | Auflösung | Dauer | Rechenzeit |
|---|---:|---:|---:|
| Funktionstest | 608×352 | 4 s | 96,8 s |
| Standard | 736×416 | 5 s | 179,9 s |
| Alltagsbetrieb | 864×480 | 5 s | 255,8 s bei 20 Schritten |
| Bild-zu-Video im Hochformat | 768×1152 | 5 s | 15 min 22 s |
| Mehrteiliger Film | 8 × 5 s → 40 s | — | Etwa 50 min einschließlich Zusammenführung |

Der Aufwand steigt mit Bildanzahl und Auflösung. Einzelne protokollierte
Abtastschritte benötigten etwa 26–47 Sekunden; diese Werte gehören zu den
jeweiligen Testkonfigurationen und lassen sich nicht pauschal auf alle Zeilen übertragen.

## Betriebshinweise

- Installationen in der beschreibbaren Containerschicht gehen beim Neuerstellen
  verloren. Für Wiederverwendbarkeit im Abbild oder persistenten Datenträger sichern.
- `docker commit` übernimmt auch den Einstiegspunkt. Vor dem Neuerstellen mit
  `docker inspect <Abbild> --format '{{.Config.Entrypoint}}'` prüfen und gegebenenfalls
  `--entrypoint /usr/bin/tini ... -- /usr/local/bin/h3-entrypoint` setzen.
- PyTorch im Container nicht durch ein beliebiges PyPI-Paket ersetzen. Bei
  CUDA-Problemen zuerst Treiber und Container Toolkit mit `make gpu-check` prüfen.
- Bei Rückgabecode 137 oder einem stockenden System andere große Modelle anhalten
  und die Auflösung reduzieren.
- Für Ton müssen `VAEDecodeAudio` und `SaveAudio` angeschlossen sein.
- Den Dienst über einen SSH-Tunnel oder ein vertrauenswürdiges lokales Netz nutzen.

## Dokumentation

- [Erstes Video](docs/2026-08-04_MiniMaxH3_Erstes_Video.md): ausführbarer Ablauf über die HTTP-API
- [Mehrteilige Videos](docs/2026-08-04_MiniMaxH3_Mehrteilige_Videos.md): Abschnitte zusammenfügen und Kontinuität erhalten
- [Fehlerbehebung](docs/Fehlerbehebung.md): 13 Themen einschließlich Ton und ABI-Problemen
- [Leistungsmessungen](docs/Leistungsmessungen.md): Vorlage für vergleichbare Messungen
- [Architektur und Optimierung](docs/Architektur_und_Optimierung.md): technische Entscheidungen
- [Promptvorlagen](docs/Promptvorlagen.md): deutsche Beschreibungen für Videotests

## Abschlussprüfung der H3-Einrichtung

- [ ] `make gpu-check` erfolgreich; Port 8188 liefert HTTP 200.
- [ ] `docker exec minimax-h3-comfyui python -c "import torchaudio"` erfolgreich.
- [ ] Drei aufeinanderfolgende Erzeugungen bei 608×352, 736×416 und 864×480 erfolgreich.
- [ ] Ausgabe enthält Bild und Ton.
- [ ] Bild-zu-Video mit einem eigenen Foto erfolgreich.
- [ ] Dienst nur über SSH-Tunnel oder vertrauenswürdiges lokales Netz erreichbar.

## Lizenzen

- Repository-Code: [MIT](LICENSE).
- MiniMax-H3-Modell: Community License, nicht Apache 2.0. Maßgeblich ist die Lizenz
  im Modellrepository.
- Mitgelieferte Schriftlizenzen bleiben in ihrer rechtlich maßgeblichen Originalfassung erhalten.

## Beispiele und Erweiterungen

[Beispielpaket mit sechs H3-Workflows, Video-Vergrößerung, Erweiterungen und Installationsanleitung](examples/README.md).

[Einladungen mit Logo: drei lokal anpassbare Vorlagen mit PDF-Ausgabe](examples/invitations/README.md).

[Polnische Facebook-Plakate: lokale FLUX.2-Bilder, Logo und optionaler Partnerstreifen](examples/posters/README.md).

[Comic-Studio: Kachelanzahl, Figuren, Szenen und Sprechblasen](examples/comics/README.md).

## ComfyUI-Templates aktualisieren

Die offizielle Galerie unter **Templates** wird über das Python-Paket
`comfyui-workflow-templates` aktualisiert. Die folgenden Befehle im Terminal
auf dem Server ausführen, sobald keine Generierung läuft:

```bash
docker exec minimax-h3-comfyui python -m pip install --upgrade comfyui-workflow-templates
docker restart minimax-h3-comfyui
```

Danach die ComfyUI-Seite mit **Strg+F5** neu laden und **Templates** öffnen.
Installierte Version prüfen:

```bash
docker exec minimax-h3-comfyui python -m pip show comfyui-workflow-templates
```

Neue Vorlagen können zusätzliche Modelle, Erweiterungen oder eine neuere
ComfyUI-Version benötigen. Modelle werden durch das Template-Update nicht
mit heruntergeladen. Eigene Workflows, etwa unter **Workflows → Einladungen**,
werden durch dieses Paket-Update nicht verändert.

Das Update bleibt bei einem Neustart erhalten, geht aber beim Neuerstellen des
Containers aus dem bisherigen Image verloren. Für eine reproduzierbare Installation
muss die getestete Template-Version zusätzlich beim Image-Build festgelegt werden;
die Basisversion stammt derzeit aus `comfyui-src/requirements.txt`.

Quelle: [Offizielle ComfyUI-Template-Sammlung](https://github.com/Comfy-Org/workflow_templates).

[Polnische Facebook-Plakate mit lokalen Bildern, Logo und Partnerstreifen](examples/posters/README.md).

[Sysop-Comics in ComfyUI: Kachelanzahl, einzelne Szenen oder eine ganze Geschichte](examples/comics/README.md).

### Redaktionellen Comic per Skript erstellen

[Projektanweisungen und vollständiger Ablauf als Markdown-Datei](docs/Comic_per_Skript_erstellen.md).

Ein geprüftes Storyboard lässt sich mit dem lokalen ComfyUI wiederholbar als Comic,
Teilseiten, PDF und ZIP mit bearbeitbarem Workflow exportieren:

```bash
python3 scripts/render_editorial_comic.py \
  examples/comics/editorial/marius-dick/storyboard.json
```

Voraussetzung: laufender [Comic-Automat](automation/comics/README.md), Docker-Zugriff
und Python 3 mit Pillow auf dem Host. Das Storyboard enthält die zuvor erstellten
Szenen, Figuren und deutschen Texte. Das Skript schreibt die Geschichte nicht um
und verwendet ausschließlich die lokalen ComfyUI-Modelle für die Bilder.

Die Ausgabe liegt unter `diagnostics/comics/<Auftrags-ID>/`; Downloadlinks werden
ausgegeben. Jeder Aufruf ohne `--job` erstellt einen neuen Auftrag. Vorhandene
gespeicherte ComfyUI-Workflows werden nicht überschrieben.

Für Korrekturen `--draft` ergänzen, das Storyboard bearbeiten und mit
`--job <Auftrags-ID> --draft` erneut aufrufen. Ohne `--draft` wird der Auftrag
abgeschlossen. Unveränderte Kacheln werden während der Bearbeitung wiederverwendet.
Alle Optionen und die Installation stehen in der
[Anleitung zum Comic-Automaten](automation/comics/README.md#ein-aufruf-für-rendern-seitenlayout-und-download).

### Lokale Vorarbeit und Bildprüfung

[Getestete Arbeitsteilung für die Comic-Produktion](docs/Comic_Lokale_Arbeitsteilung.md):
Quellenabsätze lokal aufbereiten, Texte redaktionell ausarbeiten und Bilder mit
`--local-check` lokal vorprüfen. Die Prüfung liefert Hinweise und lässt den Auftrag
offen; Geschichte und Szenen bleiben unverändert.

### Geschichtenverwaltung und elf Bildstile

Auf der [lokalen Redaktionsseite](http://192.168.1.224:8090/) lassen sich
Geschichten anlegen, Storyboards importieren, Szenen bearbeiten und neue Ausgaben
erzeugen. Definitionen und Ausgaben sind getrennt löschbar. Elf Bildstile stehen
im Studio und im Automationsdienst zur Auswahl.
[Anleitung zur Verwaltung und Stilauswahl](automation/comics/README.md#geschichten-auf-der-redaktionsseite-verwalten).

Der Comic-Automat unterstützt außerdem eine frei wählbare positive Kachelanzahl
und einen Buch-Export mit Autor, Vor-/Nachwort, Kindle-EPUB, Taschenbuch-Buchblock
und vollständigem Umschlag. Die Druckdateien enthalten Prüfhinweise für Amazon
KDP. Siehe [Comic-Bücher für KDP](docs/Comic_Buecher_KDP.md).

Comic-Vorlagen aus Büchern und Filmen: [Quellengenerator](docs/Comic_Quellengenerator.md).

Comic-Serien: [Fortsetzungen auf Basis vorhandener Geschichten](docs/Comic_Serien.md).

[33 Comic-Seitenvorlagen mit Vorschau und automatischer Übernahme in Serien](docs/Comic_Seitenvorlagen.md).

[Geführte Leseansicht, gemeinsame Buchseiten und Kindle-Create-Seitenpaket](docs/Comic_Gefuehrt_Lesen.md).

Comic-Experimente: [Mehr Wow durch neue Regie, Dramaturgie und Dialoge](docs/Comic_Experimente.md).


[Logische Skriptführung: körperliche Zustände und Übergänge](docs/Comic_Skript_Kontinuitaet.md).


[64 Bildstile mit Kategorien und lokalen Vorschaubildern](docs/Comic_Bildstile.md).


[Adaptive Kachelformate passend zu den Canvas-Seitenvorlagen](docs/Comic_Adaptive_Kachelformate.md).

### Übervolle Sprechblasen nachträglich bearbeiten

Vor dem Zeichnen passt das Comic-Studio Blasengröße und Position an das gewählte Kachelformat an. Texte werden dabei nicht umgeschrieben und die Mindestschriftgröße bleibt erhalten. Technische Leerzeichenfehler werden bereinigt.

Passt eine Beschriftung weiterhin nicht, entsteht trotzdem ein **sichtbar markierter Entwurf**. Der vollständige Text bleibt unter **Sprechblasen positionieren** erhalten. Dort Text kürzen, aufteilen oder Blasen verschieben und vergrößern und die neue Beschriftung speichern. Die neue Ausgabe übernimmt die Originalzeichnungen bytegleich; es werden keine Bilder neu erzeugt. Erst nach erfolgreicher Beschriftungsprüfung stehen Teilen und Buchausgabe wieder zur Verfügung. Fehlerhafte Figuren-Zuordnungen oder ungültige Eingaben bleiben echte Fehler.

Unter **Neue Beschriftung übernehmen** stehen die ursprüngliche Kachelbeschriftung, die Bildbeschreibung und die vollständige Geschichte der ausgewählten Ausgabe zum Nachschlagen und Kopieren bereit. Die Vorlage bleibt während der Bearbeitung unverändert. Figurenbilder in Geschichte und Bibliothek lassen sich per Klick oder Enter groß öffnen; Schließen oder Escape beendet die Ansicht.

Erzählerkästen passen ihre Höhe an die Textmenge an. Die Erzählschrift bleibt mit 20–28 Pixeln zurückhaltend und lesbar. Auch nachträglich ergänzte Erzählertexte schneiden die Zeichnung nicht mehr zu: Das vollständige Bild wird unter dem Kasten proportional eingepasst; je nach Format entstehen dabei freie Ränder. Bestehende Ausgaben bleiben erhalten, bis eine neue Beschriftungsfassung übernommen wird.

### Schwert und Scheide als fortlaufender Zustand

Bei Figuren mit ausdrücklich einem Schwert führt die Skriptplanung dessen Zustand getrennt: in der Scheide, gezogen, in einer ausdrücklich genannten Hand oder am Boden. Ziehen erzeugt kein zweites Schwert. Jeder folgende Bildprompt schreibt daher die Folgen aus: **Schwert in der Hand, Scheide leer und ohne zweiten Griff**. Beim Einstecken bleibt kein Schwert in der Hand; beim Ablegen liegt dasselbe Schwert am Boden. Ohne belegten Wechsel gilt der Zustand weiter. Ausdrückliche Doppelbewaffnung wird nicht pauschal auf ein Schwert reduziert.

Neue redaktionelle Bildausgaben und einzelne Bildkorrekturen prüfen zusätzlich die tatsächlichen Zeichnungen mit dem vorhandenen lokalen Bildmodell. Zusätzliche Schwerter werden durch eine zweite Betrachtung bestätigt und als Kachelbefund gespeichert. Bestätigte Fehler sperren Teilen und Buchexport, der Comic bleibt zum Korrigieren sichtbar. Eine reine Textänderung übernimmt den Bildbefund, weil sie die Zeichnung nicht repariert. Unklare oder fehlgeschlagene Prüfungen werden als solche angezeigt; das Modell bietet keine Garantie für fehlerfreie Bilder. Bestehende Comics werden nicht automatisch verändert oder neu gezeichnet.
