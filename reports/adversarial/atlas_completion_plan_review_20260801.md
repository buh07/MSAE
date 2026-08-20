# Atlas Completion Plan Adversarial Review

The plan in `docs/rfc-atlas-v1-completion.md` underwent iterative independent
review on 2026-08-01. Earlier rounds required revisions to source-stratified
weighting, complete-case inference, Tier-1/Tier-2 eligibility, nonlinear leakage
aggregation, G1 intersection-union testing, fourth-G1/G2 null imposition,
cross-fit CKA, CE aggregation, sentence/token random controls, deterministic
claims, GPU budgets, and the known LinES futility rule.

Final independent verdicts:

- `adversarial_completion`: **SHIP** — no blockers or revisions.
- `adversarial_plan`: **SHIP** — no blockers, revisions, or nits.
- `adversarial_todo`: **SHIP** after an additional round repaired baseline
  admissibility, stability-estimand comparability, cosine-scale control matching,
  weighted CKA, input firewalling, resource stops, and terminal states.

Both final reviews reported that the estimator, provenance/firewall rules,
diagnostic continuation, GPU execution policy, and exhaustive decision contract
were covered. Implementation and results require separate adversarial reviews.
