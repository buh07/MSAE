#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
PY="$ROOT/.venv-atlas/bin/python"
RUN="$ROOT/scripts/joint_controllability_benchmark_v4.py"
CFG="configs/joint_controllability_benchmark_v4/run.json"
PREFIX="msae_joint_control_v4"
LOG="$ROOT/reports/provenance/joint_controllability_benchmark_v4_run_20260808"
FREEZE="$ROOT/configs/joint_controllability_benchmark_v4/FREEZE.json"
REVIEW="$ROOT/reports/adversarial/joint_controllability_v4_candidate_review.md"
: "${HF_HOME:?}"; : "${TRANSFORMERS_CACHE:?}"; : "${HF_DATASETS_CACHE:?}"
[[ -f "$FREEZE" && -f "$REVIEW" ]] || { echo 'freeze/review absent' >&2; exit 5; }
grep -q '^VERDICT: SHIP$' "$REVIEW" || { echo 'candidate review not SHIP' >&2; exit 5; }
FSHA="$(sha256sum "$FREEZE" | awk '{print $1}')"
grep -q "freeze_sha256: $FSHA" "$REVIEW" || { echo 'review not freeze-bound' >&2; exit 5; }
PYTHONPATH="$ROOT/scripts" "$PY" "$RUN" preflight --config "$CFG"
mapfile -t GPU_ROWS < <(nvidia-smi --query-gpu=uuid,memory.free,memory.total,utilization.gpu --format=csv,noheader,nounits)
GPUS=()
for row in "${GPU_ROWS[@]}"; do
  IFS=',' read -r uuid free total util <<<"$row"
  uuid="${uuid// /}"; free="${free// /}"; total="${total// /}"; util="${util// /}"
  if (( free >= total-1024 && util <= 5 )); then GPUS+=("$uuid"); fi
done
((${#GPUS[@]} >= 7)) || { echo "need 7 free GPUs, found ${#GPUS[@]}" >&2; exit 3; }
SESSIONS=(task_gpt2 task_pythia task_gemma task_aggregate synthetic gpt2_l1 gpt2_l6 gpt2_l10 pythia_l8 gemma_l0 gemma_l12 gemma_l25 aggregate)
for suffix in "${SESSIONS[@]}"; do tmux has-session -t "${PREFIX}_${suffix}" 2>/dev/null && { echo "session exists: $suffix" >&2; exit 4; } || true; done
[[ ! -e "$LOG" ]] || { echo 'provenance namespace exists' >&2; exit 4; }
mkdir "$LOG"
COMMON="export HF_HOME='$HF_HOME' TRANSFORMERS_CACHE='$TRANSFORMERS_CACHE' HF_DATASETS_CACHE='$HF_DATASETS_CACHE' HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONHASHSEED=20260809 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; cd '$ROOT'; export PYTHONPATH='$ROOT/scripts';"
launch_gpu() { local suffix="$1" gpu="$2" command="$3"; tmux new-session -d -s "${PREFIX}_${suffix}" "bash -lc \"export CUDA_VISIBLE_DEVICES='$gpu'; $COMMON $command >>'$LOG/$suffix.log' 2>&1\""; }
launch_cpu() { local suffix="$1" command="$2"; tmux new-session -d -s "${PREFIX}_${suffix}" "bash -lc \"export CUDA_VISIBLE_DEVICES=''; $COMMON $command >>'$LOG/$suffix.log' 2>&1\""; }
# Opened-development gates run on GPUs 0-2. Fresh-test workers start as CPU waiters and load only after PASS.
launch_gpu task_gpt2 "${GPUS[0]}" "'$PY' '$RUN' task-gate-worker --config '$CFG' --model gpt2"
launch_gpu task_pythia "${GPUS[1]}" "'$PY' '$RUN' task-gate-worker --config '$CFG' --model pythia160"
launch_gpu task_gemma "${GPUS[2]}" "'$PY' '$RUN' task-gate-worker --config '$CFG' --model gemma2"
launch_cpu task_aggregate "'$PY' '$RUN' task-gate-aggregate --config '$CFG'"
launch_cpu synthetic "'$PY' '$RUN' synthetic --config '$CFG'"
launch_gpu gpt2_l1 "${GPUS[0]}" "'$PY' '$RUN' worker --config '$CFG' --model gpt2 --layer 1"
launch_gpu gpt2_l6 "${GPUS[1]}" "'$PY' '$RUN' worker --config '$CFG' --model gpt2 --layer 6"
launch_gpu gpt2_l10 "${GPUS[2]}" "'$PY' '$RUN' worker --config '$CFG' --model gpt2 --layer 10"
launch_gpu pythia_l8 "${GPUS[3]}" "'$PY' '$RUN' worker --config '$CFG' --model pythia160 --layer 8"
launch_gpu gemma_l0 "${GPUS[4]}" "'$PY' '$RUN' worker --config '$CFG' --model gemma2 --layer 0"
launch_gpu gemma_l12 "${GPUS[5]}" "'$PY' '$RUN' worker --config '$CFG' --model gemma2 --layer 12"
launch_gpu gemma_l25 "${GPUS[6]}" "'$PY' '$RUN' worker --config '$CFG' --model gemma2 --layer 25"
launch_cpu aggregate "'$PY' '$RUN' aggregate --config '$CFG'"
"$PY" - "$LOG/launch_manifest.json" "$FSHA" "${GPUS[@]:0:7}" <<'PY'
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
path=Path(sys.argv[1]); freeze=sys.argv[2]; gpus=sys.argv[3:]
sessions=subprocess.run(['tmux','list-sessions','-F','#{session_name}'],text=True,capture_output=True,check=True).stdout.splitlines()
record={'schema_version':'joint_control_v4_launch','freeze_sha256':freeze,'gpu_uuids':gpus,'sessions':sorted(s for s in sessions if s.startswith('msae_joint_control_v4_')),'config_sha256':hashlib.sha256(Path('configs/joint_controllability_benchmark_v4/run.json').read_bytes()).hexdigest(),'launched_unix':time.time(),'launcher_pid':os.getpid(),'development_gate_precedes_fresh_test_model_load':True,'new_training':False}
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f: json.dump(record,f,sort_keys=True,separators=(',',':')); f.write('\n')
print(json.dumps(record,indent=2))
PY
tmux list-sessions -F '#{session_name} #{session_attached} #{session_windows}' | grep "^${PREFIX}_"
