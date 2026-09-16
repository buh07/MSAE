#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
export PYTHONPATH="$ROOT/scripts"
exec "$ROOT/.venv-atlas/bin/python" "$ROOT/scripts/msae_independent_measurement_v1.py" launch
