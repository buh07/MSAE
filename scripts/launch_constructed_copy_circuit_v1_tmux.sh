#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
PY="$ROOT/.venv-atlas/bin/python"; RUN="$ROOT/scripts/constructed_copy_circuit_v1.py"; CONFIG="$ROOT/configs/constructed_copy_circuit_v1/run.json"
SESSION="msae_constructed_copy_circuit_v1"; OUT="$ROOT/results/constructed_copy_circuit_v1_20260809"; PROV="$ROOT/reports/provenance/constructed_copy_circuit_v1_run_20260809"
export CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONHASHSEED=20260831 TOKENIZERS_PARALLELISM=false

failure_handler() {
  local rc="${1:-1}"; trap - ERR INT TERM; set +e
  if [[ -f "$PROV/launch_manifest.json" ]]; then
    local token; token="$($PY -c 'import json,sys;print(json.load(open(sys.argv[1]))["launch_token"])' "$PROV/launch_manifest.json" 2>/dev/null)"
    [[ -n "$token" ]] && "$PY" "$RUN" reconcile --config "$CONFIG" --launch-token "$token" || true
  fi
  exit "$rc"
}

if [[ "${1:-}" == "--inner" ]]; then
  [[ $# -eq 6 ]] || { echo "inner args" >&2; exit 2; }
  INDEX="$2"; UUID="$3"; LOCK="$4"; BEFORE="$5"; NONCE="$6"
  mkdir -p "$(dirname "$LOCK")" "$PROV"; exec 9>"$LOCK"; flock -n 9 || { echo "GPU lock busy" >&2; exit 11; }
  trap 'failure_handler $?' ERR
  trap 'failure_handler 130' INT
  trap 'failure_handler 143' TERM
  ROW="$(nvidia-smi --id="$INDEX" --query-gpu=index,uuid,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits)"
  IFS=',' read -r IDX2 UUID2 USED TOTAL UTIL <<<"$ROW"; for x in IDX2 UUID2 USED TOTAL UTIL; do printf -v "$x" '%s' "${!x//[[:space:]]/}"; done
  PROCS="$(nvidia-smi --query-compute-apps=gpu_uuid --format=csv,noheader,nounits 2>/dev/null | grep -Fxc "$UUID" || true)"
  [[ "$IDX2" == "$INDEX" && "$UUID2" == "$UUID" && "$USED" -lt 2048 && "$UTIL" -lt 10 && "$PROCS" -eq 0 ]] || { echo "post-lock GPU recheck failed: $ROW procs=$PROCS" >&2; exit 12; }
  export CUDA_VISIBLE_DEVICES="$UUID" EXPECTED_GPU_UUID="$UUID"
  TOKEN="$($PY -c 'import secrets;print(secrets.token_hex(32))')"
  "$PY" - "$PROV/launch_manifest.json" "$CONFIG" "$INDEX" "$UUID" "$USED" "$TOTAL" "$UTIL" "$PROCS" "$LOCK" "$TOKEN" "$NONCE" "$$" "$BEFORE" <<'PY'
import hashlib,json,os,sys,time
from pathlib import Path
out,config,index,uuid,used,total,util,procs,lock,token,nonce,pid,before=sys.argv[1:]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
cfg=json.load(open(config)); root=Path.cwd()
bi,bu,bused,btotal,butil,bprocs=before.split('|')
payload={'schema_version':'constructed_copy_circuit_v1_launch','launch_token':token,'launcher_pid':int(pid),'started_ns':time.time_ns(),'config':str(Path(config).relative_to(root)),'config_sha256':sha(config),'freeze_sha256':sha(root/cfg['runtime']['freeze']),'review_binding_sha256':sha(root/cfg['runtime']['review_binding']),'protocol_lock_sha256':sha(root/cfg['runtime']['protocol_lock']),'v2_preservation_sha256':sha(root/cfg['runtime']['v2_preservation']),'gpu':{'physical_index':int(index),'uuid':uuid,'memory_used_mib':int(used),'memory_total_mib':int(total),'utilization_percent':int(util),'compute_processes':int(procs),'selection_nonce':nonce},'before_lock_evidence':{'physical_index':int(bi),'uuid':bu,'memory_used_mib':int(bused),'memory_total_mib':int(btotal),'utilization_percent':int(butil),'compute_processes':int(bprocs)},'gpu_lock_path':lock,'gpu_lock_inode':os.stat(lock).st_ino,'gpu_lock_held':True,'session':'msae_constructed_copy_circuit_v1','representation_methods_evaluated':False,'training_performed':False,'natural_prompt_assay':False}
Path(out).parent.mkdir(parents=True,exist_ok=True); fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f: json.dump(payload,f,sort_keys=True,separators=(',',':'));f.write('\n');f.flush();os.fsync(f.fileno())
PY
  "$PY" "$RUN" stage-controller --config "$CONFIG" --stage development --launch-token "$TOKEN"
  if [[ -f "$OUT/development/TECHNICAL_INVALID_STOP.json" ]]; then "$PY" "$RUN" final --config "$CONFIG" --launch-token "$TOKEN"; exit 0; fi
  "$PY" "$RUN" development-gate --config "$CONFIG" --launch-token "$TOKEN"
  if [[ -f "$OUT/development_gate/DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP.json" ]]; then "$PY" "$RUN" final --config "$CONFIG" --launch-token "$TOKEN"; exit 0; fi
  "$PY" "$RUN" authorize-confirmation --config "$CONFIG" --launch-token "$TOKEN"
  if [[ -f "$OUT/confirmation_authorization/CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP.json" || -f "$OUT/confirmation_authorization/CONFIRMATION_BLOCKED.json" ]]; then "$PY" "$RUN" final --config "$CONFIG" --launch-token "$TOKEN"; exit 0; fi
  "$PY" "$RUN" stage-controller --config "$CONFIG" --stage confirmation --launch-token "$TOKEN"
  "$PY" "$RUN" final --config "$CONFIG" --launch-token "$TOKEN"
  exit 0
fi

[[ $# -eq 0 ]] || { echo "no public args" >&2; exit 2; }
[[ -x "$PY" ]] || { echo "missing Python" >&2; exit 2; }
[[ ! -e "$OUT" && ! -e "$PROV" ]] || { echo "one-shot namespace exists" >&2; exit 3; }
tmux has-session -t "$SESSION" 2>/dev/null && { echo "tmux exists" >&2; exit 3; } || true
"$PY" "$RUN" candidate-preflight --config "$CONFIG"
"$PY" "$RUN" verify-freeze --config "$CONFIG"
"$PY" "$RUN" verify-review-binding --config "$CONFIG"
mapfile -t ROWS < <(nvidia-smi --query-gpu=index,uuid,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits | awk -F, '{for(i=1;i<=5;i++)gsub(/^ +| +$/,"",$i); if($3+0<2048 && $5+0<10) print $1"|"$2"|"$3"|"$4"|"$5}')
[[ ${#ROWS[@]} -gt 0 ]] || { echo "no free GPU" >&2; exit 4; }
mkdir -p /tmp/msae-gpu-locks; STARTED=0
for row in "${ROWS[@]}"; do
  IFS='|' read -r INDEX UUID USED TOTAL UTIL <<<"$row"; PROCS="$(nvidia-smi --query-compute-apps=gpu_uuid --format=csv,noheader,nounits 2>/dev/null | grep -Fxc "$UUID" || true)"; [[ "$PROCS" -eq 0 ]] || continue
  LOCK="/tmp/msae-gpu-locks/${UUID}.lock"; BEFORE="$INDEX|$UUID|$USED|$TOTAL|$UTIL|$PROCS"; NONCE="$($PY -c 'import secrets;print(secrets.token_hex(16))')"
  tmux new-session -d -s "$SESSION" "mkdir -p '$PROV'; exec '$0' --inner '$INDEX' '$UUID' '$LOCK' '$BEFORE' '$NONCE' > '$PROV/launcher.log' 2>&1"
  for _ in $(seq 1 30); do
    [[ -f "$PROV/launch_manifest.json" ]] && { STARTED=1; break; }
    tmux has-session -t "$SESSION" 2>/dev/null || break
    sleep 1
  done
  # Exactly one inner launch is permitted. A missing handshake is retained as a permanent
  # pre-forward launch failure; it is never killed, deleted, or retried on another GPU.
  break
done
[[ "$STARTED" -eq 1 ]] || { echo "one-shot launch failed before durable manifest; provenance retained" >&2; exit 5; }
"$PY" - "$SESSION" "$PROV/launch_manifest.json" "$PROV/handoff_status.json" "$OUT/final/result.json" <<'PY'
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
session,manifest,handoff,final=sys.argv[1:]
try: live=session in subprocess.check_output(['tmux','list-sessions','-F','#{session_name}'],text=True).splitlines()
except subprocess.CalledProcessError: live=False
if not live and not Path(final).is_file(): raise SystemExit('session neither live nor terminal')
r=json.load(open(manifest)); payload={'schema_version':'constructed_copy_circuit_v1_handoff','status':'RUNNING' if live else 'CLEANLY_TERMINAL','session':session,'session_live':live,'launcher_pid':r['launcher_pid'],'gpu':r['gpu'],'launch_manifest_sha256':hashlib.sha256(Path(manifest).read_bytes()).hexdigest(),'launcher_log':'reports/provenance/constructed_copy_circuit_v1_run_20260809/launcher.log','checked_ns':time.time_ns(),'representation_methods_evaluated':False,'training_performed':False,'natural_prompt_assay':False}
fd=os.open(handoff,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f: json.dump(payload,f,sort_keys=True,separators=(',',':'));f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps(payload,indent=2))
PY
