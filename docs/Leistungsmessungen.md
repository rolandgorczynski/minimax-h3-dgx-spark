# Messprotokoll für MiniMax H3 auf GB10

## 1. Umgebung dokumentieren

| Angabe | Wert |
|---|---|
| Datum | |
| DGX OS | |
| Betriebssystemkern | |
| NVIDIA-Treiber | |
| CUDA im Container | |
| NGC-Abbild | `nvcr.io/nvidia/pytorch:25.11-py3` |
| ComfyUI | `v0.30.0` |
| H3-Modell | FL2VA pruned INT8 convrot |
| Textkodierer | Qwen3-VL-32B NVFP4 AWQ |
| Weitere laufende Container | |
| Verfügbarer Arbeitsspeicher vor dem Auftrag | |
| Belegter Auslagerungsspeicher vor dem Auftrag | |

## 2. Testmatrix

| Nr. | Auflösung | Dauer | Startwert (`seed`) | Reserve/Spielraum | Gesamtdauer | Maximaler Arbeitsspeicher | Erfolgreich | Ton | Bemerkungen |
|---:|---:|---:|---:|---|---:|---:|:---:|:---:|---|
| 1 | 608×352 | 4 s | 42 | 12/3 GB | | | | | |
| 2 | 608×352 | 4 s | 42 | 12/3 GB | | | | | |
| 3 | 608×352 | 4 s | 42 | 12/3 GB | | | | | |
| 4 | 736×416 | 4 s | 42 | 12/3 GB | | | | | |
| 5 | 864×480 | 5 s | 42 | 12/3 GB | | | | | |
| 6 | 960×544 | 5 s | 42 | 12/3 GB | | | | | |
| 7 | 1344×768 | 4 s | 42 | 12/3 GB | | | | | |

## 3. Regeln für vergleichbare Messungen

1. Andere Container mit großen Modellen vor jedem Test anhalten.
2. Identische Beschreibung, Startwerte und Abtastparameter verwenden.
3. Den ersten Durchlauf gesondert als Kaltstart kennzeichnen.
4. Mindestens eine Ausführung mit bereits geladenem Modell erfassen.
5. Erfolg bedeutet: abspielbare Ausgabe, sichtbares Bild, Ton und weiterlaufender Dienst.
6. Jeweils nur Auflösung, Dauer oder Speicherparameter ändern.
7. Nach Speichermangel zunächst Diagnosedaten sichern, bevor größere Aufträge starten.

## 4. Qualität beurteilen

| Merkmal | 1–5 Punkte | Erläuterung |
|---|---:|---|
| Einhaltung der Beschreibung | | |
| Zeitliche Kontinuität | | |
| Stabilität der Objekte | | |
| Stabilität der Kamera | | |
| Übereinstimmung von Bild und Ton | | |
| Verständlichkeit des Tons | | |
| Bildfehler | | Höhere Punktzahl bedeutet weniger Fehler |
| Reproduzierbarkeit | | |

## 5. Laufende Überwachung

In einem zweiten Terminal:

```bash
watch -n 1 'free -h; echo; docker stats --no-stream minimax-h3-comfyui'
```

Meldungen zu Speichermangel im Betriebssystemkern prüfen:

```bash
sudo dmesg -Tw | grep -Ei 'oom|killed process'
```
