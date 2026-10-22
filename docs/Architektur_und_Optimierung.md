# Architektur und Optimierung

## 1. Warum die quantisierte ComfyUI-Variante?

Ein einzelner GB10 bietet mit 128 GB gemeinsamem Arbeitsspeicher Platz für große
Modellgewichte. Grenzen setzen Speicherbandbreite, konkurrierende Speichernutzung
und der Aufwand vollständiger Aufmerksamkeit bei langen Sequenzen. Die offizielle
BF16-Variante für vier GPUs eignet sich deshalb nicht als Einstieg auf einem Spark.

Die quantisierten Modelle belegen zusammen etwa 42,5 GB. Dadurch bleibt Platz für:

- Betriebssystem und Docker;
- CUDA-Kontext;
- Qwen3-VL-Kodierung;
- Video- und Audio-VAE;
- Aktivierungen des Diffusionsmodells;
- temporäre Tensoren der vollständigen Aufmerksamkeit;
- Ausgabekodierung und Dateicache.

## 2. Warum ein festgelegtes NGC-PyTorch-Abbild?

Eine direkte PyTorch-Installation über PyPI auf ARM64 kann ein Paket ohne
GPU-Unterstützung, eine CUDA-Version ohne SM121 oder eine zum Treiber unpassende
Version liefern. Abhängigkeiten fremder Erweiterungen können PyTorch versehentlich
ersetzen. Ein NGC-Container für Grace Blackwell verringert diese Risiken und
vereinfacht die Rückkehr zu einem funktionierenden Stand.

## 3. Warum standardmäßig `cache-none`?

H3 benötigt bereits viel Speicher für die Gewichte. Zwischengespeicherte Ergebnisse
können wiederholte Ausführungen beschleunigen, belegen aber zusätzlichen gemeinsamen
Arbeitsspeicher. Für eine stabile Ausgangskonfiguration hat vorhersehbarer
Speicherverbrauch Vorrang vor maximaler Geschwindigkeit.

## 4. Warum zunächst ohne zusätzliche Fremderweiterungen?

Zusätzliche Knoten können PyTorch ersetzen, CUDA-Erweiterungen ohne SM121-Unterstützung
kompilieren, ungeprüfte Triton- oder SageAttention-Versionen einbringen oder die
Workflow-Kompatibilität verändern. Erst die offizielle Text-zu-Video-Konfiguration
prüfen. Danach jeweils eine Erweiterung in einer eigenen Abbildschicht ergänzen
und einen funktionierenden Stand zur Wiederherstellung behalten.

## 5. Reihenfolge weiterer Optimierungen

```text
P0: Stabiler und reproduzierbarer Betrieb
P1: Grenzen für Auflösung und Dauer messen
P2: Kaltstart und wiederholte Ausführung messen
P3: SageAttention aus dem Quelltext für SM121 prüfen
P4: Warteschlange, API, Anmeldung und dauerhafte Aufträge
P5: Auf offizielle Gewichte und Implementierungen mit dünn besetzter Aufmerksamkeit aktualisieren
```

## 6. Nicht empfohlene Optimierungen

- Auslagerungsspeicher als zusätzlichen Grafikspeicher betrachten;
- alle Modelle gleichzeitig dauerhaft im Speicher halten;
- den Dienst über `0.0.0.0` ohne Anmeldung öffentlich bereitstellen;
- im laufenden Container ungeprüft `pip install -U torch` ausführen;
- Auflösung, Dauer und Auslagerungsstrategie gleichzeitig ohne Protokoll ändern;
- den ersten Test mit 15 Sekunden bei 1344 × 768 durchführen.
