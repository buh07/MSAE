#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY="${ATLAS_SIGNING_KEY:?ATLAS_SIGNING_KEY is required}"
LOG_ROOT="$ROOT/pilot_runs/20260803_atlas_rope_technical_v7/logs"
mkdir -p "$LOG_ROOT"
stage="startup"
terminalize() {
  local code=$?
  "$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v7.py" terminalize --signing-key "$KEY" \
    --terminal-status TERMINAL_PIPELINE_STAGE_FAILED --reason "Attempt-11 pipeline stage ${stage} failed with exit ${code}" \
    >>"$LOG_ROOT/terminalize.log" 2>&1 || true
  exit "$code"
}
trap terminalize ERR
stage="validation_ENGLISH_CHILDES_CTETEX"
"$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v7.py" run-panel --panel ENGLISH_CHILDES_CTETEX --signing-key "$KEY" >>"$LOG_ROOT/validation_english.log" 2>&1
stage="validation_CZECH_PDT"
"$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v7.py" run-panel --panel CZECH_PDT --signing-key "$KEY" >>"$LOG_ROOT/validation_czech.log" 2>&1
stage="science_authorization"
"$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v7.py" authorize-science --signing-key "$KEY" >>"$LOG_ROOT/science_authorization.log" 2>&1
stage="science_EWT"
"$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v7_science.py" extract-ewt --signing-key "$KEY" >>"$LOG_ROOT/science_ewt.log" 2>&1
stage="science_GUM"
"$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v7_science.py" extract-gum --signing-key "$KEY" >>"$LOG_ROOT/science_gum.log" 2>&1
stage="science_analysis_and_overlay"
"$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/run_atlas_rope_v7_science.py" analyze --signing-key "$KEY" >>"$LOG_ROOT/science_analysis.log" 2>&1
stage="complete"
printf '%s\n' "Attempt-11 pipeline complete" >>"$LOG_ROOT/pipeline.log"
