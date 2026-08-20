# PLAN — Atlas-v1 Diagnostic Continuation After the L3 Frozen Stop

**Status:** revised candidate for independent adversarial review; no continuation
scoring may start until this plan and the exact implementation candidate receive
`SHIP`.

**Date:** 2026-08-01 (America/New_York)

**Base completion freeze:**
`0aac744d4d10f56cafae645fdc71ea8348bec743a5c20561d4649aedac0503ee`

**Triggering artifacts:**

- `pilot_runs/20260801_atlas_completion_v1/raw_refit/L3/FROZEN_EQUIVOCAL_STOP.json`
  (`612d94df5970236323110e6b6e050d900477738c4488e5d284aa21169becc31c`);
- `pilot_runs/20260801_atlas_completion_v1/NOT_LAUNCHED_UPSTREAM_STOP.json`
  (`85656dd825c90e76d0fb9614a791586105175daf9507026fc7865758a43a9dd4`);
- `reports/adversarial/atlas_completion_result_review_20260801.md`
  (`7dba52503d9f1ca86cc209d05267737be5cd984b2859c77534a35e978112f172`),
  whose final verdict is `BLOCK` because the valid L3 scientific stop was
  incorrectly treated as permission to abandon diagnostics explicitly authorized
  despite decision futility.

## Goal

Complete the still-unobserved diagnostic work requested by the user and required by
the frozen continuation clause, without changing or retrying the failed L3
inference:

1. run all four existing-checkpoint K2 point estimates and 500 paired refit draw
   attempts using the exact original raw L3 point/draw IDs;
2. run the exact 500-draw cross-checkpoint stability protocol;
3. run all four exact 128-transform matched-random/sham specificity controls,
   including the registered cross-entropy collateral;
4. validate and exhaustively summarize every complete, stopped, failed, or
   not-launched outcome without promoting partial results; and
5. issue an explicit diagnostic disposition: original G1/G2 remain equivocal,
   amended G1a/G2a are invalid/unrendered, no final paper branch is selected, and
   training remains prohibited.

The continuation repairs execution/provenance only. It cannot repair L3's
inferential failure, change an estimator or endpoint, or create another chance to
select a favorable branch.

## Non-goals

- Do not mutate, delete, replace, relabel, or retry any artifact in the original
  completion root.
- Do not relax `500` draws, the `>=450` scientifically-finite rule, frozen-class
  support, task eligibility, source/document resampling, thresholds, mappings,
  layers, checkpoints, seeds, or multiplicity families.
- Do not substitute descriptive L4 for primary L3.
- Do not open or hash-read the blind final payload; `.atlas_final_unlock` remains
  absent.
- Do not train or fine-tune any model.
- Do not generate `results/atlas/completion_v1`, `planning_decision_v2`, G1/G2
  results, or a paper-branch choice. The new result is diagnostic disposition only.
- Do not use a new dataset as a substitute for the already-authorized diagnostics.
  Independent-data planning follows this continuation.

## Contract conflict and precedence

The frozen RFC contains a conflict:

- `docs/rfc-atlas-v1-completion.md:252,279` authorizes M5 diagnostics after
  deterministic G1a invalidity and says they continue unless technical corruption,
  blind-final access, or resource failure occurs.
- `docs/rfc-atlas-v1-completion.md:316-322` and the frozen launcher treat any
  upstream stop as blocking all later stages.

The original launcher followed the generic second rule and correctly made its
create-once marker. This plan does not falsify it. An additive, independently
freeze-bound root applies the more specific diagnostic-continuation rule. No new
result may override the already-forced equivocal planning outcome.

## Constraints

1. **Exact estimator reuse.** The score-bearing implementations remain the exact
   freeze-bound `run_msae_refit_worker.py`, `run_msae_stability.py`, and
   `run_msae_specificity.py`. New code may adapt verifier, run-root, baseline
   provenance, exception publication, and raw-leaf location only.
2. **Paired raw identity.** K2 draw `d` consumes original raw L3 draw `d`, not a
   rerun or compacted finite-only series. Original stop and registration hashes are
   verified before each raw payload is opened.
3. **No finite-case rescue.** K2 and stability serialize all requested IDs and use
   the unchanged `>=450` scientifically-finite terminal gate. A new scientific
   stop is a valid expected outcome, never permission to lower the threshold.
4. **Create-once isolation.** New run root is
   `pilot_runs/20260802_atlas_completion_diagnostic_continuation_v1`; result root is
   `results/atlas/completion_diagnostic_v1`; tmux session is
   `msae_atlas_completion_diag_20260802`.
5. **Additive freeze.** `configs/atlas_completion_continuation/freeze_record.json`
   binds the base and parent freezes; a prescore recursive path/type/size/SHA
   inventory of the entire old run root; exact old baseline, L3 stop/selector, root
   marker, and result-review hashes; new config/plan/preregistration/code/tests;
   and exact-digest implementation-review `SHIP` before any continuation score.
6. **Firewall preservation.** The adapter registers only the exact old stop,
   selector, point/draw leaf, and draw registration required for that invocation.
   It never registers the original run root wholesale.
7. **Resources.** Frozen remaining scoring projection is `27.3943` GPU-hours plus
   measured adapter overhead; baseline rebind is CPU-only. The launcher requires
   at least 50 GiB free disk and 128 GiB available RAM. Each GPU job has a 12-hour
   (`43200` second) allocation-queue deadline and each launched stage remains
   subject to the base 24-wall-hour budget. Cumulative original and continuation
   actual GPU-hours will be reported. To reserve the frozen total cap atomically,
   launched job caps are `5.0` GPU-hours for each K2 process, `3.25` for each
   stability process, and `0.30` for each specificity process. These conservative
   ceilings exceed the safety-factored pilot projections, sum to `54.2` GPU-hours,
   and are freeze-bound in continuation metadata. The 300-second termination
   grace and a five-second accounting margin are subtracted before the soft
   timeout, so measured GPU-process elapsed time cannot exceed the hard ceiling.
   Base actual usage is the exact schema-aware ledger of the six immutable
   base-run terminals that contain recorded GPU hours: numerical pilots v8/v9/v10,
   baseline, raw L3, and raw L4 (`11.157119510886776` GPU-hours). Earlier pilot
   artifacts lacking terminal resource accounting are explicitly unavailable, not
   silently treated as zero.
8. **Evidence class.** Continuation results remain
   `postscore_amended_architecture_evidence` and additionally record
   `diagnostic_continuation_only=true` and `decision_promotion_allowed=false`.

## Design grounding

Code inspection established:

- `run_msae_refit_worker.py:421-430` pairs each K2 call with the same raw L3 ID but
  assumes a measurement-complete raw stage in the same run root.
- Point and shard paths call the module global `k2_draw` without an override at
  `run_msae_refit_worker.py:579-582,642-645`.
- `msa_completion_common.py:1286-1335` accepts only a complete upstream stage, while
  the actual L3 stop binds all 500 raw artifacts in `retained_partial_sha256`.
- the targets' `__main__` failure handlers and the common failure publisher hard-bind
  the original config/root; executing those handlers could corrupt provenance.
- stability and specificity depend on the frozen calibration baseline and parent
  C2 artifacts, not on a promoted raw/K2 result.

The design bank has no canonical recovery entry. We therefore make one reversible
local assumption: reuse the frozen estimator modules through a small tested
in-process adapter rather than duplicate and edit their scientific implementation.

## Chosen approach

### A. Exact continuation config and verifier

Create `configs/atlas_completion_continuation/analysis.json`. Every key/value from
`configs/atlas_completion/analysis.json` is identical except the executor/provenance
key `run_root`; no scientific key changes. Extra metadata is isolated under one new
`diagnostic_continuation` object containing schema, base digest, old-stop hashes,
`diagnostic_continuation_only=true`, and
`decision_promotion_allowed=false`. The target modules tolerate but do not consume
this metadata.

`scripts/msa_completion_continuation_common.py` exposes only:

- `verify_continuation_freeze()` for the exact continuation record;
- `require_continuation_config(path)`, which accepts only the exact continuation
  config path;
- exact old-raw attestation/loading;
- baseline rebind verification;
- continuation-root terminal/failure/not-launched publication;
- a narrow firewall wrapper that registers only the exact continuation config file;
  and
- exhaustive replay helpers.

The verifier first calls the unmodified base and parent verifiers, confirms exact
bound old hashes, confirms final-lock absence, replays the freeze-bound whole-old-
root inventory, recomputes its sorted file bundle, and returns its record path/hash
for the existing firewall attestation helper.

Before the implementation review,
`scripts/snapshot_msae_completion_source_root.py` writes one prescore create-once
`configs/atlas_completion_continuation/original_run_inventory.json`. Its sorted
entries cover every descendant directory and regular file as
`{path,type,size,sha256}` (directory size/hash are `null`); symlinks and other file
types are rejected. The freeze binds this manifest. Every adapter invocation and
the final disposition recompute exact path/type/size/hash equality, detecting
additions, removals, or content changes anywhere in the old run root.

### B. CPU-only exact baseline provenance rebind

Do not rerun calibration. `scripts/bind_msae_completion_continuation_baseline.py`
verifies the four old baseline files at these exact hashes:

- `baseline.json`: `405518bb44bd9525307125d8af7dae735d5d31a93ab1e0a3b23b23a8355cf8b5`;
- `baseline_bundle.pkl`: `9e967d08488907188d39ba8c8a134a05b9582be438fcfbf1bb91f7d191ac931e`;
- `MEASUREMENT_COMPLETE.json`: `dcf92e9c5c768660a12c99196a6cb7a7e5394d9687024ca6cf79d1990779d583`;
- `TERMINAL_STATE.json`: `0b35a119478c39cb954cae0ee8d149b75018e9277175b062439c5259f231bf61`.

It rebuilds a new baseline bundle by changing only
`completion_bundle_sha256` to the continuation freeze digest. Every other bundle
key and value must be recursively exactly equal. It rebuilds `baseline.json` with
these scientific/selection-bearing fields recursively exactly equal to the old
result:

`schema_version`, `evidence_class`, `parent_bundle_sha256`, `seed_provenance`,
`baseline_selection_failed`, `selected_simple_baseline`, `selection_trace`,
`candidates`, `sentinel_alphas`, `sentinels`, and `tier1_eligibility`.

Only these enumerated provenance fields may differ:
`config_sha256`, `completion_bundle_sha256`, `resolved_config`,
`resolved_arguments`, `device`, `environment`, `input_attestation`,
`elapsed_sec`, `started_utc`, and `ended_utc`. Additive source hashes live under a
new `provenance_rebind` field and cannot affect baseline science. The binder writes
new result/bundle/terminal create-once on CPU and then re-verifies exact scientific
equality. Any mismatch publishes a baseline technical stop and a root
not-launched closure; it never starts diagnostics.

### C. Exact adapter algorithm and CLI

`scripts/run_msae_completion_continuation.py` is the only allowed scoring
entrypoint. It rejects `--config`, `--output`, unknown flags, raw/baseline/merge/
render/training targets, and non-canonical jobs/shards. Before importing any target
it resolves the stage under the new root and asserts every prospective output is
under that root. The accepted commands and the exact target argv are:

| Adapter command | Injected target argv |
|---|---|
| `k2 --job J --point --device cuda:0` | `--kind k2 --job J --point --device cuda:0 --config configs/atlas_completion_continuation/analysis.json` |
| `k2 --job J --draw-start 0 --draw-end 500 --device cuda:0` | `--kind k2 --job J --draw-start 0 --draw-end 500 --device cuda:0 --config configs/atlas_completion_continuation/analysis.json` |
| `stability --point --device cuda:0` | `--point --device cuda:0 --config configs/atlas_completion_continuation/analysis.json` |
| `stability --draw-start S --draw-end E --device cuda:0` | the exact registered shard (`0,167`, `167,334`, or `334,500`) plus the same injected config |
| `specificity --job J --device cuda:0` | `--job J --device cuda:0 --config configs/atlas_completion_continuation/analysis.json` |

`J` must be one of the exact four base-config checkpoint IDs. There is no adapter
baseline command: the CPU binder is separate.

For every target the adapter performs this order:

1. verify config/freeze/baseline, whole-old-root inventory, and final lock; resolve
   an allowlisted new-root stage; assert all three target module names are absent
   from `sys.modules`;
2. for K2 point, validate the old point pairing; for a K2 draw job, prevalidate all
   500 old raw leaves and registrations before importing the target or allowing any
   scoring. Any single mismatch is therefore fatal outside the worker's broad
   per-draw exception handler: publish a continuation technical stage stop and exit
   nonzero. A 499-good/one-corrupt regression fixture must prove completion is
   impossible;
3. retain the frozen `msa_completion_common.default_firewall`, define a narrow
   wrapper that calls it and registers only the exact continuation config file, and
   replace common `default_firewall`, `verify_completion_freeze`, and
   `require_frozen_completion_config` before target import. The wrapper must refuse
   every other sibling config path;
4. import exactly one target and assert its directly imported `default_firewall`
   and verifier globals are the installed wrappers;
5. for K2 only, retain the original target `k2_draw` and replace the module global
   with a wrapper. On each call it repeats validation for `point` or integer `d`
   against old config/base digest, exact stop and selector hashes, the raw leaf
   relative path/hash in `retained_partial_sha256`, and (for draws) registration
   relative path/hash, `draw_id`, `status=complete`, artifact path/hash, old config
   hash, base completion digest, and raw payload inner `draw_id`; it invokes the
   original function with the full unchanged parsed leaf as
   `raw_result_override`;
6. install exact target argv in `sys.argv`, call `target.main()` (never `runpy`,
   `python target.py`, or target `__main__`), restore common/target globals and argv,
   and re-verify both freezes and the whole-old-root inventory. After `main()` the
   adapter also fails nonzero if a preflight/consumption provenance-stop flag was
   set, even if frozen worker code caught the raised exception.

Pre-freeze subprocess tests exercise the actual point and shard `main()` plumbing
with fixture-only temporary roots and a stubbed scientific `k2_draw` body: they
open no live C2 activation and produce no real score. They prove argv/import/
firewall/override behavior and that the wrapper receives the fixture byte-identified
old payload/ID rather than a new-root path. A separate firewall test accepts only
the exact continuation config and refuses every other sibling path.

### D. Continuation-aware failure and resource closure

No target hard-coded failure handler and no
`msa_completion_common.write_failure_terminal` may be called. The adapter catches
every catchable exception around import and `main()` and uses its own new-root-only publisher.
A resolved stage failure is atomically published under the allowlisted new stage as
`FROZEN_EQUIVOCAL_STOP.json`/`TERMINAL_STATE.json` with exact schema:

`schema_version`, `stop_code`, `failed_gate`, `error_type`, `error`,
`requested_draw_ids`, `completed_draw_ids` recomputed from valid registrations,
`retained_partial_sha256`, `config_sha256`, `completion_bundle_sha256`,
`resolved_arguments`, `device`, `resource_accounting`, `input_attestation`,
`diagnostic_continuation_only=true`, `scientific_retry_allowed=false`, and
`decision_promotion_allowed=false`.

A failure before safe stage resolution writes only create-once root
`LAUNCH_FAILURE.json`, containing the same bindings, the canonical adapter job ID,
and no arbitrary path. Injected failures before import, at import, and inside
`main()` are tested for K2, stability, and specificity, with assertions that no
original-root mtime/hash changes.

The GPU runner performs disk/RAM checks before queueing and checks its canonical
stage terminal during allocation polling. If a sibling has already selected a
terminal before this process scores its expected output, the runner writes a job
terminal with `outcome="superseded_by_stage_stop"`, the stage-terminal path/hash,
`scoring_started=false`, and exits without GPU allocation. If allocation is still
unavailable after 43,200 seconds, it writes
`job_manifests/<job>.resource_stop.json` with schema, job ID, queue timestamps,
resource observations, config/freeze bindings, `scoring_started=false`, and
`decision_promotion_allowed=false`, then a job terminal with outcome
`resource_not_launched` and exit `75`.

The hard runtime supervisor is a separately registered failure boundary because a
worker that does not service `SIGINT` can be killed before adapter cleanup runs. A
GNU-timeout exit `124` or `137` therefore writes create-once
`job_manifests/<job>.resource_timeout.json`, bound to the canonical job/stage,
manifest/log, GPU UUID, stage deadline, reservation, measured monotonic elapsed
time, config, and freeze. Its job terminal has `outcome="resource_timeout"`,
`scoring_started=true`, and the actual nonzero exit code. It never fabricates a
scientific stage terminal. The collector validates and rehashes this record and
classifies the stage `resource_incomplete`, so an uncatchable timeout still closes
durably with null inference.

Every other nonzero or output-missing launched exit that has neither an adapter
stage terminal nor a matching root launch-failure record writes the analogous
create-once, fully bound `job_manifests/<job>.process_crash.json`. Its job outcome is
`process_crash`, and the collector classifies the stage `process_incomplete` with
null inference. A pure classification helper is used by the shell runner and tested
with prompt `SIGKILL`, native abnormal exit, ignored-`SIGINT` timeout, missing-output,
and already-closed controls.

A durable CPU `collector` tmux window waits until all 16 canonical jobs have exactly
one job terminal (success, technical failure, resource-not-launched,
resource-timeout, process-crash, or superseded-by-stage-stop). Only then does it publish the single sorted create-once
root `NOT_LAUNCHED_UPSTREAM_STOP.json`, if needed. Its mapping contains every
unlaunched/incomplete job ID as `{cause_path,cause_sha256,reason}` and, for each of
the nine diagnostic stages, its complete ordered member-job list and
`stage_outcome`. If baseline rebind fails, the launcher publishes the same schema
immediately with all 16 jobs before any GPU window is created. It never fabricates
stage terminals.

Mixed-stage closure is explicit. A stage is scientifically terminal only when its
frozen worker selected a valid complete/scientific/technical terminal and every
member process has a compatible job outcome. If one member is resource-not-launched
or resource-timeout while a sibling produced partial leaves, the stage outcome is
`resource_incomplete`; an uncatchable process-crash yields `process_incomplete`.
Partial leaves are retained/described but no inferential
summary is computed. If one worker selects a technical stage stop, later sibling
processes use `superseded_by_stage_stop`. A nominal exit-zero process is only
`job_process_success`; it is not scientific-stage completeness unless its exact
expected output exists and the stage closure is valid.

Disposition accepts exactly one compatible job record for each canonical job and
one of: a valid terminal for each of the nine diagnostic stages, or a collector-
bound resource/not-launched closure for that stage. Missing, duplicate, conflicting,
or unknown entries are verifier failures. Thus supported failure closes only after
the collector observes the full inventory and never requires a mutable root marker.

### E. tmux execution

`scripts/launch_msae_completion_continuation_tmux.sh` creates only the named
session/root, first runs the CPU binder, then launches 16 GPU jobs:

- eight K2 jobs: point and `0..499` for each of four checkpoints;
- four stability jobs: point, `[0,167)`, `[167,334)`, `[334,500)`; and
- four specificity jobs: one per checkpoint.

After the baseline is bound, these diagnostics are independent and may queue
concurrently on dynamically free GPUs. The durable CPU collector starts before the
GPU windows and remains until all 16 job records are closed. The runner obtains an atomic allocation,
requeries at actual start, binds GPU UUID, records create-once manifest/log/terminal,
and releases its allocation on every exit. A scientific stage stop is never
retried. The launcher itself does not require K2 completion before launching
stability/specificity, because those controls depend only on baseline/parent inputs.

### F. Frozen exhaustive diagnostic schema and replay

`scripts/summarize_msae_completion_continuation.py` writes create-once
`results/atlas/completion_diagnostic_v1/diagnostic_results.json`, narrative report,
and exactly one complete or stopped terminal. The JSON has these mandatory
sections; none are optional:

1. `provenance`: config/freeze/base/parent digests; all bound original hashes;
   original-root before/after inventory digest; final-lock state; baseline source
   and rebound hashes plus the exact scientific-equality verdict.
2. `execution`: the separate baseline provenance-rebind stage, all 16 canonical
   job IDs, and all nine diagnostic stages (four K2, one stability, four
   specificity), each with `outcome`, launch/terminal/resource
   paths and hashes, GPU UUID/runtime when launched, or explicit `null` plus a
   bound not-launched cause. Unknown or omitted jobs/stages fail replay.
3. `k2`: all four checkpoint IDs. Each contains terminal/stop reason, the full
   point `families`, `recoveries`, and all nine `sentinels`; requested IDs exactly
   `0..499`; complete, failed, and scientifically-finite ID lists recomputed from
   registrations/leaves; per-invalid-ID finite-failure fields; and every frozen
   family/task/sentinel draw series. Percentile/LCB/UCB summaries are recomputed
   only when at least 450 scientifically finite paired draws exist; otherwise every
   inferential summary and gate is explicit JSON `null` with
   `insufficient_scientifically_finite_draws`. Incomplete K2 draws can never yield
   a bound/gate.
4. `stability`: terminal/stop reason, full point `tasks` and `families`, requested/
   complete/failed/scientifically-finite IDs, every task's `simple_A_B` and every
   registered K2 pair, every family's learned/simple/G7 statistic, and recomputed
   draw series. Quantiles are present only at `>=450`; otherwise inferential fields
   are explicit `null` with the stop reason.
5. `specificity`: all four checkpoint IDs. Complete entries contain all 128 ordered
   transform IDs, every family/branch sentence and token-aligned summary, validity
   and boundary diagnostics, exact gate reasons, all CE collateral (`point`, 500
   draws, groups, families, and transform-side rows), and all simple-identity
   collateral. Technical/not-launched entries retain the same keys with explicit
   `null` and their bound reason; no checkpoint/family may be omitted.
6. `disposition`: fixed values
   `original_G1="equivocal_unchanged"`,
   `original_G2="equivocal_unchanged"`,
   `G1a="invalid_unrendered"`, `G2a="not_promotable_unrendered"`,
   `paper_branch="unselected"`, `training_warranted=false`,
   `diagnostic_continuation_only=true`, and
   `decision_promotion_allowed=false`.
7. `limitations`: exact list of unavailable/invalid evidence and every stage/job
   stop reason, including empty lists when nothing is missing.

The summarizer uses strict JSON parsing, recomputes finite flags and all serialized
summaries from primitive leaves using the already-reviewed pure verification
functions, validates every hash/attestation/ID, and recursively rejects NaN/Inf.
It never chooses what to report after seeing values. Its own terminal is stopped if
any expected diagnostic is technical/not-launched or scientifically insufficient;
only exhaustive measurement-complete diagnostics yield a complete diagnostic
terminal, and even that never changes the fixed disposition.

## Alternatives considered

### Edit frozen launcher/workers or write into the old root

Rejected because either would invalidate the base freeze or falsify the old
create-once `NOT_LAUNCHED` record.

### Rerun calibration

Rejected because baseline selection is decision-bearing and a post-C2 rerun could
change the comparator. Exact CPU provenance rebind is simpler and safer.

### Copy all frozen workers

Rejected because it duplicates estimator code and creates silent drift risk. The
adapter changes only verifier/provenance and the exact old raw payload location.

### Skip non-promotable K2 or move immediately to independent data

Rejected. The frozen amendment authorized these diagnostics despite decision
futility, and the user explicitly requested them. Independent data is the next
research design after honest diagnostic disposition.

## Milestones

### M1 — Preserve and bind the partial base state

- Persist the result-review `BLOCK` transcript and its exact hash.
- Confirm TODO/RESULTS/ANALYSIS/report call the base execution partial and preserve
  old artifact hashes.

**Acceptance:** all status documents say baseline/raw ran, M5 did not; original
G1/G2 remain equivocal; all named old hashes match.

### M2 — Implement continuation contract, adapter, closure, and tests

- Add config/preregistration, common verifier, baseline binder, adapter, GPU/CPU
  runners, tmux launcher, exhaustive summarizer, and tests.
- Test exact config/argv allowlist and narrow firewall; pre-import patching;
  fixture-only actual K2 point/shard override; fatal all-500 raw preflight including
  one-corrupt/499-good; baseline science equality; all hash/ID failures; injected
  failures for every target; resource/not-launched closure; duplicate/conflicting
  terminal rejection; exhaustive output/null schema; nonfinite JSON; final unlock;
  and decision-promotion denial. Resource tests cover all 16 cap assignments,
  exact `54.2`-hour reservation arithmetic, atomic concurrent reservation,
  grace-inclusive hard timeouts, runner-owned closure for an ignored-SIGINT/SIGKILL
  timeout with no adapter terminal, runner-owned prompt-crash/missing-output closure,
  nearly exhausted shared deadlines, strict mixed-
  schema base-ledger equality, monotonic per-process actual-versus-reserved time,
  same-UUID overlap rejection (with disjoint-same-UUID and overlapping-different-
  UUID acceptance), and cumulative actual/reserved totals below 192.
  The exact GPU-runner script also has a guarded, fixed-command self-test mode that
  accepts only fresh roots below the current-UID-owned, nonsymlinked canonical
  pytest base inside the system temporary directory, explicitly rejects the
  repository/base/continuation/result roots, disables core dumps, changes into the
  verified temporary root, and permits only the four harmless cases `timeout`,
  `sigkill`, `abort`, and `missing_output`; it cannot accept a scoring command. Tests
  execute this mode and rehash the published support/job-terminal records.

**Acceptance:** continuation tests and all 134 existing tests pass; compile/path/
diff checks pass; parent/base freezes and every named old hash verify; no new
continuation scoring output exists.

### M3 — Independent implementation review and freeze

- Run `/adversarial` on the exact implementation candidate and revise until `SHIP`.
- Persist the exact transcript and candidate digest, then create the additive
  freeze with a prescore-clean assertion.

**Acceptance:** exact-digest `SHIP`; continuation freeze verifies; no continuation
score or rebound baseline predates it.

### M4 — CPU baseline rebind and diagnostic GPU execution

- Start the named tmux session, run CPU baseline rebind, and require exact science
  equality plus measurement-complete provenance binding.
- Launch the exact eight K2, four stability, and four specificity jobs through the
  deadline-bound dynamic GPU allocator.
- Monitor manifests, terminals, disk/RAM, logs, and GPUs; never retry a scientific
  stop.

**Acceptance:** the collector observes every canonical job exactly once; every one
of nine diagnostic stages has a compatible valid terminal or bound resource/
not-launched outcome; mixed stages and superseded siblings follow the frozen
closure rules, including runner-owned resource-timeout/process-crash closure; every
existing reservation matches its assigned cap and the observed reservation sum
equals exactly the caps of jobs that reached reservation (with `54.2` GPU-hours as
the frozen maximum potential sum); every measured GPU process is within its grace-inclusive hard cap;
the exact six-terminal base ledger equals `11.157119510886776`; and cumulative
actual and reserved totals remain below 192.

### M5 — Strict disposition, documentation, and claim review

- Run exhaustive replay/summarization.
- Update TODO/RESULTS/ANALYSIS and the completion report with exact outcomes.
- Run full verification, `/adversarial` result review, and research claim review;
  revise until no blocker/revision remains.

**Acceptance:** machine artifacts and prose agree; no partial result is promoted;
final is locked; no training exists; reviews accept the narrow disposition.

## Definition of done

- [ ] The freeze-bound recursive old-root inventory matches before every new
  invocation and after disposition; L3/root-marker hashes and base/parent freezes
  verify.
- [ ] This plan and exact implementation receive independent `SHIP` before any new
  score.
- [ ] Continuation config/freeze/run/result roots are create-once and bound.
- [ ] Baseline is CPU-rebound with every enumerated scientific field exactly equal;
  calibration is not rerun.
- [ ] Four K2 stages request point plus exact IDs `0..499`, paired to original raw
  IDs; each completes, stops, or has an explicit technical/resource closure.
- [ ] Stability requests point plus exact IDs `0..499` and receives the same honest
  closure.
- [ ] All four specificity jobs attempt the exact 128 transforms and all CE
  collateral or preserve explicit technical/resource closure.
- [ ] Exhaustive replay covers all jobs/families/tasks/sentinels/transforms,
  recomputes primitive summaries/finite flags, and uses explicit nulls below 450.
- [ ] Original G1/G2 remain unchanged; G1a/G2a are unrendered/not promoted; no
  `planning_decision_v2`; final paper branch unselected.
- [ ] Blind final remains locked and no model training/checkpoint output exists.
- [ ] All 16 cap assignments, shared 24-hour deadlines, grace-inclusive hard
  elapsed ceilings, atomic 54.2-hour reservations, the exact six-terminal
  `11.157119510886776` base ledger, and cumulative actual/reserved totals below
  192 verify at runtime; same-UUID process intervals never overlap and every
  timeout or uncatchable process crash has runner-owned closure even if adapter
  cleanup is killed. Existing reservations sum exactly to the assigned caps of jobs
  that reached reservation; `54.2` is the maximum potential, not a required observed
  sum after valid pre-reservation closure.
- [ ] TODO/RESULTS/ANALYSIS/report accurately separate completed diagnostics,
  stops, unavailable evidence, and the next independent-data design task.
- [ ] Tests, path/compile/diff/freeze checks, adversarial result review, and claim
  review pass.

## Risks and one-way doors

- **Adapter changes science.** Only verifier/firewall functions and K2's validated
  `raw_result_override` are patched; fixture-only point/shard plumbing, target hashes,
  and payload equality are tested and freeze-bound.
- **Failure writes to old root.** Target `__main__` and common failure publisher are
  prohibited; injected-failure tests hash/mtime-check the old root.
- **Baseline drift.** No scoring rerun occurs; exact field equality is a hard gate.
- **Expected invalidity becomes selective reporting.** The mandatory output schema
  includes all jobs/leaves/families and explicit nulls, independent of results.
- **GPU starvation/collision.** Atomic allocation, actual-start requery, UUID checks,
  disk/RAM gates, 12-hour queue deadline, and explicit resource closure prevent an
  indefinite wait.
- **Post-score interpretation drift.** Fixed diagnostic-only disposition and
  independent result/claim reviews prevent branch promotion.
- **Blind-final access or training.** These are one-way doors and remain hard-denied
  by verifier, adapter allowlist, path/process/output checks, and final-lock checks.

## Verification plan

Before freeze (expected: all commands exit zero; no continuation run/result output):

```bash
/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan \
  --path docs/rfc-atlas-v1-diagnostic-continuation.md
.venv-atlas/bin/python -m pytest -q \
  tests/test_msae_completion_continuation.py \
  tests/test_msae_completion.py tests/test_atlas_metrics.py tests/test_atlas_data.py
.venv-atlas/bin/python -m compileall -q scripts tests
.venv-atlas/bin/python scripts/check_msae_paths.py
git diff --check
```

The continuation test suite must report subprocess PASS for fixture-only real K2
point/shard adapter plumbing (no live C2/score); one-corrupt/499-good fatal
preflight PASS; injected failure/no-old-root-write PASS for all three
targets; exact baseline equality PASS; and exhaustive schema/closure PASS.

Freeze gate (expected: printed continuation digest equals the persisted record,
base digest equals `0aac744d...`, every triggering/source hash above matches, and
prescore-clean is true):

```bash
.venv-atlas/bin/python scripts/freeze_msae_completion_continuation.py
.venv-atlas/bin/python -c \
 'import sys; sys.path.insert(0,"scripts"); from msa_completion_continuation_common import verify_continuation_freeze; print(verify_continuation_freeze()["bundle_sha256"])'
```

Runtime verification after tmux completion must exit zero and assert: baseline
science equality; exact 16-job/nine-diagnostic-stage closure plus the separate
baseline-rebind stage; exact K2/stability requested IDs;
all four 128-transform specificity inventories and CE collateral; recomputed finite
flags and summaries; recursive finite JSON; old-root before/after hashes; final
unlock absent; no training PID/output; tmux/GPU UUID ownership; fixed null and
no-promotion rules; all 16 cap assignments; grace-inclusive actual-versus-reserved
elapsed time; exact observed reservation arithmetic against the 54.2-hour maximum;
exact six-terminal
11.157119510886776-hour base ledger; atomic reservation consistency; and cumulative
actual/reserved totals below 192:

```bash
.venv-atlas/bin/python scripts/summarize_msae_completion_continuation.py
.venv-atlas/bin/python scripts/summarize_msae_completion_continuation.py --verify-only
```

Finally rerun the full pre-freeze suite and require independent `/adversarial` and
research-claim verdicts with no blocker/revision before documenting a final
continuation disposition.
