#!/usr/bin/env python3
"""Render six scenes locally in order and assemble the Cursed Halloween Party film."""
import argparse, json, subprocess, sys, time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
def get(url):
    with urlopen(url, timeout=20) as response: return json.load(response)
def wait(base_url, prompt_id):
    while True:
        entry = get(f'{base_url}/history/{prompt_id}').get(prompt_id)
        if entry:
            if entry.get('status', {}).get('status_str') == 'error': raise RuntimeError(json.dumps(entry['status']))
            return
        queue = get(base_url + '/queue')
        queued = [item[1] for key in ('queue_running', 'queue_pending') for item in queue.get(key, [])]
        if prompt_id not in queued: raise RuntimeError(f'ComfyUI dropped job {prompt_id} without history')
        time.sleep(20)
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comfy-url', default='http://192.168.1.224:8188')
    parser.add_argument('--input-dir', type=Path, default=Path('/home/jee/docker/minimax-h3-data/input'))
    parser.add_argument('--output-dir', type=Path, default=Path('/home/jee/docker/minimax-h3-data/output'))
    args = parser.parse_args(); base = args.comfy_url.rstrip('/')
    output = args.output_dir / 'x-generator' / 'bitzi-cursed-halloween-party'
    for scene in range(1, 7):
        result = subprocess.run([sys.executable, str(ROOT/'scripts/submit_bitzi_cursed_halloween_party.py'), '--segment', str(scene), '--comfy-url', base, '--input-dir', str(args.input_dir)], capture_output=True, text=True, check=True)
        prompt_id = json.loads(result.stdout)['prompt_id']; print(f'Scene {scene}/6 queued: {prompt_id}', flush=True)
        wait(base, prompt_id)
        if not list(output.glob(f'seg{scene}_*.mp4')): raise FileNotFoundError(f'No scene {scene} MP4 in {output}')
        if not list(args.output_dir.glob(f'audio/x-generator/bitzi-cursed-halloween-party/seg{scene}_*.flac')): raise FileNotFoundError(f'No scene {scene} audio')
        print(f'Scene {scene}/6 complete', flush=True)
    final = output/'bitzi_cursed_halloween_party.mp4'
    subprocess.run([sys.executable, str(ROOT/'scripts/assemble_bitzi_cursed_halloween_party.py'), '--input-dir', str(args.output_dir), '--output', str(final)], check=True)
    print(f'Film complete: {final}', flush=True)
if __name__ == '__main__': main()
