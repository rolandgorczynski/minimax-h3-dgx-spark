# Mehr Wow – experimentelle Regiefassungen

Der Experimentmodus erzeugt aus einer fertigen, gegebenenfalls bereits
korrigierten Comic-Ausgabe eine eigene Variante. Ziel sind ein stärkerer
emotionaler Bogen, verständliche Konflikte, Vorbereitung und Wendepunkte,
prägnante Dialoge sowie abwechslungsreicher Bildrhythmus. Mehr Blut oder Wut
allein ersetzt diese Arbeit nicht.

## Bedienung

1. Unter **Erzeugte Ausgaben** die gewünschte aktuelle Fassung wählen. Nach
   Bildkorrekturen oder neuer Beschriftung deren gespeicherte Ausgabe verwenden.
   Ungespeicherte Änderungen im Storyeditor gehören noch nicht zur Bildausgabe.
2. **Mehr Wow · Experiment** anklicken.
3. Den Spielraum wählen:
   - **Dramaturgie und Dialoge frei zuspitzen:** Handlungskern und Figuren bleiben,
     Ereignisse, Szenen, Wendepunkte, Erzählertexte und Dialoge dürfen sich ändern.
   - **Nur Bildinszenierung verstärken:** Handlung, Reihenfolge und Wortlaut der
     Erzählertexte und Sprechblasen bleiben erhalten. Die Bilder werden neu inszeniert.
4. Entscheiden, ob das bisherige Ergebnis der Geschichte erhalten bleiben soll.
   Bei reiner Inszenierung bleibt es immer erhalten. In der freien Fassung kann
   ausdrücklich auch ein anderer Schluss erlaubt werden.
5. Regler von **0 bis 3** wählen: Spannung, Wut/emotionale Reibung, Action,
   Blut/sichtbare Konsequenzen, Dialoge mit Biss und filmische Bildwirkung.
   0 bedeutet keine zusätzliche Verstärkung, 1 fein, 2 deutlich, 3 radikal.
   Vorlagen sind **Mehr Sog**, **Wut & Action**, **Mehr Herz** und **Düstere Härte**.
6. Eine eigene Regieanweisung ergänzen, zum Beispiel:

   > Weniger erklären. Ria soll eine echte Entscheidung treffen müssen. Erst
   > eine stille Nahaufnahme, dann ein harter Wechsel in die Totale. Mehr Wut
   > zwischen den Figuren, aber keine zusätzlichen Verletzungen. Der Schluss
   > soll nachhallen und die bisherige Auflösung erhalten.

7. **Experiment als neue Ausgabe erzeugen** anklicken. Erst dieser Klick startet
   den Auftrag. Er plant eine neue Fassung und zeichnet alle Kacheln neu.
8. Die mit **Experiment** markierte Ausgabe auswählen und prüfen. Unter
   **Regie und Änderungen des Experiments** stehen der Regieplan und die
   Änderungen je Kachel. **Original / Basis öffnen** wechselt zur vorherigen
   Ausgabe, sofern sie noch in der Auswahl vorhanden ist.

Eine überzeugende Wirkung ist subjektiv und muss am Ergebnis geprüft werden.
Der Modus ist ausdrücklich experimentell. Ein Versuch kann auch schlechter
werden als seine Basis; diese bleibt deshalb separat verfügbar. Die neue
Fassung kann ihrerseits die Basis für ein weiteres Experiment sein.

## Was bleibt geschützt?

- Originaldateien, Originaltext, Originalausgabe und deren gespeicherte Story.
- Figurenbibliothek, Figuren-IDs und vorhandene private Referenzbilder.
- Feedback der Basis und die bestehenden Lernregeln; das Experiment schreibt
  keine eigene Bewertung oder automatischen Erfahrungen in die Basis zurück.
- Gespeicherte ComfyUI-Workflows und Veröffentlichungsziele.

Die Kachelanzahl und der Bildstil stammen aus der ausgewählten Ausgabe.
Es gibt einen neuen Auftrag mit eigenem Seed, eigenen Dateien und einem
Snapshot der Basis. Die Originalzeichnungen werden in dessen privaten
Checkpoints gesichert. Die Neufassung braucht danach keine Dateien der Basis
zum Rendern mehr. Ein gespeicherter Versionsabdruck verhindert, dass unbemerkt
auf einer inzwischen geänderten Basis gestartet wird.

Die Variante erhält keine Zuordnung zur bisherigen Story-ID oder zur
kanonischen Serienfolge. Vorhandene Serienangaben bleiben als Herkunft unter
`based_on_series` dokumentiert. Wer die Variante später als verbindliche Story
nutzen will, übernimmt sie ausdrücklich mit den vorhandenen Importfunktionen.

## Prüfungen und Ablauf

1. Aktuelle Szenen, Dialoge, Figurenreferenzen und Rohbilder sichern.
2. Ausgewählte Originalkacheln als Bildtafel analysieren und einen Regieplan
   entwickeln. Die Bildtafel ist eine Stichprobe, keine vollständige Bildprüfung.
   Falls das lokale Bildmodell nicht verfügbar ist, erfolgt eine protokollierte
   Textanalyse als Ersatz.
3. Szenen in Abschnitten mit höchstens sechs Kacheln schreiben.
4. Je Abschnitt Motivation, Ursache und Wirkung, Kontinuität, Sprecher und
   Schlusswirkung prüfen; bei Befunden einmal nachbessern. Bleiben konkrete
   Fehler, stoppt der Auftrag vor der Bilderzeugung.
5. Die vorhandene Deutschprüfung und die Layoutprüfung anwenden. Zu lange,
   nicht passende Texte oder unbekannte Figuren-IDs werden abgewiesen.
6. Neue Bilder mit den übernommenen Figurenreferenzen zeichnen und als
   eigenständige Ausgabe exportieren. Die abschließende Sichtprüfung erfolgt
   durch dich, einschließlich Sprechblasenpositionen und Lesbarkeit.

Koordinaten und geschützte Bereiche der alten Bilder werden nicht auf neue
Kompositionen übertragen. Neue Blasen erhalten die normalen Ausgangspositionen.
Bei reiner Inszenierung bleiben dabei Wortlaut, Sprecher und Blasenstil erhalten.
Nach dem Zeichnen lassen sich die Blasen wie gewohnt verschieben.

Die freie Fassung wird als fiktionale Experimentvariante gekennzeichnet. Sie ist
keine faktentreue journalistische Überarbeitung und keine Behauptung über eine
historisch überlieferte Originalhandlung. Das gilt auch bei einer realen oder
historischen Textgrundlage. Veröffentlichung erst nach redaktioneller Prüfung.

Alle Modellaufrufe verwenden die bereits konfigurierten lokalen Modelle.
Es wird kein externer Modellanbieter hinzugefügt.

## API und Dateien

Bestehende Bearer-Authentifizierung verwenden.

- `GET /jobs/<id>/experiment-options`: Basisversion, Titel, Anzahl und Regler.
- `POST /jobs/<id>/experiment`: eigene Variante mit `version`, `mode`
  (`rewrite` oder `staging`), `keep_ending`, `levels` und optional `notes` starten.
- `levels` enthält `tension`, `anger`, `action`, `blood`, `dialogue`, `visuals`,
  jeweils als ganze Zahl von 0 bis 3.
- Ein laufendes Experiment derselben Basis verhindert einen parallelen
  Doppelauftrag. Nach Abschluss oder Fehler ist ein weiterer Versuch möglich.

`experiment-input.json` enthält den Snapshot und die Regieeinstellungen.
`experiment-report.json` dokumentiert Basis-ID, Versionsabdruck, Regieplan,
Änderungsgründe und Prüfhinweise. Unter `reports/` stehen Modellantworten und
Sprachentscheidungen. Fertige Varianten enthalten die üblichen Comic-,
Einzelkachel-, Teilseiten- und PDF-Dateien sowie das Gesamtpaket.
