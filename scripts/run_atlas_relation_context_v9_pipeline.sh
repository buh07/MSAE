#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$ROOT/configs/atlas_relation_context_v9/run.json"
PYTHON="$ROOT/.venv-atlas/bin/python"
SIGNING_KEY="${ATLAS_ATTEMPT13_SIGNING_KEY:?ATLAS_ATTEMPT13_SIGNING_KEY must name the external Ed25519 key}"

readarray -t VALUES < <("$PYTHON" - "$CONFIG" <<'PY'
import json,sys
c=json.load(open(sys.argv[1]))
print(c['runtime']['physical_gpu_index'])
print(c['run_root'])
PY
)
GPU_INDEX="${VALUES[0]}"
RUN_ROOT="$ROOT/${VALUES[1]}"
export CUDA_VISIBLE_DEVICES="$GPU_INDEX"
export CUBLAS_WORKSPACE_CONFIG=":4096:8"
export PYTHONHASHSEED=20260803
export TOKENIZERS_PARALLELISM=false

exec "$PYTHON" "$ROOT/scripts/run_atlas_relation_context_v9.py" \
  --config "configs/atlas_relation_context_v9/run.json" \
  --signing-key "$SIGNING_KEY"
