#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/jumbo/lisp/f004ndc"
MSAE_ROOT="${REPO_ROOT}/MSAE"
SCRIPT="${MSAE_ROOT}/scripts/raw_activation_separability_pilot.py"
SUMMARIZER="${MSAE_ROOT}/scripts/summarize_pilot_run.py"
WORKER="${MSAE_ROOT}/scripts/run_pilot_worker_v6.py"

TS="${TS:-$(date +%Y%m%d_%H%M%S)}"
RUN_ROOT="${MSAE_ROOT}/pilot_runs/${TS}_v6_prek2_fullsuite"
LOG_DIR="${RUN_ROOT}/logs"
OUT_DIR="${RUN_ROOT}/outputs"
MANIFEST="${RUN_ROOT}/run_manifest.tsv"
SOURCE_MANIFEST="${RUN_ROOT}/source_manifest_balanced_5.json"

mkdir -p "${RUN_ROOT}" "${LOG_DIR}" "${OUT_DIR}" "${RUN_ROOT}/reports"
echo "${RUN_ROOT}" > "${MSAE_ROOT}/pilot_runs/.latest_pilot_v6_run_root"

cat > "${SOURCE_MANIFEST}" <<'JSON'
[
  {"dataset_name":"HuggingFaceFW/fineweb-edu","dataset_config":"CC-MAIN-2024-10","dataset_split":"train","text_field":"text","source_label":"FineWeb-Edu"},
  {"dataset_name":"ArmelR/the-pile-splitted","dataset_config":"Pile-CC","dataset_split":"train","text_field":"text","source_label":"Pile-CC"},
  {"dataset_name":"ArmelR/the-pile-splitted","dataset_config":"Github","dataset_split":"train","text_field":"text","source_label":"Github"},
  {"dataset_name":"ArmelR/the-pile-splitted","dataset_config":"PubMed Abstracts","dataset_split":"train","text_field":"text","source_label":"PubMed Abstracts"},
  {"dataset_name":"ArmelR/the-pile-splitted","dataset_config":"ArXiv","dataset_split":"train","text_field":"text","source_label":"ArXiv"}
]
JSON

cat > "${MANIFEST}" <<'TSV'
job_id	stage	model	seed	layer_index	split_mode	holdout_source_label	max_text_samples	max_tokens_collect	holdout_eval_max_tokens_collect	context_length	batch_size	top_k_tokens	probe_ranks	probe_torch_max_steps_raw	probe_torch_max_steps_projected	probe_torch_patience_raw	probe_torch_patience_projected	train_source_max_text_samples	eval_source_max_text_samples	corpus_holdout_max_text_samples	source_manifest_path	output_dir	log_file	status	attempt	worker	gpu	start_time	end_time	heartbeat_time	error	notes
TSV

append_job() {
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9" "${10}" "${11}" "${12}" "${13}" "${14}" "${15}" "${16}" "${17}" "${18}" "${19}" "${20}" "${21}" "${22}" "${23}" "${24}" \
    "pending" "0" "" "" "" "" "" "" "$25" >> "${MANIFEST}"
}

# Stage A: IID confirmatory
for seed in 42 43 44 45 46; do
  for layer in 3 4; do
    job_id="A_p160_s${seed}_L${layer}_iid"
    out="${OUT_DIR}/${job_id}"
    log="${LOG_DIR}/${job_id}.log"
    append_job "${job_id}" "A" "EleutherAI/pythia-160m-deduped" "${seed}" "${layer}" "iid" "" \
      "5000" "100000" "50000" "128" "4" "256" "8,16,32" "2000" "3000" "350" "600" \
      "1200" "1200" "2500" "${SOURCE_MANIFEST}" "${out}" "${log}" "iid_confirmatory"
  done
done

append_job "A_gpt2_s42_L4_iid" "A" "gpt2" "42" "4" "iid" "" \
  "4500" "80000" "50000" "128" "8" "256" "4,8,16,32" "1800" "3000" "300" "600" \
  "1200" "1200" "2500" "${SOURCE_MANIFEST}" "${OUT_DIR}/A_gpt2_s42_L4_iid" "${LOG_DIR}/A_gpt2_s42_L4_iid.log" "pos_control"
append_job "A_p70_s42_L4_iid" "A" "EleutherAI/pythia-70m-deduped" "42" "4" "iid" "" \
  "4500" "80000" "50000" "128" "8" "256" "4,8,16,32" "1600" "3000" "300" "600" \
  "1200" "1200" "2500" "${SOURCE_MANIFEST}" "${OUT_DIR}/A_p70_s42_L4_iid" "${LOG_DIR}/A_p70_s42_L4_iid.log" "pos_control"
for layer in 2 4; do
  job_id="A_p14_s42_L${layer}_iid_smoke"
  append_job "${job_id}" "A" "EleutherAI/pythia-14m-deduped" "42" "${layer}" "iid" "" \
    "300" "5000" "2000" "128" "16" "128" "4,8,16" "800" "1200" "140" "300" \
    "500" "500" "1000" "${SOURCE_MANIFEST}" "${OUT_DIR}/${job_id}" "${LOG_DIR}/${job_id}.log" "smoke_control"
done

# Stage B: source holdout (LOSO), Pythia-160M layers 3/4 seeds 42-44
for holdout in "FineWeb-Edu" "Pile-CC" "Github" "PubMed Abstracts" "ArXiv"; do
  for seed in 42 43 44; do
    for layer in 3 4; do
      safe_holdout="$(echo "${holdout}" | tr ' ' '_' | tr '/' '_')"
      job_id="B_p160_s${seed}_L${layer}_srcHoldout_${safe_holdout}"
      append_job "${job_id}" "B" "EleutherAI/pythia-160m-deduped" "${seed}" "${layer}" "source_holdout" "${holdout}" \
        "0" "120000" "60000" "128" "4" "256" "8,16,32" "2000" "3000" "350" "600" \
        "1300" "1300" "2500" "${SOURCE_MANIFEST}" "${OUT_DIR}/${job_id}" "${LOG_DIR}/${job_id}.log" "source_holdout"
    done
  done
done

# Stage C: corpus holdout, Pythia-160M layers 3/4 seeds 42-44
for seed in 42 43 44; do
  for layer in 3 4; do
    job_id="C_p160_s${seed}_L${layer}_corpusHoldout"
    append_job "${job_id}" "C" "EleutherAI/pythia-160m-deduped" "${seed}" "${layer}" "corpus_holdout" "" \
      "0" "120000" "70000" "128" "4" "256" "8,16,32" "2000" "3000" "350" "600" \
      "1300" "1300" "3000" "${SOURCE_MANIFEST}" "${OUT_DIR}/${job_id}" "${LOG_DIR}/${job_id}.log" "corpus_holdout"
  done
done

python "${SUMMARIZER}" --run_root "${RUN_ROOT}" || true

for gpu in 4 5 6 7; do
  session="msae-pilot6-g${gpu}-${TS}"
  wlog="${LOG_DIR}/${session}.log"
  tmux new-session -d -s "${session}" \
    "bash -lc 'set -euo pipefail; cd ${REPO_ROOT}; export PYTHONUNBUFFERED=1; \
     python -u ${WORKER} --manifest ${MANIFEST} --worker ${session} --gpu ${gpu} \
     --repo_root ${REPO_ROOT} --pilot_script ${SCRIPT} --summarizer_script ${SUMMARIZER} \
     --run_root ${RUN_ROOT} 2>&1 | tee ${wlog}'"
  echo "[ok] started ${session}"
done

echo "RUN_ROOT=${RUN_ROOT}"
echo "MANIFEST=${MANIFEST}"
echo "SOURCE_MANIFEST=${SOURCE_MANIFEST}"
tmux ls | rg "msae-pilot6-"

