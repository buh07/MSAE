# MSAE v3 post-M7 gen7 execution protocol

Status: implementation candidate. This document implements the immutable gen7
plan and does not itself authorize a capability publication, protocol write,
GPU query, model call, calibration session, confirmation scoring, or Stage C.

Normative authorities:

- plan: `docs/plan-msae-independent-measurement-v3-post-m7-gen7.md`, SHA-256
  `d612a86b3c33f774e51f649f1b87dc4977d6d91d2734e27729e84eb9a4867d5d`;
- plan review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen7_plan.md`,
  SHA-256
  `f3e3117e8331849c18f1520626e50edfed5c9602aa7b09ccd24bae434e016354`.

The plan is authoritative wherever this shorter RFC omits detail. Changing that
reviewed plan requires a disjoint generation rather than reinterpretation.

## 1. Scope and historical status

Gen7 preserves the reviewed M1/M2 science, unchanged AMALGUM split, calibration
strata, all four role-specific 500-map sets, checkpoint lineages, endpoint
products, tolerances, thresholds, G1/G2 definitions, and Stage-B semantics.
It makes control-plane changes only:

1. preserve gen6 as failed before capability after its implementation review
   found a stale RFC, incomplete guards, and tautological containment evidence;
2. add the mode-0700, 78-byte `/tmp/m7p_<stage-a-sha>.sock` monitor-to-pane
   lease channel to the already-short tmux and broker channels;
3. replace independent production/test tmux launch paths with the exact shared
   `foreground_tmux_start_v1(config, fault_control)` control path; and
4. prove that path with 75 pre/post fault hooks in crash and exception modes,
   twelve non-hook lifecycle scenarios, cleanup-operation mutations, and live
   process/import/environment/sealed-open tripwires.

Gen2 failed before Stage A because four replay environment digests depended on
the candidate root. Gen3 failed before its first write. Gen4 failed before
implementation review because `renameat2(RENAME_NOREPLACE)` returned `EINVAL`
on the repository NFS mount. Gen5 froze AF_UNIX paths that Linux cannot bind.
Gen6 failed before capability and before every protocol/scientific state write.
None is reclassified as passing.

The disclosed gen5 and gen6 real-tmux invocations were non-scientific
containment tests; they were not capability runs and do not establish that
either terminal subject passed. No gen6 capability, implementation review, M3,
Stage A, signature, GPU/model job, or calibration session exists.

## 2. Immutable authority and review sequence

Every gate rehashes the frozen M1/M2 evidence, failed-gen3/gen4/gen5/gen6 subjects,
gen7 plan and plan review, the current seven-file implementation subject, and
the phase-appropriate reviews and generated artifacts. Reviews are canonical
UTF-8, newline-terminated, current-UID, mode-0644, nlink-1 regular files with an
exact ordered machine-control block. Missing, extra, duplicate, malformed,
conflicting, stale, hardlinked, symlinked, or substituted controls block.

The one-way sequence is:

1. reviewed gen7 plan;
2. all implementation/static/CPU/publisher/source-only/real-tmux tests;
3. external `gen7_pre_capability` SHIP review;
4. exactly one capability reproduction and publication;
5. external `gen7_implementation` SHIP review;
6. 24-receipt M3 setup;
7. external `gen7_post_m3` SHIP review;
8. two-tree M4 and traced prescore evidence;
9. external `gen7_prescore` SHIP review;
10. one signed calibration-only authorization; and
11. launcher-only GPU selection, lease, monitored tmux handoff, then immediate
    return without waiting for calibration results.

Confirmation scoring and Stage C remain prohibited.

## 3. Sealed data, source-only execution, and closure

The exact quarantine set is:

- `data/atlas_v1/private/final.jsonl`;
- `data/atlas_v1/private/final.records.jsonl`;
- `data/atlas_v1/private/final.units.jsonl`.

No gen7 operation opens, hashes, or content-reads these objects. Every guarded
transition compares exact lstat-only rows before and in a `finally` block after
its body. Same-inode aliases, link/type/mode/owner drift, or attempted content
access block.

Every production project-code process is source-only isolated Python
`-S -B -I`. The finite loader reads only registered `.py` source and the normal
repository `scripts/` path is removed before deferred imports. Ignored `.pyc`,
sourceless `.pyc`, and extension shadows cannot execute. The only exceptions
are the plan-registered installed-pytest harnesses; every project child they
start is still source-only isolated.

The closure contains the complete local source/value-flow ledger, exact dynamic
file/import/process/network/library registries, requirements and distribution
metadata, Python startup inputs, executables and recursive ELF dependencies,
model/tokenizer snapshot, four checkpoint lineages, environment, endpoint
registry, and every public execution route. A CPU/no-model trace runs every
registered route under file/process/network/library/model-import tripwires.

## 4. Closed namespaces and short sockets

All repository, external key/state, transaction, build, review, evidence, run,
and test paths are the literal paths in the plan. Each phase admits one exact
lstat child projection; ignored and untracked objects count. Any undeclared
object, symlink ancestor, nonregular child, wrong owner/mode/link count, or
same-inode alias blocks before a write.

All seven short `/tmp` families are independently closed. A held no-follow
`/tmp` directory FD binds device, inode, UID/GID, mode 01777, mountinfo digest,
and filesystem identity. Every gate rejects any unregistered `m7t_*`, `m7b_*`,
`m7p_*`, `m7x_*`, `m7a_*`, `m7c_*`, or `m7s_*` entry. Creators set and verify
umask 0077. Live sockets are current-UID/GID, mode-0700 unless the typed test ACK
socket requires 0600, nlink-1 sockets whose identity remains stable around every
command and unlink. Foreign/substituted paths are never removed.

For Stage-A digest `D` (exactly 64 lowercase hexadecimal characters), the three
production socket names are:

- tmux control: `/tmp/m7t_${D}.sock`;
- launcher-to-broker gate: `/tmp/m7b_${D}.sock`; and
- monitor-to-pane lease: `/tmp/m7p_${D}.sock`.

Each name is exactly 78 bytes. All three are absent before launch. The broker
socket exists only from launcher bind through final gate confirmation and is
removed before takeover ACK/launcher return. The pane socket exists only from
monitor bind through the validated two-frame pane-lease transfer and is removed
before live handoff. The tmux socket remains identity-bound for the live run and
is removed only after terminal outcome/failure and complete session/server/
process extinction.

The one registered containment command uses disjoint families
`/tmp/m7x_<test-token>.sock`, `/tmp/m7a_<test-token>.sock`,
`/tmp/m7c_<test-token>.sock`, and scratch root `/tmp/m7s_<test-token>`, plus
session `msae-independent-v3-gen7-containment`. `test-token` is the SHA-256 of
the plan-defined canonical JSON over the plan digest and ordered seven
implementation digests. The plan's exact child set contains operational records,
logs, terminal-test evidence, 150 hook ledgers, and twelve scenario ledgers.
Every test family is empty before and after every case and at supervisor exit.

## 5. Capability and failed-generation evidence

The only pre-implementation-review publication command is:

```text
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen7.py probe-gen7-capability --pre-capability-review-sha256 <64-lowerhex> --output reports/analysis/msae_independent_measurement_v3_post_m2_gen7/gen7_capability_reproduction.json
```

It runs only after all seven implementation entries and registered tests are
stable and the external pre-capability review is SHIP. Its recoverable
hard-link transaction seals the complete canonical report bytes before source
publication. A completed invocation always publishes one terminal report,
including typed negative/technical observations. Only `overall_pass=true`
permits implementation review; false is permanent failure for gen7.

The report has three exact typed checks:

1. the inherited NFS `renameat2(RENAME_NOREPLACE)` failure reproduction;
2. grouped rejection of the frozen 119-byte gen5 tmux and 129-byte gen5 broker
   socket paths with Python's pre-syscall `AF_UNIX path too long`; and
3. grouped bind/listen/connect/close/unlink round trips for all three 78-byte
   gen7 production sockets, including exact live socket and `/tmp` parent identities.

It records exact argv/cwd/timestamps, plan/review/seven-file/frozen predecessor
entries, NFS and `/tmp` mount identities, before/after rows and transcripts,
`protocol_path_used=false`, `model_gpu_tmux=false`, and
`sealed_payload_content_reads=0`.

M3 first publishes typed `failed_gen6.json`, then failed-gen5/gen4/gen3/gen2.
Failed-gen6 evidence binds the exact nine-entry plan/review/seven-file subject,
the exact external failure review and all three recorded blockers, current
complete downstream absence, disclosed commands and summaries, unavailable
transcripts without invention, and `capability/protocol/GPU/model/calibration`
as false/not-created/not-run. It never cites the failed gen6 suite as successful
evidence. Failed-gen5 evidence still binds both impossible-path observations and
separately classified non-experiment tmux history; no record erases disclosed
containment activity.

## 6. Recoverable NFS publisher and M3

All create-once repository publications use the reviewed hard-link publisher,
not rename. A mode-0600 canonical descriptor binds authority, source and
destination parent/basename, UID/mode/size/SHA-256, NFS mount identity, at most
three durable attempt markers, and a five-minute recovery deadline. Publication
uses held no-follow parent FDs, durable exact source creation, `linkat`, exact
pair validation, source unlink, NFS settling bound to the published inode, and
parent fsync. Legal prefixes are source-only, exact same-inode pair, or
destination-only. Unknown children, lost authority, non-prefix destinations,
expired/exhausted attempts, or substitution block without deletion.

Setup is a 24-receipt transaction. Each receipt binds the prior receipt, plan,
capability, implementation review, frozen predecessors, code, mount identity,
exact pre/post namespace projections, artifact entry, and sealed-read count.
The registered order is provenance root; failed gen6/gen5/gen4/gen3/gen2; M4
data; config; state; nonce; key staging; private payload; key binding; final key;
setup subject; public key; commitment; CPU trace; protocol; key-binding deletion;
key-payload deletion; key-staging removal; and setup-manifest publication. The
manifest binds receipts 0001--0023 only; receipt 0024 binds the manifest digest,
avoiding a digest cycle.

The result is non-authorizing M3 state: exact four-file config, empty M4 data,
five failed records plus setup manifest in provenance, empty nonce directory,
mode-0600 private key with public commitment, and no downstream output.

## 7. M4, prescore, signing, and Stage B

After the post-M3 review, M4 copies every exact input into two initially absent
sparse roots. All rooted builders, imports, config, closure, Stage A, status,
and manifest operations use only their explicit root. It compares full
file/directory/config/closure/Stage-A/manifest bytes, reauthorizes the live
snapshot and external state, then installs the ordered six-file prefix through
the recoverable publisher. Crash-left scratch and install prefixes are accepted
only through the plan's exact recovery projection.

The candidate manifest binds every closure input, mode/UID/nlink/action/result,
repository status and classification, protected predecessor/baseline results,
sealed metadata, exact directory projections, external absence/short-family
state, Stage A, status, and checker code. Prescore runs through the exact
`strace -f -qq -yy` descriptor command, resolves indirect opens, reconstructs
the complete typed check payload, and requires sealed content reads zero.

Signing revalidates the external prescore SHIP review and creates one
nonce/time-bound `calibration_replay_only` Ed25519 envelope. A recoverable
transaction seals the authorization bytes. The signer is the only post-setup
route that content-reads the private key. Verification uses only the committed
public key. Nonce consumption is an exact single-use, mode-0600 durable record.

The runner cannot import torch or model code until the signed authorization,
config, Stage A, closure, UUID lease, nonce, environment, and two-phase gate all
validate. Stage B records native-library realization before import, after torch,
after model, and finally; exact cache/order/digests; tolerance selection;
digest-based no-op, pooling, and counterfactual QA; and one mutually exclusive
terminal success or technical-failure tree. Confirmation and Stage C are not
reachable.

## 8. Persistent monitor and exact control protocol

All production and containment roles call the same source-only
`foreground_tmux_start_v1(config, fault_control)` bytes. Its config and fault
control have the plan's exact closed schemas and role applicability; production
fault control is the exact disabled object. The helper owns every file/socket/
process/tmux/frame/terminal/cleanup side effect. Callers provide only canonical
data and held FDs.

After repeated idle checks and the UUID flock, the launcher-role helper creates
`launcher_intent.json`, mode-0600 `monitor.log` and `tmux_server.log`, distinct
bound broker and pane sockets, and one `AF_UNIX/SOCK_SEQPACKET` socketpair. It
starts exactly one source-only monitor in its own process group with a closed
environment and six distinct inherited FDs >=3: control, lease, monitor log,
server log, pane listener, and broker-cleanup authority. The monitor verifies
stdio, all six bindings, inheritable flags, closed unrelated FDs, control
credentials, environment, launcher intent, lease, code, logs, and that its
broker duplicate is cleanup-only and never accepted.

The launcher publishes canonical mode-0600 `tmux_monitor.json` with schema
`msae_v3_gen7_tmux_monitor_v2` and the exact plan-registered keys/nested
schemas. It binds the authorization, Stage A, capability, launcher/monitor,
code, control, six FDs, logs, GPU/lease, all three socket names, and handoff/
terminal deadlines.

The socketpair carries one canonical JSON object per datagram, no ancillary FDs,
maximum 65,536 bytes, stable peer credentials, exact prior-frame chaining, and
this seven-frame sequence:

1. monitor `MONITOR_HELLO`;
2. launcher `MONITOR_RECORD_COMMITTED`;
3. monitor `MONITOR_RECORD_ACK`;
4. launcher `START_SERVER`;
5. monitor `SERVER_READY`;
6. launcher `HANDOFF_COMMITTED`;
7. monitor `TAKEOVER_ACK`.

Every frame has the exact common and payload key sets in the frozen plan. The
monitor cannot fork tmux until frame 4. Wrong credentials, type, sequence,
prior digest, canonical bytes, truncation, ancillary data, timeout, duplicate,
extra data, or premature EOF enters cleanup. Handoff's control transcript is
exactly `canonical_bytes([frame1,...,frame5])`; frames 6/7 are excluded to avoid
a digest cycle. The record-subject, record-ACK, server-start transcript,
broker-family projection, and monitor-live-subject preimages are exactly the
objects enumerated in the plan.

The pane connects only to the inherited pane listener. Its exact two-frame
`msae_v3_gen7_pane_lease_frame_v1` protocol carries monitor-to-pane
`PANE_LEASE_HANDOFF` followed by pane-to-monitor `PANE_LEASE_ACK`; the first
frame transfers exactly the lease and, in containment only, the fault-event FD
via `SCM_RIGHTS`. The monitor validates pane/tmux lineage, the ACK's exact
frame-1 digest, and descriptor identities before unlinking the pane socket. No
lease FD is inherited through tmux.

The monitor is a subreaper and owns tmux throughout the live run. It forks a
child that calls `setsid`, verifies PID=PGID, arms parent-death SIGKILL, and
executes only:

```text
/usr/bin/tmux -D -f /dev/null -S /tmp/m7t_<D>.sock
```

After the mode-0700 socket appears, separate captured process groups run bounded
15-second clients for:

- `new-session -d -s msae-independent-v3-gen7-calibration` with the exact
  source-only in-pane supervisor command;
- `set-option -s exit-empty on`;
- `show-options -s -v exit-empty` requiring `on\n`; and
- `display-message -p -t msae-independent-v3-gen7-calibration
  "#{pid} #{pane_pid}"` requiring the foreground server and pane identities.

Every `nvidia-smi` query and nonserver tmux client has a 15-second timeout.
The monitor continuously captures same-UID descendants/adopted children with
PID/start-ticks/PPID/PGID identities. The in-pane supervisor deliberately has no
parent-death signal; it survives monitor/server death and kills the broker/
worker, removes only the bound tmux socket, and claims technical failure. The
broker and worker retain parent-death protection. Conversely, the monitor
handles pane/supervisor death.

After runner readiness, the launcher durably writes handoff, opens the final
model gate, validates confirmation, removes the broker socket and proves the
`m7b_*` family empty, then sends frame 6. The monitor independently reopens the
handoff, validates lease/process/socket/gate lineage, and sends frame 7. The
launcher rejects extra data, closes its endpoint, and returns immediately. The
monitor requires that final launcher EOF before entering its terminal loop.

The monitor retains the lease and watches the terminal trees, server, captured
processes, and six-hour deadline. Success or failure triggers non-short-
circuiting TERM/wait/KILL/reap, bounded session/server clients, exact process and
PGID extinction, descriptor-bound socket unlink, final missing-socket
`has-session` proof, path recheck, terminal evidence, lease release, and exit.
Monitor death is handled by the in-pane supervisor; pane death is handled by the
monitor. No failure may return with a live session, listener, socket, captured
process/group, scratch object, or ambiguous terminal state.

## 9. Registered verification and launch behavior

Before capability publication, the implementation must pass:

- syntax and shell checks;
- predecessor/remediation suites;
- complete gen7 CPU/static/source-only/publisher/mount/recovery tests;
- planted closure and namespace mutations;
- capability report/recovery negative paths;
- 24-receipt interruption/reentry matrix; and
- the one plan-authorized, non-experiment real-tmux containment command using
  the fixed fake broker, process/GPU/model/environment tripwires, global
  deadline, all 75 crash/exception hook boundaries, twelve typed lifecycle
  scenarios, cleanup-operation mutation matrix, and exact final absence.

The pre-capability review's `CHECKS RUN` block is machine data, not prose.  It
contains exactly ten contiguous lines `CHECK_ROW_JSON: <canonical-json>` in
this order: `predecessor_v1`, `predecessor_v2`, `predecessor_v3`,
`predecessor_post_m1`, `predecessor_post_m2_runtime`,
`predecessor_remediation_v1`, `predecessor_gen4`, `gen7_cpu`,
`gen7_publisher`, and `gen7_real_tmux`.  Each object has schema
`msae_v3_gen7_pre_capability_check_v1` and exact keys `schema_version`, `id`,
`argv`, `cwd`, `environment`, `subject_sha256`, `exit_code`, and `summary`;
the last two values are literal `0` and `pass`.  `cwd` is the literal repository
root.  The first nine arrays begin with
`[/usr/bin/env,-i,PATH=/usr/bin:/bin,HOME=/thayerfs/home/f004ndc,LANG=C.UTF-8,
LC_ALL=C.UTF-8,PYTEST_DISABLE_PLUGIN_AUTOLOAD=1,<repo>/.venv-atlas/bin/python,
-B,-I,-m,pytest,-q,-p,no:cacheprovider]` followed respectively by the nine
literal file/selector suffixes in the frozen plan.  The final array is exactly
`[/usr/bin/env,-i,PATH=/usr/bin:/bin,HOME=/thayerfs/home/f004ndc,LANG=C.UTF-8,
LC_ALL=C.UTF-8,<repo>/.venv-atlas/bin/python,-S,-B,-I,
scripts/run_msae_independent_measurement_v3_post_m2_gen7_tmux_test.py]`.
Installed-pytest rows bind the exact closed environment with the four locale/
home/path fields plus `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`; the outer real-tmux
row binds only those four fields.  `subject_sha256` is the canonical
`msae_v3_gen7_check_subject_v1` digest over the registered ordered path/SHA-256
rows.  Missing, summarized, reordered, duplicated, or stale rows block.

The pre-capability adversarial review binds the exact seven implementation
hashes and zero sealed reads. The capability report then becomes immutable and
the final implementation review binds it plus the predicted failed-generation
records. Subsequent external reviews separately authorize M3-to-M4 and
prescore-to-sign transitions.

Only `launch-gen7`, after signed authorization, may invoke `nvidia-smi`. It
selects an idle GPU under the frozen rule, locks its UUID in the shared namespace,
and performs the monitored handoff above. On successful takeover it returns the
handoff/session information without waiting for calibration results. No gen7
command invokes confirmation scoring or constructs Stage C.
