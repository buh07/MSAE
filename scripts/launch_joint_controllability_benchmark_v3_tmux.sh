#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)";cd "$ROOT"
PY="$ROOT/.venv-atlas/bin/python";RUN="$ROOT/scripts/joint_controllability_benchmark_v3.py";CFG="configs/joint_controllability_benchmark_v3/run.json";PREFIX="msae_joint_control_v3";LOG="$ROOT/reports/provenance/joint_controllability_benchmark_v3";mkdir -p "$LOG"
: "${HF_HOME:?}";: "${TRANSFORMERS_CACHE:?}";: "${HF_DATASETS_CACHE:?}"
FREEZE="$ROOT/configs/joint_controllability_benchmark_v3/FREEZE.json";REVIEW="$ROOT/reports/adversarial/joint_controllability_v3_candidate_review.md"
[[ -f "$FREEZE" && -f "$REVIEW" ]] || { echo 'freeze/review absent' >&2;exit 5; }
grep -q '^VERDICT: SHIP$' "$REVIEW" || { echo 'candidate review not SHIP' >&2;exit 5; }
FSHA="$(sha256sum "$FREEZE"|awk '{print $1}')";grep -q "freeze_sha256: $FSHA" "$REVIEW" || { echo 'review not freeze-bound' >&2;exit 5; }
PYTHONPATH="$ROOT/scripts" "$PY" "$RUN" preflight --config "$CFG"
mapfile -t ROWS < <(nvidia-smi --query-gpu=uuid,memory.free,memory.total,utilization.gpu --format=csv,noheader,nounits)
GPUS=();for row in "${ROWS[@]}";do IFS=',' read -r u f t z <<<"$row";u="${u// /}";f="${f// /}";t="${t// /}";z="${z// /}";if ((f>=t-1024&&z<=5));then GPUS+=("$u");fi;done
((${#GPUS[@]}>=7))||{ echo "need 7 free GPUs, found ${#GPUS[@]}" >&2;exit 3; }
SUFFIX=(gpt2_l1 gpt2_l6 gpt2_l10 pythia_l8 gemma_l0 gemma_l12 gemma_l25 synthetic aggregate)
for s in "${SUFFIX[@]}";do tmux has-session -t "${PREFIX}_${s}" 2>/dev/null&&{ echo "session exists $s" >&2;exit 4; }||true;done
COMMON="export HF_HOME='$HF_HOME' TRANSFORMERS_CACHE='$TRANSFORMERS_CACHE' HF_DATASETS_CACHE='$HF_DATASETS_CACHE' HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONHASHSEED=20260808 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1;cd '$ROOT';export PYTHONPATH='$ROOT/scripts';"
launch(){ local s="$1" g="$2" c="$3";tmux new-session -d -s "${PREFIX}_${s}" "bash -lc \"export CUDA_VISIBLE_DEVICES='$g';$COMMON $c >>'$LOG/$s.log' 2>&1\""; }
tmux new-session -d -s "${PREFIX}_synthetic" "bash -lc \"export CUDA_VISIBLE_DEVICES='';$COMMON '$PY' '$RUN' synthetic --config '$CFG' >>'$LOG/synthetic.log' 2>&1\""
launch gpt2_l1 "${GPUS[0]}" "'$PY' '$RUN' worker --config '$CFG' --model gpt2 --layer 1"
launch gpt2_l6 "${GPUS[1]}" "'$PY' '$RUN' worker --config '$CFG' --model gpt2 --layer 6"
launch gpt2_l10 "${GPUS[2]}" "'$PY' '$RUN' worker --config '$CFG' --model gpt2 --layer 10"
launch pythia_l8 "${GPUS[3]}" "'$PY' '$RUN' worker --config '$CFG' --model pythia160 --layer 8"
launch gemma_l0 "${GPUS[4]}" "'$PY' '$RUN' worker --config '$CFG' --model gemma2 --layer 0"
launch gemma_l12 "${GPUS[5]}" "'$PY' '$RUN' worker --config '$CFG' --model gemma2 --layer 12"
launch gemma_l25 "${GPUS[6]}" "'$PY' '$RUN' worker --config '$CFG' --model gemma2 --layer 25"
tmux new-session -d -s "${PREFIX}_aggregate" "bash -lc \"export CUDA_VISIBLE_DEVICES='';$COMMON '$PY' '$RUN' aggregate --config '$CFG' >>'$LOG/aggregate.log' 2>&1\""
"$PY" - "$LOG/launch_manifest.json" "$FSHA" "${GPUS[@]:0:7}" <<'PY'
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
p=Path(sys.argv[1]);f=sys.argv[2];g=sys.argv[3:];sessions=subprocess.run(['tmux','list-sessions','-F','#{session_name}'],text=True,capture_output=True,check=True).stdout.splitlines()
x={'schema_version':'joint_control_v3_launch','freeze_sha256':f,'gpu_uuids':g,'sessions':sorted(s for s in sessions if s.startswith('msae_joint_control_v3_')),'config_sha256':hashlib.sha256(Path('configs/joint_controllability_benchmark_v3/run.json').read_bytes()).hexdigest(),'launched_unix':time.time(),'launcher_pid':os.getpid(),'positive_control_precedes_model_load':True}
fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as h:json.dump(x,h,sort_keys=True,separators=(',',':'));h.write('\n')
print(json.dumps(x,indent=2))
PY
tmux list-sessions -F '#{session_name} #{session_attached} #{session_windows}'|grep "^${PREFIX}_"
