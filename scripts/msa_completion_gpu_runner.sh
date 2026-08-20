#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "usage: $0 RUN_ROOT JOB_NAME LOG_PATH COMMAND..." >&2
  exit 2
fi
run_root=$1; job=$2; log=$3; shift 3
mkdir -p "$run_root/allocations" "$(dirname "$log")" "$run_root/job_manifests"
config_sha=$(sha256sum configs/atlas_completion/analysis.json | awk '{print $1}')
if [[ "$job" == pilot* ]]; then
  freeze_sha=prescore-pilot-candidate
elif [[ -f configs/atlas_completion/freeze_record.json ]]; then
  freeze_sha=$(python -c 'import json; print(json.load(open("configs/atlas_completion/freeze_record.json"))["bundle_sha256"])')
else
  freeze_sha=prescore-pilot-candidate
fi

claim=""
gpu=""
uuid=""
atomic_publish() {
  local target=$1
  local temporary="${target}.tmp.$$.${RANDOM}"
  cat > "$temporary"
  python - "$temporary" "$(dirname "$target")" <<'PY'
import os,sys
with open(sys.argv[1], "rb") as handle:
    os.fsync(handle.fileno())
fd=os.open(sys.argv[2], os.O_RDONLY)
try: os.fsync(fd)
finally: os.close(fd)
PY
  ln "$temporary" "$target"
  rm "$temporary"
  python - "$(dirname "$target")" <<'PY'
import os,sys
fd=os.open(sys.argv[1], os.O_RDONLY)
try: os.fsync(fd)
finally: os.close(fd)
PY
}
cleanup() {
  status=$?
  trap - EXIT INT TERM
  printf '{"job":"%s","exit_code":%d,"ended_utc":"%s"}\n' "$job" "$status" "$(date -u +%FT%TZ)" \
    | atomic_publish "$run_root/job_manifests/${job}.terminal.json"
  if [[ -n "$claim" ]]; then
    rm -f "$claim/claim.json"
    rmdir "$claim"
  fi
  exit "$status"
}
trap cleanup EXIT INT TERM

while [[ -z "$gpu" ]]; do
  while IFS=, read -r idx gpu_uuid memory; do
    idx=$(echo "$idx" | xargs); gpu_uuid=$(echo "$gpu_uuid" | xargs); memory=$(echo "$memory" | tr -dc '0-9')
    candidate="$run_root/allocations/gpu_${idx}"
    if [[ -d "$candidate" ]]; then
      # A crashed runner may leave an allocation claim behind.  Reuse is only
      # allowed for a same-host PID that is provably dead; remote/malformed/live
      # claims remain blocking.  Atomic rename prevents two waiters reclaiming it.
      python - "$candidate" "$run_root" <<'PY' >/dev/null 2>&1 || true
import json, os, socket, sys, uuid
from pathlib import Path
claim, run_root = Path(sys.argv[1]), Path(sys.argv[2])
meta = claim / "claim.json"
if not meta.is_file():
    raise SystemExit(1)
row = json.loads(meta.read_text())
if row.get("host") != socket.gethostname():
    raise SystemExit(1)
pid = int(row.get("pid", -1))
try:
    os.kill(pid, 0)
except ProcessLookupError:
    stale = pid > 0
except PermissionError:
    stale = False
else:
    stale = False
if not stale:
    raise SystemExit(1)
quarantine = run_root / "invalid_partial" / "stale_allocations"
quarantine.mkdir(parents=True, exist_ok=True)
os.rename(claim, quarantine / f"{claim.name}.{uuid.uuid4().hex}")
PY
    fi
    if mkdir "$candidate" 2>/dev/null; then
      procs=$(nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader 2>/dev/null || true)
      memory_now=$(nvidia-smi -i "$idx" --query-gpu=memory.used --format=csv,noheader,nounits | tr -dc '0-9')
      if [[ ${memory_now:-999999} -lt 1024 ]] && ! grep -q "^${gpu_uuid}," <<<"$procs"; then
        gpu=$idx; uuid=$gpu_uuid; claim=$candidate
        printf '{"job":"%s","host":"%s","pid":%d,"gpu_index":%d,"gpu_uuid":"%s","started_utc":"%s"}\n' \
          "$job" "$(hostname)" "$$" "$idx" "$gpu_uuid" "$(date -u +%FT%TZ)" \
          | atomic_publish "$candidate/claim.json"
        break
      fi
      rmdir "$candidate"
    fi
  done < <(nvidia-smi --query-gpu=index,uuid,memory.used --format=csv,noheader,nounits)
  [[ -n "$gpu" ]] || sleep 60
done

cat <<EOF | atomic_publish "$run_root/job_manifests/${job}.json"
{"job":"$job","pid":$$,"gpu_index":$gpu,"gpu_uuid":"$uuid","config_sha256":"$config_sha","completion_bundle_sha256":"$freeze_sha","started_utc":"$(date -u +%FT%TZ)","log":"$log","command":$(printf '%s\n' "$*" | python -c 'import json,sys; print(json.dumps(sys.stdin.read().rstrip()))')}
EOF

echo "[$(date -u +%FT%TZ)] job=$job gpu=$gpu uuid=$uuid command=$*" | tee -a "$log"
CUDA_VISIBLE_DEVICES="$gpu" MSAE_EXPECTED_GPU_UUID="$uuid" PYTHONHASHSEED=20260731 \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 "$@" >> "$log" 2>&1
