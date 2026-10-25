# Wöchentliche Offline-Sicherung mit rsnapshot

Stand: 25. Oktober 2026. Die inkrementelle Fortsetzung der ersten Sicherung wurde
vom Nutzer als erfolgreich bestätigt. Die hier beschriebene neue
Fassung trennt Backup und manuelle Inhaltsprüfung. Ihre Installation startet keinen
Zeitplan und keine Dienste. Kein Recovery-Test wurde durchgeführt.
Dieser Ablauf ersetzt für neue Sicherungen das bisherige Comic-Archivverfahren.

## Ziel und Umfang

Ein Root-Cronjob führt ein Steuerskript aus. Es stoppt die betroffenen Dienste,
sichert sie mit rsnapshot, prüft Größe, Zeitstempel und Metadaten und startet ausschließlich die zuvor
laufenden Dienste. Bei einem Fehler bleiben die betroffenen Dienste gestoppt.
Eine bereits vor Beginn ausgeschaltete Comic-Automation oder ComfyUI bleibt ausgeschaltet.

Erfasst werden alle vorhandenen Container mit Compose-Projektverzeichnis oder
Compose-Konfigurationsdateien unter `/home/jee/docker`. Die Zuordnung erfolgt anhand
der Docker-Labels; der Containername allein genügt nicht. Nicht mit Compose erstellte
Container und Host-Dienste werden dadurch nicht automatisch erfasst.

Die Vorbereitung enthält:

- das vollständige `/home/jee`, einschließlich Konfiguration, Caches und Modellen;
- das vollständige `/etc` als zusätzliche Nachschlage- und Wiederherstellungskopie;
- zusätzliche Bind-Mounts und lokale benannte Volumes der erfassten Container;
- Ollama als zusätzlichen Host-Dienst, mit Modellen, Programmdateien und systemd-Unit;
- Docker-Abbilder sowie exportierte Container-Dateisysteme für Änderungen in deren
  beschreibbarer Schicht; eingebundene Volumes werden separat kopiert;
- ursprüngliche Dienstzustände, Docker- und Volume-Metadaten sowie die Steuerkonfiguration.

Die Konfiguration enthält absichtlich keine bisherigen globalen Cache-Ausschlüsse.
Externe Volume-Treiber, mit Optionen eingehängte Volumes und gleichzeitig schreibende
Container außerhalb des Umfangs führen zum Abbruch vor dem Stoppen. Weitere Host-Dienste,
andere Benutzerprozesse und entfernte Datenbanken müssen bei Bedarf ausdrücklich
berücksichtigt werden. Ein Home-Verzeichnis kann währenddessen durch die Anmeldung
oder andere Programme verändert werden: Die abschließende Prüfung bricht bei
erkennbaren Größen-, Zeitstempel- oder Metadatenabweichungen ab. Eine Änderung mit
gleicher Größe und gleichem Zeitstempel erfordert die gesonderte Inhaltsprüfung. Für die geplante Ausführung deshalb
auch unabhängige Schreibzugriffe auf die übrigen Sicherungsquellen vermeiden.
Das gesamte `.codex`-Verzeichnis und die ausdrücklich aufgeführten Browser-Caches
sind nur von der strengen Abschlussprüfung ausgenommen; sie werden weiterhin kopiert.
Für laufende Codex-Datenbanken ist damit keine konsistente Wiederherstellung zugesagt.

System-Sockets und tmpfs sind keine dauerhaft wiederherzustellenden Anwendungsdaten.
Symlinks werden als Symlinks erhalten; externe Symlink-Ziele außerhalb der erfassten
Quellen müssen bei Bedarf zusätzlich in `additional_sources` eingetragen werden.
Es handelt sich um eine Datensicherung mit Wiederaufbauanleitung, kein vollständiges
bootfähiges Abbild des Betriebssystems.

## Umgestellte Datenverzeichnisse

Am 25. Oktober 2026 wurden die beiden bisher eingebundenen benannten Volumes
bei gestoppten Diensten in Bind-Mounts überführt:

| Dienst | Neuer Hostpfad | Mount im Container |
| --- | --- | --- |
| Comic-Automation | `/home/jee/docker-data/comic-automation` | `/data` |
| Spiele-Updater | `/home/jee/docker-data/games-updater` | `/state` |

Dateiinhalte wurden per SHA-256 sowie Eigentümer, Rechte, Zeitstempel und erweiterte
Attribute einschließlich vorhandener ACLs geprüft. 754 Dateien der Comic-Automation
und 8.895 Dateien des Spiele-Updaters wurden übernommen. Die Container wurden
anschließend ausschließlich erstellt, nicht gestartet. Compose verhindert mit
`create_host_path: false` die versehentliche Verwendung leerer Ersatzverzeichnisse.

Die alten Volumes `comic-automation_comic-automation-data` und
`linux-open-source-games_updater_state` bleiben unbenutzt als Rückfallkopien erhalten.
Kein `docker volume prune` ausführen, solange sie benötigt werden. Ein Rückweg besteht
darin, bei weiterhin gestoppten Containern die alten Volume-Mounts wieder in Compose
zu setzen und die Container ohne Start neu zu erstellen. Nach späteren Änderungen
in den neuen Verzeichnissen wären die alten Kopien entsprechend veraltet.

Beide neuen Datenverzeichnisse sind durch die Quelle `/home/jee` bereits abgedeckt.
Weitere künftig angelegte Docker-Volumes nimmt das Steuerskript weiterhin automatisch
zusätzlich auf. Die folgenden allgemeinen Volume-Wiederherstellungsschritte gelten
für solche Volumes bzw. frühere Sicherungen. Ollama wurde nicht verlagert und bleibt
als zusätzliche Quelle außerhalb von Home konfiguriert.

## Dateien

| Projektdatei | Aufgabe / Installationsziel |
| --- | --- |
| `scripts/docker_rsnapshot_weekly.py` | Steuerskript → `/usr/local/sbin/docker-rsnapshot-weekly` |
| `backup/docker-rsnapshot.json` | Umfang und Laufwerkskennung → `/etc/docker-rsnapshot.json` |
| `backup/rsnapshot-docker.conf` | rsnapshot-Basis → `/etc/rsnapshot.conf` |
| `backup/root-crontab.example` | Beispiel für die Root-Crontab; wird nicht automatisch installiert |
| `scripts/install_docker_rsnapshot.sh` | Einmalige Installation mit root-eigenen Dateien |

Vorhandene `/etc/rsnapshot.conf` wird bei der Installation unter einem Dateinamen
mit `vor-docker-offline` und Zeitstempel aufbewahrt. Bereits vorhandene neue
Steuerdateien werden vom Installer nicht überschrieben. Für spätere Änderungen
root-eigene Dateien bewusst aktualisieren und vorher sichern.

Die neue `/etc/rsnapshot.conf` ist eine Basis ohne statische `backup`-Zeilen.
Das Steuerskript ergänzt die tatsächlich benötigten Quellen in einer privaten
Laufkonfiguration unter `/var/lib/docker-offline-backup/rsnapshot.conf`.
Deshalb ausschließlich den Wrapper verwenden, nicht direkt `rsnapshot weekly`.

## Einmalige Installation und lesende Prüfung

```bash
sudo bash /home/jee/docker/minimax-h3-dgx-spark/scripts/install_docker_rsnapshot.sh
sudo /usr/local/sbin/docker-rsnapshot-weekly --plan
```

`--plan` verändert keine Dateien, stoppt und startet nichts. Für das Lesen aller
Volume-Verzeichnisse sind auch bei dieser Prüfung Root-Rechte erforderlich.
Die alte eingeschränkte sudo-Regel `comic-backup-ollama` wird vom neuen Verfahren
nicht benötigt: Der spätere Cronjob läuft bereits als root.

Voraussetzungen sind Docker, Python 3, rsnapshot, rsync mit ACL-/xattr-Unterstützung
sowie systemd. Die bereitgestellte Laufwerkskennung ist die aktuell ausgelesene UUID
`43610968-0243-4436-a150-276c261036bc` des unter `/mnt/backup` eingehängten ext4-Laufwerks.
Bei Austausch des Laufwerks muss diese Einstellung bewusst angepasst werden.

Die bisherigen auskommentierten Einträge in `/etc/cron.d/rsnapshot` bleiben deaktiviert.
Ebenso keine zusätzlichen täglichen rsnapshot-Aufrufe oder parallele Modellinstallationen
aktivieren. Die private Konfiguration enthält keine Hooks, die Dienste zusätzlich starten.

## Vorgesehener Zeitplan — noch nicht aktiviert

Nach ausdrücklicher Freigabe in `sudo crontab -e` aufnehmen:

```cron
0 3 * * 0 /usr/local/sbin/docker-rsnapshot-weekly --run >> /var/log/docker-offline-backup.log 2>&1
```

Sonntag um 03:00 Uhr in der lokalen Systemzeitzone. Eine Root-Crontab enthält kein
zusätzliches `root`-Feld. Der erstmalige manuelle Lauf wäre:

```bash
sudo /usr/local/sbin/docker-rsnapshot-weekly --run
```

Diese Anleitung und die Installation führen diesen Befehl nicht aus.

## Ablauf und Fehlerverhalten

1. Exklusives Lock und Journal prüfen. Ein nicht abgeschlossener vorheriger Lauf
   blockiert die nächste Ausführung, ohne Dienste zu verändern.
2. Mountpunkt und UUID, Quellen, Volume-Typen und Dienstzustände prüfen. Vor dem
   ersten Snapshot den Platzbedarf für Quellen, Docker-Exporte und deren Kopie
   konservativ schätzen; mindestens 10 GiB Reserve vorsehen. Auch der lokale
   Export-Zwischenspeicher benötigt Platz. Bei Folgeläufen ist die Reserve eine
   Untergrenze, keine Vorhersage der Größe künftiger Änderungen.
3. Ursprüngliche laufende und gestoppte Container, Restart-Policies sowie aktive
   Host-Dienste und deren Autostart-Zustände dauerhaft in `status.json` speichern.
4. Docker-Restart-Policies vorübergehend auf `no` setzen und aktivierte Ollama-
   Autostarts vorübergehend deaktivieren. Geordnet stoppen und Stillstand prüfen.
5. Docker-Abbilder und Container-Dateisysteme exportieren. Unveränderte Abbilder
   wiederverwenden; identische Dateisystemexporte behalten ihren alten Zeitstempel.
6. `rsnapshot sync` in `.sync` schreiben. Größe und Zeitstempel bestimmen, welche
   Dateien neu kopiert werden. Kein zusätzlicher vollständiger Inhaltsvergleich.
7. Bei weiterhin gestoppten Diensten Quelle und Kopie mit einem separaten
   `rsync --dry-run` ohne `--checksum` vergleichen: Größe, Zeitstempel, Eigentümer,
   Rechte, Symlinks, ACLs und erweiterte Attribute. Erkannte Abweichungen und
   Fehler verhindern den Neustart. Inhaltsänderungen mit gleicher Größe und
   gleichem Zeitstempel werden hier bewusst nicht zusätzlich erkannt.
8. Erst bei erfolgreicher Prüfung `weekly` rotieren und Schreibvorgänge flushen.
   Danach ursprüngliche Autostart-Einstellungen wiederherstellen und ausschließlich
   vorher laufende Dienste starten. Docker-Prozesszustände prüfen; das ist keine
   vollständige fachliche Funktionsprüfung jeder Anwendung.
9. Scheitert der Wiederanlauf teilweise, versucht das Skript die betroffenen Dienste
   erneut zu stoppen. Ein dabei ebenfalls auftretender Fehler wird ausdrücklich gemeldet.

Es gibt keinen bedingungslosen Neustart in einem `finally`-Block. Fehlermeldungen
gehen an stderr/stdout des Cronjobs und ins Statusjournal; ein externer Telegram-
oder E-Mail-Versand ist nicht eingerichtet. Der Rückgabecode ist bei Fehlern ungleich null.
Cron-Mail benötigt einen lokal eingerichteten Maildienst.

## Aufbewahrung und inkrementelle Speicherung

Ziel ist ausschließlich `/mnt/backup/docker-offline/`; andere vorhandene Verzeichnisse
auf `/mnt/backup`, insbesondere `DATA`, werden nicht übernommen, gelöscht oder rotiert.

```text
/mnt/backup/docker-offline/
    .sync/          # Arbeitsstand während der Übertragung
    weekly.0/       # letzter erfolgreich eingeordneter Stand
    weekly.1/       # vorherige Woche
    ...
    weekly.7/       # ältester der acht Wochenstände
```

`sync_first 1` trennt das Kopieren von der Rotation. Acht Wochenstände werden behalten.
Die eigentliche Ausführungsfrequenz bestimmt Cron, nicht der Name `weekly`.
Unveränderte Dateien teilen sich Speicher über Hardlinks. Geänderte große Dateien
benötigen in der Regel Platz für eine neue Dateiversion; dies ist keine blockweise
Deduplizierung. Das reguläre Backup liest nicht nachträglich alle Modelldateien
für einen vollständigen Inhaltsvergleich. Nur der separat gestartete manuelle
Prüfsummenjob liest Originale und Snapshot vollständig. Interne Hashes der lokalen
Docker-Exporte bleiben für deren Wiederverwendung bestehen; dies ist kein
vollständiger Inhaltsvergleich aller Home-Dateien.

Die lokalen Exportdateien unter `/var/lib/docker-offline-backup/export` belegen
zusätzlich Platz auf dem Host. Sie sind die Quelle für rsnapshot und kein zweiter
unabhängiger Backup-Datenträger. Der erste Container-Dateisystemexport erfolgt im
Stillstand und kann entsprechend dauern. Ein identischer Export wird nicht unnötig
als geänderte Datei in einen neuen Snapshot übernommen.

Die Snapshots enthalten Geheimnisse, SSH-Schlüssel und Tokens. Neue Snapshot- und
Statusverzeichnisse werden privat angelegt. Sie dürfen nicht öffentlich freigegeben werden.

## Abbruch, Fehler und Stromausfall

Ein SIGTERM oder Strg+C protokolliert den Abbruch und startet nichts. Bei SIGKILL
oder Stromausfall kann keine Fehlerbehandlung mehr laufen. Deshalb bleibt das vor
Änderungen geschriebene Journal bestehen. Nach Wiederkehr des Stroms blockiert es
den nächsten Cronlauf. Vor der eigentlichen Sicherung deaktivierte Autostarts
bleiben deaktiviert. Ein Stromausfall mitten in der Stoppphase kann bereits
teilweise geänderte Zustände hinterlassen; das Journal beschreibt den Ausgangszustand.

Prüfen:

```bash
sudo cat /var/lib/docker-offline-backup/status.json
sudo tail -n 80 /var/log/docker-offline-backup.log
docker ps -a
systemctl status ollama
```

Nicht einfach `docker compose up -d` ausführen: Das könnte auch vorher gestoppte
Container starten. Auch das Journal nicht ungeprüft löschen. Bei einem Fehler in
der Stoppphase zuerst sicherstellen, dass tatsächlich alle betroffenen Dienste
stillstehen. Root-Statusdateien enthalten genaue IDs und ursprüngliche Restart-Policies.

Nach Klärung des Fehlers und bewusster Entscheidung zum erneuten Sicherungsversuch:

1. Journal als Fehlernachweis unter einem anderen Namen aufbewahren und dadurch
   den neuen Lauf ausdrücklich freigeben. Keinen schon vorhandenen Nachweis überschreiben.
2. Mit allen betroffenen Diensten weiterhin gestoppt erneut `--run` ausführen.
   Ein noch vorhandenes `.sync` kann durch rsnapshot/rsync aktualisiert werden;
   es ist vor erfolgreicher Prüfung kein fertiger Wochenstand.
3. Der neue Lauf findet die Dienste als gestoppt vor und startet sie deshalb nicht
   automatisch. Wenn die Sicherung erfolgreich geprüft wurde, kann der ursprüngliche
   Zustand anhand des aufbewahrten ersten Journals manuell wiederhergestellt werden.
   Dazu gehören sowohl Autostart-Regeln als auch der aktive Zustand.

Das Skript nimmt nach einem Fehler keine selbständige Reparatur und keinen
selbständigen Wiederanlauf vor. Das alte Archivverfahren wird nicht parallel ausgeführt.

## Wiederherstellung — Anleitung, kein ausgeführter Test

1. Einen erfolgreich geprüften `weekly.N` auswählen. Ein `.sync`-Verzeichnis ist kein
   freigegebener Stand. Für einen neuen Host kompatibles ARM64-Linux, Docker Compose,
   NVIDIA-Treiber/Container-Runtime und bei Bedarf Python/systemd bereitstellen.
2. Im Snapshot liegen die Daten mit ihren ursprünglichen absoluten Pfaden unter
   `localhost/`, etwa `localhost/home/jee/` und
   `localhost/home/jee/models/ollama/`. Die Metadatenprüfung erfolgte zum Sicherungszeitpunkt;
   spätere Datenträgerfehler werden dadurch nicht grundsätzlich ausgeschlossen.
3. Das Zielsystem stilllegen. Ausgewählte Verzeichnisse mit Root-Rechten und
   `rsync -aHAX --numeric-ids` in leere Zielverzeichnisse zurückkopieren. Bestehende
   produktive Verzeichnisse nicht ungeprüft überschreiben. Eigentümer-IDs und Rechte erhalten.
4. Unter `localhost/var/lib/docker-offline-backup/export/` stehen `containers.json`,
   `volumes.json`, `dienstzustand.json`, Einstellungen, Steuerskript, Basis-Konfiguration,
   `images/` und `container-rootfs/`. Diese Dateien gehören zum Zeitpunkt des Snapshots.
5. Benötigte Basisabbilder mit `docker image load -i DATEI.tar` aus `images/` laden.
   Ein per Image-ID gespeichertes Abbild kann ohne ursprünglichen Tag geladen werden.
   Den ursprünglichen Namen aus `containers.json` (`Config.Image`) gegebenenfalls
   wieder mit `docker tag IMAGE_ID NAME` setzen. Nicht bauen oder aus dem Netz ziehen.
6. Falls eine Anwendung nach der Container-Erstellung in dessen beschreibbarer Schicht
   installiert oder verändert wurde, enthält `container-rootfs/CONTAINER_ID.tar` diesen
   Dateisystemstand. Mit `docker import` lässt sich daraus ein lokales Wiederherstellungs-
   abbild erstellen. Dabei gehen Container-Metadaten verloren: `Env`, `Entrypoint`, `Cmd`,
   `WorkingDir`, `User`, exponierte Ports und weitere Einstellungen müssen aus
   `containers.json` bzw. Compose wieder gesetzt werden. Das ursprüngliche Basisabbild
   allein enthält diese nachträglichen Änderungen nicht. Netzwerk- und Mountdaten
   kommen ebenfalls aus Compose bzw. den Metadaten, nicht aus dem rootfs-Tar.
7. Benannte Volumes anhand `volumes.json` neu anlegen. Die im Snapshot vorhandenen
   `_data`-Inhalte in die leeren neuen Volume-Mountpoints kopieren. Kein komplettes
   `/var/lib/docker` von einem anderen laufenden Docker-Daemon darüberkopieren.
   Bind-Mounts an ihren ursprünglichen Pfaden wiederherstellen oder Compose bewusst anpassen.
8. Ollama-Modelle inklusive Manifests und Blobs zusammen zurückkopieren. Ollama-Programm,
   Bibliotheken, Service-Unit und gegebenenfalls Drop-ins wiederherstellen, den Benutzer
   `ollama` mit passenden Rechten bereitstellen und `systemctl daemon-reload` ausführen.
   Das Home enthält die lokalen ComfyUI-Modelle und den gesicherten HF-Cache.
9. Compose-Projekte zunächst mit `docker compose create --no-build --pull never` erstellen,
   erforderliche Images/Overrides vorher zuordnen. Dies startet keine Container.
   Erst nach Kontrolle gezielt die laut `dienstzustand.json` vorher laufenden Dienste
   starten. Niemals pauschal sämtliche Projekte hochfahren. Die alten Container-IDs gelten
   auf dem neuen Host nicht; dort die Namen bzw. Compose-Dienste zuordnen.
10. Datenbanken, Bilder, Einstellungen und Zugriff prüfen. Keine Test-Comics, Modell-
    Downloads oder externen Veröffentlichungen automatisch auslösen. Root-Cron und
    Autostarts erst nach bewusster Freigabe für das neue System aktivieren.

Caches werden aus der Sicherung zurückkopiert. Laufzeitcaches dürfen sich bei normaler
Benutzung neu aufbauen; fehlende Modellgewichte werden dadurch nicht ersetzt.
Ein Recovery-Test wurde ausdrücklich nicht durchgeführt.

## Beispiel: Comic-Datenvolume zurückholen

Nur als Wiederherstellungsbeispiel auf einem neuen, stillgelegten Zielsystem, nicht
jetzt ausführen. Der Volume-Name darf dort noch nicht existieren. Die allgemeinen
Schritte oben und die zu diesem Snapshot gespeicherten Metadaten haben Vorrang.

```bash
# Leeres Volume mit dem ursprünglichen Namen erstellen:
docker volume create comic-automation_comic-automation-data

# Neuen tatsächlichen Zielpfad ermitteln:
docker volume inspect --format '{{.Mountpoint}}' comic-automation_comic-automation-data
```

Bei einer früheren Sicherung mit benanntem Volume liegt der Inhalt beispielsweise unter:

```text
/mnt/backup/docker-offline/weekly.0/localhost/var/lib/docker/volumes/comic-automation_comic-automation-data/_data/
```

Diesen Inhalt in den eben ermittelten **leeren** Ziel-Mountpoint kopieren:

```bash
sudo rsync -aHAX --numeric-ids /PFAD/ZUM/GESICHERTEN/_data/ /NEUER/VOLUME-MOUNTPOINT/
```

Ein abschließender `rsync -aHAXnci --numeric-ids` mit denselben Pfaden muss ohne
Abweichungen durchlaufen. Erst danach Compose mit passendem Volume-Namen verwenden.
Labels aus `volumes.json` bei der Neuanlage ebenfalls übernehmen, wenn sie für das
Compose-Projekt erforderlich sind. Bei abweichendem Docker-Datenverzeichnis ist der
neu ermittelte Mountpoint maßgeblich. Bei vorhandenem Volume abbrechen und dessen
Inhalt separat klären; `docker volume create` allein garantiert kein leeres Ziel.

SQLite-Datenbank, WAL und SHM werden als Teil desselben ruhenden Volume-Verzeichnisses
gesichert. Es wird nicht nur eine einzelne möglicherweise inkonsistente `.sqlite3`-
Datei aus einem laufenden Container kopiert.

## Validierung der Vorbereitung

`tests/test_docker_rsnapshot_weekly.py` prüft mit simulierten Diensten und ausschließlich
kleinen Testverzeichnissen unter anderem Fehler ohne Neustart, Journal-Sperre,
ursprünglich gestoppte Dienste sowie echte rsnapshot-Hardlinks und eine absichtlich
veränderte Datei mit unveränderter Größe und unverändertem Zeitstempel.
Keine produktiven Dienste werden durch diese Tests gestoppt oder gestartet.

Referenzen: [rsnapshot-FAQ](https://rsnapshot.org/faq.html) und
[offizielle Konfigurationsvorlage](https://github.com/rsnapshot/rsnapshot/blob/master/rsnapshot.conf.default.in).

## Vollständiges /etc nachträglich ergänzen

Die Projektkonfiguration enthält jetzt `/etc` vollständig. Bei schon installierter
Konfiguration einmal ausführen:

```bash
sudo python3 -I /home/jee/docker/minimax-h3-dgx-spark/scripts/include_etc_in_backup.py
```

Der Helfer bewahrt die vorherige Konfiguration auf und verweigert Änderungen während
einer laufenden Sicherung. Er startet weder Backup noch Dienste. Einzelne zusätzliche
Quellen unter `/etc` werden durch die vollständige Quelle ersetzt. Der Snapshot enthält
diese Dateien unter `weekly.N/localhost/etc/`, einschließlich geschützter Dateien.
Symlinks bleiben Links; außerhalb der Quellen liegende Linkziele werden nicht automatisch
mitkopiert. Für einen neuen Host einzelne benötigte Konfigurationen gezielt übernehmen;
ein komplettes `/etc` nicht ungeprüft über eine andere Systeminstallation schreiben.

## Installierte Fassung aktualisieren und Prüfjob abkoppeln

Einmalig ausführen:

```bash
sudo python3 -I /home/jee/docker/minimax-h3-dgx-spark/scripts/update_docker_rsnapshot.py
```

Dieses Update ergänzt `/etc`, entfernt die vollständige Inhaltsprüfung aus dem
regulären Backup und installiert den separaten Aufruf. Vorherige installierte
Dateien werden unter `/var/lib/docker-offline-backup/updates/ZEITSTEMPEL/` aufbewahrt.
Ein aktives Backup oder eine aktive Prüfung blockiert das Update per gemeinsamem
Lock. Es werden keine Jobs gestartet und keine Cron-Einträge aktiviert. Ein alter
Fehlerstatus wird ausdrücklich nicht als erfolgreich markiert oder gelöscht.

Der reguläre Aufruf bleibt unverändert:

```bash
sudo /usr/local/sbin/docker-rsnapshot-weekly --run
```

Der spätere Root-Cronjob verwendet ebenfalls nur diesen Aufruf. Der manuelle
Inhaltsvergleich wird nicht automatisch mit ausgeführt.

## Manueller Prüfsummenjob bei Bedarf

Nur selbst ausführen, wenn gewünscht und die betroffenen Dienste bereits gestoppt sind:

```bash
sudo /usr/local/sbin/docker-rsnapshot-checksums
```

Ein anderer abgeschlossener Wochenstand lässt sich gezielt auswählen:

```bash
sudo /usr/local/sbin/docker-rsnapshot-checksums --snapshot weekly.1
```

Der Standard ist `weekly.0`. `.sync`, fehlende Snapshots und Pfade außerhalb der
Wochenstände sind nicht erlaubt. Der Job verwendet die im ausgewählten Snapshot
gespeicherte Quellenliste und nicht einfach die heute erweiterte Liste. Ein älterer
Stand ohne vollständiges `/etc` wird dadurch nicht fälschlich als `/etc`-Sicherung
geprüft. Er verwendet dasselbe Lock wie Backup und Update; es kann nicht gleichzeitig
rotiert oder kopiert werden.

**Der Prüfjob stoppt oder startet nichts.** Laufende betroffene Dienste führen zum
Abbruch, bevor die Inhaltsprüfung beginnt. Eine erforderliche Stilllegung erfolgt
nur nach gesonderter ausdrücklicher Anweisung. Fortschrittsmeldungen nennen die
aktuell geprüfte Quelle; bei großen Verzeichnissen gibt es noch keine Prozentanzeige.

Verglichen wird mit den **heutigen Originaldateien**. Seit dem Snapshot geänderte
oder gelöschte Dateien, aktuelle Docker-Exportmetadaten und bereits wiederhergestellte
Autostart-Symlinks unter `/etc` können berechtigte Abweichungen erzeugen. Das ist kein
Beweis einer beschädigten Sicherung. Die Prüfung verändert weder Quelle noch Snapshot.
Es wird kein dauerhafter Inhaltsprüfstand für spätere Vergleiche ohne Originale erzeugt.

Der eigene Status steht in `/var/lib/docker-offline-backup/checksums-status.json`.
Das Backup-Journal `status.json` bleibt unverändert. Im neuen Backup-Journal bedeuten
`verification: metadata` und `checksums_verified: false`, dass nur die reguläre
Metadatenprüfung zum Backup gehörte. Der vorhandene Schlüssel `verified` bezieht
sich dann auf diese Prüfung, nicht auf einen vollständigen Inhaltsvergleich.

Zusätzliche Tests prüfen den separaten Job, die Weigerung bei laufenden Diensten,
die unveränderten Snapshots/Backup-Journale und die Aktualisierung unter Lock. Alle
Tests benutzen simulierte Dienste und kleine Testdateien, keine produktiven Läufe.

## Root-Crontab nach dem Update einrichten

Manuell einrichten:

```bash
sudo python3 -I /home/jee/docker/minimax-h3-dgx-spark/scripts/install_docker_backup_cron.py
```

Voraussetzung ist die aktualisierte Fassung mit vollständigem `/etc` und separatem
Prüfsummenjob. Der Installer ergänzt genau den oben genannten Sonntag-03:00-Eintrag
in der Root-Crontab. Vorhandene andere Root-Cronjobs bleiben erhalten; die bisherige
Crontab wird unter `/var/lib/docker-offline-backup/cron-originale/` aufbewahrt.
Doppelte Einträge, konkurrierende direkte rsnapshot-Aufrufe und aktive Änderungen
während Backup/Prüfung werden verhindert. Der Aufruf startet jetzt kein Backup und
ändert keine Dienste. Nach Installation ist der zukünftige Zeitplan aktiv.
Ein unvollständiges Backup-Journal blockiert weiterhin alle neuen Sicherungsläufe;
es wird weder gelöscht noch als erfolgreich umgeschrieben.

## Abschluss und manuelle Bereinigung

Ein Sammelskript für Statusprüfung, Update und Wochen-Cron sowie ein separates,
standardmäßig nur planendes Bereinigungsskript sind in
[Backup_Abschluss_und_Bereinigung.md](Backup_Abschluss_und_Bereinigung.md) beschrieben.
Eine Bereinigung wurde nicht gestartet.

## Laufende Codex-Daten und Browser-Caches

Die reguläre Metadatenprüfung und der manuelle Prüfsummenvergleich nehmen folgende
Pfade von ihrer strengen Bewertung aus, abgeleitet aus dem konfigurierten Home:

- `/home/jee/.codex` (gesamtes Verzeichnis, einschließlich Verläufen und Einstellungen);
- `/home/jee/.cache/google-chrome`;
- `/home/jee/.cache/chromium`;
- `/home/jee/.cache/mozilla`;
- `/home/jee/.cache/BraveSoftware`;
- `/home/jee/.config/google-chrome/BrowserMetrics`;
- `/home/jee/.config/chromium/BrowserMetrics`.

**Die Kopierphase sichert diese Bereiche weiter mit.** Die Ausnahme steht nicht in
rsnapshots Backup-Ausschlüssen, sondern nur im anschließenden lesenden Vergleich.
Auch bereits gesicherte, inzwischen verschwundene WAL-/SHM-/Temporärdateien werden
nicht als zu löschende Differenz bewertet. Es wird nur ein Hinweis ausgegeben.
Das ist keine Zusage einer konsistenten SQLite-Sicherung laufender Codex-Datenbanken.
Die Ausnahme ist ausdrücklich auf diese Pfade begrenzt; Docker-Daten, Modelle,
andere Home-Dateien und `/etc` werden unverändert bewertet. Tatsächliche Kopier- und
Lesefehler werden nicht pauschal ignoriert.

Die Journale nennen die Ausnahme unter `verification_ignored_paths`. Zum Installieren
auf dem bestehenden System genügt erneut der Aufruf von
`scripts/update_docker_rsnapshot.py` mit sudo; er startet nichts und bewahrt installierte Originale auf.

## Vorhandenen Stand nach fehlgeschlagenem Quellenvergleich fortsetzen

Erst nach dem Update und nur auf ausdrücklichen manuellen Aufruf:

```bash
sudo /usr/local/sbin/docker-rsnapshot-weekly --resume
```

Dieser Befehl **startet die inkrementelle Fortsetzung**. Er akzeptiert ausschließlich einen Fehler in der Phase `pruefen`
mit der Diagnose `Sicherung weicht von Quelle ab:`. Kopier-, Berechtigungs-,
Stop-/Startfehler und unklare Stromausfälle werden damit nicht stillschweigend
freigegeben. Ein bereits erfolgreich abgeschlossener Lauf wird nicht fortgesetzt.

Der alte Fehlerstatus wird vor dem neuen Lauf dauerhaft unter
`/var/lib/docker-offline-backup/fehlerhistorie/` aufbewahrt. Der vorhandene `.sync`-
Arbeitsstand bleibt erhalten und wird mit rsnapshot/rsync aktualisiert, einschließlich
der inzwischen neu aufgenommenen `/etc`-Quelle. Danach erfolgt die neue Metadatenprüfung
mit den begrenzten Laufzeitausnahmen. Erfolg wird erst nach erfolgreicher Rotation
und Abschluss dokumentiert; der alte Lauf wird nicht rückwirkend als erfolgreich markiert.

Der neue Lauf startet nur Dienste, die bei seinem tatsächlichen Beginn laufen.
Aktuell gestoppte Dienste bleiben gestoppt. Im vorigen Fehlerlauf deaktivierte
Restart-Policies und Service-Autostart-Einstellungen werden anhand des gesicherten
Fehlerjournals nach erfolgreichem Abschluss auf die ursprünglichen Sollwerte
zurückgesetzt. Das ersetzt keinen sofortigen Dienststart. Nach erfolgreicher Fortsetzung
kann `finish_docker_backup_setup.py` erneut zum Abschluss der Einrichtung aufgerufen
werden. Eine Bereinigung erfolgt weiterhin nur getrennt und manuell.

### Veränderliche CUPS-Abonnements unter /etc

Die beiden vom laufenden Druckdienst regelmäßig aktualisierten Dateien
`/etc/cups/subscriptions.conf` und `/etc/cups/subscriptions.conf.O` werden weiterhin
kopiert, aber von der strengen Abschlussbewertung ausgenommen. Zusätzlich ist nur
eine reine Zeitstempelabweichung des Verzeichnisses `/etc/cups` ein Hinweis.
Andere Änderungen am Verzeichnis (etwa Rechte, Eigentümer oder ACLs) und die übrigen
CUPS-Dateien wie `printers.conf` bleiben Fehler. Die Ausnahme gilt für die normale
Prüfung und den separaten manuellen Inhaltsvergleich und steht in den Journalfeldern
`verification_ignored_files` und `verification_ignored_directory_timestamps`.
Das Update wird mit `sudo python3 -I scripts/update_docker_rsnapshot.py` installiert;
anschließend kann der konkret fehlgeschlagene Quellenvergleich mit
`sudo /usr/local/sbin/docker-rsnapshot-weekly --resume` erneut inkrementell ausgeführt werden. Keine automatische Wiederholung erfolgt.

Chrome-Messdaten unter `BrowserMetrics` werden ebenfalls als veränderliche
Laufzeitdaten behandelt. Diese Ausnahme erfasst keine übrigen Profildaten: insbesondere
`Default/Bookmarks` und andere Einstellungen bleiben weiterhin in der Prüfung.

### Elternverzeichnisse beim Prüfen relativer Pfade

Der lesende Vergleich verwendet `--relative --no-implied-dirs`. Damit werden die
Metadaten automatisch mitgeführter Elternverzeichnisse nicht als Abweichung des
gewählten Quellbaums bewertet. Beim Vergleich von
`/var/lib/docker-offline-backup/export` liegt beispielsweise die Statusdatei im
Elternverzeichnis; ihr Schreiben ändert dessen Zeitstempel, ohne die Exportdaten
zu verändern. Der eigentliche Quellordner `export` und alle seine Inhalte bleiben
vollständig im jeweils gewählten Prüfmodus. Ein Test verändert separat Eltern-,
Quellordner-Zeitstempel und Exportinhalt und prüft diese Grenze ausdrücklich.
