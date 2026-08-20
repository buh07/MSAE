# RFC: Atlas-v1 diagnostic continuation summary recovery

**Status:** amended post-collection technical recovery; no execution before independent `SHIP` reviews and freeze  
**Scope:** reporting/verification only; scored artifacts are immutable  
**Incident:** the frozen `summarize` job failed at 2026-08-02 08:51 UTC with `KeyError: 'source'`

## Goal

Produce and strictly verify the diagnostic-continuation result from the already
closed scored-artifact collection without changing any score, draw, endpoint,
threshold, eligibility decision, scientific stop, G1/G2 disposition, or original
continuation artifact. The recovery must make the smallest possible correction:
derive the Tier-1 source inventory through the frozen row lineage rather than
reading a nonexistent field from the task-row JSONL, and replay the K2 family
summary with the exact binary-coordinate rule used by the frozen producer rather
than the generic verifier helper that incorrectly treats a shared assigned
coordinate as its own leakage coordinate.

## Non-goals

- Do not rerun a point estimate, bootstrap draw, stability draw, or specificity job.
- Do not edit the frozen continuation bundle or its run root.
- Do not delete or overwrite the failed `summarize.terminal.json` or log.
- Do not relax the `>=450/500` complete-case rule or point-finiteness rule.
- Do not select a paper branch, render G1a/G2a, open the blind final set, or train.
- Do not repair the older unused `verify_msae_completion.py` path in this recovery.

## Incident and root cause

The scoring and collection stages closed normally: all four K2 series contain 500
registered draws, stability contains 500 registered draws, and all four specificity
jobs completed. `COLLECTION_COMPLETE.json` has SHA-256
`adf2c0f09784d8e8fcaacd07188c9fa27d215f5b8c1520ba5244f31360e5a2e2`.

The create-once summarizer failed before creating the diagnostic result root. The
failure is durably recorded by:

- `job_manifests/summarize.terminal.json`, SHA-256
  `f5b78e87f8166c4197ce6f79f8cf65541811a30c7730de113ea5716971218422`,
  `outcome=technical_failure`, `exit_code=1`;
- `logs/summarize.log`, SHA-256
  `a11ebb2036a0e3d443bfb4608adfd023c791b58463b8108ba57596e317e13958`;
- traceback at `summarize_msae_completion_continuation.py:98-105`, where
  `expected_sources()` reads `row["source"]` from
  `configs/atlas/task_row_manifest.json` paths.

Those task rows contain `row_id`, `base_id`, `document_group`, `source_type`, and
labels, but not dataset `source`. The scoring workers did not use that assumption:
`load_row_file()` resolved each `row_id` against the activation-unit lineage and
returned `data.row_source`. The summarizer's independent replay adapter therefore
drifted from the scoring adapter.

An implementation dry run performed before any recovery freeze or result-root
creation then exposed a second deterministic postscore verifier drift. After only
the source adapter was corrected, the frozen replay stopped at
`verify_msae_completion.py:560` with `K2 family summary differs from serialized
recoveries`. For the frozen K2 mapping, both absolute and relative/structural
families are assigned to `pos`. The generic verifier helper computes its
nonassigned set from mappings of the *other families*, so it incorrectly retains
`pos` alongside `content` for the relative/structural family's
`leakage_by_representation`. An exhaustive pre-freeze audit of all 2,004
registered K2 result leaves (four points plus 2,000 draws) found that the
producer-rule reconstruction equals every serialized `families` object exactly,
whereas the generic verifier reconstruction differs in every leaf only by that
one spurious `pos` entry. The frozen K2 producer at
`run_msae_refit_worker.py:473-485` instead uses exactly the opposite binary
coordinate (`content` for `pos`, `pos` for `content`). The serialized point and
draw leaves match the producer: the numerical assigned recovery, leakage, and
selectivity margin agree, and the only generic reconstruction difference is the
spurious assigned-coordinate entry. A diagnostic in an isolated process using
the producer's exact binary-coordinate rule completed the entire replay and found
414/500 finite draws for every K2 series, 0/500 jointly finite stability draws,
and four completed specificity stages. These values remain preliminary until the
governed recovery below is frozen, executed, and reviewed.

## Correct lineage rule

Resolve exactly the roles consumed by the failed frozen adapter—`calibration`,
`C1`, and `C2`—and no discovery role. For every frozen Tier-1 task, perform two
independent resolutions and require per-row equality, not merely source-set
equality.

### A. Exact scoring lineage

1. use the original frozen `load_activation(role, L3, source_run_root, firewall)`;
2. use the original frozen `load_row_file(task_path, activation, firewall,
   role=role)` to obtain row indices, sources, and document groups;
3. independently validate every parsed token index is decimal, non-negative, and
   strictly within its unit's row-count interval before accepting the helper output;
4. validate `row_meta.npz` has aligned `unit_index`/`record_index` arrays, every
   index is in range, their length equals the L3 activation rows, and each task row
   index is in range.

### B. Frozen partition lineage

1. read the frozen task-row path from `configs/atlas/task_row_manifest.json`;
2. split `row_id` as `variant_id:token_index` and reject malformed or duplicate IDs;
3. map `variant_id -> base_id` using, for the same role,
   `data/atlas_v1/partitions/<role>.units.jsonl`;
4. map `base_id -> (source, document_group)` using
   `data/atlas_v1/partitions/<role>.records.jsonl`;
5. reject missing variants/records, conflicting duplicate variants/base IDs,
   mismatched activation-versus-partition variant/base mappings, empty sources or
   groups, and empty task source sets.

For each task row, A and B must yield the identical source and document group in
the identical task-row order. Each task-row file must equal its frozen manifest
hash; all partition inputs and every activation `units.json`, `records.jsonl`,
`row_meta.npz`, L3 array, and completion marker must remain covered by the verified
original source inventory/freeze. Emit per-row/source-set comparison counts and
all attested input hashes in `source_lineage.json`. Finally, compare resolved C2
source sets against every source key retained in every K2 point leaf; that last
check is supplemental, not the independent source of truth.

## Approach

### Additive, mechanically narrow adapter

Leave `scripts/summarize_msae_completion_continuation.py`,
`scripts/verify_msae_completion.py`, and `scripts/run_msae_refit_worker.py`
byte-for-byte unchanged so the original continuation freeze remains verifiable.
The parent recovery process resolves and serializes the validated source inventory,
then invokes a fresh isolated child Python process to run the frozen summarizer.
The child process imports only `json`, `os`, `pathlib`, `sys`, the frozen
summarizer, frozen verifier module, and frozen producer module; loads the serialized
inventory; performs exactly two module mutations:

1. `frozen_summary.expected_sources = inventory_adapter`;
2. `frozen_verifier.family_rows = k2_family_rows_adapter`.

The second adapter is not a new family definition: it exactly mirrors the frozen
K2 producer's branch at `run_msae_refit_worker.py:473-485`, including the
`>=2` eligible-task rule, invalid payload, assigned coordinate, binary opposite
coordinate, and call to the producer's frozen `family_summary`. It is used only by
the verifier function's global lookup during this isolated K2-only replay. Before
doing any work, it must require the exact frozen three-family mapping—absolute and
relative/structural to `pos`, lexical/semantic to `content`—plus the exact frozen
family/task and eligible-task inventories; every other mapping or call context is
a technical failure. The
child calls only `frozen_summary.recompute()` and
`frozen_summary.report_text()` as top-level scientific entry points, writes
result/report bytes to staging, and exits. Its mutations cannot survive process
exit.

A test parses the child entrypoint AST using a deny-by-default allowlist: exact
imports, the two named attribute assignments, the two named frozen-summary calls,
the one exact producer `family_summary` call inside the adapter, and no other
frozen-module mutation, deletion, dynamic execution, reflection, or arbitrary
callable invocation. Tests independently reconstruct every K2 point and all 2,000
draws using both helpers, require exact equality with the
producer-rule reconstruction, and require the generic reconstruction to differ
only by the known spurious assigned-coordinate leakage entry. The parent also
deep-fingerprints the original source files and its own immutable contract before
and after the child. Any AST, drift-contract, or fingerprint mismatch is a
technical failure.

The executable also rejects any result whose schema, complete key set, fixed
disposition, original continuation bundle, evidence class, no-promotion flags,
blind-final state, or resource totals differ from the frozen recomputation
contract. It serializes the recomputed object directly; there is no post-recompute
scientific-result mutation seam.

### Candidate before canonical publication

The first execution writes only a noncanonical, create-once candidate root:

`results/atlas/completion_diagnostic_summary_candidate_v1/`

It contains exactly `diagnostic_results.json`, `diagnostic_results.md`,
`source_lineage.json`, and `CANDIDATE_COMPLETE.json`. Define the **candidate content
digest** over the first three files only: compute their SHA-256 values, form the
path-sorted list of `{path, sha256}`, serialize as UTF-8 canonical JSON
(`sort_keys=true`, separators `(',', ':')`, no newline), and SHA-256 those bytes.
The candidate terminal is excluded from that noncircular content digest and has
its own SHA-256. The candidate terminal binds
the original continuation bundle, initial recovery bundle, three content hashes,
`canonical=false`, `diagnostic_continuation_only=true`, and
`decision_promotion_allowed=false`. It cannot be consumed as the canonical result.

After candidate `--verify-candidate` succeeds, independent exact-hash result/diff
and scientific-claim reviewers must both return `SHIP`. Each machine-readable
review record must contain exactly its schema version, verdict `SHIP`, candidate
content digest, candidate-terminal SHA-256, transcript path, and transcript
SHA-256. A second, noncircular promotion freeze binds both candidate hashes, the
path-sorted per-file inventory/hash of all three candidate content files, and
both exact review records/transcripts. Only then may a separate `publish`
subcommand construct the
canonical root:

`results/atlas/completion_diagnostic_v1/`

The canonical root contains the same three content files plus
`RECOVERY_PROVENANCE.json` and exactly one scientific terminal
(`FROZEN_EQUIVOCAL_STOP.json` for the observed stopped disposition, otherwise
`MEASUREMENT_COMPLETE.json`). Its terminal schema must bind the original
continuation bundle, initial recovery bundle, promotion-freeze bundle, original
failed-job terminal/log hashes, candidate digest, all four canonical content
hashes, fixed diagnostic/no-promotion flags, reason, and timestamp. Canonical
verification rejects a result if this recovery provenance chain is absent.
Before canonical provenance or terminal creation, `publish` must compare each of
the three staged canonical content files byte-for-byte and hash-for-hash with that
promotion-frozen candidate inventory and fail closed on any difference.
`--verify-only` repeats the direct candidate-to-canonical per-file comparison in
addition to fresh replay.

### Crash-safe reserved-root publication

An on-mount pre-freeze capability dry run established that this NFSv4 deployment
returns `EINVAL` for `renameat2(RENAME_NOREPLACE)` even for a file. Whole-directory
no-replace rename is therefore forbidden rather than wished into existence.
Candidate generation and canonical publication instead use a nonconsumable-until-
closed reserved-root protocol built from NFS-supported no-replace primitives.

Each job first creates a unique private staging directory, fsyncs that new directory
entry through its parent, builds and validates the complete staged inventory, and
then fsyncs every staged file, the staging directory, and its parent again. No
`ready_to_publish` state may exist until all of those calls return success. The
journaled `ready_to_publish` generation binds the staging aggregate
digest, destination, ordered final-file inventory, terminal-last order, and
applicable freezes. Under the job lock, `mkdir(destination, 0700)` atomically
reserves the create-once root name. The root is owned by this publication **only**
when `mkdir` itself returns success, root and parent fsync both subsequently return
success, and a write-once `root_reserved` generation records those facts for the
same publication ID. Every non-successful `mkdir` return is a permanent collision
unless such a prior durable reservation generation already exists. In particular,
an empty exact destination is not evidence of ownership after an ambiguous error.
If the process dies between successful `mkdir` and the durable reservation record,
the root is sacrificed as a collision rather than guessed to be ours. This explicit
liveness loss is the price of create-once safety without a trusted external
allocator.

The staged inventory has one unambiguous encoding: a path-sorted list of
`{path, sha256, size}` for every regular file and no other entry; paths are simple
relative basenames, SHA-256 values are lowercase hexadecimal, and size is the exact
nonnegative byte count. Canonical JSON uses sorted keys, separators `(',', ':')`,
UTF-8, and no trailing newline; the staging aggregate digest is SHA-256 of those
bytes. Ready state stores both this exact ordered list and digest. Reconciliation
rejects a missing/extra/nonregular staged entry, size or hash mismatch, unsafe path,
or any recomputed inventory/digest difference before inspecting the destination.

Only after durable root ownership is established are files published in the frozen
order by same-filesystem hard link, which
is atomic and refuses an existing final name. Candidate publishes result, report,
and lineage before its terminal. Canonical publishes those three files and
recovery provenance before its scientific terminal. After every link return or
exception, the runner accepts only an exact final file, fsyncs it and the
destination directory, and leaves the staged source/link for audit; it never
overwrites or deletes either name. Each durable state generation binds the exact
ordered published-file prefix. The on-disk inventory must equal a contiguous prefix
of the frozen inventory and must not precede the journaled prefix; a hole,
out-of-order entry, extra file, or terminal before the complete nonterminal prefix
is a permanent collision. The candidate/scientific job terminal is therefore
always last.
Finally the runner validates the exact complete root, fsyncs the root and its
parent, and records `parent_fsync_complete` before the external success closure.
No state phase advances past a file, root, or parent fsync until that exact fsync
returns success. A later explicit reconciliation may retry a failed fsync; a
persistent error produces only a technical attempt terminal and never a success
closure.

A crash may leave an owned, reserved but partial destination; that is intentional and
explicitly **nonconsumable** because candidate/canonical verification requires the
exact final inventory, terminal, and external success closure. Reconciliation
under the same lock requires the durable successful-reservation generation, verifies
that both journaled and on-disk inventories are compatible contiguous prefixes,
replays only the missing suffix from the exact staged inventory, idempotently
accepts exact existing links, rejects every mismatch/extra/out-of-order file, and
never rewrites content. A destination with only `ready_to_publish` provenance, or
without exact provenance, remains an `EEXIST` collision even if empty. This trades
atomic directory appearance—which the live NFS does not support—for bytewise
no-overwrite recovery plus a mandatory external consumption gate.

### Per-job exclusion and attempt-bound state

Candidate and publish each have a distinct durable lock file under the recovery
run root. A launcher-created attempt supervisor acquires a nonblocking exclusive
`flock` **before** creating its manifest and holds the same inherited open-file
description through the scientific/reconcile command, attempt terminal, optional
success closure, and final fsync. The Python entrypoints require the inherited lock
descriptor, verify its inode equals the configured job-lock path, and reject a
missing or mismatched descriptor. No second attempt can therefore create a
manifest, mutate state, reconcile, or close while the first job attempt is live. A
barrier-based test launches two real supervisors and proves the rejected loser
cannot alter the winner's state, destination, terminal, or closure.

The deployment is explicitly single-client: a create-once execution-owner record
binds the first supervisor's hostname plus the resolved project root, mount ID,
filesystem type/source, and device identity. Every later command must run on that
same hostname and match the mount binding; a different client is unsupported and
fails before manifest creation. This avoids pretending that untested cross-client
NFS locking is in scope while still using the server-coordinated lock for local
process exclusion. A hostname or mount migration requires a new reviewed recovery
version, not mutation of this run.

There is no overwrite-in-place current-state file. State is an append-only,
write-once generation journal under `job_state/<job>/`: each transition has a
strictly contiguous generation number, previous-generation path/hash,
`active_attempt_id`, and immutable `publication_attempt_id`. Readers reject gaps,
forks, duplicate generations, or a broken hash chain; the unique highest valid
generation is current. A normal run establishes both IDs. Reconciliation preserves
the original publication ID but claims `active_attempt_id` in the next generation.
State writes with a different attempt or previous generation fail. Before writing
an attempt terminal, the supervisor copies the exact final generation (or an
explicit `state_absent` record) to a create-once
`job_state/<job>.<attempt_id>.json` snapshot. The terminal binds that snapshot path
and hash. No later attempt can change either journal history or snapshot.

### Unobservable-exit closure

After acquiring a released job lock, passing the ephemeral on-mount capability
gate, and validating the execution-owner record—but before publishing the current
attempt's capability record or manifest—the supervisor enumerates **all** prior
final capability records, manifests, and terminals for that job. Capability records
are the durable attempt universe: every final capability record must have exactly
one terminal; manifests are an optional exact subset because capability publication
intentionally precedes manifest publication. A manifest or terminal without its
capability is invalid. Because the lock is now exclusively held, any capability
without a terminal belongs to a dead supervisor (including SIGKILL, host crash, or
power loss). If its manifest exists, it receives the normal orphan closure. If the
manifest is absent, it is closed with an immutable
`technical_failure`/`supervisor_unobservable_exit_before_manifest` terminal that
binds `manifest_state=absent`, null manifest hash, the exact capability path/hash,
exact available log hash from the capability context, a create-once `state_absent`
snapshot, released-lock observation, and recovery host/time. A present manifest is
bound as `manifest_state=present` with its exact hash. Neither orphan terminal ever
creates a success closure, even if the last state says parent fsync completed; a new
explicit reconciliation attempt must revalidate the published destination. Only
after every prior capability is terminalized may the current capability record and
then its manifest be published.

The final success closure enumerates the complete ordered manifest, terminal, and
attempt-scoped capability-record inventories. Capability and terminal IDs must be
one-to-one; manifest IDs must equal exactly the terminal rows declaring
`manifest_state=present`; every capability-only row must declare the explicit
before-manifest technical outcome. The closure binds every hash plus the successful
attempt's capability record, manifest, immutable state snapshot, and current
final-state hash. Extra, missing, duplicate, stale, or rewritten manifest, terminal,
capability, or snapshot bytes invalidate verification.
Tests SIGKILL a supervised
attempt before root reservation and after parent fsync, then prove the orphan terminal is
preserved and only an explicit exact-state reconciliation can close success.

### Durable write-once evidence protocol

Every execution-owner record, filesystem-capability record, manifest, state
generation, state snapshot, attempt terminal, and success closure uses one shared `write_once`
protocol; “create-once” never means writing directly to its final name. Serialize
canonical bytes, create a unique same-directory temporary file with exclusive
creation, write and fsync it, attempt `link(temp, final)` to the final
name, inspect both names after **every** syscall return or exception, fsync the
accepted final file and parent directory, and verify its exact expected hash. A
valid exact final record is accepted idempotently even when recovering after a
crash; an absent final plus intact temp is retained and may be retried; a malformed
or conflicting final record is a permanent technical stop. Temporary files are
never mistaken for history or silently deleted.

Before any dependent record is created, the launcher creates the recovery run root
and the complete fixed ancestry for locks, logs, capabilities, manifests, state
journals, work, verification, and job scripts. It fsyncs every newly created
directory and its parent, walking upward to the pre-existing project/run ancestor,
then revalidates and fsyncs that ancestry again after the live capability gate and
before the execution-owner record. State per-job directories are included in this
bootstrap rather than being lazily created by `write_once`. A new staging directory
similarly receives directory-plus-parent fsync both immediately after creation and
after its final staged inventory is durable. A failure at any directory/ancestor
fsync boundary prevents dependent state or evidence publication; a later attempt
must revalidate the entire ancestry before proceeding.

State snapshots are deterministic copies of the attempt-bound state. If a crash
leaves a valid snapshot but no terminal, orphan recovery reuses and verifies that
snapshot rather than trying to recreate it. If only a temp exists, it may publish
the same deterministic snapshot. If a valid success/reconciled terminal exists
but the success closure is absent, the next lock owner revalidates the destination,
snapshot, current journal head, freezes, and parent fsync, then idempotently completes the
missing success closure **before** considering a new manifest. Fault-injection
tests interrupt after each temp write, file fsync, no-replace link, final-file
fsync, and parent fsync for snapshots, terminals, and success closures.

### NFSv4 capability and ambiguous-operation rule

The actual project/result parent is on NFSv4, so local-filesystem rename folklore
is not an assumption. The strict attempt-start order is: acquire the job lock;
perform the ephemeral on-mount capability exercises; only if they pass,
revalidate and fsync the precreated complete recovery-directory ancestry;
write-once publish/validate the execution-owner record; close all prior capability-
defined orphan history; then publish the current capability record and current
manifest in that order. Directory bootstrap entries are
infrastructure rather than evidence and cannot authorize publication; no persistent
recovery **record** is written using untested mount semantics. The gate resolves `/proc/self/mountinfo`
and, on the exact deployment mount, separately exercises file and **nonempty
directory** fsync, successful hard-link no-replace publication, hard-link
`EEXIST` preservation, atomic create-once `mkdir`, and the exact job-lock
`flock(LOCK_EX|LOCK_NB)` contract. A child with a separately opened descriptor must
lose while the supervisor holds the live job lock and must not reach its guarded
manifest-creation marker. Independent
barrier-synchronized processes separately contend for the same hard-link final
name and root-directory reservation; exactly one must publish/reserve while the
loser retains its source or receives `EEXIST`.
It requires exact preserved bytes/source/destination states and re-runs for every
attempt; any mount change or unsupported operation blocks publication.

Each passing gate is serialized to the attempt-scoped write-once path
`filesystem_capabilities/<job>.<attempt_id>.json`. Its strict schema binds job,
attempt ID, tested hostname/time, exact argv/mode/log context, full mount identity,
and every fsync, hard-link, `mkdir`, contention, and separate-descriptor
live-job-lock outcome. The attempt manifest and terminal each bind this path and
hash; a capability-only orphan terminal instead binds the manifest-absent state.
The success closure requires exactly one terminal for every capability record,
requires manifests for exactly the terminal rows declaring them present,
inventories and hashes all three complete ordered sets, and separately binds the
successful attempt's capability path/hash. Verification rejects a stale, absent,
extra, mismatched, or malformed capability record before reconciliation or
consumption. Crash injection covers the boundary after capability publication and
before manifest publication, and proves the immutable manifest-absent orphan
terminal restores a valid total history without claiming scientific success.

Because NFS may report a `mkdir` or `link` error after the server applied it, the
durable `ready_to_publish` binding is retained after **every** return or exception.
The two operations deliberately have different acceptance rules. A `mkdir` error
can never establish ownership: without an earlier durable `root_reserved`
generation recording a successful return plus successful root/parent fsync, the
destination is a permanent collision, including an empty directory created by the
same failed call. After ownership has already been proven, the runner inspects each
hard-link final. An exact final file is idempotently accepted and fsynced; an absent
final with intact staged source remains retryable; both names are expected for a
successful hard link; any mismatched final, foreign entry, or non-prefix inventory
is permanent failure. No error branch removes or rewrites either name. A failed
file/root/parent fsync never advances its corresponding phase; only a later
successful retry may do so. Tests inject ambiguous errno returns both before and
after actually applied `mkdir` and `link` operations on the live NFS mount, inject
file/root/parent fsync errors, and prove that ambiguous root creation is always
sacrificed while only an already-owned exact prefix can advance.

`--verify-candidate` and `--verify-only` freshly replay all lineage and scored
leaves, compare content byte-for-byte, validate the appropriate root terminal and
freeze chain, and require the corresponding external create-once successful job
closure. A root with absent or only technical attempt closure is explicitly
non-consumable even if its internal hashes validate.

### Recovery governance

Use the execution root
`pilot_runs/20260802_atlas_completion_summary_recovery_v1`, tmux session
`msae_atlas_summary_recovery_20260802`, jobs `candidate` and `publish`, and logs
`logs/<job>.<attempt_id>.log`. The launcher assigns a unique attempt ID; inside
tmux, the lock-owning supervisor first closes any prior capability-defined orphan,
then creates the current capability record and attempt manifest before each job and
a create-once attempt terminal on
every shell-observable exit. Manifests bind schema, job, attempt ID,
exact argv, PID/host/start time, both applicable freeze hashes,
staging/destination paths, log path, and the same attempt's strict capability-record
path/hash. Attempt terminals bind schema, job,
attempt ID, manifest presence state and nullable/exact hash, capability-record
path/hash, immutable job-state snapshot path/hash, log hash, exit
code (nullable only for either `supervisor_unobservable_exit` closure), closure reason, outcome
(`success`, `technical_failure`, `destination_collision`, or `reconciled`), last
durable phase, end time, diagnostic-only, and no-promotion flags. Technical attempt
terminals never get overwritten and do not prevent a later reconciliation attempt.

Each job additionally has one create-once successful closure
`job_manifests/<job>.success.json`, written only after destination and parent fsync.
It binds the successful/reconciling attempt terminal, complete one-to-one ordered
capability/terminal histories plus the exact manifest-present subset and hashes, successful attempt's
capability record path/hash, successful state-snapshot and final-state hashes,
destination aggregate digest, applicable
freezes, and no-promotion flags. Candidate/canonical verification requires this
success closure. The append-only state journal records `ready_to_publish`, root
reservation, file-by-file progress, terminal publication, destination fsync, and
parent fsync.
Shell-observable missing terminal output is closed by the
lock-owning launcher trap; unobservable exits are closed by the next lock owner
before any new manifest. The original incident record is never reused.

Create an initial recovery config and freeze record that bind:

- the original continuation freeze (`89587d36...` file hash; bundle
  `ce5fa982...`);
- the unchanged frozen verifier (`7ca5fafd...`) and K2 producer
  (`c11c343d...`) source files already contained in that bundle;
- the immutable `COLLECTION_COMPLETE.json`, failed summarizer terminal, and log;
- the task-row manifest; six partition files (`calibration`, `C1`, and `C2`, each
  `.records.jsonl` and `.units.jsonl`); and the exact activation-lineage files
  covered by the original verified inventory;
- the recovery RFC, config, common resolver, wrapper, freeze script, and tests;
- exact forked `SHIP` plan and implementation review transcripts.

The implementation candidate set is exactly these eight paths, sorted by path:

1. `configs/atlas_completion_summary_recovery/analysis.json`;
2. `docs/rfc-atlas-v1-diagnostic-summary-recovery.md`;
3. `scripts/msa_completion_summary_recovery_common.py`;
4. `scripts/freeze_msae_completion_summary_recovery.py`;
5. `scripts/freeze_msae_completion_summary_promotion.py`;
6. `scripts/recover_msae_completion_continuation_summary.py`;
7. `scripts/launch_msae_completion_summary_recovery_tmux.sh`;
8. `tests/test_msae_completion_summary_recovery.py`.

For each path compute SHA-256, form a sorted list of `{path, sha256}`, serialize it
as UTF-8 canonical JSON (`sort_keys=true`, separators `(',', ':')`, no newline),
and SHA-256 those bytes. Plan/implementation reviews, both freeze records, output
roots, execution logs, lineage output, result/claim reviews, and documentation
updates are explicitly excluded from this digest. The initial freeze separately
binds the plan and exact-candidate implementation review hashes. The later
promotion freeze separately binds the immutable candidate hashes and exact
result/claim review hashes, avoiding circularity.

Both the initial and promotion freeze records are create-once. The initial freeze
script must refuse if either result root already exists,
if the old failed terminal/log changed, if the original freeze no longer verifies,
or if the implementation review does not bind the exact candidate digest.

## Alternative considered

**Rejected: edit the original summarizer and retry it under the old freeze.** That
would invalidate the original bundle while using scored artifacts that attest to
the old bundle, and deleting the failed job terminal would erase incident history.

**Rejected: derive expected sources from the observed point leaves alone.** That
would make the verifier self-referential: an omitted source in every leaf would
also disappear from the expected set. Frozen partition lineage is independent.

**Rejected: rerun scoring under a new full continuation freeze.** The defect is
post-collection and does not affect any scored value. Repeating approximately
17 GPU-hours would add no scientific information and introduce avoidable drift.

## Milestones

### R0 — Review and freeze design

- Record a forked adversarial `SHIP` review of this RFC.
- Implement config, resolver, wrapper, freezer, and tests without changing any
  original frozen file.
- Run the prescribed tests and record an exact-candidate forked implementation
  `SHIP` review.
- Create the initial recovery freeze only while candidate and canonical roots are
  absent.

Acceptance: the freeze verifier returns one bundle digest and all original hashes
still match.

### R1 — Execute and review noncanonical replay

- Run only the `candidate` subcommand in the dedicated tmux session on CPU.
- Preserve the original failed summarize job/window records.
- Run `--verify-candidate`, then obtain independent exact-candidate result/diff and
  scientific-claim `SHIP` reviews.
- Create the promotion freeze binding the candidate aggregate/terminal hashes,
  all three candidate content-file hashes, and review hashes while the
  canonical root is absent.

Acceptance: the noncanonical root is complete and reproducible, both reviews are
`SHIP`, the promotion freeze verifies, and no scored/run-root file changed.

### R2 — Canonical reserved-root publication

- Run only the `publish` subcommand in tmux after the promotion freeze.
- Run canonical `--verify-only` and require the mandatory recovery provenance
  chain.
- Re-verify original continuation freeze, source inventory, collection, and blind
  final lock.

Acceptance: canonical root is atomically name-reserved, every file is linked
no-replace in terminal-last order, the completed root verifies byte-for-byte
against the reviewed candidate, and it binds both recovery freezes.

### R3 — Documentation and final review

- Update `TODO.md`, `RESULTS.md`, `ANALYSIS.md`, and the atlas completion report
  with only replay-supported claims.
- Submit the documentation diff and its scientific claims to independent
  adversarial review; revise reporting until no blocker or revision remains.

Acceptance: reviewers return `SHIP` for implementation/reporting and no scientific
claim exceeds diagnostic-only evidence.

## Definition of done

- [ ] Original continuation freeze, scored artifacts, collection, failed summary
   terminal, and failed summary log retain their frozen hashes.
- [ ] No original frozen source file is edited.
- [ ] The resolver rejects every missing/conflicting/out-of-range lineage case;
  exact scoring-lineage and partition-lineage source/group values match per row;
  real-data source sets also match all K2 point-leaf source inventories.
- [ ] Recovery tests and all applicable continuation/completion/atlas tests pass.
  The single frozen pre-execution assertion
  `test_actual_adapter_and_frozen_worker_point_and_shard_paths_are_fixture_only`
  is explicitly deselected because its final `assert not cc.RUN_ROOT.exists()` is
  mechanically false after the now-frozen completed continuation run; the original
  test/source hash remains
  `16c4872ee4105b0ad0b8b340f262f32d82d228a619506ed454853fc0f683a4ac`.
  Its pre-run `174 passed` evidence is the
  frozen forked implementation review
  `reports/adversarial/atlas_completion_continuation_implementation_review_20260801.md`
  (SHA-256
  `ca6d3a4f69ab354e9e2bc2f8305e9128cbe4e9771578c6cc9df48df2f108d382`),
  produced by the exact four-file command recorded at
  `docs/rfc-atlas-v1-diagnostic-continuation.md:573-575`; both review and test are
  bound by the original continuation freeze. The post-run command must report this
  exact node as the sole deselection and no failures. Recovery tests separately
  require the frozen run root, collection terminal, all 2,004 K2 leaves, and
  isolated adapter replay.
- [ ] An exact implementation `SHIP` review precedes the recovery freeze.
- [ ] Diagnostic result replay succeeds from all 2,000 K2 draws, 500 stability draws,
   four specificity results, and supporting terminal/registration records.
- [ ] The noncanonical candidate is replay-verified and receives exact-hash result
  and claim `SHIP` reviews before a promotion freeze and canonical publication.
- [ ] Candidate and canonical roots are atomically reserved and populated by
  terminal-last, fsynced no-replace links; crash-created partial roots remain
  nonconsumable and reconcile only from exact staged bytes, a durable
  successful-`mkdir` reservation record, and compatible ordered-prefix journal and
  on-disk inventories. An ambiguous/preexisting empty root without that record is
  permanently rejected.
- [ ] Candidate/publish manifests and terminals durably close success, collision,
  pre-reservation failure, partial-link/pre-parent-fsync interruption, and post-publication
  verification failure with exact log/state hashes; idempotent reconciliation can
  finish only an exact ready-state/destination pair without rewriting content.
- [ ] Per-job exclusion spans manifest through closure; every state transition is
  generation- and attempt-bound; concurrent losers cannot mutate winner evidence.
  Every live capability record proves separate-descriptor job-lock contention and
  that the losing process cannot reach manifest creation.
- [ ] Every capability-defined attempt has exactly one immutable terminal and state
  snapshot; manifests exist for the exact terminal-declared subset. SIGKILL/orphan
  recovery, including capability publication before manifest publication, is
  explicit, fail-closed, and included in the total history before success can be
  consumed.
- [ ] Every evidence record uses the fsynced no-replace `write_once` protocol;
  all between-step crash injections reconcile an exact final or stop without
  rewriting history. The complete recovery evidence ancestry is precreated and
  fsynced through a durable ancestor before dependent records, and staging
  directories are fsynced with their parent before ready-state publication.
- [ ] The live NFSv4 capability gate passes for each attempt, execution remains on
  the bound single client/mount, ambiguous `mkdir` never creates ownership, and an
  ambiguous link advances only after owned-root, exact-prefix, staging/destination
  inspection. File/root/parent fsync failures never advance until a successful
  retry. Each present manifest, every terminal, and the success closure bind the
  matching strict attempt capability record; closure verifies one-to-one
  capability/terminal IDs and the exact terminal-declared manifest subset.
- [ ] Candidate/canonical verification rejects a hash-valid root until its external
  create-once success closure proves destination and parent fsync.
- [ ] `--verify-only` reproduces the canonical result and validates its mandatory
  original-continuation/initial-recovery/promotion provenance chain.
- [ ] The canonical terminal binds old failure evidence, candidate digest, source
  lineage, diagnostic JSON/report/provenance, and fixed no-promotion flags.
- [ ] Original G1/G2 remain equivocal; G1a/G2a remain unrendered; paper branch remains
   unselected; training remains unwarranted; blind final remains locked.
- [ ] No checkpoint or training artifact is created.

## Risks and one-way doors

- **Post-score code change:** contained by noncanonical replay, exact input/output
  hashes, prepublication result/claim reviews, two freezes, and a mandatory
  canonical provenance terminal.
- **Self-validating source inventory:** prevented by per-row agreement between
  exact activation scoring lineage and independent partition lineage.
- **Partial publication:** made safe and nonconsumable by staging, a durable
  successful-`mkdir` reservation witness, contiguous-prefix terminal-last
  no-replace links, exact reconciliation, and the mandatory external closure;
  stale staging/partial roots are never results. A crash before the reservation
  witness deliberately sacrifices the name instead of inferring ownership.
- **Silent scientific drift:** runtime global/callable snapshots, AST enforcement,
  exact result-schema/disposition invariants, and exact implementation review
  constrain the two named substitutions; the family adapter is additionally
  required to equal the unchanged producer rule on registered artifacts.
- **One-way door:** publishing the create-once diagnostic result root. It occurs
  only after reviewed candidate replay and the promotion freeze.

## Verification plan

- `bash -n` for any recovery launcher added later.
- `python -m compileall -q scripts tests`.
- focused recovery tests for real lineage, malformed IDs, missing variants/records,
  negative/out-of-range tokens, activation metadata/index mismatch, per-row
  activation/partition disagreement, hash mismatch, conflicting mappings,
  observed-source comparison, exact producer-versus-verifier family drift,
  forbidden frozen-module mutation, schema/disposition
  drift, staging crashes before reservation/link, interruption before/after parent
  fsync, `EEXIST` handling, root-reservation and hard-link contention, manifest/terminal
  closure and tamper, real barrier-based concurrent supervisors, SIGKILL before
  root reservation and after parent fsync, orphan terminalization, generation/attempt-state
  mismatch, write-once crash injection at every persistence boundary, on-mount
  NFS capability/collision checks, separate-descriptor flock contention,
  ambiguous applied/not-applied mkdir/link errors, precreated empty-root rejection,
  non-prefix/terminal-before-content rejection, file/root/parent fsync failure,
  crash injection after every recovery-directory creation/ancestor fsync and both
  staging-directory parent-fsync boundaries, stale/missing/malformed/mismatched
  capability-record rejection, direct promotion-frozen candidate-to-canonical
  per-file mismatch rejection, capability-record crash before manifest with exact
  manifest-absent orphan terminalization, canonical staged-inventory encoding and
  per-file size/hash mismatch rejection,
  exact reconciliation across every reserved-root publication phase,
  rejection without success closure, and both create-once freeze/refusal behaviors.
- all existing continuation/completion/metrics/data tests, with only the named
  frozen pre-execution `RUN_ROOT`-absence assertion explicitly deselected after
  verifying its unchanged frozen hash and cited pre-run `174 passed` review; the
  current output must show exactly one deselected node and no failures. No
  scientific or adapter test failure is waived.
- `scripts/check_msae_paths.py`, `git diff --check`, source-inventory verification.
- original continuation freeze verification before and after recovery.
- `--verify-candidate` before result/claim review and promotion freeze;
  `--verify-only` after canonical publication.
- independent `/adversarial` implementation review, prepublication candidate
  result/claim reviews, and post-documentation diff/claim reviews.
