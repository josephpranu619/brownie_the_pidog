#!/usr/bin/env bash
set -euo pipefail

VOICE_MODE="$HOME/.hermes/hermes-agent/tools/voice_mode.py"

if [ ! -f "$VOICE_MODE" ]; then
    echo "ERROR: Hermes voice_mode.py not found: $VOICE_MODE"
    exit 1
fi

python3 - "$VOICE_MODE" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

old = '''    players.append(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", file_path])
    if system == "Linux":
        players.append(["aplay", "-q", file_path])
'''

new = '''    # Brownie/Raspberry Pi: Edge TTS produces MP3. ffplay exits
    # successfully here but produces no audible output on Brownie's audio
    # stack. Decode MP3 through ffmpeg and pipe 24 kHz WAV/PCM to aplay,
    # which has been validated on the PiDog speaker.
    if (
        system == "Linux"
        and file_path.lower().endswith(".mp3")
        and shutil.which("ffmpeg")
        and shutil.which("aplay")
    ):
        players.append([
            "/bin/sh",
            "-c",
            f"ffmpeg -loglevel error -i {shlex.quote(file_path)} -f wav - | aplay -q",
        ])

    players.append(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", file_path])
    if system == "Linux":
        players.append(["aplay", "-q", file_path])
'''

if new in s:
    print("Brownie Edge audio patch already applied.")
elif old not in s:
    raise SystemExit("ERROR: expected Hermes player block not found")
else:
    p.write_text(s.replace(old, new, 1))
    print("Brownie Edge audio patch applied.")
PY
