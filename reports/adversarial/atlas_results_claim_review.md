# Adversarial Review — Atlas-v1 Results and Training Decision

**Verdict: SHIP**

**One-line:** The artifacts support only an interim equivocal stop, and the decision/reporting now says exactly that.

## Blockers

None.

## Revisions

None.

## Non-blocking nits

1. `results/atlas/k2_v1/k2_audit.json` names `projection_broad16` without a sibling `baseline_selection_failed` field. The failure is bound elsewhere (`L3_calibration_freeze.json`) and is explicit in the reports/TODO. A future companion manifest could expose it more directly without mutating immutable results.
2. `results/atlas/k2_v1/COMPLETE.json` inventories the aggregate and four audit JSONs, while functional results are bound by four separate `*_functional_COMPLETE.json` markers. The chain verifies, though a future top-level functional inventory would simplify auditing.
3. The reviewer noted that `PLAN.md` retained the pre-freeze possibility of an L4 fallback. This was resolved after review: the plan now records fixed L3 and descriptive-only L4, with any future fallback requiring a new prescore plan.

## Checks independently run

- Recomputed raw calibration/raw COMPLETE, K2 COMPLETE, all four functional-result, and architecture-decision artifact hashes; all matched.
- Ran `verify_freeze`, layer-trigger/source verification, all four activation-role verifiers, and all four checkpoint transform verifiers. Bundle `e7c12f4407249ccc556c8f56234c8de36af01d29a89de525deed7506876c8c31`, fixed L3/no fallback, activation bindings, transform markers, and checkpoint hashes verified.
- Strict-parsed all reviewed JSON and recursively checked finite floats; found no NaN/Inf. Aggregate checkpoint and embedded functional objects matched their source artifacts.
- Recomputed K2 family macro-selectivity, learned-minus-simple differences, CE means/deltas, counterfactual summaries, and the reported raw positional margins; all agreed with the reports.
- Confirmed `.atlas_final_unlock` absent, no final activation/evaluation artifact, and no active/new MSAE training process.
- Re-read current status/claim language in `TODO.md`, `RESULTS.md`, `ANALYSIS.md`, and `reports/architecture_decision.{md,json}` after revisions.

## Claim coverage

- **G1:** equivocal; primary p-values and mandatory refit inference are unavailable. L3 is primary and L4 descriptive.
- **G2:** equivocal for every checkpoint; missing simultaneous inference, valid counterfactual specificity, CKA stability, and Tier-2 collateral are explicit.
- **Decision:** `equivocal_no_decision`, `new_training_warranted_now=false`, `g3_paper_branch_selected=false`, and final test `locked_unopened` follow the preregistered precedence.
- **Permitted weaker claims:** lexical/content complement selectivity is high at the point-estimate level; positional cross-decoding is high; all four K2 point macro-selectivities trail the default simple comparator; branch removal raises CE off manifold.
- **Not established:** topology, simple equivalence/superiority, checkpoint validation, stable/causal separation, a supported negative, or justification for new training.

## Remaining unknowns

The 500-draw discovery-refit/source-stratified inference, simultaneous bounds, Tier-2 collateral, CKA stability, and matched-random/sham representation-distance controls remain future work. This SHIP verdict applies to the scoped **equivocal stop decision**, not to an affirmative scientific claim. Neural scoring was not rerun during review; provenance, arithmetic, bindings, and reporting were independently verified against the immutable completed artifacts.
