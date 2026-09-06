# Brownie Web Control — Autostart & Security Milestone

**Validated:** 2026-09-06  
**Branch:** `feature/web-control`  
**Robot:** SunFounder PiDog V2 (“Brownie”) on Raspberry Pi 4 / Ubuntu 22.04

## Milestone result

Brownie’s web-control stack now starts automatically after reboot and is remotely reachable only through the private Tailscale Serve HTTPS endpoint.

Validated after a real reboot:

- `brownie-bodyd.service` starts automatically as a user service;
- `brownie-web-api.service` starts FastAPI automatically;
- `brownie-web-ui.service` starts Vite automatically;
- user lingering keeps the user systemd manager available before interactive login;
- Tailscale Serve resumes automatically in background mode;
- `https://brownie.tail537e63.ts.net/` loads successfully and reports Brownie Online;
- no manual SSH startup command was required.

## Network hardening

The initial autostart service definitions bound Vite and FastAPI to all interfaces. Validation showed:

```text
0.0.0.0:8000
*:5173
```

That exposed the development UI/API directly to Brownie’s LAN. Because the API can control motion, camera, audio, and robot hardware, this was broader access than required.

The services were hardened to loopback-only bindings:

```text
127.0.0.1:8000  FastAPI
127.0.0.1:5173  Vite
```

Validated with `ss -ltnp` after restarting both systemd services.

The previous LAN UI URL:

```text
http://10.0.0.180:5173/
```

is no longer reachable, while the private Tailscale HTTPS URL remains functional.

## Current access architecture

```mermaid
flowchart LR
    Client[Authorized phone / tablet / desktop] -->|Tailscale encrypted tailnet| Serve[Tailscale Serve HTTPS]
    Serve -->|localhost proxy| Vite[127.0.0.1:5173]
    Vite -->|/api proxy| API[127.0.0.1:8000 FastAPI]
    API --> Sock[/tmp/brownie-body.sock]
    Sock --> Bodyd[brownie-bodyd]
    Bodyd --> Hardware[PiDog / Robot HAT]

    LAN[Ordinary LAN client] -. blocked .-> Vite
    LAN -. blocked .-> API
```

Tailscale Serve is configured in background mode and remains the intended remote entry point. Brownie uses **Serve**, not Funnel, so the control UI remains tailnet-private rather than public on the internet.

## Repo-owned recovery

The repository now contains the autostart configuration and recovery path:

```text
systemd/user/brownie-web-api.service
systemd/user/brownie-web-ui.service
systemd/user/brownie-bodyd.service
tools/install-web-control-autostart
architecture/web-control-recovery.md
```

The web service units in GitHub use loopback-only bindings, so a future restore inherits the hardened configuration.

The recovery script reinstalls the repo-owned user units, enables user lingering, enables the required services, and configures Tailscale Serve. Secrets/authentication credentials are intentionally not stored in Git.

## Controller behavior after boot

`brownie-bodyd` still starts **passively** by design. PiDog servo/hardware initialization occurs only when an explicit posture command requires it (for example Manual → Stand). This avoids Brownie unexpectedly moving merely because the computer rebooted.

Consequences while bodyd is passive:

- pose may report unknown/null;
- RGB-strip operations that require the initialized PiDog object are unavailable;
- ultrasonic passive-read behavior remains a known cleanup item;
- Manual → Stand initializes the hardware and restores normal initialized telemetry/control.

## Manual-control regression found during service migration

A frontend bug was found while switching the web processes to systemd: any posture HTTP `409` incorrectly discarded the browser’s local Manual lease ID. The still-active backend lease then appeared to the same browser as `Manual Control · IN USE / OTHER DEVICE`.

The validated fix keeps the local lease through ordinary rejected posture commands and leaves the heartbeat endpoint as the authority for actual lease loss/expiry.

## Next engineering item

Validate and repair Brownie’s autonomous voice path, beginning with the currently broken wake-word activation. The target integration is:

```text
AUTONOMOUS
  -> wake word detected
  -> Listening
  -> Thinking
  -> Talking
  -> Idle
```

The web UI must coexist with this voice loop. Manual mode should arbitrate robot motion ownership without unnecessarily disabling microphone listening, inference, or speech.
