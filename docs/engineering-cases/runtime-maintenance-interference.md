# Runtime Maintenance Interference on Brownie

**Date:** 2026-09-06  
**System:** SunFounder PiDog V2 on Raspberry Pi 4 / Ubuntu 22.04  
**Branch:** `feature/web-control`

## Problem

During autonomous/web-control testing, Brownie's UI showed a sudden CPU increase to roughly 43% with CPU temperature around 70°C, despite no intentional robotics workload that should have caused the spike.

This mattered because Brownie is intended to operate untethered and outdoors. A background operating-system job consuming a full CPU core can reduce responsiveness, increase thermals, and interfere with timing-sensitive audio and robotics workloads.

## Investigation

The first diagnostic was to identify the actual process instead of guessing from aggregate CPU telemetry:

```bash
ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -12
```

Observed:

```text
unattended-upgr ~99.6% CPU
pulseaudio      ~14.8% CPU
```

A follow-up service-status check showed that the long-lived `unattended-upgrades.service` process itself was only the shutdown helper and was not responsible for the CPU load.

The high-CPU worker completed before it could be inspected directly with `ps -fp <pid>`.

Systemd timer history then showed:

```text
apt-daily.timer last triggered at 17:23:32 UTC
```

The relevant journal window confirmed:

```text
17:23:32 Starting Daily apt download activities...
17:24:02 networkd-wait-online timeout
17:29:05 Finished Daily apt download activities.
apt-daily.service: Consumed 4min 16.824s CPU time.
```

This lined up with the observed runtime spike.

## Root Cause

Ubuntu's default APT timers were configured as:

```ini
# apt-daily.timer
[Timer]
OnCalendar=*-*-* 6,18:00
RandomizedDelaySec=12h
Persistent=true

# apt-daily-upgrade.timer
[Timer]
OnCalendar=*-*-* 6:00
RandomizedDelaySec=60m
Persistent=true
```

`Persistent=true` means a calendar timer can catch up a missed run after the machine starts again. The large randomized delay also means maintenance can occur at an unpredictable time inside the delay window.

That behavior is reasonable for a general-purpose server, but it conflicts with Brownie's requirement for predictable runtime resource usage.

## Safety Decision

Do **not** solve this by exposing a generic process-kill control in the web UI.

In particular:

- do not `kill -9` `apt`, `dpkg`, or unattended-upgrade workers;
- package-management operations can hold locks or be in the middle of filesystem/database changes;
- an abrupt kill can leave package state requiring manual recovery.

The preferred strategy is prevention and observability rather than reactive hard-killing.

## Brownie Runtime Policy

Target operating policy:

```text
Normal Brownie operation
    -> no surprise catch-up package maintenance at boot
    -> predictable CPU and thermal headroom

System-health monitor
    -> detect sustained high CPU
    -> identify top process
    -> surface process name + CPU in UI
    -> classify known OS-maintenance processes

Planned maintenance
    -> OS/package updates happen deliberately
    -> allow update to complete cleanly
    -> reboot if required
    -> validate Brownie services afterward
```

## Planned Timer Change

The first safe change is to override both APT calendar timers with:

```ini
[Timer]
Persistent=false
```

This prevents missed jobs from being immediately caught up after Brownie boots.

A second step should replace the broad randomized default windows with a deliberate maintenance schedule appropriate to Brownie's actual operating timezone and usage pattern.

The exact schedule should be set only after confirming Brownie's system timezone so that the configured `OnCalendar=` window is unambiguous.

## Planned UI Improvement

Extend system telemetry beyond aggregate CPU usage:

```text
System Health
  CPU            8%
  Temperature    52°C
  Top process    brownie-bodyd · 3%
  Maintenance    Idle
```

When sustained CPU load is high, the backend should report the actual top process rather than forcing the operator to SSH into the Pi.

Suggested threshold for investigation/UI warning:

- CPU above roughly 70% for ~10 seconds;
- then resolve and display the top CPU-consuming process;
- avoid automatic termination unless a future control is explicitly limited to known-safe workloads.

## Engineering Lessons / Interview Notes

1. Aggregate telemetry tells you **that** a problem exists; process-level telemetry tells you **why**.
2. Avoid killing infrastructure processes before identifying their role and failure mode.
3. General-purpose OS defaults are not automatically appropriate for embedded/robotic systems.
4. Background maintenance is a scheduling/resource-arbitration problem, not merely a CPU problem.
5. Embedded autonomy benefits from deterministic maintenance windows and explicit runtime headroom.
6. Good incident handling preserves evidence: process list -> service identity -> timer history -> journal correlation -> policy change.
7. Observability should be available through the robot's normal control surface, not only over SSH.

## Related Audio Observation

During the same session, Hermes produced repeated ALSA underruns during wake/listen/playback transitions. The APT CPU spike may have worsened timing pressure, but underruns were still observed after the package job ended, so the audio issue remains a separate engineering problem and must not be incorrectly attributed solely to system updates.

## Status

- Root cause of the unexpected CPU spike: **identified**.
- Hard-kill approach: **rejected**.
- Runtime maintenance policy: **defined**.
- `Persistent=false` timer override: **planned, not yet applied**.
- Deterministic maintenance schedule: **pending timezone confirmation**.
- UI top-process telemetry: **pending**.
