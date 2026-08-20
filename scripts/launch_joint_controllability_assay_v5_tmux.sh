#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
CONFIG="configs/joint_controllability_assay_v5/run.json"
PY="$ROOT/.venv-atlas/bin/python"
PREFIX="msae_joint_control_v5"
OUT="results/joint_controllability_assay_v5_20260808"
PROV="reports/provenance/joint_controllability_assay_v5_run_20260808"
FREEZE="configs/joint_controllability_assay_v5/FREEZE.json"
export HF_HOME="${HF_HOME:-/jumbo/lisp/f004ndc/huggingface}"
export TRANSFORMERS_CACHE="$HF_HOME/hub" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONHASHSEED=0
[[ ! -e "$OUT" && ! -e "$PROV" ]] || { echo "one-shot namespace exists" >&2; exit 1; }
"$PY" scripts/joint_controllability_assay_v5.py preservation-verify --config "$CONFIG"
"$PY" scripts/joint_controllability_assay_v5.py cache-preflight --config "$CONFIG" >/dev/null
"$PY" scripts/joint_controllability_assay_v5.py preflight --config "$CONFIG"
"$PY" scripts/joint_controllability_assay_v5.py verify-freeze --config "$CONFIG"
mapfile -t FREE_GPU_ROWS < <(nvidia-smi --query-gpu=index,uuid,memory.used --format=csv,noheader,nounits | awk -F, '$3+0 < 4096 {gsub(/ /,"",$1);gsub(/ /,"",$2); print $1 "|" $2}' | head -3)
[[ ${#FREE_GPU_ROWS[@]} -eq 3 ]] || { echo "need three GPUs with <4 GiB used" >&2; exit 1; }
FREE_GPUS=(); FREE_UUIDS=(); for row in "${FREE_GPU_ROWS[@]}"; do FREE_GPUS+=("${row%%|*}"); FREE_UUIDS+=("${row#*|}"); done
mkdir "$OUT"
mkdir -p "$PROV/logs"
"$PY" - "$CONFIG" "$FREEZE" "$PROV/launch_manifest.json" "${FREE_GPU_ROWS[@]}" <<'PY'
import datetime,hashlib,json,subprocess,sys
from pathlib import Path
config,freeze,out,*gpu_rows=sys.argv[1:]
gpus=[x.split('|',1)[0] for x in gpu_rows];requested={x.split('|',1)[0]:x.split('|',1)[1] for x in gpu_rows}
def sh(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
q=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,memory.used,memory.total','--format=csv,noheader'],text=True).splitlines()
records=[]
for g in gpus:
 line=next(x for x in q if x.split(',')[0].strip()==g);parts=[x.strip() for x in line.split(',')];assert requested[g]==parts[1];records.append({'physical_index':int(parts[0]),'uuid':parts[1],'name':parts[2],'memory_used':parts[3],'memory_total':parts[4]})
assignments=[{'model':m,'physical_index':records[i]['physical_index'],'uuid':records[i]['uuid']} for i,m in enumerate(['gpt2','pythia160','gemma2'])]
p={'schema_version':'joint_control_assay_v5_launch','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'config':config,'config_sha256':sh(config),'freeze':freeze,'freeze_sha256':sh(freeze),'gpus':records,'assignments':assignments,'stages':['development workers','development model-specific gate','eligible-only confirmation workers','directional final aggregate'],'no_training':True,'no_representation_methods':True}
Path(out).write_text(json.dumps(p,sort_keys=True,separators=(',',':'))+'\n')
PY
launch() { local name="$1" uuid="$2" cmd="$3"; tmux new-session -d -s "${PREFIX}_${name}" "cd '$ROOT' && export HF_HOME='$HF_HOME' TRANSFORMERS_CACHE='$TRANSFORMERS_CACHE' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONHASHSEED=0 CUDA_VISIBLE_DEVICES='$uuid' EXPECTED_GPU_UUID='$uuid'; $cmd > '$PROV/logs/${name}.log' 2>&1"; }
for i in 0 1 2; do
  model=(gpt2 pythia160 gemma2); m="${model[$i]}"; g="${FREE_UUIDS[$i]}"
  launch "dev_${m}" "$g" "'$PY' scripts/joint_controllability_assay_v5.py worker --config '$CONFIG' --model '$m' --split development"
  launch "confirm_${m}" "$g" "'$PY' scripts/joint_controllability_assay_v5.py worker --config '$CONFIG' --model '$m' --split confirmation"
done
launch "development_gate" "" "CUDA_VISIBLE_DEVICES='' '$PY' scripts/joint_controllability_assay_v5.py development-aggregate --config '$CONFIG'"
launch "final" "" "CUDA_VISIBLE_DEVICES='' '$PY' scripts/joint_controllability_assay_v5.py final-aggregate --config '$CONFIG'"
sleep 2
"$PY" - "$PREFIX" "$PROV/launch_manifest.json" <<'PY'
import json,subprocess,sys
prefix,manifest=sys.argv[1:]
text=subprocess.check_output(['tmux','list-sessions','-F','#{session_name}'],text=True)
live=sorted(x for x in text.splitlines() if x.startswith(prefix+'_'))
p=json.load(open(manifest));p['initial_live_sessions']=live;p['initial_session_count']=len(live)
open(manifest,'w').write(json.dumps(p,sort_keys=True,separators=(',',':'))+'\n')
if len(live)!=8:raise SystemExit(f'expected 8 initial sessions, got {live}')
print(json.dumps({'status':'RUNNING','sessions':live,'gpus':p['gpus']},indent=2))
PY
