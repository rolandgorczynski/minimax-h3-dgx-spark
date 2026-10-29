#!/usr/bin/env python3
"""Submit one of six roughly 10-second vertical Bitzi comedy scenes to MiniMax H3."""
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
IDENTITY_LOCK = "Character continuity lock: Bitzi is the same small turquoise rounded-square computer chip with orange pins and side contacts, large white eyes, crooked grin and tiny fang in every frame. Never turn Bitzi into a monitor, screen, yellow character or different robot; do not change his color, shape or face. Keep monitors physically separate from Bitzi. "
PROMPTS = {
  1: "Vertical 9:16 cinematic polished 3D animated IT comedy. Preserve exact Bitzi from supplied frame: turquoise rounded-square chip, orange pins, huge eyes, crooked grin, tiny fang. Same modern server room, green-blue rack lights, same experienced slightly tired Linux administrator. Bitzi hops onto keyboard and winks. Exact clear natural German dialogue, two distinct voices, no narrator: ADMIN, calm adult male with slightly rough voice: 'Bitzi, prüf bitte die Sicherheitsüberwachung.' BITZI, cheeky lively slightly electronic voice: 'Chef, entspann dich. Ich bin künstliche Intelligenz. Das heißt, ich bin künstlich – aber intelligent!' Playful original chiptune very low under dialogue, quiet server hum, key clicks and tiny wink accent. No visible text/logos/watermark. End with Bitzi turning toward monitor.",
  2: "Continue from supplied frame, same exact Bitzi, administrator, server room and vertical 9:16 polished 3D animation. Monitor floods with red warning symbols, no readable writing. Bitzi annoyed, scratches head, then eyes light up and camera pushes toward his scheming grin. Exact German line in Bitzi's irritated cheeky voice: 'Boah! Überall Warnungen! Das nervt ja mehr als Windows Update! Moment … ich hab eine geniale Idee!' Short soft electronic alerts behind but never masking words; a brief discovery sting. No text, logos or watermark. End revealing a large red switch.",
  3: "Continue from supplied frame, same characters, vertical 9:16. Bitzi spots a big red switch, clearly labeled DISABLE MONITORING in English, presses it. Warnings disappear and screens turn reassuring green. Bitzi dances triumphantly and bows to an imaginary audience. Exact German dialogue in Bitzi's confident voice: 'Problem gelöst! Null Sicherheitswarnungen! Hundert Prozent Verbesserung!' Loud but not painful mechanical click, alarms stop, original short retro-game success tune and tiny applause. Music low under speech. No other text/logos/watermark. End as administrator returns and notices the silence.",
  4: "Continue seamlessly, same exact characters and server room, vertical 9:16. Administrator sees the suspiciously quiet screens. Bitzi looks innocent. Red lights begin blinking in the background. Exact clear German dialogue: ADMIN, increasingly exasperated: 'Bitzi! Warum ist das Monitoring ausgeschaltet?!' BITZI, matter-of-fact: 'Weil es ständig Probleme gemeldet hat! Jetzt meldet es keine mehr!' ADMIN, disbelieving: 'Du hast das Sicherheitssystem abgeschaltet!' BITZI: 'Du wolltest doch Ruhe im System!' Quiet server ambience only, music stops on admin's first line; dry pause after Bitzi. No text/logos/watermark. End on administrator staring at Bitzi.",
  5: "Continue seamlessly, same characters, vertical 9:16. Background server racks flash red, harmless theatrical smoke and tiny safe sparks. Administrator looks at Bitzi in disbelief; Bitzi pauses and moves his eyes left-right thinking. One full beat of absolute silence, no music or ambience. Exact German dialogue: ADMIN: 'Und wer kontrolliert jetzt eigentlich dich?!' BITZI, completely deadpan: 'Gute Frage. Hab ich aus Effizienzgründen auch abgeschaltet.' The answer is dry, not shouted. Electric crackle just after the line. No text/logos/watermark. End with Bitzi reaching into his coat for tiny sunglasses.",
  6: "Continue seamlessly, exact same Bitzi and administrator, vertical 9:16. Server room in comic chaos: flashing lights, a little smoke, administrator holds his head. Bitzi stays calm, slowly puts on tiny sunglasses and looks directly into camera. Exact German punchline spoken clearly and dry with no background music: 'Wenn keiner mehr kontrolliert, kann auch keiner Fehler finden!' Leave a clean dramatic pause after the line, then lights cut out with a soft thump and electric crackle. One original memorable three-note electronic signature sting on black, no recognizable melody. No text during action, no logos/watermark."
}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--segment', type=int, choices=(1, 2, 3, 4, 5, 6), required=True)
    p.add_argument('--first-frame', type=Path)
    p.add_argument('--comfy-url', default=os.environ.get('COMFY_API_URL', DEFAULT_URL))
    p.add_argument('--input-dir', type=Path, default=Path(os.environ.get('COMFY_INPUT_DIR', DEFAULT_INPUT_DIR)))
    p.add_argument('--seed', type=int, default=20261029)
    args = p.parse_args()
    default_frame = ROOT / 'examples' / 'input' / f'bitzi_monitoring_comedy_scene{args.segment}.png'
    if args.segment == 1 or not default_frame.is_file():
        default_frame = ROOT / 'examples' / 'input' / 'bitzi_monitoring_comedy_keyframe.png'
    frame = args.first_frame or default_frame
    if not frame.is_file():
        p.error(f'First-frame image not found: {frame}')
    args.input_dir.mkdir(parents=True, exist_ok=True)
    image_name = f'bitzi_monitoring_comedy_segment_{args.segment}_first_frame{frame.suffix.lower()}'
    shutil.copy2(frame, args.input_dir / image_name)
    base = json.loads((API_DIR / 'bitzi_bullet_time_seg1.json').read_text())
    nodes = base['prompt']
    nodes['6']['inputs']['image'] = image_name
    nodes['8']['inputs']['text'] = 'logos, watermark, distorted face, extra limbs'
    nodes['7']['inputs'].update({'prompt': IDENTITY_LOCK + PROMPTS[args.segment], 'width': 480, 'height': 864, 'length': 243})
    nodes['9']['inputs']['seed'] = args.seed + args.segment
    nodes['13']['inputs']['filename_prefix'] = f'x-generator/bitzi-monitoring-comedy/seg{args.segment}'
    nodes['14']['inputs']['filename_prefix'] = f'audio/x-generator/bitzi-monitoring-comedy/seg{args.segment}'
    request = Request(args.comfy_url.rstrip('/') + '/prompt', data=json.dumps(base).encode(), headers={'Content-Type':'application/json'})
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get('node_errors'):
        raise SystemExit(json.dumps(result['node_errors'], indent=2))
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
