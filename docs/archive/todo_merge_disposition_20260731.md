# TODO Merge Disposition Audit — 2026-07-31

This audit preserves and accounts for the two pre-merge sources. The archived files are byte-identical to the active sources before `TODO.md` was rewritten. Every checkbox item, including nested checkbox items, has a stable line-based source ID and exactly one disposition. Non-checkbox detail is covered by the enclosing section disposition.

## Immutable source snapshots

| Source | Archive | SHA-256 |
|---|---|---|
| `MAIN` | `docs/archive/todo_main_premerge_20260731.md` | `7a3adb732e6e770529b26c17bddd85bdc83ff20d463ed15b26ebef8e5fb634c1` |
| `PCC` | `docs/archive/pcc_plan_premerge_20260731.md` | `1a932307edc5f207938757ce988a1c5ff6209b58decab145a7120504c29e4e3b` |

Verification command:

```bash
sha256sum docs/archive/todo_main_premerge_20260731.md docs/archive/pcc_plan_premerge_20260731.md
```

## Active-source retirement

- After the unified roadmap received an independent `SHIP` verdict on 2026-07-31, the root `TODO_pcc.md` filename was retired.
- Its byte-identical archived source remains `docs/archive/pcc_plan_premerge_20260731.md` with the SHA-256 above; `TODO.md` is now the sole active root TODO.

## Disposition rules

- `carried`: a completed/historical item is represented in the unified status/evidence record.
- `merged`: an active action is represented by the named destination milestone/section, possibly consolidated with duplicates.
- `superseded`: an old action is intentionally replaced by a newer gated rule or by completed evidence; the destination states the replacement.
- No source checkbox is silently dropped. No item uses `intentionally dropped`.
- Future Paper 2/3 execution details are `superseded` as active work by the G5 precondition and are preserved as gated follow-on scope in §13; their exact numerical preregistration must be rebuilt after the next-paper gate rather than executed from a stale plan.

## Section coverage

| Source section | Lines | Open | Done | Disposition | Destination |
|---|---:|---:|---:|---|---|
| `MAIN` Scope | 3–12 | 0 | 0 | merged | TODO.md §0–§14 (merged by subject) |
| `MAIN` Status Snapshot (2026-06-05) | 13–164 | 2 | 24 | carried | TODO.md §1 Current Project State |
| `MAIN` 0. Program Management, Governance, and Reproducibility | 165–213 | 9 | 5 | merged | TODO.md §0, §5, §10 |
| `MAIN` 1. Codebase and Infrastructure | 214–260 | 9 | 4 | merged | TODO.md M6 and §10 |
| `MAIN` 2. Data and Activation Pipelines | 261–288 | 11 | 0 | merged | TODO.md §5 and §10 |
| `MAIN` 3. Stage 0 (Pre-Paper) Synthetic Identifiability Sandbox | 289–316 | 9 | 0 | merged | TODO.md M2b |
| `MAIN` 4. Paper 1 Execution (K=2 Position-vs-Content) | 317–510 | 49 | 23 | merged | TODO.md M0–M10 and §9 |
| `MAIN` 5. Paper 2 Execution (K=3 Generalized MSAE) | 511–601 | 47 | 0 | superseded | TODO.md §13 Future Paper 2 |
| `MAIN` 6. Paper 3 Execution (Structured Branches) | 602–666 | 29 | 0 | superseded | TODO.md §13 Future Paper 3 |
| `MAIN` 7. Shared Evaluation and Analysis Tasks | 667–691 | 5 | 0 | merged | TODO.md M8, M9, M11 |
| `MAIN` 8. Compute and Scheduling Plan | 692–718 | 12 | 0 | merged | TODO.md M7 and §10 |
| `MAIN` 9. Writing and Publication Pipeline | 719–743 | 6 | 0 | merged | TODO.md M11–M12 |
| `MAIN` 10. High-Risk Items and Mitigations | 744–770 | 10 | 0 | merged | TODO.md §11 |
| `MAIN` 11. Minimum Acceptance Checklist Per Paper | 771–795 | 15 | 0 | merged | TODO.md §12–§13 |
| `MAIN` 12. Immediate Next 10 Actions (Priority Order) | 796–810 | 0 | 0 | merged | TODO.md §14 |
| `PCC` Scope | 3–51 | 0 | 0 | merged | TODO.md §0–§14 (merged by subject) |
| `PCC` 0. Status Snapshot and Reframing (2026-06-16) | 52–120 | 9 | 14 | carried | TODO.md §1 Current Project State |
| `PCC` 1. Core Reframing | 121–161 | 6 | 0 | merged | TODO.md §2 |
| `PCC` 2. Main Hypotheses | 162–193 | 9 | 4 | merged | TODO.md §2 |
| `PCC` 3. Operational Definitions | 194–256 | 19 | 0 | merged | TODO.md §3 |
| `PCC` 4. Working Representation Families | 257–294 | 14 | 5 | merged | TODO.md §6 |
| `PCC` 5. Task Battery and Label Families | 295–372 | 35 | 6 | merged | TODO.md §4 |
| `PCC` 6. Data Plan | 373–417 | 20 | 3 | merged | TODO.md §5 |
| `PCC` 7. Track R — Reinterpret the Existing PCC Evidence | 418–447 | 9 | 0 | merged | TODO.md M1 |
| `PCC` 8. Track P — Position-Family Observational Program (No New MSAE Training) | 448–650 | 97 | 0 | merged | TODO.md M2–M4 |
| `PCC` 9. Track C — Controlled Contrast and Counterfactual Audit | 651–691 | 21 | 0 | merged | TODO.md M4 and M8 |
| `PCC` 10. Track D — Model-Side Candidate Experiments | 692–777 | 26 | 0 | merged | TODO.md §6–§7 and M5–M7 |
| `PCC` 11. Regularization Design | 778–817 | 17 | 0 | merged | TODO.md §9 and M6–M7 |
| `PCC` 12. Causal and Counterfactual Tests | 818–845 | 11 | 0 | merged | TODO.md M8–M10 |
| `PCC` 13. Metrics and Reporting | 846–903 | 30 | 0 | merged | TODO.md §3 and M8–M9 |
| `PCC` 14. Seed, Holdout, and Stability Requirements | 904–932 | 9 | 0 | merged | TODO.md §3, §5, M7–M9 |
| `PCC` 15. Proposed Experiment Order | 933–965 | 15 | 2 | merged | TODO.md §8 |
| `PCC` 16. Decision Gates | 966–1010 | 18 | 0 | merged | TODO.md §7 |
| `PCC` 17. Risks and Failure Modes | 1011–1036 | 14 | 0 | merged | TODO.md §11 |
| `PCC` 18. Immediate Next Actions | 1037–1072 | 0 | 0 | merged | TODO.md §14 |
| `PCC` 19. Deliverables | 1073–1089 | 15 | 0 | merged | TODO.md milestone output blocks |

## Item-level disposition

| ID | Source line | State | Enclosing heading | Source item | Disposition | Destination / evidence |
|---|---:|---|---|---|---|---|
| `MAIN-L0016` | 16 | done | Status Snapshot (2026-06-05) > Completed / Locked | Pre-K2 separability suite (`v6`) completed and archived under `reports/pre_k2_suite_v6/`. | carried | TODO.md §1 Current Project State |
| `MAIN-L0017` | 17 | done | Status Snapshot (2026-06-05) > Completed / Locked | Pre-K2 governance artifacts committed and tagged: | carried | TODO.md §1 Current Project State |
| `MAIN-L0022` | 22 | done | Status Snapshot (2026-06-05) > Completed / Locked | Paper 1 pre-K2 decision locked: | carried | TODO.md §1 Current Project State |
| `MAIN-L0027` | 27 | done | Status Snapshot (2026-06-05) > Completed / Locked | GPU-first K=2 trainer, wave evaluators, compatibility sweep scripts, and full pre-K2 reporting pipeline are implemented. | carried | TODO.md §1 Current Project State |
| `MAIN-L0028` | 28 | done | Status Snapshot (2026-06-05) > Completed / Locked | Fastdata-stream K=2 wave-2 run completed at: | carried | TODO.md §1 Current Project State |
| `MAIN-L0030` | 30 | done | Status Snapshot (2026-06-05) > Completed / Locked | Completed wave-2 jobs: | carried | TODO.md §1 Current Project State |
| `MAIN-L0037` | 37 | open | Status Snapshot (2026-06-05) > Active | Paper 1 post-wave follow-up experiments: | merged | TODO.md §1 Current Project State |
| `MAIN-L0040` | 40 | open | Status Snapshot (2026-06-05) > Active | PCC post-A1 interpretation and next-step decision capture: | merged | TODO.md §1 Current Project State |
| `MAIN-L0062` | 62 | done | Status Snapshot (2026-06-05) > Current Interpretation | The balanced/interleaved data-loader restart solved the prior throughput collapse without harming training quality. | carried | TODO.md §1 Current Project State |
| `MAIN-L0063` | 63 | done | Status Snapshot (2026-06-05) > Current Interpretation | `lambda_inc=1e-2` continues to produce a strong incoherence advantage over the matched no-inc control. | carried | TODO.md §1 Current Project State |
| `MAIN-L0064` | 64 | done | Status Snapshot (2026-06-05) > Current Interpretation | In the completed `1B`-token wave, all three regularized seeds finish with lower incoherence and slightly higher FVU than the no-inc control. | carried | TODO.md §1 Current Project State |
| `MAIN-L0065` | 65 | done | Status Snapshot (2026-06-05) > Current Interpretation | Active-latent utilization is healthy across both branches in the completed wave. | carried | TODO.md §1 Current Project State |
| `MAIN-L0066` | 66 | done | Status Snapshot (2026-06-05) > Current Interpretation | `L3` remains the primary Paper 1 training target; `L4` remains a contingency path only. | carried | TODO.md §1 Current Project State |
| `MAIN-L0067` | 67 | done | Status Snapshot (2026-06-05) > Current Interpretation | The first PCC Stage A0 batch is implemented and completed on GPUs `4,5,6,7` against the final `L3` checkpoints. | carried | TODO.md §1 Current Project State |
| `MAIN-L0068` | 68 | done | Status Snapshot (2026-06-05) > Current Interpretation | The first PCC-0 readout shows only small joint gains on the minimal task battery; this supports doing aggregation/decision work before any larger PCC architecture push. | carried | TODO.md §1 Current Project State |
| `MAIN-L0069` | 69 | done | Status Snapshot (2026-06-05) > Current Interpretation | PCC Stage A0 aggregate decision completed: | carried | TODO.md §1 Current Project State |
| `MAIN-L0073` | 73 | done | Status Snapshot (2026-06-05) > Current Interpretation | PCC Stage A1 expanded observational audit completed on GPUs `4,5,6,7`: | carried | TODO.md §1 Current Project State |
| `MAIN-L0078` | 78 | done | Status Snapshot (2026-06-05) > Current Interpretation | Under the current Stage A1 rule, PCC does **not** proceed to Stage B: | carried | TODO.md §1 Current Project State |
| `MAIN-L0083` | 83 | done | Status Snapshot (2026-06-05) > Current Interpretation | PCC Stage A1b diagnostic follow-up completed on the same four `L3` checkpoints: | carried | TODO.md §1 Current Project State |
| `MAIN-L0094` | 94 | done | Status Snapshot (2026-06-05) > Current Interpretation | A1b does **not** overturn the frozen A1 decision, but it does materially strengthen the amendment case: | carried | TODO.md §1 Current Project State |
| `MAIN-L0104` | 104 | done | Status Snapshot (2026-06-05) > Current Interpretation | A prospective PCC amendment draft now exists: | carried | TODO.md §1 Current Project State |
| `MAIN-L0107` | 107 | done | Status Snapshot (2026-06-05) > Current Interpretation | The PCC state was frozen before confirmation: | carried | TODO.md §1 Current Project State |
| `MAIN-L0113` | 113 | done | Status Snapshot (2026-06-05) > Current Interpretation | PCC Stage A1c confirmation completed on the same four `L3` checkpoints: | carried | TODO.md §1 Current Project State |
| `MAIN-L0129` | 129 | done | Status Snapshot (2026-06-05) > Current Interpretation | The PCC amendment is now adopted as a prospective governance artifact: | carried | TODO.md §1 Current Project State |
| `MAIN-L0138` | 138 | done | Status Snapshot (2026-06-05) > Current Interpretation | PCC Stage B-light control audit completed on the same checkpoint family: | carried | TODO.md §1 Current Project State |
| `MAIN-L0155` | 155 | done | Status Snapshot (2026-06-05) > Current Interpretation | The next scientifically important follow-up after the completed `1B` wave is not more scaling with the same setup, but targeted follow-up: | carried | TODO.md §1 Current Project State |
| `MAIN-L0168` | 168 | open | 0. Program Management, Governance, and Reproducibility > 0.1 Milestones and Decision Gates | Create milestone tracker with `M0`..`M8`: | merged | TODO.md §0, §5, §10 |
| `MAIN-L0178` | 178 | open | 0. Program Management, Governance, and Reproducibility > 0.1 Milestones and Decision Gates | Define owner(s), deadline, and exit criteria for each milestone. | merged | TODO.md §0, §5, §10 |
| `MAIN-L0179` | 179 | done | 0. Program Management, Governance, and Reproducibility > 0.1 Milestones and Decision Gates | `M0` is effectively complete: prereg, pre-K2 suite, gate report, trainer, and wave launch infrastructure exist. | carried | TODO.md §0, §5, §10 |
| `MAIN-L0182` | 182 | done | 0. Program Management, Governance, and Reproducibility > 0.2 Preregistration and Freeze Rules | Create `prereg/` directory. | carried | TODO.md §0, §5, §10 |
| `MAIN-L0183` | 183 | done | 0. Program Management, Governance, and Reproducibility > 0.2 Preregistration and Freeze Rules | Add pre-K2 prereg / gate files: | carried | TODO.md §0, §5, §10 |
| `MAIN-L0186` | 186 | done | 0. Program Management, Governance, and Reproducibility > 0.2 Preregistration and Freeze Rules | Timestamp and git-tag prereg / gate commits before K=2 wave launch: | carried | TODO.md §0, §5, §10 |
| `MAIN-L0189` | 189 | done | 0. Program Management, Governance, and Reproducibility > 0.2 Preregistration and Freeze Rules | Add policy: no threshold changes after training starts without a versioned amendment file. | carried | TODO.md §0, §5, §10 |
| `MAIN-L0190` | 190 | open | 0. Program Management, Governance, and Reproducibility > 0.2 Preregistration and Freeze Rules | Add paper-specific prereg files for Paper 2 and Paper 3: | merged | TODO.md §0, §5, §10 |
| `MAIN-L0197` | 197 | open | 0. Program Management, Governance, and Reproducibility > 0.3 Experiment Registry and Naming | Create `experiments/registry.csv` with columns: | merged | TODO.md §0, §5, §10 |
| `MAIN-L0199` | 199 | open | 0. Program Management, Governance, and Reproducibility > 0.3 Experiment Registry and Naming | Establish run naming convention: | merged | TODO.md §0, §5, §10 |
| `MAIN-L0201` | 201 | open | 0. Program Management, Governance, and Reproducibility > 0.3 Experiment Registry and Naming | Add mandatory metadata logging for each run: | merged | TODO.md §0, §5, §10 |
| `MAIN-L0205` | 205 | open | 0. Program Management, Governance, and Reproducibility > 0.4 Statistical Testing Infrastructure | Implement shared stats module: | merged | TODO.md §0, §5, §10 |
| `MAIN-L0209` | 209 | open | 0. Program Management, Governance, and Reproducibility > 0.4 Statistical Testing Infrastructure | Standardize confidence interval reporting format. | merged | TODO.md §0, §5, §10 |
| `MAIN-L0210` | 210 | open | 0. Program Management, Governance, and Reproducibility > 0.4 Statistical Testing Infrastructure | Add guardrails for multiple comparison pitfalls in ablation-heavy sections. | merged | TODO.md §0, §5, §10 |
| `MAIN-L0217` | 217 | open | 1. Codebase and Infrastructure > 1.1 Repository Structure | Create directories: | merged | TODO.md M6 and §10 |
| `MAIN-L0226` | 226 | open | 1. Codebase and Infrastructure > 1.1 Repository Structure | Add paper-specific config trees: | merged | TODO.md M6 and §10 |
| `MAIN-L0232` | 232 | done | 1. Codebase and Infrastructure > 1.2 Core Training Framework | Build GPU-first custom K=2 MSAE trainer abstraction: | carried | TODO.md M6 and §10 |
| `MAIN-L0236` | 236 | open | 1. Codebase and Infrastructure > 1.2 Core Training Framework | Extend trainer to Paper 2/3 heterogeneity: | merged | TODO.md M6 and §10 |
| `MAIN-L0239` | 239 | done | 1. Codebase and Infrastructure > 1.2 Core Training Framework | Implement decoder unit-norm constraints and projected gradient updates. | carried | TODO.md M6 and §10 |
| `MAIN-L0240` | 240 | done | 1. Codebase and Infrastructure > 1.2 Core Training Framework | Implement dead-latent tracking and AuxK revival for sparse branches. | carried | TODO.md M6 and §10 |
| `MAIN-L0243` | 243 | done | 1. Codebase and Infrastructure > 1.3 Logging and Monitoring | Log every configurable interval: | carried | TODO.md M6 and §10 |
| `MAIN-L0246` | 246 | open | 1. Codebase and Infrastructure > 1.3 Logging and Monitoring | Add explicit absorption-oriented diagnostics for Paper 1 follow-up: | merged | TODO.md M6 and §10 |
| `MAIN-L0249` | 249 | open | 1. Codebase and Infrastructure > 1.3 Logging and Monitoring | Log every 5,000 steps: | merged | TODO.md M6 and §10 |
| `MAIN-L0252` | 252 | open | 1. Codebase and Infrastructure > 1.3 Logging and Monitoring | For dense branch (Paper 2+): log effective rank and singular-value spectrum. | merged | TODO.md M6 and §10 |
| `MAIN-L0255` | 255 | open | 1. Codebase and Infrastructure > 1.4 Determinism and Seed Controls | Seed all RNG sources and record seed provenance. | merged | TODO.md M6 and §10 |
| `MAIN-L0256` | 256 | open | 1. Codebase and Infrastructure > 1.4 Determinism and Seed Controls | Save activation shuffle seeds and bucket ordering hashes. | merged | TODO.md M6 and §10 |
| `MAIN-L0257` | 257 | open | 1. Codebase and Infrastructure > 1.4 Determinism and Seed Controls | Add reproducibility test: repeated tiny run reproduces same metrics within tolerance. | merged | TODO.md M6 and §10 |
| `MAIN-L0264` | 264 | open | 2. Data and Activation Pipelines > 2.1 Corpora and Splits | Define training corpus snapshots: | merged | TODO.md §5 and §10 |
| `MAIN-L0267` | 267 | open | 2. Data and Activation Pipelines > 2.1 Corpora and Splits | Define evaluation/holdout activation set: | merged | TODO.md §5 and §10 |
| `MAIN-L0269` | 269 | open | 2. Data and Activation Pipelines > 2.1 Corpora and Splits | Define filtering rules: | merged | TODO.md §5 and §10 |
| `MAIN-L0273` | 273 | open | 2. Data and Activation Pipelines > 2.2 Activation Extraction | Implement activation extraction for: | merged | TODO.md §5 and §10 |
| `MAIN-L0277` | 277 | open | 2. Data and Activation Pipelines > 2.2 Activation Extraction | Implement buffered activation storage (1e6-item bucket shuffle). | merged | TODO.md §5 and §10 |
| `MAIN-L0278` | 278 | open | 2. Data and Activation Pipelines > 2.2 Activation Extraction | Persist dataset lineage and sampling script hashes. | merged | TODO.md §5 and §10 |
| `MAIN-L0281` | 281 | open | 2. Data and Activation Pipelines > 2.3 Probe Dataset Builders | Position labels (0–1023 or specified bucketing). | merged | TODO.md §5 and §10 |
| `MAIN-L0282` | 282 | open | 2. Data and Activation Pipelines > 2.3 Probe Dataset Builders | Token identity labels (top-1024 bucket with defined OOV handling). | merged | TODO.md §5 and §10 |
| `MAIN-L0283` | 283 | open | 2. Data and Activation Pipelines > 2.3 Probe Dataset Builders | Matched-token different-position pairs for invariance. | merged | TODO.md §5 and §10 |
| `MAIN-L0284` | 284 | open | 2. Data and Activation Pipelines > 2.3 Probe Dataset Builders | Relative-position synthetic task dataset for causal probe. | merged | TODO.md §5 and §10 |
| `MAIN-L0285` | 285 | open | 2. Data and Activation Pipelines > 2.3 Probe Dataset Builders | Syntax/semantics/frequency probe datasets for Paper 2 unsupervised discovery. | merged | TODO.md §5 and §10 |
| `MAIN-L0292` | 292 | open | 3. Stage 0 (Pre-Paper) Synthetic Identifiability Sandbox > 3.1 Planted Data Generator | Implement synthetic generator for: | merged | TODO.md M2b |
| `MAIN-L0296` | 296 | open | 3. Stage 0 (Pre-Paper) Synthetic Identifiability Sandbox > 3.1 Planted Data Generator | Add sparse + low-rank variant for forward compatibility. | merged | TODO.md M2b |
| `MAIN-L0299` | 299 | open | 3. Stage 0 (Pre-Paper) Synthetic Identifiability Sandbox > 3.2 Recovery Procedure | Implement alternating l1 minimization / sparse recovery baseline. | merged | TODO.md M2b |
| `MAIN-L0300` | 300 | open | 3. Stage 0 (Pre-Paper) Synthetic Identifiability Sandbox > 3.2 Recovery Procedure | Implement MSAE-style training on synthetic samples. | merged | TODO.md M2b |
| `MAIN-L0301` | 301 | open | 3. Stage 0 (Pre-Paper) Synthetic Identifiability Sandbox > 3.2 Recovery Procedure | Sweep: | merged | TODO.md M2b |
| `MAIN-L0306` | 306 | open | 3. Stage 0 (Pre-Paper) Synthetic Identifiability Sandbox > 3.3 Outputs | Phase diagram figure: | merged | TODO.md M2b |
| `MAIN-L0308` | 308 | open | 3. Stage 0 (Pre-Paper) Synthetic Identifiability Sandbox > 3.3 Outputs | Theoretical overlay figure: | merged | TODO.md M2b |
| `MAIN-L0310` | 310 | open | 3. Stage 0 (Pre-Paper) Synthetic Identifiability Sandbox > 3.3 Outputs | Write short methods note for reuse in Paper 1 theory section. | merged | TODO.md M2b |
| `MAIN-L0313` | 313 | open | 3. Stage 0 (Pre-Paper) Synthetic Identifiability Sandbox > 3.3 Outputs | Synthetic pipeline stable, figures reproducible, and recovery trends qualitatively match theory expectations. | merged | TODO.md M2b |
| `MAIN-L0320` | 320 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.0 Raw-Activation Separability Pilot (No SAE, Required) | Train raw-activation linear probes for position and token identity on Pythia-160M layers 3 and 4. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0321` | 321 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.0 Raw-Activation Separability Pilot (No SAE, Required) | Construct probe-derived subspaces (`S_pos`, `S_tok`) via SVD at ranks `{8,16,32}`. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0322` | 322 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.0 Raw-Activation Separability Pilot (No SAE, Required) | Evaluate projected performance on `Proj_{S_pos}`, `Proj_{S_pos^perp}`, `Proj_{S_tok}`, `Proj_{S_tok^perp}`. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0323` | 323 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.0 Raw-Activation Separability Pilot (No SAE, Required) | Compute principal-angle and cross-projection overlap diagnostics. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0324` | 324 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.0 Raw-Activation Separability Pilot (No SAE, Required) | Enforce pilot pass thresholds before launching K=2 training. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0325` | 325 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.0 Raw-Activation Separability Pilot (No SAE, Required) | Resolve layer target from pilot: | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0328` | 328 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.0 Raw-Activation Separability Pilot (No SAE, Required) | Archive pilot outputs and gate report in `reports/pre_k2_suite_v6/`. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0331` | 331 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.1 Finalize Paper 1 Prereg | Lock thresholds for the pre-K2 decision suite. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0332` | 332 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.1 Finalize Paper 1 Prereg | Lock baseline set and reporting protocol for the pre-K2 gate. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0333` | 333 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.1 Finalize Paper 1 Prereg | Lock final Paper 1 post-training reporting bundle for the K=2 paper draft: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0337` | 337 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.1 Finalize Paper 1 Prereg | Lock robustness addendum criterion for regularizer warmdown stability. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0340` | 340 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.2 Implement Paper 1 Architecture | Branch `D_position`: TopK, `m_pos=8k`, `k_pos=8`. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0341` | 341 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.2 Implement Paper 1 Architecture | Branch `D_content`: TopK, `m_content=32k`, `k_content=24`. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0342` | 342 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.2 Implement Paper 1 Architecture | Quadratic cross-branch incoherence loss `lambda_inc \|\|D_pos^T D_content\|\|_F^2 / (m_pos*m_content)` estimator. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0343` | 343 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.2 Implement Paper 1 Architecture | AuxK and dead-latent revival. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0344` | 344 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.2 Implement Paper 1 Architecture | Extend Paper 1 trainer with generalized coherence family and scope controls: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0350` | 350 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.3 Train Main Model Runs | Train 5 seeds for headline config: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0356` | 356 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.3 Train Main Model Runs | Launch wave-1 `100M` token runs: | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0361` | 361 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.3 Train Main Model Runs | Promote to wave-2 `1B` token run set from approved checkpoints. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0362` | 362 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.3 Train Main Model Runs | Add fourth live baseline on GPU `6`: | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0364` | 364 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.3 Train Main Model Runs | Finish wave-2 runs and archive final summaries. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0365` | 365 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.3 Train Main Model Runs | Decide which regularized seeds become headline Paper 1 runs after `1B` completion. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0368` | 368 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.4 Initialization Variant Runs | Random Gaussian init (baseline). | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0369` | 369 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.4 Initialization Variant Runs | Fourier-biased position init + random content init. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0370` | 370 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.4 Initialization Variant Runs | PCA-conditioned init from holdout diagnostics. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0373` | 373 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.5 Baselines (Required) | K=1 matched-parameter SAE (`m=40k`), post-hoc position/content split. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0374` | 374 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.5 Baselines (Required) | K=2 no-incoherence baseline (`lambda_inc=0`) launched and completed through wave-2. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0375` | 375 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.5 Baselines (Required) | Optional extra comparisons if budget allows: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0379` | 379 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.7 PCC Follow-On Audit | Execute `TODO_pcc.md` Stage A0 on final `L3` wave-2 checkpoints. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0387` | 387 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.7 PCC Follow-On Audit | Run minimal PCC-0 battery: | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0391` | 391 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.7 PCC Follow-On Audit | Aggregate `joint_gain` across completed `g4/g5/g6` regularized checkpoints and `g7` no-inc control. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0399` | 399 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.7 PCC Follow-On Audit | Execute expanded PCC Stage A1 observational audit on the same `L3` checkpoint family. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0407` | 407 | done | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.7 PCC Follow-On Audit | Decide whether PCC proceeds to Stage B or stops with a no-PCC-go outcome. | carried | TODO.md M0–M10 and §9 |
| `MAIN-L0418` | 418 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6 Paper 1 Ablation Matrix | Incoherence sweep: `lambda_inc in {0,1e-4,1e-3,1e-2,1e-1}`. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0419` | 419 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6 Paper 1 Ablation Matrix | Regularizer warmdown/hysteresis: finetune 1-2B tokens with `lambda_inc=0` after converged training; track coherence drift and probe degradation. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0420` | 420 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6 Paper 1 Ablation Matrix | Sparsity allocation sweep: `(k_pos,k_content) in {(4,28),(8,24),(16,16),(24,8)}`. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0421` | 421 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6 Paper 1 Ablation Matrix | Width allocation sweep at `m_total=40k`: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0423` | 423 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6 Paper 1 Ablation Matrix | Init sweep as above. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0426` | 426 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6A Coherence Penalty Family and Scope Experiments | Add coherence-penalty family sweep motivated by `neurips_2026_feature_absorption.pdf`. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0427` | 427 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6A Coherence Penalty Family and Scope Experiments | Implement penalty-shape sweep on the cross-branch Gram matrix: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0430` | 430 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6A Coherence Penalty Family and Scope Experiments | Implement penalty-scope sweep: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0434` | 434 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6A Coherence Penalty Family and Scope Experiments | Run short-budget smoke ablation (`25M` to `100M` tokens) for the penalty family/scope grid before any long reruns. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0435` | 435 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6A Coherence Penalty Family and Scope Experiments | Promote only the best one or two penalty variants to longer `300M` or `1B` follow-up budgets. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0436` | 436 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6A Coherence Penalty Family and Scope Experiments | Track collapse/suppression diagnostics during these sweeps: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0442` | 442 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6A Coherence Penalty Family and Scope Experiments | Add anti-suppression evaluation: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0446` | 446 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6A Coherence Penalty Family and Scope Experiments | Compare all penalty-family results to the current quadratic baseline (`p=2`, cross only) on: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0453` | 453 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6B Absorption-Oriented Follow-Up Evaluations | Add a feature-absorption / overlap audit for K=2 branches: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0457` | 457 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6B Absorption-Oriented Follow-Up Evaluations | Evaluate whether lower incoherence reflects true specialization rather than feature suppression. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0458` | 458 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.6B Absorption-Oriented Follow-Up Evaluations | Use matched-seed `g4` vs `g7` as the primary causal ablation for Paper 1 regularizer claims. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0461` | 461 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.7 Four-Probe Evaluation Suite | Probe 1 position prediction: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0464` | 464 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.7 Four-Probe Evaluation Suite | Probe 2 token identity prediction: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0466` | 466 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.7 Four-Probe Evaluation Suite | Probe 3 position invariance: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0469` | 469 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.7 Four-Probe Evaluation Suite | Probe 4 causal intervention: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0474` | 474 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.8 Seed Stability Analysis | Train/evaluate 5 seeds for all headline and core baseline configs. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0475` | 475 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.8 Seed Stability Analysis | Implement Paulo-Belrose Hungarian matching: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0477` | 477 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.8 Seed Stability Analysis | Report: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0483` | 483 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.9 Theory Section Assets | Estimate empirical `mu_hat(D_pos,D_content)` trajectory during training. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0484` | 484 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.9 Theory Section Assets | Estimate descent-cone statistics over training snapshots. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0485` | 485 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.9 Theory Section Assets | Draft explicit caveat text on sufficient-vs-necessary bounds. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0486` | 486 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.9 Theory Section Assets | Draft short conjectural ER-SpUD adaptation paragraph (clearly marked as conjecture). | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0489` | 489 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.10 IOI Case Study | Define IOI-compatible evaluation pipeline for Pythia-160M lower layers. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0490` | 490 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.10 IOI Case Study | Quantify branch-specific logit-difference retention under `D_pos` and `D_content` clamping. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0491` | 491 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.10 IOI Case Study | Quantify attribution concentration of position-sensitive IOI signal across branches. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0492` | 492 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.10 IOI Case Study | Quantify cross-branch leakage on control tasks with predeclared thresholds. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0493` | 493 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.10 IOI Case Study | Produce one figure + one table with preregistered metrics. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0496` | 496 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.11 Paper 1 Gate Computation | Compute 5 core prereg criteria on 5-seed means. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0497` | 497 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.11 Paper 1 Gate Computation | Compute regularizer warmdown robustness addendum criterion. | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0498` | 498 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.11 Paper 1 Gate Computation | Produce gate report: | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0504` | 504 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.11 Paper 1 Gate Computation | `results/paper1/summary.csv` | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0505` | 505 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.11 Paper 1 Gate Computation | `figures/paper1/*.png` | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0506` | 506 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.11 Paper 1 Gate Computation | `docs/paper1_methods.md` | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0507` | 507 | open | 4. Paper 1 Execution (K=2 Position-vs-Content) > 4.11 Paper 1 Gate Computation | `docs/paper1_gate_report.md` | merged | TODO.md M0–M10 and §9 |
| `MAIN-L0514` | 514 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) | Paper 1 gate outcome reviewed and approved for progression. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0517` | 517 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.1 Finalize Paper 2 Prereg | Freeze 7 success criteria. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0518` | 518 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.1 Finalize Paper 2 Prereg | Freeze SAEBench and Kantamneni comparison protocol details. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0521` | 521 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.2 Implement Paper 2 Architecture | `D1`: TopK, `k=32`, `m1=65k`. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0522` | 522 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.2 Implement Paper 2 Architecture | `D2`: JumpReLU, `m2=16k`, `eps=1e-3`, threshold init `1e-3`. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0523` | 523 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.2 Implement Paper 2 Architecture | `D3`: dense low-rank branch `UV^T`, `r<=64`, no sparsity. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0524` | 524 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.2 Implement Paper 2 Architecture | Incoherence terms: | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0529` | 529 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.3 Train Main Runs (Gemma-2-2B, Layer 12) | Match SAEBench training recipe: | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0533` | 533 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.3 Train Main Runs (Gemma-2-2B, Layer 12) | Train 5 seeds at headline config. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0536` | 536 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.4 Monitoring and Diagnostics | Log `mu_hat_{jk}` every 1000 steps. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0537` | 537 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.4 Monitoring and Diagnostics | Log Babel proxy every 5000 steps. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0538` | 538 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.4 Monitoring and Diagnostics | Log per-branch and total FVU. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0539` | 539 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.4 Monitoring and Diagnostics | Log descent-cone estimates. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0540` | 540 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.4 Monitoring and Diagnostics | Log dense-branch effective rank utilization. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0543` | 543 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.5 Supporting Experiment: K=2 Attention-vs-MLP | Build activation hooks for attention output and MLP output at layer 12. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0544` | 544 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.5 Supporting Experiment: K=2 Attention-vs-MLP | Train constrained/anchored K=2 model. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0545` | 545 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.5 Supporting Experiment: K=2 Attention-vs-MLP | Evaluate with dedicated probes: | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0550` | 550 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.6 Unsupervised K=2 Discovery Experiment | Train random-init K=2 with incoherence-only structural bias. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0551` | 551 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.6 Unsupervised K=2 Discovery Experiment | Run full probe battery (position/content + syntax/frequency + attention/MLP). | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0552` | 552 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.6 Unsupervised K=2 Discovery Experiment | Determine discovered split via peak probe signal. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0553` | 553 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.6 Unsupervised K=2 Discovery Experiment | Quantify consistency across seeds. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0556` | 556 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.7 Dark-Matter Validation | Compute variance explained by `D3`. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0557` | 557 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.7 Dark-Matter Validation | Measure residual linear predictability from input activations. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0558` | 558 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.7 Dark-Matter Validation | Compare with and without dense branch. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0559` | 559 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.7 Dark-Matter Validation | Compare against frozen rank-matched PCA control branch. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0560` | 560 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.7 Dark-Matter Validation | Analyze top singular directions of `D3` for reproducible structured alignment across seeds. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0561` | 561 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.7 Dark-Matter Validation | Verify target conditions in prereg thresholds. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0564` | 564 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.8 Full SAEBench Evaluation | Run all 8 SAEBench families at `L0 in {20,40,80,160,320,640}`. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0565` | 565 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.8 Full SAEBench Evaluation | Baselines at matched L0: | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0569` | 569 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.8 Full SAEBench Evaluation | Run 5 seeds for each comparable system where feasible. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0572` | 572 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.9 Kantamneni 113-Task Benchmark | Reproduce protocol on Gemma-2-9B layer 20 for probing comparison. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0573` | 573 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.9 Kantamneni 113-Task Benchmark | Evaluate MSAE probe vs: | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0576` | 576 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.9 Kantamneni 113-Task Benchmark | Run Quiver-of-Arrows style toolkit test with MSAE probe added. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0579` | 579 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.10 Paper 2 Ablation Matrix | `K` sweep: `{1,2,3,4,6}`. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0580` | 580 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.10 Paper 2 Ablation Matrix | `lambda_inc` sweep: `{0,1e-4,1e-3,1e-2,1e-1}`. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0581` | 581 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.10 Paper 2 Ablation Matrix | Branch heterogeneity sweep: | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0583` | 583 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.10 Paper 2 Ablation Matrix | Dense branch off/on ablation. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0584` | 584 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.10 Paper 2 Ablation Matrix | Dense branch learned-vs-frozen-PCA control ablation. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0585` | 585 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.10 Paper 2 Ablation Matrix | Width allocation at fixed total budget: | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0587` | 587 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.10 Paper 2 Ablation Matrix | Encoder tying / projection-trick ablation. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0590` | 590 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.11 Paper 2 Gate Computation | Evaluate all 7 prereg criteria using 5-seed means. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0591` | 591 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.11 Paper 2 Gate Computation | Run bootstrap + BH-corrected significance across metric families. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0592` | 592 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.11 Paper 2 Gate Computation | Publish gate report with pass/fail and suggested next action. | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0595` | 595 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.11 Paper 2 Gate Computation | `results/paper2/summary.csv` | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0596` | 596 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.11 Paper 2 Gate Computation | `results/paper2/saebench_table.csv` | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0597` | 597 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.11 Paper 2 Gate Computation | `results/paper2/kantamneni_table.csv` | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0598` | 598 | open | 5. Paper 2 Execution (K=3 Generalized MSAE) > 5.11 Paper 2 Gate Computation | `docs/paper2_gate_report.md` | superseded | TODO.md §13 Future Paper 2; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0605` | 605 | open | 6. Paper 3 Execution (Structured Branches) | Paper 2 gate outcome reviewed and approved for progression. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0608` | 608 | open | 6. Paper 3 Execution (Structured Branches) > 6.1 Finalize Paper 3 Prereg | Freeze 4 success criteria. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0609` | 609 | open | 6. Paper 3 Execution (Structured Branches) > 6.1 Finalize Paper 3 Prereg | Freeze evaluation protocols for Engels and Chanin benchmarks. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0612` | 612 | open | 6. Paper 3 Execution (Structured Branches) > 6.2 Implement Structured Branches | `D_subspace` branch: | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0617` | 617 | open | 6. Paper 3 Execution (Structured Branches) > 6.2 Implement Structured Branches | `D_multiscale` branch: | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0620` | 620 | open | 6. Paper 3 Execution (Structured Branches) > 6.2 Implement Structured Branches | Integrate with Paper 2 backbone and coherence penalties. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0623` | 623 | open | 6. Paper 3 Execution (Structured Branches) > 6.3 Train Main Runs | Run Paper 3 feasibility pilot first (50M tokens, 3 seeds, reduced-width K=5). | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0624` | 624 | open | 6. Paper 3 Execution (Structured Branches) > 6.3 Train Main Runs | Check pilot convergence gate before full sweep. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0625` | 625 | open | 6. Paper 3 Execution (Structured Branches) > 6.3 Train Main Runs | Gemma-2-2B layer 12, 500M tokens, 5 seeds. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0626` | 626 | open | 6. Paper 3 Execution (Structured Branches) > 6.3 Train Main Runs | Preserve Paper 2 baseline comparability. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0629` | 629 | open | 6. Paper 3 Execution (Structured Branches) > 6.4 Validation: Engels Circular Features | Implement or integrate Engels discovery pipeline. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0630` | 630 | open | 6. Paper 3 Execution (Structured Branches) > 6.4 Validation: Engels Circular Features | Evaluate whether circular features are captured as single 2D atoms/subspaces. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0631` | 631 | open | 6. Paper 3 Execution (Structured Branches) > 6.4 Validation: Engels Circular Features | Compute: | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0635` | 635 | open | 6. Paper 3 Execution (Structured Branches) > 6.4 Validation: Engels Circular Features | Run causal clamping interventions on recovered subspace atoms. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0638` | 638 | open | 6. Paper 3 Execution (Structured Branches) > 6.5 Validation: Chanin Absorption | Run first-letter absorption benchmark at `L0 in {40,80,160}`. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0639` | 639 | open | 6. Paper 3 Execution (Structured Branches) > 6.5 Validation: Chanin Absorption | Compare directly to Matryoshka at matched settings. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0640` | 640 | open | 6. Paper 3 Execution (Structured Branches) > 6.5 Validation: Chanin Absorption | Report: | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0646` | 646 | open | 6. Paper 3 Execution (Structured Branches) > 6.6 Theoretical Section Assets | Draft atomic-norm formulation for structured branches. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0647` | 647 | open | 6. Paper 3 Execution (Structured Branches) > 6.6 Theoretical Section Assets | Add combined descent-dimension estimation for full architecture. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0648` | 648 | open | 6. Paper 3 Execution (Structured Branches) > 6.6 Theoretical Section Assets | Clearly delimit theorem-backed vs heuristic components. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0651` | 651 | open | 6. Paper 3 Execution (Structured Branches) > 6.7 Mechanistic Case Studies | Case Study 1: modular arithmetic/temporal circuit tracing with subspace atoms. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0652` | 652 | open | 6. Paper 3 Execution (Structured Branches) > 6.7 Mechanistic Case Studies | Case Study 2: SHIFT/SCR Bias-in-Bios debiasing with MSAE features. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0653` | 653 | open | 6. Paper 3 Execution (Structured Branches) > 6.7 Mechanistic Case Studies | Compare compactness/targeting vs standard SAE feature pipelines. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0656` | 656 | open | 6. Paper 3 Execution (Structured Branches) > 6.8 Paper 3 Gate Computation | Evaluate 4 prereg criteria on 5-seed means. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0657` | 657 | open | 6. Paper 3 Execution (Structured Branches) > 6.8 Paper 3 Gate Computation | Produce final go/no-go with effect sizes and uncertainty. | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0660` | 660 | open | 6. Paper 3 Execution (Structured Branches) > 6.8 Paper 3 Gate Computation | `results/paper3/summary.csv` | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0661` | 661 | open | 6. Paper 3 Execution (Structured Branches) > 6.8 Paper 3 Gate Computation | `results/paper3/engels_metrics.csv` | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0662` | 662 | open | 6. Paper 3 Execution (Structured Branches) > 6.8 Paper 3 Gate Computation | `results/paper3/chanin_metrics.csv` | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0663` | 663 | open | 6. Paper 3 Execution (Structured Branches) > 6.8 Paper 3 Gate Computation | `docs/paper3_gate_report.md` | superseded | TODO.md §13 Future Paper 3; execution is blocked by G5 and must be freshly preregistered after the next-paper gate |
| `MAIN-L0670` | 670 | open | 7. Shared Evaluation and Analysis Tasks > 7.1 Unified Metric Definitions | Create single source-of-truth metric spec with formulas and split definitions. | merged | TODO.md M8, M9, M11 |
| `MAIN-L0671` | 671 | open | 7. Shared Evaluation and Analysis Tasks > 7.1 Unified Metric Definitions | Add strict compatibility checks so each run can be scored by the same evaluator. | merged | TODO.md M8, M9, M11 |
| `MAIN-L0674` | 674 | open | 7. Shared Evaluation and Analysis Tasks > 7.2 Visualization Pack | Standard plotting scripts for: | merged | TODO.md M8, M9, M11 |
| `MAIN-L0683` | 683 | open | 7. Shared Evaluation and Analysis Tasks > 7.3 Error Analysis Templates | Build templates for analyzing gate failures: | merged | TODO.md M8, M9, M11 |
| `MAIN-L0688` | 688 | open | 7. Shared Evaluation and Analysis Tasks > 7.3 Error Analysis Templates | Ensure each failed criterion yields a diagnostic note and proposed remediation. | merged | TODO.md M8, M9, M11 |
| `MAIN-L0695` | 695 | open | 8. Compute and Scheduling Plan > 8.1 Capacity Planning | Reserve compute blocks aligned to program estimates: | merged | TODO.md M7 and §10 |
| `MAIN-L0699` | 699 | open | 8. Compute and Scheduling Plan > 8.1 Capacity Planning | Maintain queue of high-priority runs (gate-critical first). | merged | TODO.md M7 and §10 |
| `MAIN-L0702` | 702 | open | 8. Compute and Scheduling Plan > 8.2 Budget Tracking | Log GPU-hours per run and cumulative totals by paper. | merged | TODO.md M7 and §10 |
| `MAIN-L0703` | 703 | open | 8. Compute and Scheduling Plan > 8.2 Budget Tracking | Track baseline-reproduction overhead separately (Matryoshka/BatchTopK/JumpReLU reruns). | merged | TODO.md M7 and §10 |
| `MAIN-L0704` | 704 | open | 8. Compute and Scheduling Plan > 8.2 Budget Tracking | Add automated alerts for budget overruns. | merged | TODO.md M7 and §10 |
| `MAIN-L0705` | 705 | open | 8. Compute and Scheduling Plan > 8.2 Budget Tracking | Re-prioritize ablations if gate-critical budget is threatened. | merged | TODO.md M7 and §10 |
| `MAIN-L0708` | 708 | open | 8. Compute and Scheduling Plan > 8.4 Inference Cost Tracking | Benchmark inference-time throughput and latency for K=1 vs K=2 vs K=3 vs K=5 feature extraction. | merged | TODO.md M7 and §10 |
| `MAIN-L0709` | 709 | open | 8. Compute and Scheduling Plan > 8.4 Inference Cost Tracking | Benchmark peak memory footprint and activation-cache overhead by architecture. | merged | TODO.md M7 and §10 |
| `MAIN-L0710` | 710 | open | 8. Compute and Scheduling Plan > 8.4 Inference Cost Tracking | Report compute tax of multi-branch MSAE in Paper 2 and Paper 3 result tables. | merged | TODO.md M7 and §10 |
| `MAIN-L0713` | 713 | open | 8. Compute and Scheduling Plan > 8.3 Runtime QA | Add spot-check runs to validate new config changes before full sweeps. | merged | TODO.md M7 and §10 |
| `MAIN-L0714` | 714 | open | 8. Compute and Scheduling Plan > 8.3 Runtime QA | Add checkpoint resume tests for long jobs. | merged | TODO.md M7 and §10 |
| `MAIN-L0715` | 715 | open | 8. Compute and Scheduling Plan > 8.3 Runtime QA | Add divergence detectors (NaN, dead-latent collapse, runaway coherence). | merged | TODO.md M7 and §10 |
| `MAIN-L0722` | 722 | open | 9. Writing and Publication Pipeline > 9.1 Paper Draft Skeletons | Create docs skeletons: | merged | TODO.md M11–M12 |
| `MAIN-L0726` | 726 | open | 9. Writing and Publication Pipeline > 9.1 Paper Draft Skeletons | Pre-map each figure/table to exact run IDs. | merged | TODO.md M11–M12 |
| `MAIN-L0729` | 729 | open | 9. Writing and Publication Pipeline > 9.2 Claims-to-Evidence Table | Maintain `docs/claims_matrix.csv` with columns: | merged | TODO.md M11–M12 |
| `MAIN-L0731` | 731 | open | 9. Writing and Publication Pipeline > 9.2 Claims-to-Evidence Table | Enforce: no claim without linked evidence artifact. | merged | TODO.md M11–M12 |
| `MAIN-L0734` | 734 | open | 9. Writing and Publication Pipeline > 9.3 Artifact Packaging | Create reproducibility bundle per paper: | merged | TODO.md M11–M12 |
| `MAIN-L0740` | 740 | open | 9. Writing and Publication Pipeline > 9.3 Artifact Packaging | Add README with exact reproduction steps and expected outputs. | merged | TODO.md M11–M12 |
| `MAIN-L0747` | 747 | open | 10. High-Risk Items and Mitigations > 10.1 Risk: Coherence Regularizer Is Doing All Work | Run explicit `lambda_inc=0` and decay-to-zero tests. | merged | TODO.md §11 |
| `MAIN-L0748` | 748 | open | 10. High-Risk Items and Mitigations > 10.1 Risk: Coherence Regularizer Is Doing All Work | Document robustness of decomposition without heavy regularization. | merged | TODO.md §11 |
| `MAIN-L0751` | 751 | open | 10. High-Risk Items and Mitigations > 10.2 Risk: Dense Branch Trivializes Sparse Branches | Track dense variance capture; set red-line thresholds. | merged | TODO.md §11 |
| `MAIN-L0752` | 752 | open | 10. High-Risk Items and Mitigations > 10.2 Risk: Dense Branch Trivializes Sparse Branches | Constrain/ablate rank and test if sparse branches remain informative. | merged | TODO.md §11 |
| `MAIN-L0755` | 755 | open | 10. High-Risk Items and Mitigations > 10.3 Risk: No Probe Gains vs Baselines | Run targeted diagnosis: | merged | TODO.md §11 |
| `MAIN-L0759` | 759 | open | 10. High-Risk Items and Mitigations > 10.3 Risk: No Probe Gains vs Baselines | Decide whether to reframe as negative-result contribution. | merged | TODO.md §11 |
| `MAIN-L0762` | 762 | open | 10. High-Risk Items and Mitigations > 10.4 Risk: Seed Stability Does Not Improve | Diagnose matching sensitivity and overlap criterion robustness. | merged | TODO.md §11 |
| `MAIN-L0763` | 763 | open | 10. High-Risk Items and Mitigations > 10.4 Risk: Seed Stability Does Not Improve | Test alternate init and sparsity allocations before abandoning claim. | merged | TODO.md §11 |
| `MAIN-L0766` | 766 | open | 10. High-Risk Items and Mitigations > 10.5 Risk: SAEBench Underperformance vs Matryoshka | Identify metric families with best deltas; quantify tradeoffs explicitly. | merged | TODO.md §11 |
| `MAIN-L0767` | 767 | open | 10. High-Risk Items and Mitigations > 10.5 Risk: SAEBench Underperformance vs Matryoshka | Reframe claims around wins (if consistent) rather than global leadership. | merged | TODO.md §11 |
| `MAIN-L0774` | 774 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 1 | Synthetic sandbox complete. | merged | TODO.md §12–§13 |
| `MAIN-L0775` | 775 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 1 | 5-seed headline runs complete. | merged | TODO.md §12–§13 |
| `MAIN-L0776` | 776 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 1 | Two mandatory baselines complete. | merged | TODO.md §12–§13 |
| `MAIN-L0777` | 777 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 1 | Core ablations complete. | merged | TODO.md §12–§13 |
| `MAIN-L0778` | 778 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 1 | Four probes + seed stability complete. | merged | TODO.md §12–§13 |
| `MAIN-L0779` | 779 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 1 | Gate computed and archived. | merged | TODO.md §12–§13 |
| `MAIN-L0782` | 782 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 2 | 5-seed K=3 headline runs complete. | merged | TODO.md §12–§13 |
| `MAIN-L0783` | 783 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 2 | SAEBench full suite complete at target L0 values. | merged | TODO.md §12–§13 |
| `MAIN-L0784` | 784 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 2 | Kantamneni benchmark complete. | merged | TODO.md §12–§13 |
| `MAIN-L0785` | 785 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 2 | K/`lambda_inc`/dense-branch ablations complete. | merged | TODO.md §12–§13 |
| `MAIN-L0786` | 786 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 2 | Gate computed and archived. | merged | TODO.md §12–§13 |
| `MAIN-L0789` | 789 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 3 | Structured branches implemented and validated on smoke tests. | merged | TODO.md §12–§13 |
| `MAIN-L0790` | 790 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 3 | Engels + Chanin validations complete. | merged | TODO.md §12–§13 |
| `MAIN-L0791` | 791 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 3 | Two case studies complete. | merged | TODO.md §12–§13 |
| `MAIN-L0792` | 792 | open | 11. Minimum Acceptance Checklist Per Paper > Paper 3 | Gate computed and archived. | merged | TODO.md §12–§13 |
| `PCC-L0055` | 55 | done | 0. Status Snapshot and Reframing (2026-06-16) > 0.1 Established by the current project | The raw-activation pre-K2 suite supports a stable position/content separation on `Pythia-160M`. | carried | TODO.md §1 Current Project State |
| `PCC-L0056` | 56 | done | 0. Status Snapshot and Reframing (2026-06-16) > 0.1 Established by the current project | In the final pre-K2 suite, `Pythia-160M` layers `3` and `4` pass the v2 separability gate at headline ranks `8` and `16` across IID, source-holdout, and corpus-holdout conditions. | carried | TODO.md §1 Current Project State |
| `PCC-L0057` | 57 | done | 0. Status Snapshot and Reframing (2026-06-16) > 0.1 Established by the current project | The final packaged result reports `92/92` headline passes and `0/46` passes at boundary rank `32`. | carried | TODO.md §1 Current Project State |
| `PCC-L0058` | 58 | done | 0. Status Snapshot and Reframing (2026-06-16) > 0.1 Established by the current project | `L3` is the primary K=2 target and `L4` is the fallback. | carried | TODO.md §1 Current Project State |
| `PCC-L0059` | 59 | done | 0. Status Snapshot and Reframing (2026-06-16) > 0.1 Established by the current project | The GPU-first K=2 trainer is operational, resumable, and stable enough to support long runs. | carried | TODO.md §1 Current Project State |
| `PCC-L0060` | 60 | done | 0. Status Snapshot and Reframing (2026-06-16) > 0.1 Established by the current project | The current wave-2 fastdata-stream run shows that `lambda_inc=1e-2` substantially reduces incoherence relative to the no-inc control. | carried | TODO.md §1 Current Project State |
| `PCC-L0061` | 61 | done | 0. Status Snapshot and Reframing (2026-06-16) > 0.1 Established by the current project | The strongest existing claim is about **branch separation** and geometry, not universal reconstruction improvement. | carried | TODO.md §1 Current Project State |
| `PCC-L0064` | 64 | done | 0. Status Snapshot and Reframing (2026-06-16) > 0.2 Completed PCC bridge stages | Stage A0 aggregate decision is complete: | carried | TODO.md §1 Current Project State |
| `PCC-L0068` | 68 | done | 0. Status Snapshot and Reframing (2026-06-16) > 0.2 Completed PCC bridge stages | Stage A1 expanded observational audit is complete: | carried | TODO.md §1 Current Project State |
| `PCC-L0072` | 72 | done | 0. Status Snapshot and Reframing (2026-06-16) > 0.2 Completed PCC bridge stages | Stage A1b diagnostic follow-up is complete: | carried | TODO.md §1 Current Project State |
| `PCC-L0076` | 76 | done | 0. Status Snapshot and Reframing (2026-06-16) > 0.2 Completed PCC bridge stages | The PCC state was frozen before confirmation: | carried | TODO.md §1 Current Project State |
| `PCC-L0078` | 78 | done | 0. Status Snapshot and Reframing (2026-06-16) > 0.2 Completed PCC bridge stages | Stage A1c confirmation is complete: | carried | TODO.md §1 Current Project State |
| `PCC-L0085` | 85 | done | 0. Status Snapshot and Reframing (2026-06-16) > 0.2 Completed PCC bridge stages | Stage B-light control audit is complete: | carried | TODO.md §1 Current Project State |
| `PCC-L0096` | 96 | done | 0. Status Snapshot and Reframing (2026-06-16) > 0.2 Completed PCC bridge stages | Still out of scope so far: | carried | TODO.md §1 Current Project State |
| `PCC-L0102` | 102 | open | 0. Status Snapshot and Reframing (2026-06-16) > 0.3 New interpretation pressure introduced by the updated idea | The current K=2 “position” branch is best interpreted as a branch anchored to **absolute-position-predictive signal**, not necessarily all positional structure. | merged | TODO.md §1 Current Project State |
| `PCC-L0103` | 103 | open | 0. Status Snapshot and Reframing (2026-06-16) > 0.3 New interpretation pressure introduced by the updated idea | Syntax may depend strongly on **relative position**, **distance**, **ordering**, **boundary structure**, and **structural depth**, not just absolute token index. | merged | TODO.md §1 Current Project State |
| `PCC-L0104` | 104 | open | 0. Status Snapshot and Reframing (2026-06-16) > 0.3 New interpretation pressure introduced by the updated idea | Therefore, current positive “joint” syntax gains may be explained in at least two ways: | merged | TODO.md §1 Current Project State |
| `PCC-L0107` | 107 | open | 0. Status Snapshot and Reframing (2026-06-16) > 0.3 New interpretation pressure introduced by the updated idea | The next bridge-program priority is now to separate those explanations cleanly. | merged | TODO.md §1 Current Project State |
| `PCC-L0110` | 110 | open | 0. Status Snapshot and Reframing (2026-06-16) > 0.4 What remains unresolved | Is the current syntax-like joint signal really **PCC**, or mostly **broad positional-family leakage**? | merged | TODO.md §1 Current Project State |
| `PCC-L0111` | 111 | open | 0. Status Snapshot and Reframing (2026-06-16) > 0.4 What remains unresolved | Can we isolate a branch that captures **absolute + relative + structural position** and leave behind a more clearly **de-positioned content** representation? | merged | TODO.md §1 Current Project State |
| `PCC-L0112` | 112 | open | 0. Status Snapshot and Reframing (2026-06-16) > 0.4 What remains unresolved | If such a branch exists, does the apparent crossover signal shrink materially? | merged | TODO.md §1 Current Project State |
| `PCC-L0113` | 113 | open | 0. Status Snapshot and Reframing (2026-06-16) > 0.4 What remains unresolved | If not, does a true shared/interaction component remain after positional-family stripping? | merged | TODO.md §1 Current Project State |
| `PCC-L0114` | 114 | open | 0. Status Snapshot and Reframing (2026-06-16) > 0.4 What remains unresolved | Does the right next architecture look more like: | merged | TODO.md §1 Current Project State |
| `PCC-L0140` | 140 | open | 1. Core Reframing > 1.3 Safer language for the new target | **de-positioned content** | merged | TODO.md §2 |
| `PCC-L0141` | 141 | open | 1. Core Reframing > 1.3 Safer language for the new target | **position-minimized content** | merged | TODO.md §2 |
| `PCC-L0142` | 142 | open | 1. Core Reframing > 1.3 Safer language for the new target | **content after broad positional scrubbing** | merged | TODO.md §2 |
| `PCC-L0150` | 150 | open | 1. Core Reframing > 1.4 Main decision tree for the new program | **Case A: broad positional-family branch succeeds** | merged | TODO.md §2 |
| `PCC-L0153` | 153 | open | 1. Core Reframing > 1.4 Main decision tree for the new program | **Case B: absolute and relative/structural position separate from each other** | merged | TODO.md §2 |
| `PCC-L0156` | 156 | open | 1. Core Reframing > 1.4 Main decision tree for the new program | **Case C: genuine PCC remains after broad positional stripping** | merged | TODO.md §2 |
| `PCC-L0165` | 165 | open | 2. Main Hypotheses > 2.1 Primary updated hypotheses | **H1 (broad positional-family hypothesis):** | merged | TODO.md §2 |
| `PCC-L0167` | 167 | open | 2. Main Hypotheses > 2.1 Primary updated hypotheses | **H2 (de-positioned-content hypothesis):** | merged | TODO.md §2 |
| `PCC-L0169` | 169 | open | 2. Main Hypotheses > 2.1 Primary updated hypotheses | **H3 (residual-PCC hypothesis):** | merged | TODO.md §2 |
| `PCC-L0171` | 171 | open | 2. Main Hypotheses > 2.1 Primary updated hypotheses | **H4 (split-complexity hypothesis):** | merged | TODO.md §2 |
| `PCC-L0176` | 176 | open | 2. Main Hypotheses > 2.1 Primary updated hypotheses | **H5 (regularization hypothesis):** | merged | TODO.md §2 |
| `PCC-L0180` | 180 | open | 2. Main Hypotheses > 2.2 Null / weakening outcomes | **N1:** syntax remains mostly content-private even after better positional modeling. | merged | TODO.md §2 |
| `PCC-L0181` | 181 | open | 2. Main Hypotheses > 2.2 Null / weakening outcomes | **N2:** broad positional-family probes fail to isolate a stable low-rank positional family. | merged | TODO.md §2 |
| `PCC-L0182` | 182 | open | 2. Main Hypotheses > 2.2 Null / weakening outcomes | **N3:** de-positioned content loses too much semantic utility to be a meaningful target. | merged | TODO.md §2 |
| `PCC-L0183` | 183 | open | 2. Main Hypotheses > 2.2 Null / weakening outcomes | **N4:** observed “joint” gains disappear under stronger controls and better labeling. | merged | TODO.md §2 |
| `PCC-L0187` | 187 | done | 2. Main Hypotheses > 2.3 Grounding in the current record | the pre-K2 suite shows a robust position/content separability regime | carried | TODO.md §2 |
| `PCC-L0188` | 188 | done | 2. Main Hypotheses > 2.3 Grounding in the current record | the current K=2 model clearly changes branch geometry | carried | TODO.md §2 |
| `PCC-L0189` | 189 | done | 2. Main Hypotheses > 2.3 Grounding in the current record | the completed PCC bridge stages already show that some syntax-like tasks behave differently from semantic tasks | carried | TODO.md §2 |
| `PCC-L0190` | 190 | done | 2. Main Hypotheses > 2.3 Grounding in the current record | the matched-seed `g7 > g4` sensitivity suggests some overlap-sensitive signal may be getting suppressed by stronger private/private regularization | carried | TODO.md §2 |
| `PCC-L0200` | 200 | open | 3. Operational Definitions > 3.1 Position-family | absolute position | merged | TODO.md §3 |
| `PCC-L0201` | 201 | open | 3. Operational Definitions > 3.1 Position-family | distance to BOS/EOS | merged | TODO.md §3 |
| `PCC-L0202` | 202 | open | 3. Operational Definitions > 3.1 Position-family | front/middle/back coarse location | merged | TODO.md §3 |
| `PCC-L0203` | 203 | open | 3. Operational Definitions > 3.1 Position-family | relative order within a local window | merged | TODO.md §3 |
| `PCC-L0204` | 204 | open | 3. Operational Definitions > 3.1 Position-family | signed distance to an anchor or governing token | merged | TODO.md §3 |
| `PCC-L0205` | 205 | open | 3. Operational Definitions > 3.1 Position-family | dependency head direction and distance | merged | TODO.md §3 |
| `PCC-L0206` | 206 | open | 3. Operational Definitions > 3.1 Position-family | clause/phrase boundary proximity | merged | TODO.md §3 |
| `PCC-L0207` | 207 | open | 3. Operational Definitions > 3.1 Position-family | depth-like structural location | merged | TODO.md §3 |
| `PCC-L0208` | 208 | open | 3. Operational Definitions > 3.1 Position-family | repetition distance / previous-occurrence distance | merged | TODO.md §3 |
| `PCC-L0211` | 211 | open | 3. Operational Definitions > 3.2 Absolute-position signal | index-like signal recoverable from one token’s activation: | merged | TODO.md §3 |
| `PCC-L0216` | 216 | open | 3. Operational Definitions > 3.3 Relative-position signal | relational or offset-like signal: | merged | TODO.md §3 |
| `PCC-L0224` | 224 | open | 3. Operational Definitions > 3.4 Structural-position signal | structure-like arrangement information that is still more positional than semantic: | merged | TODO.md §3 |
| `PCC-L0231` | 231 | open | 3. Operational Definitions > 3.5 De-positioned content | a representation that: | merged | TODO.md §3 |
| `PCC-L0239` | 239 | open | 3. Operational Definitions > 3.6 Residual crossover / PCC | **PCC-0:** joint-only predictive gain | merged | TODO.md §3 |
| `PCC-L0240` | 240 | open | 3. Operational Definitions > 3.6 Residual crossover / PCC | **PCC-1:** residual after removing both private content and broad positional-family signal | merged | TODO.md §3 |
| `PCC-L0241` | 241 | open | 3. Operational Definitions > 3.6 Residual crossover / PCC | **PCC-2:** supervised low-rank interaction readout | merged | TODO.md §3 |
| `PCC-L0242` | 242 | open | 3. Operational Definitions > 3.6 Residual crossover / PCC | **PCC-3:** learned shared branch | merged | TODO.md §3 |
| `PCC-L0246` | 246 | open | 3. Operational Definitions > 3.7 Token-local versus relation-aware settings | **token-local** | merged | TODO.md §3 |
| `PCC-L0248` | 248 | open | 3. Operational Definitions > 3.7 Token-local versus relation-aware settings | **relation-aware** | merged | TODO.md §3 |
| `PCC-L0260` | 260 | done | 4. Working Representation Families > 4.1 Existing representations already available | raw activation `x` | carried | TODO.md §6 |
| `PCC-L0261` | 261 | done | 4. Working Representation Families > 4.1 Existing representations already available | K=2 position reconstruction `x_pos_priv` | carried | TODO.md §6 |
| `PCC-L0262` | 262 | done | 4. Working Representation Families > 4.1 Existing representations already available | K=2 content reconstruction `x_content_priv` | carried | TODO.md §6 |
| `PCC-L0263` | 263 | done | 4. Working Representation Families > 4.1 Existing representations already available | joint concatenation `[x_pos_priv, x_content_priv]` | carried | TODO.md §6 |
| `PCC-L0264` | 264 | done | 4. Working Representation Families > 4.1 Existing representations already available | residual proxy `x_resid` | carried | TODO.md §6 |
| `PCC-L0267` | 267 | open | 4. Working Representation Families > 4.2 New analysis-side candidate representations | `S_abs` | merged | TODO.md §6 |
| `PCC-L0269` | 269 | open | 4. Working Representation Families > 4.2 New analysis-side candidate representations | `S_rel` | merged | TODO.md §6 |
| `PCC-L0271` | 271 | open | 4. Working Representation Families > 4.2 New analysis-side candidate representations | `S_struct` | merged | TODO.md §6 |
| `PCC-L0273` | 273 | open | 4. Working Representation Families > 4.2 New analysis-side candidate representations | `S_posfam` | merged | TODO.md §6 |
| `PCC-L0275` | 275 | open | 4. Working Representation Families > 4.2 New analysis-side candidate representations | `x_depos_proj` | merged | TODO.md §6 |
| `PCC-L0278` | 278 | open | 4. Working Representation Families > 4.2 New analysis-side candidate representations | `x_depos_regress` | merged | TODO.md §6 |
| `PCC-L0280` | 280 | open | 4. Working Representation Families > 4.2 New analysis-side candidate representations | `x_depos_adv` | merged | TODO.md §6 |
| `PCC-L0282` | 282 | open | 4. Working Representation Families > 4.2 New analysis-side candidate representations | `x_pcc_resid` | merged | TODO.md §6 |
| `PCC-L0286` | 286 | open | 4. Working Representation Families > 4.3 Candidate model-side branch families | `x_abs_priv` | merged | TODO.md §6 |
| `PCC-L0287` | 287 | open | 4. Working Representation Families > 4.3 Candidate model-side branch families | `x_rel_priv` | merged | TODO.md §6 |
| `PCC-L0288` | 288 | open | 4. Working Representation Families > 4.3 Candidate model-side branch families | `x_struct_priv` | merged | TODO.md §6 |
| `PCC-L0289` | 289 | open | 4. Working Representation Families > 4.3 Candidate model-side branch families | `x_posfam_priv` | merged | TODO.md §6 |
| `PCC-L0290` | 290 | open | 4. Working Representation Families > 4.3 Candidate model-side branch families | `x_content_depos` | merged | TODO.md §6 |
| `PCC-L0291` | 291 | open | 4. Working Representation Families > 4.3 Candidate model-side branch families | `x_shared` / `x_pcc` | merged | TODO.md §6 |
| `PCC-L0298` | 298 | open | 5. Task Battery and Label Families > 5.1 Absolute-position tasks | exact token position bucket over `0..1023` | merged | TODO.md §4 |
| `PCC-L0299` | 299 | open | 5. Task Battery and Label Families > 5.1 Absolute-position tasks | coarse position bucket: | merged | TODO.md §4 |
| `PCC-L0304` | 304 | open | 5. Task Battery and Label Families > 5.1 Absolute-position tasks | distance to BOS | merged | TODO.md §4 |
| `PCC-L0305` | 305 | open | 5. Task Battery and Label Families > 5.1 Absolute-position tasks | distance to EOS / sequence tail | merged | TODO.md §4 |
| `PCC-L0306` | 306 | open | 5. Task Battery and Label Families > 5.1 Absolute-position tasks | relative fraction through context window | merged | TODO.md §4 |
| `PCC-L0309` | 309 | open | 5. Task Battery and Label Families > 5.2 Relative-position tasks | signed distance to dependency head | merged | TODO.md §4 |
| `PCC-L0310` | 310 | open | 5. Task Battery and Label Families > 5.2 Relative-position tasks | head direction: | merged | TODO.md §4 |
| `PCC-L0314` | 314 | open | 5. Task Battery and Label Families > 5.2 Relative-position tasks | head-distance bucket | merged | TODO.md §4 |
| `PCC-L0315` | 315 | open | 5. Task Battery and Label Families > 5.2 Relative-position tasks | signed distance to previous occurrence of same token or lemma | merged | TODO.md §4 |
| `PCC-L0316` | 316 | open | 5. Task Battery and Label Families > 5.2 Relative-position tasks | local order within a small context window | merged | TODO.md §4 |
| `PCC-L0317` | 317 | open | 5. Task Battery and Label Families > 5.2 Relative-position tasks | repeated-token offset bucket | merged | TODO.md §4 |
| `PCC-L0318` | 318 | open | 5. Task Battery and Label Families > 5.2 Relative-position tasks | distance to nearest punctuation/boundary token | merged | TODO.md §4 |
| `PCC-L0321` | 321 | open | 5. Task Battery and Label Families > 5.3 Structural-position tasks | BIO or boundary tagging | merged | TODO.md §4 |
| `PCC-L0322` | 322 | open | 5. Task Battery and Label Families > 5.3 Structural-position tasks | clause boundary detection | merged | TODO.md §4 |
| `PCC-L0323` | 323 | open | 5. Task Battery and Label Families > 5.3 Structural-position tasks | phrase boundary detection | merged | TODO.md §4 |
| `PCC-L0324` | 324 | open | 5. Task Battery and Label Families > 5.3 Structural-position tasks | parse depth or approximate bracket depth | merged | TODO.md §4 |
| `PCC-L0325` | 325 | open | 5. Task Battery and Label Families > 5.3 Structural-position tasks | dependency depth from root | merged | TODO.md §4 |
| `PCC-L0326` | 326 | open | 5. Task Battery and Label Families > 5.3 Structural-position tasks | inside/outside span markers | merged | TODO.md §4 |
| `PCC-L0327` | 327 | open | 5. Task Battery and Label Families > 5.3 Structural-position tasks | token role in local span: | merged | TODO.md §4 |
| `PCC-L0334` | 334 | open | 5. Task Battery and Label Families > 5.4 Content tasks | token identity top-k bucket | merged | TODO.md §4 |
| `PCC-L0335` | 335 | open | 5. Task Battery and Label Families > 5.4 Content tasks | lemma or lexical cluster where feasible | merged | TODO.md §4 |
| `PCC-L0336` | 336 | open | 5. Task Battery and Label Families > 5.4 Content tasks | NER type: | merged | TODO.md §4 |
| `PCC-L0340` | 340 | open | 5. Task Battery and Label Families > 5.4 Content tasks | supersense or coarse semantic class where feasible | merged | TODO.md §4 |
| `PCC-L0341` | 341 | open | 5. Task Battery and Label Families > 5.4 Content tasks | semantic role labels if a clean token-level version is available | merged | TODO.md §4 |
| `PCC-L0342` | 342 | open | 5. Task Battery and Label Families > 5.4 Content tasks | event/entity type labels | merged | TODO.md §4 |
| `PCC-L0347` | 347 | open | 5. Task Battery and Label Families > 5.5 Mixed or ambiguous tasks | POS tagging | merged | TODO.md §4 |
| `PCC-L0348` | 348 | open | 5. Task Battery and Label Families > 5.5 Mixed or ambiguous tasks | dependency relation labels | merged | TODO.md §4 |
| `PCC-L0349` | 349 | open | 5. Task Battery and Label Families > 5.5 Mixed or ambiguous tasks | agreement features: | merged | TODO.md §4 |
| `PCC-L0353` | 353 | open | 5. Task Battery and Label Families > 5.5 Mixed or ambiguous tasks | argument-role syntax labels where available | merged | TODO.md §4 |
| `PCC-L0354` | 354 | open | 5. Task Battery and Label Families > 5.5 Mixed or ambiguous tasks | attachment-sensitive labels | merged | TODO.md §4 |
| `PCC-L0355` | 355 | open | 5. Task Battery and Label Families > 5.5 Mixed or ambiguous tasks | scope-sensitive constructions | merged | TODO.md §4 |
| `PCC-L0358` | 358 | done | 5. Task Battery and Label Families > 5.6 Current PCC tasks to remap under the new framing | `syntax_pos` | carried | TODO.md §4 |
| `PCC-L0359` | 359 | done | 5. Task Battery and Label Families > 5.6 Current PCC tasks to remap under the new framing | `syntax_dep_coarse` | carried | TODO.md §4 |
| `PCC-L0360` | 360 | done | 5. Task Battery and Label Families > 5.6 Current PCC tasks to remap under the new framing | `head_dir_dist` | carried | TODO.md §4 |
| `PCC-L0361` | 361 | done | 5. Task Battery and Label Families > 5.6 Current PCC tasks to remap under the new framing | `sem_wnut17_typeonly` | carried | TODO.md §4 |
| `PCC-L0362` | 362 | done | 5. Task Battery and Label Families > 5.6 Current PCC tasks to remap under the new framing | `sem_fewnerd_coarse_binary` | carried | TODO.md §4 |
| `PCC-L0363` | 363 | done | 5. Task Battery and Label Families > 5.6 Current PCC tasks to remap under the new framing | `sem_wikineural_en_binary` | carried | TODO.md §4 |
| `PCC-L0366` | 366 | open | 5. Task Battery and Label Families > 5.6 Current PCC tasks to remap under the new framing | primarily absolute-position-like | merged | TODO.md §4 |
| `PCC-L0367` | 367 | open | 5. Task Battery and Label Families > 5.6 Current PCC tasks to remap under the new framing | primarily relative/structural-position-like | merged | TODO.md §4 |
| `PCC-L0368` | 368 | open | 5. Task Battery and Label Families > 5.6 Current PCC tasks to remap under the new framing | primarily content-like | merged | TODO.md §4 |
| `PCC-L0369` | 369 | open | 5. Task Battery and Label Families > 5.6 Current PCC tasks to remap under the new framing | mixed/ambiguous | merged | TODO.md §4 |
| `PCC-L0376` | 376 | open | 6. Data Plan > 6.1 Primary model/layer sites | Primary site: `Pythia-160M`, `L3` | merged | TODO.md §5 |
| `PCC-L0377` | 377 | open | 6. Data Plan > 6.1 Primary model/layer sites | Secondary site: `Pythia-160M`, `L4` | merged | TODO.md §5 |
| `PCC-L0378` | 378 | open | 6. Data Plan > 6.1 Primary model/layer sites | Optional layer add-ons after initial read: | merged | TODO.md §5 |
| `PCC-L0384` | 384 | done | 6. Data Plan > 6.2 Reuse of current project assets | Reuse the existing pre-K2 activation/probe infrastructure wherever possible. | carried | TODO.md §5 |
| `PCC-L0385` | 385 | done | 6. Data Plan > 6.2 Reuse of current project assets | Reuse the current `L3` checkpoints: | carried | TODO.md §5 |
| `PCC-L0390` | 390 | done | 6. Data Plan > 6.2 Reuse of current project assets | Reuse current `x_pos_priv`, `x_content_priv`, and residual outputs. | carried | TODO.md §5 |
| `PCC-L0391` | 391 | open | 6. Data Plan > 6.2 Reuse of current project assets | Build new derived label tables and contrast metadata on top of existing activation dumps before launching any new model training. | merged | TODO.md §5 |
| `PCC-L0395` | 395 | open | 6. Data Plan > 6.3 Annotation sources > Gold / high-quality labeled corpora | Universal Dependencies for POS, head direction, head distance, dependency labels, depth-like approximations | merged | TODO.md §5 |
| `PCC-L0396` | 396 | open | 6. Data Plan > 6.3 Annotation sources > Gold / high-quality labeled corpora | OntoNotes or equivalent for syntax + NER + SRL if available in current environment | merged | TODO.md §5 |
| `PCC-L0397` | 397 | open | 6. Data Plan > 6.3 Annotation sources > Gold / high-quality labeled corpora | WNUT17 | merged | TODO.md §5 |
| `PCC-L0398` | 398 | open | 6. Data Plan > 6.3 Annotation sources > Gold / high-quality labeled corpora | FewNERD | merged | TODO.md §5 |
| `PCC-L0399` | 399 | open | 6. Data Plan > 6.3 Annotation sources > Gold / high-quality labeled corpora | WikiNeural | merged | TODO.md §5 |
| `PCC-L0400` | 400 | open | 6. Data Plan > 6.3 Annotation sources > Gold / high-quality labeled corpora | BLiMP / SyntaxGym / controlled contrast data | merged | TODO.md §5 |
| `PCC-L0403` | 403 | open | 6. Data Plan > 6.3 Annotation sources > Silver-scale labels | Stanza or spaCy parses/tags for larger held-out corpora | merged | TODO.md §5 |
| `PCC-L0404` | 404 | open | 6. Data Plan > 6.3 Annotation sources > Silver-scale labels | automatic NER / semantic tags where gold is too small | merged | TODO.md §5 |
| `PCC-L0405` | 405 | open | 6. Data Plan > 6.3 Annotation sources > Silver-scale labels | keep a gold subset for calibration | merged | TODO.md §5 |
| `PCC-L0408` | 408 | open | 6. Data Plan > 6.4 Split design | IID split | merged | TODO.md §5 |
| `PCC-L0409` | 409 | open | 6. Data Plan > 6.4 Split design | source-holdout split | merged | TODO.md §5 |
| `PCC-L0410` | 410 | open | 6. Data Plan > 6.4 Split design | corpus-holdout split | merged | TODO.md §5 |
| `PCC-L0411` | 411 | open | 6. Data Plan > 6.4 Split design | matched-token split | merged | TODO.md §5 |
| `PCC-L0412` | 412 | open | 6. Data Plan > 6.4 Split design | matched-position split | merged | TODO.md §5 |
| `PCC-L0413` | 413 | open | 6. Data Plan > 6.4 Split design | matched-length split | merged | TODO.md §5 |
| `PCC-L0414` | 414 | open | 6. Data Plan > 6.4 Split design | matched-template split for contrast sets | merged | TODO.md §5 |
| `PCC-L0421` | 421 | open | 7. Track R — Reinterpret the Existing PCC Evidence > Goal | Re-read the completed A0/A1/A1b/A1c/B-light outputs through the new positional-family lens before launching new experiments. | merged | TODO.md M1 |
| `PCC-L0424` | 424 | open | 7. Track R — Reinterpret the Existing PCC Evidence > Key questions | Which current “syntax” tasks are actually strongest candidates for **relative/structural positional** readouts? | merged | TODO.md M1 |
| `PCC-L0425` | 425 | open | 7. Track R — Reinterpret the Existing PCC Evidence > Key questions | Does `syntax_pos` look more like true crossover or like undercaptured broad position? | merged | TODO.md M1 |
| `PCC-L0426` | 426 | open | 7. Track R — Reinterpret the Existing PCC Evidence > Key questions | Does the sharp weakening of `syntax_dep_coarse` under matched-token control suggest lexical shortcut dependence, or does it suggest that current representations are missing the right relative-position abstraction? | merged | TODO.md M1 |
| `PCC-L0427` | 427 | open | 7. Track R — Reinterpret the Existing PCC Evidence > Key questions | Does `g7 > g4` imply that stronger private/private regularization suppresses useful shared structure, or that it suppresses broad positional leakage the current K=2 split has not allocated correctly? | merged | TODO.md M1 |
| `PCC-L0430` | 430 | open | 7. Track R — Reinterpret the Existing PCC Evidence > Concrete outputs | Write `analysis/pcc_reinterpretation_20260616.md` | merged | TODO.md M1 |
| `PCC-L0431` | 431 | open | 7. Track R — Reinterpret the Existing PCC Evidence > Concrete outputs | Build a task mapping table: | merged | TODO.md M1 |
| `PCC-L0438` | 438 | open | 7. Track R — Reinterpret the Existing PCC Evidence > Concrete outputs | Record a short decision memo: | merged | TODO.md M1 |
| `PCC-L0444` | 444 | open | 7. Track R — Reinterpret the Existing PCC Evidence > Why this stage matters | It prevents the project from running a large new experiment while still interpreting all joint gain as “shared syntax” by default. | merged | TODO.md M1 |
| `PCC-L0453` | 453 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P0 — Label inventory and positional-family probe design > Goal | Define the target families for the broadened positional program before any new gate or architecture claim. | merged | TODO.md M2–M4 |
| `PCC-L0456` | 456 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P0 — Label inventory and positional-family probe design > Deliverables | `prereg/pcc_positional_family_revision_v2.md` | merged | TODO.md M2–M4 |
| `PCC-L0457` | 457 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P0 — Label inventory and positional-family probe design > Deliverables | `analysis/position_family_labels/` | merged | TODO.md M2–M4 |
| `PCC-L0458` | 458 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P0 — Label inventory and positional-family probe design > Deliverables | `configs/pcc/position_family_probe_suite.yaml` | merged | TODO.md M2–M4 |
| `PCC-L0461` | 461 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P0 — Label inventory and positional-family probe design > Concrete tasks | finalize absolute-position label set | merged | TODO.md M2–M4 |
| `PCC-L0462` | 462 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P0 — Label inventory and positional-family probe design > Concrete tasks | finalize relative-position label set | merged | TODO.md M2–M4 |
| `PCC-L0463` | 463 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P0 — Label inventory and positional-family probe design > Concrete tasks | finalize structural-position label set | merged | TODO.md M2–M4 |
| `PCC-L0464` | 464 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P0 — Label inventory and positional-family probe design > Concrete tasks | finalize content label set | merged | TODO.md M2–M4 |
| `PCC-L0465` | 465 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P0 — Label inventory and positional-family probe design > Concrete tasks | tag each current PCC task into one or more of those families | merged | TODO.md M2–M4 |
| `PCC-L0466` | 466 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P0 — Label inventory and positional-family probe design > Concrete tasks | declare which labels are token-local only and which require relation-aware features | merged | TODO.md M2–M4 |
| `PCC-L0469` | 469 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P0 — Label inventory and positional-family probe design > Minimum acceptance criteria | every label family has: | merged | TODO.md M2–M4 |
| `PCC-L0480` | 480 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Goal | Test whether raw activations admit a broader **position-family vs content** separation than the current absolute-position-only gate. | merged | TODO.md M2–M4 |
| `PCC-L0483` | 483 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Question | Can a low-rank or modest-rank positional-family subspace explain: | merged | TODO.md M2–M4 |
| `PCC-L0490` | 490 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Inputs | raw activations `x` | merged | TODO.md M2–M4 |
| `PCC-L0491` | 491 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Inputs | absolute-position probes | merged | TODO.md M2–M4 |
| `PCC-L0492` | 492 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Inputs | relative-position probes | merged | TODO.md M2–M4 |
| `PCC-L0493` | 493 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Inputs | structural-position probes | merged | TODO.md M2–M4 |
| `PCC-L0494` | 494 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Inputs | content probes | merged | TODO.md M2–M4 |
| `PCC-L0497` | 497 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Candidate subspace construction methods | stack probe weight vectors and run PCA/SVD | merged | TODO.md M2–M4 |
| `PCC-L0498` | 498 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Candidate subspace construction methods | CCA/PLS across positional tasks | merged | TODO.md M2–M4 |
| `PCC-L0499` | 499 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Candidate subspace construction methods | supervised multi-task linear encoder for positional-family labels | merged | TODO.md M2–M4 |
| `PCC-L0500` | 500 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Candidate subspace construction methods | compare separate `S_abs`, `S_rel`, `S_struct`, and combined `S_posfam` | merged | TODO.md M2–M4 |
| `PCC-L0503` | 503 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Core comparisons | `Proj_{S_abs}(x)` | merged | TODO.md M2–M4 |
| `PCC-L0504` | 504 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Core comparisons | `Proj_{S_rel}(x)` | merged | TODO.md M2–M4 |
| `PCC-L0505` | 505 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Core comparisons | `Proj_{S_struct}(x)` | merged | TODO.md M2–M4 |
| `PCC-L0506` | 506 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Core comparisons | `Proj_{S_posfam}(x)` | merged | TODO.md M2–M4 |
| `PCC-L0507` | 507 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Core comparisons | orthogonal complements of each | merged | TODO.md M2–M4 |
| `PCC-L0510` | 510 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Primary outputs | positional-family recovery curves | merged | TODO.md M2–M4 |
| `PCC-L0511` | 511 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Primary outputs | content retention in positional complements | merged | TODO.md M2–M4 |
| `PCC-L0512` | 512 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Primary outputs | principal angles between `S_posfam` and content subspaces | merged | TODO.md M2–M4 |
| `PCC-L0513` | 513 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Primary outputs | cross-projection energy | merged | TODO.md M2–M4 |
| `PCC-L0514` | 514 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Primary outputs | rank window where position-family is strongest and content leakage is lowest | merged | TODO.md M2–M4 |
| `PCC-L0517` | 517 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Success signals | broad position-family tasks are much better recovered from `S_posfam` than from the complement | merged | TODO.md M2–M4 |
| `PCC-L0518` | 518 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Success signals | content tasks are much better recovered from the complement than from `S_posfam` | merged | TODO.md M2–M4 |
| `PCC-L0519` | 519 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Success signals | syntax-like tasks move materially toward the positional-family side relative to the old absolute-position-only split | merged | TODO.md M2–M4 |
| `PCC-L0522` | 522 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Failure signals | `S_posfam` cannot be made meaningfully cleaner than the raw representation | merged | TODO.md M2–M4 |
| `PCC-L0523` | 523 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Failure signals | content collapses when broad positional-family is removed | merged | TODO.md M2–M4 |
| `PCC-L0524` | 524 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Failure signals | relative/structural position does not behave as a coherent family | merged | TODO.md M2–M4 |
| `PCC-L0527` | 527 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P1 — Raw-activation positional-family gate > Decision use | If P1 is strongly positive, prioritize revised `K=2` all-position vs content before full PCC branch training. | merged | TODO.md M2–M4 |
| `PCC-L0534` | 534 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Goal | Quantify how much absolute, relative, and structural positional information is still present in `x_content_priv` and `x_resid`. | merged | TODO.md M2–M4 |
| `PCC-L0537` | 537 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Inputs | `x` | merged | TODO.md M2–M4 |
| `PCC-L0538` | 538 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Inputs | `x_pos_priv` | merged | TODO.md M2–M4 |
| `PCC-L0539` | 539 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Inputs | `x_content_priv` | merged | TODO.md M2–M4 |
| `PCC-L0540` | 540 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Inputs | `[x_pos_priv, x_content_priv]` | merged | TODO.md M2–M4 |
| `PCC-L0541` | 541 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Inputs | `x_resid` | merged | TODO.md M2–M4 |
| `PCC-L0542` | 542 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Inputs | positional-family labels from P0 | merged | TODO.md M2–M4 |
| `PCC-L0543` | 543 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Inputs | content labels from P0 | merged | TODO.md M2–M4 |
| `PCC-L0546` | 546 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Core questions | How much absolute-position information is left in `x_content_priv`? | merged | TODO.md M2–M4 |
| `PCC-L0547` | 547 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Core questions | How much relative-position information is left in `x_content_priv`? | merged | TODO.md M2–M4 |
| `PCC-L0548` | 548 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Core questions | How much structural-position information is left in `x_content_priv`? | merged | TODO.md M2–M4 |
| `PCC-L0549` | 549 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Core questions | How much semantic/content information is left in `x_pos_priv`? | merged | TODO.md M2–M4 |
| `PCC-L0550` | 550 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Core questions | Does `x_resid` look more like missed position-family signal or like genuine interaction signal? | merged | TODO.md M2–M4 |
| `PCC-L0553` | 553 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Metrics | position leakage from `x_content_priv` | merged | TODO.md M2–M4 |
| `PCC-L0554` | 554 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Metrics | content leakage from `x_pos_priv` | merged | TODO.md M2–M4 |
| `PCC-L0555` | 555 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Metrics | residual selectivity index | merged | TODO.md M2–M4 |
| `PCC-L0556` | 556 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Metrics | broad-position joint gain vs old absolute-position joint gain | merged | TODO.md M2–M4 |
| `PCC-L0559` | 559 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Interpretation rules | If `x_content_priv` retains strong relative/structural positional signal, then the current K=2 split is likely too narrow on the position side. | merged | TODO.md M2–M4 |
| `PCC-L0560` | 560 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P2 — Leakage audit on existing K=2 checkpoints > Interpretation rules | If `x_content_priv` is already low-leakage on broad position but syntax joint gains remain, then genuine PCC becomes more plausible. | merged | TODO.md M2–M4 |
| `PCC-L0567` | 567 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Goal | Test whether the candidate content representation is stable under transformations that mainly move position, and whether the candidate positional-family representation moves in the expected direction. | merged | TODO.md M2–M4 |
| `PCC-L0571` | 571 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Concrete transformation families > Mostly position-changing, semantics-preserving | prepend neutral prefix tokens to shift absolute positions | merged | TODO.md M2–M4 |
| `PCC-L0572` | 572 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Concrete transformation families > Mostly position-changing, semantics-preserving | insert punctuation or formatting tokens that preserve broad proposition | merged | TODO.md M2–M4 |
| `PCC-L0573` | 573 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Concrete transformation families > Mostly position-changing, semantics-preserving | add or remove neutral appositive or filler phrases | merged | TODO.md M2–M4 |
| `PCC-L0574` | 574 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Concrete transformation families > Mostly position-changing, semantics-preserving | reorder clauses when broad meaning is preserved | merged | TODO.md M2–M4 |
| `PCC-L0575` | 575 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Concrete transformation families > Mostly position-changing, semantics-preserving | active/passive alternations where semantics is approximately preserved | merged | TODO.md M2–M4 |
| `PCC-L0576` | 576 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Concrete transformation families > Mostly position-changing, semantics-preserving | dative alternations | merged | TODO.md M2–M4 |
| `PCC-L0579` | 579 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Concrete transformation families > Mostly semantics-changing, structure-preserving | entity substitutions under fixed template | merged | TODO.md M2–M4 |
| `PCC-L0580` | 580 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Concrete transformation families > Mostly semantics-changing, structure-preserving | lexical substitutions matched on POS and inflection | merged | TODO.md M2–M4 |
| `PCC-L0581` | 581 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Concrete transformation families > Mostly semantics-changing, structure-preserving | event/entity type substitutions with same surface skeleton | merged | TODO.md M2–M4 |
| `PCC-L0582` | 582 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Concrete transformation families > Mostly semantics-changing, structure-preserving | role reversals in matched templates | merged | TODO.md M2–M4 |
| `PCC-L0585` | 585 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Measurements | branch activation shift magnitude | merged | TODO.md M2–M4 |
| `PCC-L0586` | 586 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Measurements | cosine stability within each representation family | merged | TODO.md M2–M4 |
| `PCC-L0587` | 587 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Measurements | positional-family probe shifts | merged | TODO.md M2–M4 |
| `PCC-L0588` | 588 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Measurements | content-task probe shifts | merged | TODO.md M2–M4 |
| `PCC-L0589` | 589 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Measurements | selectivity of change: | merged | TODO.md M2–M4 |
| `PCC-L0594` | 594 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Success pattern for de-positioned content | low change under mostly positional shifts | merged | TODO.md M2–M4 |
| `PCC-L0595` | 595 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Success pattern for de-positioned content | higher change under content substitutions | merged | TODO.md M2–M4 |
| `PCC-L0596` | 596 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Success pattern for de-positioned content | low recoverable position-family signal after transformation | merged | TODO.md M2–M4 |
| `PCC-L0599` | 599 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Success pattern for a true positional-family branch | high sensitivity to positional shifts | merged | TODO.md M2–M4 |
| `PCC-L0600` | 600 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P3 — Shift-based counterfactual invariance suite > Success pattern for a true positional-family branch | lower sensitivity to lexical substitutions when structure is held fixed | merged | TODO.md M2–M4 |
| `PCC-L0607` | 607 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P4 — Linear residualization and adversarial scrubbing baselines > Goal | Test whether simple non-generative baselines can already create a useful de-positioned content representation. | merged | TODO.md M2–M4 |
| `PCC-L0610` | 610 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P4 — Linear residualization and adversarial scrubbing baselines > Baseline families | projection residual: | merged | TODO.md M2–M4 |
| `PCC-L0612` | 612 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P4 — Linear residualization and adversarial scrubbing baselines > Baseline families | linear regression residual: | merged | TODO.md M2–M4 |
| `PCC-L0614` | 614 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P4 — Linear residualization and adversarial scrubbing baselines > Baseline families | branch residualization: | merged | TODO.md M2–M4 |
| `PCC-L0616` | 616 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P4 — Linear residualization and adversarial scrubbing baselines > Baseline families | adversarial linear scrubber: | merged | TODO.md M2–M4 |
| `PCC-L0620` | 620 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P4 — Linear residualization and adversarial scrubbing baselines > Why this matters | If a simple baseline already removes most positional-family leakage while keeping semantic utility, then the project should not rush into a new PCC architecture. | merged | TODO.md M2–M4 |
| `PCC-L0621` | 621 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P4 — Linear residualization and adversarial scrubbing baselines > Why this matters | If simple baselines fail, that strengthens the case for a learned multi-branch model. | merged | TODO.md M2–M4 |
| `PCC-L0624` | 624 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P4 — Linear residualization and adversarial scrubbing baselines > Concrete comparisons | compare `x_content_priv` to `x_depos_proj` | merged | TODO.md M2–M4 |
| `PCC-L0625` | 625 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P4 — Linear residualization and adversarial scrubbing baselines > Concrete comparisons | compare `x_content_priv` to `x_depos_regress` | merged | TODO.md M2–M4 |
| `PCC-L0626` | 626 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P4 — Linear residualization and adversarial scrubbing baselines > Concrete comparisons | compare `x_content_priv` to `x_depos_adv` | merged | TODO.md M2–M4 |
| `PCC-L0627` | 627 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P4 — Linear residualization and adversarial scrubbing baselines > Concrete comparisons | compare all of them on: | merged | TODO.md M2–M4 |
| `PCC-L0637` | 637 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P5 — Residual crossover audit after broad positional stripping > Goal | Decide whether a real PCC signal remains after positional-family removal. | merged | TODO.md M2–M4 |
| `PCC-L0640` | 640 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P5 — Residual crossover audit after broad positional stripping > Representations to evaluate | `x_depos_*` | merged | TODO.md M2–M4 |
| `PCC-L0641` | 641 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P5 — Residual crossover audit after broad positional stripping > Representations to evaluate | joint of `x_posfam` and `x_depos_*` | merged | TODO.md M2–M4 |
| `PCC-L0642` | 642 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P5 — Residual crossover audit after broad positional stripping > Representations to evaluate | low-rank bilinear interaction readouts over those representations | merged | TODO.md M2–M4 |
| `PCC-L0643` | 643 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P5 — Residual crossover audit after broad positional stripping > Representations to evaluate | residual proxy after subtracting both broad position and content models | merged | TODO.md M2–M4 |
| `PCC-L0646` | 646 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P5 — Residual crossover audit after broad positional stripping > Decision rule | If syntax/relational tasks still show stable positive joint-only or bilinear-only gain after broad positional stripping, call that surviving signal a real PCC candidate. | merged | TODO.md M2–M4 |
| `PCC-L0647` | 647 | open | 8. Track P — Position-Family Observational Program (No New MSAE Training) > Stage P5 — Residual crossover audit after broad positional stripping > Decision rule | If the gains largely vanish, treat the original PCC story as mostly under-modeled positional structure. | merged | TODO.md M2–M4 |
| `PCC-L0654` | 654 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Goal | Use cleaner controlled transformations to distinguish: | merged | TODO.md M4 and M8 |
| `PCC-L0661` | 661 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Contrast families > Structure-changing, broad-content-preserving | active/passive | merged | TODO.md M4 and M8 |
| `PCC-L0662` | 662 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Contrast families > Structure-changing, broad-content-preserving | dative alternation | merged | TODO.md M4 and M8 |
| `PCC-L0663` | 663 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Contrast families > Structure-changing, broad-content-preserving | clefting | merged | TODO.md M4 and M8 |
| `PCC-L0664` | 664 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Contrast families > Structure-changing, broad-content-preserving | topicalization | merged | TODO.md M4 and M8 |
| `PCC-L0665` | 665 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Contrast families > Structure-changing, broad-content-preserving | relative clause movement | merged | TODO.md M4 and M8 |
| `PCC-L0666` | 666 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Contrast families > Structure-changing, broad-content-preserving | constituent reordering | merged | TODO.md M4 and M8 |
| `PCC-L0669` | 669 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Contrast families > Position-changing, structure-minimizing | neutral prefix insertion | merged | TODO.md M4 and M8 |
| `PCC-L0670` | 670 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Contrast families > Position-changing, structure-minimizing | neutral suffix insertion | merged | TODO.md M4 and M8 |
| `PCC-L0671` | 671 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Contrast families > Position-changing, structure-minimizing | paragraph-format padding | merged | TODO.md M4 and M8 |
| `PCC-L0672` | 672 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Contrast families > Position-changing, structure-minimizing | sentence index shift within a concatenated context | merged | TODO.md M4 and M8 |
| `PCC-L0675` | 675 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Contrast families > Content-changing, structure-preserving | entity substitutions | merged | TODO.md M4 and M8 |
| `PCC-L0676` | 676 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Contrast families > Content-changing, structure-preserving | event substitutions | merged | TODO.md M4 and M8 |
| `PCC-L0677` | 677 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Contrast families > Content-changing, structure-preserving | role reversals in fixed frame | merged | TODO.md M4 and M8 |
| `PCC-L0678` | 678 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Contrast families > Content-changing, structure-preserving | lexical substitutions matched on POS and morphology | merged | TODO.md M4 and M8 |
| `PCC-L0681` | 681 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Measurements | branch activation shift magnitude | merged | TODO.md M4 and M8 |
| `PCC-L0682` | 682 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Measurements | probe-score deltas by branch | merged | TODO.md M4 and M8 |
| `PCC-L0683` | 683 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Measurements | joint gain deltas | merged | TODO.md M4 and M8 |
| `PCC-L0684` | 684 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Measurements | causal branch-ablation effects on contrast discrimination | merged | TODO.md M4 and M8 |
| `PCC-L0687` | 687 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Key interpretation goals | determine whether current “syntax gain” is more sensitive to **broad positional-family changes** than to genuine meaning changes | merged | TODO.md M4 and M8 |
| `PCC-L0688` | 688 | open | 9. Track C — Controlled Contrast and Counterfactual Audit > Key interpretation goals | determine whether semantic families remain primarily content-private under the same controls | merged | TODO.md M4 and M8 |
| `PCC-L0700` | 700 | open | 10. Track D — Model-Side Candidate Experiments > D1 — Revised K=2: all-position vs de-positioned content > When to choose | choose this if broad positional-family stripping explains most of the earlier syntax-like joint gain | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0701` | 701 | open | 10. Track D — Model-Side Candidate Experiments > D1 — Revised K=2: all-position vs de-positioned content > When to choose | choose this if de-positioned content remains semantically useful | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0704` | 704 | open | 10. Track D — Model-Side Candidate Experiments > D1 — Revised K=2: all-position vs de-positioned content > Model sketch | branch 1: | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0708` | 708 | open | 10. Track D — Model-Side Candidate Experiments > D1 — Revised K=2: all-position vs de-positioned content > Model sketch | branch 2: | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0714` | 714 | open | 10. Track D — Model-Side Candidate Experiments > D1 — Revised K=2: all-position vs de-positioned content > Concrete experiment | initialize or regularize branch 1 using `S_posfam` | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0715` | 715 | open | 10. Track D — Model-Side Candidate Experiments > D1 — Revised K=2: all-position vs de-positioned content > Concrete experiment | compare directly against the current absolute-position K=2 model | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0716` | 716 | open | 10. Track D — Model-Side Candidate Experiments > D1 — Revised K=2: all-position vs de-positioned content > Concrete experiment | report: | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0725` | 725 | open | 10. Track D — Model-Side Candidate Experiments > D2 — K=3: absolute-position + relative/structural-position + content > When to choose | choose this if broad positional-family is real, but clearly not well modeled as one coherent branch | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0726` | 726 | open | 10. Track D — Model-Side Candidate Experiments > D2 — K=3: absolute-position + relative/structural-position + content > When to choose | especially choose this if `S_abs` and `S_rel/S_struct` are only weakly aligned | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0729` | 729 | open | 10. Track D — Model-Side Candidate Experiments > D2 — K=3: absolute-position + relative/structural-position + content > Model sketch | branch 1: | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0731` | 731 | open | 10. Track D — Model-Side Candidate Experiments > D2 — K=3: absolute-position + relative/structural-position + content > Model sketch | branch 2: | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0733` | 733 | open | 10. Track D — Model-Side Candidate Experiments > D2 — K=3: absolute-position + relative/structural-position + content > Model sketch | branch 3: | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0737` | 737 | open | 10. Track D — Model-Side Candidate Experiments > D2 — K=3: absolute-position + relative/structural-position + content > Concrete experiment | compare whether syntax-like signal moves primarily into branch 2 | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0738` | 738 | open | 10. Track D — Model-Side Candidate Experiments > D2 — K=3: absolute-position + relative/structural-position + content > Concrete experiment | test whether content branch becomes cleaner than under revised K=2 | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0743` | 743 | open | 10. Track D — Model-Side Candidate Experiments > D3 — Interaction-on-top readout on frozen branches > When to choose | choose this if broad positional stripping does not erase the residual joint signal, but a full additive shared branch still feels too assumption-heavy | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0746` | 746 | open | 10. Track D — Model-Side Candidate Experiments > D3 — Interaction-on-top readout on frozen branches > Model sketch | freeze existing K=2 or revised K=2 branches | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0747` | 747 | open | 10. Track D — Model-Side Candidate Experiments > D3 — Interaction-on-top readout on frozen branches > Model sketch | fit low-rank bilinear or factorized interaction readouts on top | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0750` | 750 | open | 10. Track D — Model-Side Candidate Experiments > D3 — Interaction-on-top readout on frozen branches > Why this is attractive | low-risk | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0751` | 751 | open | 10. Track D — Model-Side Candidate Experiments > D3 — Interaction-on-top readout on frozen branches > Why this is attractive | cheap | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0752` | 752 | open | 10. Track D — Model-Side Candidate Experiments > D3 — Interaction-on-top readout on frozen branches > Why this is attractive | directly tests whether interaction structure exists without changing the generative model | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0757` | 757 | open | 10. Track D — Model-Side Candidate Experiments > D4 — Shared/private PCC model > When to choose | choose this only if residual PCC survives broad positional-family stripping and interaction-on-top evidence is strong | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0760` | 760 | open | 10. Track D — Model-Side Candidate Experiments > D4 — Shared/private PCC model > Model sketch | `x = x_pos_priv + x_content_priv + x_shared` | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0761` | 761 | open | 10. Track D — Model-Side Candidate Experiments > D4 — Shared/private PCC model > Model sketch | `x_shared` is interpreted as shared/interaction-like only after evaluation | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0766` | 766 | open | 10. Track D — Model-Side Candidate Experiments > D5 — Hierarchical content split > When to choose | choose this if the evidence suggests the current content branch is a mixture of: | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0771` | 771 | open | 10. Track D — Model-Side Candidate Experiments > D5 — Hierarchical content split > Model sketch | stage 1: | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0773` | 773 | open | 10. Track D — Model-Side Candidate Experiments > D5 — Hierarchical content split > Model sketch | stage 2: | merged | TODO.md §6–§7 and M5–M7 |
| `PCC-L0781` | 781 | open | 11. Regularization Design > Principle | Do **not** assume the current K=2 symmetric private/private incoherence penalty is the right default for every revised architecture. | merged | TODO.md §9 and M6–M7 |
| `PCC-L0784` | 784 | open | 11. Regularization Design > Updated rationale | Strong regularization may be appropriate between: | merged | TODO.md §9 and M6–M7 |
| `PCC-L0787` | 787 | open | 11. Regularization Design > Updated rationale | But if a real shared/PCC branch exists, forcing it to be strongly orthogonal to both private branches may destroy the very signal the branch is supposed to carry. | merged | TODO.md §9 and M6–M7 |
| `PCC-L0791` | 791 | open | 11. Regularization Design > Candidate regularization schemes > For revised K=2 all-position vs content | no regularizer | merged | TODO.md §9 and M6–M7 |
| `PCC-L0792` | 792 | open | 11. Regularization Design > Candidate regularization schemes > For revised K=2 all-position vs content | current quadratic incoherence | merged | TODO.md §9 and M6–M7 |
| `PCC-L0793` | 793 | open | 11. Regularization Design > Candidate regularization schemes > For revised K=2 all-position vs content | smaller `lambda_inc` sweep: | merged | TODO.md §9 and M6–M7 |
| `PCC-L0797` | 797 | open | 11. Regularization Design > Candidate regularization schemes > For revised K=2 all-position vs content | optionally: | merged | TODO.md §9 and M6–M7 |
| `PCC-L0801` | 801 | open | 11. Regularization Design > Candidate regularization schemes > For K=3 absolute/relative/content | strong `lambda(abs, content)` | merged | TODO.md §9 and M6–M7 |
| `PCC-L0802` | 802 | open | 11. Regularization Design > Candidate regularization schemes > For K=3 absolute/relative/content | moderate `lambda(rel, content)` | merged | TODO.md §9 and M6–M7 |
| `PCC-L0803` | 803 | open | 11. Regularization Design > Candidate regularization schemes > For K=3 absolute/relative/content | weak or tuned `lambda(abs, rel)` because these branches may be related but not identical | merged | TODO.md §9 and M6–M7 |
| `PCC-L0806` | 806 | open | 11. Regularization Design > Candidate regularization schemes > For shared/private PCC | strong private/private regularization | merged | TODO.md §9 and M6–M7 |
| `PCC-L0807` | 807 | open | 11. Regularization Design > Candidate regularization schemes > For shared/private PCC | weak or zero shared/private orthogonality | merged | TODO.md §9 and M6–M7 |
| `PCC-L0808` | 808 | open | 11. Regularization Design > Candidate regularization schemes > For shared/private PCC | optional usage incentives if shared branch collapses | merged | TODO.md §9 and M6–M7 |
| `PCC-L0811` | 811 | open | 11. Regularization Design > Required ablations | no regularizer | merged | TODO.md §9 and M6–M7 |
| `PCC-L0812` | 812 | open | 11. Regularization Design > Required ablations | current quadratic cross-branch baseline | merged | TODO.md §9 and M6–M7 |
| `PCC-L0813` | 813 | open | 11. Regularization Design > Required ablations | revised pairwise penalty scope | merged | TODO.md §9 and M6–M7 |
| `PCC-L0814` | 814 | open | 11. Regularization Design > Required ablations | regularizer-strength sensitivity after the candidate architecture is stable | merged | TODO.md §9 and M6–M7 |
| `PCC-L0821` | 821 | open | 12. Causal and Counterfactual Tests > Goal | Move beyond probes and test whether candidate branches cause selective behavior changes. | merged | TODO.md M8–M10 |
| `PCC-L0824` | 824 | open | 12. Causal and Counterfactual Tests > Ablation tests | ablate broad positional-family branch | merged | TODO.md M8–M10 |
| `PCC-L0825` | 825 | open | 12. Causal and Counterfactual Tests > Ablation tests | ablate de-positioned content branch | merged | TODO.md M8–M10 |
| `PCC-L0826` | 826 | open | 12. Causal and Counterfactual Tests > Ablation tests | ablate residual/shared branch if one exists | merged | TODO.md M8–M10 |
| `PCC-L0827` | 827 | open | 12. Causal and Counterfactual Tests > Ablation tests | measure effect on: | merged | TODO.md M8–M10 |
| `PCC-L0835` | 835 | open | 12. Causal and Counterfactual Tests > Transplant tests | transplant positional-family codes across matched sentences | merged | TODO.md M8–M10 |
| `PCC-L0836` | 836 | open | 12. Causal and Counterfactual Tests > Transplant tests | transplant de-positioned content codes across matched frames | merged | TODO.md M8–M10 |
| `PCC-L0837` | 837 | open | 12. Causal and Counterfactual Tests > Transplant tests | transplant shared/PCC codes if a credible shared candidate is available | merged | TODO.md M8–M10 |
| `PCC-L0840` | 840 | open | 12. Causal and Counterfactual Tests > Expected selectivity patterns | positional-family transplant changes order/structure-sensitive behavior strongly | merged | TODO.md M8–M10 |
| `PCC-L0841` | 841 | open | 12. Causal and Counterfactual Tests > Expected selectivity patterns | de-positioned content transplant changes semantic content strongly | merged | TODO.md M8–M10 |
| `PCC-L0842` | 842 | open | 12. Causal and Counterfactual Tests > Expected selectivity patterns | shared/PCC transplant, if it exists, changes relational/syntax-sensitive behavior more than bare lexical identity or bare position | merged | TODO.md M8–M10 |
| `PCC-L0849` | 849 | open | 13. Metrics and Reporting > 13.1 Observational metrics | private-branch probe performance | merged | TODO.md §3 and M8–M9 |
| `PCC-L0850` | 850 | open | 13. Metrics and Reporting > 13.1 Observational metrics | joint performance | merged | TODO.md §3 and M8–M9 |
| `PCC-L0851` | 851 | open | 13. Metrics and Reporting > 13.1 Observational metrics | joint-only gain | merged | TODO.md §3 and M8–M9 |
| `PCC-L0852` | 852 | open | 13. Metrics and Reporting > 13.1 Observational metrics | residual performance | merged | TODO.md §3 and M8–M9 |
| `PCC-L0853` | 853 | open | 13. Metrics and Reporting > 13.1 Observational metrics | bilinear/interacting readout gain | merged | TODO.md §3 and M8–M9 |
| `PCC-L0854` | 854 | open | 13. Metrics and Reporting > 13.1 Observational metrics | rank-recovery curves for: | merged | TODO.md §3 and M8–M9 |
| `PCC-L0859` | 859 | open | 13. Metrics and Reporting > 13.1 Observational metrics | principal angles among: | merged | TODO.md §3 and M8–M9 |
| `PCC-L0865` | 865 | open | 13. Metrics and Reporting > 13.1 Observational metrics | CCA / PLS overlap among candidate representations | merged | TODO.md §3 and M8–M9 |
| `PCC-L0868` | 868 | open | 13. Metrics and Reporting > 13.2 New key bridge metrics | **position leakage score** | merged | TODO.md §3 and M8–M9 |
| `PCC-L0870` | 870 | open | 13. Metrics and Reporting > 13.2 New key bridge metrics | **content retention score** | merged | TODO.md §3 and M8–M9 |
| `PCC-L0872` | 872 | open | 13. Metrics and Reporting > 13.2 New key bridge metrics | **shift invariance score** | merged | TODO.md §3 and M8–M9 |
| `PCC-L0874` | 874 | open | 13. Metrics and Reporting > 13.2 New key bridge metrics | **structure sensitivity ratio** | merged | TODO.md §3 and M8–M9 |
| `PCC-L0876` | 876 | open | 13. Metrics and Reporting > 13.2 New key bridge metrics | **residual PCC score** | merged | TODO.md §3 and M8–M9 |
| `PCC-L0880` | 880 | open | 13. Metrics and Reporting > 13.3 Training metrics | total FVU | merged | TODO.md §3 and M8–M9 |
| `PCC-L0881` | 881 | open | 13. Metrics and Reporting > 13.3 Training metrics | branch-only error ratios | merged | TODO.md §3 and M8–M9 |
| `PCC-L0882` | 882 | open | 13. Metrics and Reporting > 13.3 Training metrics | branch energy ratios | merged | TODO.md §3 and M8–M9 |
| `PCC-L0883` | 883 | open | 13. Metrics and Reporting > 13.3 Training metrics | incoherence metrics between private branches | merged | TODO.md §3 and M8–M9 |
| `PCC-L0884` | 884 | open | 13. Metrics and Reporting > 13.3 Training metrics | overlap metrics involving any shared branch | merged | TODO.md §3 and M8–M9 |
| `PCC-L0885` | 885 | open | 13. Metrics and Reporting > 13.3 Training metrics | active latent fractions | merged | TODO.md §3 and M8–M9 |
| `PCC-L0886` | 886 | open | 13. Metrics and Reporting > 13.3 Training metrics | usage entropy / gini | merged | TODO.md §3 and M8–M9 |
| `PCC-L0887` | 887 | open | 13. Metrics and Reporting > 13.3 Training metrics | revival rate per M tokens | merged | TODO.md §3 and M8–M9 |
| `PCC-L0890` | 890 | open | 13. Metrics and Reporting > 13.4 Causal metrics | syntax drop under branch removal | merged | TODO.md §3 and M8–M9 |
| `PCC-L0891` | 891 | open | 13. Metrics and Reporting > 13.4 Causal metrics | semantics drop under branch removal | merged | TODO.md §3 and M8–M9 |
| `PCC-L0892` | 892 | open | 13. Metrics and Reporting > 13.4 Causal metrics | position-family drop under branch removal | merged | TODO.md §3 and M8–M9 |
| `PCC-L0893` | 893 | open | 13. Metrics and Reporting > 13.4 Causal metrics | selectivity index for each branch | merged | TODO.md §3 and M8–M9 |
| `PCC-L0894` | 894 | open | 13. Metrics and Reporting > 13.4 Causal metrics | transplant success / degradation scores | merged | TODO.md §3 and M8–M9 |
| `PCC-L0897` | 897 | open | 13. Metrics and Reporting > 13.5 Reporting principles | Keep the already-established Paper 1 result separate from new positional-family and PCC claims. | merged | TODO.md §3 and M8–M9 |
| `PCC-L0898` | 898 | open | 13. Metrics and Reporting > 13.5 Reporting principles | Do **not** overstate the current K=2 result as already proving broad positional-family separation. | merged | TODO.md §3 and M8–M9 |
| `PCC-L0899` | 899 | open | 13. Metrics and Reporting > 13.5 Reporting principles | Use “de-positioned content” rather than “pure content” unless the evidence becomes unusually strong. | merged | TODO.md §3 and M8–M9 |
| `PCC-L0900` | 900 | open | 13. Metrics and Reporting > 13.5 Reporting principles | Do **not** call something a “syntax branch” unless the evidence clearly shows branch-level selectivity beyond general positional-family effects. | merged | TODO.md §3 and M8–M9 |
| `PCC-L0907` | 907 | open | 14. Seed, Holdout, and Stability Requirements > Minimum standards before claiming broad positional-family separation | at least `3` seeds for observational audits | merged | TODO.md §3, §5, M7–M9 |
| `PCC-L0908` | 908 | open | 14. Seed, Holdout, and Stability Requirements > Minimum standards before claiming broad positional-family separation | IID + source-holdout required | merged | TODO.md §3, §5, M7–M9 |
| `PCC-L0909` | 909 | open | 14. Seed, Holdout, and Stability Requirements > Minimum standards before claiming broad positional-family separation | corpus-holdout strongly preferred | merged | TODO.md §3, §5, M7–M9 |
| `PCC-L0910` | 910 | open | 14. Seed, Holdout, and Stability Requirements > Minimum standards before claiming broad positional-family separation | matched-token and matched-position controls required for publication-facing claims | merged | TODO.md §3, §5, M7–M9 |
| `PCC-L0913` | 913 | open | 14. Seed, Holdout, and Stability Requirements > Minimum standards before claiming residual PCC | broad positional-family stripping must already be in place | merged | TODO.md §3, §5, M7–M9 |
| `PCC-L0914` | 914 | open | 14. Seed, Holdout, and Stability Requirements > Minimum standards before claiming residual PCC | residual joint/bilinear gain must survive: | merged | TODO.md §3, §5, M7–M9 |
| `PCC-L0921` | 921 | open | 14. Seed, Holdout, and Stability Requirements > Stability outputs | pass/fail tables by: | merged | TODO.md §3, §5, M7–M9 |
| `PCC-L0928` | 928 | open | 14. Seed, Holdout, and Stability Requirements > Stability outputs | bootstrap CIs for key metrics | merged | TODO.md §3, §5, M7–M9 |
| `PCC-L0929` | 929 | open | 14. Seed, Holdout, and Stability Requirements > Stability outputs | threshold sensitivity for any new gates | merged | TODO.md §3, §5, M7–M9 |
| `PCC-L0936` | 936 | done | 15. Proposed Experiment Order > Phase 0 — Freeze historical record | Freeze and archive the final outputs of the completed K=2 fastdata-stream wave. | carried | TODO.md §8 |
| `PCC-L0937` | 937 | done | 15. Proposed Experiment Order > Phase 0 — Freeze historical record | Freeze the completed PCC A0/A1/A1b/A1c/B-light artifacts. | carried | TODO.md §8 |
| `PCC-L0938` | 938 | open | 15. Proposed Experiment Order > Phase 0 — Freeze historical record | Write a reinterpretation memo before any new model-side claims. | merged | TODO.md §8 |
| `PCC-L0941` | 941 | open | 15. Proposed Experiment Order > Phase 1 — No-new-training reinterpretation and label build | Track R reinterpretation memo | merged | TODO.md §8 |
| `PCC-L0942` | 942 | open | 15. Proposed Experiment Order > Phase 1 — No-new-training reinterpretation and label build | Stage P0 positional-family label inventory | merged | TODO.md §8 |
| `PCC-L0943` | 943 | open | 15. Proposed Experiment Order > Phase 1 — No-new-training reinterpretation and label build | task-family remapping of current PCC results | merged | TODO.md §8 |
| `PCC-L0946` | 946 | open | 15. Proposed Experiment Order > Phase 2 — No-new-training positional-family audits | Stage P1 raw-activation positional-family gate | merged | TODO.md §8 |
| `PCC-L0947` | 947 | open | 15. Proposed Experiment Order > Phase 2 — No-new-training positional-family audits | Stage P2 K=2 leakage audit | merged | TODO.md §8 |
| `PCC-L0948` | 948 | open | 15. Proposed Experiment Order > Phase 2 — No-new-training positional-family audits | Stage P3 shift-based counterfactual suite | merged | TODO.md §8 |
| `PCC-L0949` | 949 | open | 15. Proposed Experiment Order > Phase 2 — No-new-training positional-family audits | Stage P4 residualization/adversarial baselines | merged | TODO.md §8 |
| `PCC-L0950` | 950 | open | 15. Proposed Experiment Order > Phase 2 — No-new-training positional-family audits | Stage P5 residual-PCC audit after broad positional stripping | merged | TODO.md §8 |
| `PCC-L0953` | 953 | open | 15. Proposed Experiment Order > Phase 3 — Minimal new model work | D3 interaction-on-top readout on frozen branches if residual PCC survives | merged | TODO.md §8 |
| `PCC-L0954` | 954 | open | 15. Proposed Experiment Order > Phase 3 — Minimal new model work | D1 revised K=2 all-position vs content if broad positional-family explanation dominates | merged | TODO.md §8 |
| `PCC-L0957` | 957 | open | 15. Proposed Experiment Order > Phase 4 — Higher-complexity model work | D2 K=3 absolute/relative/content if broad positional-family exists but does not look single-branch | merged | TODO.md §8 |
| `PCC-L0958` | 958 | open | 15. Proposed Experiment Order > Phase 4 — Higher-complexity model work | D4 shared/private PCC model only if genuine residual PCC remains after broad positional stripping | merged | TODO.md §8 |
| `PCC-L0959` | 959 | open | 15. Proposed Experiment Order > Phase 4 — Higher-complexity model work | D5 hierarchical content split only if the content side still looks internally mixed after revised K=2 | merged | TODO.md §8 |
| `PCC-L0962` | 962 | open | 15. Proposed Experiment Order > Phase 5 — Regularization follow-up | run targeted regularization studies only after a candidate architecture is justified | merged | TODO.md §8 |
| `PCC-L0970` | 970 | open | 16. Decision Gates > Gate PF-1: Is the current PCC story mostly under-modeled broad position? | broad positional-family probes recover much more syntax/structure-sensitive signal than the old absolute-position-only setup | merged | TODO.md §7 |
| `PCC-L0971` | 971 | open | 16. Decision Gates > Gate PF-1: Is the current PCC story mostly under-modeled broad position? | `x_content_priv` shows substantial relative/structural position leakage | merged | TODO.md §7 |
| `PCC-L0972` | 972 | open | 16. Decision Gates > Gate PF-1: Is the current PCC story mostly under-modeled broad position? | simple broad positional stripping materially reduces the earlier syntax-like joint gain | merged | TODO.md §7 |
| `PCC-L0975` | 975 | open | 16. Decision Gates > Gate PF-1: Is the current PCC story mostly under-modeled broad position? | do not conclude this yet | merged | TODO.md §7 |
| `PCC-L0979` | 979 | open | 16. Decision Gates > Gate PF-2: Does a useful de-positioned content representation exist? | semantic/content tasks remain strong after broad positional stripping | merged | TODO.md §7 |
| `PCC-L0980` | 980 | open | 16. Decision Gates > Gate PF-2: Does a useful de-positioned content representation exist? | broad position leakage drops sharply | merged | TODO.md §7 |
| `PCC-L0981` | 981 | open | 16. Decision Gates > Gate PF-2: Does a useful de-positioned content representation exist? | the representation remains stable under positional shifts | merged | TODO.md §7 |
| `PCC-L0984` | 984 | open | 16. Decision Gates > Gate PF-2: Does a useful de-positioned content representation exist? | record that “pure” or strongly de-positioned content may not be a meaningful target at this site | merged | TODO.md §7 |
| `PCC-L0988` | 988 | open | 16. Decision Gates > Gate PF-3: Does residual PCC survive after broad positional stripping? | syntax/relational tasks still show stable positive joint-only or bilinear-only gain | merged | TODO.md §7 |
| `PCC-L0989` | 989 | open | 16. Decision Gates > Gate PF-3: Does residual PCC survive after broad positional stripping? | that gain survives controls and holdouts | merged | TODO.md §7 |
| `PCC-L0990` | 990 | open | 16. Decision Gates > Gate PF-3: Does residual PCC survive after broad positional stripping? | the gain is not obviously explained by leftover positional-family leakage | merged | TODO.md §7 |
| `PCC-L0993` | 993 | open | 16. Decision Gates > Gate PF-3: Does residual PCC survive after broad positional stripping? | stop before launching shared-branch training | merged | TODO.md §7 |
| `PCC-L0997` | 997 | open | 16. Decision Gates > Gate PF-4: Is one positional branch enough? | `S_abs`, `S_rel`, and `S_struct` behave like one coherent family | merged | TODO.md §7 |
| `PCC-L1000` | 1000 | open | 16. Decision Gates > Gate PF-4: Is one positional branch enough? | absolute and relative/structural position separate materially from each other | merged | TODO.md §7 |
| `PCC-L1001` | 1001 | open | 16. Decision Gates > Gate PF-4: Is one positional branch enough? | one position-family branch looks too compressed or unstable | merged | TODO.md §7 |
| `PCC-L1005` | 1005 | open | 16. Decision Gates > Gate PF-5: Is a trained new model justified? | no-new-training evidence is already strong | merged | TODO.md §7 |
| `PCC-L1006` | 1006 | open | 16. Decision Gates > Gate PF-5: Is a trained new model justified? | a concrete architecture choice is supported by the decision tree above | merged | TODO.md §7 |
| `PCC-L1007` | 1007 | open | 16. Decision Gates > Gate PF-5: Is a trained new model justified? | the planned model comparison is specific enough to falsify the chosen story | merged | TODO.md §7 |
| `PCC-L1014` | 1014 | open | 17. Risks and Failure Modes > Conceptual risks | “pure content” may not exist cleanly in contextual residual activations. | merged | TODO.md §11 |
| `PCC-L1015` | 1015 | open | 17. Risks and Failure Modes > Conceptual risks | relative position may not be token-local and may require pairwise/window-aware features. | merged | TODO.md §11 |
| `PCC-L1016` | 1016 | open | 17. Risks and Failure Modes > Conceptual risks | syntax may not reduce to broad positional-family structure even if position matters a lot. | merged | TODO.md §11 |
| `PCC-L1017` | 1017 | open | 17. Risks and Failure Modes > Conceptual risks | broad positional-family stripping may remove useful semantic/contextual information accidentally. | merged | TODO.md §11 |
| `PCC-L1020` | 1020 | open | 17. Risks and Failure Modes > Experimental risks | lexical shortcuts may masquerade as relative-position signal | merged | TODO.md §11 |
| `PCC-L1021` | 1021 | open | 17. Risks and Failure Modes > Experimental risks | structural labels may be noisy or parser-dependent | merged | TODO.md §11 |
| `PCC-L1022` | 1022 | open | 17. Risks and Failure Modes > Experimental risks | contrast-set transformations may accidentally change semantics while intended to change only structure or position | merged | TODO.md §11 |
| `PCC-L1023` | 1023 | open | 17. Risks and Failure Modes > Experimental risks | prefix/suffix shift tests may introduce distribution shift artifacts | merged | TODO.md §11 |
| `PCC-L1026` | 1026 | open | 17. Risks and Failure Modes > Modeling risks | forcing all broad positional structure into one branch may be too restrictive | merged | TODO.md §11 |
| `PCC-L1027` | 1027 | open | 17. Risks and Failure Modes > Modeling risks | K=3 may be necessary but harder to stabilize than the current K=2 regime | merged | TODO.md §11 |
| `PCC-L1028` | 1028 | open | 17. Risks and Failure Modes > Modeling risks | over-regularization may destroy shared or structurally positional signal | merged | TODO.md §11 |
| `PCC-L1031` | 1031 | open | 17. Risks and Failure Modes > Reporting risks | overclaiming “syntax branch” when evidence only supports “position-family-sensitive” structure | merged | TODO.md §11 |
| `PCC-L1032` | 1032 | open | 17. Risks and Failure Modes > Reporting risks | overclaiming “pure content” when evidence only supports “reduced position leakage” | merged | TODO.md §11 |
| `PCC-L1033` | 1033 | open | 17. Risks and Failure Modes > Reporting risks | treating the existing PCC results as already decisive when they were collected under the narrower absolute-position framing | merged | TODO.md §11 |
| `PCC-L1075` | 1075 | open | 19. Deliverables | `analysis/pcc_reinterpretation_20260616.md` | merged | TODO.md milestone output blocks |
| `PCC-L1076` | 1076 | open | 19. Deliverables | `analysis/position_family_labels/` | merged | TODO.md milestone output blocks |
| `PCC-L1077` | 1077 | open | 19. Deliverables | `analysis/position_family_gate/` | merged | TODO.md milestone output blocks |
| `PCC-L1078` | 1078 | open | 19. Deliverables | `analysis/position_leakage_audit/` | merged | TODO.md milestone output blocks |
| `PCC-L1079` | 1079 | open | 19. Deliverables | `analysis/shift_counterfactuals/` | merged | TODO.md milestone output blocks |
| `PCC-L1080` | 1080 | open | 19. Deliverables | `analysis/deposition_baselines/` | merged | TODO.md milestone output blocks |
| `PCC-L1081` | 1081 | open | 19. Deliverables | `analysis/residual_pcc_audit/` | merged | TODO.md milestone output blocks |
| `PCC-L1082` | 1082 | open | 19. Deliverables | `analysis/pcc_candidate_comparison/` | merged | TODO.md milestone output blocks |
| `PCC-L1083` | 1083 | open | 19. Deliverables | `configs/pcc/` | merged | TODO.md milestone output blocks |
| `PCC-L1084` | 1084 | open | 19. Deliverables | `prereg/pcc_positional_family_revision_v2.md` | merged | TODO.md milestone output blocks |
| `PCC-L1085` | 1085 | open | 19. Deliverables | `reports/pcc_stageR.md` | merged | TODO.md milestone output blocks |
| `PCC-L1086` | 1086 | open | 19. Deliverables | `reports/pcc_stageP.md` | merged | TODO.md milestone output blocks |
| `PCC-L1087` | 1087 | open | 19. Deliverables | `reports/pcc_stageCounterfactual.md` | merged | TODO.md milestone output blocks |
| `PCC-L1088` | 1088 | open | 19. Deliverables | `reports/pcc_model_decision.md` | merged | TODO.md milestone output blocks |
| `PCC-L1089` | 1089 | open | 19. Deliverables | `reports/pcc_final_decision.md` | merged | TODO.md milestone output blocks |

## Assertions

- `MAIN`: `269` checkbox IDs = `213` open + `56` done; every ID appears exactly once above.
- `PCC`: `428` checkbox IDs = `394` open + `34` done; every ID appears exactly once above.
- Disposition count:
  - `MAIN` `carried`: `56`
  - `MAIN` `merged`: `137`
  - `MAIN` `superseded`: `76`
  - `PCC` `carried`: `34`
  - `PCC` `merged`: `394`
- `intentionally dropped`: `0`.
- Destination anchors are section-level by design; consolidated duplicate actions share a destination, while the source ID preserves one-to-one auditability.
