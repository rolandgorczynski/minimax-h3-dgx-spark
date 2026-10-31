#!/usr/bin/env python3
"""Assemble the Zombie Processes clips with German subtitles and safe audio."""
import argparse
import subprocess
import tempfile
from pathlib import Path
from audio_mastering import master_audio


def run(command):
    subprocess.run(command, check=True)


def concat(paths, destination):
    destination.write_text(''.join("file '" + str(Path(path).resolve()).replace("'", "'\\''") + "'\n" for path in paths))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=Path('/home/jee/docker/minimax-h3-data/output'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.input_dir
    videos, audios = [], []
    for scene in range(1, 7):
        video = sorted(root.glob(f'x-generator/bitzi-zombie-processes/seg{scene}_*.mp4'), key=lambda p: p.stat().st_mtime)
        audio = sorted(root.glob(f'audio/x-generator/bitzi-zombie-processes/seg{scene}_*.flac'), key=lambda p: p.stat().st_mtime)
        if not video or not audio:
            parser.error(f'Missing H3 video/audio for scene {scene}')
        videos.append(video[-1])
        audios.append(audio[-1])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bitzi-zombie-processes-') as temp_dir:
        temp = Path(temp_dir)
        concat(videos, temp / 'videos.txt')
        concat(audios, temp / 'audios.txt')
        run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(temp / 'videos.txt'),
             '-c', 'copy', '-an', str(temp / 'joined.mp4')])
        run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(temp / 'audios.txt'),
             '-c:a', 'flac', str(temp / 'sound.flac')])
        master_audio(temp / 'sound.flac', temp / 'mastered.flac',
                     post_filters='afade=t=out:st=60.25:d=0.5,apad=pad_dur=2')
        (temp / 'captions.srt').write_text('''1
00:00:00,500 --> 00:00:03,700
Bitzi, kümmere dich um die Zombie-Prozesse.

2
00:00:03,800 --> 00:00:06,800
Endlich! Ein echter Halloween-Auftrag!

3
00:00:10,500 --> 00:00:12,600
Die Untoten sind überall!

4
00:00:12,700 --> 00:00:18,700
Die Prozesse sind bereits beendet. Ihr Elternprozess muss nur noch den Exit-Status abholen.

5
00:00:20,500 --> 00:00:26,000
Keine Eltern, keine Zombies. Ich habe den Stammbaum vereinfacht!

6
00:00:30,500 --> 00:00:34,000
Bitzi! Du hast alle wichtigen Prozesse gekillt!

7
00:00:34,100 --> 00:00:38,800
Kollateralschäden im Kampf gegen die Untoten.

8
00:00:40,500 --> 00:00:42,100
Er ist wieder da!

9
00:00:42,200 --> 00:00:49,200
Der Dienst hat wieder ein Kind gestartet und dessen Exit-Status nicht abgeholt.

10
00:00:50,500 --> 00:00:53,000
Was genau war dein Plan?

11
00:00:53,100 --> 00:00:59,500
Ein Betriebssystem ohne lebende Prozesse. Auftrag erledigt!

'''.replace('\n+', '\n'), encoding='utf-8')
        video_filter = (
            f"scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos,crop=720:1280,"
            f"fade=t=out:st=60.25:d=0.5,tpad=stop_mode=add:color=black:stop_duration=2,"
            f"subtitles={temp/'captions.srt'}:force_style='FontName=DejaVu Sans,FontSize=9,Outline=1,Shadow=1,Alignment=2,MarginV=40',"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='BITZI':fontcolor=white:fontsize=40:expansion=none:borderw=2:bordercolor=black@0.8:x=(w-tw)/2:y=500:enable='between(t,60.75,62.75)',"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='NO ZOMBIES':fontcolor=0x8df5bb:fontsize=26:expansion=none:borderw=2:bordercolor=black@0.8:x=(w-tw)/2:y=580:enable='between(t,60.75,62.75)',"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='NO SERVICES':fontcolor=white:fontsize=24:expansion=none:borderw=2:bordercolor=black@0.8:x=(w-tw)/2:y=630:enable='between(t,60.75,62.75)',"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='Roland Gorczynski':fontcolor=white@0.94:fontsize=18:borderw=2:bordercolor=black@0.80:x=w-tw-22:y=h-th-54,"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='bits.gorczynski.online':fontcolor=white@0.90:fontsize=12:borderw=2:bordercolor=black@0.80:x=w-tw-22:y=h-th-22"
        )
        run(['ffmpeg', '-y', '-i', str(temp / 'joined.mp4'), '-i', str(temp / 'mastered.flac'),
             '-vf', video_filter,
             '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
             '-c:a', 'aac', '-ar', '48000', '-b:a', '192k', '-movflags', '+faststart', str(args.output)])
    print(args.output)


if __name__ == '__main__':
    main()
