# Brownie Behavior Validation

Validated on the physical Brownie PiDog V2 running Ubuntu 22.04.

All behavior-palette entries were exercised successfully:

1. Wake Up
2. Function Demonstration
3. Patrol
4. Response
5. Rest
6. Be Picked Up
7. Face Track
8. Push Up
9. Howling
10. Balance
11. Play PiDog with Keyboard
12. Ball Track

Wake Up includes Brownie-specific shorter tail-wag timing and exits cleanly back to the behavior menu.

Continuous behaviors are stopped with Ctrl+C and return to the Brownie Behaviors menu.

## SunFounder Controller / Remote Control
Validated on 2026-08-14:
- SunFounder Controller app sends live joystick/button data to Brownie.
- Remote control works over Tailscale, not just local Wi-Fi.
- PiDog movement/actions work from the remote app.
- Live camera stream works over Tailscale.
- Vilib `ifconfig` dependency replaced with Ubuntu-compatible `ip` lookup.
