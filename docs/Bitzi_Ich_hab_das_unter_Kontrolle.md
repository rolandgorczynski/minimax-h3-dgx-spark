# Bitzi: Ich hab das unter Kontrolle!

Ein 60-Sekunden-IT-Comedy-Clip im Hochformat 9:16 (720×1280). Sechs MiniMax-H3-Szenen erzählen die komplette Monitoring-Pointe: Auftrag, Warnungsflut, Abschaltknopf, Admin-Konfrontation, Kontrollfrage und Schlussgag. Jede Szene hat ein eigenes, aus derselben Bitzi-Referenz abgeleitetes Startbild. Das verhindert, dass die Figur zwischen den Szenen ihre Farbe oder Form ändert. Die deutsche Sprach- und Soundanweisung liegt direkt im H3-Prompt. Der Zusammenbau normalisiert den Pegel, begrenzt Spitzen und brennt deutsche Untertitel ein.

## Dateien

- `examples/input/bitzi_monitoring_comedy_keyframe.png`: Startbild mit dem bekannten Bitzi und Linux-Administrator.
- `examples/input/bitzi_monitoring_comedy_scene2.png` bis `scene6.png`: konsistente Szenen-Keyframes.
- `scripts/submit_bitzi_monitoring_comedy.py`: einzelne Szene an ComfyUI senden; Szenen 1 bis 6.
- `scripts/run_bitzi_monitoring_comedy.py`: sechs Szenen nacheinander rendern und den Film zusammensetzen.
- `scripts/assemble_bitzi_monitoring_comedy.py`: sechs fertige H3-Ausgaben verbinden, Ton normalisieren/limitieren und Untertitel einbrennen.

## Rendern

ComfyUI muss laufen. Standardmäßig wird `http://192.168.1.224:8188` und `/home/jee/docker/minimax-h3-data` verwendet. Die Pfade und URL lassen sich per Argument oder `COMFY_API_URL` ändern.

```bash
python3 scripts/run_bitzi_monitoring_comedy.py
```

Der vollständige Film liegt standardmäßig unter:

```text
/home/jee/docker/minimax-h3-data/output/x-generator/bitzi-monitoring-comedy/bitzi_ich_hab_das_unter_kontrolle_60s.mp4
```

Für einen bereits gestarteten ersten Job lässt sich dieser übernehmen:

```bash
python3 scripts/run_bitzi_monitoring_comedy.py --first-prompt-id PROMPT_ID
```

Die H3-Spracherzeugung orientiert sich an den wörtlich angegebenen Dialogen; die eingebrannten Untertitel enthalten den freigegebenen Skripttext. Vor Veröffentlichung Ton und gesprochene Formulierungen einmal anhören, da generative Sprachmodelle einzelne Wörter abwandeln können.
