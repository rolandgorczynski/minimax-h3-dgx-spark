# Fehlerbehebung

## 1. `torch.cuda.is_available() = False`

Umgebung prüfen:

```bash
docker info
nvidia-container-cli info
docker compose config
```

Anschließend Abbild neu bauen und GPU-Zugriff prüfen:

```bash
make rebuild
make gpu-check
```

Im Container nicht einfach `pip install torch` ausführen. Dadurch kann die für
ARM64 und GB10 angepasste CUDA-PyTorch-Version des NGC-Abbilds ersetzt werden.

## 2. `no kernel image is available for execution on the device`

Der GB10 verwendet die Rechenarchitektur SM121. Häufige Ursachen sind ein älteres
PyTorch-/CUDA-Abbild ohne SM121, ein vorgefertigtes Paket für x86 oder ältere GPUs
oder eine Erweiterung, die PyTorch, Triton oder CUDA-Bibliotheken ersetzt hat.

1. Zuletzt ergänzte Fremderweiterungen entfernen.
2. Das ursprüngliche `BASE_IMAGE` wiederherstellen.
3. `make rebuild` ausführen.
4. Mit `make gpu-check` prüfen.

## 3. Rückgabecode 137, stockendes System oder unterbrochenes SSH

Häufig liegt Speichermangel im gemeinsamen Arbeitsspeicher vor. Zunächst anhalten
und den Speicher prüfen:

```bash
make stop
docker ps
free -h
```

In `.env` eine konservativere Konfiguration setzen:

```dotenv
RESERVE_VRAM_GB=16
VRAM_HEADROOM_GB=4
ASYNC_OFFLOAD_STREAMS=1
COMFYUI_EXTRA_ARGS=--fast-disk --disable-smart-memory
```

Mit `make restart` neu starten. Im Workflow die Auflösung reduzieren, zunächst vier
Sekunden Dauer und `batch_size=1` verwenden. Andere Inferenz- und Trainingscontainer
anhalten und keine hochauflösenden Vorschauen zwischenspeichern.

Nur zur gezielten Diagnose und bei bekanntem Einfluss den Linux-Dateicache leeren:

```bash
sudo sync
echo 3 | sudo tee /proc/sys/vm/drop_caches
```

Dies ersetzt weder kleinere Aufträge noch ist es eine allgemeine Beschleunigung.

## 4. `nvidia-smi` zeigt keinen Gesamtspeicher oder `N/A`

DGX Spark verwendet gemeinsamen Arbeitsspeicher. Übliche Angaben für getrennten
Grafikspeicher können auf GB10 fehlen oder den verfügbaren physischen Speicher
unzutreffend abbilden. Zusätzlich prüfen:

```bash
free -h
docker stats --no-stream
dmesg -T | grep -Ei 'oom|killed process'
```

Freien Speicher nicht allein anhand der Grafikspeicherspalte beurteilen.

## 5. ComfyUI findet die Modelle nicht

```bash
make verify-models
```

Die Dateien gehören je nach Typ in `models/diffusion_models/`,
`models/text_encoders/` und `models/vae/`. Die tatsächlichen Einbindungen prüfen:

```bash
docker compose config
docker inspect minimax-h3-comfyui --format '{{json .Mounts}}' | jq
```

## 6. Hugging-Face-Download schlägt fehl

Falls erforderlich einen gültigen Zugangsschlüssel in `.env` eintragen:

```dotenv
HF_TOKEN=hf_xxxxxxxxx
```

Erneut laden und verfügbaren Speicherplatz prüfen:

```bash
make download
df -hT "$H3_DATA_ROOT"
du -sh "$H3_DATA_ROOT/hf-cache"
```

Nicht mehrere Downloadprozesse gleichzeitig auf dieselbe Zieldatei schreiben lassen.

## 7. Schwarzes Bild, beschädigte Ausgabe oder fehlender Ton

Die zusammengehörenden Komponenten verwenden:

```text
FL2VA INT8 convrot
Qwen3-VL-32B NVFP4 AWQ
Video-VAE FP16
Audio-VAE FP32
```

Nicht alle Komponenten pauschal auf FP16 oder BF16 umstellen. Den offiziellen
FP32-Audio-VAE beibehalten. Zunächst den offiziellen Workflow aus der Vorlagensammlung
wiederherstellen, Fremderweiterungen und eigene Abtastparameter deaktivieren und
mit 608 × 352 bei vier Sekunden testen.

Ausgabedatei prüfen:

```bash
ffprobe -hide_banner "$H3_DATA_ROOT/output/<Dateiname>.mp4"
```

## 8. Weboberfläche nicht erreichbar

Auf dem Server:

```bash
make status
ss -ltnp | grep 8188
```

Auf dem eigenen Rechner den SSH-Tunnel erneut aufbauen:

```bash
ssh -N -L 8188:127.0.0.1:8188 nvidia@<Server-IP>
```

Im Browser `http://127.0.0.1:8188` öffnen.

## 9. Erster Start bleibt lange beim Laden stehen

Beim ersten Start werden CUDA initialisiert, Modellverzeichnisse gelesen und die
Oberfläche geladen. Mit `make logs` den Fortschritt ansehen. Solange neue Meldungen
erscheinen, nicht wiederholt neu starten. Bei einer konkreten Fehlermeldung
`make diagnostics` ausführen und die Diagnose sichern.

## 10. SageAttention bereits zum Einstieg installieren?

Für die Ausgangskonfiguration nicht installieren. Allgemeine Binärpakete enthalten
möglicherweise kein SM121. Eine Übersetzung aus dem Quelltext bringt zusätzliche
Abhängigkeiten von CUDA, Compiler und PyTorch-ABI mit sich. Bei Fehlern lässt sich
sonst schwer zwischen H3, ComfyUI und der Erweiterung unterscheiden.

Zuerst die offizielle quantisierte Konfiguration prüfen. Danach SageAttention in
einer getrennten Umgebung oder Abbildschicht testen und ein funktionierendes Abbild
ohne diese Erweiterung behalten.

## 11. Nach Neuerstellung: `ModuleNotFoundError: torchaudio` oder ABI-Fehler

**Fehlerbild:** Nach `docker compose up -d` oder einem neuen `docker run` bricht
ComfyUI mit `No module named 'torchaudio'` oder
`OSError: Could not load libtorchaudio.so` ab.

**Ursachen:** Eine Installation in der beschreibbaren Containerschicht überlebt das
Löschen des Containers nicht. Der H3-Audio-VAE unter
`comfy/ldm/lightricks/vae/audio_vae.py` benötigt aber `torchaudio`. Gleichzeitig
passen die üblichen PyPI-Pakete nicht zur dokumentierten NGC-PyTorch-Version
`2.10.0a0+b558c986e8.nv25.11`. Unter anderem trat
`undefined symbol: torch_get_mutable_data_ptr` auf.

**Dokumentierte Reparatur:** Der Quelltextstand `87ff22e49ed0` vom 13. September 2025
ließ sich erfolgreich bauen. Die Veröffentlichung v2.10.0 benötigte dagegen
Kopfdateien unter `torch/csrc/stable/`, die im verwendeten NGC-PyTorch fehlten.

Auf dem Host herunterladen und in den Container kopieren:

```bash
curl -L -o /tmp/torchaudio-src.tar.gz \
  https://codeload.github.com/pytorch/audio/tar.gz/87ff22e49ed0
docker cp /tmp/torchaudio-src.tar.gz minimax-h3-comfyui:/tmp/
docker exec minimax-h3-comfyui bash -c '
  cd /tmp && tar xzf torchaudio-src.tar.gz
  pip install --no-build-isolation --no-deps /tmp/audio-87ff22e49ed0
  python -c "import torchaudio; print(torchaudio.__version__)"
'
```

Die dokumentierte Ausgabe lautet `2.8.0a0`. Das getestete NGC-Abbild bringt die
benötigten Werkzeuge gcc, cmake, ninja und libsndfile mit.

Den funktionierenden Stand dauerhaft als Abbild sichern:

```bash
docker commit minimax-h3-comfyui local/minimax-h3-comfyui:v0.30.0-ta
```

Beim Start mit diesem Abbild den ursprünglichen Einstiegspunkt verwenden.
`docker commit` übernimmt gegebenenfalls auch einen temporären Befehl wie
`sleep infinity`. Das folgende Beispiel verwendet den dokumentierten Datenpfad
`/mnt/minimax-h3`; für die eigene Umgebung anpassen und Namenskonflikte mit einem
bestehenden Container vorher auflösen:

```bash
docker run -d --name minimax-h3-comfyui --gpus all --ipc host --shm-size 16gb \
  --restart unless-stopped -p 127.0.0.1:8188:8188 \
  -e HF_ENDPOINT=https://hf-mirror.com -e H3_DATA_ROOT=/mnt/minimax-h3 \
  -v /mnt/minimax-h3/models:/opt/ComfyUI/models \
  -v /mnt/minimax-h3/input:/opt/ComfyUI/input \
  -v /mnt/minimax-h3/output:/opt/ComfyUI/output \
  -v /mnt/minimax-h3/temp:/opt/ComfyUI/temp \
  -v /mnt/minimax-h3/user:/opt/ComfyUI/user \
  -v /mnt/minimax-h3/custom_nodes:/opt/ComfyUI/custom_nodes \
  -v /mnt/minimax-h3/hf-cache:/data/hf-cache \
  --entrypoint /usr/bin/tini local/minimax-h3-comfyui:v0.30.0-ta \
  -- /usr/local/bin/h3-entrypoint
```

Installationen entweder in ein Abbild übernehmen oder persistent einbinden. Bei
NGC-PyTorch Erweiterungen wie torchaudio und torchvision passend zur ABI bauen.
Den Einstiegspunkt mit `docker inspect <Abbild> --format '{{.Config.Entrypoint}}'`
prüfen.

Zur Abnahme müssen `/system_stats` HTTP 200 und `import torchaudio` Erfolg liefern.
Danach 608 × 352, 736 × 416 und 864 × 480 nacheinander testen.

## 12. H3-Videos standardmäßig mit Ton erzeugen

Die dokumentierte Nutzervorgabe vom 4. August 2026 lautet: H3-Videos mit nativen
Geräuschen erzeugen. H3 berechnet Bild und Ton gemeinsam, die Tonausgabe benötigt
aber eigene Dekodier- und Speicherknoten. Frühere Workflows enthielten nur
`VAEDecode` und lieferten deshalb stumme Videos.

Alle drei Audioknoten anschließen:

```json
"audio_vae_loader": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
"audio_decode": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["sampler", 0], "vae": ["audio_vae_loader", 0]}},
"audio_save": {"class_type": "SaveAudio", "inputs": {"audio": ["audio_decode", 0], "filename_prefix": "audio/h3_xxx"}}
```

Den offiziellen FP32-Audio-VAE `minimax_h3_audio_vae_fp32.safetensors` verwenden.
Video-VAE in FP16 und Audio-VAE in FP32 sind getrennte Dateien. `SaveAudio` schreibt
hier unter `output/audio/`. Anschließend Ton und Video mit ffmpeg zusammenführen.
Geräusche ausdrücklich beschreiben, beispielsweise „knisterndes Brennholz und
nächtliches Zirpen von Insekten“.

## 13. Tonspur vorhanden, aber kaum hörbar

Im dokumentierten Test erzeugte der Audio-VAE Spitzen um −34 dB und einen
Effektivpegel um −50 dB. Eine Tonspur kann deshalb vorhanden und trotzdem kaum
hörbar sein. Sehr zurückhaltende Geräuschbeschreibungen können dies verstärken.
Die beobachtete Datei war technisch intakt; die Übertragung war nicht die Ursache.

Pegel prüfen:

```bash
ffmpeg -i out.flac -af astats=metadata=1 -f null - 2>&1 | grep -E "Peak level dB|RMS level dB"
# Spitzen unter −20 dB können auf zu leisen Ton hinweisen.
```

Empfohlene Nachbearbeitung mit dynamischer Lautheitsnormalisierung:

```bash
ffmpeg -y -i video_with_audio.mp4 \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
  -c:v copy -c:a aac out_loud.mp4
# Dokumentiertes Ergebnis: Spitzen etwa −3,4 dB, Effektivpegel etwa −20 dB.
```

In der dokumentierten H3-Produktion gehört `loudnorm` zur regulären Nachbearbeitung.
Eine Beschreibung wie „klar und gut hörbar“ kann helfen, ersetzt die Pegelprüfung
und Normalisierung aber nicht.
