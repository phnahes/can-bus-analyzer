#!/bin/bash
# Release helper wrapper (version bump + tag, or tag-only after PR merge).
#
# Usage:
#   ./extras/release.sh 1.2.4
#   ./extras/release.sh 1.2.4 --dry-run
#   ./extras/release.sh 1.2.3 --tag-only --force   # tag current HEAD (version must match __init__.py)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"
python3 "$SCRIPT_DIR/release.py" "$@"

