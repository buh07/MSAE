VERDICT: SHIP
ONE-LINE: Scientific estimand, freshness, firewalls, lineage, GPU enforcement, and terminal handling are ready for controlled freezing.

BLOCKERS
  - None.

REVISIONS
  - None.

NITS
  - tests/test_joint_controllability_assay_v5.py:86 — assign `v5.ROOT` through `monkeypatch.setattr` to avoid module-state leakage if tests are reordered.

CHECKS RUN
  - `.venv-atlas/bin/python -m py_compile scripts/joint_controllability_assay_v5.py scripts/analyze_joint_controllability_v4_1_pythia.py` → passed
  - `bash -n scripts/launch_joint_controllability_assay_v5_tmux.sh` → passed
  - `.venv-atlas/bin/python -m pytest -q tests/test_joint_controllability_assay_v5.py` → 12 passed
  - offline `cache-preflight` → PASS; Gemma weight index and all required shards content-hashed
  - `preservation-verify` → PASS
  - `preflight` → PASS; 22 candidate files, no training or method authorization
  - deterministic-prepare record audit → current config hash matches; two rebuilds and accepted tree share all seven file hashes
  - cache-attestation inspection → Gemma `model.safetensors.index.json` present
  - diagnostic inspection → deterministic role mapping true, design rank 8/22, identifiability false

CONTRACT COVERAGE
  - Exact v4.1 preservation → met — complete preservation verification passes
  - Narrow hash-bound claim and analysis-only diagnostic → met — exact hashes, generator, JSON, and markdown are inventoried
  - Counterbalanced 192-component panels and 42 within-component shams → met — incidence and estimand tests pass
  - Token-length and one-token-label constraints → met — exhaustive prepared-row checks pass
  - Freshness and split/source disjointness → met — pinned revisions, fingerprints, exclusion hashes, and deterministic rebuild agree
  - Model-specific eligibility and distinct-family barrier → met — unique-family registry/counting and both-source authorization enforced
  - Confirmation firewall → met — behavioral test proves an ineligible confirmation worker never invokes scoring
  - No representation method or training path → met — no reachable v5 CLI path and authorization flags remain false
  - Offline/cache lineage → met — offline assertions, content-hashed weights/index/metadata, and launch-time revalidation exist
  - Physical GPU mapping → met — UUID selection, visibility, runtime validation, and aggregate verification agree
  - Output isolation and terminals → met — exclusive roots, atomic terminals, bounded waits, and early-failure publication are implemented
  - Pre-freeze sequencing → met — absence of `FREEZE.json` is intentional pending inclusion of this review

UNKNOWNS
  - Final freeze inventory and post-freeze verification remain to be checked by the separate frozen-candidate review.
  - Actual tmux/GPU liveness can only be confirmed at launch.
