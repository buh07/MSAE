#!/usr/bin/env bash
set -euo pipefail
ROOT="${MSAE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SAE_SESSION="trained_copy_sae_capacity_v1_r1_20260813"
BRIDGE_SESSION="causal_manifold_bridge_v1_r1_20260813"
SAE_LOG="$ROOT/reports/provenance/trained_copy_sae_capacity_v1_r1_launcher_20260813.log"
BRIDGE_LOG="$ROOT/reports/provenance/causal_manifold_bridge_v1_r1_launcher_20260813.log"
HANDSHAKE_ITERATIONS="${MSAE_HANDSHAKE_ITERATIONS:-240}"
HANDSHAKE_SLEEP="${MSAE_HANDSHAKE_SLEEP:-0.5}"
[[ ! -e "$SAE_LOG" && ! -e "$BRIDGE_LOG" ]] || { echo "launcher log exists" >&2; exit 1; }
! tmux has-session -t "$SAE_SESSION" 2>/dev/null || { echo "SAE session exists" >&2; exit 1; }
! tmux has-session -t "$BRIDGE_SESSION" 2>/dev/null || { echo "bridge session exists" >&2; exit 1; }
mkdir -p "$ROOT/reports/provenance"

declare -a IDX UUID LOCK TOKEN
cleanup_pre_handoff(){ for d in "${LOCK[@]:-}"; do [[ -z "$d" ]] || rm -rf "$d"; done; }
cleanup_all_workers(){
  tmux kill-session -t "$SAE_SESSION" 2>/dev/null || true
  tmux kill-session -t "$BRIDGE_SESSION" 2>/dev/null || true
  for d in "${LOCK[@]:-}"; do [[ -z "$d" ]] || rm -rf "$d"; done
}
fail_all(){ local msg="$1" rc="${2:-1}"; echo "$msg" >&2; cleanup_all_workers; trap - ERR INT TERM; exit "$rc"; }
trap cleanup_pre_handoff ERR INT TERM
reserve_lock(){
  local d="$1" u="$2" owner pid tomb
  if mkdir "$d" 2>/dev/null; then return 0; fi
  [[ -f "$d/owner" ]] || return 1
  owner="$(cat "$d/owner")";pid="${owner#*:}"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null && return 1
  nvidia-smi --query-compute-apps=gpu_uuid --format=csv,noheader 2>/dev/null | grep -qx "$u" && return 1
  tomb="${d}.stale.$$";mv "$d" "$tomb" 2>/dev/null || return 1;rm -rf "$tomb";mkdir "$d"
}
mapfile -t GPUS < <(nvidia-smi --query-gpu=index,uuid,memory.used,utilization.gpu --format=csv,noheader,nounits)
for row in "${GPUS[@]}"; do
  IFS=',' read -r i u mem util <<<"$row";i="${i// /}";u="${u// /}";mem="${mem// /}";util="${util// /}"
  (( mem <= 1024 && util <= 10 )) || continue
  # Refuse GPUs with any active compute PID even if utilization has not sampled it yet.
  if nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader 2>/dev/null | grep -q "^${u},"; then continue; fi
  d="/tmp/msae_gpu_${u}.lockdir"
  if reserve_lock "$d" "$u"; then
    tok="$(python - <<'PY'
import secrets
print(secrets.token_hex(24))
PY
)";printf '%s\n' "$tok" >"$d/token";printf 'coordinator:%s\n' "$$" >"$d/owner"
    IDX+=("$i");UUID+=("$u");LOCK+=("$d");TOKEN+=("$tok")
    ((${#IDX[@]}==2)) && break
  fi
done
((${#IDX[@]}==2)) || fail_all "two free GPUs unavailable"

launch_one(){
  local session="$1" script="$2" log="$3" hours="$4" i="$5" u="$6" d="$7" tok="$8"
  local cmd
  cmd="set -euo pipefail
trap 'if [[ -f \"$d/worker_token\" && \"\$(cat \"$d/worker_token\")\" == \"$tok\" ]]; then rm -rf \"$d\"; fi' EXIT TERM INT HUP
for n in \$(seq 1 200); do [[ -f \"$d/HANDOFF\" ]] && break; sleep 0.05; done
[[ -f \"$d/HANDOFF\" && \"\$(cat \"$d/token\")\" == \"$tok\" ]]
printf '%s\n' '$tok' >\"$d/worker_token\"
export CUDA_VISIBLE_DEVICES='$u' CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONHASHSEED=0
cd '$ROOT'
read -r m q < <(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits -i '$i' | tr -d ' ' | tr ',' ' ')
(( m <= 1024 && q <= 10 )) || exit 73
	timeout --signal=TERM --kill-after=30s '${hours}h' python '$ROOT/scripts/$script' run --physical-index '$i' --gpu-uuid '$u' --pane-pid \"\$\$\" --gpu-lockdir '$d' --launch-token '$tok' 2>&1 | tee -a '$log'"
  tmux new-session -d -s "$session" "$cmd"
}

launch_one "$SAE_SESSION" trained_copy_sae_capacity_v1_r1.py "$SAE_LOG" 24 "${IDX[0]}" "${UUID[0]}" "${LOCK[0]}" "${TOKEN[0]}"
SAE_PID="$(tmux display-message -p -t "$SAE_SESSION:0.0" '#{pane_pid}')"
if ! launch_one "$BRIDGE_SESSION" causal_manifold_bridge_v1_r1.py "$BRIDGE_LOG" 36 "${IDX[1]}" "${UUID[1]}" "${LOCK[1]}" "${TOKEN[1]}"; then
  fail_all "bridge partial launch failed"
fi
BRIDGE_PID="$(tmux display-message -p -t "$BRIDGE_SESSION:0.0" '#{pane_pid}')"
write_manifest(){
 python - "$1" "$2" "$3" "$4" "$5" "$6" <<'PY'
import hashlib,json,os,sys
path,session,index,uuid,pane,token=sys.argv[1:]
data={"session":session,"physical_index":int(index),"gpu_uuid":uuid,"pane_pid":int(pane),"token_sha256":hashlib.sha256(token.encode()).hexdigest()}
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444)
with os.fdopen(fd,'w') as f:json.dump(data,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
PY
}
write_manifest "$ROOT/reports/provenance/trained_copy_sae_capacity_v1_r1_LAUNCH.json" "$SAE_SESSION" "${IDX[0]}" "${UUID[0]}" "$SAE_PID" "${TOKEN[0]}"
write_manifest "$ROOT/reports/provenance/causal_manifold_bridge_v1_r1_LAUNCH.json" "$BRIDGE_SESSION" "${IDX[1]}" "${UUID[1]}" "$BRIDGE_PID" "${TOKEN[1]}"
printf 'worker:%s\n' "$SAE_PID" >"${LOCK[0]}/owner";printf '%s\n' "$SAE_PID" >"${LOCK[0]}/pane_pid";printf 'GPU_LOCK_OWNERSHIP_TRANSFERRED\n' >"${LOCK[0]}/HANDOFF"
printf 'worker:%s\n' "$BRIDGE_PID" >"${LOCK[1]}/owner";printf '%s\n' "$BRIDGE_PID" >"${LOCK[1]}/pane_pid";printf 'GPU_LOCK_OWNERSHIP_TRANSFERRED\n' >"${LOCK[1]}/HANDOFF"
trap 'cleanup_all_workers' ERR INT TERM
for n in $(seq 1 "$HANDSHAKE_ITERATIONS"); do
  [[ -f "$ROOT/reports/provenance/trained_copy_sae_capacity_v1_r1_run_20260813/events/010_FIT_ACCESS_MAY_HAVE_OCCURRED.json" && -f "$ROOT/reports/provenance/causal_manifold_bridge_v1_r1_run_20260813/events/010_FIT_ACCESS_MAY_HAVE_OCCURRED.json" ]] && break
  tmux has-session -t "$SAE_SESSION" && tmux has-session -t "$BRIDGE_SESSION" || fail_all 'worker exited before first access'
  sleep "$HANDSHAKE_SLEEP"
done
[[ -f "$ROOT/reports/provenance/trained_copy_sae_capacity_v1_r1_run_20260813/events/010_FIT_ACCESS_MAY_HAVE_OCCURRED.json" && -f "$ROOT/reports/provenance/causal_manifold_bridge_v1_r1_run_20260813/events/010_FIT_ACCESS_MAY_HAVE_OCCURRED.json" ]] || fail_all 'startup handshake timeout'
tmux has-session -t "$SAE_SESSION";tmux has-session -t "$BRIDGE_SESSION"
kill -0 "$SAE_PID";kill -0 "$BRIDGE_PID"
[[ "$(cat "${LOCK[0]}/owner")" == "worker:$SAE_PID" && "$(cat "${LOCK[1]}/owner")" == "worker:$BRIDGE_PID" ]]
SAE_WORKER="$(python -c 'import json,sys;print(json.load(open(sys.argv[1]))["pid"])' "$ROOT/reports/provenance/trained_copy_sae_capacity_v1_r1_run_20260813/events/000_RUN_START_NO_PANEL_ACCESS.json")"
BRIDGE_WORKER="$(python -c 'import json,sys;print(json.load(open(sys.argv[1]))["pid"])' "$ROOT/reports/provenance/causal_manifold_bridge_v1_r1_run_20260813/events/000_RUN_START_NO_PANEL_ACCESS.json")"
nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader,nounits | tr -d ' ' | grep -qx "${UUID[0]},${SAE_WORKER}"
nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader,nounits | tr -d ' ' | grep -qx "${UUID[1]},${BRIDGE_WORKER}"
printf 'SESSION=%s PANE_PID=%s GPU_INDEX=%s GPU_UUID=%s LOCK=%s LOG=%s\n' "$SAE_SESSION" "$SAE_PID" "${IDX[0]}" "${UUID[0]}" "${LOCK[0]}" "$SAE_LOG"
printf 'SESSION=%s PANE_PID=%s GPU_INDEX=%s GPU_UUID=%s LOCK=%s LOG=%s\n' "$BRIDGE_SESSION" "$BRIDGE_PID" "${IDX[1]}" "${UUID[1]}" "${LOCK[1]}" "$BRIDGE_LOG"
trap - ERR INT TERM
