#!/usr/bin/env bash
set -euo pipefail

action=${1:-status}
session=msae_atlas_summary_recovery_20260802
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
run_root=pilot_runs/20260802_atlas_completion_summary_recovery_v1
py=.venv-atlas/bin/python
driver=scripts/recover_msae_completion_continuation_summary.py

status() {
  if tmux has-session -t "$session" 2>/dev/null; then
    tmux list-windows -t "$session" -F '#I #W #{pane_current_command}'
  else
    echo "tmux session: absent"
  fi
  find "$run_root/job_manifests" -maxdepth 1 -type f \
    \( -name '*.manifest.json' -o -name '*.terminal.json' -o -name '*.success.json' \) \
    -printf '%f\n' 2>/dev/null | sort || true
  for job in candidate publish; do
    if compgen -G "$run_root/job_state/$job/g*.json" >/dev/null; then
      "$py" - "$job" <<'PY'
import sys
sys.path.insert(0,"scripts")
from msa_completion_summary_recovery_common import read_state_chain
row=read_state_chain(sys.argv[1])
print(f"{row['job']}: g{row['generation']} {row['phase']}")
PY
    fi
  done
}

case "$action" in
  status)
    status
    exit 0
    ;;
  candidate)
    job=candidate; mode=run
    ;;
  reconcile-candidate)
    job=candidate; mode=reconcile
    ;;
  publish)
    job=publish; mode=run
    ;;
  reconcile-publish)
    job=publish; mode=reconcile
    ;;
  *)
    echo "usage: $0 {candidate|reconcile-candidate|publish|reconcile-publish|status}" >&2
    exit 2
    ;;
esac

tmux has-session -t "$session" 2>/dev/null && {
  echo "tmux session already exists: $session" >&2
  exit 2
}

"$py" - <<'PY'
import sys
sys.path.insert(0, "scripts")
from msa_completion_summary_recovery_common import ensure_recovery_directories
ensure_recovery_directories()
PY
launch_lock="$run_root/locks/launch.lock"
exec 8>>"$launch_lock"
flock -n 8 || {
  echo "another recovery launch is being prepared" >&2
  exit 75
}

attempt=$(
  "$py" - <<'PY'
from datetime import datetime,timezone
import os,secrets
print(f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{os.getppid()}_{secrets.token_hex(4)}")
PY
)
log="$run_root/logs/$job.$attempt.log"
closure_log="$run_root/logs/$job.$attempt.closure.log"
touch "$log" "$closure_log" "$run_root/locks/$job.lock"
"$py" - "$log" "$closure_log" "$run_root/locks/$job.lock" "$launch_lock" <<'PY'
import pathlib,sys
sys.path.insert(0, "scripts")
from msa_completion_summary_recovery_common import fsync_directory, fsync_file
for value in sys.argv[1:]:
    path=pathlib.Path(value)
    fsync_file(path); fsync_directory(path.parent)
PY

argv=("$py" "$driver" supervise --job "$job" --attempt-id "$attempt" --mode "$mode" \
  --log "$log" --closure-log "$closure_log")
printf -v command_q '%q ' "${argv[@]}"
tmux new-session -d -s "$session" -n "$job" \
  "cd $(printf '%q' "$root") && exec $command_q"
echo "launched $job attempt $attempt in tmux session $session"
status
