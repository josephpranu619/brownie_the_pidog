# Troubleshooting Memory

This folder records the problems encountered while bringing Brownie up on Ubuntu 22.04, what actually caused them, and how they were verified after repair.

The goal is not to collect random fixes. Each entry should preserve the reasoning that prevents us from rediscovering the same issue later.

## Current troubleshooting notes

- `camera.md` — camera stack, sensor detection, and build compatibility
- `audio.md` — Robot HAT playback/capture and Linux audio behavior
- `gpio-and-robot-hat.md` — GPIO ownership and Robot HAT compatibility
- `power-and-battery.md` — power, charging, and low-voltage lessons

Ubuntu- and Python-specific findings are currently documented in the main setup guide and can be split into dedicated troubleshooting files later if needed.

## Entry format

Every troubleshooting note should answer:

1. What was the symptom?
2. What was the real root cause?
3. What fixed it?
4. How did we verify the fix?
5. What should we avoid doing next time?
