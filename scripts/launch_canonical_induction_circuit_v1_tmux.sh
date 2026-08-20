#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
PY="$ROOT/.venv-atlas/bin/python"; RUN="$ROOT/scripts/canonical_induction_circuit_v1.py"
CONFIG="configs/canonical_induction_circuit_v1/run.json"; FREEZE="configs/canonical_induction_circuit_v1/FREEZE.json"
PREFIX="msae_induction_v1"; OUT="results/canonical_induction_circuit_v1_20260809"; PROV="reports/provenance/canonical_induction_circuit_v1_run_20260809"
CANDIDATE="reports/adversarial/canonical_induction_circuit_v1_candidate_review.md"; FROZEN="reports/adversarial/canonical_induction_circuit_v1_frozen_review.md"; BINDING="reports/provenance/canonical_induction_circuit_v1_candidate/FROZEN_REVIEW_BINDING.json"

export CUBLAS_WORKSPACE_CONFIG=:4096:8
export HF_HOME="${HF_HOME:-/jumbo/lisp/f004ndc/huggingface}" TRANSFORMERS_CACHE="${HF_HOME:-/jumbo/lisp/f004ndc/huggingface}/hub"
export HF_DATASETS_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONHASHSEED=20260815

[[ -f "$FREEZE" && -f "$CANDIDATE" && -f "$FROZEN" && -f "$BINDING" ]] || { echo "freeze and reviews required" >&2; exit 2; }
[[ "$(head -n 1 "$CANDIDATE")" == "VERDICT: SHIP" && "$(head -n 1 "$FROZEN")" == "VERDICT: SHIP" ]] || { echo "first-line SHIP verdicts required" >&2; exit 2; }
"$PY" "$RUN" review-binding --config "$CONFIG"
[[ ! -e "$OUT" && ! -e "$PROV" ]] || { echo "one-shot namespace exists" >&2; exit 3; }
SESSIONS=(development development_gate confirmation final)
for suffix in "${SESSIONS[@]}"; do tmux has-session -t "${PREFIX}_${suffix}" 2>/dev/null && { echo "session collision" >&2; exit 3; } || true; done
"$PY" "$RUN" preservation-verify --config "$CONFIG"; "$PY" "$RUN" cache-preflight --config "$CONFIG"; "$PY" "$RUN" preflight --pre-gate --config "$CONFIG"; "$PY" "$RUN" verify-freeze --pre-gate --config "$CONFIG"

GPU_ROW="$(nvidia-smi --query-gpu=index,uuid,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits | awk -F, '$3+0 < 4096 {for(i=1;i<=5;i++)gsub(/^ +| +$/,"",$i); print $1"|"$2"|"$3"|"$4"|"$5; exit}')"
[[ -n "$GPU_ROW" ]] || { echo "no GPU below 4 GiB" >&2; exit 4; }
IFS='|' read -r GPU_INDEX GPU_UUID GPU_USED GPU_TOTAL GPU_UTIL <<<"$GPU_ROW"
mkdir "$OUT"; mkdir -p "$PROV/logs"
"$PY" - "$CONFIG" "$FREEZE" "$PROV/launch_manifest.json" "$GPU_ROW" <<'PY'
import datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
config,freeze,out,row=sys.argv[1:]; index,uuid,used,total,util=row.split('|'); sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
actual={int(x.split(',')[0].strip()):x.split(',')[1].strip() for x in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader,nounits'],text=True).splitlines()}
if actual.get(int(index)) != uuid: raise SystemExit('selected GPU UUID mapping changed')
payload={'schema_version':'canonical_induction_circuit_v1_launch','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'config':config,'config_sha256':sha(config),'freeze':freeze,'freeze_sha256':sha(freeze),'gpu':{'physical_index':int(index),'uuid':uuid,'memory_used_mib':int(used),'memory_total_mib':int(total),'utilization_percent':int(util)},'sessions_expected':4,'cublas_workspace_config':os.environ['CUBLAS_WORKSPACE_CONFIG'],'exact_repeated_inference_required':True,'confirmation_firewall':True,'technical_positive_control_only':True,'single_model':True,'general_method_claim':False,'representation_methods':False,'optimization_jobs':False,'ioi_v1_unchanged':True}
fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f: json.dump(payload,f,sort_keys=True,separators=(',',':'));f.write('\n');f.flush();os.fsync(f.fileno())
PY

gpu_job() { local suffix="$1" command="$2" uuid="$GPU_UUID"; tmux new-session -d -s "${PREFIX}_${suffix}" "cd '$ROOT' && export CUBLAS_WORKSPACE_CONFIG=:4096:8 HF_HOME='$HF_HOME' TRANSFORMERS_CACHE='$TRANSFORMERS_CACHE' HF_DATASETS_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONHASHSEED=20260815 CUDA_VISIBLE_DEVICES='$uuid' EXPECTED_GPU_UUID='$uuid'; $command > '$PROV/logs/${suffix}.log' 2>&1"; }
cpu_job() { local suffix="$1" command="$2"; tmux new-session -d -s "${PREFIX}_${suffix}" "cd '$ROOT' && export CUBLAS_WORKSPACE_CONFIG=:4096:8 HF_HOME='$HF_HOME' TRANSFORMERS_CACHE='$TRANSFORMERS_CACHE' HF_DATASETS_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONHASHSEED=20260815 CUDA_VISIBLE_DEVICES=''; $command > '$PROV/logs/${suffix}.log' 2>&1"; }

gpu_job development "'$PY' '$RUN' worker --config '$CONFIG' --stage development"
gpu_job confirmation "'$PY' '$RUN' worker --config '$CONFIG' --stage confirmation"
cpu_job development_gate "'$PY' '$RUN' development-gate --config '$CONFIG'"
cpu_job final "'$PY' '$RUN' final --config '$CONFIG'"
sleep 3
"$PY" - "$PREFIX" "$PROV/launch_manifest.json" "$OUT" "$PROV/handoff_status.json" <<'PY'
import hashlib,json,os,subprocess,sys
from pathlib import Path
prefix,manifest,out,handoff=sys.argv[1:];out=Path(out)
try:text=subprocess.check_output(['tmux','list-sessions','-F','#{session_name}'],text=True)
except subprocess.CalledProcessError:text=''
live=sorted(x for x in text.splitlines() if x.startswith(prefix+'_')); suffixes=['development','development_gate','confirmation','final']; clean={}
for suffix in suffixes:
 paths=[out/'development'/'COMPLETE.json'] if suffix=='development' else ([out/'development_gate'/'result.json'] if suffix=='development_gate' else ([out/'confirmation'/'COMPLETE.json',out/'confirmation'/'BLOCKED.json'] if suffix=='confirmation' else [out/'final'/'result.json']))
 clean[suffix]=[str(p) for p in paths if p.is_file()]
missing=[s for s in suffixes if f'{prefix}_{s}' not in live and not clean[s]]
if missing:raise SystemExit(f'missing live session or clean terminal: {missing}')
payload={'schema_version':'canonical_induction_circuit_v1_handoff','status':'RUNNING_OR_CLEANLY_TERMINATED','launch_manifest_sha256':hashlib.sha256(Path(manifest).read_bytes()).hexdigest(),'initial_live_sessions':live,'initial_clean_terminals':clean}
fd=os.open(handoff,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f:json.dump(payload,f,sort_keys=True,separators=(',',':'));f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps({'status':payload['status'],'sessions':live,'clean_terminals':clean,'launch':json.load(open(manifest))},indent=2))
PY
