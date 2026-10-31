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

## Funktionen

- Auf dem Host werden DGX OS, Treiber, Docker und NVIDIA Container Toolkit benötigt.
  ComfyUI und Modellabhängigkeiten bleiben im Container; das angepasste NGC-PyTorch bleibt erhalten.
- Video-VAE in FP16 mit etwa 5,21 GB und Audio-VAE in FP32 mit etwa 0,605 GB erzeugen Bild und Ton gemeinsam.
- Hauptmodell: FL2VA pruned INT8 convrot mit etwa 21,0 GB; Textkodierer:
  Qwen3-VL-32B NVFP4 AWQ mit etwa 15,7 GB.
- Unter `scripts/` liegen Werkzeuge für Speicherinitialisierung, Vorprüfung,
  Downloads, Modellprüfung, Status und Diagnosedaten.
- Ergänzende Anleitungen behandeln Fehlerbehebung, Leistungsmessungen,
  Architektur, Einladungen und Plakate.

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
- [Audio-Mastering](docs/Audio_Mastering.md): zweistufige Lautheitsmessung und sichere Sprachfilter
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



## Getrennte Anwendungen

Comic-Studio, Bitzi-Produktion und persönliche Betriebswerkzeuge werden in eigenständigen Repositories gepflegt. Sie nutzen bei Bedarf weiterhin dieselbe ComfyUI-Installation. Ihre Quelltexte, Figurenakten, Geschichten und Produktionsdateien sind nicht Bestandteil dieses öffentlichen Hauptbranches. Plakate und Einladungen bleiben vorerst hier.

[Aufteilung und Workflow-Orte](docs/Repository_Aufteilung.md).
