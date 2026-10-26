# Skriptvorarbeit per Cron fortsetzen

Der Benutzer-Cron von `jee` prüft jede Minute, ob die bestehende Comic-Unterhaltung frei ist, und reiht dann einen Auftrag für höchstens vier weitere Skripte ein. Er schreibt keine Tastendrücke in `screen`. Stattdessen verwendet er den installierten offiziellen Befehl `codex queue --thread … --message …` mit einer festen Unterhaltungs-ID. Eine offene Screen-Anzeige derselben Unterhaltung kann weiter benutzt werden; der Trigger startet keine zweite Codex-Arbeitssitzung.

Es werden keine Bilder erzeugt. Figurenkontinuität, empfohlene Kachelzahl, deutsche Dialoge, Beschriftungsprüfung, Import als neue Geschichte und Fortschrittsdokumentation gehören zum Auftrag. Andere Punkte aus `todo.txt` gehören ausdrücklich nicht dazu. Die Skripte schreibt Codex selbst, kein lokales Ersatzmodell. Der Trigger ruft keine Modell-API mit eigenem Schlüssel auf; Codex verwendet die vorhandene Anmeldung und deren verfügbare Limits.

## Dateien und Zeitplan

- Programm: `scripts/comic_skript_cron.py`.
- Konfiguration: `/home/jee/docker-data/comic-skript-cron/config.json`.
- Auftragsstatus: `/home/jee/docker-data/comic-skript-cron/status.json`, erst nach der ersten Zustellung vorhanden.
- Lesbares Protokoll: `/home/jee/docker-data/comic-skript-cron/trigger.log`.
- Cron-Ausgabe und Fehlermeldungen: `/home/jee/docker-data/comic-skript-cron/cron.log`.
- Fortschritt: `docs/Comic_Skriptvorarbeit_Fortschritt.md` und `/home/jee/docker-data/comic-sinnanalyse-redaktion/skriptauftrag.json`.

Der Eintrag `* * * * *` läuft jede Minute in der lokalen Systemzeit. Bereits vorhandene fremde Cron-Einträge bleiben erhalten. Vor dem Ändern wird die bisherige Crontab im Konfigurationsverzeichnis aufbewahrt. Der alte auskommentierte `screen`-Job bleibt auskommentiert.

## Verhalten und Grenzen

Eine Sperrdatei verhindert gleichzeitige Trigger. Die Unterhaltungs-ID wird gegen Projektpfad und Archivstatus geprüft. Ein neuer Auftrag wird nur nach einem protokollierten abgeschlossenen Codex-Turn gesendet. Laufende, abgebrochene oder nicht eindeutig erkennbare Turns werden übersprungen.

Vor der Zustellung wird ein offener Auftrag gespeichert. Solange die Zahl fertiger Skripte danach nicht gestiegen ist, wird kein weiterer Auftrag eingereiht. Das verhindert auch nach Zeitüberschreitung, Stromausfall oder einer unklaren Zustellantwort blinde Wiederholungen. Nach einem Fehler oder ausgeschöpften Limit gegebenenfalls erst die Unterhaltung und den Status prüfen; es gibt keine unbegrenzte automatische Wiederholung.

Die Rückgabe des Queue-Befehls bestätigt nur die Einreihung, nicht die Fertigstellung von Skripten. Der Ablauf benötigt einen erreichbaren lokalen Codex-App-Server. Ob die tatsächlich aktive Unterhaltung unmittelbar weiterarbeitet, wird beim ersten produktiven Trigger sichtbar. Installation, Trockenprüfung und automatisierte Tests senden keinen Testauftrag. Während der Einrichtung wurde kein produktiver Queue-Auftrag ausgelöst.

Neue manuelle Anweisungen haben Vorrang. Bei einer Pause-Anweisung soll Codex den Cron mit `--disable` pausieren. Ist der gesamte Skriptauftrag fertig, sendet der Trigger nichts mehr.

## Prüfen und pausieren

Alle Befehle als Benutzer `jee`, nicht mit `sudo`, ausführen. Die Standardaktion prüft nur und sendet nichts:

```bash
python3 scripts/comic_skript_cron.py
```

Cron und Versand pausieren:

```bash
python3 scripts/comic_skript_cron.py --disable
```

Nach bewusster Freigabe wieder einrichten:

```bash
python3 scripts/comic_skript_cron.py --install
```

`--install` setzt die Konfiguration auf aktiv, installiert den Cron und startet keinen sofortigen Arbeitslauf. Ein eventuell bereits offener Auftrag wird dadurch nicht gelöscht. `--tick` ist die produktive Cron-Aktion und soll nicht zum unverbindlichen Test aufgerufen werden.

Nach einem unklaren Zustellversuch den Status nicht blind löschen: zunächst sicherstellen, dass keine Nachricht mehr offen ist. Konfiguration, Zustellstatus und Protokolle liegen im Home-Verzeichnis und werden mitgesichert. Bei Wiederherstellung auf einem anderen Rechner die gespeicherte Unterhaltungs-ID und Codex-Zustandsdatei prüfen; niemals automatisch `--last` als Ersatz verwenden.

Offizielle Dokumentation: [Codex CLI – Queue](https://developers.openai.com/codex/cli/reference#codex-queue).
