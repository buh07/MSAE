# Atlas v3.1 attempt 5 numerical-QA stop

## Decision

Attempt 5 is **technically invalid and stopped before full extraction**. The frozen protocol said that either uniform-position translation control failing the elementwise equivalence gate terminates the study. Both EWT and GUM failed both controls. No threshold was changed, no failed QA was promoted, no full-extraction authorization was issued, no scientific endpoint was opened, and no neural training ran.

The machine-readable stop record is `pilot_runs/20260803_atlas_discovery_v3_1_attempt5/ATTEMPT5_TECHNICALLY_INVALID.json` (SHA-256 `5e65243341a71215dddb3500f868b1a1464a25b21b640d92bd6533be3b08d368`).

## Frozen-gate results

| Source | repeated identical inference | derived atol | uniform +16 | prefix-position-only |
|---|---:|---:|---:|---:|
| EWT | max absolute error 0 | 5e-7 + 5e-6 relative | FAIL | FAIL |
| GUM | max absolute error 0 | 5e-7 + 5e-6 relative | FAIL | FAIL |

The signed QA artifacts are retained in the unique staging directories rather than in the promoted `numerical_qa/` directory. This is intentional fail-closed behavior.

## Diagnostic characterization (not a scientific endpoint)

The shift-control differences were deterministic rather than replay noise. In float16 inference, median absolute element differences were roughly 2.4e-4--4.9e-4, 99th percentiles were roughly 1.6e-3--2.0e-3, and maximum rowwise relative-L2 changes ranged from 0.00149 to 0.00370. The largest absolute differences were 0.125 (EWT uniform), 0.0078125 (EWT prefix-only), 0.25 (GUM uniform), and 0.03125 (GUM prefix-only). Difference values occur on float16 quantization increments.

This pattern is consistent with deterministic finite-precision effects: a global RoPE phase translation is invariant in real arithmetic, but separately evaluated absolute phases need not produce elementwise-identical layer activations in half precision. That explanation is an inference, not established by attempt 5; the formal conclusion remains only that the frozen measurement implementation failed its gate.

## Why this is not threshold relaxation

Attempt 5 remains failed. A successor may change the numerical estimator only as a new, disclosed attempt. The cleanest candidate is float32 score-bearing inference, a fresh deterministic QA subset that excludes every attempt-5 QA pair, the unchanged elementwise formula and hard ceiling, and a new adversarial review before inference. The attempt-5 QA pairs should also be excluded from successor intervention endpoints so observed technical residuals cannot enter score-bearing estimates.
