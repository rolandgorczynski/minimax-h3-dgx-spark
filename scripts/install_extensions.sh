#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
: "${H3_DATA_ROOT:?Run make init first}"
python3 - "${H3_DATA_ROOT}" <<'PY'
import json, pathlib, subprocess, sys, shutil
root = pathlib.Path(sys.argv[1])
for name, spec in json.loads(pathlib.Path('config/extensions.json').read_text()).items():
    dest = root / 'custom_nodes' / name
    if not dest.exists():
        subprocess.run(['git', 'clone', '--filter=blob:none', '--no-checkout', spec['url'], str(dest)], check=True)
        subprocess.run(['git', '-C', str(dest), 'checkout', '--detach', spec['commit']], check=True)
    actual = subprocess.check_output(['git', '-C', str(dest), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != spec['commit']:
        raise SystemExit(f'{name}: existing checkout differs; refusing to overwrite')
    edited = {}
    for edit in spec.get('text_edits', []):
        file = edit['file']
        original = subprocess.check_output(['git', '-C', str(dest), 'show', f'{spec["commit"]}:{file}'])
        expected = edited.get(file, (original, original))[1]
        old, new = edit['old'].encode(), edit['new'].encode()
        if expected.count(old) != 1:
            raise SystemExit(f'{name}: expected integration point missing in {file}')
        edited[file] = (original, expected.replace(old, new, 1))
    for file, (original, expected) in edited.items():
        if (dest / file).read_bytes() not in (original, expected):
            raise SystemExit(f'{name}: local changes in {file}; refusing to overwrite')
    dirty = subprocess.check_output(['git', '-C', str(dest), 'status', '--porcelain'], text=True)
    allowed = set(spec.get('runtime_files', [])) | set(edited)
    if any(line[3:] not in allowed for line in dirty.splitlines()):
        raise SystemExit(f'{name}: local changes; refusing to overwrite')
    for file, (_, expected) in edited.items():
        (dest / file).write_bytes(expected)
    print(f'{name}: {spec["commit"]}')
for name in ('dgx-server-downloads', 'dgx-german-ui', 'dgx-invitations'):
    shutil.copytree(pathlib.Path('extensions') / name, root / 'custom_nodes' / name,
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
translation = root / 'custom_nodes/ComfyUI-Global-Translation/config.json'
config = json.loads(translation.read_text())
config.update(locale='de-DE', translation_enabled=True, translate_options=False)
translation.write_text(json.dumps(config, indent=2) + '\n')
workflows = root / 'user/default/workflows/MiniMax-H3'
workflows.mkdir(parents=True, exist_ok=True)
for source in pathlib.Path('examples/workflows').glob('*.json'):
    shutil.copy2(source, workflows / source.name)
invitations = root / 'user/default/workflows/Einladungen'
invitations.mkdir(parents=True, exist_ok=True)
for source in pathlib.Path('examples/invitations/workflows').glob('*.json'):
    shutil.copy2(source, invitations / source.name)
for source in pathlib.Path('examples/invitations/input').glob('*.png'):
    target = root / 'input' / source.name
    if not target.exists():
        shutil.copy2(source, target)
print(f'Einladungen: {invitations}')
sample = root / 'input/h3_robot_coffee_turbo.mp4'
if not sample.exists():
    shutil.copy2('examples/output/robot-coffee-turbo.mp4', sample)
print(f'Workflows: {workflows}')
settings = root / 'user/default/comfy.settings.json'
values = json.loads(settings.read_text()) if settings.exists() else {}
if values.get('DGX.Translation.Locale') != 'de':
    if settings.exists():
        backup = settings.with_suffix('.json.before-german')
        if not backup.exists():
            shutil.copy2(settings, backup)
    values['DGX.Translation.Locale'] = 'de'
    settings.write_text(json.dumps(values, indent=2) + '\n')
    print('German UI enabled; reload the browser.')
if values.get('Comfy.VueNodes.Enabled') is not False:
    if settings.exists():
        backup = settings.with_suffix('.json.before-extensions')
        if not backup.exists():
            shutil.copy2(settings, backup)
    values['Comfy.VueNodes.Enabled'] = False
    settings.write_text(json.dumps(values, indent=2) + '\n')
    print('Classic canvas enabled for rgthree compatibility; reload the browser.')
PY
