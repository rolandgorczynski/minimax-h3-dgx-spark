#!/usr/bin/env python3
"""Submit one 15-second Bitzi bullet-time segment to local ComfyUI MiniMax H3."""
import argparse
import json
import os
import shutil
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / 'examples' / 'api'
DEFAULT_INPUT_DIR = Path('/home/jee/docker/minimax-h3-data/input')
DEFAULT_URL = 'http://192.168.1.224:8188'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--segment', type=int, choices=(1, 2), required=True)
    parser.add_argument('--first-frame', type=Path)
    parser.add_argument('--comfy-url', default=os.environ.get('COMFY_API_URL', DEFAULT_URL))
    parser.add_argument('--input-dir', type=Path, default=Path(os.environ.get('COMFY_INPUT_DIR', DEFAULT_INPUT_DIR)))
    args = parser.parse_args()
    default_frame = ROOT / 'examples' / 'input' / 'bitzi_bullet_time_keyframe.png'
    frame = args.first_frame or default_frame
    if not frame.is_file():
        parser.error(f'First-frame image not found: {frame}')
    args.input_dir.mkdir(parents=True, exist_ok=True)
    image_name = f'bitzi_bullet_time_segment_{args.segment}_first_frame{frame.suffix.lower()}'
    shutil.copy2(frame, args.input_dir / image_name)

    payload = json.loads((API_DIR / f'bitzi_bullet_time_seg{args.segment}.json').read_text())
    payload['prompt']['6']['inputs']['image'] = image_name
    request = Request(
        args.comfy_url.rstrip('/') + '/prompt',
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'},
    )
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get('node_errors'):
        raise SystemExit(json.dumps(result['node_errors'], indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
