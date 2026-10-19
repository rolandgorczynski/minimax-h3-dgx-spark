#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
: "${H3_DATA_ROOT:?Run make init first}"
python3 - "$H3_DATA_ROOT" <<'PY'
import pathlib, shutil, sys
from datetime import datetime
root = pathlib.Path(sys.argv[1])
for name in ('dgx-invitations', 'dgx-posters'):
    shutil.copytree(pathlib.Path('extensions') / name, root/'custom_nodes'/name,
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
workflows = root/'user/default/workflows/Plakaty'
workflows.mkdir(parents=True, exist_ok=True)
for source in pathlib.Path('examples/posters/workflows').glob('*.json'):
    target = workflows/source.name
    if target.exists() and target.read_bytes() != source.read_bytes():
        backup = root/'user/default/workflow-backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup/target.name)
        print(f'Previous workflow backed up: {backup/target.name}')
    shutil.copy2(source, target)
for source in pathlib.Path('examples/posters/input').glob('*'):
    target = root/'input'/source.name
    if not target.exists():
        shutil.copy2(source, target)
print(f'Workflow: {workflows}')
print('Native ComfyUI generation: no external API, key or shared network required.')
PY
