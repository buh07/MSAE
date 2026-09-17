# Prospective no-admin containment availability diagnostic v1

2026-09-17. **DRAFT: no active probe is authorized by this document alone.**
Independent prospective SHIP is required before implementation or system mutation.

## Goal / non-goals
Determine, using only fresh synthetic children, whether this current Jumbo session
can use delegated cgroup leaves and mandatory bubblewrap namespaces; demonstrate
why mere same-UID writable membership is not descendant containment. This is an
availability/negative-control diagnostic, NOT a production sandbox choice, process512
qualification, scientific experiment, full security proof or hard disk quota.
No production code/guard, canonical approval, original protocol/config/TODO/V10 or
scientific artifact changes. No real history/status/source/raw/private/keys/payload/
scoring/GPU/tmux/K2/branch/G3/C2. Existing experiments, tasks and service limits must
not be disturbed. All persisted files remain under fresh Jumbo tmp/lisplab1 roots.

## Grounding / design clarifications
Design query for NORSPAN hard helper/descendant containment returned no match;
DES-0203/0221 retain Jumbo topology. bin/query refs require_whole_qualification with
the literal public runtime path refuses the undeclared nested MSAE repository;
public source-only inspection confirms the guard remains unconditional and helper
containment unqualified. No production architecture or proof semantics are selected.
Low-risk assumption: bounded source-free availability probes are useful even when
permissions deny every operation; denial is a recorded unavailable outcome, never
an invitation to relax isolation or contact administrators.

Read-only facts already retained at marker-wave planning pointer: root-owned current
session cgroup with no finite pids.max; writable delegated user@516097.service with
cpu/memory/pids controllers. Current common-ancestor migration permission is unknown;
new leaf writability MUST NOT be presumed sufficient to move a session child.
Installed /usr/bin/bwrap and unshare are root-owned, non-setuid; no file capabilities
reported. Local bwrap help advertises explicit user/pid/net/cgroup namespaces and
--disable-userns. This establishes syntax availability, NOT actual kernel permission.
No cgroup limit/membership or namespace mutation has happened yet.

## Approach / alternative
Two independent, opt-in synthetic probes, recording operation results/errno and
bounded child observations. Prefer explicit failure over permissive '-try' namespace
flags, fallback to the host, extra privileges or changing ancestor controllers.
Do not use systemd-run, start/modify a user service, move an existing process, alter
ancestor subtree_control/limits, use sudo/root, contact administrators, reboot, run
network traffic or bind the real project/home/Jumbo tree into a sandbox.
A draft cannot solve a denied common-ancestor permission or sandbox architecture;
record that outcome and propose a separately reviewed solution only afterward.

## Milestones / verification
D0. Revalidate exact paths, inode/owner/modes, controller and ancestor permissions,
self membership, binary versions/help and live process/thread/FD baselines. Save only
these system facts and numeric synthetic observations. No directory crawling/private
reads. Record exact executable/script bytes and every command before execution.

D1. Cgroup probe, at most ONE attempt per named operation. Separate monotonic
setup30s, each command/fork phase10s, cleanup5s and combined diagnostic1MiB+1 budgets;
phase deadlines never reset by partial output. These are harness budgets, not proof
of universal descendant cleanup or hard kernel allocation bounds:
- Create exactly two fresh, exclusive named leaf directories under the existing
  delegated user service, never an existing group or nested service. Name includes a
  recorded random nonce; capture original inode identity before any write. Verify
  expected control names and empty membership. Never change ancestor controls.
- Set both leaves pids.max=4 and read back; no CPU/memory pressure test in this scope.
  If unsupported, permission denied or unexpected identity/members, stop cgroup arm
  and retain BLOCK/unavailable metadata; no fallback/retry.
- Launch exactly one owned Popen parked until GO. The exact supplement must use
  child SELF-migration (write cgroup.procs=0 from that child), not parent writes of a
  check-then-act numeric PID that could be reused. Only fresh-leaf original control
  descriptors may be explicitly transported in this D1 arm; bind/check the kernel
  filesystem and original file identity, sanitize all other inherited descriptors.
  Named/descriptor and before/after membership observations are not an atomic
  same-UID replacement fence. If original identity is ambiguous, stop before write.
  If self-migration is denied (including common-ancestor EACCES), kill/reap only this
  owned child, release descriptors and stop this arm. Never move the coordinator,
  unrelated process or preexisting manager. No PID-reuse safety claim from stat checks.
- If admitted, the child attempts at most5 additional single-threaded forks, with a
  harness absolute family ceiling6 and no repeated fork after failure. Children park
  with parent-held cleanup identities. Record pids.current/max/events, fork errno,
  RLIMIT_NPROC and member identities. Evidence must distinguish genuine kernel pids
  rejection from unrelated RLIMIT/resource/setup failure. Kill/reap all child-owned
  descendants using their exact recorded identities; record baseline restoration.
- Negative escape control only after first family is reaped: a second owned parked
  Popen self-migrates into leafA once, then the same-UID child tries to move ONLY itself
  into fresh leafB (its own cgroup.procs=0 write via the original control descriptor). Both leaves remain pids.max=4; no write
  to existing ancestor cgroup.procs. If it succeeds, record escape from leafA; this
  blocks a claim that leafA alone is descendant containment. If denied, record the
  specific denial; do NOT infer universal isolation. No arbitrary escape/flood loop.
- Never expose a writable new cgroup to real producers. No process512 claim.

D2. Separate mandatory namespace availability probe:
- Exact bwrap argv, sanitized environment, close_fds, no inherited project/directory
  FDs, bounded stdin/stdout/stderr, parent-owned process group and killed-parent
  semantics. Deadline30s setup +10s command +5s cleanup, total diagnostics1MiB+1.
- Explicit --unshare-user/--unshare-pid/--unshare-net/--unshare-ipc/--unshare-uts,
  --disable-userns, --new-session and --die-with-parent, never *-try or --share-net.
  A fresh mount root exposes only read-only public interpreter/runtime dependencies,
  a fresh synthetic /work, private /proc/dev and tmpfs /tmp. No /sys cgroup binding,
  host /proc, host home, Jumbo project, credentials or actual payload. The exact
  minimal public runtime dependency allowlist must be frozen/reviewed before launch;
  do not bind '/' or '/jumbo' as a shortcut. If minimal runtime cannot execute, record
  unavailable and stop; do not silently broaden the mount list.
- Run a finite public script returning IDs of its own namespace handles, UID mapping,
  proc PID visibility and synthetic-only write/read observations. No connections,
  socket traffic or inspection of foreign processes/protected paths. Network namespace
  identity alone does not establish all network/IPC/FD/protected-content containment.
- Denied namespace/mount/disable-userns support is an unavailable outcome, not PASS
  or authorization to run on the host. Exact helper code/runtime/attack suite needs
  a new production design/review if this diagnostic motivates one.

D3. All-path resource/recovery and evidence:
- Every live owned child has independent monotonic kill/reap and pipe/selector cleanup;
  setup/malformed/timeout/foreign-resource substitutions remain failed retained cases.
  Cleanup errors preserve primary and append secondary notes, not false success.
- A positively attributed expected kernel pids-limit fork rejection is successful
  diagnostic evidence: stop further forks, reap/restore the family, then negative
  escape control may proceed. Permission/setup/unrelated-resource ambiguity or
  incomplete process/descriptor cleanup BLOCKS that control. No initiated failure
  is retried; fresh D2 is independent only after a clean owned process/FD baseline.
  Never guess/adopt/discover a new child/cgroup. PID/start observations support
  custody but do not eliminate numeric migration/kill check-then-act races.
- Persist original cgroup identities/control values/member observations and syscall
  results. Retain the at-mostTWO fresh kernel leaf nodes, including failed partial
  setup, as explicit bounded diagnostic resources; NO rmdir or pathname deletion in
  this scope. Check-then-act identity/emptiness cannot atomically bind rmdir against
  same-UID rename/replacement. Report retained original paths/identities/member state
  separately from process/descriptor cleanup; never claim full kernel-resource release.
  A later removal needs separately reviewed original-authority/concurrency assumptions
  or a safe mechanism; ambiguity means retention, not foreign deletion/retry.
- Independently review retained numeric observations and exact fixture fault tests;
  report availability/denial/escape separately from containment qualification.

## Definition of done / remaining obligations
Every attempted operation has an exact prospective command/path and recorded result;
no foreign/group/ancestor or existing task is altered; owned processes/descriptors
are restored or an explicit retained failure blocks the affected arm. At mostTWO
fresh kernel leaf nodes intentionally persist and are reported, not cleanup-PASS. Unexpected writes/member identities
stop the affected arm; no failed initiated diagnostic is silently retried.
The result can be AVAILABLE, UNAVAILABLE or BLOCKED/UNKNOWN, never production SHIP.
Full allocation/disk/FD/helper/network/protected-content/descendant adversarial
qualification, server guarantees and the complete9/80fault matrix remain separate.
User FINAL approval and source→payload→C1→G3→conditional branch→C2→release gates stay
unchanged. No owner/admin response is needed merely to record a denied synthetic probe.

## Risks / stop criteria / one-way doors
Kernel/userns rules may deny all probes. Same UID can write ancestors or create
alternate namespaces; a positive availability result is not a security boundary.
A killed supervisor might strand a child; before any fork, the bounded owned family
must have independently reviewed lifetime-stable handles/reaping/kill strategy, not
numeric PID/start checks or process-group-only claims. If that mechanism cannot be
established, do not fork. Cgroup node cleanup can race; NO removal in this draft.
No one-way scientific operation and no architecture/canonical decision in this draft.
D1/D2 implementation supplements (including runtime mount list and descendant cleanup)
must be prospectively accepted before their respective launches.
