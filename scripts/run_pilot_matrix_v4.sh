#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/jumbo/lisp/f004ndc"
MSAE_ROOT="${REPO_ROOT}/MSAE"
SCRIPT="${MSAE_ROOT}/scripts/raw_activation_separability_pilot.py"
SUMMARIZER="${MSAE_ROOT}/scripts/summarize_pilot_run.py"

TS="${TS:-$(date +%Y%m%d_%H%M%S)}"
RUN_ROOT="${MSAE_ROOT}/pilot_runs/${TS}_rankcurve_c2var_balanced"
LOG_DIR="${RUN_ROOT}/logs"
OUT_DIR="${RUN_ROOT}/outputs"
MANIFEST="${RUN_ROOT}/run_manifest.tsv"

mkdir -p "${LOG_DIR}" "${OUT_DIR}"
echo "${RUN_ROOT}" > "${MSAE_ROOT}/pilot_runs/.latest_pilot2_run_root"

cat > "${MANIFEST}" <<'EOF'
session	gpu	model	layer_index	max_text_samples	max_tokens_collect	context_length	batch_size	top_k_tokens	probe_ranks	probe_backend	probe_c_raw	probe_c_projected	probe_torch_max_steps_raw	probe_torch_max_steps_projected	probe_torch_patience_raw	probe_torch_patience_projected	output_dir	log_file
EOF

append_manifest() {
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9" "${10}" "${11}" "${12}" "${13}" "${14}" "${15}" "${16}" "${17}" "${18}" "${19}" \
    >> "${MANIFEST}"
}

SESSION_G4="msae-pilot4-g4-${TS}"
LOG_G4="${LOG_DIR}/g4_pythia14m_smoke.log"
tmux new-session -d -s "${SESSION_G4}" \
"bash -lc 'set -euo pipefail; cd ${REPO_ROOT}; export PYTHONUNBUFFERED=1; for L in 2 4; do OUT=${OUT_DIR}/g4_pythia14m_layer\${L}; mkdir -p \"\${OUT}\"; echo [run] gpu=4 layer=\${L} out=\${OUT}; CUDA_VISIBLE_DEVICES=4 python -u ${SCRIPT} --model_name EleutherAI/pythia-14m-deduped --dataset_name wikitext --dataset_config wikitext-2-raw-v1 --dataset_split train --max_text_samples 300 --max_tokens_collect 5000 --context_length 128 --batch_size 16 --layer_index \${L} --position_max 64 --top_k_tokens 128 --probe_ranks 4,8,16 --probe_max_iter 1000 --probe_backend torch --probe_c_raw 0.2 --probe_c_projected 1.0 --probe_torch_max_steps_raw 600 --probe_torch_max_steps_projected 1200 --probe_torch_batch_size 4096 --probe_torch_lr 0.05 --probe_torch_eval_every 50 --probe_torch_patience_raw 120 --probe_torch_patience_projected 300 --probe_torch_min_steps 120 --c2_alt_mode linear_rank_drop --min_examples_per_class 6 --min_samples_after_filter 1200 --skip_first_position --output_dir \"\${OUT}\"; python ${SUMMARIZER} --run_root ${RUN_ROOT} || true; done' > '${LOG_G4}' 2>&1"
append_manifest "${SESSION_G4}" "4" "EleutherAI/pythia-14m-deduped" "2" "300" "5000" "128" "16" "128" "4,8,16" "torch" "0.2" "1.0" "600" "1200" "120" "300" "${OUT_DIR}/g4_pythia14m_layer2" "${LOG_G4}"
append_manifest "${SESSION_G4}" "4" "EleutherAI/pythia-14m-deduped" "4" "300" "5000" "128" "16" "128" "4,8,16" "torch" "0.2" "1.0" "600" "1200" "120" "300" "${OUT_DIR}/g4_pythia14m_layer4" "${LOG_G4}"

SESSION_G5="msae-pilot4-g5-${TS}"
LOG_G5="${LOG_DIR}/g5_pythia70m.log"
OUT_G5="${OUT_DIR}/g5_pythia70m_layer4"
mkdir -p "${OUT_G5}"
tmux new-session -d -s "${SESSION_G5}" "cd '${REPO_ROOT}' && export PYTHONUNBUFFERED=1 && CUDA_VISIBLE_DEVICES=5 python -u '${SCRIPT}' --model_name EleutherAI/pythia-70m-deduped --dataset_name wikitext --dataset_config wikitext-2-raw-v1 --dataset_split train --max_text_samples 4500 --max_tokens_collect 80000 --context_length 128 --batch_size 8 --layer_index 4 --position_max 64 --top_k_tokens 256 --probe_ranks 4,8,16,32,64,96 --probe_max_iter 1000 --probe_backend torch --probe_c_raw 0.2 --probe_c_projected 1.0 --probe_torch_max_steps_raw 1200 --probe_torch_max_steps_projected 3000 --probe_torch_batch_size 8192 --probe_torch_lr 0.05 --probe_torch_eval_every 50 --probe_torch_patience_raw 250 --probe_torch_patience_projected 600 --probe_torch_min_steps 200 --c2_alt_mode linear_rank_drop --min_examples_per_class 10 --min_samples_after_filter 1500 --skip_first_position --output_dir '${OUT_G5}' > '${LOG_G5}' 2>&1"
append_manifest "${SESSION_G5}" "5" "EleutherAI/pythia-70m-deduped" "4" "4500" "80000" "128" "8" "256" "4,8,16,32,64,96" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_G5}" "${LOG_G5}"

SESSION_G6="msae-pilot4-g6-${TS}"
LOG_G6="${LOG_DIR}/g6_gpt2.log"
OUT_G6="${OUT_DIR}/g6_gpt2_layer4"
mkdir -p "${OUT_G6}"
tmux new-session -d -s "${SESSION_G6}" "cd '${REPO_ROOT}' && export PYTHONUNBUFFERED=1 && CUDA_VISIBLE_DEVICES=6 python -u '${SCRIPT}' --model_name gpt2 --dataset_name wikitext --dataset_config wikitext-2-raw-v1 --dataset_split train --max_text_samples 4500 --max_tokens_collect 80000 --context_length 128 --batch_size 8 --layer_index 4 --position_max 64 --top_k_tokens 256 --probe_ranks 4,8,16,32,64,96 --probe_max_iter 1000 --probe_backend torch --probe_c_raw 0.2 --probe_c_projected 1.0 --probe_torch_max_steps_raw 1200 --probe_torch_max_steps_projected 3000 --probe_torch_batch_size 8192 --probe_torch_lr 0.05 --probe_torch_eval_every 50 --probe_torch_patience_raw 250 --probe_torch_patience_projected 600 --probe_torch_min_steps 200 --c2_alt_mode linear_rank_drop --min_examples_per_class 10 --min_samples_after_filter 1500 --skip_first_position --output_dir '${OUT_G6}' > '${LOG_G6}' 2>&1"
append_manifest "${SESSION_G6}" "6" "gpt2" "4" "4500" "80000" "128" "8" "256" "4,8,16,32,64,96" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_G6}" "${LOG_G6}"

SESSION_G7="msae-pilot4-g7-${TS}"
LOG_G7="${LOG_DIR}/g7_pythia160m_layers1to4.log"
tmux new-session -d -s "${SESSION_G7}" \
"bash -lc 'set -euo pipefail; cd ${REPO_ROOT}; export PYTHONUNBUFFERED=1; for L in 1 2 3 4; do OUT=${OUT_DIR}/g7_pythia160m_layer\${L}; mkdir -p \"\${OUT}\"; echo [run] gpu=7 layer=\${L} out=\${OUT}; CUDA_VISIBLE_DEVICES=7 python -u ${SCRIPT} --model_name EleutherAI/pythia-160m-deduped --dataset_name wikitext --dataset_config wikitext-2-raw-v1 --dataset_split train --max_text_samples 5000 --max_tokens_collect 100000 --context_length 128 --batch_size 4 --layer_index \${L} --position_max 64 --top_k_tokens 256 --probe_ranks 8,16,32,64 --probe_max_iter 1000 --probe_backend torch --probe_c_raw 0.2 --probe_c_projected 1.0 --probe_torch_max_steps_raw 1200 --probe_torch_max_steps_projected 3000 --probe_torch_batch_size 8192 --probe_torch_lr 0.05 --probe_torch_eval_every 50 --probe_torch_patience_raw 250 --probe_torch_patience_projected 600 --probe_torch_min_steps 200 --c2_alt_mode linear_rank_drop --min_examples_per_class 10 --min_samples_after_filter 1500 --skip_first_position --output_dir \"\${OUT}\"; python ${SUMMARIZER} --run_root ${RUN_ROOT} || true; done' > '${LOG_G7}' 2>&1"
append_manifest "${SESSION_G7}" "7" "EleutherAI/pythia-160m-deduped" "1" "5000" "100000" "128" "4" "256" "8,16,32,64" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g7_pythia160m_layer1" "${LOG_G7}"
append_manifest "${SESSION_G7}" "7" "EleutherAI/pythia-160m-deduped" "2" "5000" "100000" "128" "4" "256" "8,16,32,64" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g7_pythia160m_layer2" "${LOG_G7}"
append_manifest "${SESSION_G7}" "7" "EleutherAI/pythia-160m-deduped" "3" "5000" "100000" "128" "4" "256" "8,16,32,64" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g7_pythia160m_layer3" "${LOG_G7}"
append_manifest "${SESSION_G7}" "7" "EleutherAI/pythia-160m-deduped" "4" "5000" "100000" "128" "4" "256" "8,16,32,64" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g7_pythia160m_layer4" "${LOG_G7}"

python "${SUMMARIZER}" --run_root "${RUN_ROOT}" || true

echo "RUN_ROOT=${RUN_ROOT}"
echo "MANIFEST=${MANIFEST}"
tmux ls | rg "msae-pilot4-"
