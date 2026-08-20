#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv-atlas/bin/python"
RUNNER="$ROOT/scripts/proxy_control_benchmark_v2.py"
CONFIG="configs/proxy_control_benchmark_v2/run.json"
PREFIX="msae_proxy_control_v2"
LOGROOT="$ROOT/reports/provenance/proxy_control_benchmark_v2"
mkdir -p "$LOGROOT"
: "${HF_HOME:?HF_HOME must name the pinned local cache}"
: "${TRANSFORMERS_CACHE:?TRANSFORMERS_CACHE must name the pinned local cache}"
: "${HF_DATASETS_CACHE:?HF_DATASETS_CACHE must name the pinned local cache}"
FREEZE="$ROOT/configs/proxy_control_benchmark_v2/FREEZE.json"
REVIEW="$ROOT/reports/adversarial/proxy_control_benchmark_v2_candidate_review.md"
[[ -f "$FREEZE" && -f "$REVIEW" ]] || { echo "freeze or candidate review absent" >&2; exit 5; }
grep -q '^VERDICT: SHIP$' "$REVIEW" || { echo "candidate review did not SHIP" >&2; exit 5; }
FREEZE_SHA="$(sha256sum "$FREEZE" | awk '{print $1}')"
grep -q "freeze_sha256: $FREEZE_SHA" "$REVIEW" || { echo "candidate review not bound to freeze" >&2; exit 5; }
PYTHONPATH="$ROOT/scripts" "$PY" "$RUNNER" preflight --config "$CONFIG"

mapfile -t GPU_ROWS < <(nvidia-smi --query-gpu=index,uuid,memory.free,memory.total,utilization.gpu --format=csv,noheader,nounits)
UUIDS=()
for row in "${GPU_ROWS[@]}"; do
  IFS=',' read -r index uuid free total util <<<"$row"
  index="${index// /}"; uuid="${uuid// /}"; free="${free// /}"; total="${total// /}"; util="${util// /}"
  if (( free >= total - 1024 && util <= 5 )); then
    UUIDS+=("$uuid")
  else
    echo "skipping occupied GPU $index: $row" >&2
  fi
done
if [[ ${#UUIDS[@]} -lt 7 ]]; then echo "need seven free GPUs, found ${#UUIDS[@]}" >&2; exit 3; fi
UUIDS=("${UUIDS[@]:0:7}")
for suffix in p160_l1 p160_l6 p160_l10 p410_l2 p410_l12 p410_l22 qwen synthetic aggregate; do
  if tmux has-session -t "${PREFIX}_${suffix}" 2>/dev/null; then echo "session exists: ${PREFIX}_${suffix}" >&2; exit 4; fi
done
common="export HF_HOME='$HF_HOME' TRANSFORMERS_CACHE='$TRANSFORMERS_CACHE' HF_DATASETS_CACHE='$HF_DATASETS_CACHE' HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONHASHSEED=20260808 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; cd '$ROOT';"
launch_gpu() {
  local suffix="$1" gpu="$2" command="$3" log="$LOGROOT/$1.log"
  tmux new-session -d -s "${PREFIX}_${suffix}" "bash -lc \"export CUDA_VISIBLE_DEVICES='${gpu}'; ${common} ${command} >>'${log}' 2>&1\""
}
# Start the lightweight analytic gate on CPU first; workers create WAITING records and cannot
# model-load before PASS. Preserve every free GPU for the seven scientific worker sessions.
tmux new-session -d -s "${PREFIX}_synthetic" "bash -lc \"export CUDA_VISIBLE_DEVICES=''; ${common} '$PY' '$RUNNER' synthetic --config '$CONFIG' >>'$LOGROOT/synthetic.log' 2>&1\""
launch_gpu p160_l1  "${UUIDS[0]}" "'$PY' '$RUNNER' worker --config '$CONFIG' --model pythia160 --layer 1"
launch_gpu p160_l6  "${UUIDS[1]}" "'$PY' '$RUNNER' worker --config '$CONFIG' --model pythia160 --layer 6"
launch_gpu p160_l10 "${UUIDS[2]}" "'$PY' '$RUNNER' worker --config '$CONFIG' --model pythia160 --layer 10"
launch_gpu p410_l2  "${UUIDS[3]}" "'$PY' '$RUNNER' worker --config '$CONFIG' --model pythia410 --layer 2"
launch_gpu p410_l12 "${UUIDS[4]}" "'$PY' '$RUNNER' worker --config '$CONFIG' --model pythia410 --layer 12"
launch_gpu p410_l22 "${UUIDS[5]}" "'$PY' '$RUNNER' worker --config '$CONFIG' --model pythia410 --layer 22"
launch_gpu qwen      "${UUIDS[6]}" "for L in 2 12 22; do '$PY' '$RUNNER' worker --config '$CONFIG' --model qwen05 --layer \$L || exit \$?; done"
tmux new-session -d -s "${PREFIX}_aggregate" "bash -lc \"export CUDA_VISIBLE_DEVICES=''; ${common} '$PY' '$RUNNER' aggregate --config '$CONFIG' >>'$LOGROOT/aggregate.log' 2>&1\""

"$PY" - "$LOGROOT/launch_manifest.json" "$FREEZE_SHA" "${UUIDS[@]}" <<'PY'
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
path=Path(sys.argv[1]);freeze=sys.argv[2];uuids=sys.argv[3:]
sessions=subprocess.run(['tmux','list-sessions','-F','#{session_name}'],text=True,capture_output=True,check=True).stdout.splitlines()
payload={'schema_version':'proxy_control_benchmark_v2_launch_manifest','freeze_sha256':freeze,'gpu_uuids':uuids,
         'sessions':sorted(x for x in sessions if x.startswith('msae_proxy_control_v2_')),
         'config_sha256':hashlib.sha256(Path('configs/proxy_control_benchmark_v2/run.json').read_bytes()).hexdigest(),
         'launched_unix':time.time(),'launcher_pid':os.getpid(),'synthetic_gate_precedes_science':True}
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f:json.dump(payload,f,sort_keys=True,separators=(',',':'));f.write('\n')
print(json.dumps(payload,indent=2))
PY

tmux list-sessions -F '#{session_name} #{session_attached} #{session_windows}' | grep "^${PREFIX}_"
