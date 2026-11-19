#!/usr/bin/env bash
set -Eeuo pipefail
BRICKMORE_BUNDLE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$BRICKMORE_BUNDLE_ROOT/Scripts/environment.sh"
if [[ "${1:-}" == fetch ]]; then shift; exec "$BRICKMORE_LAUNCHER" -X utf8 Scripts/fetch.py "$@"; fi
exec "$BRICKMORE_LAUNCHER" -X utf8 Scripts/run_comparison.py "$@"
