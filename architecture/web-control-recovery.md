# Brownie Web-Control Recovery

This document captures the reproducible setup for Brownie's personal web-control stack so the robot can be restored from GitHub after a reimage or hardware failure.

## What GitHub owns

The repository contains:

- `systemd/user/brownie-mic.service`
- `systemd/user/brownie-bodyd.service`
- `systemd/user/brownie-web-api.service`
- `systemd/user/brownie-web-ui.service`
- `tools/install-web-control-autostart`
- FastAPI backend, React/Vite frontend, Brownie body controller, Voice recording code, and Tailscale-compatible Vite host configuration.

No Tailscale auth keys, passwords, or other credentials belong in Git.

## Expected Brownie paths

The current service files assume:

- Linux user: `pranu`
- Repo: `/home/pranu/brownie_the_pidog`
- FastAPI venv: `/home/pranu/brownie_the_pidog/app/backend/.venv`
- npm: `/home/pranu/.local/bin/npm`
- bodyd socket: `/tmp/brownie-body.sock`
- Vite port: `5173`
- FastAPI port: `8000`

If these paths change, update the repo-owned service files before installing them.

## Prerequisites after a fresh OS install

Before restoring autostart:

1. Clone this repository and check out the intended branch.
2. Reinstall the project's Python/backend and Node/frontend dependencies.
3. Install and authenticate Tailscale, joining Brownie to the intended private tailnet.
4. Confirm Robot HAT / PiDog dependencies and audio setup are present.

Do not store Tailscale auth keys in this repository.

## Restore autostart

From the repo root:

```bash
chmod +x tools/install-web-control-autostart
./tools/install-web-control-autostart --start
```

The installer:

1. Copies the repo-owned user service files into `~/.config/systemd/user/`.
2. Reloads the user systemd manager.
3. Enables `brownie-bodyd.service`, `brownie-web-api.service`, and `brownie-web-ui.service`.
4. Enables systemd linger for the current user so user services can start at boot before an interactive login.
5. Configures private Tailscale Serve in background mode for Vite on port `5173`.
6. With `--start`, restarts the enabled Brownie services immediately.

Without `--start`, the script installs/enables everything but leaves currently running manual development processes alone.

## Why Tailscale is not another user service

On Linux, Tailscale runs as a system service. Brownie's web UI uses Tailscale Serve with `--bg`; Tailscale documents that background Serve configuration persists and automatically resumes after reboot or a Tailscale restart. The repo therefore records the Serve command in the restore installer instead of creating a duplicate custom Tailscale service.

The intended exposure is **Tailscale Serve only**, private to the tailnet. Do not replace it with Tailscale Funnel unless public internet exposure is explicitly intended.

## Validation after restore or reboot

Check services:

```bash
systemctl --user status brownie-bodyd.service --no-pager
systemctl --user status brownie-web-api.service --no-pager
systemctl --user status brownie-web-ui.service --no-pager
```

Check local APIs:

```bash
curl http://127.0.0.1:8000/api/system
curl http://127.0.0.1:8000/api/status
curl http://127.0.0.1:8000/api/distance
```

Check Serve:

```bash
tailscale serve status
```

Then open Brownie's private HTTPS URL from an authorized tailnet device and validate:

- UI shows Online.
- Manual lease can be acquired/released.
- Stand/Sit works.
- Camera loads.
- Voice library loads.
- This-device microphone records over HTTPS.
- Brownie recording playback works.
- Distance returns a numeric value after PiDog hardware is initialized.

## Distance note

The body controller intentionally starts passive and does not construct `Pidog()` until a posture/body command needs hardware. The normal initialized distance path uses `DOG.read_distance()` and has been validated on real hardware. A passive pre-initialization ultrasonic read may return `null`; do not reset or reinitialize Robot HAT hardware from another process just to force a passive reading, because Brownie's one-owner architecture takes priority.

## Operational rule

Treat the repository as the source of truth. If an installed service in `~/.config/systemd/user/` needs to change, edit the matching file under `systemd/user/` in Git first, then reinstall/reload it. Avoid untracked one-off edits to installed unit files.
