#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)";cd "$ROOT"
export CUDA_VISIBLE_DEVICES=-1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONHASHSEED=20260805
PY="$ROOT/.venv-atlas/bin/python";CONFIG="$ROOT/configs/relational_measurement_v4/run.json";PREPARED="$ROOT/data/relational_measurement_v4/prepared.json";RUNROOT="$ROOT/results/relational_measurement_v4_opened_development1";RESULT="$RUNROOT/result.json"
AUTH="$ROOT/reports/provenance/relational_measurement_v4_authorization_v1.json";READY="$ROOT/reports/provenance/relational_measurement_v4_supervisor_ready_v1.json";START="$ROOT/reports/provenance/relational_measurement_v4_launcher_trigger_v1.json";HANDOFF="$ROOT/reports/provenance/relational_measurement_v4_owner_handoff_v1.json";OPENING="$ROOT/reports/provenance/relational_measurement_v4_opening_v1.json";CLOSURE="$ROOT/reports/provenance/relational_measurement_v4_closure_v1.json"
SMOKEA="$ROOT/reports/provenance/relational_measurement_v4_smoke_a.json";SMOKEB="$ROOT/reports/provenance/relational_measurement_v4_smoke_b.json";TESTREPORT="$ROOT/reports/provenance/relational_measurement_v4_tests.xml";REVIEW="$ROOT/reports/adversarial/relational_measurement_v4_candidate_review.md"
for path in "$PREPARED" "$RUNROOT" "$AUTH" "$READY" "$START" "$HANDOFF" "$OPENING" "$CLOSURE" "$SMOKEA" "$SMOKEB" "$TESTREPORT" "$ROOT/data/relational_measurement_v4/panels";do [[ ! -e "$path" ]]||{ echo "create-once path exists: $path" >&2;exit 2;};done
TMP="$(mktemp -d "$ROOT/.cache/relational_measurement_v4_keys.XXXXXX")";OWNER_KEY="$TMP/owner.pem";SUP_KEY="$TMP/supervisor.pem";trap 'rm -rf "$TMP"' EXIT
"$PY" scripts/relational_measurement_v4_lifecycle.py keygen --path "$OWNER_KEY" >/dev/null;"$PY" scripts/relational_measurement_v4_lifecycle.py keygen --path "$SUP_KEY" >/dev/null
PYTHONPATH="$ROOT:$ROOT/scripts" "$PY" -m pytest -q --junitxml="$TESTREPORT" tests/test_relational_measurement_v4.py tests/test_relational_objects_v3_scout.py tests/test_relational_objects_v2.py tests/test_conllu_spec.py
"$PY" scripts/run_relational_measurement_v4.py --config "$CONFIG" --mode smoke --output "$SMOKEA";"$PY" scripts/run_relational_measurement_v4.py --config "$CONFIG" --mode smoke --output "$SMOKEB";cmp "$SMOKEA" "$SMOKEB"
"$PY" scripts/run_relational_measurement_v4.py --config "$CONFIG" --mode prepare --output "$PREPARED"
"$PY" scripts/relational_measurement_v4_lifecycle.py authorize --config "$CONFIG" --prepared "$PREPARED" --output "$AUTH" --owner-key "$OWNER_KEY" --supervisor-key "$SUP_KEY" --test-report "$TESTREPORT" --smoke-a "$SMOKEA" --smoke-b "$SMOKEB" --candidate-review "$REVIEW"
NONCE="$("$PY" -c 'import secrets;print(secrets.token_hex(32))')";CANDIDATE_SHA="$(sha256sum "$CONFIG"|awk '{print $1}')";POST_TIMEOUT="$("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["runtime"]["postopening_timeout_seconds"])' "$CONFIG")"
"$PY" scripts/relational_measurement_v4_lifecycle.py supervise --authorization "$AUTH" --ready "$READY" --start-signal "$START" --handoff "$HANDOFF" --opening "$OPENING" --closure "$CLOSURE" --run-root "$RUNROOT" --prepared "$PREPARED" --result "$RESULT" --key "$SUP_KEY" --owner-key "$OWNER_KEY" --owner-script "$ROOT/scripts/run_relational_measurement_v4_owner.sh" --config "$CONFIG" --nonce "$NONCE" --namespace relational_measurement_v4_opened_development1 --candidate-sha256 "$CANDIDATE_SHA" --launcher-pid $$ --timeout 60 --post-timeout "$POST_TIMEOUT" &
SUP_PID=$!
for _ in $(seq 1 600);do [[ -s "$READY" ]]&&break;sleep .1;done
[[ -s "$READY" ]]||{ echo 'supervisor readiness timeout' >&2;kill "$SUP_PID" 2>/dev/null||true;wait "$SUP_PID"||true;exit 3;}
"$PY" scripts/relational_measurement_v4_lifecycle.py trigger --authorization "$AUTH" --ready "$READY" --output "$START" --key "$OWNER_KEY" --nonce "$NONCE" --launcher-pid $$
wait "$SUP_PID"
