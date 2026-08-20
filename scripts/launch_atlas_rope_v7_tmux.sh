#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION="${1:-atlas_rope_v7_attempt11_20260803}"
GPU_INDEX="${2:?physical GPU index required}"
KEY="${ATLAS_SIGNING_KEY:?ATLAS_SIGNING_KEY is required}"
TERMINAL="$ROOT/pilot_runs/20260803_atlas_rope_technical_v7/TERMINAL.json"
COMPLETE="$ROOT/results/atlas_rope_v7_attempt11_science/COMPLETE.json"
LAUNCH_RECORD="$ROOT/pilot_runs/20260803_atlas_rope_technical_v7/provenance/tmux_launch.txt"
GPU_UUID="$(nvidia-smi -i "$GPU_INDEX" --query-gpu=uuid --format=csv,noheader | tr -d '[:space:]')"
if tmux has-session -t "$SESSION" 2>/dev/null; then echo "session already exists: $SESSION"; exit 0; fi
if [[ -f "$TERMINAL" || -f "$COMPLETE" ]]; then echo "terminal/completion already exists; refusing relaunch"; exit 0; fi
tmux new-session -d -s "$SESSION" -c "$ROOT" \
  "export CUDA_VISIBLE_DEVICES=$(printf '%q' "$GPU_INDEX"); export ATLAS_SIGNING_KEY=$(printf '%q' "$KEY"); exec bash scripts/run_atlas_rope_v7_pipeline.sh >>pilot_runs/20260803_atlas_rope_technical_v7/logs/pipeline.log 2>&1"
observed="$(tmux display-message -p -t "$SESSION" '#{session_name} #{pane_pid} #{pane_current_command}')"
mkdir -p "$(dirname "$LAUNCH_RECORD")"
{
  printf 'launched_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'gpu_index=%s\n' "$GPU_INDEX"
  printf 'gpu_uuid=%s\n' "$GPU_UUID"
  printf 'tmux=%s\n' "$observed"
} >"$LAUNCH_RECORD"
printf '%s\n' "$observed"
