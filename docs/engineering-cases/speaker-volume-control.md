# Speaker Volume Control

## Goal

Add a simple, safe way to change Brownie's speaker volume from the Brownie tuning interface.

This control is also intended to become the backend for a future phone interface so Brownie's volume can be adjusted quickly, for example during nighttime use.

## Hardware Control

Brownie's Robot HAT exposes:

- mixer control: `robot-hat speaker`
- ALSA card: `1`
- raw playback range: `0–255`
- percentage control accepted directly by `amixer`

Example command:

    amixer -c 1 sset 'robot-hat speaker' 50%

Observed result:

- raw value: `128`
- reported volume: `50%`

## Implementation

`tools/brownie-tuning` now provides:

- Show speaker volume
- Set speaker volume

The user-facing range is:

- `0%` = silent
- `100%` = maximum hardware volume

Input is validated to whole numbers from 0 through 100.

The implementation uses percentages directly rather than exposing the hardware's raw `0–255` scale.

## Validation

Tested through Brownie Hub:

- current volume displayed correctly at 50%
- changed volume from 50% to 20%
- readback reported 20%

The audio initialization service was restarted with:

    systemctl --user restart brownie-mic.service

After restart, the speaker remained at 20%.

Therefore the Robot HAT speaker mixer is a suitable persistent runtime control for Brownie's volume.

## Future Direction

Expose the same volume-control backend through a phone-accessible Brownie control interface.

This would allow fast adjustments such as lowering volume for nighttime use without opening an SSH session.
