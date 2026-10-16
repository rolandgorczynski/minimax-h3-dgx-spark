#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
for group in r2v turbo effects; do
  docker compose run --rm --no-deps --entrypoint python comfyui /usr/local/bin/h3-download-models "${group}"
done
python3 - "${H3_DATA_ROOT}/input" <<'PY'
from pathlib import Path
import sys, urllib.request, shutil, hashlib
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
expected_sha = '49fafd45f8fd7aa8d31ab2a22d14d91b536c34494a5cfe31eb5d89c2fa266abb'
def verified(path):
    return (path.is_file() and path.stat().st_size == expected_size
            and hashlib.sha256(path.read_bytes()).hexdigest() == expected_sha)
if not verified(dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_suffix('.pth.download')
    url = 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth'
    with urllib.request.urlopen(url, timeout=120) as source, temporary.open('wb') as target:
        shutil.copyfileobj(source, target)
    if not verified(temporary):
        raise SystemExit('Real-ESRGAN model checksum mismatch')
    temporary.replace(dest)
    print(dest)
PY
