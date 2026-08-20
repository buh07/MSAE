#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/pcc_stage_a0_audit.py"
RUN_TS="$(date +%Y%m%d_%H%M%S)"
RUN_ROOT="${REPO_ROOT}/pilot_runs/${RUN_TS}_pcc_stage_a0"
OUT_DIR="${RUN_ROOT}/outputs"
LOG_DIR="${RUN_ROOT}/logs"
MANIFEST="${RUN_ROOT}/run_manifest.tsv"
SESSIONS_TXT="${RUN_ROOT}/tmux_sessions.txt"
STATUS_TXT="${RUN_ROOT}/launch_status.txt"

mkdir -p "${OUT_DIR}" "${LOG_DIR}"

export HF_HOME="/jumbo/lisp/f004ndc/.cache/huggingface"
export HF_DATASETS_CACHE="/jumbo/lisp/f004ndc/.cache/huggingface/datasets"
export XDG_CACHE_HOME="/jumbo/lisp/f004ndc/.cache"
export TMPDIR="/jumbo/lisp/f004ndc/tmp"
mkdir -p "${HF_DATASETS_CACHE}" "${TMPDIR}"

GIT_HASH="$(cd "${REPO_ROOT}" && git rev-parse HEAD 2>/dev/null || true)"

cat > "${MANIFEST}" <<'TSV'
job_id	gpu	seed	lambda_inc	layer	model_name	checkpoint_path	output_dir	log_path	tmux_session
TSV
: > "${SESSIONS_TXT}"
: > "${STATUS_TXT}"

append_job() {
  local job_id="$1"
  local gpu="$2"
  local seed="$3"
  local lambda_inc="$4"
  local layer="$5"
  local model_name="$6"
  local checkpoint_path="$7"
  local output_dir="$8"
  local log_path="$9"
  local tmux_session="${10}"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "${job_id}" "${gpu}" "${seed}" "${lambda_inc}" "${layer}" "${model_name}" \
    "${checkpoint_path}" "${output_dir}" "${log_path}" "${tmux_session}" >> "${MANIFEST}"
}

launch_job() {
  local job_id="$1"
  local gpu="$2"
  local seed="$3"
  local lambda_inc="$4"
  local layer="$5"
  local model_name="$6"
  local checkpoint_path="$7"

  local output_dir="${OUT_DIR}/${job_id}"
  local log_path="${LOG_DIR}/${job_id}.log"
  local session="pcc-a0-${job_id}-${RUN_TS}"

  mkdir -p "${output_dir}"

  append_job "${job_id}" "${gpu}" "${seed}" "${lambda_inc}" "${layer}" "${model_name}" \
    "${checkpoint_path}" "${output_dir}" "${log_path}" "${session}"
  echo "${session}" >> "${SESSIONS_TXT}"

  tmux new-session -d -s "${session}" \
    "bash -lc '
      set -euo pipefail
      export PYTHONUNBUFFERED=1
      export HF_HOME="${HF_HOME}"
      export HF_DATASETS_CACHE="${HF_DATASETS_CACHE}"
      export XDG_CACHE_HOME="${XDG_CACHE_HOME}"
      export TMPDIR="${TMPDIR}"
      cd "${REPO_ROOT}"
      echo [start] job=${job_id} gpu=${gpu} seed=${seed} lambda=${lambda_inc} layer=${layer} model=${model_name} checkpoint=${checkpoint_path}
      CUDA_VISIBLE_DEVICES=${gpu} python -u "${SCRIPT}" \
        --checkpoint_path "${checkpoint_path}" \
        --model_name "${model_name}" \
        --layer_index "${layer}" \
        --seed "${seed}" \
        --device cuda \
        --dtype auto \
        --output_dir "${output_dir}" \
        --git_commit_hash "${GIT_HASH}" \
        --context_length 192 \
        --model_batch_size 12 \
        --probe_backend torch \
        --probe_torch_max_steps 1200 \
        --probe_torch_batch_size 8192 \
        --probe_torch_lr 0.02 \
        --probe_torch_scheduler cosine \
        --probe_torch_eval_every 50 \
        --probe_torch_patience 300 \
        --probe_torch_min_steps 200 \
        --probe_torch_lr_position_raw_highdim 0.01 \
        --probe_torch_lr_position_raw_highdim_threshold 768 \
        --min_examples_per_class 20 \
        --max_train_sentences_ud 4000 \
        --max_eval_sentences_ud 1000 \
        --max_train_sentences_wnut 3394 \
        --max_eval_sentences_wnut 1009 \
        --cache_dir "${RUN_ROOT}/cache"
      echo [done] job=${job_id}
    ' > "${log_path}" 2>&1"

  echo "launched ${job_id} on gpu ${gpu} as ${session}" | tee -a "${STATUS_TXT}"
}

launch_job \
  "pcc_a0_g4_L3_s42_inc1e2" \
  "4" "42" "1e-2" "3" "EleutherAI/pythia-160m-deduped" \
  "${REPO_ROOT}/pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g4_L3_s42_inc1e2/checkpoints/final_step249244_tok1000000016.pt"

launch_job \
  "pcc_a0_g5_L3_s43_inc1e2" \
  "5" "43" "1e-2" "3" "EleutherAI/pythia-160m-deduped" \
  "${REPO_ROOT}/pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g5_L3_s43_inc1e2/checkpoints/final_step249244_tok1000000016.pt"

launch_job \
  "pcc_a0_g6_L3_s44_inc1e2" \
  "6" "44" "1e-2" "3" "EleutherAI/pythia-160m-deduped" \
  "${REPO_ROOT}/pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g6_L3_s44_inc1e2/checkpoints/final_step249675_tok1000000042.pt"

launch_job \
  "pcc_a0_g7_L3_s42_inc0" \
  "7" "42" "0" "3" "EleutherAI/pythia-160m-deduped" \
  "${REPO_ROOT}/pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g7_L3_s42_inc0/checkpoints/final_step249244_tok1000000016.pt"

{
  echo "run_root=${RUN_ROOT}"
  echo "manifest=${MANIFEST}"
  echo "sessions=${SESSIONS_TXT}"
  echo "launched_at=$(date --iso-8601=seconds)"
} | tee -a "${STATUS_TXT}"
