#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/jumbo/lisp/f004ndc"
MSAE_ROOT="${REPO_ROOT}/MSAE"
TRAIN_SCRIPT="${MSAE_ROOT}/scripts/train_msae_k2.py"
WORKER_SCRIPT="${MSAE_ROOT}/scripts/run_msae_k2_worker.py"
EVAL_WAVE1_SCRIPT="${MSAE_ROOT}/scripts/evaluate_msae_k2_wave1.py"
STATUS_WAVE2_SCRIPT="${MSAE_ROOT}/scripts/evaluate_msae_k2_wave2_status.py"
GIT_HASH="$(cd "${MSAE_ROOT}" && git rev-parse HEAD)"

MODE="${MODE:-wave1}" # wave1 | wave2_resume
TS="${TS:-$(date +%Y%m%d_%H%M%S)}"
AUTO_PROMOTE="${AUTO_PROMOTE:-0}"
GATE_MODE="${GATE_MODE:-balanced}"
METRICS_SCHEMA_VERSION="${METRICS_SCHEMA_VERSION:-k2_msae_v2}"

WAVE1_TOKENS="${WAVE1_TOKENS:-100000000}"
WAVE2_TOKENS="${WAVE2_TOKENS:-1000000000}"
CHECKPOINT_EVERY_TOKENS="${CHECKPOINT_EVERY_TOKENS:-25000000}"
LOG_EVERY_STEPS="${LOG_EVERY_STEPS:-20}"
WARMUP_STEPS="${WARMUP_STEPS:-1000}"

WAVE1_GPU_LIST="${WAVE1_GPU_LIST:-4,5,6,7}"
WAVE2_GPU_LIST="${WAVE2_GPU_LIST:-4,5,7}"
MONITOR_GPU="${MONITOR_GPU:-6}"
MONITOR_POLL_SEC="${MONITOR_POLL_SEC:-600}"

if [[ "${MODE}" == "wave1" ]]; then
  RUN_ROOT="${MSAE_ROOT}/pilot_runs/${TS}_k2_msae_wave1"
else
  RUN_ROOT="${MSAE_ROOT}/pilot_runs/${TS}_k2_msae_wave2"
fi
LOG_DIR="${RUN_ROOT}/logs"
OUT_DIR="${RUN_ROOT}/outputs"
REPORT_DIR="${RUN_ROOT}/reports"
MANIFEST="${RUN_ROOT}/run_manifest.tsv"

mkdir -p "${RUN_ROOT}" "${LOG_DIR}" "${OUT_DIR}" "${REPORT_DIR}"
if [[ "${MODE}" == "wave1" ]]; then
  echo "${RUN_ROOT}" > "${MSAE_ROOT}/pilot_runs/.latest_k2_wave1_run_root"
else
  echo "${RUN_ROOT}" > "${MSAE_ROOT}/pilot_runs/.latest_k2_wave2_run_root"
fi
echo "${RUN_ROOT}" > "${MSAE_ROOT}/pilot_runs/.latest_k2_run_root"

cat > "${MANIFEST}" <<'TSV'
job_id	stage	model	seed	layer_index	lambda_inc	target_tokens	context_length	model_batch_size	microbatch_size	effective_batch_size	dataset_name	dataset_config	dataset_split	text_field	output_dir	log_file	resume_path	status	attempt	worker	gpu	start_time	end_time	heartbeat_time	error	notes
TSV

append_job() {
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9" "${10}" "${11}" "${12}" "${13}" "${14}" "${15}" "${16}" "${17}" "${18}" \
    "pending" "0" "" "" "" "" "" "" "$19" >> "${MANIFEST}"
}

start_workers() {
  local phase="$1"
  local gpu_csv="$2"
  IFS=',' read -r -a gpu_arr <<< "${gpu_csv}"
  for gpu in "${gpu_arr[@]}"; do
    local session="msae-k2-${phase}-g${gpu}-${TS}"
    local wlog="${LOG_DIR}/${session}.log"
    tmux new-session -d -s "${session}" \
      "bash -lc 'set -euo pipefail; cd ${REPO_ROOT}; export PYTHONUNBUFFERED=1; \
       python -u ${WORKER_SCRIPT} --manifest ${MANIFEST} --worker ${session} --gpu ${gpu} \
       --repo_root ${REPO_ROOT} --train_script ${TRAIN_SCRIPT} --run_root ${RUN_ROOT} \
       --git_commit_hash ${GIT_HASH} \
       --checkpoint_every_tokens ${CHECKPOINT_EVERY_TOKENS} \
       --log_every_steps ${LOG_EVERY_STEPS} \
       --warmup_steps ${WARMUP_STEPS} \
       2>&1 | tee ${wlog}'"
    echo "[ok] started ${session}"
  done
}

if [[ "${MODE}" == "wave1" ]]; then
  append_job \
    "k2_wave1_g4_L3_s42_inc1e2" "wave1" "EleutherAI/pythia-160m-deduped" "42" "3" "1e-2" "${WAVE1_TOKENS}" \
    "128" "4" "64" "4096" "ArmelR/the-pile-splitted" "all" "train" "text" \
    "${OUT_DIR}/k2_wave1_g4_L3_s42_inc1e2" "${LOG_DIR}/k2_wave1_g4_L3_s42_inc1e2.log" "" \
    "wave_mode=wave1;gate_mode=${GATE_MODE};schema=${METRICS_SCHEMA_VERSION};git=${GIT_HASH};role=L3_baseline"

  append_job \
    "k2_wave1_g5_L3_s43_inc1e2" "wave1" "EleutherAI/pythia-160m-deduped" "43" "3" "1e-2" "${WAVE1_TOKENS}" \
    "128" "4" "64" "4096" "ArmelR/the-pile-splitted" "all" "train" "text" \
    "${OUT_DIR}/k2_wave1_g5_L3_s43_inc1e2" "${LOG_DIR}/k2_wave1_g5_L3_s43_inc1e2.log" "" \
    "wave_mode=wave1;gate_mode=${GATE_MODE};schema=${METRICS_SCHEMA_VERSION};git=${GIT_HASH};role=L3_baseline"

  append_job \
    "k2_wave1_g6_L4_s42_inc1e2" "wave1" "EleutherAI/pythia-160m-deduped" "42" "4" "1e-2" "${WAVE1_TOKENS}" \
    "128" "4" "64" "4096" "ArmelR/the-pile-splitted" "all" "train" "text" \
    "${OUT_DIR}/k2_wave1_g6_L4_s42_inc1e2" "${LOG_DIR}/k2_wave1_g6_L4_s42_inc1e2.log" "" \
    "wave_mode=wave1;gate_mode=${GATE_MODE};schema=${METRICS_SCHEMA_VERSION};git=${GIT_HASH};role=L4_fallback"

  append_job \
    "k2_wave1_g7_L3_s42_inc0" "wave1" "EleutherAI/pythia-160m-deduped" "42" "3" "0" "${WAVE1_TOKENS}" \
    "128" "4" "64" "4096" "ArmelR/the-pile-splitted" "all" "train" "text" \
    "${OUT_DIR}/k2_wave1_g7_L3_s42_inc0" "${LOG_DIR}/k2_wave1_g7_L3_s42_inc0.log" "" \
    "wave_mode=wave1;gate_mode=${GATE_MODE};schema=${METRICS_SCHEMA_VERSION};git=${GIT_HASH};role=no_inc_control"

  start_workers "wave1" "${WAVE1_GPU_LIST}"

  echo "RUN_ROOT=${RUN_ROOT}"
  echo "MANIFEST=${MANIFEST}"

  if [[ "${AUTO_PROMOTE}" == "1" ]]; then
    echo "[info] AUTO_PROMOTE=1: waiting for wave1 completion"
    while true; do
      pending=$(awk -F'\t' 'NR>1 && $19=="pending" {c++} END{print c+0}' "${MANIFEST}")
      running=$(awk -F'\t' 'NR>1 && $19=="running" {c++} END{print c+0}' "${MANIFEST}")
      failed=$(awk -F'\t' 'NR>1 && $19=="failed" {c++} END{print c+0}' "${MANIFEST}")
      echo "[status] pending=${pending} running=${running} failed=${failed}"
      if [[ "${pending}" == "0" && "${running}" == "0" ]]; then
        break
      fi
      sleep 60
    done

    python "${EVAL_WAVE1_SCRIPT}" --run_root "${RUN_ROOT}" --wave1_target_tokens "${WAVE1_TOKENS}" \
      --wave2_target_tokens "${WAVE2_TOKENS}" --output_json "reports/k2_wave1_decision.json" \
      --output_md "reports/k2_wave1_decision.md"
  fi
  exit 0
fi

# wave2_resume mode
SOURCE_WAVE1_RUN_ROOT="${SOURCE_WAVE1_RUN_ROOT:-}"
if [[ -z "${SOURCE_WAVE1_RUN_ROOT}" ]]; then
  latest_wave1_file="${MSAE_ROOT}/pilot_runs/.latest_k2_wave1_run_root"
  if [[ -f "${latest_wave1_file}" ]]; then
    SOURCE_WAVE1_RUN_ROOT="$(cat "${latest_wave1_file}")"
  fi
fi
if [[ -z "${SOURCE_WAVE1_RUN_ROOT}" ]]; then
  echo "[error] SOURCE_WAVE1_RUN_ROOT not set and no .latest_k2_wave1_run_root found"
  exit 1
fi

DECISION_JSON="${DECISION_JSON:-${SOURCE_WAVE1_RUN_ROOT}/reports/k2_wave1_decision.json}"
if [[ ! -f "${DECISION_JSON}" ]]; then
  echo "[error] decision file not found: ${DECISION_JSON}"
  exit 1
fi

python - "${MANIFEST}" "${DECISION_JSON}" "${OUT_DIR}" "${LOG_DIR}" "${WAVE2_TOKENS}" "${GATE_MODE}" "${METRICS_SCHEMA_VERSION}" "${GIT_HASH}" <<'PY'
import csv
import json
import math
import sys
from pathlib import Path

manifest, decision_path, out_dir, log_dir, wave2_tokens, gate_mode, schema, git_hash = sys.argv[1:]
decision = json.loads(Path(decision_path).read_text(encoding="utf-8"))
promote = decision.get("promote_jobs", [])

rows = []
for rec in promote:
    layer = int(rec["layer_index"])
    lam = float(rec["lambda_inc"])
    # Keep L3 baselines and no-inc control. L4 stays paused unless explicit regression trigger.
    if not ((layer == 3 and abs(lam - 1e-2) < 1e-12) or abs(lam) < 1e-12):
        continue
    old_id = rec["job_id"]
    jid = f"{old_id}_wave2"
    out = str(Path(out_dir) / jid)
    log = str(Path(log_dir) / f"{jid}.log")
    note_role = "L3_baseline" if abs(lam - 1e-2) < 1e-12 else "no_inc_control"
    notes = (
        f"wave_mode=wave2_resume;gate_mode={gate_mode};schema={schema};git={git_hash};"
        f"source_decision={decision_path};role={note_role};l4_paused=1"
    )
    rows.append(
        {
            "job_id": jid,
            "stage": "wave2",
            "model": "EleutherAI/pythia-160m-deduped",
            "seed": str(rec["seed"]),
            "layer_index": str(layer),
            "lambda_inc": str(lam),
            "target_tokens": str(wave2_tokens),
            "context_length": "128",
            "model_batch_size": "4",
            "microbatch_size": "64",
            "effective_batch_size": "4096",
            "dataset_name": "ArmelR/the-pile-splitted",
            "dataset_config": "all",
            "dataset_split": "train",
            "text_field": "text",
            "output_dir": out,
            "log_file": log,
            "resume_path": str(rec["resume_path"]),
            "status": "pending",
            "attempt": "0",
            "worker": "",
            "gpu": "",
            "start_time": "",
            "end_time": "",
            "heartbeat_time": "",
            "error": "",
            "notes": notes,
        }
    )

if not rows:
    raise SystemExit("no wave2 jobs selected from decision file")

fieldnames = [
    "job_id","stage","model","seed","layer_index","lambda_inc","target_tokens","context_length",
    "model_batch_size","microbatch_size","effective_batch_size","dataset_name","dataset_config","dataset_split",
    "text_field","output_dir","log_file","resume_path","status","attempt","worker","gpu","start_time","end_time",
    "heartbeat_time","error","notes",
]
with open(manifest, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
    w.writeheader()
    w.writerows(rows)
print(f"[done] wrote wave2 manifest rows={len(rows)}")
PY

FALLBACK_RESUME_PATH="${FALLBACK_RESUME_PATH:-}"
if [[ -z "${FALLBACK_RESUME_PATH}" ]]; then
  FALLBACK_RESUME_PATH="$(python - "${SOURCE_WAVE1_RUN_ROOT}" <<'PY'
import csv
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
manifest = root / "run_manifest.tsv"
if not manifest.exists():
    print("")
    raise SystemExit(0)
rows = list(csv.DictReader(open(manifest, "r", encoding="utf-8", newline=""), delimiter="\t"))
cand = None
for r in rows:
    try:
        if int(r["layer_index"]) == 4 and abs(float(r["lambda_inc"]) - 1e-2) < 1e-12:
            cand = r
            break
    except Exception:
        continue
if cand is None:
    print("")
    raise SystemExit(0)
s = Path(cand["output_dir"]) / "train_summary.json"
if s.exists():
    obj = json.loads(s.read_text(encoding="utf-8"))
    print(obj.get("checkpoint_final", ""))
else:
    print("")
PY
)"
fi

start_workers "wave2" "${WAVE2_GPU_LIST}"

monitor_session="msae-k2-wave2-monitor-g${MONITOR_GPU}-${TS}"
monitor_log="${LOG_DIR}/${monitor_session}.log"
tmux new-session -d -s "${monitor_session}" \
  "bash -lc 'set -euo pipefail; cd ${REPO_ROOT}; export PYTHONUNBUFFERED=1; export CUDA_VISIBLE_DEVICES=${MONITOR_GPU}; \
   while true; do \
     python -u ${STATUS_WAVE2_SCRIPT} --run_root ${RUN_ROOT} --fallback_resume_path \"${FALLBACK_RESUME_PATH}\" \
       --output_json reports/wave2_status_snapshot.json --output_md reports/wave2_status.md; \
     pending=\$(awk -F\"\\t\" \"NR>1 && \\\$19==\\\"pending\\\" {c++} END{print c+0}\" ${MANIFEST}); \
     running=\$(awk -F\"\\t\" \"NR>1 && \\\$19==\\\"running\\\" {c++} END{print c+0}\" ${MANIFEST}); \
     if [[ \"\$pending\" == \"0\" && \"\$running\" == \"0\" ]]; then \
       break; \
     fi; \
     sleep ${MONITOR_POLL_SEC}; \
   done \
   2>&1 | tee ${monitor_log}'"
echo "[ok] started ${monitor_session}"

echo "RUN_ROOT=${RUN_ROOT}"
echo "MANIFEST=${MANIFEST}"
echo "SOURCE_WAVE1_RUN_ROOT=${SOURCE_WAVE1_RUN_ROOT}"
