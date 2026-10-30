# Bitzi

Bitzi ist das wiederkehrende KI- und Technik-Maskottchen von **Bits mit Biss**. Dieses Verzeichnis ist seine verbindliche Figurenakte: Bio, Bildreferenz, Stimme, Designregeln und Produktionsroutine.

## Figurenkarte

- **Name:** Bitzi
- **Rolle:** freches, sympathisches Mikrochip-Maskottchen und Hauptfigur der IT-Comedy-Reihe
- **Persönlichkeit:** clever, übermütig, selbstsicher und wörtlich konsequent; nie bösartig
- **Serienidee:** Bitzi bekommt eine einfache technische Aufgabe. Seine Lösung funktioniert genau wie geplant – und optimiert dabei gern das falsche Problem.
- **Leitsatz:** „Bitzi macht keine Fehler. Er optimiert die Realität.“

## Bilder

- [Kanonische Referenz](images/bitzi-avatar-reference.png) – unveränderte Vorlage für neue Generierungen.
- [Signiertes Profilbild](images/bitzi-profile-signed.png) – öffentlich nutzbare Fassung mit Name und Webadresse.
- [Keyframe aus dem Serverraum](../../examples/input/bitzi_monitoring_comedy_keyframe.png) – Beispiel für Bitzi in einer Szene.

Für neue KI-Bilder immer die **kanonische, nicht signierte Referenz** als Figurenreferenz verwenden. Die Signatur wird anschließend deterministisch gesetzt, damit Bildmodelle den Schriftzug nicht verfälschen oder mehrfach ins Bild malen.

## Inhalt dieses Verzeichnisses

- [Verbindliche Figurenakte](personality.md): Rolle, Persönlichkeit, Stimme und Grenzen.
- [Bio](bio.md): Figur und Serienwelt.
- [Visuelle Identität](visual-identity.md): unveränderliche Merkmale und Bildregeln.
- [Stimme und Charakter](voice-and-personality.md): Sprechweise, Humor und Grenzen.
- [Produktionsroutine](production-routine.md): tatsächlich verwendeter Ablauf für Bilder und Filme.
- [Bildprompt](prompts/character-image.md) und [Videoprompt](prompts/bitzi-video.md): wiederverwendbare Vorlagen.

## Produktionsskripte

Die lauffähigen Werkzeuge liegen unter [`scripts/`](../../scripts/):

- `submit_bitzi_monitoring_comedy.py`
- `run_bitzi_monitoring_comedy.py`
- `assemble_bitzi_monitoring_comedy.py`
- `watermark_bitzi_image.py`

Die Beschriftung **Roland Gorczynski / bits.gorczynski.online** wird bei Exporten unten rechts ergänzt. Telegram-Beschreibungen können dieselbe Adresse als klickbaren Link enthalten. Ein Link innerhalb der Bildpixel selbst ist nicht klickbar.

## Herkunft und Genauigkeit

Die kanonische Bilddatei wurde aus der bestehenden Bits-mit-Biss-Referenz übernommen. Der ursprüngliche Prompt und das genaue Bildmodell dafür sind nicht dokumentiert; deshalb wird dafür keine Herkunft erfunden. Die dokumentierte Filmroutine bezieht sich auf den späteren Bitzi-Kurzfilm und nennt nur Werkzeuge, die dabei tatsächlich verwendet wurden.
