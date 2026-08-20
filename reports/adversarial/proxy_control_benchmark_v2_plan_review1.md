VERDICT: REVISE
ONE-LINE: The design is sound, but independence and oracle semantics need stricter prospective definitions.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)
  - [high] PLAN_PROXY_CONTROL_BENCHMARK_V2.md:52-56 — the v1 cyclic factor grouping is called a component-block interval without acknowledging that blocks are reconstructed post hoc from eight repeated lexical/template cycles.
    reasoning — those groups are nuisance-factor sensitivity units, not newly observed independent experimental components.
    impact — calling them independent would repeat the pseudoreplication problem the companion is supposed to diagnose.
    fix — label v1 block results conservative factor-cycle sensitivity only; reserve independent component-block language for v2's prospectively generated blocks.
  - [high] PLAN_PROXY_CONTROL_BENCHMARK_V2.md:72-77 — the behavior-gradient oracle is described conceptually but does not freeze its exact objective, nuisance penalty, rank selection, or whether natural-effect magnitude/sign enters fitting.
    reasoning — materially different oracle definitions could convert an oracle-only branch into failure or success.
    impact — the central architecture decision would remain researcher-degreed after data opening.
    fix — freeze the exact matrix/objective, rank, regularization, sign convention, and development-only inputs in config and tests before the final freeze.
  - [medium] PLAN_PROXY_CONTROL_BENCHMARK_V2.md:57-62 — token-length filtering is permitted but the plan does not forbid scientific-effect or model-logit filtering during panel preparation.
    reasoning — prescore selection must remain label/model-output blind to be prospective.
    impact — effect-conditioned support would bias behavioral recovery upward.
    fix — state that preparation may use tokenizer IDs/lengths and dataset labels only, never activations, logits, gradients, effect sizes, or method outcomes.
  - [medium] PLAN_PROXY_CONTROL_BENCHMARK_V2.md:37-40 — naturalistic context truncation and unrelated-context pairing are unspecified.
    reasoning — different truncation sides or output-aware context selection can change whether evidence is present.
    impact — the naturalistic endpoint would not be reproducible or leakage-resistant.
    fix — freeze raw row IDs, deterministic context normalization, truncation side/budget, unrelated pairing by label-blind length, and no answer/effect-aware filtering.
  - [medium] PLAN_PROXY_CONTROL_BENCHMARK_V2.md:95-111 — decision branches lack numerical pass criteria.
    reasoning — verbal outcomes such as “passes both directions” leave post-result flexibility.
    impact — training authorization would not be prospective.
    fix — add frozen recovery, specificity, collateral, eligibility, direction, model-replication, association, and positive-control thresholds to the config and bind them into the freeze.

NITS            (optional, cap at 5)
  - PLAN_PROXY_CONTROL_BENCHMARK_V2.md:32 — record that v1 checkpoints are serialized float16 artifacts even though v1 live evaluation used float32 weights.

CHECKS RUN
  - `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN_PROXY_CONTROL_BENCHMARK_V2.md` → PLAN: PASS.
  - `nvidia-smi` → eight RTX 6000 Ada GPUs currently idle; runtime availability remains launch-time state.
CONTRACT COVERAGE
  - v1 preservation → met — exact import hashing and create-once output are explicit.
  - cached companion → partial — analyses listed, but v1 block terminology needs correction.
  - paper update → met — ledger-bound integration is required.
  - prospective corrected v2 → partial — metric correction and panels are specified; oracle and decision thresholds need exact freezes.
  - conditional training → partial — no real SAE training is explicit; authorization thresholds are not yet numerical.
  - launch and stop → met — tmux launch and no-wait acceptance are explicit.
UNKNOWNS
  - Whether thirty-two cached LongBench yes/no rows survive every tokenizer and fixed context budget.
  - Whether the behavior-gradient oracle can meet a nontrivial synthetic gate under the final objective.
