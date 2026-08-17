#!/usr/bin/env bash
set -euo pipefail

echo "=== Brownie: Hermes configuration ==="

if ! command -v hermes >/dev/null 2>&1; then
    echo "ERROR: hermes is not installed."
    echo "Run scripts/setup/install_hermes.sh first."
    exit 1
fi

HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

if [[ ! -x "$HERMES_PY" ]]; then
    echo "ERROR: Hermes Python environment not found at:"
    echo "  $HERMES_PY"
    exit 1
fi

hermes config set model.default gpt-5.6-luna
hermes config set model.provider openai-codex
hermes config set terminal.backend local
hermes config set terminal.cwd "$HOME/brownie_the_pidog"

# Preferred Brownie voice.
hermes config set tts.edge.voice en-US-BrianNeural
hermes config set voice.auto_tts true

# Brownie wake word.
hermes config set wake_word.provider sherpa
hermes config set wake_word.phrase brownie

# Sherpa wake-word support needs pypinyin inside Hermes' own venv.
if ! "$HERMES_PY" -m pip --version >/dev/null 2>&1; then
    echo "Bootstrapping pip inside Hermes venv..."
    "$HERMES_PY" -m ensurepip --upgrade
fi

if ! "$HERMES_PY" -c "import pypinyin" >/dev/null 2>&1; then
    echo "Installing pypinyin for wake-word support..."
    "$HERMES_PY" -m pip install pypinyin
fi

echo
echo "Configured:"
hermes config get model.default
hermes config get model.provider
hermes config get terminal.backend
hermes config get terminal.cwd
hermes config get tts.edge.voice
hermes config get voice.auto_tts
hermes config get wake_word.provider
hermes config get wake_word.phrase

echo
echo "OAuth authentication is intentionally NOT stored in Git."
echo "On a fresh rebuild, authenticate separately with: hermes model"
