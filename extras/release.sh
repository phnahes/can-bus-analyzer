#!/bin/bash
# Release helper wrapper (version bump + tag).
#
# Usage:
#   ./extras/release.sh 1.1.1
#   ./extras/release.sh 1.1.1 --dry-run
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"
python3 "$SCRIPT_DIR/release.py" "$@"

