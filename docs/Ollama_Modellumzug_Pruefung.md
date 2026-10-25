# Prüfung vor dem Ollama-Modellumzug

Stand: 25. Oktober 2026. Es wurden keine Modelle verschoben, keine Ollama-
Konfiguration geändert und keine Dienste gestartet.

## Befund

- Bisheriger Modellpfad: `/usr/share/ollama/.ollama/models`, ungefähr 211 GiB.
- Vorgesehener neuer Pfad: `/home/jee/models/ollama`.
- Auf dem Home-Dateisystem sind beim Prüfen etwa 986 GiB frei. Eine zunächst
  zusätzliche vollständige Kopie ist damit möglich; während des Kopierens keine
  parallelen Modellinstallationen durchführen.
- In den vorhandenen Docker-Containern wurde kein Mount auf das Ollama-
  Modellverzeichnis gefunden. Die Comic-Automation verwendet
  `http://host.docker.internal:11434`; diese Schnittstelle ändert sich nicht.
- Der Host-Dienst läuft als Benutzer und Gruppe `ollama`. `ProtectHome=no` ist
  bereits gesetzt; zusätzliche ReadWritePaths-/InaccessiblePaths-Einschränkungen
  sind aktuell nicht gesetzt.
- Die Unit liegt unter `/etc/systemd/system/ollama.service`; der vorhandene
  Drop-in `ollama.service.d/listen.conf` muss erhalten bleiben.
- `/home/jee` hat Modus 750 und gehört `jee:jee`. Der Benutzer `ollama` besitzt
  deshalb noch keinen ausreichenden Durchgang zu den künftigen Modellen.
  Dass `jee` Mitglied der Gruppe `ollama` ist, löst diese umgekehrte Richtung nicht.
- Die für das Modellverzeichnis erforderlichen Besitzer-/Gruppenrechte und der
  Durchgang durch die übergeordneten Verzeichnisse müssen vor der Umschaltung
  als Benutzer `ollama` tatsächlich geprüft werden. Eine mögliche Einrichtung
  verwendet eine passende Dienst-Zusatzgruppe statt ACLs; deren Zugriffsumfang
  ist vor dem Setzen zu prüfen.
- Die vorbereitete rsnapshot-Konfiguration läuft als root. Sie kann anschließend
  auch geschützte Modelle unter `/home/jee` lesen; die gesonderte alte Modellquelle
  außerhalb von Home muss dann entfernt werden.

## Betroffene Dateien bei einer späteren Umstellung

1. Neuer eigener Drop-in für `OLLAMA_MODELS` und gegebenenfalls die Dienstgruppe;
   vorhandene Listen-/Netzwerk-Konfiguration nicht überschreiben.
2. `backup/docker-rsnapshot.json`: alten Modellpfad aus `additional_sources`
   entfernen; `/home/jee` umfasst den neuen Modellpfad bereits.
3. Falls bereits installiert, dieselbe Änderung in `/etc/docker-rsnapshot.json`.
4. Backup- und Wiederherstellungsdokumentation aktualisieren.

Die alten Archivskripte und deren eingeschränkter sudo-Helfer enthalten noch den
festen bisherigen Ollama-Pfad. Sie sind nicht für den neuen rsnapshot-Ablauf nötig
und dürfen nach einem Modellumzug nicht unverändert für neue Sicherungen verwendet
werden. Ebenso ist die Ollama-Programminstallation unter `/usr/local` vom Umzug der
Modell-Dateien zu unterscheiden; ihre Sicherung bleibt zusätzlich erforderlich.

## Sicherer späterer Ablauf

Ollama stoppen, vollständige Kopie anlegen, Dateiinhalte und Metadaten prüfen,
Berechtigungen als tatsächlicher Dienstbenutzer testen, Konfiguration umstellen
und systemd neu einlesen. Alte Modelldaten zunächst als Rückfallkopie behalten.
Es erfolgt kein automatischer Dienststart. Für nötige Root-Änderungen wird eine
lokal mit sudo ausführbare Einrichtungsdatei vorbereitet, kein Passwort im Chat.

Die vor dem Container-Stopp laufenden Container und ihre ursprünglichen Restart-
Policies stehen lokal unter
`/home/jee/docker-data/migrations/docker-zustand-vor-modellumzug.json`.
Die Datei enthält gerätespezifische Laufzeitdaten und wird nicht in Git veröffentlicht.
Diese Liste ist ein Nachweis und kein Auftrag für einen automatischen Wiederanlauf.

Die geprüfte Ausführungsdatei und der Ablauf stehen jetzt in
[Ollama_Modelle_Umziehen.md](Ollama_Modelle_Umziehen.md). Die Erstellung dieser Dateien
hat noch keine Modelle verschoben und keine Dienstkonfiguration geändert.

Nachtrag: Der spätere Umzug wurde vom Nutzer erfolgreich durchgeführt. Die obigen
Angaben dokumentieren die Vorprüfung; der neue Modellpfad ist inzwischen aktiv konfiguriert.
