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
- Conversational speech is handled by Hermes TTS and does not authorize a bark or other PiDog sound effect.
- Only use the PiDog bark helper when the user explicitly requests a bark, dog sound, or clearly dog-like vocal response.
- The `--confirm-audio` flag may only be used when the current-turn request explicitly authorizes audio output.
- Never add `--confirm-audio` automatically or based only on earlier conversation context.
- The `--confirm-light` flag may only be used when the current-turn request explicitly authorizes that light action.
- Never add `--confirm-light` automatically or based only on earlier conversation context.
- Prefer short, bounded actions.
- Brownie's body is owned by one persistent `brownie-bodyd` process.
- Never instantiate a separate `Pidog()` for normal Hermes motion commands.
- Never call `Pidog.close()` after a posture command, because it forces `stop_and_lie()`.

## Resource rules

Brownie runs on a Raspberry Pi 4.

- Minimize idle CPU and RAM usage.
- Use the single persistent Brownie body controller for motion.
- Do not run duplicate PiDog controller processes.
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

This command is safe to run automatically.

Validated guarded motion commands:

    python3 ~/brownie_the_pidog/hermes/skills/pidog-control/scripts/pidog_action.py stand --confirm-motion

    python3 ~/brownie_the_pidog/hermes/skills/pidog-control/scripts/pidog_action.py sit --confirm-motion

These commands are allowed only when the current user turn explicitly requests that motion.

The motion helper talks to the persistent Brownie body controller over:

    /tmp/brownie-body.sock

It does not instantiate `Pidog()` directly.

## Current implementation status

Validated:

- passive status
- persistent Brownie body ownership
- stand posture
- sit posture
- posture persistence after command completion
- posture-preserving body-controller shutdown
- guarded Hermes motion helper path

Not yet enabled or validated through this skill:

- lie
- walk
- forward/backward motion
- turning
- tail motion
- other expressive servo actions

Do not invent PiDog commands. Use only commands implemented and reviewed in this repository.
