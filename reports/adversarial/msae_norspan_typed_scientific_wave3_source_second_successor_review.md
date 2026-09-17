VERDICT: REVISE
ONE-LINE: Prior source blockers are resolved; early RED still omits the required current producer pin and intercepted-command count.

BLOCKERS
  - None remaining against the repaired test-source mechanisms identified by the prior implementation reviews. Whole production qualification remains BLOCK.

REVISIONS
  - [medium] tests/test_msae_norspan_typed_scientific_wave3.py:158-162,229-230,243-248,281-284,344-348,395-407 — Per-cell final callbacks still omit current_catalog_pin and synthetic_git_commands if an earlier assertion prevents fresh_refusal.
    reasoning — fresh_start facts are now recorded before retained_snapshot at lines 170-175, which repairs a failure of that snapshot. They remain after the raw firing/shape assertions (lines 243-246), private shape assertions (lines 362-377), and terminal firing/pin/shape assertions (lines 395-405). The always-attempted guarded final callback receives tracker.facts, which emits raw/private counters but neither pin(self.f) nor len(self.f.calls); hook.facts emits only the captured predecessor, not the current post-fault tuple. Thus an early RED has no direct current producer tuple or intercepted-command total in its causal properties.
    impact — The previously retained should-fix RED pin/transport-property revision is not fully discharged, and the plan's all-cell causal facts remain partial despite the repaired core assertions.
    fix — Add current_catalog_pin=pin(self.f) and synthetic_git_commands=len(self.f.calls) to tracker.facts, or equivalent always-attempted per-cell guarded callbacks. Once the fixture/tracker exists, those finite fields must not depend on reaching fresh_refusal. Keep setup-unavailable values explicit rather than inventing pin/count observations. Preserve active primary errors using observe; no production change or cell-count expansion is needed.

NITS
  - None.

CHECKS RUN
  - Full static nl/sed inspection and sha256sum of tests/test_msae_norspan_typed_scientific_wave3.py — exact SHA-256 4c96b7e15ac936c53e9e2f8cecef865cb876067cf111a584b2e79b22d0b3e31b, 407 lines. No test import, collection or execution.
  - Cross-checked repaired source mechanisms against approved plan v3 and the same previously allowed public source/fixture paths; no new directories, runtime artifacts or protected objects were read.
  - Checked arithmetic and pass-through instrumentation: 2 positive + 8 raw-read + 2 drift + 16 private + 12 terminal = 40 declared cells; no outcome/firing attestation from that count.
  - Persisted only this distinct mode-0644 report. Did not inspect or wait for the old active job, read its completed result, launch current tests, modify source/plan, stage or commit.

CONTRACT COVERAGE
  - Prior BLOCKER: exact initiating drift predicate → met statically — lines 271-274 require n.GateFailure with anchored escaped history_drift:synthetic-history\.txt, exactly one mutation firing, one real loader invocation and all four completed consumer reads, and record the actual reason. This matches actual history_collisions content rejection in the allowed preparer at lines 2009-2012.
  - Drift no scientific rejection/success and retained changed bytes → met statically — lines 275-280 assert no seal, rejection or source_ready and reread the intended changed ordinary bytes before/after fresh attempts. Registry content binding and prehistory nonempty plain-text setup remain at lines 255-268.
  - Prior BLOCKER: drift final observation guard → met statically — physical_seal namespace inspection now runs inside the observe callback lambda at line 282, not as a pre-call keyword expression. Secondary observation failures remain under primary-preserving handling at lines 26-36.
  - Prior revision: post-fresh producer tuple equality → met statically — lines 170-173 capture exact producer pin before snapshot/fresh work; line 192 requires unchanged tuple after EACH expected load/recover/prepare refusal, alongside exact physical map equality and unchanged real raw/private/command counters at lines 193-197.
  - Exact fresh load/execute typed refusal → retained statically — lines 179-191 distinguish predecessor CatalogStore.load directory_cardinality from mandatory successful noncatalog loading and exact Controller.execute type/reason. No generic exception can satisfy this helper, and no execute is credited after a refused load.
  - Exact post-fresh physical retention/no repair → retained statically — named synthetic tree identity/type/mode/nlink/size/content-SHA map (lines 71-95), exact equality after every operation (line 193), plus ordinary changed-byte assertions. Post-observation facts and retained digest remain guarded at lines 199-205.
  - Real private publisher/pair-attempt no retry → retained statically — counters precede pass-through actual entry/creation calls (lines 120-127); private cells assert one entry and exact prior/target role attempts (lines 375-376); all fresh operations assert unchanged counts (lines 195-196).
  - Reachable stage/link/catalog original-inode faults and outside predecessor capture → retained statically — lines 305-342 target exact parent/original stage, capture before original-stage write or promotion, bind the new original catalog inode after terminal physical pair, and inject once. Initiating terminal pin equality is asserted at line 396.
  - Corrected descriptor forwarding and missing-parent guard → retained statically — lines 116-118,298-303. No scientific predicate, real loader or publisher outcome is replaced.
  - Primary-safe FD/JUnit finalization → retained statically — lines 45-68 guard FD observations and serialization, preserve active primary notes and fail unestablished cleanup/observation when no primary exists. All per-cell final observations now run inside observe callbacks; initial setup availability and actual runtime outcomes remain unverified.
  - All-cell RED current pin/intercepted-command properties → partial — fresh_start now precedes retention observation, but early assertion RED still misses the two final finite fields as detailed in REVISIONS.
  - Actual synthetic terminal success/license rejection/reconstruction → source-only conditional — lines 208-230 separate initiating raw load from permitted single terminal reconstruction and assert no launch/past-success/model/C2 authority. No current-source run or result was inspected.
  - Whole nine groups/80 whole rows → OPEN. Whole production technical approval → BLOCK. No real source authority, scientific eligibility, scoring/training/model/launch authority follows from this source review or old candidate outcomes.

UNKNOWNS
  - This REVISE is a retained test-source evidence completeness issue, not a new production defect or a claim of runtime failure. Core prior BLOCK mechanisms are repaired statically; dynamic exact forty-cell firing/retention/pins/FD/JUnit evidence remains PENDING.
  - No tests of this exact hash were launched, imported, collected or executed by this reviewer. The old forty-cell candidate remains archival UNQUALIFIED regardless of pass count; initial pre-loader TypeError RED and all earlier negative review/source artifacts remain preserved.
  - A future source SHIP would apply only to this bounded synthetic test harness and conditional exact forty-cell execution under v3, not acceptance evidence, production architecture, whole qualification, owner trust/approval, eligibility, model/training/scoring or launch.
  - Read scope was current tests/test_msae_norspan_typed_scientific_wave3.py against retained plan/review findings and the same allowed public files: tests/msae_norspan_controller_fixture.py, tests/test_msae_norspan_typed_history_wave2.py, tests/test_msae_norspan_jpc_full_recovery.py, scripts/prepare_msae_independent_norspan_v1.py, scripts/msae_norspan_jpc_controller.py, scripts/msae_norspan_jpc_runtime.py and scripts/msae_jumbo_pair_commit.py. No actual scratch/fixture trees, keys/history/private/blind/protected state, process census, acquisition/network, namespace/cgroup operations, legacy test collection/import or model operations were inspected/performed.
  - Global production/frozen76/staged367 manifests, canonical binding and exact FINAL owner receipt were not audited in this bounded source review. Production guard remains blocked by the retained allowed source/task boundary; V10 is terminal and AMALGUMv3/later gates receive no authority here.
