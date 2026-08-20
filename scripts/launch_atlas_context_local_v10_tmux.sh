#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$ROOT/configs/atlas_context_local_v10/run.json"
PYTHON="$ROOT/.venv-atlas/bin/python"
KEY="${1:?usage: launch_atlas_context_local_v10_tmux.sh /absolute/path/to/key}"
readarray -t V < <("$PYTHON" - "$CONFIG" <<'PY'
import json,sys
c=json.load(open(sys.argv[1])); print(c['tmux_session']); print(c['runtime']['physical_gpu_index']); print(c['runtime']['gpu_uuid'])
PY
)
SESSION="${V[0]}"; INDEX="${V[1]}"; UUID="${V[2]}"
[[ "$KEY" = /* && -f "$KEY" ]] || { echo 'signing key must be an existing absolute path' >&2; exit 1; }
! tmux has-session -t "$SESSION" 2>/dev/null || { echo "existing tmux session: $SESSION" >&2; exit 1; }
ROW="$(nvidia-smi --query-gpu=index,uuid,memory.free --format=csv,noheader,nounits | awk -F, -v i="$INDEX" '$1+0==i {gsub(/^ +| +$/,"",$2); gsub(/^ +| +$/,"",$3); print $2" "$3}')"
read -r ACTUAL_UUID FREE <<<"$ROW"
[[ "$ACTUAL_UUID" = "$UUID" && "$FREE" -ge 2000 ]] || { echo "GPU unavailable/drift: expected $INDEX $UUID, saw $ROW" >&2; exit 1; }
printf -v CMD 'cd %q && export ATLAS_ATTEMPT14_SIGNING_KEY=%q && exec bash scripts/run_atlas_context_local_v10_pipeline.sh' "$ROOT" "$KEY"
tmux new-session -d -s "$SESSION" "$CMD"
tmux set-option -t "$SESSION" remain-on-exit on >/dev/null
printf 'launched %s on physical GPU %s (%s; %s MiB free)\n' "$SESSION" "$INDEX" "$UUID" "$FREE"
