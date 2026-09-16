# Plan: MSAE independent measurement v3 post-M6 gen6

## Status and purpose

This is a prospective, disjoint recovery generation. Gen5 is preserved as a
failed-before-capability/implementation-review attempt. Its reviewed plan froze
two pathname AF_UNIX sockets that cannot exist on Linux: the tmux `-S` path is
119 encoded bytes and the run-root `broker.sock` path is 129 encoded bytes,
while pathname `sockaddr_un.sun_path[108]` permits at most 107 pathname bytes
plus the terminating NUL. A CPU-only `socket.bind` reproducer rejected the exact
119-byte tmux path with `OSError: AF_UNIX path too long` before a syscall errno
was available. No gen5 capability report, implementation review, M3 state,
Stage A, signature, GPU/model job, or calibration tmux session was created.

Gen6 preserves the scientific protocol, frozen M1/M2 evidence, endpoints,
checkpoint lineages, thresholds, NFS publisher, scientific run ordering, and
Stage-B semantics. Its only semantic changes are control-plane changes: (1)
typed terminal gen5 evidence; (2) two distinct short AF_UNIX paths that each
retain the full 64-hex Stage-A digest; and (3) a captured foreground tmux server,
separate bounded clients, a persistent outside-tmux subreaper monitor with a
complementary in-pane supervisor, and the
corresponding timeout/cleanup extensions required to make those short-path starts
failure-contained. It never reinterprets gen5 as passing.

## Goal

Produce a reviewable gen6 implementation that can:

1. preserve gen5 as failed before capability/protocol-state writes, while retaining the
   already-typed gen4/gen3/gen2 failures;
2. create the non-authorizing M3 state exactly once;
3. construct and compare two complete M4 candidate trees;
4. pass an external traced prescore review;
5. sign one calibration-only authorization;
6. select a free GPU and hand the calibration replay to tmux durably; and
7. return immediately after handoff without waiting for results.

Confirmation scoring and Stage C remain prohibited.

## Constraints

- Preserve every frozen predecessor and failed attempt; never reinterpret a
  failed or absent stage as passing.
- Do not open, hash, or content-read the three literal quarantined payloads
  `data/atlas_v1/private/final.jsonl`,
  `data/atlas_v1/private/final.records.jsonl`, and
  `data/atlas_v1/private/final.units.jsonl`; lstat-only checks are mandatory
  around every guarded operation. No glob or inferred basename may substitute
  for this exact sealed set.
- Do not run setup, M4, signing, GPU inventory, model code, or tmux before its
  explicit review gate. CPU-only temporary capability tests are not experiments.
  The gen6 plan review alone authorizes one non-experiment tmux extinction test
  in session/socket namespace `msae-independent-v3-gen6-test-<pid>` with a fake
  broker, GPU/model/query tripwires, and mandatory cleanup/absence verification;
  it does not authorize the calibration session.
- Use source-only isolated Python (`-S -B -I`) for every production/controller,
  supervisor, and spawned project-code entry, subject only to the two exact
  installed-pytest harness exceptions registered below; bind the full code,
  model, tokenizer, checkpoint, executable, library, environment, endpoint, and
  inference closure.
- Keep calibration replay and Stage B separate from confirmation/Stage C.
- Use exact create-once namespaces and fail closed on any undeclared object,
  drift, uncertain authority, or exhausted recovery budget.

## Approach

Create a disjoint gen6 control-plane generation around the unchanged scientific
protocol. First freeze and review this plan. Then copy the frozen gen5
scientific/control logic through an explicit typed substitution, add gen5
terminal evidence, replace both impossible sockets with exact short full-digest
paths, and prove all inherited plus new behavior with CPU-only fault injection.
Cross M3, M4, external prescore, signing, and live handoff as separate reviewed
one-way transitions.

## Immutable predecessors

Gen6 binds and revalidates these authorities:

- reviewed M1 completion:
  `eed3004cf955b449b23a9bf470bd14725eca5a9e4cf27623f54fce33afa2c636`;
- reviewed M2 completion:
  `e593a6283aa5468ddbee1cc755dbe60c4ee503375a0cbce44c52614dd232d737`;
- failed gen3 plan, reviews, source, and terminal evidence already registered by
  the gen4 design;
- gen4 plan:
  `c443a9eba2305a488b9948467676829c4d317cd67d9c4936a339d6af33bd023b`;
- gen4 plan review:
  `45976d778388d0020c58ea4e3a278c7a1d54d0f67b6a266f5fdc2733366c5fce`;
- terminal gen4 subject:
  - controller `c2f52fa4c0a38d033a0034afe3d258c713cc9bd0e393c00b57e4b20635493faa`;
  - runtime `a0f56b1e8c7acab74179bb51fc1d5d3ff101384882e50fcc80f92d3815b72446`;
  - runner `b1588dbe4db9e2bd30f8d3d290bdcaf235f846859881d2931be9b18f336fc3cd`;
  - launcher `86e99a67af8bc3ce6b35191855ef63931fab576de44565cd55f9da6f9e0c0bf1`;
  - RFC `64c175b46ab77d0b6e60577b1b33406c9ede162f4b5ddc3e45b9b394f770fcb3`;
  - tests `189824871ad197d74957357fbbb35ef269c7b214f7c6b4431e81bccbf285cd48`.

- failed gen5 plan:
  `757ee41fc7ec5440ef1e5d0b132528d86a43a43cd7fc145be828fe5355fe723e`;
- gen5 plan review:
  `bdd23fb26ff1cf7edbe4fbae8efb41b34b22bbaa72e9fa8e88f2231b035bd167`;
- terminal mutable gen5 implementation subject, frozen only as failed input:
  - RFC `0fd7e9bec658c4755b52f1a56639e19bbca9b2edb46a684b2e543a07c3c1db1c`;
  - controller `3a0471d33af027294e20cdd50fd76af7812f6ebdb9bd1f3e1035bdc32d708e49`;
  - runtime `2ba4d988fcf14e0a6bb975fa5f1fe437d02ddfe6f387cf20e93eb776a4489feb`;
  - runner `828c94a8bb12882c0abb4be06afad84b6bfa9db82f56b820fa55eb425fda1bb6`;
  - launcher `3731a3fd4f235d7306686b0371ba63672a182246f4d12eddb736a507a71730d2`;
  - tmux-test supervisor
    `d47d582b25e0613fd611d76244c7875bfce8d5a4e4f770aea25bef60306abf8f`;
  - tests `eb194164dfddc5a858ba2fa123fe6fd7a029170142e366e01f8217d47ab3d597`.

The original gen4 and gen5 plans/reviews remain unchanged. Gen6 does not
reinterpret their authority. The gen5 implementation subject is not called a
reviewed implementation; its exact bytes are bound only so the failed attempt
cannot drift after this plan review.

## Exact namespaces

Gen6 uses only these new namespaces:

- plan: `docs/plan-msae-independent-measurement-v3-post-m6-gen6.md`;
- controller:
  `scripts/msae_independent_measurement_v3_post_m2_gen6.py`;
- runtime:
  `scripts/msae_independent_measurement_v3_post_m2_gen6_runtime.py`;
- runner: `scripts/run_msae_independent_calibration_v3_gen6.py`;
- launcher: `scripts/launch_msae_independent_calibration_v3_gen6.sh`;
- real-tmux test supervisor:
  `scripts/run_msae_independent_measurement_v3_post_m2_gen6_tmux_test.py`;
- RFC: `docs/rfc-msae-independent-measurement-v3-post-m6-gen6.md`;
- tests: `tests/test_msae_independent_measurement_v3_post_m6_gen6.py`;
- plan review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen6_plan.md`;
- pre-capability review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen6_pre_capability.md`;
- implementation review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen6_implementation.md`;
- post-M3 review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen6_post_m3.md`;
- prescore review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen6_prescore.md`;
- config: `configs/msae_independent_measurement_v3_post_m2_gen6/`;
- provenance: `reports/provenance/msae_independent_measurement_v3_post_m2_gen6/`;
- M4 data: `data/msae_independent_measurement_v3_post_m2_gen6/`;
- private key:
  `/jumbo/lisp/f004ndc/.msae_keys/independent_measurement_v3_post_m2_gen6_ed25519_private.pem`;
- state:
  `/jumbo/lisp/f004ndc/.msae_state/independent_measurement_v3_post_m2_gen6/`;
- run:
  `pilot_runs/20260821_msae_independent_measurement_v3_post_m2_gen6_calibration/`;
- M4 roots:
  `/tmp/msae_independent_measurement_v3_post_m2_gen6_{primary,rebuild}`;
- setup journal:
  `reports/provenance/msae_independent_measurement_v3_post_m2_gen6/.setup_m3_gen6_transaction/`;
- setup manifest:
  `reports/provenance/msae_independent_measurement_v3_post_m2_gen6/setup_m3_gen6_manifest.json`;
- setup-key subordinate staging root (not a link transaction):
  `/jumbo/lisp/f004ndc/.msae_keys/.independent_measurement_v3_post_m2_gen6_setup/`;
- M4-install transaction:
  `reports/provenance/msae_independent_measurement_v3_post_m2_gen6/.m4_install_transaction/`;
- sign transaction:
  `pilot_runs/20260821_msae_independent_measurement_v3_post_m2_gen6_calibration/.sign_transaction/`;
- nonce directory:
  `/jumbo/lisp/f004ndc/.msae_state/independent_measurement_v3_post_m2_gen6/nonces/`;
- failed-gen5 terminal:
  `reports/provenance/msae_independent_measurement_v3_post_m2_gen6/failed_gen5.json`;
- failed-gen4 terminal:
  `reports/provenance/msae_independent_measurement_v3_post_m2_gen6/failed_gen4.json`;
- inherited failed-gen3 terminal and gen2 failure, copied as typed gen6 evidence:
  `reports/provenance/msae_independent_measurement_v3_post_m2_gen6/{failed_gen3.json,failed_gen2.json}`;
- capability-reproduction report:
  `reports/analysis/msae_independent_measurement_v3_post_m2_gen6/gen6_capability_reproduction.json`;
- capability-report transaction:
  `reports/analysis/msae_independent_measurement_v3_post_m2_gen6/.capability_report_transaction/`;
- capability-probe root:
  `/jumbo/lisp/f004ndc/tmp/msae_independent_measurement_v3_post_m2_gen6_capability_probe`;
- prescore evidence:
  `/tmp/msae_independent_measurement_v3_post_m2_gen6_<manifest_sha256>.prescore.{check.json,trace.log}`;
- tmux server/control socket:
  `/tmp/m6t_<stage_a_sha256>.sock` (78 encoded bytes for a 64-hex digest);
- launcher/broker handoff socket:
  `/tmp/m6b_<stage_a_sha256>.sock` (78 encoded bytes for a 64-hex digest);
- tmux session: `msae-independent-v3-gen6-calibration`;
- NFS publisher fault-test root:
  `/jumbo/lisp/f004ndc/tmp/msae_independent_measurement_v3_post_m2_gen6_publisher_tests`;
- local-filesystem rejection-test root:
  `/tmp/msae_independent_measurement_v3_post_m2_gen6_mount_rejection_tests`;
- real-tmux extinction-test namespace, where `<supervisor_pid>` is the unpadded
  base-10 result of `os.getpid()` in the sole reviewed supervisor process:
  - session `msae-independent-v3-gen6-test-<supervisor_pid>`;
  - tmux server socket
    `/tmp/msae-independent-v3-gen6-test-<supervisor_pid>.tmux.sock`;
  - fake-broker ACK socket
    `/tmp/msae-independent-v3-gen6-test-<supervisor_pid>.ack.sock`;
  - scratch root `/tmp/msae-independent-v3-gen6-test-<supervisor_pid>.scratch`.

Publisher source basenames are not governed by one implicit naming convention;
the complete per-transaction source/destination table below is authoritative.
In particular, transaction-local payloads and adjacent `.<basename>.partial`
sources are ephemeral hard-link sources, while `private_key.payload` and
`key_binding.json` are authoritative subordinate staging destinations with
their own later deletion receipts. Every transaction has exactly one mode-0600
`transaction.json` descriptor and only its phase-registered sources, receipts,
or payload prefix. Review roots allow only the plan, plan review, pre-capability
review, implementation review, post-M3 review, and prescore review at their
registered phase. Config
has exactly four final children; provenance and M4 data use the phase child sets
listed below. Prescore evidence and both handoff sockets must be absent until
their named phase.

Any undeclared gen6-prefixed sibling, symlink, hardlink, device, FIFO, socket,
wrong-owner object, wrong mode, or unexpected child blocks before a write. The
short socket families are separately closed namespaces even though their names
do not contain `gen6`: every gate enumerates `/tmp` no-follow through a held
`O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC` directory descriptor, binds `/tmp`'s stable
device/inode/UID/mode/mountinfo/fstatfs row (root-owned mode 01777 on the current
host), and rejects every `m6t_*` or `m6b_*` entry except the one
exact phase-registered basename. During capability reproduction those are only
the fixed `m6t_`/`m6b_` + 64 lowercase `a` + `.sock` probes, one at a time;
during scientific handoff they are only the Stage-A-digest-derived paths with
the distinct lifetimes below; at every other phase both families are empty.
The complete filtered `/tmp` projection is bound in the static/behavioral
closure, candidate and prescore checks, authorization, launcher intent,
readiness/handoff, terminal evidence, and every before/after absence check.
Every short-family socket-creating process sets and verifies umask 0077 before
creation. Every live registered `m6t_*`/`m6b_*` socket is a current-UID, nlink-1
`S_IFSOCK` object with
mode 0700 on the bound `/tmp` filesystem; its device/inode/UID/GID/mode/nlink and
held-parent identity must remain stable across every operation. Path replacement,
parent/mount drift, a different mode, or an unbound socket blocks without unlinking
the foreign object.

## Failed-generation and capability evidence

Only after all seven gen6 implementation entries are complete, every registered
CPU/static/publisher/source-only-import test and the real non-experiment tmux
containment test pass, and the exact pre-capability adversarial review is SHIP,
the exact CPU-only command

```text
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen6.py probe-gen6-capability --pre-capability-review-sha256 <64-lowerhex> --output reports/analysis/msae_independent_measurement_v3_post_m2_gen6/gen6_capability_reproduction.json
```

creates one canonical mode-0644, UID-owned, nlink-1 report. It has schema
`msae_v3_gen6_capability_reproduction_v1`, writer generation `post_m2_gen6`,
exact argv/cwd/start/end UTC timestamps, the exact plan, plan-review,
pre-capability-review, and seven implementation-entry digests, the frozen gen4
and gen5 entries,
filesystem `fstatfs` type/fsid, parsed mountinfo identity, exact fixed probe root
`/jumbo/lisp/f004ndc/tmp/msae_independent_measurement_v3_post_m2_gen6_capability_probe`,
the held `/tmp` parent identity/mount row and umask, source/destination logical
names and modes, before/after lstat rows,
transcript UTF-8 and SHA-256, `protocol_path_used=false`, and
`model_gpu_tmux=false`, and `sealed_payload_content_reads=0`. The report has
three independently typed checks, each with canonical `outcome`, complete
observations, and reason codes, plus `overall_pass` equal to the conjunction of
the three exact expected outcomes:

1. the inherited gen4 NFS `renameat2(RENAME_NOREPLACE)` reproduction below;
2. exact `socket.AF_UNIX/SOCK_STREAM.bind` attempts for the 119-byte gen5 tmux
   path and 129-byte gen5 broker path, each requiring Python's pre-syscall
   `OSError: AF_UNIX path too long`, `errno=null`, absent before/after, and no
   listener; and
3. exact bind/listen/connect/close/unlink checks for
   `/tmp/m6t_` + 64 lowercase `a` + `.sock` and
   `/tmp/m6b_` + 64 lowercase `a` + `.sock`, each requiring encoded length 78,
   the exact current-UID/mode-0700/nlink-1 socket identity while live under the
   held bound `/tmp` directory, and exact absence afterward.

Its disposable directory is exactly the fixed NFS root
above, is absent before/after, and cannot be caller-selected. The report schema
rejects any filesystem/mount identity other than the bound repository NFS mount.
The two short socket probes are under `/tmp`, do not overlap any protocol path,
and must be absent before/after. Before each probe, after each probe, and before
the report transaction is bootstrapped, the held-descriptor family projection
must show no other `m6t_*` or `m6b_*` entry.

Every cleanly completed invocation, including an expected-check mismatch,
technical error converted to a typed observation, or `overall_pass=false`, seals
and publishes its canonical report exactly once through the descriptor before
returning. Only an externally observed abrupt process interruption before a
complete report and before either descriptor-bootstrap name is durable is the
restartable no-authority state. An `overall_pass=false` report is permanent gen6
failed-before-protocol-state evidence: no final implementation review, setup, or
same-generation capability rerun is allowed. Only `overall_pass=true`, exact
schema validation, and empty probe/transaction/short-socket namespaces permit the
final implementation review.

Before its first gen6 protocol write, setup reconstructs canonical
`failed_gen5.json` with schema `msae_v3_gen6_failed_gen5_evidence_v1`. It binds
the exact gen5 plan/review and seven-file failed implementation subject, the
capability report, both frozen gen5 templates and encoded lengths, the 108-byte
`sockaddr_un.sun_path` capacity/107-byte pathname maximum, the exact Python
exception observations, and complete current absence of the gen5 capability,
implementation/post-M3/prescore reviews, config, provenance, M4-data, key,
state, run, M4 roots/transaction, evidence, both sockets, signature, nonce,
GPU/model work, and calibration tmux. Its terminal fields are
`capability=not_created`, `implementation_review=not_created`,
`m3=not_created`, `stage_a=not_run`, `authorization=not_created`, and
`model_gpu_calibration_tmux=not_run`. Separately it contains
`operator_disclosed_nonexperiment_tmux_containment_tests` with the exact
reviewed command/cwd/environment, `invocations_disclosed_at_least=3`, disclosed
passing summaries `1 passed in 14.88s`, `1 passed in 29.99s`, and
`1 passed in 29.98s`, `exact_timestamps_available=false`,
`full_transcripts_available=false`, `transcript_sha256=null`, and explicit
`per_invocation_subject_digests_available=false`,
`terminal_seven_file_subject_tested=false`, and
classifications `plan_authorized_process_containment_test=true`,
`capability_report=false`, `scientific_experiment=false`, `gpu_query=false`,
`model_import_or_call=false`, and `calibration_tmux=false`. The summaries are
operator-disclosed containment-test history only; because the invocations were
iterative and their exact subject digests are unavailable, they are not evidence
that the frozen terminal gen5 seven-file subject passed. The exact command is:

```text
cwd=/jumbo/lisp/f004ndc/experiments/wip/MSAE
/usr/bin/env -i PATH=/usr/bin:/bin HOME=/thayerfs/home/f004ndc LANG=C.UTF-8 LC_ALL=C.UTF-8 /jumbo/lisp/f004ndc/experiments/wip/MSAE/.venv-atlas/bin/python -S -B -I scripts/run_msae_independent_measurement_v3_post_m2_gen5_tmux_test.py
```

It explicitly labels the exact current bind
reproduction as a current capability observation, not a historical syscall
trace, and contains no self-digest or gen6 implementation-review digest. The
implementation review binds `PREDICTED_GEN6_FAILED_GEN5_SHA256`.

Before its first gen6 protocol write, setup reconstructs a canonical
`failed_gen4.json`. It binds the exact gen4 subject above, the unchanged gen4
plan/review, the capability-reproduction report, absence of the gen4
implementation review and all gen4 protocol state, and three separate evidence
classes:

1. `operator_disclosed_historical_attempt`: exact pytest argv and cwd, the
   historical pytest temporary path printed in the exception, numeric errno 22,
   disclosed result `OSError: [Errno 22] Invalid argument`,
   `timestamp_available=false`, `full_transcript_available=false`, and
   `transcript_sha256=null`;
2. `mechanically_reproduced_current_capability`: the reviewed report entry and
   its exact timestamp/transcript digest, explicitly not a historical syscall
   observation;
3. `mechanically_observed_current_absence`: exact lstat/namespace projection at
   setup time, explicitly not evidence of historical process behavior.

The fixed probe root is on the same bound NFS mount as the repository, is not a
protocol namespace, and must be absent before and after the command. `/tmp` is
not used. The reproduced probe requires:

- a no-follow O_EXCL regular staging file and absent sibling destination;
- `renameat2(RENAME_NOREPLACE)` returned `EINVAL`;
- the destination remained absent and staging bytes/identity remained intact;
- no protocol path was used.

The historical disclosed environment and argv are exactly:

```text
cwd=/jumbo/lisp/f004ndc/experiments/wip/MSAE
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
.venv-atlas/bin/python -B -I -m pytest -q -p no:cacheprovider tests/test_msae_independent_measurement_v3_post_m4_gen4.py -k "gen4_terminal_payload or historical_preflight_verification or exact_gen4_cli_shape or atomic_publisher_recovers or setup_prefix_validator or sign_transaction_reuses"
```

The disclosed exception path is
`/jumbo/lisp/f004ndc/tmp/lisplab-1/pytest-of-f004ndc/pytest-1287/test_atomic_publisher_recovers0/artifact.json`.

The record contains no self digest and no gen6 implementation-review digest;
the external implementation review binds `PREDICTED_GEN6_FAILED_GEN4_SHA256`.
The result is
evidence of filesystem capability, not scientific execution. Gen6 setup
publishes it under the gen6 provenance root. The terminal record
states `m3=not_run`, `stage_a=not_run`, `authorization=not_created`, and
`model_gpu_tmux=not_run` for gen4.

`failed_gen3.json` has schema `msae_v3_gen6_failed_gen3_evidence_v1`, writer
generation `post_m2_gen6`, the exact immutable gen3 subject, the operator/
mechanical/current-absence evidence payload specified by the frozen gen4 plan,
and terminal fields `m3=not_created`, `stage_a=not_run`,
`authorization=not_created`, `model_gpu_tmux=not_run`. `failed_gen2.json` has
schema `msae_v3_gen6_failed_gen2_evidence_v1`, writer generation
`post_m2_gen6`, the exact gen2 M3 subject and private-key lstat, the mechanically
reproduced fixed-root four-field config diff, sealed reads zero, and terminal
fields `stage_a=not_created`, `m4=not_created`, `prescore=not_created`,
`authorization=not_created`, `model_gpu_tmux=not_run`. Both are canonical typed
gen6 wrappers, not claims that gen4 or gen5 published predecessor artifacts. Neither
contains its own digest or a gen6 implementation-review digest. The
implementation review separately binds `PREDICTED_GEN6_FAILED_GEN5_SHA256`,
`PREDICTED_GEN6_FAILED_GEN4_SHA256`,
`PREDICTED_GEN6_FAILED_GEN3_SHA256`, and
`PREDICTED_GEN6_FAILED_GEN2_SHA256` before setup.

## Registered NFS-capable no-replace publisher

### Alternatives considered

- Reusing gen4's `renameat2(RENAME_NOREPLACE)` is rejected because the exact
  target filesystem returns `EINVAL`.
- Writing the final basename directly with `O_EXCL` is rejected because it
  exposes incomplete canonical objects under their authoritative names.
- Staging on local ext4 and copying to NFS is rejected because cross-filesystem
  publication is not atomic and cannot preserve no-replace semantics.
- A rename-first/fallback design is rejected as unnecessary branching on this
  known NFS target. Gen6 instead registers one link/unlink state machine. If
  hard-link or directory-fsync semantics are unavailable, setup blocks and a
  later generation must choose a different reviewed design.

### Common preconditions

Every setup, M4-install, and signing destination has predetermined canonical
bytes, mode, owner, source basename, destination basename, and parent roots.
Before publication the implementation:

1. opens both parent directories with `O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC`;
2. binds parent device/inode/UID/mode and requires stable identities before and
   after the operation;
3. requires source and destination parents on the same filesystem;
4. opens the source with `O_NOFOLLOW|O_CLOEXEC`, requires a UID-owned nlink-1
   regular file of the exact mode and bytes, and rechecks its path identity;
5. requires the destination basename absent by no-follow lookup.

The capability-report, setup, M4-install, and sign transactions each have one
root `transaction.json` with schema `msae_v3_gen6_link_transaction_v1`. It
contains: `schema_version`, `protocol_id`, `generation`, `transaction_kind`,
`authority_sha256`, exact input/review digests, an ordered `publications` table,
`mountinfo_sha256`, literal `filesystem_magic=0x6969`, `filesystem_fsid`,
`created_unix`, `recovery_deadline_unix`, and `maximum_link_attempts=3`.
`authority_sha256` is the canonical digest of external authority inputs, never
the descriptor's own digest: capability binds the plan review, the
pre-capability SHIP review, and all seven gen6 controller/runtime/runner/
launcher/tmux-supervisor/RFC/test entries; setup binds the implementation review
and exact setup argv/
predecessors; M4 binds post-M3 review plus the complete live input snapshot;
sign binds prescore review plus manifest/Stage-A/config/commitment/closure.
Each publication row binds `ordinal`, `source_parent`, `source_basename`,
`destination_parent`, `destination_basename`, `mode`, `uid`, `payload_kind`,
and `authority_kind`. `fixed_sha256` rows also bind `payload_sha256` and
`payload_size`. `derived_builder` rows instead bind an exact reviewed builder
ID, canonical input-entry-set digest, output schema, and allowed field set; the
builder and an independent validator must reproduce identical canonical bytes
immediately before source creation and again before link. Setup receipts and
lstat-dependent setup subject/manifest rows use this typed derived authority;
they never accept caller-supplied bytes. Basenames are single components other
than `.`/`..`; paths are canonical registered roots. The transaction deadline is
created once with the root descriptor: 300 seconds for capability/sign, 3600
seconds for setup, and 21600 seconds for M4. It is not recomputed per action.

### Finite descriptor bootstrap

The root descriptor is the sole nonrecursive bootstrap exception. Its exact
source is `.transaction.json.bootstrap` beside `transaction.json`. With both
names absent, the command computes all descriptor bytes in memory, creates the
source O_EXCL/no-follow mode 0600, full-writes and file-fsyncs it, then fsyncs
the parent. The source is parsed and independently validated against the exact
current command, inputs, roots, mount, review authority, schemas, and time
bounds before it can authorize its own `linkat` publication. Source-only,
exact-pair, and destination-only recovery use the same link/nlink rules below;
foreign bytes/names block. Once destination-only is durable, it is the root
authority for every publication row. This bootstrap is permitted only at the
four exact transaction roots above and is tested at every write/link/fsync/
unlink boundary. No transaction descriptor is published by a descriptor that
itself depends on that destination.

### Exact transaction topology and cleanup

There are exactly four governing link transactions:

1. capability report:
   `reports/analysis/msae_independent_measurement_v3_post_m2_gen6/.capability_report_transaction/`;
   descriptor names `.transaction.json.bootstrap` and `transaction.json`;
   governed source `report.payload`; final report path registered above;
2. setup:
   `reports/provenance/msae_independent_measurement_v3_post_m2_gen6/.setup_m3_gen6_transaction/`;
   the same descriptor names; governed rows are the 23 receipts, all final
   setup files, and all subordinate setup-key objects;
3. M4 install:
   `reports/provenance/msae_independent_measurement_v3_post_m2_gen6/.m4_install_transaction/`;
   the same descriptor names; governed sources `00.payload` through
   `05.payload`; governed destinations are the three M4-data then three
   provenance outputs in registered order;
4. signing:
   `pilot_runs/20260821_msae_independent_measurement_v3_post_m2_gen6_calibration/.sign_transaction/`;
   the same descriptor names; governed source `authorization.payload`; final
   destination `../authorization.json`.

The exact hard-link publication rows are the following. `P` denotes the gen6
provenance root, `C` the gen6 config root, `D` the gen6 M4-data root, `J` the
setup journal, `K` the subordinate setup-key staging root, and `R` the run root;
these symbols are aliases only for the absolute/relative canonical roots above
and never appear in a descriptor.

| Governing transaction | Source parent / literal basename | Destination parent / literal basename | Source lifetime |
|---|---|---|---|
| capability descriptor bootstrap | capability transaction / `.transaction.json.bootstrap` | capability transaction / `transaction.json` | ephemeral; unlink after exact pair is parent-fsynced |
| capability report | capability transaction / `report.payload` | capability analysis root / `gen6_capability_reproduction.json` | ephemeral; unlink immediately after destination-parent fsync and exact-pair verification |
| setup descriptor bootstrap | `J` / `.transaction.json.bootstrap` | `J` / `transaction.json` | ephemeral; unlink after exact pair is parent-fsynced |
| setup terminal evidence | `P` / `.failed_gen5.json.partial`, `.failed_gen4.json.partial`, `.failed_gen3.json.partial`, `.failed_gen2.json.partial` | `P` / `failed_gen5.json`, `failed_gen4.json`, `failed_gen3.json`, `failed_gen2.json` respectively | each source ephemeral; unlink immediately after its destination-parent fsync and exact-pair verification |
| setup key payload | `K` / `.private_key.payload.partial` | `K` / `private_key.payload` | `.partial` is ephemeral; `private_key.payload` is an authoritative subordinate staging destination retained through receipt 0019 and deleted by the receipt-0020 action |
| setup key binding | `K` / `.key_binding.json.partial` | `K` / `key_binding.json` | `.partial` is ephemeral; `key_binding.json` is an authoritative subordinate staging destination deleted by the receipt-0019 action |
| setup final private key | final key parent / `.independent_measurement_v3_post_m2_gen6_ed25519_private.pem.partial` | final key parent / `independent_measurement_v3_post_m2_gen6_ed25519_private.pem` | source is a separately recreated ephemeral copy of the descriptor-sealed key bytes and is unlinked immediately after destination-parent fsync; `K/private_key.payload` is not this link source |
| setup config outputs | `C` / `.ed25519_public.pem.partial`, `.authorization_commitment.json.partial`, `.cpu_no_model_public_entry_trace.json.partial`, `.protocol.json.partial` | `C` / `ed25519_public.pem`, `authorization_commitment.json`, `cpu_no_model_public_entry_trace.json`, `protocol.json` respectively | each source ephemeral; unlink immediately after its destination-parent fsync and exact-pair verification |
| setup manifest | `P` / `.setup_m3_gen6_manifest.json.partial` | `P` / `setup_m3_gen6_manifest.json` | source ephemeral; unlink immediately after destination-parent fsync and exact-pair verification |
| setup receipts | `J` / `.<receipt-name>.partial`, for each of the 23 literal receipt names registered below | `J` / the corresponding literal receipt name | each `.partial` source is ephemeral; the receipt destination remains authoritative until reverse receipt cleanup after receipt 0023 and manifest verification |
| M4 descriptor bootstrap | M4 transaction / `.transaction.json.bootstrap` | M4 transaction / `transaction.json` | ephemeral; unlink after exact pair is parent-fsynced |
| M4 outputs | M4 transaction / `00.payload`, `01.payload`, `02.payload`, `03.payload`, `04.payload`, `05.payload` | respectively `D/dependency_closure.json`, `D/endpoint_registry.json`, `D/environment_allowlist.json`, `P/stage_a.json`, `P/status.json`, `P/prescore_candidate_manifest.json` | each transaction-local source is ephemeral; unlink immediately after its destination-parent fsync and exact-pair verification |
| sign descriptor bootstrap | sign transaction / `.transaction.json.bootstrap` | sign transaction / `transaction.json` | ephemeral; unlink after exact pair is parent-fsynced |
| authorization | sign transaction / `authorization.payload` | `R` / `authorization.json` | source ephemeral; unlink immediately after destination-parent fsync and exact-pair verification |

Setup directory creation, the virtual setup-subject action, the virtual
pre-manifest-projection action, deletion of `key_binding.json` and
`private_key.payload`, and removal of `K` are receipt-governed actions but are
not hard-link publication rows and have no source basename. No other
`.partial`, `.payload`, descriptor, receipt, or destination name is legal.

`/jumbo/lisp/f004ndc/.msae_keys/.independent_measurement_v3_post_m2_gen6_setup/`
is explicitly a subordinate staging root, not a fifth link transaction. It has
no `transaction.json`; while governed by the durable setup-journal descriptor,
its exact children progress `{}` → `{private_key.payload}` →
`{private_key.payload,key_binding.json}`. Final private-key publication uses a
descriptor-bound adjacent source in the final key parent, so the original
payload remains until the receipt-0020 action. Receipt 0019 records deletion of
`key_binding.json`, receipt 0020 records deletion of `private_key.payload`, and
receipt 0021 records removal of the empty subordinate root. Each deletion/removal
is durable before its identically numbered receipt is published.

Before a root descriptor exists, only these exact empty-prefix roots are legal:
the capability analysis parent+transaction root; gen6 provenance+empty setup
journal; empty M4 transaction root; or run root+empty sign transaction. Each
directory is mode 0700, UID-owned, non-symlink, created no-follow/exclusively,
and immediately parent-fsynced. A crash may re-enter only that exact empty
prefix and bootstrap the descriptor; no governed source may exist yet.

Every ephemeral hard-link source and attempt marker is removed by successful
publication. Authoritative subordinate staging destinations and receipt
destinations are not called sources and are removed only at the literal receipt
or final-projection cleanup boundary in the table and list below.
Final-output-conditioned cleanup is literal:

- capability: exact final report → remove markers, descriptor, empty
  transaction root;
- setup: exact setup manifest plus receipt 0023 → validate receipts/outputs,
  remove receipts 0023 down to 0001 with a journal fsync after each, remove the
  descriptor, then remove the empty journal. A crash leaves only an exact
  receipt prefix plus descriptor, or after descriptor deletion an empty journal
  conditioned on the exact manifest/final projection;
- M4: exact six-destination prefix governs recovery; after all six, remove any
  remaining sources `05` down to `00`, markers, descriptor, then the empty
  transaction root. Descriptor-deleted empty root is legal only with all six
  exact destinations;
- sign: exact `authorization.json` → remove payload/markers, descriptor, then
  the empty sign transaction. Descriptor-deleted empty root is legal only with
  exact authorization.

The governing descriptor remains durable until its rows, receipts (if any),
and final output projection verify. Foreign names, receipt holes, destination
holes, non-prefix cleanup, or descriptor absence before that condition poison
the generation.

All rows are fully bound in the root descriptor. The complete canonical
capability-report bytes, including its non-recomputable timestamps and observed
transcripts, are computed before bootstrap and included base64 in the mode-0600
capability descriptor under `sealed_payloads`, with exact digest/size and the
single `report.payload` row binding. Setup-key and sign random bytes are likewise
generated before bootstrap and included under `sealed_random_payloads`. If no
bootstrap name ever becomes durable, no transaction authority exists: a
documented process interruption may restart capability observation or generate
fresh setup/sign randomness. Once either bootstrap name is durable, those exact
descriptor bytes are the sole authority; recovery never reruns a capability
observation or regenerates randomness and recreates only the identical sealed
payload bytes. A completed negative capability validation is published with
`overall_pass=false`, is a semantic failure, and is not a restartable
interruption. The capability descriptor is deleted only after
the exact report destination is durable and verified; the setup descriptor is
deleted only after the private key, all receipts, setup manifest, and final
projection are durable; the sign descriptor is deleted only after
`authorization.json` is final and verified. Fault tests cover a durable
descriptor with neither report source nor destination and require byte-identical
reconstruction from `sealed_payloads`.

For each table row, before its ephemeral source is first created, its literal
`source_basename` and literal `destination_basename` are both absent. When the
row's governing `transaction.json` is durable, those same two literal names are
absent, and no `.<destination_basename>.attempt-{1,2,3}` exists, the row is
pending and the descriptor-bound exact source, including any embedded random
payload, may be recreated. Source creation is O_EXCL and no-follow, followed by
full-write, file fsync, source-parent fsync, and stable descriptor/source
verification. If `transaction.json` is durable but the row's literal source and
destination basenames are both absent after any registered attempt marker,
recovery blocks as data loss. No source is linked without its matching durable
`transaction.json` and exact publication row.

The descriptor also binds the exact `/proc/self/mountinfo` fields for each
parent (`mount_id`, `parent_id`, `major_minor`, `root`, `mount_point`,
`mount_options`, `optional_fields`, `filesystem_type`, `mount_source`, and
`super_options`) and their canonical digest, plus `fstatfs` literal
`NFS_SUPER_MAGIC=0x6969` and fsid. Every attempt reopens and
revalidates those identities before and after publication. Both parents must
remain on the same bound NFS mount; mount replacement or a different fsid,
filesystem type, or mountinfo row blocks.

### Publication

Before each payload link, the source parent gets the next exact empty mode-0700
attempt-marker directory `.<destination-basename>.attempt-{1,2,3}` using
descriptor-relative `mkdirat`, followed by parent fsync. Existing markers must
form an exact prefix, be UID-owned empty directories on the bound mount, and be
within the descriptor deadline before a new marker is created. Existing markers
remain valid evidence after expiry. An uncertain mkdir result is resolved only by
that exact state. The marker is durable before the payload link, so crashes and
operator re-entry cannot exceed three attempts. Markers are removed in reverse
order with a parent fsync only after final destination verification.

Publication then uses `linkat(source_dirfd, source_basename, destination_dirfd,
destination_basename, 0)` exactly once per invocation with held directory
descriptors and registered single-component basenames. It must create the
absent destination atomically, after
which the implementation requires source and destination to be the same
device/inode, UID-owned regular files of the exact mode/bytes with nlink 2.
It fsyncs the destination parent, revalidates both names and held descriptors,
unlinks only the registered source basename, fsyncs the source parent, and
requires the destination to be the sole nlink-1 name with exact bytes.

After any nonzero `linkat` result, recovery first performs the same descriptor,
mount, and exact-state inspection. An exact pair or destination-only state is
completed/accepted even if NFS returned an uncertain error. An exact source-only
state always ends that invocation as a recoverable technical interruption
without deletion, regardless of errno; a later invocation may consume the next
marker and make one new descriptor-identical attempt. After three markers or
the deadline, source-only is terminal. This single rule includes `EEXIST`,
`EXDEV`, permission/unsupported errors, and uncertain transport errors; it does
not treat any of them as evidence that a destination exists.
There is no copy, overwrite, rename, or temporary directory outside the
destination filesystem.

### NFS uncertain results and recovery

On `EEXIST`, uncertain error, or replay, only three registered states are accepted:

1. source-only, nlink 1, exact bytes: retry publication;
2. source+destination, same device/inode, each nlink 2, exact bytes: fsync the
   destination parent, unlink the source, fsync the source parent, and verify;
3. destination-only, nlink 1, exact bytes: publication already completed.

A publisher performs no in-process retry loop. Each invocation consumes at
most one durable attempt marker; three markers or an expired descriptor block.
Each invocation revalidates all bytes, paths, markers, descriptors, parents,
and mount identity. Exhaustion forbids a new link only; an already exact pair
may still remove its source, and an exact destination-only state remains
complete.

A foreign destination, different inodes, a third link, nlink other than the
registered value, uncertain bytes, unstable parent, symlink, or extra basename
blocks without deletion. Every read is through a stable no-follow descriptor.

### Fault-injection acceptance

Behavioral tests force `EEXIST`, `EXDEV`, `EPERM`, `EACCES`, `EOPNOTSUPP`,
`ENOSYS`, and `EROFS`; simulate interruption after source creation, file fsync,
link, destination-parent fsync, source unlink, and source-parent fsync; and cover
source-only, exact-pair, destination-only, foreign-destination, third-link,
short-write, symlink, hardlink, owner/mode, and parent-swap cases. Each legal
prefix converges byte-identically; every other state fails closed.

The publisher tests use two fixed non-protocol namespaces and run serially
without xdist. The NFS matrix exclusively owns
`/jumbo/lisp/f004ndc/tmp/msae_independent_measurement_v3_post_m2_gen6_publisher_tests`;
the local rejection case exclusively owns
`/tmp/msae_independent_measurement_v3_post_m2_gen6_mount_rejection_tests`.
Each root must be absent before and after its test, is created mode 0700 by the
current UID with no symlink ancestor or extra child, and while live contains
only the table-driven literal names `transaction.json`,
`.transaction.json.bootstrap`, `source.payload`, `destination.json`,
`foreign_destination.json`, `third_link.json`, `replacement_parent`, and
`.destination.json.attempt-{1,2,3}` or
`.transaction.json.attempt-{1,2,3}` as allowed by the state under test. The NFS
matrix first proves its root has the repository's exact bound mountinfo row,
`fstatfs` magic `0x6969`, and fsid, then exercises the production publisher with
one wholly uninjected production transaction before any injected case. That
baseline must observe a real source nlink-1, real `linkat` success and exact
nlink-2 pair, destination-parent fsync, source unlink, source-parent fsync,
destination-only nlink-1 bytes, marker/descriptor reverse cleanup, and final
root absence on the bound NFS server. The descriptor-bootstrap submatrix then
explicitly covers
bootstrap-source-only, exact bootstrap pair, destination-only, each injected
write/link/fsync/unlink crash boundary, three-marker exhaustion, expiry with no
new marker/link, post-expiry exact-pair completion, and reverse marker/source
cleanup. The local case creates only its empty mode-0700 root,
invokes the unmodified production mount validator, and must reject before any
descriptor, source, destination, or marker mutation; state-machine-only
injection may use in-memory fake descriptors but may not bypass or monkeypatch
that production mount rejection. Cleanup is TERM/wait/KILL safe, no-follow,
limited to the exact owned root, parent-fsynced, and followed by lstat absence.

The exact publisher-test command, from the repository root, is:

```text
/usr/bin/env -i PATH=/usr/bin:/bin HOME=/thayerfs/home/f004ndc LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /jumbo/lisp/f004ndc/experiments/wip/MSAE/.venv-atlas/bin/python -B -I -m pytest -q -p no:cacheprovider tests/test_msae_independent_measurement_v3_post_m6_gen6.py::test_nfs_publisher_fault_matrix tests/test_msae_independent_measurement_v3_post_m6_gen6.py::test_local_mount_rejection_precedes_protocol_mutation
```

This publisher pytest process is the first explicit `-S` exception: installed
pytest requires the venv site initialization, plugins/cache are disabled, and
the test module installs and verifies the reviewed source-only finder before it
imports any project module. Every Python child it creates uses `-S -B -I`.

The one authorized real-tmux extinction test is a distinct non-experiment
process-containment test. Its exact supervisor command, also from the repository
root, is:

```text
/usr/bin/env -i PATH=/usr/bin:/bin HOME=/thayerfs/home/f004ndc LANG=C.UTF-8 LC_ALL=C.UTF-8 /jumbo/lisp/f004ndc/experiments/wip/MSAE/.venv-atlas/bin/python -S -B -I scripts/run_msae_independent_measurement_v3_post_m2_gen6_tmux_test.py
```

The source-only supervisor derives the session, tmux server socket, ACK socket,
and scratch root registered above from its own PID. All four must be absent
before it creates the mode-0700 scratch root, binds/listens on the mode-0600 ACK
socket, and starts its sole child. The test tmux socket is current-UID,
current-GID, mode-0700, nlink-1 `S_IFSOCK`; before startup the test holds and
binds `/tmp`'s exact production parent/mount identity and sets/verifies umask
0077, and it revalidates the tmux socket's stable device/inode/UID/GID/mode/nlink
after every client operation. Any installed-tmux mode/identity mismatch blocks
the pre-capability review. The ACK socket is current-UID, current-GID, mode-0600,
nlink-1 `S_IFSOCK` after immediate chmod and stable fstat/lstat revalidation.
These test-only names are not members of the `m6t_*`/`m6b_*` families. It
executes exactly this child environment and
argv, with no shell and no other inherited `MSAE_*`, CUDA, Python-path, preload,
or plugin variables:

```text
environment={PATH:/usr/bin:/bin,HOME:/thayerfs/home/f004ndc,LANG:C.UTF-8,LC_ALL:C.UTF-8,PYTEST_DISABLE_PLUGIN_AUTOLOAD:1,MSAE_GEN6_ALLOW_REAL_TMUX_TEST:1,MSAE_GEN6_TMUX_TEST_TOKEN:<supervisor_pid>,CUDA_VISIBLE_DEVICES:""}
argv=[/jumbo/lisp/f004ndc/experiments/wip/MSAE/.venv-atlas/bin/python,-B,-I,-m,pytest,-q,-p,no:cacheprovider,tests/test_msae_independent_measurement_v3_post_m6_gen6.py::test_failed_handoff_extinction_kills_real_processes_and_socket]
```

The missing `-S` on that pytest child is the second and only other explicit
harness exception needed to import installed pytest. Plugins/cache are disabled, the test installs
the reviewed source-only finder before importing any project module, and all
spawned project/controller or fake-broker Python entries still require
`-S -B -I`. The supervisor starts the pytest child in its own process group,
uses one selector-driven main loop with a 120-second monotonic child deadline,
and is the cleanup authority that survives a pytest timeout. On timeout or any
child outcome it TERM/waits three seconds, then KILLs/waits the pytest group
before entering the same unconditional namespace teardown. Supervisor
SIGTERM/HUP/INT handlers only set one atomic shutdown flag and write one byte to
a self-pipe; the main loop masks/reclassifies later signals and one serialized
`finally` performs the idempotent cleanup. Signal handlers never call
subprocess or filesystem routines, and the supervisor is never the process
killed by an inner timeout.

Within the child, the test's fake pane-supervisor argv is exactly
`[realpath(.venv-atlas/bin/python), "-S", "-B", "-I", "-c",
FAKE_TMUX_PANE_SUPERVISOR_SOURCE, <ack-socket>, <scratch-root>/process.json]`, where the
literal source and its SHA-256 are test constants bound by the implementation
review. The supervisor, not pytest, owns the ACK listener and validates the
accepted peer with `SO_PEERCRED`; the peer PID/UID/GID must be the exact pane-supervisor
PID/current UID/GID and must equal the captured tmux pane PID/start-tick identity.
The child and supervisor bind the foreground server PID/start-tick/PGID and
capture the pane identity with the exact `display-message -p -t` vector above as
soon as the session exists and before either permits an identity ACK; stdout is
the same exact two-positive-decimal-PID canonical line required in production.

The fake pane entry models the complementary production supervisor. It does not
arm parent death; before forking it installs the exact HUP/TERM handlers and
binds the monitor/server/socket test identities. It uses `os.fork`, not
subprocess, to create a broker in a separate process group. That broker and its
one worker descendant each set/recheck `PR_SET_PDEATHSIG=SIGKILL`; the worker
requires `getppid()` still equals the captured broker PID (otherwise it calls
`_exit(125)`), does not ignore TERM, and blocks on a private pipe.
The pane supervisor writes canonical `msae_v3_gen6_tmux_test_process_v1` identity
bytes to exact mode-0600 `scratch/.process.json.partial`, file-fsyncs, publishes
only to `scratch/process.json`, and directory-fsyncs before sending the same
identity to the supervisor. The record contains monitor, foreground server,
pane supervisor, broker, and worker PID/start-tick/PGID identities plus exact
parent links. The supervisor independently
parses the durable record, rechecks every `/proc` identity/ancestry and peer
credential, then replies with the one-byte identity-bound ACK. Only after the
pane supervisor receives that byte may it release the broker's pipe barrier; the worker then
sets TERM resistance, clears its parent-death signal, and reports one-byte
`resistance-armed` through the broker. The supervisor revalidates all identities
and durably publishes exact mode-0600 `scratch/identity_bound.json`; only that
file permits pytest to call the production extinction helper. Thus no
TERM-resistant/reparentable descendant exists before the surviving supervisor
has its durable exact identity. Missing, late, duplicate, malformed, partial,
or out-of-order record/ACK blocks and enters teardown. The identity exchange has
a five-second deadline inside the supervisor's 120-second child deadline.

Before starting tmux, the test installs tripwires that fail on `/usr/bin/nvidia-smi`
or any GPU-query helper, any `torch`, `transformers`, `datasets`, or model-runner
import, any CUDA device/environment activation, and any protocol controller
setup/M4/sign/launch route. `CUDA_VISIBLE_DEVICES` is the empty string. Only the
fake Python argv, the exact foreground
`/usr/bin/tmux -D -f /dev/null -S <tmux-socket>` server argv, and the separate
bounded exact `/usr/bin/tmux -f /dev/null -S <tmux-socket>` new-session,
`set-option -s exit-empty on`, `show-options -s -v exit-empty`,
`display-message -p -t <session> "#{pid} #{pane_pid}"`, has-session,
kill-session, and kill-server client vectors are allowed. The child uses the
same factored production foreground-server/start-client/identity-client helper,
with the test session/socket and fake broker as typed inputs; it may not replace
that helper with an independently implemented test launcher. After the ACK the test
exercises the production failed-handoff extinction helper. Both the child's
`finally` and the independently surviving supervisor use the same idempotent
teardown contract: descriptor-safely parse at most the exact mode-0600
`scratch/process.json`; an absent/partial record means the descendant barrier
was never released, so teardown kills the captured pane/broker, kills the tmux
server, and relies on the still-armed parent-death signal before verifying the
captured process tree extinct. With a valid record, it TERM/bounded-waits then
KILLs/waits the exact recorded PID/start-tick and entire PGID. In both cases it
issues exact tmux kill-session and kill-server vectors on the fixed server
socket; closes/unlinks the ACK socket; no-follow removes only
`.process.json.partial`, `process.json`, `.identity_bound.json.partial`,
`identity_bound.json`, `terminal.claim.test`, `technical_failure.test.json`, and
the empty exact scratch root; and verifies tmux
`has-session` is nonzero, both sockets and scratch are absent, and no recorded
or captured pane/broker PID/start-tick, descendant, or PGID member remains.
Fault tests terminate at every monitor/pane/broker/worker fork,
monitor-record write/fsync/commit/ACK/`START_SERVER`, server exec/socket,
new-session, exit-empty set/proof, identity, partial-write, publish, ACK,
barrier-release, resistance-arm, and child-timeout boundary and require the same
final absence. Real-process cases kill the validated monitor while the pane
supervisor survives and separately kill the pane supervisor while the monitor
survives; each case must create exactly one technical-failure claim and prove
the other authority performed cleanup, using only exact mode-0600
`scratch/terminal.claim.test` and `scratch/technical_failure.test.json` and never
a protocol run root. Stubbing either production cleanup path
must make its corresponding case fail before test-finalizer emergency cleanup.
The supervisor returns success only if
pytest returned zero and its independent final teardown/absence verification
succeeded. The test namespace never overlaps a capability, protocol, GPU-lock,
nonce, run, or prescore path.

## M3 setup and review gates

The exact setup command is:

```text
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen6.py setup-m3-gen6 --reviewed-m2-sha256 e593a6283aa5468ddbee1cc755dbe60c4ee503375a0cbce44c52614dd232d737 --failed-gen3-plan-review-sha256 e3b2f0047b6fc14aabb0c60227cc1710cac17d3aca67618277ff1e64b4f902bb --failed-gen3-implementation-review-sha256 b77237868339a93f1b4e6ad4592260c83b2a0c318c22c9be27a1d0971f86462a --failed-gen4-plan-review-sha256 45976d778388d0020c58ea4e3a278c7a1d54d0f67b6a266f5fdc2733366c5fce --failed-gen5-plan-review-sha256 bdd23fb26ff1cf7edbe4fbae8efb41b34b22bbaa72e9fa8e88f2231b035bd167 --gen6-plan-review-sha256 <64-lowerhex> --gen6-pre-capability-review-sha256 <64-lowerhex> --gen6-implementation-review-sha256 <64-lowerhex>
```

Reordered, missing, duplicate, extra, uppercase, or aliased options block. Old
gen4 setup/build/sign/launch
routes remain fail-closed. The CLI pins reviewed M2, the failed-gen3 plan and
implementation reviews, the gen4 and gen5 plan reviews, and the gen6 plan,
pre-capability, and implementation reviews exactly as shown. The validators
derive and rehash every plan/source digest required by those review schemas; no
unpassed predecessor hash is caller-selected. Setup validates all namespaces,
quarantined lstat-only
invariants, source-only imports, the complete CPU/no-model surface trace, and
all failed-generation terminal payloads before any write.

The gen6 setup journal is a create-once receipt-prefix DAG equivalent to the
frozen gen5 design, with one inserted failed-gen5 receipt. Its exact ordered receipts are:

1. gen6 provenance root;
2. `failed_gen5.json`;
3. `failed_gen4.json`;
4. `failed_gen3.json`;
5. `failed_gen2.json`;
6. gen6 M4-data root;
7. gen6 config root;
8. gen6 state root;
9. gen6 nonce root;
10. setup-key subordinate staging root;
11. private-key payload;
12. key binding;
13. final private key;
14. setup subject;
15. public key;
16. authorization commitment;
17. CPU/no-model trace;
18. protocol config;
19. key-binding deletion;
20. key-payload deletion;
21. key-staging-root removal;
22. pre-manifest projection verification;
23. setup-manifest publication.

Receipts are mode-0600 canonical JSON with the exact names:
`0001_gen6_provenance_root.json`, `0002_failed_gen5.json`,
`0003_failed_gen4.json`, `0004_failed_gen3.json`, `0005_failed_gen2.json`,
`0006_gen6_m4_data_root.json`, `0007_gen6_config_root.json`,
`0008_gen6_state_root.json`, `0009_gen6_nonce_root.json`,
`0010_key_staging_root.json`, `0011_key_payload.json`,
`0012_key_binding.json`, `0013_final_private_key.json`,
`0014_setup_subject.json`, `0015_public_key.json`,
`0016_authorization_commitment.json`, `0017_cpu_no_model_trace.json`,
`0018_protocol_config.json`, `0019_key_binding_deleted.json`,
`0020_key_payload_deleted.json`, `0021_key_staging_root_removed.json`,
`0022_pre_manifest_projection.json`, and `0023_setup_manifest.json`.
Each receipt uses schema `msae_v3_gen6_setup_receipt_v1` with exact keys
`schema_version`, `protocol_id`, `generation`, `index`, `step`, `action`,
`target`, `transaction_sha256`, `predecessor_receipt_sha256`, and
`payload_sha256` (null for mkdir/delete/rmdir verification). Receipts do not
embed inode/timestamp fields; the setup subject/manifest independently bind the
complete final lstat projection. All receipt bytes are recursively derived from
the root descriptor and registered action result.
A valid state has a receipt prefix and at most the next registered
action object/adjacent partial/attempt-marker prefix. The setup transaction
descriptor binds all predicted deterministic payloads, review authority,
mount identity, exact receipt list, roots, and publisher descriptors. All writes
use the registered publisher. The setup manifest binds all
receipts through 0022, the exact derivation rule for receipt 0023, exact
directories, final entries, review authorities, and the private
key lstat/public-key agreement. M3 contains no execution authorization.
Receipt 0023 then binds the published manifest digest; the manifest does not
embed receipt 0023 and therefore has no digest cycle. Reverse cleanup validates
all 23 receipts before removing them and the root descriptor.

An independent post-M3 adversarial SHIP review binds the exact implementation,
setup manifest/subject, protocol, commitment/public key, private-key lstat with
content unread, CPU trace, failed-gen2/gen3/gen4/gen5 records, zero quarantined reads,
and complete downstream absence.

## Exact review schemas

Every review is canonical UTF-8, mode 0644, UID-owned, nlink 1, newline
terminated, and has unique ordered controls. Malformed/indented/duplicate/extra
control-like lines block. Each review is externally published create-once with
no-follow `O_EXCL`, full write, file fsync, and parent fsync; pre-existing,
partial, symlinked, hardlinked, permissive, noncanonical, or rewritten review
bytes block rather than being repaired in place.

The plan review scope is `gen6_plan` with controls:
`FAILED_GEN4_PLAN_SHA256`, `FAILED_GEN4_PLAN_REVIEW_SHA256`,
`FAILED_GEN5_PLAN_SHA256`, `FAILED_GEN5_PLAN_REVIEW_SHA256`, and
`GEN6_PLAN_SHA256`.

The pre-capability review scope is `gen6_pre_capability`. It is written only
after all implementation bytes and all safe verification commands, including
the registered real non-experiment tmux containment test, are final and pass.
In exact order it binds: `GEN6_PLAN_SHA256`, `GEN6_PLAN_REVIEW_SHA256`,
`GEN6_CONTROLLER_SHA256`, `GEN6_RUNTIME_SHA256`, `GEN6_RUNNER_SHA256`,
`GEN6_LAUNCHER_SHA256`, `GEN6_TMUX_TEST_SUPERVISOR_SHA256`, `GEN6_RFC_SHA256`,
`GEN6_TESTS_SHA256`, and `SEALED_PAYLOAD_CONTENT_READS: 0`. Its mandatory
`CHECKS RUN` section records the exact argv, cwd, closed environment, exit status,
and result summary for the complete CPU/predecessor/static/publisher/import and
real-tmux command set. A review is not SHIP if any command result is missing,
stale, or was run on bytes different from the nine bound plan/review/code
subjects. Capability publication is forbidden before this exact review is
descriptor-safely revalidated.

The implementation review scope is `gen6_implementation`. In exact order it
binds: `M1_COMPLETION_SHA256`, `M2_COMPLETION_SHA256`,
`FAILED_GEN3_PLAN_SHA256`, `FAILED_GEN3_PLAN_REVIEW_SHA256`,
`FAILED_GEN3_CONTROLLER_SHA256`, `FAILED_GEN3_RUNTIME_SHA256`,
`FAILED_GEN3_RUNNER_SHA256`, `FAILED_GEN3_LAUNCHER_SHA256`,
`FAILED_GEN3_RFC_SHA256`, `FAILED_GEN3_TESTS_SHA256`,
`FAILED_GEN3_IMPLEMENTATION_REVIEW_SHA256`, `HISTORICAL_PREFLIGHT_SHA256`,
`PREDICTED_GEN6_FAILED_GEN3_SHA256`, `PREDICTED_GEN6_FAILED_GEN2_SHA256`,
`FAILED_GEN4_PLAN_SHA256`, `FAILED_GEN4_PLAN_REVIEW_SHA256`,
`FAILED_GEN4_CONTROLLER_SHA256`, `FAILED_GEN4_RUNTIME_SHA256`,
`FAILED_GEN4_RUNNER_SHA256`, `FAILED_GEN4_LAUNCHER_SHA256`,
`FAILED_GEN4_RFC_SHA256`, `FAILED_GEN4_TESTS_SHA256`,
`FAILED_GEN5_PLAN_SHA256`, `FAILED_GEN5_PLAN_REVIEW_SHA256`,
`FAILED_GEN5_CONTROLLER_SHA256`, `FAILED_GEN5_RUNTIME_SHA256`,
`FAILED_GEN5_RUNNER_SHA256`, `FAILED_GEN5_LAUNCHER_SHA256`,
`FAILED_GEN5_TMUX_TEST_SUPERVISOR_SHA256`, `FAILED_GEN5_RFC_SHA256`,
`FAILED_GEN5_TESTS_SHA256`, `GEN6_CAPABILITY_REPRODUCTION_SHA256`,
`PREDICTED_GEN6_FAILED_GEN5_SHA256`, `PREDICTED_GEN6_FAILED_GEN4_SHA256`,
`GEN6_PLAN_SHA256`, `GEN6_PLAN_REVIEW_SHA256`,
`GEN6_PRE_CAPABILITY_REVIEW_SHA256`, `GEN6_CONTROLLER_SHA256`,
`GEN6_RUNTIME_SHA256`, `GEN6_RUNNER_SHA256`, `GEN6_LAUNCHER_SHA256`,
`GEN6_TMUX_TEST_SUPERVISOR_SHA256`, `GEN6_RFC_SHA256`, and
`GEN6_TESTS_SHA256`, and `SEALED_PAYLOAD_CONTENT_READS: 0`. The terminal digest
is predicted without the
implementation review digest. Before accepting this review, the parser
independently reconstructs the capability schema and requires
`overall_pass=true`; binding the digest of a false or malformed report never
authorizes setup.

The post-M3 scope is `gen6_post_m3` with ordered controls:
`GEN6_IMPLEMENTATION_REVIEW_SHA256`, `POST_M3_SUBJECT_SHA256`,
`GEN6_PROTOCOL_SHA256`, `GEN6_AUTHORIZATION_COMMITMENT_SHA256`,
`GEN6_PUBLIC_KEY_SHA256`, `GEN6_CPU_TRACE_SHA256`,
`GEN6_SETUP_MANIFEST_SHA256`, `GEN6_FAILED_GEN5_SHA256`,
`GEN6_FAILED_GEN4_SHA256`, `GEN6_FAILED_GEN3_SHA256`,
`GEN6_FAILED_GEN2_SHA256`, and
`M2_COMPLETION_SHA256`, and `SEALED_PAYLOAD_CONTENT_READS: 0`.

The prescore scope is `gen6_prescore` with ordered controls:
`GEN6_IMPLEMENTATION_REVIEW_SHA256`, `GEN6_POST_M3_REVIEW_SHA256`,
`GEN6_PROTOCOL_SHA256`, `GEN6_STAGE_A_SHA256`, `GEN6_STATUS_SHA256`,
`GEN6_CANDIDATE_MANIFEST_SHA256`, `GEN6_DEPENDENCY_CLOSURE_SHA256`,
`GEN6_ENDPOINT_REGISTRY_SHA256`, `GEN6_ENVIRONMENT_ALLOWLIST_SHA256`,
`GEN6_PRESCORE_CHECK_SHA256`, `GEN6_PRESCORE_TRACE_SHA256`,
`GEN6_PRESCORE_CHECKER_SHA256`, and `SEALED_PAYLOAD_CONTENT_READS: 0`.

Plan/pre-capability/implementation authorities and all predecessor terminal
entries are bound again in protocol config, setup subject/manifest,
authorization commitment,
CPU trace, closure, both M4 trees, Stage A, candidate manifest, post-M3 review,
prescore review, signed envelope, and prelaunch/worker validation.

## Gen5-to-gen6 substitution table

| Surface | Gen5 | Gen6 |
|---|---|---|
| generation | `post_m2_gen5` | `post_m2_gen6` |
| public commands | `*-gen5` | `*-gen6` |
| controller/runtime/runner/launcher | `*gen5*` | `*gen6*` |
| real-tmux test supervisor | exact frozen gen5 path | exact reviewed gen6 supervisor path above |
| plan/RFC/tests | `*gen5*` paths | exact gen6 paths above |
| config/provenance/M4 data | `...post_m2_gen5` | `...post_m2_gen6` |
| setup/key/M4/sign transactions | gen5 names | exact gen6 names above |
| reviews/scopes/controls | `GEN5_*`, `gen5_*` | exact `GEN6_*`, `gen6_*` schemas above |
| state/nonce/run | gen5 roots | exact gen6 roots above |
| prescore evidence/tmux session | gen5 prefix/session | exact gen6 prefix/session above |
| tmux `-S` socket | impossible 119-byte frozen path | `/tmp/m6t_<full-stage-sha256>.sock` |
| broker handoff socket | impossible 129-byte run-root `broker.sock` | `/tmp/m6b_<full-stage-sha256>.sock` |
| tmux startup/containment | daemonizing one-shot `new-session` client with gen5 cleanup | persistent outside-tmux subreaper monitor, captured foreground `tmux -D` server-only process, separate bounded clients, complementary in-pane supervisor, descendant capture, and exact extended cleanup above |
| M4 outputs | gen5 data/provenance six-file set | gen6 data/provenance six-file set |
| Stage B | gen5 run-root terminal schema | byte-identical schema with generation/path substitution |
| terminal failure | gen5 run-root schema | byte-identical schema with generation/path substitution |
| publisher | descriptor/mount-bound linkat state machine | byte-identical algorithm with generation/path substitution |

All other scientific fields and schemas must compare byte-identically after
this typed substitution. Control-plane differences are permitted only in the
literal table rows above and their explicitly registered tests/closure entries.
A broad textual replacement is forbidden.

## Exact phase projections

- Post-plan-review/pre-implementation: only the gen6 plan and plan review exist.
- Pre-capability review: add exactly the seven gen6 controller/runtime/runner/
  launcher/tmux-supervisor/RFC/test entries. The pre-capability review,
  capability analysis root/report/transaction/probe root, all gen6 config,
  provenance, M4-data, key, state, run, scratch, evidence, both short socket
  families, and later reviews are absent.
- Post-pre-capability-review/pre-capability: add only the exact pre-capability
  SHIP review. The capability report/transaction/probe root and every later
  artifact remain absent.
- Post-capability/pre-implementation-review: add exactly the canonical
  capability-reproduction report; its transaction and probe root are absent and
  the complete `m6t_*`/`m6b_*` projection is empty. No implementation review or
  protocol state exists.
- Post-implementation review/pre-M3: add only the implementation review.
- Post-M3: config contains exactly `protocol.json`,
  `authorization_commitment.json`, `ed25519_public.pem`, and
  `cpu_no_model_public_entry_trace.json`; provenance contains exactly
  `failed_gen5.json`, `failed_gen4.json`, `failed_gen3.json`, `failed_gen2.json`, and
  `setup_m3_gen6_manifest.json`; M4 data is empty; state contains the empty
  `nonces/`; the private key exists; setup journal and key-staging root are absent; run,
  M4 scratch/transaction, evidence, socket, and later reviews are absent.
- Post-post-M3-review: add only the post-M3 review.
- Post-M4: M4 data contains exactly `dependency_closure.json`,
  `endpoint_registry.json`, and `environment_allowlist.json`; provenance adds
  exactly `stage_a.json`, `status.json`, and
  `prescore_candidate_manifest.json`; both M4 roots/transaction are absent.
- Post-prescore: add exactly the digest-derived check/trace and prescore review.
- Post-sign: the run root contains exactly mode-0600 `authorization.json`;
  `.sign_transaction` is absent. A legal sign-recovery prefix contains only its
  descriptor, registered payload/partial, and attempt-marker prefix.
- Launch top-level allowlist:
  `authorization.json`, `launcher_intent.json`, `logs`,
  `tmux_monitor.json`, `lock_acquired.json`, `handoff.json`, `nonce_consumed.json`,
  `observed_environment.json`, `tolerance_selection.json`,
  `cached_noop_hash_replay.json`, `canonical_pooling_qa.json`,
  `counterfactual_cache_alignment_qa.json`, `cache`, `terminal.claim`,
  `.terminal_failure_staging`, `terminal_failure`,
  `.terminal_success_staging`, and `terminal_success`.
- `logs` has exactly the prefix `{}` → `{monitor.log}` →
  `{monitor.log,tmux_server.log}` →
  `{monitor.log,tmux_server.log,broker.log}` →
  `{monitor.log,tmux_server.log,broker.log,worker.log}`; all are mode-0600
  regular files opened no-follow before their owning process starts. The launcher
  alone creates/opens the monitor/server logs and passes their exact FDs; the
  in-pane supervisor alone creates `broker.log`; the broker alone creates
  `worker.log`. No two roles share creation authority. `cache` has exactly
  `{main_long,main_short,pair_context,pair_entity}`; each stratum has
  `forward_0.npy` through `forward_3.npy` and then `pooling_per_unit.npy` in the
  scientific order below.
- Literal control rows are `R0={}` (run absent),
  `R1={authorization.json}`, `R2=R1+{launcher_intent.json}`,
  `R3=R2+{logs}`, `R4=R3+{tmux_monitor.json}`,
  `R5=R4+{lock_acquired.json}`, `R6=R5+{nonce_consumed.json}`, and
  `R7=R6+{handoff.json}`. The external
  `/tmp/m6b_<stage_a_sha256>.sock` may exist only from launcher bind through
  broker handoff and must be descriptor-bound, absent before/after, and never a
  run-root child. No row admits a missing predecessor or extra child.
- After final-gate acknowledgement, the external broker socket is removed and the exact
  scientific sequence is: `observed_environment.json`; `cache/`; for
  `main_long`, `main_short`, `pair_context`, `pair_entity` in that order,
  create the stratum directory and `forward_0.npy` through `forward_3.npy`;
  `tolerance_selection.json`; `cached_noop_hash_replay.json`; the four
  `pooling_per_unit.npy` files in the same order;
  `canonical_pooling_qa.json`; and
  `counterfactual_cache_alignment_qa.json`. At most that exact prefix is legal.
- Success creates `.terminal_success_staging` with the sorted prefix of exactly
  `stage_b.json`, `status.json`, `runtime_native_pre_import.json`,
  `runtime_native_post_torch.json`, `runtime_native_post_model.json`, and
  `runtime_native_final.json`; creates `terminal.claim`; atomically exposes
  `terminal_success`; and retains the full scientific prefix. Failure may start
  from any valid R1--R7/scientific prefix, removes success staging/socket,
  creates `terminal.claim`, creates `.terminal_failure_staging` with
  `technical_failure.json` then `status.json`, and atomically exposes
  `terminal_failure`. The final failure/success directories have those exact
  file sets. Outcomes/staging are mutually exclusive.
- No nonregular run child is allowed. The broker `/tmp` socket exists only for
  live handoff and is removed before launcher return. The registered tmux-control
  socket and dedicated tmux session may remain only while the calibration run is
  live; terminal/failure cleanup proves the session, foreground server, captured
  groups, and socket extinct. No other short-family entry is ever legal.

At every phase, ignored/untracked entries count. The verifier enumerates all
children with lstat, rejects symlink ancestors and same-inode aliases, and
reconstructs the expected projection independently of the candidate manifest.

## M4, prescore, signing, and launch

Except for gen6 namespaces, typed gen5 failure evidence, the two short socket
paths, and the explicit foreground-server/subreaper timeout-containment extension,
M4, prescore,
authorization, nonce, GPU lease, watchdog, two-phase model gate, Stage-B QA,
and terminal-result semantics are identical to the frozen gen5 plan:

1. materialize two initially absent complete sparse candidate trees without
   live-repository fallback;
2. compare full tree/file/directory/config/closure/Stage-A/manifest bytes;
3. reauthorize live inputs and the post-M3 subject before install;
4. install the ordered six-file M4 prefix using the registered publisher;
5. run the digest-derived traced prescore check and obtain an external SHIP
   review with exact controls and sealed reads zero;
6. sign one nonce/time-bound calibration-only envelope through a recoverable
   descriptor transaction using the same publisher;
7. let only the signed launcher query GPUs, acquire the shared UUID lock, and
   start the exact tmux handoff;
8. return after durable readiness/final ACK without waiting for calibration.

For Stage-A digest `D`, the launcher derives exactly
`tmux_socket=/tmp/m6t_${D}.sock` and
`broker_socket=/tmp/m6b_${D}.sock`; `D` must match `[0-9a-f]{64}` and both
encoded paths must equal 78 bytes. The authorization, candidate manifest,
launcher intent, readiness, handoff, broker, worker, cleanup, and terminal
evidence bind both distinct strings, the held `/tmp` parent/mount row, closed
umask 0077, and each live socket's device/inode/UID/GID/mode-0700/nlink-1 phase
identity. The broker
socket never appears under the run root. Both are absent before GPU selection,
created only after the UUID lease is held, and no-follow identity-checked around
every use. The broker socket is removed and proven absent before the durable
final ACK/launcher return. The tmux server socket remains identity-bound while
the calibration session is live so watchdog/cleanup can address that server;
handoff and terminal records bind it. It is removed only after terminal outcome
or failure, once the session/server and every captured process/group are proven
extinct. Prelaunch requires both absent; a later launch is forbidden by the
single-use nonce rather than by pretending the live tmux socket is absent.

### Monitor record and control protocol

`tmux_monitor.json` has schema `msae_v3_gen6_tmux_monitor_v1` and the exact
top-level keys, in canonical order: `schema_version`, `protocol_id`,
`generation`, `status`, `created_utc`, `stage_a_sha256`,
`authorization_envelope_sha256`, `launcher_intent_sha256`,
`launch_capability_sha256`, `gpu`, `lease`, `launcher`, `monitor`, `code`,
`control`, `inherited_fds`, `logs`, `tmux_socket_path`, `broker_socket_path`,
`handoff_deadline_unix`, and `terminal_deadline_unix`. Literal values are
`protocol_id=msae_independent_measurement_v3`, `generation=post_m2_gen6`, and
`status=monitor_record_committed`. `gpu` is exactly `{uuid,index}`. `lease` is
exactly `{path,device,inode,uid,gid,mode,nlink,payload_sha256}`. `launcher` is
exactly `{pid,start_ticks}`. `monitor` is exactly
`{pid,start_ticks,pgid,argv_sha256}`; the capability-bearing argv plaintext is
validated live but is not persisted. `code` is exactly
`{controller_sha256,runtime_sha256,dependency_closure_sha256}`. `control` is
exactly `{family,type,launcher_pid,launcher_uid,launcher_gid,monitor_pid,
monitor_uid,monitor_gid}` with literal `AF_UNIX`/`SOCK_SEQPACKET`.
`inherited_fds` is exactly `{control,lease,monitor_log,server_log}` with four
mutually distinct decimal integers each at least 3. Before monitor code proceeds,
it proves control is the one bound socket endpoint, lease/log objects match their
exact identities, FDs 0/1/2 have only the registered stdio bindings, every
unrelated FD is closed, and only the intended exec/pass-through descriptors have
their registered inheritable flags. `logs` is exactly `{monitor,server}`;
each value is exactly `{path,device,inode,uid,gid,mode,nlink}` for its bound
mode-0600 file. All hashes are lowercase ASCII SHA-256, all paths/IDs/deadlines
must equal independently derived signed/live values, and no null/extra key is
accepted. The record contains no self-digest; later frames bind the SHA-256 of
its exact canonical bytes.

The socketpair carries one canonical UTF-8 JSON object per `SOCK_SEQPACKET`
datagram, maximum 65,536 bytes, with no ancillary FDs after process creation,
no `MSG_TRUNC`, no trailing bytes, and stable `SO_PEERCRED`. Every successful
frame has schema `msae_v3_gen6_monitor_frame_v1` and exact common keys
`schema_version`, `protocol_id`, `generation`, `frame_type`, `sequence`,
`prior_frame_sha256`, and `payload`. Sequence is the literal ordinal below;
`prior_frame_sha256` is null only for frame 1 and otherwise hashes the exact
preceding frame. This table is the authoritative successful wire schema:

| Seq | Direction/type | Exact payload keys |
|---:|---|---|
| 1 | monitor→launcher `MONITOR_HELLO` | `monitor_pid`, `monitor_start_ticks`, `monitor_pgid`, `monitor_argv_sha256`, `environment_sha256`, `inherited_fd_set_sha256`, `launcher_intent_sha256` |
| 2 | launcher→monitor `MONITOR_RECORD_COMMITTED` | `record_path`, `record_sha256` |
| 3 | monitor→launcher `MONITOR_RECORD_ACK` | `record_sha256`, `record_subject_sha256` |
| 4 | launcher→monitor `START_SERVER` | `record_sha256`, `record_ack_sha256`, `tmux_socket_path`, `broker_socket_path` |
| 5 | monitor→launcher `SERVER_READY` | `server_pid`, `server_start_ticks`, `server_pgid`, `pane_pid`, `pane_start_ticks`, `tmux_socket_binding`, `session`, `exit_empty`, `server_start_transcript_sha256` |
| 6 | launcher→monitor `HANDOFF_COMMITTED` | `handoff_sha256`, `gate_confirmation_sha256`, `broker_family_projection_sha256` |
| 7 | monitor→launcher `TAKEOVER_ACK` | `handoff_sha256`, `gate_confirmation_sha256`, `monitor_live_subject_sha256`, `terminal_deadline_unix` |

`tmux_socket_binding` is the exact device/inode/UID/GID/mode/nlink object defined
above; `session` is the one literal registered name and `exit_empty` is literal
`on`. Every payload has exactly the listed keys and independently revalidates its
live subject before send and after receive. A failure before frame 7 is expressed
by terminal claim plus channel EOF/process status, never by an unregistered frame.
Wrong direction/type/sequence, duplicate/extra frame, stale prior digest,
credential drift, truncation, timeout, or EOF at any other point blocks and
enters the registered cleanup path.

All derived monitor digests have these exact canonical JSON preimages:

- `record_subject_sha256` hashes an object with exact keys `schema_version`
  (`msae_v3_gen6_monitor_record_subject_v1`), `record_sha256`, `record_entry`,
  `monitor_process`, `inherited_fd_bindings`, `launcher_intent_sha256`, and
  `run_root_binding`. `record_entry` is exactly
  `{path,device,inode,uid,gid,mode,nlink,size,sha256}`;
  `monitor_process` is exactly `{pid,start_ticks,ppid,pgid,uid,gid}`;
  `inherited_fd_bindings` is exactly `{control,lease,monitor_log,server_log}` and
  each value is exactly `{fd,type,device,inode,uid,gid,mode,nlink,path}` (path is
  null only for the unnamed socketpair endpoint); `run_root_binding` is exactly
  `{path,device,inode,uid,gid,mode,nlink}`.
- `record_ack_sha256` is exactly the SHA-256 of canonical frame-3
  `MONITOR_RECORD_ACK` bytes, not a free-standing caller value.
- `server_start_transcript_sha256` hashes an object with exact keys
  `schema_version` (`msae_v3_gen6_server_start_transcript_v1`), `record_sha256`,
  `server_argv`, `server_process`, `tmux_socket_binding`, `new_session_argv`,
  `new_session_returncode`, `set_option_argv`, `set_option_returncode`,
  `show_options_argv`, `show_options_returncode`, `show_options_stdout`,
  `display_argv`, `display_returncode`, `display_stdout`, `pane_process`, and
  `descendant_projection_sha256`. Process objects are exactly
  `{pid,start_ticks,ppid,pgid,uid,gid}`; every argv is the literal vector above;
  return codes are integer zero and observed stdout is the exact canonical text.
- `broker_family_projection_sha256` hashes an object with exact keys
  `schema_version` (`msae_v3_gen6_broker_family_projection_v1`),
  `tmp_parent_binding`, `exact_broker_path`, and `entries`, where the parent
  binding is exactly `{path,device,inode,uid,gid,mode,mountinfo_sha256}` and
  `entries` is the canonical empty list after broker-socket removal.
- `monitor_live_subject_sha256` hashes an object with exact keys
  `schema_version` (`msae_v3_gen6_monitor_live_subject_v1`), `record_sha256`,
  `handoff_sha256`, `gate_confirmation_sha256`, `monitor_process`, `lease`,
  `server_process`, `pane_process`, `broker_process`, `worker_process`,
  `tmux_socket_binding`, `broker_family_projection_sha256`, and
  `terminal_deadline_unix`. Process, lease, and socket objects reuse the exact
  schemas above and are revalidated live immediately before frame 7.

The `control_channel_transcript_sha256` stored in `handoff.json` hashes
`canonical_bytes([frame_1,frame_2,frame_3,frame_4,frame_5])` only. Frames 6 and 7
are necessarily excluded because frame 6 contains `handoff_sha256`; this exact
five-frame prefix prevents a digest cycle. Frame 6 separately binds the handoff
digest and frame 7 binds both frame 6 and the live takeover subject.

Every `nvidia-smi` query and every nonserver tmux client has a frozen
15-second timeout. After the repeated idle check, UUID lease, durable launcher
intent, log-directory creation, and bound broker socket, the launcher creates one
`AF_UNIX/SOCK_SEQPACKET` socketpair with `SOCK_CLOEXEC`; only the child control FD
and a duplicate of the held lease FD are made inheritable. The launcher also
creates `logs/monitor.log` then `logs/tmux_server.log` with no-follow `O_EXCL`,
mode 0600, current UID/nlink 1, file fsync and log-directory fsync, opens and
identity-binds each, and makes only those two log FDs inheritable. It starts one
source-only internal monitor in its own process group with exact argv
`[<isolated-python>,-S,-B,-I,<gen6-controller>,monitor-tmux-gen6,--control-fd,
<decimal-fd>,--lease-fd,<decimal-fd>,--gpu-uuid,<uuid>,--gpu-index,<decimal>,
--monitor-log-fd,<decimal-fd>,--server-log-fd,<decimal-fd>,
--launch-capability,<64-lowerhex>,--intent-sha256,<64-lowerhex>]`, `pass_fds`
containing exactly those four FDs, the closed registered environment,
`start_new_session=true`, `shell=false`, and registered monitor stdout/stderr.
Direct or stale invocation fails before tmux/model work. The monitor revalidates
the launcher intent/capability, exact peer PID/start-tick, all four inherited FDs,
GPU lock object/path, both log objects/paths, and closed environment; duplicates
only `monitor.log` to its stdout/stderr; sets and verifies
`PR_SET_CHILD_SUBREAPER=1`; and sends a canonical monitor-hello frame. The
launcher binds its PID/start-tick/PGID/argv/code digest/control-peer credentials
and publishes mode-0600 `tmux_monitor.json` before accepting any broker identity.
It then sends `MONITOR_RECORD_COMMITTED` with the exact record digest. Through a
held run-root descriptor, the monitor reopens and independently validates the
canonical record, its own complete identity/argv/code/environment/FD bindings,
and stable path metadata, then replies `MONITOR_RECORD_ACK`. After validating
that ACK, the launcher sends `START_SERVER` binding the record and ACK digests;
the monitor is forbidden to fork the tmux server before it validates that exact
next frame. EOF after ACK but before `START_SERVER` is a pre-server failure.

The monitor, not the soon-returning launcher, owns tmux for the whole live run.
It forks one child that calls and verifies `setsid()` (so PID=PGID and it is not
in the monitor group), sets `PR_SET_PDEATHSIG=SIGKILL`, verifies the monitor
parent again, and `execve`s exact server-only argv
`[/usr/bin/tmux,-D,-f,/dev/null,-S,/tmp/m6t_${D}.sock]` with the closed
environment and registered server log. Installed tmux forbids any command when
global `-D` is present, so this argv contains no `new-session` token. Global
`-D` keeps the server in the foreground; its PID/start-tick/PGID and parent link
are the server authority. After the exact mode-0700 socket and server identity
appear within 15 seconds, the monitor starts a separate captured `shell=false`
client group with exact argv
`[/usr/bin/tmux,-f,/dev/null,-S,/tmp/m6t_${D}.sock,new-session,-d,-s,
msae-independent-v3-gen6-calibration,/usr/bin/bash,--noprofile,--norc,-c,
<exact-content-bound-supervise-broker-command>]`, the same closed environment/log
binding, and a 15-second deadline. Its PID/start-tick/PGID are recorded before it
may affect handoff. After it returns zero, the monitor runs the exact bounded
client `[/usr/bin/tmux,-f,/dev/null,-S,/tmp/m6t_${D}.sock,set-option,-s,
exit-empty,on]`; `-s` selects the server option. It immediately runs the bounded
proof client `[/usr/bin/tmux,-f,/dev/null,-S,/tmp/m6t_${D}.sock,show-options,
-s,-v,exit-empty]` and requires canonical stdout `on\n`; together these restore
and verify exit-on-empty after `-D` turned it off. It then runs exact bounded identity argv
`[/usr/bin/tmux,-f,/dev/null,-S,/tmp/m6t_${D}.sock,display-message,-p,-t,
msae-independent-v3-gen6-calibration,"#{pid} #{pane_pid}"]`; the quotes denote one
literal argv element and are not passed. Stdout must be one canonical line with
exactly two positive unpadded decimal PIDs, and the first must equal the captured
foreground-server PID. The monitor then sends exact frame-5 `SERVER_READY`; the
launcher revalidates its complete live payload and will not accept or signal any
broker identity before that frame passes.

From monitor start until terminal cleanup, its 50-millisecond bounded loop walks
`/proc` with the robust `stat` parser and records every same-UID descendant
PID/start-tick/PPID/PGID and every later child it adopts as subreaper. Before any
other broker work, the source-only in-pane supervisor deliberately does **not**
arm parent death. It installs serialized TERM/HUP/INT handlers, binds the exact
server/socket/monitor/intent identities, and is the complementary cleanup
authority that survives a foreground-server or monitor death and pty HUP. It
starts the broker as its child; the broker and worker each arm and verify
`PR_SET_PDEATHSIG=SIGKILL`. The broker validates intent and connects and may not
fork the worker until the launcher validates `SO_PEERCRED`, the durable monitor/
server/pane identities, and transfers the lease. The worker reports its dedicated
PGID before the pre-model gate. Monitor-ready and every later control frame have exact
canonical schemas, monotonically increasing sequence numbers, peer credentials,
full lineage digests, and a shared 30-second handoff deadline. Duplicate, late,
partial, malformed, reordered, EOF-before-commit, or extra frames block.

Only after runner pre-model readiness is validated does the launcher write and
fsync `handoff.json`, send the final model gate through the broker, and validate
the runner acknowledgement and broker confirmation. It then closes/unlinks the
broker socket, proves the whole `m6b_*` family empty, and sends the monitor the
exact handoff/gate-confirmation transcript digests in `HANDOFF_COMMITTED`. The
launcher returns only after the monitor reopens/revalidates the durable handoff,
revalidates the gate-confirmation lineage and broker-socket absence, and replies
`TAKEOVER_ACK`. After that ACK, launcher-side EOF is expected; before it, EOF
means launcher death and the monitor claims technical failure. `handoff.json`
binds monitor PID/start-tick/PGID, exact argv/environment/code digest, server/
pane/broker/worker identities, both socket identities, lease, control-channel
transcript digest, and the monitor's six-hour absolute deadline.
The monitor retains a validated lease FD after launcher return, continuously
revalidates the lease, server/session/socket, descendant groups, and terminal
namespace, and races all failure writers only through the existing create-once
`terminal.claim`. Server, pane supervisor, broker, worker, lease, deadline, or
lineage loss before an exact terminal outcome produces technical-failure/not-run.
On exact terminal success/failure it validates the terminal, terminates/waits/
reaps any remaining groups, uses only bound 15-second tmux clients, proves session
and both sockets absent plus every captured/adopted PID/PGID extinct, releases the
lease, and exits. The monitor may not exit normally earlier. Monitor death causes
the server's parent-death SIGKILL; the in-pane supervisor survives the resulting
HUP, validates the bound handoff/server/socket state, TERM/KILLs and reaps its
broker/worker groups, unlinks only the still-bound tmux socket, races the same
terminal claim to technical-failure/not-run, verifies process/socket extinction,
and exits. Conversely, pane-supervisor death is detected and terminalized by the
monitor. Thus one of the two complementary authorities survives either single
monitor/server or pane-supervisor failure; neither treats the other's unvalidated
frame identity as signal authority.

Any server-socket, new-session, exit-empty, identity-client, accept, or ACK
timeout closes the listener/lease-transfer path and never releases the model
gate. Before launcher return, cleanup retains the launcher's lease and
TERM/waits three seconds then KILLs/waits three seconds for the validated monitor
group; the monitor independently performs the same cleanup for all client,
descendant, and server groups and repeats scans to a fixed 15-second extinction
deadline. Only fully validated captured/adopted identities are signaled. Fault
tests cover launcher EOF before/after commit, monitor death with surviving
in-pane cleanup, pane-supervisor death with surviving monitor cleanup, monitor ACK loss,
server pre-exec stall, delayed socket creation, stuck foreground server,
new-session and exit-empty uncertain completion, pane reparent/new PGID before
identity, broker reparent/new PGID before ACK, server death after launcher return,
lease loss, terminal-claim races, identity/cleanup-client timeout, dead leaders,
resistant descendants, and path substitution without invoking a GPU or real
calibration tmux.

The exact ordered public commands are:

```text
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen6.py build-m4-gen6 --post-m3-review-sha256 <64-lowerhex>
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen6.py prescore-traced-check --manifest reports/provenance/msae_independent_measurement_v3_post_m2_gen6/prescore_candidate_manifest.json --output /tmp/msae_independent_measurement_v3_post_m2_gen6_<manifest_sha256>.prescore.check.json --trace /tmp/msae_independent_measurement_v3_post_m2_gen6_<manifest_sha256>.prescore.trace.log
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen6.py verify-prescore-trace --manifest reports/provenance/msae_independent_measurement_v3_post_m2_gen6/prescore_candidate_manifest.json --check /tmp/msae_independent_measurement_v3_post_m2_gen6_<manifest_sha256>.prescore.check.json --trace /tmp/msae_independent_measurement_v3_post_m2_gen6_<manifest_sha256>.prescore.trace.log
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen6.py sign-gen6
scripts/launch_msae_independent_calibration_v3_gen6.sh
```

`monitor-tmux-gen6`, `supervise-broker-gen6`, `broker-gen6`, and the runner are
internal capability-gated routes, not public commands. Each requires the exact
intent/capability, parent/peer lineage, inherited FD set, argv, and closed
environment registered above and fails before tmux, GPU use, or model import on
direct, stale, reordered, or replayed invocation.
The static/value-flow and CPU behavioral closure add exact site-specific mappings
for the control `socketpair`, four inherited monitor FDs, monitor/server/client
argv and environments, `prctl`/`setsid`, `/proc` descendant scans, log and monitor
record paths, all canonical frame schemas, and every bounded tmux vector. No
global path registry, arbitrary FD/argv, unbound socket method, or unregistered
internal route is introduced.

Calibration may build Stage B only. Any detected timeout, lease loss, broker/worker
death, OOM, exception, or invalid QA creates exactly one technical-failure
not-run terminal state and never exposes Stage B. The complementary monitor and
in-pane supervisor contracts cover either authority's individual death.
Scientific ineligibility is a
valid separate Stage-B outcome. Confirmation scoring and Stage C remain absent.

## Milestones

### P0 — plan authority

- [ ] Freeze this plan.
- [ ] Obtain an independent plan SHIP review at the gen6 plan-review path.
- [ ] Bind both exact files in every later artifact.

### P1 — implementation, pre-capability review, and capability

- [ ] Implement disjoint gen6 controller/runtime/runner/launcher/tmux-test-
  supervisor/RFC/tests.
- [ ] Run all predecessor and gen6 CPU/no-model tests.
- [ ] Run syntax, shell, diff, static-closure, value-flow, source-only-import, and
  quarantined-lstat checks.
- [ ] Run the registered publisher fault matrices and real non-experiment tmux
  containment test; verify every test namespace is absent afterward.
- [ ] Obtain an independent pre-capability SHIP review that freezes the exact
  plan/review and seven implementation-entry hashes plus the check results.
- [ ] Only then invoke the create-once capability command. Mechanically reproduce
  the gen4 NFS failure, both gen5 overlength-socket failures, and both gen6
  short-socket successes only in the registered disposable CPU paths; verify the
  canonical report, recovered-byte behavior, empty transaction/probe roots, and
  empty short-prefix socket families.
- [ ] Obtain an independent final implementation SHIP review binding the
  pre-capability review, capability report, exact implementation bytes, and
  predicted failed-generation records.

### P2 — M3

- [ ] Invoke `setup-m3-gen6` once with exact review pins.
- [ ] Verify completion and obtain a fresh post-M3 SHIP review.

### P3 — M4 and external prescore

- [ ] Build both M4 trees and install only after exact equality.
- [ ] Run the traced prescore check.
- [ ] Obtain a fresh external prescore SHIP review.

### P4 — authorization and handoff

- [ ] Sign the exact calibration-only envelope.
- [ ] Invoke the gen6 launcher.
- [ ] Allow that signed launcher alone to inspect free GPUs and create tmux.
- [ ] Report the durable handoff immediately without waiting.

## Verification plan

- P0: hash the plan/review; parse exact controls; run the plan structural gate.
- P1 publisher: run deterministic fault-injection tests for every source,
  attempt-marker, link, fsync, unlink, uncertain-result, mount-swap, and recovery
  boundary on NFS and a local temporary filesystem; assert exact bytes/child
  sets after each replay.
- P1 closure: run the complete predecessor+gen6 pytest set with plugins/cache
  disabled, the CPU/no-model every-public-entry trace, static/value-flow
  recomputation, malicious `.pyc`/sourceless/extension-shadow regressions,
  `py_compile`, `bash -n`, and `git diff --check`.
- P1 containment: run every verifier under the quarantined-open tripwire and
  compare before/after lstat for all three sealed files. Run the one real tmux
  extinction test only in its fixed non-experiment test socket/session namespace,
  with all GPU/model/query calls mocked, the factored persistent-monitor and
  complementary-pane-supervisor death directions exercised, and a final exact
  terminal/process/group/session/socket/scratch absence check.
- P1 monitor schema: mutate, omit, duplicate, reorder, truncate, and substitute
  every `tmux_monitor.json` field, nested key, frame common field, per-type payload
  field, sequence/prior digest, credential, FD, and direction; require rejection
  before the corresponding irreversible action and zero signals to unvalidated
  identities.
- P1 one-way sequencing: rehash all nine plan/review/implementation subjects and
  verify the complete test results before pre-capability review; revalidate that
  SHIP review immediately before the descriptor bootstrap; then publish the
  capability report exactly once and reconstruct its report bytes and namespace
  from the sealed descriptor in every injected recovery state. Only afterward
  may the final implementation review be created.
- P2: reconstruct the setup subject/manifest/receipts independently, compare
  exact namespace projections, and obtain an adversarial post-M3 SHIP verdict.
- P3: compare both complete M4 trees byte-for-byte, reconstruct the candidate
  manifest, run `strace -yy` prescore verification, and obtain an external SHIP
  review.
- P4: independently verify signature/nonce/intent/lease/handoff bindings and
  return only after the runner's pre-model readiness and durable final ACK.

## Definition of done

- [ ] Gen4 and gen5 plan/review/source subjects remain exact; gen5 is typed as
  failed before capability and all gen5 protocol state remains absent.
- [ ] Gen6 plan and independent plan review are immutable and machine-bound.
- [ ] Gen6 terminal evidence distinguishes capability testing from scientific work.
- [ ] Both registered gen6 AF_UNIX paths encode to exactly 78 bytes, bind in the
  capability test, and retain the full Stage-A digest. The broker socket is absent
  outside its bounded handoff interval; the tmux-control socket is absent before
  launch and after terminal/failure but remains identity-bound during the live
  calibration session. Every non-exact `m6t_*`/`m6b_*` sibling blocks.
- [ ] The publisher passes all registered NFS, uncertain-result, race, and crash
  tests on the actual repository filesystem.
- [ ] Every gen6 artifact and executable is in the exact candidate/closure manifest.
- [ ] All predecessor and gen6 tests pass without model/GPU/tmux use, except a
  separately controlled real-tmux extinction test run immediately before the
  pre-capability review.
- [ ] Static and behavioral closure cover every public entry and publication
  primitive; valid ignored bytecode/shadow modules cannot execute.
- [ ] The durable monitor-record/START_SERVER/takeover protocol and both
  complementary cleanup authorities pass real-process death/timeout/race tests;
  the launcher returns only after monitor takeover and the monitor remains an
  outside-tmux validated lease holder through terminal cleanup.
- [ ] A fresh adversarial pre-capability verdict is SHIP before the create-once
  capability report, and a fresh final implementation verdict is SHIP afterward.
- [ ] No setup, M4, signature, GPU query, model call, or tmux session occurs before
  its preceding review gate.

## Risks and one-way doors

- NFS can return an error after completing a namespace mutation. Exact-state
  reconstruction, durable attempt markers, and poison-on-ambiguity address this;
  unsupported mount semantics block rather than degrade.
- A same-UID concurrent process can race names or mounts. Held descriptors,
  no-follow operations, exact inode/mount revalidation, and undeclared-child
  rejection make such a race fail closed, though it can intentionally poison a
  generation.
- The successor is large because it preserves full provenance. The typed
  substitution comparison and complete predecessor test suite guard accidental
  scientific changes.

- Publishing the gen6 plan review freezes this plan.
- Publishing the pre-capability review freezes the seven implementation entries
  authorized for the capability observation. Publishing the capability report is
  a separate one-way door: a completed semantic/capability failure terminates
  gen6 before protocol state and cannot be reinterpreted or retried in gen6.
  Only crash recovery under the same durable descriptor, sealed report bytes,
  three-attempt limit, and deadline is permitted. The final implementation review
  may be published only after exact capability-report validation.
- `setup-m3-gen6` is the first gen6 protocol-state write.
- M4 installation, external review publication, signature creation, nonce
  consumption, and tmux handoff are separately irreversible transitions.
- A semantic/protocol failure is preserved as terminal evidence and never
  reinterpreted as passing or retried under the same generation. A crash or
  registered uncertain result may replay only the same descriptor-bound
  authority with at most three attempts and the transaction-kind deadline:
  capability/sign 300 seconds, setup 3600 seconds, or M4 21600 seconds. Expiry
  forbids only a new marker/link; exact-pair completion, destination-only
  acceptance, and reverse cleanup remain mandatory after expiry. That replay
  is not a new scientific transition.
