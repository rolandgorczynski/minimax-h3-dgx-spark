# Das erste MiniMax-H3-Video mit Ton

> Dokumentierter Teststand: 4. August 2026 auf spark-44a8, GB10 mit 121 GB gemeinsamem Arbeitsspeicher.
> Voraussetzung: `minimax-h3-comfyui` läuft; `/system_stats` liefert HTTP 200.
> Der gesamte Ablauf funktioniert ohne Browser: Auftrag über HTTP einreichen,
> Fortschritt prüfen, MP4 und FLAC abholen und mit ffmpeg zusammenführen.

## 1. Voraussetzungen prüfen

```bash
docker ps | grep minimax-h3-comfyui
curl -s http://127.0.0.1:8188/system_stats | head -c 60
ls /mnt/minimax-h3/models/diffusion_models/
```

Die vier benötigten Modelldateien müssen in ihren jeweiligen Verzeichnissen
für Diffusionsmodelle, Textkodierer und VAE vorhanden sein. `/mnt/minimax-h3`
ist der Datenpfad des dokumentierten Beispiels und gegebenenfalls anzupassen.

## 2. Text-zu-Video mit Ton einreichen

Den folgenden Code als `first_video.py` speichern und mit `python3 first_video.py`
ausführen. Er benötigt ausschließlich die Python-Standardbibliothek.

```python
import json, urllib.request

workflow = {
 "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}},
 "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax"}},
 "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
 "4": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
 "5": {"class_type": "EmptyMiniMaxH3LatentAV", "inputs": {"width": 608, "height": 352, "length": 96, "batch_size": 1}},
 "6": {"class_type": "MiniMaxH3SigmaShift", "inputs": {"model": ["1", 0], "shift_video": 12.0, "shift_audio": 3.0}},
 "7": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {"clip": ["2", 0], "vae": ["3", 0],
       "prompt": "Ein majestätischer Wal schwimmt im tiefblauen Ozean. Sonnenstrahlen dringen durch die Wasseroberfläche. Filmische Bildgestaltung und Meeresrauschen in Stereo.",
       "width": 608, "height": 352, "length": 96}},
 "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": "unscharf, geringe Qualität, verformt, verwackelte Kamera"}},
 "9": {"class_type": "KSampler", "inputs": {"model": ["6", 0], "positive": ["7", 0], "negative": ["8", 0],
       "latent_image": ["7", 1], "seed": 42, "steps": 20, "cfg": 1.0,
       "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
 "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
 "11": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["9", 0], "vae": ["4", 0]}},
 "12": {"class_type": "CreateVideo", "inputs": {"images": ["10", 0], "fps": 24.0}},
 "13": {"class_type": "SaveVideo", "inputs": {"video": ["12", 0], "filename_prefix": "h3_first", "format": "auto", "codec": "auto"}},
 "14": {"class_type": "SaveAudio", "inputs": {"audio": ["11", 0], "filename_prefix": "audio/h3_first"}}
}

req = urllib.request.Request("http://127.0.0.1:8188/prompt",
    data=json.dumps({"prompt": workflow, "client_id": "first"}).encode(),
    headers={"Content-Type": "application/json"})
print(json.load(urllib.request.urlopen(req, timeout=20)))  # Gibt die prompt_id aus
```

Wesentliche Parameter:

- `length`: 96 entspricht etwa vier, 124 etwa fünf und 362 etwa 15 Sekunden bei 24 Bildern pro Sekunde.
- Zunächst mit 608 × 352 testen: dokumentiert etwa 97 Sekunden. Bei 864 × 480 wurden etwa 4,3 Minuten gemessen.
- Die dokumentierte Konfiguration nutzt `cfg=1.0`, 20 Schritte und `euler/simple`.

## 3. Fortschritt beobachten

```bash
curl -s http://127.0.0.1:8188/queue | python3 -m json.tool
docker logs -f minimax-h3-comfyui
```

Die Warteschlange zeigt ausstehende Aufträge, das Containerprotokoll den
Abtastfortschritt. Eine typische unveränderte Programmausgabe lautet:

```text
Requested to load MiniMaxH3 ... 19995MB Staged
  20%|██        | 4/20 [01:55<07:40, 28.8s/it]
```

Die protokollierten 26–47 Sekunden je Schritt hängen von der Testkonfiguration ab.

## 4. Ausgaben finden

Die Ausgabe wird auf das eingebundene NVMe-Laufwerk geschrieben:

```bash
ls -la /mnt/minimax-h3/output/h3_first_00001_.mp4
ls -la /mnt/minimax-h3/output/audio/h3_first_00001.flac
```

Die MP4 enthält zunächst das stumme H.264-Video, die FLAC die getrennte Tonspur.
Die tatsächlichen laufenden Dateinummern können abweichen. Den Abschluss eines
Auftrags über seine zurückgegebene `prompt_id` prüfen:

```bash
curl -s http://127.0.0.1:8188/history/<prompt_id> | python3 -m json.tool
```

## 5. Bild und Ton zusammenführen und Lautheit normalisieren

Der Audio-VAE lieferte im dokumentierten Test Spitzen um −34 dB. Ein bloßes
Zusammenführen kann deshalb zu einer kaum hörbaren Tonspur führen. ffmpeg im
Container verwenden; eine Hostinstallation ist dann nicht erforderlich:

```bash
docker exec minimax-h3-comfyui ffmpeg -y \
  -i output/h3_first_00001_.mp4 -i output/audio/h3_first_00001.flac \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11" -c:v copy -c:a aac -shortest \
  output/h3_first_final.mp4

# Erwartet werden Einträge für video und audio.
docker exec minimax-h3-comfyui ffprobe -v error -show_entries stream=codec_type -of csv output/h3_first_final.mp4
```

Nach der Normalisierung wurden Spitzen um −3 bis −5 dB beobachtet.

## 6. GIF-Vorschau zum Teilen

```bash
docker exec minimax-h3-comfyui ffmpeg -y -i output/h3_first_final.mp4 \
  -vf "fps=8,scale=432:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
  -loop 0 output/h3_first_preview.gif
```

## 7. Häufige Probleme

| Fehlerbild | Ursache und Abhilfe |
|---|---|
| Antwort enthält `{"error": ...}` | Pfade und Namen der vier Modelldateien prüfen. |
| Video bleibt stumm | Audio-VAE in FP32, `VAEDecodeAudio` und `SaveAudio` anschließen; siehe Knoten 4, 11 und 14. |
| Berechnung dauert über zehn Minuten | Auflösung und Bildanzahl prüfen; etwa 4,3 Minuten für 864 × 480 bei fünf Sekunden wurden dokumentiert. |
| Rückgabecode 137 oder stockendes System | Andere große Modellcontainer anhalten oder Auflösung reduzieren. |
| Eigenes Bild animieren | Bild unter `/mnt/minimax-h3/input/` ablegen und `LoadImage` mit `first_frame` von Knoten 7 verbinden. |

## 8. Weitere Schritte

- Mehrere unabhängige Aufträge durch wiederholte `/prompt`-Aufrufe einreihen. Die
  Warteschlange arbeitet sie nacheinander ab; jeder Auftrag muss für sich in den Speicher passen.
- Für längere Filme und Figurenkontinuität die [Anleitung für mehrteilige Videos](2026-08-04_MiniMaxH3_Mehrteilige_Videos.md) verwenden.
- Die Standardbereitstellung bindet ComfyUI an `127.0.0.1`. Zugriff über SSH-Tunnel
  oder ein vertrauenswürdiges lokales Netz einrichten.
