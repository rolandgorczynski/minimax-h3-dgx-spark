#!/usr/bin/env python3
"""Render six scenes in order from consistent, authored Bitzi keyframes."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_URL=os.environ.get('COMFY_API_URL','http://192.168.1.224:8188')

def get_json(url):
    with urlopen(url,timeout=15) as r: return json.load(r)

def wait_for_job(base,prompt_id,interval):
    while True:
        history=get_json(f'{base}/history/{prompt_id}')
        entry=history.get(prompt_id)
        if entry:
            status=entry.get('status',{})
            if status.get('status_str')=='error' or status.get('completed') is False:
                raise RuntimeError(f'ComfyUI job failed: {json.dumps(status)}')
            return entry
        queue=get_json(f'{base}/queue')
        ids=[item[1] for key in ('queue_running','queue_pending') for item in queue.get(key,[])]
        if prompt_id not in ids:
            # A failed prompt may leave no history entry; don't wait forever.
            time.sleep(interval)
            if prompt_id not in [item[1] for key in ('queue_running','queue_pending') for item in get_json(f'{base}/queue').get(key,[])]:
                raise RuntimeError(f'ComfyUI dropped prompt {prompt_id} without output history')
        time.sleep(interval)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--comfy-url',default=DEFAULT_URL)
    p.add_argument('--input-dir',type=Path,default=Path('/home/jee/docker/minimax-h3-data/input'))
    p.add_argument('--output-dir',type=Path,default=Path('/home/jee/docker/minimax-h3-data/output'))
    p.add_argument('--first-prompt-id',help='Adopt an already-submitted scene 1 job.')
    p.add_argument('--poll-seconds',type=int,default=20)
    a=p.parse_args(); base=a.comfy_url.rstrip('/')
    (a.output_dir/'x-generator/bitzi-monitoring-comedy').mkdir(parents=True,exist_ok=True)
    for scene in range(1,7):
        keyframe=(ROOT/'examples/input/bitzi_monitoring_comedy_keyframe.png' if scene==1 else ROOT/f'examples/input/bitzi_monitoring_comedy_scene{scene}.png')
        if not keyframe.is_file():
            raise FileNotFoundError(f'Missing scene keyframe: {keyframe}')
        if scene==1 and a.first_prompt_id:
            prompt_id=a.first_prompt_id
        else:
            cmd=[sys.executable,str(ROOT/'scripts/submit_bitzi_monitoring_comedy.py'),'--segment',str(scene),'--first-frame',str(keyframe),'--comfy-url',base,'--input-dir',str(a.input_dir)]
            result=subprocess.run(cmd,text=True,capture_output=True,check=True)
            prompt_id=json.loads(result.stdout)['prompt_id']
            print(f'Szene {scene}/6 eingereiht: {prompt_id}',flush=True)
        entry=wait_for_job(base,prompt_id,a.poll_seconds)
        candidates=sorted((a.output_dir/'x-generator/bitzi-monitoring-comedy').glob(f'seg{scene}_*.mp4'),key=lambda x:x.stat().st_mtime)
        if not candidates:
            raise FileNotFoundError(f'No ComfyUI video output found for scene {scene}')
        video=candidates[-1]
        print(f'Szene {scene}/6 fertig: {video}',flush=True)
    assemble=ROOT/'scripts/assemble_bitzi_monitoring_comedy.py'
    final=a.output_dir/'x-generator/bitzi-monitoring-comedy/bitzi_ich_hab_das_unter_kontrolle_60s.mp4'
    subprocess.run([sys.executable,str(assemble),'--input-dir',str(a.output_dir),'--output',str(final)],check=True)
    print(f'Fertig: {final}',flush=True)

if __name__=='__main__': main()
