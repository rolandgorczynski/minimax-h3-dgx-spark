# Comic-Studio: vom Skript zur Veröffentlichung

Das Dashboard hat vier getrennte Arbeitsschritte. Die Navigation selbst startet
keinen Auftrag und löscht keine Eingaben. Zurückwechseln ist jederzeit möglich.

## 1 · Skript erstellen

Drei Eingabewege stehen unter einer gemeinsamen Überschrift:

- **Meine Geschichte:** Titel und Text einfügen, Kachelanzahl festlegen und
  **Skript / Szenen erstellen** klicken. Figuren, Erzählertext, Dialoge, Zustände
  und Übergänge werden geplant und anschließend zur Bearbeitung angezeigt.
- **Buch oder Film als Vorlage:** Quelle wählen, gewünschte Kachelanzahl und
  Adaptionswünsche angeben. Das lokale Modell erzeugt ein bearbeitbares Skript.
  **Als neue Geschichte übernehmen** speichert es und öffnet Schritt 2.
- **Fortsetzung / Serie:** Vorige Folge wählen, Serienwissen und neue Handlung
  festlegen, die neue Folge anlegen und deren Szenen planen. Bestehende Figuren
  und Gestaltungsvorgaben werden übernommen, ohne die vorige Folge zu ändern.

Die Kachelanzahl gehört zum Skript, weil sie den Handlungsbogen aufteilt. Ein
neues Quellenskript benötigt keine Bildstilentscheidung. Seine Bildstilzeile
bleibt ausdrücklich offen; die technische interne Standardkennung beeinflusst
nicht den Schreibauftrag und wird nicht als Stilvorgabe in die Szenen eingebrannt.

Unter den erweiterten Optionen von „Meine Geschichte“ lässt sich weiterhin
**Eine neue Geschichte lokal erfinden** wählen. Auch dieser Weg schreibt jetzt
zuerst eine Geschichte und erstellt einen prüfbaren Szenenplan. Keine Bilder.
**Neue Geschichte vorbereiten** übernimmt vorhandene Einstellungen als Ausgangspunkt
für einen neuen Entwurf, startet aber noch keinen Auftrag.

Bei einer geänderten Kachelanzahl wird direkt daneben **Skript neu erstellen**
aktiv. Der Hinweis zeigt die bisherige und die neue Anzahl. Nach Bestätigung wird
das Skript neu aufgeteilt; Bilder werden dabei nicht erzeugt. Bis zur bestätigten
Neuplanung bleiben die bisherigen Szenen erhalten, auch beim Verkleinern der
Kachelanzahl. Bei Buch-/Filmvorlagen gibt es denselben Button für ein neues
Quellenskript; bereits übernommene Geschichten und Comic-Ausgaben bleiben erhalten.

Das Skript speichern und mit **Weiter zur Comic-Gestaltung** fortfahren.

## 2 · Comic erzeugen

Ein gespeichertes Skript auswählen oder das gerade übernommene verwenden.
Hier befinden sich:

- Bildstil und die Bibliothek mit lokalen Vorschaubildern;
- Canvas-/Seitenvorlagen mit ihren unterschiedlich geformten Kacheln;
- Figurenprofile, Referenzbilder und wiederverwendbare Figurenbibliothek;
- **Gestaltung speichern** und der getrennte Button **Comic erzeugen**.

Neue Skripte haben zunächst keine gewählte Bildsprache. Für die Bilderzeugung
muss ein Stil ausgewählt sein. Vorhandene Geschichten behalten ihren bisherigen
Stil; Serien übernehmen die gespeicherten Vorgaben ihrer Basis. Ein Stil- oder
Seitenvorlagenwechsel erhält den Szenenplan und dessen Texte.

Sind Ausgangstext oder Kachelanzahl nachträglich verändert worden, muss der
Szenenplan zuerst in Schritt 1 aktualisiert werden. Die Bilderzeugung startet
keine versteckte Skriptplanung. Änderungen direkt an den einzelnen Szenen sind
weiterhin möglich und werden mit dem Skript gespeichert.

**Comic erzeugen** erstellt eine eigene Ausgabe mit einem Schnappschuss des
Skripts und der Gestaltung. Bereits vorhandene Ausgaben bleiben erhalten.

## 3 · Comic bearbeiten

Die gewünschte erzeugte Ausgabe auswählen. Hier sind Vorschau, Fortschritt,
Prüfhinweise, Einzelbildkorrekturen, Sprechblasenpositionierung, geführtes Lesen,
Experimente und optionales Feedback zusammengefasst. Korrekturen und Experimente
verwenden weiterhin die vorhandenen Verfahren für neue Ausgaben; die bisherigen
Fassungen können ausgewählt werden.

## 4 · Veröffentlichen und exportieren

Dieser Bereich verwendet die in Schritt 3 ausgewählte Ausgabe. Titel und
Ausgabenkennung zeigen, welche Fassung gemeint ist. Wurden Skript oder Gestaltung
inzwischen bearbeitet, weist der Bereich darauf hin: Die ältere Ausgabe bleibt
unverändert und enthält noch nicht die neueren Änderungen.

Hier liegen Comic-Paket, PDF, EPUB-/Taschenbuchexport sowie Telegram, X und
Substack. Die Teilen-Dialoge bieten Titel, Begleittext und Quellenlink zur
Bearbeitung an. Nur der ausdrückliche Telegram-Veröffentlichungsbutton sendet
direkt in den gespeicherten Kanal; X und Substack behalten ihren bisherigen Ablauf.

## Bestehende Daten und technische Kompatibilität

Es ist keine Datenmigration notwendig. Gespeicherte Geschichten, Quellenskripte,
Serien, Figuren und Ausgaben bleiben erhalten. Neue Quellenskripte markieren den
Bildstil als noch offen. Alte Quellenaufträge mit ausdrücklich übergebenem Stil
lassen sich weiterhin lesen und übernehmen.

Bestehende externe Automationsaufrufe bleiben kompatibel. Die Trennung betrifft
den geführten Dashboard-Ablauf; historische API-Aufrufe für vollständige
Automatikdurchläufe werden nicht entfernt. Gespeicherte ComfyUI-Workflows werden
für diesen Umbau nicht verändert.
