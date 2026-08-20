#!/usr/bin/env bash
set -euo pipefail

phase=${1:-}
session=msae_atlas_completion_20260801
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
run_root=pilot_runs/20260801_atlas_completion_v1
mkdir -p "$run_root/logs" "$run_root/job_manifests"
owner="$run_root/tmux_owner.json"
config_sha=$(sha256sum configs/atlas_completion/analysis.json | awk '{print $1}')
if [[ "$phase" == pilot ]]; then
  freeze_sha=prescore-pilot-candidate
elif [[ -f configs/atlas_completion/freeze_record.json ]]; then
  freeze_sha=$(python -c 'import json; print(json.load(open("configs/atlas_completion/freeze_record.json"))["bundle_sha256"])')
else
  echo "completion freeze is absent" >&2
  exit 1
fi

# One intentional M2 transition is allowed: the prescore-pilot coordinator may
# be replaced by a newly freeze-bound coordinator only after every pilot window
# has exited and every GPU allocation lock has been released.  The prior owner
# marker is archived rather than overwritten.
if [[ "$phase" != pilot ]] && tmux has-session -t "$session" 2>/dev/null \
   && grep -q '"completion_bundle_sha256":"prescore-pilot-candidate"' "$owner" 2>/dev/null; then
  windows=$(tmux list-windows -t "$session" -F '#W')
  [[ "$windows" == coordinator ]] || { echo "pilot-to-freeze transition blocked by live windows" >&2; exit 1; }
  if find "$run_root/allocations" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    echo "pilot-to-freeze transition blocked by GPU allocation" >&2; exit 1
  fi
  archive="$run_root/tmux_owner.prescore_pilot.json"
  [[ ! -e "$archive" ]] || { echo "prescore owner archive already exists" >&2; exit 1; }
  tmux kill-session -t "$session"
  mv "$owner" "$archive"
fi

if tmux has-session -t "$session" 2>/dev/null; then
  [[ -f "$owner" ]] || { echo "existing session lacks owner marker" >&2; exit 1; }
  grep -q "\"config_sha256\":\"$config_sha\"" "$owner" || { echo "existing session ownership/config mismatch" >&2; exit 1; }
  grep -q "\"completion_bundle_sha256\":\"$freeze_sha\"" "$owner" || { echo "existing session ownership/freeze mismatch" >&2; exit 1; }
else
  printf '{"session":"%s","run_root":"%s","config_sha256":"%s","completion_bundle_sha256":"%s"}\n' "$session" "$run_root" "$config_sha" "$freeze_sha" > "$owner"
  tmux new-session -d -s "$session" -n coordinator "cd '$root'; exec bash"
fi

window_exists() { tmux list-windows -t "$session" -F '#W' | grep -Fxq "$1"; }
launch() {
  local name=$1; shift
  if window_exists "$name"; then
    echo "window already exists, not relaunched: $name"
    return
  fi
  local log="$run_root/logs/${name}.log"
  [[ ! -f "$run_root/job_manifests/${name}.terminal.json" ]] || { echo "terminal job manifest exists, not relaunched: $name"; return; }
  local quoted=""
  printf -v quoted '%q ' "$@"
  tmux new-window -d -t "$session" -n "$name" "cd '$root'; exec scripts/msa_completion_gpu_runner.sh '$run_root' '$name' '$log' $quoted"
}
launch_cpu() {
  local name=$1; shift
  if window_exists "$name"; then
    echo "window already exists, not relaunched: $name"
    return
  fi
  local log="$run_root/logs/${name}.log"
  [[ ! -f "$run_root/job_manifests/${name}.terminal.json" ]] || { echo "terminal job manifest exists, not relaunched: $name"; return; }
  local quoted=""
  printf -v quoted '%q ' "$@"
  tmux new-window -d -t "$session" -n "$name" "cd '$root'; exec scripts/msa_completion_cpu_runner.sh '$run_root' '$name' '$log' $quoted"
}

py=.venv-atlas/bin/python
require_complete_stage() {
  local stage=$1
  local state
  state=$("$py" - "$stage" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "scripts")
from msa_completion_common import terminal_state
print(terminal_state(Path(sys.argv[1])) or "absent")
PY
)
  [[ "$state" == complete ]] && return 0
  if [[ "$state" == stopped ]]; then
    echo "upstream frozen stop blocks phase $phase: $stage" >&2
    "$py" - "$run_root" "$stage" "$phase" "$config_sha" "$freeze_sha" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "scripts")
from msa_completion_common import atomic_write_json, not_launched_payload
run_root, stage, phase = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
stop = stage / "FROZEN_EQUIVOCAL_STOP.json"
skipped = {"raw": ["raw_refit", "k2_refit", "stability", "specificity", "merge", "verification", "render"],
           "k2": ["k2_refit", "stability", "specificity", "merge", "verification", "render"],
           "controls": ["stability", "specificity", "merge", "verification", "render"],
           "merge": ["merge", "verification", "render"],
           "verify": ["verification", "render"]}.get(phase, [phase])
payload=not_launched_payload(stop, skipped_stages=skipped,
                             config_sha256=sys.argv[4],
                             completion_bundle_sha256=sys.argv[5])
path=run_root/"NOT_LAUNCHED_UPSTREAM_STOP.json"
if not path.exists(): atomic_write_json(path,payload)
PY
  else
    echo "upstream stage is not terminal yet: $stage" >&2
  fi
  return 1
}
case "$phase" in
  pilot)
    launch pilot_v10 "$py" scripts/msa_completion_pilot.py --device cuda:0
    ;;
  baseline)
    launch baseline "$py" scripts/calibrate_msae_completion.py --device cuda:0
    ;;
  raw)
    require_complete_stage "$run_root/baseline" || exit 1
    launch raw_L3_point "$py" scripts/run_msae_refit_worker.py --kind raw --layer 3 --point --device cuda:0
    launch raw_L4_point "$py" scripts/run_msae_refit_worker.py --kind raw --layer 4 --point --device cuda:0
    for layer in 3 4; do
      for shard in 0 1 2; do
        start=$((shard * 167)); end=$(((shard + 1) * 167)); [[ $end -le 500 ]] || end=500
        launch "raw_L${layer}_${start}_${end}" "$py" scripts/run_msae_refit_worker.py --kind raw --layer "$layer" --draw-start "$start" --draw-end "$end" --device cuda:0
      done
    done
    ;;
  k2)
    require_complete_stage "$run_root/raw_refit/L3" || exit 1
    require_complete_stage "$run_root/raw_refit/L4" || exit 1
    jobs=(k2_wave2_fast_g4_L3_s42_inc1e2 k2_wave2_fast_g5_L3_s43_inc1e2 k2_wave2_fast_g6_L3_s44_inc1e2 k2_wave2_fast_g7_L3_s42_inc0)
    for job in "${jobs[@]}"; do
      short=$(sed -E 's/^k2_wave2_fast_(g[0-9]+).*/\1/' <<<"$job")
      launch "${short}_point" "$py" scripts/run_msae_refit_worker.py --kind k2 --job "$job" --point --device cuda:0
      launch "${short}_draws" "$py" scripts/run_msae_refit_worker.py --kind k2 --job "$job" --draw-start 0 --draw-end 500 --device cuda:0
    done
    ;;
  controls)
    jobs=(k2_wave2_fast_g4_L3_s42_inc1e2 k2_wave2_fast_g5_L3_s43_inc1e2 k2_wave2_fast_g6_L3_s44_inc1e2 k2_wave2_fast_g7_L3_s42_inc0)
    for job in "${jobs[@]}"; do require_complete_stage "$run_root/k2_refit/$job" || exit 1; done
    launch stability_point "$py" scripts/run_msae_stability.py --point --device cuda:0
    for shard in 0 1 2; do
      start=$((shard * 167)); end=$(((shard + 1) * 167)); [[ $end -le 500 ]] || end=500
      launch "stability_${start}_${end}" "$py" scripts/run_msae_stability.py --draw-start "$start" --draw-end "$end" --device cuda:0
    done
    for job in "${jobs[@]}"; do
      short=$(sed -E 's/^k2_wave2_fast_(g[0-9]+).*/\1/' <<<"$job")
      launch "specificity_${short}" "$py" scripts/run_msae_specificity.py --job "$job" --device cuda:0
    done
    ;;
  merge)
    require_complete_stage "$run_root/stability" || exit 1
    jobs=(k2_wave2_fast_g4_L3_s42_inc1e2 k2_wave2_fast_g5_L3_s43_inc1e2 k2_wave2_fast_g6_L3_s44_inc1e2 k2_wave2_fast_g7_L3_s42_inc0)
    for job in "${jobs[@]}"; do require_complete_stage "$run_root/specificity/$job" || exit 1; done
    launch_cpu merge "$py" scripts/merge_msae_refit.py
    ;;
  verify)
    require_complete_stage "results/atlas/completion_v1" || exit 1
    launch_cpu verify "$py" scripts/verify_msae_completion.py
    ;;
  render)
    require_complete_stage "results/atlas/completion_v1" || exit 1
    require_complete_stage "$run_root/verification" || exit 1
    launch_cpu render "$py" scripts/render_msae_completion_decision.py
    ;;
  *)
    echo "usage: $0 {pilot|baseline|raw|k2|controls|merge|verify|render}" >&2
    exit 2
    ;;
esac

tmux list-windows -t "$session" -F '#I #W #{pane_current_command}'
