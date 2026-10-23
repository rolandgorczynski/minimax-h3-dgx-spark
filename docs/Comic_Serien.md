# Fortsetzungen und Serien – basierend auf einer vorhandenen Geschichte

Jede Folge bleibt eine eigene, bearbeitbare Geschichte mit eigener Kachelanzahl
und eigenem Bildstil. Das Anlegen einer Folge startet keine KI-Anfrage und keinen
Bildlauf. Die Basisgeschichte und ihre erzeugten Ausgaben werden nicht verändert.

## Eine neue Folge schreiben

1. Eine gespeicherte Geschichte öffnen und **Auf dieser Geschichte aufbauen**
   klicken. Ungespeicherte Änderungen werden dabei zuerst gespeichert.
   Alternativ **Fortsetzung / Serie – basierend auf …** öffnen und eine Basis
   aus den gespeicherten Geschichten oder fertigen Comic-Ausgaben wählen.
2. Serientitel, Folgennummer und Titel der neuen Folge prüfen. Die nächste freie
   Nummer wird vorgeschlagen. Bereits belegte Nummern derselben Serie werden
   beim Anlegen abgewiesen.
3. **Direkte Fortsetzung** wählen, wenn der neue Text am bisherigen Ende anschließt.
   **Neue Handlung im selben Universum – basierend auf** erlaubt eine andere
   Handlung mit denselben Figuren und Weltregeln.
4. Unter **Serienwissen** feste Fakten, Beziehungen, Regeln und längerfristige
   Entwicklungen festhalten. Unter **Offene Fäden** ungeklärte Fragen und den
   übergreifenden Serienbogen eintragen.
5. Den Text der neuen Folge eingeben. Alternativ zunächst **Schreibauftrag
   aktualisieren und anzeigen** klicken: Der kopierbare und herunterladbare
   Auftrag enthält Basis, Figuren und Serienvorgaben. Er ruft selbst kein LLM auf.
   Du kannst ihn zum Schreiben oder für eine gesonderte KI-Anfrage verwenden.
6. **Neue Folge zum Schreiben anlegen** klicken. Die Folge wird als neue
   Geschichte mit übernommenen Figuren und zunächst leerem Szenenplan gespeichert.
   Du kannst den Text auch erst danach im normalen Storyeditor eintragen.
7. **Szenen erstellen** klicken, den Plan prüfen und anschließend **Comic erzeugen**.

Bei einer reinen automatischen Definition zunächst eine fertige Ausgabe über
**Ausgewählte Ausgabe übernehmen** als bearbeitbare Geschichte speichern oder
im Serienformular unmittelbar die fertige Ausgabe auswählen. Die Basis benötigt
Figurenprofile und eine Geschichte oder einen Szenenplan.

## Was wird übernommen?

- Figuren mit denselben IDs, Namen, Beschreibungen, Kleidung, Vorgeschichten,
  Gesinnungen und vorhandenen Referenzbildern.
- Bei unverändertem Figurenprofil auch private Referenzbilder aus der letzten
  fertigen Ausgabe der Basisgeschichte, sofern als Snapshot vorhanden.
- Der letzte dokumentierte Figuren-Zustand aus den Szenen, etwa Haarlänge,
  Kleidung und mitgeführte Gegenstände.
- Der Text der vorigen Folge und deren letzte drei Szenen als Hintergrund.
- Serientitel und Serien-ID, Folgennummer, Basis-ID und die Version der Basis.
- Serienwissen, offene Fäden, Signatur, Erzählerkonfiguration und Autorvorschlag
  für den späteren Buchexport, soweit vorhanden.

Die neue Folge bekommt ihre eigene Geschichte-ID. Alte Szenen, Bildrevisionen,
Dialoglisten und Renderaufträge werden nicht als neue Handlung kopiert. Die
Szenenplanung betrachtet nur den neuen Text als zu adaptierende Handlung.
Die vorige Folge und das Serienwissen dienen zur Kontinuität.

Änderungen an Frisur oder Kleidung im neuen Text dürfen einen geerbten Zustand
ablösen. Personen, die in einer Folge nicht auftreten, bleiben in deren
Figurenbestand für spätere Fortsetzungen erhalten. Es gilt weiterhin die
vorhandene Grenze von acht Figuren pro bearbeitbarer Geschichte; nicht benötigte
Figuren lassen sich im Entwurf entfernen.

## Kontinuität prüfen

Serienwissen ist eine bearbeitbare Gedächtnisstütze. Die Software erstellt hier
keine automatische Zusammenfassung aller bisherigen Folgen. Langfristig wichtige
Entwicklungen deshalb in **Serienwissen** und **Offene Fäden** nachführen. Der
vollständige Text und das Ende der unmittelbar gewählten Basis werden zusätzlich
übernommen. Das verhindert nicht jede mögliche Fehlinterpretation des Modells:
Namen, Zustände, Wissen der Figuren und Dialoge vor dem Rendern prüfen.

Im Storyeditor erscheint die Zuordnung **Serie · Folge · basierend auf …**.
Darunter können Serienwissen und offene Fäden für diese Folge geändert und mit
**Speichern** gesichert werden. Die Angaben werden bei der nächsten Fortsetzung
wieder angeboten. Frühere Folgen werden durch solche Änderungen nicht bearbeitet.

Wenn eine korrigierte Bildausgabe der verbindliche Stand sein soll, diese Ausgabe
als Basis wählen. Der gespeicherte Textentwurf und eine später korrigierte Ausgabe
können unterschiedliche Zustände enthalten. Einzelne Bilder werden nicht visuell
analysiert, um daraus ungeschriebene Serienfakten abzuleiten.

Eine Basis wird beim Anlegen als Kontext und mit Figurenkopien übernommen.
Spätere Änderungen oder das Löschen der Basis verändern die vorhandene Folge
nicht rückwirkend. Eine andere Basis während des Schreibens zu wählen, verwirft
ungespeicherte Angaben nur nach Bestätigung. Ein inzwischen geänderter Basistext
wird über die Versionsprüfung erkannt; die Basis dann neu laden.

## API

Die bestehende Bearer-Authentifizierung gilt unverändert.

- `GET /series/bases`: geeignete Geschichten und fertige Comic-Ausgaben.
- `POST /series/preview`: Basis laden und Schreibauftrag vorbereiten, ohne etwas
  zu speichern. Zunächst `base_kind` (`story` oder `job`) und `base_id` senden.
  Die Antwort enthält `settings` mit `base_version`, Titeln, Vorschlägen und
  Folgennummer. Weitere Formularangaben können beim erneuten Aufruf mitgegeben werden.
- `POST /series/episodes`: die geprüften `settings` mitsamt optionalem `article`,
  `canon` und `open_threads` als neue Folge speichern. Bei einer gespeicherten
  Geschichte muss die zuvor geladene `base_version` mitgesendet werden.

Serienangaben liegen unter `payload.series` im Storyboard. Der Export eines
Storyboards erhält diese Metadaten. Es wird kein ComfyUI-Workflow geändert und
kein externer Modellanbieter angesprochen.
