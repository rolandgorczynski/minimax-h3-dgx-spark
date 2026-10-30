#!/usr/bin/env python3
"""Submit one English Bitzi: The Ultimate Cybersecurity scene to local MiniMax H3."""
import argparse,json,os,shutil
from pathlib import Path
from urllib.request import Request,urlopen
from bitzi_cast_lock import CAST_LOCK
ROOT=Path(__file__).resolve().parents[1]; URL=os.environ.get('COMFY_API_URL','http://192.168.1.224:8188'); INPUT=Path(os.environ.get('COMFY_INPUT_DIR','/home/jee/docker/minimax-h3-data/input'))
LOCK="Exact character continuity: Bitzi is the same small turquoise rounded-square computer chip with orange pins and side contacts, huge expressive eyes, crooked grin and tiny fang. Keep the same shape, color and proportions. "
P={
1:"Vertical 9:16 polished 3D animated IT comedy, same office and characters. CEO, worried adult male: 'Bitzi! Hackers everywhere! I want our company network to be absolutely secure!' Bitzi jumps up: 'Absolutely secure? Boss, that's my specialty!' He cracks tiny knuckles dramatically. Playful dramatic news-like synth and quiet office ambience, low under speech. Two distinct voices, no narrator, no extra lines, no visible words, no watermark.",
2:"Continue same office, Bitzi and Linux administrator, vertical 9:16. Bitzi scans the security console frantically, freezes, points triumphantly at a physical network cable. BITZI: 'Aha! I've found the security vulnerability!' ADMIN: 'Which one?' BITZI loudly: 'THE INTERNET CONNECTION!' Fast scanning beeps, short drumroll and discovery sting, never covering words. No narrator, no extra lines, no readable text, no watermark.",
3:"Same exact Bitzi, office, vertical 9:16. Bitzi strains and pulls the Ethernet cable from central switch. Screens go dark; he dances wildly with a little confetti. BITZI: 'Done! No hackers! No malware! No cyberattacks! I call it ZERO INTERNET TRUST!' Network click, abrupt silence then original cheerful chiptune victory sting low under dialogue. No narrator, no extra lines, no readable text, no watermark.",
4:"Same characters and office, vertical 9:16. CEO tries computer and silent VoIP handset, horrified; Bitzi points proudly at the unplugged cable. CEO: 'Bitzi! We don't have internet anymore!' BITZI: 'Correct! One less security risk!' CEO: 'But we can't work anymore!' BITZI: 'Statistically speaking, working is a risk factor too!' Joyful music cuts, three soft error notes, awkward pause. Two distinct clear voices, no narrator, no extra dialogue, no readable text, no watermark.",
5:"Same office, vertical 9:16. Linux administrator rushes in and reconnects Ethernet cable; screens light. Bitzi looks horrified then inspired and presses a large red button. ADMIN: 'Bitzi! This is insane! We need the network!' BITZI: 'You destroyed my security architecture!' ADMIN: 'We just need proper access controls!' BITZI: 'Access controls? Genius!' Dramatic glitch, ominous buildup, loud but safe confirmation beep, then silence. No narrator, no extra dialogue, no readable labels, no watermark.",
6:"Same characters and office, vertical 9:16. Every monitor shows simple red lock icons. CEO desperately types; administrator tries to log in; Bitzi's own screen is locked too. CEO: 'Bitzi! Nobody can access the system! Not even you!' BITZI glances at his locked screen: 'So what?' Pause. Looks to camera and says clearly, deadpan: 'If nobody can get in, nobody can get hacked!' Admin gently bangs forehead against desk. No music under punchline; original cheeky three-note sting on black. No narrator, no extra words, no readable text or watermark."
}
def main():
 p=argparse.ArgumentParser();p.add_argument('--segment',type=int,choices=range(1,7),required=True);p.add_argument('--comfy-url',default=URL);p.add_argument('--input-dir',type=Path,default=INPUT);p.add_argument('--seed',type=int,default=20261030);a=p.parse_args();frame=ROOT/'examples/input/bitzi-cybersecurity'/f'scene{a.segment}.png'
 if not frame.is_file():p.error(f'Missing keyframe: {frame}')
 a.input_dir.mkdir(parents=True,exist_ok=True);name=f'bitzi_cybersecurity_scene{a.segment}.png';shutil.copy2(frame,a.input_dir/name)
 payload=json.loads((ROOT/'examples/api/bitzi_bullet_time_seg1.json').read_text());n=payload['prompt'];n['6']['inputs']['image']=name;n['8']['inputs']['text']='logos, watermark, distorted face, extra limbs';n['7']['inputs'].update({'prompt':CAST_LOCK+LOCK+P[a.segment],'width':480,'height':864,'length':243});n['9']['inputs']['seed']=a.seed+a.segment;n['13']['inputs']['filename_prefix']=f'x-generator/bitzi-cybersecurity/seg{a.segment}';n['14']['inputs']['filename_prefix']=f'audio/x-generator/bitzi-cybersecurity/seg{a.segment}'
 req=Request(a.comfy_url.rstrip('/')+'/prompt',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
 with urlopen(req,timeout=30) as r:result=json.load(r)
 if result.get('node_errors'):raise SystemExit(json.dumps(result['node_errors'],indent=2))
 print(json.dumps(result))
if __name__=='__main__':main()
