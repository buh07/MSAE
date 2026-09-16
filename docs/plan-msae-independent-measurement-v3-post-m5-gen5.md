# Plan: MSAE independent measurement v3 post-M5 gen5

## Status and purpose

This is a prospective, disjoint recovery generation. Gen4 is preserved as a
failed-before-M3 implementation attempt. Its reviewed plan required
`renameat2(RENAME_NOREPLACE)`, but the repository filesystem is NFS and a
CPU-only temporary-file probe returned `EINVAL`. No gen4 implementation review,
M3 state, Stage A, signature, GPU/model job, or tmux session was created.

Gen5 preserves the scientific protocol, frozen M1/M2 evidence, endpoints,
checkpoint lineages, thresholds, and run ordering. Its sole semantic change is
a registered, crash-recoverable no-replace publisher that works on the actual
NFS filesystem. It also records the terminal gen4 attempt honestly.

## Goal

Produce a reviewable gen5 implementation that can:

1. preserve gen4 as failed before its first one-way write;
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
- Do not open, hash, or content-read the three quarantined `final*.jsonl`
  payloads; lstat-only checks are mandatory around every guarded operation.
- Do not run setup, M4, signing, GPU inventory, model code, or tmux before its
  explicit review gate. CPU-only temporary capability tests are not experiments.
  The gen5 plan review alone authorizes one non-experiment tmux extinction test
  in session/socket namespace `msae-independent-v3-gen5-test-<pid>` with a fake
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

Create a disjoint gen5 control-plane generation around the unchanged scientific
protocol. First freeze and review this plan. Then copy the reviewed gen4
scientific/control logic through an explicit typed substitution, add a
descriptor/mount-bound linkat publisher and gen4 terminal evidence, and prove
the implementation with CPU-only fault injection. Cross M3, M4, external
prescore, signing, and live handoff as separate reviewed one-way transitions.

## Immutable predecessors

Gen5 binds and revalidates these authorities:

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

The original gen4 plan and review remain unchanged. Gen5 does not reinterpret
their authority.

## Exact namespaces

Gen5 uses only these new namespaces:

- plan: `docs/plan-msae-independent-measurement-v3-post-m5-gen5.md`;
- controller:
  `scripts/msae_independent_measurement_v3_post_m2_gen5.py`;
- runtime:
  `scripts/msae_independent_measurement_v3_post_m2_gen5_runtime.py`;
- runner: `scripts/run_msae_independent_calibration_v3_gen5.py`;
- launcher: `scripts/launch_msae_independent_calibration_v3_gen5.sh`;
- real-tmux test supervisor:
  `scripts/run_msae_independent_measurement_v3_post_m2_gen5_tmux_test.py`;
- RFC: `docs/rfc-msae-independent-measurement-v3-post-m5-gen5.md`;
- tests: `tests/test_msae_independent_measurement_v3_post_m5_gen5.py`;
- plan review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen5_plan.md`;
- implementation review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen5_implementation.md`;
- post-M3 review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen5_post_m3.md`;
- prescore review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen5_prescore.md`;
- config: `configs/msae_independent_measurement_v3_post_m2_gen5/`;
- provenance: `reports/provenance/msae_independent_measurement_v3_post_m2_gen5/`;
- M4 data: `data/msae_independent_measurement_v3_post_m2_gen5/`;
- private key:
  `/jumbo/lisp/f004ndc/.msae_keys/independent_measurement_v3_post_m2_gen5_ed25519_private.pem`;
- state:
  `/jumbo/lisp/f004ndc/.msae_state/independent_measurement_v3_post_m2_gen5/`;
- run:
  `pilot_runs/20260821_msae_independent_measurement_v3_post_m2_gen5_calibration/`;
- M4 roots:
  `/tmp/msae_independent_measurement_v3_post_m2_gen5_{primary,rebuild}`;
- setup journal:
  `reports/provenance/msae_independent_measurement_v3_post_m2_gen5/.setup_m3_gen5_transaction/`;
- setup manifest:
  `reports/provenance/msae_independent_measurement_v3_post_m2_gen5/setup_m3_gen5_manifest.json`;
- setup-key subordinate staging root (not a link transaction):
  `/jumbo/lisp/f004ndc/.msae_keys/.independent_measurement_v3_post_m2_gen5_setup/`;
- M4-install transaction:
  `reports/provenance/msae_independent_measurement_v3_post_m2_gen5/.m4_install_transaction/`;
- sign transaction:
  `pilot_runs/20260821_msae_independent_measurement_v3_post_m2_gen5_calibration/.sign_transaction/`;
- nonce directory:
  `/jumbo/lisp/f004ndc/.msae_state/independent_measurement_v3_post_m2_gen5/nonces/`;
- failed-gen4 terminal:
  `reports/provenance/msae_independent_measurement_v3_post_m2_gen5/failed_gen4.json`;
- inherited failed-gen3 terminal and gen2 failure, copied as typed gen5 evidence:
  `reports/provenance/msae_independent_measurement_v3_post_m2_gen5/{failed_gen3.json,failed_gen2.json}`;
- capability-reproduction report:
  `reports/analysis/msae_independent_measurement_v3_post_m2_gen5/gen4_publisher_capability_reproduction.json`;
- capability-report transaction:
  `reports/analysis/msae_independent_measurement_v3_post_m2_gen5/.capability_report_transaction/`;
- capability-probe root:
  `/jumbo/lisp/f004ndc/tmp/msae_independent_measurement_v3_post_m2_gen5_capability_probe`;
- prescore evidence:
  `/tmp/msae_independent_measurement_v3_post_m2_gen5_<manifest_sha256>.prescore.{check.json,trace.log}`;
- handoff socket:
  `/tmp/msae_independent_measurement_v3_post_m2_gen5_<stage_a_sha256>.sock`;
- tmux session: `msae-independent-v3-gen5-calibration`;
- NFS publisher fault-test root:
  `/jumbo/lisp/f004ndc/tmp/msae_independent_measurement_v3_post_m2_gen5_publisher_tests`;
- local-filesystem rejection-test root:
  `/tmp/msae_independent_measurement_v3_post_m2_gen5_mount_rejection_tests`;
- real-tmux extinction-test namespace, where `<supervisor_pid>` is the unpadded
  base-10 result of `os.getpid()` in the sole reviewed supervisor process:
  - session `msae-independent-v3-gen5-test-<supervisor_pid>`;
  - tmux server socket
    `/tmp/msae-independent-v3-gen5-test-<supervisor_pid>.tmux.sock`;
  - fake-broker ACK socket
    `/tmp/msae-independent-v3-gen5-test-<supervisor_pid>.ack.sock`;
  - scratch root `/tmp/msae-independent-v3-gen5-test-<supervisor_pid>.scratch`.

Publisher source basenames are not governed by one implicit naming convention;
the complete per-transaction source/destination table below is authoritative.
In particular, transaction-local payloads and adjacent `.<basename>.partial`
sources are ephemeral hard-link sources, while `private_key.payload` and
`key_binding.json` are authoritative subordinate staging destinations with
their own later deletion receipts. Every transaction has exactly one mode-0600
`transaction.json` descriptor and only its phase-registered sources, receipts,
or payload prefix. Review roots allow only the plan, plan review, implementation
review, post-M3 review, and prescore review at their registered phase. Config
has exactly four final children; provenance and M4 data use the phase child sets
listed below. Prescore evidence and the handoff socket must be absent until
their named phase.

Any undeclared gen5-prefixed sibling, symlink, hardlink, device, FIFO, socket,
wrong-owner object, wrong mode, or unexpected child blocks before a write.

## Gen4 terminal evidence

Before implementation review, the exact CPU-only command

```text
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen5.py probe-gen4-publisher-capability --output reports/analysis/msae_independent_measurement_v3_post_m2_gen5/gen4_publisher_capability_reproduction.json
```

creates one canonical mode-0644, UID-owned, nlink-1 report. It has schema
`msae_v3_gen5_gen4_capability_reproduction_v1`, writer generation
`post_m2_gen5`, exact argv/cwd/start/end UTC timestamps, the gen4 runtime entry,
numeric errno, filesystem `fstatfs` type/fsid, parsed mountinfo identity, exact
fixed probe root
`/jumbo/lisp/f004ndc/tmp/msae_independent_measurement_v3_post_m2_gen5_capability_probe`,
source/destination logical names and modes, before/after lstat rows,
transcript UTF-8 and SHA-256, `protocol_path_used=false`, and
`model_gpu_tmux=false`. Its disposable directory is exactly the fixed NFS root
above, is absent before/after, and cannot be caller-selected. The report schema
rejects any filesystem/mount identity other than the bound repository NFS mount.

Before its first gen5 protocol write, setup reconstructs a canonical
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

The record contains no self digest and no gen5 implementation-review digest;
the external implementation review binds its predicted digest. The result is
evidence of filesystem capability, not scientific execution. Gen5 setup
publishes it under the gen5 provenance root. The terminal record
states `m3=not_run`, `stage_a=not_run`, `authorization=not_created`, and
`model_gpu_tmux=not_run` for gen4.

`failed_gen3.json` has schema `msae_v3_gen5_failed_gen3_evidence_v1`, writer
generation `post_m2_gen5`, the exact immutable gen3 subject, the operator/
mechanical/current-absence evidence payload specified by the frozen gen4 plan,
and terminal fields `m3=not_created`, `stage_a=not_run`,
`authorization=not_created`, `model_gpu_tmux=not_run`. `failed_gen2.json` has
schema `msae_v3_gen5_failed_gen2_evidence_v1`, writer generation
`post_m2_gen5`, the exact gen2 M3 subject and private-key lstat, the mechanically
reproduced fixed-root four-field config diff, sealed reads zero, and terminal
fields `stage_a=not_created`, `m4=not_created`, `prescore=not_created`,
`authorization=not_created`, `model_gpu_tmux=not_run`. Both are canonical typed
gen5 wrappers, not claims that gen4 published predecessor artifacts. Neither
contains its own digest or a gen5 implementation-review digest. The
implementation review separately binds `PREDICTED_GEN5_FAILED_GEN3_SHA256` and
`PREDICTED_GEN5_FAILED_GEN2_SHA256` before setup.

## Registered NFS-capable no-replace publisher

### Alternatives considered

- Reusing gen4's `renameat2(RENAME_NOREPLACE)` is rejected because the exact
  target filesystem returns `EINVAL`.
- Writing the final basename directly with `O_EXCL` is rejected because it
  exposes incomplete canonical objects under their authoritative names.
- Staging on local ext4 and copying to NFS is rejected because cross-filesystem
  publication is not atomic and cannot preserve no-replace semantics.
- A rename-first/fallback design is rejected as unnecessary branching on this
  known NFS target. Gen5 instead registers one link/unlink state machine. If
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
root `transaction.json` with schema `msae_v3_gen5_link_transaction_v1`. It
contains: `schema_version`, `protocol_id`, `generation`, `transaction_kind`,
`authority_sha256`, exact input/review digests, an ordered `publications` table,
`mountinfo_sha256`, literal `filesystem_magic=0x6969`, `filesystem_fsid`,
`created_unix`, `recovery_deadline_unix`, and `maximum_link_attempts=3`.
`authority_sha256` is the canonical digest of external authority inputs, never
the descriptor's own digest: capability binds plan review plus all seven gen5
controller/runtime/runner/launcher/tmux-supervisor/RFC/test entries; setup binds
the implementation review and exact setup argv/
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
   `reports/analysis/msae_independent_measurement_v3_post_m2_gen5/.capability_report_transaction/`;
   descriptor names `.transaction.json.bootstrap` and `transaction.json`;
   governed source `report.payload`; final report path registered above;
2. setup:
   `reports/provenance/msae_independent_measurement_v3_post_m2_gen5/.setup_m3_gen5_transaction/`;
   the same descriptor names; governed rows are the 22 receipts, all final
   setup files, and all subordinate setup-key objects;
3. M4 install:
   `reports/provenance/msae_independent_measurement_v3_post_m2_gen5/.m4_install_transaction/`;
   the same descriptor names; governed sources `00.payload` through
   `05.payload`; governed destinations are the three M4-data then three
   provenance outputs in registered order;
4. signing:
   `pilot_runs/20260821_msae_independent_measurement_v3_post_m2_gen5_calibration/.sign_transaction/`;
   the same descriptor names; governed source `authorization.payload`; final
   destination `../authorization.json`.

The exact hard-link publication rows are the following. `P` denotes the gen5
provenance root, `C` the gen5 config root, `D` the gen5 M4-data root, `J` the
setup journal, `K` the subordinate setup-key staging root, and `R` the run root;
these symbols are aliases only for the absolute/relative canonical roots above
and never appear in a descriptor.

| Governing transaction | Source parent / literal basename | Destination parent / literal basename | Source lifetime |
|---|---|---|---|
| capability descriptor bootstrap | capability transaction / `.transaction.json.bootstrap` | capability transaction / `transaction.json` | ephemeral; unlink after exact pair is parent-fsynced |
| capability report | capability transaction / `report.payload` | capability analysis root / `gen4_publisher_capability_reproduction.json` | ephemeral; unlink immediately after destination-parent fsync and exact-pair verification |
| setup descriptor bootstrap | `J` / `.transaction.json.bootstrap` | `J` / `transaction.json` | ephemeral; unlink after exact pair is parent-fsynced |
| setup terminal evidence | `P` / `.failed_gen4.json.partial`, `.failed_gen3.json.partial`, `.failed_gen2.json.partial` | `P` / `failed_gen4.json`, `failed_gen3.json`, `failed_gen2.json` respectively | each source ephemeral; unlink immediately after its destination-parent fsync and exact-pair verification |
| setup key payload | `K` / `.private_key.payload.partial` | `K` / `private_key.payload` | `.partial` is ephemeral; `private_key.payload` is an authoritative subordinate staging destination retained through receipt 0018 and deleted by receipt 0019 |
| setup key binding | `K` / `.key_binding.json.partial` | `K` / `key_binding.json` | `.partial` is ephemeral; `key_binding.json` is an authoritative subordinate staging destination deleted by receipt 0018 |
| setup final private key | final key parent / `.independent_measurement_v3_post_m2_gen5_ed25519_private.pem.partial` | final key parent / `independent_measurement_v3_post_m2_gen5_ed25519_private.pem` | source is a separately recreated ephemeral copy of the descriptor-sealed key bytes and is unlinked immediately after destination-parent fsync; `K/private_key.payload` is not this link source |
| setup config outputs | `C` / `.ed25519_public.pem.partial`, `.authorization_commitment.json.partial`, `.cpu_no_model_public_entry_trace.json.partial`, `.protocol.json.partial` | `C` / `ed25519_public.pem`, `authorization_commitment.json`, `cpu_no_model_public_entry_trace.json`, `protocol.json` respectively | each source ephemeral; unlink immediately after its destination-parent fsync and exact-pair verification |
| setup manifest | `P` / `.setup_m3_gen5_manifest.json.partial` | `P` / `setup_m3_gen5_manifest.json` | source ephemeral; unlink immediately after destination-parent fsync and exact-pair verification |
| setup receipts | `J` / `.<receipt-name>.partial`, for each of the 22 literal receipt names registered below | `J` / the corresponding literal receipt name | each `.partial` source is ephemeral; the receipt destination remains authoritative until reverse receipt cleanup after receipt 0022 and manifest verification |
| M4 descriptor bootstrap | M4 transaction / `.transaction.json.bootstrap` | M4 transaction / `transaction.json` | ephemeral; unlink after exact pair is parent-fsynced |
| M4 outputs | M4 transaction / `00.payload`, `01.payload`, `02.payload`, `03.payload`, `04.payload`, `05.payload` | respectively `D/dependency_closure.json`, `D/endpoint_registry.json`, `D/environment_allowlist.json`, `P/stage_a.json`, `P/status.json`, `P/prescore_candidate_manifest.json` | each transaction-local source is ephemeral; unlink immediately after its destination-parent fsync and exact-pair verification |
| sign descriptor bootstrap | sign transaction / `.transaction.json.bootstrap` | sign transaction / `transaction.json` | ephemeral; unlink after exact pair is parent-fsynced |
| authorization | sign transaction / `authorization.payload` | `R` / `authorization.json` | source ephemeral; unlink immediately after destination-parent fsync and exact-pair verification |

Setup directory creation, the virtual setup-subject action, the virtual
pre-manifest-projection action, deletion of `key_binding.json` and
`private_key.payload`, and removal of `K` are receipt-governed actions but are
not hard-link publication rows and have no source basename. No other
`.partial`, `.payload`, descriptor, receipt, or destination name is legal.

`/jumbo/lisp/f004ndc/.msae_keys/.independent_measurement_v3_post_m2_gen5_setup/`
is explicitly a subordinate staging root, not a fifth link transaction. It has
no `transaction.json`; while governed by the durable setup-journal descriptor,
its exact children progress `{}` → `{private_key.payload}` →
`{private_key.payload,key_binding.json}`. Final private-key publication uses a
descriptor-bound adjacent source in the final key parent, so the original
payload remains until receipt 0019. Receipt 0018 deletes `key_binding.json`,
0019 deletes `private_key.payload`, and 0020 removes the empty subordinate root.

Before a root descriptor exists, only these exact empty-prefix roots are legal:
the capability analysis parent+transaction root; gen5 provenance+empty setup
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
- setup: exact setup manifest plus receipt 0022 → validate receipts/outputs,
  remove receipts 0022 down to 0001 with a journal fsync after each, remove the
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

All rows are fully bound in the root descriptor. Setup-key and sign random
bytes are generated in memory before bootstrap and included base64 in the
mode-0600 root descriptor under `sealed_random_payloads`, with their exact row
digest/size. If bootstrap source creation never becomes durable, no authority
exists and fresh randomness may be generated. Once either bootstrap name is
durable, those descriptor bytes are the authority and recovery recreates only
the identical random payload. The setup descriptor is deleted only after the
private key, all receipts, setup manifest, and final projection are durable; the sign
descriptor is deleted only after `authorization.json` is final and verified.

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
`/jumbo/lisp/f004ndc/tmp/msae_independent_measurement_v3_post_m2_gen5_publisher_tests`;
the local rejection case exclusively owns
`/tmp/msae_independent_measurement_v3_post_m2_gen5_mount_rejection_tests`.
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
/usr/bin/env -i PATH=/usr/bin:/bin HOME=/thayerfs/home/f004ndc LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /jumbo/lisp/f004ndc/experiments/wip/MSAE/.venv-atlas/bin/python -B -I -m pytest -q -p no:cacheprovider tests/test_msae_independent_measurement_v3_post_m5_gen5.py::test_nfs_publisher_fault_matrix tests/test_msae_independent_measurement_v3_post_m5_gen5.py::test_local_mount_rejection_precedes_protocol_mutation
```

This publisher pytest process is the first explicit `-S` exception: installed
pytest requires the venv site initialization, plugins/cache are disabled, and
the test module installs and verifies the reviewed source-only finder before it
imports any project module. Every Python child it creates uses `-S -B -I`.

The one authorized real-tmux extinction test is a distinct non-experiment
process-containment test. Its exact supervisor command, also from the repository
root, is:

```text
/usr/bin/env -i PATH=/usr/bin:/bin HOME=/thayerfs/home/f004ndc LANG=C.UTF-8 LC_ALL=C.UTF-8 /jumbo/lisp/f004ndc/experiments/wip/MSAE/.venv-atlas/bin/python -S -B -I scripts/run_msae_independent_measurement_v3_post_m2_gen5_tmux_test.py
```

The source-only supervisor derives the session, tmux server socket, ACK socket,
and scratch root registered above from its own PID. All four must be absent
before it creates the mode-0700 scratch root, binds/listens on the mode-0600 ACK
socket, and starts its sole child. It executes exactly this child environment and
argv, with no shell and no other inherited `MSAE_*`, CUDA, Python-path, preload,
or plugin variables:

```text
environment={PATH:/usr/bin:/bin,HOME:/thayerfs/home/f004ndc,LANG:C.UTF-8,LC_ALL:C.UTF-8,PYTEST_DISABLE_PLUGIN_AUTOLOAD:1,MSAE_GEN5_ALLOW_REAL_TMUX_TEST:1,MSAE_GEN5_TMUX_TEST_TOKEN:<supervisor_pid>,CUDA_VISIBLE_DEVICES:""}
argv=[/jumbo/lisp/f004ndc/experiments/wip/MSAE/.venv-atlas/bin/python,-B,-I,-m,pytest,-q,-p,no:cacheprovider,tests/test_msae_independent_measurement_v3_post_m5_gen5.py::test_failed_handoff_extinction_kills_real_processes_and_socket]
```

The missing `-S` on that pytest child is the second and only other explicit
harness exception needed to import installed pytest. Plugins/cache are disabled, the test installs
the reviewed source-only finder before importing any project module, and all
spawned project/controller or fake-broker Python entries still require
`-S -B -I`. The supervisor starts the pytest child in its own process group,
uses one selector-driven main loop with a 30-second monotonic child deadline,
and is the cleanup authority that survives a pytest timeout. On timeout or any
child outcome it TERM/waits three seconds, then KILLs/waits the pytest group
before entering the same unconditional namespace teardown. Supervisor
SIGTERM/HUP/INT handlers only set one atomic shutdown flag and write one byte to
a self-pipe; the main loop masks/reclassifies later signals and one serialized
`finally` performs the idempotent cleanup. Signal handlers never call
subprocess or filesystem routines, and the supervisor is never the process
killed by an inner timeout.

Within the child, the test's fake broker argv is exactly
`[realpath(.venv-atlas/bin/python), "-S", "-B", "-I", "-c",
FAKE_TMUX_BROKER_SOURCE, <ack-socket>, <scratch-root>/process.json]`, where the
literal source and its SHA-256 are test constants bound by the implementation
review. The supervisor, not pytest, owns the ACK listener and validates the
accepted peer with `SO_PEERCRED`; the peer PID/UID/GID must be the exact broker
PID/current UID/GID and a descendant of the captured tmux pane PID/start-tick.
The supervisor captures that pane identity with the exact display-panes vector
as soon as the session exists and before it permits an identity ACK.

The fake broker uses `os.fork`, not subprocess, to create a separate process
group with one descendant. Before forking it sets and rechecks
`PR_SET_PDEATHSIG=SIGKILL`; the descendant immediately sets/rechecks its own
`PR_SET_PDEATHSIG=SIGKILL`, then requires `getppid()` still equals the captured
broker PID (otherwise it calls `_exit(125)`), does not ignore TERM, and blocks
on a private pipe.
The broker writes canonical `msae_v3_gen5_tmux_test_process_v1` identity bytes
to exact mode-0600 `scratch/.process.json.partial`, file-fsyncs, publishes only
to `scratch/process.json`, and directory-fsyncs before sending the same identity
to the supervisor. The record contains pane, broker, and descendant
PID/start-tick, exact parent links, and worker PGID. The supervisor independently
parses the durable record, rechecks every `/proc` identity/ancestry and peer
credential, then replies with the one-byte identity-bound ACK. Only after the
broker receives that byte may it release the pipe barrier; the descendant then
sets TERM resistance, clears its parent-death signal, and reports one-byte
`resistance-armed` through the broker. The supervisor revalidates all identities
and durably publishes exact mode-0600 `scratch/identity_bound.json`; only that
file permits pytest to call the production extinction helper. Thus no
TERM-resistant/reparentable descendant exists before the surviving supervisor
has its durable exact identity. Missing, late, duplicate, malformed, partial,
or out-of-order record/ACK blocks and enters teardown. The identity exchange has
a five-second deadline inside the supervisor's 30-second child deadline.

Before starting tmux, the test installs tripwires that fail on `/usr/bin/nvidia-smi`
or any GPU-query helper, any `torch`, `transformers`, `datasets`, or model-runner
import, any CUDA device/environment activation, and any protocol controller
setup/M4/sign/launch route. `CUDA_VISIBLE_DEVICES` is the empty string. Only the
fake Python argv and the exact `/usr/bin/tmux -f /dev/null -S <tmux-socket>`
new/display/has-session/kill-session/kill-server vectors are allowed. After the ACK the test
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
`identity_bound.json`, and the empty exact scratch root; and verifies tmux
`has-session` is nonzero, both sockets and scratch are absent, and no recorded
or captured pane/broker PID/start-tick, descendant, or PGID member remains.
Fault tests terminate at every fork, partial-write, fsync, publish, identity,
ACK, barrier-release, resistance-arm, and child-timeout boundary and require the
same final absence. The supervisor returns success only if
pytest returned zero and its independent final teardown/absence verification
succeeded. The test namespace never overlaps a capability, protocol, GPU-lock,
nonce, run, or prescore path.

## M3 setup and review gates

The exact setup command is:

```text
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen5.py setup-m3-gen5 --reviewed-m2-sha256 e593a6283aa5468ddbee1cc755dbe60c4ee503375a0cbce44c52614dd232d737 --failed-gen3-plan-review-sha256 e3b2f0047b6fc14aabb0c60227cc1710cac17d3aca67618277ff1e64b4f902bb --failed-gen3-implementation-review-sha256 b77237868339a93f1b4e6ad4592260c83b2a0c318c22c9be27a1d0971f86462a --failed-gen4-plan-review-sha256 45976d778388d0020c58ea4e3a278c7a1d54d0f67b6a266f5fdc2733366c5fce --gen5-plan-review-sha256 <64-lowerhex> --gen5-implementation-review-sha256 <64-lowerhex>
```

Reordered, missing, duplicate, extra, uppercase, or aliased options block. Old
gen4 setup/build/sign/launch
routes remain fail-closed. Setup requires exact SHA-256 pins for reviewed M2,
failed-gen3 plan/review, gen4 plan/review, gen5 plan/review, and the current
gen5 implementation review. It validates all namespaces, quarantined lstat-only
invariants, source-only imports, the complete CPU/no-model surface trace, and
the gen4 terminal payload before any write.

The gen5 setup journal is a create-once receipt-prefix DAG equivalent to the
reviewed gen4 design. Its exact ordered receipts are:

1. gen5 provenance root;
2. `failed_gen4.json`;
3. `failed_gen3.json`;
4. `failed_gen2.json`;
5. gen5 M4-data root;
6. gen5 config root;
7. gen5 state root;
8. gen5 nonce root;
9. setup-key subordinate staging root;
10. private-key payload;
11. key binding;
12. final private key;
13. setup subject;
14. public key;
15. authorization commitment;
16. CPU/no-model trace;
17. protocol config;
18. key-binding deletion;
19. key-payload deletion;
20. key-staging-root removal;
21. pre-manifest projection verification;
22. setup-manifest publication.

Receipts are mode-0600 canonical JSON with the exact names:
`0001_gen5_provenance_root.json`, `0002_failed_gen4.json`,
`0003_failed_gen3.json`, `0004_failed_gen2.json`,
`0005_gen5_m4_data_root.json`, `0006_gen5_config_root.json`,
`0007_gen5_state_root.json`, `0008_gen5_nonce_root.json`,
`0009_key_staging_root.json`, `0010_key_payload.json`,
`0011_key_binding.json`, `0012_final_private_key.json`,
`0013_setup_subject.json`, `0014_public_key.json`,
`0015_authorization_commitment.json`, `0016_cpu_no_model_trace.json`,
`0017_protocol_config.json`, `0018_key_binding_deleted.json`,
`0019_key_payload_deleted.json`, `0020_key_staging_root_removed.json`,
`0021_pre_manifest_projection.json`, and `0022_setup_manifest.json`.
Each receipt uses schema `msae_v3_gen5_setup_receipt_v1` with exact keys
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
receipts through 0021, the exact derivation rule for receipt 0022, exact
directories, final entries, review authorities, and the private
key lstat/public-key agreement. M3 contains no execution authorization.
Receipt 0022 then binds the published manifest digest; the manifest does not
embed receipt 0022 and therefore has no digest cycle. Reverse cleanup validates
all 22 receipts before removing them and the root descriptor.

An independent post-M3 adversarial SHIP review binds the exact implementation,
setup manifest/subject, protocol, commitment/public key, private-key lstat with
content unread, CPU trace, failed-gen3/gen4 records, zero quarantined reads,
and complete downstream absence.

## Exact review schemas

Every review is canonical UTF-8, mode 0644, UID-owned, nlink 1, newline
terminated, and has unique ordered controls. Malformed/indented/duplicate/extra
control-like lines block.

The plan review scope is `gen5_plan` with controls:
`FAILED_GEN4_PLAN_SHA256`, `FAILED_GEN4_PLAN_REVIEW_SHA256`, and
`GEN5_PLAN_SHA256`.

The implementation review scope is `gen5_implementation`. In exact order it
binds: `M1_COMPLETION_SHA256`, `M2_COMPLETION_SHA256`,
`FAILED_GEN3_PLAN_SHA256`, `FAILED_GEN3_PLAN_REVIEW_SHA256`,
`FAILED_GEN3_CONTROLLER_SHA256`, `FAILED_GEN3_RUNTIME_SHA256`,
`FAILED_GEN3_RUNNER_SHA256`, `FAILED_GEN3_LAUNCHER_SHA256`,
`FAILED_GEN3_RFC_SHA256`, `FAILED_GEN3_TESTS_SHA256`,
`FAILED_GEN3_IMPLEMENTATION_REVIEW_SHA256`, `HISTORICAL_PREFLIGHT_SHA256`,
`PREDICTED_GEN5_FAILED_GEN3_SHA256`, `PREDICTED_GEN5_FAILED_GEN2_SHA256`,
`FAILED_GEN4_PLAN_SHA256`, `FAILED_GEN4_PLAN_REVIEW_SHA256`,
`FAILED_GEN4_CONTROLLER_SHA256`, `FAILED_GEN4_RUNTIME_SHA256`,
`FAILED_GEN4_RUNNER_SHA256`, `FAILED_GEN4_LAUNCHER_SHA256`,
`FAILED_GEN4_RFC_SHA256`, `FAILED_GEN4_TESTS_SHA256`,
`GEN4_CAPABILITY_REPRODUCTION_SHA256`, `PREDICTED_GEN4_TERMINAL_SHA256`,
`GEN5_PLAN_SHA256`, `GEN5_PLAN_REVIEW_SHA256`, `GEN5_CONTROLLER_SHA256`,
`GEN5_RUNTIME_SHA256`, `GEN5_RUNNER_SHA256`, `GEN5_LAUNCHER_SHA256`,
`GEN5_TMUX_TEST_SUPERVISOR_SHA256`, `GEN5_RFC_SHA256`, and
`GEN5_TESTS_SHA256`. The terminal digest is predicted without the
implementation review digest.

The post-M3 scope is `gen5_post_m3` with ordered controls:
`GEN5_IMPLEMENTATION_REVIEW_SHA256`, `POST_M3_SUBJECT_SHA256`,
`GEN5_PROTOCOL_SHA256`, `GEN5_AUTHORIZATION_COMMITMENT_SHA256`,
`GEN5_PUBLIC_KEY_SHA256`, `GEN5_CPU_TRACE_SHA256`,
`GEN5_SETUP_MANIFEST_SHA256`, `GEN4_TERMINAL_SHA256`,
`GEN3_TERMINAL_SHA256`, `GEN2_M4_FAILURE_SHA256`, and
`M2_COMPLETION_SHA256`.

The prescore scope is `gen5_prescore` with ordered controls:
`GEN5_IMPLEMENTATION_REVIEW_SHA256`, `GEN5_POST_M3_REVIEW_SHA256`,
`GEN5_PROTOCOL_SHA256`, `GEN5_STAGE_A_SHA256`, `GEN5_STATUS_SHA256`,
`GEN5_CANDIDATE_MANIFEST_SHA256`, `GEN5_DEPENDENCY_CLOSURE_SHA256`,
`GEN5_ENDPOINT_REGISTRY_SHA256`, `GEN5_ENVIRONMENT_ALLOWLIST_SHA256`,
`GEN5_PRESCORE_CHECK_SHA256`, `GEN5_PRESCORE_TRACE_SHA256`,
`GEN5_PRESCORE_CHECKER_SHA256`, and `SEALED_PAYLOAD_CONTENT_READS: 0`.

Plan/implementation authorities and all predecessor terminal entries are bound
again in protocol config, setup subject/manifest, authorization commitment,
CPU trace, closure, both M4 trees, Stage A, candidate manifest, post-M3 review,
prescore review, signed envelope, and prelaunch/worker validation.

## Gen4-to-gen5 substitution table

| Surface | Gen4 | Gen5 |
|---|---|---|
| generation | `post_m2_gen4` | `post_m2_gen5` |
| public commands | `*-gen4` | `*-gen5` |
| controller/runtime/runner/launcher | `*gen4*` | `*gen5*` |
| real-tmux test supervisor | absent as a distinct authority | exact reviewed gen5 supervisor path above |
| plan/RFC/tests | `*gen4*` paths | exact gen5 paths above |
| config/provenance/M4 data | `...post_m2_gen4` | `...post_m2_gen5` |
| setup/key/M4/sign transactions | gen4 names | exact gen5 names above |
| reviews/scopes/controls | `GEN4_*`, `gen4_*` | exact `GEN5_*`, `gen5_*` schemas above |
| state/nonce/run | gen4 roots | exact gen5 roots above |
| evidence/socket/tmux | gen4 prefix/session | exact gen5 prefix/session above |
| M4 outputs | gen4 data/provenance six-file set | gen5 data/provenance six-file set |
| Stage B | gen4 run-root terminal schema | byte-identical schema with generation/path substitution |
| terminal failure | gen4 run-root schema | byte-identical schema with generation/path substitution |
| publisher | renameat2-only | descriptor/mount-bound linkat state machine above |

All other scientific fields and schemas must compare byte-identically after
this typed substitution. A broad textual replacement is forbidden.

## Exact phase projections

- Post-plan-review/pre-implementation: only the gen5 plan and plan review exist.
- Pre-implementation review: add exactly the seven gen5 controller/runtime/
  runner/launcher/tmux-supervisor/RFC/test entries
  and capability-reproduction report. All gen5 config,
  provenance, M4-data, key, state, run, scratch, evidence, socket, and later
  reviews are absent.
- Post-implementation review/pre-M3: add only the implementation review.
- Post-M3: config contains exactly `protocol.json`,
  `authorization_commitment.json`, `ed25519_public.pem`, and
  `cpu_no_model_public_entry_trace.json`; provenance contains exactly
  `failed_gen4.json`, `failed_gen3.json`, `failed_gen2.json`, and
  `setup_m3_gen5_manifest.json`; M4 data is empty; state contains the empty
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
  `authorization.json`, `launcher_intent.json`, `logs`, `broker.sock`,
  `lock_acquired.json`, `handoff.json`, `nonce_consumed.json`,
  `observed_environment.json`, `tolerance_selection.json`,
  `cached_noop_hash_replay.json`, `canonical_pooling_qa.json`,
  `counterfactual_cache_alignment_qa.json`, `cache`, `terminal.claim`,
  `.terminal_failure_staging`, `terminal_failure`,
  `.terminal_success_staging`, and `terminal_success`.
- `logs` has exactly the prefix `{}` → `{broker.log}` →
  `{broker.log,worker.log}`. `cache` has exactly
  `{main_long,main_short,pair_context,pair_entity}`; each stratum has
  `forward_0.npy` through `forward_3.npy` and then `pooling_per_unit.npy` in the
  scientific order below.
- Literal control rows are `R0={}` (run absent),
  `R1={authorization.json}`, `R2=R1+{launcher_intent.json}`,
  `R3=R2+{logs}`, `R4=R3+{broker.sock}`,
  `R5=R4+{lock_acquired.json}`, `R6=R5+{nonce_consumed.json}`, and
  `R7=R6+{handoff.json}`. No row admits a missing predecessor or extra child.
- After final-gate acknowledgement, `broker.sock` may be removed and the exact
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
- `broker.sock` is the sole allowed nonregular run child and is removed after
  handoff/failure. The dedicated tmux session may exist only for the live run.

At every phase, ignored/untracked entries count. The verifier enumerates all
children with lstat, rejects symlink ancestors and same-inode aliases, and
reconstructs the expected projection independently of the candidate manifest.

## M4, prescore, signing, and launch

Except for gen5 namespaces and the registered publisher, M4, prescore,
authorization, nonce, GPU lease, watchdog, two-phase model gate, Stage-B QA,
and terminal-result semantics are identical to the frozen gen4 plan:

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

The exact ordered public commands are:

```text
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen5.py build-m4-gen5 --post-m3-review-sha256 <64-lowerhex>
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen5.py prescore-traced-check --manifest reports/provenance/msae_independent_measurement_v3_post_m2_gen5/prescore_candidate_manifest.json --output /tmp/msae_independent_measurement_v3_post_m2_gen5_<manifest_sha256>.prescore.check.json --trace /tmp/msae_independent_measurement_v3_post_m2_gen5_<manifest_sha256>.prescore.trace.log
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen5.py verify-prescore-trace --manifest reports/provenance/msae_independent_measurement_v3_post_m2_gen5/prescore_candidate_manifest.json --check /tmp/msae_independent_measurement_v3_post_m2_gen5_<manifest_sha256>.prescore.check.json --trace /tmp/msae_independent_measurement_v3_post_m2_gen5_<manifest_sha256>.prescore.trace.log
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen5.py sign-gen5
scripts/launch_msae_independent_calibration_v3_gen5.sh
```

Calibration may build Stage B only. Any timeout, lease loss, broker/worker
death, OOM, exception, or invalid QA creates exactly one technical-failure
not-run terminal state and never exposes Stage B. Scientific ineligibility is a
valid separate Stage-B outcome. Confirmation scoring and Stage C remain absent.

## Milestones

### P0 — plan authority

- [ ] Freeze this plan.
- [ ] Obtain an independent plan SHIP review at the gen5 plan-review path.
- [ ] Bind both exact files in every later artifact.

### P1 — implementation, no one-way writes

- [ ] Implement disjoint gen5 controller/runtime/runner/launcher/tmux-test-
  supervisor/RFC/tests.
- [ ] Mechanically reproduce the gen4 capability failure only in a disposable CPU
  directory;
- [ ] Run all predecessor and gen5 CPU/no-model tests.
- [ ] Run syntax, shell, diff, static-closure, value-flow, source-only-import, and
  quarantined-lstat checks;
- [ ] Obtain an independent implementation SHIP review.

### P2 — M3

- [ ] Invoke `setup-m3-gen5` once with exact review pins.
- [ ] Verify completion and obtain a fresh post-M3 SHIP review.

### P3 — M4 and external prescore

- [ ] Build both M4 trees and install only after exact equality.
- [ ] Run the traced prescore check.
- [ ] Obtain a fresh external prescore SHIP review.

### P4 — authorization and handoff

- [ ] Sign the exact calibration-only envelope.
- [ ] Invoke the gen5 launcher.
- [ ] Allow that signed launcher alone to inspect free GPUs and create tmux.
- [ ] Report the durable handoff immediately without waiting.

## Verification plan

- P0: hash the plan/review; parse exact controls; run the plan structural gate.
- P1 publisher: run deterministic fault-injection tests for every source,
  attempt-marker, link, fsync, unlink, uncertain-result, mount-swap, and recovery
  boundary on NFS and a local temporary filesystem; assert exact bytes/child
  sets after each replay.
- P1 closure: run the complete predecessor+gen5 pytest set with plugins/cache
  disabled, the CPU/no-model every-public-entry trace, static/value-flow
  recomputation, malicious `.pyc`/sourceless/extension-shadow regressions,
  `py_compile`, `bash -n`, and `git diff --check`.
- P1 containment: run every verifier under the quarantined-open tripwire and
  compare before/after lstat for all three sealed files. Run the one real tmux
  extinction test only in its fixed non-experiment test socket/session namespace,
  with all GPU/model/query calls mocked and a final absence check.
- P2: reconstruct the setup subject/manifest/receipts independently, compare
  exact namespace projections, and obtain an adversarial post-M3 SHIP verdict.
- P3: compare both complete M4 trees byte-for-byte, reconstruct the candidate
  manifest, run `strace -yy` prescore verification, and obtain an external SHIP
  review.
- P4: independently verify signature/nonce/intent/lease/handoff bindings and
  return only after the runner's pre-model readiness and durable final ACK.

## Definition of done

- [ ] Gen4 plan/review/source remain exact and gen4 state remains absent.
- [ ] Gen5 plan and independent plan review are immutable and machine-bound.
- [ ] Gen5 terminal evidence distinguishes capability testing from scientific work.
- [ ] The publisher passes all registered NFS, uncertain-result, race, and crash
  tests on the actual repository filesystem.
- [ ] Every gen5 artifact and executable is in the exact candidate/closure manifest.
- [ ] All predecessor and gen5 tests pass without model/GPU/tmux use, except a
  separately controlled real-tmux extinction test run immediately before the
  implementation review.
- [ ] Static and behavioral closure cover every public entry and publication
  primitive; valid ignored bytecode/shadow modules cannot execute.
- [ ] A fresh adversarial implementation verdict is SHIP.
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

- Publishing the gen5 plan review freezes this plan.
- `setup-m3-gen5` is the first gen5 protocol-state write.
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
