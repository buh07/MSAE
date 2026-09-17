# NORSPAN containment preflight wave 1 v2 — prospective launch supplement

2026-09-17. DRAFT successor, NOT LAUNCH AUTHORITY until exact independent plan and implementation review.
Initial wave1 plan and its BLOCK report remain immutable; this distinct v2 fixes literal migration framing and runtime identities, and strengthens startup-failure handling.

## Goal and scope
Advance Stage1 with bounded, synthetic **D1a/D2a preflights**, not the unimplemented
fork-family, escape-control or full bubblewrap arms in the parent availability plan.
An unavailable prerequisite is an explicit result, not permission to broaden privileges.
The user approved continuation, NOT production qualification or final scientific access.
The parent draft/review remains unchanged. This document explicitly narrows the active
slice: no target fork, subprocess, network, production code import or scientific access.
The coordinator may create one parked Python child per arm; the child never forks.
If preflights succeed, stop at AVAILABLE_PREREQUISITE_ONLY; D1b fork/escape and D2
bubblewrap launch remain separately gated on lifetime-stable descendant qualification.

No production implementation, original protocol/config/TODO/V10, keys, real history,
source/raw/private/payload/scoring/GPU/tmux/K2/G3/C2 access. Never execute the legacy
preparer test. No administrator contact, sudo, systemd, existing-group changes,
ancestor writes, existing process migration, host fallback or destructive cleanup.
All disk evidence lives in a fresh Jumbo tmp/lisplab1 root. At most TWO new exclusive
kernel cgroup leaves may be intentionally retained, with identities and member state.

## Grounding and alternatives
The parent draft requires exact launch supplements. Public runtime:require_whole_qualification
is FIRST/unconditional. Writable delegated user@516097.service advertises pids; the
current session is outside it, so common-ancestor migration remains unknown.
Full bwrap helpers/fork trees are deliberately NOT launched because their cleanup is
not yet qualified. A single no-fork userns syscall gives useful availability evidence
without pretending to have reviewed that unresolved tree. No production sandbox is
selected here; DES-0203 Jumbo topology and reviewed client-only v3 limits are preserved.

## Exact subjects / commands / dependencies
Create only scripts/msae_norspan_containment_preflight.py and
 tests/test_msae_norspan_containment_preflight.py, plus public evidence/status bindings.
The CLI has no general command runner. Child argv is exactly:
 /usr/bin/python3.12 -I -S -B <exact frozen public script> --child <cgroup|userns> <parent-pidfd> [<original-leaf-cgroup.procs-fd>]
Parent-child environment is exactly PATH=/usr/bin, LC_ALL=C. close_fds=True; pass_fds
contains ONLY the parent pidfd and, for D1a, one held original leaf cgroup.procs FD.
Stdin is a fresh pipe; stdout/stderr are fresh pipes; no project/history/private/keys
or directory FD inheritance. Script uses only Python public stdlib and root-owned
ELF runtime libraries. Freeze script and finite public runtime hashes/identities before
active launch; unexpected writable/non-root dependency blocks. Dynamic loader behavior
is ordinary host behavior, NOT content/network sandboxing. No LD_* inherited.

Public runtime identity subjects: /usr/bin/python3.12; resolved /usr/lib/python3.12;
/usr/lib/python3.12/encodings; /usr/lib/python3.12/lib-dynload/_ctypes.cpython-312-x86_64-linux-gnu.so;
_struct is an interpreter built-in, not an extension path;
resolved libm.so.6,libz.so.1,libexpat.so.1,libc.so.6,ld-linux-x86-64.so.2,libffi.so.8.
Freeze exact resolved names. Include root-owned /etc/ld.so.preload, /etc/ld.so.cache
and resolved /usr/lib/x86_64-linux-gnu/nosetxattr.so, because host loader preload
is active independently of the environment. Record the exact preload bytes; no claim
that minimal environment removes it. Capture the finite public imported stdlib source
and existing corresponding cached bytecode paths from a fresh source-only import
manifest; freeze those root-owned identities/bytes too, never crawl whole directories.
The interpreter stdlib/encodings directories are identity subjects, not byte attestations
of every descendant. Fail if the imported finite closure is missing or unexpected. No bwrap mounts in this slice.
Future full D2 mount allowlist must be separately frozen/reviewed, with no host root,
Jumbo/home/project/cgroup/protected binds or permissive namespace flags.

## Lifetime / phase / resource contract
Coordinator must be single-threaded with default SIGCHLD and no external reaper.
Open an original pidfd for coordinator BEFORE Popen; child first establishes
PR_SET_PDEATHSIG=SIGKILL then polls that inherited original parent pidfd. A parent
that died before prctl is detected through the pidfd: no GO or syscall is allowed.
After prctl any parent death kills this no-fork target. PID/start checks and groups
are NOT authority. Parent obtains a target pidfd while its direct unreaped Popen
child is parked; single-thread/no-external-reaping preserves that child's lifetime.
Child performs no declared diagnostic syscall before exact READY then GO framing.
Use a fresh per-invocation nonce in both exact frames. Partial EOF, wrong/extra GO or
pre-GO result/bytes reject. No normal payload write precedes GO. Parent signals
only through original target pidfd; waits/reaps only its original Popen child.
Never numeric kill, process-tree scans, adopted foreign handles or repeated initiated operations.
A Popen startup/pidfd-acquisition failure is BEFORE GO. Close the owned input pipe:
the exact parked child must exit on EOF without performing a diagnostic. Reap the
original unreaped Popen child with cleanup5s; no Popen.kill/terminate/os.kill fallback.
If cooperative EOF exit cannot be verified, explicitly retain incomplete cleanup/BLOCK
and stop all arms; do not claim successful release, signal a numeric PID or retry.
No external thread/reaper is allowed to release/reuse that direct-child identity.

Separate monotonic setup30s, command10s, cleanup5s; partial output never resets clocks.
Combined stdout+stderr limit1MiB (+one observed overflow byte). Nonblocking concurrent
read and exact one-record framing; extra output/objects/early result are rejected.
The no-fork child performs at most one declared operation and exits. Timeout/malformed/
setup failure closes stdin and, ONLY when an original target pidfd was acquired,
pidfd-SIGKILLs and reaps that owned child; missing-handle cleanup uses the explicit
cooperative-EOF/BLOCK path above, never an unconditional release promise. Cleanup faults
preserve the primary and report incomplete cleanup (BLOCK); never cleanup-success
on unproven release. Secondary close/reap errors are retained. OS-uninterruptible
waits are not claimed universally bounded. Evidence roots and kernel nodes retained.

## D1a — setup / self-migration only
Use ONLY /sys/fs/cgroup/user.slice/user-516097.slice/user@516097.service.
Bind original delegated-directory identity/UID/mode and cgroup2 mount from public
/proc/self/mountinfo; expected owner516097. Open with O_DIRECTORY|O_NOFOLLOW.
Create TWO fresh leaves named msae-norspan-preflight-<nonce>-a/-b, once each, through
that held parent FD. Record every mkdir/open/write/read result, leaf inode identity,
original control identity and initial members. Never reuse a name or discoverlatest.
Set pids.max with exact bytes hex34 0a once per leaf and read back. All writes
check exact return lengths and retain partial-write errors; do not retry partial writes. Unexpected membership/control
identity or permission failure stops; partial nodes are retained, not retried/deleted.
Open original leafA cgroup.procs O_WRONLY|O_NOFOLLOW with held leaf directory FD.
Park exactly one child; on GO it writes exactly the TWO bytes hex **30 0a** (Python literal b"0\n") to the transported original
control FD once (SELF migration), reporting errno or current /proc/self/cgroup.
Check leaf identities/current members and exact original child reap; both leaves
must have no members after reap, else BLOCK. A denied write is UNAVAILABLE_SELF_MIGRATION
and stops D1. A successful write is AVAILABLE_PREREQUISITE_ONLY, not pids-enforcement
or escape qualification; no fork, escape, pids512 or ancestor claim in either result.
Controlled-writer assumption: no other task may intentionally mutate these nonce
leaves or reassign the parked child; observations detect some interference, not all
concurrent writers. No exclusivity proof is inferred from nonce, inode or UID.
Same-UID namespace exclusion is NOT proved; unexpected replacement/content/members
blocks, and no failed initiated operation is retried. No pathname deletion.

## D2a — mandatory userns prerequisite, no helper tree
After clean owned-process/FD restoration of D1a (intentional leaves excluded), launch
one distinct parked no-fork child. On GO invoke libc unshare(CLONE_NEWUSER) once.
Report syscall return/errno and own namespace handle before/after only. No UID/GID map
writes, other namespaces, bwrap/unshare command, fork, mount, socket or connection.
EPERM/EACCES/ENOSYS are UNAVAILABLE_USERNS_PREREQUISITE; other failures BLOCKED_UNKNOWN.
Success is AVAILABLE_PREREQUISITE_ONLY; it does not launch full D2 or qualify isolation.
No denied operation is retried; there is NO host fallback for a namespace payload.

## Milestones / acceptance / review
1. Independent plan SHIP before implementation. Write test-first requirement failures.
2. Implement exact no-fork harness and fixtures. Synthetic tests cover setup allocation,
   FD-acquisition/selector setup, pre-GO bytes, malformed/extra output, bounded deadlines,
   output cap, kill/reap/close primary+secondary failures and actual FD reuse.
3. Real killed-coordinator fixture: a separately owned fixture coordinator launches a
   parked child and is killed via its original pidfd; original target pidfd reaches
   exit with no operation. Fixture cleanup retains original handles/no numeric kill. A dedicated fixture
   process (never the existing coordinator/pytest process) may mark itself child-subreaper
   and use a fresh anonymous AF_UNIX socketpair solely to transport the ORIGINAL target
   pidfd using SCM_RIGHTS. It adopts/reaps only its fixture family after killing the
   fixture coordinator; no global tree scan or original process migration. Test early
   parent death before prctl as well as parked-after-READY parent death. Fixture-only
   forks/transports are not scientific D1/D2 operations and have their own exact tests.
4. Independent exact implementation review before real cgroup/userns syscalls. Freeze
   source/runtime/argv/evidence identities; do not include test keys/private artifacts.
5. Run D0 then D1a/D2a once under accepted subjects and command; no retry. Independent
   evidence audit. Outcomes recorded separately from full containment/whole approval.
6. Keep full9-group/80-row status OPEN and production guard unchanged. Update synthesis
   and handoff with exact tests/results/blockers. A public-only checkpoint can be
   consolidated; never stage actual protected artifacts or rewrite older reviews.

Definition of done for THIS slice: causal tests and independent scoped review; at
most two retained fresh leaf nodes; each attempted syscall/child phase has recorded
identity/result; no foreign/ancestor/existing-task changes; no false full containment
or scientific authority. Success is bounded engineering progress, not Stage1 closure.

## Stop conditions / later stages
Missing pidfd/prctl support, nondefault SIGCHLD, multiple coordinator threads,
unknown runtime, unstable identities, unexpected members/bytes, allocation/deadline/
cleanup error -> BLOCK affected arm; D2 only after verified clean owned baseline.
If either prerequisite succeeds, implement/review the unresolved full arm separately,
not on this launch authority. Whole implementation/canonical FINAL owner receipt,
independent source->sealed payload->reviewed C1->justified G3->conditional training->
once-only C2->release remain mandatory. Generic user approval never manufactures a
FINAL exact receipt or waives technical qualification. Earlier BLOCK/REVISE remain.
