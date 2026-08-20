# PLAN — Trained-Control Studies R2 Technical Recovery

## Goal

Recover both failed R1 executions without changing either scientific estimand, frozen panels,
method inventory, thresholds, seeds, or decision logic. Preserve both failures, correct the two
runtime-only implementation defects, independently review the exact recoveries, and relaunch both
in new namespaces.

## Constraints

- Preserve both R1 candidates, reviews, locks, freezes, launch manifests, logs, partial outputs, and
  provenance events by exact hash before implementing R2.
- Do not edit or resume either R1 result/provenance namespace.
- Reuse the exact R1 prepared fit/development/confirmation payload bytes; do not run `prepare`.
- Do not open development or confirmation during diagnosis, tests, candidate review, or freezing.
- The only execution-code changes are (A) evaluate SAE tensors under `torch.no_grad()` and detach
  before NumPy conversion, and (B) make runtime matrix QA use the same float64 rank and condition
  computation already used by the frozen prescore audit.
- Keep all methods, hyperparameters, thresholds, bootstraps, panels, generators, and seeds unchanged.
- R2 must use isolated source/config/test/review/lock/result/provenance/log/manifest/tmux namespaces.
- Treat both R1 executions as terminal technical failures; neither may be resumed in place.

## Failure diagnoses

### SAE-capacity R1

All fits completed and development opened, but the first SAE evaluation attempted
`p.cpu().numpy()` on a tensor retaining the SAE parameter autograd graph. Evaluation mode does not
disable gradient tracking. The run therefore raised `Can't call numpy() on Tensor that requires
grad`. The repair is technical: perform frozen-model SAE prediction under `torch.no_grad()` and
use detached arrays at every NumPy boundary. One native development score may have existed
transiently in memory before the exception, but no score was serialized, logged, inspected, or
used for a decision; confirmation remained unopened. Preservation must include a signed exposure
attestation and an audit proving the absence of confirmation access and serialized scientific
results.

### Causal-manifold R1

`fit_matrix_audit()` evaluates rank on a float64 copy through `matrix_qa()`. In contrast,
`fit_registry()` computes the SVD on float64 but obtains `delta_rank` and `ambient_rank` from the
original float32 arrays. NumPy's dtype-dependent default rank tolerance can therefore assign a
different effective rank, and the runtime condition calculation then indexes the float64 singular
spectrum using the inconsistent float32 rank. R1 consequently raised
`registered donor fit rank/conditioning failed` even though its frozen prescore trace-matrix audit
recorded full rank and conditions around 581–649.

## Approach

1. Hash and preserve both complete R1 failure states.
2. Create isolated R2 successors bound to that preservation record and both R1 freezes.
3. Wrap SAE evaluation predictions in `torch.no_grad()`, detach every NumPy conversion, and add a
   regression that reaches the failed evaluation path with a loaded frozen SAE.
4. Centralize donor/ambient rank and condition computation through `matrix_qa()` (float64), use
   those records in `fit_registry()`, and emit the actual diagnostic values on failure.
5. Add regression tests that reproduce the float32/float64 mismatch and prove runtime QA equals the
   frozen prescore audit for all four generators without opening later panels.
6. Generate a canonical protocol-parity artifact that proves config equality after removing only
   the following JSON pointers: `/namespace`; `/runtime/candidate_manifest`,
   `/runtime/candidate_review`, `/runtime/freeze`, `/runtime/frozen_review`,
   `/runtime/generator_lock`, `/runtime/launch_manifest`, `/runtime/launcher_log`,
   `/runtime/output_root`, `/runtime/provenance_root`, `/runtime/review_binding`, and
   `/runtime/tmux_session`; plus the R2-only addition `/recovery_lineage/r1_freezes`.
   `/runtime/prepared_root`, both existing `/recovery_lineage/original_freezes` bindings, both
   hard timeouts, and every scientific field must remain exactly equal. Also generate an
   allowlisted source diff with two separately enumerated categories: (a) namespace/governance
   binding constants for config, plan, tests, launcher, parity, reviews, locks, manifests, outputs,
   and preservation validation; and (b) executable scientific-body changes limited to A's
   no-grad/detach repair and B's rank/condition diagnostic repair. Bind the parity artifact into
   both candidates and locks.
7. Run CPU and CUDA candidate QA and the focused test/launcher suite, then obtain independent `/adversarial` review of
   the exact candidate.
8. Create the generator locks and R2 freezes from the already prepared byte-identical payloads; obtain
   a second independent frozen-artifact review and verify all bindings.
9. Launch both R2 successors once in tmux on free GPUs and return after process, GPU UUID, and
   fit-access handshakes are verified.

## Milestones and acceptance criteria

### M1 — Preserve and diagnose

- R1 failure preservation lists every file under both partial result and provenance roots plus
  both candidates, reviews, locks, freezes, launch manifests, and launcher logs.
- Preservation records recursive file counts and hashes; existing empty directories/root state;
  logs, manifests, events, and partial checkpoints; and explicit absence of confirmation access,
  terminal results, and confirmation artifacts. Verification rejects corruption, deletion, and
  added files.
- The preservation record itself has a reported SHA-256.
- A signed exposure attestation records that A may have computed one transient native development
  score, that it was not persisted or inspected, and that B did not open development.
- Regressions demonstrate the autograd/NumPy and dtype-dependent rank mismatches that caused R1.

### M2 — Implement isolated R2 recovery

- R2 never writes to R1 paths.
- Both R2 scripts validate the R1 preservation record and both R1 freezes before candidate, freeze,
  and run.
- SAE evaluation reaches NumPy only through explicitly detached tensors and the regression executes
  the formerly failing prediction/norm-match path.
- Runtime donor/ambient matrix QA uses float64 consistently and matches frozen audit values.
- A value-preservation regression proves A's pre-detach predictions, patched logits, metrics, and
  gates are exactly equal or within the already registered numerical tolerance after detachment.
- B regressions prove basis projectors, singular spectra, ranks, conditions, and serialized
  diagnostics match the float64 frozen reference for all generators.
- A canonical parity artifact applies exactly the JSON-pointer list in Approach step 6 and fails on
  any other difference. It separately records the namespace/governance source-binding changes and
  proves executable scientific-body changes are limited to the two diagnosed repairs. Both
  candidates and generator locks bind the parity-artifact hash.
- `prepare` rejects because the reused payload roots already exist; payload hashes and mtimes are
  recorded unchanged. Each R2 freeze's payload records equal its R1 freeze byte-for-byte.

### M3 — Review and freeze

- Focused tests pass.
- CPU candidates, CUDA candidates, `bash -n`, and launcher mocks for success, partial failure,
  timeout, signal, stale-owner recovery, PID remapping, namespace collision, and cleanup pass.
- The exact candidate receives `VERDICT: SHIP` bound to its SHA-256.
- The exact freeze receives `VERDICT: SHIP` bound to its SHA-256.
- `verify-frozen` passes and proves byte-identical payload reuse.

### M4 — Relaunch

- Both R2 successors launch on free physical GPUs with exact PID-to-UUID evidence.
- Both R2 processes are alive and have recorded fit access before control returns.
- No result claim is made before terminal completion.

## Risks

- **Hidden second failures:** candidate and focused runtime tests must exercise the SAE prediction
  conversion path and at least one bridge fit-registry path far enough to write a checkpoint, not
  merely call the isolated helpers.
- **Outcome-conditioned protocol change:** transitive hash comparison must show all scientific
  config sections unchanged through the canonical field-removal parity algorithm and allowlisted
  source diff.
- **Namespace collision:** launcher preflight must fail if any R2 output/provenance/log/manifest or
  tmux namespace already exists.
- **GPU contention:** retain UUID locks and worker ancestry/handshake checks.
- **Long runtime:** ETA must be presented as an estimate. A's unchanged 24-hour and B's unchanged
  36-hour hard timeouts are separate safety ceilings, not ETAs.

## Definition of done

Both R1 failures are immutable and hash-preserved; both R2 successors contain only the reviewed
runtime and recovery-lineage repairs; tests, candidate reviews, frozen reviews, and frozen
verification pass; and both R2 experiments are running in tmux on verified free GPUs with
evidence-based ETAs.
