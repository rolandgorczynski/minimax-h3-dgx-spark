"""Two-pass EBU R128 mastering for the final audio track of H3 comic videos."""

from __future__ import annotations

import json
import argparse
import re
import subprocess
from pathlib import Path


def build_filter_chain(
    *,
    channels: int,
    target_lufs: float,
    true_peak: float,
    lra: float,
    measured: dict[str, str] | None = None,
    post_filters: str = "",
    speech_cleanup: bool = False,
) -> str:
    """Build a filter chain; optional speech cleanup is unsuitable for full music mixes."""
    filters: list[str] = []
    if speech_cleanup:
        filters.extend(
            [
                "highpass=f=80",
                "deesser=i=0.4",
                "acompressor=threshold=0.125:ratio=2:attack=15:release=200:makeup=1.5",
            ]
        )
    if post_filters:
        filters.append(post_filters)

    norm = (
        f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}"
        f":dual_mono={'true' if channels == 1 else 'false'}"
    )
    if measured is not None:
        norm += (
            f":measured_I={measured['input_i']}"
            f":measured_TP={measured['input_tp']}"
            f":measured_LRA={measured['input_lra']}"
            f":measured_thresh={measured['input_thresh']}"
            f":offset={measured['target_offset']}:linear=true"
        )
    norm += ":print_format=json"
    filters.append(norm)
    return ",".join(filters)


def parse_loudnorm_stats(text: str) -> dict[str, str]:
    """Extract the last loudnorm JSON object from FFmpeg's diagnostic output."""
    for match in reversed(list(re.finditer(r"\{[^{}]*\}", text, flags=re.DOTALL))):
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            continue
        required = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
        if all(key in data for key in required):
            if any(str(data[key]).lower() in {"-inf", "inf", "nan"} for key in required):
                break
            return {key: str(data[key]) for key in required}
    raise ValueError("FFmpeg did not return complete loudnorm measurements")


def _probe_channels(ffprobe: str, source: Path) -> int:
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=channels",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(source),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        channels = int(result.stdout.strip().splitlines()[0])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"Cannot determine audio channel count for {source}") from exc
    if channels < 1:
        raise ValueError(f"Invalid audio channel count for {source}: {channels}")
    return channels


def _run_measurement(ffmpeg: str, source: Path, filter_chain: str) -> dict[str, str]:
    result = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-af",
            filter_chain,
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_loudnorm_stats(result.stderr + "\n" + result.stdout)


def master_audio(
    source: Path,
    destination: Path,
    *,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    target_lufs: float = -16.0,
    true_peak: float = -1.5,
    lra: float = 11.0,
    post_filters: str = "",
    speech_cleanup: bool = False,
) -> dict[str, str]:
    """Measure the final mix, then normalize it in a second pass to 48 kHz FLAC.

    ``post_filters`` can carry timeline operations such as an ending fade and pad;
    they run before loudness measurement so the delivered mix is what gets measured.
    ``speech_cleanup`` should only be enabled for dialogue-dominant audio. H3 often
    generates music and effects in the same track, so it is opt-in.
    """
    source = Path(source)
    destination = Path(destination)
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    channels = _probe_channels(ffprobe, source)
    first_pass = build_filter_chain(
        channels=channels,
        target_lufs=target_lufs,
        true_peak=true_peak,
        lra=lra,
        post_filters=post_filters,
        speech_cleanup=speech_cleanup,
    )
    stats = _run_measurement(ffmpeg, source, first_pass)
    second_pass = build_filter_chain(
        channels=channels,
        target_lufs=target_lufs,
        true_peak=true_peak,
        lra=lra,
        measured=stats,
        post_filters=post_filters,
        speech_cleanup=speech_cleanup,
    )
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-nostats",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-af",
            second_pass,
            "-ar",
            "48000",
            "-c:a",
            "flac",
            "-compression_level",
            "8",
            str(destination),
        ],
        check=True,
    )
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--target-lufs", type=float, default=-16.0)
    parser.add_argument("--true-peak", type=float, default=-1.5)
    parser.add_argument("--lra", type=float, default=11.0)
    parser.add_argument("--post-filters", default="")
    parser.add_argument(
        "--speech-cleanup",
        action="store_true",
        help="Apply high-pass, de-esser, and gentle compression; use for dialogue-only audio.",
    )
    args = parser.parse_args()
    stats = master_audio(
        args.source,
        args.destination,
        ffmpeg=args.ffmpeg,
        ffprobe=args.ffprobe,
        target_lufs=args.target_lufs,
        true_peak=args.true_peak,
        lra=args.lra,
        post_filters=args.post_filters,
        speech_cleanup=args.speech_cleanup,
    )
    print(
        f"Measured {stats['input_i']} LUFS, true peak {stats['input_tp']} dBTP; "
        f"mastered to {args.destination} at 48 kHz."
    )


if __name__ == "__main__":
    main()
