# Modell-Downloads auf dem DGX

Die Erweiterung leitet die Modell-Downloadaktionen der installierten
ComfyUI-Weboberfläche (Frontend 1.47.11) an den Server weiter.

1. Nach der Installation die Oberfläche mit **Strg+F5** neu laden.
2. Im Fehlerbereich wie gewohnt **Download** oder **Download all** anklicken.
3. Im Fenster **DGX Downloads** Fortschritt und Fehler ansehen. Dort gibt es
   außerdem **Alle Workflow-Modelle auf den DGX laden**.

Die Dateien landen in den persistent eingebundenen Modellordnern auf dem DGX,
nicht im Download-Ordner des Browsers. Bestehende Dateien werden übersprungen.
Einzelne Downloads laufen nacheinander, auch wenn das Fenster geschlossen wird.
Nach einem Abbruch oder Server-Neustart den Download erneut starten: vorhandene
Teildateien werden per HTTP Range fortgesetzt. Die Auftragsliste selbst lebt
nur bis zum nächsten Server-Neustart.

Nach Abschluss werden die Modell-Auswahllisten aktualisiert. Falls die
Fehleranzeige noch einen alten Eintrag zeigt, den Workflow erneut laden.

## Voraussetzungen und Grenzen

- Der Workflow muss Modellangaben mit Dateiname, URL und Modellordner enthalten.
  Ohne URL lässt sich die benötigte Quelle nicht zuverlässig bestimmen.
- Unterstützte Quellen: Hugging Face, Civitai und GitHub-Release-Dateien.
  Nicht unterstützte Weiterleitungen werden als Fehler angezeigt.
- Geschützte Hugging-Face-Modelle benötigen eine akzeptierte Modelllizenz und
  einen passenden `HF_TOKEN` in der Server-`.env` (Container danach neu erstellen).
  GitHub-Tokens werden für diese Modell-Downloads nicht verwendet.
- Fehlende **Custom Nodes** werden nicht dadurch installiert; diese Erweiterung
  lädt ausschließlich Modell-Dateien. Sie aktualisiert auch kein ComfyUI.
- Die Standard-Downloadfunktion erzeugt im Webclient programmgesteuert einen
  Downloadlink. Die Erweiterung fängt diesen gezielt für Modell-Dateien der
  unterstützten Quellen ab. Normale Links und lokale Datei-Exporte bleiben erhalten.
  Nach einem Frontend-Upgrade diesen Integrationstest erneut durchführen.

## Installation und Prüfung

`make install-extensions` kopiert die Erweiterung in den persistenten
`custom_nodes`-Ordner. Anschließend ComfyUI neu starten.
Keine zusätzlichen Python-Abhängigkeiten oder Änderungen am ComfyUI-Kern nötig.

```bash
python -m unittest discover -s tests -v
```

Die Tests benötigen `aiohttp`, das im ComfyUI-Image bereits vorhanden ist.
Sie prüfen echte lokale HTTP-Übertragungen, Wiederaufnahme, ignorierte
Range-Header, Verbindungsabbrüche, vorhandene Dateien sowie Pfad- und
Zugriffsbeschränkungen. GitHub CI führt sie ebenfalls aus.
