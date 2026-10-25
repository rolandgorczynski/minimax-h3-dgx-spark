# Backup abschließen und alte Kopien manuell bereinigen

Die Skripte sind vorbereitet, aber nicht mit Root-Rechten auf den echten Daten
ausgeführt. Sie starten keine Anwendungsdienste und keinen sofortigen Backup-Lauf.
Der Abschluss aktiviert ausdrücklich den zukünftigen Wochen-Cronjob.

## 1. Abschluss und Einrichtung zusammen ausführen

Manuell ausführen:

```bash
sudo python3 -I /home/jee/docker/minimax-h3-dgx-spark/scripts/finish_docker_backup_setup.py
```

Das Skript prüft Journal, Laufwerks-UUID und passenden jüngsten Snapshot. Nur wenn
`phase: fertig`, `verified: true` und der Snapshot zum selben Lauf gehören, installiert
es das Update für vollständiges `/etc` und die getrennte manuelle Inhaltsprüfung.
Danach richtet es den Root-Cronjob für Sonntag 03:00 Uhr ein. Bestehende andere
Cronjobs bleiben erhalten. Die Prüfsummenprüfung erhält keinen eigenen Zeitplan.

Bei einem unvollständigen oder fehlgeschlagenen Backup hält es vor der Einrichtung
an und gibt die vorhandene Fehlermeldung aus. Es löscht oder beschönigt kein Journal
und startet kein neues Backup als vermeintliche Reparatur. Dann die Ausgabe prüfen.
Bei dem bekannten gescheiterten Quellenvergleich zuerst das Update aus
`scripts/update_docker_rsnapshot.py` mit sudo installieren und anschließend
`sudo /usr/local/sbin/docker-rsnapshot-weekly --resume` ausdrücklich ausführen. Dieser aktualisiert den vorhandenen Stand und
prüft ihn neu. Erst danach das Abschluss-Skript erneut aufrufen.
Ohne diese ausdrückliche Fortsetzung bleiben die Dienste in ihrem jetzigen Zustand.

## 2. Bereinigung zuerst nur anzeigen

Manuell ausführen:

```bash
sudo python3 -I /home/jee/docker/minimax-h3-dgx-spark/scripts/cleanup_old_comic_data.py --plan
```

Ohne Argumente gilt ebenfalls die reine Planung. Vorgesehen sind ausschließlich:

- das alte Volume `comic-automation_comic-automation-data`;
- das alte Volume `linux-open-source-games_updater_state`;
- die alte Modellkopie `/usr/share/ollama/.ollama/models`;
- die überholte sudoers-Datei `/etc/sudoers.d/comic-backup-ollama` und ihr Helfer
  `/usr/local/sbin/comic-backup-ollama`, soweit unverändert wiedererkannt.

Die neuen Datenverzeichnisse müssen existieren und im erfolgreich dokumentierten
Snapshot liegen. Der dokumentierte Modellumzug muss abgeschlossen sein, das Backup
muss danach begonnen haben. Journal und Snapshot müssen zusammenpassen; die richtige
Backup-Platte muss eingehängt sein. Die alten Volumes dürfen von keinem vorhandenen
Container referenziert werden, auch nicht von gestoppten. Die neuen Bind-Mounts
müssen eingerichtet und deren Container bereits gestoppt sein. Auch Ollama muss
bereits gestoppt und auf den neuen Modellpfad konfiguriert sein. Ein noch eingebundener
alter Modellpfad oder ein verschachtelter Mount verhindert die Bereinigung.

Das ist eine Prüfung der dokumentierten Migration und Sicherungsvoraussetzungen,
kein zusätzlicher vollständiger Inhaltsvergleich. Die optionale Prüfsummenprüfung
bleibt separat verfügbar. Die Bereinigung führt keinen Recovery-Test durch.

## 3. Nur bei eigener Freigabe endgültig löschen

Manuell ausführen:

```bash
sudo python3 -I /home/jee/docker/minimax-h3-dgx-spark/scripts/cleanup_old_comic_data.py --delete
```

`--delete` löscht die zuvor aufgeführten alten Kopien endgültig. Die alten Volumes
werden einzeln ohne `--force` entfernt. Es gibt kein `prune` und keine pauschale
Löschung unter `/mnt/backup` oder `/var/lib/docker`.

Behalten werden insbesondere:

- `/home/jee/models/ollama` und `/home/jee/docker-data/...`;
- alle rsnapshot-Stände und andere Dateien auf `/mnt/backup`, einschließlich `DATA`;
- der lokale Docker-Exportcache für die Wiederverwendung beim nächsten Backup;
- Journale, Logs und Originalkopien der Konfigurationen.

Eine fremd veränderte alte sudo-Regel bzw. ein veränderter Helfer wird nicht entfernt,
sondern zur manuellen Prüfung gemeldet. Unverändert erkannte Dateien werden vor der
Entfernung privat unter `/var/lib/docker-offline-backup/alte-sudo-regel/` aufbewahrt.
Der Bereinigungsstatus steht in `/var/lib/docker-offline-backup/bereinigung.json`.

Alle Skripte verwenden das gemeinsame Lock. Bei gleichzeitigem Backup oder laufender
Inhaltsprüfung erfolgt kein paralleler Abschluss-/Bereinigungslauf. Ein Abbruch beim
Löschen kann einen teilweise bereinigten Zustand hinterlassen; der Status nennt die
bereits entfernten Elemente. Es wird kein automatischer Dienststart ausgeführt.

Alte Archiv-Skriptdateien im Projekt und historische Dokumentation bleiben erhalten.
Die bereinigten alten Datenpfade sind anschließend keine nutzbaren Rückfallkopien
mehr. Für neue Sicherungen ausschließlich den neuen rsnapshot-Ablauf verwenden.

## Tests

Acht Tests verwenden nur temporäre Testdateien, simulierte Docker-/systemd-Antworten
und Test-Snapshots. Geprüft wurden Fehlerstatus vor Einrichtung, zusammengehöriger
Wochenstand, reine Planung ohne Löschung, fehlende neue Daten im Snapshot, referenzierte
Volumes, eingebundene alte Modelle und die ausschließlich gezielte Entfernung unter
Erhalt von neuen Daten, Snapshot und Exportcache.
