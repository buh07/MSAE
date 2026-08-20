#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv-atlas/bin/python"
RUN="$ROOT/scripts/known_mechanism_ioi_v1.py"
CONFIG="configs/known_mechanism_ioi_v1/run.json"
FREEZE="configs/known_mechanism_ioi_v1/FREEZE.json"
PREFIX="msae_known_ioi_v1"
OUT="results/known_mechanism_ioi_v1_20260809"
PROV="reports/provenance/known_mechanism_ioi_v1_run_20260809"
CANDIDATE_REVIEW="reports/adversarial/known_mechanism_ioi_v1_candidate_review.md"
FROZEN_REVIEW="reports/adversarial/known_mechanism_ioi_v1_frozen_review.md"
BINDING="reports/provenance/known_mechanism_ioi_v1_candidate/FROZEN_REVIEW_BINDING.json"

export HF_HOME="${HF_HOME:-/jumbo/lisp/f004ndc/huggingface}"
export TRANSFORMERS_CACHE="$HF_HOME/hub"
export HF_DATASETS_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTHONHASHSEED=20260814

[[ -f "$FREEZE" && -f "$CANDIDATE_REVIEW" && -f "$FROZEN_REVIEW" && -f "$BINDING" ]] || { echo "freeze and both reviews are required" >&2; exit 2; }
grep -q '^VERDICT: SHIP$' "$CANDIDATE_REVIEW" || { echo "candidate review is not SHIP" >&2; exit 2; }
grep -q '^VERDICT: SHIP$' "$FROZEN_REVIEW" || { echo "frozen review is not SHIP" >&2; exit 2; }
"$PY" - "$FREEZE" "$FROZEN_REVIEW" "$BINDING" <<'PY'
import hashlib,json,sys
from pathlib import Path
freeze,review,binding=map(Path,sys.argv[1:])
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
value=json.loads(binding.read_text())
assert value['status']=='SHIP' and value['freeze_sha256']==digest(freeze) and value['review_sha256']==digest(review)
PY

[[ ! -e "$OUT" && ! -e "$PROV" ]] || { echo "one-shot output/provenance namespace exists" >&2; exit 3; }
SESSIONS=(behavior_gpt2 behavior_pythia160 behavior_gemma2 patch_gpt2 patch_pythia160 patch_gemma2 confirmation_gpt2 confirmation_pythia160 confirmation_gemma2 behavior_gate patch_gate final)
for suffix in "${SESSIONS[@]}"; do
  tmux has-session -t "${PREFIX}_${suffix}" 2>/dev/null && { echo "session already exists: ${PREFIX}_${suffix}" >&2; exit 3; } || true
done

"$PY" "$RUN" preservation-verify --config "$CONFIG"
"$PY" "$RUN" cache-preflight --config "$CONFIG" >/dev/null
"$PY" "$RUN" preflight --config "$CONFIG"
"$PY" "$RUN" verify-freeze --config "$CONFIG"

mapfile -t GPU_ROWS < <(nvidia-smi --query-gpu=index,uuid,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits | awk -F, '$3+0 < 4096 {for(i=1;i<=5;i++)gsub(/^ +| +$/,"",$i); print $1"|"$2"|"$3"|"$4"|"$5}' | head -3)
[[ ${#GPU_ROWS[@]} -eq 3 ]] || { echo "need three GPUs below 4 GiB used; found ${#GPU_ROWS[@]}" >&2; exit 4; }
declare -a GPU_INDEX GPU_UUID
for row in "${GPU_ROWS[@]}"; do
  IFS='|' read -r idx uuid used total util <<<"$row"
  GPU_INDEX+=("$idx"); GPU_UUID+=("$uuid")
done
[[ $(printf '%s\n' "${GPU_UUID[@]}" | sort -u | wc -l) -eq 3 ]] || { echo "GPU UUID collision" >&2; exit 4; }

mkdir "$OUT"
mkdir -p "$PROV/logs"
"$PY" - "$CONFIG" "$FREEZE" "$PROV/launch_manifest.json" "${GPU_ROWS[@]}" <<'PY'
import datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
config,freeze,out,*rows=sys.argv[1:]
digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
gpus=[]
for row in rows:
    index,uuid,used,total,util=row.split('|')
    gpus.append({'physical_index':int(index),'uuid':uuid,'memory_used_mib':int(used),'memory_total_mib':int(total),'utilization_percent':int(util)})
actual={int(line.split(',')[0].strip()):line.split(',')[1].strip() for line in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader,nounits'],text=True).splitlines()}
assert all(actual[gpu['physical_index']]==gpu['uuid'] for gpu in gpus)
models=['gpt2','pythia160','gemma2']
payload={'schema_version':'known_mechanism_ioi_v1_launch','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'config':config,'config_sha256':digest(config),'freeze':freeze,'freeze_sha256':digest(freeze),'gpus':gpus,'assignments':[{'model':model,'physical_index':gpus[i]['physical_index'],'uuid':gpus[i]['uuid']} for i,model in enumerate(models)],'sessions_expected':12,'gpu_pipelines':3,'cpu_aggregators':3,'confirmation_firewall':True,'representation_methods':False,'optimization_jobs':False,'v6_2_unchanged':True,'v6_3_created':False}
fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as handle:
    json.dump(payload,handle,sort_keys=True,separators=(',',':'));handle.write('\n');handle.flush();os.fsync(handle.fileno())
PY

launch_gpu() {
  local suffix="$1" uuid="$2" command="$3"
  tmux new-session -d -s "${PREFIX}_${suffix}" "cd '$ROOT' && export HF_HOME='$HF_HOME' TRANSFORMERS_CACHE='$TRANSFORMERS_CACHE' HF_DATASETS_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONHASHSEED=20260814 CUDA_VISIBLE_DEVICES='$uuid' EXPECTED_GPU_UUID='$uuid'; $command > '$PROV/logs/${suffix}.log' 2>&1"
}
launch_cpu() {
  local suffix="$1" command="$2"
  tmux new-session -d -s "${PREFIX}_${suffix}" "cd '$ROOT' && export HF_HOME='$HF_HOME' TRANSFORMERS_CACHE='$TRANSFORMERS_CACHE' HF_DATASETS_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONHASHSEED=20260814 CUDA_VISIBLE_DEVICES=''; $command > '$PROV/logs/${suffix}.log' 2>&1"
}

MODELS=(gpt2 pythia160 gemma2)
for i in 0 1 2; do
  model="${MODELS[$i]}"; uuid="${GPU_UUID[$i]}"
  launch_gpu "behavior_${model}" "$uuid" "'$PY' '$RUN' behavior-worker --config '$CONFIG' --model '$model'"
  launch_gpu "patch_${model}" "$uuid" "'$PY' '$RUN' patch-worker --config '$CONFIG' --model '$model'"
  launch_gpu "confirmation_${model}" "$uuid" "'$PY' '$RUN' confirmation-worker --config '$CONFIG' --model '$model'"
done
launch_cpu behavior_gate "'$PY' '$RUN' behavior-gate --config '$CONFIG'"
launch_cpu patch_gate "'$PY' '$RUN' patch-gate --config '$CONFIG'"
launch_cpu final "'$PY' '$RUN' final --config '$CONFIG'"

sleep 3
"$PY" - "$PREFIX" "$PROV/launch_manifest.json" "$OUT" "$PROV/handoff_status.json" <<'PY'
import hashlib,json,os,subprocess,sys
from pathlib import Path
prefix,manifest,out,handoff=sys.argv[1:]
out=Path(out);handoff=Path(handoff)
try:
    text=subprocess.check_output(['tmux','list-sessions','-F','#{session_name}'],text=True)
except subprocess.CalledProcessError:
    text=''
live=sorted(name for name in text.splitlines() if name.startswith(prefix+'_'))
suffixes=['behavior_gpt2','behavior_pythia160','behavior_gemma2','patch_gpt2','patch_pythia160','patch_gemma2','confirmation_gpt2','confirmation_pythia160','confirmation_gemma2','behavior_gate','patch_gate','final']
clean={}
for suffix in suffixes:
    stage,*rest=suffix.split('_'); paths=[]
    if suffix=='behavior_gate': paths=[out/'gates'/'behavior'/'result.json']
    elif suffix=='patch_gate': paths=[out/'gates'/'patch'/'result.json']
    elif stage=='behavior': paths=[out/'development'/'behavior'/rest[0]/'COMPLETE.json']
    elif stage=='patch': paths=[out/'development'/'patch'/rest[0]/'COMPLETE.json',out/'development'/'patch'/rest[0]/'BLOCKED.json']
    elif stage=='confirmation': paths=[out/'confirmation'/rest[0]/'COMPLETE.json',out/'confirmation'/rest[0]/'BLOCKED.json']
    else: paths=[out/'final'/'result.json']
    clean[suffix]=[str(path) for path in paths if path.is_file()]
missing=[suffix for suffix in suffixes if f'{prefix}_{suffix}' not in live and not clean[suffix]]
if missing: raise SystemExit(f'missing live session or clean terminal: {missing}')
payload={'schema_version':'known_mechanism_ioi_v1_handoff','status':'RUNNING_OR_CLEANLY_TERMINATED','launch_manifest_sha256':hashlib.sha256(Path(manifest).read_bytes()).hexdigest(),'initial_live_sessions':live,'initial_session_count':len(live),'initial_clean_terminals':clean}
fd=os.open(handoff,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as handle:
    json.dump(payload,handle,sort_keys=True,separators=(',',':'));handle.write('\n');handle.flush();os.fsync(handle.fileno())
print(json.dumps({'status':payload['status'],'sessions':live,'clean_terminals':clean,'launch':json.load(open(manifest))},indent=2))
PY
