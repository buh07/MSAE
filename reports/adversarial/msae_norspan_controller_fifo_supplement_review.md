VERDICT: SHIP
ONE-LINE: Qualify import and FIFO-reader phases separately without attributing old timeouts, relaxing reader deadlines or accepting timeouts as rejection.

BLOCKERS
  - None for the separately proposed synthetic-only phase qualification.

REVISIONS
  - None required before implementation under the stated captured-diagnostics and cleanup contract.

NITS
  - None.

CHECKS RUN
  - Read public docs/plan-msae-norspan-controller-fifo-diagnostics-supplement-v1.md:1-24.
  - sha256sum of that named public supplement -> 2141b456ae6de87fad0e352791e8a0f682e67318af83259d72c0964fa9586e34, matching the requested candidate.
  - Read only public tests/test_msae_norspan_client_boundaries.py:1-35 -> four actual reader variants; existing child imports/setup and reader all share the old3-second subprocess.run timeout at line32.
  - No tests, code edits, real census/status/credentials/source/raw/private/payload reads, acquisition/Git/network requests, model/GPU command or administrator contact executed.

CONTRACT COVERAGE
  - Historical evidence remains truthful -> met prospectively: supplement:3-7 explicitly retains both old timeouts as failures, marks cause UNKNOWN and states that earlier conditional bootstrap attribution is not established.
  - Independent prospective phase qualification -> met prospectively: supplement:9-13 requires one child, bounded30-second imports to a single flushed READY immediately before the unchanged reader, then unchanged3-second reader completion with actual GateFailure. Missing READY, wrong return or either timeout fails.
  - No retries or masking -> met prospectively: supplement:14-17 requires owned kill/reap, pipe cleanup and no timeout-as-rejection. The child and chosen reader are not replaced after failure.
  - Captured diagnostics -> met prospectively: supplement:9,13 requires captured stderr. The coordinator's explicitly reviewed alternative is an exclusive fresh synthetic stderr file, retained even on failure, inspected after child termination using at most1MiB+1 and rejected on overflow. This bounds admitted/loaded diagnostics, NOT disk allocation or a kernel/server quota.
  - Synthetic custody and exact successor qualification -> met prospectively: supplement:17-24 confines paths/repos to fresh synthetic fixtures, preserves old49/root/independent results, freezes the exact changed public harness and plan, requalifies all four readers, and preserves unconditional guards/no real operations.

UNKNOWNS
  - Use an absolute monotonic bootstrap deadline starting at Popen return. A single select using remaining time followed by one bounded64-byte exact READY read is a sound fail-closed implementation; partial/extra/EOF markers fail rather than accumulating unbounded bytes or resetting the deadline.
  - READY must follow all imports/setup, be emitted once as a flushed/atomic marker, and precede the same actual reader with no additional imports/setup. The parent must begin the3-second operation wait immediately after valid READY, without retry or deadline reset.
  - DEVNULL does not satisfy the document's captured-stderr contract. For the approved file alternative, explicitly retain and report timeout phase/return plus bounded diagnostics; overflow is failure and the full synthetic file remains evidence. No bounded-disk-allocation claim follows.
  - Explicit finally cleanup must kill a still-running owned child, reap it, and close stdout/stderr-file handles exactly once on success, missing READY, both timeout phases, invalid exit, allocation/selection/read errors and interruption. Secondary cleanup failures must not replace the primary failure or yield success. Avoid relying on context-manager implicit duplicate closes.
  - Actual executable green evidence for all four variants, invalid/missing readiness, bootstrap/reader timeouts and cleanup is still required. The prospective harness change does not prove the historical failures were caused by cold imports.
  - This verdict does not grant production I/O/process containment, hard resource bounds, scientific scoring or launch authority.
