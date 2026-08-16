#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$REPO_ROOT/hermes/skills/pidog-control"
SKILLS_ROOT="$HOME/.hermes/skills"
DST="$SKILLS_ROOT/pidog-control"

if [ ! -d "$SRC" ]; then
    echo "ERROR: source skill not found: $SRC"
    exit 1
fi

mkdir -p "$SKILLS_ROOT"

case "$DST" in
    "$SKILLS_ROOT"/*) ;;
    *)
        echo "ERROR: refusing unsafe destination: $DST"
        exit 1
        ;;
esac

rm -rf "$DST"
cp -a "$SRC" "$DST"

echo "Deployed:"
echo "  $SRC"
echo "->"
echo "  $DST"
