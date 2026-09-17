# Jumbo storage facts needed before production approval

This is an unsubmitted administrator handoff, not a claim that storage was
provisioned or approved. The experiment must remain on Jumbo (DES-0203).
No administrator privileges, mounts or migration were attempted.

Observed mount: `/jumbo/lisp`, NFS4.2 export
`jumbo.thayer.dartmouth.edu:/mnt/storage/lisp`, client `lisplab1`.
Canonical project: `/jumbo/lisp/f004ndc/experiments/wip/MSAE`.
The current client reports EINVAL for `renameat2(RENAME_NOREPLACE)`; ordinary
exclusive create, no-replace hardlink and file/directory fsync succeed in synthetic
same-client probes. Those probes do not establish server crash persistence.

Please establish, for this export **or a compatible volume mounted beneath the
same Jumbo topology**, the following written facts:

1. Exact durable path/mount/export/underlying filesystem identity, supported
   clients, account/ACL ownership and whether hardlinks or no-replace rename have
   documented limitations. No off-Jumbo canonical placement is acceptable here.
2. File-fsync, directory-fsync and NFS COMMIT/stable-storage semantics, server
   failover/reboot guarantees, and any write-cache or directory durability caveat.
3. Account/project quota and reservable headroom, not just whole-export free space.
   A prospective contained run has a 64GiB total-output cap; required storage also
   includes frozen inputs, retained failed runs/checkpoints and snapshots. Branch
   training footprint cannot be fixed before its scientific branch/runtime plan.
4. Retention and snapshot/backup schedule, expiration/deletion authority, recovery
   procedure, expected recovery-point/time limits and ability to preserve/recover
   original sealed identities/bytes without overwriting retained failed evidence.
5. Whether a second independent client and administrator-led safe synthetic
   failover/reboot test are available. No real payload or destructive production
   crash test should be used to establish these guarantees.

Preferred compatible-volume route, if provided: freeze the exact Jumbo paths,
identities, modes, quota, retention and recovery; independently review; run fresh
synthetic file/directory durability and no-replace tests on actual destinations.
Changing TMPDIR alone is not storage approval.

Alternative currently under source-free review: JPC-1 permanent stage/final
hardlink pairs on the existing export, exact nlink2 and original-FD/manifest custody,
no unlink/rename fallback. This is a prospective **protocol amendment**, not a
storage repair or runtime fallback. It still requires complete paired production
integration, full fault-matrix qualification, whole approval and exact canonical
authority; administrator unknowns above remain explicit. If reviewers require
unavailable storage evidence, keep the production launch stopped.

Local observations, tests and limits:
[Jumbo qualification status](status-msae-norspan-jumbo-qualification-2026-09-16.md).
