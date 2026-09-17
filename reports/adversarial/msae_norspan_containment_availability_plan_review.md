VERDICT: SHIP
ONE-LINE: The revised draft is safe planning only; exact active probes still require independently accepted launch supplements.

BLOCKERS
  - None for further documentation/specification under this revised draft. This is NOT launch-ready implementation approval.
REVISIONS
  - None beyond the review-driven amendments now present.
NITS
  - None.

CHECKS RUN
  - Read the explicit public containment-availability draft before and after amendments. Final reviewed SHA256: eb1ec43825e8c36b1302224723661094823998807811d2e3b1a58e888bec2a28; mode0644.
  - Bounded public source inspection of runtime.py:49-57, prepare.py:1595-1603 and controller.py:409-412 confirms the unconditional guard and unchanged UNVERIFIED helper/protected-content/network disclosures.
  - No tests, imports, probe children, cgroups/namespaces/systemd/GPU, protected reads, real census/status/Git, network or system mutation. Only this distinct0644 report was created; marker-wave plan/review and frozen67 subjects were not changed.

CONTRACT COVERAGE
  - Safe staging versus active launch → met as draft. Plan:3-4,43-44,144-150 requires independently reviewed exact supplements before active arms, including lifetime-stable descendant cleanup and runtime mounts. This SHIP accepts planning/specification, not unspecified command execution, a production architecture or hard-bound proof.
  - Migration permissions/PID reuse → met as future constraints. Plan:27-33,63-72 no longer presumes fresh-leaf writability permits cross-ancestor migration. Required child self-migration via original cgroup.procs descriptor and value0 avoids parent numeric-PID check-then-act migration. Denial stops the arm; existing processes/coordinator/ancestor controls cannot be moved or changed.
  - Same-UID negative control and initiated-failure sequencing → met prospectively. Plan:73-85,111-117 permits a second, distinct escape control only after positively attributed pids-limit evidence and restored first-family resources. Expected kernel fork rejection is diagnostic success, not an operational failure. Ambiguous setup/resource/cleanup failures block that control; no initiated retry or denied-escape isolation claim. Fresh D2 requires a clean owned process/FD baseline.
  - Foreign-resource deletion and retention → met after amendment. Plan:118-125,130-134 forbids all rmdir/pathname deletion and retains at mostTWO fresh kernel leaves, explicitly reporting incomplete kernel-resource release. This removes the original identity/emptiness-check-versus-same-UID-replacement deletion race without claiming those checks are atomic.
  - Descendant/resource safety → partial, deliberately deferred. Plan:52-55,73-78,107-117,144-150 bounds family growth/deadlines/diagnostics and requires exact lifetime-stable ownership/reaping before any fork. Numeric PID/start checks or process groups alone cannot discharge this requirement. Failure/secondary cleanup errors remain evidence, not success.
  - Sandbox host dependency/privilege leakage → met as required staging constraints, exact execution unresolved. Plan:36-42,87-105 rejects permissive namespace flags, host fallback, privilege escalation, systemd/ancestor changes and broad root/Jumbo/home/project mounts. Exact read-only public runtime dependencies, sanitized environment/FD transport and mandatory namespace argv require a separately frozen/reviewed allowlist. Syntax availability and namespace IDs alone prove no isolation.
  - Qualification/science boundaries → met as unchanged constraints. Plan:129-150 keeps availability/denial/escape distinct from process512, allocation/FD/disk/helper/network/protected-content/descendant/server qualification, whole9/80 closure and FINAL owner/source/scientific approval. Current production guard remains unconditional.

UNKNOWNS
  - Neither kernel namespace permission, common-ancestor migration permission nor same-UID escape was tested. If denial prevents the negative control, escape/isolation stays UNKNOWN, not disproven or qualified.
  - Exact supplements must freeze scripts/argv, transitive runtime dependency and symlink targets, held control authority, monotonic phase framing/overflow behavior, FD inheritance and lifetime-stable kill/reap supervision, including killed-supervisor and cleanup-error fixtures. No probe may start on this draft/report alone.
  - Identity/member checks do not exclude arbitrary same-UID concurrent writers. Future active-arm safety must state its controlled-writer assumptions and response to unexpected members/control changes; do not upgrade monitoring into atomic ownership/isolation.
  - Intentional kernel-leaf retention is bounded diagnostic state, not full cleanup PASS or permission for repeated fresh runs accumulating leaves. Future removal/rerun needs separate prospective review.
