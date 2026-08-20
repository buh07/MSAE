#!/usr/bin/env bash
set -uo pipefail
if [[ $# -lt 4 ]]; then echo "usage: $0 RUN_ROOT JOB LOG COMMAND..." >&2; exit 2; fi
run_root=$1; job=$2; log=$3; shift 3
.venv-atlas/bin/python - "$run_root" "$job" "$log" "$@" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,"scripts")
from msa_completion_common import ROOT
from msa_completion_continuation_common import RUN_ROOT
if Path(sys.argv[1]).resolve()!=RUN_ROOT.resolve():
    raise SystemExit("noncanonical continuation run root")
job,args=sys.argv[2],sys.argv[4:]
if Path(sys.argv[3]).resolve()!=(RUN_ROOT/"logs"/f"{job}.log").resolve():
    raise SystemExit("noncanonical continuation log path")
py=".venv-atlas/bin/python"
allowed={
 "baseline_rebind":[[py,"scripts/bind_msae_completion_continuation_baseline.py"]],
 "collector":[[py,"scripts/collect_msae_completion_continuation.py"],
              [py,"scripts/collect_msae_completion_continuation.py","--baseline-failed",
               str((RUN_ROOT/"baseline/FROZEN_EQUIVOCAL_STOP.json").relative_to(ROOT))],
              [py,"scripts/collect_msae_completion_continuation.py","--baseline-failed",
               str((RUN_ROOT/"job_manifests/baseline_rebind.terminal.json").relative_to(ROOT))]],
 "summarize":[[py,"scripts/summarize_msae_completion_continuation.py"]],
}
if job not in allowed or args not in allowed[job]:
    raise SystemExit(f"noncanonical CPU command for {job}: {args}")
PY
[[ $? -eq 0 ]] || exit $?
mkdir -p "$run_root/job_manifests" "$(dirname "$log")"
config_sha=$(sha256sum configs/atlas_completion_continuation/analysis.json | awk '{print $1}')
freeze_sha=$(python -c 'import json; print(json.load(open("configs/atlas_completion_continuation/freeze_record.json"))["bundle_sha256"])')
manifest="$run_root/job_manifests/${job}.json"; terminal="$run_root/job_manifests/${job}.terminal.json"
[[ ! -e "$manifest" && ! -e "$terminal" ]] || { echo "CPU job already launched: $job" >&2; exit 2; }
python - "$manifest" "$job" "$config_sha" "$freeze_sha" "$log" "$*" <<'PY'
import json,os,sys
from datetime import datetime,timezone
p,job,c,f,log,command=sys.argv[1:]
row={"schema_version":"atlas_completion_continuation_cpu_job_manifest_v1","job":job,"pid":os.getpid(),
"execution_device":"cpu","config_sha256":c,"completion_bundle_sha256":f,"started_utc":datetime.now(timezone.utc).isoformat(),"log":log,"command":command}
with open(p,"x") as h: json.dump(row,h,sort_keys=True,separators=(",",":")); h.write("\n")
PY
set +e
CUDA_VISIBLE_DEVICES="" PYTHONHASHSEED=20260731 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 "$@" >>"$log" 2>&1
status=$?
set -e
outcome=job_process_success; [[ $status -eq 0 ]] || outcome=technical_failure
python - "$terminal" "$job" "$status" "$outcome" "$config_sha" "$freeze_sha" <<'PY'
import json,sys
from datetime import datetime,timezone
p,job,status,outcome,c,f=sys.argv[1:]
row={"schema_version":"atlas_completion_continuation_job_terminal_v1","job":job,"exit_code":int(status),"outcome":outcome,"scoring_started":False,"gpu_index":None,"gpu_uuid":None,"config_sha256":c,"completion_bundle_sha256":f,"diagnostic_continuation_only":True,"decision_promotion_allowed":False,"ended_utc":datetime.now(timezone.utc).isoformat()}
with open(p,"x") as h: json.dump(row,h,sort_keys=True,separators=(",",":")); h.write("\n")
PY
exit "$status"
