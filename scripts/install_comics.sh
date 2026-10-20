#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
: "${H3_DATA_ROOT:?Run make init first}"
python3 - "$H3_DATA_ROOT" <<'PY'
from datetime import datetime
from pathlib import Path
import shutil
import sys
root = Path(sys.argv[1])
for name in ('dgx-invitations', 'dgx-comics'):
    shutil.copytree(Path('extensions')/name, root/'custom_nodes'/name,
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
workflows = root/'user/default/workflows/Comics'
workflows.mkdir(parents=True, exist_ok=True)
for source in Path('examples/comics/workflows').glob('*.json'):
    target = workflows/source.name
    if target.exists() and target.read_bytes() != source.read_bytes():
        backup = root/'user/default/workflow-backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup/target.name)
    shutil.copy2(source, target)
for source in Path('examples/comics/input').glob('*.png'):
    target = root/'input'/source.name
    if not target.exists():
        shutil.copy2(source, target)
print(f'Comic workflow installed: {workflows}')
print('Uses existing ComfyUI models and packages. Restart ComfyUI once and reload the browser.')
PY
