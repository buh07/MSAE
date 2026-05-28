# Pilot v6 Preregistration (Pre-K2 Gate)

Timestamp: to be fixed by git commit/tag `prereg-v6`.

## Scope
- This prereg applies to the pre-K2 raw-activation separability suite.
- Primary target family: `EleutherAI/pythia-160m-deduped`.
- Candidate layers: `L3` primary, `L4` backup.
- Headline ranks: `r8` and `r16`.
- Boundary diagnostic rank: `r32` (not a headline pass criterion).

## Locked Criteria (v2)
- `c1_new_rank_recovery`: `rank_at_pos90 <= ceil(d/8)`.
- `c2_var_v2`: `(c2_var_ratio >= 3.0) AND (tok_energy_excess >= 0.05)`.
- `c3_v2`: `(pos_drop_frac_v2 >= 0.25) AND (tok_drop_frac_v2 >= 0.25)`.
- `c4`: `median principal angle >= 45 deg`.
- Gate metric: `all_pass_v2 = c1_new_rank_recovery AND c2_var_v2 AND c3_v2 AND c4`.

## Suite Structure
- Stage A IID confirmatory:
  - Pythia-160M L3/L4, seeds `42..46`, ranks `8,16,32`.
  - Controls: GPT-2 L4; Pythia-70M L4; Pythia-14M smoke.
- Stage B source holdout:
  - 5-source LOSO over `{FineWeb-Edu, Pile-CC, Github, PubMed Abstracts, ArXiv}`.
  - Pythia-160M L3/L4, seeds `42,43,44`, ranks `8,16,32`.
- Stage C corpus holdout:
  - Train on balanced 5-source mixture, evaluate on OpenWebText holdout.
  - Pythia-160M L3/L4, seeds `42,43,44`, ranks `8,16,32`.

## Statistical Reporting
- Bootstrap CI (95%) for:
  - `raw_pos_auc`
  - `c2_var_ratio`
  - `tok_drop_frac_v2`
  - `all_pass_v2` pass rate
- Threshold sensitivity grids:
  - `c2_var_ratio_threshold in {2.5, 3.0, 3.5}`
  - `c2_var_excess_floor in {0.03, 0.05, 0.07}`
  - `c3_v2_drop_fraction in {0.20, 0.25, 0.30}`

## Layer Selection Rule (Locked)
- Choose primary layer by:
  1. Highest holdout headline pass rate (`r8/r16`, non-IID runs).
  2. Highest overall headline pass rate (`r8/r16`).
  3. Highest mean `raw_pos_auc`.
- The non-selected layer is the fallback.

## Operational Block
- K=2 MSAE training is blocked until:
  - prereg commit is pushed,
  - full v6 suite completes,
  - pre-K2 decision artifact is generated and pushed.

