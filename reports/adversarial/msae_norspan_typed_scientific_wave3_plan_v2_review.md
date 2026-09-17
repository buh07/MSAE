VERDICT: REVISE
ONE-LINE: Stage-write faults cannot capture their required predecessor at a terminal promotion edge that they never reach.

BLOCKERS
  - None asserted against production correctness from this source-only prospective review. Whole technical approval remains BLOCK.

REVISIONS
  - [high] docs/plan-msae-norspan-typed-scientific-fault-wave3-v2.md:37-43 — All twelve terminal cells require the current producer sequence/path/hash “immediately BEFORE terminal _insert_final,” but four cells fail at the original stage write before that edge is reachable.
    reasoning — scripts/msae_jumbo_pair_commit.py:384-393 opens the original stage and writes it; only after successful writing, mode binding, fsync and stage validation does _insert_final run (lines 397-403). A one-shot OSError or KeyboardInterrupt from the stage write exits through the failure cleanup (lines 410-412), never through the planned pre-promotion capture. Capturing a stale earlier pin or moving the fault to a link would evade the cell's declared causal boundary.
    impact — Both success/rejection stage-write paths × both exception types cannot satisfy the specified immediate pre-promotion pin oracle, so the forty-cell acceptance contract remains internally inconsistent.
    fix — Declare phase-specific captures: stage-write cells capture the exact current producer (path, SHA-256, sequence) immediately before the first targeted original-stage os.write; link and catalog-write cells capture it immediately before terminal _insert_final. After each fault assert the producer tuple remains that exact captured predecessor. Retain the already specified explicit predecessor CatalogStore.load refusal and original-inode evidence. Do not change production code, reduce the cell count or adapt away RED.

NITS
  - docs/plan-msae-norspan-typed-scientific-fault-wave3-v2.md:31-32 — The implementation review should require an attributable actual history-content drift refusal, not merely any exception/no-success. The now-declared independent frozen text object makes this oracle feasible; runtime evidence is still pending.

CHECKS RUN
  - nl -ba docs/plan-msae-norspan-typed-scientific-fault-wave3-v2.md — inspected the exact successor text without importing, collecting or running tests.
  - Cross-checked against the retained v1 REVISE and previously inspected expressly allowed public source only: pair stage write precedes terminal link (scripts/msae_jumbo_pair_commit.py:384-412); catalog producer tuple advances only after successful snapshot write (scripts/msae_norspan_jpc_controller.py:162-175); explicit load checks exact catalog-directory membership (lines 190-203).
  - Arithmetic: 2 positive + 8 raw-read + 2 drift + 16 private-sealing + 12 terminal = 40 prospective cells. Exactly four terminal stage-write cells are affected by the unreachable capture.
  - Persisted a distinct mode-0644 report. No plan, test, fixture or production code was edited.

CONTRACT COVERAGE
  - Prior obligation: one exact physical terminal catalog-write fault → met prospectively — v2 lines 39-43 select first actual os.write on the newly O_EXCL-opened snapshot original inode after terminal physical-pair success.
  - Prior obligation: explicit predecessor fresh load, no discovery/adoption, correct catalog/partial refusal → met prospectively — v2 lines 44-48 specify explicit CatalogStore.load, extra-snapshot cardinality refusal and partial-terminal inventory refusal. Producer pin capture is partial because of the stage-write contradiction above.
  - Prior obligation: independently bound ordinary history drift object → met prospectively — v2 lines 27-31 declare plain non-approval, non-excluded synthetic-history.txt before history/authority/acquire, with original SHA-256, adapter, nonempty lexical units and extracted-unit-count binding; same-length changed bytes are retained.
  - Prior obligation: failure-safe causal properties and FD observation even on RED, without replacing primary → met prospectively — v2 lines 50-54 require finally emission, operation cleanup, FD restoration, preserved primary and finite captured JSON-native facts. Runtime implementation remains unverified.
  - Actual synthetic loader/scientific predicates/private publisher, original identities, retained evidence and no retry → met prospectively — v2 lines 14-26,33-36,55-61. Initiating calls must remain distinct from positive terminal reconstruction; no actual firing is attested here.
  - Production guard, production/frozen76 subjects, no model/scoring/training/source authority → met as plan boundary — v2 lines 4-11,65,70-76. Production qualification remains unconditional in the allowed source (runtime lines 49-57; preparer lines 1595-1603; controller lines 251-256).
  - Close-before-release, supervisors/descendants and combined faults → excluded explicitly — v2 lines 60-61; this report grants no guarantee for them.
  - Whole nine-group/80-row closure, canonical binding and exact FINAL owner receipt → unmet and OPEN by design — v2 lines 16,78-80. Whole technical approval remains BLOCK.

UNKNOWNS
  - No wave3 test implementation, dynamic firing, exception chains, resource outcomes, JUnit, progress/timings or regressions were imported, collected, executed or verified. REVISE authorizes no implementation/run under this plan.
  - Existing1172/frozen76 regression claims were not reproduced; neither they nor this prospective report establish new-cell evidence.
  - Read scope was ONLY this v2 plan and the retained prior review against these public files: tests/msae_norspan_controller_fixture.py, tests/test_msae_norspan_typed_history_wave2.py, tests/test_msae_norspan_jpc_full_recovery.py, scripts/prepare_msae_independent_norspan_v1.py, scripts/msae_norspan_jpc_controller.py, scripts/msae_norspan_jpc_runtime.py and scripts/msae_jumbo_pair_commit.py. No actual keys/history/private/blind/state, process census, acquisition/network, namespace/cgroup operation, legacy test collection/import or model operation was inspected or performed.
  - The retained v1 REVISE remains unchanged. V10 remains terminal; later gates and AMALGUMv3 calibration receive no authority from this review.
