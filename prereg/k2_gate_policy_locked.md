# K=2 Gate Policy (Locked Before K=2 Training)

## Scope
This policy locks the pre-K2 go/no-go criteria and reporting inputs for Paper 1 K=2 MSAE training.

## Primary Target
- Model: `EleutherAI/pythia-160m-deduped`
- Primary layer: `L3`
- Fallback layer: `L4`
- Headline ranks: `r8`, `r16`
- Boundary diagnostic rank (non-headline): `r32`

## Locked Criteria (v2)
- `c1_new_rank_recovery`: `rank_at_pos90 <= ceil(d / 8)`
- `c2_var_v2`: `(c2_var_ratio >= 3.0) AND (tok_energy_excess >= 0.05)`
- `c3_v2`: `(pos_drop_frac_v2 >= 0.25) AND (tok_drop_frac_v2 >= 0.25)`
- `c4`: `median principal angle >= 45 deg`
- Combined gate: `all_pass_v2 = c1_new AND c2_var_v2 AND c3_v2 AND c4`

## Split Policy
- Split-specific reporting is mandatory:
  - `iid`
  - `source_holdout`
  - `corpus_holdout`
- Mixed-split pooled statistics may be reported for robustness context but are not treated as standalone headline decodability estimates.

## Layer Selection Rule
Choose primary layer by:
1. Highest holdout headline pass-rate (`r8/r16` on non-IID runs)
2. Highest overall headline pass-rate (`r8/r16`)
3. Highest mean `raw_pos_auc`

## Required Artifacts Before K=2
- Pre-K2 decision artifacts committed and pushed:
  - `pre_k2_decision.json`
  - `pre_k2_decision.md`
- Split-specific CI outputs committed:
  - `ci_metrics_iid.tsv`
  - `ci_metrics_source_holdout.tsv`
  - `ci_metrics_corpus_holdout.tsv`
- Convergence report committed:
  - `convergence_quality.tsv`
- Compatibility report committed:
  - `compatibility_iid_v5_vs_v6.md`

## K=2 Training Defaults (Locked for First Wave)
- Training corpus: The Pile stream (`ArmelR/the-pile-splitted`, config `all`)
- Topology: 4 independent jobs (not DDP)
- Baseline incoherence: `lambda_inc = 1e-2`
- Control: `lambda_inc = 0`
- Wave 1 budget: `100M` activation-tokens per run
- Promotion target: `1B` activation-tokens for promoted runs

## Amendments
Any threshold or policy changes after this lock must be recorded in a timestamped amendment file and new git tag.
