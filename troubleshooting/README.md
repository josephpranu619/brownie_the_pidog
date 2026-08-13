# Troubleshooting Memory

This folder records the problems encountered while bringing Brownie up on Ubuntu 22.04, what actually caused them, and how they were verified after repair.

The goal is not to collect random fixes. Each entry should preserve the reasoning that prevents us from rediscovering the same issue later.

## Known categories

- `ubuntu-compatibility.md` — assumptions made by Raspberry Pi OS-oriented installers and tools
- `camera.md` — libcamera, Picamera2, kmsxx/pykms, overlays, and sensor detection
- `audio.md` — ALSA, PulseAudio, Robot HAT playback/capture, and SSH audio pitfalls
- `gpio-and-robot-hat.md` — GPIO ownership, `lgpio`, MCU reset, and Robot HAT compatibility
- `python-compatibility.md` — Python 3.10 vs Python 3.11 assumptions
- `power-and-battery.md` — low-voltage behavior and charging lessons

## Entry format

Every troubleshooting note should answer:

1. What was the symptom?
2. What was the real root cause?
3. What fixed it?
4. How did we verify the fix?
5. What should we avoid doing next time?
