#!/usr/bin/env bash
set -Eeuo pipefail
PACKAGE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"
OLD_RUNTIME=/mnt/brickmore-data/brickmore-jrd-20261025/use-runtime.sh
if [[ "${BRICKGPT_LOAD_OLD_RUNTIME:-1}" == 1 && -r "$OLD_RUNTIME" ]]; then
    set +u
    source "$OLD_RUNTIME"
    set -u
    cd "$PACKAGE_ROOT"
fi
PY="${BRICKGPT_PYTHON:-}"
if [[ -z "$PY" ]]; then
    if [[ -n "${BRICKMORE_ENV:-}" && -x "$BRICKMORE_ENV/bin/python" ]]; then
        PY="$BRICKMORE_ENV/bin/python"
    elif [[ -x /mnt/brickmore-data/brickmore-jrd-20261025/runtime/envs/paper/bin/python ]]; then
        PY=/mnt/brickmore-data/brickmore-jrd-20261025/runtime/envs/paper/bin/python
    else
        PY=python3
    fi
fi
export PYTHONUTF8=1 PYTHONUNBUFFERED=1
mkdir -p .runtime/tmp
export TMPDIR="$PWD/.runtime/tmp"
if [[ "${1:-}" == deps ]]; then
    "$PY" Scripts/batch.py verify
    exec "$PY" -m pip --disable-pip-version-check install --no-index --no-deps --target "$PWD/.runtime/deps" VendorsWheels/*.whl
fi
exec "$PY" Scripts/batch.py "$@"
