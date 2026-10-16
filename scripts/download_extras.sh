#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
for group in r2v turbo effects; do
  docker compose run --rm --no-deps --entrypoint python comfyui /usr/local/bin/h3-download-models "${group}"
done
python3 - "${H3_DATA_ROOT}/input" <<'PY'
from pathlib import Path
import sys, urllib.request, shutil
root = Path(sys.argv[1])
root.mkdir(parents=True, exist_ok=True)
base = 'https://raw.githubusercontent.com/Comfy-Org/workflow_templates/04a508b31bec1818e48122ca0761c1de4140a234/input/'
for name in ('mecha_dragon_lightning.png', 'red_superboy_on_city_roof.png', 'transparent_rgb_gaming_mouse.png'):
    dest = root / name
    if dest.exists():
        continue
    temporary = dest.with_suffix('.download')
    with urllib.request.urlopen(base + name, timeout=120) as source, temporary.open('wb') as target:
        shutil.copyfileobj(source, target)
    temporary.replace(dest)
    print(dest)
dest = root.parent / 'models/upscale_models/RealESRGAN_x2plus.pth'
expected_size = 67061725
if not dest.exists() or dest.stat().st_size != expected_size:
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_suffix('.pth.download')
    url = 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth'
    with urllib.request.urlopen(url, timeout=120) as source, temporary.open('wb') as target:
        shutil.copyfileobj(source, target)
    if temporary.stat().st_size != expected_size:
        raise SystemExit('Incomplete Real-ESRGAN model download')
    temporary.replace(dest)
    print(dest)
PY
