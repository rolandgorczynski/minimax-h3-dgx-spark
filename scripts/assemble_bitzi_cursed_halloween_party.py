#!/usr/bin/env python3
"""Assemble party scenes with German captions, leveled audio and end card."""
import argparse, subprocess, tempfile
from pathlib import Path

def run(cmd):
    subprocess.run(cmd, check=True)

def concat(paths, destination):
    destination.write_text(''.join("file '" + str(Path(p).resolve()).replace("'", "'\\''") + "'\\n" for p in paths))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-dir', type=Path, default=Path('/home/jee/docker/minimax-h3-data/output'))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    videos, audios = [], []
    for n in range(1, 7):
        v = sorted(a.input_dir.glob(f'x-generator/bitzi-cursed-halloween-party/seg{n}_*.mp4'), key=lambda x: x.stat().st_mtime)
        s = sorted(a.input_dir.glob(f'audio/x-generator/bitzi-cursed-halloween-party/seg{n}_*.flac'), key=lambda x: x.stat().st_mtime)
        if not v or not s: p.error(f'Missing video/audio for scene {n}')
        videos.append(v[-1]); audios.append(s[-1])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bitzi-cursed-party-') as td:
        t = Path(td); concat(videos, t/'v.txt'); concat(audios, t/'a.txt')
        run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(t/'v.txt'),'-c','copy','-an',str(t/'video.mp4')])
        run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(t/'a.txt'),'-c:a','flac',str(t/'audio.flac')])
        (t/'captions.srt').write_text("""1
00:00:00,500 --> 00:00:04,100
Bitzi, organisiere eine Halloween-Party. Nur geladene Gäste kommen rein!

2
00:00:04,200 --> 00:00:06,800
Ich setze auf modernste KI!

3
00:00:10,500 --> 00:00:13,500
Ein Chef-Foto. Unendlich viele Chefs!

4
00:00:13,600 --> 00:00:16,500
So funktioniert Identitätserkennung nicht.

5
00:00:20,500 --> 00:00:23,600
Die VIP-Liste funktioniert perfekt!

6
00:00:23,700 --> 00:00:26,800
Du hast jeden zum Chef gemacht!

7
00:00:30,500 --> 00:00:34,000
Warum bezahlt mein Konto für fünfzig Leute?

8
00:00:34,100 --> 00:00:37,500
Exklusive Bewirtung. Im großen Stil!

9
00:00:40,500 --> 00:00:43,500
Bitzi, ich bin der echte Chef!

10
00:00:43,600 --> 00:00:47,300
Genau das würde ein Hochstapler sagen.

11
00:00:50,500 --> 00:00:52,500
Wer hat jetzt das Sagen?

12
00:00:52,600 --> 00:00:55,500
Offenbar wir alle.
""", encoding='utf-8')
        vf = (f"scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos,crop=720:1280,"
              f"tpad=stop_mode=add:color=black:stop_duration=2,fade=t=out:st=60.75:d=0.5,"
              f"subtitles={t/'captions.srt'}:force_style='FontName=DejaVu Sans,FontSize=9,Outline=1,Shadow=1,Alignment=2,MarginV=40',"
              "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='BITZI':fontcolor=white:fontsize=40:expansion=none:borderw=2:bordercolor=black@0.8:x=(w-tw)/2:y=500:enable='between(t,60.75,62.75)',"
              "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='ONE PHOTO. FIFTY CEOS.':fontcolor=0x8df5bb:fontsize=24:expansion=none:borderw=2:bordercolor=black@0.8:x=(w-tw)/2:y=580:enable='between(t,60.75,62.75)',"
              "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='Roland Gorczynski':fontcolor=white@0.94:fontsize=18:borderw=2:bordercolor=black@0.80:x=w-tw-22:y=h-th-54,"
              "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='bits.gorczynski.online':fontcolor=white@0.90:fontsize=12:borderw=2:bordercolor=black@0.80:x=w-tw-22:y=h-th-22")
        af = 'loudnorm=I=-20:TP=-6:LRA=11,alimiter=limit=0.45:attack=5:release=80:level=false,afade=t=out:st=60.75:d=0.5,apad=pad_dur=2'
        run(['ffmpeg','-y','-i',str(t/'video.mp4'),'-i',str(t/'audio.flac'),'-vf',vf,'-af',af,
             '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-b:a','192k','-movflags','+faststart',str(a.output)])
    print(a.output)

if __name__ == '__main__': main()
