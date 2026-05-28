#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/jumbo/lisp/f004ndc"
MSAE_ROOT="${REPO_ROOT}/MSAE"
TRAIN_SCRIPT="${MSAE_ROOT}/scripts/train_msae_k2.py"
WORKER_SCRIPT="${MSAE_ROOT}/scripts/run_msae_k2_worker.py"
EVAL_SCRIPT="${MSAE_ROOT}/scripts/evaluate_msae_k2_wave1.py"
GIT_HASH="$(cd "${MSAE_ROOT}" && git rev-parse HEAD)"

TS="${TS:-$(date +%Y%m%d_%H%M%S)}"
RUN_ROOT="${MSAE_ROOT}/pilot_runs/${TS}_k2_msae_wave1"
LOG_DIR="${RUN_ROOT}/logs"
OUT_DIR="${RUN_ROOT}/outputs"
REPORT_DIR="${RUN_ROOT}/reports"
MANIFEST="${RUN_ROOT}/run_manifest.tsv"

AUTO_PROMOTE="${AUTO_PROMOTE:-0}"
WAVE1_TOKENS="${WAVE1_TOKENS:-100000000}"
WAVE2_TOKENS="${WAVE2_TOKENS:-1000000000}"
CHECKPOINT_EVERY_TOKENS="${CHECKPOINT_EVERY_TOKENS:-25000000}"
LOG_EVERY_STEPS="${LOG_EVERY_STEPS:-20}"
WARMUP_STEPS="${WARMUP_STEPS:-1000}"

mkdir -p "${RUN_ROOT}" "${LOG_DIR}" "${OUT_DIR}" "${REPORT_DIR}"
echo "${RUN_ROOT}" > "${MSAE_ROOT}/pilot_runs/.latest_k2_run_root"

cat > "${MANIFEST}" <<'TSV'
job_id	stage	model	seed	layer_index	lambda_inc	target_tokens	context_length	model_batch_size	microbatch_size	effective_batch_size	dataset_name	dataset_config	dataset_split	text_field	output_dir	log_file	resume_path	status	attempt	worker	gpu	start_time	end_time	heartbeat_time	error	notes
TSV

append_job() {
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9" "${10}" "${11}" "${12}" "${13}" "${14}" "${15}" "${16}" "${17}" "${18}" \
    "pending" "0" "" "" "" "" "" "" "$19" >> "${MANIFEST}"
}

# Wave 1 matrix
append_job \
  "k2_wave1_g4_L3_s42_inc1e2" "wave1" "EleutherAI/pythia-160m-deduped" "42" "3" "1e-2" "${WAVE1_TOKENS}" \
  "128" "4" "64" "4096" "ArmelR/the-pile-splitted" "all" "train" "text" \
  "${OUT_DIR}/k2_wave1_g4_L3_s42_inc1e2" "${LOG_DIR}/k2_wave1_g4_L3_s42_inc1e2.log" "" "L3_baseline"

append_job \
  "k2_wave1_g5_L3_s43_inc1e2" "wave1" "EleutherAI/pythia-160m-deduped" "43" "3" "1e-2" "${WAVE1_TOKENS}" \
  "128" "4" "64" "4096" "ArmelR/the-pile-splitted" "all" "train" "text" \
  "${OUT_DIR}/k2_wave1_g5_L3_s43_inc1e2" "${LOG_DIR}/k2_wave1_g5_L3_s43_inc1e2.log" "" "L3_baseline"

append_job \
  "k2_wave1_g6_L4_s42_inc1e2" "wave1" "EleutherAI/pythia-160m-deduped" "42" "4" "1e-2" "${WAVE1_TOKENS}" \
  "128" "4" "64" "4096" "ArmelR/the-pile-splitted" "all" "train" "text" \
  "${OUT_DIR}/k2_wave1_g6_L4_s42_inc1e2" "${LOG_DIR}/k2_wave1_g6_L4_s42_inc1e2.log" "" "L4_fallback"

append_job \
  "k2_wave1_g7_L3_s42_inc0" "wave1" "EleutherAI/pythia-160m-deduped" "42" "3" "0" "${WAVE1_TOKENS}" \
  "128" "4" "64" "4096" "ArmelR/the-pile-splitted" "all" "train" "text" \
  "${OUT_DIR}/k2_wave1_g7_L3_s42_inc0" "${LOG_DIR}/k2_wave1_g7_L3_s42_inc0.log" "" "no_inc_control"

start_workers() {
  local phase="$1"
  for gpu in 4 5 6 7; do
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

start_workers "wave1"

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

  python "${EVAL_SCRIPT}" --run_root "${RUN_ROOT}" --wave1_target_tokens "${WAVE1_TOKENS}" --wave2_target_tokens "${WAVE2_TOKENS}" \
    --output_json "reports/k2_wave1_decision.json" --output_md "reports/k2_wave1_decision.md"

  RUN_ROOT_ENV="${RUN_ROOT}" python - <<'PY'
import json, csv
import os
from pathlib import Path
run_root = Path(os.environ["RUN_ROOT_ENV"])
manifest = run_root / "run_manifest.tsv"
decision = json.loads((run_root / "reports" / "k2_wave1_decision.json").read_text(encoding="utf-8"))

rows = []
with open(manifest, "r", encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f, delimiter="\t"))

for rec in decision.get("promote_jobs", []):
    jid = rec["job_id"] + "_wave2"
    base = next((r for r in rows if r["job_id"] == rec["job_id"]), None)
    if base is None:
        continue
    row = dict(base)
    row["job_id"] = jid
    row["stage"] = "wave2"
    row["target_tokens"] = str(rec["target_tokens"])
    row["resume_path"] = rec["resume_path"]
    row["output_dir"] = str(run_root / "outputs" / jid)
    row["log_file"] = str(run_root / "logs" / f"{jid}.log")
    row["status"] = "pending"
    row["attempt"] = "0"
    row["worker"] = ""
    row["gpu"] = ""
    row["start_time"] = ""
    row["end_time"] = ""
    row["heartbeat_time"] = ""
    row["error"] = ""
    row["notes"] = "auto_promoted"
    rows.append(row)

fieldnames = rows[0].keys()
with open(manifest, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
    w.writeheader()
    w.writerows(rows)
print("[done] appended wave2 jobs")
PY

  start_workers "wave2"
fi
