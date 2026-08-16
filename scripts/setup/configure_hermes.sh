#!/usr/bin/env bash
set -euo pipefail

echo "=== Brownie: Hermes configuration ==="

if ! command -v hermes >/dev/null 2>&1; then
    echo "ERROR: hermes is not installed."
    echo "Run scripts/setup/install_hermes.sh first."
    exit 1
fi

hermes config set model.default gpt-5.6-luna
hermes config set model.provider openai-codex
hermes config set terminal.backend local

echo
echo "Configured:"
hermes config get model.default
hermes config get model.provider
hermes config get terminal.backend

echo
echo "OAuth authentication is intentionally NOT stored in Git."
echo "On a fresh rebuild, authenticate separately with: hermes model"
