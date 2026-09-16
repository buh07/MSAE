# MSAE v3 post-M2 gen4 execution protocol

Status: implementation candidate; execution is forbidden until an independent
`gen4_implementation` SHIP review binds these exact bytes.

This RFC implements the frozen plan
`docs/plan-msae-independent-measurement-v3-post-m4-gen4.md`. The plan is
normative if prose here is ambiguous. M0--M2 scientific decisions are unchanged.
Confirmation scoring and Stage C are out of scope.

## 1. Historical disposition

The reviewed `post_m2_gen3` setup command was invoked twice. Both invocations
failed with `ValueError: failed-preflight manifest drift` before the dominating
source-level write branch. Gen4 writes one canonical terminal record at
`reports/provenance/msae_independent_measurement_v3_post_m2_gen3/setup_m3_attempts_1_2_failure.json`.
It distinguishes operator disclosure, mechanically reproduced control flow, and
current-state absence. It does not claim a historical syscall observation.

Gen2 remains failed before Stage A because its generic config builder made four
replay `environment_sha256` fields candidate-root dependent. Gen4 mechanically
rebuilds the immutable generic config at a fixed synthetic root, compares the
full gen2 config, and writes one canonical `m4_failure.json`. Neither record
contains its own digest or the implementation-review digest. The external
implementation review authorizes their predicted digests.

The original gen3 plan, plan review, six implementation entries, implementation
review, and historical preflight remain immutable. Gen3 setup is never invoked
again. The previously disclosed read-only `nvidia-smi` inventory call is
recorded but is not launch evidence.

## 2. Gen4 authority and namespaces

The plan SHA-256 is
`c443a9eba2305a488b9948467676829c4d317cd67d9c4936a339d6af33bd023b`.
The create-once plan review has scope `gen4_plan`. The implementation review has
scope `gen4_implementation` and the exact 22 controls registered in the plan.
The post-M3 review has scope `gen4_post_m3` and ten controls. The prescore review
has scope `gen4_prescore`, twelve digest controls, and
`SEALED_PAYLOAD_CONTENT_READS: 0`. Controls are unique, lower-hex, canonical,
newline terminated, and in registered order. Extra, duplicated, indented,
malformed, stale, or conflicting controls block.

All mutable paths are disjoint under the `post_m2_gen4` config, provenance,
M4-data, state, key, run, scratch, evidence, socket, and tmux-session namespaces
listed in the plan. The only cross-generation outputs are the two terminal
records above. Review-prefix child sets and every output directory have exact
phase-specific projections; ignored and untracked extras block.

## 3. Exact public commands

The only M3 command is, in exactly this option order:

```text
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen4.py setup-m3-gen4 --reviewed-m2-sha256 e593a6283aa5468ddbee1cc755dbe60c4ee503375a0cbce44c52614dd232d737 --failed-gen3-plan-review-sha256 e3b2f0047b6fc14aabb0c60227cc1710cac17d3aca67618277ff1e64b4f902bb --failed-gen3-implementation-review-sha256 b77237868339a93f1b4e6ad4592260c83b2a0c318c22c9be27a1d0971f86462a --gen4-plan-review-sha256 45976d778388d0020c58ea4e3a278c7a1d54d0f67b6a266f5fdc2733366c5fce --gen4-implementation-review-sha256 <64-lowerhex>
```

Remaining public transitions, in order, are:

```text
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen4.py build-m4-gen4 --post-m3-review-sha256 <64-lowerhex>
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen4.py prescore-traced-check --manifest reports/provenance/msae_independent_measurement_v3_post_m2_gen4/prescore_candidate_manifest.json --output /tmp/msae_independent_measurement_v3_post_m2_gen4_<manifest_sha256>.prescore.check.json --trace /tmp/msae_independent_measurement_v3_post_m2_gen4_<manifest_sha256>.prescore.trace.log
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen4.py verify-prescore-trace --manifest reports/provenance/msae_independent_measurement_v3_post_m2_gen4/prescore_candidate_manifest.json --check /tmp/msae_independent_measurement_v3_post_m2_gen4_<manifest_sha256>.prescore.check.json --trace /tmp/msae_independent_measurement_v3_post_m2_gen4_<manifest_sha256>.prescore.trace.log
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen4.py sign-gen4
scripts/launch_msae_independent_calibration_v3_gen4.sh
```

Old command names, aliases, reordered/missing/duplicate/extra options, and
noncanonical paths block before writes, subprocesses, GPU queries, or model
imports. `broker-gen4`, `supervise-broker-gen4`, and the runner are internal
capability-bound routes only.

## 4. Source and sealed-data containment

The controller and runner remove the repository scripts directory from normal
`sys.path` before local or deferred third-party imports. A finite source-only
finder loads the exact registered local `.py` files, never `.pyc` or extension
shadows. Static analysis binds all local AST value flow, dynamic file sites,
process argv/environment templates, imports, library loads, and network sites.
A CPU/no-model trace exercises every registered public entry and plants file,
process, shell, library, and network escapes.

The three private `final*.jsonl` payloads are metadata-only quarantine objects.
Every one-way command runs under an open/read/hash tripwire and compares exact
before/after lstat rows even if the guarded body raises. No sealed payload is
opened or hashed. Same-inode aliases block.

The signing private key is content-read only during staged setup agreement and
signing. Post-M3, M4, prescore, worker, and launch validation use the committed
public key and exact private-key lstat identity only.

## 5. M3 setup transaction

Setup validates all reviews, predictions, source-only closure, quarantine,
phase namespaces, and downstream absence before its first write. Its canonical
`transaction.json` binds the exact argv, four lineage maps, expected paths,
stable root identities, and the exact 21 receipt names. The journal is mode
0700; its descriptor and receipts are mode 0600.

The ordered actions are exactly:

1. gen3 provenance root;
2. gen3 terminal record;
3. gen2 M4-failure record;
4. gen4 M4-data root;
5. gen4 config root;
6. gen4 state root;
7. nonce root;
8. key-transaction root;
9. staged private-key payload;
10. key descriptor;
11. final private key;
12. durable virtual setup subject;
13. public key;
14. authorization commitment;
15. CPU/no-model trace;
16. protocol config;
17. key-descriptor deletion;
18. key-payload deletion;
19. key-transaction removal;
20. pre-manifest projection verification;
21. setup-manifest publication.

Receipts are an exact prefix. Only the next action object may be durable without
its receipt. Later objects, holes, extra children, wrong type/mode/UID/link,
noncanonical bytes, or non-prefix adjacent partials poison gen4. Every file uses
the registered adjacent-partial publisher: no-follow O_EXCL create, full-write,
file fsync, `renameat2(RENAME_NOREPLACE)`, and parent fsync. Unbound key bytes
may be regenerated only before their descriptor exists.

The setup subject binds both terminal records, all lineages, current
implementation-review authority, transaction, receipts through 0011, the
private/public key pair, and exact roots. Commitment, trace, and protocol bind
its digest. The completion manifest then binds the subject, receipts through
0020, final entries, and exact child sets without creating a digest cycle.
After receipt 0021, descending receipt/descriptor cleanup is fsynced after every
deletion. Manifest-conditioned cleanup accepts only the registered remaining
prefix or empty journal root.

Successful M3 has no execution authorization. Exact children are one setup
manifest in gen4 provenance; four config files; empty M4 data; state containing
an empty nonce directory; one gen3 terminal; one gen2 terminal; and no transient,
M4, prescore, signature, run, GPU, model, or tmux output.

## 6. M4 and Stage A

A fresh external `gen4_post_m3` review binds the exact post-M3 subject. Each M4
scratch tree first publishes a role-specific build descriptor containing the
post-M3 review, input snapshot, and candidate path set. Crash-left trees are
validated without following links, deleted with parent fsync, and rebuilt.
Both complete candidate trees reconstruct config, dependency closure, endpoint
registry, environment allowlist, Stage A, status, and candidate manifest with
no live-repository fallback. Their descriptors are validated separately; all
candidate bytes and directory projections compare exactly.

The install transaction descriptor binds generation, review, input snapshot,
six ordered destinations, all payload digests, and the candidate-manifest
digest. Staging payloads and final destinations are ordered prefixes. Every
destination uses the registered no-replace publisher. Reverse cleanup leaves
only a payload prefix; descriptor-deleted empty-root cleanup is allowed only
when all six exact destinations exist. Transaction absence with a strict
output prefix blocks.

Stage A binds M1/M2 completions, the gen2 terminal, gen3 terminal, gen4 setup
manifest, implementation and post-M3 reviews, checkpoint and endpoint products,
closure/environment, and all typed artifacts. Stage B and Stage C remain
`not_run`.

## 7. Prescore and signing

The manifest-derived traced check is create-once. `strace -f -yy` evidence is
resolved descriptor-safely and must show the exact checker/controller/manifest/
Stage-A/closure opens while showing zero sealed-content opens. The external
prescore review must have the exact registered 12 controls.

Signing revalidates every scientific/review check before creating the mode-0700
run root. It computes nonce, validity interval, unsigned envelope, signature,
and authorization bytes in memory. A mode-0600 sign descriptor binds those
random/time-dependent bytes, all review authorities, exact key lstat, and public
key. Re-entry reuses a valid descriptor. `authorization.payload` is fsynced and
renamed no-replace to `authorization.json`; both directories are fsynced;
descriptor/root cleanup is recoverable. Final signed state is exactly one
mode-0600 authorization file and an empty external nonce directory.

## 8. GPU launch and terminal outcomes

Only the signed launcher may call `nvidia-smi`. It selects an idle GPU, acquires
the persistent UUID lock, rechecks idleness and compute processes under the
lock, authenticates pane/broker/worker lineage and peer credentials, consumes
the authorization nonce exactly once, and completes the durable two-phase
pre-model acknowledgement before returning. tmux uses
`msae-independent-v3-gen4-calibration` with `bash --noprofile --norc` and a
closed environment. Lease/path drift, timeout, broker/worker death, exception,
OOM, or failed handoff terminates and verifies the whole process group and
records `technical_failure_not_run` without Stage B.

The worker imports no model before exact config, closure, authorization, nonce,
lease, readiness, native-map, and final-gate validation. Successful calibration
writes the registered four-stratum forward/pooling caches and typed QA in exact
order, then atomically exposes exactly six terminal-success files. A legitimate
no-ladder-pass or pooling failure is scientific `ineligible`, not a technical
failure. Confirmation scoring and Stage C are not run.

## 9. Acceptance gates

Before implementation review: predecessor and gen4 tests, syntax/shell checks,
static/value-flow closure, CPU/no-model trace, source-shadow attacks, quarantine,
setup/M4/sign crash-prefix tests, exact review/CLI schemas, and no downstream
state. After setup: a fresh post-M3 SHIP. After M4/traced check: a fresh external
prescore SHIP. Only then sign and launch. The coordinator returns immediately
after durable tmux handoff and does not wait for results.
