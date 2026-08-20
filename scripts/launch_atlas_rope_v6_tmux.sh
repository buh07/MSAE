#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION="${1:-atlas_rope_v6_attempt10_20260803}"
KEY="${ATLAS_SIGNING_KEY:?ATLAS_SIGNING_KEY must name the frozen Ed25519 key}"
TERMINAL="$ROOT/pilot_runs/20260803_atlas_rope_technical_v6/TERMINAL.json"
COMPLETE="$ROOT/results/atlas_rope_v6_attempt10_science/COMPLETE.json"
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "session already exists: $SESSION"; exit 0
fi
if [[ -f "$TERMINAL" || -f "$COMPLETE" ]]; then
  echo "signed terminal/completion already exists; not relaunching"; exit 0
fi
tmux new-session -d -s "$SESSION" -c "$ROOT" \
  "export ATLAS_SIGNING_KEY=$(printf '%q' "$KEY"); exec bash scripts/run_atlas_rope_v6_pipeline.sh >>pilot_runs/20260803_atlas_rope_technical_v6/logs/pipeline.log 2>&1"
if tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux display-message -p -t "$SESSION" '#{session_name} #{pane_pid} #{pane_current_command}'
elif [[ -f "$TERMINAL" ]]; then
  "$ROOT/.venv-atlas/bin/python" -c \
    'import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from atlas_rope_v6 import read_json,verify_envelope; p=verify_envelope(read_json(Path(sys.argv[2]))); assert p.get("no_retry_authorized") is True; print(p["status"])' \
    "$ROOT/scripts" "$TERMINAL"
  echo "one-shot session already produced a signed terminal; not relaunching"
elif [[ -f "$COMPLETE" ]]; then
  "$ROOT/.venv-atlas/bin/python" -c \
    'import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from atlas_rope_v6 import read_json,verify_envelope; p=verify_envelope(read_json(Path(sys.argv[2]))); assert p.get("status")=="COMPLETE"; print(p["status"])' \
    "$ROOT/scripts" "$COMPLETE"
  echo "one-shot session already produced a signed completion; not relaunching"
else
  echo "unexpected early tmux exit without signed terminal/completion" >&2
  exit 1
fi
