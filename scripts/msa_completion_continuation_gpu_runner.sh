#!/usr/bin/env bash
set -uo pipefail
atomic_publish() {
  local target=$1 temporary="${1}.tmp.$$.${RANDOM}"
  cat > "$temporary"
  python - "$temporary" "$(dirname "$target")" <<'PY'
import os,sys
with open(sys.argv[1],"rb") as h: os.fsync(h.fileno())
fd=os.open(sys.argv[2],os.O_RDONLY)
try: os.fsync(fd)
finally: os.close(fd)
PY
  ln "$temporary" "$target" && rm "$temporary"
}
write_terminal_record() {
  local status=$1
  [[ -e "$run_root/job_manifests/${job}.terminal.json" ]] && return 0
  JOB="$job" STATUS="$status" OUTCOME="$outcome" STARTED="$scoring_started" GPU="$gpu" UUID="$uuid" \
  PROCESS_STARTED="$process_started_utc" PROCESS_ENDED="$process_ended_utc" PROCESS_ELAPSED="$process_elapsed_seconds" \
  STAGE="$stage" EXPECTED="$expected" CONFIG_SHA="$config_sha" FREEZE_SHA="$freeze_sha" \
  .venv-atlas/bin/python - <<'PY' | atomic_publish "$run_root/job_manifests/${job}.terminal.json"
import json,os
from datetime import datetime,timezone
print(json.dumps({"schema_version":"atlas_completion_continuation_job_terminal_v1",
 "job":os.environ["JOB"],"exit_code":int(os.environ["STATUS"]),"outcome":os.environ["OUTCOME"],
 "scoring_started":os.environ["STARTED"]=="true","gpu_index":(int(os.environ["GPU"]) if os.environ["GPU"] else None),
 "gpu_uuid":os.environ["UUID"] or None,"stage":os.environ["STAGE"],"expected_output":os.environ["EXPECTED"],
 "process_started_utc":os.environ["PROCESS_STARTED"] or None,
 "process_ended_utc":os.environ["PROCESS_ENDED"] or None,
 "process_elapsed_seconds":float(os.environ["PROCESS_ELAPSED"]),
 "config_sha256":os.environ["CONFIG_SHA"],"completion_bundle_sha256":os.environ["FREEZE_SHA"],
 "diagnostic_continuation_only":True,"decision_promotion_allowed":False,
 "ended_utc":datetime.now(timezone.utc).isoformat()},sort_keys=True,separators=(",",":")))
PY
}
publish_supervisor_record() {
  local kind=$1 target
  if [[ "$kind" == resource_timeout ]]; then
    target="$run_root/job_manifests/${job}.resource_timeout.json"
  else
    target="$run_root/job_manifests/${job}.process_crash.json"
  fi
  JOB="$job" STATUS="$exit_code" KIND="$kind" \
  GPU="$gpu" UUID="$uuid" STAGE="$stage" EXPECTED="$expected" \
  PROCESS_STARTED="$process_started_utc" PROCESS_ENDED="$process_ended_utc" PROCESS_ELAPSED="$process_elapsed_seconds" \
  MANIFEST="$run_root/job_manifests/${job}.json" LOG="$log" \
  DEADLINE_PATH="$deadline_path" DEADLINE_SHA="$deadline_sha" \
  RESERVATION_PATH="$reservation_path" RESERVATION_SHA="$reservation_sha" \
  CONFIG_SHA="$config_sha" FREEZE_SHA="$freeze_sha" \
  .venv-atlas/bin/python - <<'PY' | atomic_publish "$target"
import json,os,sys
from pathlib import Path
sys.path.insert(0,"scripts")
from msa_completion_continuation_common import supervisor_record_payload
manifest=Path(os.environ["MANIFEST"]); log=Path(os.environ["LOG"])
print(json.dumps(supervisor_record_payload(
 kind=os.environ["KIND"],job_id=os.environ["JOB"],exit_code=int(os.environ["STATUS"]),
 gpu_index=int(os.environ["GPU"]),gpu_uuid=os.environ["UUID"],
 stage=Path(os.environ["STAGE"]),expected_output=os.environ["EXPECTED"],
 process_started_utc=os.environ["PROCESS_STARTED"],process_ended_utc=os.environ["PROCESS_ENDED"],
 process_elapsed_seconds=float(os.environ["PROCESS_ELAPSED"]),launch_manifest=manifest,log=log,
 stage_deadline=Path(os.environ["DEADLINE_PATH"]),stage_deadline_sha256=os.environ["DEADLINE_SHA"],
 budget_reservation=Path(os.environ["RESERVATION_PATH"]),
 budget_reservation_sha256=os.environ["RESERVATION_SHA"],config_sha256=os.environ["CONFIG_SHA"],
 completion_bundle_sha256=os.environ["FREEZE_SHA"]),sort_keys=True,separators=(",",":")))
PY
}
cleanup() {
  local status=$?
  trap - EXIT INT TERM
  [[ $exit_code -ne 1 || $status -eq 1 ]] || exit_code=$status
  write_terminal_record "$exit_code" || true
  if [[ -n "$claim" ]]; then rm -f "$claim/claim.json"; rmdir "$claim" 2>/dev/null || true; fi
  exit "$exit_code"
}
if [[ ${1:-} == --self-test-supervisor ]]; then
  [[ ${MSAE_CONTINUATION_SUPERVISOR_SELFTEST:-} == 1 && $# -eq 3 ]] || {
    echo "supervisor self-test requires its explicit test guard, root, and case" >&2; exit 2; }
  test_root=$2; test_case=$3; repo_root=$(pwd -P); test_python="$repo_root/.venv-atlas/bin/python"
  test_root=$(.venv-atlas/bin/python - "$test_root" "$test_case" "$repo_root" <<'PY'
import os,pwd,sys,tempfile
from pathlib import Path
root=Path(sys.argv[1]).resolve(); case=sys.argv[2]; repo=Path(sys.argv[3]).resolve(strict=True)
tmp=Path(tempfile.gettempdir()).resolve(strict=True)
pytest_base=tmp/f"pytest-of-{pwd.getpwuid(os.getuid()).pw_name}"
if not pytest_base.is_dir() or pytest_base.is_symlink() or pytest_base.stat().st_uid!=os.getuid():
    raise SystemExit("canonical pytest base is absent, symlinked, or not owned by current UID")
pytest_base=pytest_base.resolve(strict=True)
try: relative=root.relative_to(pytest_base)
except ValueError: raise SystemExit("supervisor self-test root is outside canonical pytest temporary base")
if not relative.parts or not relative.parts[0].startswith("pytest-"):
    raise SystemExit("supervisor self-test root lacks canonical pytest invocation ancestor")
protected=[repo, repo/"pilot_runs/20260801_atlas_completion_v1",
 repo/"pilot_runs/20260802_atlas_completion_diagnostic_continuation_v1",
 repo/"results/atlas/completion_diagnostic_v1"]
for path in protected:
    try: root.relative_to(path.resolve())
    except ValueError: pass
    else: raise SystemExit("supervisor self-test root is inside a protected experiment root")
if case not in {"timeout","sigkill","abort","missing_output"}:
    raise SystemExit("unknown supervisor self-test case")
if root.exists(): raise SystemExit("supervisor self-test root already exists")
print(root)
PY
  )
  [[ $? -eq 0 ]] || exit $?
  run_root=$test_root; job="selftest_${test_case}"; stage="$test_root/stage"
  expected=intentionally_absent.json; gpu=0; uuid=GPU-supervisor-selftest
  scoring_started=true; config_sha=$(printf 'a%.0s' {1..64}); freeze_sha=$(printf 'b%.0s' {1..64})
  mkdir -p "$stage" "$run_root/job_manifests" "$run_root/logs" "$run_root/support"
  log="$run_root/logs/${job}.log"
  test_manifest="$run_root/job_manifests/${job}.json"
  deadline_path="$run_root/support/deadline.json"
  reservation_path="$run_root/support/reservation.json"
  .venv-atlas/bin/python - "$test_manifest" "$log" "$deadline_path" "$reservation_path" <<'PY'
import json,sys
from pathlib import Path
for path,row in [
 (Path(sys.argv[1]),{"schema_version":"supervisor_selftest_manifest_v1"}),
 (Path(sys.argv[3]),{"schema_version":"supervisor_selftest_deadline_v1"}),
 (Path(sys.argv[4]),{"schema_version":"supervisor_selftest_reservation_v1"})]:
 path.write_text(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n")
Path(sys.argv[2]).write_text("supervisor self-test\n")
PY
  soft=10; grace=1
  case "$test_case" in
    timeout) soft=1; test_command=("$test_python" -c 'import signal,time; signal.signal(signal.SIGINT,lambda *a:None); time.sleep(30)') ;;
    sigkill) test_command=("$test_python" -c 'import os; os.kill(os.getpid(),9)') ;;
    abort) test_command=("$test_python" -c 'import os; os.abort()') ;;
    missing_output) test_command=(/bin/true) ;;
  esac
  process_started_utc=$(date -u +%Y-%m-%dT%H:%M:%S.%N%:z)
  process_start_ns=$(.venv-atlas/bin/python -c 'import time; print(time.monotonic_ns())')
  set +e
  (cd "$test_root" && ulimit -c 0 &&
   timeout --signal=INT --kill-after="${grace}s" "$soft" "${test_command[@]}") >>"$log" 2>&1
  test_status=$?
  set -e
  process_end_ns=$(.venv-atlas/bin/python -c 'import time; print(time.monotonic_ns())')
  process_ended_utc=$(date -u +%Y-%m-%dT%H:%M:%S.%N%:z)
  process_elapsed_seconds=$(.venv-atlas/bin/python - "$process_start_ns" "$process_end_ns" <<'PY'
import sys
print(max(0.0,(int(sys.argv[2])-int(sys.argv[1]))/1e9))
PY
  )
  test_outcome=$(.venv-atlas/bin/python - "$test_status" "$process_elapsed_seconds" "$soft" <<'PY'
import sys
sys.path.insert(0,"scripts")
from msa_completion_continuation_common import classify_supervised_exit
print(classify_supervised_exit(
 exit_code=int(sys.argv[1]),process_elapsed_seconds=float(sys.argv[2]),
 soft_timeout_seconds=float(sys.argv[3]),expected_output_exists=False,
 stage_terminal_exists=False,matching_launch_failure_exists=False))
PY
  )
  [[ "$test_outcome" == resource_timeout || "$test_outcome" == process_crash ]] || {
    echo "unexpected supervisor self-test outcome: $test_outcome" >&2; exit 1; }
  [[ $test_status -ne 0 ]] || test_status=1
  exit_code=$test_status; outcome=$test_outcome
  deadline_sha=$(sha256sum "$deadline_path" | awk '{print $1}')
  reservation_sha=$(sha256sum "$reservation_path" | awk '{print $1}')
  publish_supervisor_record "$outcome"
  claim=""
  set +e; (trap cleanup EXIT; exit "$exit_code"); cleanup_status=$?; set -e
  [[ $cleanup_status -eq $exit_code ]] || {
    echo "supervisor self-test cleanup status mismatch" >&2; exit 1; }
  exit 0
fi
if [[ $# -lt 4 ]]; then echo "usage: $0 RUN_ROOT JOB LOG COMMAND..." >&2; exit 2; fi
run_root=$1; job=$2; log=$3; shift 3
.venv-atlas/bin/python - "$run_root" "$job" "$log" "$@" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,"scripts")
from msa_completion_continuation_common import RUN_ROOT,canonical_gpu_command
if Path(sys.argv[1]).resolve()!=RUN_ROOT.resolve():
    raise SystemExit("noncanonical continuation run root")
if Path(sys.argv[3]).resolve()!=(RUN_ROOT/"logs"/f"{sys.argv[2]}.log").resolve():
    raise SystemExit("noncanonical continuation log path")
if sys.argv[4:]!=canonical_gpu_command(sys.argv[2]):
    raise SystemExit(f"noncanonical GPU command for {sys.argv[2]}")
PY
[[ $? -eq 0 ]] || exit $?
mkdir -p "$run_root/allocations" "$run_root/job_manifests" "$(dirname "$log")"
config=configs/atlas_completion_continuation/analysis.json
freeze=configs/atlas_completion_continuation/freeze_record.json
config_sha=$(sha256sum "$config" | awk '{print $1}')
freeze_sha=$(python -c 'import json; print(json.load(open("configs/atlas_completion_continuation/freeze_record.json"))["bundle_sha256"])')
readarray -t spec < <(.venv-atlas/bin/python - "$job" <<'PY'
import sys
sys.path.insert(0,"scripts")
from msa_completion_continuation_common import RUN_ROOT,canonical_job_specs
row=canonical_job_specs()[sys.argv[1]]
print(RUN_ROOT/row["stage"])
print(row["expected"])
PY
)
stage=${spec[0]}; expected=${spec[1]}
claim=""; gpu=""; uuid=""; scoring_started=false; outcome=process_failure; exit_code=1
process_started_utc=""; process_ended_utc=""; process_elapsed_seconds=0
stage_terminal_json() {
  .venv-atlas/bin/python - "$stage" <<'PY'
import json,sys
from pathlib import Path
sys.path.insert(0,"scripts")
from msa_completion_common import terminal_state,sha256_file
p=Path(sys.argv[1]); state=terminal_state(p)
if state:
 name="MEASUREMENT_COMPLETE.json" if state=="complete" else "FROZEN_EQUIVOCAL_STOP.json"
 q=p/name
 print(json.dumps({"state":state,"path":str(q),"sha256":sha256_file(q)}))
PY
}
trap cleanup EXIT INT TERM
# Frozen resource prechecks.
avail_kb=$(df -Pk "$(dirname "$run_root")" | awk 'NR==2 {print $4}')
mem_kb=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)
if (( avail_kb < 50*1024*1024 || mem_kb < 128*1024*1024 )); then
  outcome=resource_not_launched; exit_code=75
  JOB="$job" AVAIL="$avail_kb" MEM="$mem_kb" CONFIG_SHA="$config_sha" FREEZE_SHA="$freeze_sha" \
  .venv-atlas/bin/python - <<'PY' | atomic_publish "$run_root/job_manifests/${job}.resource_stop.json"
import json,os
from datetime import datetime,timezone
print(json.dumps({"schema_version":"atlas_completion_continuation_resource_stop_v1","job":os.environ["JOB"],
 "reason":"disk_or_ram_precheck_failed","disk_available_kib":int(os.environ["AVAIL"]),
 "ram_available_kib":int(os.environ["MEM"]),"scoring_started":False,
 "config_sha256":os.environ["CONFIG_SHA"],"completion_bundle_sha256":os.environ["FREEZE_SHA"],
 "decision_promotion_allowed":False,"recorded_utc":datetime.now(timezone.utc).isoformat()},sort_keys=True,separators=(",",":")))
PY
  exit "$exit_code"
fi
queue_start=$(date +%s); queue_start_utc=$(date -u +%FT%TZ)
while [[ -z "$gpu" ]]; do
  terminal=$(stage_terminal_json || true)
  if [[ -n "$terminal" && ! -e "$stage/$expected" ]]; then
    outcome=superseded_by_stage_stop; exit_code=0
    printf '%s\n' "$terminal" | JOB="$job" CONFIG_SHA="$config_sha" FREEZE_SHA="$freeze_sha" .venv-atlas/bin/python -c \
      'import json,os,sys; from datetime import datetime,timezone; d=json.load(sys.stdin); print(json.dumps({"schema_version":"atlas_completion_continuation_superseded_v1","job":os.environ["JOB"],"stage_terminal_state":d["state"],"stage_terminal_path":d["path"],"stage_terminal_sha256":d["sha256"],"scoring_started":False,"config_sha256":os.environ["CONFIG_SHA"],"completion_bundle_sha256":os.environ["FREEZE_SHA"],"decision_promotion_allowed":False,"recorded_utc":datetime.now(timezone.utc).isoformat()},sort_keys=True,separators=(",",":")))' \
      | atomic_publish "$run_root/job_manifests/${job}.superseded_stage.json"
    exit 0
  fi
  now=$(date +%s)
  if (( now - queue_start >= 43200 )); then
    outcome=resource_not_launched; exit_code=75
    gpu_observations=$(.venv-atlas/bin/python - <<'PY'
import csv,json,subprocess
try:
 out=subprocess.run(["nvidia-smi","--query-gpu=index,uuid,memory.used",
  "--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=30,check=True).stdout
 rows=[]
 for fields in csv.reader(out.splitlines()):
  if len(fields)!=3: continue
  rows.append({"gpu_index":int(fields[0].strip()),"gpu_uuid":fields[1].strip(),
               "memory_used_mib":int(fields[2].strip())})
except Exception:
 rows=[]
print(json.dumps(rows,sort_keys=True,separators=(",",":")))
PY
    )
    JOB="$job" START="$queue_start_utc" GPU_OBSERVATIONS="$gpu_observations" \
    CONFIG_SHA="$config_sha" FREEZE_SHA="$freeze_sha" \
    .venv-atlas/bin/python - <<'PY' | atomic_publish "$run_root/job_manifests/${job}.resource_stop.json"
import json,os
from datetime import datetime,timezone
print(json.dumps({"schema_version":"atlas_completion_continuation_resource_stop_v1","job":os.environ["JOB"],
 "reason":"gpu_queue_deadline_exceeded","queue_started_utc":os.environ["START"],
 "queue_deadline_seconds":43200,"queue_ended_utc":datetime.now(timezone.utc).isoformat(),
 "gpu_observations":json.loads(os.environ["GPU_OBSERVATIONS"]),
 "scoring_started":False,"config_sha256":os.environ["CONFIG_SHA"],
 "completion_bundle_sha256":os.environ["FREEZE_SHA"],"decision_promotion_allowed":False},
 sort_keys=True,separators=(",",":")))
PY
    exit "$exit_code"
  fi
  while IFS=, read -r idx gpu_uuid memory; do
    idx=$(xargs <<<"$idx"); gpu_uuid=$(xargs <<<"$gpu_uuid"); memory=$(tr -dc '0-9' <<<"$memory")
    candidate="$run_root/allocations/gpu_${idx}"
    if [[ -d "$candidate" ]]; then
      # Reclaim only a same-host, provably dead allocation; never guess about
      # remote, malformed, or live owners.
      .venv-atlas/bin/python - "$candidate" "$run_root" <<'PYRECLAIM' >/dev/null 2>&1 || true
import json,os,socket,sys,uuid
from pathlib import Path
claim,root=Path(sys.argv[1]),Path(sys.argv[2]); meta=claim/"claim.json"
if not meta.is_file(): raise SystemExit(1)
row=json.loads(meta.read_text())
if row.get("host")!=socket.gethostname(): raise SystemExit(1)
pid=int(row.get("pid",-1))
try: os.kill(pid,0)
except ProcessLookupError: stale=pid>0
except PermissionError: stale=False
else: stale=False
if not stale: raise SystemExit(1)
q=root/"invalid_partial/stale_allocations"; q.mkdir(parents=True,exist_ok=True)
os.rename(claim,q/f"{claim.name}.{uuid.uuid4().hex}")
PYRECLAIM
    fi
    if mkdir "$candidate" 2>/dev/null; then
      procs=$(nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader 2>/dev/null || true)
      memory_now=$(nvidia-smi -i "$idx" --query-gpu=memory.used --format=csv,noheader,nounits | tr -dc '0-9')
      if [[ ${memory_now:-999999} -lt 1024 ]] && ! grep -q "^${gpu_uuid}," <<<"$procs"; then
        gpu=$idx; uuid=$gpu_uuid; claim=$candidate
        printf '{"job":"%s","host":"%s","pid":%d,"gpu_index":%d,"gpu_uuid":"%s","started_utc":"%s"}\n' \
          "$job" "$(hostname)" "$$" "$idx" "$gpu_uuid" "$(date -u +%FT%TZ)" | atomic_publish "$candidate/claim.json"
        break
      fi
      rmdir "$candidate"
    fi
  done < <(nvidia-smi --query-gpu=index,uuid,memory.used --format=csv,noheader,nounits)
  [[ -n "$gpu" ]] || sleep 60
done
# Requery immediately after allocation and before process start.
actual_uuid=$(nvidia-smi -i "$gpu" --query-gpu=uuid --format=csv,noheader | xargs)
actual_mem=$(nvidia-smi -i "$gpu" --query-gpu=memory.used --format=csv,noheader,nounits | tr -dc '0-9')
if [[ "$actual_uuid" != "$uuid" || ${actual_mem:-999999} -ge 1024 ]]; then
  outcome=resource_not_launched; exit_code=75
  JOB="$job" GPU="$gpu" UUID="$uuid" ACTUAL_UUID="$actual_uuid" ACTUAL_MEM="$actual_mem" \
  CONFIG_SHA="$config_sha" FREEZE_SHA="$freeze_sha" .venv-atlas/bin/python - <<'PYRESOURCE' | atomic_publish "$run_root/job_manifests/${job}.resource_stop.json"
import json,os
from datetime import datetime,timezone
print(json.dumps({"schema_version":"atlas_completion_continuation_resource_stop_v1","job":os.environ["JOB"],
 "reason":"gpu_requery_failed","observed_gpu_index":int(os.environ["GPU"]),
 "expected_gpu_uuid":os.environ["UUID"],"observed_gpu_uuid":os.environ["ACTUAL_UUID"],
 "observed_memory_mib":int(os.environ["ACTUAL_MEM"] or -1),
 "scoring_started":False,"config_sha256":os.environ["CONFIG_SHA"],
 "completion_bundle_sha256":os.environ["FREEZE_SHA"],"decision_promotion_allowed":False,
 "recorded_utc":datetime.now(timezone.utc).isoformat()},sort_keys=True,separators=(",",":")))
PYRESOURCE
  gpu=""; uuid=""
  exit "$exit_code"
fi
# Atomically share one 24-hour deadline across sibling processes and reserve a
# conservative per-job slice under the frozen 192 GPU-hour cap.
mkdir -p "$run_root/stage_deadlines" "$run_root/budget_reservations"
limit_json=$(JOB="$job" STAGE="$stage" RUN_ROOT_ARG="$run_root" \
  .venv-atlas/bin/python - <<'PY'
import json,os,sys
from pathlib import Path
sys.path.insert(0,"scripts")
from msa_completion_continuation_common import canonical_job_specs,reserve_gpu_resources
root=Path(os.environ["RUN_ROOT_ARG"]); job=os.environ["JOB"]; spec=canonical_job_specs()[job]
print(json.dumps(reserve_gpu_resources(
 run_root=root,job_id=job,stage=Path(os.environ["STAGE"]),spec=spec)))
PY
) || {
  outcome=resource_not_launched; exit_code=75
  JOB="$job" GPU="$gpu" UUID="$uuid" CONFIG_SHA="$config_sha" FREEZE_SHA="$freeze_sha" .venv-atlas/bin/python - <<'PY' | atomic_publish "$run_root/job_manifests/${job}.resource_stop.json"
import json,os
from datetime import datetime,timezone
print(json.dumps({"schema_version":"atlas_completion_continuation_resource_stop_v1","job":os.environ["JOB"],
 "reason":"stage_or_total_gpu_budget_gate_failed","scoring_started":False,
 "observed_gpu_index":int(os.environ["GPU"]),"observed_gpu_uuid":os.environ["UUID"],
 "config_sha256":os.environ["CONFIG_SHA"],"completion_bundle_sha256":os.environ["FREEZE_SHA"],
 "decision_promotion_allowed":False,"recorded_utc":datetime.now(timezone.utc).isoformat()},sort_keys=True,separators=(",",":")))
PY
  gpu=""; uuid=""
  exit "$exit_code"
}
readarray -t limits < <(printf '%s' "$limit_json" | .venv-atlas/bin/python -c \
 'import json,sys; d=json.load(sys.stdin); print(d["deadline"]); print(d["reservation"]); print(d["deadline_sha256"]); print(d["reservation_sha256"]); print(d["soft_timeout_seconds"]); print(d["termination_grace_seconds"]); print(d["timeout_accounting_margin_seconds"]); print(d["hard_runtime_ceiling_seconds"])')
deadline_path=${limits[0]}; reservation_path=${limits[1]}; deadline_sha=${limits[2]}; reservation_sha=${limits[3]}
soft_timeout=${limits[4]}; termination_grace=${limits[5]}; timeout_margin=${limits[6]}; hard_runtime_ceiling=${limits[7]}
if (( soft_timeout <= 0 )); then
  outcome=resource_not_launched; exit_code=75
  JOB="$job" DEADLINE_PATH="$deadline_path" DEADLINE_SHA="$deadline_sha" \
  RESERVATION_PATH="$reservation_path" RESERVATION_SHA="$reservation_sha" \
  CONFIG_SHA="$config_sha" FREEZE_SHA="$freeze_sha" .venv-atlas/bin/python - <<'PY' | atomic_publish "$run_root/job_manifests/${job}.resource_stop.json"
import json,os
from datetime import datetime,timezone
print(json.dumps({"schema_version":"atlas_completion_continuation_resource_stop_v1","job":os.environ["JOB"],
 "reason":"shared_stage_deadline_exhausted","scoring_started":False,
 "stage_deadline_path":os.environ["DEADLINE_PATH"],"stage_deadline_sha256":os.environ["DEADLINE_SHA"],
 "budget_reservation_path":os.environ["RESERVATION_PATH"],"budget_reservation_sha256":os.environ["RESERVATION_SHA"],
 "config_sha256":os.environ["CONFIG_SHA"],"completion_bundle_sha256":os.environ["FREEZE_SHA"],
 "decision_promotion_allowed":False,"recorded_utc":datetime.now(timezone.utc).isoformat()},sort_keys=True,separators=(",",":")))
PY
  gpu=""; uuid=""
  exit "$exit_code"
fi
# A sibling may have selected a stage terminal after this process claimed a GPU.
# Recheck immediately before publishing a launch manifest or starting scoring.
terminal=$(stage_terminal_json || true)
if [[ -n "$terminal" && ! -e "$stage/$expected" ]]; then
  outcome=superseded_by_stage_stop; exit_code=0
  printf '%s\n' "$terminal" | JOB="$job" CONFIG_SHA="$config_sha" FREEZE_SHA="$freeze_sha" .venv-atlas/bin/python -c \
    'import json,os,sys; from datetime import datetime,timezone; d=json.load(sys.stdin); print(json.dumps({"schema_version":"atlas_completion_continuation_superseded_v1","job":os.environ["JOB"],"stage_terminal_state":d["state"],"stage_terminal_path":d["path"],"stage_terminal_sha256":d["sha256"],"scoring_started":False,"config_sha256":os.environ["CONFIG_SHA"],"completion_bundle_sha256":os.environ["FREEZE_SHA"],"decision_promotion_allowed":False,"recorded_utc":datetime.now(timezone.utc).isoformat()},sort_keys=True,separators=(",",":")))' \
    | atomic_publish "$run_root/job_manifests/${job}.superseded_stage.json"
  gpu=""; uuid=""
  exit 0
fi
command_json=$(printf '%s\n' "$*" | python -c 'import json,sys; print(json.dumps(sys.stdin.read().rstrip()))')
printf '{"schema_version":"atlas_completion_continuation_job_manifest_v1","job":"%s","pid":%d,"gpu_index":%d,"gpu_uuid":"%s","config_sha256":"%s","completion_bundle_sha256":"%s","started_utc":"%s","log":"%s","command":%s,"stage_deadline_path":"%s","stage_deadline_sha256":"%s","budget_reservation_path":"%s","budget_reservation_sha256":"%s","soft_timeout_seconds":%d,"termination_grace_seconds":%d,"timeout_accounting_margin_seconds":%d,"hard_runtime_ceiling_seconds":%d}\n' \
 "$job" "$$" "$gpu" "$uuid" "$config_sha" "$freeze_sha" "$(date -u +%FT%TZ)" "$log" "$command_json" "$deadline_path" "$deadline_sha" "$reservation_path" "$reservation_sha" "$soft_timeout" "$termination_grace" "$timeout_margin" "$hard_runtime_ceiling" | atomic_publish "$run_root/job_manifests/${job}.json"
scoring_started=true
echo "[$(date -u +%FT%TZ)] job=$job gpu=$gpu uuid=$uuid command=$*" | tee -a "$log"
set +e
process_started_utc=$(date -u +%Y-%m-%dT%H:%M:%S.%N%:z)
process_start_ns=$(.venv-atlas/bin/python -c 'import time; print(time.monotonic_ns())')
CUDA_VISIBLE_DEVICES="$gpu" MSAE_EXPECTED_GPU_UUID="$uuid" PYTHONHASHSEED=20260731 \
 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
 timeout --signal=INT --kill-after="${termination_grace}s" "$soft_timeout" "$@" >>"$log" 2>&1
exit_code=$?
process_end_ns=$(.venv-atlas/bin/python -c 'import time; print(time.monotonic_ns())')
process_ended_utc=$(date -u +%Y-%m-%dT%H:%M:%S.%N%:z)
process_elapsed_seconds=$(.venv-atlas/bin/python - "$process_start_ns" "$process_end_ns" <<'PY'
import sys
print(max(0.0,(int(sys.argv[2])-int(sys.argv[1]))/1e9))
PY
)
set -e
terminal_after=$(stage_terminal_json || true)
matching_launch_failure=false
if [[ -f "$run_root/LAUNCH_FAILURE.json" ]]; then
  matching_launch_failure=$(JOB="$job" CONFIG_SHA="$config_sha" FREEZE_SHA="$freeze_sha" \
    .venv-atlas/bin/python - "$run_root/LAUNCH_FAILURE.json" <<'PY'
import json,os,sys
try: row=json.load(open(sys.argv[1]))
except Exception: print("false")
else:
 print("true" if row.get("job_id")==os.environ["JOB"]
       and row.get("config_sha256")==os.environ["CONFIG_SHA"]
       and row.get("completion_bundle_sha256")==os.environ["FREEZE_SHA"] else "false")
PY
  )
fi
expected_exists=false; [[ -e "$stage/$expected" ]] && expected_exists=true
process_outcome=$(.venv-atlas/bin/python - "$exit_code" "$process_elapsed_seconds" "$soft_timeout" \
  "$expected_exists" "$([[ -n "$terminal_after" ]] && echo true || echo false)" "$matching_launch_failure" <<'PY'
import sys
sys.path.insert(0,"scripts")
from msa_completion_continuation_common import classify_supervised_exit
boolean=lambda value: value=="true"
print(classify_supervised_exit(
 exit_code=int(sys.argv[1]),process_elapsed_seconds=float(sys.argv[2]),
 soft_timeout_seconds=float(sys.argv[3]),expected_output_exists=boolean(sys.argv[4]),
 stage_terminal_exists=boolean(sys.argv[5]),matching_launch_failure_exists=boolean(sys.argv[6])))
PY
)
outcome=$process_outcome
if [[ "$outcome" == resource_timeout || "$outcome" == process_crash ]]; then
  [[ $exit_code -ne 0 ]] || exit_code=1
  publish_supervisor_record "$outcome"
elif [[ "$outcome" == technical_failure && $exit_code -eq 0 ]]; then
  exit_code=1
fi
exit "$exit_code"
