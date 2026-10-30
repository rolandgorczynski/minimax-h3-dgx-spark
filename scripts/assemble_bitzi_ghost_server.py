#!/usr/bin/env python3
"""Assemble Bitzi: The Ghost in the Server with German captions and an extended ending."""
import argparse,subprocess,tempfile
from pathlib import Path
def run(c):subprocess.run(c,check=True)
def concat(paths,dest):dest.write_text(''.join("file '"+str(Path(p).resolve()).replace("'","'\\''")+"'\n" for p in paths))
def main():
 p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,default=Path('/home/jee/docker/minimax-h3-data/output'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.input_dir;vids=[];auds=[]
 for i in range(1,7):
  v=sorted(root.glob(f'x-generator/bitzi-ghost-server/seg{i}_*.mp4'),key=lambda x:x.stat().st_mtime);au=sorted(root.glob(f'audio/x-generator/bitzi-ghost-server/seg{i}_*.flac'),key=lambda x:x.stat().st_mtime)
  if not v or not au:p.error(f'Missing H3 video/audio for scene {i}')
  vids.append(v[-1]);auds.append(au[-1])
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='bitzi-ghost-server-') as td:
  t=Path(td);concat(vids,t/'v.txt');concat(auds,t/'a.txt');run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(t/'v.txt'),'-c','copy','-an',str(t/'joined.mp4')]);run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(t/'a.txt'),'-c:a','flac',str(t/'sound.flac')])
  (t/'captions.srt').write_text('''1
00:00:00,500 --> 00:00:03,700
Bitzi, bitte entferne die alten Geisterkonten!

2
00:00:03,800 --> 00:00:06,800
Halloween ist meine Spezialität!

3
00:00:10,500 --> 00:00:13,300
Die Geister stecken in den Konten!

4
00:00:13,400 --> 00:00:15,800
Das sind ehemalige Mitarbeiter!

5
00:00:20,500 --> 00:00:26,000
Ausgetrieben! Dieses Netzwerk ist offiziell geisterfrei!

6
00:00:30,500 --> 00:00:33,000
Du hast alle Konten gelöscht!

7
00:00:33,100 --> 00:00:35,800
Jedes einzelne. Ich bin gründlich.

8
00:00:40,500 --> 00:00:43,000
Warum ist der Geist dann noch online?

9
00:00:43,100 --> 00:00:45,800
Offenbar hatte er Root-Rechte.

10
00:00:50,500 --> 00:00:53,000
Wie kommen wir wieder rein?!

11
00:00:53,100 --> 00:00:55,000
Gar nicht.

12
00:00:55,100 --> 00:00:59,500
Der Geist hat endlich seine Privatsphäre!

''',encoding='utf-8')
  vf=(f"scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos,crop=720:1280,fade=t=out:st=60.25:d=0.5,tpad=stop_mode=add:color=black:stop_duration=2,"
      f"subtitles={t/'captions.srt'}:force_style='FontName=DejaVu Sans,FontSize=9,Outline=1,Shadow=1,Alignment=2,MarginV=40',"
      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='BITZI':fontcolor=white:fontsize=40:expansion=none:borderw=2:bordercolor=black@0.8:x=(w-tw)/2:y=500:enable='between(t,60.75,62.75)',"
      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='100% GHOST-FREE':fontcolor=0x8df5bb:fontsize=26:expansion=none:borderw=2:bordercolor=black@0.8:x=(w-tw)/2:y=580:enable='between(t,60.75,62.75)',"
      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='100% LOCKED OUT':fontcolor=white:fontsize=24:expansion=none:borderw=2:bordercolor=black@0.8:x=(w-tw)/2:y=630:enable='between(t,60.75,62.75)',"
      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='Roland Gorczynski':fontcolor=white@0.94:fontsize=18:borderw=2:bordercolor=black@0.80:x=w-tw-22:y=h-th-54,"
      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='bits.gorczynski.online':fontcolor=white@0.90:fontsize=12:borderw=2:bordercolor=black@0.80:x=w-tw-22:y=h-th-22")
  af="loudnorm=I=-20:TP=-6:LRA=11,alimiter=limit=0.45:attack=5:release=80:level=false,afade=t=out:st=60.25:d=0.5,apad=pad_dur=2"
  run(['ffmpeg','-y','-i',str(t/'joined.mp4'),'-i',str(t/'sound.flac'),'-vf',vf,'-af',af,'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-b:a','192k','-movflags','+faststart',str(a.output)])
 print(a.output)
if __name__=='__main__':main()
