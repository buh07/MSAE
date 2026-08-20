#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv-atlas/bin/python"
CONFIG="$ROOT/configs/relational_attention_edges_v1/run.json"

readarray -t VALUES < <("$PYTHON" - "$CONFIG" <<'PY'
import json,sys
c=json.load(open(sys.argv[1]))
print(c['tmux_session'])
print(c['paths']['log'])
PY
)
SESSION="${VALUES[0]}"
LOG="$ROOT/${VALUES[1]}"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "tmux session already exists: $SESSION" >&2
  exit 72
fi
if [[ -e "$LOG" ]]; then
  echo "frozen log path already exists: $LOG" >&2
  exit 73
fi
mkdir -p "$(dirname "$LOG")"
COMMAND="cd $(printf '%q' "$ROOT") && bash $(printf '%q' "$ROOT/scripts/run_relational_attention_edges_v1_pipeline.sh") 2>&1 | tee $(printf '%q' "$LOG")"
tmux new-session -d -s "$SESSION" "bash -o pipefail -c $(printf '%q' "$COMMAND")"
tmux set-option -t "$SESSION" remain-on-exit on
printf 'launched session=%s log=%s\n' "$SESSION" "$LOG"
