# Brownie the PiDog

Brownie is my SunFounder PiDog V2, built around a Raspberry Pi 4 and customized to run on Ubuntu 22.04 with ROS 2 Humble compatibility in mind.

This repository is the source of truth for how Brownie is built, operated, diagnosed, repaired, and extended.

## Using Brownie

The current local-control interface is a fuzzy command palette launched from a shell with `Ctrl+G`. It provides quick access to posture commands, a safe forward walk, battery status, and hardware diagnostics.

The control system is intentionally evolving. The command palette is the first interaction mode; future modes may include ROS 2 nodes, voice control, perception, and AI-assisted behavior.

## Repository guide

- `setup/` — how to rebuild Brownie from a fresh Ubuntu 22.04 Raspberry Pi 4
- `architecture/` — Brownie's hardware/software architecture and control model
- `troubleshooting/` — problems we encountered, root causes, fixes, and verification steps
- `docs/` — validation status and project roadmap
- `tools/` — Brownie-specific executable tools such as the command palette and diagnostic checker

## Current platform

- Raspberry Pi 4
- Ubuntu 22.04.5 LTS, aarch64
- Python 3.10.12
- ROS 2 Humble
- SunFounder Robot HAT
- SunFounder PiDog V2
- OV5647 5 MP camera

## Current capabilities

Brownie has been validated for camera capture, speaker playback, microphone capture and replay, ultrasonic distance sensing, dual-touch sensing, sound direction, IMU, RGB lighting, battery monitoring, servo initialization, posture control, and controlled forward walking.

## Start here

For a new machine, begin with `setup/README.md` and `setup/ubuntu-22.04-from-scratch.md`.

For a problem that has happened before, check `troubleshooting/README.md` before debugging from scratch.

For understanding why Brownie is structured the way it is, start with `architecture/README.md`.
