VERDICT: BLOCK
ONE-LINE: Frozen gen6 cannot authorize capability: predecessor tests fail and the mandatory tmux matrix is not implemented.

BLOCKERS
  - [critical] docs/plan-msae-independent-measurement-v3-post-m6-gen6.md:1399,1440-1443,1483-1485 — the frozen authority requires every predecessor suite to pass before pre-capability SHIP.
    reasoning — Independently running the exact frozen gen5 CPU suite produced `11 failed, 147 passed, 1 skipped`. Gen5’s honest failed-generation classification does not create a test-pass exception; the plan separately requires its immutable test suite to pass.
    impact — Publishing a SHIP pre-capability review would contradict the frozen plan and RFC lines 295-305, invalidating the capability one-way door.
    fix — Preserve gen6 as failed before capability. A disjoint generation must explicitly register typed expected failures or another honest predecessor-verification rule; do not reinterpret gen6.

  - [critical] scripts/run_msae_independent_measurement_v3_post_m2_gen6_tmux_test.py:33-36,640-682,1093-1114; tests/test_msae_independent_measurement_v3_post_m6_gen6.py:3765-3794 — the registered real-tmux test uses an independent launcher and lacks required boundary cases.
    reasoning — Frozen plan lines 788-790 forbid replacing the factored production foreground-server/start/identity helpers with an independently implemented test launcher. The supervisor directly implements tmux server startup, promotion and clients, while pytest directly runs new-session/set/show. Its fault modes omit the plan-mandated monitor-record, record-ACK, `START_SERVER`, server-exec/socket, new-session and exit-empty boundaries required at lines 806-816.
    impact — The disclosed one-pass real-tmux result does not prove the frozen containment contract or production startup lifecycle.
    fix — In a disjoint generation, make the registered test execute the actual production helpers and inject every frozen namespace/lifecycle boundary.

  - [high] scripts/msae_independent_measurement_v3_post_m2_gen6_runtime.py:12544-12553 — post-`START_SERVER` server-spawn failure bypasses monitor terminalization and teardown.
    reasoning — After accepting frame 4, `subprocess.Popen` is outside the monitor’s main exception/finally region. If it raises, the monitor only restores umask and exits; it does not claim technical failure or run descendant/socket/control cleanup. Concurrent launcher loss therefore leaves no surviving authority to create an unambiguous terminal.
    impact — This violates the complementary-authority and “no ambiguous terminal state” requirements in RFC lines 284-291.
    fix — In the successor, place server creation inside the monitor-owned failure/cleanup region and terminalize every post-`START_SERVER` exception before exit.

REVISIONS
- None.

NITS
- None.

CHECKS RUN
  - `sha256sum` on plan, plan review and seven implementation subjects → all nine exact registered digests matched.
  - Frozen gen5 plan/review/seven-file hashes → all matched plan lines 97-109.
  - Closed-environment gen5 pytest suite → `11 failed, 147 passed, 1 skipped in 149.63s`.
  - Closed-environment gen6 pytest suite → interrupted after blockers were accepted; `72 passed` through 44%, no failures observed before interruption.
  - `py_compile`, `bash -n`, `git diff --check` → passed. `py_compile` unintentionally refreshed four ignored gen6 `scripts/__pycache__` files; this was disclosed immediately and no reviewed or protocol artifact was changed.
  - Gen6 review/capability/M3/M4/key/state/run/test socket namespaces → 17 registered paths and all `m6t_*`, `m6b_*`, and real-test families absent.
  - Three quarantined `final*.jsonl` files → lstat only; each remains UID-owned mode-0600 regular nlink-1. Contents were never opened or hashed.
  - No capability, setup, M4, signing, launch, tmux, GPU query, or model import/call was run.

CONTRACT COVERAGE
  - Exact plan/review/implementation bindings → met — all registered hashes match.
  - Predecessor test gate → unmet — frozen gen5 suite has 11 failures.
  - Registered real-tmux fault matrix → unmet — independent launcher and missing frozen boundaries.
  - Complementary post-START monitor authority → unmet — server-spawn exception escapes monitor cleanup.
  - Pre-capability one-way absence → met — all registered output and socket families remain absent.
  - Quarantine invariant → met — lstat-only inspection; zero content reads.
  - Capability/setup/scientific sequencing → met so far — no prohibited transition occurred.

UNKNOWNS
  - The prohibited real-tmux command was not rerun independently; its reported pass cannot cure the static contract mismatch.
  - The complete gen6 safe suite was not rerun to completion after the decisive blockers.
