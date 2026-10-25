# Comic-Studio: vollständige Offline-Sicherung und Wiederherstellung

## Sicherung starten

```bash
cd /home/jee/docker/minimax-h3-dgx-spark
python3 scripts/backup_comic_studio.py --plan
python3 scripts/backup_comic_studio.py
```

Das Ziel ist `/mnt/backup/comic-studio/ZEITSTEMPEL/`. Das Laufwerk muss eingehängt
sein. Jede Sicherung erhält einen neuen Ordner; ältere Sicherungen werden nicht
überschrieben oder automatisch gelöscht. Der Ordner ist nur für seinen Besitzer
zugänglich, denn Konfiguration und Docker-Abbilder enthalten auch Zugangsdaten.

Vor dem Anhalten werden die Comic- und ComfyUI-Warteschlangen geprüft. Bei laufenden
oder wartenden Aufträgen bricht das Skript ohne Anhalten ab. Die beiden betroffenen
Container bleiben während der eigentlichen Sicherung gestoppt und werden danach
in ihrem vorherigen Zustand gestartet. Andere Docker-Projekte bleiben unangetastet.
Der separate Ollama-Dienst bleibt für andere Anwendungen verfügbar. Während des
Backups dort keine Modelle installieren oder löschen; laufende Inferenz liest
nur die bestehenden Modellblobs. Dateiveränderungen während der Archivierung
führen zu einem Fehler statt zu einer als vollständig markierten Sicherung.

Enthalten:

- betroffene Compose-Dateien, `.env`, optionale Telegram-Konfiguration, Projektcode,
  Quellenkatalog, Beispiele, Schriften, Skripte und Dokumentation;
- vollständiges Comic-Datenvolume mit SQLite, Geschichten, Szenen, Bewertungen,
  Veröffentlichungsprotokollen, Figuren, Referenzbildern und Ausgaben;
- ComfyUI-Eingaben, Ausgaben, temporäre Bilder, Benutzer-/Workflow-Daten und die
  tatsächlich installierten Erweiterungen;
- ComfyUI-Modelle, vorhandener Hugging-Face-Cache sowie Ollama-Modelle mit Manifesten
  und Blobs; Modellgewichte werden jetzt ausdrücklich mitgesichert;
- lokale Ollama-Programmdateien, Bibliotheken und systemd-Konfiguration;
- Schnappschüsse beider Docker-Container als ladbare Abbilder, einschließlich
  nachträglich installierter Python-Pakete. Kein Registry-Download beim Recovery.

Nicht enthalten sind Betriebssystem, Docker Engine, NVIDIA-Treiber und NVIDIA
Container Toolkit. Diese Grundlagen müssen auf einem kompatiblen Linux-/ARM64-
Zielsystem bereits offline verfügbar sein. Keine anderen Docker-Stacks werden
gesichert. Es erfolgt kein Recovery-Test und kein probeweiser Modell- oder Comic-Lauf.

## Hintergrundbetrieb und Fortschritt

Das Skript benötigt nach dem Start keine laufende Unterhaltung mit dem Assistenten.
Beispiel für einen vom Terminal unabhängigen Start:

```bash
cd /home/jee/docker/minimax-h3-dgx-spark
mkdir -p /mnt/backup/comic-studio
chmod 700 /mnt/backup/comic-studio
nohup python3 -u scripts/backup_comic_studio.py \
  > /mnt/backup/comic-studio/backup.log 2>&1 < /dev/null &
echo $!
```

```bash
tail -f /mnt/backup/comic-studio/backup.log
ls -l /mnt/backup/comic-studio/
```

Große Archive melden regelmäßig die bereits geschriebenen GiB. Ein zweiter Lauf
wird durch eine Dateisperre verhindert. Erst ein Ordner ohne `.partial`, mit
`FERTIG`, `manifest.json` und `SHA256SUMS` ist ein abgeschlossener Sicherungsstand.
Einzelne fertig geschriebene Archive haben zusätzlich eine `.sha256`-Datei.

## Unterbrechung, insbesondere Stromausfall

Ein normales Schließen des Terminals beendet einen mit `nohup` gestarteten Lauf
nicht. Bei regulärem Abbruch per SIGTERM oder Strg+C versucht das Skript, zuvor
laufende Container wieder zu starten. Bei Stromausfall, SIGKILL oder einem
Systemabsturz kann dieses Aufräumen nicht ausgeführt werden.

Archive werden vor ihrer Fertigmeldung mit `fsync` auf den Datenträger geschrieben.
Anschließend wird ihre Prüfsumme dauerhaft abgelegt. Die Abschlussdateien werden
zuletzt geschrieben; erst dann wird der `.partial`-Ordner atomar umbenannt. Ein
Stromausfall währenddessen ist trotzdem kein Anlass, einen unvollständigen Stand
als vollständige Sicherung zu verwenden. Maßgeblich sind Abschlusskennzeichnung
und vollständige, passende Prüfsummen, nicht allein das Vorhandensein großer Dateien.

Nach Wiederkehr des Stroms:

1. Backup-Laufwerk wieder einhängen; mit `findmnt -T /mnt/backup` sicherstellen,
   dass dort wirklich das Laufwerk liegt.
2. Im Protokoll und im jüngsten `.partial`-Ordner nachsehen. `DIENSTZUSTAND.json`
   dokumentiert schon vor dem Anhalten, welche Container vorher liefen.
3. Die Originaldaten wurden durch die Sicherung nicht gelöscht. Zunächst den
   ursprünglichen Betrieb wieder aufnehmen, nicht über unvollständige Daten
   restaurieren. Durch `docker stop` angehaltene Dienste mit `unless-stopped`
   können auch nach einem Neustart des Rechners weiterhin angehalten sein.
4. Die vorher laufenden Dienste bei Bedarf manuell starten:

   ```bash
   docker start minimax-h3-comfyui
   docker start comic-automation-comic-automation-1
   ```

   Bei abweichenden Namen die Angaben aus `DIENSTZUSTAND.json` verwenden. Dienste,
   die vorher bereits gestoppt waren, nicht versehentlich aktivieren.
5. Das Sicherungsskript erneut aufrufen. Es legt einen neuen Zeitstempel an.
   **Es setzt unvollständige Archive nicht automatisch fort und mischt keinen
   alten Teilstand mit neueren Anwendungsdaten.** Ausreichend Platz für den neuen
   Lauf berücksichtigen. Einen alten `.partial`-Ordner erst separat entfernen,
   wenn sicher kein Prozess mehr hineinschreibt und seine Dateien nicht mehr
   benötigt werden. Fertige ältere Backups bleiben erhalten.

Bei einem Abbruch können lokal zusätzlich `local/comic-studio-backup:…`-Images
übrig bleiben. Sie sind Sicherungsschnappschüsse, keine anderen Projekte. Erst
nach Klärung des Sicherungsstands nicht mehr benötigte Schnappschüsse gezielt
entfernen; keine pauschale Docker-Bereinigung und kein `docker compose down -v`.

## Wiederherstellung – ausschließlich Anleitung, nicht automatisch ausgeführt

Die folgenden Schritte beschreiben ein echtes Recovery auf ein vorbereitetes
Zielsystem. Es wird kein Recovery-Test vom Backup-Skript gestartet. Eine vorhandene
Installation zuerst anhalten und nicht ungeprüft mit der Rücksicherung überschreiben.

### 1. Vollständigen Stand auswählen und Abbilder laden

```bash
BACKUP=/mnt/backup/comic-studio/DEIN_ZEITSTEMPEL
cd "$BACKUP"
test -f FERTIG
test ! -f FEHLGESCHLAGEN
sha256sum -c SHA256SUMS
zstd -dc docker-images.tar.zst | docker image load
```

Bei fehlenden oder abweichenden Prüfsummen nicht mit der Wiederherstellung
fortfahren. Das Lesen der Prüfsummen gehört zur tatsächlichen Wiederherstellung;
das Backup-Skript führt keine Wiederherstellung zum Test aus.

### 2. Projekt und ComfyUI-Daten anlegen

Ein leeres Zielverzeichnis verwenden, beispielsweise:

```bash
RESTORE=/srv/comic-studio
export H3_DATA_ROOT=/srv/comic-studio-data
mkdir -p "$RESTORE/project" "$H3_DATA_ROOT"
zstd -dc "$BACKUP/projekt.tar.zst" | tar -xpf - -C "$RESTORE/project"
for bereich in input output temp user custom_nodes; do
  mkdir -p "$H3_DATA_ROOT/$bereich"
  zstd -dc "$BACKUP/data/comfy-$bereich.tar.zst" | \
    tar -xpf - -C "$H3_DATA_ROOT/$bereich"
done
```

Besitzrechte entsprechen den im Manifest dokumentierten Benutzer-IDs. Falls der
Zielbenutzer davon abweicht, Rechte passend zu den Compose-Benutzern setzen;
ComfyUI und Comic-Automation laufen hier mit UID/GID 1000:1000. Bei fehlenden
Rechten die betreffenden Wiederherstellungsschritte als Administrator ausführen.
Die Anwendung und nicht pauschal der gesamte Datenträger soll passende Rechte haben.

### 3. Modelle und Caches aufbauen

Die Modelle liegen als echte Dateien in eigenen Archiven vor. Symlinks in den
Quelldaten bleiben Symlinks; deren Ziele stehen zusätzlich in
`modelle-nur-verweise.json`. Beim hier erfassten ComfyUI-Modellbestand gibt es
keine externen Dateilinks. Auf anderen Installationen solche Ziele vorab beachten.

```bash
mkdir -p "$H3_DATA_ROOT/models" "$H3_DATA_ROOT/hf-cache"
zstd -dc "$BACKUP/data/comfy-modelle.tar.zst" | \
  tar -xpf - -C "$H3_DATA_ROOT/models"
zstd -dc "$BACKUP/data/hf-cache.tar.zst" | \
  tar -xpf - -C "$H3_DATA_ROOT/hf-cache"
```

Die Unterordner wie `diffusion_models`, `text_encoders`, `vae`, `vision`, `loras`
und `checkpoints` erhalten ihre ursprünglichen Namen. Nicht alle Gewichte in einen
flachen Ordner verschieben: Workflows verweisen auf konkrete Modellnamen und Pfade.
Der vorhandene HF-Cache wird in seiner Originalstruktur wiederhergestellt; seine
Revisionen, Blobs und Snapshot-Verweise nicht beliebig umbenennen. Ein leerer Cache
kann als Verzeichnis neu angelegt werden, ersetzt aber keine fehlenden Gewichte,
Tokenizer oder Repository-Konfigurationen. Für Offline-Betrieb deshalb den
mitgesicherten Cache verwenden.

CUDA-/Kernel-Caches wie `.nv/ComputeCache` oder Xet-Zwischendaten sind keine
zusätzlichen Modellquellen. Fehlende Laufzeit-Caches können bei späterer normaler
Nutzung neu entstehen. Das Recovery löst dafür keinen Probeauftrag aus.

### 4. Lokales Ollama wiederherstellen

Dieser Dienst läuft außerhalb der beiden Compose-Projekte. Für ein Recovery auf
demselben Host vorhandene Programmdateien nicht unnötig überschreiben. Bei einer
neuen, vorbereiteten Maschine kann der gesicherte ARM64-Programmstand verwendet
werden. Installation und systemd-Konfiguration benötigen Administratorrechte:

```bash
# Falls bereits vorhanden, vor einer tatsächlichen Rücksicherung anhalten:
sudo systemctl stop ollama
zstd -dc "$BACKUP/ollama-programm.tar.zst" | sudo tar -xpf - -C /
getent passwd ollama || sudo useradd --system --user-group \
  --home-dir /usr/share/ollama --create-home --shell /usr/sbin/nologin ollama
sudo mkdir -p /usr/share/ollama/.ollama/models
zstd -dc "$BACKUP/data/ollama-modelle.tar.zst" | \
  sudo tar -xpf - -C /usr/share/ollama/.ollama/models
sudo chown -R ollama:ollama /usr/share/ollama/.ollama
sudo systemctl daemon-reload
sudo systemctl enable --now ollama
```

Der aktuelle Modellpfad lautet `/usr/share/ollama/.ollama/models`. Bei einem im
Manifest abweichenden `model_areas.ollama-modelle` diesen Pfad verwenden oder
`OLLAMA_MODELS` in einer systemd-Drop-in-Datei darauf setzen. Ein abweichender
Dienstbenutzer ist ebenfalls im Manifest dokumentiert. Bei Bedarf den Benutzer
zu den auf dem Zielhost vorhandenen GPU-Gruppen `video` und `render` hinzufügen.

**Manifeste und Blobs zusammen zurückspielen.** Nur die Blobs oder nur die
Modellnamen reichen nicht für `ollama run`. Der vollständige Modellbaum ermöglicht
die Wiederverwendung der vorhandenen Modelle ohne `ollama pull`. Hostname,
Bind-Adresse und Port aus der gesicherten Ollama-Konfiguration an das Zielsystem
anpassen. Die Comic-Konfiguration erwartet normalerweise den lokalen Dienst unter
`http://host.docker.internal:11434`. Docker- und NVIDIA-Grundinstallation sind
Voraussetzungen und werden nicht über dieses Programmarchiv installiert.

### 5. Comic-Datenvolume zurückspielen

Ein frisches Volume verwenden, damit keine vorhandenen Daten überschrieben werden:

```bash
export COMIC_RESTORE_VOLUME=comic-studio-wiederherstellung
export COMIC_RESTORE_NETWORK=comic-studio-wiederherstellung
COMIC_IMAGE=$(python3 -c \
  'import json; print(json.load(open("manifest.json"))["containers"]["comic-automation"]["backup_image"])')
docker volume create "$COMIC_RESTORE_VOLUME"
zstd -dc "$BACKUP/data/comic-automation.tar.zst" | \
  docker run --rm -i --network none --user 0:0 \
    --mount "type=volume,src=$COMIC_RESTORE_VOLUME,dst=/restore" \
    --entrypoint /bin/tar "$COMIC_IMAGE" --numeric-owner -xpf - -C /restore
```

Den Volumenamen vorab mit `docker volume inspect` prüfen: Ein bestehendes Volume
wird durch `docker volume create` nicht geleert. Die Extraktion nur in ein wirklich
leeres Zielvolume ausführen. Das Backup enthält auch SQLite-WAL-Dateien, sofern
sie im gestoppten Zustand vorhanden waren; die zusammengehörigen Dateien behalten.

### 6. Genau die gesicherten Dienste starten

In `.env` insbesondere `H3_DATA_ROOT`, lokale Bind-IP/Ports und Ollama-Adresse
prüfen. Die vorhandenen Token bleiben aus der gesicherten Konfiguration erhalten.
Keine Tokens in öffentliche Protokolle oder Git kopieren. Die folgenden Starts
bauen keine Images und laden nichts aus einer Registry:

```bash
cd "$RESTORE/project"
export H3_DATA_ROOT=/srv/comic-studio-data
export COMIC_RESTORE_VOLUME=comic-studio-wiederherstellung
export COMIC_RESTORE_NETWORK=comic-studio-wiederherstellung
docker compose -p minimax-h3-dgx-spark \
  -f docker-compose.yml -f docker-compose.posters.yml \
  -f "$BACKUP/recovery/comfyui.offline.yml" \
  up -d --no-build --pull never comfyui
docker compose -p comic-automation \
  -f docker-compose.comic-automation.yml \
  -f "$BACKUP/recovery/comic.offline.yml" \
  up -d --no-build --pull never comic-automation
```

Abweichende Projektnamen stehen im Manifest. `docker-compose.posters.yml` ist hier
nur der tatsächlich verwendete leere ComfyUI-Overlay, kein weiterer Dienst.
Netzwerk- und Volumenamen werden durch die Recovery-Overrides auf die oben gewählten
Ziele gesetzt. Die Workflow-Vorlage wird aus dem zurückgesicherten Projekt eingebunden.

Damit sind Anwendung, Daten und lokale Modellbestände zurückgespielt. Anschließend
kann der Betreiber das Dashboard normal öffnen. Die Anleitung und das Backup
starten keinen Comic, veröffentlichen keinen Telegram-Beitrag und führen keinen
Recovery-Test aus. Der wieder gestartete vorhandene Telegram-Trigger behält jedoch
seine gesicherten Einstellungen und nimmt seinen normalen Betrieb wieder auf.
