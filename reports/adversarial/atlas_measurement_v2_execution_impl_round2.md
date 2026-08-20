# VERDICT

**BLOCK**

# ONE-LINE

Round-1 provenance binding and launch-transition defects are fixed, but the new terminal validator still trusts subordinate endpoint booleans instead of independently validating endpoint reason/value consistency, so it can certify a contradictory result as supported.

# BLOCKERS

1. **Round-1 blocker 2 remains: terminal truth validation is not independent below the top-level booleans.** `validate_analysis_truth` computes eligibility from stored `measurement_eligible`, construct `eligible`, and `candidate_geometry_complete` flags, and computes support from stored `selective_k2_posfam_passed`/`candidate_geometry_passed` flags (`scripts/validate_msae_measurement_v2_terminal.py:33-55`). It never re-derives those flags from C1 measurability, C2 finite counts/intervals, specificity finite fractions/margins/no-op status, family probe/counterfactual results, or the CKA cells. A static synthetic fixture with `c1_raw_measurable=false`, `c2_finite_complete=false`, zero specificity pairs, `passed=false`, and no CKA pairs—but all of those trusted summary flags set true—was accepted as `K2_broad_position_content_selective_supported`. This directly misses the RFC requirement to validate endpoint reason/value consistency (`docs/rfc-atlas-v2-execution.md:444-453`). **Required fix:** independently recompute every decision-bearing subordinate eligibility/pass flag and reject absent, contradictory, nonfinite, or incorrectly reasoned endpoint records before recomputing the top-level truth table.

2. **The same terminal validator does not yet enforce the complete exact inventory/schema contract.** Current-attempt job names and command digests are checked, but job/lease fields are not validated as a complete schema: terminal `job`, wrapper/child PID identity, start ticks, configured role-to-GPU UUID, and the exact lease set are not compared (`scripts/validate_msae_measurement_v2_terminal.py:67-86`). Aggregation also does not enumerate and reject unexpected raw-cache or transform IDs (`scripts/validate_msae_measurement_v2_terminal.py:89-97`; `scripts/run_msae_measurement_v2.py:839-848`). These omissions leave the new M6 validator short of its claimed exact-jobs/exact-shards guarantee.

# REVISIONS

1. **Recovery stage and job authentication are still disconnected.** Recovery validates committed caches and job records in separate loops, but never requires a committed raw/transform/analysis artifact to be linked to the successful job/lease that produced it (`scripts/validate_msae_measurement_v2_terminal.py:107-143`). A cache created outside the wrapper can be accepted, then a later attempt's expected command can merely reuse it and produce a successful current-attempt job record. Bind each committed artifact/manifest to its producing attempt/job/command/lease digest.
2. **There are no focused tests for the newly added terminal validator, recovery validator, or shared terminal lock.** The reviewed test file remains unchanged at ten utility/data tests (`tests/test_msae_measurement_v2_run.py:52-147`), which is why contradictory endpoint records currently pass unnoticed.

# NITS

None beyond the revisions above.

# CHECKS RUN

- Confirmed config SHA-256 `83d6718839e0c8f359b7e888e1da7a1cce6e0af73b228ecd559a265270fbdbd8` and implementation-inventory validation: **PASS**.
- `.venv-atlas/bin/python -m pytest -q tests/test_msae_measurement_v2.py tests/test_msae_measurement_v2_run.py`: **39 passed**.
- Python compilation of the three execution modules plus the new terminal validator: **PASS**.
- Bash syntax for pipeline and launcher: **PASS**.
- Static contradictory-endpoint fixture: **incorrectly accepted** by `validate_analysis_truth` (blocking finding).
- No neural experiment, tmux launch, or GPU work was run.

# CONTRACT COVERAGE

- **Round-1 blocker 1 — FIXED.** The builder now binds current config SHA and Git HEAD (`scripts/msae_measurement_v2_run.py:656-673`); the trusted reviewer binds the builder payload and builder-key fingerprint, distinct identity, and fixed transcript/diff artifact paths and hashes (`scripts/msae_measurement_v2_run.py:705-751`); preparation and reuse invoke this verifier (`scripts/msae_measurement_v2_run.py:754-767,841-859`).
- **Round-1 blocker 2 — NOT FIXED.** Aggregate, failure, and abandonment now share a terminal flock (`scripts/run_msae_measurement_v2.py:821-889`; `scripts/run_msae_measurement_v2_pipeline.sh:73-85`; `scripts/launch_msae_measurement_v2_tmux.sh:99-115`), and exact current job names/commands plus top-level truth are checked, but endpoint reason/value and complete inventory/schema validation remain insufficient.
- **Round-1 blocker 3 — TRANSITION FIXED; AUTHENTICATION PARTIAL.** Recovery now accepts authenticated pre-owner launch roots, retains the old owner via a stale hard link until atomic coordinator replacement, validates before takeover, and increments attempt namespaces (`scripts/launch_msae_measurement_v2_tmux.sh:44-87`; `scripts/run_msae_measurement_v2_pipeline.sh:16-37`). The artifact-to-producing-job gap remains.

# UNKNOWNS

- Live recovery, shared-lock races, wrapper death, and orphan handling were not fault-injected.
- External provenance artifacts were not modified or regenerated in this review.
