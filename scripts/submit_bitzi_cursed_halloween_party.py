#!/usr/bin/env python3
"""Submit one Cursed Halloween Party scene to the local MiniMax H3 workflow."""
import argparse
import json
import os
import shutil
from pathlib import Path
from urllib.request import Request, urlopen

from bitzi_cast_lock import CAST_LOCK

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = os.environ.get('COMFY_API_URL', 'http://192.168.1.224:8188')
DEFAULT_INPUT = Path(os.environ.get('COMFY_INPUT_DIR', '/home/jee/docker/minimax-h3-data/input'))
PROMPTS = {
    1: "Halloween office party. CEO hands Bitzi a guest list. CEO: 'Bitzi, organize a Halloween party. Only invited guests get in!' Bitzi jumps up: 'I’ll use cutting-edge AI!' Admin watches, dryly skeptical. Festive chiptune, party bell. Clear English dialogue, no narrator, no extra lines, no readable screen text, no watermark.",
    2: "At the party entrance, Bitzi scans costumed guests wearing wigs, fake moustaches and vampire makeup, using one executive photo. The scanner gives each a green match icon. Bitzi: 'One executive photo. Infinite executive recognition!' Admin: 'That is not how identity works.' CEO observes. Scanner pings accelerate into a silly fanfare. No narrator, no extra lines, no readable words, no watermark.",
    3: "The scanner rolls out a red carpet for every costumed guest; a long queue forms. Bitzi dances proudly: 'The VIP list is working perfectly!' Admin, exasperated: 'You’ve made everyone the CEO!' CEO watches the absurd line. Overblown VIP fanfare ends in a record scratch. No narrator, no extra dialogue, no readable text, no watermark.",
    4: "At the crowded Halloween buffet, the CEO sees an absurdly long paper receipt draped over stacks of empty catering trays. No currency, payment card, account details, or readable writing. CEO: 'Why is my account paying for fifty people?' Bitzi: 'Executive hospitality. At scale!' Admin looks at the receipt in disbelief. Cha-ching sounds become silly and rapid, kept low under clear English dialogue. No narrator, no extra lines, no watermark.",
    5: "The real CEO arrives without a costume at the party scanner. A red X icon flashes; costumed guests turn to stare. CEO: 'Bitzi, I’m the actual CEO!' Bitzi points confidently: 'That’s exactly what an impostor would say.' Admin looks alarmed. Spooky sting and one dry error beep. No narrator, no added words, no readable screen text, no watermark.",
    6: "Final scene: costumed guests gently escort the confused CEO toward the open exit. Bitzi pins a VIP badge on himself; scanner gives a simple crown icon. Admin asks: 'Who’s in charge now?' Bitzi: 'Apparently, all of us.' Music stops before the line. Hold one beat, cut to black with the original three-note electronic signature. Clear English dialogue, no narrator, no extra lines, no readable text, no watermark.",
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--segment', type=int, choices=range(1, 7), required=True)
    parser.add_argument('--comfy-url', default=DEFAULT_URL)
    parser.add_argument('--input-dir', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--seed', type=int, default=20261101)
    args = parser.parse_args()
    frame = ROOT / 'examples' / 'input' / 'bitzi-cursed-halloween-party' / f'scene{args.segment}.png'
    if not frame.is_file():
        parser.error(f'Missing keyframe: {frame}')
    args.input_dir.mkdir(parents=True, exist_ok=True)
    image_name = f'bitzi_cursed_halloween_party_scene{args.segment}.png'
    shutil.copy2(frame, args.input_dir / image_name)
    payload = json.loads((ROOT / 'examples' / 'api' / 'bitzi_bullet_time_seg1.json').read_text())
    nodes = payload['prompt']
    nodes['6']['inputs']['image'] = image_name
    nodes['8']['inputs']['text'] = 'letters, subtitles, logos, watermark, distorted face, extra limbs, gore'
    nodes['7']['inputs'].update({'prompt': CAST_LOCK + PROMPTS[args.segment], 'width': 480, 'height': 864, 'length': 243})
    nodes['9']['inputs']['seed'] = args.seed + args.segment
    nodes['13']['inputs']['filename_prefix'] = f'x-generator/bitzi-cursed-halloween-party/seg{args.segment}'
    nodes['14']['inputs']['filename_prefix'] = f'audio/x-generator/bitzi-cursed-halloween-party/seg{args.segment}'
    request = Request(args.comfy_url.rstrip('/') + '/prompt', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get('node_errors'):
        raise SystemExit(json.dumps(result['node_errors'], indent=2))
    print(json.dumps(result))

if __name__ == '__main__':
    main()
