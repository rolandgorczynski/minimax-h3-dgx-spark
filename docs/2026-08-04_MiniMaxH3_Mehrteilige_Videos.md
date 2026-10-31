# Mehrteilige Videos mit MiniMax H3

> Dokumentierter Teststand: 4. August 2026 auf spark-44a8.
> Ergebnisse: fünf Abschnitte als 25-Sekunden-Film „Flucht in der Regennacht“
> und acht Abschnitte als 40-Sekunden-Film „Die Versammlung“.
> Ablauf: offizielle Vorlagen, HTTP-Aufträge, Bild und Ton zusammenführen,
> Abschnitte verbinden und Kontinuität verbessern.

## 1. Offizielle Vorlagen und Beispielbeschreibungen beziehen

Comfy-Org stellt Workflow-Vorlagen mit Beispielbeschreibungen bereit:

```bash
mkdir -p /tmp/h3-official && cd /tmp/h3-official
for t in t2v i2v r2v; do
  curl -sL -o video_minimax_h3_${t}.json \
    "https://ghfast.top/https://raw.githubusercontent.com/Comfy-Org/workflow_templates/main/templates/video_minimax_h3_${t}.json"
done
```

Die Dateien verwenden das Oberflächenformat mit `nodes` und `links`. Längere
Beispielbeschreibungen lassen sich so auslesen:

```python
import json, glob
for f in sorted(glob.glob('video_minimax_h3_*.json')):
    d = json.load(open(f))
    print('='*40, f)
    for n in d.get('nodes', []):
        w = n.get('widgets_values', [])
        if w and isinstance(w[0], str) and len(w[0]) > 100:
            print(w[0][:300])
```

Die dokumentierten Beispiele zeigen eine Verfolgung in einer futuristischen Stadt
für Text-zu-Video, eine Produktwerbung mit transparenter Maus für Bild-zu-Video
und Comic-Superhelden mit Referenzbild und Referenzton für Referenz-zu-Video.
Die Auflösungstabelle reicht von etwa 0,2 MP bei 608 × 352 bis 0,8 MP bei 1216 × 672.

## 2. Aufträge über die HTTP-API einreichen

Der Ablauf verbindet Hauptmodell und Sigma-Verschiebung mit Textkodierer,
Video-VAE, Audio-VAE und `MiniMaxH3ImageToVideo`. Auf `KSampler` folgen die beiden
Dekodierer und die getrennten Ausgaben `SaveVideo` und `SaveAudio`.

Die folgende Funktion lässt sich wiederverwenden:

```python
import json, urllib.request

def submit(prefix, seed, prompt, first_frame=None):
    wf = {
     "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}},
     "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax"}},
     "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
     "4": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
     "5": {"class_type": "EmptyMiniMaxH3LatentAV", "inputs": {"width": 864, "height": 480, "length": 124, "batch_size": 1}},
     "6": {"class_type": "MiniMaxH3SigmaShift", "inputs": {"model": ["1", 0], "shift_video": 12.0, "shift_audio": 3.0}},
     "7": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "prompt": prompt, "width": 864, "height": 480, "length": 124}},
     "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": "Text, Untertitel, Logos, Wasserzeichen, Animation, Zeichentrickdarstellung, künstliche Computergrafik, Unschärfe, geringe Qualität, Verformung"}},
     "9": {"class_type": "KSampler", "inputs": {"model": ["6", 0], "positive": ["7", 0], "negative": ["8", 0], "latent_image": ["7", 1], "seed": seed, "steps": 20, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
     "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
     "11": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["9", 0], "vae": ["4", 0]}},
     "12": {"class_type": "CreateVideo", "inputs": {"images": ["10", 0], "fps": 24.0}},
     "13": {"class_type": "SaveVideo", "inputs": {"video": ["12", 0], "filename_prefix": prefix, "format": "auto", "codec": "auto"}},
     "14": {"class_type": "SaveAudio", "inputs": {"audio": ["11", 0], "filename_prefix": "audio/" + prefix}}
    }
    if first_frame:
        wf["15"] = {"class_type": "LoadImage", "inputs": {"image": first_frame}}
        wf["7"]["inputs"]["first_frame"] = ["15", 0]
    req = urllib.request.Request("http://127.0.0.1:8188/prompt",
        data=json.dumps({"prompt": wf, "client_id": "x"}).encode(),
        headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=20))
```

`length=124` entspricht etwa fünf und `length=362` etwa 15 Sekunden, der
dokumentierten Obergrenze. Wiederholte `submit()`-Aufrufe reihen unabhängige Aufträge
zur nacheinander erfolgenden Ausführung ein. Das verhindert gleichzeitiges Rendern,
garantiert aber nicht, dass ein einzelner großer Auftrag in den Speicher passt.
Den Status über `/history/<prompt_id>` oder `/queue` prüfen.

## 3. Ton normalisieren und mit dem Bild verbinden

Im dokumentierten Test war der dekodierte Ton mit Spitzen um −34 dB sehr leise.
Die gemeinsame Routine `scripts/audio_mastering.py` misst den finalen Mix in zwei
Durchläufen, korrigiert Mono-/Stereo-Messung und gibt FLAC mit 48 kHz aus:

```bash
python3 scripts/audio_mastering.py audio/full_mix.flac audio/full_mix_mastered.flac
ffmpeg -y -i video.mp4 -i audio/full_mix_mastered.flac \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -ar 48000 -b:a 192k \
  -shortest final.mp4
```

Bei mehreren Abschnitten zuerst die unbearbeiteten FLAC-Dateien verbinden und den
gesamten Mix einmal mastern. Einzelnes Normalisieren der Abschnitte kann hörbare
Lautheitssprünge an den Schnittstellen erzeugen. Fade und Padding können dem Skript
als `--post-filters` mitgegeben werden; sie werden dann in beiden Messdurchläufen
berücksichtigt. Details und optionale, nur für Dialogspuren geeignete Filter stehen
in [Audio-Mastering](Audio_Mastering.md).

Der im Testbericht genannte −16-LUFS-Wert ist ein Ausgangsziel für Sprache, kein
Plattformlimit. H3-Komplettmischungen mit Musik und Effekten werden ohne die
optionalen Sprachfilter verarbeitet.

## 4. Abschnitte zu einem Film verbinden

Alle Abschnitte auf identische Auflösung, Bildrate und Tonkodierung bringen,
beispielsweise 864 × 480, 24 Bilder pro Sekunde und AAC. Dann ohne erneute
Videokodierung zusammenführen:

```bash
: > concat.txt
for seg in seg1 seg2 seg3 seg4 seg5; do
  echo "file '/pfad/${seg}_final.mp4'" >> concat.txt
done
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy full_video.mp4
```

GIF-Vorschau zum Teilen:

```bash
ffmpeg -y -i full_video.mp4 \
  -vf "fps=8,scale=540:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
  -loop 0 preview.gif
```

## 5. Kontinuität von Geschichte und Figuren verbessern

Unabhängig erzeugte Abschnitte können deutlich unterschiedliche Figuren,
Umgebungen oder Kamerapositionen zeigen. Drei Ansätze helfen:

| Verfahren | Umsetzung | Wirkung |
|---|---|---|
| Längere Abschnitte | Statt achtmal fünf Sekunden beispielsweise 15 + 15 + 10 Sekunden | Nur zwei statt sieben Übergänge; Handlung innerhalb eines Abschnitts bleibt zusammenhängend. |
| Schlussbild als Startbild | Letztes Bild des fertigen Abschnitts als `first_frame` des nächsten verwenden | Umgebung, Farbgebung und Positionen können unmittelbar fortgeführt werden. |
| Feste Figurenbeschreibungen | Aussehen, Farben, Kleidung und Merkmale in jeder Beschreibung wiederholen | Verbessert die Wiedererkennbarkeit; eine vollständige Identitätsgarantie entsteht dadurch nicht. |

Schlussbild auslesen:

```bash
ffmpeg -y -sseof -0.1 -i segN_final.mp4 -frames:v 1 segN_lastframe.png
```

Beschreibungsvorlage mit einheitlicher Gestaltung, festen Figuren und eigener Tonkulisse:

```text
[Gestaltung] Epischer fotorealistischer Realfilm mit einem Superheldenteam.
Große Bildwirkung, anamorphotische Optik, dramatisches räumliches Licht,
ausgeprägte Farbgestaltung, Filmkorn und kraftvolle natürliche Bewegung.

[Figuren] HELD_A: Dunkelgoldene Metallrüstung mit leuchtenden goldenen Energielinien.
HELD_B: Bewegliche Figur in tiefroter taktischer Rüstung mit glühendem goldenem Energieschild.
HELD_C: Fliegende Figur im blau-silbernen Anzug mit langem dunklem Umhang.

[Fortsetzung] Beschreiben, wie das Ende des vorherigen Abschnitts hier weitergeht.
[Ton] Geräusche pro Abschnitt beschreiben und den musikalischen Verlauf fortführen.
[Einschränkungen] Keine Texte, Untertitel, Logos oder Wasserzeichen.
Keine Zeichentrickdarstellung; fotorealistische Realfilmwirkung beibehalten.
```

## 6. Dokumentierte Rechenzeiten

Testumgebung: spark-44a8, 864 × 480. Die Angaben sind historische Messwerte.

| Filmdauer | Bilder | Rechenzeit | Erläuterung |
|---|---:|---:|---|
| 5 s | 124 | Etwa 5,5 min | Einzelner Abschnitt |
| 15 s | 362 | Etwa 16 min | Langer durchgehender Abschnitt |
| 25 s aus fünf Abschnitten | — | Etwa 30 min | Einschließlich Zusammenführung |
| 40 s aus acht Abschnitten | — | Etwa 50 min | Einschließlich Zusammenführung |

## 7. Vollständiger Produktionsablauf

1. Handlung und Einstellungen planen; jeden Abschnitt mit einheitlicher Gestaltung und festen Figuren beschreiben.
2. Unabhängige Abschnitte durch wiederholte `submit()`-Aufrufe einreihen.
3. Bei verketteten Startbildern auf den Abschluss des Vorgängers warten, Schlussbild auslesen und erst dann den nächsten Abschnitt einreichen.
4. Bild und Ton mit `loudnorm` verbinden, Abschnitte zusammenführen und eine GIF-Vorschau erzeugen.
5. Synchronität, Figurenkontinuität, Umgebung und sichtbare Übergänge prüfen.

Fortgeschrittene Varianten: `batch_size>1` erhöht den Speicherbedarf und kann mehrere
Varianten einer Beschreibung liefern. Für „Foto wird bewegtes Bild“ `first_frame`
verwenden. Referenz-zu-Video benötigt zusätzlich das Modell `ref2va`.
