# Rebuilding Brownie on Ubuntu 22.04

This guide captures the working path used for Brownie's Raspberry Pi 4.

## Target environment

- Raspberry Pi 4
- Ubuntu 22.04.5 LTS, aarch64
- Python 3.10.12
- ROS 2 Humble may coexist with the PiDog stack

Keep `/usr/bin/python3` on the Ubuntu system Python. Do not replace it with Python 3.11; ROS 2 Humble packages on Jammy are built around Python 3.10.

## 1. Base packages

Install normal build and hardware-development prerequisites first: Git, pip/setuptools, I2C tools, ALSA tools, SoX, development headers, and Meson/Ninja as needed by the camera stack.

Enable I2C and SPI before validating Robot HAT devices.

Expected I2C devices on Brownie were visible on bus 1 at:

```text
0x15  0x36  0x74
```

## 2. Robot HAT

Clone SunFounder's Robot HAT repository and use branch `2.5.x`.

Brownie's working version was 2.5.5.

The upstream installer assumes Raspberry Pi OS/Debian version behavior in a few places. On Ubuntu 22.04, the Debian-version detection needed a compatibility patch so the installer continued as Debian 12-compatible for its dependency logic.

After installation, install `lgpio` if it is not already present.

### Ubuntu GPIO compatibility patch

Robot HAT's `device.py` expects `pinctrl` or `raspi-gpio` for certain one-shot GPIO controls. Ubuntu on Brownie's Pi did not provide either command.

A fallback using `lgpio` on gpiochip0 was added to `set_pin()` so Robot HAT operations such as MCU reset and speaker-enable work without Raspberry Pi OS-specific utilities.

Verify with:

```bash
robot_hat reset_mcu
```

Expected result:

```text
Onboard MCU reset.
```

## 3. Vilib

Clone SunFounder's Vilib repository and install it after Robot HAT.

Brownie's working Vilib version was 0.3.19.

The installer required the same Ubuntu/Debian-version compatibility adjustment as Robot HAT.

A Flask/blinker packaging conflict was resolved by reinstalling Flask/blinker into the system pip environment used by this robot build.

Vilib depends on a working Picamera2/libcamera stack, so camera setup must be completed before treating Vilib import failures as a Vilib problem.

## 4. Camera stack

Brownie uses an OV5647 5 MP camera.

The Ubuntu packages available during the bring-up were not sufficient for the desired Raspberry Pi camera stack, so libcamera, kmsxx/pykms, Picamera2, and rpicam-apps were assembled manually.

See `camera-stack.md` for the detailed compatibility notes.

The critical boot configuration is:

```ini
camera_auto_detect=0
dtoverlay=ov5647
```

A wrong `imx219` overlay caused the initial camera probe failure.

Verify with:

```bash
rpicam-hello --list-cameras
```

Brownie should report an OV5647 sensor at 2592x1944.

## 5. PiDog

Clone SunFounder's PiDog repository and install the package.

Brownie's working version was 1.3.13.

### Python 3.10 compatibility

The PiDog source used `enum.StrEnum`, which is Python 3.11-only. Brownie intentionally stays on Python 3.10 for Ubuntu 22.04 / ROS 2 Humble compatibility.

`dual_touch.py` was patched to use:

```python
from enum import Enum

class TouchStyle(str, Enum):
    ...
```

Reinstall the package after patching so the globally installed copy contains the change.

### Headless audio compatibility

PiDog's speaker helpers attempted to run `sudo killall pulseaudio`. On Brownie's headless SSH environment this could leave background sudo prompts attached to the terminal and later produce broken sudo/TTY behavior.

Those calls were disabled in Brownie's installed PiDog source. Audio diagnostics use `pasuspender` instead of killing PulseAudio.

## 6. Audio

The Robot HAT appears as an ALSA playback and capture device.

Use `plughw:1,0`, not raw `hw:1,0`, for flexible format conversion.

The microphone is exposed as two channels, but Brownie's useful signal is on channel 1. Treat it as mono channel 1 for diagnostics and playback.

See `audio-stack.md`.

## 7. Validate before motion

Before moving servos, validate:

- GPIO chips
- I2C devices and addresses
- Robot HAT MCU reset
- camera detection and capture
- speaker
- microphone capture/playback
- ultrasonic
- dual touch
- sound direction
- IMU
- RGB strip
- battery voltage

Then perform controlled servo initialization followed by stand/sit tests.

Do not put servo movement inside the default diagnostic run.

## 8. Brownie custom layer

Brownie's custom integration tools live in this repository under `tools/`:

- `pidog_check.py` — passive and explicit hardware diagnostics
- `brownie` — direct controls and diagnostics palette
- `brownie-behaviors` — PiDog example-behavior palette
- `brownie-hub` — top-level launcher for Brownie tools

Create command symlinks:

```bash
mkdir -p ~/bin
ln -sf ~/brownie_the_pidog/tools/brownie ~/bin/brownie
ln -sf ~/brownie_the_pidog/tools/brownie-behaviors ~/bin/brownie-behaviors
ln -sf ~/brownie_the_pidog/tools/brownie-hub ~/bin/brownie-hub
```

Ensure `~/bin` is on `PATH`.

Brownie's top-level keyboard shortcut is `Ctrl+G`. Add this exact Bash binding to `~/.bashrc`:

```bash
bind '"\C-g":"brownie-hub\C-m"'
```

## 9. Final verification

A healthy Brownie should be able to:

1. boot and remain reachable over SSH;
2. report the camera;
3. capture a full-resolution JPEG;
4. play speaker audio;
5. record and replay microphone channel 1;
6. read ultrasonic distance;
7. read touch, sound-direction, and IMU sensors;
8. control RGB lighting;
9. initialize servos without binding;
10. stand, sit, lie, and perform a controlled forward gait.
