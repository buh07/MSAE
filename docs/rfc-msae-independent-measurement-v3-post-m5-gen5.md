# MSAE v3 post-M5 gen5 execution protocol

Status: implementation candidate. No M3, M4, model, GPU, calibration tmux,
confirmation, or Stage C action is authorized until the applicable independent
review gate passes.

This RFC implements the frozen plan
`docs/plan-msae-independent-measurement-v3-post-m5-gen5.md`, SHA-256
`757ee41fc7ec5440ef1e5d0b132528d86a43a43cd7fc145be828fe5355fe723e`.
Its independent plan review has SHA-256
`bdd23fb26ff1cf7edbe4fbae8efb41b34b22bbaa72e9fa8e88f2231b035bd167`.
The plan is normative where this shorter RFC is ambiguous.

## 1. Scope and historical status

Gen5 preserves the reviewed M1/M2 science, selected AMALGUM source, all four
partitions, checkpoint lineages, endpoint product, tolerance ladder, safety
factor, thresholds, and G1/G2 rules. It changes only the failed-generation
provenance and NFS publication control plane.

Gen2 failed before Stage A because four replay `environment_sha256` fields were
candidate-root dependent. Gen3's reviewed setup was invoked twice and failed at
the same dominating prewrite exception; it produced no gen3 protocol state.
Gen4 failed before implementation review/M3 because its frozen
`renameat2(RENAME_NOREPLACE)` publisher returns `EINVAL` on the repository NFS
mount. Gen5 never reinterprets any of those attempts as passing.

Gen5 writes typed copies `failed_gen4.json`, `failed_gen3.json`, and
`failed_gen2.json` only under its own provenance root. Historical namespaces are
read-only. The gen4 record separates operator disclosure, a current mechanical
capability reproduction, and current absence observations. The latter two are
not claimed to be the historical syscall trace.

## 2. Immutable authority

The implementation revalidates the exact M1/M2 completion digests, failed gen3
plan/review/code/test/preflight digests, failed gen4 plan/review/code/test
digests, frozen gen5 plan/review, capability report, predicted failure-record
digests, and the seven current gen5 implementation entries: controller,
runtime, runner, launcher, tmux-test supervisor, RFC, and tests.

All reviews are canonical UTF-8, mode 0644, current-UID, nlink-1 regular files
with one exact `VERDICT: SHIP`, one exact registered `REVIEW_SCOPE`, and the
ordered digest controls specified by the frozen plan. Extra, missing,
duplicated, malformed, padded, conflicting, stale, or substituted controls
block.

The review sequence is:

1. `gen5_plan` (already frozen);
2. `gen5_implementation` before M3;
3. `gen5_post_m3` before M4;
4. `gen5_prescore` after the traced candidate check and before signing.

## 3. Source and sealed-data closure

Production project-code processes use source-only isolated Python
`-S -B -I`. The finite source loader never reads `.pyc` or extension shadows,
and the ordinary repository `scripts/` directory is removed from `sys.path`
before deferred third-party imports. The only exceptions are the two reviewed
installed-pytest commands for the publisher matrix and the one fake-broker tmux
extinction test; every project-code child those tests spawn remains
`-S -B -I`.

Static closure binds the complete local AST/value-flow ledger, every dynamic
file site, exact process/environment patterns, AF_UNIX network sites, dynamic
library sites, model snapshot, checkpoint aliases, Python startup inputs,
distribution lock/metadata, ELF dependencies, and every registered public
entry. A CPU/no-model trace exercises the registered entries and planted file,
process, shell, library, and network escapes.

The three private `final*.jsonl` files are quarantine objects. No gen5 command
opens, hashes, or content-reads them. Every one-way transition runs under the
sealed-content tripwire and compares exact before/after lstat rows in a
`finally` path. Same-inode aliases, link-count drift, type/mode/owner drift, or
a blocked content-open attempt fail closed.

## 4. Gen4 capability record

The only pre-implementation-review create-once command is:

```text
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen5.py probe-gen4-publisher-capability --output reports/analysis/msae_independent_measurement_v3_post_m2_gen5/gen4_publisher_capability_reproduction.json
```

It uses the fixed non-protocol NFS probe root registered in the plan, records
exact UTC timestamps, argv/cwd, failed-gen4 runtime entry, mountinfo/fstatfs
identity, errno 22, before/after source lstat, absent destination, transcript,
and zero model/GPU/tmux activity, then removes the probe root. The report is
published by the link transaction below and is canonical mode 0644, UID-owned,
nlink 1. Any non-NFS mount, non-`EINVAL` result, mutated source, created
destination, extra namespace object, or cleanup failure blocks.

## 5. Descriptor-bound NFS publisher

There are exactly four authoritative link transactions: capability report,
M3 setup, M4 install, and signing. Each uses a mode-0700 UID-owned transaction
root and one canonical mode-0600 `transaction.json`. The descriptor binds its
kind, external authority digest, exact ordered publication rows, literal source
and destination parents/basenames, modes, UID, fixed payload digest/size or a
registered derived builder, exact NFS mountinfo digest/fsid/magic, creation and
recovery deadline, maximum three link attempts, and any sealed random payload.

The descriptor bootstrap is the sole finite exception. It publishes
`.transaction.json.bootstrap` to `transaction.json` with the same no-replace
link state machine. Before authority exists, only the exact empty root and
bootstrap source are legal.

For each row the publisher:

1. opens both parents `O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC` and binds their stable
   identities and the registered NFS mount;
2. validates or O_EXCL/full-writes/file-fsyncs/source-parent-fsyncs the exact
   source;
3. creates and parent-fsyncs the next exact empty attempt-marker directory;
4. performs one `linkat(..., flags=0)` call;
5. resolves success or error only from exact source/destination inode states;
6. for an exact pair, destination-parent-fsyncs, unlinks only the source,
   source-parent-fsyncs, and requires an exact nlink-1 destination; and
7. removes markers in reverse order only after final verification.

Accepted recovery states are exact source-only nlink 1, exact source/destination
pair nlink 2 on one inode, and exact destination-only nlink 1. Any other state,
foreign destination, third hard link, symlink, wrong bytes/mode/UID, mount or
parent replacement, attempt-budget exhaustion, or expired new attempt blocks.
A nonzero `linkat` with source-only state is a recoverable technical
interruption, not evidence of completion and not an in-process retry.

The fixed NFS fault matrix first runs one wholly uninjected real transaction,
then covers the registered errno and crash boundaries. The fixed local `/tmp`
case must reject before any descriptor, source, destination, or marker mutation.
Both roots are absent before and after. These are CPU/filesystem safety tests,
not experiments.

## 6. M3 and 22 receipts

The exact M3 command is:

```text
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen5.py setup-m3-gen5 --reviewed-m2-sha256 e593a6283aa5468ddbee1cc755dbe60c4ee503375a0cbce44c52614dd232d737 --failed-gen3-plan-review-sha256 e3b2f0047b6fc14aabb0c60227cc1710cac17d3aca67618277ff1e64b4f902bb --failed-gen3-implementation-review-sha256 b77237868339a93f1b4e6ad4592260c83b2a0c318c22c9be27a1d0971f86462a --failed-gen4-plan-review-sha256 45976d778388d0020c58ea4e3a278c7a1d54d0f67b6a266f5fdc2733366c5fce --gen5-plan-review-sha256 bdd23fb26ff1cf7edbe4fbae8efb41b34b22bbaa72e9fa8e88f2231b035bd167 --gen5-implementation-review-sha256 <64-lowerhex>
```

Setup validates every pin, review, predecessor, namespace, quarantine row, and
downstream absence before its first write. Random private-key bytes are sealed
in the root descriptor. The subordinate setup-key root is not a fifth
transaction. Its `private_key.payload` and `key_binding.json` remain until their
registered deletion receipts; final private-key publication uses a distinct
adjacent source.

The exact receipt order is:

1. gen5 provenance root;
2. `failed_gen4.json`;
3. `failed_gen3.json`;
4. `failed_gen2.json`;
5. M4-data root;
6. config root;
7. state root;
8. nonce root;
9. setup-key staging root;
10. key payload;
11. key binding;
12. final private key;
13. virtual setup subject;
14. public key;
15. authorization commitment;
16. CPU/no-model trace;
17. protocol config;
18. key-binding deletion;
19. key-payload deletion;
20. staging-root removal;
21. pre-manifest projection;
22. setup manifest.

Receipt filenames and fields are exactly those in the frozen plan. Each receipt
has only `schema_version`, `protocol_id`, `generation`, `index`, `step`,
`action`, `target`, `transaction_sha256`,
`predecessor_receipt_sha256`, and `payload_sha256`. A legal crash state is an
exact receipt prefix plus at most its registered next-action source/marker
prefix. The setup manifest binds receipts 1--21 and the derivation of receipt
22, avoiding a digest cycle. Cleanup validates all 22 and removes them in
reverse with directory fsync after each deletion.

Completed M3 is non-authorizing: exactly four config files, the three typed
failure records and setup manifest, empty M4-data, empty nonce state, one
private key with exact lstat/public-key agreement, no Stage A, no signature,
and no GPU/model/tmux state.

## 7. M4, Stage A, and prescore

A fresh `gen5_post_m3` review binds the complete M3 subject, including the three
failure records, implementation review, setup manifest/subject, protocol,
commitment, public key, private-key lstat with content unread, CPU trace, M2,
zero sealed reads, and exact downstream absence.

`build-m4-gen5` constructs two complete sparse candidate trees from the same
frozen snapshot. Each tree executes the candidate-root generic builder,
closure, environment, endpoint registry, and Stage-A builders with no live-root
fallback. Complete file/directory manifests and every output byte must compare
identically. Live inputs, Git status, review subject, quarantine metadata, and
external absence are revalidated immediately before the six-output link
transaction installs, in order:

1. `dependency_closure.json`;
2. `endpoint_registry.json`;
3. `environment_allowlist.json`;
4. `stage_a.json`;
5. `status.json`;
6. `prescore_candidate_manifest.json`.

The manifest binds every candidate file and ancestor directory, exact status
classification, complete protected-baseline checks, quarantine results,
required absent evidence/socket/run paths, closure, Stage A, and its
self-exclusion rule. Stage B and Stage C remain `not_run`.

The digest-derived `strace -f -yy` check must reconstruct exactly and prove all
required opens plus zero sealed-content opens. A genuinely external
`gen5_prescore` review binds the registered manifest/check/trace/Stage-A/config/
closure/status/endpoint/environment/checkpoint controls and
`SEALED_PAYLOAD_CONTENT_READS: 0`.

## 8. Signing, GPU handoff, and Stage B

Only after prescore SHIP may `sign-gen5` read the private key. It seals one
calibration-only authorization in the sign descriptor and publishes
`authorization.payload` to `authorization.json` through the link state machine.
The envelope binds the exact instruction, commitment, config, Stage A,
manifest, closure, review, nonce, and 24-hour maximum interval. The external
nonce directory must still be empty.

Only the signed launcher may query `nvidia-smi`. It selects an idle GPU, obtains
the persistent UUID lock, rechecks compute processes while holding the same
object, authenticates tmux pane/broker/worker/peer lineage, consumes the nonce
once, and completes the two-phase durable pre-model ACK. The coordinator returns
immediately after that ACK and does not wait for results.

The worker imports no model before the final gate. It then runs calibration
replay only, creates four-stratum caches and typed QA, and exposes either the
six-file terminal-success directory or a mutually exclusive technical-failure
not-run directory. A legitimate no-tolerance or pooling-selectivity failure is
scientific `ineligible`, not a technical exception. Confirmation scoring and
Stage C are prohibited and are not authorized by the envelope.

## 9. Final gates

Before implementation SHIP: exact syntax/shell checks, all predecessor and gen5
CPU tests, real NFS publisher matrix, local mount rejection, the single reviewed
fake-broker tmux extinction test, static/value-flow closure, CPU/no-model trace,
source-shadow attacks, transaction crash recovery, review/CLI mutation tests,
quarantine stability, and complete downstream absence must pass.

After implementation SHIP, cross only M3. Obtain post-M3 SHIP before M4. Obtain
external prescore SHIP before signing. Only then launch calibration via tmux on
a launcher-selected idle GPU. Never run confirmation or Stage C in this branch.
