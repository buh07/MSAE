#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
CONFIG=${MSAE_V2_CONFIG:-configs/atlas_measurement_v2/run.json}
PY=.venv-atlas/bin/python
readarray -t VALUES < <("$PY" - "$CONFIG" <<'PY'
import json,sys
from pathlib import Path
cfg=json.load(open(sys.argv[1]));print(cfg["session"]);print((Path.cwd()/cfg["run_root"]).resolve())
PY
)
SESSION=${VALUES[0]}; RUN_ROOT=${VALUES[1]}; CONFIG_SHA=$(sha256sum "$CONFIG"|awk '{print $1}')
mode=${1:-fresh}

pid_matches() {
  local pid=$1 ticks=$2
  [[ -r "/proc/$pid/stat" ]] && [[ $(awk '{print $22}' "/proc/$pid/stat") == "$ticks" ]]
}

validate_prepared() {
  "$PY" scripts/run_msae_measurement_v2.py --config "$CONFIG" --stage validate >/dev/null
  "$PY" scripts/run_msae_measurement_v2.py --config "$CONFIG" --stage prepare >/dev/null
}

case "$mode" in
  fresh)
    validate_prepared
    tmux has-session -t "$SESSION" 2>/dev/null && { echo "session already exists: $SESSION" >&2; exit 1; }
    [[ ! -e "$RUN_ROOT" ]] || { echo "fresh run root already exists: $RUN_ROOT" >&2; exit 1; }
    mkdir -m 700 "$RUN_ROOT"
    mkdir -m 700 "$RUN_ROOT/logs"
    "$PY" - "$RUN_ROOT/launch.json" "$SESSION" "$CONFIG_SHA" <<'PY'
import json,os,sys,time
from pathlib import Path
path=Path(sys.argv[1]);payload={"schema_version":"atlas_measurement_v2_launch_v1","session":sys.argv[2],
  "config_sha256":sys.argv[3],"host":os.uname().nodename,"launcher_pid":os.getpid(),"launched_unix":time.time()}
with path.open("x") as f:json.dump(payload,f,sort_keys=True,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
PY
    tmux new-session -d -s "$SESSION" -n coordinator \
      "cd '$ROOT'; export MSAE_V2_CONFIG='$CONFIG' MSAE_V2_ATTEMPT=1; exec scripts/run_msae_measurement_v2_pipeline.sh >>'$RUN_ROOT/logs/coordinator.log' 2>&1"
    ;;
  --recover)
    validate_prepared
    [[ -d "$RUN_ROOT" && -f "$RUN_ROOT/launch.json" ]] || { echo "recovery requires an authenticated launch root" >&2; exit 1; }
    [[ ! -e "$RUN_ROOT/COMPLETE.json" && ! -e "$RUN_ROOT/ABANDONED.json" ]] || { echo "terminal run cannot recover" >&2; exit 1; }
    readarray -t LAUNCH < <("$PY" - "$RUN_ROOT/launch.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]));print(x["host"]);print(x["config_sha256"])
PY
)
    [[ ${LAUNCH[0]} == "$(hostname)" && ${LAUNCH[1]} == "$CONFIG_SHA" ]] || { echo "launch host/config mismatch" >&2; exit 1; }
    attempt=1
    if [[ -f "$RUN_ROOT/owner.json" ]]; then
      readarray -t OWNER < <("$PY" - "$RUN_ROOT/owner.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]));print(x["host"]);print(x["pid"]);print(x["start_ticks"]);print(x["config_sha256"]);print(x["attempt"])
PY
)
      [[ ${OWNER[0]} == "$(hostname)" && ${OWNER[3]} == "$CONFIG_SHA" ]] || { echo "owner host/config mismatch" >&2; exit 1; }
      pid_matches "${OWNER[1]}" "${OWNER[2]}" && { echo "live owner blocks recovery" >&2; exit 1; }
      attempt=$((${OWNER[4]}+1))
    fi
    tmux has-session -t "$SESSION" 2>/dev/null && { echo "live tmux session blocks recovery" >&2; exit 1; }
    # Recovery is deliberately fail-closed around live children. A human may use
    # --abandon after proving every recorded PID dead; no unverified PID is killed.
    "$PY" - "$RUN_ROOT" <<'PY'
import json,os,sys
from pathlib import Path
root=Path(sys.argv[1])
for lease in (root/"leases").glob("*.json"):
    row=json.load(open(lease));pid=int(row["child_pid"]);ticks=int(row["child_start_ticks"])
    try: current=int(Path(f"/proc/{pid}/stat").read_text().split()[21])
    except FileNotFoundError: continue
    if current==ticks: raise SystemExit(f"live authenticated orphan requires explicit operator handling: {lease}")
unknown=[p for p in root.rglob(".*.tmp") if p.exists()]
if unknown:raise SystemExit(f"unknown temporary outputs block recovery: {unknown[:3]}")
PY
    "$PY" scripts/validate_msae_measurement_v2_terminal.py --recovery --config "$CONFIG" --run-root "$RUN_ROOT" >"$RUN_ROOT/logs/recovery_validation.${attempt}.json"
    stamp=$(date -u +%Y%m%dT%H%M%S%N)
    if [[ -f "$RUN_ROOT/owner.json" ]]; then ln "$RUN_ROOT/owner.json" "$RUN_ROOT/owner.stale.${stamp}.json"; fi
    if [[ -f "$RUN_ROOT/HANDOFF_READY.json" ]]; then mv "$RUN_ROOT/HANDOFF_READY.json" "$RUN_ROOT/HANDOFF_READY.attempt$((attempt-1)).${stamp}.json"; fi
    if [[ -f "$RUN_ROOT/FAILED.json" ]]; then mv "$RUN_ROOT/FAILED.json" "$RUN_ROOT/FAILED.attempt$((attempt-1)).${stamp}.json"; fi
    tmux new-session -d -s "$SESSION" -n coordinator \
      "cd '$ROOT'; export MSAE_V2_CONFIG='$CONFIG' MSAE_V2_ATTEMPT='$attempt'; exec scripts/run_msae_measurement_v2_pipeline.sh >>'$RUN_ROOT/logs/coordinator.recovery.${attempt}.log' 2>&1"
    ;;
  --abandon)
    [[ -d "$RUN_ROOT" && -f "$RUN_ROOT/owner.json" ]] || { echo "abandon requires an existing owner" >&2; exit 1; }
    [[ ! -e "$RUN_ROOT/COMPLETE.json" && ! -e "$RUN_ROOT/FAILED.json" && ! -e "$RUN_ROOT/ABANDONED.json" ]] || { echo "terminal run cannot be abandoned" >&2; exit 1; }
    readarray -t OWNER < <("$PY" - "$RUN_ROOT/owner.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]));print(x["pid"]);print(x["start_ticks"]);print(x["config_sha256"])
PY
)
    [[ ${OWNER[2]} == "$CONFIG_SHA" ]] || { echo "owner config mismatch" >&2; exit 1; }
    pid_matches "${OWNER[0]}" "${OWNER[1]}" && { echo "live owner blocks abandonment" >&2; exit 1; }
    tmux has-session -t "$SESSION" 2>/dev/null && { echo "live tmux session blocks abandonment" >&2; exit 1; }
    (
    flock -x 199
    "$PY" - "$RUN_ROOT" "$CONFIG_SHA" <<'PY'
import json,os,sys,time
from pathlib import Path
root=Path(sys.argv[1])
if any((root/name).exists() for name in ("COMPLETE.json","FAILED.json","ABANDONED.json")):raise SystemExit("terminal marker appeared while waiting for abandonment lock")
for lease in (root/"leases").glob("*.json"):
    row=json.load(open(lease));pid=int(row["child_pid"]);ticks=int(row["child_start_ticks"])
    try:current=int(Path(f"/proc/{pid}/stat").read_text().split()[21])
    except FileNotFoundError:continue
    if current==ticks:raise SystemExit(f"live child blocks abandonment: {lease}")
path=root/"ABANDONED.json";payload={"schema_version":"atlas_measurement_v2_abandoned_v1","status":"abandoned",
  "config_sha256":sys.argv[2],"abandoned_unix":time.time()}
with path.open("x") as f:json.dump(payload,f,sort_keys=True,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
PY
    ) 199>"$RUN_ROOT/terminal.lock"
    echo "abandoned: $RUN_ROOT"
    exit 0
    ;;
  *) echo "usage: $0 [fresh|--recover|--abandon]" >&2; exit 2;;
esac

for _ in $(seq 1 600); do
  [[ ! -e "$RUN_ROOT/FAILED.json" && ! -e "$RUN_ROOT/ABANDONED.json" && ! -e "$RUN_ROOT/COMPLETE.json" ]] || { echo "run became terminal before live handoff" >&2; exit 1; }
  tmux has-session -t "$SESSION" 2>/dev/null || { echo "tmux coordinator exited before ownership" >&2; exit 1; }
  if [[ -f "$RUN_ROOT/owner.json" && -f "$RUN_ROOT/coordinator_state.json" && -f "$RUN_ROOT/heartbeat.json" ]]; then
    if "$PY" - "$RUN_ROOT" "$CONFIG_SHA" <<'PY'
import json,os,sys,time
from pathlib import Path
root=Path(sys.argv[1]);config_sha=sys.argv[2]
owner=json.load(open(root/"owner.json"));state=json.load(open(root/"coordinator_state.json"));heartbeat=json.load(open(root/"heartbeat.json"))
if owner.get("config_sha256")!=config_sha or state.get("config_sha256")!=config_sha or heartbeat.get("config_sha256")!=config_sha:raise SystemExit(1)
if time.time()-float(heartbeat["heartbeat_unix"])>=65:raise SystemExit(1)
pids=[int(x) for x in state.get("wrapper_pids",[])]
expected={"extract":4,"transform":4,"analyze":1}
if state.get("stage") not in expected or len(pids)!=expected[state["stage"]]:raise SystemExit(1)
if heartbeat.get("stage")!=state.get("stage") or heartbeat.get("wrapper_pids")!=pids:raise SystemExit(1)
leases={}
for path in (root/"leases").glob("*.json"):
    row=json.load(open(path));leases[int(row["wrapper_pid"])]=row
for pid in pids:
    row=leases.get(pid)
    if row is None or row.get("config_sha256")!=config_sha:raise SystemExit(1)
    for key,tick_key in (("wrapper_pid","wrapper_start_ticks"),("child_pid","child_start_ticks")):
        process=int(row[key]);expected_ticks=int(row[tick_key])
        try:observed=int(Path(f"/proc/{process}/stat").read_text().split()[21])
        except FileNotFoundError:raise SystemExit(1)
        if observed!=expected_ticks:raise SystemExit(1)
    fd=Path(f"/proc/{int(row['child_pid'])}/fd/200")
    try:target=os.readlink(fd)
    except OSError:raise SystemExit(1)
    if target!=row["lock_path"]:raise SystemExit(1)
handoff={"schema_version":"atlas_measurement_v2_live_handoff_v1","config_sha256":config_sha,
         "stage":state["stage"],"wrapper_pids":pids,"child_pids":[int(leases[p]["child_pid"]) for p in pids],
         "lease_jobs":[leases[p]["job"] for p in pids],"verified_unix":time.time()}
path=root/"HANDOFF_READY.json"
with path.open("x") as f:json.dump(handoff,f,sort_keys=True,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
PY
    then break; fi
  fi
  sleep 0.5
done
[[ -f "$RUN_ROOT/HANDOFF_READY.json" ]] || { echo "live GPU-stage handoff did not become ready" >&2; exit 1; }
tmux list-windows -t "$SESSION" -F '#I #W #{pane_pid} #{pane_current_command}'
cat "$RUN_ROOT/HANDOFF_READY.json"
