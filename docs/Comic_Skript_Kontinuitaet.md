# Skriptführung und körperliche Kontinuität

Neue Artikel-Szenenpläne, Quellenskripte und automatisch erfundene Geschichten
werden vor der Bilderzeugung um eine körperliche Zustandsführung ergänzt.
Vorhandene Comics und Zeichnungen werden dadurch nicht verändert. Eine neue
Skripterstellung startet erst durch den jeweiligen normalen Erstellungsaufruf.

## Grundregel

**Ein Zustand gilt weiter, bis eine belegte Handlung ihn ändert.**

Beispiel:

1. Hildebrand kommt auf seinem braunen Pferd angeritten.
2. Alebrand spricht mit Hildebrand.
3. Hildebrand antwortet.

In Kachel 2 und 3 bleibt Hildebrand im Sattel. Das Skript darf nicht stillschweigend
ein Absteigen und erneutes Aufsteigen erfinden. Die Bildbeschreibung muss den
Reiter, das Pferd und gegebenenfalls den Höhenunterschied zum Gesprächspartner
klar benennen. „Steht ihm gegenüber“ allein belegt kein Absteigen.

## Geprüfte Zustände

- Fortbewegung: beritten, zu Fuß, in einem Fahrzeug, fliegend oder schwimmend.
- Reittier oder Fahrzeug.
- Eindeutige Körperhaltung.
- Ort.
- Gehaltene bzw. mitgeführte Gegenstände.
- Verletzungen.
- Lebenszustand.
- Kleidung.

Unbekannte Angaben bleiben offen. Eine Figur darf aus dem Bild verschwinden,
ohne ihren zuletzt bekannten Zustand zu verlieren. Die Zustandsführung geht
auch über Grenzen der abschnittsweisen Skripterstellung hinweg weiter.

## Ablauf

1. Ein lokales Modell ermittelt relevante Zustände und tatsächliche Änderungen.
   Jede Angabe braucht ein wörtliches Zitat aus der Textgrundlage; bei der
   Artikelplanung aus dem zur Kachel gehörenden Quellabschnitt. Ein fehlerhafter
   Bildentwurf ist kein Beleg.
2. Das Programm führt daraus ein Zustandsprotokoll. Unbelegte Behauptungen werden
   verworfen und im Bericht festgehalten. Fortbewegungswechsel werden zusätzlich
   auf eindeutige Hinweise geprüft: bloßes Sprechen oder Gegenüberstehen genügt
   für einen Wechsel zu Fuß nicht.
3. Die Bildbeschreibungen werden unter Beibehaltung der Ereignisse präzisiert.
   Erzählertexte, Sprechblasen, Sprecher, Figuren-IDs und Kachelanzahl bleiben
   erhalten.
4. Ein weiterer lokaler Modellaufruf prüft die Beschreibungen gegen die erwarteten
   Zustände. Bei belegten Widersprüchen folgt eine begrenzte Korrektur und erneute
   Prüfung. Bleibt ein Widerspruch, stoppt die Erstellung vor dem Zeichnen.
5. Relevante sichtbare Zustände stehen zusätzlich ausdrücklich in der jeweiligen
   Bildanweisung und im Figurenzustand für das Bildmodell.

Im Dashboard erscheint **Körperliche Zustände und Übergänge prüfen**. Diese
zusätzlichen lokalen Modellaufrufe benötigen Zeit, erzeugen aber keine Bilder.
Wenn sich keine relevanten Zustände ergeben, entfällt die zusätzliche
Bildbeschreibungsüberarbeitung.

## Serien und bearbeitete Skripte

Direkte Fortsetzungen übernehmen die strukturierten Endzustände als
`series.initial_continuity_state`. Für **neue Handlung im selben Universum**
wird diese körperliche Ausgangsposition nicht automatisch übernommen.
Figurenidentität, Serienwissen und bisheriges Aussehen folgen weiterhin den
bestehenden Serienregeln.

Bei Quellenskripten werden die festgeschriebenen Angaben im ausgegebenen Skript
sichtbar. Unveränderte Kontinuitätsfelder ermöglichen bei der Übernahme außerdem
die Zuordnung der gesicherten Zustände zu den Figuren-IDs der neuen Geschichte.
Manuelle Änderungen können neue Widersprüche einführen; sie werden nicht durch
ein Hintergrundverfahren rückgängig gemacht. Vorhandene Szenen werden nicht
allein durch ein Softwareupdate neu geplant.

## Grenzen

Die semantische Zuordnung von Quellenstellen zu Zuständen bleibt eine Aufgabe
der lokalen Modelle und ist fehlbar. Die Prüfung verbessert das Skript, ersetzt
aber keine Sichtprüfung fertiger Bilder. Das Bildmodell kann eindeutige
Anweisungen trotzdem falsch zeichnen. Eine automatische nachträgliche Bildprüfung
auf alle körperlichen Zustände ist mit dieser Änderung nicht hinzugekommen.
Experimentelle Regiefassungen und gezielte Einzelbildkorrekturen behalten ihre
jeweiligen eigenen Prüfabläufe.

## Daten und Diagnose

- `continuity_state` je Kachel: strukturierte bekannte Zustände einschließlich
  zwischenzeitlich unsichtbarer Figuren.
- `character_states`: sichtbare Zustände als konkrete Bildmodell-Anweisung.
- `continuity-report.json`: geprüfte Kacheln, Quellenbelege, verworfene unbelegte
  Zustandsbehauptungen und Endzustand.
- Artikelentwürfe speichern außerdem ein `continuity_ledger`.

Der Bericht dokumentiert eine modellgestützte Prüfung und ist keine Garantie
für Fehlerfreiheit. Alle beteiligten Modelle sind die vorhandenen lokalen
Modelle; externe Dienste oder Modell-Downloads sind nicht erforderlich.
