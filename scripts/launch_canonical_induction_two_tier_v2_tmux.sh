#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
PY="$ROOT/.venv-atlas/bin/python"; RUN="$ROOT/scripts/canonical_induction_two_tier_v2.py"; CONFIG="$ROOT/configs/canonical_induction_two_tier_v2/run.json"
SESSION="msae_induction_two_tier_v2"; OUT="$ROOT/results/canonical_induction_two_tier_v2_20260809"; PROV="$ROOT/reports/provenance/canonical_induction_two_tier_v2_run_20260809"
export CUBLAS_WORKSPACE_CONFIG=:4096:8 HF_HOME="${HF_HOME:-/jumbo/lisp/f004ndc/huggingface}" TRANSFORMERS_CACHE="${HF_HOME:-/jumbo/lisp/f004ndc/huggingface}/hub"
export HF_DATASETS_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONHASHSEED=20260822

failure_handler() {
  set +e
  [[ -f "$PROV/launch_manifest.json" ]] || return 0
  local token; token="$($PY -c 'import json,sys;print(json.load(open(sys.argv[1]))["launch_token"])' "$PROV/launch_manifest.json" 2>/dev/null)" || return 0
  for stage in development confirmation; do
    local a="$PROV/${stage}_ATTEMPT.json"
    [[ "$stage" == development && -f "$OUT/development_gate/DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP.json" ]] && continue
    [[ -f "$a" || -d "$PROV/qa/$stage" || -d "$OUT/$stage" ]] && "$PY" "$RUN" reconcile-stage --config "$CONFIG" --stage "$stage" --launch-token "$token" || true
  done
  [[ -f "$OUT/development/COMPLETE.json" && ! -f "$OUT/development_gate/result.json" && ! -f "$OUT/development_gate/DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP.json" ]] && "$PY" "$RUN" reconcile-development-gate --config "$CONFIG" --launch-token "$token" || true
  [[ -f "$OUT/development_gate/result.json" && ! -f "$OUT/confirmation_authorization/CONFIRMATION_AUTHORIZATION.json" && ! -f "$OUT/confirmation_authorization/CONFIRMATION_BLOCKED.json" && ! -f "$OUT/confirmation_authorization/CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP.json" ]] && "$PY" "$RUN" reconcile-authorization --config "$CONFIG" --launch-token "$token" || true
  [[ ! -f "$OUT/final/result.json" ]] && "$PY" "$RUN" final --config "$CONFIG" --launch-token "$token" || true
}

if [[ "${1:-}" == "--inner" ]]; then
  [[ $# -eq 6 ]] || { echo "inner args: --inner INDEX UUID LOCK BEFORE_JSON" >&2; exit 2; }
  INDEX="$2"; UUID="$3"; LOCK="$4"; BEFORE="$5"; NONCE="$6"
  mkdir -p "$(dirname "$LOCK")" "$PROV"
  exec 9>"$LOCK"; flock -n 9 || { echo "GPU lock busy: $UUID" >&2; exit 11; }
  trap failure_handler ERR INT TERM
  ROW="$(nvidia-smi --id="$INDEX" --query-gpu=index,uuid,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits)"
  IFS=',' read -r IDX2 UUID2 USED TOTAL UTIL <<<"$ROW"; for x in IDX2 UUID2 USED TOTAL UTIL; do printf -v "$x" '%s' "${!x//[[:space:]]/}"; done
  PROCS="$(nvidia-smi --query-compute-apps=gpu_uuid --format=csv,noheader,nounits 2>/dev/null | grep -Fxc "$UUID" || true)"
  [[ "$IDX2" == "$INDEX" && "$UUID2" == "$UUID" && "$USED" -lt 2048 && "$UTIL" -lt 10 && "$PROCS" -eq 0 ]] || { echo "post-lock GPU recheck failed: $ROW procs=$PROCS" >&2; exit 12; }
  export CUDA_VISIBLE_DEVICES="$UUID" EXPECTED_GPU_UUID="$UUID"
  TOKEN="$($PY -c 'import secrets;print(secrets.token_hex(32))')"
  "$PY" - "$PROV/launch_manifest.json" "$CONFIG" "$INDEX" "$UUID" "$USED" "$TOTAL" "$UTIL" "$PROCS" "$LOCK" "$TOKEN" "$BEFORE" "$NONCE" "$$" <<'PY'
import hashlib,json,os,sys,time
from pathlib import Path
out,config,index,uuid,used,total,util,procs,lock,token,before,nonce,pid=sys.argv[1:]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
cfg=json.load(open(config)); cwd=Path.cwd()
payload={'schema_version':'canonical_induction_two_tier_v2_launch','launch_token':token,'launcher_pid':int(pid),'started_ns':time.time_ns(),'config':str(Path(config).relative_to(cwd)),'config_sha256':sha(config),'freeze_sha256':sha(cwd/cfg['runtime']['freeze']),'review_binding_sha256':sha(cwd/cfg['runtime']['review_binding']),'cache_attestation_sha256':sha(cwd/cfg['runtime']['cache_attestation']),'gpu':{'physical_index':int(index),'uuid':uuid,'memory_used_mib':int(used),'memory_total_mib':int(total),'utilization_percent':int(util),'compute_processes':int(procs)},'gpu_lock_path':lock,'gpu_lock_inode':os.stat(lock).st_ino,'gpu_lock_held':True,'before_lock_evidence':json.loads(before),'post_lock_recheck':True,'selection_nonce':nonce,'session':'msae_induction_two_tier_v2','representation_methods':False,'training':False,'external_set_scope':'FIGURE2_UPSTREAM_SET_NOT_COMPLETE_RANDOM_TOKEN_CIRCUIT'}
Path(out).parent.mkdir(parents=True,exist_ok=True)
fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
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

[[ $# -eq 0 ]] || { echo "no public arguments" >&2; exit 2; }
[[ -x "$PY" ]] || { echo "missing Python env" >&2; exit 2; }
[[ ! -e "$OUT" && ! -e "$PROV" ]] || { echo "one-shot runtime namespace exists" >&2; exit 3; }
tmux has-session -t "$SESSION" 2>/dev/null && { echo "tmux session exists" >&2; exit 3; } || true
"$PY" "$RUN" preservation-verify --config "$CONFIG"
"$PY" "$RUN" preflight --config "$CONFIG" --pre-gate
"$PY" "$RUN" verify-freeze --config "$CONFIG" --pre-gate
"$PY" "$RUN" review-binding --config "$CONFIG"
mapfile -t ROWS < <(nvidia-smi --query-gpu=index,uuid,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits | awk -F, '{for(i=1;i<=5;i++)gsub(/^ +| +$/,"",$i); if($3+0<2048 && $5+0<10) print $1"|"$2"|"$3"|"$4"|"$5}')
[[ ${#ROWS[@]} -gt 0 ]] || { echo "no GPU meets memory/utilization availability" >&2; exit 4; }
mkdir -p /tmp/msae-gpu-locks
STARTED=0
for row in "${ROWS[@]}"; do
  IFS='|' read -r INDEX UUID USED TOTAL UTIL <<<"$row"
  PROCS="$(nvidia-smi --query-compute-apps=gpu_uuid --format=csv,noheader,nounits 2>/dev/null | grep -Fxc "$UUID" || true)"; [[ "$PROCS" -eq 0 ]] || continue
  LOCK="/tmp/msae-gpu-locks/${UUID}.lock"; BEFORE="$($PY -c 'import json,sys;print(json.dumps({"index":int(sys.argv[1]),"uuid":sys.argv[2],"memory_used_mib":int(sys.argv[3]),"memory_total_mib":int(sys.argv[4]),"utilization_percent":int(sys.argv[5]),"compute_processes":int(sys.argv[6])},separators=(",",":")))' "$INDEX" "$UUID" "$USED" "$TOTAL" "$UTIL" "$PROCS")"; NONCE="$($PY -c 'import secrets;print(secrets.token_hex(16))')"
  tmux new-session -d -s "$SESSION" "mkdir -p '$PROV'; exec '$0' --inner '$INDEX' '$UUID' '$LOCK' '$BEFORE' '$NONCE' > '$PROV/launcher.log' 2>&1"
  for _ in 1 2 3 4 5; do [[ -f "$PROV/launch_manifest.json" ]] && { STARTED=1; break; }; sleep 1; done
  [[ "$STARTED" -eq 1 ]] && break
  tmux kill-session -t "$SESSION" 2>/dev/null || true; rm -rf "$PROV"
done
[[ "$STARTED" -eq 1 ]] || { echo "could not acquire/recheck a free GPU" >&2; exit 5; }
sleep 2
"$PY" - "$SESSION" "$PROV/launch_manifest.json" "$PROV/handoff_status.json" "$OUT/final/result.json" <<'PY'
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
session,manifest,handoff,final=sys.argv[1:]
try: live=session in subprocess.check_output(['tmux','list-sessions','-F','#{session_name}'],text=True).splitlines()
except subprocess.CalledProcessError: live=False
if not live and not Path(final).is_file(): raise SystemExit('session is neither live nor cleanly terminal')
launch=json.load(open(manifest)); payload={'schema_version':'canonical_induction_two_tier_v2_handoff','status':'RUNNING' if live else 'CLEANLY_TERMINAL','session':session,'session_live':live,'launcher_pid':launch['launcher_pid'],'gpu':launch['gpu'],'gpu_lock_path':launch['gpu_lock_path'],'launch_manifest_sha256':hashlib.sha256(Path(manifest).read_bytes()).hexdigest(),'launcher_log':'reports/provenance/canonical_induction_two_tier_v2_run_20260809/launcher.log','checked_ns':time.time_ns(),'representation_methods':False,'training':False}
fd=os.open(handoff,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f: json.dump(payload,f,sort_keys=True,separators=(',',':'));f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps(payload,indent=2))
PY
