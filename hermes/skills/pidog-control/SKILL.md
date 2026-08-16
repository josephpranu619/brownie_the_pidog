---
name: pidog-control
description: Safely inspect and control Brownie, a SunFounder PiDog V2 running on Raspberry Pi 4. Use for PiDog status checks, explicitly requested motion, sound, expressive actions, and RGB light control.
---

# Brownie PiDog Control

This skill controls Brownie, a SunFounder PiDog V2.

## Safety rules

- Passive status checks may run automatically.
- Never move servos automatically.
- Any posture or movement action requires an explicit user request in the current turn that names or clearly implies that action.
- The `--confirm-motion` flag may only be used when that current-turn request authorizes the specific requested movement.
- Never add `--confirm-motion` automatically, speculatively, or based only on earlier conversation context.
- Never run `safe-test` automatically.
- Never run arbitrary PiDog demo scripts without explicit approval.
- Sound and RGB actions require an explicit user request.
- Prefer short, bounded actions.
- Do not start persistent PiDog controller services unless explicitly required and approved.

## Resource rules

Brownie runs on a Raspberry Pi 4.

- Minimize idle CPU and RAM usage.
- Prefer direct, short-lived commands over persistent daemons.
- Do not run local LLM inference.
- Avoid unnecessary browser or container runtimes.

## Repository ownership

Brownie-specific PiDog/Hermes code is maintained in:

`~/brownie_the_pidog/hermes/skills/pidog-control/`

The Git repository is the source of truth.

Do not store authentication credentials or secrets in this skill.

## Implemented commands

Passive status check:

    python3 ~/brownie_the_pidog/hermes/skills/pidog-control/scripts/pidog_status.py

This command is safe to run automatically. It does not instantiate Pidog(), move servos, play audio, control lights, or start background services.

## Current implementation status

Only the passive status helper is implemented and reviewed.

Do not invent PiDog commands. Use only commands implemented and reviewed in this repository.
