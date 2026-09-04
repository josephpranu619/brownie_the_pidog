# Wake-Word Reliability — "Brownie"

## Problem

Brownie often requires the wake word "Brownie" to be spoken multiple times before Hermes begins listening.

Observed behavior:
- Often requires 3–6 attempts.
- Detection improves when "Brownie" is spoken in a deeper/base voice.
- Natural voice is husky, so forcing a different speaking style is not an acceptable final solution.

## System Path

Audio flows through:

VoiceHAT microphone
→ ALSA `mic`
→ PulseAudio `brownie_mic_boosted`
→ Hermes
→ Sherpa-ONNX keyword spotter

Understanding each layer separately prevents changing unrelated parameters.

## Investigation

### 1. Microphone service

Confirmed the active default PulseAudio source is:

`brownie_mic_boosted`

The source is available and RUNNING.

### 2. PulseAudio software gain

Measured:

- Volume: 100%
- Gain: 0.00 dB
- Muted: no

This means PulseAudio itself is not adding extra software amplification.

### 3. Hardware microphone gain

VoiceHAT capture device:

- ALSA card 1
- `robot-hat mic`
- Capture gain: 255 / 255
- 100%
- +25.00 dB

The hardware microphone gain is already at its maximum.

### 4. Actual microphone signal

Live RMS measurements showed approximately:

- Quiet room: 30–100 RMS
- Normal nearby speech: 700–1800 RMS
- Peaks around 1800+

Conclusion: the microphone has a strong signal-to-noise ratio and is not the primary cause of missed wake words.

### 5. Hermes wake-word provider

Configuration:

- Provider: Sherpa
- Phrase: `brownie`
- Wake word enabled

Hermes default wake sensitivity is `0.6`.

For Sherpa, Hermes maps sensitivity to:

`keywords_threshold = 0.05 + 0.4 * sensitivity`

Therefore:

- sensitivity 0.6 → threshold 0.29
- sensitivity 0.5 → threshold 0.25
- sensitivity 0.4 → threshold 0.21
- sensitivity 0.3 → threshold 0.17

Important: in Hermes' shared configuration, a **higher sensitivity value means stricter detection**.

### 6. Sensitivity experiments

Tested:

- 0.5 — still required approximately 6 attempts in one test
- 0.4 — somewhat improved
- 0.3 — similar to 0.4

Even at 0.3, Brownie commonly required 3–4 wake-word attempts, and a deeper voice worked better.

Conclusion: lowering the keyword threshold helps somewhat but does not solve the underlying recognition problem.

### 7. Sherpa keyword construction

Sherpa does not use a trained custom "Brownie" wake-word model.

Hermes takes the configured text phrase, uppercases it, converts it at runtime using Sherpa's BPE `text2token`, writes the generated token sequence into a temporary keyword file, and passes that to the generic streaming keyword spotter.

No custom pronunciation/token override was found in the Hermes wake-word implementation or documentation searched so far.

## Current Working Hypothesis

The microphone path is healthy.

The remaining reliability issue is likely caused by how Sherpa's generic open-vocabulary keyword model represents and recognizes the word "Brownie" for this speaker's natural pronunciation.

This is likely a keyword/model recognition issue rather than a microphone-gain issue.

## Engineering Principle Learned

Debug systems layer-by-layer:

1. Physical hardware
2. ALSA
3. PulseAudio
4. Actual measured signal
5. Application configuration
6. Recognition/model behavior

Do not keep tuning one layer after evidence has ruled it out.

Also define a stopping condition before tuning so engineering does not become endless trial-and-error.

## Status

Investigation ongoing.

Next question:

Can Sherpa support a better pronunciation/token representation for "Brownie", or should Brownie use a dedicated trained wake-word model instead of generic open-vocabulary keyword spotting?

## Final Solution

_To be completed once validated._

## Provider Resource Benchmark on Raspberry Pi 4

Measured with Brownie idle and wake listener active.

### Sherpa

Steady-state Hermes process:

- CPU: approximately 29–30% of one CPU core
- RSS: approximately 681,824 KB (~666 MiB)

### OpenWakeWord — bundled `hey_hermes` model

After settling:

- CPU: approximately 34–37% of one CPU core
- RSS: approximately 359,776 KB (~351 MiB)

### Interpretation

OpenWakeWord used roughly 5–7 percentage points more of one CPU core than Sherpa, but approximately 315 MiB less resident memory in this test.

The additional CPU usage was modest on the 4-core Raspberry Pi, while memory usage was substantially lower.

The bundled trained `hey_hermes` model also felt noticeably more reliable than Sherpa's open-vocabulary recognition.

Therefore OpenWakeWord passed the initial resource-safety test and is a viable candidate for a custom trained `Brownie` wake-word model.

A custom model should still be accepted only if:
- wake reliability improves materially,
- false triggers remain low,
- Hermes responsiveness remains normal,
- body/audio behavior is unaffected.

### Runtime acceptance result

After allowing OpenWakeWord to settle:

- CPU stabilized around 34–37% of one core.
- RSS stabilized around 359,776 KB (~351 MiB).
- Hermes remained responsive during normal use.
- The bundled trained `hey_hermes` wake model felt noticeably easier and more reliable to trigger than Sherpa's open-vocabulary `brownie` keyword.

Decision:
OpenWakeWord passed the runtime/resource feasibility check on Brownie's Raspberry Pi 4.

The next experiment is therefore a custom trained OpenWakeWord model for the exact wake word `Brownie`.

## Final Decision

The production configuration was restored to:

- Provider: Sherpa
- Wake phrase: `brownie`
- Sensitivity: `0.3`

This is more permissive than the original default and gives somewhat better recognition, but it does not completely solve the wake-word reliability issue.

### Why the issue is not considered fully solved

Evidence ruled out microphone sensitivity as the primary problem:

- hardware capture gain is already at the maximum (+25 dB),
- PulseAudio input is healthy and unmuted,
- measured speech RMS is strong relative to the quiet-room noise floor.

Lowering Sherpa's keyword threshold improved detection only modestly. Recognition still depends noticeably on how the word "Brownie" is spoken.

Hermes' Sherpa provider uses generic open-vocabulary BPE tokenization rather than a wake model trained specifically for the word "Brownie" or for this speaker.

### Alternative evaluated: OpenWakeWord

Hermes' bundled trained `hey_hermes` OpenWakeWord model was tested on Brownie's Raspberry Pi 4.

Observed runtime comparison:

| Provider | Idle CPU | Hermes RSS |
|---|---:|---:|
| Sherpa | ~29–30% of one core | ~666 MiB |
| OpenWakeWord | ~34–37% of one core | ~351 MiB |

The trained OpenWakeWord model felt substantially more reliable to trigger.

OpenWakeWord therefore passed the initial runtime feasibility test:
- only a modest CPU increase,
- substantially lower measured resident memory,
- no obvious disruption to normal Hermes operation.

Hermes supports a custom OpenWakeWord `.onnx` model for the exact word `Brownie`.

### Deferred work

Training a custom wake-word model is intentionally deferred.

Reason:
training introduces a separate machine-learning workflow that is substantially more complex than the current robotics/audio debugging task. It should be learned and evaluated as its own project rather than rushed into this fix.

### Production outcome

Keep Sherpa + `brownie` + sensitivity `0.3` for now.

Future improvement:
train and evaluate a dedicated OpenWakeWord `Brownie` model when the custom-model workflow can be approached deliberately.

## Key Engineering Lessons

1. Debug from lower layers upward instead of tuning the application first.
2. Measure signal quality before assuming microphone gain is inadequate.
3. Know what a configuration parameter actually controls before changing it.
4. Define a stopping condition for tuning experiments.
5. Benchmark an architectural alternative on the real target hardware before adopting it.
6. Compare both reliability and system resource cost.
7. A partially improved production configuration can be preferable to introducing an incompletely understood subsystem.
8. Preserve investigation history so future work starts from evidence instead of repeating experiments.
