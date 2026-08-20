#!/usr/bin/env bash
set -euo pipefail
ROOT="${MSAE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SESSION="capacity_external_validity_v1_20260810r2"
CAP_OUT="$ROOT/results/capacity_controller_diagnostic_v1_20260810r2"
EXT_OUT="$ROOT/results/trained_copy_external_v1_20260810r2"
CAP_PROV="$ROOT/reports/provenance/capacity_controller_diagnostic_v1_r2_run_20260810r2"
EXT_PROV="$ROOT/reports/provenance/trained_copy_external_v1_r2_run_20260810r2"
SCRIPT="$ROOT/scripts/capacity_external_validity_v1_r2.py"
LOG="$ROOT/reports/provenance/capacity_external_validity_v1_r2_launcher_20260810r2.log"
render_cmd() {
 local chosen_index="$1" chosen_uuid="$2" lockdir="$3" token="$4"
 cat <<EOF
set -euo pipefail
trap 'rm -rf "$lockdir"' EXIT TERM INT HUP
[[ "\$(cat "$lockdir/token")" == "$token" ]]
export CUDA_VISIBLE_DEVICES="$chosen_index"
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONHASHSEED=0
cd "$ROOT"
RUN_ROOT=\$(readlink /proc/self/cwd)
read -r current_mem current_util < <(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits -i "$chosen_index" | tr -d ' ' | tr ',' ' ')
if (( current_mem > 1024 || current_util > 10 )); then echo 'selected GPU became busy; one-shot launch stopped';exit 73;fi
set +e
timeout --signal=TERM --kill-after=30s 8h env MSAE_ROOT="\$RUN_ROOT" python "\$RUN_ROOT/scripts/capacity_external_validity_v1_r2.py" run-pipeline --physical-index "$chosen_index" --gpu-uuid "$chosen_uuid" --launch-token "$token" 2>&1 | tee -a "$LOG"
rc=\${PIPESTATUS[0]}
set -e
exit \$rc
EOF
}
if [[ "${MSAE_LAUNCH_DRY_RUN:-0}" == 1 ]]; then
 render_cmd 0 GPU-DRY-RUN /tmp/msae-dry-run-lock TOKEN-DRY-RUN
 exit 0
fi
if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session exists: $SESSION" >&2; exit 1; fi
for p in "$CAP_OUT" "$EXT_OUT" "$CAP_PROV" "$EXT_PROV"; do [[ ! -e "$p" ]] || { echo "immutable namespace exists: $p" >&2; exit 1; }; done
[[ ! -e "$LOG" ]] || { echo "immutable launcher log exists: $LOG" >&2; exit 1; }
MSAE_ROOT="$ROOT" python "$SCRIPT" verify-review-binding >/dev/null
mapfile -t GPUS < <(nvidia-smi --query-gpu=index,uuid,memory.used,utilization.gpu --format=csv,noheader,nounits)
chosen_index="";chosen_uuid="";lockdir=""
for row in "${GPUS[@]}"; do
 IFS=',' read -r ai au am av <<<"$row";i="${ai// /}";u="${au// /}";mem="${am// /}";util="${av// /}"
 (( mem <= 1024 && util <= 10 )) || continue
 candidate="/tmp/msae_capacity_external_r2_${u}.lockdir"
 if mkdir "$candidate" 2>/dev/null; then chosen_index="$i";chosen_uuid="$u";lockdir="$candidate";break;fi
done
[[ -n "$chosen_index" ]] || { echo "no free lockable GPU" >&2;exit 1; }
token="$(python - <<'PY'
import secrets
print(secrets.token_hex(24))
PY
)"
printf '%s\n' "$token" > "$lockdir/token"
cmd="$(render_cmd "$chosen_index" "$chosen_uuid" "$lockdir" "$token")"
if ! tmux new-session -d -s "$SESSION" "$cmd";then rm -rf "$lockdir";exit 1;fi
sleep 2
if ! tmux has-session -t "$SESSION" 2>/dev/null;then echo 'tmux job exited during startup' >&2;tail -100 "$LOG" 2>/dev/null||true;exit 1;fi
printf 'SESSION=%s\nGPU_INDEX=%s\nGPU_UUID=%s\nLOG=%s\n' "$SESSION" "$chosen_index" "$chosen_uuid" "$LOG"
