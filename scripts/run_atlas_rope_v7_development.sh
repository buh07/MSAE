#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY="${ATLAS_SIGNING_KEY:?ATLAS_SIGNING_KEY is required}"
GPU_UUID="${ATLAS_GPU_UUID:?ATLAS_GPU_UUID is required}"
LOG="$ROOT/pilot_runs/20260803_atlas_rope_technical_v7/logs/development.log"
mkdir -p "$(dirname "$LOG")"
exec "$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v7.py" run-development \
  --signing-key "$KEY" --gpu-uuid "$GPU_UUID" >>"$LOG" 2>&1
