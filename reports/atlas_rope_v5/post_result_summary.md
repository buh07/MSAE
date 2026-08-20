# Atlas v3.5 Attempt 9 — terminal technical result

## Decision

Attempt 9 is **terminal at held-out GUM technical validation**. The signed terminal is
`TERMINAL_GUM_VALIDATION_FAILED` with `no_retry_authorized=true`. Do not rerun GUM, change a
threshold, open GENTLE, authorize science, or execute the atlas under this attempt.

This is a result about the **numerical measurement protocol**, not about position/content
separation. The scientific atlas was never run.

## What passed

- Attempt 8 remained retired and unpromoted.
- Its opened EWT bundle was imported only as signed calibration history.
- Exact cached replay passed.
- Repeated live reference inference was byte-identical.
- The calibration union contained 1,272 rows and selected frozen caps:
  - `atol=2e-5`, `rtol=5e-6`;
  - relative L2 `1e-5`;
  - cosine distance `1e-11`.
- The EWT hooked/unhooked diagnostic observer check was byte-exact on arrays, row IDs, population,
  and C-order bytes. Diagnostic values were not used to tune caps.
- All 16 fresh GUM sentinels passed their strict zero-failure rules:
  - uniform shift: 8 pairs / 16 rows; maximum relative L2 `1.113e-6`;
  - prefix-position-only: 8 pairs / 8 rows; maximum relative L2 `1.944e-6`.
- 29 of the 30 GUM shift-by-length grid cells passed.

## What failed

The single fatal cell was `9-16|shift=64`:

- coordinate failures: 1 element in 1 row, within the cell budgets of 30 elements / 2 rows;
- relative-L2 failures: 1 row, against a budget of 0;
- cosine failures: 1 row, against a budget of 0;
- maximum relative L2: `1.02437885e-5` versus cap `1e-5`;
- maximum cosine distance: `2.83223445e-11` versus cap `1e-11`;
- required coordinate atol: `9.81171322e-5` versus cap `2e-5`.

The fatal row was position 2 of sentence `GUM_podcast_wrestling-68` in document
`GUM_podcast_wrestling`. Only coordinate 393 exceeded `atol + rtol*|reference|`:

- reference: `-10.5126819611`;
- shifted: `-10.5128326416`;
- absolute difference: `1.50680542e-4`;
- allowed bound: `7.25634098e-5`.

A second cell, `9-16|shift=16`, had one coordinate failure but remained valid because its row-level
relative L2 and cosine stayed under cap. Across the full GUM grid there were only two coordinate
failures in two rows, but the preregistered zero-failure row-level criteria made the shift-64 row
fatal.

## Numerical diagnosis

The EWT technical diagnostic supports this finite-precision propagation sequence:

1. At layer 0, pre-rotary Q/K are still invariant under a global position-ID translation.
2. Float32 rotary evaluation already differs slightly from the float64 rotary reference at layer 0.
   The largest local-rotary relative L2 observed was `2.814e-7`.
3. Aligned post-rotary Q/K and theoretically invariant attention logits therefore differ at layer 0.
4. Those differences first appear in propagated pre-rotary Q/K and hidden states at layer 1.
5. Nonlinear attention/residual computation can amplify them in later layers. In the diagnostic
   subset, aligned/post and propagated/pre Q reached maximum relative L2 about `4.073e-4`, logits
   about `4.311e-4`, and hidden states about `1.292e-4`.

This makes stochastic inference or cache/reduction mismatch unlikely: cached replay, repeated live
references, and hooked-vs-unhooked observer runs were exact. The best current explanation is that
RoPE translation is mathematically equivariant but only approximately so in the frozen float32
implementation; small phase/trigonometric rounding differences enter immediately and are amplified
in an input-, shift-, head-, and layer-dependent way.

That causal statement remains an inference. The layer diagnostic used selected EWT development
examples, not the fatal GUM row, so it identifies a plausible mechanism rather than proving which
operation generated coordinate 393's error.

## Downstream state

- `GUM_PASS.json`: absent.
- GENTLE grid/PASS: absent and unauthorized after the terminal.
- science authorization: absent.
- Attempt-9 scientific activation caches/results: absent.
- neural training/checkpoints: absent.

## Scientific claim boundary

Supported: exact replay and live-repeat reproducibility work; approximate RoPE equivariance is
small but nonuniform and the EWT-calibrated caps did not generalize to the complete GUM grid.

Unsupported: any conclusion about absolute, boundary, sequential, contextual, lexical, or
relational signal organization. Attempt 9 did not reach those endpoints.

Primary machine-readable audit: `reports/atlas_rope_v5/post_result_summary.json`.
