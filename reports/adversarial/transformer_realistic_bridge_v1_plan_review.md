VERDICT: SHIP
ONE-LINE: The revised protocol resolves the causal-oracle, support, estimator, lifecycle, and method-failure defects.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)

CHECKS RUN
  - Root-run `check-plan` on the exact revised copy -> PASS
  - Three adversarial passes resolved full-state tautology, causal oracle, support, regime gates, method failure, and seed aggregation.
  - The forked critic could not persist the last pass because host process creation was temporarily denied; this exact report was persisted by the coordinator.

CONTRACT COVERAGE
  - Preserve v1.1 while updating living paper and ledger -> met.
  - Contrast GPT-2 contribution with constructed complete control -> met.
  - Do not return to K2 -> met.
  - Use transformer-realistic operations and nontrivial selective ground truth -> met.
  - Avoid full-state-transplant tautology -> met.
  - Define a valid nuisance-preserving hybrid recovery oracle -> met.
  - Ensure independent support and endpoint eligibility -> met.
  - Localize failure across the operation ladder -> met.
  - Freeze valid method estimators and strength comparisons -> met.
  - Prevent zero-output methods, rare targets, or seed aggregation from evading failure -> met.
  - Keep method evaluation conditional and separately frozen -> met.
  - Launch once under tmux on a free UUID-locked GPU -> met.

UNKNOWNS
  - Implementation correctness remains to be assessed during candidate and exact-frozen adversarial reviews.
