# Plan: MSAE v3 gen4 successor after terminal gen3 setup failure

## Goal

Terminalize the immutable `post_m2_gen3` implementation as failed before its
first protocol-state write, then implement and independently review a wholly
disjoint `post_m2_gen4` M3/M4/calibration protocol. Preserve M0--M2, gen2, the
original gen3 plan/review, all gen3 attempt bytes, and both failed gen3 setup
invocations without reinterpretation.

## Observed history and evidence classes

The plan freezes these facts before any gen4 implementation edit:

- Original gen3 plan SHA-256:
  `c4ea59571eacc970cb282a44460367ff25fd67b972fe4a957da165ac3e579ef7`.
- Original gen3 plan-review SHA-256:
  `e3b2f0047b6fc14aabb0c60227cc1710cac17d3aca67618277ff1e64b4f902bb`.
- Create-once gen3 implementation-review SHA-256:
  `b77237868339a93f1b4e6ad4592260c83b2a0c318c22c9be27a1d0971f86462a`.
  Its SHIP verdict remains valid for the exact reviewed gen3 bytes; it is not a
  current implementation authority after the setup failure.
- Historical preflight SHA-256:
  `411da64bc63dfa33c2b11813f6ce117943b0f2598fdcb388637ed2efb633dc6e`.
  It correctly records `generation=post_m2_gen1_failed_preflight`,
  `successor_generation=post_m2_gen2`, Stage A not run, authorization absent,
  and model/GPU/tmux not run.
- The identical reviewed gen3 `setup-m3` argv was mistakenly invoked twice.
  Both returned nonzero with `ValueError: failed-preflight manifest drift`.
  Invocation 1 has no retained full transcript. Invocation 2 produced an
  operator-captured 935-byte traceback with SHA-256
  `e39e1583d30ce5eb0aa5277ff88d3eb37bee2eb357d8e68ca366591847413020`;
  its exact text will be embedded in reviewed evidence and never depended on at
  its mutable `/tmp` location.
- Mechanically reproduced source control flow shows that reviewed gen3 runtime
  reconstructed the immutable old preflight with
  `successor_generation=GENERATION=post_m2_gen3`, compared it to the correct
  `post_m2_gen2` bytes, and raised before a protocol write site was reachable.
- Mechanically observed current absence shows no gen3 config, provenance,
  M4-data, private key, state/nonce, run, M4 scratch/evidence/socket, or gen2
  `m4_failure.json`. This is present-state evidence, not a historical syscall
  counter. The statement that neither invocation added a protocol-state output
  is an inference from the disclosed identical argv, mechanically reproduced
  dominating raise, and mechanically observed current absence; it is not a
  historical write observation. The gen3 plan, plan review, six implementation
  entries, and implementation review all already existed before either
  invocation and remain immutable.
- The coordinator separately disclosed one accidental read-only pre-SHIP
  `nvidia-smi` inventory query. It created no repository/protocol state, CUDA
  context, job, model call, or tmux session and is never used as launch evidence.

The terminal record has three distinct sections:
`operator_disclosed`, `mechanically_reproduced_source_control_flow`, and
`mechanically_observed_current_absence`. It never claims
`protocol_writes_observed=0` or upgrades disclosure/inference to observation.

## Immutable failed-gen3 inputs

These exact existing paths and their gen3-review-controlled digests remain
byte-identical, at the same paths, and are never renamed, overwritten,
hard-linked, or executed again as a setup route:

- `docs/plan-msae-independent-measurement-v3-post-m4-gen3.md`
- `reports/adversarial/msae_independent_measurement_v3_post_m2_gen3_plan.md`
- `scripts/msae_independent_measurement_v3_post_m2_gen3.py`
- `scripts/msae_independent_measurement_v3_post_m2_gen3_runtime.py`
- `scripts/run_msae_independent_calibration_v3_gen3.py`
- `scripts/launch_msae_independent_calibration_v3_gen3.sh`
- `docs/rfc-msae-independent-measurement-v3-post-m4-gen3.md`
- `tests/test_msae_independent_measurement_v3_post_m4_gen3.py`
- `reports/adversarial/msae_independent_measurement_v3_post_m2_gen3_implementation.md`

The old `setup-m3` command is permanently terminal and never invoked a third
time. Gen3 receives only the reviewed terminal failure record described below;
it never receives config, key, state, Stage A, authorization, or run state.

## Exact gen4 namespaces

| Class | Exact gen4 path |
|---|---|
| Plan | `docs/plan-msae-independent-measurement-v3-post-m4-gen4.md` |
| Plan review | `reports/adversarial/msae_independent_measurement_v3_post_m2_gen4_plan.md` |
| Controller | `scripts/msae_independent_measurement_v3_post_m2_gen4.py` |
| Runtime | `scripts/msae_independent_measurement_v3_post_m2_gen4_runtime.py` |
| Runner | `scripts/run_msae_independent_calibration_v3_gen4.py` |
| Launcher | `scripts/launch_msae_independent_calibration_v3_gen4.sh` |
| RFC | `docs/rfc-msae-independent-measurement-v3-post-m4-gen4.md` |
| Tests | `tests/test_msae_independent_measurement_v3_post_m4_gen4.py` |
| Implementation review | `reports/adversarial/msae_independent_measurement_v3_post_m2_gen4_implementation.md` |
| Post-M3 review | `reports/adversarial/msae_independent_measurement_v3_post_m2_gen4_post_m3.md` |
| Prescore review | `reports/adversarial/msae_independent_measurement_v3_post_m2_gen4_prescore.md` |
| M4 data | `data/msae_independent_measurement_v3_post_m2_gen4/` |
| Config | `configs/msae_independent_measurement_v3_post_m2_gen4/` |
| Provenance | `reports/provenance/msae_independent_measurement_v3_post_m2_gen4/` |
| Setup journal | `reports/provenance/msae_independent_measurement_v3_post_m2_gen4/.setup_m3_gen4_transaction/` |
| M4 install transaction | `reports/provenance/msae_independent_measurement_v3_post_m2_gen4/.m4_install_transaction/` |
| Sign transaction | `pilot_runs/20260821_msae_independent_measurement_v3_post_m2_gen4_calibration/.sign_transaction/` |
| Private key | `/jumbo/lisp/f004ndc/.msae_keys/independent_measurement_v3_post_m2_gen4_ed25519_private.pem` |
| Setup-key transaction | `/jumbo/lisp/f004ndc/.msae_keys/.independent_measurement_v3_post_m2_gen4_setup/` |
| State/nonces | `/jumbo/lisp/f004ndc/.msae_state/independent_measurement_v3_post_m2_gen4/nonces/` |
| Run | `pilot_runs/20260821_msae_independent_measurement_v3_post_m2_gen4_calibration/` |
| M4 trees | `/tmp/msae_independent_measurement_v3_post_m2_gen4_{primary,rebuild}` |
| Prescore evidence | `/tmp/msae_independent_measurement_v3_post_m2_gen4_{manifest_sha256}.prescore.{check.json,trace.log}` |
| Socket/session | `/tmp/msae_independent_measurement_v3_post_m2_gen4_{stage_a_sha256}.sock`; `msae-independent-v3-gen4-calibration` |

The one gen4-authorized terminal write into gen3 is
`reports/provenance/msae_independent_measurement_v3_post_m2_gen3/setup_m3_attempts_1_2_failure.json`.
The one gen4-authorized terminal write into gen2 remains
`reports/provenance/msae_independent_measurement_v3_post_m2_gen2/m4_failure.json`.
Both cross-generation terminal-record schemas name
`writer_generation=post_m2_gen4` and bind the gen4 plan, plan review, all six
gen4 implementation-entry digests, and the predecessor bytes they terminalize;
they deliberately do not contain the gen4 implementation-review digest. The
review externally authorizes their predicted digests, avoiding a review/record
digest cycle. Neither failed gen3 invocation is represented as their writer.
Every other gen2/gen3
downstream path remains absent. The cross-generation GPU
UUID-lock directory remains shared and persistent but is never an output.

## Implementation approach

### G0 — plan lineage and current authority

Install a create-once plan review with exact scope `gen4_plan` and exactly two
controls: `FAILED_GEN3_PLAN_SHA256` and `GEN4_PLAN_SHA256`. Freeze both. No gen4
code edit precedes that review.

The create-once implementation review has scope `gen4_implementation`. After
the two fixed lines `VERDICT: SHIP` and `REVIEW_SCOPE: gen4_implementation`, it
contains exactly these 22 unique lower-hex digest controls and no other
control-like line:

```text
FAILED_GEN3_PLAN_SHA256
FAILED_GEN3_PLAN_REVIEW_SHA256
FAILED_GEN3_CONTROLLER_SHA256
FAILED_GEN3_RUNTIME_SHA256
FAILED_GEN3_RUNNER_SHA256
FAILED_GEN3_LAUNCHER_SHA256
FAILED_GEN3_RFC_SHA256
FAILED_GEN3_TESTS_SHA256
FAILED_GEN3_IMPLEMENTATION_REVIEW_SHA256
HISTORICAL_PREFLIGHT_SHA256
PREDICTED_GEN3_TERMINAL_SHA256
M1_COMPLETION_SHA256
M2_COMPLETION_SHA256
PREDICTED_GEN2_M4_FAILURE_SHA256
GEN4_PLAN_SHA256
GEN4_PLAN_REVIEW_SHA256
GEN4_CONTROLLER_SHA256
GEN4_RUNTIME_SHA256
GEN4_RUNNER_SHA256
GEN4_LAUNCHER_SHA256
GEN4_RFC_SHA256
GEN4_TESTS_SHA256
```

The gen4 authority registry classifies the immutable gen3 implementation review
as `authorized_current_implementation=false`; the immutable review's own bytes
are never relabeled or edited. Only the gen4 implementation review can
authorize current bytes.

Every schema after both terminal records exist uses the same four named lineage maps, each with an exact
key set: `scientific_predecessor` (M1 completion, M2 completion, predicted gen2
failure), `failed_gen3` (plan, plan review, six implementation entries,
implementation review, historical preflight, predicted terminal),
`gen4_plan_authority` (gen4 plan and plan review), and
`gen4_implementation_subject` (six gen4 implementation entries, deliberately
excluding the review wherever that review also binds the enclosing payload).
Schemas that are downstream of implementation review additionally carry its
digest in a separate acyclic authority field.

The records themselves use explicit acyclic exceptions. The gen3 terminal
record's `failed_gen3_subject` omits only its own predicted-terminal digest and
contains no implementation-review digest; the gen2 failure record's
`scientific_predecessor_subject` contains only M1 and M2 and omits its own
predicted-failure digest. The gen2 record may bind the already-computed gen3
terminal digest. Neither predicted record contains its own digest directly or
through a nested map. The setup subject, created after both records and review
exist, has the exact additional key
`implementation_review_authority_sha256`; this is the acyclic authority field
promised above.

### G1 — typed gen3 terminal record

Before writes, compute a canonical gen3 terminal payload with:

- exact identical argv and invocation count 2;
- per-invocation disclosed outcome; transcript 1 unavailable; transcript 2
  embedded exactly with its origin, size, and digest;
- exact failed-gen3 plan/review/implementation entries and controlled digests;
- read-only exact historical-preflight verification and digest;
- source-AST/control-flow reproduction identifying the mismatching two values
  and proving the raise dominates every protocol write call;
- exact current-absence rows for every gen2/gen3 output namespace and lstat-only
  sealed identities, timestamped only as current observations;
- `status=failed_before_first_protocol_state_write`,
  `setup_m3_command_attempts=2`, the two exact
  `setup_m3_attempt_statuses=failed_prewrite`,
  `m3_protocol_state=not_created`, and Stage A/authorization/model/job/tmux
  `not_run`, with successor `post_m2_gen4`. The record never says that the M3
  transition command itself was not run.

The payload and review explicitly distinguish evidence classes. Substitution,
omission, wrong generation, extra output, or changed attempt bytes blocks.

### G2 — read-only historical-preflight verifier

Gen4 has no historical-preflight creation branch. It requires the existing
artifact as canonical, regular, non-symlink, mode-0644, UID-owned, nlink-1 bytes
at exact SHA-256 `411da64b...`. It validates exact schema/semantics, referenced
old config/commitment/public entries/digests, and recorded private-key lstat
without reading that private key. A direct real-artifact test installs write and
fsync tripwires, validates `successor_generation=post_m2_gen2`, reproduces the
failed-gen3 mismatch, proves gen4 read-only acceptance, and mutation-tests every
field.

### G3 — disjoint exact setup command

The only new transition command is this exact argv shape and order:

```text
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen4.py setup-m3-gen4 --reviewed-m2-sha256 e593a6283aa5468ddbee1cc755dbe60c4ee503375a0cbce44c52614dd232d737 --failed-gen3-plan-review-sha256 e3b2f0047b6fc14aabb0c60227cc1710cac17d3aca67618277ff1e64b4f902bb --failed-gen3-implementation-review-sha256 b77237868339a93f1b4e6ad4592260c83b2a0c318c22c9be27a1d0971f86462a --gen4-plan-review-sha256 <64-lowerhex> --gen4-implementation-review-sha256 <64-lowerhex>
```

The CLI rejects old setup/build/sign/launch commands and any reordered,
missing, duplicate, or extra option. Before its first write it revalidates every
lineage, prediction, namespace, source-only closure, quarantine lstat, and exact
downstream absence.

### G4 — complete durable setup DAG

All deterministic payloads are computed before writes. Key-dependent payloads
are computed only after the staged key descriptor is durable. Every directory
uses no-follow exclusive creation, mode 0700, an immediate directory fsync, and
a parent-directory fsync. Every committed file uses the same registered atomic
publisher: create no-follow O_EXCL `.<basename>.partial` beside the target with
the final mode, full-write, file-fsync, then Linux
`renameat2(RENAME_NOREPLACE)` to the final basename and fsync the parent. A
crash-left partial is recoverable only when it is a UID-owned nlink-1 regular
file of the exact mode whose bytes are an exact prefix of the already registered
expected canonical bytes; it is unlinked/fsynced and republished. A full final
file is immutable. Partial+final coexistence, non-prefix bytes, or any other
entry blocks. The only unbound-random exceptions are staged private-key bytes
before key descriptor publication and signing bytes before sign-descriptor
publication; because no final authority then exists, an exact safe partial may
be removed and regenerated. The closure binds the rename syscall wrapper and
tests termination at create, every short write, file fsync, rename, and parent
fsync.

The setup journal is an exact transient directory named
`.setup_m3_gen4_transaction`. Its first and only committed non-numbered file is
`transaction.json`, a mode-0600 canonical descriptor binding the exact argv,
all four lineage classes, expected paths, and the lstat identities of its
mode-0700 provenance root and journal directory. Before that descriptor exists,
the only recoverable physical prefixes are: neither root; the empty exact
provenance root; or the exact provenance root containing only the empty journal
directory. After the descriptor exists, it is immutable.

The descriptor is followed by exactly this ordered receipt list, with no gap:

```text
0001_gen3_provenance_root.json
0002_gen3_terminal_record.json
0003_gen2_m4_failure.json
0004_gen4_m4_data_root.json
0005_gen4_config_root.json
0006_gen4_state_root.json
0007_gen4_nonce_root.json
0008_key_transaction_root.json
0009_key_payload.json
0010_key_descriptor.json
0011_final_private_key.json
0012_setup_subject.json
0013_public_key.json
0014_authorization_commitment.json
0015_cpu_trace.json
0016_protocol_config.json
0017_key_descriptor_removed.json
0018_key_payload_removed.json
0019_key_transaction_removed.json
0020_pre_manifest_projection_verified.json
0021_setup_manifest_written.json
```

Before action `i`, receipts 0001 through `i-1` (an empty set for action 1) must
exist and validate, all receipts `i` and later must be absent, and the action's target is either absent or
already the exact expected post-action object. The implementation performs or
validates that single action and then creates receipt `i`. A present receipt
with an absent/wrong target, a later object/receipt without its predecessor, or
any undeclared child poisons the generation. This admits only the one-object
receipt-lag state caused by termination between object durability and receipt
durability.

The 21 actions are, in order: create/fsync the gen3 provenance root; write the
gen3 terminal record; write the gen2 M4-failure record; create/fsync the gen4
M4-data root; create/fsync the gen4 config root; create/fsync the gen4 state
root; create/fsync its empty `nonces` root; create/fsync the external setup-key
transaction root; generate/fsync its mode-0600 `private_key.payload`; derive the
public key and write mode-0600 `descriptor.json` binding the staged private
bytes/digest/full fstat identity, public bytes/digest, final target, and all
lineages; O_EXCL-copy/fsync/verify the final private key; compute and durably
embed the immutable setup subject in receipt 0012; write the gen4
`ed25519_public.pem`; write `authorization_commitment.json`; write
`cpu_no_model_public_entry_trace.json`; write `protocol.json`; unlink/fsync the
key `descriptor.json`; unlink/fsync `private_key.payload`; rmdir/fsync the empty
external setup-key transaction; revalidate the exact pre-manifest projection;
and finally write the create-once `setup_m3_gen4_manifest.json`.

The setup subject is a canonical object with exact keys
`{schema_version,protocol_id,generation,lineage,
implementation_review_authority_sha256,terminal_record_sha256,
gen2_failure_sha256,setup_transaction_sha256,receipt_sha256_through_0011,
private_key_binding,public_key_pem_b64,public_key_sha256,exact_roots}`. Receipt
0012 has the normal receipt keys plus exactly `setup_subject` and
`setup_subject_sha256`; it is both the receipt and the durable subject carrier.
For this virtual action only, `target_path="virtual://setup_subject"`,
`payload_sha256=setup_subject_sha256`, and `post_lstat=null`, so no receipt field
hashes the enclosing receipt.
Authorization commitment, CPU trace, and protocol config bind that subject
digest, never the later completion-manifest digest.

Canonical setup `transaction.json` has exactly
`{schema_version,protocol_id,generation,argv,argv_sha256,lineage,
expected_paths,root_bindings,receipt_names}`. Ordinary receipts are mode 0600
and have exactly `{schema_version,protocol_id,generation,step_index,step_name,
transaction_sha256,predecessor_receipt_sha256,target_path,action,payload_sha256,
post_lstat}`; directory/deletion fields use explicit JSON null rather than
omission. The key `descriptor.json` has exactly
`{schema_version,protocol_id,generation,transaction_sha256,staged_path,
staged_sha256,staged_fstat,public_key_pem_b64,public_key_sha256,final_key_path,
lineage}`. The final mode-0644 setup manifest has exactly
`{schema_version,protocol_id,generation,status,lineage,transaction_sha256,
receipt_sha256_through_0020,setup_subject,setup_subject_sha256,final_entries,
exact_child_sets}`. Maps themselves have registered exact key sets and sorted
canonical encoding. Deleted key evidence remains in receipts, the setup subject,
and the final manifest after staging cleanup.

The setup manifest is never updated. It is one canonical O_EXCL file binding
`transaction.json`, receipts 0001--0020, every final object/digest/identity, and
the exact final child sets. Receipt 0021 binds its digest. After receipt 0021 is
durable, cleanup deletes numbered receipts in descending order, then
`transaction.json`, then the empty journal directory, fsyncing the containing
directory after every unlink/rmdir. With the final manifest present, recovery
accepts only the exact remaining *prefix* of receipts produced by that
descending cleanup, validates every remaining receipt against the manifest,
and continues cleanup; it never recreates a deleted receipt. After
`transaction.json` deletion, the final-manifest-conditioned empty journal root
is the one additional legal crash state and recovery only fsyncs/rmdirs it.
Final success is
the manifest present with both transient transaction roots absent.

For each object, receipt, and cleanup deletion boundary, tests inject process
termination, call the identical argv, and require exact validation and
deterministic continuation. A hole, unexpected child, wrong byte/mode/UID/link/
type, unbound final key, descriptor mismatch, non-prefix cleanup state, or
downstream object poisons the generation and blocks. “Invoke once” means one
authorized argv/operation; identical-argv re-entry is permitted only for this
exact reviewed crash prefix, never after changed code/reviews/config.

M3 phase child sets are exact:

- gen3 provenance: `{setup_m3_attempts_1_2_failure.json}`;
- gen2 post-M2 provenance: `{m4_failure.json}`;
- gen4 provenance: `{setup_m3_gen4_manifest.json}`;
- gen4 M4 data: `{}`;
- gen4 config: `{protocol.json, authorization_commitment.json,
  ed25519_public.pem, cpu_no_model_public_entry_trace.json}`;
- gen4 state: `{nonces}` and nonce children `{}`;
- setup-key transaction, run, M4 roots, evidence, socket/session: absent.

During setup, the gen4 provenance child set is exactly the journal directory;
then exactly journal plus `setup_m3_gen4_manifest.json`; then exactly the final
manifest. The journal children are exactly `transaction.json` plus a prefix of
the ordered receipt list before publication, and after publication exactly
`transaction.json` plus a cleanup-produced prefix, then the final-manifest-
conditioned empty set. At a publication boundary only the current action's
registered adjacent partial basename may additionally exist. The external key-transaction
children are exactly `{}`, then `{private_key.payload}`, then
`{private_key.payload,descriptor.json}`, then the reverse-deletion sets
`{private_key.payload}` and `{}`, before the root itself becomes absent. The
config children are exactly the ordered prefixes of
`{ed25519_public.pem, authorization_commitment.json,
cpu_no_model_public_entry_trace.json, protocol.json}`; the state children are
exactly `{nonces}` and the nonce root remains empty throughout M3.

### G5 — downstream closure and phase sets

Failed gen3 plan/reviews/attempt bytes/terminal record, historical preflight,
gen4 plan/reviews/current bytes, and gen2 failure record feed the immutable
setup subject. Protocol config, commitment, and stored/reproduced CPU trace bind
that subject digest and the exact prerequisite entries, not the later setup
manifest. The completion manifest then binds the subject and all three config
objects. From the post-M3 subject/review onward, the completion manifest is
required in dependency closure, Stage A, both M4 trees, status/candidate
manifest, traced prescore, prescore review, signed envelope, nonce record,
launcher intent, readiness, and pre-model revalidation. This dependency graph
is strictly one-way and contains no manifest/config digest cycle.

After M4, gen4 provenance is exactly
`{setup_m3_gen4_manifest.json, stage_a.json, status.json,
prescore_candidate_manifest.json}` and gen4 M4 data is exactly
`{dependency_closure.json, endpoint_registry.json,
environment_allowlist.json}`. Review-prefix sets are:

- pre-M3:
  `{msae_independent_measurement_v3_post_m2_gen4_plan.md,
  msae_independent_measurement_v3_post_m2_gen4_implementation.md}`;
- post-M3/prescore-before-review: that exact set plus
  `msae_independent_measurement_v3_post_m2_gen4_post_m3.md`;
- signed launch: that exact set plus
  `msae_independent_measurement_v3_post_m2_gen4_prescore.md`.

These are exact matches over the shared adversarial directory's
`msae_independent_measurement_v3_post_m2_gen4_*.md` prefix; any backup,
temporary, hardlink, symlink, ignored, or other prefixed sibling blocks. The M4
install transaction, when present, contains exactly `transaction.json` and an
ordered prefix of `00.payload` through `05.payload`, mapped respectively to
dependency closure, endpoint registry, environment allowlist, Stage A, status,
and candidate manifest. It is absent after M4; arbitrary subsets and holes
block.

The post-M3 review has exactly `VERDICT: SHIP`,
`REVIEW_SCOPE: gen4_post_m3`, and these ten unique digest controls:

```text
GEN4_IMPLEMENTATION_REVIEW_SHA256
POST_M3_SUBJECT_SHA256
GEN4_PROTOCOL_SHA256
GEN4_AUTHORIZATION_COMMITMENT_SHA256
GEN4_PUBLIC_KEY_SHA256
GEN4_CPU_TRACE_SHA256
GEN4_SETUP_MANIFEST_SHA256
GEN3_TERMINAL_SHA256
GEN2_M4_FAILURE_SHA256
M2_COMPLETION_SHA256
```

The prescore review has exactly `VERDICT: SHIP`,
`REVIEW_SCOPE: gen4_prescore`, `SEALED_PAYLOAD_CONTENT_READS: 0`, and these 12
unique digest controls:

```text
GEN4_IMPLEMENTATION_REVIEW_SHA256
GEN4_POST_M3_REVIEW_SHA256
GEN4_PROTOCOL_SHA256
GEN4_STAGE_A_SHA256
GEN4_STATUS_SHA256
GEN4_CANDIDATE_MANIFEST_SHA256
GEN4_DEPENDENCY_CLOSURE_SHA256
GEN4_ENDPOINT_REGISTRY_SHA256
GEN4_ENVIRONMENT_ALLOWLIST_SHA256
GEN4_PRESCORE_CHECK_SHA256
GEN4_PRESCORE_TRACE_SHA256
GEN4_PRESCORE_CHECKER_SHA256
```

Every review schema enumerates exact control-key sets; tests mutate every
missing, extra, duplicate, malformed, stale-generation, and wrong-authority
line. Every ignored/untracked extra child blocks.

The run root is absent through prescore. Signing creates mode-0700 run root
with exactly the mode-0600 `authorization.json`. Launch may add only this exact
finite top-level set:

```text
launcher_intent.json  logs  broker.sock  lock_acquired.json  handoff.json
nonce_consumed.json  observed_environment.json  tolerance_selection.json
cached_noop_hash_replay.json  canonical_pooling_qa.json
counterfactual_cache_alignment_qa.json  cache  terminal.claim
.terminal_failure_staging  terminal_failure
.terminal_success_staging  terminal_success
```

`logs` has exactly `{broker.log,worker.log}`. `cache` has exactly
`{main_long,main_short,pair_context,pair_entity}` and each stratum directory has
exactly `pooling_per_unit.npy` plus `forward_0.npy` through `forward_3.npy`.
`terminal_failure` (or its same-shaped staging directory) has exactly
`{technical_failure.json,status.json}`. `terminal_success` (or its same-shaped
staging directory) has exactly `{stage_b.json,status.json,
runtime_native_pre_import.json,runtime_native_post_torch.json,
runtime_native_post_model.json,runtime_native_final.json}`. `broker.sock` is
the sole allowed non-regular entry and is removed after handoff/failure.
Registered transition rows freeze which prefix/subset is legal before
readiness, during scoring, during a terminal atomic rename, and at either final
outcome; success/failure and their staging directories are mutually exclusive,
and every other run child blocks.

Those rows are literal: `R0={}` (run absent); `R1={authorization.json}`;
`R2=R1+{launcher_intent.json}`; `R3=R2+{logs}` with the log-child prefix
`{}, {broker.log}, {broker.log,worker.log}`; `R4=R3+{broker.sock}`;
`R5=R4+{lock_acquired.json}`; `R6=R5+{nonce_consumed.json}`; and
`R7=R6+{handoff.json}`. After final-gate acknowledgement, `broker.sock` may be
removed and the scientific sequence is exactly: `observed_environment.json`;
`cache/`; for strata `main_long,main_short,pair_context,pair_entity` in that
order, create the stratum directory and `forward_0.npy` through
`forward_3.npy`; `tolerance_selection.json`; `cached_noop_hash_replay.json`;
the same four `pooling_per_unit.npy` files in order;
`canonical_pooling_qa.json`; and
`counterfactual_cache_alignment_qa.json`. At most that exact sequence prefix is
legal. Success then creates `.terminal_success_staging` with the sorted prefix
of its six registered files, creates `terminal.claim`, atomically renames to
`terminal_success`, and leaves the full scientific sequence plus the success
directory. Failure may start from any valid R1--R7/scientific prefix, removes
success staging/socket, creates `terminal.claim`, creates
`.terminal_failure_staging` with `technical_failure.json` then `status.json`,
and atomically renames to `terminal_failure`. The two final rows retain their
legal preterminal prefix plus exactly one full terminal directory and no
staging/socket. No row permits both outcomes, an out-of-order scientific file,
or a second nonce.

### G5.1 — exact remaining one-way commands

The only public post-setup transition argv shapes are, in this order:

```text
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen4.py build-m4-gen4 --post-m3-review-sha256 <64-lowerhex>
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen4.py prescore-traced-check --manifest reports/provenance/msae_independent_measurement_v3_post_m2_gen4/prescore_candidate_manifest.json --output /tmp/msae_independent_measurement_v3_post_m2_gen4_<manifest_sha256>.prescore.check.json --trace /tmp/msae_independent_measurement_v3_post_m2_gen4_<manifest_sha256>.prescore.trace.log
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen4.py verify-prescore-trace --manifest reports/provenance/msae_independent_measurement_v3_post_m2_gen4/prescore_candidate_manifest.json --check /tmp/msae_independent_measurement_v3_post_m2_gen4_<manifest_sha256>.prescore.check.json --trace /tmp/msae_independent_measurement_v3_post_m2_gen4_<manifest_sha256>.prescore.trace.log
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen4.py sign-gen4
scripts/launch_msae_independent_calibration_v3_gen4.sh
```

The manifest digest is derived by isolated Python from the exact manifest bytes
and the evidence paths must be absent before the traced command. Build consumes
the exact installed post-M3 review digest; signing consumes the exact installed
prescore review and emits only `authorization.json`; the launcher consumes that
exact signed file. Direct `broker-gen4`, `supervise-broker-gen4`, and runner
routes require a fresh launcher capability/intent and are not public commands.
Argument reordering, aliases, missing/duplicate/extra options, old-generation
commands, or noncanonical evidence paths block before a write/process/GPU call.

### G5.2 — M4 and signing recovery state machines

M4 is recoverable only under this exact state machine. Each primary/rebuild
tree creates a mode-0600 `.build_descriptor.json` first, binding the post-M3
review, input snapshot, exact candidate path set, and tree role. A crash-left
tree is accepted only if it is an owned mode-0700 non-symlink dedicated root
with either no child or that valid descriptor plus a schema-valid prefix/subset
of the registered candidate paths; it is deleted bottom-up without following
links, parent-fsynced, and rebuilt. Any foreign, hardlinked, device, FIFO,
socket, symlink, wrong-mode/owner, or unregistered entry terminally blocks.
Both complete trees must compare byte-for-byte and be removed/fsynced before
the install transaction starts.

The M4 install transaction is then created mode 0700. Its mode-0600
`transaction.json` has exactly `{schema_version,protocol_id,generation,
post_m3_review_sha256,input_snapshot_sha256,destinations,payload_sha256,
candidate_manifest_sha256}` and binds the six destinations in the already
registered order. Payloads `00.payload`--`05.payload` are written/fsynced in
order. Before all six exist, only their exact prefix and zero destinations are
legal, plus at most the current atomic-publisher partial. After all six exist,
destinations are installed with the registered atomic publisher in the same
order; only a destination prefix is legal. Once all
six reproduce, payloads are unlinked in descending order, then the descriptor
and transaction root are removed with parent fsync after every deletion. Thus
cleanup leaves only a payload prefix. After descriptor deletion, an empty
transaction root conditioned on all six exact destinations is legal and only
its fsync/rmdir remains. Transaction absent with all six exact
destinations is final success; transaction absent with a strict destination
prefix blocks. Empty/partial pre-descriptor transaction state may be removed
only before any destination exists. Every injected build, payload, destination,
and cleanup boundary is tested through the public build command.

Signing performs every semantic/review/private-key check before creating the
run root. It computes the complete random nonce, validity interval, canonical
unsigned envelope, signature, and authorization bytes in memory. It then
creates the mode-0700 run root and exact transient
`.sign_transaction/transaction.json`. That mode-0600 descriptor has exactly
`{schema_version,protocol_id,generation,implementation_review_sha256,
post_m3_review_sha256,prescore_review_sha256,authorization_b64,
authorization_sha256,unsigned_sha256,nonce,not_before,not_after,
private_key_lstat,public_key_sha256}`. It writes/fsyncs mode-0600
`authorization.payload`, atomically renames it to `../authorization.json`,
fsyncs both the source transaction directory and destination run root, then
removes the descriptor and transaction directory with
parent fsyncs. Before a valid descriptor exists, only empty run/transaction or
regular one-link mode-0600 staging-byte prefixes may be removed and regenerated,
because no signed authority is published. Once a valid descriptor exists, its
random/time-dependent bytes are immutable and re-entry must reuse them. A
descriptor-bound partial payload may be removed/recreated only after proving it
is a byte prefix of the descriptor's payload; after final rename only exact
authorization plus optional descriptor is legal. After descriptor deletion,
exact authorization plus an empty sign-transaction root is legal and recovery
only fsyncs/rmdirs it. Final success is exactly
`{authorization.json}`. Tests terminate after every root, descriptor, payload,
rename, fsync, and cleanup boundary and invoke the same public sign command.

Any setup, M4, or signing semantic/validation failure outside one of these
exact crash prefixes terminalizes gen4; changed bytes or review values never
repair it in place. A later generation may record that failure, but gen4 never
silently upgrades it to a crash recovery. No experiment process is reachable
from any recovery branch.

The external nonce directory is empty until the worker's authorized consume.
Its only legal child thereafter is exactly
`<sha256-of-canonical-authorization.json>.consumed`, a mode-0600 UID-owned
nlink-1 regular canonical record binding authorization, Stage A, launcher
intent, worker identity, and consume time. The run-root mode-0644
`nonce_consumed.json` is its exact digest/identity attestation. Both remain the
only nonce children through either terminal result; missing, second, malformed,
or stale-generation nonce state blocks before model import.

### G6 — source, signer, and experiment containment

Gen4 retains source-only exact local-module loading and removes repository
scripts from default `sys.path` before deferred imports. Timestamp-valid,
sourceless, and extension shadows remain unreachable. Quarantined payloads stay
lstat-only. Signing private-key content is restricted to staged setup agreement
and signer use; workers verify only public commitment and exact private lstat.
No further GPU query, model import/call, experiment, or tmux command occurs
until post-M3, M4, traced prescore, external prescore SHIP, and signature all
complete. The prior inventory query is never reused.

## Verification plan

Before the gen4 implementation review:

- direct real-artifact preflight verification under write/fsync/open tripwires;
- canonical two-invocation gen3 terminal reconstruction and evidence-class
  mutation tests;
- crash injection after every setup DAG durability boundary, including staging
  key pre-binding cleanup, post-binding reuse, final-key copy, each config child,
  manifest transaction, staging removal, and every invalid hole;
- short-write/kill recovery for every registered adjacent partial, every M4
  tree/payload/destination/cleanup state, and every sign descriptor/payload/
  rename/cleanup state, including all three final-output-conditioned empty
  transaction roots;
- exact phase child-set and review-control mutation matrices;
- compile, shell syntax, static/value-flow closure, CPU no-model trace, source
  shadow attacks, candidate two-tree no-live-fallback, quarantine, signer,
  nonce, lease, process, readiness, and terminal behavior;
- all predecessor, failed-gen3, and gen4 tests with an ACL-neutral `/tmp` base;
- fresh `/adversarial` SHIP on exact gen4 implementation bytes.

After reviewed setup, obtain/install fresh post-M3 SHIP before M4. After M4 and
traced prescore, obtain/install fresh external prescore SHIP before signing.
Only the signed launcher may query current GPU state, select/lease a free UUID,
and create the tmux worker. Return immediately after durable two-phase handoff;
do not wait for calibration results. Confirmation scoring and Stage C remain
not run.

## Milestones

- [ ] **P0 — gen4 plan reviewed:** pass the plan gate, obtain independent SHIP
  on these exact bytes, install the create-once plan review, and freeze it with
  all failed-gen3 lineage.
- [ ] **P1 — reversible gen4 implementation:** create only disjoint gen4 files;
  implement terminal evidence, read-only preflight, exact setup DAG, complete
  lineage, and source/launch containment without any one-way write.
- [ ] **P2 — implementation reviewed:** pass all CPU/static/behavioral checks,
  obtain/install gen4 implementation SHIP, and keep every downstream namespace
  absent.
- [ ] **P3 — M3 gen4:** invoke the reviewed setup argv, recover only validated
  crash prefixes if needed, verify exact M3 child sets, and obtain/install fresh
  post-M3 SHIP.
- [ ] **P4 — M4 and prescore:** build two equal complete trees, install exact M4
  outputs, run traced prescore, and obtain/install external prescore SHIP.
- [ ] **P5 — signed handoff:** sign calibration-only authorization; let only its
  launcher query/select/lease a free GPU and start tmux; return after durable
  handoff without waiting.

## One-way doors

Failed-gen3 plans/reviews/code/tests and historical preflight are immutable.
Gen4 plan/review, gen3 terminal record, gen2 terminal record, setup manifest,
key/config/trace, implementation/post-M3/prescore reviews, M4, signature, nonce,
and terminal run state are append-only once published. Registered adjacent
partials and transaction roots are transient and may change only through the
exact recovery grammars above. A semantic setup, M4, or signing failure
terminalizes gen4; only an exact tested crash prefix is recoverable by identical
argv and unchanged authority.

## Definition of done

- Gen3 is terminally failed with honest two-invocation, three-class evidence and
  no scientific/config/key/run state.
- Gen4 has disjoint code, reviews, generation fields, state/output namespaces,
  setup command, closure, signature, socket/session, and run identity.
- Every setup durability boundary and phase child set is explicit and tested.
- Every downstream gate binds failed gen3 and current gen4 lineage without
  stale-review authority.
- Full CPU-safe verification and each fresh adversarial gate pass.
- Calibration alone launches on a then-free leased GPU via tmux and the caller
  returns immediately; confirmation and Stage C remain not run.
