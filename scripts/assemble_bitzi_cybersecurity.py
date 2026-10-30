#!/usr/bin/env python3
"""Assemble the English MiniMax H3 scenes with German captions and safe audio."""
import argparse,subprocess,tempfile
from pathlib import Path
def run(c):subprocess.run(c,check=True)
def concat(paths,dest):dest.write_text(''.join("file '"+str(Path(p).resolve()).replace("'","'\\''")+"'\n" for p in paths))
def main():
 p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,default=Path('/home/jee/docker/minimax-h3-data/output'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.input_dir;vids=[];auds=[]
 for i in range(1,7):
  v=sorted(root.glob(f'x-generator/bitzi-cybersecurity/seg{i}_*.mp4'),key=lambda x:x.stat().st_mtime); au=sorted(root.glob(f'audio/x-generator/bitzi-cybersecurity/seg{i}_*.flac'),key=lambda x:x.stat().st_mtime)
  if not v or not au:p.error(f'Missing H3 video/audio for scene {i}')
  vids.append(v[-1]);auds.append(au[-1])
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='bitzi-cybersecurity-') as td:
  t=Path(td);concat(vids,t/'v.txt');concat(auds,t/'a.txt');run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(t/'v.txt'),'-c','copy','-an',str(t/'joined.mp4')]);run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(t/'a.txt'),'-c:a','flac',str(t/'sound.flac')])
  (t/'captions.srt').write_text('''1\n00:00:00,500 --> 00:00:03,800\nBitzi! Überall Hacker! Ich will, dass\nunser Firmennetz absolut sicher ist!\n\n2\n00:00:03,900 --> 00:00:06,700\nAbsolut sicher? Chef, das ist mein Spezialgebiet!\n\n3\n00:00:10,500 --> 00:00:13,500\nAha! Ich hab die Sicherheitslücke gefunden!\n\n4\n00:00:13,600 --> 00:00:14,700\nWelche?\n\n5\n00:00:14,800 --> 00:00:18,500\nDIE INTERNETVERBINDUNG!\n\n6\n00:00:20,500 --> 00:00:24,500\nFertig! Keine Hacker! Keine Malware!\nKeine Cyberangriffe!\n\n7\n00:00:24,500 --> 00:00:27,500\nIch nenne es ZERO INTERNET TRUST!\n\n8\n00:00:30,500 --> 00:00:33,000\nBitzi! Wir haben kein Internet mehr!\n\n9\n00:00:33,000 --> 00:00:34,200\nKorrekt! Ein Sicherheitsrisiko weniger!\n\n10\n00:00:34,200 --> 00:00:36,500\nAber wir können nicht mehr arbeiten!\n\n11\n00:00:36,500 --> 00:00:39,500\nStatistisch gesehen ist Arbeiten\nauch ein Risikofaktor!\n\n12\n00:00:40,500 --> 00:00:43,000\nBitzi! Das ist Wahnsinn!\nWir BRAUCHEN das Netzwerk!\n\n13\n00:00:43,000 --> 00:00:45,200\nDu hast gerade meine ganze\nSicherheitsarchitektur zerstört!\n\n14\n00:00:45,200 --> 00:00:47,500\nWir brauchen nur vernünftige Zugriffskontrollen!\n\n15\n00:00:47,500 --> 00:00:50,000\nZugriffskontrollen? GENIAL!\n\n16\n00:00:50,800 --> 00:00:54,000\nBitzi! Niemand kann auf das System zugreifen!\nNicht mal du!\n\n17\n00:00:54,000 --> 00:00:55,000\nNa und?\n\n18\n00:00:55,500 --> 00:00:59,000\nWenn niemand reinkommt,\nkann auch niemand gehackt werden!\n''',encoding='utf-8')
  vf=(f"scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos,crop=720:1280,"
      "drawbox=x=40:y=105:w=640:h=300:color=0x071522@1.0:t=fill:enable='between(t,50,60)',"
      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='100% SECURITY':fontcolor=0x8df5bb:fontsize=27:expansion=none:borderw=0:x=68:y=165:enable='between(t,50,60)',"
      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='0% ACCESS':fontcolor=white:fontsize=27:expansion=none:borderw=0:x=68:y=270:enable='between(t,50,60)',"
      f"subtitles={t/'captions.srt'}:force_style='FontName=DejaVu Sans,FontSize=9,Outline=1,Shadow=1,Alignment=2,MarginV=40',"
      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='Roland Gorczynski':fontcolor=white@0.94:fontsize=18:borderw=2:bordercolor=black@0.80:x=w-tw-22:y=h-th-54,"
      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='bits.gorczynski.online':fontcolor=white@0.90:fontsize=12:borderw=2:bordercolor=black@0.80:x=w-tw-22:y=h-th-22")
  run(['ffmpeg','-y','-i',str(t/'joined.mp4'),'-i',str(t/'sound.flac'),'-vf',vf,'-af','loudnorm=I=-20:TP=-6:LRA=11,alimiter=limit=0.45:attack=5:release=80:level=false','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-b:a','192k','-t','60','-movflags','+faststart',str(a.output)])
 print(a.output)
if __name__=='__main__':main()
