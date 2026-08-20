VERDICT: SHIP
freeze_sha256: 6d74a766ff4a1ce51f887a5de44f5939673bfb344dcad188056c863151cc44f3
ONE-LINE: The frozen v2 candidate is prospective, failure-closed, hierarchy-aware, and ready for one-shot launch.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)
  - scripts/proxy_control_benchmark_v2.py:214-221 — position-panel contrast tokens retain generic `answer_base`/`answer_cf` field names; explain this in the post-result methods, without changing the frozen rows.

CHECKS RUN
  - `proxy_control_benchmark_v2.py preflight` against the bound freeze → PASS; output namespace absent; candidate inventory SHA-256 `c0f5c9fe2fd7cb87b77f016059b8766472d21b3ce27fef504627094168eddb76`.
  - `PYTHONPATH=scripts .venv-atlas/bin/python -m pytest -q tests/test_proxy_control_benchmark_v1.py tests/test_proxy_control_benchmark_v2.py` → 17 passed.
  - Python compilation and launcher `bash -n` → passed.
  - `verify_paper_claims.py` → 48 claims, 186 evidence bindings, PASS.
  - deterministic synthetic smoke in two create-once namespaces → byte-identical results and terminals; ground-truth/oracle checks PASS and random negative remains below cap.
  - label-only source rebuild → exact hashes; 1,152 controlled rows, 32 unique natural rows, disjoint development/test templates, 32 test blocks per source/concept, and nontrivial shams.
  - launch-state audit → eight GPUs idle, no colliding tmux sessions, and v2 output/launch-manifest namespaces absent.
  - reproducibility audit → seeded Python/NumPy/Torch, deterministic flags, offline exact model revisions, pinned lock file, exact dataset fingerprints/hashes, no hardcoded local-home path, no candidate-source credential literal.

CONTRACT COVERAGE
  - preserve v1 unchanged → met — imported artifact manifest is fully checked before freeze and lazily rechecked at each checkpoint/proxy load.
  - cached analysis companion → met — sign-aligned, stratified, block-aware, Pareto, and capacity analyses are create-once and require no model forward.
  - paper update → met — potency-versus-precision prose is evidence-ledger bound and the claim verifier passes.
  - signed and sham-corrected v2 → met — natural-effect sign is retained; every controlled sham is a distinct matched intervention.
  - prospective hierarchy → met — test-template rows are nested in vocabulary/component blocks, then model/layer/seed bootstrap strata; transfer directions remain a required fixed pair.
  - oracle and positive controls → met — exact development-only behavior-gradient objective is frozen; synthetic PASS lineage is required before model loading.
  - no new SAE training → met — workers import exact v1 float16 checkpoints into float32 evaluation modules and expose no training call.
  - endpoint isolation and decisions → met — controlled and naturalistic endpoints are separated; numerical gates and result-independent interpretation branches are frozen.
  - tmux/GPU execution → met — seven scientific worker sessions select only free UUIDs; Qwen layers are serialized on one GPU; analytic gate and aggregate run separately.
  - unhappy paths → met — freeze drift, data drift, gate failure, worker error, namespace collision, occupied GPUs, and incomplete shards fail closed with explicit terminals or launcher errors.

UNKNOWNS
  - Scientific eligibility and functional outcomes are intentionally unknown until the frozen panels run.
  - Full CUDA execution may expose an unsupported deterministic kernel; the guarded worker will terminalize that as a technical failure rather than relaxing determinism.
