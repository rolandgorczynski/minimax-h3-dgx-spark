#!/usr/bin/env python3
"""Join two H3 clips and master their audio with measured loudness and true peak."""
import argparse
import subprocess
import tempfile
from pathlib import Path
from audio_mastering import master_audio


def concat_file(paths, destination):
    def quote(path):
        return str(path.resolve()).replace("'", "'\\''")
    destination.write_text(''.join(f"file '{quote(Path(path))}'\n" for path in paths))


def run(args):
    subprocess.run(args, check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--video-1', type=Path, required=True)
    p.add_argument('--video-2', type=Path, required=True)
    p.add_argument('--audio-1', type=Path, required=True)
    p.add_argument('--audio-2', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--ffmpeg', default='ffmpeg')
    args = p.parse_args()
    for path in (args.video_1, args.video_2, args.audio_1, args.audio_2):
        if not path.is_file():
            p.error(f'Input does not exist: {path}')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bitzi-h3-') as temp:
        temp = Path(temp)
        videos, audios = temp/'videos.txt', temp/'audios.txt'
        video_join, audio_join = temp/'joined.mp4', temp/'joined.flac'
        concat_file([args.video_1, args.video_2], videos)
        concat_file([args.audio_1, args.audio_2], audios)
        run([args.ffmpeg, '-y', '-f', 'concat', '-safe', '0', '-i', str(videos), '-c', 'copy', '-an', str(video_join)])
        run([args.ffmpeg, '-y', '-f', 'concat', '-safe', '0', '-i', str(audios), '-c:a', 'flac', str(audio_join)])
        mastered = temp/'mastered.flac'
        master_audio(audio_join, mastered, ffmpeg=args.ffmpeg)
        run([
            args.ffmpeg, '-y', '-i', str(video_join), '-i', str(mastered),
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', str(args.output),
        ])
    print(args.output)


if __name__ == '__main__':
    main()
