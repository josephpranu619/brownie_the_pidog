# Brownie Roadmap

Brownie is being developed in layers so each new capability rests on a validated lower layer.

## Phase 1 — Hardware and platform bring-up

Status: complete for the initial Ubuntu 22.04 build.

Goals:

- stable Raspberry Pi 4 host
- Robot HAT support
- camera, audio, sensors, RGB, servos, and battery validated
- reusable diagnostic tooling

## Phase 2 — Reliable local control

Status: in progress.

Goals:

- `Ctrl+G` fuzzy command palette
- posture commands
- safe natural gait transitions
- process isolation between motion control and low-level diagnostics
- richer movement choices and behavior shortcuts

## Phase 3 — ROS 2 integration

Goals:

- expose Brownie's sensors and actuators through clean ROS 2 nodes/topics/services
- preserve hardware safety boundaries
- make local Brownie tools coexist with ROS 2 rather than replace them

## Phase 4 — Perception

Goals:

- camera streaming and image processing
- object/person/environment perception
- sensor fusion where useful

## Phase 5 — Voice interaction

Goals:

- microphone input pipeline
- speech recognition
- speaker responses
- command and conversational modes

## Phase 6 — AI integration

Goals:

- connect Brownie with Hermes/ChatGPT-style reasoning and tool use
- convert natural-language intent into bounded robot behaviors
- keep low-level safety and hardware control deterministic

## Phase 7 — Autonomous behaviors

Goals:

- environment-aware actions
- multi-step behaviors
- safe autonomy built on the validated local, ROS 2, perception, and voice layers
