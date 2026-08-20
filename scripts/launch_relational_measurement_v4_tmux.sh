#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION="relational_measurement_v4"
LOG="$ROOT/reports/provenance/relational_measurement_v4_tmux.log"
if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session exists: $SESSION" >&2; exit 2; fi
set -o noclobber
: > "$LOG"
set +o noclobber
tmux new-session -d -s "$SESSION" "set -o pipefail; cd '$ROOT' && bash scripts/run_relational_measurement_v4_pipeline.sh 2>&1 | tee -a '$LOG'"
echo "$SESSION"
