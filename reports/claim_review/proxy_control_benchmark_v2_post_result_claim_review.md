CLAIM: REVISE
SUMMARY: V2 supports a local potency–precision tradeoff, not universal nonseparability or general SAE failure.

BLOCKERS
  - results/proxy_control_benchmark_v2_20260808/aggregate/result.json — zero of 90 method/concept/stage decisions passed, but several hierarchical intervals show positive behavioral recovery — “no evaluated method jointly passed” is supported; “the information is behaviorally inert” is contradicted.
  - results/proxy_control_benchmark_v2_20260808/aggregate/result.json — the behavior-gradient oracle is a frozen rank-limited eigenspace estimator, not an end-to-end supervised optimum — its failure cannot establish that every supervised linear separator or nonlinear controller would fail.
  - data/proxy_control_benchmark_v2_prepared/PRESCORE.json — SOURCE_C and SOURCE_D are two generated vocabulary/template panels from one generator, and the model-level hierarchy contains three models, two from Pythia — evidence is insufficient for “standard interpretability proxies systematically fail across models and natural language.”

REVISIONS
  - results/proxy_control_benchmark_v2_20260808/aggregate/result.json — state the primary result conjunctively: no method achieved eligible, cross-source, two-model recovery, sham specificity, and collateral safety at any concept/stage.
  - results/proxy_control_benchmark_v2_20260808/aggregate/result.json — describe relative-position oracle recovery as a positive but unsafe signal: hierarchical recovery 0.330 (95% interval 0.104–0.620), behavioral specificity 0.319 (0.090–0.673), and collateral KL 0.058 (0.019–0.131).
  - results/proxy_control_benchmark_v2_20260808/aggregate/result.json — distinguish representation specificity from behavioral control: task projection and linear erasure isolate relative-position changes geometrically (about 0.234–0.239) while recovering only about 0.008–0.011 of the behavioral effect.
  - results/proxy_control_benchmark_v2_20260808/aggregate/result.json — report proxy associations by method class. Linear captured variance predicts recovery/signed specificity but predicts worse collateral safety; learned probe recovery predicts potency while predicting worse representation-level intervention specificity; learned geometric stability is negatively associated with potency and intervention specificity.
  - results/proxy_control_benchmark_v2_20260808/aggregate/result.json — label the naturalistic QA endpoint ineligible/descriptive: average eligibility is approximately 0.65, below the frozen 0.80 threshold.
  - results/proxy_control_benchmark_v2_20260808/aggregate/result.json — do not call every failed gate an equivalence result; several confidence intervals are wide and some effects are materially positive. The supported negative concerns joint selective control.
  - reports/provenance/proxy_control_benchmark_v2/qwen_launch_recovery.json — disclose the pre-inference Qwen launch-shell recovery as an operational incident; it changed neither rows, code, thresholds, nor model arguments.

EVIDENCE CHECKED
  - configs/proxy_control_benchmark_v2/FREEZE.json — candidate inventory, thresholds, decision table, model revisions, and no-training rule were frozen before scientific forwards.
  - results/proxy_control_benchmark_v2_20260808/synthetic/result.json — ground-truth and behavior-gradient positive controls passed; random negative remained below its cap.
  - results/proxy_control_benchmark_v2_20260808/aggregate/COMPLETE.json — aggregate completed with result SHA-256 `f59b0a0fd3a2f12c764ba9e4977f151552b590c3518405899d0ffa9740c7315b`.
  - results/proxy_control_benchmark_v2_20260808/aggregate/result.json — 1,296 metric rows, 972 controlled rows, 324 naturalistic rows, nine model/layer clusters, 120 hierarchical summaries, and zero passing formal decisions.
  - results/proxy_control_benchmark_v2_20260808/shards/*/COMPLETE.json — all nine model/layer shards completed; no technical-failure or blocked terminal exists.
  - scripts/proxy_control_benchmark_v2.py and 17-test verification — signed effect alignment, component-block inference, class-specific associations, imported-checkpoint lineage, gate ordering, and hierarchical factors were exercised before opening.

UNKNOWNS
  - Whether the same potency–precision tradeoff replicates on genuinely natural held-out interventions rather than shared generated-panel grammar.
  - Whether a directly optimized supervised controller with an explicit collateral penalty can improve the Pareto frontier.
  - Whether other activation sites, attention-edge objects, nonlinear subspaces, or multi-layer controllers permit selective intervention.
