#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY="${ATLAS_SIGNING_KEY:?ATLAS_SIGNING_KEY must name the frozen Ed25519 key}"
LOG_ROOT="$ROOT/pilot_runs/20260803_atlas_rope_technical_v6/logs"
mkdir -p "$LOG_ROOT"
stage="startup"
terminalize() {
  local code=$?
  "$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v6.py" terminalize-failure --signing-key "$KEY" \
    --terminal-status "TERMINAL_PIPELINE_STAGE_FAILED" --reason "Attempt-10 pipeline stage ${stage} failed with exit ${code}" \
    >>"$LOG_ROOT/terminalize.log" 2>&1 || true
  exit "$code"
}
trap terminalize ERR
stage="GENTLE_validation"
"$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v6.py" run-gentle --signing-key "$KEY" >>"$LOG_ROOT/gentle.log" 2>&1
stage="science_authorization"
"$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v6.py" authorize-science --signing-key "$KEY" >>"$LOG_ROOT/science_authorization.log" 2>&1
stage="science_EWT_extraction"
"$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v6_science.py" extract-ewt --signing-key "$KEY" >>"$LOG_ROOT/science_ewt.log" 2>&1
stage="science_GUM_extraction"
"$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v6_science.py" extract-gum --signing-key "$KEY" >>"$LOG_ROOT/science_gum.log" 2>&1
stage="science_QA_bridge_and_analysis"
"$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v6_science.py" analyze --signing-key "$KEY" >>"$LOG_ROOT/science_analysis.log" 2>&1
stage="complete"
printf '%s\n' "Attempt-10 pipeline complete" >>"$LOG_ROOT/pipeline.log"
