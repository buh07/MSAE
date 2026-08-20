#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$ROOT/configs/atlas_relation_context_v9/run.json"
PYTHON="$ROOT/.venv-atlas/bin/python"
SIGNING_KEY="${1:?usage: launch_atlas_relation_context_v9_tmux.sh /absolute/path/to/signing-key}"
SESSION="$($PYTHON - "$CONFIG" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))['tmux_session'])
PY
)"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "refusing existing tmux session: $SESSION" >&2
  exit 1
fi
if [[ ! -f "$SIGNING_KEY" || "$SIGNING_KEY" != /* ]]; then
  echo "signing key must be an existing absolute path" >&2
  exit 1
fi

printf -v TMUX_COMMAND 'cd %q && export ATLAS_ATTEMPT13_SIGNING_KEY=%q && exec bash scripts/run_atlas_relation_context_v9_pipeline.sh' \
  "$ROOT" "$SIGNING_KEY"
tmux new-session -d -s "$SESSION" "$TMUX_COMMAND"
printf 'launched %s\n' "$SESSION"
