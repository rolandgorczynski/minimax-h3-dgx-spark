#!/usr/bin/env python3
"""Submit one English Bitzi: The Zombie Processes scene to local MiniMax H3."""
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
    1: "Vertical 9:16 polished cinematic 3D animated Halloween IT comedy. Same office server room and exact recurring cast from the keyframe. ADMIN, calm and practical: 'Bitzi, take care of the zombie processes.' BITZI, delighted: 'Finally! A real Halloween mission!' CEO remains a silent, worried observer. Outside the window, children in friendly zombie costumes pass by. Soft spooky chiptune, keyboard taps, no scary violence. Clear English dialogue, no narrator, no extra lines, no readable screen text, no watermark.",
    2: "Continue with the same exact Bitzi, Linux administrator and CEO from the keyframe; same server room, faces, clothes and voices. The CEO watches silently. Bitzi inspects a process tree with simple icons and points at one dead child process. BITZI: 'The undead are everywhere!' ADMIN, patient and technically precise: 'Those processes have already exited. Their parent still has to collect the exit status.' Spooky radar pings and a restrained drum cue stay low under speech. No narrator, no added words, no readable screen text, no watermark.",
    3: "Continue seamlessly, same exact recurring cast and server room. Bitzi presses a large red control; the process tree and service icons vanish from the monitor. The administrator reaches too late; the CEO silently gasps. BITZI, pleased with himself: 'No parents, no zombies. I have simplified the family tree!' A heavy but soft click, short heroic chiptune, then a comic pause. Keep voices distinct and dialogue clear. No narrator, no extra lines, no readable text, no watermark.",
    4: "Same exact Bitzi, administrator and CEO; same office and costumes. The terminal looks nearly empty. ADMIN, controlled but alarmed: 'Bitzi! You killed every important process!' BITZI, matter-of-fact: 'Casualties in the war against the undead.' The CEO stares at the empty screen, speechless. Music drops out for the admin's response; one quiet error tone. No narrator, no extra dialogue, no readable screen text, no watermark.",
    5: "Continue same scene with all three recurring characters and locked identities. The administrator restarts the service. A child-process icon appears and then a small red defunct marker; the parent service remains running. The CEO watches, concerned. BITZI, startled: 'It came back!' ADMIN, explaining the actual cause: 'The restarted service did the same thing: spawned a child and never collected its exit status.' Ominous synth builds gently; dialogue stays fully clear. No narrator, no extra lines, no readable text, no watermark.",
    6: "Final scene, same exact Bitzi, administrator and CEO from the supplied frame. Empty process monitor in the same server room. ADMIN, exhausted but calm: 'What exactly was your plan?' BITZI raises a pumpkin like a trophy, puts on his tiny sunglasses and says with cheerful deadpan: 'An operating system with no living processes. Mission accomplished!' The CEO silently facepalms. Leave one beat of silence, then cut to black with the original three-note electronic sting. No narrator, no extra dialogue, no visible lettering, no watermark.",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--segment', type=int, choices=range(1, 7), required=True)
    parser.add_argument('--comfy-url', default=DEFAULT_URL)
    parser.add_argument('--input-dir', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--seed', type=int, default=20261031)
    args = parser.parse_args()

    frame = ROOT / 'examples' / 'input' / 'bitzi-zombie-processes' / f'scene{args.segment}.png'
    if not frame.is_file():
        parser.error(f'Missing keyframe: {frame}')
    args.input_dir.mkdir(parents=True, exist_ok=True)
    image_name = f'bitzi_zombie_processes_scene{args.segment}.png'
    shutil.copy2(frame, args.input_dir / image_name)

    payload = json.loads((ROOT / 'examples' / 'api' / 'bitzi_bullet_time_seg1.json').read_text())
    nodes = payload['prompt']
    nodes['6']['inputs']['image'] = image_name
    nodes['8']['inputs']['text'] = 'letters, subtitles, logos, watermark, distorted face, extra limbs, gore'
    nodes['7']['inputs'].update({
        'prompt': CAST_LOCK + PROMPTS[args.segment],
        'width': 480, 'height': 864, 'length': 243,
    })
    nodes['9']['inputs']['seed'] = args.seed + args.segment
    nodes['13']['inputs']['filename_prefix'] = f'x-generator/bitzi-zombie-processes/seg{args.segment}'
    nodes['14']['inputs']['filename_prefix'] = f'audio/x-generator/bitzi-zombie-processes/seg{args.segment}'
    request = Request(args.comfy_url.rstrip('/') + '/prompt', data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get('node_errors'):
        raise SystemExit(json.dumps(result['node_errors'], indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
