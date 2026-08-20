#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$ROOT/configs/atlas_context_local_v10/run.json"
PYTHON="$ROOT/.venv-atlas/bin/python"
SIGNING_KEY="${ATLAS_ATTEMPT14_SIGNING_KEY:?ATLAS_ATTEMPT14_SIGNING_KEY must name the external key}"
GPU_UUID="$($PYTHON - "$CONFIG" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))['runtime']['gpu_uuid'])
PY
)"
export CUDA_VISIBLE_DEVICES="$GPU_UUID"
export CUBLAS_WORKSPACE_CONFIG=":4096:8"
export PYTHONHASHSEED=20260804
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export PYTHONPATH="$ROOT/scripts"
exec "$PYTHON" "$ROOT/scripts/run_atlas_context_local_v10.py" run --signing-key "$SIGNING_KEY"
