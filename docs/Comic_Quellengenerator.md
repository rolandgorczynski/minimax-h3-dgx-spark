# Bücher und Filme als Comic-Vorlagen

Der Quellenbereich im Dashboard erzeugt mit dem konfigurierten lokalen LLM ein
deutsches Comic-Skript. Das Skript lässt sich bearbeiten, speichern und direkt
als neue Geschichte mit fertigen Figuren, Szenen und Sprechblasen übernehmen.
Eine erneute Artikelanalyse ist dafür nicht nötig. Bilder werden erst nach dem
Klick auf **Comic erzeugen** in der übernommenen Geschichte erzeugt.

## Bedienung

1. **Buch oder Film als Comic-Vorlage** öffnen.
2. Eine gespeicherte Vorlage auswählen. Mitgeliefert werden **Der kleine Prinz**,
   **Die Bremer Stadtmusikanten** und **Eine Weihnachtsgeschichte**.
3. Unter **Quellendaten und Rechtehinweise bearbeiten** die Textgrundlage prüfen.
   Die mitgelieferten Einträge enthalten eigene kurze Inhaltszusammenfassungen,
   keine vollständigen Originaltexte. Das Ergebnis ist eine freie Adaption,
   keine garantiert vollständige oder wortgetreue Wiedergabe des Originals.
4. Comic-Stil, Kachelanzahl, optional Autor/Pseudonym und Adaptionswünsche angeben.
5. **Comic-Skript lokal erstellen** anklicken. Zuerst entstehen Figuren und ein
   Handlungsbogen; die Szenen folgen in Abschnitten mit höchstens sechs Kacheln.
   Eine lokale Logikprüfung vergleicht jeden Abschnitt auch mit der gespeicherten
   Textgrundlage und kann eine Korrektur auslösen. Der erzeugte Handlungsbogen
   gilt dabei nicht automatisch als verlässlich. Verbleibende
   Hinweise sowie Ergebnisse der Layoutprüfung werden angezeigt. Sprache wird
   zusätzlich geprüft. Modellprüfungen ersetzen deine eigene Prüfung nicht.
6. Das fertige Skript im Textfeld prüfen und ändern. **Skript speichern** erhält
   Änderungen für das erneute Öffnen. **Skript herunterladen** liefert eine
   Textdatei. Die Grundstruktur aus der Formatvorlage beibehalten.
7. **Als neue Geschichte übernehmen** klicken. Titel, Autor, Figuren, Kachelgrenzen,
   Bildtexte und Dialoge stammen aus dem bearbeiteten Skript. Unbekannte Sprecher,
   fehlerhafte Nummerierungen oder widersprüchliche Kachelzahlen führen zu einer
   verständlichen Fehlermeldung. Es wird immer eine neue Geschichte angelegt.
8. Im normalen Storyeditor prüfen und **Comic erzeugen** klicken. Den Autor
   übernimmt das Buchformular als änderbaren Vorschlag, sofern dort noch keine
   eigenen Buchangaben gespeichert wurden.

Ein aktiver Skriptauftrag wird nach erneutem Öffnen des Quellenbereichs im selben
Browser weiter angezeigt. Es wird dabei kein neuer Auftrag gestartet. Bei einem
Fehler kann erneut **Comic-Skript lokal erstellen** gewählt werden.

## Weitere Quellen aufnehmen

**Neue Quelle** wählen. Titel, Art (Buch, Film oder eigene Vorlage), Urheber,
konkrete Ausgabe/Fassung, Quellenadresse, Absatzländer, Rechtehinweis und eine
Textgrundlage eintragen. Danach **Quelle speichern** klicken. Bestehende Einträge
lassen sich unter demselben Namen bearbeiten und speichern. Der Katalog liegt
in der Datenbank des Comic-Automaten und bleibt bei Container-Neustarts erhalten.
Ein gestarteter Skriptauftrag erhält einen eigenen unveränderlichen Snapshot
seiner Quelle; spätere Katalogänderungen betreffen erst neue Aufträge.

Die Textgrundlage darf bis zu 16.000 Zeichen umfassen. Für längere Werke eine
saubere Inhaltszusammenfassung oder den gewünschten Ausschnitt verwenden.
Quellenadressen dienen als Nachweis: Es gibt keinen automatischen Download,
keine Suche nach Volltexten und keine Filmtranskription. Der Generator kennt nur
die übergebene Grundlage und seine lokalen Modellkenntnisse.

## Skriptformat

Die Struktur folgt [Comic_Story_Eingabeformat.md](Comic_Story_Eingabeformat.md).
Der Quellenbereich liest die nummerierten Kacheln direkt ein. Das gewöhnliche
Feld **Geschichte / Artikel** nutzt weiterhin die Artikelanalyse; dort wird
kein automatischer Import dieser Struktur zugesichert.

Wichtige Felder:

- Kopf: `TITEL`, `AUTOR`, `KACHELANZAHL`, `BILDSTIL`, `STIMMUNG UND FARBWELT`.
- `FIGUREN`: pro Figur `Name`, `Aussehen`, `Kleidung` und optional
  `Persönlichkeit und Vorgeschichte`.
- `KACHEL 1: Titel`, dann fortlaufend 2, 3 usw.
- Pro Kachel `Ort und Zeit`, `Sichtbare Figuren`, `Bildbeschreibung`,
  `Erzählertext`, optionale `Dialog 1` usw. und `Kontinuität / Änderung`.
- Pro Dialog `Sprecher`, `Sprechweise`, `Sichtbarkeit`, `Text`.

Figurennamen müssen eindeutig sein und dürfen keine Kommas, Doppelpunkte oder
Zeilenumbrüche enthalten. Sichtbare Figuren werden durch Kommas getrennt.
`Sichtbare Figuren` bestimmt, wer im Bild erscheint; ein zugeordneter Sprecher
kann auch außerhalb des Bildes sprechen. `Sprechweise` kennt `normal`,
`schreiend` und `flüsternd`. Regieangaben werden nicht in die Blasentexte kopiert.
Gesinnung bleibt im erzeugten Skript zunächst nicht festgelegt; im übernommenen
Storyeditor kann sie mit den vorhandenen RPG-Optionen geändert werden. Das freie
Erzählerfeld beschreibt die Absicht, konfiguriert aber keine sichtbare Erzählerfigur.

Der gewählte Stil aus dem Quellenformular bleibt der technische Renderstil.
Die Beschreibung unter `BILDSTIL` und die Farbwelt ergänzen die Bildkomposition.
Freie Buchseitenlayouts werden durch das Skript nicht automatisch gesetzt.

## Rechtehinweise statt automatischer Freigabe

Ein alter Titel oder ein alter Film ist nicht automatisch in allen Ländern und
in jeder Ausgabe frei. Der Katalog dokumentiert Angaben, er trifft keine
rechtliche Entscheidung. Verwendete Texte, Übersetzungen, Zeichnungen,
Filmfassungen und vorgesehene Absatzländer getrennt prüfen. Die mitgelieferten
Zusammenfassungen enthalten keine übernommenen modernen Übersetzungstexte.

Für Deutschland regeln unter anderem §§ 64–65 UrhG die Schutzdauer; bei Filmen
ist nicht allein das Veröffentlichungsjahr entscheidend. Siehe
[Urheberrechtsgesetz](https://www.gesetze-im-internet.de/urhg/BJNR012730965.html).
Der französische Verlegerverband nennt für **Le Petit Prince** den Eintritt in
die Gemeinfreiheit in Frankreich am 1. Januar 2033:
[Durée des droits d’auteur](https://www.sne.fr/editeur-et-auteur/duree-des-droits-dauteurs/).
Der Katalogeintrag ist deshalb ausdrücklich keine weltweite Freigabe.

## API

Alle API-Aufrufe verwenden den konfigurierten Bearer-Token wie der bestehende
Automat. Die Oberfläche übernimmt diese Aufrufe.

- `GET /sources`: Quellenkatalog.
- `POST /sources`: Quelle anlegen oder mit vorhandener `id` aktualisieren.
- `POST /source-tasks`: Skriptauftrag mit `source_id`, `style`, `count`, optional
  `author` und `instructions` erstellen. Noch keine Bilder.
- `GET /source-tasks/<id>`: Fortschritt, nach Abschluss auch `script` und
  `source_issues`.
- `PUT /source-tasks/<id>/script`: bearbeitetes Skript als `{"script":"…"}` sichern.
- `POST /source-tasks/<id>/adopt`: Skript als `{"script":"…"}` in eine neue
  bearbeitbare Geschichte übernehmen. Kein Renderauftrag.

Quellenskriptaufträge sind Hilfsaufträge und erscheinen nicht zwischen den
Comic-Bildausgaben. Lokale LLM-Konfiguration und vorhandene Renderworkflows
bleiben unverändert. Es wird kein externer Modellanbieter angesprochen.

## Quellenpaket mit zehn Heldensagen

Zehn zusätzliche, einzeln auswählbare Vorlagen behandeln Mut, Treue, Ausdauer
und Versöhnung. [Übersicht und Import](../examples/comics/sources/README.md).
Die Textgrundlagen sind neu formuliert; die alten Stoffe und die jeweils
gewählten Ausschnitte sind mit Herkunft und Abgrenzung dokumentiert.

## Sprachprüfung

Geprüft werden die eigentlichen Nutztexte; technische JSON-Schlüssel, Figuren-IDs
und Kennungen wie `shout` sind keine fremdsprachigen Erzähltexte. Negative
Sprachurteile werden unabhängig gegengeprüft. Bei Ollama übernimmt diese
Gegenprüfung das konfigurierte Textmodell statt des Kritiker-Modells. Bestätigte
Befunde müssen vorhandene Textstellen wörtlich nennen. Erst dann wird übersetzt.
Deutsche Redewendungen, Stilfragen und erfundene Beanstandungen rechtfertigen
keine Übersetzung. Bleiben bestätigte fremdsprachige Texte bestehen, stoppt der
Auftrag weiterhin vor der Bilderzeugung. Die Entscheidungen stehen unter
`reports/*-language-decision-*.json` beim jeweiligen Auftrag.
