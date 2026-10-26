#!/bin/bash
set -euo pipefail
alt=/usr/share/ollama/.ollama/models
neu=/home/jee/models/ollama
if [[ $EUID -ne 0 ]]; then echo "Bitte mit sudo bash ausführen."; exit 1; fi
[[ -d "$alt" && ! -L "$alt" && -d "$neu" && ! -L "$neu" ]] || { echo "Abbruch: Modellpfade prüfen."; exit 1; }
systemctl show ollama -p Environment --value | grep -Fq 'OLLAMA_MODELS=/home/jee/models/ollama' || { echo "Abbruch: Ollama nutzt nicht den erwarteten neuen Pfad."; exit 1; }
[[ -n $(find "$neu" -type f -print -quit) ]] || { echo "Abbruch: Neuer Modellordner leer."; exit 1; }
if findmnt -rn -o TARGET | grep -Eq '^/usr/share/ollama/\.ollama/models(/|$)'; then echo "Abbruch: Mount im alten Modellverzeichnis."; exit 1; fi
pruefung=$(mktemp)
trap 'rm -f "$pruefung"' EXIT
set +e
lsof -nP +D "$alt" > "$pruefung"
status=$?
set -e
if [[ -s "$pruefung" || $status -gt 1 ]]; then cat "$pruefung"; echo "Abbruch: Zugriff erkannt oder Prüfung fehlgeschlagen."; exit 1; fi
rm -rf --one-file-system -- "$alt"
echo "Alte Ollama-Modellkopie gelöscht. Neue Modelle unverändert."
