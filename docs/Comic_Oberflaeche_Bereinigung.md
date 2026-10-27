# Bereinigung der vier Comic-Arbeitsbereiche

Stand: 27. Oktober 2026. Erste Umsetzung der fünf priorisierten Punkte aus dem Oberflächen-Audit.

## Rückkehrpunkt vor den Änderungen

- Git-Commit: `1a731e3`
- Git-Tag auf GitHub: `comic-vor-ui-bereinigung-2026-10-27`
- Der Tag sichert den Programm- und Dokumentationsstand. Laufzeitdaten, gespeicherte Figuren und erzeugte Ausgaben werden dadurch nicht zurückgesetzt oder gesichert.

Zum getrennten Prüfen des alten Codes kann später ein zusätzliches Arbeitsverzeichnis angelegt werden:

```bash
git worktree add ../comic-vor-ui-bereinigung comic-vor-ui-bereinigung-2026-10-27
```

Das startet keine Dienste und ändert keine Datenbank. Eine tatsächliche Rückkehr der laufenden Anwendung erfordert anschließend ein bewusstes Bereitstellen des alten Programmstands.

## 1. Ein gemeinsamer Editor

**Bilder und Texte bearbeiten** ist der zentrale Einstieg für Zeichnungen, Bildanweisungen, Erzählertext, Sprechblasen und Positionen. Der alte separate Bildkorrekturblock ist aus der Oberfläche entfernt. Die Korrektur-API bleibt für bestehende Aufträge erhalten. Die lange Textgrundlage ist in der Ausgabenansicht aufklappbar, damit sie den Comic nicht aus dem sichtbaren Bereich drängt.

## 2. Wirkungen eindeutig benennen

- **Skript sichern**: Storydefinition speichern.
- **Gestaltung sichern · ohne Bilderzeugung**: Stil, Layout und Besetzung speichern.
- **Quellenadaption zwischenspeichern**: noch nicht als neue Geschichte übernommenes Quellenskript sichern.
- **Bearbeitung später fortsetzen · Stand speichern**: Arbeitsstand pro Ausgabe sichern.
- **Neue fertige Ausgabe erstellen**: neue beschriftete Ausgabe auf vorhandenen Zeichnungen erzeugen.
- **Ganze Kachel mit dieser Anweisung neu zeichnen**: ausdrücklich eine vollständige Neuzeichnung der gewählten Kachel, keine Bereichsretusche.

## 3. Ausgaben und Versionsverlauf

Die Auswahlliste gruppiert Ausgaben nach gespeicherter Geschichte. Unterschiedliche Geschichten mit gleichem Titel werden nicht allein wegen des Titels zusammengefasst. Standardmäßig wird je Geschichte die neueste geladene Ausgabe gezeigt; eine bewusst ausgewählte ältere Fassung bleibt ebenfalls sichtbar.

**Frühere Fassungen anzeigen** blendet die übrigen geladenen Fassungen ein. **Vorherige Fassung**, **Original dieser Fassung** und **Neueste Ausgabe dieser Geschichte** bieten eindeutige Sprünge. Original bezeichnet die Wurzel der jeweiligen Bearbeitungskette, nicht notwendigerweise die erste jemals erzeugte Ausgabe einer Geschichte. Ein alter Vorfahr außerhalb der normalen Liste wird bei Bedarf lesend nachgeladen.

Der **Ausgabenverlauf** listet Änderungsart, Zeitpunkt und Kennung. Hauptansicht und Veröffentlichungsbereich weisen darauf hin, wenn eine ältere Fassung ausgewählt ist. Nichts wird automatisch auf die neueste Ausgabe umgeschaltet oder gelöscht.

Interne Textpräzisierungsaufträge werden bereits vor der Begrenzung der öffentlichen Auftragsliste ausgefiltert, damit sie ältere sichtbare Comic-Ausgaben nicht aus der Liste drängen.

## 4. Konkrete Prüfhinweise

Beschriftungs- und Ausrüstungswarnungen mit Kachelnummer erhalten **Dort bearbeiten**. Der Knopf öffnet den gemeinsamen Editor direkt bei dieser Kachel. Der Beschriftungshinweis erklärt, dass die Bilder erhalten sind; die konkrete Ursache steht unmittelbar daneben.

## 5. Veröffentlichung korrekt benennen

- **Für X vorbereiten** und **Für Substack vorbereiten** erzeugen keinen automatischen Post. Sie führen zu Beitragstext und Bildpaket; der Versand erfolgt im jeweiligen Dienst.
- **Telegram-Beitrag vorbereiten** öffnet den Prüfdialog. Erst **Auf Telegram veröffentlichen** sendet über den Bot.

## Umfang und Prüfung

Keine Geschichten, Figuren, Arbeitsstände oder Comicdateien wurden für diese Oberflächenbereinigung gelöscht. Die vier Bereiche bleiben bestehen. Die Kachelanzahl-Regel, Quellenverwaltung, Autorenfunktionen und Buch-Exportstruktur wurden in dieser ersten Runde nicht umgebaut.

Prüfung: Python-Tests, Browsertests mit API-Attrappen für Verlauf und direkte Kachelsprünge sowie bestehende Tests für 24-Kachel-Bearbeitung und Vier-Schritt-Workflow. Keine Modell- oder Bilderzeugung für die Bereinigung gestartet; nichts veröffentlicht.

### Zuletzt bearbeitete Geschichte wieder aufnehmen

Der Eingabebereich heißt jetzt „Eigener Text“. Neben „Neue Geschichte“ öffnet ein zusätzlicher Button die zuletzt in diesem Browser bearbeitete Geschichte; ihr Titel steht daneben. Eingaben in einer vorhandenen Geschichte und das Sichern merken deren ID. Reines Öffnen, Listenaktualisierungen und automatische Importe setzen diese Vormerkung nicht um. Beim erneuten Aufruf wird die vorgemerkte Geschichte bevorzugt geladen.

Ohne neue Bearbeitungsvormerkung wird die bisherige Browser-ID als „zuletzt geöffnet“ angeboten. Gelöschte IDs werden nicht angeboten. Vor dem Wechsel wird bei ungespeicherten Änderungen nachgefragt. Die Vormerkung speichert keine ungesicherten Textänderungen und gilt nicht browserübergreifend. Neue Texte deshalb weiterhin mit „Skript sichern“ speichern.

Geprüft mit dem Dashboard-Browsertest: Geschichte bearbeiten und sichern, leere neue Geschichte öffnen und anschließend die zuvor bearbeitete Geschichte samt Titel wieder aufrufen. Keine Modelle oder Bilder erzeugt.

### Erster Bereich: Auswertung bearbeiten und Skript gemeinsam neu planen

„Neue Geschichte“ steht zuerst in der blauen Eingabenavigation. Die frei anpassbare Kachelzahl steht neben „Gespeichertes Skript / Geschichte“. Der zusätzliche Einstieg „Auf dieser Geschichte aufbauen“ entfällt; Fortsetzungen bleiben unter „Fortsetzung / Serie“. „Geschichte löschen“ steht direkt neben der zentralen Skriptaktion. Die erweiterten Optionen werden nicht mehr angezeigt; Figuren und Referenzbilder bleiben in Schritt 2.

Die redaktionelle Auswertung wird mit der Geschichte beziehungsweise Quelle angezeigt. Grundfrage, Deutungsart, Kernaussage, Schlusswirkung, Belege und Handlungskette lassen sich bearbeiten. Die Buttons zum Laden, erneuten Übernehmen der Empfehlung und Herunterladen der Auswertung entfallen. Ohne hinterlegte Auswertung erscheint ein Hinweis auf die noch nötige redaktionelle Vorbereitung; es läuft keine automatische Ersatzanalyse.

Änderungen an Auswertung, Text oder Kachelzahl machen eine vollständige Neuplanung notwendig. „Skript sichern“ speichert diese Vorgaben, erstellt aber keine Szenen. „Skript neu erstellen“ verwendet den sichtbaren Ausgangstext, die bearbeitete Auswertung und die gewählte Kachelzahl. Vor dem Ersetzen vorhandener Szenen wird nachgefragt. Die Quellenanalyse im gemeinsamen Cache bleibt unverändert; die eigene Deutung wird separat in dieser Geschichte gespeichert. Bilder werden erst in Schritt 2 erzeugt. Fertige Ausgaben bleiben erhalten.

Nach Änderungen am Ausgangstext muss die vorhandene Auswertung geprüft und gegebenenfalls angepasst werden. Beim bewussten Neuplanen wird sie für den neuen Text übernommen. Eine vollkommen neue Geschichte ohne vorhandene Auswertung benötigt weiterhin eine redaktionelle Vorbereitung. Die Fortschrittsanzeige für die Szenenplanung bleibt bestehen.

Geprüft: 215 Python-Tests (einer übersprungen), Dashboard-Browsertest einschließlich editierter Auswertung, Speichern und Wiederöffnen, verbindlicher Kachelzahl, veraltetem Skript, bestätigter Neuplanung und unverändertem Quellen-Cache. Keine echten Modelle oder Comic-Generierung für diese Tests.

### Löschaktionen gehören zu „Bearbeiten“

Im ersten Schritt gibt es keinen Löschbutton mehr. Vorhandene Szenen werden über „Skript neu erstellen“ ersetzt. In Schritt 3 steht „Geschichte und alle Comics löschen“. Diese Aktion löscht weiterhin die gespeicherte Geschichte samt zugehörigen Ausgaben und fragt unter Nennung des Titels nach. Sie bezieht sich auf die Geschichte der ausgewählten Comic-Ausgabe, unabhängig vom in Schritt 1 geöffneten Skript. Bei laufenden zugehörigen Aufträgen ist sie gesperrt. „Diese Ausgabe löschen“ entfernt weiterhin nur die einzelne Ausgabe. Eine Funktion zum isolierten Löschen des Szenenplans wurde nicht eingeführt.

Der Wiederaufnahme-Button steht mit zusätzlichem Abstand in einer eigenen Zeile. Der Navigationseinstieg „Eigener Text“ wurde entfernt; die Texteingabe bleibt über „Neue Geschichte“ und die Auswahl gespeicherter Geschichten erreichbar.

### Figurenbilder vor der Comic-Generierung

In Schritt 2 gibt es „Figuren generieren“. Nach der Stilwahl erstellt der Button nacheinander nur die fehlenden Referenzbilder und sichert jedes fertige Bild in der gespeicherten Geschichte. Eine Statusanzeige nennt Figur und Fortschritt. Vorhandene Referenzen bleiben erhalten. Der Porträtmodus verwendet die bestehende Beschreibung direkt: keine neue Textmodell-Planung, keine Änderung von Name, Aussehenstext, Kleidung, Vorgeschichte oder Gesinnung. Comic-Kacheln werden dabei nicht erzeugt.

Währenddessen sind Stilwechsel, die Geschichtenauswahl in Schritt 2, die erneute Figuren- und Comic-Generierung sowie der dortige Speicherbutton gesperrt. Falls die Geschichte andernorts bearbeitet wird, überschreibt ein verspätetes Ergebnis diese Änderungen nicht. Nach der Vorschau kann „Comic generieren“ die gespeicherten Figurenbilder verwenden. Die Canvas-Vorlagen starten zugeklappt; die zusätzliche Bibliotheksvorschau entfällt.

Geprüft mit Figurenprofil-Tests und dem Dashboard-Browsertest: Porträt ohne Textmodell-Aufruf, unveränderte Profilfelder, getrennte Generierung, Sicherung und kein Comic-Auftrag beim Figurenbutton. Keine echten Modelle für den Test gestartet.

Sind bereits alle Figurenbilder vorhanden, bleibt der Figurenbutton aktiv und heißt „Figuren neu generieren“. Nach Bestätigung werden alle Referenzbilder dieser Geschichte im gewählten Stil neu gezeichnet und schrittweise gesichert. Profile, Bibliotheksfiguren und fertige Comics bleiben erhalten. Fehlen noch Bilder, erstellt „Figuren generieren“ weiterhin zunächst nur diese fehlenden Referenzen.

### Figurenauswahl: Bestätigung oben und Original erhalten

„Durch diese Figur ersetzen“ steht direkt neben der Auswahl oberhalb der Vorschaugalerie. Nach dem ersten Austausch erscheint „Ursprüngliche Figur“ zusätzlich als erster Eintrag und als Bildkachel. Damit lässt sich das ursprüngliche Profil mit Referenzbildern, Kleidungszuordnung und Bibliotheksverknüpfung wiederherstellen. Mehrere Wechsel behalten dieselbe erste Sicherung; zwischenzeitliche Ersatzprofile werden nicht als zusätzliche private Varianten gesammelt. Reguläre Bibliotheksfiguren bleiben weiterhin auswählbar. Die ursprüngliche Sicherung bleibt auch nach Speichern und erneutem Öffnen erhalten.

### Bibliotheksfoto automatisch als Comicfigur übernehmen

Beim Bestätigen eines Bibliothekstauschs muss ein Bildstil gewählt sein. Die Figurenauswahl schließt sich, das Profil wird übernommen und das erste Referenzfoto wird mit FLUX als Bildreferenz im gewählten Comicstil neu gezeichnet. Das Ergebnis ersetzt das Foto in der privaten Geschichtenkopie und wird automatisch gesichert. Die Bibliotheksdatei und die erste gesicherte Ursprungsfigur werden nicht verändert. Die Umwandlung erfindet keine neue Beschreibung, Biografie oder Gesinnung. Ohne Foto wird die bestehende Beschreibung verwendet.

Der Porträtknoten unterstützt dafür ein optionales Referenzbild; gespeicherte ComfyUI-Workflows werden nicht verändert. Auch „Figuren neu generieren“ nutzt vorhandene Bilder als Identitätsreferenz. Bei Fehlern bleibt das übernommene Profil gesichert; bei zwischenzeitlichen Bearbeitungen wird das Ergebnis nicht über die Änderungen geschrieben.

### Bearbeiten: Ausgabe oben, Werkzeuge darunter

Schritt 3 ist in zwei Bereiche gegliedert. Oben stehen Titel, Verarbeitungsanzeige, Seitenwechsel und Comicbild der ausgewählten Ausgabe. Direkt darunter folgen die Aktionen für diese Ausgabe einschließlich Einzel- und Gesamtlöschung sowie Auswahl und Fassungsverlauf.

Die Verarbeitungsanzeige zeigt die echten Auftragsphasen, eine Schrittliste, Gesamtzeit und Zeit im aktuellen Schritt. Bei vorhandenen Zählerdaten wird der Kachelfortschritt angezeigt. Laufende Aufträge werden in diesem Bereich alle 2,5 Sekunden abgefragt. Fehler bleiben als Unterbrechung sichtbar; eine fertige Ausgabe zeigt eine zugeklappte Abschlussanzeige. Zeitangaben sind Laufzeiten, keine Fertigstellungsprognosen.

Die Blöcke „Prüfhinweise“, „Andere Geschichte erzeugen“, „Optionales Feedback“ und „Automatische Erfahrungen“ sowie der doppelte Stil-/Kachelhinweis zur Verbesserung werden nicht mehr angezeigt. Die bisherige automatische Erfahrungsanzeige wird nicht mehr regelmäßig abgefragt. Gespeicherte Bewertungen und serverseitige Prüfungen bleiben erhalten; konkrete Beschriftungs- und Bildwarnungen mit direktem Sprung in den Editor bleiben sichtbar.

### Kachel direkt im Bild- und Texteditor vergrößern

„Bilder und Texte bearbeiten“ enthält eine Ansichtsauswahl: Einpassen, 150 %, 200 % oder 300 %. Die vergrößerte Kachel lässt sich im Bildbereich scrollen und weiterhin bearbeiten. Der Zoom ändert nur die Darstellung, weder die Bildausgabe noch Blasenkoordinaten oder den gespeicherten Bearbeitungsstand. Beim erneuten Öffnen startet die Ansicht mit „Einpassen“. Die separate Leseansicht bleibt für Lese- und Seitenreihenfolge verfügbar.
