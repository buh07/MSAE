VERDICT: BLOCK

ONE-LINE: Gen7’s real-tmux proof omits the frozen prefix, action, transcript, delta, and cleanup evidence.

BLOCKERS
  - [critical] `scripts/run_msae_independent_measurement_v3_post_m2_gen7_tmux_test.py:1022-1092,1565-1583,1640-1663` — scenario action evidence is reconstructed only after cleanup, not before the action.
    reasoning — The supervisor calls `_g7_act` immediately after receiving the boundary. It never constructs `msae_v3_gen7_scenario_prefix_v2` or `required_prefix_sha256`. Its later projection derives targets from the reporter, assigns the same post-cleanup process array to both pre/post action state, and always sets `term_escalation` to null. The owner independently repeats the same flawed derivation at `scripts/msae_independent_measurement_v3_post_m2_gen7_runtime.py:14164-14236`, making the comparison tautological. Concrete target errors include S02 binding the monitor reporter group instead of the server group, S06/S07 binding the launcher instead of the monitor peer, S10 binding the worker instead of the pane supervisor, and S11 omitting the resistant group member. `_g7_validate_monitor_frame` at supervisor lines 1103-1113 also leaves protocol, generation, prior digest, and exact payload semantics unchecked.
    impact — This violates the mandatory pre-action prefix, exact target, independent observation, and S10/S11 TERM/KILL evidence contracts at `docs/plan-msae-independent-measurement-v3-post-m7-gen7.md:1067-1197`. A passing real-tmux run therefore does not prove the frozen fault matrix.
    fix — A disjoint generation must reconstruct and hash the complete prefix before acknowledgement/action, independently capture each exact target, validate complete monitor frames, and bind genuine before/after and TERM/KILL observations.

  - [critical] `scripts/run_msae_independent_measurement_v3_post_m2_gen7_tmux_test.py:1722-1776` — no immutable overall real-tmux transcript is produced.
    reasoning — The supervisor computes an outer-final digest and sends it in frame 6, then ultimately returns only an exit code. `tests/test_msae_independent_measurement_v3_post_m7_gen7.py:4133-4139` checks only the ledger digest and scratch removal; it neither validates nor retains the outer-final digest. No `msae_v3_gen7_scenario_outer_result_v1` implementation exists.
    impact — The required per-case outer-final and scenario-result evidence is lost, violating plan lines 735-737, 1190-1197, and 1505-1511.
    fix — A disjoint generation must define, independently validate, and durably bind every case’s prefix, action, ledger, and outer-final digest into the reviewed overall transcript.

  - [high] `scripts/msae_independent_measurement_v3_post_m2_gen7_runtime.py:4012-4048,4087-4141,4193-4224` — the claimed typed delta comparator is a frozen whole-file hash allowlist, not a typed classifier.
    reasoning — The code attaches declared class labels to whole-byte/AST hashes without mapping actual changed nodes or lines to those classes. The runtime’s hash registry is normalized out of its own fingerprint, and only a manually selected subset of scientific functions receives semantic equality checks. The test at `tests/test_msae_independent_measurement_v3_post_m7_gen7.py:1341-1370` proves only that unregistered bytes change a digest.
    impact — Arbitrary candidate changes can be accepted by updating the same-file hash registry before review; the comparator cannot mechanically establish that every delta belongs to the four classes required by plan lines 280-309.
    fix — A disjoint generation must implement an actual AST/JSON/line diff whose every changed element maps to one closed allowed class, with independently frozen policy data.

  - [high] `tests/test_msae_independent_measurement_v3_post_m7_gen7.py:3797-3910` — cleanup mutation testing does not exercise the required selected crash/exception cases through outer containment.
    reasoning — The test covers seven broad operation IDs but always builds the first hook, disables `_fault_hook`, calls `_containment_monitor_cleanup` directly with synthetic state, and manually kills/removes resources in `finally`. The crash/exception parameter chiefly changes the supplied owner; neither selected fault path nor `_g7_emergency_containment` is exercised. Each broad ID also combines multiple concrete cleanup boundaries.
    impact — This does not establish the plan requirement that stubbing each registered production cleanup action makes both its real crash and exception cases fail before outer emergency cleanup protects the host (`plan:1206-1219`).
    fix — A disjoint generation must inject each cleanup mutation into the corresponding real selected cases, require a failing matrix result, and independently verify emergency extinction.

REVISIONS
  - None.

NITS
  - None.

CHECKS RUN
  - SHA-256 recheck:
    - plan: `d612a86b3c33f774e51f649f1b87dc4977d6d91d2734e27729e84eb9a4867d5d`
    - plan review: `f3e3117e8331849c18f1520626e50edfed5c9602aa7b09ccd24bae434e016354`
    - controller: `4c10f5b5bc18ad4ae3828de5b6cebdf32e65c5ddf1f7acdec1aa2a1f8ad99ef9`
    - runtime: `017862e1c433d45fea4e91b60e2f23a62084a1f2c8200a1a8222fddfa7a125bc`
    - runner: `c28bec9c4d2c4be61ba0bd6a87df81e9c33a6a196bfecc5a4b778ecc9189df91`
    - launcher: `21519cf92d0ed1d91d9ac4ad0caa2178cc80572624401952afe629b6fba6ba4b`
    - tmux supervisor: `cd85077c33b283a5c2bfb767632d5ee29c59d3b16f6f0652e0802393a4fae6a7`
    - RFC: `857620e5df9be77aef2315816d9f16b6c1cad885eafcd9b8baf96db0af496f59`
    - tests: `c99fdef8f6ff505986aa81e2dbbf8da0f8f840e232fe1ee7c3c36ea800df258e`
  - Targeted safe pytest selection → `20 passed, 157 deselected`.
  - In-memory compilation of five Python subjects → PASS.
  - `bash -n scripts/launch_msae_independent_calibration_v3_gen7.sh` → PASS.
  - `git diff --check` → PASS.
  - Code search for scenario prefix/outer-result schemas → zero implementation matches.
  - One-way namespace lstat scan → all registered gen7 capability/review/M3/M4/run/state/key/temp outputs absent; all seven short families empty.
  - Quarantined payloads → lstat only; three expected regular entries observed, zero content reads.

CONTRACT COVERAGE
  - Frozen plan and plan-review pins → met.
  - Exact seven-file identities and modes → met.
  - Pre-capability one-way-output absence → met.
  - Quarantine lstat-only invariant → met.
  - Pre-capability review/namespace gate → met by static inspection and targeted tests.
  - Shared-helper, fault-binding, and tripwire mechanisms → partial — present, but the matrix evidence is incomplete.
  - Exact scenario prefix/target/action proof → unmet.
  - Immutable overall real-tmux transcript → unmet.
  - Typed four-class delta enforcement → unmet.
  - Cleanup mutation non-tautology → unmet.

UNKNOWNS
  - The real-tmux command was not rerun, as prohibited. Its disclosed passing result cannot cure the structural contract violations.
  - The complete safe suite and predecessor suites were not independently rerun; only the targeted current-byte selection was executed.
  - No GPU, model, capability, setup, M4, signing, launch, or tmux action was performed.
