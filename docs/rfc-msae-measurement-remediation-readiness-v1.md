# PLAN — MSAE measurement-remediation readiness v1

> Written 2026-08-20. This is an additive, no-experiment implementation plan.
> It does not amend or retry any frozen Atlas/MSAE result.

## Goal

Prepare a fail-closed, unit-tested **three-stage** contract for the next
independent MSAE measurement study: label/provenance readiness may qualify a
separately reviewed calibration-replay stage; calibrated technical readiness may
qualify separately reviewed confirmation scoring; and postscore endpoint
eligibility may qualify a decision review. None of these software statuses is an
operator authorization to launch work.

## Non-goals

- Do not run model inference, activation extraction, probe fitting, GPU jobs,
  training, sweeps, or tmux launchers.
- Do not rerun, relax, reinterpret, overwrite, or repair Atlas completion v1 or
  measurement v2 result artifacts in place.
- Do not inspect or open the blind-final payload.
- Do not select a K2/K3/shared/relation-aware architecture.
- Do not select a confirmation dataset from neural outcomes.
- Do not infer numerical tolerances from confirmation or final data.

## Constraints

- The repository is highly dirty. The exact write allowlist is:
  `docs/rfc-msae-measurement-remediation-readiness-v1.md`,
  `scripts/msae_measurement_remediation_v1.py`,
  `tests/test_msae_measurement_remediation_v1.py`,
  `configs/msae_measurement_remediation_v1/draft.json`, and new files under
  `reports/provenance/msae_measurement_remediation_v1/`. No other path may
  change during this work.
- Before implementation, create `BASELINE.json` under that provenance root. It
  records the write allowlist; `git status`; process/tmux/GPU-process snapshots;
  SHA-256 inventories for `data/atlas_v1`, `data/atlas_completion_v1`,
  `configs/atlas`, `configs/atlas_completion`,
  `configs/atlas_completion_continuation`, `configs/atlas_measurement_v2`,
  `results/atlas`, `pilot_runs/20260801_atlas_completion_v1`,
  `pilot_runs/20260802_atlas_completion_diagnostic_continuation_v1`, and
  `pilot_runs/20260802_atlas_measurement_v2_4`; the exact scripts
  `msa_completion_common.py`, `run_msae_refit_worker.py`,
  `run_msae_specificity.py`, `run_msae_stability.py`,
  `verify_msae_completion.py`, `msae_measurement_v2.py`,
  `audit_msae_measurement_v2.py`, `run_msae_measurement_v2.py`, and
  `msae_measurement_v2_run.py`; and the four final checkpoint paths/digests
  declared in `configs/atlas_measurement_v2/run.json`.
  `FINAL_STATIC_VERIFICATION.json` must reproduce the protected inventory and
  fail on any non-allowlisted dirty-path delta. The baseline also records file
  type, size, and SHA-256 for every path returned by
  `git status --porcelain=v1 -z -uall`, including already modified and untracked
  files; final verification compares content, deletion, replacement, and status
  identity and rejects any new non-allowlisted status path. The immutability
  claim is limited to this explicit protected set plus the complete set of
  pre-existing dirty paths, not every clean file in the repository. Python
  bytecode/cache roots are redirected outside the repository.
- Existing reviewed pure utilities in `scripts/msae_measurement_v2.py` are reused
  rather than copied. The new draft records their SHA-256 as a dependency.
- Every new utility is CPU-only, deterministic, side-effect-free, and accepts
  in-memory metadata/arrays. It may not import Torch, Transformers, datasets,
  networking, subprocess, or launcher code.
- A prospective study is `blocked` unless all required prerequisites are ready;
  finite subordinate values remain visible and are never replaced by zero.
- Unit tests and static checks are allowed. They are software verification, not
  experiments. No existing experiment CLI or launcher may be invoked. Static
  and runtime tripwires forbid dynamic imports, eval/exec, Torch/model/dataset
  imports, network/process/tmux APIs, and filesystem writes from the new module.

## Grounding and design-bank clarification

- Deterministic code queries found `draw_group_multiplicities` in
  `scripts/msa_completion_common.py:800`, and found the historical global
  stability predicate in `scripts/run_msae_stability.py:47` with verifier reuse
  in `scripts/verify_msae_completion.py:637`.
- The historical specificity implementation uses `model_representations` only
  within `scripts/run_msae_specificity.py`; its old `group_summary` is also
  imported by the old pilot and verifier. These frozen paths will not be edited.
- The existing measurement-v2 utility already provides document-support audits,
  representation caches with canonical pooling, explicit endpoint status,
  task/family CKA, delta CKA, and nuisance-residualized CKA. This plan adds only
  the missing prospective readiness and functional-reproducibility contracts.
- The design ledger returned no matching canonical entry for this scope. The
  reviewed Atlas-v2 prescore RFC is therefore treated as historical design input,
  not silently modified canon.

## Approach

Add `scripts/msae_measurement_remediation_v1.py`, a small pure module layered on
the reviewed measurement-v2 primitives. It will provide:

1. a deterministic, calibration-only numerical-tolerance selector over an
   explicitly ordered, componentwise-nondecreasing **tolerance ladder**, with
   role/provenance checks and no confirmation/final-data path;
2. endpoint-specific functional **reproducibility** summaries for recovery,
   leakage, and signed selectivity that preserve task/checkpoint finite values
   and keep `ineligible` separate from `not_run`;
3. thin stage-specific readiness adapters over the already reviewed
   `aggregate_endpoint_records` precedence engine; they report every blocker but
   never emit an operator launch authorization;
4. a machine-readable draft config whose deliberately unset fields demonstrate
   fail-closed behavior and bind the reused dependency digest.

The module will not write caches or load datasets. Its only I/O helper verifies
the canonical imported origin and SHA-256 of the reused measurement-v2 module.
Dataset-specific adapters and launch code remain future, separately reviewed
work after a real candidate source is proposed.

### Stage A — label/provenance readiness

This aggregate may return `stage_ready=true` only for the narrow purpose
`calibration_replay_candidate`. Required records are: candidate confirmation
source named; immutable source/revision digest; independent grouping provenance;
label-only support audit; required construct inventory; counterfactual-template
technical specification; ordered tolerance ladder frozen as a prescore candidate;
and dependency attestation. Replay results are **not** required at this stage.
An external signed review is still required to authorize calibration-only model
calls.

### Stage B — calibrated technical readiness

This aggregate may return `stage_ready=true` only for the narrow purpose
`confirmation_scoring_candidate`. It requires Stage A eligible plus successful
calibration-only repeated inference, a selected replay tolerance, exact cached
no-op/hash replay, canonical pooling QA, and counterfactual cache/alignment QA.
It explicitly rejects calibration records whose role is discovery, confirmation,
final, blind, or private. An external signed review is still required to launch
confirmation scoring.

### Stage C — postscore decision eligibility

This aggregate may return `stage_ready=true` only for the narrow purpose
`decision_review_candidate`. It requires Stage B eligible plus every registered
required localization, functional reproducibility, collateral, counterfactual,
and baseline endpoint. Optional endpoints are preserved but do not enter the
conjunction. It does not train, select an architecture, or promote a paper claim.

Every adapter uses endpoint statuses `eligible`, `ineligible`, and `not_run`.
Only the adapter boundary uses `stage_ready`; the word `authorized` is reserved
for a later signed operator record that this implementation cannot create.

### Calibration replay estimand

- One calibration stratum is fixed by identical source-role, model, checkpoint,
  code, environment, dtype, pooling/reduction-path, row-ID, and input digests.
  Every digest is a 64-character SHA-256 hex value. The role must be exactly
  `calibration`.
- A stratum contains exactly one named reference evaluation plus at least three
  uniquely named repeat evaluations (at least four arrays total). Evaluation IDs
  and array digests must be unique; row IDs must be unique, non-empty, and
  identical in order; all arrays must have the same non-empty shape and contain
  finite float32 values.
- All unordered evaluation pairs are compared. For coordinate `i`, pairwise
  `error_i=abs(x_i-y_i)` and `scale_i=max(abs(x_i),abs(y_i))` are computed in
  float64.
- A tolerance candidate `(atol,rtol)` passes a stratum iff for every pair and
  coordinate, `safety_factor * error_i <= atol + rtol * scale_i`. The
  `safety_factor` is a finite prescore value strictly greater than one.
- The candidate ladder is a non-empty sequence, not a Cartesian grid. Both
  coordinates are finite/nonnegative, entries are unique, and every later entry
  is componentwise no smaller with at least one strict increase. Selection is
  the first candidate in this total order that passes **every required
  calibration stratum**. No passing candidate returns `ineligible`; there is no
  extrapolation. The result includes the full stratum-by-candidate pass matrix,
  pair/coordinate counts, observed maxima, selected index/value, and rationale.
- The ladder, safety factor, required strata, and pairing rule must be frozen by
  a separate prescore review before any calibration arrays are produced. The
  checked-in draft leaves them unset; synthetic unit-test ladders are not study
  thresholds or preregistered values.

### Functional reproducibility estimand

- Inputs are registered checkpoint records with distinct checkpoint IDs and
  distinct training seeds, registered representative tasks, and the three finite
  real metrics `recovery`, `leakage`, and signed `selectivity`. These metrics are
  intentionally not clipped to `[0,1]`.
- At least three checkpoints are required mechanically; the future config fixes
  a larger minimum (normally five for a model-generalization claim) before
  scoring. No interval or model-level p-value is inferred from three checkpoints.
- For a task/metric, the descriptive estimand reports all checkpoint values, all
  registered pairwise signed and absolute differences, mean, minimum, maximum,
  and maximum spread. It is complete only when every registered checkpoint is
  `eligible` with a finite value. `ineligible` takes precedence over `not_run`;
  available values remain descriptive.
- A prescore nonnegative maximum-spread threshold is separately fixed for each
  metric. A complete task is reproducible iff its maximum spread is no larger
  than that metric's threshold. Stable negative selectivity remains a localization
  failure; reproducibility never implies scientific success.
- Family values are constructed **task first**: within each checkpoint, take the
  equal-weight macro mean over the frozen representative tasks only when all are
  eligible; then apply the same registered-checkpoint spread estimand. Available
  task/checkpoint means are labeled descriptive and cannot populate the complete
  family value. Missingness in one family cannot erase another family's output.
- There is no bootstrap CI in this utility. Training seed is the outer unit;
  document resampling cannot manufacture more model seeds.

**Alternative considered and rejected:** patching
`run_msae_specificity.py`/`run_msae_stability.py` in place would break the clear
lineage of the frozen completion and make old results appear retroactively
repairable.

**Simpler option considered:** documentation alone would record the desired
policy but would not make accidental authorization, confirmation-derived replay
tolerances, or global missingness coupling mechanically impossible. The proposed
pure module is the smallest executable guard.

**Relevant ADRs:** none; the design query returned no match.

## Milestones

- [ ] **M0 — Protected-state baseline.** Create the exact baseline/protected
  inventory and capture process/tmux/GPU-process state before any implementation
  file is created. Acceptance: every allowlisted path is absent except this RFC
  and provenance baseline; all protected files hash successfully; the baseline
  records pre-existing dirty paths so later changes are attributable.
- [ ] **M1 — Prospective replay calibration.** Add calibration-role and digest
  validation plus deterministic ordered-ladder selection. Acceptance: tests cover exact
  repeats, ladder-boundary selection, no-candidate failure, all-pairs coverage,
  safety factor, multi-stratum selection, full pass matrix, nonfinite/misaligned
  or empty arrays, duplicate IDs/digests, invalid/mixed provenance, malformed or
  incomparable ladders, order invariance of input mappings, and refusal of every
  non-calibration role.
- [ ] **M2 — Endpoint-specific functional reproducibility.** Add the precisely
  defined task/family checkpoint-spread summaries without a global all-family
  finite predicate. Acceptance: tests cover unbounded/signed finite metrics,
  distinct seeds, pairwise deltas, thresholds, task-first family aggregation,
  insufficient checkpoints, stable-negative selectivity, and independent family
  missingness.
- [ ] **M3 — Three fail-closed readiness contracts and draft config.** Add thin
  adapters over `aggregate_endpoint_records`, local dependency-origin/digest
  verification, and an unset draft config. Acceptance: each stage has the exact
  required inputs above; Stage A does not depend on replay results; Stage B does;
  Stage C adds postscore endpoints; all blockers are reported; optional endpoints
  cannot rescue/block; an empty required set is invalid; no adapter can emit an
  operator authorization; and the checked-in draft is blocked.
- [ ] **M4 — Documentation and verification.** Document how a future candidate
  becomes eligible and how this work relates to the historical v1/v2 artifacts.
  Acceptance: targeted unit tests, Python compilation, strict static/runtime
  side-effect tripwires, protected-state comparison, and config validation pass;
  no experiment/run/result artifact is created. M4 updates this RFC's checkboxes
  and deviations log; no second documentation path is created.

## Definition of done

- [ ] The protected-state comparison proves that no tracked or untracked
  historical result, run, freeze, checkpoint, old scoring script, or other
  non-allowlisted dirty path changed after the baseline.
- [ ] Numerical tolerance selection is possible only for an explicit
  `calibration` role, requires at least three aligned finite repeats, selects from
  a prescore-ordered componentwise ladder, and returns `ineligible` rather than
  extrapolating beyond the ladder.
- [ ] Functional reproducibility uses the frozen task-first/checkpoint-spread
  estimand independently by task and family for all three registered metrics,
  with explicit status/reasons and retained finite subordinate values.
- [ ] Stage A, B, and C readiness are separate required-only conjunctions; each
  reports all blockers, optional endpoints are neutral, and none can emit a
  launch/operator authorization.
- [ ] The draft config is schema-validated, dependency-digest-bound, and remains
  intentionally blocked because no new study is authorized.
- [ ] New tests are deterministic, CPU-only, network-free, and cover unhappy
  paths; targeted tests and compilation pass.
- [ ] No experiment, GPU process, activation extraction, probe fit, model load,
  dataset download, or tmux session is launched.

## Verification plan

- Tests: `.venv-atlas/bin/python -m pytest -q tests/test_msae_measurement_remediation_v1.py`.
- Syntax: `.venv-atlas/bin/python -m py_compile scripts/msae_measurement_remediation_v1.py`.
- Static boundary: a strict positive import allowlist plus AST rejection of
  `__import__`, dynamic import, `eval`, `exec`, process/network/tmux/model APIs,
  and filesystem-write surfaces; the draft-config test checks all stages blocked.
- Runtime boundary: monkeypatch socket, subprocess, `os.system`/all spawn APIs,
  Torch/model/dataset imports, and write APIs while importing the module and
  exercising every public in-memory function. The one dependency verifier is
  exercised separately with read-only access to its single canonical file.
- Provenance: use `PYTHONPYCACHEPREFIX` outside the repository and disable pytest
  cache; capture and compare before/after process, tmux, GPU-process, protected
  inventories, and non-allowlisted dirty-path hashes.
- Diff audit: inspect only the new RFC/module/config/test files, then run an
  independent adversarial review of the exact worktree paths.
- Explicitly do **not** run any research smoke, audit CLI, model script, pipeline,
  launcher, or experiment command.

## Risks and one-way doors

- The tolerance ladder and readiness schema could become a one-way scientific
  commitment if frozen. They remain labeled `draft`; freezing requires a new
  prescore scientific review before calibration inference.
- Reusing measurement-v2 utilities creates a dependency on historical source.
  The draft binds its digest and fails on drift; a future frozen study should
  vendor or freeze that dependency explicitly.
- Three repeats characterize technical reproducibility, not scientific
  uncertainty. The module and docs must not call the selected tolerance a
  confidence interval.
- Endpoint-specific reporting can expose finite descriptive values from an
  ineligible family. Status must travel with every value so those values cannot be
  promoted accidentally.

## Open questions

- The replacement confirmation source, its genuine grouping unit, and its
  independence evidence remain unset; no reasonable assumption is made here.
- The exact replay ladder, safety factor, required strata, functional spread
  thresholds, and minimum model seeds remain unset until a separate prescore
  design review. Synthetic test values exercise mechanics only.
- Whether later leakage warrants K3/shared/conditional/relation-aware modeling is
  blocked on a valid independent measurement result.

## Deviations log

- None.
