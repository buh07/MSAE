# NORSPAN — Jumbo client storage contract v3

2026-09-16. **PROSPECTIVE; no production/source/scoring authority.** Owner requires
Jumbo and forbids administrator contact. This replaces the proposed requirement to
obtain administrator assurances only after independent contract review; it does not
change active topology, source eligibility, scientific thresholds or scoring access.
Original publication/retention amendment and failed reviews remain immutable history.

## Scope and assumptions

Canonical placement stays beneath `/jumbo/lisp/f004ndc/experiments/wip/MSAE`.
New synthetic qualification/logs/cache/checkpoints stay beneath
`/jumbo/lisp/f004ndc/tmp/lisplab1`. No mount, volume, snapshot, FUSE, server quota,
backup facility or administrative privilege is assumed or requested.

One create-once controller owns private0700 acquisition scratch. Every authorized
producer belongs to its owned child session. Group termination and leader reaping
must complete before post-command observation or terminal affirmation. No other
protocol-authorized writer runs during that observation. Private permissions and
create-once markers do not isolate arbitrary same-UID/remote/server mutation.
Arbitrary concurrent writers/stat-preserving reconstruction are outside verified
isolation. Detected drift, stop/reap failure or unavailable required custody keeps
the invocation unresolved; never retry initiated source/raw work.

## Publication and trusted observations

JPC keeps both `.F.stage` and final `F` permanently, exactly nlink2, original owned
dev/inode/mode/size/hash, full no-follow named ancestors and no-replace hardlink.
No rename/unlink/overwrite fallback or initiated evidence cleanup. Visibility is
not successful publication, manifest approval or scientific access authority.
Consumers require independently anchored outside expected receipts and containing
typed controls/lineage; freshly observed metadata/hashes never become expectations.
Ordinary source/code/config/review/history objects remain unpaired nlink1.

Scratch observation retains the original descriptor for each admitted object,
full immutable expected fingerprints (including directory mtime/ctime/size/nlink),
finite directory names and budget counts through sync/alias/final-FD checks.
Names are enumerated incrementally, not unbounded listdir/set; reject >1024 admitted
objects or depth64 before acquiring further objects. These stricter operational
admission limits do not relax original65536-entry/4096-open-file ceilings.
Every admitted FD closes once; cleanup failures cannot be swallowed or replace an
operation failure. Original and foreign evidence remain, even when rejected.

**This is a conditional multi-observation custody check, NOT an atomic filesystem
snapshot or immutable-current-tree guarantee.** Successful file/directory fsync
means the client observed successful calls for the admitted original objects and
names under this controlled-writer assumption; it does not establish a simultaneous
tree state, server reboot persistence, backup or restore guarantee.

## NFS attribute limitation: newly measured

Fresh synthetic qualification observed same-length altered bytes with unchanged
full named/owned fingerprints. A100-case diagnostic falsely accepted13 scheduled
last-existing-check rewrites; a separate100-case probe retained unchanged times60
cases even after successful fsync and statx FORCE_SYNC. These are client observations,
not proof of physical loss, remote corruption, or exhausted storage. Exact retained
logs are linked in the v5plan; earlier green primitive/candidate evidence is preserved.

Timestamp/size metadata cannot alone prove absence of mutation on this filesystem.
An additional bounded original-FD expected-byte fence is required at paired
publication/open/verification/read boundaries, both durability settings. Aggregates
require an all-held-original-FD final expected-byte phase after existing sequential
pair validations, followed by frozen metadata/named-alias/ancestry checks, without
rebasing expectations. Scratch final held-directory name checks
are required independently of mtime/ctime. These remain finite conditional
observations, not atomic simultaneity or isolation from arbitrary later mutation.
New requirements need implementation/testing; writing them does not close defects.

## Bounds: what can and cannot be asserted

| Property | Required client behavior | Assurance boundary |
|---|---|---|
| Command time |600-second monotonic deadline with owned group stop/reap | No success if cleanup fails; OS/server blocking cannot be called bounded solely by polling |
| Captured output |16MiB stdout/4MiB stderr, concurrent draining and reject excess | Application buffers/captured bytes, not all subprocess disk/network bytes |
| Regular-file reads |8GiB/file and64GiB aggregate observed/read cap, no-follow/nonblocking regular files and pinned ancestry | Bound reads before/during use; not physical disk allocation quota |
| Scratch totals |Reject observed >8GiB/file,64GiB total,65536 entries | Admission/terminal gate, NOT in-flight hard total quota or reserved headroom |
| Observation descriptors |Max1024 admitted objects plus owned ancestry; original4096 ceiling not exceeded | Operational rejection if capacity/custody cannot be established, no exemptions |
| Observation memory/depth |Incremental names, finite records and depth64 | No unbounded preallocation before admission checks |
| Per-file kernel limit |Separate fresh-child RLIMIT_FSIZE probe on Jumbo stopped growth beyond8 synthetic bytes with EFBIG27 | Probe only; not production activation, aggregate quota, descendant isolation or server retention |
| Process count |Original declaration512 unchanged | Not proven enforced by current supervisor or UID-wide RLIMIT_NPROC; do not report it as a passed hard containment limit |
| Available space |Optional fresh metadata observation/failure handling | Free-space report is not a quota/reservation and cannot prevent another writer exhausting it |

Requirements in this table are not declared implemented merely by writing them.
Each needs exact candidate/test/transcript evidence. Current predecessor has six
scratch failures, incompatible application readers and incomplete recovery.

## Recovery and incomplete evidence

Fresh explicit recovery performs zero source/model operations. It needs an outside
authenticated finite receipt catalog and validates complete prescribed physical
pairs, canonical duplicate-free/finite typed control schemas, authority/history/
entry lineage, retained PRE-START scratch and current observed custody/durability.

- Incomplete/mismatched/unknown evidence stays unresolved and untouched.
- Complete pre-start can report readiness for a future separately authorized FIRST
  access only after all controls pass; recovery itself does not initiate that access.
- Any started stage/final without a trusted complete terminal forbids repeated work.
- Complete terminal can report present reconstructed custody, never infer that the
  original invocation returned success. Separately declared terminal raw exception
  needs its own accounting/qualification; it is not generic raw replay permission.

No cleanup/rebuild/reacquisition/same-call recovery or scorer capability follows
from recovery. Caller-supplied digests/SHIP headers alone are not authenticated
independent approval. Original failing invocation still fails, secondary notes kept.

## Explicitly UNKNOWN, not failed and not promised

Server stable storage/write caches; failover/reboot and multi-client isolation;
administrator deletion/retention and backups/snapshot schedule; disaster recovery;
restored inode identities; account/project quotas or reservable headroom. Existing
tests establish neither physical data loss nor exhausted storage. No administrator
contact is planned to resolve these unknowns.

Client contracts/results/manuscript/release must not silently upgrade these into
guarantees. An unchanged future gate requiring a hard bound or persistence/isolation
that clients cannot establish remains BLOCK. Any change to such operational
requirements needs a separate prospective amendment and independent review; this
document does not waive scientific independence, C1/C2 containment or once-only access.

## Approval and activation

Need prospective independent contract SHIP, exact implementation qualification and
authenticated canonical bindings before applicable production use. Plan/primitive/
contract-only SHIP is not whole launch approval. Current entrypoint guard remains
unconditional. No real source/history/authority/payload/scoring/training began.

Source readiness remains unknown; V10 terminal, AMALGUM v3 exposed calibration only.
