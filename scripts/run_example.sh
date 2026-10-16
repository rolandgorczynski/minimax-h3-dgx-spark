#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
case "${1:-}" in
  extension_smoke|turbo_draft|video_upscale_x2) example="$1" ;;
  *) echo "Usage: $0 extension_smoke|turbo_draft|video_upscale_x2" >&2; exit 2 ;;
esac
bind="${COMFYUI_BIND:-127.0.0.1}"
[[ "${bind}" != "0.0.0.0" ]] || bind=127.0.0.1
python3 - "examples/api/${example}.json" "http://${bind}:${COMFYUI_PORT:-8188}" <<'PY'
import json, pathlib, sys, urllib.request, urllib.error
prompt = json.loads(pathlib.Path(sys.argv[1]).read_text())
request = urllib.request.Request(
    sys.argv[2] + '/prompt',
    data=json.dumps({'prompt': prompt, 'client_id': 'h3-examples'}).encode(),
    headers={'Content-Type': 'application/json'},
)
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        print(json.dumps(json.load(response), indent=2))
except urllib.error.HTTPError as error:
    print(error.read().decode(), file=sys.stderr)
    raise SystemExit(1)
PY
