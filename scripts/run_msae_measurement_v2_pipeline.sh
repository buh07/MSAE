#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
CONFIG=${MSAE_V2_CONFIG:-configs/atlas_measurement_v2/run.json}
PY=.venv-atlas/bin/python
readarray -t CONFIG_VALUES < <($PY - "$CONFIG" <<'PY'
import json,sys
from pathlib import Path
root=Path.cwd();cfg=json.load(open(sys.argv[1]))
print((root/cfg["run_root"]).resolve())
print((root/cfg["data_root"]).resolve())
print(cfg["session"])
PY
)
RUN_ROOT=${CONFIG_VALUES[0]};DATA_ROOT=${CONFIG_VALUES[1]};SESSION=${CONFIG_VALUES[2]}
CONFIG_SHA=$(sha256sum "$CONFIG" | awk '{print $1}')
export MSAE_V2_CONFIG_SHA256=$CONFIG_SHA
ATTEMPT=${MSAE_V2_ATTEMPT:-1}
[[ $ATTEMPT =~ ^[1-9][0-9]*$ ]] || { echo "invalid attempt: $ATTEMPT" >&2; exit 2; }
mkdir -p "$RUN_ROOT/logs" "$RUN_ROOT/jobs" "$RUN_ROOT/leases"
touch "$RUN_ROOT/terminal.lock";chmod 600 "$RUN_ROOT/terminal.lock"

atomic_state() {
  local path=$1; shift
  "$PY" - "$path" "$@" <<'PY'
import json,os,sys,tempfile,time
from pathlib import Path
path=Path(sys.argv[1]); data=json.loads(sys.argv[2]); data["written_unix"]=time.time()
fd,name=tempfile.mkstemp(prefix=f".{path.name}.",suffix=".tmp",dir=path.parent)
with os.fdopen(fd,"w") as f: json.dump(data,f,sort_keys=True,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
os.replace(name,path)
PY
}

pid_ticks() { awk '{print $22}' "/proc/$1/stat"; }
OWNER_PID=$$
OWNER_TICKS=$(pid_ticks $$)
HOST=$(hostname)
atomic_state "$RUN_ROOT/owner.json" "{\"schema_version\":\"atlas_measurement_v2_owner_v1\",\"host\":\"$HOST\",\"pid\":$OWNER_PID,\"start_ticks\":$OWNER_TICKS,\"config_sha256\":\"$CONFIG_SHA\",\"session\":\"$SESSION\",\"attempt\":$ATTEMPT}"

active_pids=()
stage=starting
write_stage() {
  local joined=""
  if ((${#active_pids[@]})); then joined=$(IFS=,; echo "${active_pids[*]}"); fi
  "$PY" - "$RUN_ROOT/coordinator_state.json" "$stage" "$joined" "$CONFIG_SHA" <<'PY'
import json,os,sys,tempfile,time
from pathlib import Path
path=Path(sys.argv[1]); pids=[int(x) for x in sys.argv[3].split(",") if x]
data={"schema_version":"atlas_measurement_v2_coordinator_state_v1","stage":sys.argv[2],"wrapper_pids":pids,
      "config_sha256":sys.argv[4],"updated_unix":time.time()}
fd,name=tempfile.mkstemp(prefix=f".{path.name}.",suffix=".tmp",dir=path.parent)
with os.fdopen(fd,"w") as f:json.dump(data,f,sort_keys=True,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
os.replace(name,path)
PY
}

heartbeat() {
  while kill -0 "$OWNER_PID" 2>/dev/null; do
    "$PY" - "$RUN_ROOT" "$HOST" "$OWNER_PID" "$OWNER_TICKS" "$CONFIG_SHA" <<'PY'
import json,os,sys,tempfile,time
from pathlib import Path
root=Path(sys.argv[1]); state=json.load(open(root/"coordinator_state.json"))
data={"schema_version":"atlas_measurement_v2_heartbeat_v1","host":sys.argv[2],"pid":int(sys.argv[3]),
      "start_ticks":int(sys.argv[4]),"config_sha256":sys.argv[5],"stage":state["stage"],
      "wrapper_pids":state["wrapper_pids"],"heartbeat_unix":time.time()}
path=root/"heartbeat.json";fd,name=tempfile.mkstemp(prefix=".heartbeat.",suffix=".tmp",dir=root)
with os.fdopen(fd,"w") as f:json.dump(data,f,sort_keys=True,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
os.replace(name,path)
PY
    sleep 30
  done
}

failure() {
  local code=${1:-$?}
  trap - EXIT ERR INT TERM
  for pid in "${active_pids[@]:-}"; do kill -TERM "$pid" 2>/dev/null || true; done
  for pid in "${active_pids[@]:-}"; do wait "$pid" 2>/dev/null || true; done
  kill "$HEARTBEAT_PID" 2>/dev/null || true
  (
    flock -x 199
    if [[ ! -e "$RUN_ROOT/COMPLETE.json" && ! -e "$RUN_ROOT/FAILED.json" && ! -e "$RUN_ROOT/ABANDONED.json" ]]; then
      atomic_state "$RUN_ROOT/FAILED.json" "{\"schema_version\":\"atlas_measurement_v2_failure_v1\",\"status\":\"failed\",\"stage\":\"$stage\",\"exit_code\":$code,\"config_sha256\":\"$CONFIG_SHA\"}"
    fi
  ) 199>"$RUN_ROOT/terminal.lock"
  exit "$code"
}
trap 'failure $?' EXIT ERR
trap 'failure 130' INT
trap 'failure 143' TERM
write_stage
heartbeat & HEARTBEAT_PID=$!

# Fail before materializing neural outputs unless there is room for two complete copies.
"$PY" - "$RUN_ROOT" "$DATA_ROOT/prepared/manifest.json" <<'PY'
import json,shutil,sys
from pathlib import Path
root=Path(sys.argv[1]);prepared=json.load(open(Path(sys.argv[2])))
rows=sum(role["activation_rows"] for role in prepared["roles"].values())
projected=rows*768*4*(1+2*4) + 2_000_000_000
free=shutil.disk_usage(root).free
if free < 2*projected: raise SystemExit(f"insufficient disk: free={free}, required={2*projected}")
print(json.dumps({"rows":rows,"projected_bytes":projected,"required_free_bytes":2*projected,"free_bytes":free}))
PY

stage=prepare;active_pids=();write_stage
"$PY" scripts/run_msae_measurement_v2.py --config "$CONFIG" --stage prepare >"$RUN_ROOT/logs/prepare.log" 2>&1

mapfile -t GPU_UUIDS < <("$PY" - "$CONFIG" <<'PY'
import json,sys
for x in json.load(open(sys.argv[1]))["gpu_uuids"]:print(x)
PY
)
if [[ ${#GPU_UUIDS[@]} -ne 4 ]]; then echo "exactly four GPU UUIDs required" >&2; exit 1; fi

run_gpu() {
  local stage_job=$1 uuid=$2; shift 2
  local job="attempt${ATTEMPT}_${stage_job}"
  "$PY" scripts/msae_measurement_v2_gpu_runner.py --run-root "$RUN_ROOT" --job "$job" --uuid "$uuid" \
    --log "$RUN_ROOT/logs/${job}.log" -- "$@" &
  active_pids+=("$!")
}
wait_wave() {
  local finished status i
  local remaining=("${active_pids[@]}")
  while ((${#remaining[@]})); do
    status=0
    wait -n -p finished "${remaining[@]}" || status=$?
    for i in "${!remaining[@]}"; do
      if [[ ${remaining[$i]} == "$finished" ]]; then unset 'remaining[i]'; break; fi
    done
    remaining=("${remaining[@]}")
    if ((status)); then
      for i in "${remaining[@]}"; do kill -TERM "$i" 2>/dev/null || true; done
      for i in "${remaining[@]}"; do wait "$i" 2>/dev/null || true; done
      return "$status"
    fi
  done
  active_pids=();write_stage
}

stage=extract;active_pids=()
roles=(discovery calibration C1 C2)
for i in 0 1 2 3; do
  run_gpu "extract_${roles[$i]}" "${GPU_UUIDS[$i]}" "$PY" scripts/run_msae_measurement_v2.py \
    --config "$CONFIG" --stage extract --role "${roles[$i]}" --device cuda:0 --batch-size 24
done
write_stage;wait_wave

stage=transform;active_pids=()
jobs=(g4 g5 g6 g7)
for i in 0 1 2 3; do
  run_gpu "transform_${jobs[$i]}" "${GPU_UUIDS[$i]}" "$PY" scripts/run_msae_measurement_v2.py \
    --config "$CONFIG" --stage transform --job "${jobs[$i]}" --device cuda:0 --batch-size 512
done
write_stage;wait_wave

stage=analyze;active_pids=()
run_gpu analyze "${GPU_UUIDS[0]}" "$PY" scripts/run_msae_measurement_v2.py \
  --config "$CONFIG" --stage analyze --device cuda:0 --batch-size 512
write_stage;wait_wave

stage=aggregate;active_pids=();write_stage
"$PY" scripts/run_msae_measurement_v2.py --config "$CONFIG" --stage aggregate >"$RUN_ROOT/logs/aggregate.log" 2>&1
stage=complete;write_stage
kill "$HEARTBEAT_PID" 2>/dev/null || true
wait "$HEARTBEAT_PID" 2>/dev/null || true
trap - EXIT ERR INT TERM
exit 0
