# Audio-Mastering für H3-Comics

Die Assembly-Skripte messen die fertige H3-Tonspur jetzt in zwei Durchläufen und
normalisieren sie auf einen einstellbaren integrierten Lautheitswert und True Peak.
Standard sind −16 LUFS und −1,5 dBTP bei 48 kHz. Das sind redaktionelle Startwerte,
keine von YouTube festgelegte Pflicht.

`scripts/audio_mastering.py` prüft zuerst die Kanalzahl. `dual_mono=true` wird nur für
Monoquellen gesetzt; Stereo bleibt Stereo. Optionale Fade- und Pad-Filter werden vor
der Messung angewendet, damit gemessen wird, was später tatsächlich im Film landet.
Der zweite Durchlauf übernimmt die Messwerte aus dem ersten.

## Verwendung

Die `assemble_bitzi_*.py`-Skripte rufen die gemeinsame Routine vor dem Muxen auf.
Für eine einzelne FLAC-Datei:

```bash
python3 scripts/audio_mastering.py input.flac mastered.flac
```

Für dialogdominantes Audio kann man zusätzlich die optionale Sprachbearbeitung
aktivieren:

```bash
python3 scripts/audio_mastering.py input.flac mastered.flac --speech-cleanup
```

Diese Option setzt Hochpass bei 80 Hz, De-Esser mit Intensität 0,4 und einen milden
Kompressor. MiniMax H3 mischt Dialog, Musik und Effekte häufig gemeinsam in eine
Spur. Deshalb bleibt Sprachbearbeitung standardmäßig aus: Auf einer kompletten
Musik- oder Effektmischung könnte sie Klangfarben verändern. Bei einem einzelnen
Bassproblem ist ein gezielter EQ nach Gehör besser als pauschales Filtern.

Messwerte werden auf der Konsole ausgegeben. Das Werkzeug verändert keine H3-Quelle;
es erzeugt eine separate 48-kHz-FLAC-Datei für die anschließende Videomontage.

## Bezug zu A-112

Aus der Recherche A-112 übernommen wurden die Zwei-Pass-Messung, die 48-kHz-Ausgabe
und die bedingte Mono-Korrektur. Die vorgeschlagenen Filter für Sprache sind als
Option verfügbar, aber nicht auf H3-Komplettmischungen erzwungen. Ein Wechsel von H3
zu Wan oder LTX sowie ein Character-LoRA-Training wurde nicht übernommen: Der Bericht
weist diese Spark-Konfigurationen nicht als eigene Tests aus; einzelne genannte
Modelllizenzen schränken außerdem die kommerzielle Nutzung ein.

Quellen: [A-112 – Comic-Serie lokal auf DGX Spark](https://github.com/rolandgorczynski/researcher/blob/main/berichte/A-112-comic-serie-lokal-dgx-spark-2026-10-31.md),
[FFmpeg-Filterdokumentation zu `loudnorm`](https://www.ffmpeg.org/ffmpeg-filters.html#loudnorm).
