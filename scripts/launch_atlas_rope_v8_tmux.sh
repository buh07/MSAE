#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY="${ATLAS_SIGNING_KEY:?ATLAS_SIGNING_KEY must name the frozen Ed25519 key}"
SESSION="atlas_rope_v8_attempt12_20260803"
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "tmux session already exists: $SESSION" >&2
  exit 1
fi
GPU0_UUID="$(nvidia-smi --query-gpu=index,uuid --format=csv,noheader | awk -F, '$1 ~ /^[[:space:]]*0[[:space:]]*$/ {gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2}')"
if [[ "$GPU0_UUID" != "GPU-ec526219-fb07-e57e-a30d-5d2ab843fb15" ]]; then
  echo "physical GPU-0 UUID mismatch: $GPU0_UUID" >&2
  exit 1
fi
tmux new-session -d -s "$SESSION" -c "$ROOT" \
  "export CUDA_VISIBLE_DEVICES=0; export ATLAS_SIGNING_KEY=$(printf '%q' "$KEY"); exec bash scripts/run_atlas_rope_v8_pipeline.sh"
printf '%s\n' "$SESSION"
