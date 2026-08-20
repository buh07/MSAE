CLAIM: REVISE
SUMMARY: v1 supports a proxy–selectivity tradeoff, but metric confounds block the broad systematic claim.

BLOCKERS
  - scripts/proxy_control_benchmark_v1.py:603-604 — behavioral recovery is aligned to the signed natural effect, but behavioral specificity divides by its absolute value — negative natural effects, concentrated in relative-position rows, reverse the meaning of the specificity score and contaminate cross-concept associations.
  - scripts/proxy_control_benchmark_v1.py:737-744 and 873-874 — every linear split is assigned reconstruction FVU 0 and rank sparsity 1/16, whereas learned methods use measured reconstruction FVU and active-code count 32 — the pooled reconstruction and sparsity correlations are method-class contrasts, not comparable proxy-performance effects.
  - scripts/proxy_control_benchmark_v1.py:193-228 and 710-715 — the 128 component rows recycle 8 names/answers/entities and 4 fillers/templates, but component intervals resample rows independently — row-level equivalence intervals overstate independent intervention support.
  - results/proxy_control_benchmark_v1_20260808/synthetic/metrics.jsonl — no synthetic reference method cleanly recovers both private factors even at zero correlation, no shared factor, and linear mixing — the module does not establish a passing positive control and cannot distinguish evaluator/method failure from representational nonseparability.

REVISIONS
  - results/proxy_control_benchmark_v1_20260808/aggregate/result.json — replace “standard proxies do not predict control” with the supported claim: probe recovery and CKA predict raw behavioral recovery but not behavioral specificity, and both are negatively associated with collateral safety in these controlled panels.
  - results/proxy_control_benchmark_v1_20260808/shards/*/metrics.jsonl — report method-, concept-, and layer-stratified estimates; treat learned-only estimates as primary and pooled reconstruction/sparsity correlations as descriptive confounded contrasts.
  - results/proxy_control_benchmark_v1_20260808/shards/*/component_metrics.jsonl — add an explicitly post-result sensitivity analysis that aligns sham-adjusted movement to the sign of the natural counterfactual; do not overwrite or relabel the frozen v1 metric.
  - scripts/proxy_control_benchmark_v1.py:559-573 — report that asymmetric and swapped K2 always selected the larger branch, while equal K2 lacked a stable global identity; this is capacity-following, not semantic branch recovery.
  - configs/proxy_control_benchmark_v1/run.json:4,26-48 — retain the exploratory label and distinguish natural-text activation training from fresh controlled-generator evaluation; do not claim natural-corpus prevalence or confirmation.

EVIDENCE CHECKED
  - proxy_control_benchmark_v1 status command — all nine model/layer shards and the synthetic job are complete; no tmux server or GPU process remains.
  - COMPLETE.json/result hashes — all nine shard hashes, synthetic hashes, and aggregate hash verified exactly.
  - tests/test_proxy_control_benchmark_v1.py — 7 passed with PYTHONPATH=scripts.
  - results/proxy_control_benchmark_v1_20260808/aggregate/result.json — 918 metric rows, nine clusters; probe recovery versus behavioral recovery rho 0.539, versus behavioral specificity rho -0.087 with interval crossing zero, and versus collateral safety rho -0.611; CKA shows the same recovery/safety tradeoff.
  - all shard metrics — mean probe recovery 0.794 versus leakage 0.841; selectivity falls from 0.016 early to -0.049 middle and -0.107 late while CKA rises from 0.638 to 0.722 to 0.837.
  - all component metrics — all 918 summary rows have finite behavioral endpoints; context and lexical natural effects are positive, while only 29.3% of relative-position natural effects are positive, exposing the specificity-direction issue.
  - synthetic metrics — equal K2 has near-zero mean private-factor selectivity; asymmetric/swapped K2 select the capacity-dominant branch and do not recover both private factors cleanly.

UNKNOWNS
  - Whether sign-aligned, hierarchically clustered specificity replicates prospectively on fresh controlled panels.
  - Whether the proxy-to-control tradeoff holds on naturalistic behavioral tasks rather than deterministic generators.
  - Whether a true behavior-supervised oracle and a ground-truth projector can pass the same evaluation.
  - Whether associations remain after method fixed effects with more than nine independent model/layer units.
