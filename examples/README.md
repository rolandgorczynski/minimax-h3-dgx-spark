# MiniMax H3: Beispiele und Erweiterungen

In ComfyUI links **Workflows → MiniMax-H3** öffnen. Alternativ eine JSON-Datei
aus `workflows/` in die Oberfläche ziehen. Nach der Installation den Browser
mit Strg+F5 neu laden. Der Installer deaktiviert Nodes 2.0 zugunsten des
klassischen Canvas, da rgthree dort kompatibler ist; vorhandene Einstellungen
werden einmalig als `comfy.settings.json.before-extensions` gesichert. Bilder in Load Image dürfen durch eigene ersetzt werden.

| Workflow | Einsatz | Voraussetzungen |
|---|---|---|
| `video_minimax_h3_t2v.json` | Text zu Video mit Ton | vier Basismodelle |
| `video_minimax_h3_i2v.json` | Foto/Produktbild animieren | Basismodelle + Eingabebild |
| `video_minimax_h3_first_last_frame.json` | Bewegung zwischen Start- und Endbild | Basismodelle + zwei Bilder |
| `video_minimax_h3_t2v_turbo_8step.json` | schneller Entwurf mit 8 Schritten | Basismodelle + Turbo-LoRA |
| `video_minimax_h3_r2v.json` | zwei Bildreferenzen kombinieren | zusätzlich Ref2VA-Modell |
| `video_upscale_x2_with_audio.json` | vorhandenes Video 2× hochskalieren, Ton behalten | VideoHelperSuite + RealESRGAN_x2plus |
| `video_minimax_h3_i2v_continuation.json` | Clip laden → letzten Frame als Startbild | Basismodelle + VideoHelperSuite; optional Turbo-LoRA |

Die Beispiele starten bei 0,2 Megapixeln. Dauer und Auflösung erst nach einem
erfolgreichen kurzen Durchlauf erhöhen. Turbo spart Schritte; Bewegung und Ton
können gegenüber dem normalen Modus schwächer ausfallen. Die erste/letzte
Bildvorlage verwendet zunächst unterschiedliche Beispielmotive: für gezielte
Übergänge zwei zusammengehörige eigene Bilder einsetzen.

## Fertiges Beispiel

![Roboter gießt Kaffee ein](output/robot-coffee-preview.jpg)

[Video mit Ton herunterladen](output/robot-coffee-turbo.mp4) — auf diesem GB10
mit `api/turbo_draft.json` erzeugt: 608 × 352, 56 Frames, 8 Schritte,
2,33 Sekunden Video, rund 88 Sekunden einschließlich Modellladen.
Dies ist ein kurzer Funktionstest, kein Qualitätsbenchmark.

[Dieselbe Szene nach 2×-Upscaling mit Originalton](output/robot-coffee-upscaled-x2.mp4)
— 1216 × 704, 24 fps, H.264/AAC; auf diesem GB10 in rund 37 Sekunden verarbeitet.

Die Fortsetzungsvorlage nimmt den letzten Frame eines geladenen Clips als
Startbild für einen neuen Clip. Sie erzeugt die nächste Szene; sie hängt die
Dateien nicht automatisch zusammen und übernimmt keine Audio-Kontinuität.

## Neue Werkzeuge

- **Real-ESRGAN 2×**: vorhandene Videos nachträglich hochskalieren. Das Beispiel
  wandelt auf 24 fps und übernimmt den Originalton. Für lange Clips
  `frame_load_cap` im Video-Loader begrenzen und abschnittsweise arbeiten.
- **VideoHelperSuite**: Videos/Audio importieren, Frames auswählen, Bildfolgen
  mit Ton exportieren und Video-Vorschauen. Suche nach `VHS` in der Node-Auswahl.
- **rgthree-comfy**: übersichtlichere Verbindungen, Context-Nodes, Seed-Steuerung,
  Gruppen aktivieren/deaktivieren und LoRA-Loader. Suche nach `rgthree`.
- **KJNodes**: Skalierung, Zuschnitt, Masken, Farbabgleich, Batch-Verarbeitung
  und H3-Hilfsnodes. Suche nach `KJ` oder `MiniMax`.
- **H3-Effekt-Embeddings (vorbereitet)**: zehn Community-Effekte, z.B. Explosion,
  Blumen, Zeitlupe, Feuer und Sturm. Liegen unter `models/pending-upgrade/embeddings/`.
  Der H3-Tokenizer in 0.30.0 unterstützt die benötigte `embedding:`-Auswertung
  noch nicht; deshalb sind diese Dateien nicht aktiv. Nach einem getesteten
  Upgrade können sie nach `models/embeddings/` verschoben werden.

Ein installierter Node wird erst aktiv, wenn er im ausgeführten Workflow steckt.
Speicher-/Attention-Patches aus KJNodes nicht wahllos kombinieren. Die Beispiele
verwenden die normale PyTorch-Attention des vorhandenen Images.

## Installation auf einem weiteren Rechner

```bash
make build
make install-extensions
make download-extras
make up
```

Wenn ComfyUI bereits läuft: nach der Installation `docker compose restart comfyui`
ausführen und den Browser neu laden.

`config/extensions.json` fixiert die vier Erweiterungen auf geprüfte Commits.
Die Installation überschreibt keine abweichenden oder bearbeiteten Checkouts.
Python-Abhängigkeiten werden im Dockerfile installiert; Constraints schützen
bereits vorhandene Pakete, insbesondere NGC-PyTorch und NumPy. Nur eine
OpenCV-Distribution (`opencv-python-headless`) wird verwendet.

## Vorlagen für neuere ComfyUI-Versionen

`newer-comfyui/` enthält zusätzlich die offiziellen ControlNet- und Multiframe-
Vorlagen. Sie sind bewusst nicht in der aktiven Workflow-Liste installiert:
ComfyUI 0.30.0 fehlen `MiniMaxH3FunControlNetApply` und `MiniMaxH3AddGuide`.
Dafür wäre ein separat getestetes ComfyUI-Upgrade nötig; ControlNet benötigt
auch zusätzliche Modellgewichte. Diese Dateien sind Anschauungsmaterial.

## Quellen und Lizenz

Die drei Basisvorlagen stammen aus dem installierten Paket
`comfyui-workflow-templates` 0.11.27. Fortsetzung und neuere Vorlagen stammen aus
[Comfy-Org/workflow_templates](https://github.com/Comfy-Org/workflow_templates)
Commit `04a508b31bec1818e48122ca0761c1de4140a234`.
Die Vorlagen wurden auf das vorhandene FP16-Video-VAE und kleine Startauflösungen
angepasst. Start/Endbild und Turbo sind davon abgeleitete Varianten; die Fortsetzung
wurde um VideoHelperSuite-Videoimport und Auswahl des letzten Frames ergänzt.
Upstream-MIT-Lizenz: `LICENSE.upstream`.

Der Upscaling-Workflow verwendet die vorhandenen ComfyUI-Upscale-Nodes und
[RealESRGAN_x2plus aus Release v0.2.1](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.1).

Die drei Beispielbilder werden vom selben Upstream-Commit geladen, nicht mit
Git versioniert. Modellgewichte unterliegen den Bedingungen ihres Modell-Repos.
Es wurden keine kostenpflichtigen API-Workflows eingerichtet.

## Ausgeführte Prüfung

VideoHelperSuite, rgthree und KJNodes laden gemeinsam; 327 zusätzliche Nodes sind registriert,
kein ursprünglicher Node wurde durch sie ersetzt. Ein H3-Turbo-Durchlauf mit
Video und AAC-Audio wurde erfolgreich ausgeführt. `api/extension_smoke.json` prüft KJ-Skalierung, rgthree-Zuschnitt
und VHS-MP4-Export gemeinsam (kurzes Standbildvideo, kein H3-Modell nötig).
`api/turbo_draft.json` ist ein API-Beispiel für einen kurzen H3-Entwurf mit Ton.
Die API-Dateien sind für `/prompt`, die Dateien in `workflows/` für die Oberfläche.

API-Beispiele mit der lokalen `.env` starten:

```bash
./scripts/run_example.sh extension_smoke
./scripts/run_example.sh turbo_draft
./scripts/run_example.sh video_upscale_x2
```

Die Befehle reihen jeweils einen Auftrag ein. Fortschritt in ComfyUI beobachten;
Ausgaben landen unter `output/examples/`. Der Turbo-Entwurf ist mit 56 Frames
sehr kurz und dient dem Funktionstest; für Ergebnisse im trainierten Bereich
mindestens etwa fünf Sekunden (124 Frames) verwenden.

## Downloads direkt in der Oberfläche

**Download** und **Download all** im ComfyUI-Fehlerbereich laden Modelle jetzt
auf den DGX. Der Knopf **DGX Downloads** zeigt Fortschritt und Fehler und kann
alle im Workflow hinterlegten Modelle laden. Vorhandene Dateien bleiben erhalten.
Nach der Einrichtung einmal **Strg+F5** drücken.
[Details und Grenzen](../extensions/dgx-server-downloads/README.md).

## Deutsche Oberfläche

Die Installation aktiviert das lokale deutsche Übersetzungspaket. Danach einmal
**Strg+F5** drücken. In den Einstellungen unter **Übersetzungssprache** zwischen
**Deutsch** und **English** wechseln. Einzelne Erweiterungstexte können Englisch
bleiben; technische Modell- und Samplerwerte bleiben unverändert.
[Details](../extensions/dgx-german-ui/README.md).
