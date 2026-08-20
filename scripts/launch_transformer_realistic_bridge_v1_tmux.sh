#!/usr/bin/env bash
set -euo pipefail
ROOT="${MSAE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SESSION="transformer_realistic_bridge_v1_20260810"
BRIDGE_OUT="$ROOT/results/transformer_realistic_bridge_v1_20260810"
METHODS_OUT="$ROOT/results/transformer_realistic_methods_v1_20260810"
BRIDGE_PROV="$ROOT/reports/provenance/transformer_realistic_bridge_v1_run_20260810"
METHODS_PROV="$ROOT/reports/provenance/transformer_realistic_methods_v1_run_20260810"
SCRIPT="$ROOT/scripts/transformer_realistic_bridge_v1.py"

if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session exists: $SESSION" >&2; exit 1; fi
if [[ -e "$BRIDGE_OUT" || -e "$METHODS_OUT" || -e "$BRIDGE_PROV" || -e "$METHODS_PROV" ]]; then echo "immutable result/provenance namespace exists" >&2; exit 1; fi
MSAE_ROOT="$ROOT" python "$SCRIPT" verify-review-binding --kind both >/dev/null

mapfile -t GPUS < <(nvidia-smi --query-gpu=index,uuid,memory.used,utilization.gpu --format=csv,noheader,nounits)
chosen_index=""; chosen_uuid=""; lockdir=""
for row in "${GPUS[@]}"; do
  IFS=',' read -r raw_index raw_uuid raw_mem raw_util <<<"$row"
  index="${raw_index// /}"; uuid="${raw_uuid// /}"; mem="${raw_mem// /}"; util="${raw_util// /}"
  (( mem <= 1024 && util <= 10 )) || continue
  candidate="/tmp/msae_transformer_bridge_${uuid}.lockdir"
  if mkdir "$candidate" 2>/dev/null; then chosen_index="$index"; chosen_uuid="$uuid"; lockdir="$candidate"; break; fi
done
if [[ -z "$chosen_index" ]]; then echo "no free lockable GPU" >&2; exit 1; fi
launch_token="$(python - <<'PY'
import secrets
print(secrets.token_hex(24))
PY
)"
printf '%s\n' "$launch_token" > "$lockdir/token"
mkdir -p "$BRIDGE_PROV" "$METHODS_PROV"
python - "$BRIDGE_PROV/handoff_status.json" "$SESSION" "$chosen_index" "$chosen_uuid" "$launch_token" <<'PY'
import json,sys,time
p,session,index,uuid,token=sys.argv[1:]
with open(p,'x') as f: json.dump({'status':'TMUX_START_REQUESTED','session':session,'physical_gpu_index':int(index),'gpu_uuid':uuid,'launch_token':token,'time_ns':time.time_ns()},f,indent=2,sort_keys=True); f.write('\n')
PY
cmd=$(cat <<EOF
set -euo pipefail
trap 'rm -rf "$lockdir"' EXIT TERM INT HUP
[[ "\$(cat "$lockdir/token")" == "$launch_token" ]]
export CUDA_VISIBLE_DEVICES="$chosen_index"
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONHASHSEED=0
cd "$ROOT"
RUN_ROOT=/proc/self/cwd
read -r current_mem current_util < <(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits -i "$chosen_index" | tr -d ' ' | tr ',' ' ')
if (( current_mem > 1024 || current_util > 10 )); then echo 'selected GPU became busy; one-shot launch stopped without retry'; exit 73; fi
set +e
MSAE_ROOT="$RUN_ROOT" python "$RUN_ROOT/scripts/transformer_realistic_bridge_v1.py" run-pipeline --physical-index "$chosen_index" --gpu-uuid "$chosen_uuid" --launch-token "$launch_token" 2>&1 | tee "$RUN_ROOT/reports/provenance/transformer_realistic_bridge_v1_run_20260810/launcher.log"
rc=\${PIPESTATUS[0]}
set -e
exit \$rc
EOF
)
if ! tmux new-session -d -s "$SESSION" "$cmd"; then rm -rf "$lockdir"; exit 1; fi
sleep 2
if ! tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux job exited during startup" >&2; tail -80 "$BRIDGE_PROV/launcher.log" 2>/dev/null || true; exit 1; fi
printf 'SESSION=%s\nGPU_INDEX=%s\nGPU_UUID=%s\nLAUNCH_TOKEN=%s\nLOG=%s\n' "$SESSION" "$chosen_index" "$chosen_uuid" "$launch_token" "$BRIDGE_PROV/launcher.log"
