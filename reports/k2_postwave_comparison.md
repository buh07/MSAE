# Existing K=2 1B Post-wave Comparison

Source: terminal `train_summary.json` files in `pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/`. These are tail-training diagnostics, not a held-out branch-localization evaluation.

| Job | Seed | `lambda_inc` | Resume tokens | Final tokens | Tail-100 FVU | Tail-100 incoherence | Pos active | Content active |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| g4 | 42 | 0.01 | 400,016,486 | 1,000,000,016 | 0.076385 | 0.004643 | 0.8870 | 0.9112 |
| g5 | 43 | 0.01 | 400,016,486 | 1,000,000,016 | 0.071359 | 0.003150 | 0.8973 | 0.9257 |
| g6 | 44 | 0.01 | 300,016,447 | 1,000,000,042 | 0.073543 | 0.002811 | 0.8959 | 0.9346 |
| g7 | 42 | 0 | 400,016,486 | 1,000,000,016 | 0.069778 | 0.015200 | 0.9233 | 0.9298 |

The regularized-seed mean tail-100 incoherence is `0.003535`, about `4.30x` lower than g7. The matched-seed g4–g7 comparison is `3.27x` lower incoherence for g4, with `+0.006607` absolute FVU (worse reconstruction). All final dead fractions are zero.

## Interpretation limits

- The incoherence regularizer changed the logged cross-branch geometry in its intended direction and paid a modest reconstruction cost.
- This table does not establish that branches isolate absolute position, broad structural position, or content; that requires the independent atlas/K=2 audit.
- `g4`–`g6` are development-level model variations, while `g7` is a matched-seed regularizer intervention, not a fourth regularized replicate.
- Resume lineage differs (`g6` resumed earlier), and exact stream position was not restored. Cross-job differences cannot be attributed only to seed or `lambda_inc`.
- FVU and incoherence are inapplicable as substitutes for held-out selectivity, leakage, counterfactual specificity, and suffix-model collateral.
