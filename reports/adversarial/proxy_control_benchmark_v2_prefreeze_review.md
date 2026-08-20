VERDICT: SHIP
ONE-LINE: The frozen candidate now gates inference, preserves lineage, and implements the promised hierarchy without outcome-dependent paths.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)
  - scripts/proxy_control_benchmark_v2.py:214-221 — `answer_base`/`answer_cf` are contrast-token names for the position panel, not different semantic answers; document this naming in post-result methods prose.

CHECKS RUN
  - `PYTHONPATH=scripts .venv-atlas/bin/python -m pytest -q tests/test_proxy_control_benchmark_v1.py tests/test_proxy_control_benchmark_v2.py` → 17 passed.
  - `.venv-atlas/bin/python -m py_compile scripts/proxy_control_benchmark_v2.py scripts/analyze_proxy_control_benchmark_v1.py tests/test_proxy_control_benchmark_v2.py` → passed.
  - `bash -n scripts/launch_proxy_control_benchmark_v2_tmux.sh` → passed.
  - `.venv-atlas/bin/python scripts/verify_paper_claims.py` → 48 claims and 186 evidence bindings, PASS.
  - two independent `smoke` namespaces followed by byte comparison → result and terminal files identical; synthetic positive/oracle gates passed and random negative remained below its cap.
  - `verify_prepared(..., regenerate_natural=True)` → 1,152 controlled rows and 32 unique natural rows exactly regenerate; all controlled prompts are non-no-op and IDs are unique.
  - repro audit → config-derived seeds, deterministic Torch flags, offline pinned revisions, exact data hashes, no hardcoded home paths, and no credential literals in candidate source.

CONTRACT COVERAGE
  - preserve v1 → met — full import manifest verification is required before freeze and checkpoint load (`scripts/proxy_control_benchmark_v2.py:338-351,403-420,647-658`).
  - cached companion and paper update → met — create-once companion artifacts exist and the ledger verifier passes.
  - corrected behavior metric and shams → met — signed denominator, nontrivial shams, and positive/negative sign tests are explicit (`scripts/proxy_control_benchmark_v2.py:172-193,594-620`; `tests/test_proxy_control_benchmark_v2.py:13-37`).
  - hierarchical inference → met — component blocks and templates are resampled below nested model/layer/seed strata, with transfer directions retained as a fixed required pair (`scripts/proxy_control_benchmark_v2.py:961-1035`).
  - positive-control precondition → met — signed PASS lineage is polled before model loading (`scripts/proxy_control_benchmark_v2.py:671-687,696-721,917-937`).
  - no new real SAE training → met — workers only import exact v1 checkpoints; the source/test guard finds no `train_decomposition(` path.
  - free-GPU tmux launch → met — launcher filters occupied devices, requires seven free UUIDs for seven worker sessions, and keeps the analytic gate on CPU (`scripts/launch_proxy_control_benchmark_v2_tmux.sh:22-51`).
  - create-once and failure terminals → met — result namespaces use exclusive creation; worker, gate, and aggregate technical failures are terminalized.

UNKNOWNS
  - Full scientific wall time and realized behavior-effect eligibility cannot be known before the prospective panels are opened.
  - CUDA deterministic-kernel support must still be confirmed by the launched workers; failures will create `TECHNICAL_FAIL.json` rather than silently changing algorithms.
