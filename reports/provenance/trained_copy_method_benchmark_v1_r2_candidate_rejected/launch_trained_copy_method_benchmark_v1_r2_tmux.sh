#!/usr/bin/env bash
set -euo pipefail
ROOT="${MSAE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SESSION="trained_copy_method_benchmark_v1_r2_20260810"
LOG="$ROOT/reports/provenance/trained_copy_method_benchmark_v1_r2_launcher_20260810.log"
PY="$ROOT/scripts/trained_copy_method_benchmark_v1_r2.py"
[[ ! -e "$LOG" ]] || { echo "launcher log exists" >&2; exit 1; }
! tmux has-session -t "$SESSION" 2>/dev/null || { echo "tmux session exists" >&2; exit 1; }
if compgen -G '/tmp/msae_trained_copy_methods_v1_r2_*.lockdir' >/dev/null; then echo "stale benchmark GPU lock" >&2; exit 1; fi
mapfile -t GPUS < <(nvidia-smi --query-gpu=index,uuid,memory.used,utilization.gpu --format=csv,noheader,nounits)
INDEX="";UUID="";LOCK="";TOKEN=""
for row in "${GPUS[@]}"; do
  IFS=',' read -r i u mem util <<<"$row";i="${i// /}";u="${u// /}";mem="${mem// /}";util="${util// /}"
  (( mem <= 1024 && util <= 10 )) || continue
  candidate="/tmp/msae_trained_copy_methods_v1_r2_${u}.lockdir"
  if mkdir "$candidate" 2>/dev/null; then INDEX="$i";UUID="$u";LOCK="$candidate";TOKEN="$(python - <<'PY'
import secrets
print(secrets.token_hex(24))
PY
)";printf '%s\n' "$TOKEN" >"$LOCK/token";break;fi
done
[[ -n "$UUID" ]] || { echo "no free GPU" >&2; exit 1; }
cleanup(){ rm -rf "$LOCK"; }
trap cleanup ERR INT TERM
python "$PY" launch-preflight --physical-index "$INDEX" --gpu-uuid "$UUID"
CMD="set -euo pipefail
trap 'rm -rf \"$LOCK\"' EXIT TERM INT HUP
[[ \"\$(cat \"$LOCK/token\")\" == \"$TOKEN\" ]]
export CUDA_VISIBLE_DEVICES=\"$UUID\"
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONHASHSEED=0
cd \"$ROOT\"
RUN_ROOT=\$(readlink /proc/self/cwd)
read -r current_mem current_util < <(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits -i \"$INDEX\" | tr -d ' ' | tr ',' ' ')
if (( current_mem > 1024 || current_util > 10 )); then echo 'selected GPU became busy; one-shot launch stopped';exit 73;fi
set +e
timeout --signal=TERM --kill-after=30s 8h env MSAE_ROOT=\"\$RUN_ROOT\" python \"\$RUN_ROOT/scripts/trained_copy_method_benchmark_v1_r2.py\" run-pipeline --physical-index \"$INDEX\" --gpu-uuid \"$UUID\" --pane-pid \"\$\$\" --gpu-lockdir \"$LOCK\" --launch-token \"$TOKEN\" 2>&1 | tee -a \"$LOG\"
rc=\${PIPESTATUS[0]}
set -e
exit \$rc"
tmux new-session -d -s "$SESSION" "$CMD"
PANE_PID="$(tmux display-message -p -t "$SESSION:0.0" '#{pane_pid}')"
trap - ERR INT TERM
printf 'SESSION=%s\nPANE_PID=%s\nGPU_INDEX=%s\nGPU_UUID=%s\nLOG=%s\n' "$SESSION" "$PANE_PID" "$INDEX" "$UUID" "$LOG"
