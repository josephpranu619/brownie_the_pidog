#!/usr/bin/env bash
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/systemd/user/brownie-mic.service"
DST="$HOME/.config/systemd/user/brownie-mic.service"

mkdir -p "$HOME/.config/systemd/user"
install -m 0644 "$SRC" "$DST"

systemctl --user daemon-reload
systemctl --user enable brownie-mic.service

echo "Installed: $DST"
echo "Enabled: brownie-mic.service"
