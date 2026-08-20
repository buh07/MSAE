#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY="${ATLAS_SIGNING_KEY:?ATLAS_SIGNING_KEY is required}"
LOG_ROOT="$ROOT/pilot_runs/20260803_atlas_rope_analysis_recovery_v8/logs"
mkdir -p "$LOG_ROOT"
stage="startup"
terminalize_failure() {
  local code=$?
  "$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v8.py" terminalize \
    --signing-key "$KEY" --terminal-status TERMINAL_PIPELINE_STAGE_FAILED \
    --reason "Attempt-12 pipeline stage ${stage} failed with exit ${code}" \
    >>"$LOG_ROOT/terminalize.log" 2>&1 || true
  exit "$code"
}
trap terminalize_failure ERR
if [[ "${CUDA_VISIBLE_DEVICES:-}" != "0" ]]; then
  echo "Attempt-12 requires CUDA_VISIBLE_DEVICES=0" >&2
  false
fi
stage="analysis_only_recovery"
"$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v8.py" analyze --signing-key "$KEY" \
  >>"$LOG_ROOT/analysis.log" 2>&1
stage="terminal_complete"
"$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v8.py" terminalize \
  --signing-key "$KEY" --terminal-status TERMINAL_COMPLETE \
  --reason "Attempt-12 one-shot exploratory analysis-only recovery completed" \
  >>"$LOG_ROOT/terminalize.log" 2>&1
trap - ERR
printf '%s\n' "Attempt-12 pipeline terminal complete" >>"$LOG_ROOT/pipeline.log"

