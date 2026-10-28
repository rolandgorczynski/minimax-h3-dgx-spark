# Elf weitere Geschichten: Auswahl auf 100 erweitert

Die bisherige Auswahl von 89 Geschichten wurde um elf neue, von Codex geschriebene Skripte ergänzt. Die separate Schneiderlein-Referenz bleibt außerhalb dieser Auswahl. Alle übrigen Quellen bleiben zurückgestellt; der automatische Skript-Cron bleibt pausiert.

Die neuen Skripte übernehmen die vorhandene redaktionelle Sinnanalyse und empfohlene Kachelzahl. Erzähler steht in jeder dritten Kachel und zusätzlich bei Bedarf; Erzähler und Gespräch werden nicht in derselben Kachel gemischt. Jede Kachel ohne Gespräch erhält Erzählertext. Dialoge sind frei neu formulierte Adaption, keine behaupteten Originalzitate.

Die Bildregie beschreibt einzelne Zeitpunkte, Raumpositionen und Zustandswechsel. Das vollständige Kontinuitätsregister wird getrennt geführt. Es wurden keine Modelle aufgerufen und keine Bilder erzeugt. Bildstil ist offen und wird in Schritt 2 gewählt. Die späteren Bilder benötigen weiterhin eine Sichtprüfung.

| Geschichte | Kacheln | Skript |
|---|---:|---|
| Blümelis-Alpe – Die Milch und das Schweigen | 14 | [Lesen](bluemelis-alpe-14.txt) · [Studio-Definition](bluemelis-alpe-14.json) |
| Mutter Gottes am Felsen – Die unerreichbare Nähe | 10 | [Lesen](muttergottes-felsen-10.txt) · [Studio-Definition](muttergottes-felsen-10.json) |
| Die Teufelsbrücke – Der Preis der ersten Seele | 10 | [Lesen](teufelsbruecke-gemse-10.txt) · [Studio-Definition](teufelsbruecke-gemse-10.json) |
| Der Stierenbach – Neun Jahre für einen Augenblick | 14 | [Lesen](stierenbach-neun-jahre-14.txt) · [Studio-Definition](stierenbach-neun-jahre-14.json) |
| Der Besserstein – Lieber eine Ruine | 10 | [Lesen](besserstein-burg-10.txt) · [Studio-Definition](besserstein-burg-10.json) |
| Der Kreuzliberg – Zurück aus dem stummen Holz | 12 | [Lesen](kreuzliberg-rettung-12.txt) · [Studio-Definition](kreuzliberg-rettung-12.json) |
| Die Würfelwiese – Was die Erde nicht erklärt | 6 | [Lesen](wuerfelwiese-raetsel-6.txt) · [Studio-Definition](wuerfelwiese-raetsel-6.json) |
| Die Basler Uhrglocke – Eine Stunde voraus | 8 | [Lesen](basler-uhrglocke-8.txt) · [Studio-Definition](basler-uhrglocke-8.json) |
| Die Schlangenjungfrau – Der dritte Kuss | 14 | [Lesen](schlangenjungfrau-augst-14.txt) · [Studio-Definition](schlangenjungfrau-augst-14.json) |
| Herzog Bernhard – Ein Eid im Zorn | 12 | [Lesen](bernhard-wort-12.txt) · [Studio-Definition](bernhard-wort-12.json) |
| Vom treuen Eckart – Hüten ist nicht besitzen | 12 | [Lesen](treuer-eckart-hort-12.txt) · [Studio-Definition](treuer-eckart-hort-12.json) |

**Prüfung:** 11 Skripte, 122 Kacheln, keine Beschriftungswarnungen. Szenen und Figuren wurden nach dem Import aus der Studio-API zurückgelesen und verglichen. Die 89 bisherigen Geschichten wurden nicht geändert.

## Reproduzierbarkeit

`Redaktion.json` enthält die von Codex verfassten Szenen, Texte und Zustandswechsel. `Pruefbericht.json` enthält die technischen Ergebnisse, `Importiert.json` die Studio-Kennungen.

Die lokalen Artefakte lassen sich ohne Modellaufruf neu bauen und prüfen:

```bash
python3 scripts/build_comic_selection_extension.py
```

Der Befehl verändert das Studio nicht. Der bestehende Importer kann anschließend eine einzelne Definition mit `--apply` als neue Geschichte übernehmen; wiederholte Importe derselben Skriptkennung werden erkannt.

Vorheriger Auswahlzustand und Auftragsstand liegen privat unter `/home/jee/docker-data/comic-automation/bildregie-redaktion/20261028-erweiterung-100/`.
