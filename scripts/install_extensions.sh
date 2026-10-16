#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
: "${H3_DATA_ROOT:?Run make init first}"
python3 - "${H3_DATA_ROOT}" <<'PY'
import json, pathlib, subprocess, sys, shutil
root = pathlib.Path(sys.argv[1])
for name, spec in json.loads(pathlib.Path('config/extensions.json').read_text()).items():
    dest = root / 'custom_nodes' / name
    if dest.exists():
        actual = subprocess.check_output(['git', '-C', str(dest), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != spec['commit']:
            raise SystemExit(f'{name}: existing checkout differs; refusing to overwrite')
        if subprocess.check_output(['git', '-C', str(dest), 'status', '--porcelain'], text=True).strip():
            raise SystemExit(f'{name}: local changes; refusing to overwrite')
    else:
        subprocess.run(['git', 'clone', '--filter=blob:none', '--no-checkout', spec['url'], str(dest)], check=True)
        subprocess.run(['git', '-C', str(dest), 'checkout', '--detach', spec['commit']], check=True)
    print(f'{name}: {spec["commit"]}')
shutil.copytree('extensions/dgx-server-downloads', root / 'custom_nodes/dgx-server-downloads',
                dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
workflows = root / 'user/default/workflows/MiniMax-H3'
workflows.mkdir(parents=True, exist_ok=True)
for source in pathlib.Path('examples/workflows').glob('*.json'):
    shutil.copy2(source, workflows / source.name)
sample = root / 'input/h3_robot_coffee_turbo.mp4'
if not sample.exists():
    shutil.copy2('examples/output/robot-coffee-turbo.mp4', sample)
print(f'Workflows: {workflows}')
settings = root / 'user/default/comfy.settings.json'
values = json.loads(settings.read_text()) if settings.exists() else {}
if values.get('Comfy.VueNodes.Enabled') is not False:
    if settings.exists():
        backup = settings.with_suffix('.json.before-extensions')
        if not backup.exists():
            shutil.copy2(settings, backup)
    values['Comfy.VueNodes.Enabled'] = False
    settings.write_text(json.dumps(values, indent=2) + '\n')
    print('Classic canvas enabled for rgthree compatibility; reload the browser.')
PY
