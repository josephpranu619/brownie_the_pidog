# Brownie Command Palette

Brownie's current local-control interface is a fuzzy-search command palette launched from Bash with `Ctrl+G`.

It uses `fzf` so common actions can be searched instead of memorized as aliases. Current entries include stand, sit, lie down, walk forward, battery status, passive diagnostics, camera, ultrasonic, touch, speaker, microphone, and Robot HAT MCU reset.

## Shell integration

The shell shortcut launches `brownie` as a normal foreground command. This keeps terminal ownership simple for `fzf` and interactive diagnostics.

## Motion rule

Walking always transitions through `stand` first and waits for that action to finish before the forward gait begins. This avoids starting a gait from an incompatible pose.

## Process model

Motion control and low-level diagnostics should not share the same long-lived hardware-owning process. The intended model is:

```text
menu launcher
  -> motion process
  -> diagnostic process
```

Only one hardware-owning process should be active at a time. This prevents GPIO and audio resource conflicts.
