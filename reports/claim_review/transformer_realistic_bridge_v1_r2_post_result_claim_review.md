# Transformer-realistic bridge v1 r2 post-result claim review

CLAIM: REVISE  
SUMMARY: Bridge and matched-strength findings hold for one synthetic generator; broader discovery, supervision, SAE, K2, or natural-model claims do not.

## Blockers to broad claims

- `PLAN_TRANSFORMER_REALISTIC_BRIDGE_V1_R2.md:318-319` — “component discovery, not evaluator” is too specific. Failures also conflate rank, optimization, objective design, feature selection, and direction estimation.
- `PLAN_TRANSFORMER_REALISTIC_BRIDGE_V1_R2.md:269-287` — the behavior-supervised rank-8, finite-step controller is not an upper-bound skyline. It is a privileged behavior-supervised baseline.
- No implication for natural transformers, K2, SAEs generally, or supervision generally is supported: no pretrained model, natural prompt, or K2 was evaluated.

## Supported claims and revisions

- **Supported with scope:** On one fixed untrained synthetic generator, the evaluator recognized the registered complete causal controller across six transformer-like regimes and two disjoint row panels. Every regime passed; worst incomplete-gap lower bounds were 0.1679 development and 0.1693 confirmation.
- **Supported:** Under the preregistered matched-L2 estimand, random, PCA, DiffMean, LEACE-style, all three SAE seeds, and all three supervised seeds failed joint control on both panels; exact ground truth passed every gate on both.
- Estimated methods were not wholly ineffective. DiffMean and LEACE achieved target recovery around 0.77 and 0.73 but failed joint specificity, collateral, and full-vocabulary requirements.
- **Recommended interpretation:** The frozen evaluator executes and distinguishes known complete versus incomplete control on this synthetic operation ladder; the registered estimators did not recover comparably selective controllers.

## Evidence checked

- Frozen plan/configs: six regimes, fixed gates, disjoint 512/192/192 method train/development/confirmation splits, fixed learned seeds.
- Bridge final and summaries: `TRANSFORMER_REALISTIC_GROUND_TRUTH_CONFIRMED`, 192/192 eligible rows per regime, all gates passed.
- Bridge QA: repeated live passes exact; all 140 registered fields per regime passed separate NumPy-oracle tolerances.
- Methods summaries: only `ground_truth=true` under `family_pass_every_seed`; every estimated and incomplete family false on both panels.
- Fit summary: all six checkpoints completed 2,000 fixed steps; SAE training reconstruction loss was low, but selected SAE controllers did not provide causal control.
- Code: row-wise ground-truth norm matching, same-site/same-path orthogonal controls, common metrics, and every-seed family rules.
- Lineage: disjoint balanced panels and freeze, review-binding, recovery-parity, payload-continuity, and completion hashes passed.

## Unknowns

- No variation across model/generator parameter seeds or external replication.
- Torch and NumPy implementations are separate but co-located.
- Matched total L2 norm does not imply matched downstream causal leverage.
- Representation quality, controller selection, capacity, loss scaling, and optimization remain confounded.

## Next registered study recommendation

Use fresh model/panel seeds, a provably learnable train-only full-rank or closed-form supervised baseline, rank/objective/optimization ablations, and separate direction-recovery metrics. Do not tune against the opened panels or advance K2/natural-model claims yet.
