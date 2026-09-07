"""Brownie-specific Hermes runtime hooks.

Loaded automatically by Python when ``integrations/hermes`` is on PYTHONPATH.
This keeps Brownie's hardware/audio adaptations in the Brownie repository instead
of modifying the installed Hermes checkout in ~/.hermes.

Responsibilities:
- replace Hermes' PortAudio/sounddevice record beeps with 48 kHz PulseAudio WAV
  playback, matching Brownie's Robot HAT output path;
- drive Brownie's listening LED through brownie-bodyd from Hermes' stable voice
  cue boundary: 880 Hz start cue = listening on, 660 Hz double stop cue = off.

All hooks are best-effort: a missing body daemon or speaker must never break the
Hermes voice loop.
"""

from __future__ import annotations

import math
import os
import socket
import struct
import subprocess
import sys
import wave
from pathlib import Path

BODY_SOCKET = Path("/tmp/brownie-body.sock")
BEEP_RATE = 48_000
BEEP_AMPLITUDE = 0.22
BEEP_GAP_SECONDS = 0.08
BEEP_FADE_SECONDS = 0.008
BEEP_DIR = Path("/tmp/brownie-hermes-beeps")


def _body_command(command: str) -> str:
    """Send a best-effort command to brownie-bodyd and return its reply."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            sock.connect(str(BODY_SOCKET))
            sock.sendall((command + "\n").encode())
            return sock.recv(4096).decode().strip()
    except Exception as exc:
        return f"ERROR: {exc}"


def _beep_path(frequency: int, duration: float, count: int) -> Path:
    duration_ms = max(1, int(round(duration * 1000)))
    return BEEP_DIR / f"{frequency}hz-{duration_ms}ms-x{count}.wav"


def _write_beep(path: Path, *, frequency: int, duration: float, count: int) -> None:
    BEEP_DIR.mkdir(parents=True, exist_ok=True)

    tone_samples = max(1, int(BEEP_RATE * duration))
    fade_samples = min(int(BEEP_RATE * BEEP_FADE_SECONDS), tone_samples // 2)
    gap_samples = int(BEEP_RATE * BEEP_GAP_SECONDS)
    pcm = bytearray()

    for beep_index in range(count):
        for i in range(tone_samples):
            gain = 1.0
            if fade_samples:
                if i < fade_samples:
                    gain = i / fade_samples
                elif i >= tone_samples - fade_samples:
                    gain = max(0.0, (tone_samples - i - 1) / fade_samples)

            value = BEEP_AMPLITUDE * gain * math.sin(2 * math.pi * frequency * i / BEEP_RATE)
            pcm.extend(struct.pack("<h", int(value * 32767)))

        if beep_index < count - 1:
            pcm.extend(b"\x00\x00" * gap_samples)

    temp_path = path.with_suffix(".tmp.wav")
    with wave.open(str(temp_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(BEEP_RATE)
        wav_file.writeframes(bytes(pcm))
    os.replace(temp_path, path)


def _brownie_play_beep(frequency: int = 880, duration: float = 0.12, count: int = 1) -> None:
    """Hermes-compatible voice cue using Brownie's clean PulseAudio path.

    Hermes uses one 880 Hz beep immediately before recording and two 660 Hz beeps
    immediately after recording stops. Those stable cue semantics also drive the
    listening LED, avoiding dependence on Hermes' internal CLI class layout.
    """
    try:
        frequency = int(frequency)
        count = max(1, int(count))
        duration = float(duration)

        led_action = "none"
        led_reply = "not-sent"
        if frequency == 880 and count == 1:
            led_action = "loading"
            led_reply = _body_command("led loading")
        elif frequency == 660 and count == 2:
            led_action = "off"
            led_reply = _body_command("led off")

        print(
            f"Brownie voice cue: {frequency}Hz x{count} -> LED {led_action}; bodyd={led_reply}",
            file=sys.stderr,
            flush=True,
        )

        path = _beep_path(frequency, duration, count)
        if not path.exists():
            _write_beep(
                path,
                frequency=frequency,
                duration=duration,
                count=count,
            )

        subprocess.run(
            ["paplay", str(path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=max(2.0, count * (duration + BEEP_GAP_SECONDS) + 1.0),
        )
    except Exception as exc:
        print(f"Brownie voice cue hook error: {exc}", file=sys.stderr, flush=True)


def _install_hooks() -> None:
    try:
        from tools import voice_mode

        voice_mode.play_beep = _brownie_play_beep
    except Exception as exc:
        print(f"Brownie Hermes hook unavailable: {exc}", file=sys.stderr, flush=True)
        return

    print(
        "Brownie Hermes hooks active: 48 kHz beeps + cue-driven listening LED",
        file=sys.stderr,
        flush=True,
    )


_install_hooks()
