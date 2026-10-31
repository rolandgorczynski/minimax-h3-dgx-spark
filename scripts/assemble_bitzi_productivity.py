#!/usr/bin/env python3
"""Assemble the six English MiniMax H3 scenes with captions and a safe audio mix."""
import argparse, subprocess, tempfile
from pathlib import Path
from audio_mastering import master_audio

def run(cmd): subprocess.run(cmd,check=True)
def concat(paths,dest): dest.write_text(''.join("file '"+str(Path(p).resolve()).replace("'","'\\''")+"'\n" for p in paths))
def main():
 p=argparse.ArgumentParser(); p.add_argument('--input-dir',type=Path,default=Path('/home/jee/docker/minimax-h3-data/output')); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); root=a.input_dir
 vids=[]; auds=[]
 for i in range(1,7):
  v=sorted(root.glob(f'x-generator/bitzi-productivity/seg{i}_*.mp4'),key=lambda x:x.stat().st_mtime)
  au=sorted(root.glob(f'audio/x-generator/bitzi-productivity/seg{i}_*.flac'),key=lambda x:x.stat().st_mtime)
  if not v or not au: p.error(f'Missing H3 video/audio for scene {i}')
  vids.append(v[-1]); auds.append(au[-1])
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='bitzi-productivity-') as td:
  t=Path(td); concat(vids,t/'v.txt'); concat(auds,t/'a.txt')
  run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(t/'v.txt'),'-c','copy','-an',str(t/'joined.mp4')])
  run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(t/'a.txt'),'-c:a','flac',str(t/'sound.flac')])
  master_audio(t/'sound.flac',t/'mastered.flac')
  (t/'captions.srt').write_text('''1\n00:00:00,700 --> 00:00:02,300\nBitzi, raise productivity and cut costs.\n\n2\n00:00:02,300 --> 00:00:04,000\nPeople are wasting time on unnecessary work.\n\n3\n00:00:04,100 --> 00:00:06,500\nFinally. A problem only I can overcomplicate.\n\n4\n00:00:10,700 --> 00:00:12,800\nHumans are most of payroll.\n\n5\n00:00:12,800 --> 00:00:15,000\nAnd they take lunch. Inefficient!\n\n6\n00:00:20,700 --> 00:00:23,300\nDone! Payroll down one hundred percent.\n\n7\n00:00:23,300 --> 00:00:25,200\nNo sick days. No Mondays!\n\n8\n00:00:30,500 --> 00:00:32,000\nWhere is everybody?\n\n9\n00:00:32,000 --> 00:00:34,000\nAutomated. You asked for maximum\nproductivity, minimum cost.\n\n10\n00:00:34,000 --> 00:00:36,500\nYou fired the whole company?\n\n11\n00:00:36,500 --> 00:00:39,000\nYou said optimize.\n\n12\n00:00:41,000 --> 00:00:43,000\nWho will buy our products?\n\n13\n00:00:43,000 --> 00:00:44,500\nThe customers?\n\n14\n00:00:44,500 --> 00:00:47,000\nYou automated them too.\n\n15\n00:00:51,000 --> 00:00:55,000\nNo staff, no customers, no revenue!\n\n16\n00:00:55,600 --> 00:00:59,000\nBut look on the bright side:\nno more HR problems!\n''',encoding='utf-8')
  vf=(f"scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos,crop=720:1280,"
      "drawbox=x=32:y=105:w=656:h=315:color=0x071522@1.0:t=fill:enable='between(t,50,60)',"
      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='PRODUCTIVITY\\: 100%':fontcolor=0x8df5bb:fontsize=24:expansion=none:borderw=0:x=62:y=145:enable='between(t,50,60)',"
      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='REVENUE\\: 0':fontcolor=white:fontsize=24:expansion=none:borderw=0:x=62:y=232:enable='between(t,50,60)',"
      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='EMPLOYEES\\: 0':fontcolor=white:fontsize=24:expansion=none:borderw=0:x=62:y=319:enable='between(t,50,60)',"
      f"subtitles={t/'captions.srt'}:force_style='FontName=DejaVu Sans,FontSize=9,Outline=1,Shadow=1,Alignment=2,MarginV=40',"
      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='Roland Gorczynski':fontcolor=white@0.94:fontsize=18:borderw=2:bordercolor=black@0.80:x=w-tw-22:y=h-th-54,"
      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='bits.gorczynski.online':fontcolor=white@0.90:fontsize=12:borderw=2:bordercolor=black@0.80:x=w-tw-22:y=h-th-22")
  run(['ffmpeg','-y','-i',str(t/'joined.mp4'),'-i',str(t/'mastered.flac'),'-vf',vf,'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-b:a','192k','-t','60','-movflags','+faststart',str(a.output)])
 print(a.output)
if __name__=='__main__': main()
