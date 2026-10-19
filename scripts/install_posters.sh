#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
: "${H3_DATA_ROOT:?Run make init first}"
python3 - "$H3_DATA_ROOT" "${1:-/home/jee/docker/flux-klein-spark/.env}" <<'PY'
import json, pathlib, shutil, sys
root = pathlib.Path(sys.argv[1])
for name in ('dgx-invitations', 'dgx-posters'):
    shutil.copytree(pathlib.Path('extensions') / name, root/'custom_nodes'/name,
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
workflows = root/'user/default/workflows/Plakaty'
workflows.mkdir(parents=True, exist_ok=True)
for source in pathlib.Path('examples/posters/workflows').glob('*.json'):
    target = workflows/source.name
    if target.exists() and target.read_bytes() != source.read_bytes():
        raise SystemExit(f'{target}: local changes; refusing to overwrite')
    shutil.copy2(source, target)
for source in pathlib.Path('examples/posters/input').glob('*'):
    target = root/'input'/source.name
    if not target.exists():
        shutil.copy2(source, target)
config = root/'user/default/dgx-posters.json'
if not config.exists():
    values = {}
    for line in pathlib.Path(sys.argv[2]).read_text().splitlines():
        key, sep, value = line.partition('=')
        if sep and key.strip() == 'FLUX_API_KEY':
            values[key.strip()] = value.strip().strip('\"\'')
    token = values.get('FLUX_API_KEY', '')
    if len(token) < 32:
        raise SystemExit('Missing FLUX_API_KEY in local FLUX .env')
    config.touch(mode=0o600)
    config.write_text(json.dumps({'url': 'http://flux-image:7862/v1', 'api_key': token})+'\n')
print(f'Workflow: {workflows}')
print('Local FLUX configuration installed; key is not stored in the workflow.')
PY
