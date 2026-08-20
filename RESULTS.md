# MSAE Results

Last updated: 2026-08-02 (America/New_York)

This document is a factual index of MSAE experiment runs, statuses, result artifacts, and recorded metrics. It intentionally does not include analysis or interpretation.

## Atlas-v1 execution (2026-07-31 through 2026-08-01)

Status: complete through the preregistered architecture decision; blind final test not opened.

| Stage | Status | Primary artifacts |
|---|---|---|
| M0 provenance | complete with recorded limitations | [artifact readiness](reports/artifact_readiness.md), [registry](experiments/registry.csv), [K=2 comparison](reports/k2_postwave_comparison.md) |
| PCC reinterpretation | complete | [memo](analysis/pcc_reinterpretation.md), [synthesis](reports/pcc_historical_synthesis.md) |
| Label/shortcut inventory and four partitions | complete | [inventory](analysis/label_inventory/), [QA](reports/atlas_data_qa.md), [partition hashes](configs/atlas/partition_hashes.json) |
| Atlas preregistration/freeze | complete | [preregistration](prereg/separable_information_atlas_v1.md), freeze digest `e7c12f4407249ccc556c8f56234c8de36af01d29a89de525deed7506876c8c31` |
| Minimal synthetic metric test | 16 passed | [report](reports/synthetic_metric_smoke.md) |
| Raw L3/L4 atlas | complete; G1 equivocal | [report](reports/raw_atlas_results.md), [L3 JSON](results/atlas/raw_v1/L3_raw_atlas.json), [L4 JSON](results/atlas/raw_v1/L4_raw_atlas.json) |
| Existing K=2 audit | complete; G2 equivocal | [report](reports/k2_atlas_audit_results.md), [audit JSON](results/atlas/k2_v1/k2_audit.json) |
| Architecture/training decision | complete | [decision](reports/architecture_decision.md), [JSON](reports/architecture_decision.json) |

Raw primary-site L3 point values:

| Candidate/family | Recovery | Leakage | Selectivity margin |
|---|---:|---:|---:|
| split absolute | 0.930 | 1.065 | -0.135 |
| split structural | 0.863 | 0.989 | -0.126 |
| split lexical | 1.000 | 0.012 | +0.988 |
| broad absolute | 0.935 | 1.068 | -0.133 |
| broad structural | 0.979 | 0.991 | -0.013 |
| broad-complement lexical | 0.999 | 0.070 | +0.929 |

Existing K=2 point comparison:

| Checkpoint | K=2 macro selectivity | Simple comparator | Difference | C2 FVU |
|---|---:|---:|---:|---:|
| g4 | -0.103 | +0.304 | -0.407 | 0.0324 |
| g5 | -0.107 | +0.304 | -0.411 | 0.0504 |
| g6 | -0.146 | +0.304 | -0.450 | 0.0208 |
| g7 | -0.042 | +0.304 | -0.346 | 0.0258 |

Both gates are recorded as equivocal. A later frozen post-score completion attempt is summarized below; it stopped at the primary L3 minimum-complete-case gate, so it did not replace the original decision. No new model training was run or authorized.

## Atlas-v1 post-score completion attempt (2026-08-01 through 2026-08-02 UTC)

Status: partial completion with a frozen inferential-invalidity stop; blind final test not opened; no promoted completion decision.

| Stage | Status | Recorded result |
|---|---|---|
| Pilot v10 | complete | numerical and budget gates passed; `43.8532` projected GPU-hours; discovery/calibration roles only |
| Implementation review/freeze | complete | adversarial `SHIP`; candidate `2d2e50f0...`; completion freeze `0aac744d...` |
| Calibration baseline/Tier-2 eligibility | complete, selection failed | `projection_broad16` fallback; 8/9 sentinels eligible; 5/9 Tier-1 tasks eligible |
| Raw L3 500-draw refit | frozen stop | all 500 artifacts present; point finite; `414/500` scientifically finite; required `>=450` |
| Descriptive raw L4 500-draw refit | complete | point finite; `500/500` scientifically finite |
| K2 refits, stability, specificity, merge, verification, render | not launched | bound to the L3 stop by `NOT_LAUNCHED_UPSTREAM_STOP.json` |

The ineligible Tier-2 sentinel was `source_type` (point raw-minus-chance
`-0.06552`, 2.5th percentile `-0.07483`, threshold `0.02`). The four
ineligible Tier-1 tasks and their finite calibration counts were `abs_pos_16`
`316`, `abs_pos_8` `438`, `lemma_identity_256` `320`, and
`token_identity_256` `314`.

The 86 scientifically nonfinite L3 draws came from bootstrap omission of a
frozen truth class in required Tier-2 evaluations: UPOS affected 36 draws,
capitalization 32, and coarse dependency relation 21; the counts overlap in
three draws. The terminal therefore records
`stop_code=insufficient_scientifically_finite_draws`, no scientific retry, and
no decision promotion.

No amended G1a/G2a or `planning_decision_v2` was rendered. Original G1/G2 remain
equivocal and no paper branch or training run is authorized. Full disposition:
[reports/atlas_completion_results.md](reports/atlas_completion_results.md).

This base-root execution did not satisfy the frozen clause authorizing K2,
stability, and specificity diagnostics after G1a invalidity. The separately
reviewed additive continuation below subsequently executed and dispositioned
those analyses without changing this base-root record.

## Atlas-v1 additive diagnostic continuation and recovered summary (2026-08-02)

Status: all 16 registered GPU scoring jobs completed technically; four K2 stages
and stability stopped under their frozen scientific-validity rules; all four
specificity computations completed with invalid counterfactual gates. Candidate
and canonical summaries were independently reviewed, success-closed, and replay
verified. Blind final test not opened; no decision or training promoted.

| Item | Status | Recorded result |
|---|---|---|
| Additive continuation collection | closed | 9 registered stages; 16 jobs; every job `job_process_success` with exit code 0 |
| K2 discovery-refit inference | scientifically stopped | four point jobs plus `4 × 500` draw artifacts; every checkpoint `414/500` finite; required `>=450` |
| Tier-2 collateral | computed but not confirmatory | included in K2 point/draw outputs; complete-case gate failed |
| Cross-checkpoint stability | scientifically stopped | point nonfinite; `0/500` jointly finite draws |
| Matched-random/sham specificity | computation complete, gate invalid | four outputs; every `counterfactual_gate_valid=false` |
| Summary recovery implementation | reviewed/frozen | adversarial `SHIP`; implementation candidate `875479ca...`; recovery bundle `2a80a592...` |
| Candidate summary | reviewed/replay verified | content `a88a3708...`; terminal `88e3eef0...`; result and claim reviews `SHIP` |
| Canonical publication | complete | root `62ccdb28...`; terminal `frozen_equivocal_stop`; final `verify-only` passed |

The relative/structural stability point recorded learned mean pairwise CKA
`0.9982635047210163` and simple A/B CKA `1.0`. Because the joint point endpoint
was nonfinite and no draw was jointly finite, these values are descriptive
coordinates only, not stability evidence.

The continuation used `17.021625942461668` actual GPU-hours and `54.2` observed
reserved GPU-hours, within the frozen 192 GPU-hour ceiling. It did not change the
scientific disposition: original G1/G2 remain equivocal; G1a is
invalid/unrendered; G2a is not promotable/unrendered; the paper branch remains
unselected; training is not warranted by current evidence.

Primary artifacts:
- [canonical diagnostic report](results/atlas/completion_diagnostic_v1/diagnostic_results.md)
- [canonical diagnostic JSON](results/atlas/completion_diagnostic_v1/diagnostic_results.json)
- [canonical recovery provenance](results/atlas/completion_diagnostic_v1/RECOVERY_PROVENANCE.json)
- [continuation collection terminal](pilot_runs/20260802_atlas_completion_diagnostic_continuation_v1/COLLECTION_COMPLETE.json)
- [implementation review](reports/adversarial/atlas_completion_summary_recovery_implementation_review_20260802.md)
- [result review](reports/adversarial/atlas_completion_summary_recovery_result_review_20260802.md)
- [claim review](reports/adversarial/atlas_completion_summary_recovery_claim_review_20260802.md)

## Top-Level Report Packages

- Pre-K2 report bundle: [README.md](reports/pre_k2_suite_v6/README.md)
- Pre-K2 report digest: [RESULTS.md](reports/pre_k2_suite_v6/RESULTS.md)
- Pre-K2 aggregate table: [aggregate_results.tsv](reports/pre_k2_suite_v6/aggregate_results.tsv)
- Pre-K2 CI tables:
  - [ci_metrics.tsv](reports/pre_k2_suite_v6/ci_metrics.tsv)
  - [ci_metrics_iid.tsv](reports/pre_k2_suite_v6/ci_metrics_iid.tsv)
  - [ci_metrics_source_holdout.tsv](reports/pre_k2_suite_v6/ci_metrics_source_holdout.tsv)
  - [ci_metrics_corpus_holdout.tsv](reports/pre_k2_suite_v6/ci_metrics_corpus_holdout.tsv)
- Pre-K2 convergence table: [convergence_quality.tsv](reports/pre_k2_suite_v6/convergence_quality.tsv)
- Pre-K2 threshold sensitivity: [threshold_sensitivity.tsv](reports/pre_k2_suite_v6/threshold_sensitivity.tsv)
- Pre-K2 compatibility report: [compatibility_iid_v5_vs_v6.md](reports/pre_k2_suite_v6/compatibility_iid_v5_vs_v6.md)
- Pre-K2 decision artifacts:
  - [pre_k2_decision.md](reports/pre_k2_suite_v6/pre_k2_decision.md)
  - [pre_k2_decision.json](reports/pre_k2_suite_v6/pre_k2_decision.json)
- Pre-K2 control notes: [control_notes.md](reports/pre_k2_suite_v6/control_notes.md)

## Experiment Index

| Phase | Run | Status | Primary artifacts |
|---|---|---:|---|
| Raw-activation pilot | `20260526_201536` | complete | [manifest](pilot_runs/20260526_201536/run_manifest.tsv), [status](pilot_runs/20260526_201536/status_snapshot.json) |
| Raw-activation rerun (`saga3000`, `c2_alt`) | `20260526_224002_saga3000_c2alt` | partial | [manifest](pilot_runs/20260526_224002_saga3000_c2alt/run_manifest.tsv), [status](pilot_runs/20260526_224002_saga3000_c2alt/status_snapshot.json) |
| Torch GPU probes | `20260527_124434_torch_gpu_probes` | complete | [aggregate](pilot_runs/20260527_124434_torch_gpu_probes/aggregate_results.tsv), [manifest](pilot_runs/20260527_124434_torch_gpu_probes/run_manifest.tsv), [status](pilot_runs/20260527_124434_torch_gpu_probes/status_snapshot.json) |
| Rank-curve launcher attempt | `20260527_140213_rankcurve_c2var_balanced` | launcher-only | [manifest](pilot_runs/20260527_140213_rankcurve_c2var_balanced/run_manifest.tsv) |
| Rank-curve balanced | `20260527_140327_rankcurve_c2var_balanced` | complete | [aggregate](pilot_runs/20260527_140327_rankcurve_c2var_balanced/aggregate_results.tsv), [manifest](pilot_runs/20260527_140327_rankcurve_c2var_balanced/run_manifest.tsv), [status](pilot_runs/20260527_140327_rankcurve_c2var_balanced/status_snapshot.json) |
| v5 balanced multiseed | `20260527_210247_v5_gpufirst_balanced_multiseed` | complete | [aggregate](pilot_runs/20260527_210247_v5_gpufirst_balanced_multiseed/aggregate_results.tsv), [manifest](pilot_runs/20260527_210247_v5_gpufirst_balanced_multiseed/run_manifest.tsv), [status](pilot_runs/20260527_210247_v5_gpufirst_balanced_multiseed/status_snapshot.json) |
| v6 pre-K2 full suite attempt 1 | `20260528_001028_v6_prek2_fullsuite` | partial | [decision.md](pilot_runs/20260528_001028_v6_prek2_fullsuite/pre_k2_decision.md), [decision.json](pilot_runs/20260528_001028_v6_prek2_fullsuite/pre_k2_decision.json), [manifest](pilot_runs/20260528_001028_v6_prek2_fullsuite/run_manifest.tsv), [status](pilot_runs/20260528_001028_v6_prek2_fullsuite/status_snapshot.json) |
| v6 pre-K2 full suite attempt 2 | `20260528_001131_v6_prek2_fullsuite` | partial | [decision.md](pilot_runs/20260528_001131_v6_prek2_fullsuite/pre_k2_decision.md), [decision.json](pilot_runs/20260528_001131_v6_prek2_fullsuite/pre_k2_decision.json), [manifest](pilot_runs/20260528_001131_v6_prek2_fullsuite/run_manifest.tsv), [status](pilot_runs/20260528_001131_v6_prek2_fullsuite/status_snapshot.json) |
| v6 pre-K2 full suite final | `20260528_001543_v6_prek2_fullsuite` | complete | [aggregate](pilot_runs/20260528_001543_v6_prek2_fullsuite/aggregate_results.tsv), [decision.md](pilot_runs/20260528_001543_v6_prek2_fullsuite/pre_k2_decision.md), [decision.json](pilot_runs/20260528_001543_v6_prek2_fullsuite/pre_k2_decision.json), [status](pilot_runs/20260528_001543_v6_prek2_fullsuite/status_snapshot.json) |
| v5-compatible IID compatibility sweep | `20260528_132545_compat_v5_iid` | complete | [aggregate](pilot_runs/20260528_132545_compat_v5_iid/aggregate_results.tsv), [decision.md](pilot_runs/20260528_132545_compat_v5_iid/pre_k2_decision.md), [decision.json](pilot_runs/20260528_132545_compat_v5_iid/pre_k2_decision.json), [status](pilot_runs/20260528_132545_compat_v5_iid/status_snapshot.json) |
| K=2 smoke test | `_k2_smoke_test` | complete | [summary](pilot_runs/_k2_smoke_test/train_summary.json), [metrics](pilot_runs/_k2_smoke_test/train_metrics.jsonl) |
| K=2 resume test | `_k2_resume_test` | complete | [phase1 summary](pilot_runs/_k2_resume_test/phase1/train_summary.json), [phase2 summary](pilot_runs/_k2_resume_test/phase2/train_summary.json) |
| K=2 wave1 | `20260528_142003_k2_msae_wave1` | complete | [decision.md](pilot_runs/20260528_142003_k2_msae_wave1/reports/k2_wave1_decision.md), [decision.json](pilot_runs/20260528_142003_k2_msae_wave1/reports/k2_wave1_decision.json), [manifest](pilot_runs/20260528_142003_k2_msae_wave1/run_manifest.tsv) |
| K=2 wave2 smoke | `20260529_000001_smoke_k2_msae_wave2` | complete | [status.md](pilot_runs/20260529_000001_smoke_k2_msae_wave2/reports/wave2_status.md), [status.json](pilot_runs/20260529_000001_smoke_k2_msae_wave2/reports/wave2_status_snapshot.json), [manifest](pilot_runs/20260529_000001_smoke_k2_msae_wave2/run_manifest.tsv) |
| K=2 wave2 initial long run | `20260529_122259_k2_msae_wave2` | superseded | [status.md](pilot_runs/20260529_122259_k2_msae_wave2/reports/wave2_status.md), [status.json](pilot_runs/20260529_122259_k2_msae_wave2/reports/wave2_status_snapshot.json), [manifest](pilot_runs/20260529_122259_k2_msae_wave2/run_manifest.tsv) |
| K=2 fastdata launch attempt | `20260601_131703_k2_msae_wave2_fastdata` | empty launch dir | run dir only |
| K=2 fastdata launch attempt | `20260601_131736_k2_msae_wave2_fastdata` | logs only | [launch_info](pilot_runs/20260601_131736_k2_msae_wave2_fastdata/launch_info.txt) |
| K=2 wave2 fastdata stream | `20260601_132158_k2_msae_wave2_fastdata_stream` | complete | [manifest](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/run_manifest.tsv), [g4 summary](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g4_L3_s42_inc1e2/train_summary.json), [g5 summary](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g5_L3_s43_inc1e2/train_summary.json), [g6 summary](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g6_L3_s44_inc1e2/train_summary.json), [g7 summary](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g7_L3_s42_inc0/train_summary.json) |

## Raw-Activation Pilot Series

### 1. Initial 4-GPU raw-activation pilot

Run root: [20260526_201536](pilot_runs/20260526_201536)

Status: complete per-model artifact set

Scope recorded in [run_manifest.tsv](pilot_runs/20260526_201536/run_manifest.tsv):
- `g4`: `EleutherAI/pythia-14m-deduped`, layer `3`, ranks `8,16`
- `g5`: `EleutherAI/pythia-70m-deduped`, layer `4`, ranks `8,16`
- `g6`: `gpt2`, layer `4`, rank `8`
- `g7`: `EleutherAI/pythia-160m-deduped`, layer `4`, rank `8`

Result artifacts:
- [status_snapshot.json](pilot_runs/20260526_201536/status_snapshot.json)
- [g4 raw_sep_summary.json](pilot_runs/20260526_201536/outputs/g4_pythia14m/raw_sep_summary.json)
- [g4 raw_sep_rank_table.csv](pilot_runs/20260526_201536/outputs/g4_pythia14m/raw_sep_rank_table.csv)
- [g5 raw_sep_summary.json](pilot_runs/20260526_201536/outputs/g5_pythia70m/raw_sep_summary.json)
- [g5 raw_sep_rank_table.csv](pilot_runs/20260526_201536/outputs/g5_pythia70m/raw_sep_rank_table.csv)
- [g6 raw_sep_summary.json](pilot_runs/20260526_201536/outputs/g6_gpt2/raw_sep_summary.json)
- [g6 raw_sep_rank_table.csv](pilot_runs/20260526_201536/outputs/g6_gpt2/raw_sep_rank_table.csv)
- [g7 raw_sep_summary.json](pilot_runs/20260526_201536/outputs/g7_pythia160m/raw_sep_summary.json)
- [g7 raw_sep_rank_table.csv](pilot_runs/20260526_201536/outputs/g7_pythia160m/raw_sep_rank_table.csv)

### 2. `saga3000` rerun with additive `c2_alt`

Run root: [20260526_224002_saga3000_c2alt](pilot_runs/20260526_224002_saga3000_c2alt)

Status: partial artifact set

Recorded launcher artifacts:
- [run_manifest.tsv](pilot_runs/20260526_224002_saga3000_c2alt/run_manifest.tsv)
- [status_snapshot.json](pilot_runs/20260526_224002_saga3000_c2alt/status_snapshot.json)

Final result artifacts present:
- [g4 raw_sep_summary.json](pilot_runs/20260526_224002_saga3000_c2alt/outputs/g4_pythia14m/raw_sep_summary.json)
- [g4 raw_sep_rank_table.csv](pilot_runs/20260526_224002_saga3000_c2alt/outputs/g4_pythia14m/raw_sep_rank_table.csv)
- [smoke raw_sep_summary.json](pilot_runs/20260526_224002_saga3000_c2alt/outputs/smoke/raw_sep_summary.json)
- [smoke raw_sep_rank_table.csv](pilot_runs/20260526_224002_saga3000_c2alt/outputs/smoke/raw_sep_rank_table.csv)

### 3. Torch GPU probes

Run root: [20260527_124434_torch_gpu_probes](pilot_runs/20260527_124434_torch_gpu_probes)

Status: complete

Aggregate results:
- total rows: `4`
- `all_pass`: `0/4`
- `all_pass_alt_c2`: `0/4`
- `c4`: `4/4`

Aggregate artifacts:
- [aggregate_results.tsv](pilot_runs/20260527_124434_torch_gpu_probes/aggregate_results.tsv)
- [run_manifest.tsv](pilot_runs/20260527_124434_torch_gpu_probes/run_manifest.tsv)
- [status_snapshot.json](pilot_runs/20260527_124434_torch_gpu_probes/status_snapshot.json)

Per-run result artifacts:
- [g5 pythia-70m summary](pilot_runs/20260527_124434_torch_gpu_probes/outputs/g5_pythia70m/raw_sep_summary.json), [rank table](pilot_runs/20260527_124434_torch_gpu_probes/outputs/g5_pythia70m/raw_sep_rank_table.csv)
- [g6 gpt2 summary](pilot_runs/20260527_124434_torch_gpu_probes/outputs/g6_gpt2/raw_sep_summary.json), [rank table](pilot_runs/20260527_124434_torch_gpu_probes/outputs/g6_gpt2/raw_sep_rank_table.csv)
- [g7 pythia-160m summary](pilot_runs/20260527_124434_torch_gpu_probes/outputs/g7_pythia160m/raw_sep_summary.json), [rank table](pilot_runs/20260527_124434_torch_gpu_probes/outputs/g7_pythia160m/raw_sep_rank_table.csv)

### 4. Rank-curve launcher attempt

Run root: [20260527_140213_rankcurve_c2var_balanced](pilot_runs/20260527_140213_rankcurve_c2var_balanced)

Status: launcher-only

Artifacts present:
- [run_manifest.tsv](pilot_runs/20260527_140213_rankcurve_c2var_balanced/run_manifest.tsv)
- [commands/g4.sh](pilot_runs/20260527_140213_rankcurve_c2var_balanced/commands/g4.sh)

### 5. Rank-curve balanced run

Run root: [20260527_140327_rankcurve_c2var_balanced](pilot_runs/20260527_140327_rankcurve_c2var_balanced)

Status: complete

Aggregate results:
- total rows: `34`
- `c1_new_rank_recovery`: `34/34`
- `c4`: `34/34`
- `all_pass`: `0/34`
- `all_pass_alt_c2`: `0/34`
- `all_pass_recovery_var`: `0/34`
- `all_pass_v2`: `0/34`

Aggregate artifacts:
- [aggregate_results.tsv](pilot_runs/20260527_140327_rankcurve_c2var_balanced/aggregate_results.tsv)
- [run_manifest.tsv](pilot_runs/20260527_140327_rankcurve_c2var_balanced/run_manifest.tsv)
- [status_snapshot.json](pilot_runs/20260527_140327_rankcurve_c2var_balanced/status_snapshot.json)

Per-run output directories:
- [g4_pythia14m_layer2](pilot_runs/20260527_140327_rankcurve_c2var_balanced/outputs/g4_pythia14m_layer2)
- [g4_pythia14m_layer4](pilot_runs/20260527_140327_rankcurve_c2var_balanced/outputs/g4_pythia14m_layer4)
- [g5_pythia70m_layer4](pilot_runs/20260527_140327_rankcurve_c2var_balanced/outputs/g5_pythia70m_layer4)
- [g6_gpt2_layer4](pilot_runs/20260527_140327_rankcurve_c2var_balanced/outputs/g6_gpt2_layer4)
- [g7_pythia160m_layer1](pilot_runs/20260527_140327_rankcurve_c2var_balanced/outputs/g7_pythia160m_layer1)
- [g7_pythia160m_layer2](pilot_runs/20260527_140327_rankcurve_c2var_balanced/outputs/g7_pythia160m_layer2)
- [g7_pythia160m_layer3](pilot_runs/20260527_140327_rankcurve_c2var_balanced/outputs/g7_pythia160m_layer3)
- [g7_pythia160m_layer4](pilot_runs/20260527_140327_rankcurve_c2var_balanced/outputs/g7_pythia160m_layer4)

### 6. v5 GPU-first balanced multiseed

Run root: [20260527_210247_v5_gpufirst_balanced_multiseed](pilot_runs/20260527_210247_v5_gpufirst_balanced_multiseed)

Status: complete

Aggregate results:
- total rows: `54`
- `c1_new_rank_recovery`: `54/54`
- `c2_var_v2`: `35/54`
- `c3_v2`: `26/54`
- `c4`: `54/54`
- `all_pass_v2`: `22/54`

`all_pass_v2` pass ranks by output directory:
- `g4_pythia14m_s42_layer2`: `4, 8`
- `g4_pythia14m_s42_layer4`: none
- `g5_pythia70m_s42_layer4`: `4, 8, 16`
- `g6_gpt2_s42_layer4`: `8, 16`
- `g5_pythia160m_s43_layer2`: `8`
- `g5_pythia160m_s43_layer3`: `8, 16`
- `g5_pythia160m_s43_layer4`: `8, 16`
- `g6_pythia160m_s44_layer2`: `8`
- `g6_pythia160m_s44_layer3`: `8, 16`
- `g6_pythia160m_s44_layer4`: `8, 16`
- `g7_pythia160m_s42_layer2`: `8`
- `g7_pythia160m_s42_layer3`: `8, 16`
- `g7_pythia160m_s42_layer4`: `8, 16`

Artifacts:
- [aggregate_results.tsv](pilot_runs/20260527_210247_v5_gpufirst_balanced_multiseed/aggregate_results.tsv)
- [run_manifest.tsv](pilot_runs/20260527_210247_v5_gpufirst_balanced_multiseed/run_manifest.tsv)
- [status_snapshot.json](pilot_runs/20260527_210247_v5_gpufirst_balanced_multiseed/status_snapshot.json)
- [outputs directory](pilot_runs/20260527_210247_v5_gpufirst_balanced_multiseed/outputs)

## Pre-K2 Full-Suite Runs

### 7. v6 pre-K2 full suite attempt 1

Run root: [20260528_001028_v6_prek2_fullsuite](pilot_runs/20260528_001028_v6_prek2_fullsuite)

Status: partial

Artifacts present:
- [pre_k2_decision.md](pilot_runs/20260528_001028_v6_prek2_fullsuite/pre_k2_decision.md)
- [pre_k2_decision.json](pilot_runs/20260528_001028_v6_prek2_fullsuite/pre_k2_decision.json)
- [threshold_sensitivity.tsv](pilot_runs/20260528_001028_v6_prek2_fullsuite/threshold_sensitivity.tsv)
- [run_manifest.tsv](pilot_runs/20260528_001028_v6_prek2_fullsuite/run_manifest.tsv)
- [status_snapshot.json](pilot_runs/20260528_001028_v6_prek2_fullsuite/status_snapshot.json)

### 8. v6 pre-K2 full suite attempt 2

Run root: [20260528_001131_v6_prek2_fullsuite](pilot_runs/20260528_001131_v6_prek2_fullsuite)

Status: partial

Artifacts present:
- [pre_k2_decision.md](pilot_runs/20260528_001131_v6_prek2_fullsuite/pre_k2_decision.md)
- [pre_k2_decision.json](pilot_runs/20260528_001131_v6_prek2_fullsuite/pre_k2_decision.json)
- [threshold_sensitivity.tsv](pilot_runs/20260528_001131_v6_prek2_fullsuite/threshold_sensitivity.tsv)
- [run_manifest.tsv](pilot_runs/20260528_001131_v6_prek2_fullsuite/run_manifest.tsv)
- [status_snapshot.json](pilot_runs/20260528_001131_v6_prek2_fullsuite/status_snapshot.json)

### 9. v6 pre-K2 full suite final

Run root: [20260528_001543_v6_prek2_fullsuite](pilot_runs/20260528_001543_v6_prek2_fullsuite)

Status: complete

Aggregate result counts:
- total aggregate rows: `152`
- `all_pass_v2`: `97/152`
- `c1_new_rank_recovery`: `152/152`
- `c2_var_v2`: `98/152`
- `c3_v2`: `129/152`
- `c4`: `152/152`

Reported in [reports/pre_k2_suite_v6/RESULTS.md](reports/pre_k2_suite_v6/RESULTS.md):
- primary recommendation: `L3`
- fallback recommendation: `L4`
- headline ranks: `8, 16`
- boundary diagnostic rank: `32`
- headline all-pass-v2 rate (`Pythia-160M`, `r8/r16`, all split modes): `92/92`
- boundary all-pass-v2 rate (`Pythia-160M`, `r32`, all split modes): `0/46`

`Pythia-160M` `all_pass_v2` counts from [aggregate_results.tsv](pilot_runs/20260528_001543_v6_prek2_fullsuite/aggregate_results.tsv):
- IID, `L3`, `r8`: `5/5`
- IID, `L3`, `r16`: `5/5`
- IID, `L3`, `r32`: `0/5`
- IID, `L4`, `r8`: `5/5`
- IID, `L4`, `r16`: `5/5`
- IID, `L4`, `r32`: `0/5`
- Source-holdout, `L3`, `r8`: `15/15`
- Source-holdout, `L3`, `r16`: `15/15`
- Source-holdout, `L3`, `r32`: `0/15`
- Source-holdout, `L4`, `r8`: `15/15`
- Source-holdout, `L4`, `r16`: `15/15`
- Source-holdout, `L4`, `r32`: `0/15`
- Corpus-holdout, `L3`, `r8`: `3/3`
- Corpus-holdout, `L3`, `r16`: `3/3`
- Corpus-holdout, `L3`, `r32`: `0/3`
- Corpus-holdout, `L4`, `r8`: `3/3`
- Corpus-holdout, `L4`, `r16`: `3/3`
- Corpus-holdout, `L4`, `r32`: `0/3`

Artifacts:
- [aggregate_results.tsv](pilot_runs/20260528_001543_v6_prek2_fullsuite/aggregate_results.tsv)
- [ci_metrics.tsv](pilot_runs/20260528_001543_v6_prek2_fullsuite/ci_metrics.tsv)
- [ci_metrics_iid.tsv](pilot_runs/20260528_001543_v6_prek2_fullsuite/ci_metrics_iid.tsv)
- [ci_metrics_source_holdout.tsv](pilot_runs/20260528_001543_v6_prek2_fullsuite/ci_metrics_source_holdout.tsv)
- [ci_metrics_corpus_holdout.tsv](pilot_runs/20260528_001543_v6_prek2_fullsuite/ci_metrics_corpus_holdout.tsv)
- [pre_k2_decision.md](pilot_runs/20260528_001543_v6_prek2_fullsuite/pre_k2_decision.md)
- [pre_k2_decision.json](pilot_runs/20260528_001543_v6_prek2_fullsuite/pre_k2_decision.json)
- [run_manifest.tsv](pilot_runs/20260528_001543_v6_prek2_fullsuite/run_manifest.tsv)
- [status_snapshot.json](pilot_runs/20260528_001543_v6_prek2_fullsuite/status_snapshot.json)
- [outputs directory](pilot_runs/20260528_001543_v6_prek2_fullsuite/outputs)

### 10. v5-compatible IID compatibility sweep

Run root: [20260528_132545_compat_v5_iid](pilot_runs/20260528_132545_compat_v5_iid)

Status: complete

Aggregate result counts:
- total rows: `30`
- `all_pass_v2`: `20/30`
- `c1_new_rank_recovery`: `30/30`
- `c2_var_v2`: `27/30`
- `c3_v2`: `20/30`
- `c4`: `30/30`

Compatibility artifacts:
- [aggregate_results.tsv](pilot_runs/20260528_132545_compat_v5_iid/aggregate_results.tsv)
- [ci_metrics.tsv](pilot_runs/20260528_132545_compat_v5_iid/ci_metrics.tsv)
- [ci_metrics_iid.tsv](pilot_runs/20260528_132545_compat_v5_iid/ci_metrics_iid.tsv)
- [pre_k2_decision.md](pilot_runs/20260528_132545_compat_v5_iid/pre_k2_decision.md)
- [pre_k2_decision.json](pilot_runs/20260528_132545_compat_v5_iid/pre_k2_decision.json)
- [status_snapshot.json](pilot_runs/20260528_132545_compat_v5_iid/status_snapshot.json)
- [compatibility_iid_v5_vs_v6.md](reports/pre_k2_suite_v6/compatibility_iid_v5_vs_v6.md)
- [outputs directory](pilot_runs/20260528_132545_compat_v5_iid/outputs)

## K=2 Training Validation Runs

### 11. K=2 smoke test

Run root: [_k2_smoke_test](pilot_runs/_k2_smoke_test)

Status: complete

Recorded in [train_summary.json](pilot_runs/_k2_smoke_test/train_summary.json):
- layer: `3`
- seed: `42`
- `lambda_inc`: `0.01`
- tokens seen: `20,011`
- throughput: `861.997 tok/s`
- final checkpoint: [final_step79_tok20011.pt](pilot_runs/_k2_smoke_test/checkpoints/final_step79_tok20011.pt)

### 12. K=2 resume test

Run root: [_k2_resume_test](pilot_runs/_k2_resume_test)

Status: complete

Recorded in [phase1/train_summary.json](pilot_runs/_k2_resume_test/phase1/train_summary.json):
- layer: `2`
- seed: `42`
- `lambda_inc`: `0.01`
- tokens seen: `30,010`
- throughput: `1378.478 tok/s`
- final checkpoint: [final_step120_tok30010.pt](pilot_runs/_k2_resume_test/phase1/checkpoints/final_step120_tok30010.pt)

Recorded in [phase2/train_summary.json](pilot_runs/_k2_resume_test/phase2/train_summary.json):
- layer: `2`
- seed: `42`
- `lambda_inc`: `0.01`
- tokens seen: `40,015`
- throughput: `4974.754 tok/s`
- final checkpoint: [final_step160_tok40015.pt](pilot_runs/_k2_resume_test/phase2/checkpoints/final_step160_tok40015.pt)

## K=2 Wave 1

### 13. K=2 wave1 100M-token run

Run root: [20260528_142003_k2_msae_wave1](pilot_runs/20260528_142003_k2_msae_wave1)

Status: complete

Decision artifact [k2_wave1_decision.md](pilot_runs/20260528_142003_k2_msae_wave1/reports/k2_wave1_decision.md) records:
- target tokens: `100,000,000`
- wave2 target tokens: `1,000,000,000`
- dead-fraction fail threshold: `0.6`

Job outcomes recorded in the decision artifact:
- `k2_wave1_g4_L3_s42_inc1e2`: status `done`, stable `True`, tokens `100000039`, throughput `1604.8`
- `k2_wave1_g5_L3_s43_inc1e2`: status `done`, stable `True`, tokens `100000039`, throughput `1605.0`
- `k2_wave1_g6_L4_s42_inc1e2`: status `done`, stable `True`, tokens `100000039`, throughput `1605.0`
- `k2_wave1_g7_L3_s42_inc0`: status `done`, stable `True`, tokens `100000039`, throughput `1605.0`

Promoted checkpoints listed by the decision artifact:
- [g4 final_step24663_tok100000039.pt](pilot_runs/20260528_142003_k2_msae_wave1/outputs/k2_wave1_g4_L3_s42_inc1e2/checkpoints/final_step24663_tok100000039.pt)
- [g5 final_step24663_tok100000039.pt](pilot_runs/20260528_142003_k2_msae_wave1/outputs/k2_wave1_g5_L3_s43_inc1e2/checkpoints/final_step24663_tok100000039.pt)
- [g7 final_step24663_tok100000039.pt](pilot_runs/20260528_142003_k2_msae_wave1/outputs/k2_wave1_g7_L3_s42_inc0/checkpoints/final_step24663_tok100000039.pt)

Wave1 artifacts:
- [run_manifest.tsv](pilot_runs/20260528_142003_k2_msae_wave1/run_manifest.tsv)
- [k2_wave1_decision.md](pilot_runs/20260528_142003_k2_msae_wave1/reports/k2_wave1_decision.md)
- [k2_wave1_decision.json](pilot_runs/20260528_142003_k2_msae_wave1/reports/k2_wave1_decision.json)
- [outputs directory](pilot_runs/20260528_142003_k2_msae_wave1/outputs)

## K=2 Wave 2

### 14. Wave2 smoke run

Run root: [20260529_000001_smoke_k2_msae_wave2](pilot_runs/20260529_000001_smoke_k2_msae_wave2)

Status: complete

Status snapshot [wave2_status.md](pilot_runs/20260529_000001_smoke_k2_msae_wave2/reports/wave2_status.md) records:
- `k2_wave1_g4_L3_s42_inc1e2_wave2`: tokens `102000007`, `tail100_fvu=0.1144`, `tail100_incoh=0.0602`
- `k2_wave1_g5_L3_s43_inc1e2_wave2`: tokens `102000007`, `tail100_fvu=0.1219`, `tail100_incoh=0.0556`
- `k2_wave1_g7_L3_s42_inc0_wave2`: tokens `102000007`, `tail100_fvu=0.1172`, `tail100_incoh=0.2123`

Artifacts:
- [wave2_status.md](pilot_runs/20260529_000001_smoke_k2_msae_wave2/reports/wave2_status.md)
- [wave2_status_snapshot.json](pilot_runs/20260529_000001_smoke_k2_msae_wave2/reports/wave2_status_snapshot.json)
- [g4 summary](pilot_runs/20260529_000001_smoke_k2_msae_wave2/outputs/k2_wave1_g4_L3_s42_inc1e2_wave2/train_summary.json)
- [g5 summary](pilot_runs/20260529_000001_smoke_k2_msae_wave2/outputs/k2_wave1_g5_L3_s43_inc1e2_wave2/train_summary.json)
- [g7 summary](pilot_runs/20260529_000001_smoke_k2_msae_wave2/outputs/k2_wave1_g7_L3_s42_inc0_wave2/train_summary.json)

### 15. Wave2 initial long run

Run root: [20260529_122259_k2_msae_wave2](pilot_runs/20260529_122259_k2_msae_wave2)

Status: superseded

Status snapshot [wave2_status.md](pilot_runs/20260529_122259_k2_msae_wave2/reports/wave2_status.md) records:
- generated: `2026-06-01T17:16:09Z`
- regression trigger: `True`
- `k2_wave1_g4_L3_s42_inc1e2_wave2`: tokens `407529691`, `tail100_fvu=0.4083`, `tail100_incoh=0.1072`, `quality_ok=False`
- `k2_wave1_g5_L3_s43_inc1e2_wave2`: tokens `407529691`, `tail100_fvu=0.3674`, `tail100_incoh=0.1030`, `quality_ok=False`
- `k2_wave1_g7_L3_s42_inc0_wave2`: tokens `407529691`, `tail100_fvu=0.2873`, `tail100_incoh=0.2198`, `quality_ok=True`
- `k2_wave2_g6_L3_s44_inc1e2_fresh`: tokens `307460612`, `tail100_fvu=0.3035`, `tail100_incoh=0.1122`, `quality_ok=False`

Artifacts:
- [wave2_status.md](pilot_runs/20260529_122259_k2_msae_wave2/reports/wave2_status.md)
- [wave2_status_snapshot.json](pilot_runs/20260529_122259_k2_msae_wave2/reports/wave2_status_snapshot.json)
- [run_manifest.tsv](pilot_runs/20260529_122259_k2_msae_wave2/run_manifest.tsv)
- [outputs directory](pilot_runs/20260529_122259_k2_msae_wave2/outputs)

### 16. Fastdata launch attempts

Run roots:
- [20260601_131703_k2_msae_wave2_fastdata](pilot_runs/20260601_131703_k2_msae_wave2_fastdata)
- [20260601_131736_k2_msae_wave2_fastdata](pilot_runs/20260601_131736_k2_msae_wave2_fastdata)

Status:
- `20260601_131703_k2_msae_wave2_fastdata`: empty launch directory
- `20260601_131736_k2_msae_wave2_fastdata`: launch info and logs present

Artifacts present in `20260601_131736_k2_msae_wave2_fastdata`:
- [launch_info.txt](pilot_runs/20260601_131736_k2_msae_wave2_fastdata/launch_info.txt)
- [g4 log](pilot_runs/20260601_131736_k2_msae_wave2_fastdata/logs/k2_wave2_fast_g4_L3_s42_inc1e2.log)
- [g5 log](pilot_runs/20260601_131736_k2_msae_wave2_fastdata/logs/k2_wave2_fast_g5_L3_s43_inc1e2.log)
- [g6 log](pilot_runs/20260601_131736_k2_msae_wave2_fastdata/logs/k2_wave2_fast_g6_L3_s44_inc1e2.log)
- [g7 log](pilot_runs/20260601_131736_k2_msae_wave2_fastdata/logs/k2_wave2_fast_g7_L3_s42_inc0.log)

### 17. Wave2 fastdata stream run

Run root: [20260601_132158_k2_msae_wave2_fastdata_stream](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream)

Status as checked on 2026-06-04:
- `g4`: complete
- `g5`: complete
- `g6`: complete
- `g7`: complete

Completed job summaries:

| Job | Layer | Seed | `lambda_inc` | Tokens | Tail-100 FVU | Tail-500 FVU | Tail-100 incoh | Tail-500 incoh | Tail-100 active pos | Tail-100 active content | Summary |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `g4` | 3 | 42 | 0.01 | 1,000,000,016 | 0.076385 | 0.080254 | 0.004643 | 0.005319 | 0.887024 | 0.911224 | [train_summary.json](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g4_L3_s42_inc1e2/train_summary.json) |
| `g5` | 3 | 43 | 0.01 | 1,000,000,016 | 0.071359 | 0.071459 | 0.003150 | 0.003587 | 0.897339 | 0.925735 | [train_summary.json](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g5_L3_s43_inc1e2/train_summary.json) |
| `g6` | 3 | 44 | 0.01 | 1,000,000,042 | 0.073543 | 0.077025 | 0.002811 | 0.002758 | 0.895935 | 0.934631 | [train_summary.json](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g6_L3_s44_inc1e2/train_summary.json) |
| `g7` | 3 | 42 | 0.00 | 1,000,000,016 | 0.069778 | 0.070882 | 0.015200 | 0.017394 | 0.923279 | 0.929779 | [train_summary.json](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g7_L3_s42_inc0/train_summary.json) |

Additional final metric snapshots from [train_summary.json](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g4_L3_s42_inc1e2/train_summary.json) files:
- `g4`: tail-100 slopes `fvu=-1.29e-05`, `incoh=-3.42e-06`
- `g5`: tail-100 slopes `fvu=2.98e-05`, `incoh=-1.52e-06`
- `g6`: tail-100 slopes `fvu=-3.81e-05`, `incoh=-7.79e-07`
- `g7`: tail-100 slopes `fvu=1.34e-07`, `incoh=-1.04e-05`

Artifacts:
- [run_manifest.tsv](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/run_manifest.tsv)
- [g4 metrics](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g4_L3_s42_inc1e2/train_metrics.jsonl)
- [g4 summary](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g4_L3_s42_inc1e2/train_summary.json)
- [g5 metrics](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g5_L3_s43_inc1e2/train_metrics.jsonl)
- [g5 summary](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g5_L3_s43_inc1e2/train_summary.json)
- [g6 metrics](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g6_L3_s44_inc1e2/train_metrics.jsonl)
- [g6 summary](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g6_L3_s44_inc1e2/train_summary.json)
- [g7 metrics](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g7_L3_s42_inc0/train_metrics.jsonl)
- [g7 summary](pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g7_L3_s42_inc0/train_summary.json)

## Schema and Auxiliary Smoke Artifacts

Raw-activation schema smoke artifacts:
- [_smoke_gpu_probe_20260527 summary](pilot_runs/_smoke_gpu_probe_20260527/raw_sep_summary.json)
- [_smoke_gpu_probe_20260527 rank table](pilot_runs/_smoke_gpu_probe_20260527/raw_sep_rank_table.csv)
- [_smoke_v4_schema_20260527 summary](pilot_runs/_smoke_v4_schema_20260527/raw_sep_summary.json)
- [_smoke_v4_schema_20260527 rank table](pilot_runs/_smoke_v4_schema_20260527/raw_sep_rank_table.csv)
- [_smoke_v5_schema_20260527_205921 summary](pilot_runs/_smoke_v5_schema_20260527_205921/raw_sep_summary.json)
- [_smoke_v5_schema_20260527_205921 rank table](pilot_runs/_smoke_v5_schema_20260527_205921/raw_sep_rank_table.csv)
- [_smoke_v5_schema2_20260527_210207 summary](pilot_runs/_smoke_v5_schema2_20260527_210207/raw_sep_summary.json)
- [_smoke_v5_schema2_20260527_210207 rank table](pilot_runs/_smoke_v5_schema2_20260527_210207/raw_sep_rank_table.csv)

## Result File Conventions

Common artifact types used across runs:
- `run_manifest.tsv`: launch matrix or job manifest
- `status_snapshot.json`: launcher/runtime status snapshot
- `aggregate_results.tsv`: per-row aggregate metric table for pilot runs
- `raw_sep_summary.json`: per-job raw-activation summary
- `raw_sep_rank_table.csv`: per-job rank table
- `train_metrics.jsonl`: stepwise training log
- `train_summary.json`: finalized training summary for completed jobs
- `pre_k2_decision.md` / `pre_k2_decision.json`: pre-K2 decision outputs
- `k2_wave1_decision.md` / `k2_wave1_decision.json`: wave1 promotion outputs
- `wave2_status.md` / `wave2_status_snapshot.json`: wave2 monitoring outputs
