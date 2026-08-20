VERDICT: SHIP
ONE-LINE: The revised plan prospectively isolates measurement repair, fixed checkpoints, gates, and training decisions.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)
  - PLAN_PROXY_CONTROL_BENCHMARK_V2.md:69-72 — wrap the long template-disjointness sentence during implementation-only cleanup.

CHECKS RUN
  - `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN_PROXY_CONTROL_BENCHMARK_V2.md` → PLAN: PASS.
  - manual contract audit → exact oracle matrix, effect-blind prescore, natural truncation/pairing, numerical decisions, float16 lineage, and v1 sensitivity terminology are present.
CONTRACT COVERAGE
  - v1 preservation → met — byte-hash import and no-overwrite constraints.
  - cached companion → met — required analyses and conservative v1 factor-cycle interpretation.
  - paper update → met — evidence-ledger verification required.
  - corrected v2 → met — signed metric, matched shams, disjoint templates, block hierarchy, oracle, positive controls, natural endpoint, and class-specific proxies.
  - conditional training → met — no real SAE training; numerical future-authorization conditions frozen.
  - launch and stop → met — synthetic-gated tmux execution and no-wait endpoint explicit.
UNKNOWNS
  - Runtime tokenizer support and oracle gate performance remain implementation/smoke facts, correctly required before freeze and launch.
