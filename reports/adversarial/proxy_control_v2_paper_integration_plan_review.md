VERDICT: SHIP
ONE-LINE: The plan preserves frozen outcomes while separating cached synthesis, paper claims, and unopened confirmation design.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)
  - PLAN_PROXY_CONTROL_V2_PAPER_INTEGRATION.md:60 — “signed-by-hash” should mean hash-bound provenance, not a cryptographic signature.

CHECKS RUN
  - `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN_PROXY_CONTROL_V2_PAPER_INTEGRATION.md` → PLAN: PASS.
  - deterministic query for `aggregate` → `scripts/proxy_control_benchmark_v2.py:1032`.
  - deterministic query for `paper_claim_ledger_v1` → only the frozen v2 inventory and paper verifier reference it.
  - artifact audit → v2 aggregate, nine shard terminals, component rows, synthetic PASS, freeze, claim review, and Qwen operational recovery are present.

CONTRACT COVERAGE
  - preserve v1/v2 → met — immutable outcomes and thresholds are explicit non-goals.
  - stop current training → met — closure artifact denies K2, context/local, shared, and supervised training authorization.
  - cached analysis → met — required outputs and zero-forward boundary are concrete and verifiable.
  - update paper → met — v2's positive and negative findings, naturalistic ineligibility, exact ledger bindings, and limitations are required.
  - naturalistic successor → met — only a draft is authorized, with a development/confirmation firewall and prospective stop rules.
  - adversarial impact review → met — novelty, generality, causal language, statistics, baselines, actionability, and narrative focus are explicit attack surfaces.

UNKNOWNS
  - Whether the integrated paper's chronological structure can be repaired locally or requires a later full rewrite around the benchmark.
  - Which naturalistic task has adequate model-level effect support; correctly deferred to opened development rather than chosen from v2 outcomes.
