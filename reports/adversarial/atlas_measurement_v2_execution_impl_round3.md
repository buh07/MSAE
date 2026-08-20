# VERDICT

**BLOCK**

# ONE-LINE

Round-2 summary-flag contradictions and inventory/producer binding are fixed, but terminal validation still accepts decision-bearing task and specificity summaries that are untethered from their underlying probe metrics/draws, so the claimed independent frozen-input comparison is incomplete.

# BLOCKERS

1. **Task endpoint validation re-derives booleans from already-derived summaries, not from the underlying frozen measurements.** `validate_analysis_truth` trusts `c1_raw_signal` and the stored recovery interval `finite`/`lower` fields, then checks that the flags agree with those values (`scripts/validate_msae_measurement_v2_terminal.py:41-58`). It never requires or checks `results["evaluations"]`, never recomputes `c1_raw_signal = raw C1 macro-F1 - 1/C`, and never recomputes recovery/selectivity points or intervals from the stored F1/bootstrap draws. Indeed, the new supposedly valid fixture contains no `evaluations` object at all and is accepted (`tests/test_msae_measurement_v2_run.py:139-179`). An analyzer defect can therefore fabricate internally consistent recovery summaries and still receive `COMPLETE.json`. This does not satisfy independent endpoint reason/value consistency or the frozen-input comparison required at M6.

2. **Specificity validation still permits impossible count/interval records and cannot independently validate its estimands.** It checks `finite_fraction == finite_pairs/pairs` and derives pass flags from stored interval bounds (`scripts/validate_msae_measurement_v2_terminal.py:62-88`), but does not enforce `0 <= finite_pairs <= pairs`, `0 <= finite_control_pairs <= control_pairs`, or `0 <= interval.finite <= 500`. Thus, for example, `pairs=20`, `finite_pairs=40`, `finite_fraction=2.0`, and a `finite=600` interval can be internally consistent under this validator and eligible. It also cannot recompute the specificity intervals because per-draw values or a deterministic cache recomputation are not validated here. These impossible values are decision-bearing through `counterfactual_complete` (`scripts/validate_msae_measurement_v2_terminal.py:86,106-121`).

# REVISIONS

1. Add adversarial fixtures for each subordinate contract, not only C1 raw-signal contradiction: missing `evaluations`, F1/raw-signal mismatch, recovery interval/draw mismatch, impossible specificity counts, specificity margin mismatch, missing/extra CKA cells, producer-command drift, and extra raw/transform/lease/job IDs.

# NITS

None.

# CHECKS RUN

- Confirmed config SHA-256 `c40702ecfb2c759a797fd5ce2c07fd04ae57a1e354a9b3b3e137159ec6e3f5ed`; config and implementation inventory load: **PASS**.
- `.venv-atlas/bin/python -m pytest -q tests/test_msae_measurement_v2.py tests/test_msae_measurement_v2_run.py`: **40 passed**.
- Python compilation of execution, GPU-runner, and terminal-validator modules: **PASS**.
- Bash syntax for launcher and pipeline: **PASS**.
- No neural experiment, tmux launch, or GPU work was run.

# CONTRACT COVERAGE

- **Round-2 blocker 1 — PARTIALLY FIXED.** Task/family/specificity/CKA summary flags and top-level truth are now cross-checked (`scripts/validate_msae_measurement_v2_terminal.py:41-122`), and the prior contradictory-summary fixture is rejected. Base-metric-to-summary consistency remains unchecked.
- **Round-2 blocker 2 — FIXED for requested inventories.** Exact raw/transform directories, current job records, lease fields, PID lineage, GPU UUID assignment, command hashes, and exact lease/start inventories are validated (`scripts/validate_msae_measurement_v2_terminal.py:141-198`).
- **Round-2 producer-link revision — FIXED.** Raw, transform, and analysis artifacts bind producing job/command identifiers and require successful matching lease/start/terminal records during aggregation and recovery (`scripts/run_msae_measurement_v2.py:70-73,206-213,250-267,806-827`; `scripts/validate_msae_measurement_v2_terminal.py:133-138,175-198,208-247`).

# UNKNOWNS

- Live recovery, terminal-lock races, and real GPU numerical behavior were not exercised.
