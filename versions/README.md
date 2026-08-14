# Brownie Rebuild Ground Truth

This directory records the known-working software state for rebuilding Brownie from a fresh Raspberry Pi 4 / Ubuntu 22.04 installation.

Read these in this order:

1. `ubuntu-packages.md` — base manually installed Ubuntu prerequisites
2. `vendor-repos.md` — exact Robot HAT, PiDog, and Vilib source commits
3. `python-stack.md` — known-working Python package versions
4. `camera-stack.md` — exact camera revisions, build configuration, boot settings, Python bindings, and native-library state

Vendor compatibility patches are stored under `../patches/`.

The full rebuild procedure is maintained in `../setup/ubuntu-22.04-from-scratch.md`.

Important: a version or configuration should only be added here after it has been observed or validated on the working Brownie system.
