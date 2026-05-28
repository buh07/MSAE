#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/jumbo/lisp/f004ndc"
MSAE_ROOT="${REPO_ROOT}/MSAE"
SCRIPT="${MSAE_ROOT}/scripts/raw_activation_separability_pilot.py"
SUMMARIZER="${MSAE_ROOT}/scripts/summarize_pilot_run.py"
WORKER="${MSAE_ROOT}/scripts/run_pilot_worker_v6.py"
GIT_HASH="$(cd "${MSAE_ROOT}" && git rev-parse HEAD)"

TS="${TS:-$(date +%Y%m%d_%H%M%S)}"
RUN_ROOT="${MSAE_ROOT}/pilot_runs/${TS}_compat_v5_iid"
LOG_DIR="${RUN_ROOT}/logs"
OUT_DIR="${RUN_ROOT}/outputs"
MANIFEST="${RUN_ROOT}/run_manifest.tsv"

mkdir -p "${RUN_ROOT}" "${LOG_DIR}" "${OUT_DIR}"
echo "${RUN_ROOT}" > "${MSAE_ROOT}/pilot_runs/.latest_pilot_compat_run_root"

cat > "${MANIFEST}" <<'TSV'
job_id	stage	model	seed	layer_index	split_mode	holdout_source_label	max_text_samples	max_tokens_collect	holdout_eval_max_tokens_collect	context_length	batch_size	top_k_tokens	probe_ranks	probe_torch_max_steps_raw	probe_torch_max_steps_projected	probe_torch_patience_raw	probe_torch_patience_projected	train_source_max_text_samples	eval_source_max_text_samples	corpus_holdout_max_text_samples	source_manifest_path	output_dir	log_file	status	attempt	worker	gpu	start_time	end_time	heartbeat_time	error	notes
TSV

append_job() {
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9" "${10}" "${11}" "${12}" "${13}" "${14}" "${15}" "${16}" "${17}" "${18}" "${19}" "${20}" "${21}" "${22}" "${23}" "${24}" \
    "pending" "0" "" "" "" "" "" "" "$25" >> "${MANIFEST}"
}

for seed in 42 43 44 45 46; do
  for layer in 3 4; do
    job_id="compat_p160_s${seed}_L${layer}_iid"
    out="${OUT_DIR}/${job_id}"
    log="${LOG_DIR}/${job_id}.log"
    append_job "${job_id}" "compat" "EleutherAI/pythia-160m-deduped" "${seed}" "${layer}" "iid" "" \
      "5000" "100000" "50000" "128" "4" "256" "8,16,32" "2000" "3000" "350" "600" \
      "0" "0" "0" "" "${out}" "${log}" "v5_like_iid"
  done
done

python "${SUMMARIZER}" --run_root "${RUN_ROOT}" || true

for gpu in 4 5 6 7; do
  session="msae-compat-g${gpu}-${TS}"
  wlog="${LOG_DIR}/${session}.log"
  tmux new-session -d -s "${session}" \
    "bash -lc 'set -euo pipefail; cd ${REPO_ROOT}; export PYTHONUNBUFFERED=1; \
     python -u ${WORKER} --manifest ${MANIFEST} --worker ${session} --gpu ${gpu} \
     --repo_root ${REPO_ROOT} --pilot_script ${SCRIPT} --summarizer_script ${SUMMARIZER} \
     --run_root ${RUN_ROOT} --git_commit_hash ${GIT_HASH} 2>&1 | tee ${wlog}'"
  echo "[ok] started ${session}"
done

echo "RUN_ROOT=${RUN_ROOT}"
echo "MANIFEST=${MANIFEST}"
tmux ls | rg "msae-compat-"
