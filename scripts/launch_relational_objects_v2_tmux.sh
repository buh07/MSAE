#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv-atlas/bin/python"
SESSION="msae_relational_objects_v2_opened_development2_20260804"
LOG="$ROOT/pilot_runs/20260804_relational_objects_v2_opened_development2.log"
if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session already exists: $SESSION" >&2; exit 1; fi
if [[ -e "$ROOT/pilot_runs/scientific_source_openings/relational_objects_v2_opened_development2.DEVELOPMENT_OPENED.json" || -e "$ROOT/pilot_runs/20260804_relational_objects_v2_opened_development2" || -e "$ROOT/results/relational_objects_v2_opened_development2" ]]; then
  echo "one-shot namespace already consumed" >&2; exit 1
fi
mkdir -p "$(dirname "$LOG")"
: > "$LOG"
COMMAND="set -o pipefail; cd '$ROOT' && export CUDA_VISIBLE_DEVICES=0 CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONHASHSEED=20260804 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false && '$PY' scripts/run_relational_objects_v2.py run 2>&1 | tee -a '$LOG'"
tmux new-session -d -s "$SESSION" "$COMMAND"
for _ in $(seq 1 120); do
  if grep -q '^RUNNER_READY$' "$LOG" 2>/dev/null; then
    echo "RUNNER_READY session=$SESSION log=$LOG"
    exit 0
  fi
  if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "runner exited before readiness" >&2; tail -80 "$LOG" >&2; exit 1
  fi
  sleep 1
done
tmux send-keys -t "$SESSION" C-c || true
sleep 2
echo "runner handshake timed out and was interrupted" >&2
exit 1
