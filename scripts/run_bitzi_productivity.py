#!/usr/bin/env python3
"""Render and assemble the English one-minute Bitzi productivity comedy."""
import argparse,json,subprocess,sys,time
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
def get(url):
 with urlopen(url,timeout=20) as r:return json.load(r)
def wait(base,pid):
 while True:
  entry=get(f'{base}/history/{pid}').get(pid)
  if entry:
   if entry.get('status',{}).get('status_str')=='error': raise RuntimeError(json.dumps(entry['status']))
   return
  q=get(base+'/queue'); ids=[x[1] for k in ('queue_running','queue_pending') for x in q.get(k,[])]
  if pid not in ids: raise RuntimeError(f'ComfyUI dropped job {pid} without history')
  time.sleep(20)
def main():
 p=argparse.ArgumentParser();p.add_argument('--comfy-url',default='http://192.168.1.224:8188');p.add_argument('--input-dir',type=Path,default=Path('/home/jee/docker/minimax-h3-data/input'));p.add_argument('--output-dir',type=Path,default=Path('/home/jee/docker/minimax-h3-data/output'));p.add_argument('--first-prompt-id');a=p.parse_args();base=a.comfy_url.rstrip('/');out=a.output_dir/'x-generator/bitzi-productivity'
 for i in range(1,7):
  if i==1 and a.first_prompt_id: pid=a.first_prompt_id
  else:
   res=subprocess.run([sys.executable,str(ROOT/'scripts/submit_bitzi_productivity.py'),'--segment',str(i),'--comfy-url',base,'--input-dir',str(a.input_dir)],capture_output=True,text=True,check=True);pid=json.loads(res.stdout)['prompt_id']
  print(f'Scene {i}/6 queued: {pid}',flush=True);wait(base,pid)
  if not list(out.glob(f'seg{i}_*.mp4')):raise FileNotFoundError(f'No scene {i} MP4 found under {out}')
  if not list(a.output_dir.glob(f'audio/x-generator/bitzi-productivity/seg{i}_*.flac')):raise FileNotFoundError(f'No scene {i} audio found')
  print(f'Scene {i}/6 complete',flush=True)
 final=out/'bitzi_the_productivity_revolution_60s.mp4'
 subprocess.run([sys.executable,str(ROOT/'scripts/assemble_bitzi_productivity.py'),'--input-dir',str(a.output_dir),'--output',str(final)],check=True)
 print(f'Film complete: {final}',flush=True)
if __name__=='__main__':main()
