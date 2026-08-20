# TODO.md — End-to-End Execution Plan for MSAE Program

## Scope
This TODO operationalizes `MSAE_revised.md` into concrete implementation, experiment, evaluation, and publication tasks for:
- Paper 1: K=2 position-vs-content MSAE on Pythia-160M.
- Paper 2: K=3 generalized MSAE with dense dark-matter branch on Gemma-2-2B.
- Paper 3: Structured branches (subspace + multiscale) on top of Paper 2.

All tasks are written to support strict reproducibility, pre-declared thresholds, and clear decision gates.

---

## Status Snapshot (2026-06-05)

### Completed / Locked
- [x] Pre-K2 separability suite (`v6`) completed and archived under `reports/pre_k2_suite_v6/`.
- [x] Pre-K2 governance artifacts committed and tagged:
  - `prereg-v6`
  - `pre-k2-suite-v6`
  - `k2-launch-v1`
  - `k2-launch-v2`
- [x] Paper 1 pre-K2 decision locked:
  - primary layer `L3`
  - fallback layer `L4`
  - headline ranks `{8, 16}`
  - rank `32` treated as boundary diagnostic only
- [x] GPU-first K=2 trainer, wave evaluators, compatibility sweep scripts, and full pre-K2 reporting pipeline are implemented.
- [x] Fastdata-stream K=2 wave-2 run completed at:
  - `pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/`
- [x] Completed wave-2 jobs:
  - `g4`: `L3`, seed `42`, `lambda_inc=1e-2`
  - `g5`: `L3`, seed `43`, `lambda_inc=1e-2`
  - `g6`: `L3`, seed `44`, `lambda_inc=1e-2`
  - `g7`: `L3`, seed `42`, `lambda_inc=0` control

### Active
- [ ] Paper 1 post-wave follow-up experiments:
  - small `lambda` calibration check
  - standard single-branch SAE comparator
- [ ] PCC post-A1 interpretation and next-step decision capture:
  - Stage A0 aggregate root:
    - `pilot_runs/20260604_184924_pcc_stage_a0/`
  - Stage A1 aggregate root:
    - `pilot_runs/20260605_013756_pcc_stage_a1/`
  - Stage A1b diagnostic root:
    - `pilot_runs/20260605_030600_pcc_stage_a1b/`
  - frozen PCC checkpoint record:
    - `prereg/pcc_state_checkpoint_20260605_pre_a1c.md`
  - amendment draft:
    - `prereg/pcc_gate_revision_v1.md`
  - A1c confirmation root:
    - `pilot_runs/20260605_034815_pcc_stage_a1c/`
  - current frozen gate outcome:
    - stop before Stage B / PCC branch training under the original Stage A1 decision rule
  - current amended gate outcome:
    - `stage_a1r_decision.json` / `stage_a1r_decision.md` at the A1c root record `proceed_to_stage_b = true`
  - Stage B-light control audit root:
    - `pilot_runs/20260605_040323_pcc_stage_b_light_controls/`
    - completed on GPUs `4,5,6,7`

### Current Interpretation
- [x] The balanced/interleaved data-loader restart solved the prior throughput collapse without harming training quality.
- [x] `lambda_inc=1e-2` continues to produce a strong incoherence advantage over the matched no-inc control.
- [x] In the completed `1B`-token wave, all three regularized seeds finish with lower incoherence and slightly higher FVU than the no-inc control.
- [x] Active-latent utilization is healthy across both branches in the completed wave.
- [x] `L3` remains the primary Paper 1 training target; `L4` remains a contingency path only.
- [x] The first PCC Stage A0 batch is implemented and completed on GPUs `4,5,6,7` against the final `L3` checkpoints.
- [x] The first PCC-0 readout shows only small joint gains on the minimal task battery; this supports doing aggregation/decision work before any larger PCC architecture push.
- [x] PCC Stage A0 aggregate decision completed:
  - `pos_ud_ewt` and `deprel_ud_ewt` pass the minimum Stage A0 “promising” threshold
  - `ner_wnut17` remains content-private but not strongly crossover-enriched
  - Stage A1 observational expansion was authorized and launched
- [x] PCC Stage A1 expanded observational audit completed on GPUs `4,5,6,7`:
  - run root:
    - `pilot_runs/20260605_013756_pcc_stage_a1/`
  - all four `L3` checkpoints completed:
    - `g4`, `g5`, `g6`, `g7`
- [x] Under the current Stage A1 rule, PCC does **not** proceed to Stage B:
  - passed syntax family count = `1` (`syntax_pos`)
  - passed semantic family count = `1` (`sem_wnut`)
  - formal result:
    - `proceed_to_stage_b = false`
- [x] PCC Stage A1b diagnostic follow-up completed on the same four `L3` checkpoints:
  - run root:
    - `pilot_runs/20260605_030600_pcc_stage_a1b/`
  - reporting cleanup added:
    - convergence summary tables
    - fit-health appendix
    - explicit note that frozen A1/A1b probe selection still uses validation `top1`
  - diagnostic task changes:
    - split `deprel_coarse` from `head_dir_dist`
    - add BIO-collapsed `typeonly` NER labels
    - add `entity` vs `O` binary NER labels
- [x] A1b does **not** overturn the frozen A1 decision, but it does materially strengthen the amendment case:
  - passed syntax diagnostic families:
    - `syntax_pos`
    - `syntax_dep_coarse`
  - passed semantic diagnostic families:
    - `sem_wnut17_typeonly`
    - `sem_fewnerd_coarse_binary`
    - `sem_wikineural_en_binary`
  - aggregate diagnostic verdict:
    - `candidate_amendment_supported = true`
- [x] A prospective PCC amendment draft now exists:
  - `prereg/pcc_gate_revision_v1.md`
  - it preserves the frozen A1 no-go and requires a fresh amended observational evaluation before any Stage B decision
- [x] The PCC state was frozen before confirmation:
  - `prereg/pcc_state_checkpoint_20260605_pre_a1c.md`
  - this preserves the distinction between:
    - the frozen A1 no-go
    - the A1b diagnostic explanation
    - the proposed revised rule
- [x] PCC Stage A1c confirmation completed on the same four `L3` checkpoints:
  - run root:
    - `pilot_runs/20260605_034815_pcc_stage_a1c/`
  - technical change:
    - NER probe checkpoint selection aligned to validation `macro_f1`
    - semantic probe budgets increased
  - amended confirmation result:
    - passed syntax families:
      - `syntax_pos`
      - `syntax_dep_coarse`
    - passed semantic families:
      - `sem_wnut17_typeonly`
      - `sem_fewnerd_coarse_binary`
      - `sem_wikineural_en_binary`
    - aggregate verdict:
      - `amendment_confirmed = true`
- [x] The PCC amendment is now adopted as a prospective governance artifact:
  - adoption record:
    - `pilot_runs/20260605_034815_pcc_stage_a1c/amendment_decision.json`
  - amended observational decision:
    - `pilot_runs/20260605_034815_pcc_stage_a1c/stage_a1r_decision.json`
    - `pilot_runs/20260605_034815_pcc_stage_a1c/stage_a1r_decision.md`
  - important limitation:
    - this does **not** replace the frozen A1 record
    - it creates a separate amended observational decision path
- [x] PCC Stage B-light control audit completed on the same checkpoint family:
  - run root:
    - `pilot_runs/20260605_040323_pcc_stage_b_light_controls/`
  - scope:
    - matched-token controls
    - coarse matched-position controls
    - residual-vs-joint comparisons
    - regularizer sensitivity (`g4` vs `g7`)
  - key readout:
    - `syntax_pos` remains positive under both full and coarse position controls, and stays modestly positive under matched-token control
    - `syntax_dep_coarse` remains clearly positive under full and coarse position controls, but drops substantially under matched-token control
    - `sem_fewnerd_coarse_binary` and `sem_wikineural_en_binary` remain content-private with low positive joint gain under all three control settings
    - matched-seed regularizer sensitivity remains strongest for syntax families, with `g7 > g4` on `syntax_pos` and `syntax_dep_coarse`
  - still excluded:
    - new PCC branch training
    - new checkpoints
    - full curated contrast-set pack
- [x] The next scientifically important follow-up after the completed `1B` wave is not more scaling with the same setup, but targeted follow-up:
  - small `lambda` calibration
  - standard SAE baseline
  - freeze, confirm, and then adopt or reject the PCC amendment cleanly
  - run Stage B-light controls before any new PCC branch training
  - use the completed Stage B-light controls to decide whether a curated contrast-set phase is justified
  - do not launch new PCC branch training until the Stage B-light interpretation is in hand

---

## 0. Program Management, Governance, and Reproducibility

### 0.1 Milestones and Decision Gates
- [ ] Create milestone tracker with `M0`..`M8`:
  - `M0`: infra + prereg complete.
  - `M1`: synthetic identifiability sandbox complete.
  - `M2`: Paper 1 main runs complete.
  - `M3`: Paper 1 gate decision.
  - `M4`: Paper 2 main runs complete.
  - `M5`: Paper 2 gate decision.
  - `M6`: Paper 3 main runs complete.
  - `M7`: Paper 3 gate decision.
  - `M8`: final artifact + camera-ready package.
- [ ] Define owner(s), deadline, and exit criteria for each milestone.
- [x] `M0` is effectively complete: prereg, pre-K2 suite, gate report, trainer, and wave launch infrastructure exist.

### 0.2 Preregistration and Freeze Rules
- [x] Create `prereg/` directory.
- [x] Add pre-K2 prereg / gate files:
  - `prereg/pilot_v6_preregistered_thresholds.md`
  - `prereg/k2_gate_policy_locked.md`
- [x] Timestamp and git-tag prereg / gate commits before K=2 wave launch:
  - `prereg-v6`
  - `pre-k2-suite-v6`
- [x] Add policy: no threshold changes after training starts without a versioned amendment file.
- [ ] Add paper-specific prereg files for Paper 2 and Paper 3:
  - `prereg/paper2_thresholds.md`
  - `prereg/paper3_thresholds.md`
  - `prereg/metrics_definitions.md`
  - `prereg/analysis_plan.md`

### 0.3 Experiment Registry and Naming
- [ ] Create `experiments/registry.csv` with columns:
  - `run_id`, `paper`, `stage`, `model`, `layer`, `dataset`, `tokens`, `seed`, `config_path`, `commit_sha`, `status`, `notes`.
- [ ] Establish run naming convention:
  - `p{paper}-s{stage}-{arch}-{model}-l{layer}-seed{n}-cfg{short}`.
- [ ] Add mandatory metadata logging for each run:
  - code commit SHA, data snapshot/version, hardware, wall-clock, cost, env hash.

### 0.4 Statistical Testing Infrastructure
- [ ] Implement shared stats module:
  - mean/std over 5 seeds.
  - paired bootstrap (10,000 resamples).
  - BH correction across metric families.
- [ ] Standardize confidence interval reporting format.
- [ ] Add guardrails for multiple comparison pitfalls in ablation-heavy sections.

---

## 1. Codebase and Infrastructure

### 1.1 Repository Structure
- [ ] Create directories:
  - `configs/`
  - `src/`
  - `scripts/`
  - `analysis/`
  - `results/`
  - `figures/`
  - `prereg/`
  - `docs/`
- [ ] Add paper-specific config trees:
  - `configs/paper1/`
  - `configs/paper2/`
  - `configs/paper3/`

### 1.2 Core Training Framework
- [x] Build GPU-first custom K=2 MSAE trainer abstraction:
  - multi-branch encoders/decoders for `D_position` and `D_content`.
  - mutual incoherence regularizer for branch pairs.
  - checkpoint/resume, wave evaluation, and tmux launch support.
- [ ] Extend trainer to Paper 2/3 heterogeneity:
  - JumpReLU / dense low-rank / structured branches.
  - generalized coherence-penalty family support across branch types.
- [x] Implement decoder unit-norm constraints and projected gradient updates.
- [x] Implement dead-latent tracking and AuxK revival for sparse branches.

### 1.3 Logging and Monitoring
- [x] Log every configurable interval:
  - total loss, reconstruction loss, total FVU, branch-only error ratios, dead-latent counts.
  - coherence metrics, throughput, source mix, utilization health, revival rates.
- [ ] Add explicit absorption-oriented diagnostics for Paper 1 follow-up:
  - frozen probe retention / suppression checks.
  - cross-branch overlap and branch-specific decoder-cosine summaries.
- [ ] Log every 5,000 steps:
  - Babel proxy on concatenated sparse dictionary.
  - descent cone/statistical-dimension estimates.
- [ ] For dense branch (Paper 2+): log effective rank and singular-value spectrum.

### 1.4 Determinism and Seed Controls
- [ ] Seed all RNG sources and record seed provenance.
- [ ] Save activation shuffle seeds and bucket ordering hashes.
- [ ] Add reproducibility test: repeated tiny run reproduces same metrics within tolerance.

---

## 2. Data and Activation Pipelines

### 2.1 Corpora and Splits
- [ ] Define training corpus snapshots:
  - Paper 1: The Pile, 8B-token training stream.
  - Paper 2 and 3: The Pile, 500M-token SAEBench-style stream.
- [ ] Define evaluation/holdout activation set:
  - Paper 1: 100M-token OpenWebText holdout for probes and init diagnostics.
- [ ] Define filtering rules:
  - exclude BOS/EOS/padding where required.

### 2.2 Activation Extraction
- [ ] Implement activation extraction for:
  - Pythia-160M layer 3 residual stream (Paper 1 primary), with layer 4 as fallback.
  - Gemma-2-2B layer 12 residual stream (Paper 2 and 3 primary).
  - Additional sites for ablations (Pythia layer sweeps; attention/MLP outputs for Paper 2 support experiment).
- [ ] Implement buffered activation storage (1e6-item bucket shuffle).
- [ ] Persist dataset lineage and sampling script hashes.

### 2.3 Probe Dataset Builders
- [ ] Position labels (0–1023 or specified bucketing).
- [ ] Token identity labels (top-1024 bucket with defined OOV handling).
- [ ] Matched-token different-position pairs for invariance.
- [ ] Relative-position synthetic task dataset for causal probe.
- [ ] Syntax/semantics/frequency probe datasets for Paper 2 unsupervised discovery.

---

## 3. Stage 0 (Pre-Paper) Synthetic Identifiability Sandbox

### 3.1 Planted Data Generator
- [ ] Implement synthetic generator for:
  - `y = D1* a1* + D2* a2*` with orthogonal `D1*`, `D2*`.
  - dimensions `n in {64, 256, 1024}`.
  - Bernoulli-Gaussian coefficients with configurable sparsity.
- [ ] Add sparse + low-rank variant for forward compatibility.

### 3.2 Recovery Procedure
- [ ] Implement alternating l1 minimization / sparse recovery baseline.
- [ ] Implement MSAE-style training on synthetic samples.
- [ ] Sweep:
  - coherence levels.
  - `(k1+k2)` regimes below/near/above Donoho-Elad heuristic zone.

### 3.3 Outputs
- [ ] Phase diagram figure:
  - empirical recovery success vs `(k1+k2, mu_hat, n)`.
- [ ] Theoretical overlay figure:
  - McCoy-Tropp statistical-dimension boundary.
- [ ] Write short methods note for reuse in Paper 1 theory section.

Gate to proceed:
- [ ] Synthetic pipeline stable, figures reproducible, and recovery trends qualitatively match theory expectations.

---

## 4. Paper 1 Execution (K=2 Position-vs-Content)

### 4.0 Raw-Activation Separability Pilot (No SAE, Required)
- [x] Train raw-activation linear probes for position and token identity on Pythia-160M layers 3 and 4.
- [x] Construct probe-derived subspaces (`S_pos`, `S_tok`) via SVD at ranks `{8,16,32}`.
- [x] Evaluate projected performance on `Proj_{S_pos}`, `Proj_{S_pos^perp}`, `Proj_{S_tok}`, `Proj_{S_tok^perp}`.
- [x] Compute principal-angle and cross-projection overlap diagnostics.
- [x] Enforce pilot pass thresholds before launching K=2 training.
- [x] Resolve layer target from pilot:
  - `L3` primary
  - `L4` fallback
- [x] Archive pilot outputs and gate report in `reports/pre_k2_suite_v6/`.

### 4.1 Finalize Paper 1 Prereg
- [x] Lock thresholds for the pre-K2 decision suite.
- [x] Lock baseline set and reporting protocol for the pre-K2 gate.
- [ ] Lock final Paper 1 post-training reporting bundle for the K=2 paper draft:
  - exact wave-2 headline metrics
  - coherence-family ablation rules
  - final branch-specialization / anti-suppression diagnostics
- [ ] Lock robustness addendum criterion for regularizer warmdown stability.

### 4.2 Implement Paper 1 Architecture
- [x] Branch `D_position`: TopK, `m_pos=8k`, `k_pos=8`.
- [x] Branch `D_content`: TopK, `m_content=32k`, `k_content=24`.
- [x] Quadratic cross-branch incoherence loss `lambda_inc ||D_pos^T D_content||_F^2 / (m_pos*m_content)` estimator.
- [x] AuxK and dead-latent revival.
- [ ] Extend Paper 1 trainer with generalized coherence family and scope controls:
  - `inc_p` for `mean(|gram|^p)` rather than fixed square
  - `inc_scope in {cross, within, both}`
  - optional per-branch weights and normalized logging

### 4.3 Train Main Model Runs
- [ ] Train 5 seeds for headline config:
  - Adam `(beta1=0, beta2=0.999)`, `eps=1e-8`.
  - LR `7e-5`, cosine warmup 1000.
  - batch 4096.
  - 8B training tokens from The Pile.
  - incoherence warmup over first 10k steps.
- [x] Launch wave-1 `100M` token runs:
  - `L3`, seed `42`, `lambda_inc=1e-2`
  - `L3`, seed `43`, `lambda_inc=1e-2`
  - `L4`, seed `42`, `lambda_inc=1e-2`
  - `L3`, seed `42`, `lambda_inc=0`
- [x] Promote to wave-2 `1B` token run set from approved checkpoints.
- [x] Add fourth live baseline on GPU `6`:
  - `L3`, seed `44`, `lambda_inc=1e-2`
- [x] Finish wave-2 runs and archive final summaries.
- [ ] Decide which regularized seeds become headline Paper 1 runs after `1B` completion.

### 4.4 Initialization Variant Runs
- [ ] Random Gaussian init (baseline).
- [ ] Fourier-biased position init + random content init.
- [ ] PCA-conditioned init from holdout diagnostics.

### 4.5 Baselines (Required)
- [ ] K=1 matched-parameter SAE (`m=40k`), post-hoc position/content split.
- [x] K=2 no-incoherence baseline (`lambda_inc=0`) launched and completed through wave-2.
- [ ] Optional extra comparisons if budget allows:
  - K=1 TopK/JumpReLU matched-L0 variants.

### 4.7 PCC Follow-On Audit
- [x] Execute `TODO_pcc.md` Stage A0 on final `L3` wave-2 checkpoints.
  - completed matrix run:
    - `pilot_runs/20260604_184924_pcc_stage_a0/`
  - completed jobs:
    - `pcc_a0_g4_L3_s42_inc1e2`
    - `pcc_a0_g5_L3_s43_inc1e2`
    - `pcc_a0_g6_L3_s44_inc1e2`
    - `pcc_a0_g7_L3_s42_inc0`
- [x] Run minimal PCC-0 battery:
  - POS-style syntax task
  - dependency/agreement-style syntax task
  - NER-style semantics task
- [x] Aggregate `joint_gain` across completed `g4/g5/g6` regularized checkpoints and `g7` no-inc control.
  - Stage A0 aggregate decision files written under:
    - `pilot_runs/20260604_184924_pcc_stage_a0/`
  - formal Stage A0 decision:
    - `pos_ud_ewt`: stable-positive
    - `deprel_ud_ewt`: stable-positive
    - `ner_wnut17`: content-private
    - `proceed_to_stage_a1 = true`
- [x] Execute expanded PCC Stage A1 observational audit on the same `L3` checkpoint family.
  - completed matrix run:
    - `pilot_runs/20260605_013756_pcc_stage_a1/`
  - completed jobs:
    - `pcc_a1_g4_L3_s42_inc1e2`
    - `pcc_a1_g5_L3_s43_inc1e2`
    - `pcc_a1_g6_L3_s44_inc1e2`
    - `pcc_a1_g7_L3_s42_inc0`
- [x] Decide whether PCC proceeds to Stage B or stops with a no-PCC-go outcome.
  - Stage A1 aggregate decision files written under:
    - `pilot_runs/20260605_013756_pcc_stage_a1/`
  - formal Stage A1 decision:
    - `passed_syntax_families = ['syntax_pos']`
    - `passed_semantic_families = ['sem_wnut']`
    - `proceed_to_stage_b = false`
    - conclusion:
      - stop PCC expansion at Stage A1 under the current gate

### 4.6 Paper 1 Ablation Matrix
- [ ] Incoherence sweep: `lambda_inc in {0,1e-4,1e-3,1e-2,1e-1}`.
- [ ] Regularizer warmdown/hysteresis: finetune 1-2B tokens with `lambda_inc=0` after converged training; track coherence drift and probe degradation.
- [ ] Sparsity allocation sweep: `(k_pos,k_content) in {(4,28),(8,24),(16,16),(24,8)}`.
- [ ] Width allocation sweep at `m_total=40k`:
  - `(2k,38k)`, `(4k,36k)`, `(8k,32k)`, `(16k,24k)`, `(20k,20k)`.
- [ ] Init sweep as above.

### 4.6A Coherence Penalty Family and Scope Experiments
- [ ] Add coherence-penalty family sweep motivated by `neurips_2026_feature_absorption.pdf`.
- [ ] Implement penalty-shape sweep on the cross-branch Gram matrix:
  - `p in {1.5, 1.75, 2.0, 3.0}`
  - penalty form `mean(|D_pos D_content^T|^p)` with `p=2.0` matching the current baseline
- [ ] Implement penalty-scope sweep:
  - `cross` = cross-branch only
  - `within` = within-branch only
  - `both` = combined cross + within
- [ ] Run short-budget smoke ablation (`25M` to `100M` tokens) for the penalty family/scope grid before any long reruns.
- [ ] Promote only the best one or two penalty variants to longer `300M` or `1B` follow-up budgets.
- [ ] Track collapse/suppression diagnostics during these sweeps:
  - decoder cosine concentration
  - active latent fractions
  - usage entropy / Gini
  - revival rates
  - branch energy ratios
- [ ] Add anti-suppression evaluation:
  - frozen probe retention on position/content probes
  - branch ablations on `recon_pos` / `recon_content`
  - cross-branch leakage metrics on matched-token / relative-position tasks
- [ ] Compare all penalty-family results to the current quadratic baseline (`p=2`, cross only) on:
  - total FVU
  - cross-branch incoherence
  - branch specialization
  - seed stability

### 4.6B Absorption-Oriented Follow-Up Evaluations
- [ ] Add a feature-absorption / overlap audit for K=2 branches:
  - branch-internal decoder cosine overlap distributions
  - repeated-feature / duplicate-feature counts
  - matched-seed feature alignment across regularized vs no-inc runs
- [ ] Evaluate whether lower incoherence reflects true specialization rather than feature suppression.
- [ ] Use matched-seed `g4` vs `g7` as the primary causal ablation for Paper 1 regularizer claims.

### 4.7 Four-Probe Evaluation Suite
- [ ] Probe 1 position prediction:
  - standardized train/test splits.
  - multiclass metric definition fixed (AUC/top-1 as preregistered).
- [ ] Probe 2 token identity prediction:
  - top-1024 task with fixed class handling.
- [ ] Probe 3 position invariance:
  - fixed pair-construction protocol.
  - report cosine gap and CI.
- [ ] Probe 4 causal intervention:
  - clamp `D_position` vs `D_content` components.
  - measure CE deltas and relative-position task deltas.

### 4.8 Seed Stability Analysis
- [ ] Train/evaluate 5 seeds for all headline and core baseline configs.
- [ ] Implement Paulo-Belrose Hungarian matching:
  - shared latent criterion: cosine >= 0.7 on both encoder and decoder.
- [ ] Report:
  - within-branch overlap.
  - across-branch overlap.
  - comparison to K=1 TopK baseline.

### 4.9 Theory Section Assets
- [ ] Estimate empirical `mu_hat(D_pos,D_content)` trajectory during training.
- [ ] Estimate descent-cone statistics over training snapshots.
- [ ] Draft explicit caveat text on sufficient-vs-necessary bounds.
- [ ] Draft short conjectural ER-SpUD adaptation paragraph (clearly marked as conjecture).

### 4.10 IOI Case Study
- [ ] Define IOI-compatible evaluation pipeline for Pythia-160M lower layers.
- [ ] Quantify branch-specific logit-difference retention under `D_pos` and `D_content` clamping.
- [ ] Quantify attribution concentration of position-sensitive IOI signal across branches.
- [ ] Quantify cross-branch leakage on control tasks with predeclared thresholds.
- [ ] Produce one figure + one table with preregistered metrics.

### 4.11 Paper 1 Gate Computation
- [ ] Compute 5 core prereg criteria on 5-seed means.
- [ ] Compute regularizer warmdown robustness addendum criterion.
- [ ] Produce gate report:
  - pass count, failed criteria, confidence intervals.
  - recommendation: advance / iterate once / pivot to negative-result framing.
  - claim framing: intrinsic morphological separation vs incoherence-regularized separation.

Deliverables:
- [ ] `results/paper1/summary.csv`
- [ ] `figures/paper1/*.png`
- [ ] `docs/paper1_methods.md`
- [ ] `docs/paper1_gate_report.md`

---

## 5. Paper 2 Execution (K=3 Generalized MSAE)

Precondition:
- [ ] Paper 1 gate outcome reviewed and approved for progression.

### 5.1 Finalize Paper 2 Prereg
- [ ] Freeze 7 success criteria.
- [ ] Freeze SAEBench and Kantamneni comparison protocol details.

### 5.2 Implement Paper 2 Architecture
- [ ] `D1`: TopK, `k=32`, `m1=65k`.
- [ ] `D2`: JumpReLU, `m2=16k`, `eps=1e-3`, threshold init `1e-3`.
- [ ] `D3`: dense low-rank branch `UV^T`, `r<=64`, no sparsity.
- [ ] Incoherence terms:
  - sparse-sparse coherence.
  - sparse-dense row-space decorrelation (`||D_j^T U||^2`).

### 5.3 Train Main Runs (Gemma-2-2B, Layer 12)
- [ ] Match SAEBench training recipe:
  - The Pile, 500M tokens.
  - context 1024, batch 2048.
  - LR `3e-4`, 1000 warmup, sparsity warmup 5000, last-20% decay.
- [ ] Train 5 seeds at headline config.

### 5.4 Monitoring and Diagnostics
- [ ] Log `mu_hat_{jk}` every 1000 steps.
- [ ] Log Babel proxy every 5000 steps.
- [ ] Log per-branch and total FVU.
- [ ] Log descent-cone estimates.
- [ ] Log dense-branch effective rank utilization.

### 5.5 Supporting Experiment: K=2 Attention-vs-MLP
- [ ] Build activation hooks for attention output and MLP output at layer 12.
- [ ] Train constrained/anchored K=2 model.
- [ ] Evaluate with dedicated probes:
  - attention-pattern prediction.
  - MLP reconstruction/feature probes.

### 5.6 Unsupervised K=2 Discovery Experiment
- [ ] Train random-init K=2 with incoherence-only structural bias.
- [ ] Run full probe battery (position/content + syntax/frequency + attention/MLP).
- [ ] Determine discovered split via peak probe signal.
- [ ] Quantify consistency across seeds.

### 5.7 Dark-Matter Validation
- [ ] Compute variance explained by `D3`.
- [ ] Measure residual linear predictability from input activations.
- [ ] Compare with and without dense branch.
- [ ] Compare against frozen rank-matched PCA control branch.
- [ ] Analyze top singular directions of `D3` for reproducible structured alignment across seeds.
- [ ] Verify target conditions in prereg thresholds.

### 5.8 Full SAEBench Evaluation
- [ ] Run all 8 SAEBench families at `L0 in {20,40,80,160,320,640}`.
- [ ] Baselines at matched L0:
  - Gemma-Scope JumpReLU.
  - BatchTopK.
  - Matryoshka BatchTopK.
- [ ] Run 5 seeds for each comparable system where feasible.

### 5.9 Kantamneni 113-Task Benchmark
- [ ] Reproduce protocol on Gemma-2-9B layer 20 for probing comparison.
- [ ] Evaluate MSAE probe vs:
  - standard SAE probe baseline.
  - plain logistic regression on raw activations.
- [ ] Run Quiver-of-Arrows style toolkit test with MSAE probe added.

### 5.10 Paper 2 Ablation Matrix
- [ ] `K` sweep: `{1,2,3,4,6}`.
- [ ] `lambda_inc` sweep: `{0,1e-4,1e-3,1e-2,1e-1}`.
- [ ] Branch heterogeneity sweep:
  - `(TopK,TopK,dense)` vs `(TopK,JumpReLU,dense)`.
- [ ] Dense branch off/on ablation.
- [ ] Dense branch learned-vs-frozen-PCA control ablation.
- [ ] Width allocation at fixed total budget:
  - `(99k,1k,0)`, `(90k,10k,16)`, `(65k,16k,64)`, `(50k,30k,64)`, `(40k,40k,16)`.
- [ ] Encoder tying / projection-trick ablation.

### 5.11 Paper 2 Gate Computation
- [ ] Evaluate all 7 prereg criteria using 5-seed means.
- [ ] Run bootstrap + BH-corrected significance across metric families.
- [ ] Publish gate report with pass/fail and suggested next action.

Deliverables:
- [ ] `results/paper2/summary.csv`
- [ ] `results/paper2/saebench_table.csv`
- [ ] `results/paper2/kantamneni_table.csv`
- [ ] `docs/paper2_gate_report.md`

---

## 6. Paper 3 Execution (Structured Branches)

Precondition:
- [ ] Paper 2 gate outcome reviewed and approved for progression.

### 6.1 Finalize Paper 3 Prereg
- [ ] Freeze 4 success criteria.
- [ ] Freeze evaluation protocols for Engels and Chanin benchmarks.

### 6.2 Implement Structured Branches
- [ ] `D_subspace` branch:
  - block atoms `A_i in R^{d x r_i}`, `r_i in {2,3,4}`.
  - group-sparse activation over atoms.
  - within-atom dense coefficients.
  - nuclear/group regularization terms.
- [ ] `D_multiscale` branch:
  - nested dictionaries with BatchTopK.
  - per-scale reconstruction weighting.
- [ ] Integrate with Paper 2 backbone and coherence penalties.

### 6.3 Train Main Runs
- [ ] Run Paper 3 feasibility pilot first (50M tokens, 3 seeds, reduced-width K=5).
- [ ] Check pilot convergence gate before full sweep.
- [ ] Gemma-2-2B layer 12, 500M tokens, 5 seeds.
- [ ] Preserve Paper 2 baseline comparability.

### 6.4 Validation: Engels Circular Features
- [ ] Implement or integrate Engels discovery pipeline.
- [ ] Evaluate whether circular features are captured as single 2D atoms/subspaces.
- [ ] Compute:
  - Separability Index.
  - epsilon-Mixture Index.
  - within-circle variance captured.
- [ ] Run causal clamping interventions on recovered subspace atoms.

### 6.5 Validation: Chanin Absorption
- [ ] Run first-letter absorption benchmark at `L0 in {40,80,160}`.
- [ ] Compare directly to Matryoshka at matched settings.
- [ ] Report:
  - absorption rate.
  - partial-absorption rate.
  - multi-latent absorption rate.

### 6.6 Theoretical Section Assets
- [ ] Draft atomic-norm formulation for structured branches.
- [ ] Add combined descent-dimension estimation for full architecture.
- [ ] Clearly delimit theorem-backed vs heuristic components.

### 6.7 Mechanistic Case Studies
- [ ] Case Study 1: modular arithmetic/temporal circuit tracing with subspace atoms.
- [ ] Case Study 2: SHIFT/SCR Bias-in-Bios debiasing with MSAE features.
- [ ] Compare compactness/targeting vs standard SAE feature pipelines.

### 6.8 Paper 3 Gate Computation
- [ ] Evaluate 4 prereg criteria on 5-seed means.
- [ ] Produce final go/no-go with effect sizes and uncertainty.

Deliverables:
- [ ] `results/paper3/summary.csv`
- [ ] `results/paper3/engels_metrics.csv`
- [ ] `results/paper3/chanin_metrics.csv`
- [ ] `docs/paper3_gate_report.md`

---

## 7. Shared Evaluation and Analysis Tasks

### 7.1 Unified Metric Definitions
- [ ] Create single source-of-truth metric spec with formulas and split definitions.
- [ ] Add strict compatibility checks so each run can be scored by the same evaluator.

### 7.2 Visualization Pack
- [ ] Standard plotting scripts for:
  - coherence vs training step.
  - FVU per-branch and total.
  - probe performance comparisons.
  - ablation fronts.
  - seed overlap heatmaps.
  - gate criteria pass/fail dashboards.

### 7.3 Error Analysis Templates
- [ ] Build templates for analyzing gate failures:
  - coherence collapse.
  - dense branch dominance.
  - probe metric disagreement.
  - seed instability persistence.
- [ ] Ensure each failed criterion yields a diagnostic note and proposed remediation.

---

## 8. Compute and Scheduling Plan

### 8.1 Capacity Planning
- [ ] Reserve compute blocks aligned to program estimates:
  - Paper 1: main + ablations.
  - Paper 2: SAEBench-heavy schedule.
  - Paper 3: structured-branch overhead.
- [ ] Maintain queue of high-priority runs (gate-critical first).

### 8.2 Budget Tracking
- [ ] Log GPU-hours per run and cumulative totals by paper.
- [ ] Track baseline-reproduction overhead separately (Matryoshka/BatchTopK/JumpReLU reruns).
- [ ] Add automated alerts for budget overruns.
- [ ] Re-prioritize ablations if gate-critical budget is threatened.

### 8.4 Inference Cost Tracking
- [ ] Benchmark inference-time throughput and latency for K=1 vs K=2 vs K=3 vs K=5 feature extraction.
- [ ] Benchmark peak memory footprint and activation-cache overhead by architecture.
- [ ] Report compute tax of multi-branch MSAE in Paper 2 and Paper 3 result tables.

### 8.3 Runtime QA
- [ ] Add spot-check runs to validate new config changes before full sweeps.
- [ ] Add checkpoint resume tests for long jobs.
- [ ] Add divergence detectors (NaN, dead-latent collapse, runaway coherence).

---

## 9. Writing and Publication Pipeline

### 9.1 Paper Draft Skeletons
- [ ] Create docs skeletons:
  - `docs/paper1_outline.md`
  - `docs/paper2_outline.md`
  - `docs/paper3_outline.md`
- [ ] Pre-map each figure/table to exact run IDs.

### 9.2 Claims-to-Evidence Table
- [ ] Maintain `docs/claims_matrix.csv` with columns:
  - claim, required metric, run IDs, figure/table, status.
- [ ] Enforce: no claim without linked evidence artifact.

### 9.3 Artifact Packaging
- [ ] Create reproducibility bundle per paper:
  - configs
  - scripts
  - run registry subset
  - summary results
  - figure generation scripts
- [ ] Add README with exact reproduction steps and expected outputs.

---

## 10. High-Risk Items and Mitigations

### 10.1 Risk: Coherence Regularizer Is Doing All Work
- [ ] Run explicit `lambda_inc=0` and decay-to-zero tests.
- [ ] Document robustness of decomposition without heavy regularization.

### 10.2 Risk: Dense Branch Trivializes Sparse Branches
- [ ] Track dense variance capture; set red-line thresholds.
- [ ] Constrain/ablate rank and test if sparse branches remain informative.

### 10.3 Risk: No Probe Gains vs Baselines
- [ ] Run targeted diagnosis:
  - data split leakage checks.
  - probe capacity mismatch.
  - feature activation sparsity mismatch.
- [ ] Decide whether to reframe as negative-result contribution.

### 10.4 Risk: Seed Stability Does Not Improve
- [ ] Diagnose matching sensitivity and overlap criterion robustness.
- [ ] Test alternate init and sparsity allocations before abandoning claim.

### 10.5 Risk: SAEBench Underperformance vs Matryoshka
- [ ] Identify metric families with best deltas; quantify tradeoffs explicitly.
- [ ] Reframe claims around wins (if consistent) rather than global leadership.

---

## 11. Minimum Acceptance Checklist Per Paper

### Paper 1
- [ ] Synthetic sandbox complete.
- [ ] 5-seed headline runs complete.
- [ ] Two mandatory baselines complete.
- [ ] Core ablations complete.
- [ ] Four probes + seed stability complete.
- [ ] Gate computed and archived.

### Paper 2
- [ ] 5-seed K=3 headline runs complete.
- [ ] SAEBench full suite complete at target L0 values.
- [ ] Kantamneni benchmark complete.
- [ ] K/`lambda_inc`/dense-branch ablations complete.
- [ ] Gate computed and archived.

### Paper 3
- [ ] Structured branches implemented and validated on smoke tests.
- [ ] Engels + Chanin validations complete.
- [ ] Two case studies complete.
- [ ] Gate computed and archived.

---

## 12. Immediate Next 10 Actions (Priority Order)

1. [ ] Finish the active `1B` wave-2 K=2 runs and archive final summaries/checkpoints.
2. [ ] Generate a post-wave comparison report for `g4/g5/g6` vs `g7` using tail-window metrics and matched-seed ablations.
3. [ ] Patch the trainer with generalized coherence-penalty controls:
   - `inc_p`
   - `inc_scope`
   - normalized logging for the selected penalty family
4. [ ] Run a short coherence-family smoke sweep (`p in {1.5,1.75,2.0,3.0}`) on `L3`.
5. [ ] Run a short scope sweep (`cross`, `within`, `both`) at the best penalty exponents.
6. [ ] Add branch anti-suppression / specialization evaluations to the Paper 1 analysis suite.
7. [ ] Decide whether the quadratic cross-only penalty remains the Paper 1 default after the new ablations.
8. [ ] Launch the K=1 matched-parameter baseline if it is still missing at Paper 1 parity.
9. [ ] Finalize the Paper 1 claims-to-evidence mapping for the K=2 results bundle.
10. [ ] Freeze the exact Paper 1 reporting package before any Paper 2 training begins.
