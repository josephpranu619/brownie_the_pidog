# GPIO and Robot HAT Troubleshooting

## Robot HAT utility expects unavailable Raspberry Pi OS helpers

### Symptom

Robot HAT operations that toggle a GPIO line fail on Ubuntu because the expected Raspberry Pi OS command-line helpers are absent.

### Root cause

The underlying GPIO hardware is available, but the vendor helper path assumes tools that are not present on Brownie's Ubuntu installation.

### Resolution

Brownie's Robot HAT installation uses `lgpio` on the primary GPIO chip as a fallback for one-shot GPIO changes. This restored operations such as onboard MCU reset and speaker enable.

### Verification

The Robot HAT MCU reset operation completes successfully and reports that the onboard MCU was reset.

## GPIO busy after running Brownie control

### Symptom

A low-level diagnostic, especially ultrasonic ranging, can fail with a GPIO-busy error after the high-level PiDog controller has been active in the same long-running process.

### Root cause

The PiDog stack initializes and owns GPIO-backed resources. Closing the high-level object does not always make a persistent interpreter equivalent to a completely fresh process.

### Resolution direction

Keep motion control and low-level diagnostics in separate processes. The command palette should act as an orchestrator rather than as the permanent owner of every hardware library.

### Verification

The ultrasonic diagnostic succeeds when run from a fresh process after the Brownie controller process has exited.
