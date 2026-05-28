#!/usr/bin/env bash
set -euo pipefail

# Small-model raw-activation separability pilot for 16GB-class GPUs.
# Usage:
#   bash MSAE/scripts/run_small_model_pilot.sh
#
# Override defaults via env vars, e.g.:
#   MODEL=EleutherAI/pythia-14m-deduped MAX_TOKENS=40000 bash ...

MODEL="${MODEL:-EleutherAI/pythia-14m-deduped}"
DATASET_NAME="${DATASET_NAME:-wikitext}"
DATASET_CONFIG="${DATASET_CONFIG:-wikitext-2-raw-v1}"
DATASET_SPLIT="${DATASET_SPLIT:-train}"
OUTPUT_DIR="${OUTPUT_DIR:-MSAE/pilot_outputs/raw_sep_${MODEL##*/}}"

MAX_TEXT_SAMPLES="${MAX_TEXT_SAMPLES:-2000}"
MAX_TOKENS="${MAX_TOKENS:-60000}"
CONTEXT_LEN="${CONTEXT_LEN:-128}"
BATCH_SIZE="${BATCH_SIZE:-8}"
LAYER_INDEX="${LAYER_INDEX:-3}"
POSITION_MAX="${POSITION_MAX:-128}"
TOPK_TOKENS="${TOPK_TOKENS:-256}"
RANKS="${RANKS:-8,16,32}"

python MSAE/scripts/raw_activation_separability_pilot.py \
  --model_name "${MODEL}" \
  --dataset_name "${DATASET_NAME}" \
  --dataset_config "${DATASET_CONFIG}" \
  --dataset_split "${DATASET_SPLIT}" \
  --max_text_samples "${MAX_TEXT_SAMPLES}" \
  --max_tokens_collect "${MAX_TOKENS}" \
  --context_length "${CONTEXT_LEN}" \
  --batch_size "${BATCH_SIZE}" \
  --layer_index "${LAYER_INDEX}" \
  --position_max "${POSITION_MAX}" \
  --top_k_tokens "${TOPK_TOKENS}" \
  --probe_ranks "${RANKS}" \
  --skip_first_position \
  --output_dir "${OUTPUT_DIR}"

