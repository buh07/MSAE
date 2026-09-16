#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
export PYTHONDONTWRITEBYTECODE=1
export CUDA_CACHE_DISABLE=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
exec "$ROOT/.venv-atlas/bin/python" -S -B -I "$ROOT/scripts/msae_independent_measurement_v3_post_m2_gen6.py" launch-gen6
