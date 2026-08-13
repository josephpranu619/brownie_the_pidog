# System Overview

Brownie is a SunFounder PiDog V2 customized around a Raspberry Pi 4 running Ubuntu 22.04.5 LTS.

## High-level flow

```text
User over SSH
   |
   +--> Ctrl+G -> Brownie command palette (fzf)
   |               |
   |               +--> motion commands -> PiDog Python API -> Robot HAT -> servos
   |               +--> diagnostics -> pidog_check.py -> individual hardware tests
   |
   +--> direct shell / Python development
   |
   +--> ROS 2 Humble (future deeper integration)
```

## Hardware

- Raspberry Pi 4
- SunFounder Robot HAT
- PiDog V2 servo assemblies
- OV5647 5 MP camera
- Robot HAT speaker
- Robot HAT microphone
- Ultrasonic distance sensor
- Dual touch sensor
- Sound-direction sensor
- SH3001 IMU
- RGB chest strip
- Robot HAT battery / power system

## Software layers

### Operating system

Ubuntu 22.04.5 LTS, 64-bit, on Raspberry Pi 4.

The system Python remains Python 3.10. This is intentional because ROS 2 Humble packages on Ubuntu 22.04 are built for the Jammy system Python environment.

### Robot HAT

SunFounder Robot HAT 2.5.x supplies GPIO/I2C/SPI access, MCU control, audio helpers, battery voltage reading, and device abstractions used by PiDog.

Brownie's Ubuntu setup includes a compatibility patch in Robot HAT's `device.py` so MCU reset/speaker-enable GPIO control can fall back to `lgpio` when Raspberry Pi OS-specific commands such as `pinctrl` or `raspi-gpio` are unavailable.

### PiDog

SunFounder PiDog 1.3.x provides the high-level robot API: leg/head/tail control, actions, ultrasonic, touch, sound direction, IMU, RGB, and sound effects.

A Python 3.10 compatibility patch replaces use of Python 3.11-only `enum.StrEnum` with a `str, Enum` class in `dual_touch.py`.

PiDog's Ubuntu installation was also patched so its speaker helpers do not run `sudo killall pulseaudio`, which previously interfered with headless SSH sessions.

### Camera

Brownie uses Raspberry Pi's modern camera stack:

```text
OV5647 sensor
  -> libcamera
  -> Picamera2 / rpicam-apps
  -> Vilib / custom applications
```

The camera is explicitly configured as OV5647 in `/boot/firmware/config.txt`.

### Audio

ALSA exposes the Robot HAT sound card for playback and capture. PulseAudio normally owns the sound devices in the user session. Low-level diagnostics use `pasuspender` so ALSA hardware tests can temporarily access the card without killing PulseAudio.

The microphone appears as stereo through ALSA, but Brownie's useful microphone signal is on channel 1; channel 2 is effectively silent. Diagnostic playback therefore extracts channel 1 before normalization and playback.

## Safety model

Passive diagnostics never move servos. Motion is initiated only through explicit commands.

Walking should not begin directly from arbitrary poses. Brownie's control layer first transitions to `stand`, waits for completion, and only then begins the gait.

## Process isolation

The PiDog controller can retain GPIO/audio resources while the Python process remains alive. Hardware diagnostics should therefore run in a clean process after the motion controller has fully exited, rather than competing with a live PiDog instance.
