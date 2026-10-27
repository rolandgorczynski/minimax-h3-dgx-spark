# Bildregie am Beispiel des tapferen Schneiderleins

Die Bildvorgaben dieser Studio-Geschichte wurden von Codex anhand tatsächlicher lokaler FLUX.2-Klein-9B-Ausgaben überarbeitet. Handlung, zwölf Kacheln, Figuren-IDs, Erzählertexte und Dialogwortlaut bleiben erhalten. Sichtbare Figuren, Kamera, Requisiten und Blasenpositionen wurden gezielt präzisiert. Die bisherigen Comic-Ausgaben und der gespeicherte Workflow 04 werden nicht überschrieben.

## Was der Vergleich gezeigt hat

- Die Reservierung einer freien oberen Fläche begünstigte einen leeren Kasten und fehlende Bildteile. Der Erzähler wird außerhalb des Bildes gesetzt; die Illustration soll deshalb durchgehend ausgefüllt sein.
- „Schneider klein dahinter“ begünstigte eine zweite Miniaturfigur. Eine einzige räumliche Situation, genaue sichtbare Figurenanzahl und erwachsene Proportionen sind eindeutiger.
- Die alte Vogelreferenz zeigte ein kräftiges Tier. Eine neue Referenz definiert einen handtellergroßen braunen Singvogel.
- Gegenstände in einer Personenreferenz können trotz anderer Szenenanweisung wieder auftauchen. Für die wiederkehrenden Personen werden Ausschnitte mit Gesicht, Schultern und Kleidung ohne Handrequisiten verwendet. Die Originalbilder bleiben im lokalen Vorher-Snapshot erhalten.
- Unsichtbarer Besitz gehört ins Kontinuitätsregister. Die eigentliche Bildbeschreibung und die übergebenen visuellen Figuren-Zustände enthalten die sichtbare Situation; ein verborgener Vogel wird dort nicht nochmals beschrieben.
- Eine eindeutig getragene Sitzfläche unter dem Gesäß war wirksamer als die allgemeine Angabe „in den Ästen sitzen“.
- Mehrere gleichzeitig gezeigte Handlungen steigerten die Fehlerzahl. Die Steinprobe ist nun eine Hand-Nahaufnahme, die Käseantwort eine einzelne Figur und die Nachtszene zeigt den Riesen am leeren Bett. Die zuvor gezeigte sichere Nische erklärt, wo der Schneider bleibt.
- Auch ein gutes Rohbild kann durch die Beschriftung beschädigt werden. Blasen wurden an den tatsächlichen Gesichtern vorbei positioniert; der Frage-Antwort-Ablauf in Kachel 3 bleibt von oben nach unten lesbar.

## Empfohlenes redaktionelles Vorgehen

1. **Handlungsregister:** Wer ist wo, besitzt was, hat etwas abgelegt oder verlassen? Dieses Register darf auch unsichtbare Informationen enthalten.
2. **Sichtbarer Bildauftrag:** Genau ein Zeitpunkt, sichtbare Figuren und Gegenstände, Kamera und entscheidende Geste. Sichtbares von Besitz und späteren Ereignissen trennen.
3. **Referenzen prüfen:** Gesichtsidentität erhalten; Bildrequisiten, Größenmaßstab und Tierart dürfen dem aktuellen Bildauftrag nicht widersprechen.
4. **Kontrollierter Vergleich:** Modell, Bildgröße und Seed möglichst konstant halten. Prompt und zugehörige Referenzen zusammen dokumentieren.
5. **Rohbild ansehen:** Köpfe, Gliedmaßen, Duplikate, Handgriffe, Größen, Eigentümer der Gegenstände, Handlung und Hintergrund kontrollieren.
6. **Nur belegte Fehler korrigieren:** Bei überladener Szene lieber die Kamera auf den entscheidenden Moment richten, statt immer weitere Verbote anzuhängen.
7. **Beschriftetes Bild ansehen:** Lesbarkeit, verdeckte Gesichter, Sprecherzuordnung, Blasenschwänze und Leserichtung prüfen.
8. **Geprüfte Variante erhalten:** Neue Vorgaben speichern; bestehende Ergebnisse behalten. Ein anderer Seed oder Bildstil erfordert eine neue Bildprüfung.

## Exakte Mengen

Die Anordnung „vier plus drei“ machte die sieben Fliegen im Versuch nicht zuverlässig abzählbar. Es entstanden unter anderem fünf, acht oder neun Tiere. Eine zufällig passende Anzahl ist kein Beweis für ein zuverlässiges Promptverfahren.

In der übernommenen Kachel 1 liegt ein Teil der Fliegengruppe nachvollziehbar unter dem Stofflappen. Der Erzähler vermittelt die Zahl sieben; das Bild behauptet keine vollständig sichtbare und abzählbare Gesamtzahl. Das ist eine bewusste Bildentscheidung, keine bestandene Zählprüfung.

## Testbedingungen und Ablage

- Lokales Modell und vorhandene Lader des Workflows 04; Holzschnitt / Linolschnitt.
- 1024 × 704 Pixel für die Illustrationen, vier Sampling-Schritte unverändert.
- Grundseed `45432533`, pro Originalkachel um deren nullbasierten Index erhöht.
- Eigene Testdatenbank und eigene ComfyUI-Sitzungen; keine Modelle oder bestehenden Workflows verändert.
- Lokale vollständige Testablage: `/home/jee/docker-data/comic-automation/prompt-tests/schneiderlein-20261027/`.
- `geschichte-vorher.json` und `geschichte-nachher.json`: private Studio-Snapshots mit Referenzen; nicht ins Git aufnehmen.
- `testdaten/jobs/*/vorgaben.json`: tatsächlich verwendete Szenen, Seeds und Figurenreferenzen der einzelnen Tests.
- `Auswertung.md`: Versuchsverlauf; `Ergebnis/`: zusammengestellte Prüffassung mit Einzelbildern, drei Teilseiten und PDF.
- [Überarbeitete Vorgaben ohne eingebettete Referenzbilder](../examples/comics/bildregie/schneiderlein-12-bildvorgaben.json).

Das Verfahren verbessert die geprüften Fälle, garantiert jedoch keine fehlerfreien künftigen Bilder. Kleine Anatomie-, Kleidungs- und Umgebungsabweichungen bleiben prüfpflichtig. Eine allgemeine automatische Bildfreigabe ist mit dieser redaktionellen Überarbeitung nicht eingebaut.

Abschluss dieses Versuchs: **48 Vergleichsbilder und eine neue Vogelreferenz**. Die Studio-Geschichte `cc173612a0bd4bb9bd069abfdeee8b91` enthält die präzisierten Vorgaben in Version **5**.

Die geprüften Testbilder sind zusätzlich als **neue Studio-Ausgabe** `93bf4d8236164080908fbc6acfbcb0d8` dieser Geschichte bereitgestellt (Status: vor Veröffentlichung prüfen). Es wurde dafür keine bestehende Ausgabe ersetzt.
