# TODO.md — End-to-End Execution Plan for MSAE Program

## Scope
This TODO operationalizes `MSAE_revised.md` into concrete implementation, experiment, evaluation, and publication tasks for:
- Paper 1: K=2 position-vs-content MSAE on Pythia-160M.
- Paper 2: K=3 generalized MSAE with dense dark-matter branch on Gemma-2-2B.
- Paper 3: Structured branches (subspace + multiscale) on top of Paper 2.

All tasks are written to support strict reproducibility, pre-declared thresholds, and clear decision gates.

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

### 0.2 Preregistration and Freeze Rules
- [ ] Create `prereg/` directory.
- [ ] Add prereg files:
  - `prereg/paper1_thresholds.md`
  - `prereg/paper2_thresholds.md`
  - `prereg/paper3_thresholds.md`
  - `prereg/metrics_definitions.md`
  - `prereg/analysis_plan.md`
- [ ] Timestamp and git-tag prereg commits before first run per paper:
  - `paper1-prereg-v1`
  - `paper2-prereg-v1`
  - `paper3-prereg-v1`
- [ ] Add policy: no threshold changes after training starts without a versioned amendment file.

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
- [ ] Build SAELens-compatible MSAE trainer abstraction:
  - multi-branch encoders/decoders.
  - heterogeneous branch activations (TopK, JumpReLU, dense low-rank, structured branches).
  - mutual incoherence regularizer for branch pairs.
- [ ] Implement decoder unit-norm constraints and projected gradient updates.
- [ ] Implement dead-latent tracking and AuxK revival for sparse branches.

### 1.3 Logging and Monitoring
- [ ] Log every 1,000 steps (or configurable):
  - total loss, reconstruction loss, per-branch FVU, dead-latent counts.
  - coherence metrics: `mu_hat_{jk}`, optional sampled `||D_j^T D_k||_F`.
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
- [ ] Train raw-activation linear probes for position and token identity on Pythia-160M layers 3 and 4.
- [ ] Construct probe-derived subspaces (`S_pos`, `S_tok`) via SVD at ranks `{8,16,32}`.
- [ ] Evaluate projected performance on `Proj_{S_pos}`, `Proj_{S_pos^perp}`, `Proj_{S_tok}`, `Proj_{S_tok^perp}`.
- [ ] Compute principal-angle and cross-projection overlap diagnostics.
- [ ] Enforce pilot pass thresholds before launching full 8B-token MSAE training.
- [ ] If pilot fails, run layer-retarget contingency (`layer 2`) or narrow claim scope.

### 4.1 Finalize Paper 1 Prereg
- [ ] Lock thresholds (5 criteria in revised doc).
- [ ] Lock robustness addendum criterion for regularizer warmdown stability.
- [ ] Lock baseline set and ablation matrix.
- [ ] Lock reporting protocol (5-seed means and significance).

### 4.2 Implement Paper 1 Architecture
- [ ] Branch `D_position`: TopK, `m_pos=8k`, `k_pos=8`.
- [ ] Branch `D_content`: TopK, `m_content=32k`, `k_content=24`.
- [ ] Incoherence loss `lambda_inc ||D_pos^T D_content||_F^2 / (m_pos*m_content)`.
- [ ] AuxK and dead-latent revival.

### 4.3 Train Main Model Runs
- [ ] Train 5 seeds for headline config:
  - Adam `(beta1=0, beta2=0.999)`, `eps=1e-8`.
  - LR `7e-5`, cosine warmup 1000.
  - batch 4096.
  - 8B training tokens from The Pile.
  - incoherence warmup over first 10k steps.

### 4.4 Initialization Variant Runs
- [ ] Random Gaussian init (baseline).
- [ ] Fourier-biased position init + random content init.
- [ ] PCA-conditioned init from holdout diagnostics.

### 4.5 Baselines (Required)
- [ ] K=1 matched-parameter SAE (`m=40k`), post-hoc position/content split.
- [ ] K=2 no-incoherence baseline (`lambda_inc=0`).
- [ ] Optional extra comparisons if budget allows:
  - K=1 TopK/JumpReLU matched-L0 variants.

### 4.6 Paper 1 Ablation Matrix
- [ ] Incoherence sweep: `lambda_inc in {0,1e-4,1e-3,1e-2,1e-1}`.
- [ ] Regularizer warmdown/hysteresis: finetune 1-2B tokens with `lambda_inc=0` after converged training; track coherence drift and probe degradation.
- [ ] Sparsity allocation sweep: `(k_pos,k_content) in {(4,28),(8,24),(16,16),(24,8)}`.
- [ ] Width allocation sweep at `m_total=40k`:
  - `(2k,38k)`, `(4k,36k)`, `(8k,32k)`, `(16k,24k)`, `(20k,20k)`.
- [ ] Init sweep as above.

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

1. [ ] Create prereg files and freeze Paper 1 thresholds in a tagged commit.
2. [ ] Scaffold repository directories and experiment registry.
3. [ ] Implement activation extraction pipeline for Pythia-160M layer 3 (layer 4 fallback).
4. [ ] Implement K=2 MSAE trainer with incoherence + AuxK.
5. [ ] Implement four-probe evaluation scripts (position, token, invariance, causal).
6. [ ] Run synthetic identifiability sandbox pilot at `n=64`.
7. [ ] Launch first Paper 1 headline training seed.
8. [ ] Launch K=1 matched baseline and K=2 no-incoherence baseline.
9. [ ] Build seed-matching analysis module (Paulo-Belrose criterion).
10. [ ] Draft Paper 1 gate-report template before results arrive.
