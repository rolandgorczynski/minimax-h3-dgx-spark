# Bitzi – Produktionsroutine

Diese Beschreibung hält den Ablauf des Films **„Ich hab das unter Kontrolle!“** fest und dient als wiederholbarer Standard für neue Bilder und Clips.

## Bildreferenz und Keyframes

1. Mit der kanonischen Referenz `images/bitzi-avatar-reference.png` die Identität von Bitzi festlegen.
2. Für jede Szene einen eigenen Start-Keyframe aus derselben Referenz erzeugen. Im Monitoring-Film wurde dafür OpenAIs `image_gen` verwendet.
3. Die Keyframes getrennt nach Szene ablegen. Bei einem früheren Versuch driftete Bitzis Gesicht bei einer rein fortlaufenden H3-Animation in einen gelben Monitor-Kopf ab. Eigene, referenzbasierte Keyframes plus eine explizite Identitätssperre verhinderten das in den korrigierten Szenen.
4. Die kanonische Referenz unbeschriftet lassen. Ein signiertes Bild nicht als Generierungsreferenz benutzen, damit Name und Webadresse nicht in die Szene kopiert werden.

## Video und Ton

Für **„Ich hab das unter Kontrolle!“** wurde MiniMax H3 lokal in ComfyUI verwendet. H3 erzeugte Bildbewegung und Ton gemeinsam. Der 60-Sekunden-Film besteht aus sechs Szenen von ungefähr zehn Sekunden; pro Szene wurde ein passender Keyframe verwendet. Die Prompts enthielten die Figurenmerkmale, Handlung, Dialog, Musik und Sounddesign. Die Modellstimme kann einzelne Wörter anders aussprechen als der Skripttext; die Untertitel stammen separat aus dem festgelegten Skript.

Die ComfyUI-Ausgaben werden mit `scripts/run_bitzi_monitoring_comedy.py` nacheinander erzeugt und mit `scripts/assemble_bitzi_monitoring_comedy.py` zusammengesetzt. Der dokumentierte Export:

- ist exakt 60 Sekunden lang,
- wird mit 720×1280 Pixeln und 24 fps ausgegeben,
- enthält eingebrannte deutsche Untertitel,
- wird mit FFmpeg auf ungefähr −20 LUFS normalisiert und bei ungefähr −6 dBTP begrenzt,
- wird mit 48-kHz-Stereo-Audio und H.264/AAC codiert,
- erhält am Ende den sichtbaren Schriftzug „Roland Gorczynski“ und `bits.gorczynski.online` unten rechts.

Musik und Sprache waren in der H3-Tonspur gemeinsam generiert. Deshalb lässt sich die Musik nicht verlustfrei wie eine getrennte Studiotonspur austauschen; ein Austausch kann Sprache und Effekte beeinträchtigen.

## Einzelbilder

Neue Bilder werden mit der kanonischen Referenz und der Vorlage `prompts/character-image.md` erstellt. Die Signatur wird nach dem Rendern deterministisch ergänzt:

```bash
python3 scripts/watermark_bitzi_image.py input.png output.png
```

Das Skript überschreibt die Quelle nicht. PNG-Transparenz bleibt erhalten.

## Veröffentlichungsprüfung

- Bitzis Gesicht, Türkis und Kontakte in mehreren Szenen-Stills prüfen.
- Untertitel auf lesbare Zeilenlänge und sichere Ränder prüfen.
- Gesamtlaufzeit, Bildgröße, Audio-Spitzen und Lautheit messen.
- Dialogtext nicht als wortgetreu behaupten, wenn die H3-Tonspur nicht gegengehört oder transkribiert wurde.
- Nur die fertige Montage teilen. Die im Medium sichtbare Webadresse wird in Telegram durch einen klickbaren Link in der Beschreibung ergänzt.

## Ursprung der Referenz

Das kanonische Avatarbild lag bereits im X-Generator-Projekt unter `assets/bitsmitbiss-avatar.png`. Sein genauer ursprünglicher Bildprompt und das damalige Modell sind dort nicht festgehalten. Diese Akte erfindet sie nicht nachträglich.
