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
changed = False

# 1) Initialize Brownie's half-duplex follow-up state.
marker_init = "self._brownie_followup_mode = False  # Half-duplex follow-ups after wake"
if marker_init not in s:
    old = """        self._voice_continuous = False  # Whether to auto-restart after agent responds
        self._voice_tts_done = threading.Event()  # Signals TTS playback finished
"""
    new = """        self._voice_continuous = False  # Whether to auto-restart after agent responds
        self._brownie_followup_mode = False  # Half-duplex follow-ups after wake
        self._voice_tts_done = threading.Event()  # Signals TTS playback finished
"""
    if old not in s:
        raise SystemExit("ERROR: voice-state initialization block not found.")
    s = s.replace(old, new, 1)
    changed = True

# 2) Wake activation honors voice.auto_tts.
marker_tts = "# Brownie: wake-word activation should honor voice.auto_tts"
if marker_tts not in s:
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
        raise SystemExit("ERROR: wake auto-TTS block not found.")
    s = s.replace(old, new, 1)
    changed = True

# 3) Wake activation opens Brownie's half-duplex conversation.
wake_followup = """        self._voice_continuous = False
        self._brownie_followup_mode = True
        try:
            self._voice_start_recording()
"""
if wake_followup not in s:
    old = """        self._voice_continuous = False
        try:
            self._voice_start_recording()
"""
    if old not in s:
        raise SystemExit("ERROR: wake recording block not found.")
    s = s.replace(old, wake_followup, 1)
    changed = True

# 4) Keep wake detector paused while Brownie conversation is open.
old = """                        or getattr(self, "_voice_processing", False)
                        or not self._pending_input.empty()
"""
new = """                        or getattr(self, "_voice_processing", False)
                        or getattr(self, "_brownie_followup_mode", False)
                        or not self._pending_input.empty()
"""
if new not in s:
    if old not in s:
        raise SystemExit("ERROR: wake watchdog block not found.")
    s = s.replace(old, new, 1)
    changed = True

# 5) Brownie follow-up mode closes quietly after one genuine silent listen.
marker_close = "if self._brownie_followup_mode or self._no_speech_count >= 3:"
if marker_close not in s:
    old = """                    if self._no_speech_count >= 3:
                        self._voice_continuous = False
                        self._no_speech_count = 0
                        _cprint(f"{_DIM}No speech detected 3 times, continuous mode stopped.{_RST}")
                        stop_continuous_restart = True
"""
    new = """                    if self._brownie_followup_mode or self._no_speech_count >= 3:
                        self._voice_continuous = False
                        self._brownie_followup_mode = False
                        self._no_speech_count = 0
                        stop_continuous_restart = True
"""
    if old not in s:
        raise SystemExit("ERROR: silence shutdown block not found.")
    s = s.replace(old, new, 1)
    changed = True

# 6) Restart capture during Brownie's half-duplex conversation.
new = """                (self._voice_continuous or getattr(self, "_brownie_followup_mode", False))
                and not submitted
"""
if new not in s:
    old = """                self._voice_continuous
                and not submitted
"""
    if old not in s:
        raise SystemExit("ERROR: no-speech restart block not found.")
    s = s.replace(old, new, 1)
    changed = True

# 7) Reopen mic only after TTS has completely finished.
new = """                        if (
                            self._voice_mode
                            and (self._voice_continuous or getattr(self, "_brownie_followup_mode", False))
                            and not self._voice_recording
                        ):
"""
if new not in s:
    old = """                        if self._voice_mode and self._voice_continuous and not self._voice_recording:
"""
    if old not in s:
        raise SystemExit("ERROR: post-TTS restart block not found.")
    s = s.replace(old, new, 1)
    changed = True

if changed:
    p.write_text(s)
    print("Applied Brownie wake + half-duplex conversation patches.")
else:
    print("Brownie wake + half-duplex conversation patches already applied.")
PY
