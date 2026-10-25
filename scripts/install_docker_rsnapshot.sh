#!/bin/bash
# Installiert Dateien, aktiviert weder Cron noch Dienste und startet keine Sicherung.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Einmal mit sudo ausführen.' >&2; exit 1; }
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
for tool in python3 rsnapshot rsync docker systemctl findmnt; do
    command -v "$tool" >/dev/null || { echo "Werkzeug fehlt: $tool" >&2; exit 1; }
done
python3 - "$project" <<'PY'
import ast,json,sys
from pathlib import Path
root=Path(sys.argv[1])
ast.parse((root/'scripts/docker_rsnapshot_weekly.py').read_text())
json.loads((root/'backup/docker-rsnapshot.json').read_text())
PY
for file in /usr/local/sbin/docker-rsnapshot-weekly /etc/docker-rsnapshot.json /usr/local/sbin/docker-rsnapshot-checksums; do
    if [[ -e "$file" || -L "$file" ]]; then
        echo "Datei existiert bereits; nichts überschrieben: $file" >&2
        exit 1
    fi
done
install -o root -g root -m 0700 "$project/scripts/docker_rsnapshot_weekly.py" /usr/local/sbin/docker-rsnapshot-weekly
install -o root -g root -m 0700 "$project/scripts/docker_rsnapshot_checksums.sh" /usr/local/sbin/docker-rsnapshot-checksums
install -o root -g root -m 0600 "$project/backup/docker-rsnapshot.json" /etc/docker-rsnapshot.json
if [[ -e /etc/rsnapshot.conf || -L /etc/rsnapshot.conf ]]; then
    previous="/etc/rsnapshot.conf.vor-docker-offline-$(date -u +%Y%m%dT%H%M%SZ)"
    cp -a -- /etc/rsnapshot.conf "$previous"
    echo "Bisherige Konfiguration aufbewahrt: $previous"
fi
# Keine möglicherweise vorhandene symbolische Verknüpfung verfolgen.
rm -f -- /etc/rsnapshot.conf
install -o root -g root -m 0600 "$project/backup/rsnapshot-docker.conf" /etc/rsnapshot.conf
echo 'Installiert. Kein Cron aktiviert, keine Dienste gestartet/gestoppt, keine Sicherung gestartet.'
echo 'Lesende Prüfung: sudo /usr/local/sbin/docker-rsnapshot-weekly --plan'
