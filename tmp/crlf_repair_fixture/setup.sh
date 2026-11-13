#!/usr/bin/env bash
set -Eeuo pipefail
BRICKMORE_BUNDLE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$BRICKMORE_BUNDLE_ROOT/Scripts/environment.sh"
mkdir -p .runtime Downloads/wheels Downloads/models
if "$BRICKMORE_LAUNCHER" -X utf8 Scripts/doctor.py; then exit 0; fi
if "$BRICKMORE_LAUNCHER" -c 'import json,sys; r=json.load(open(".runtime/environment.json"))["roles"]; sys.exit(0 if not r["structure"] or not r["render"] else 1)'; then
  if [[ "${1:---offline}" == --online ]]; then "$BRICKMORE_LAUNCHER" Scripts/fetch.py wheels; fi
  if ! compgen -G 'Downloads/wheels/*.whl' >/dev/null; then
    echo 'CPU dependencies missing. On the connected transfer host run: python Scripts/fetch.py wheels'
    echo 'Copy Downloads/wheels back into this folder and rerun: bash setup.sh --offline'; exit 2
  fi
  "$BRICKMORE_LAUNCHER" -X utf8 Scripts/verify_downloads.py Downloads/wheels
  BRICKMORE_CPU_BASE="$(command -v python3.12 || true)"
  if [[ -z "$BRICKMORE_CPU_BASE" ]]; then BRICKMORE_CPU_BASE="$BRICKMORE_LAUNCHER"; fi
  "$BRICKMORE_CPU_BASE" -c 'import sys; assert sys.version_info[:2]==(3,12), "Offline CPU wheels require Python 3.12"'
  if [[ ! -x .runtime/cpu/bin/python ]]; then "$BRICKMORE_CPU_BASE" -m venv .runtime/cpu; fi
  .runtime/cpu/bin/python -m pip install --no-index --find-links Downloads/wheels -r requirements-cpu.txt
  export CPU_PYTHON="$BRICKMORE_BUNDLE_ROOT/.runtime/cpu/bin/python"
fi
if [[ "${1:---offline}" == --online ]]; then
  BRICKMORE_MISSING_MODELS="$("$BRICKMORE_LAUNCHER" -c 'import json; d=json.load(open(".runtime/environment.json")); print(" ".join(m for m in ["vqa","pe","siglip2"] if d.get("roles",{}).get("gpu") and not d.get("models",{}).get(m,{}).get("ok")))')"
  if [[ -n "$BRICKMORE_MISSING_MODELS" ]]; then "$BRICKMORE_LAUNCHER" Scripts/fetch.py models --metrics $BRICKMORE_MISSING_MODELS; fi
fi
"$BRICKMORE_LAUNCHER" -X utf8 Scripts/doctor.py
