# Plan: MSAE v3 post-M4 failure preservation and gen3 successor

## Goal

Preserve `post_m2_gen2` as a failed, non-authorizing M4 attempt; repair the
candidate-root protocol-config reconstruction in a new `post_m2_gen3`
generation; independently review it; and only then repeat M3/M4, external
prescore review, signing, and the calibration-only tmux handoff.

## Observed failure and invariants

- Gen2 M3 completed create-once with protocol SHA-256
  `0abb5276f5241fc8bd206b271d63a11ece254adbbf6f66cc54f414121ce73c4e`.
- The reviewed M4 command stopped before producing Stage A or installing any M4
  output with `ValueError: active protocol config does not reproduce`.
- Root cause: the generic base builder hashes an environment commitment that
  contains `str((ROOT / ".venv-atlas/bin/python").resolve())`. During the
  independent M4 tree build, `base.ROOT` is the sparse `/tmp` tree, so the
  reconstructed environment hash differs from the live M3 config even though
  Python is a registered external executable.
- Both M4 temporary roots were cleaned. No prescore review, signature,
  authorization, nonce record, run root, GPU query, model call/import, or
  experiment tmux session was created. The three quarantined payloads remain
  lstat-only.
- Gen2 runtime, runner, launcher, RFC, test, M3 config/trace/commitment/public
  key, private-key identity, and state directory are now immutable.

## Constraints

1. Never edit or reinterpret gen2 bytes or claim its M3/Stage A passed.
2. Never open/hash the three quarantined `final*.jsonl` payloads.
3. Create no gen3 M3 state until the plan and implementation receive fresh
   independent adversarial SHIP verdicts.
4. Create no GPU query, model import/call, experiment, or launch tmux session
   before the final external prescore SHIP and signature.
5. Confirmation scoring and Stage C remain out of scope.

## Implementation

### M0: terminalize gen2 without changing its evidence

Create, through the reviewed gen3 setup transition, an O_EXCL canonical
`reports/provenance/msae_independent_measurement_v3_post_m2_gen2/m4_failure.json`.
Before writing, independently verify exact gen2 M3 file digests/modes, the
private/public binding, empty nonce directory, absent gen2 M4 outputs/review/run
root/signature, cleaned build roots, and lstat-only sealed identities. Record
the command and exception as `operator_attested`, set
`full_original_transcript_available=false`, and separately record the
independently reproduced four-field environment-only diff, present-state facts,
`stage_a=not_created`, `m4_outputs=not_created`, and
`model_gpu_tmux=not_run`. Gen2 is never rerun merely to manufacture a
transcript. A mismatching existing record blocks.

### M1: add a disjoint gen3 continuation

Keep all gen2 files byte-identical. Add:

- `scripts/msae_independent_measurement_v3_post_m2_gen3.py` (successor CLI),
- `scripts/msae_independent_measurement_v3_post_m2_gen3_runtime.py`,
- `scripts/run_msae_independent_calibration_v3_gen3.py`,
- `scripts/launch_msae_independent_calibration_v3_gen3.sh`,
- a gen3 RFC and gen3 runtime tests.

Use the exhaustive namespace table below. The new controller exposes only
successor commands. It calls the immutable post-M1 controller for M1, the
immutable gen2 runtime's `verify_m2_completion` for M2, and the immutable
controller's `extend_closure_payload` with every gen3 local dependency. The
gen3 RFC supersedes the predecessor's mandatory-entrypoint wording only for
post-gen2 commands; it retains both immutable verification/extension duties.

| Object class | Exact gen3 namespace |
|---|---|
| M4 data products | `data/msae_independent_measurement_v3_post_m2_gen3/{dependency_closure,endpoint_registry,environment_allowlist}.json` |
| Config/key trace | `configs/msae_independent_measurement_v3_post_m2_gen3/{protocol.json,authorization_commitment.json,ed25519_public.pem,cpu_no_model_public_entry_trace.json}` |
| Stage A/status/manifest/transaction | `reports/provenance/msae_independent_measurement_v3_post_m2_gen3/{stage_a.json,status.json,prescore_candidate_manifest.json}`; transient create-once recovery is confined to `.m4_install_transaction/{transaction.json,00.payload,...,05.payload}` |
| Plan | `docs/plan-msae-independent-measurement-v3-post-m4-gen3.md` |
| Plan review | `reports/adversarial/msae_independent_measurement_v3_post_m2_gen3_plan.md` |
| Implementation review | `reports/adversarial/msae_independent_measurement_v3_post_m2_gen3_implementation.md` |
| Post-M3 review | `reports/adversarial/msae_independent_measurement_v3_post_m2_gen3_post_m3.md` |
| Prescore review | `reports/adversarial/msae_independent_measurement_v3_post_m2_gen3_prescore.md` |
| Private key | `/jumbo/lisp/f004ndc/.msae_keys/independent_measurement_v3_post_m2_gen3_ed25519_private.pem` |
| State/nonces | `/jumbo/lisp/f004ndc/.msae_state/independent_measurement_v3_post_m2_gen3/nonces/`; the state root has no other child and nonce children are only envelope-digest-derived `[0-9a-f]{64}.consumed` records created at launch |
| Run | `pilot_runs/20260821_msae_independent_measurement_v3_post_m2_gen3_calibration/` |
| M4 trees | `/tmp/msae_independent_measurement_v3_post_m2_gen3_{primary,rebuild}` |
| Prescore evidence | `/tmp/msae_independent_measurement_v3_post_m2_gen3_{manifest_sha256}.prescore.{check.json,trace.log}` |
| Tmux socket/session | `/tmp/msae_independent_measurement_v3_post_m2_gen3_{stage_a_sha256}.sock`; `msae-independent-v3-gen3-calibration` |
| Cross-generation GPU exclusion | the existing shared UUID lock directory; persistent by design and never treated as a generation output |

`m4_failure.json` is the sole append-only gen3 write under a gen2 namespace.
Every other gen2 M4/review/sign/run path must remain absent, and every gen3
path must be initially absent.

The gen3 RFC expands the run row into the inherited exact allowlist for
authorization, intent, broker evidence/logs, QA/cache files, mutually exclusive
terminal staging/final trees, and their exact derived children. Every
undeclared child of the config, provenance, state, nonce, run, transaction, and
review roots blocks. The plan, plan review, implementation review, and post-M3
review are phase-aware registered local files: each is added to the local-file,
closure, candidate, static-surface, and repository-status projections as soon
as it exists. The immutable controller's `extend_closure_payload` receives all
four. M4 Stage A and the candidate manifest bind their canonical bytes,
digests, types, modes, ownership, and link counts; omission, drift, or any
unclassified extra status path blocks.

### M2: make generic protocol reconstruction root-independent

In gen3 `_protocol_config_payload`, continue loading the generic builder and all
repository files from the explicit candidate root. Apply one exact typed
adapter to each replay stratum:

1. require the rooted `code_sha256` to equal the candidate-tree **gen2** runner
   digest emitted by the immutable generic builder, then replace it with the
   candidate-tree gen3 runner digest;
2. require the rooted `environment_sha256` to equal the independently
   reconstructed candidate-root `.venv-atlas` derivation, then replace it with
   the canonical registered external-Python derivation; and
3. require every other typed stratum field to be byte-for-byte unchanged.

Cross-check the final `code_sha256` against the gen3 runner entry in config and
closure. Cross-check the final environment value against a typed derivation
record containing the external Python realpath, file size, mode, digest,
startup digest, deterministic/TF32/model-revision/dtype/cache-dtype values. The
adapter rejects missing, duplicate, or extra substitutions. Keep
module/launcher/dependency bytes rooted in the candidate tree.

Bind the canonical Python realpath/digest in the dependency closure and add the
environment derivation inputs to the protocol config. No symlink or live
repository fallback is allowed. Tests must reject a hard-coded gen2 environment
hash, executable path/target/byte drift, config/closure derivation mismatch,
missing executable records, and any candidate-root `.venv-atlas` fallback.

### M3: close the gen3 candidate and failure paths

Update exact local-module, candidate, closure, endpoint, process, and public
entry registries for the gen3 controller/runtime/runner/launcher/RFC/tests and
the gen2 failure record. Regenerate static surface, dynamic-site, non-file-site,
and whole-AST ledgers only after semantic planted-escape tests pass. Preserve
the exact five-file model snapshot and closed worker environment.

Add behavioral regressions for:

- live-root vs two independent sparse-root protocol-config byte equality;
- exact code/environment substitutions plus omission/duplication, and an
  intentionally changed third generic field still blocking;
- gen2 failure-record substitution/omission/extra output;
- complete gen3 M4 two-tree materialization with no live fallback;
- all existing nonce, lease, broker, readiness, failure, terminal, typed-QA,
  static-closure, and CPU/no-model tripwires under gen3 names.

Run compile, Bash syntax, diff check, the gen3 suite, and all predecessor suites
with an ACL-neutral `/tmp` pytest base.

### M3b: machine-enforce the independent review gates

After the final plan receives SHIP and before implementation begins, install the
plan review as a create-once mode-0644, UID-owned, nlink-1, non-symlink,
canonical UTF-8 transcript. Its exact schema has one `VERDICT: SHIP`, one
`REVIEW_SCOPE: plan`, and one lowercase `PLAN_SHA256` line; conflicting,
multiple, missing, or extra control lines block. The reviewed plan and plan
review are immutable thereafter.

Before any gen3 setup write, install a distinct implementation review with the
same filesystem invariants. Its exact schema has one `VERDICT: SHIP`, one
`REVIEW_SCOPE: implementation`, and one lowercase SHA-256 line for the plan,
plan review, gen3 controller, runtime, runner, launcher, RFC, tests, and
predicted gen2 failure payload. Conflicting/multiple verdicts or any
missing/extra control/digest line blocks. `setup-m3` requires both
`--plan-review-sha256` and `--implementation-review-sha256`, independently
verifies both exact files and all transitive digest bindings before any write,
and embeds both review entries/digests into config, commitment, and trace.

After M3, install a second create-once canonical review binding the realized
config, trace, commitment, public key, private-key lstat (content unread), state
and nonce directory identities, gen2 failure record, implementation review, and
plan review. It records the reviewer's historical observation of this exact
downstream-absence set: all three gen3 M4 data products; gen3
`stage_a.json`, `status.json`, `prescore_candidate_manifest.json`, and M4
transaction/build roots; every manifest-digest-derived gen3 prescore check and
trace path; the gen3 prescore review; authorization/run root; nonce records; and
the dedicated gen3 tmux socket/session. It also records absence of the
corresponding gen2 M4 data, stage/status/manifest/transaction/build-root,
prescore-review/evidence, authorization/run, nonce, and tmux outputs, with the
sole exception of the expected `m4_failure.json`. The dedicated session is
defined only under its dedicated socket, so socket absence proves both without
invoking tmux. The post-M3 transcript is self-excluded from its own historical
observation; O_EXCL installation is permitted only after that exact set was
observed absent. Once installed it is an expected, bound candidate input, not a
member of the downstream-absence set. `build-m4` requires
`--post-m3-review-sha256` and rejects before copying/building unless the file has
one exact `VERDICT: SHIP`, `REVIEW_SCOPE: post_m3`, all required digest/identity
lines, and every reproducible current-state binding. Tests call both CLIs
directly to prove omitted/forged/replayed review inputs cannot cross either
one-way door.

### M4: gates and execution order

1. Install the exact create-once plan-review artifact from the independent plan
   SHIP; freeze the reviewed plan.
2. Fresh adversarial SHIP on the final gen3 diff; install its distinct exact
   implementation-review artifact binding the plan review.
3. Confirm all gen3 namespaces other than the plan and two reviews are absent and sealed
   files are lstat-only.
4. Create gen3 M3 with both required review digests, obtain/install a separate
   post-M3/pre-M4 SHIP, and pass its digest to the rejecting M4 CLI gate.
5. Build gen3 M4 and require exact independent-tree equality.
6. Run the digest-derived traced prescore commands.
7. Obtain a fresh external adversarial review of the realized candidate and
   install only its exact SHIP transcript.
8. Sign the exact envelope.
9. Launch calibration. Only here may the launcher query GPUs, select a free UUID,
   acquire its lease, and start the worker through tmux.
10. Return immediately after the durable two-phase handoff; do not wait for
   calibration results.

## Milestones

- [ ] **P0 — reviewed plan:** obtain SHIP on these exact plan bytes, install the
  create-once plan review, and freeze both artifacts.
- [ ] **P1 — reversible implementation:** implement the disjoint gen3 files,
  typed root-independent adapter, exact registries/review gates, failure record
  prediction, and behavioral regressions without creating M3 or using
  GPU/model/tmux surfaces.
- [ ] **P2 — implementation review:** pass all CPU-only checks and obtain/install
  an independent implementation SHIP binding the plan review and complete diff.
- [ ] **P3 — M3 transition:** call setup exactly once with both review digests;
  verify the create-once config, trace, key commitment, gen2 failure record, and
  still-absent downstream state; then obtain/install post-M3 SHIP.
- [ ] **P4 — M4 and prescore:** build both complete sparse trees, require byte
  equality, install Stage A/status/manifest, generate traced prescore evidence,
  and obtain/install the independent prescore SHIP.
- [ ] **P5 — authorized handoff:** sign once, select/lease a free GPU UUID, start
  calibration through the dedicated tmux server, verify durable two-phase
  handoff, and return without polling results.

## Verification plan

- [ ] Before every transition, use lstat-only quarantine tripwires and exact
   before/after metadata comparisons for the three sealed payloads; a content
   open/hash is a hard failure.
- [ ] Run in-memory Python compilation, `bash -n` for the gen3 launcher,
   `git diff --check`, the gen3 test module, and every predecessor/remediation
   suite with an ACL-neutral `/tmp` pytest base. Require zero failures.
- [ ] Run the static closure analyzer and CPU/no-model public-entry harness twice;
   require exact registered surfaces/site/value-flow digests, exact request
   projection, zero model/GPU/tmux access, and rejection of all planted file,
   process, network, library, legacy-route, and self-authenticating-constant
   escapes even when aggregate hashes are updated in memory.
- [ ] In two initially absent temporary roots, reconstruct protocol config and all
   M4 candidate bytes. Compare full path/type/mode/size/hash manifests and exact
   Stage-A bytes, assert no live-repository fallback, then reauthorize the live
   input/status/directory snapshot before create-once installation.
- [ ] Mutation-test every review schema/digest line and both direct CLIs. Prove
   missing, duplicated, conflicting, stale, replayed, wrong-scope, hardlinked,
   symlinked, permissive-mode, or noncanonical review bytes block before the
   corresponding one-way-door write.
- [ ] Reconstruct Stage-B typed QA independently and retain all existing
   real-process tests for separate-process flock contention, UUID/path
   substitution, peer/pane/broker/worker lineage, timeout/lease loss, group
   extinction, broker death, terminal atomicity, nonce short writes/replay, and
   cache durability. These run before signing and without a model call.
- [ ] After M4, execute only the digest-derived isolated traced prescore commands.
   Require the exact check/trace schemas and candidate digests before soliciting
   the final external review. Do not query GPUs or invoke experiment tmux until
   that review is installed and the envelope is signed.
- [ ] At launch, verify free-GPU selection again under the shared UUID lock, closed
   worker environment/native closure, consumed nonce, and the two-phase
   readiness/model gate. Return as soon as the durable handoff artifact is
   validated; do not inspect calibration results.

## Definition of done

- Gen2 is visibly and immutably failed at M4 with no scientific output.
- Gen3 Stage A, candidate manifest, closure, and traced prescore evidence pass
  their independent gates and are externally SHIP-reviewed.
- A signed, single-use, calibration-only authorization is consumed exactly once.
- The free-GPU tmux handoff is live and durable, and the coordinator returns
  without polling results.

## One-way doors

- Plan review, implementation review, gen2 failure record, gen3
  key/config/trace, post-M3 review, gen3 M4 outputs, external review,
  signature/nonce, and run terminal state are create-once.
- Any failure before a gate creates or preserves a failed/not-run generation;
  it is never repaired in place after its bound bytes become immutable.
