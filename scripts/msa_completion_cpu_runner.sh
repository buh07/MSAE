#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "usage: $0 RUN_ROOT JOB_NAME LOG_PATH COMMAND..." >&2
  exit 2
fi
run_root=$1; job=$2; log=$3; shift 3
mkdir -p "$(dirname "$log")" "$run_root/job_manifests"
config_sha=$(sha256sum configs/atlas_completion/analysis.json | awk '{print $1}')
freeze_sha=$(python -c 'import json; print(json.load(open("configs/atlas_completion/freeze_record.json"))["bundle_sha256"])')

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
  printf '{"job":"%s","exit_code":%d,"ended_utc":"%s"}\n' \
    "$job" "$status" "$(date -u +%FT%TZ)" \
    | atomic_publish "$run_root/job_manifests/${job}.terminal.json"
  exit "$status"
}
trap cleanup EXIT INT TERM

cat <<EOF | atomic_publish "$run_root/job_manifests/${job}.json"
{"job":"$job","pid":$$,"execution_device":"cpu","config_sha256":"$config_sha","completion_bundle_sha256":"$freeze_sha","started_utc":"$(date -u +%FT%TZ)","log":"$log","command":$(printf '%s\n' "$*" | python -c 'import json,sys; print(json.dumps(sys.stdin.read().rstrip()))')}
EOF

echo "[$(date -u +%FT%TZ)] job=$job device=cpu command=$*" | tee -a "$log"
CUDA_VISIBLE_DEVICES="" PYTHONHASHSEED=20260731 HF_HUB_OFFLINE=1 \
TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 "$@" >> "$log" 2>&1
