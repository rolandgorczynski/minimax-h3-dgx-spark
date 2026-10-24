# Kacheln an die Seitenvorlage anpassen

Neue Ausgaben mit einer Seitenvorlage erhalten passende Kachelformate statt
identischer Bilder in unterschiedlich großen weißen Feldern. Die Einstellung
**Bisheriges Layout** behält das bisherige Format bei.

## Was die Vorlage jetzt bestimmt

- Das Seitenverhältnis jedes Felds legt Breite und Höhe der beschrifteten Kachel fest.
- Große Hauptfelder bekommen mehr Bildfläche und eine höhere Sampling-Auflösung.
- Für die Illustration wird der Platz des Erzählerkastens berücksichtigt. Das
  lokale Bildmodell erzeugt ein entsprechend breites, quadratisches oder hohes Bild.
- Die Texte werden anschließend im vorgesehenen Kachelformat gesetzt. Fertige
  Sprechblasen oder Erzählerkästen werden nicht durch einen Bildbeschnitt gekürzt.
- Die Felder werden beim Zusammenstellen der neuen Seiten vollständig ausgefüllt.
- Scrollvorlagen bilden längere Bildfolgen, Zeitungsstreifen ein breites Format.

Die Formatvorgaben gelten auch bei mehr als zwölf Kacheln und wiederholen sich
auf den weiteren Seiten der Vorlage. Die Szenen und Dialoge werden durch die
Formatwahl nicht umgeschrieben.

## Bedienung

Geschichte öffnen, unter **Canvas-/Seitenvorlagen** eine Vorlage auswählen und
speichern. Beim nächsten Erzeugen dieser Geschichte werden die neuen Formate
verwendet. Bei einer vorhandenen Ausgabe ist eine neue Ausgabe erforderlich;
ein Softwareupdate verändert keine gespeicherten Comic-Bilder.

Die geführte Leseansicht, EPUB und Taschenbuch übernehmen die so erzeugten
Kacheln und die zugehörigen Seitenproportionen. Der Sprechblaseneditor verwendet
für jede Kachel deren tatsächliche Breite und Höhe. Bereits gespeicherte
Positionen werden bei einem Formatwechsel anhand des Bildbereichs umgerechnet;
die genaue Zuordnung zu Gesichtern sollte anschließend kontrolliert werden.

## Lesbarkeit

Schriftgrößen werden bei größeren Kacheln mitgeführt. Die Vorprüfung verwendet
bereits das tatsächliche Format und stoppt, wenn der Text darin nicht lesbar
unterzubringen ist. Sehr flache Filmstreifen bieten weniger Platz für lange
Gespräche. Dann Blasen vergrößern, Text aufteilen oder eine höhere Vorlage wählen.
Die Druckprüfung berücksichtigt zusätzlich die Schriftgröße im gewählten Buchformat
und die ursprüngliche Illustrationsauflösung.

## Bestehende Ausgaben

Alte Dateien bleiben unverändert. Ihre bisherigen Seiten behalten die alte
Anordnung, solange keine vollständige neue Ausgabe erzeugt wird. Reine
Einzelbildkorrekturen und neue Beschriftungen erhalten das Format ihrer Basis.
Auch eine Feedbackkorrektur einer älteren Ausgabe löst keine unerwartete
Formatumstellung aller übrigen Bilder aus.

Bei neuen Ausgaben mit adaptiven Formaten werden diese auch für weitere
Einzelbildkorrekturen, Beschriftungen und Leser-/Buchexporte beibehalten.

## Technische Daten

`canvas_size` je Szene enthält die Zielgröße einschließlich Textbereich.
`render_size` beschreibt die davon abgeleitete Illustrationsgröße. Beide Angaben
werden durch Planung, ComfyUI-Planparser, Sampling, Zwischenspeicher und
Beschriftung weitergereicht. Die Auflösungen sind begrenzt und an das Raster des
lokalen Bildmodells angepasst. Bestehende ComfyUI-Workflow-Dateien werden nicht
geändert; die Formatvorgaben sind Bestandteil des übergebenen Szenenplans.

Ein neues Seitenverhältnis kann die Kameraarbeit des Bildmodells beeinflussen.
Die Formatprüfung garantiert keine fehlerfreie Darstellung aller Körperteile
oder Gegenstände; dafür bleibt die Sichtprüfung der erzeugten Bilder erforderlich.
