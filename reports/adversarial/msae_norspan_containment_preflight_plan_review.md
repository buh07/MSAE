VERDICT: BLOCK
ONE-LINE: Fix the migration bytes, impossible runtime identity and missing-pidfd cleanup branch before accepting this exact preflight supplement.

BLOCKERS
  - [high] docs/plan-msae-norspan-containment-preflight-wave1.md:84-88 — The exact declared Python literal is b"0\\n": the file contains bytes 30 5c 5c 6e between its quotes, not one escaped newline.
    reasoning — That literal emits 30 5c 6e, not the required decimal self-PID followed by newline. The declared cgroup write therefore does not implement the parent plan's self-migration operation, and its rejection cannot establish migration permission availability.
    impact — D1a can produce a malformed-operation result rather than the promised prerequisite diagnostic. The once-only/no-retry contract makes fixing this after launch too late for this run.
    fix — Specify exact transmitted bytes hex 30 0a, with Python literal b"0\n"; require an exact-byte fixture and reject short writes without retrying.
  - [medium] docs/plan-msae-norspan-containment-preflight-wave1.md:40-49 — The mandatory _struct.cpython-312-x86_64-linux-gnu.so identity path at line 46 is nonexistent. The finite ELF list also omits the host's configured /etc/ld.so.preload and resolved nosetxattr.so; an empty inherited LD_* environment does not disable that configuration.
    reasoning — Bounded stat returns ENOENT for the named _struct extension. Exact public /etc/ld.so.preload contains /usr/${LIB}/nosetxattr.so, with a root-owned resolved /usr/lib/x86_64-linux-gnu/nosetxattr.so present. Ordinary host-loader behavior is expressly permitted, but its actual dependency identity must be included in the promised finite freeze rather than silently omitted.
    impact — The exact mandatory runtime manifest cannot freeze as written, and its proposed finite identities do not account for an observed loader dependency.
    fix — Record _struct's actual built-in/module classification, removing the fictitious file subject; freeze the exact preload configuration, loader cache and resolved preload object alongside the finite interpreter/ELF/imported-source-or-pyc closure. Do not substitute a directory crawl or claim this is content/network containment.
  - [high] docs/plan-msae-norspan-containment-preflight-wave1.md:59-70,104-106 — The parent acquires its target pidfd only after Popen, yet every setup failure is specified to pidfd-SIGKILL and reap that child. The explicitly required FD-acquisition fault case can occur before a target pidfd exists.
    reasoning — If target pidfd acquisition fails after successful child creation, the original parent pidfd is not authority to signal the target. Direct unreaped-child custody makes original-child wait/reap safe, but does not manufacture the missing target pidfd. Numeric kill, adopting another handle and retrying an initiated operation are forbidden by the same plan.
    impact — The universal setup-failure cleanup recipe has an undefined branch that could strand a live owned child or tempt an impermissible fallback; general secondary-error recording does not define the permitted missing-handle actions.
    fix — Specify this branch prospectively: close stdin, bounded-wait/reap only the original Popen child, preserve the acquisition failure, and if the child remains live record missing signal authority/incomplete cleanup as BLOCK and prohibit D2 or any additional launch. An atomic original-target-handle acquisition design is another option, but requires its own exact review. Add a causal fixture where Popen succeeds, pidfd acquisition fails and EOF does not promptly terminate the child.

REVISIONS
  - [medium] docs/plan-msae-norspan-containment-preflight-wave1.md:78-91 — Same-UID namespace exclusion is expressly unproved; identity/member observations are detection, not an atomic fence against another writer inserting a task between an empty-membership check and pids.max mutation.
    reasoning — Held directory/control descriptors bind original created objects and avoid pathname adoption/deletion, but cannot exclude concurrent same-UID membership/control writes to those objects.
    impact — The no-foreign-task-change statement needs a stated controlled-writer premise, not an implication that after-the-fact checks establish exclusion.
    fix — State the diagnostic's single controlled coordinator/no concurrent external leaf writers assumption and retain immediate BLOCK on observed replacement, unexpected members or control changes. Do not upgrade that assumption or monitoring into production isolation.

NITS
  - None.

CHECKS RUN
  - Read the exact explicit plan, parent availability draft and its existing public planning review; no workspace backend or active plan resolver was required for this literal-path review.
  - sha256sum of reviewed initial plan → 429dce98de195190c0466c00e2e6e1d2d3a8e2d2a3c0fe2d4228fab48f683572; rechecked unchanged before report creation.
  - sha256sum of parent plan → eb1ec43825e8c36b1302224723661094823998807811d2e3b1a58e888bec2a28; parent planning review → 31a39af84510544c06e4661e28f488bb7870b057629a26a66af4e40e9687ae92.
  - sed of the exact line 84 piped to od → confirms two literal backslashes in the Python bytes literal.
  - Bounded stat of exactly named public interpreter/_ctypes/_struct runtime subjects → interpreter and _ctypes root-owned; named _struct extension ENOENT.
  - cat of the exact public loader preload config and bounded stat of it, ld.so.cache and the resolved nosetxattr.so → configured preload present; all three subjects root-owned mode0644.
  - No active probes, child launches, imports, tests, process/history/protected-source scans, cgroup/namespace/systemd/GPU operations, network or production changes. Only this distinct mode0644 report was created; no older artifact was changed.

CONTRACT COVERAGE
  - Prospective independent staging → met as workflow, not launch authority; lines 3,103,110-113 require separate exact implementation review/freeze before real cgroup/userns operations.
  - No-fork D1a/D2a slice and scientific limits → met prospectively; lines 6-18,88-100,114-131 stop at AVAILABLE_PREREQUISITE_ONLY and keep full arms, Stage1/whole9/80, production guard and scientific receipts separate.
  - Lifetime-stable parent/target custody → partial; lines 54-63 explicitly require original parent pidfd before launch, PDEATHSIG before READY/GO and original direct-unreaped target acquisition, but the missing-target-pidfd branch needs the blocker fix.
  - Externally owned killed-coordinator fixture → met as a required implementation acceptance case, not executed; lines 107-109 require killing only the fixture coordinator through its original pidfd and observing the original parked target pidfd exit without an operation. Exact fixture handle acquisition/transfer and orphan cleanup remain implementation-review obligations.
  - Fresh leaf creation/control custody/retention → met prospectively subject to controlled-writer assumptions; lines 75-91 bind cgroup2/delegated directory, create at most two nonce leaves through its held FD, transport only original leafA control and prohibit reuse/retry/deletion. Both leaves' post-reap empty membership is required, with partial nodes retained.
  - Exact self-migration operation → unmet in the reviewed artifact; line 84 specifies incorrect bytes. Denial classification must apply to the corrected operation, not malformed requests.
  - Mandatory no-helper-tree userns prerequisite → met prospectively; lines 93-100 limit one owned child to one libc unshare(CLONE_NEWUSER), no map writes or helper/fork/mount/socket/network fallback and explicitly nonqualifying outcomes.
  - Framing/deadlines/output cap/secondary failures → met as testable requirements, not verified behavior; lines 61-72,104-109 specify READY/GO, separate fixed monotonic budgets, concurrent nonblocking bounded output, malformed/extra-output rejection and primary-preserving BLOCK on incomplete cleanup.
  - Runtime/environment/FD freeze → partial; isolated interpreter flags, exact minimal environment and narrow pass_fds are specified, but the observed manifest defects prevent exact accepted runtime subjects.
  - Causal tests and independent evidence audit → pending by design; no tests or evidence probes were run, and neither this plan review nor later prerequisite success closes containment/Stage1.

UNKNOWNS
  - Kernel cgroup permission, migration permission and userns availability were not tested and remain UNKNOWN.
  - Actual finite imported-source/pyc and transitive ELF closure, frozen script/argv/evidence identities, selector/FD-reuse fault behavior and cleanup error handling require the exact implementation review.
  - This review did not independently read production guard source; unchanged guard status remains a stated constraint supported by the existing parent planning review, not a new source audit here.
  - No same-UID concurrency exclusion, universal scheduling/uninterruptible syscall bound, full descendant safety, bubblewrap isolation or scientific authority is established.
