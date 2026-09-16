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
  The initial porcelain-status byte stream is captured into a temporary file
  outside the repository **before** `BASELINE.json` is installed; the baseline
  is then written atomically from that snapshot and never attempts to inventory
  itself. `FINAL_STATIC_VERIFICATION.json` must reproduce the protected
  inventory and fail on any non-allowlisted dirty-path delta. The baseline also
  records file type, size, and SHA-256 for every **non-allowlisted** path returned
  by `git status --porcelain=v1 -z -uall`, including already modified and
  untracked files; final verification compares content, deletion, replacement,
  and status identity and rejects any new non-allowlisted status path.
  Pre-existing allowlisted paths, including this RFC, are recorded in a separate
  mutable-work inventory with their starting hashes; their final hashes and
  exact deltas are recorded rather than required to remain unchanged. The
  immutability claim is limited to the explicit protected set plus the complete
  set of pre-existing **non-allowlisted** dirty paths, not every clean file in
  the repository. Python bytecode/cache roots are redirected outside the
  repository.
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

The module will not write caches or load datasets. Its only direct path-I/O
helper verifies the canonical imported origin and SHA-256 of the reused
measurement-v2 module; raw config bytes are supplied by the caller rather than
opened by the module.
Dataset-specific adapters and launch code remain future, separately reviewed
work after a real candidate source is proposed.

The module exports exactly `payload_sha256`, `select_replay_tolerance`,
`summarize_functional_reproducibility`, `validate_draft_config`,
`verify_dependency`, `build_stage_a`, `build_stage_b`, and `build_stage_c` via
`__all__`; reviewed dependency functions are imported under private aliases.
`verify_dependency` resolves
`Path(__file__).with_name("msae_measurement_v2.py")`, rejects a symlink or any
realpath other than that literal sibling, verifies that the imported module's
`__file__` resolves to the same file, and hashes it against the digest stored in
the bound config. Every stage builder calls this verifier afresh and embeds the
newly observed path/digest; no stage accepts a caller-asserted dependency
attestation or merely trusts a predecessor's copy.

### Versioned artifact binding shared by all stages

Every public config-consuming function accepts `(raw_config_bytes,
expected_raw_config_sha256, ...)`. It hashes the unmodified bytes and rejects a
mismatch **before** parsing. The strict UTF-8 JSON loader rejects a BOM, trailing
bytes, duplicate object keys, non-string keys, and nonfinite numbers and requires
a top-level object. All registries are derived only from that parsed object; a
caller cannot supply a replacement registry. The draft's protocol ID, schema
versions, exact ordered checkpoint/stratum/task registries, and exact endpoint
registries are therefore bound to the SHA-256 of the checked-in raw bytes
without placing a circular self-digest inside the file.

All registry, selector-result, and stage-artifact lineage hashes use one private
serializer, exactly
`json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
allow_nan=False).encode("utf-8") + b"\n"`, after recursively rejecting values
outside the JSON domain, non-string dictionary keys, and nonfinite floats. Raw
config hashes use the raw file bytes and do **not** use this serializer. Payload
hashing remains the explicitly newline-free binary framing defined below.

Every supplied generic endpoint evidence record has the exact schema
`{schema_version, protocol_config_sha256, endpoint_name, category, status,
reasons, evidence_artifact_sha256, observed_value}` with no extra keys;
`schema_version` is fixed by the config, `status` is one of the three registered
statuses, `reasons` is an ordered unique list of nonempty strings,
`evidence_artifact_sha256` is non-null for `eligible`/`ineligible` and null only
for `not_run`, and `observed_value` is JSON-domain data. Missing required
evidence becomes an explicit `not_run` record; malformed evidence is an input
error.

Every stage artifact has an exact versioned schema with `stage`, `purpose`,
protocol-config SHA-256, dependency SHA-256, exact requirement-registry digest,
validated endpoint records, aggregate output, and `stage_ready`. The adapter
constructs the requirement list only from the bound config and sets
`stage_ready = (overall.status == "eligible")`. Optional well-formed records are
preserved but neutral; malformed optional records are input errors. It never
accepts a caller-selected required list.

Each builder freshly calls `verify_dependency`, compares its observed canonical
path/digest with the parsed config and (for B/C) predecessor artifact, and embeds
the fresh attestation. Stage B accepts the complete Stage-A artifact, recomputes
its canonical JSON SHA-256 and Stage-A aggregate from its bound records,
verifies its schema, purpose/config/dependency/registry bindings and
`stage_ready`, then embeds the prior-stage digest. Stage C accepts the complete
Stage-A and Stage-B artifacts, revalidates A, requires B's prior-stage digest to
equal the freshly recomputed Stage-A artifact digest, and then performs the same
full recomputation for B. Registry digests are recomputed with the shared canonical serializer
from registry objects in the freshly parsed raw config. The Stage-C config must
contain nonempty ordered registries for `localization`,
`functional_reproducibility`, `collateral`, `counterfactual`, and `baseline`;
empty categories are configuration errors. Endpoint names are globally unique
across all stage/category registries, and required and optional endpoint
registries are disjoint. These are consistency and lineage checks, not
authenticity or launch permission; an external signed review remains mandatory.

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
The replay input is a versioned in-memory bundle with exact keys
`{schema_version, protocol_config_sha256, replay_registry_sha256, source_role,
source_revision, partition, observations}`. `source_role` must be exactly
`calibration`; all other lineage fields must equal the parsed config.
`observations` is the complete registered stratum/evaluation mapping described
below, including arrays, row IDs, payload hashes, and all registered provenance
fields; extra or missing entries are errors. Stage B does not accept generic
endpoint assertions for `calibration_replay` or
`selected_replay_tolerance`: it calls `select_replay_tolerance` itself using the
ladder, safety factor, registry, and observations derived from the bound
config/bundle, then constructs those two endpoint records internally. It hashes
the selector's array-free result with the shared serializer and embeds the
replay schema/config/registry/role, selected candidate, complete pass matrix,
and payload digests. Thus discovery, confirmation, final, blind, or private
observations cannot be converted into an eligible replay record by caller
assertion. An external signed review is still required to launch confirmation
scoring.

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

- Before any arrays exist, the bound config contains an ordered frozen stratum
  registry. One calibration stratum fixes its stratum ID, source role/revision,
  partition, model, checkpoint, code, environment, dtype,
  pooling/reduction-path, ordered row-ID digest, input digest, exactly one
  reference evaluation ID, and at least three repeat evaluation IDs. Every
  digest is a 64-character SHA-256 hex value. Every observation must match the
  registry exactly; extra/unregistered strata or evaluations are errors. The
  role must be exactly `calibration`, so relabeling confirmation/final data cannot
  satisfy the registered source/partition/input digests.
- A stratum contains exactly one named reference evaluation plus at least three
  uniquely named repeat evaluations (at least four arrays total). Evaluation IDs
  are unique; payload hashes may be equal for exact repeats. Row IDs must be
  unique, non-empty, and identical in order; all arrays must have the same
  non-empty shape and contain finite float32 values. The implementation
  recomputes each payload SHA-256 over
  `u64be(len(header_json)) || header_json || u64be(len(rows_json)) || rows_json || array.tobytes(order="C")`,
  where JSON is UTF-8 canonical JSON with sorted keys, compact separators, and no
  trailing newline; `header_json` contains only dtype and shape, and `rows_json`
  is the ordered row-ID array. Supplied payload digests must match. The
  result binds the registry and protocol-config digests.
- All unordered evaluation pairs are compared. For coordinate `i`, pairwise
  `error_i=abs(x_i-y_i)` and `scale_i=max(abs(x_i),abs(y_i))` are computed in
  float64.
- A tolerance candidate `(atol,rtol)` passes a stratum iff for every pair and
  coordinate, `safety_factor * error_i <= atol + rtol * scale_i`. The
  `safety_factor` is a finite prescore value strictly greater than one.
- Every derived product, sum, bound, error, and ratio must remain finite in
  float64; overflow is an input error, never an automatic pass/fail.
- The candidate ladder is a non-empty sequence, not a Cartesian grid. Both
  coordinates are finite, `atol` is strictly positive, `rtol` is nonnegative,
  entries are unique, and every later entry
  is componentwise no smaller with at least one strict increase. Selection is
  the first candidate in this total order that passes **every required
  calibration stratum**. No passing candidate returns `ineligible`; there is no
  extrapolation. The result includes the full stratum-by-candidate pass matrix,
  pair count, coordinate-comparison count, maximum absolute error (activation
  units), maximum symmetric scale (activation units), maximum finite
  `safety_factor*error/(atol+rtol*scale)` ratio per candidate, selected
  index/value, and rationale.
- Strictly positive `atol` makes every diagnostic-ratio denominator positive.
  Pass/fail is computed directly from the inequality rather than from that
  diagnostic ratio. Candidate-bound products and sums are checked for float64
  finiteness before comparison; any overflow is an input error.
- The ladder, safety factor, required strata, and pairing rule must be frozen by
  a separate prescore review before any calibration arrays are produced. The
  checked-in draft leaves them unset; synthetic unit-test ladders are not study
  thresholds or preregistered values.

### Functional reproducibility estimand

- Inputs are registered checkpoint records with distinct checkpoint IDs,
  training seeds, checkpoint artifact SHA-256 values, and distinct
  `(training_run_id, training_run_digest)` pairs, with frozen model ID,
  training-run ID/digest, checkpoint ID/digest, and seed. The mapping among
  training-run identity, seed, checkpoint ID, and checkpoint digest is one to
  one; any duplicate component or contradictory mapping is a config error.
  Inputs also contain registered
  representative tasks and the three finite real metrics `recovery`, `leakage`,
  and signed `selectivity`. These metrics are intentionally not clipped to
  `[0,1]`.
- The config has a required `minimum_checkpoints` field of at least three and the
  registry length must meet it before scoring. This draft leaves the registry and
  minimum unset. No interval or model-level p-value is inferred by this utility.
- For a task/metric, the descriptive estimand reports all checkpoint values, all
  registered pairwise signed and absolute differences, mean, minimum, maximum,
  and maximum spread. Checkpoint registry order defines pairs `i<j`, with signed
  delta `value[j]-value[i]`. It is complete only when every registered checkpoint is
  `eligible` with a finite value. `ineligible` takes precedence over `not_run`;
  available values remain descriptive.
- Every subtraction, absolute value, `math.fsum`, division used for a mean, and
  `max-min` spread is performed in float64 and checked for finiteness. Finite
  inputs whose derived delta, absolute delta, family sum/mean, or spread is not
  representable as finite float64 are input errors, never eligible/ineligible
  observations. Extreme opposite-sign values are covered by tests.
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
- Runtime status mapping is exact: any registered checkpoint/task record marked
  `ineligible` makes that task/metric `ineligible`; otherwise any missing or
  `not_run` record makes it `not_run`; otherwise nonfinite data are input errors;
  and a complete maximum spread above threshold makes it `ineligible` with
  reason `maximum_spread_exceeded`. Too few registered checkpoints is a config
  error before scoring, not an observed instability result.

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

- [x] **M0 — Protected-state baseline.** Create the exact baseline/protected
  inventory and capture process/tmux/GPU-process state before any implementation
  file is created. Acceptance: capture porcelain status to a temporary path
  outside the repository before atomically installing the baseline; every
  allowlisted path is absent except this RFC and provenance baseline; all
  protected files hash successfully; the baseline freezes every pre-existing
  non-allowlisted dirty-path hash/type/size and separately records allowlisted
  starting state so its reviewed deltas remain attributable.
- [x] **M1 — Prospective replay calibration.** Add calibration-role and digest
  validation plus deterministic ordered-ladder selection. Acceptance: tests cover exact
  repeats, ladder-boundary selection, no-candidate failure, all-pairs coverage,
  safety factor, multi-stratum selection, full pass matrix, nonfinite/misaligned
  or empty arrays, duplicate IDs, payload-digest mismatches/equality for exact
  repeats, invalid/mixed provenance, malformed or
  incomparable ladders, zero `atol`, arithmetic overflow, order invariance of
  input mappings, and refusal of every non-calibration role.
- [x] **M2 — Endpoint-specific functional reproducibility.** Add the precisely
  defined task/family checkpoint-spread summaries without a global all-family
  finite predicate. Acceptance: tests cover unbounded/signed finite metrics,
  distinct seeds, pairwise deltas, thresholds, task-first family aggregation,
  insufficient checkpoints, stable-negative selectivity, and independent family
  missingness, one-to-one lineage enforcement, and finite inputs whose derived
  deltas/sums/spreads overflow.
- [x] **M3 — Three fail-closed readiness contracts and draft config.** Add thin
  adapters over `aggregate_endpoint_records`, local dependency-origin/digest
  verification, and an unset draft config. Acceptance: each stage has the exact
  required inputs above; Stage A does not depend on replay results; Stage B does;
  Stage C adds postscore endpoints; all blockers are reported; optional endpoints
  cannot rescue/block; an empty required set is invalid; no adapter can emit an
  operator authorization; every stage/prior-stage/category/config/dependency
  binding is reverified; and the checked-in draft is blocked.
- [x] **M4 — Documentation and verification.** Document how a future candidate
  becomes eligible and how this work relates to the historical v1/v2 artifacts.
  Acceptance: targeted unit tests, Python compilation, strict static/runtime
  side-effect tripwires, protected-state comparison, and config validation pass;
  no experiment/run/result artifact is created. M4 updates this RFC's checkboxes
  and deviations log; no second documentation path is created.

## Definition of done

- [x] The protected-state comparison proves that no artifact in the explicit
  protected set or pre-existing non-allowlisted dirty-path inventory changed
  after the baseline, no new non-allowlisted dirty path appeared, and every
  allowlisted starting/final delta is recorded.
- [x] Numerical tolerance selection is possible only for an explicit
  `calibration` role, requires at least three aligned finite repeats, selects from
  a prescore-ordered componentwise ladder, and returns `ineligible` rather than
  extrapolating beyond the ladder.
- [x] Functional reproducibility uses the frozen task-first/checkpoint-spread
  estimand independently by task and family for all three registered metrics,
  with explicit status/reasons and retained finite subordinate values.
- [x] Stage A, B, and C readiness are separate required-only conjunctions; each
  reports all blockers, optional endpoints are neutral, and none can emit a
  launch/operator authorization.
- [x] The draft config is schema-validated, dependency-digest-bound, and remains
  intentionally blocked because no new study is authorized.
- [x] New tests are deterministic, CPU-only, network-free, and cover unhappy
  paths; targeted tests and compilation pass.
- [x] No experiment, GPU process, activation extraction, probe fit, model load,
  dataset download, or tmux session is launched.

## Verification plan

- Tests:
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPYCACHEPREFIX=/tmp/msae-remediation-pycache .venv-atlas/bin/python -m pytest -q -p no:cacheprovider tests/test_msae_measurement_remediation_v1.py`.
- Syntax:
  `PYTHONPYCACHEPREFIX=/tmp/msae-remediation-pycache .venv-atlas/bin/python -m py_compile scripts/msae_measurement_remediation_v1.py`.
- Static boundary: a strict positive import allowlist plus AST rejection of
  `__import__`, dynamic import, `eval`, `exec`, process/network/tmux/model APIs,
  and filesystem-write surfaces; the draft-config test checks all stages blocked.
- Runtime boundary: monkeypatch socket, subprocess, `os.system`/all spawn APIs,
  Torch/model/dataset imports, and write APIs while importing the module and
  exercising every public in-memory function. The one dependency verifier is
  exercised separately with read-only access to its single canonical file.
- Public surface: define and test the exact `__all__`; no unreviewed callable is
  public.
- Provenance: use `PYTHONPYCACHEPREFIX` outside the repository and disable pytest
  cache; capture and compare before/after process, tmux, GPU-process, protected
  inventories, and non-allowlisted dirty-path hashes.
- Diff audit: inspect only the new RFC/module/config/test files, then run an
  independent adversarial review of the exact worktree paths.
- Explicitly do **not** run any research smoke, audit CLI, model script, pipeline,
  launcher, or experiment command.
- `BASELINE.json` freezes an exact verification-command allowlist (plan gate,
  named pytest, the cache-redirected `py_compile` command above, static
  inspection, hashing/status/process/tmux/GPU observation, and adversarial
  review). `FINAL_STATIC_VERIFICATION.json` records their transcript/digests.
  The no-experiment claim is limited to the reviewed new module and recorded
  commands; process snapshots are supplementary and do not claim to exclude an
  unobserved transient external process.

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

## Implementation outcome and future use

The implemented public surface is the eight-function `__all__` listed above.
The checked-in draft deliberately contains no source revision, replay strata,
tolerance ladder, seed/checkpoint registry, family registry, thresholds, or
Stage-C endpoint names. `validate_draft_config` therefore reports it as blocked;
this is the intended current research status, not a request to fill those values
from the historical neural results.

A future candidate proceeds in this order:

1. independently name and digest the replacement source, partition, grouping
   evidence, label inventory, replay strata, ladder, safety factor, checkpoint
   lineages, representative tasks/families, spread thresholds, and all five
   Stage-C endpoint categories;
2. obtain the external signed prescore review that is intentionally outside this
   module, then build Stage A from label/provenance evidence;
3. only after separate operator approval, collect calibration-role replay arrays
   and let Stage B recompute the registered tolerance selection;
4. only after another separate approval, score confirmation endpoints and build
   Stage C from the complete recursively verified Stage-A/Stage-B chain; and
5. send the Stage-C artifact and substantive results to a scientific claim
   review before selecting a paper branch.

This implementation is additive. It does not modify, repair, rerun, or promote
Atlas completion v1 or measurement v2 artifacts, and it creates no new empirical
result.

## Open questions

- Shared-workspace concurrency cannot be prevented. Any protected or
  pre-existing dirty-path change after the baseline, regardless of actor, stops
  this implementation without a Definition-of-Done claim; it is not overwritten
  or attributed speculatively.
- The replacement confirmation source, its genuine grouping unit, and its
  independence evidence remain unset; no reasonable assumption is made here.
- The exact replay ladder, safety factor, required strata, functional spread
  thresholds, and minimum model seeds remain unset until a separate prescore
  design review. Synthetic test values exercise mechanics only.
- Whether later leakage warrants K3/shared/conditional/relation-aware modeling is
  blocked on a valid independent measurement result.

## Deviations log

- The first baseline emission was atomically corrected before implementation to
  include clean and absent exact-allowlist starting states. The accepted
  `BASELINE.json` records that correction; no implementation or protected path
  existed or changed between the two emissions.
- Independent implementation review initially found four fail-open gaps (reduced
  Stage-A/B requirement registries, cross-metric missingness coupling, split
  replay lineage, and incomplete side-effect tripwires), then found incomplete
  edge coverage, a tautological Stage-B-to-A chain check, and non-ASCII digest
  acceptance. All were repaired and assigned regression tests before the final
  `VERDICT: SHIP`.
- Verification is intentionally limited to CPU-only unit/static checks. No
  research smoke, model call, activation extraction, probe fit, training job,
  GPU job, or tmux session was launched.
