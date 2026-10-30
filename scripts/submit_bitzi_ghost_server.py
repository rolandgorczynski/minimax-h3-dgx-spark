#!/usr/bin/env python3
"""Submit one English Bitzi: The Ghost in the Server scene to local MiniMax H3."""
import argparse,json,os,shutil
from pathlib import Path
from urllib.request import Request,urlopen
from bitzi_cast_lock import CAST_LOCK
ROOT=Path(__file__).resolve().parents[1];URL=os.environ.get('COMFY_API_URL','http://192.168.1.224:8188');INPUT=Path(os.environ.get('COMFY_INPUT_DIR','/home/jee/docker/minimax-h3-data/input'))
LOCK="Exact character continuity: Bitzi is the same small turquoise rounded-square computer chip with orange pins and side contacts, huge expressive eyes, crooked grin and tiny fang. Keep exact same shape, color and proportions. "
P={
1:"Vertical 9:16 polished cinematic 3D animated Halloween IT comedy. Same server room and characters as supplied frame. ADMIN, practical adult male: 'Bitzi, please remove the old ghost accounts!' BITZI, cheeky and delighted: 'It's Halloween. Ghosts are my specialty!' Pumpkin lights flicker, one howling wind effect and a heroic electronic sting. Two clear distinct voices, no narrator, no extra dialogue, no visible words, no watermark.",
2:"Continue seamlessly with exact same characters and server room, vertical 9:16. Bitzi investigates user profile icons and old permissions on server monitors; a pumpkin rolls past. BITZI: 'The ghosts live inside the accounts!' ADMIN, dryly: 'Those are former employees!' Spooky synth and quiet scanning sounds under dialogue. No narrator, no extra lines, no readable text, no watermark.",
3:"Same exact Bitzi and server room, vertical 9:16. Bitzi presses a bright button; many account profile icons vanish from the monitors. Bitzi celebrates as cobweb confetti falls. BITZI: 'EXORCISED! This network is officially ghost-free!' Funny bell toll and short victory jingle, low under voice. No narrator, no extra dialogue, no readable text, no watermark.",
4:"Continue same scene, characters and vertical 9:16. Administrator tries to log in, receives an empty profile screen. CEO looks worried; Bitzi gestures proudly at blank monitors. ADMIN: 'You deleted every account!' BITZI: 'Every single one. I'm thorough.' Music stops for a beat. Two distinct clear voices, no narrator, no extra lines, no readable text, no watermark.",
5:"Same server room and characters, vertical 9:16. After all account icons vanish, one mysterious active session glow remains on a server screen. Administrator points in alarm. ADMIN: 'Then why is the ghost still online?' BITZI, surprised: 'Oh. Apparently it had root access.' Ominous bass, short pause after the line. No narrator, no extra dialogue, no legible text, no watermark.",
6:"Same exact Bitzi, CEO, administrator, server room and vertical 9:16. Empty login windows float in the background; Bitzi calmly puts on tiny sunglasses. CEO: 'How do we get back in?!' BITZI, cheerful deadpan: 'We don't. The ghost finally has its privacy!' Dramatic silence then a cheeky original three-note electronic jingle on black. No narrator, no extra lines, no visible words, no watermark."
}
def main():
 p=argparse.ArgumentParser();p.add_argument('--segment',type=int,choices=range(1,7),required=True);p.add_argument('--comfy-url',default=URL);p.add_argument('--input-dir',type=Path,default=INPUT);p.add_argument('--seed',type=int,default=20261030);a=p.parse_args();frame=ROOT/'examples/input/bitzi-ghost-server'/f'scene{a.segment}.png'
 if not frame.is_file():p.error(f'Missing keyframe: {frame}')
 a.input_dir.mkdir(parents=True,exist_ok=True);name=f'bitzi_ghost_server_scene{a.segment}.png';shutil.copy2(frame,a.input_dir/name)
 payload=json.loads((ROOT/'examples/api/bitzi_bullet_time_seg1.json').read_text());n=payload['prompt'];n['6']['inputs']['image']=name;n['8']['inputs']['text']='logos, watermark, distorted face, extra limbs';n['7']['inputs'].update({'prompt':CAST_LOCK+LOCK+P[a.segment],'width':480,'height':864,'length':243});n['9']['inputs']['seed']=a.seed+a.segment;n['13']['inputs']['filename_prefix']=f'x-generator/bitzi-ghost-server/seg{a.segment}';n['14']['inputs']['filename_prefix']=f'audio/x-generator/bitzi-ghost-server/seg{a.segment}'
 req=Request(a.comfy_url.rstrip('/')+'/prompt',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
 with urlopen(req,timeout=30) as r:result=json.load(r)
 if result.get('node_errors'):raise SystemExit(json.dumps(result['node_errors'],indent=2))
 print(json.dumps(result))
if __name__=='__main__':main()
