#!/usr/bin/env bash
export PYTHONUTF8=1 PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 TBB_NUM_THREADS=1
export PYTHONFAULTHANDLER=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
if [[ -f "$BRICKMORE_BUNDLE_ROOT/environment.local.sh" ]]; then
  source "$BRICKMORE_BUNDLE_ROOT/environment.local.sh"
elif [[ "${BRICKMORE_LOAD_OLD_RUNTIME:-1}" == 1 && -f /mnt/brickmore-data/brickmore-jrd-20261025/use-runtime.sh ]]; then
  set +u
  source /mnt/brickmore-data/brickmore-jrd-20261025/use-runtime.sh
  set -u
fi
cd "$BRICKMORE_BUNDLE_ROOT"
if [[ -n "${GPU_PYTHON:-}" ]]; then BRICKMORE_LAUNCHER="$GPU_PYTHON"
elif [[ -n "${BRICKMORE_ENV:-}" && -x "$BRICKMORE_ENV/bin/python" ]]; then BRICKMORE_LAUNCHER="$BRICKMORE_ENV/bin/python"
else BRICKMORE_LAUNCHER="$(command -v python3 || command -v python)"; fi
export BRICKMORE_LAUNCHER
