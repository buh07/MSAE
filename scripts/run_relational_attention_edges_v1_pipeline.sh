#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv-atlas/bin/python"
CONFIG="$ROOT/configs/relational_attention_edges_v1/run.json"
SIGNING_KEY="/jumbo/lisp/f004ndc/.generated/sessions/unleashed-3/modes/unleashed/.secrets/attempt13_ed25519.pem"

readarray -t VALUES < <("$PYTHON" - "$CONFIG" <<'PY'
import json,sys
c=json.load(open(sys.argv[1]))
print(c['runtime']['gpu_uuid'])
print(c['runtime']['lock_path'])
print(c['paths']['run_root'])
PY
)
GPU_UUID="${VALUES[0]}"
LOCK_PATH="${VALUES[1]}"
RUN_ROOT="$ROOT/${VALUES[2]}"

export CUDA_VISIBLE_DEVICES="$GPU_UUID"
export CUBLAS_WORKSPACE_CONFIG=":4096:8"
export PYTHONHASHSEED=20260804
export TOKENIZERS_PARALLELISM=false
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export PYTHONPATH="$ROOT/scripts"

exec 9>"$LOCK_PATH"
flock -n 9 || { echo "GPU UUID lock is already held: $GPU_UUID" >&2; exit 73; }

"$PYTHON" "$ROOT/scripts/run_relational_attention_edges_v1.py" run --signing-key "$SIGNING_KEY" &
PID=$!
READY="$RUN_ROOT/RUNNER_READY.json"
for _ in $(seq 1 240); do
  if [[ -f "$READY" ]]; then
    READY_SHA="$($PYTHON - "$READY" <<'PY'
import hashlib,sys
print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())
PY
)"
    printf '%s\n' "$READY_SHA" > "$RUN_ROOT/LAUNCH_ACK"
    wait "$PID"
    exit $?
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    wait "$PID"
    exit $?
  fi
  sleep 0.25
done
kill "$PID" 2>/dev/null || true
wait "$PID" || true
if [[ ! -f "$RUN_ROOT/TERMINAL.json" ]]; then
  "$PYTHON" "$ROOT/scripts/run_relational_attention_edges_v1.py" terminalize-handshake-timeout --signing-key "$SIGNING_KEY"
fi
[[ -f "$RUN_ROOT/TERMINAL.json" ]] || { echo "signed timeout terminal missing" >&2; exit 75; }
echo "RUNNER_READY handshake timed out" >&2
exit 74
