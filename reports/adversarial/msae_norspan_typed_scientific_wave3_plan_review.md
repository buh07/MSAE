VERDICT: REVISE
ONE-LINE: Fix catalog fault boundaries, independently bound drift objects, and failure-safe causal evidence before implementing these forty cells.

BLOCKERS
  - None asserted against production correctness from this prospective, source-only review. Whole technical approval remains BLOCK.

REVISIONS
  - [high] docs/plan-msae-norspan-typed-scientific-fault-wave3.md:34-44 — “actual post-pair catalog snapshot” does not specify a physical fault operation or ordinal, although every fault must bind an opened original identity.
    reasoning — scripts/msae_norspan_jpc_controller.py:103-135 performs snapshot open, writes, chmod, fsync, copied read, original-FD reads and final fences. Raising at a snapshot wrapper entry can leave no opened snapshot inode; choosing another boundary changes retained physical evidence. CatalogStore.checkpoint advances the producer tuple only after _write_snapshot succeeds (lines 162-175), and CatalogStore.load requires exact physical catalog membership (lines 190-203). An entire snapshot is not a unique causal fault edge.
    impact — Four of the twelve terminal cells lack an unambiguous firing and recovery oracle; a wrapper exception could be counted as actual original-FD catalog evidence.
    fix — Declare the first actual os.write on the newly opened terminal snapshot original FD as the catalog boundary, or name another single exact operation. Match its outside-directory identity and original device/inode, confirm the completed terminal physical stage/final pair, capture the authoritative (path, SHA-256, sequence) immediately before terminal promotion, and assert the returned tuple stays that exact predecessor after failure. Explicit fresh CatalogStore.load must use this tuple without discovery or hashing observed files into new expectations; record load refusal separately from any subsequently reachable recover/prepare refusal. Fix these identities and case IDs before implementation; do not expand the forty-cell count to claim all snapshot operations.

  - [medium] docs/plan-msae-norspan-typed-scientific-fault-wave3.md:27-29 — The “ordinary synthetic history object” is not identified or independently bound to a frozen text expectation.
    reasoning — The existing Fixture constructs its synthetic root from copied, signed approval subjects and a synthetic .git/HEAD (tests/msae_norspan_controller_fixture.py:94-119), rather than declaring a separate ordinary history text object. History's adapters distinguish text/archive from no-read objects; the actual text-drift check uses the registry content digest (scripts/prepare_msae_independent_norspan_v1.py:2002-2014). Merely refusing final success does not demonstrate that this check fired, rather than a different approval, adapter, or custody predicate.
    impact — Both drift cells can be described as causal history-content tests without proving they mutated the claimed history domain or received a history-drift refusal.
    fix — Predeclare an ordinary plain synthetic-history.txt inside the disposable root before authority/history/acquire, outside signed approval subjects and protected/no-read namespaces. Confirm its frozen registry row is text with the original device/inode, mode, nlink, size, SHA-256 and extracted-unit count before interception. At raw ordinal 1 or 3, capture original/new bytes and identity, mutate once, and require an attributable actual history-drift refusal with no successful terminal. Use an unmutated valid control so unrelated fixture failure cannot satisfy the drift oracle; retain the changed object and preserve RED/BLOCK if science instead succeeds.

  - [medium] docs/plan-msae-norspan-typed-scientific-fault-wave3.md:40-44,50-60 — Every cell promises JUnit causal properties and FD restoration, including retained RED outcomes, without requiring failure-safe evidence emission or FD assertions.
    reasoning — The named precedent emits facts only after earlier assertions pass (tests/test_msae_norspan_typed_history_wave2.py:89-105,128-137). A failed firing/pin/refusal assertion can prevent both property emission and the final FD assertion. This is particularly consequential where this plan explicitly requires preserving unexpected success as RED rather than altering expectations.
    impact — A failed cell may have neither inspectable firing/pin/evidence facts nor a checked FD baseline, undermining the promised independent review of RED causality.
    fix — Require failure-safe try/finally or equivalent fixture finalization for all forty cells: capture facts incrementally, emit JUnit evidence and check final FD restoration even when a primary assertion or exception fails, and preserve that primary failure rather than replacing it with an evidence/teardown error. Record FD observations before fixture work, after initiating failure/success, and after explicit fresh recovery/refusal; release only test-owned resources, never delete evidence. Distinguish initiating raw-loader calls from the permitted one terminal raw reconstruction in each positive recovery, and record read/transport counts on failure paths as well as green paths.

NITS
  - None.

CHECKS RUN
  - nl/sed/grep/wc of the one plan and seven expressly named public source files only — static, read-only cross-checks; no imports, collection or execution.
  - Arithmetic inspection: 2 positive + 8 raw-read + 2 drift + 16 private-sealing + 12 terminal = 40 prospective cells.
  - Source inspection: actual raw consumer loop has four OwnedPair.read_bytes boundaries (scripts/prepare_msae_independent_norspan_v1.py:2875,2891-2897); flat custody verification does not add consumer read_bytes calls (scripts/msae_norspan_jpc_runtime.py:395-424).
  - Source inspection: actual private publisher iterates discovery, calibration, C1, C2, with original stage writer and no-replace promotion (scripts/msae_norspan_jpc_runtime.py:33,438-450; scripts/msae_jumbo_pair_commit.py:384-408).
  - Source inspection: production qualification remains unconditional RuntimeBlocked before real inspection (scripts/msae_norspan_jpc_runtime.py:49-57; scripts/prepare_msae_independent_norspan_v1.py:1595-1603; scripts/msae_norspan_jpc_controller.py:251-256).
  - Report persisted separately as mode 0644; no plan, test, fixture or production code edited.

CONTRACT COVERAGE
  - Finite test-only scope and immutable production/frozen76 subjects → met prospectively — plan lines 4-16,48-61.
  - Actual scientific success and license rejection with explicit terminal reconstruction → met prospectively — plan lines 18-20; actual scientific predicates and fresh recovery paths are present in named source, not replaced gate outcomes.
  - Four raw consumer ordinals × two interruption types with no scientific rejection of IO failure → met prospectively — plan lines 21-26; raw load occurs outside the ScientificGateFailure catch (preparer lines 3025-3033).
  - Two causally attributable ordinary history drift cells → partial — unbound object selection and refusal oracle addressed above.
  - Four private role originals × write/link × two interruption types → met prospectively — plan lines 30-33; actual role ordering and original-writer paths present; execution remains unverified.
  - Success/rejection terminal originals × write/link/catalog × two interruption types → partial — catalog's physical operation and exact predecessor/recovery oracle need revision.
  - All-cell causal JUnit evidence, retention, counts and FD restoration, including RED → partial — failure-safe collection/assertion obligation needs revision.
  - No universal exception identity, no close-before-release/descendant/combined-fault qualification → met — plan lines 43-46 explicitly exclude those claims.
  - No new undefined scientific mocks or producer-success adoption → met prospectively — plan requires the existing guarded synthetic Fixture, real loader and real predicates; source has synthetic process/status/Git/storage-placement producers. Their observations do not establish production containment or source authority.
  - Whole nine-group/80-row qualification and launch/scoring/training authority → unmet and OPEN by design, never inferred — plan lines 16,63-65. Whole technical approval remains BLOCK.

UNKNOWNS
  - No proposed wave3 code, cells, exception chains, FD outcomes, JUnit, timings or runtime guarantees were executed or verified. This review authorizes no implementation/run while the plan verdict is REVISE.
  - Existing1172/frozen76 regression claims were not reproduced or audited; they are not evidence for the forty proposed cells.
  - Exact whole approval, canonical binding and FINAL owner receipt remain pending. V10 remains terminal; AMALGUMv3 calibration and later gates receive no authority from this review.
  - Scope was ONLY docs/plan-msae-norspan-typed-scientific-fault-wave3.md, tests/msae_norspan_controller_fixture.py, tests/test_msae_norspan_typed_history_wave2.py, tests/test_msae_norspan_jpc_full_recovery.py, scripts/prepare_msae_independent_norspan_v1.py, scripts/msae_norspan_jpc_controller.py, scripts/msae_norspan_jpc_runtime.py and scripts/msae_jumbo_pair_commit.py. No actual keys/history/private/blind/state, process census, network/acquisition, namespace/cgroup operations, legacy test import/collection, model operation or production subject modification occurred.
