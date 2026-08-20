#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv-atlas/bin/python"
RUN="$ROOT/scripts/behavioral_endpoint_v6_2.py"
CONFIG="configs/behavioral_endpoint_v6_2/run.json"
FREEZE="configs/behavioral_endpoint_v6_2/FREEZE.json"
PREFIX="msae_behavior_v6_2"
OUT="results/behavioral_endpoint_v6_2_20260809"
PROV="reports/provenance/behavioral_endpoint_v6_2_run_20260809"
CANDIDATE_REVIEW="reports/adversarial/behavioral_endpoint_v6_2_candidate_review.md"
FROZEN_REVIEW="reports/adversarial/behavioral_endpoint_v6_2_frozen_review.md"
REVIEW_BINDING="reports/provenance/behavioral_endpoint_v6_2_candidate/FROZEN_REVIEW_BINDING.json"

export HF_HOME="${HF_HOME:-/jumbo/lisp/f004ndc/huggingface}"
export TRANSFORMERS_CACHE="$HF_HOME/hub"
export HF_DATASETS_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTHONHASHSEED=20260811

[[ -f "$FREEZE" && -f "$CANDIDATE_REVIEW" && -f "$FROZEN_REVIEW" && -f "$REVIEW_BINDING" ]] || {
  echo "freeze and both SHIP reviews are required" >&2; exit 2;
}
grep -q '^VERDICT: SHIP$' "$CANDIDATE_REVIEW" || { echo "candidate review is not SHIP" >&2; exit 2; }
grep -q '^VERDICT: SHIP$' "$FROZEN_REVIEW" || { echo "frozen review is not SHIP" >&2; exit 2; }
"$PY" - "$FREEZE" "$FROZEN_REVIEW" "$REVIEW_BINDING" <<'PY'
import hashlib,json,sys
from pathlib import Path
freeze,review,binding=map(Path,sys.argv[1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
x=json.loads(binding.read_text())
assert x['status']=='SHIP' and x['freeze_sha256']==sha(freeze) and x['review_sha256']==sha(review)
PY

[[ ! -e "$OUT" && ! -e "$PROV" ]] || { echo "one-shot output/provenance namespace exists" >&2; exit 3; }
SESSIONS=(dev_retrieval_gpt2 dev_retrieval_pythia160 dev_retrieval_gemma2 dev_agreement_gpt2 dev_agreement_pythia160 dev_agreement_gemma2 confirm_retrieval_gpt2 confirm_retrieval_pythia160 confirm_retrieval_gemma2 confirm_agreement_gpt2 confirm_agreement_pythia160 confirm_agreement_gemma2 gate_retrieval gate_agreement final)
for suffix in "${SESSIONS[@]}"; do
  tmux has-session -t "${PREFIX}_${suffix}" 2>/dev/null && { echo "session already exists: ${PREFIX}_${suffix}" >&2; exit 3; } || true
done

"$PY" "$RUN" preservation-verify --config "$CONFIG"
"$PY" "$RUN" cache-preflight --config "$CONFIG" >/dev/null
"$PY" "$RUN" preflight --config "$CONFIG"
"$PY" "$RUN" verify-freeze --config "$CONFIG"

mapfile -t GPU_ROWS < <(nvidia-smi --query-gpu=index,uuid,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits | awk -F, '$3+0 < 4096 {for(i=1;i<=5;i++)gsub(/^ +| +$/,"",$i); print $1"|"$2"|"$3"|"$4"|"$5}' | head -6)
[[ ${#GPU_ROWS[@]} -eq 6 ]] || { echo "need six GPUs with less than 4 GiB used; found ${#GPU_ROWS[@]}" >&2; exit 4; }
declare -a GPU_INDEX GPU_UUID
for row in "${GPU_ROWS[@]}"; do
  IFS='|' read -r idx uuid used total util <<<"$row"
  GPU_INDEX+=("$idx"); GPU_UUID+=("$uuid")
done
[[ $(printf '%s\n' "${GPU_UUID[@]}" | sort -u | wc -l) -eq 6 ]] || { echo "GPU UUID collision" >&2; exit 4; }

mkdir "$OUT"
mkdir -p "$PROV/logs"
"$PY" - "$CONFIG" "$FREEZE" "$PROV/launch_manifest.json" "${GPU_ROWS[@]}" <<'PY'
import datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
config,freeze,out,*rows=sys.argv[1:]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
gpu=[]
for row in rows:
    idx,uuid,used,total,util=row.split('|')
    gpu.append({'physical_index':int(idx),'uuid':uuid,'memory_used_mib':int(used),'memory_total_mib':int(total),'utilization_percent':int(util)})
query=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader,nounits'],text=True).splitlines()
actual={int(x.split(',')[0].strip()):x.split(',')[1].strip() for x in query}
assert all(actual[x['physical_index']]==x['uuid'] for x in gpu)
pairs=[('retrieval','gpt2'),('retrieval','pythia160'),('retrieval','gemma2'),('agreement','gpt2'),('agreement','pythia160'),('agreement','gemma2')]
assignments=[{'endpoint':e,'model':m,'physical_index':gpu[i]['physical_index'],'uuid':gpu[i]['uuid']} for i,(e,m) in enumerate(pairs)]
payload={'schema_version':'behavioral_endpoint_v6_2_launch','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'config':config,'config_sha256':sha(config),'freeze':freeze,'freeze_sha256':sha(freeze),'gpus':gpu,'assignments':assignments,'sessions_expected':15,'development_workers':6,'confirmation_waiters':6,'cpu_gates':3,'confirmation_firewall':True,'new_training':False,'representation_methods':False,'v5_unchanged':True,'failed_v6_1_preserved':True,'technical_execution_repair':True}
fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f:json.dump(payload,f,sort_keys=True,separators=(',',':'));f.write('\n')
PY

launch_gpu() {
  local suffix="$1" uuid="$2" command="$3"
  tmux new-session -d -s "${PREFIX}_${suffix}" "cd '$ROOT' && export HF_HOME='$HF_HOME' TRANSFORMERS_CACHE='$TRANSFORMERS_CACHE' HF_DATASETS_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONHASHSEED=20260811 CUDA_VISIBLE_DEVICES='$uuid' EXPECTED_GPU_UUID='$uuid'; $command > '$PROV/logs/${suffix}.log' 2>&1"
}
launch_cpu() {
  local suffix="$1" command="$2"
  tmux new-session -d -s "${PREFIX}_${suffix}" "cd '$ROOT' && export HF_HOME='$HF_HOME' TRANSFORMERS_CACHE='$TRANSFORMERS_CACHE' HF_DATASETS_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONHASHSEED=20260811 CUDA_VISIBLE_DEVICES=''; $command > '$PROV/logs/${suffix}.log' 2>&1"
}

ENDPOINT=(retrieval retrieval retrieval agreement agreement agreement)
MODEL=(gpt2 pythia160 gemma2 gpt2 pythia160 gemma2)
for i in 0 1 2 3 4 5; do
  endpoint="${ENDPOINT[$i]}"; model="${MODEL[$i]}"; uuid="${GPU_UUID[$i]}"
  launch_gpu "dev_${endpoint}_${model}" "$uuid" "'$PY' '$RUN' worker --config '$CONFIG' --endpoint '$endpoint' --model '$model' --stage development"
  # This process is a CPU-only waiter until the endpoint gate passes for its own model.
  launch_gpu "confirm_${endpoint}_${model}" "$uuid" "'$PY' '$RUN' worker --config '$CONFIG' --endpoint '$endpoint' --model '$model' --stage confirmation"
done
launch_cpu gate_retrieval "'$PY' '$RUN' development-gate --config '$CONFIG' --endpoint retrieval"
launch_cpu gate_agreement "'$PY' '$RUN' development-gate --config '$CONFIG' --endpoint agreement"
launch_cpu final "'$PY' '$RUN' final --config '$CONFIG'"

sleep 2
"$PY" - "$PREFIX" "$PROV/launch_manifest.json" "$OUT" "$PROV/handoff_status.json" <<'PY'
import hashlib,json,os,subprocess,sys
from pathlib import Path
prefix,manifest,out,handoff=sys.argv[1:];out=Path(out);handoff=Path(handoff)
text=subprocess.check_output(['tmux','list-sessions','-F','#{session_name}'],text=True)
live=sorted(x for x in text.splitlines() if x.startswith(prefix+'_'))
suffixes=['dev_retrieval_gpt2','dev_retrieval_pythia160','dev_retrieval_gemma2','dev_agreement_gpt2','dev_agreement_pythia160','dev_agreement_gemma2','confirm_retrieval_gpt2','confirm_retrieval_pythia160','confirm_retrieval_gemma2','confirm_agreement_gpt2','confirm_agreement_pythia160','confirm_agreement_gemma2','gate_retrieval','gate_agreement','final']
clean={}
for suffix in suffixes:
    parts=suffix.split('_');paths=[]
    if parts[0]=='dev':paths=[out/'development'/parts[1]/parts[2]/'COMPLETE.json']
    elif parts[0]=='confirm':paths=[out/'confirmation'/parts[1]/parts[2]/'COMPLETE.json',out/'confirmation'/parts[1]/parts[2]/'BLOCKED.json']
    elif parts[0]=='gate':paths=[out/'development_gate'/parts[1]/'result.json']
    else:paths=[out/'final'/'result.json']
    clean[suffix]=[str(x) for x in paths if x.is_file()]
missing=[s for s in suffixes if f'{prefix}_{s}' not in live and not clean[s]]
if missing:raise SystemExit(f'missing live session or clean terminal: {missing}')
p=json.load(open(manifest));payload={'schema_version':'behavioral_endpoint_v6_2_handoff','status':'RUNNING_OR_CLEANLY_TERMINATED','launch_manifest_sha256':hashlib.sha256(Path(manifest).read_bytes()).hexdigest(),'initial_live_sessions':live,'initial_session_count':len(live),'initial_clean_terminals':clean}
fd=os.open(handoff,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f:
    json.dump(payload,f,sort_keys=True,separators=(',',':'));f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps({'status':'RUNNING_OR_CLEANLY_TERMINATED','sessions':live,'clean_terminals':clean,'gpus':p['gpus'],'assignments':p['assignments']},indent=2))
PY
