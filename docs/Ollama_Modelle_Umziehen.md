# Ollama-Modelle mit sudo ins Home verlagern

Der Umzug wurde am 25. Oktober 2026 erfolgreich ausgeführt und vom Nutzer bestätigt.
Das Skript bleibt für die Nachvollziehbarkeit des Ablaufs erhalten. Es startet weder Ollama noch Docker-Container und führt kein Backup aus.

## Ausführen

Der ursprüngliche manuelle Aufruf lautet:

```bash
sudo python3 -I /home/jee/docker/minimax-h3-dgx-spark/scripts/migrate_ollama_models.py
```

Das Passwort ausschließlich im lokalen Terminal eingeben. Den Lauf nach Möglichkeit
bis zum Abschluss durchlaufen lassen. Bei etwa 211 GiB Modellen dauern Kopieren und
die anschließende vollständige Prüfsummenprüfung entsprechend lange.

## Was der Lauf macht

1. Prüft Root-Rechte, Werkzeuge, Dienstbenutzer, Home-Durchgang und Backup-Konfiguration.
   Sind Docker-Container aktiv, bricht er ab; er stoppt sie nicht eigenständig.
2. Schreibt ein privates, dauerhaftes Journal unter `/var/lib/ollama-model-move/`.
3. Deaktiviert Ollamas Autostart und stoppt den Host-Dienst. Dadurch beginnt nach
   einem Stromausfall kein automatischer Modellzugriff auf eine halbfertige Kopie.
4. Prüft freien Platz für eine weitere vollständige Kopie und Reserve. Es wird
   nichts aus dem bisherigen Modellverzeichnis gelöscht.
5. Kopiert `/usr/share/ollama/.ollama/models/` mit rsync nach
   `/home/jee/models/ollama/`. Dateiinhalte, Rechte, Zeitstempel, Hardlinks, ACLs und
   erweiterte Attribute werden übernommen. Die Zielbesitzer werden bewusst auf
   `ollama:ollama` vereinheitlicht, damit auch bislang anders besessene Dateien für
   den Dienst lesbar sind. Es werden keine neuen ACL-Regeln eingerichtet.
6. Vergleicht Quelle und Ziel separat erneut mit Prüfsummen und Metadaten unter
   Berücksichtigung der beabsichtigten Zielbesitzer. Jede Abweichung stoppt den Ablauf.
7. Setzt das Modell-Hauptverzeichnis auf `ollama:ollama`, Modus `2770`. Der Dienst
   läuft weiter als `ollama`. `jee` ist auf diesem Gerät bereits Mitglied der
   Gruppe `ollama`; das Skript kontrolliert dies.
8. Prüft als Benutzer `ollama` mit Zusatzgruppe `jee`, ob sämtliche kopierten Dateien
   lesbar und die Verzeichnisse beschreibbar sind. Es startet dafür keinen Ollama-Server.
9. Schreibt einen neuen systemd-Drop-in und erhält den bestehenden `listen.conf`:

   ```ini
   [Service]
   Environment="OLLAMA_MODELS=/home/jee/models/ollama"
   SupplementaryGroups=jee
   ReadWritePaths=/home/jee/models/ollama
   UMask=0007
   ```

   Die zusätzliche Gruppe gilt nur für den Dienst, nicht als globale neue
   Gruppenmitgliedschaft des Kontos `ollama`. Sie ermöglicht den Durchgang durch
   das vorhandene `/home/jee` mit Modus 750. Sie gewährt dem Dienst damit auch den
   vorhandenen Zugriff der Gruppe `jee` auf andere entsprechend freigegebene
   Benutzerdateien; diese Berechtigung ist nicht auf den Modellordner beschränkt.
   Eigentümer und Modus des Home-Verzeichnisses selbst werden nicht verändert.
10. Entfernt den alten Modellpfad aus den zusätzlichen Quellen in
    `backup/docker-rsnapshot.json` sowie, falls schon installiert,
    `/etc/docker-rsnapshot.json`. Die Quelle `/home/jee` muss den neuen Ort bereits
    abdecken, sonst wird der Umzug abgebrochen. Programm und Bibliotheken unter
    `/usr/local` bleiben weiterhin zusätzliche Backup-Quellen.
11. Liest systemd mit `daemon-reload` neu ein und kontrolliert den wirksamen
    Modellpfad, die Zusatzgruppe sowie die unveränderte sonstige Dienstumgebung.
    Die API-Adresse und bestehende Listen-Konfiguration bleiben erhalten.

Bei Erfolg erscheint `FERTIG`. **Ollama bleibt gestoppt und sein Autostart deaktiviert.**
Alle Docker-Container bleiben gestoppt. Erst nach ausdrücklicher Entscheidung
werden Dienste oder Autostarts wieder freigegeben; das gehört nicht zu diesem Skript.
Die alte Modellkopie bleibt als Rückfallmöglichkeit erhalten und belegt weiterhin Platz.

## Fehler oder Stromausfall

Status und letzte Phase stehen hier:

```bash
sudo cat /var/lib/ollama-model-move/status.json
```

Ein Fehler startet nichts und löscht die Originalmodelle nicht. Bei einem
Stromausfall kann keine Abschlussmeldung mehr geschrieben werden; das Journal
bleibt mit der letzten dauerhaften Phase zurück. Nach Prüfung ausdrücklich fortsetzen:

```bash
sudo python3 -I /home/jee/docker/minimax-h3-dgx-spark/scripts/migrate_ollama_models.py --resume
```

`--resume` akzeptiert nur einen zu denselben Pfaden gehörenden, nicht abgeschlossenen
Lauf. Ein gefülltes Ziel ohne passendes Journal wird nicht überschrieben. Der
Prüfsummenvergleich verhindert, dass eine unvollständige oder falsche Datei allein
wegen Größe und Zeitstempel übernommen wird. Die Freiplatzprüfung bleibt auch bei
Fortsetzung konservativ und verlangt Reserve für eine weitere vollständige Kopie.
Ein bereits abgeschlossener Umzug wird nicht erneut ausgeführt.

Vor Änderungen gesicherte Konfigurationsdateien und ihre Originalpfade liegen unter
`/var/lib/ollama-model-move/originale/`. Beim ersten Schreiben werden sie einmalig
aufbewahrt und bei einer Fortsetzung nicht durch bereits geänderte Versionen ersetzt.

## Rückweg

Ollama gestoppt lassen. Anhand `originale/*/pfad.json` feststellen, welche Dateien
ursprünglich existierten. Vorhandene Originale aus `inhalt` mit den erhaltenen
Dateirechten zurückkopieren; einen vom Umzug neu angelegten Drop-in wieder entfernen.
Danach `systemctl daemon-reload` ausführen und den alten Modellpfad kontrollieren.
Das ursprüngliche Aktiv-/Autostart-Verhalten steht im Journal. Es wird nicht
selbständig wiederhergestellt. Neue Modelle oder Änderungen nach einem späteren
Start am neuen Ort sind in der alten Kopie nicht automatisch enthalten.

Das alte Archiv-Backup und dessen nur für den alten Modellpfad freigegebener
sudo-Helfer sind nach der Umstellung kein passendes neues Sicherungsverfahren.
Für neue Sicherungen den vorbereiteten rsnapshot-Ablauf verwenden.

## Prüfung des Skripts

Neun Tests mit simuliertem systemd und kleinen Testmodellen prüfen unter anderem:
Root-Anforderung, laufende Container als Abbruchgrund, erfolgreiche Umstellung ohne
Startbefehl, Abbruch vor Konfigurationsänderung bei Prüfsummenfehlern, unveränderte
Originaldaten, Fortsetzung eines unterbrochenen Laufs und Symlink-Sonderfälle.
Ein echter rsync-Test erkennt auch geänderte Inhalte bei gleicher Größe und gleichem
Zeitstempel. Es wurde kein produktiver Modellumzug und kein Recovery-Test ausgeführt.
