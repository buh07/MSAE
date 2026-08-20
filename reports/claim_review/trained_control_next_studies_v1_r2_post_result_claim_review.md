CLAIM: REVISE
SUMMARY: SAE localization is supported in the synthetic copy model; bridge and general-method claims remain unauthorized.

BLOCKERS
  - `results/causal_manifold_bridge_v1_r2_20260813/PRECONFIRMATION.json` — the all-cell exact/identity gate failed and confirmation stayed closed — no bridge method comparison, factorial effect, or discovery claim is established.
  - `results/trained_copy_sae_capacity_v1_r2_20260813/final/result.json` — the study covers three seeds of one trained synthetic copy-transformer design — claims about standard SAEs or pretrained language models generally would exceed the evidence.

REVISIONS
  - Report that all 1,440 sub-full SAE records failed and all 360 full-budget records passed, but note that the four selector labels are identical at budget 256 because every feature is retained.
  - Emphasize that rank-32 ambient PCA, output-oracle, and paired-linear controllers passed whereas rank 16 failed; this localizes the SAE result to feature-basis/selection rather than a high intrinsic controller rank.
  - Describe the bridge as a positive-control qualification failure: exact recovery, full-vocabulary recovery, necessity, and collateral safety were essentially perfect on supported cells, while 25/512 cells lacked support and control-margin uncertainty/non-specific random-direction effects prevented all-cell qualification.
  - Do not use the bridge development method rankings: they were measured, but the prospective lifecycle forbids method or factorial claims after exact-control qualification failed.

EVIDENCE CHECKED
  - `reports/provenance/trained_copy_sae_capacity_v1_r2_run_20260813/TERMINAL.json` and final artifact — terminal hash matched; confirmation completed.
  - Separate fit/development/confirmation shards versus embedded final records — exact equality; 323 methods per checkpoint/panel and all values finite.
  - SAE budget stratification — budgets 16/32/64/128: 0/360 records passed each; budget 256: 360/360 passed.
  - Linear baselines — rank-32/64 ambient PCA, output oracle, and paired linear passed across both panels and all three model seeds; rank 16 and random rank 16/32 failed.
  - SAE fit diagnostics — mean ambient reconstruction relative L2 was approximately 0.0032–0.0059 despite sub-full control failure.
  - `reports/provenance/causal_manifold_bridge_v1_r2_run_20260813/TERMINAL.json` and preconfirmation — development technical stop; confirmation unauthorized and absent.
  - Bridge sealed development shards — hashes matched; exact QA, view firewall, and incomplete-controller QA passed 512/512.
  - Bridge exact controls — exact passed 368/512 and identity 372/512; both passed 358/512. Both had support in 487/512, and supported failures were confined to the registered control-margin gate.

UNKNOWNS
  - Whether a redesigned bridge with prospectively guaranteed random-control separation would preserve these patterns.
  - Whether released SAEs or natural pretrained transformers show the same full-dictionary versus rank-32 gap.
