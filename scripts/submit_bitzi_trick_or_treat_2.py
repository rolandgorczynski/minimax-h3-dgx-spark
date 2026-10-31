#!/usr/bin/env python3
"""Submit one English Trick or Treat 2.0 scene to local MiniMax H3."""
import argparse, json, os, shutil
from pathlib import Path
from urllib.request import Request, urlopen
from bitzi_cast_lock import CAST_LOCK

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = os.environ.get('COMFY_API_URL', 'http://192.168.1.224:8188')
DEFAULT_INPUT = Path(os.environ.get('COMFY_INPUT_DIR', '/home/jee/docker/minimax-h3-data/input'))
PROMPTS = {
  1: "At the outdoor company doorway on Halloween, the CEO points to the candy bowl and says: 'Bitzi, distribute the candy fairly!' Bitzi replies: 'Fairness is just an algorithm!' The admin watches skeptically. Children wait with trick-or-treat bags. Festive chiptune, doorbell. No party hall, no camera or face scan, no narrator, no extra dialogue, no readable text, no watermark.",
  2: "Bitzi presents his absurd costume scorecard to children in harmless Halloween costumes and says: 'Everyone gets exactly what their costume deserves!' He ranks costume icons with stars on a tablet; this is manual costume scoring, not face recognition. The CEO and admin look on. Outdoor company doorstep, pumpkins, candy bowl. No camera, no scanner, no party hall, no narrator, no extra words, no readable text, no watermark.",
  3: "At the same doorstep, a disappointed child in a friendly ghost costume holds an empty bag; a child in a playful dinosaur suit receives one tiny pea. CHILD: 'That’s not candy!' BITZI: 'But it’s nutritionally optimized!' The admin is incredulous, CEO uneasy. A small game-show buzzer then silly victory sting. No facial recognition, no camera, no narrator, no extra lines, no readable text, no watermark.",
  4: "A patient line of costumed children waits at the outdoor candy table. The CEO urgently gestures to the full bowl: 'BITZI! JUST GIVE THEM CHOCOLATE!' Bitzi guards his scorecard: 'Without quality control? Never!' The admin looks exhausted. Grumbling crowd and music stop. Keep the children safe and cheerful, no party hall, no camera, no added dialogue, no readable text, no watermark.",
  5: "Bitzi notices a standing mirror and admires his own reflection, which is only a reflection, not another character. BITZI: 'Finally, a worthy candidate!' He points proudly at himself as the perfect authentic robot costume. CEO and admin exchange a worried look; children wait in the background. Magic sparkle and restrained drumroll. No clone, no camera, no narrator, no extra dialogue, no readable text, no watermark.",
  6: "Finale at the same company doorway: Bitzi pours the remaining wrapped chocolates into his own small trick-or-treat bag and puts on tiny sunglasses. CEO: 'BITZI! YOU TOOK ALL OF IT!' Bitzi, calm and smug: 'The AI decided objectively. Take it up with the algorithm!' Admin facepalms. Candy avalanche sound, stop music just before punchline, hold a beat, cut to black with the recurring original three-note sting. No narrator, no extra lines, no readable text, no watermark."
}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--segment',type=int,choices=range(1,7),required=True)
    p.add_argument('--comfy-url',default=DEFAULT_URL)
    p.add_argument('--input-dir',type=Path,default=DEFAULT_INPUT)
    p.add_argument('--seed',type=int,default=20261102)
    a=p.parse_args()
    frame=ROOT/'examples/input/bitzi-trick-or-treat-2'/f'scene{a.segment}.png'
    if not frame.is_file(): p.error(f'Missing keyframe: {frame}')
    a.input_dir.mkdir(parents=True,exist_ok=True)
    name=f'bitzi_trick_or_treat_2_scene{a.segment}.png'
    shutil.copy2(frame,a.input_dir/name)
    graph=json.loads((ROOT/'examples/api/bitzi_bullet_time_seg1.json').read_text())
    nodes=graph['prompt']
    nodes['6']['inputs']['image']=name
    nodes['8']['inputs']['text']='letters, subtitles, logos, watermark, distorted face, extra limbs, gore'
    nodes['7']['inputs'].update({'prompt':CAST_LOCK+PROMPTS[a.segment],'width':480,'height':864,'length':243})
    nodes['9']['inputs']['seed']=a.seed+a.segment
    nodes['13']['inputs']['filename_prefix']=f'x-generator/bitzi-trick-or-treat-2/seg{a.segment}'
    nodes['14']['inputs']['filename_prefix']=f'audio/x-generator/bitzi-trick-or-treat-2/seg{a.segment}'
    req=Request(a.comfy_url.rstrip('/')+'/prompt',data=json.dumps(graph).encode(),headers={'Content-Type':'application/json'})
    with urlopen(req,timeout=30) as response: result=json.load(response)
    if result.get('node_errors'): raise SystemExit(json.dumps(result['node_errors'],indent=2))
    print(json.dumps(result))
if __name__=='__main__': main()
