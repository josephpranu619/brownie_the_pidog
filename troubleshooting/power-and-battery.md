# Power and Battery Troubleshooting

## Robot HAT appears dead after low-voltage event

### Symptom

Brownie can appear unresponsive after the battery has fallen very low, especially after an unsuitable charging attempt or an abrupt voltage drop.

### Root cause

The battery/protection circuitry can enter a protected low-voltage state. That can look like a dead Robot HAT even when the electronics are still healthy.

### Resolution

Charge from the expected stable 5 V input with the HAT switched off during charging, then re-check battery voltage before servo movement.

### Verification

After a proper charge Brownie's battery recovered to the normal fully charged range and the Pi/Robot HAT returned to stable operation.

## Lesson from the charging incident

Do not assume a multi-voltage USB power source will behave like a simple 5 V supply at the HAT charge input. Use a known stable 5 V source appropriate for the charging path.

## Movement policy

Battery voltage is checked before motion tests. The diagnostic tool warns when voltage is very low, and servo movement is intentionally excluded from passive diagnostics.
