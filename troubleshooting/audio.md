# Audio Troubleshooting

Brownie's Robot HAT provides both playback and capture through ALSA, while the Ubuntu user session also runs PulseAudio.

## Direct hardware test reports device busy

### Symptom

A direct speaker or microphone test against the Robot HAT ALSA device reports that the device or resource is busy.

### Root cause

PulseAudio is legitimately holding the sound-card control devices. The hardware itself can still be healthy.

### Resolution

Brownie's hardware diagnostics temporarily suspend PulseAudio for the duration of the direct ALSA operation and then allow it to resume. This preserves the normal desktop/user audio service rather than terminating it.

### Verification

A successful speaker test produces audible left/right playback. A successful microphone test records five seconds from channel 1, normalizes that channel, and plays the recording back through the Robot HAT speaker.

## Microphone appears stereo but one channel is silent

### Symptom

Capture succeeds but one exposed channel contains essentially no useful signal.

### Root cause

Brownie's useful microphone signal is on channel 1 even though ALSA exposes a two-channel stream.

### Resolution

Treat the microphone as mono channel 1 for analysis and replay.

## Headless SSH becomes unhealthy after PiDog audio calls

### Symptom

After a PiDog script exits, later privilege prompts in the same SSH terminal can behave incorrectly.

### Root cause

The vendor audio workaround attempted a privileged PulseAudio reset from inside the PiDog library. In a headless session this could leave a background password prompt attached to the pseudo-terminal.

### Resolution

Brownie's PiDog installation disables that hidden privilege-changing audio workaround. Explicit audio diagnostics use bounded PulseAudio suspension instead.

### Lesson

Do not solve direct-ALSA contention by indiscriminately terminating the user's audio server from inside robot-library helper functions.

## Known-good Brownie audio mapping

On the working Raspberry Pi 4 / Ubuntu 22.04 build:

- ALSA playback card 0: `bcm2835 Headphones`
- ALSA playback card 1: `snd_rpi_googlevoicehat_soundcar`
- ALSA capture card 1: `snd_rpi_googlevoicehat_soundcar`
- Brownie Robot HAT audio device: card 1, device 0

Use `plughw:1,0` for direct playback/capture tests so ALSA can perform format conversion.

Useful verification commands:

```bash
aplay -l
arecord -l
```

## PulseAudio runtime

Known-working Ubuntu packages:

- `pulseaudio`: `1:15.99.1+dfsg1-1ubuntu2.2`
- `pulseaudio-utils`: `1:15.99.1+dfsg1-1ubuntu2.2`
- `pasuspender`: `15.99.1` at `/usr/bin/pasuspender`
