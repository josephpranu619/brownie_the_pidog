#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

SOUND_DIR = Path.home() / "pidog" / "sounds"
BARK_FILE = SOUND_DIR / "single_bark_1.mp3"


def main():
    parser = argparse.ArgumentParser(
        description="Brownie guarded audio helper"
    )
    parser.add_argument("action", choices=["bark"])
    parser.add_argument(
        "--volume",
        type=int,
        default=125,
        help="Software volume percent, 0-150",
    )
    parser.add_argument(
        "--confirm-audio",
        action="store_true",
        help="Required acknowledgement that audio output was explicitly requested",
    )
    args = parser.parse_args()

    if not args.confirm_audio:
        print(
            "REFUSED: audio output requires --confirm-audio after an explicit user request.",
            file=sys.stderr,
        )
        return 2

    if not BARK_FILE.exists():
        print(f"ERROR: bark sound not found: {BARK_FILE}", file=sys.stderr)
        return 1

    volume = max(0, min(150, args.volume))
    gain = volume / 100.0

    ffmpeg = subprocess.Popen(
        [
            "ffmpeg",
            "-loglevel", "error",
            "-i", str(BARK_FILE),
            "-filter:a", f"volume={gain}",
            "-f", "wav",
            "-"
        ],
        stdout=subprocess.PIPE,
    )

    aplay = subprocess.run(
        ["aplay"],
        stdin=ffmpeg.stdout,
    )

    if ffmpeg.stdout:
        ffmpeg.stdout.close()

    ffmpeg_rc = ffmpeg.wait()

    if ffmpeg_rc != 0 or aplay.returncode != 0:
        print("ERROR: audio playback failed", file=sys.stderr)
        return 1

    print(f"action 'bark' completed at volume {volume}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
