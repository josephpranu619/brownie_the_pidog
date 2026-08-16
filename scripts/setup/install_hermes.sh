#!/usr/bin/env bash
set -euo pipefail

echo "=== Brownie: Hermes Agent installation ==="

if command -v hermes >/dev/null 2>&1; then
    echo "Hermes is already installed:"
    hermes --version
    exit 0
fi

curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash -s -- --skip-browser

echo
echo "Hermes installation complete."
echo "Open a new shell, or run: source ~/.bashrc"
