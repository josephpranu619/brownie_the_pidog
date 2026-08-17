#!/usr/bin/env bash
set -euo pipefail

TARGET="$HOME/.hermes/hermes-agent/cli.py"

if [[ ! -f "$TARGET" ]]; then
    echo "ERROR: Hermes cli.py not found: $TARGET"
    exit 1
fi

python3 - "$TARGET" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

marker = "# Brownie: wake-word activation should honor voice.auto_tts"

if marker in s:
    print("Brownie wake auto-TTS patch already applied.")
    raise SystemExit(0)

old = """        with self._voice_lock:
            self._voice_mode = True
        self._voice_continuous = False
"""

new = """        with self._voice_lock:
            self._voice_mode = True

        # Brownie: wake-word activation should honor voice.auto_tts,
        # just like manually running /voice on.
        try:
            from hermes_cli.config import load_config
            _raw_voice = load_config().get("voice")
            _voice_cfg = _raw_voice if isinstance(_raw_voice, dict) else {}
            if _voice_cfg.get("auto_tts", False):
                with self._voice_lock:
                    self._voice_tts = True
        except Exception:
            pass

        self._voice_continuous = False
"""

if old not in s:
    raise SystemExit("ERROR: expected Hermes wake-word block not found; no changes made.")

p.write_text(s.replace(old, new, 1))
print("Applied Brownie wake auto-TTS patch.")
PY
