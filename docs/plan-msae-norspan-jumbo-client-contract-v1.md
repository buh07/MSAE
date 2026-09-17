# PLAN — NORSPAN Jumbo client contract and integration v1

2026-09-16. Prospective source-free implementation plan; NOT source/scoring authority.

## Goal
Fix concrete scratch/process/read defects, complete paired application consumers
and explicit recovery integration, and prospectively qualify a Jumbo-only contract
without administrator contact or invented server/backup guarantees.

## Constraints and non-goals
- Owner explicitly forbids administrator contact. All canonical placement remains
  on Jumbo, DES-0203/0221 unchanged. DES-0230 is proposed only; its administrator
  requirement is a proposed contract to revise prospectively, not silently satisfy.
- All new synthetic subjects/logs/cache/checkpoints beneath
  `/jumbo/lisp/f004ndc/tmp/lisplab1`; candidate code/docs stay in the child project.
- No real source/network/history/census/authority/raw/private/payload/model/GPU/tmux/
  scoring/K2/branch/G3/C2. Never open/hash/print Atlas private finals or real V8/V9/V10
  source/raw/private. No initiated retries, evidence deletion or automatic commit/push.
- Original science plan/config/TODO/V10 reference stay byte-identical. All source,
  license, pedigree, history-overlap, group-role, support, split, claims and decision
  predicates unchanged. V10 terminal; AMALGUM v3 exposed calibration only.
- Preserve prior exact candidates/checkpoints and every BLOCK; scoped SHIP never
  becomes whole approval. The production launch guard remains unconditional.

## Design-bank clarification and approach
Design query for NORSPAN/Jumbo scratch returned DES-0203; DES-0230 explicitly
proposes paired publication/retention, not activation. User now chooses a
client-controlled/no-administrator route and asks prospective review of its scope.
`bin/query` refuses this undeclared child-repository scope; bounded direct reads
of designated public source files establish wiring without searching real history.
The latest whole-candidate review records six maintained scratch failures, old
nlink1 consumers, skipped teardown, blocking sparse FIFO, missing trust/recovery.

Keep JPC permanent stage/final nlink2; ordinary code/config/reviews stay nlink1.
Replace scratch recursive close/reopen validation with a **bounded original-FD
inventory**: retain every admitted child FD through observation, sync, flat
named-alias validation and final original-FD fingerprint sweep. Freeze full
file AND directory mtime/ctime/size/link/type/mode/dev/inode fingerprints, exact
directory names and budgets; reject before admitting beyond 1024 retained objects.
Never collect replacement expectations in validation. Maintain the two named
alias-validation boundaries from retained regressions, then a materially different
original-FD sweep; do not add a third identical recursive walk.

This is NOT an atomic filesystem snapshot or isolation against arbitrary
concurrent same-UID/other-client mutation. It has an explicit controlled-writer
assumption: one create-once controller, private 0700 scratch, owned child session
stopped and leader reaped before inventory/terminal checks; no protocol-authorized
writer remains during observation. Advisory locks do not prove arbitrary writer
exclusion. Unexpected drift fails closed. Finite syscall/metadata validation does
not prove global simultaneity or resistance to malicious stat-preserving writers.
Reports must state this conditional observation contract, not immutable/live
snapshot or server persistence. Relevant named in-call late-mutation tests remain
mandatory and must actually trigger; no skipped/deselected counters to claim closure.

Refactor cleanup to attempt each owned stop/reap/selector/pipe/file/ancestor release
once, preserving the original operation fault and recording secondary errors.
Owned leader/process-group termination obligations are independent of FD closure;
failed termination/reaping prohibits success. Do not retry Linux released FDs.
Open producer/ordinary regular files no-follow/nonblocking before fstat; enforce
per-file/total read byte budgets before and during read, exact fingerprints and
complete named ancestry. This bounds reads, not all server disk allocation.

Paired consumers must use a finite explicit **outside expected receipt session**,
not infer expectations from visible stages, metadata or observed hashes. Live
writers register their actual returned receipt only after success; fresh recovery
needs an externally pinned catalog digest plus trusted containing control schemas
and lineage. Sessionless paired reads fail. Separate physical/logical enumeration
recognizes only prescribed complete/partial pairs; partial remains unresolved.
Update control fields/retained scratch/phase schema/raw/private/seal/history callers
without broad alias/directory exclusions. Ordinary accessible history stays visible.
An explicit fresh recovery command grants zero source/model work and no inferred
past success; any started stage/final without complete terminal forbids retry.
Outside canonical whole/readiness authority is NOT fabricated by a caller's digest
or SHIP header; application integration is distinct from production activation.

## Revised storage contract to review
- Verified locally: native exclusive create/no-replace hardlink, original-FD
  expected-byte custody, prescribed names, file/directory fsync returns, bounded
  reads/output buffers/timeouts/retained descriptors, no initiated deletion/retry,
  explicit current observation/recovery and operation counters, where named tests pass.
- Application thresholds unchanged: 8GiB/file, 64GiB observed total,65536 entries,
  4096 declared open-file ceiling. New scanner1024-object admission is stricter.
  Enforce supervised time/output and read caps; observed scratch totals are gates,
  NOT hard allocation quota/reservation. No claim they prevent in-flight disk growth.
- Linux per-file RLIMIT_FSIZE may be probed synthetically, but is NOT a per-run
  aggregate quota/process-count/descendant-isolation guarantee; don't activate
  unqualified limits or introduce unsafe threaded preexec functions.
- Unverified: server stable-storage/failover/reboot, multi-client isolation, backups,
  retention by administrators, restorability of original identities, quota/reserved
  headroom. No claim of physical loss or exhausted space; no administrator required
  to learn local behavior. Keep these UNKNOWN in every relevant release artifact.
- No self-provisioned mount/FUSE/snapshot/volume implied. Ordinary owner-created
  private directories are not an administrator durability guarantee.
- Use separately named client config/storage-contract doc; preserve old amendment
  and its hashes. No server assurance or administrative hard limit is silently
  claimed by old fields. A future reviewer can BLOCK if scientific/operational
  acceptance cannot honestly hold under this bounded contract.

Alternative considered: administrator-provisioned compatible volume would not fix
software and contradicts no-contact requirement. Repeated walks/ignoring stages/
loosening nlink/copying cleanup_verified=True/unsafe rename fallback are rejected.
Actual enforced snapshot/quota infrastructure is not assumed available.

## Milestones
- [ ] N0 preserve prior170-file checkpoint and current public subjects; prospectively
  independent-review this exact plan and revised conditional storage contract.
- [ ] N1 test-first scratch original-FD inventory, supervisor/all-reader cleanup and
  nonblocking bounded sparse reads. Acceptance: all retained late7+second-pass10
  tests really inject, no false accepted tested mutation, no deleted evidence,
  no owned leaks/reused-FD double-close; real synthetic child and combined faults.
- [ ] N2 separately named no-admin storage config/doc and exact scientific projection;
  local enforceability table/tests, explicit UNKNOWN server/quota/backup assumptions.
  Acceptance: independent bounded contract review; no administrator contact.
- [ ] N3 strict paired consumer/session, physical/logical inventory, raw/private/
  retained-scratch/control/history and explicit fresh application recovery integration.
  Acceptance: actual synthetic complete/rejection/partial/stale/wrong-byte/extra/
  alias/no-retry controls and trusted outside receipt prerequisites; no mock authority
  converted to production approval, no blanket real-identity test suite execution.
- [ ] N4 native-Jumbo named fault progress and independent exact candidate review;
  checkpoint/status/synthesis updated. Every missing/failed whole row explicitly open.
  Acceptance: bounded review scope honest, whole launch either exact approved successor
  plus authenticated authority OR BLOCK. Current task does not activate source work.

## Definition of done
- [ ] Concrete named software failures fixed and independently requalified.
- [ ] Paired writer/reader/control/recovery integration is actually usable on synthetic
  inputs, or unfinished parts explicitly documented without declaring completion.
- [ ] Bounds checked/enforced/conditional/unknown individually distinguished.
- [ ] Revised no-admin Jumbo storage contract prospectively independently reviewed;
  unchanged scientific gates and server guarantees not invented.
- [ ] Reproducible finite PUBLIC/SYNTHETIC checkpoint and accurate handoff; no real work.

## Verification plan
- check-plan; original public/config/science/review hashes before/after.
- Named maintained eleven suites, new explicit synthetic repair/integration suites,
  fresh Jumbo TMPDIR/basetemp and no cacheprovider. Never blanket project pytest.
- py_compile with fresh Jumbo PYTHONPYCACHEPREFIX; git diff --check. Lint/type tools
  only when available, missing not PASS. Retained JUnit/log/failed roots/test IDs.
- Independent plan and risky milestone candidate reviews; exact bytes freeze during
  review. No change to frozen reviewed plan; moving milestone state in new status.

## Risks and one-way doors
This changes operational assurance, not scientific evidence: no server/backup or
hard aggregate quota guarantee. Arbitrary concurrent writers are outside claimed
isolation; owned-group stop/reap failures remain BLOCK. Client observations cannot
establish server-wide guarantees. Receipt authenticity/schema/history and future
whole authority cannot be replaced by untrusted digests. Real source remains once-only.

## Next command
Read and independently review this plan before implementation; no source work.
