# Comic gemeinsam an Bildern und Sprechblasen bearbeiten

In **3 · Bearbeiten** zeigt die Comicansicht alle exportierten Seiten. Über **Vorherige Seite**, **Nächste Seite** oder die Seitenauswahl lässt sich die gesamte Ausgabe ansehen.

**Sprechblasen positionieren** öffnet den gemeinsamen Editor. Die Kachelauswahl sowie **Vorherige** und **Nächste** führen durch alle Bilder der Geschichte, auch über die erste Zwölfergruppe hinaus.

- Blasen verschieben und vergrößern, ihre Schweifspitzen zuordnen sowie Dialog und Erzählertext ändern.
- Unter **Dieses Bild korrigieren** einen Wunsch für die aktuelle Kachel eintragen und **Nur dieses Bild neu erzeugen** anklicken. Der Auftrag zeichnet genau diese Kachel neu; alle anderen Zeichnungen werden übernommen. Die bearbeiteten Beschriftungen aller Kacheln bleiben erhalten. Nach Abschluss bleibt der Editor bei derselben Kachel.
- **Bearbeitungsstand speichern** sichert Blasen, Texte, Schutzbereiche, noch offene Korrekturwünsche und die aktuelle Kachel auf dem Server. Das funktioniert auch mit noch nicht fertig eingepassten Texten. Beim erneuten Öffnen derselben Ausgabe wird der Stand geladen. Dieser Schritt erzeugt weder Bilder noch einen neuen Comic.
- **Comic-Ausgabe speichern** erstellt aus dem geprüften Stand eine neue beschriftete Ausgabe. Die Originalzeichnungen bleiben erhalten. Bildkorrekturen haben bereits jeweils eine eigene neue Ausgabe erstellt; die vorherige Fassung bleibt verfügbar.

Ein gespeicherter Korrekturwunsch allein startet keine Generierung. Ein ausgeführter Bildauftrag speichert nach erfolgreichem Abschluss den Stand auch unter seiner neuen Ausgabe. Bei einem Fehler bleibt der zuvor gesicherte Stand unter der Ausgangsausgabe erhalten.

Arbeitsnotizen werden nicht in das herunterladbare Comic-Paket aufgenommen. Die Skriptvorarbeit und ihr Cron werden durch die Bildbearbeitung nicht aktiviert.

## Kurzen Korrekturwunsch präzisieren

Im gemeinsamen Editor genügt zunächst ein kurzer Wunsch, etwa: „Hänsel vollständig im verschlossenen Käfig, Gitter vor Gesicht und Körper. Gretel putzt davor, die Hexe überwacht sie.“

**Korrektur präzisieren** lässt das interne lokale Modell die bestehende Zeichnung und die Szenenbeschreibung auswerten. Es formuliert eine vollständige Bildanweisung mit räumlichen Beziehungen, sichtbaren Merkmalen, Personenanzahl, Kamera, Ausschlüssen und Erhaltungsregeln. Dabei entsteht noch kein Comicbild.

Die **Bildanweisung** ist editierbar. Erst **Mit dieser Bildanweisung neu erzeugen** startet eine neue Zeichnung. Der geprüfte Beschreibungstext wird dabei unverändert verwendet und nicht erneut vom Planungsmodell umgeschrieben. Auch eine direkt manuell bearbeitete Beschreibung kann so verwendet werden. Nach einer Änderung des kurzen Wunsches muss die Anweisung erneut präzisiert oder manuell angepasst werden.

Der Bearbeitungsstand speichert auch diese Bildanweisungen. Bei der älteren Einzelbildkorrektur führt **Korrektur im Editor präzisieren** zum passenden Bild. **Ganze Kachel direkt neu zeichnen** bezeichnet ausdrücklich den bisherigen direkten Ablauf.

Die Korrektur bleibt eine Neuzeichnung der gesamten Kachel. Präzise Formulierungen erhöhen die Steuerbarkeit, garantieren aber keine identischen Pixel oder fehlerfreien Details. Eine Bearbeitung ausschließlich innerhalb eines markierten Bereichs ist hier nicht implementiert.

## Veröffentlichungsziele als Standard speichern

Unter **4 · Veröffentlichen und exportieren → Meine Veröffentlichungsziele** lassen sich X-Profil, Substack-Profil beziehungsweise Publikationsadresse und Telegram-Kanal jederzeit eingeben und ändern. Nach einer Änderung wird der zugehörige Knopf **Als Standard speichern** aktiv. Jeder Wert wird unabhängig gespeichert und für kommende Veröffentlichungen aller Geschichten vorbelegt.

Für Telegram prüft **Als Standard speichern und prüfen** zugleich den Kanal und die Veröffentlichungsberechtigung des konfigurierten Bots. Dabei wird keine Nachricht gesendet. Bei X und Substack bleiben das tatsächlich angemeldete Konto und die abschließende Veröffentlichung im jeweiligen Dienst maßgeblich; die Profiladresse meldet keinen Benutzer an.

Die Felder in den Teilen-Dialogen sind ebenfalls editierbar und verwenden dieselben gespeicherten Standardwerte. Profiladressen und Kanäle sind nicht im Programm fest hinterlegt.
