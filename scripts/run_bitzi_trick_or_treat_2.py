#!/usr/bin/env python3
"""Render six Trick or Treat 2.0 scenes sequentially and assemble the film."""
import argparse,json,subprocess,sys,time
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
def get(url):
    with urlopen(url,timeout=20) as r: return json.load(r)
def wait(base,pid):
    while True:
        entry=get(f'{base}/history/{pid}').get(pid)
        if entry:
            if entry.get('status',{}).get('status_str')=='error': raise RuntimeError(json.dumps(entry['status']))
            return
        q=get(base+'/queue')
        active=[x[1] for key in ('queue_running','queue_pending') for x in q.get(key,[])]
        if pid not in active: raise RuntimeError(f'ComfyUI dropped job {pid}')
        time.sleep(20)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--comfy-url',default='http://192.168.1.224:8188')
    p.add_argument('--input-dir',type=Path,default=Path('/home/jee/docker/minimax-h3-data/input'))
    p.add_argument('--output-dir',type=Path,default=Path('/home/jee/docker/minimax-h3-data/output'))
    a=p.parse_args(); base=a.comfy_url.rstrip('/')
    out=a.output_dir/'x-generator/bitzi-trick-or-treat-2'
    for n in range(1,7):
        res=subprocess.run([sys.executable,str(ROOT/'scripts/submit_bitzi_trick_or_treat_2.py'),'--segment',str(n),'--comfy-url',base,'--input-dir',str(a.input_dir)],capture_output=True,text=True,check=True)
        pid=json.loads(res.stdout)['prompt_id']; print(f'Scene {n}/6 queued: {pid}',flush=True); wait(base,pid)
        if not list(out.glob(f'seg{n}_*.mp4')): raise FileNotFoundError(f'Missing scene {n} video')
        if not list((a.output_dir/'audio/x-generator/bitzi-trick-or-treat-2').glob(f'seg{n}_*.flac')): raise FileNotFoundError(f'Missing scene {n} audio')
        print(f'Scene {n}/6 complete',flush=True)
    final=out/'bitzi_trick_or_treat_2.mp4'
    subprocess.run([sys.executable,str(ROOT/'scripts/assemble_bitzi_trick_or_treat_2.py'),'--input-dir',str(a.output_dir),'--output',str(final)],check=True)
    print(f'Film complete: {final}',flush=True)
if __name__=='__main__': main()
