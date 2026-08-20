# Atlas completion diagnostic continuation v1

**Frozen purpose:** complete the K2 refit, stability, matched-random/sham
specificity, and cross-entropy collateral diagnostics that were authorized by the
atlas completion amendment but skipped after the primary L3 scientific stop.

This continuation is additive and diagnostic-only. It preserves the original run
root, original G1/G2 equivocal decision, failed G1a inference, locked blind final,
and no-training decision. It cannot render G1a/G2a, select a paper branch, lower the
450/500 scientifically-finite threshold, compact finite draws, or replace the
registered raw L3 pairing.

## Fixed inputs and estimators

- Base completion freeze:
  `0aac744d4d10f56cafae645fdc71ea8348bec743a5c20561d4649aedac0503ee`.
- Primary L3 stop:
  `612d94df5970236323110e6b6e050d900477738c4488e5d284aa21169becc31c`.
- All scientific config values, checkpoints, roles, estimators, tasks, sentinels,
  seeds, transforms, thresholds, resampling units, and multiplicity families are
  exactly those in `configs/atlas_completion/analysis.json`.
- The only executor-config change is the new create-once run root. Additive metadata
  explicitly denies decision promotion.
- Baseline selection is not rerun. The verified old baseline is CPU-rebound with
  exact equality of all scientific/selection-bearing fields.
- K2 point/draw `d` consumes the exact verified old raw L3 point/draw `d`. All 500
  raw pairings are prevalidated before a K2 draw process scores.

## Fixed job and stage inventory

There are exactly 16 GPU jobs and nine diagnostic stages: point plus `[0,500)` for
four K2 checkpoints; stability point plus `[0,167)`, `[167,334)`, `[334,500)`; and
one 128-transform specificity job for each checkpoint. Stability and specificity
may run independently of the non-promotable K2 outcome after the baseline rebind.

A durable collector closes every job as process-success, technical failure,
resource-not-launched, resource-timeout, process-crash, or superseded-by-stage-stop. A stage is complete/stopped only
under its frozen terminal contract; otherwise an exact collector-bound resource or
not-launched closure is reported. Partial leaves are retained but cannot produce an
inferential bound.

The frozen total budget remains 192 GPU-hours including base work. Atomic
continuation reservations use per-process ceilings of 5.0 GPU-hours for K2, 3.25
for stability, and 0.30 for specificity (54.2 GPU-hours total); each timeout is the
smaller of that ceiling and the remaining shared 24-hour stage window. These caps
are above the safety-factored pilot projections and are not scientific thresholds.
The 300-second termination grace plus a five-second accounting margin is deducted
from the soft timeout, and measured GPU-process elapsed time must remain at or
below the hard ceiling. Base actual usage is the schema-aware ledger of the six
immutable terminals with recorded GPU time—pilot v8/v9/v10, baseline, L3, and
L4—totaling 11.157119510886776 GPU-hours; earlier pilots without terminal resource
accounting are explicitly unavailable rather than counted as zero.

If a worker fails to service `SIGINT` during the 300-second grace and is killed by
the runtime supervisor, the runner writes a create-once, config/freeze/deadline/
reservation/GPU-bound `resource_timeout` record and job terminal using monotonic
elapsed accounting. It does not invent a stage terminal. The collector classifies
that stage `resource_incomplete`, retains partial leaves descriptively, and emits no
inferential summary. Same-UUID scoring-process intervals may not overlap.

Any other nonzero or output-missing launched exit without an adapter stage terminal
or matching root launch-failure record writes the analogous fully bound
`process_crash` record. The collector marks that stage `process_incomplete` and
emits no inferential summary. At runtime the observed reservation sum must equal the
assigned caps of exactly the jobs that reached reservation; 54.2 GPU-hours is the
maximum potential sum, not a requirement after valid pre-reservation closure.

## Fixed reporting and disposition

Every checkpoint, family, task, sentinel, draw ID, transform, specificity branch,
and CE collateral family is reported. Scientifically-finite flags and summaries
are replayed from primitive leaves. Inferential summaries are JSON null below 450
scientifically-finite draws. No family may be silently omitted.

The disposition is fixed regardless of diagnostic values:

- original G1 and G2: `equivocal_unchanged`;
- G1a: `invalid_unrendered`;
- G2a: `not_promotable_unrendered`;
- paper branch: `unselected`;
- training warranted: `false`;
- decision promotion allowed: `false`.

The entire old run-root path/type/size/SHA inventory is captured before the new
freeze and must match before every continuation invocation and final disposition.
The blind-final unlock must remain absent. No model training or checkpoint writing
is authorized.
