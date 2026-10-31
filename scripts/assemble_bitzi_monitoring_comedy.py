#!/usr/bin/env python3
"""Join six vertical H3 scenes, normalize dialogue audio and burn in German captions."""
import argparse
import subprocess
import tempfile
from pathlib import Path
from audio_mastering import master_audio

def run(args):
    subprocess.run(args, check=True)

def concat_file(paths, dest):
    dest.write_text(''.join("file '" + str(Path(x).resolve()).replace("'", "'\\''") + "'\n" for x in paths))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-dir', type=Path, default=Path('/home/jee/docker/minimax-h3-data/output'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--ffmpeg', default='ffmpeg')
    a=p.parse_args()
    root=a.input_dir
    def latest(pattern):
        found=sorted(root.glob(pattern),key=lambda x:x.stat().st_mtime)
        if not found: return root/pattern
        return found[-1]
    vids=[latest(f'x-generator/bitzi-monitoring-comedy/seg{i}_*.mp4') for i in range(1,7)]
    auds=[latest(f'audio/x-generator/bitzi-monitoring-comedy/seg{i}_*.flac') for i in range(1,7)]
    missing=[str(x) for x in vids+auds if not x.is_file()]
    if missing: p.error('Missing H3 outputs: '+', '.join(missing))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bitzi-monitoring-') as td:
        td=Path(td); vf=td/'videos.txt'; af=td/'audio.txt'; joined=td/'joined.mp4'; sound=td/'sound.flac'
        concat_file(vids,vf); concat_file(auds,af)
        run([a.ffmpeg,'-y','-f','concat','-safe','0','-i',str(vf),'-c','copy','-an',str(joined)])
        run([a.ffmpeg,'-y','-f','concat','-safe','0','-i',str(af),'-c:a','flac',str(sound)])
        mastered=td/'mastered.flac'
        master_audio(sound,mastered,ffmpeg=a.ffmpeg)
        # Caption timing tracks the six beats; silence is deliberately preserved before the last punchline.
        srt=td/'captions.srt'
        srt.write_text('''1
00:00:01,000 --> 00:00:03,200
Bitzi, prüf bitte die
Sicherheitsüberwachung.

2
00:00:03,400 --> 00:00:05,700
Chef, entspann dich.
Ich bin künstliche Intelligenz.

3
00:00:05,800 --> 00:00:09,700
Das heißt, ich bin künstlich –
aber intelligent!

4
00:00:10,700 --> 00:00:15,000
Boah! Überall Warnungen!
Das nervt ja mehr als Windows Update!

5
00:00:15,100 --> 00:00:19,500
Moment … ich hab eine geniale Idee!

6
00:00:21,500 --> 00:00:26,000
Problem gelöst! Null Sicherheitswarnungen!
Hundert Prozent Verbesserung!

7
00:00:31,000 --> 00:00:33,700
Bitzi! Warum ist das Monitoring
ausgeschaltet?!

8
00:00:33,800 --> 00:00:37,200
Weil es ständig Probleme gemeldet hat!
Jetzt meldet es keine mehr!

9
00:00:37,300 --> 00:00:39,200
Du hast das Sicherheitssystem
abgeschaltet!

10
00:00:39,250 --> 00:00:40,300
Du wolltest doch Ruhe im System!

11
00:00:40,700 --> 00:00:43,800
Und wer kontrolliert jetzt
eigentlich dich?!

12
00:00:45,000 --> 00:00:49,800
Gute Frage. Hab ich aus Effizienzgründen
auch abgeschaltet.

13
00:00:54,000 --> 00:00:59,000
Wenn keiner mehr kontrolliert,
kann auch keiner Fehler finden!
''',encoding='utf-8')
        # Keep native H3 audio; measured two-pass mastering controls loudness and true peak.
        video_filter=(f"crop=480:852:0:6,scale=720:1280:flags=lanczos,"
                      f"subtitles={srt}:force_style='FontName=DejaVu Sans,FontSize=12,Outline=1,Shadow=1,Alignment=2,MarginV=25',"
                      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='Roland Gorczynski':fontcolor=white@0.94:fontsize=18:borderw=2:bordercolor=black@0.80:x=w-tw-22:y=h-th-54,"
                      "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='bits.gorczynski.online':fontcolor=white@0.90:fontsize=12:borderw=2:bordercolor=black@0.80:x=w-tw-22:y=h-th-22")
        run([a.ffmpeg,'-y','-i',str(joined),'-i',str(mastered),'-vf',video_filter,'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-b:a','192k','-t','60','-movflags','+faststart',str(a.output)])
    print(a.output)

if __name__=='__main__': main()
