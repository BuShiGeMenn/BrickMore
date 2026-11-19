#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ "${1:-}" == --offline ]]; then shift; fi
bash run.sh doctor "$@"
