# Brownie Bring-up Status

This is the validated state reached during the initial Ubuntu 22.04 bring-up.

## Platform

- Raspberry Pi 4
- Ubuntu 22.04.5 LTS, aarch64
- Python 3.10.12
- ROS 2 Humble present
- Robot HAT 2.5.x line
- PiDog 1.3.13
- Vilib 0.3.19
- OV5647 5 MP camera

## Validated hardware and subsystems

- GPIO chips visible
- I2C buses visible
- expected devices detected on I2C bus 1
- Robot HAT MCU reset
- OV5647 camera detection
- full-resolution camera capture
- Robot HAT speaker playback
- Robot HAT microphone capture
- microphone channel-1 playback verification
- ultrasonic ranging
- dual-touch front/rear and slide gestures
- sound-direction sensor
- SH3001 IMU
- RGB chest strip
- battery-voltage reading
- servo initialization without binding
- stand
- sit
- lie
- controlled forward gait

## Diagnostic policy

The normal checker is passive by default. Hardware-active tests require explicit flags. Servo movement is intentionally excluded from automatic diagnostics.

## Known architecture issue still to refine

The current Brownie palette can release its PiDog object before launching a diagnostic, but some process-owned resources can remain awkward when control and low-level diagnostics are mixed in one long-running Python process. The planned refinement is stronger process isolation between the palette, motion controller, and hardware-diagnostic commands.

This is an architecture refinement, not an indication that the underlying ultrasonic, speaker, or microphone hardware is failing; those subsystems have been validated independently.
