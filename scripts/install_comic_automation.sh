#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
: "${H3_DATA_ROOT:?Run make init first}"
python3 - "$H3_DATA_ROOT" <<'PY'
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);workflows=root/'user/default/workflows'
def hashes():return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in workflows.rglob('*.json') if p.name!='04_Comic_Automat_9B.json'}
def idle():
    run=subprocess.run(['docker','exec','minimax-h3-comfyui','curl','-fsS','http://127.0.0.1:8188/queue'],capture_output=True,text=True,check=True)
    queue=json.loads(run.stdout)
    if queue['queue_running'] or queue['queue_pending']:
        raise SystemExit('ComfyUI ist beschäftigt. Installation ohne Neustart beendet; bei leerer Warteschlange erneut ausführen.')
idle();before=hashes()
shutil.copytree('extensions/dgx-comics',root/'custom_nodes/dgx-comics',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
target=workflows/'Comics/04_Comic_Automat_9B.json';target.parent.mkdir(parents=True,exist_ok=True)
if not target.exists():shutil.copy2('examples/comics/workflows/04_Comic_Automat_9B.json',target)
if before!=hashes():raise SystemExit('Unerwartete Änderung an vorhandenen Workflows.')
idle();subprocess.run(['docker','restart','minimax-h3-comfyui'],check=True)
print('Automationshelfer installiert; vorhandene Workflows unverändert. Neue Vorlage: 04_Comic_Automat_9B.')
PY
