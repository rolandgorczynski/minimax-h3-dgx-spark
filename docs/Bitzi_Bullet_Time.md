# Bitzi Bullet-Time: lokaler MiniMax-H3-Workflow

Der Clip ist eine eigenständige Bullet-Time-Hommage mit Bitzi. Er verwendet keine Filmfigur, Logos oder kopierten Filmframes. Der 30-Sekunden-Film besteht aus zwei 15-Sekunden-Segmenten, weil H3 für einen einzelnen Durchlauf auf etwa 15 Sekunden ausgelegt ist.

## Dateien

- `examples/api/bitzi_bullet_time_seg1.json` und `examples/api/bitzi_bullet_time_seg2.json`: direkt an ComfyUI `/prompt` übergebbare API-Workflows.
- `examples/input/bitzi_bullet_time_keyframe.png`: Startbild mit Bitzi und den schwebenden Projektilen.
- `scripts/submit_bitzi_bullet_time.py`: kopiert das Startbild in ComfyUI `input/` und schickt einen Segmentauftrag an den lokalen ComfyUI-Server.
- `scripts/assemble_bitzi_bullet_time.py`: verbindet beide Video- und Tonsegmente. Die Tonspur wird gemeinsam auf −20 LUFS normalisiert und mit einem Peak-Limiter bei ungefähr −7 dBFS abgesichert.

## Rendern

ComfyUI und die MiniMax-H3-Modelle müssen laufen. Standardmäßig verwendet das Submit-Script `http://192.168.1.224:8188`; abweichende Adressen lassen sich mit `--comfy-url` oder `COMFY_API_URL` angeben.

```bash
python3 scripts/submit_bitzi_bullet_time.py --segment 1
```

Nach Abschluss den letzten Frame aus `seg1_00001_.mp4` extrahieren:

```bash
docker exec minimax-h3-comfyui ffmpeg -y -sseof -0.1 \
  -i /opt/ComfyUI/output/x-generator/bitzi-bullet-time/seg1_00001_.mp4 \
  -frames:v 1 /opt/ComfyUI/input/bitzi_bullet_time_seg2_first_frame.png
```

Dann den zweiten Auftrag mit diesem Bild starten:

```bash
python3 scripts/submit_bitzi_bullet_time.py --segment 2 \
  --first-frame /home/jee/docker/minimax-h3-data/input/bitzi_bullet_time_seg2_first_frame.png
```

Die API-Antwort liefert eine `prompt_id`; Fortschritt und Ausgaben stehen unter `/history/<prompt_id>`. ComfyUI schreibt Video und FLAC-Audio nach `output/x-generator/bitzi-bullet-time/` und `output/audio/x-generator/bitzi-bullet-time/`.

## Zusammenfügen und Ton

```bash
python3 scripts/assemble_bitzi_bullet_time.py \
  --video-1 /home/jee/docker/minimax-h3-data/output/x-generator/bitzi-bullet-time/seg1_00001_.mp4 \
  --video-2 /home/jee/docker/minimax-h3-data/output/x-generator/bitzi-bullet-time/seg2_00001_.mp4 \
  --audio-1 /home/jee/docker/minimax-h3-data/output/audio/x-generator/bitzi-bullet-time/seg1_00001.flac \
  --audio-2 /home/jee/docker/minimax-h3-data/output/audio/x-generator/bitzi-bullet-time/seg2_00001.flac \
  --output /home/jee/docker/minimax-h3-data/output/x-generator/bitzi-bullet-time/bitzi_bullet_time_30s.mp4
```

Der Audio-Mix wird erst nach der Verkettung normalisiert. So erhalten beide Szenen denselben Zielpegel; `alimiter` begrenzt Transienten zusätzlich. Die genaue Laufzeit richtet sich nach dem tatsächlich gerenderten Frame-Raster.
