# H3: Prüfung nach Zentralisierung des Modellcaches

Stand: 1. November 2026.

## Ergebnis

H3/ComfyUI wurde neu gestartet und ist gesund unter `http://192.168.1.224:8188/`. NVIDIA GB10 und CUDA werden erkannt. Der zentrale Hugging-Face-Bildcache ist nach `/data/hf-cache` eingebunden; UID/GID 1000:1000 kann lesen und schreiben. Die eigentlichen ComfyUI-Modelle verbleiben unter `/home/jee/services/bild-und-video/data/models`.

## Durchgeführte Prüfungen

- Systemstatus, Warteschlange, Erweiterungs- und Node-API erreichbar; 1160 Nodes registriert. Alle acht Custom-Node-Pakete laut Startprotokoll geladen.
- Laufendes Comic-Studio erreicht ComfyUI unter `http://comfyui:8188` im gemeinsamen Docker-Netz.
- Echter Bildauftrag aus dem Comic-Studio-Container: FLUX Klein 9B, Qwen 3 8B, FLUX2-VAE, 512 × 512 Pixel, vier Schritte. Erfolgreich, Laufzeit einschließlich Abfrage etwa 24 Sekunden. Bild visuell geprüft.
- Testdatei: `/home/jee/services/bild-und-video/data/output/qa/h3-neustart-20261101_00001_.png`. Keine vorhandene Geschichte oder Workflowdatei überschrieben.
- Elf Tests der Download-Erweiterung bestanden, in einem isolierten Container ohne Netzwerk. Host-Python hat kein aiohttp; deshalb wurde die vorhandene Laufzeitumgebung des Images verwendet.
- FL2VA-Modell, H3-Textencoder, beide VAEs und optionales Ref2VA-Modell vorhanden. Diese Prüfung bestätigt Vorhandensein und Größe, keine vollständige Integritätsprüfung aller Gewichte.
- Download-API erreichbar. Manueller Modell-Download schreibt gezielt ins ComfyUI-Modellverzeichnis; Cache-Downloads verwenden den zentralen Cache. Keine externen Modelle zu Testzwecken heruntergeladen.

## Weitere Verbraucher

- Comic-Studio: läuft; interne Verbindung und echter Bildauftrag geprüft.
- Artikelredaktion/X-Generator: konfigurierte Adresse `http://192.168.1.224:8188`; derzeit kein entsprechender Container aktiv. Keine vollständige Anwendungsausführung geprüft.
- Robot: gleiche Adresse in Compose; derzeit gestoppt.
- Bitzi Studio: Skripte verwenden gleiche Adresse und die aktuellen Input-/Output-Verzeichnisse; derzeit gestoppt.
- Betriebszentrale: verwendet H3 für Anzeige/Verwaltung und Sicherung.

## Grenzen und Hinweise

Keine vollständige H3-Videogenerierung oder komplette Comic-Produktion ausgeführt. Inaktive Verbraucher wurden nicht gestartet. rgthree meldet eine allgemeine mögliche Inkompatibilität mit dem optionalen neuen Nodes-2.0-Editor; dies betrifft nicht die erfolgreich getestete API-Bildgenerierung. FLUX-Klein-Dienst bleibt auf Wunsch gestoppt; seine Modelle sind über H3 weiterhin verfügbar.
