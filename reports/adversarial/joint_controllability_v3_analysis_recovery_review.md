VERDICT: SHIP
ONE-LINE: Recovery now enforces exact v3 lineage, faithful aggregation, isolated output, and COMPLETE-last preservation semantics.

BLOCKERS
  - None.

REVISIONS
  - None.

CHECKS RUN
  - `check-plan --path PLAN_JOINT_CONTROLLABILITY_V3_RECOVERY_V4.md` -> PASS.
  - `PYTHONPATH=scripts pytest -q tests/test_joint_controllability_v3_analysis_recovery.py` -> 7 passed.
  - `python -m py_compile scripts/recover_joint_controllability_v3_analysis.py` -> passed.
  - `verify_lineage(DEFAULT_SOURCE)` -> 51,456 rows, seven exact shards, 25 exact source-tree files.
  - Recovery manifest digest -> matched the embedded SHA-256.
  - Import closure -> neither Torch nor Transformers loaded.
  - Inlined `block_interval` -> matches the hash-bound v2 implementation.
  - Original/recovery aggregation comparison -> grouping, seeds, metrics, thresholds, stages, and decisions match.

CONTRACT COVERAGE
  - Preserve v3 byte-for-byte -> met.
  - Exact v3 input lineage -> met.
  - Exact estimators, thresholds, groupings, and seeds -> met.
  - Native JSON in a separate namespace -> met.
  - Require 51,456 rows and 402 cells -> met.
  - No inference or training path -> met.

UNKNOWNS
  - Ruff is unavailable in the active environment.

origin: independent forked adversarial reviewer
