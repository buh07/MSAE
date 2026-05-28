#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/jumbo/lisp/f004ndc"
MSAE_ROOT="${REPO_ROOT}/MSAE"
SCRIPT="${MSAE_ROOT}/scripts/raw_activation_separability_pilot.py"
SUMMARIZER="${MSAE_ROOT}/scripts/summarize_pilot_run.py"

TS="${TS:-$(date +%Y%m%d_%H%M%S)}"
RUN_ROOT="${MSAE_ROOT}/pilot_runs/${TS}_v5_gpufirst_balanced_multiseed"
LOG_DIR="${RUN_ROOT}/logs"
OUT_DIR="${RUN_ROOT}/outputs"
MANIFEST="${RUN_ROOT}/run_manifest.tsv"

mkdir -p "${LOG_DIR}" "${OUT_DIR}"
echo "${RUN_ROOT}" > "${MSAE_ROOT}/pilot_runs/.latest_pilot2_run_root"

cat > "${MANIFEST}" <<'MANIFEST_EOF'
session	gpu	model	seed	layer_index	max_text_samples	max_tokens_collect	context_length	batch_size	top_k_tokens	probe_ranks	probe_backend	probe_c_raw	probe_c_projected	probe_torch_max_steps_raw	probe_torch_max_steps_projected	probe_torch_patience_raw	probe_torch_patience_projected	output_dir	log_file
MANIFEST_EOF

append_manifest() {
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9" "${10}" "${11}" "${12}" "${13}" "${14}" "${15}" "${16}" "${17}" "${18}" "${19}" "${20}" \
    >> "${MANIFEST}"
}

COMMON_ARGS=(
  --dataset_name wikitext
  --dataset_config wikitext-2-raw-v1
  --dataset_split train
  --position_max 64
  --probe_max_iter 1000
  --probe_backend torch
  --probe_c_raw 0.2
  --probe_c_projected 1.0
  --probe_torch_eval_every 50
  --probe_torch_min_steps 200
  --probe_torch_token_ceiling_top1 0.995
  --probe_torch_token_ceiling_evals 3
  --probe_torch_token_ceiling_loss_eps 1e-4
  --probe_torch_lr_position_raw_highdim 0.01
  --probe_torch_lr_position_raw_highdim_threshold 768
  --c2_alt_mode linear_rank_drop
  --c2_var_v2_ratio_threshold 3.0
  --c2_var_v2_excess_floor 0.05
  --c3_v2_drop_fraction 0.25
  --skip_first_position
)

SESSION_G4="msae-pilot5-g4-${TS}"
LOG_G4="${LOG_DIR}/g4_pythia14m_smoke.log"
tmux new-session -d -s "${SESSION_G4}" \
"bash -lc 'set -euo pipefail; cd ${REPO_ROOT}; export PYTHONUNBUFFERED=1; \
for L in 2 4; do \
OUT=${OUT_DIR}/g4_pythia14m_s42_layer\${L}; mkdir -p \"\${OUT}\"; \
echo [run] gpu=4 seed=42 layer=\${L} out=\${OUT}; \
CUDA_VISIBLE_DEVICES=4 python -u ${SCRIPT} \
--model_name EleutherAI/pythia-14m-deduped \
--seed 42 --max_text_samples 300 --max_tokens_collect 5000 --context_length 128 --batch_size 16 \
--layer_index \${L} --top_k_tokens 128 --probe_ranks 4,8,16 \
--probe_torch_max_steps_raw 600 --probe_torch_max_steps_projected 1200 \
--probe_torch_batch_size 4096 --probe_torch_lr 0.05 \
--probe_torch_patience_raw 120 --probe_torch_patience_projected 300 \
--min_examples_per_class 6 --min_samples_after_filter 1200 \
${COMMON_ARGS[*]} --output_dir \"\${OUT}\"; \
python ${SUMMARIZER} --run_root ${RUN_ROOT} || true; \
done' > '${LOG_G4}' 2>&1"
append_manifest "${SESSION_G4}" "4" "EleutherAI/pythia-14m-deduped" "42" "2" "300" "5000" "128" "16" "128" "4,8,16" "torch" "0.2" "1.0" "600" "1200" "120" "300" "${OUT_DIR}/g4_pythia14m_s42_layer2" "${LOG_G4}"
append_manifest "${SESSION_G4}" "4" "EleutherAI/pythia-14m-deduped" "42" "4" "300" "5000" "128" "16" "128" "4,8,16" "torch" "0.2" "1.0" "600" "1200" "120" "300" "${OUT_DIR}/g4_pythia14m_s42_layer4" "${LOG_G4}"

SESSION_G5="msae-pilot5-g5-${TS}"
LOG_G5="${LOG_DIR}/g5_p70_then_p160_s43.log"
tmux new-session -d -s "${SESSION_G5}" \
"bash -lc 'set -euo pipefail; cd ${REPO_ROOT}; export PYTHONUNBUFFERED=1; \
OUT=${OUT_DIR}/g5_pythia70m_s42_layer4; mkdir -p \"\${OUT}\"; \
echo [run] gpu=5 seed=42 model=pythia70m layer=4 out=\${OUT}; \
CUDA_VISIBLE_DEVICES=5 python -u ${SCRIPT} \
--model_name EleutherAI/pythia-70m-deduped \
--seed 42 --max_text_samples 4500 --max_tokens_collect 80000 --context_length 128 --batch_size 8 \
--layer_index 4 --top_k_tokens 256 --probe_ranks 4,8,16,32,64,96 \
--probe_torch_max_steps_raw 1200 --probe_torch_max_steps_projected 3000 \
--probe_torch_batch_size 8192 --probe_torch_lr 0.05 \
--probe_torch_patience_raw 250 --probe_torch_patience_projected 600 \
--min_examples_per_class 10 --min_samples_after_filter 1500 \
${COMMON_ARGS[*]} --output_dir \"\${OUT}\"; \
python ${SUMMARIZER} --run_root ${RUN_ROOT} || true; \
for L in 2 3 4; do \
OUT=${OUT_DIR}/g5_pythia160m_s43_layer\${L}; mkdir -p \"\${OUT}\"; \
echo [run] gpu=5 seed=43 model=pythia160m layer=\${L} out=\${OUT}; \
CUDA_VISIBLE_DEVICES=5 python -u ${SCRIPT} \
--model_name EleutherAI/pythia-160m-deduped \
--seed 43 --max_text_samples 5000 --max_tokens_collect 100000 --context_length 128 --batch_size 4 \
--layer_index \${L} --top_k_tokens 256 --probe_ranks 8,16,32,64 \
--probe_torch_max_steps_raw 1200 --probe_torch_max_steps_projected 3000 \
--probe_torch_batch_size 8192 --probe_torch_lr 0.05 \
--probe_torch_patience_raw 250 --probe_torch_patience_projected 600 \
--min_examples_per_class 10 --min_samples_after_filter 1500 \
${COMMON_ARGS[*]} --output_dir \"\${OUT}\"; \
python ${SUMMARIZER} --run_root ${RUN_ROOT} || true; \
done' > '${LOG_G5}' 2>&1"
append_manifest "${SESSION_G5}" "5" "EleutherAI/pythia-70m-deduped" "42" "4" "4500" "80000" "128" "8" "256" "4,8,16,32,64,96" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g5_pythia70m_s42_layer4" "${LOG_G5}"
append_manifest "${SESSION_G5}" "5" "EleutherAI/pythia-160m-deduped" "43" "2" "5000" "100000" "128" "4" "256" "8,16,32,64" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g5_pythia160m_s43_layer2" "${LOG_G5}"
append_manifest "${SESSION_G5}" "5" "EleutherAI/pythia-160m-deduped" "43" "3" "5000" "100000" "128" "4" "256" "8,16,32,64" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g5_pythia160m_s43_layer3" "${LOG_G5}"
append_manifest "${SESSION_G5}" "5" "EleutherAI/pythia-160m-deduped" "43" "4" "5000" "100000" "128" "4" "256" "8,16,32,64" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g5_pythia160m_s43_layer4" "${LOG_G5}"

SESSION_G6="msae-pilot5-g6-${TS}"
LOG_G6="${LOG_DIR}/g6_gpt2_then_p160_s44.log"
tmux new-session -d -s "${SESSION_G6}" \
"bash -lc 'set -euo pipefail; cd ${REPO_ROOT}; export PYTHONUNBUFFERED=1; \
OUT=${OUT_DIR}/g6_gpt2_s42_layer4; mkdir -p \"\${OUT}\"; \
echo [run] gpu=6 seed=42 model=gpt2 layer=4 out=\${OUT}; \
CUDA_VISIBLE_DEVICES=6 python -u ${SCRIPT} \
--model_name gpt2 \
--seed 42 --max_text_samples 4500 --max_tokens_collect 80000 --context_length 128 --batch_size 8 \
--layer_index 4 --top_k_tokens 256 --probe_ranks 4,8,16,32,64,96 \
--probe_torch_max_steps_raw 1200 --probe_torch_max_steps_projected 3000 \
--probe_torch_batch_size 8192 --probe_torch_lr 0.05 \
--probe_torch_patience_raw 250 --probe_torch_patience_projected 600 \
--min_examples_per_class 10 --min_samples_after_filter 1500 \
${COMMON_ARGS[*]} --output_dir \"\${OUT}\"; \
python ${SUMMARIZER} --run_root ${RUN_ROOT} || true; \
for L in 2 3 4; do \
OUT=${OUT_DIR}/g6_pythia160m_s44_layer\${L}; mkdir -p \"\${OUT}\"; \
echo [run] gpu=6 seed=44 model=pythia160m layer=\${L} out=\${OUT}; \
CUDA_VISIBLE_DEVICES=6 python -u ${SCRIPT} \
--model_name EleutherAI/pythia-160m-deduped \
--seed 44 --max_text_samples 5000 --max_tokens_collect 100000 --context_length 128 --batch_size 4 \
--layer_index \${L} --top_k_tokens 256 --probe_ranks 8,16,32,64 \
--probe_torch_max_steps_raw 1200 --probe_torch_max_steps_projected 3000 \
--probe_torch_batch_size 8192 --probe_torch_lr 0.05 \
--probe_torch_patience_raw 250 --probe_torch_patience_projected 600 \
--min_examples_per_class 10 --min_samples_after_filter 1500 \
${COMMON_ARGS[*]} --output_dir \"\${OUT}\"; \
python ${SUMMARIZER} --run_root ${RUN_ROOT} || true; \
done' > '${LOG_G6}' 2>&1"
append_manifest "${SESSION_G6}" "6" "gpt2" "42" "4" "4500" "80000" "128" "8" "256" "4,8,16,32,64,96" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g6_gpt2_s42_layer4" "${LOG_G6}"
append_manifest "${SESSION_G6}" "6" "EleutherAI/pythia-160m-deduped" "44" "2" "5000" "100000" "128" "4" "256" "8,16,32,64" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g6_pythia160m_s44_layer2" "${LOG_G6}"
append_manifest "${SESSION_G6}" "6" "EleutherAI/pythia-160m-deduped" "44" "3" "5000" "100000" "128" "4" "256" "8,16,32,64" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g6_pythia160m_s44_layer3" "${LOG_G6}"
append_manifest "${SESSION_G6}" "6" "EleutherAI/pythia-160m-deduped" "44" "4" "5000" "100000" "128" "4" "256" "8,16,32,64" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g6_pythia160m_s44_layer4" "${LOG_G6}"

SESSION_G7="msae-pilot5-g7-${TS}"
LOG_G7="${LOG_DIR}/g7_p160_s42_layers234.log"
tmux new-session -d -s "${SESSION_G7}" \
"bash -lc 'set -euo pipefail; cd ${REPO_ROOT}; export PYTHONUNBUFFERED=1; \
for L in 2 3 4; do \
OUT=${OUT_DIR}/g7_pythia160m_s42_layer\${L}; mkdir -p \"\${OUT}\"; \
echo [run] gpu=7 seed=42 model=pythia160m layer=\${L} out=\${OUT}; \
CUDA_VISIBLE_DEVICES=7 python -u ${SCRIPT} \
--model_name EleutherAI/pythia-160m-deduped \
--seed 42 --max_text_samples 5000 --max_tokens_collect 100000 --context_length 128 --batch_size 4 \
--layer_index \${L} --top_k_tokens 256 --probe_ranks 8,16,32,64 \
--probe_torch_max_steps_raw 1200 --probe_torch_max_steps_projected 3000 \
--probe_torch_batch_size 8192 --probe_torch_lr 0.05 \
--probe_torch_patience_raw 250 --probe_torch_patience_projected 600 \
--min_examples_per_class 10 --min_samples_after_filter 1500 \
${COMMON_ARGS[*]} --output_dir \"\${OUT}\"; \
python ${SUMMARIZER} --run_root ${RUN_ROOT} || true; \
done' > '${LOG_G7}' 2>&1"
append_manifest "${SESSION_G7}" "7" "EleutherAI/pythia-160m-deduped" "42" "2" "5000" "100000" "128" "4" "256" "8,16,32,64" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g7_pythia160m_s42_layer2" "${LOG_G7}"
append_manifest "${SESSION_G7}" "7" "EleutherAI/pythia-160m-deduped" "42" "3" "5000" "100000" "128" "4" "256" "8,16,32,64" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g7_pythia160m_s42_layer3" "${LOG_G7}"
append_manifest "${SESSION_G7}" "7" "EleutherAI/pythia-160m-deduped" "42" "4" "5000" "100000" "128" "4" "256" "8,16,32,64" "torch" "0.2" "1.0" "1200" "3000" "250" "600" "${OUT_DIR}/g7_pythia160m_s42_layer4" "${LOG_G7}"

python "${SUMMARIZER}" --run_root "${RUN_ROOT}" || true

echo "RUN_ROOT=${RUN_ROOT}"
echo "MANIFEST=${MANIFEST}"
tmux ls | rg "msae-pilot5-"
