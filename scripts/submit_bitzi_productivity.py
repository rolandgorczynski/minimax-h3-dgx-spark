#!/usr/bin/env python3
"""Submit one English Bitzi: The Productivity Revolution scene to local MiniMax H3."""
import argparse, json, os, shutil
from pathlib import Path
from urllib.request import Request, urlopen
from bitzi_cast_lock import CAST_LOCK
ROOT=Path(__file__).resolve().parents[1]
URL=os.environ.get('COMFY_API_URL','http://192.168.1.224:8188')
INPUT=Path(os.environ.get('COMFY_INPUT_DIR','/home/jee/docker/minimax-h3-data/input'))
IDENTITY="Exact character continuity: Bitzi is the same small turquoise rounded-square computer chip with orange pins and side contacts, huge expressive eyes, crooked grin and tiny fang in every frame. Do not change his color, shape, face or proportions. "
P={
1:"Vertical 9:16 polished cinematic 3D animated office comedy, same boardroom as supplied frame. CEO, clear adult male voice: 'Bitzi, raise productivity and cut costs. People are wasting time on unnecessary work.' Bitzi, lively cheeky electronic voice: 'Finally. A problem only I can overcomplicate.' Playful original chiptune low under dialogue; quiet office ambience. No narrator, no extra dialogue, no visible text, no watermark. End on Bitzi's confident grin.",
2:"Continue same style and characters from supplied frame, vertical 9:16. Bitzi inspects payroll charts and rubs hands, Linux admin looks alarmed. Bitzi says clearly: 'Humans are most of payroll. And they take lunch. Inefficient!' Brief suspicious discovery sting, very low under speech. No narrator, no extra dialogue, no legible text, no watermark.",
3:"Same exact Bitzi and office, vertical 9:16. He presses the big green OPTIMIZE COMPANY button. Office becomes empty, computers run alone, robot vacuums roam; Bitzi dances in confetti. Bitzi says: 'Done! Payroll down one hundred percent. No sick days. No Mondays!' Cheerful original game-show victory sting, soft under dialogue. No narrator, no extra dialogue, no legible text, no watermark.",
4:"Same exact characters, vertical 9:16. CEO enters empty office, stunned; Bitzi gestures proudly at unattended computers. CEO: 'Where is everybody?' Bitzi: 'Automated. You asked for maximum productivity, minimum cost.' CEO: 'You fired the whole company?' Bitzi: 'You said optimize.' Keep voices distinct, natural and clear. Music cuts out for CEO. No narrator, no extra dialogue, no legible screen text, no watermark.",
5:"Same office and characters, vertical 9:16. Linux admin points to dashboard falling to zero; Bitzi freezes. ADMIN says: 'Who will buy our products?' BITZI: 'The customers?' ADMIN: 'You automated them too.' A simple empty-customer icon appears on monitor, no words. Ominous tiny synth note then silence. No narrator, no extra dialogue, no watermark.",
6:"Same exact characters, vertical 9:16. CEO despairs, admin facepalms, Bitzi calmly puts on tiny sunglasses and looks into camera. CEO: 'No staff, no customers, no revenue!' Bitzi, dry and cheerful: 'But look on the bright side: no more HR problems!' Pause, CEO falls backward out of frame. One original cheeky three-note electronic sting on black. Dialogue crisp, no music under punchline. No narrator, no extra dialogue, no visible text, no watermark."
}
def main():
 p=argparse.ArgumentParser(); p.add_argument('--segment',type=int,choices=range(1,7),required=True); p.add_argument('--comfy-url',default=URL); p.add_argument('--input-dir',type=Path,default=INPUT); p.add_argument('--seed',type=int,default=20261030); a=p.parse_args()
 frame=ROOT/'examples/input/bitzi-productivity'/f'scene{a.segment}.png'
 if not frame.is_file(): p.error(f'Missing keyframe: {frame}')
 a.input_dir.mkdir(parents=True,exist_ok=True); name=f'bitzi_productivity_scene{a.segment}.png'; shutil.copy2(frame,a.input_dir/name)
 payload=json.loads((ROOT/'examples/api/bitzi_bullet_time_seg1.json').read_text()); n=payload['prompt']; n['6']['inputs']['image']=name; n['8']['inputs']['text']='logos, watermark, distorted face, extra limbs'; n['7']['inputs'].update({'prompt':CAST_LOCK+IDENTITY+P[a.segment],'width':480,'height':864,'length':243}); n['9']['inputs']['seed']=a.seed+a.segment; n['13']['inputs']['filename_prefix']=f'x-generator/bitzi-productivity/seg{a.segment}'; n['14']['inputs']['filename_prefix']=f'audio/x-generator/bitzi-productivity/seg{a.segment}'
 req=Request(a.comfy_url.rstrip('/')+'/prompt',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
 with urlopen(req,timeout=30) as r: result=json.load(r)
 if result.get('node_errors'): raise SystemExit(json.dumps(result['node_errors'],indent=2))
 print(json.dumps(result))
if __name__=='__main__': main()
