#!/usr/bin/env python3
"""Assemble Trick or Treat 2.0 with German subtitles and a safe, leveled mix."""
import argparse,subprocess,tempfile
from pathlib import Path
from audio_mastering import master_audio
def run(args): subprocess.run(args,check=True)
def concat(paths,dest):
    dest.write_text(''.join("file '"+str(Path(p).resolve()).replace("'","'\\''")+"'\n" for p in paths))
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-dir',type=Path,default=Path('/home/jee/docker/minimax-h3-data/output'))
    p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    videos=[]; audios=[]
    for n in range(1,7):
        v=sorted(a.input_dir.glob(f'x-generator/bitzi-trick-or-treat-2/seg{n}_*.mp4'),key=lambda x:x.stat().st_mtime)
        s=sorted(a.input_dir.glob(f'audio/x-generator/bitzi-trick-or-treat-2/seg{n}_*.flac'),key=lambda x:x.stat().st_mtime)
        if not v or not s: p.error(f'Missing scene {n} video/audio')
        videos.append(v[-1]); audios.append(s[-1])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bitzi-trick-or-treat-2-') as td:
        t=Path(td); concat(videos,t/'v.txt'); concat(audios,t/'a.txt')
        run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(t/'v.txt'),'-c','copy','-an',str(t/'video.mp4')])
        run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(t/'a.txt'),'-c:a','flac',str(t/'audio.flac')])
        master_audio(t/'audio.flac',t/'mastered.flac',post_filters='afade=t=out:st=60.75:d=0.5,apad=pad_dur=2')
        (t/'captions.srt').write_text("""1
00:00:00,500 --> 00:00:03,800
Bitzi, verteile die Süßigkeiten gerecht!

2
00:00:03,900 --> 00:00:06,500
Fairness ist nur ein Algorithmus!

3
00:00:10,500 --> 00:00:15,200
Jeder bekommt genau das, was sein Kostüm verdient!

4
00:00:20,500 --> 00:00:22,200
Das ist doch keine Süßigkeit!

5
00:00:22,300 --> 00:00:26,000
Aber ernährungsphysiologisch optimal!

6
00:00:30,500 --> 00:00:33,300
Bitzi! Gib ihnen einfach Schokolade!

7
00:00:33,400 --> 00:00:36,700
Ohne Qualitätskontrolle? Niemals!

8
00:00:40,500 --> 00:00:43,500
Endlich ein würdiger Kandidat!

9
00:00:50,500 --> 00:00:53,200
Bitzi! Du hast alles genommen!

10
00:00:53,300 --> 00:00:58,700
Die KI hat objektiv entschieden. Beschwer dich beim Algorithmus!
""",encoding='utf-8')
        vf=(f"scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos,crop=720:1280,"
            f"tpad=stop_mode=add:color=black:stop_duration=2,fade=t=out:st=60.75:d=0.5,"
            f"subtitles={t/'captions.srt'}:force_style='FontName=DejaVu Sans,FontSize=9,Outline=1,Shadow=1,Alignment=2,MarginV=40',"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='BITZI':fontcolor=white:fontsize=40:expansion=none:borderw=2:bordercolor=black@0.8:x=(w-tw)/2:y=500:enable='between(t,60.75,62.75)',"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='ALGORITHMICALLY FAIR.':fontcolor=0x8df5bb:fontsize=23:expansion=none:borderw=2:bordercolor=black@0.8:x=(w-tw)/2:y=570:enable='between(t,60.75,62.75)',"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='PRACTICALLY EATEN.':fontcolor=white:fontsize=23:expansion=none:borderw=2:bordercolor=black@0.8:x=(w-tw)/2:y=615:enable='between(t,60.75,62.75)',"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='Roland Gorczynski':fontcolor=white@0.94:fontsize=18:borderw=2:bordercolor=black@0.8:x=w-tw-22:y=h-th-54,"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='bits.gorczynski.online':fontcolor=white@0.90:fontsize=12:borderw=2:bordercolor=black@0.8:x=w-tw-22:y=h-th-22")
        run(['ffmpeg','-y','-i',str(t/'video.mp4'),'-i',str(t/'mastered.flac'),'-vf',vf,'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-b:a','192k','-movflags','+faststart',str(a.output)])
    print(a.output)
if __name__=='__main__': main()
