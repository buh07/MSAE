#!/usr/bin/env bash
set -euo pipefail
phase=${1:-all}
session=msae_atlas_completion_diag_20260802
root=$(cd "$(dirname "$0")/.." && pwd); cd "$root"
run_root=pilot_runs/20260802_atlas_completion_diagnostic_continuation_v1
py=.venv-atlas/bin/python
config=configs/atlas_completion_continuation/analysis.json
freeze=configs/atlas_completion_continuation/freeze_record.json
config_sha=$(sha256sum "$config" | awk '{print $1}')
freeze_sha=$($py -c 'import json; print(json.load(open("configs/atlas_completion_continuation/freeze_record.json"))["bundle_sha256"])')
verify_freeze() {
  "$py" - <<'PY'
import sys
sys.path.insert(0,"scripts")
from msa_completion_continuation_common import verify_continuation_freeze
print(verify_continuation_freeze()["bundle_sha256"])
PY
}
window_exists() { tmux list-windows -t "$session" -F '#W' 2>/dev/null | grep -Fxq "$1"; }
launch_cpu() {
  local name=$1; shift
  [[ ! -e "$run_root/job_manifests/${name}.terminal.json" ]] || return 0
  window_exists "$name" && return 0
  local log="$run_root/logs/${name}.log" quoted=""; printf -v quoted '%q ' "$@"
  tmux new-window -d -t "$session" -n "$name" "cd '$root'; exec scripts/msa_completion_continuation_cpu_runner.sh '$run_root' '$name' '$log' $quoted"
}
launch_gpu() {
  local name=$1; shift
  [[ ! -e "$run_root/job_manifests/${name}.terminal.json" ]] || return 0
  window_exists "$name" && return 0
  local log="$run_root/logs/${name}.log" quoted=""; printf -v quoted '%q ' "$@"
  tmux new-window -d -t "$session" -n "$name" "cd '$root'; exec scripts/msa_completion_continuation_gpu_runner.sh '$run_root' '$name' '$log' $quoted"
}
case "$phase" in
  all)
    verify_freeze >/dev/null
    tmux has-session -t "$session" 2>/dev/null && { echo "tmux session already exists" >&2; exit 2; }
    [[ ! -e "$run_root" ]] || { echo "continuation run root already exists" >&2; exit 2; }
    avail_kb=$(df -Pk . | awk 'NR==2 {print $4}'); mem_kb=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)
    (( avail_kb >= 50*1024*1024 && mem_kb >= 128*1024*1024 )) || { echo "disk/RAM precheck failed" >&2; exit 75; }
    mkdir -p "$run_root/logs" "$run_root/job_manifests"
    printf '{"session":"%s","run_root":"%s","config_sha256":"%s","completion_bundle_sha256":"%s"}\n' \
      "$session" "$run_root" "$config_sha" "$freeze_sha" > "$run_root/tmux_owner.json"
    tmux new-session -d -s "$session" -n coordinator "cd '$root'; exec bash"
    tmux new-window -d -t "$session" -n orchestrator "cd '$root'; exec scripts/launch_msae_completion_continuation_tmux.sh orchestrate"
    ;;
  orchestrate)
    verify_freeze >/dev/null
    launch_cpu baseline_rebind "$py" scripts/bind_msae_completion_continuation_baseline.py
    while [[ ! -e "$run_root/job_manifests/baseline_rebind.terminal.json" ]]; do sleep 10; done
    baseline_ok=$($py - <<'PY'
import json,sys
from pathlib import Path
sys.path.insert(0,"scripts")
from msa_completion_common import terminal_state
r=Path("pilot_runs/20260802_atlas_completion_diagnostic_continuation_v1")
j=json.load(open(r/"job_manifests/baseline_rebind.terminal.json"))
print("yes" if j["exit_code"]==0 and terminal_state(r/"baseline")=="complete" else "no")
PY
)
    if [[ "$baseline_ok" != yes ]]; then
      cause="$run_root/baseline/FROZEN_EQUIVOCAL_STOP.json"
      [[ -f "$cause" ]] || cause="$run_root/job_manifests/baseline_rebind.terminal.json"
      launch_cpu collector "$py" scripts/collect_msae_completion_continuation.py --baseline-failed "$cause"
      exit 1
    fi
    # Collector is durable and starts before any GPU process.
    launch_cpu collector "$py" scripts/collect_msae_completion_continuation.py
    jobs=(k2_wave2_fast_g4_L3_s42_inc1e2 k2_wave2_fast_g5_L3_s43_inc1e2 k2_wave2_fast_g6_L3_s44_inc1e2 k2_wave2_fast_g7_L3_s42_inc0)
    for job in "${jobs[@]}"; do
      short=$(sed -E 's/^k2_wave2_fast_(g[0-9]+).*/\1/' <<<"$job")
      launch_gpu "${short}_point" "$py" scripts/run_msae_completion_continuation.py k2 --job "$job" --point --device cuda:0
      launch_gpu "${short}_draws" "$py" scripts/run_msae_completion_continuation.py k2 --job "$job" --draw-start 0 --draw-end 500 --device cuda:0
    done
    launch_gpu stability_point "$py" scripts/run_msae_completion_continuation.py stability --point --device cuda:0
    for range in 0:167 167:334 334:500; do
      start=${range%:*}; end=${range#*:}
      launch_gpu "stability_${start}_${end}" "$py" scripts/run_msae_completion_continuation.py stability --draw-start "$start" --draw-end "$end" --device cuda:0
    done
    for job in "${jobs[@]}"; do
      short=$(sed -E 's/^k2_wave2_fast_(g[0-9]+).*/\1/' <<<"$job")
      launch_gpu "specificity_${short}" "$py" scripts/run_msae_completion_continuation.py specificity --job "$job" --device cuda:0
    done
    ;;
  summarize)
    [[ -e "$run_root/job_manifests/collector.terminal.json" ]] || { echo "collector is not terminal" >&2; exit 2; }
    launch_cpu summarize "$py" scripts/summarize_msae_completion_continuation.py
    ;;
  status)
    tmux list-windows -t "$session" -F '#I #W #{pane_current_command}' || true
    find "$run_root/job_manifests" -maxdepth 1 -name '*.terminal.json' -printf '%f\n' 2>/dev/null | sort
    ;;
  *) echo "usage: $0 {all|orchestrate|summarize|status}" >&2; exit 2;;
esac
[[ "$phase" == status ]] || tmux list-windows -t "$session" -F '#I #W #{pane_current_command}'
