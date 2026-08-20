#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)";cd "$ROOT";PY="$ROOT/.venv-atlas/bin/python"
"$PY" scripts/relational_measurement_v4_lifecycle.py handoff --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --output "$V4_HANDOFF" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid $$
"$PY" scripts/relational_measurement_v4_lifecycle.py opening --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --handoff "$V4_HANDOFF" --output "$V4_OPENING" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid $$
mkdir "$V4_RUNROOT"
set +e
"$PY" scripts/run_relational_measurement_v4.py --config "$V4_CONFIG" --mode execute --prepared "$V4_PREPARED" --authorization "$V4_AUTH" --opening "$V4_OPENING" --output "$V4_RESULT" --nonce "$V4_NONCE"
STATUS=$?
set -e
if [[ $STATUS -eq 0 ]]; then
  "$PY" scripts/relational_measurement_v4_lifecycle.py terminal --authorization "$V4_AUTH" --opening "$V4_OPENING" --prepared "$V4_PREPARED" --result "$V4_RESULT" --output "$V4_CLOSURE" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE"
else
  REASON="$("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["reason"])' "$V4_RUNROOT/failure.json" 2>/dev/null || printf UNEXPECTED_EXCEPTION)"
  "$PY" scripts/relational_measurement_v4_lifecycle.py terminal --authorization "$V4_AUTH" --opening "$V4_OPENING" --prepared "$V4_PREPARED" --output "$V4_CLOSURE" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --technical-reason "$REASON" --partial-root "$V4_RUNROOT"
fi
exit "$STATUS"
