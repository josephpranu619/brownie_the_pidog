# Brownie Engineering Context

Brownie is a SunFounder PiDog V2 running on a Raspberry Pi 4 with Ubuntu 22.04.

## Core rules

- Keep all setup and configuration changes reproducible through this Git repository.
- Prefer repo-managed scripts over one-off manual system changes.
- Keep the repository synchronized with GitHub after validated milestones.
- Minimize idle CPU and RAM usage; Brownie has Raspberry Pi 4-class resources.
- Do not run local LLM inference unless explicitly requested.
- Prefer lightweight, on-demand processes over persistent background services.

## PiDog safety

- Never move servos automatically during diagnostics or setup.
- Servo or other disruptive hardware actions require explicit opt-in.
- Validate hardware changes one subsystem at a time.
- Do not proceed past unresolved hardware or setup failures.

## Hermes

- Brownie-owned Hermes skills live under `hermes/skills/` in this repository.
- Upstream/bundled Hermes skills remain managed by Hermes itself.
- Never commit Hermes authentication tokens, OAuth state, API keys, or other secrets.
