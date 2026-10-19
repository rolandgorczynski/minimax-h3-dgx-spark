#!/usr/bin/env bash
set -Eeuo pipefail
# One-time download. Captioning itself subsequently uses local files only.
docker exec -i minimax-h3-comfyui python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download('HuggingFaceTB/SmolVLM-500M-Instruct',
    revision='a7da5b986cb59b408707209984f360a5f4ad7e47',
    local_dir='/opt/ComfyUI/models/vision/SmolVLM-500M-Instruct',
    allow_patterns=['*.json', '*.txt', 'model.safetensors', 'README.md'])
print('Vision model downloaded; ready for offline image captioning.')
PY
