# TODO.md — Unified MSAE Experimental and Paper Roadmap

**Roadmap version:** 2026-08-02

**Active scope:** finish the next MSAE paper before beginning the larger Paper 2/3 program.

**Supersedes as an active plan:** the pre-merge `TODO.md` and `TODO_pcc.md`. Byte-identical source snapshots and the merge audit are under `docs/archive/`.

## 0. How to Use This Document

This is the single active execution plan for the MSAE project. It combines:
- the original three-paper MSAE roadmap;
- the completed raw-activation and K=2 work;
- the completed PCC A0/A1/A1b/A1c/B-light/contrast sequence;
- the newer hypothesis that “position” may be a family of absolute, relative, and structural signals;
- the work required to choose, train, evaluate, and write the next paper.

### Status labels
- `[x]` — completed and supported by an artifact.
- `[ ]` — not yet completed.
- **AUTHORITATIVE** — use for the current claim or decision.
- **DIAGNOSTIC / EXPLORATORY** — useful for designing the next test, not confirmatory evidence.
- **SUPERSEDED** — historically informative, but replaced by a corrected run or policy.
- **PLANNED** — a proposed deliverable or path that does not exist yet.

### Evidence precedence
When artifacts disagree, use claim-specific evidence rather than “newest file wins”:
1. Frozen preregistrations and decision records govern what a gate meant at that time. Amendments coexist with; they do not rewrite, frozen decisions.
2. A run manifest describes intended jobs, not completion.
3. Final structured summaries and aggregate tables govern reported metrics.
4. Completion requires a final summary and terminal completion evidence when both are expected.
5. Status snapshots are time-bounded and cannot override a later final summary.
6. Logs are diagnostic fallback evidence and do not override consistent structured results.
7. `RESULTS.md`, `ANALYSIS.md`, and old TODO status prose are date-bounded secondary summaries.

### Frozen governance distinctions
These records must remain separate in every paper draft and project summary:
- [x] Original Stage A1 decision: `proceed_to_stage_b = false`.
- [x] A1b diagnostic: candidate amendment supported; it did not alter A1.
- [x] A1c confirmation and A1r: the prospective amended observational gate passed.
- [x] B-light: analysis-only controls on existing checkpoints.
- [x] Small Stage-B contrast audit: `proceed_to_stage_c = false`.

---

## 1. Current Project State

### 1.1 Bottom line

The project has completed feasibility, intermediate K=2 training, the atlas-v1 architecture-confirmation audit, and the requested post-score diagnostic execution, but it has **not** completed the next paper or selected a paper branch. **Atlas-v1 returned G1 = equivocal and G2 = equivocal. The base completion root stopped because primary L3 produced only `414/500` scientifically finite refit draws versus the frozen `>=450` minimum. A separately reviewed additive continuation then ran all 16 registered scoring jobs: all four K2 refits again had `414/500` scientifically finite draws, stability had `0/500` jointly finite draws, and all four specificity computations completed with invalid counterfactual gates. The recovered canonical summary therefore preserves the original equivocal decisions, leaves G1a/G2a unrendered, and does not warrant new model training from the current evidence.** The earlier pre-K2 and training results below remain valid for their narrower engineering and logged-metric claims; they do not override this newer functional architecture decision or the registered stops.

The strongest supported statements are:
- [x] Under the older locked v2 pre-K2 gate, Pythia-160M layers 3 and 4 contain a robust low-rank regime separating position-predictive and token/content-predictive probe subspaces; atlas-v1 does not establish selective absolute-vs-structural positional components.
- [x] Layer 3 is the frozen atlas-v1 primary site; layer 4 is descriptive only. The older pre-K2 decision named L4 as a fallback, but atlas-v1 explicitly disabled data-selected fallback.
- [x] The custom K=2 trainer is operational, resumable, and capable of reaching a 1B-token budget.
- [x] `lambda_inc=1e-2` materially reduces the logged cross-branch incoherence estimate relative to a matched no-incoherence control.
- [x] The current regularizer pays a modest reconstruction cost; lower logged incoherence is a geometry result, not evidence of functionally selective branches.
- [x] Existing PCC audits show small task-dependent joint gains, especially for POS and coarse dependency labels, but do not yet distinguish genuine shared interaction from under-modeled relative/structural position.
- [x] Atlas-v1 point diagnostics favor a lexical/semantic complement and disfavor the existing K=2 branch interpretation. The frozen completion plus diagnostic continuation ran the requested raw/K2 refits, Tier-2 collateral, stability, and specificity computations, but their registered inferential gates failed. This is neither a supported negative nor a simple-baseline win.

The project has **not** yet established that:
- [ ] the learned K=2 branches satisfy the four original position/content validation criteria;
- [ ] K=2 beats a matched standard K=1 SAE;
- [ ] the learned decomposition is stable across five confirmatory seeds;
- [ ] a shared/PCC branch is warranted;
- [ ] all positional information can be represented by one branch;
- [ ] a broad taxonomy of activation information is naturally separable;
- [ ] the frozen simple projection comparator is equivalent or superior under the preregistered simultaneous gates;
- [ ] Paper 2 or Paper 3 should begin.

No MSAE or PCC job is currently active.

### 1.2 Run inventory and disposition

#### Raw-activation and pre-K2 work
| Run | State | Evidence use |
|---|---|---|
| `pilot_runs/20260526_201536/` | complete | early feasibility; exploratory |
| `pilot_runs/20260526_224002_saga3000_c2alt/` | partial | criterion/optimizer development only |
| `pilot_runs/20260527_124434_torch_gpu_probes/` | complete | GPU-probe engineering; exploratory |
| `pilot_runs/20260527_140213_rankcurve_c2var_balanced/` | launcher-only | no scientific result |
| `pilot_runs/20260527_140327_rankcurve_c2var_balanced/` | complete | rank-curve diagnostic |
| `pilot_runs/20260527_210247_v5_gpufirst_balanced_multiseed/` | complete | transitional v2-gate evidence |
| `pilot_runs/20260528_001028_v6_prek2_fullsuite/` | partial/pending snapshot | superseded attempt |
| `pilot_runs/20260528_001131_v6_prek2_fullsuite/` | partial/running snapshot | superseded attempt |
| `pilot_runs/20260528_001543_v6_prek2_fullsuite/` | complete, 50/50 jobs | **AUTHORITATIVE pre-K2 run** |
| `pilot_runs/20260528_132545_compat_v5_iid/` | complete | data-regime compatibility control |

Authoritative pre-K2 results:
- [x] Pythia-160M headline ranks `8,16`: `92/92` v2 gate passes across IID, source-holdout, and corpus-holdout rows.
- [x] Boundary rank `32`: `0/46` passes.
- [x] Mean raw position AUC: L3 `0.7911`; L4 `0.7805`.
- [x] Historical pre-K2 decision: L3 primary, L4 fallback; atlas-v1 later froze L3 and made L4 descriptive.
- [x] Packaged evidence: `reports/pre_k2_suite_v6/`.

#### K=2 training work
| Run | State | Evidence use |
|---|---|---|
| `pilot_runs/_k2_smoke_test/` | complete | trainer smoke |
| `pilot_runs/_k2_resume_test/` | complete | checkpoint/resume validation |
| `pilot_runs/20260528_142003_k2_msae_wave1/` | complete, four 100M jobs | promotion gate |
| `pilot_runs/20260529_000001_smoke_k2_msae_wave2/` | complete | wave-2 smoke |
| `pilot_runs/20260529_122259_k2_msae_wave2/` | compromised | **SUPERSEDED** data-pipeline failure mode |
| `pilot_runs/20260601_131703_k2_msae_wave2_fastdata/` | empty launch directory | no result |
| `pilot_runs/20260601_131736_k2_msae_wave2_fastdata/` | logs only | failed/abandoned launch attempt |
| `pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/` | complete, four 1B jobs | **AUTHORITATIVE current K=2 behavior** |

Final 1B tail metrics (`FVU`: lower is better; incoherence is the logged estimator):
| Job | Seed | `lambda_inc` | Tail-100 FVU | Tail-100 incoherence | Active pos | Active content |
|---|---:|---:|---:|---:|---:|---:|
| `g4` | 42 | `1e-2` | 0.076385 | 0.004643 | 0.887 | 0.911 |
| `g5` | 43 | `1e-2` | 0.071359 | 0.003150 | 0.897 | 0.926 |
| `g6` | 44 | `1e-2` | 0.073543 | 0.002811 | 0.896 | 0.935 |
| `g7` | 42 | `0` | 0.069778 | 0.015200 | 0.923 | 0.930 |

Interpretation:
- [x] Matched-seed `g4` vs `g7`: about `3.3x` lower incoherence, but `+0.00661` absolute FVU.
- [x] Mean regularized incoherence is about `4.3x` lower than the control.
- [x] All final dead fractions are zero; branch utilization is healthy.
- [x] All regularized seeds reconstruct slightly worse than the control.
- [ ] Decide whether a clean from-zero replication under the corrected loader is required. The current fastdata run resumed prior checkpoints and is sufficient for intermediate validation, not automatically for a final clean training claim.

#### PCC and positional-family bridge work
| Stage | Run | State and formal interpretation |
|---|---|---|
| A0 | `pilot_runs/20260604_184924_pcc_stage_a0/` | complete; POS/deprel promising; proceed to A1 |
| A1 | `pilot_runs/20260605_013756_pcc_stage_a1/` | complete; frozen no-go, `proceed_to_stage_b=false` |
| A1b | `pilot_runs/20260605_030600_pcc_stage_a1b/` | complete diagnostic; candidate amendment supported |
| A1c/A1r | `pilot_runs/20260605_034815_pcc_stage_a1c/` | complete; amended observational path confirmed and adopted prospectively |
| B-light | `pilot_runs/20260605_040323_pcc_stage_b_light_controls/` | complete, analysis-only controls |
| Small contrasts | `pilot_runs/20260605_111613_pcc_stage_b_contrasts/` | complete exploratory audit; `0` syntax and `4` semantic families pass; no Stage C |

PCC interpretation:
- [x] POS joint gains are small but repeat across several observational settings.
- [x] Coarse dependency gains survive full/coarse-position controls but weaken sharply under matched-token control.
- [x] Semantic sentinels are generally content-private; label framing and probe-selection metric materially affect the gate.
- [x] Matched-seed `g7 > g4` syntax gain is consistent with the incoherence regularizer suppressing either useful shared structure or positional leakage.
- [x] The 24-pair contrast audit is exploratory: three hand-written pairs per family, sentence-mean pooling, and sign-based family tests are insufficient for a paper claim.
- [x] Reinterpret all PCC results under the broader positional-family hypothesis before building a PCC branch; see `analysis/pcc_reinterpretation.md`.

#### Atlas-v1 post-score completion attempt

| Run | State | Evidence use |
|---|---|---|
| `pilot_runs/20260801_atlas_completion_v1/` | frozen stop after baseline and raw L3/L4 | **AUTHORITATIVE completion-attempt disposition; no promoted branch decision** |

- [x] Pilot v10 passed numerical and resource gates; the implementation received adversarial `SHIP` and was frozen as `0aac744d4d10f56cafae645fdc71ea8348bec743a5c20561d4649aedac0503ee` before completion scores.
- [x] Calibration baseline selection failed: only eight of nine Tier-2 sentinels were eligible (`source_type` failed), and only five of nine Tier-1 tasks met the frozen denominator rule. `projection_broad16` was retained as the registered fallback with `baseline_selection_failed=true`.
- [x] L3 and L4 each produced all 500 requested draw artifacts. L3 had `414/500` scientifically finite draws and wrote `FROZEN_EQUIVOCAL_STOP.json`; descriptive L4 had `500/500` finite draws.
- [x] The root `NOT_LAUNCHED_UPSTREAM_STOP.json` accurately binds what the base launcher skipped, but this left the explicitly authorized K2, stability, and specificity diagnostic work incomplete.
- [x] Original G1/G2 and the no-decision branch remain unchanged; no `planning_decision_v2` was rendered and no training was launched. See `reports/atlas_completion_results.md`.

#### Additive diagnostic continuation and canonical recovery

| Run/artifact | State | Evidence use |
|---|---|---|
| `pilot_runs/20260802_atlas_completion_diagnostic_continuation_v1/` | 16/16 scoring jobs closed; four K2 and stability stages stopped scientifically; four specificity stages complete but invalid | **AUTHORITATIVE diagnostic execution; no decision-promotion authority** |
| `results/atlas/completion_diagnostic_v1/` | recovered canonical summary, externally success-closed and replay-verified | **AUTHORITATIVE combined diagnostic disposition** |

- [x] All four K2 point jobs and all `4 × 500` discovery-refit draws ran. Every checkpoint retained exactly `414/500` scientifically finite draws, below the frozen `>=450` requirement.
- [x] Tier-2 collateral was computed within the K2 refits, but the complete-case failure prevents confirmatory family inference.
- [x] Cross-checkpoint stability ran for the point and all 500 draws. The joint endpoint had `0/500` scientifically finite draws. The relative/structural point coordinates (learned mean pairwise CKA `0.9982635047210163`; simple A/B CKA `1.0`) are descriptive only.
- [x] All four matched-random/sham specificity computations completed, but every `counterfactual_gate_valid` value is `false`; these results cannot support a causal or negative claim.
- [x] Candidate replay, independent result review, independent claim review, promotion freeze, canonical tmux publication, and final verification all passed. The blind final stayed locked and no training/checkpoint artifact was created.
- [x] Original G1/G2 remain equivocal; G1a is invalid/unrendered; G2a is not promotable/unrendered; the paper branch remains unselected; training is **not warranted by current evidence**.

---

## 2. Expanded Scientific Objective

### 2.1 Primary question

Can a transformer residual stream be decomposed into a **small, reproducible set of components** that selectively preserve distinct, operationally defined information families while controlling reconstruction loss, leakage, and causal side effects?

The next paper should answer this question first on Pythia-160M L3. Atlas-v1 treats L4 as descriptive; any future L4 fallback would require a new prescore amendment/preregistration and independent confirmation. The project should not assume in advance that the correct decomposition is position/content, broad-position/content, or private/shared.

### 2.2 Why the original framing must expand

The original K=2 experiment treated “position” mainly as absolute token index. Contextual activations can also carry:
- relative order and signed distance;
- dependency direction/distance;
- boundary, span, and depth structure;
- formatting and sequence-location cues.

Therefore a syntax-like signal in the current content/joint representation has at least two explanations:
1. genuine position-content interaction/shared information;
2. positional-family information that the absolute-position branch failed to isolate.

These explanations require different architectures. They must be separated observationally before new model training.

### 2.3 Primary hypotheses

- [ ] **H1 — low-complexity family structure:** a small number of task-derived subspaces explain a reproducible portion of held-out information selectivity.
- [ ] **H2 — broad positional-family:** absolute, relative, and structural-position tasks share enough geometry to support one broad position component.
- [ ] **H3 — multiple positional components:** absolute position separates materially from relative/structural position, favoring at least two positional components.
- [ ] **H4 — de-positioned content:** a representation can substantially reduce broad positional leakage while retaining lexical/semantic utility.
- [ ] **H5 — residual interaction/PCC:** stable syntax or relational utility remains only in joint/bilinear/shared readouts after broad positional stripping.
- [ ] **H6 — regularization tradeoff:** cross-branch incoherence improves selectivity but can suppress useful shared or incompletely modeled structure.
- [ ] **H7 — minimal-K:** the smallest architecture justified by held-out evidence is more stable and competitive than larger speculative decompositions.
- [ ] **H8 — dense residual:** some linearly predictable reconstruction residual is better represented by a dense low-rank component than by additional sparse atoms; this remains a gated follow-on unless it is needed for the next paper.

### 2.4 Null and weakening outcomes

- [ ] **N1:** apparent families are probe-specific and do not replicate across tasks/datasets.
- [ ] **N2:** removing broad position destroys too much content utility for “de-positioned content” to be meaningful.
- [ ] **N3:** relative/structural position is not coherent in token-local activations and requires relation-aware features.
- [ ] **N4:** joint gains vanish under held-out controls; no PCC/shared branch is justified.
- [ ] **N5:** simple projection or scrubbing matches MSAE; the learned multi-branch model adds no value.
- [ ] **N6:** K=1 SAE matches the selected MSAE at equal capacity, sparsity, data, and compute.
- [ ] **N7:** larger K reduces reconstruction or stability without improving selective information recovery.
- [ ] **N8:** the entire result is better framed as regularizer-induced partitioning than intrinsic morphological decomposition.

### 2.5 Non-goals and claim discipline

- [ ] Do not promise “pure” content; use **position-minimized** or **de-positioned** content.
- [ ] Do not call probe-weight clusters ground-truth ontology.
- [ ] Do not equate orthogonality with functional independence.
- [ ] Do not equate low incoherence loss with mutual-coherence theorem satisfaction.
- [ ] Do not call joint gain PCC until it survives broad-position removal and held-out controls.
- [ ] Do not claim unsupervised discovery if labels/tasks selected the architecture or branch interpretation.
- [ ] Do not start Paper 2/3 execution until the next-paper gate is frozen.

---

## 3. Operational Definition of “Separable Information”

### 3.1 Information family

An **information family** is a preregistered collection of tasks that share a proposed functional role. It is a hypothesis about representation, not a statement that the model contains a single natural feature type.

Every family must have:
- [ ] a definition and exclusion rules;
- [ ] at least two task variants or datasets when feasible;
- [ ] chance/baseline performance;
- [ ] shortcut and confound analysis;
- [ ] token-local or relation-aware designation;
- [ ] discovery and confirmatory versions;
- [ ] a fixed primary metric.

### 3.2 Candidate component

A **candidate component** may be a probe-derived subspace, projection residual, learned MSAE branch, dense low-rank branch, or explicitly modeled shared/interaction representation.

A component is not validated by decodability alone. It must satisfy all applicable axes below.

### 3.3 Required evidence axes

1. **Recovery:** the assigned family remains decodable from the component on held-out data.
2. **Selectivity:** assigned-family recovery exceeds non-assigned-family recovery after normalization to raw/chance performance.
3. **Depletion/leakage:** the complement and non-assigned components lose the assigned signal, while sentinel families are retained where expected.
4. **Reconstruction accounting:** components add to a competitive reconstruction; information is not “separated” merely by discarding difficult variance.
5. **Stability:** the component/family relation replicates across seeds, splits, sources, and task variants, accounting for branch permutation.
6. **Counterfactual or causal specificity:** interventions that primarily alter a family preferentially move/affect the assigned component.
7. **Baseline advantage:** the result is not matched by raw probes, PCA/projection, linear scrubbing, a standard K=1 SAE, or an unregularized/capacity-matched multi-branch control.

### 3.4 Core normalized metrics

For task `t`, let `S_raw(t)` be the raw score, `S_chance(t)` the chance/control score, and `S_c(t)` the score from component `c`.

Metric eligibility and orientation rules:
- [ ] Convert every primary task metric to a bounded higher-is-better orientation before normalization; report losses such as FVU/CE separately rather than inserting them into the recovery formula.
- [ ] A task is eligible for normalized recovery only when the cross-fitted raw-over-chance gap is positive and its lower 95% confidence bound exceeds an eligibility floor locked in M2 (planning default: the larger of `0.02` absolute or two estimated standard errors).
- [ ] If `S_raw - S_chance` fails that rule, mark normalized recovery **undefined**, exclude it from family aggregation under the preregistered missing-task rule, and treat the task as evidence that the family is not reliably measurable at this site; never replace the denominator with an arbitrary epsilon to manufacture a score.
- [ ] Define target and sentinel intervention effects as non-negative magnitudes in a preregistered beneficial/harmful direction. An opposite-signed target effect is a failed specificity test, not a negative denominator.
- [ ] Make absolute target-minus-sentinel effect the primary specificity gate. Ratios are descriptive only, use a locked positive denominator floor, and are undefined when their interpretation would change under that floor.
- [ ] Report every normalized value or ratio with its raw numerator, denominator, uncertainty, and undefined-task count.

- [ ] **Normalized recovery:** `(S_c - S_chance) / (S_raw - S_chance)`.
- [ ] **Assigned-family recovery:** mean/median normalized recovery over confirmatory tasks in the assigned family.
- [ ] **Leakage:** maximum normalized recovery for that family from non-assigned components.
- [ ] **Selectivity margin:** assigned recovery minus highest non-assigned recovery.
- [ ] **Complement depletion:** raw normalized recovery minus recovery from the component complement.
- [ ] **Joint-only gain:** joint score minus the better private component score.
- [ ] **Residual gain:** residual score minus the better private component score.
- [ ] **Counterfactual specificity:** primary = target-change minus matched-sentinel-change; descriptive ratio = target-change divided by `max(sentinel-change, delta_floor)` when eligible.
- [ ] **Causal specificity:** primary = target-task degradation minus largest non-target degradation; descriptive ratio uses the same locked-floor rule when eligible.
- [ ] **Reconstruction:** total and branch-only FVU, CE delta where applicable, and component energy shares.
- [ ] **Geometry:** principal-angle distributions, cross-projection energy, decoder Gram summaries, and explicitly named incoherence estimators.
- [ ] **Stability:** subspace similarity, canonical correlations, and permutation-aligned encoder/decoder feature overlap.

### 3.5 Provisional promotion criteria

These are planning defaults, not a post-hoc confirmation gate. M2 must lock exact thresholds, eligibility floors, undefined-task handling, and aggregation rules before confirmatory evaluation.

A family may enter architecture selection only if:
- [ ] its preregistered one-sided randomization-test p-value passes BH at `q <= 0.05`, **and** its separate two-sided hierarchical-bootstrap 95% effect-size CI is above zero; BH is applied to p-values, not to CIs;
- [ ] the directional result holds under every required holdout mode and the preregistered inferential unit for that evidence tier;
- [ ] assigned-family normalized recovery is provisionally `>=0.75` and exceeds leakage by `>=0.20` absolute, or a preregistered task-appropriate equivalent;
- [ ] at least one independent task/dataset not used to construct the subspace confirms the family;
- [ ] the effect is not explained by token identity, sequence length, source, class imbalance, or probe non-convergence.

A learned component may support the paper claim only if, in addition:
- [ ] it beats the calibration-frozen primary simple non-generative baseline on selectivity at matched applicable retention/collateral/reconstruction gates;
- [ ] its total FVU is within a preregistered non-inferiority margin of the matched K=1 baseline;
- [ ] causal/counterfactual specificity survives held-out templates or examples;
- [ ] stability and utilization gates pass.

Inferential units must not be conflated:
- [ ] **Raw atlas:** resample documents/templates/tasks/sources as appropriate; probe initialization refits are optimization checks, not independent model seeds.
- [ ] **Existing checkpoints:** report each checkpoint separately; the three regularized training seeds support development-level model variation, while the matched no-inc checkpoint is a causal regularizer control rather than a fourth regularized replicate.
- [ ] **New trained model:** require five independent training seeds for model-level generalization and a `4/5` directional stability rule where preregistered.

Executable multiplicity and resampling policy:
- [ ] The elementary G1 hypothesis is one preregistered `(Tier-1 family, candidate component/grouping, primary selectivity contrast, site)` tuple. The correction family contains every such L3 tuple opened for G1. Atlas-v1 L4 is descriptive and has no primary family; a later fallback policy would require a new prescore plan. Task variants are aggregated within their family rather than silently counted as independent hypotheses.
- [ ] The elementary G2 superiority hypothesis is one `(architecture-confirmed existing learned representation, calibration-frozen primary simple baseline, macro Tier-1 selectivity contrast, site)` tuple. These tuples form one G2 BH family. Retention, collateral-damage, stability, and applicable reconstruction requirements are simultaneous non-inferiority gates using a max-statistic hierarchical bootstrap across all representations/axes, not extra opportunities to select a favorable p-value.
- [ ] M8 registers four primary endpoint classes before unblinding: **legacy core** (the four original Paper-1 criteria), **family localization** (one signed component–Tier-1-family assignment each), **counterfactual specificity** (one effect per locked transformation family), and **causal specificity** (one effect per locked intervention family). The union of all elementary primary p-values in these classes is one global M8 BH family at `q <=0.05`; class labels are reporting strata, not four chances to correct separately.
- [ ] M8 claims are hierarchically gated even after global BH: counterfactual/causal specificity cannot support a family whose localization gate failed, and a learned-model advantage cannot survive a failed seed-stability/non-inferiority gate. Every primary test remains in the predeclared global family whether or not its upstream gate passes; there is no data-dependent removal or alpha recycling.
- [ ] Geometry summaries, unregistered task variants, secondary metrics, subgroup analyses, and extra interventions are descriptive/exploratory: report effects and uncertainty, but no p-value from them can pass G5 or rescue a failed primary endpoint.
- [ ] Discovery and calibration reduce the candidate ranks/groupings to the finite list in the preregistration. Adding a rank, grouping, metric, or family after confirmation opens requires an amendment and is exploratory, not a new member of the old correction family.
- [ ] Hierarchical resampling uses the highest independent unit first—source/dataset, then document/template/lemma as applicable—and refits the probe/subspace inside each resample. Tokens are never treated as independent replicates.
- [ ] For learned-model comparisons, training seed is the outermost unit. With five seeds, require the locked `4/5` directional rule and report all paired seed effects; nested document resampling may quantify within-seed task uncertainty but cannot increase the model-level sample size or rescue a failed seed-level result. If an exact seed-level test lacks resolution, describe directional replication and interval estimates rather than claiming p-value significance.

---

## 4. Candidate Information-Family Atlas

To control scope, families are tiered. Tier 1 determines the next architecture. Tier 2 supplies sentinels and may be promoted only by evidence. Tier 3 belongs to later papers unless needed to explain a Tier-1 failure.

### 4.1 Tier 1 — primary architecture-selection families

#### A. Absolute position
- [ ] exact/bucketed token index;
- [ ] distance to BOS and sequence tail;
- [ ] fractional/coarse position;
- [ ] prefix/suffix shift sensitivity.

#### B. Relative and structural position
- [ ] dependency-head direction and signed/bucketed distance;
- [ ] dependency/root depth;
- [ ] local order and repeated-token offset;
- [ ] distance to punctuation/boundary;
- [ ] span/BIO boundary role;
- [ ] clause/phrase boundary proximity where labels are reliable.

#### C. Lexical and semantic content
- [ ] token identity/frequency-controlled lexical bucket;
- [ ] lemma or lexical cluster where reliable;
- [ ] WNUT17 type-only NER;
- [ ] FewNERD coarse/entity-binary;
- [ ] WikiNeural entity-binary;
- [ ] entity/event substitutions in held-out templates.

### 4.2 Tier 2 — sentinels and candidate split refinements

#### D. Syntax and morphology
- [ ] POS and ambiguity-controlled POS;
- [ ] coarse dependency relation separated from head direction/distance;
- [ ] number, tense, person, and agreement;
- [ ] active/passive, dative, topicalization, and relative-clause contrasts;
- [ ] role-sensitive syntax tasks.

#### E. Surface, format, frequency, and domain
- [ ] token frequency and capitalization;
- [ ] punctuation/whitespace/code-vs-prose format;
- [ ] document source/domain;
- [ ] sequence/document boundaries;
- [ ] source-held-out controls preventing domain shortcuts.

### 4.3 Tier 3 — gated future families

#### F. Computational provenance
- [ ] attention-output vs MLP-output prediction;
- [ ] layer/site provenance;
- [ ] attention-pattern or circuit-role readouts.

#### G. Dense residual / “dark matter”
- [ ] residual linear predictability from current/earlier activations;
- [ ] singular spectrum and effective rank;
- [ ] learned dense branch vs frozen rank-matched PCA.

#### H. Multi-dimensional and hierarchical structure
- [ ] circular/time-like subspaces;
- [ ] subspace-valued atoms;
- [ ] hierarchy/absorption benchmarks;
- [ ] multiscale content structure.

### 4.4 Token-local versus relation-aware modes

- [ ] Run token-local tests first because they are closest to current MSAE training.
- [ ] Add pair/window/relation-aware features only when a preregistered token-local failure plus positive relational control justifies them.
- [ ] Never compare token-local and relation-aware performance as though input information were matched.

---

## 5. Data, Split, and Governance Plan

### 5.1 Discovery/confirmation firewall

The same labels, templates, or examples must not both define a component and confirm it.

- [ ] **Discovery set:** choose candidate task groupings, subspace ranks, and architecture family.
- [ ] **Calibration set:** estimate variance and lock numerical thresholds; do not report as confirmation.
- [ ] **Architecture-confirmation set:** fixed datasets/tasks/templates used once by M3/M4 to decide G1/G2; it may select the paper path but can never supply a headline final estimate.
- [ ] **Final test set:** a separately hashed blind partition opened once by M8 only after code, config, checkpoints, analyses, and claim-branch freeze.

Where a task family has only one dataset:
- [ ] split by document/source/template/lemma rather than random token alone;
- [ ] use task variants not used in subspace construction;
- [ ] report the single-dataset limitation explicitly.

### 5.2 Planned data sources

- [ ] Reuse final pre-K2 source mixture and OpenWebText holdout only with lineage recorded.
- [ ] UD English EWT for discovery syntax labels; select a different UD English treebank or held-out genre for confirmation.
- [ ] Keep WNUT17, FewNERD, and WikiNeural roles distinct; do not tune one family definition on all three and then call the same three confirmatory.
- [ ] Build a larger controlled-contrast set from BLiMP/SyntaxGym or a comparably documented source; keep hand-written templates as smoke tests only.
- [ ] Construct fixed semantic substitutions and positional shifts with human/automatic validation that the intended factor changed.
- [ ] Record tokenizer alignment, excluded BOS/EOS/padding, context truncation, class filtering, and label-collapse rules.

### 5.3 Shortcut controls

Every primary task must test relevant shortcuts:
- [ ] token identity and frequency;
- [ ] absolute index and sequence length;
- [ ] lexical overlap and named-entity surface form;
- [ ] document/source domain;
- [ ] label imbalance and majority baseline;
- [ ] template identity;
- [ ] parser/dataset-specific artifacts.

### 5.4 Reproducibility lock

Before confirmation:
- [ ] freeze data manifests and hashes;
- [ ] freeze activation-extraction commit/config and hidden-state indexing;
- [ ] freeze seed lists and batch/data order;
- [ ] freeze primary metrics and probe-selection metrics;
- [ ] freeze task-family aggregation and BH families;
- [ ] freeze failure/retry policy;
- [ ] create a versioned amendment for any later change.

Partition consumption is fixed:
- [ ] M2 constructs, quality-checks, hashes, and freezes distinct discovery, calibration, architecture-confirmation, and final-test manifests—including all counterfactual templates—before representation scoring.
- [ ] M3 may use discovery/calibration iteratively, then opens architecture-confirmation once for G1.
- [ ] M4 consumes the already-frozen architecture-confirmation transformations once for G2; it may not add, repair, or cherry-pick examples after seeing scores.
- [ ] M7 trains on training data and selects checkpoints/configurations on discovery/calibration validation only; it cannot inspect architecture-confirmation or final-test activations.
- [ ] M8 is the sole final-test opening. A scientific failure is a result, not a retry. A rerun is permitted only for a preregistered technical-invalidity condition, must retain the invalid output, use a signed amendment before unblinding the repair, and may not change examples, metrics, thresholds, or model choice.

---

## 6. Representations and Mandatory Comparators

### 6.1 Existing representations
- [x] raw activation `x`;
- [x] current K=2 `x_pos_priv`;
- [x] current K=2 `x_content_priv`;
- [x] private joint `[x_pos_priv, x_content_priv]`;
- [x] additive residual `x_resid = x - x_pos_priv - x_content_priv`.

### 6.2 No-new-training representations
- [ ] `S_abs`, `S_rel`, `S_struct`, and combined `S_posfam` from discovery probes;
- [ ] family subspace graph from principal angles, cross-prediction, and canonical correlations;
- [ ] projection residual `x - Proj_S(x)`;
- [ ] regression residual after predicting family labels;
- [ ] INLP/adversarial linear scrubbing baseline;
- [ ] low-rank bilinear readout for residual interactions;
- [ ] frozen PCA and random-subspace controls at matched rank.

### 6.3 Candidate learned models
- [ ] **K=1:** standard matched-parameter TopK/JumpReLU SAE.
- [ ] **K=2-original:** absolute-position-private + content-private.
- [ ] **K=2-posfam:** broad-position-family + de-positioned content.
- [ ] **K=3-pos:** absolute position + relative/structural position + content.
- [ ] **K=2 plus interaction readout:** frozen private branches with a small bilinear/shared readout.
- [ ] **K=3-private/shared:** position-private + content-private + shared/PCC.
- [ ] **Hierarchical content split:** coarse semantic/content + finer lexical/entity component, only if the content side remains reproducibly mixed after positional-family removal.
- [ ] **K=3-dense:** sparse + sparse + dense low-rank; gated to the dark-matter question.

### 6.4 Mandatory baselines for the next paper

Every branch requires:
- [ ] raw activation probe/reference;
- [ ] PCA/random/probe-projection baselines at matched rank;
- [ ] projection/regression/adversarial scrubbing baselines;
- [ ] matched-magnitude random-direction and inactive-branch/sham interventions for every causal edit;
- [ ] reconstruction- or CE-matched perturbation controls, with activation-scale/alignment checks; an off-manifold intervention that fails these checks cannot support a causal claim.

Every learned-model headline additionally requires:
- [ ] K=1 SAE at matched total parameter count, token budget, site, and effective sparsity;
- [ ] selected K-branch architecture with `lambda_inc=0`;
- [ ] capacity-matched selected architecture with the same branch widths/sparsity but shuffled or neutral branch assignment where applicable;
- [ ] corrected-loader fresh-from-zero training control if the artifact-readiness gate requires it;
- [ ] frozen PCA and added-sparse controls when evaluating a learned dense branch.

An existing-checkpoint/simple-baseline paper activates K=1/no-incoherence training controls only if its headline compares or causally attributes behavior to learned K=2; otherwise it must make no learned-model advantage/generalization claim. The negative-atlas branch records learned training controls as `not_applicable`.

---

## 7. Architecture Decision Tree and Stop Rules

### Gate G0 — Is the historical artifact base ready?
Proceed only if:
- [ ] authoritative checkpoints, configs, logs, summaries, and data lineage are locatable;
- [ ] stale absolute paths are repaired or mapped;
- [ ] the corrected loader is reproducible;
- [ ] dirty-code differences used by the 1B checkpoints are reconstructed and reviewed.

Otherwise:
- [ ] stop new science runs and repair provenance first.

### Gate G1 — Does a raw-activation family atlas replicate?

Apply the eligibility and inferential rules in §3.5, then use this exhaustive decision table (threshold changes require a preregistration amendment before M3 scoring):

| Architecture-confirmation outcome | Decision |
|---|---|
| No new family passes all §3.5 gates | retain the narrow existing K=2 question or take the negative-atlas path; no larger K |
| A matched-total-rank broad-position subspace gives every absolute and relative/structural subfamily recovery `>=0.75`, leakage `<=0.55`, and selectivity margin `>=0.20`, and the **upper one-sided 95% bound** on the split model's macro-selectivity advantage is `<0.05` | one broad position family; permit **K=2-posfam** |
| Separate absolute and relative/structural subspaces improve macro selectivity over matched-rank broad position with a **lower one-sided 95% bound** `>=0.05`, and each separately passes §3.5 with unique assigned-family advantage `>=0.05` | multiple positional families; permit **K=3-pos** |
| Any interval crossing the `0.05` material-benefit boundary, or other partial/conflicting/underpowered evidence | equivocal/no-decision; report the mixture, gather a preregistered independent dataset if feasible, and do not promote a larger architecture |

Residual and dense add-ons have independent gates:
- [ ] **Residual PCC/interaction:** after broad-position stripping, joint/bilinear normalized gain must be `>=0.05`, have a hierarchical 95% CI above zero, reproduce on at least two locked task/dataset variants, and show the same direction in every usable existing regularized checkpoint. A trained interaction claim later also requires `4/5` model seeds. Failure means no shared/PCC branch.
- [ ] **Dense residual eligibility:** a cross-fitted rank-`<=64` linear predictor must explain residual variance with `R^2 >=0.20` and a 95% CI above zero on at least two sources/tasks before a dense candidate may even be screened. If screened, a learned dense branch must later beat both matched-rank frozen PCA and an added sparse alternative by `>=0.02` on the preregistered reconstruction–selectivity objective before supporting a claim. Failure at either step keeps dense work in Tier 3 and off the next-paper critical path.

### Gate G2 — Do simple baselines already solve the problem?

Compare every existing learned representation permitted by G1 to the **single primary simple baseline selected and frozen on calibration in M2**; the other simple candidates are robustness results and cannot change G2. Apply the G2 BH and simultaneous-bound rules in §3.5. For each common metric, form the paired difference in the direction “learned is better.” The simple baseline **matches** only when the simultaneous upper one-sided 95% bounds are `<=0.05` normalized selectivity loss, `<=0.02` normalized assigned-family-retention loss, `<=0.02` normalized sentinel/LM collateral-damage penalty, and `<=0.05` stability loss.

Metric applicability is structural and frozen in M2: selectivity, assigned retention, collateral damage, and resampled stability are required for every activation-space transform. FVU is a gate only when both representations claim total activation reconstruction under the same definition; exact projection/complement and label-only/readout baselines mark it `not_applicable` and cannot pass or fail because of FVU. Every learned generative candidate must separately meet the §3.5 FVU margin against matched K=1 before an affirmative learned-model claim.

| G2 outcome | Decision |
|---|---|
| Simple baseline is within every applicable simultaneous margin | simple/existing-analysis path; no new learned model |
| Learned representation passes G2 BH, has selectivity-advantage lower simultaneous 95% bound `>=0.05`, remains within retention/collateral and any applicable reconstruction margins, and passes stability | learned-model path |
| Metrics conflict, CIs cross both equivalence and superiority bounds, or stability fails | equivocal/no-decision; narrow or negative paper, not a larger model |

The learned-superiority row is checked first, simple-match second, and all boundary/overlap cases go to equivocal/no-decision; analysts may not choose among conflicting metrics. For interpreting existing K=2, “low broad-position leakage” means maximum eligible positional-family leakage `<=0.25`; “substantial retained position” means `>0.25`. Residual PCC is plausible only if the separate G1 residual gate passes. Selectivity takes precedence over collateral/reconstruction only inside their locked bands; outside an applicable band the candidate fails.

### Gate G3 — Choose the smallest justified architecture

Promotion requires:
- [ ] at least two confirmable families;
- [ ] an explicit branch-to-family hypothesis;
- [ ] a reason the next-smaller K cannot represent the observed family geometry;
- [ ] a capacity-matched comparison plan;
- [ ] a falsifiable prediction for every added branch.

Preference order:
1. no new learned model if analysis baselines suffice;
2. revised K=2;
3. K=3 absolute/structural/content;
4. interaction-on-top;
5. trainable shared/private branch;
6. dense or structured branches only under their separate gates.

G3 signs exactly one completion branch:
1. **Learned-model branch:** execute activated M5–M10 work and train all learned headline comparators at the budgets/seeds specified in M7.
2. **Existing-checkpoint/simple-baseline branch:** freeze the winning existing/simple representation, skip new trainer/model training, and run the locked final atlas, scrubbing, counterfactual, causal-if-valid, stability, and case-study evaluation in M8–M10. Current resumed K=2 checkpoints remain exploratory unless a learned-model generalization claim activates five fresh corrected-loader seeds.
3. **Negative-atlas branch:** train no new model; confirm the null on an independent source/dataset and the final-test partition, report power/sensitivity and shortcut controls, and write a limits result. M6/M7 model work is not applicable.

### Gate G4 — Training promotion

At each budget, stop a variant for:
- [ ] persistent FVU regression outside the locked non-inferiority band;
- [ ] branch collapse, domination, or unhealthy utilization;
- [ ] no selectivity improvement over the strongest baseline;
- [ ] instability across required seeds;
- [ ] evidence that an added branch has no unique held-out role;
- [ ] compute/runtime failure that invalidates comparability.

### Gate G5 — Paper outcome

- **Advance with a positive decomposition claim:** all primary component gates and mandatory comparators pass.
- **Advance with a narrower positional-family claim:** broad position is supported but general family discovery is not.
- **Advance with a regularizer-dependent separation claim:** while the regularizer is active, separation is stable across preregistered tasks and at least `4/5` training seeds and all other component gates pass; warmdown disappearance is evidence of dependence, not evidence of validity by itself.
- **Advance with a negative/limits paper:** simple baselines match MSAE, cross-seed/task components are unstable, or no architecture passes causal/selectivity gates.
- **Do not begin Paper 2/3:** until this gate and its claims-to-evidence table are signed off.

---

## 8. Ordered Milestones From Now to Paper

Every activated milestone receives an owner and target date in `experiments/registry.csv`. This contract table is authoritative when prose below is ambiguous; a skipped conditional stage gets a signed `not_applicable` record rather than silently disappearing.

| Stage | Versioned inputs | Required outputs | Required baselines | Gate | Stop / no-go |
|---|---|---|---|---|---|
| M0 | repository, historical runs/bundles | registry, readiness and K2 comparison reports | manifests vs terminal artifacts | G0 provenance pass | missing lineage/checkpoints: repair before science |
| M1 | frozen PCC decisions/tables/scripts | reinterpretation and historical synthesis | A1 frozen path, amended path, matched `g4/g7` | signed interpretation | no training inference from M1 alone |
| M2 | label sources, split policy, M0 lineage | hashed four-way data/transform manifests and preregistration | chance/majority and shortcut manifests | every primary family measurable or limited | any final-test exposure or unfrozen gate: rebuild before scoring |
| M2b-min | metric code, planted fixtures | positive/negative regression report | shuffled/random assignment | recovery and null calibration pass | metric failure blocks M3 interpretation |
| M2b-full | activated dictionary-identifiability, dense, or theorem claim | phase/dense/theory artifacts | sparse-only, frozen PCA, random | claim-specific synthetic gate | skip for an ordinary learned separability claim |
| M3 | M2 manifests/preregistration, raw activations | raw atlas, geometry, G1 report | random/PCA/permuted/matched-rank | G1 table selects a path | equivocal means no larger K |
| M4 | frozen architecture-confirmation transforms, existing checkpoints | leakage/scrubbing/counterfactual tables, G2 report | raw, projection, scrubbing, random/sham | G2 table selects a path | no post-score transform changes; mixed result narrows claim |
| M5 | signed G1–G3 branch, M2 gates | architecture decision and training preregistration or `not_applicable` | next-smaller K and capacity plan if learned | G3 branch signed | no unjustified added branch |
| M6 | activated architecture/evaluation spec | tested trainer/evaluator commit or analysis-only validation report | exact synthetic fixtures/reference estimators | all activated checks pass | failed reproducibility/metric test blocks GPU work |
| M7 | frozen train/calibration manifests, configs, code and branch decision | registry rows, checkpoints, per-budget immutable promotion reports | activated learned comparators in §M7 | G4 at each budget | stopped variants recorded; no final-test access |
| M8 | frozen selected checkpoints/representations and blind final manifest | final functional/geometry tables and one opening record | branch-specific mandatory controls | all applicable final gates evaluated | scientific failure is final; only technical-invalidity retry policy applies |
| M9 | frozen M8 results and M2 inference spec | statistics tables and paper-gate report | null/sensitivity analyses | multiplicity/sensitivity audit pass | discrepant exploratory analysis cannot replace primary result |
| M10 | M5-signed case choice/frozen interventions and M8 final results | case figure/table | raw/simple, K1/no-inc when applicable, sham/matched edits | primary or fallback case completes | absent valid M5 choice blocks M8; later failure is reported |
| M11 | G5 decision and claims-to-evidence table | complete draft and figures/tables | strongest relevant alternative | every claim has evidence/failure condition | unsupported prose removed or weakened |
| M12 | paper, versioned scripts/configs/artifacts | reproducible frozen release/tag | independent claim/statistical review | all branch-specific DoD items pass | unresolved provenance or claim audit blocks submission |

## M0 — Historical freeze and artifact readiness

**Inputs:** current repository, pre-K2 bundle, K=2 outputs, PCC outputs.

Tasks:
- [x] Create `experiments/registry.csv` with run ID, stage, model, layer, data, budget, seed, config, commit, state, and evidence class.
- [x] Record the empty/log-only/superseded runs without converting them into scientific results.
- [x] Reconstruct and document the `1cef38e-dirty` training diff.
- [x] Restore or regenerate the missing fastdata-stream run manifest.
- [x] Replace or map obsolete `/jumbo/lisp/f004ndc/MSAE` paths.
- [x] Verify final checkpoint hashes and summaries.
- [x] Record environment, GPU, wall-clock, and data-source lineage.
- [x] Decide whether current 1B checkpoints may be confirmatory or are development-only.

Outputs (**COMPLETE**):
- `experiments/registry.csv`
- `reports/artifact_readiness.md`
- `reports/k2_postwave_comparison.md`

Gate:
- [x] G0 passes before new confirmatory work.

## M1 — Reinterpret the completed PCC evidence

Tasks:
- [x] Write `analysis/pcc_reinterpretation.md`.
- [x] Map each A0/A1/A1b/A1c/B-light/contrast task to absolute, relative/structural, content, surface/domain, or ambiguous load.
- [x] Explain why `syntax_dep_coarse` weakens under token matching.
- [x] Reanalyze `g7 > g4` as both shared-signal suppression and unallocated-position hypotheses.
- [x] Audit the 24-pair contrast script for pooling, token alignment, scale, and sign-only gates.
- [x] Record one of: broad-position favored, residual PCC favored, both plausible, or neither supported.

Outputs (**COMPLETE**):
- `analysis/pcc_reinterpretation.md`
- `reports/pcc_historical_synthesis.md`

Stop rule:
- [x] No PCC/shared-branch training is allowed from M1 alone.

## M2 — Label inventory, data manifest, and preregistration

Tasks:
- [x] Create the Tier-1/Tier-2 task inventory.
- [x] Assign disjoint discovery, calibration, architecture-confirmation, and final-test roles.
- [x] Define token-local and relation-aware variants separately.
- [x] Fix label collapsing and primary metric per task.
- [x] Define the elementary hypotheses, family aggregation, hierarchical resampling, BH correction families, effect-size CIs, and model-seed rule exactly as in §3.5.
- [x] Construct all positional/content/structure counterfactual templates and example manifests; run human/automatic validity, token-alignment, shortcut, scale, and duplication QA before any representation is scored.
- [x] Hash and blind the architecture-confirmation and final-test labels/transforms separately; record custodianship and the one-opening/retry policy.
- [x] Freeze the complete G1/G2 decision tables, including eligibility, broad-vs-split, equivalence/superiority, residual-PCC, dense-residual, mixed/equivocal precedence, and negative/no-decision outcomes.
- [x] Fit/tune the simple-baseline candidates on discovery and apply the frozen calibration rule. Because Tier-2 collateral was unavailable, record `baseline_selection_failed=true` and retain preregistered default `projection_broad16` as a comparator—not a validated winner—before architecture-confirmation.
- [x] Run code-only/data-loading smokes; do not inspect confirmatory results.
- [x] Use development variance to lock numerical gates.
- [x] Write and tag the preregistration before M3 confirmation.

Outputs (**COMPLETE**):
- `configs/atlas/task_manifest.yaml`
- `configs/atlas/transform_manifest.yaml`
- `configs/atlas/partition_hashes.json`
- `prereg/separable_information_atlas_v1.md`
- `analysis/label_inventory/`

Gate:
- [x] Every promoted primary family has at least one independent architecture-confirmation task; a family with only an explicit limitation may remain reported but cannot pass G1.

## M2b — Synthetic identifiability and metric sandbox

Purpose: validate the recovery logic and evaluation metrics on planted components before interpreting neural activations, without putting the full dense/theory program on every paper path.

Mandatory minimal metric smoke:
- [x] Use small planted sparse components with known positive, overlapping, absent-family, shuffled-assignment, and near-zero raw-over-chance cases.
- [x] Verify normalization/undefined handling, family assignment, leakage/selectivity, hierarchical resampling, multiplicity code, and permutation alignment.
- [x] Make these fixtures regression tests for every activated evaluation path.

Conditional full identifiability/dense/theory study—activate only for an explicit dictionary-identifiability, dense-residual, or theorem claim; an ordinary learned K=2/K=3 separability claim does **not** activate it:
- [ ] Generate `y = D_1* alpha_1* + D_2* alpha_2*` with known dictionaries at ambient dimensions `64,256,1024`.
- [ ] Sweep Bernoulli–Gaussian sparsities across predicted recoverable and non-recoverable regimes and vary cross-dictionary coherence.
- [ ] Add low-rank + sparse data only for the dense-residual branch.
- [ ] Measure support and dictionary/subspace recovery, reconstruction, leakage, and failure calibration.
- [ ] Overlay empirical recovery on an applicable sufficient bound or phase calculation, explicitly labeling assumptions.

Outputs:
- **COMPLETE (mandatory):** `reports/synthetic_metric_smoke.md` and executable regression fixtures
- Conditional full-study artifacts, only when activated:
  - `results/synthetic/phase_diagram.tsv`
  - `figures/synthetic/recovery_phase_diagram.*`
  - `figures/synthetic/lowrank_sparse_recovery.*`
  - `reports/synthetic_gate.md`

Gate:
- [x] The minimal smoke passes before M3 interpretation; failure blocks the atlas. Conditional full-study failures block only the activated dictionary-identifiability, dense-residual, or theorem claim.

## M3 — Raw-activation separability atlas

Tasks:
- [x] Fit standardized raw probes for all discovery families at L3 and L4.
- [x] Construct the preregistered split and broad projection subspaces; no CCA/PLS alternative was preregistered or opened.
- [ ] Sweep ranks with nested selection on discovery/calibration data only.
- [x] Compute normalized recovery, assigned-vs-nonassigned leakage/selectivity, and principal angles.
- [ ] Add the fuller complement-depletion matrix, cross-projection energy, and canonical-correlation analysis if the atlas is continued.
- [ ] Build a family graph/clustering using discovery data.
- [x] Freeze candidate grouping/rank from discovery/calibration before opening architecture-confirmation tasks once for G1.
- [ ] Evaluate IID, source holdout, corpus holdout, and task/dataset holdout on their locked partitions; do not access the final test.
- [x] Report L3 primary and L4 descriptive under the frozen fixed-layer policy.

Mandatory controls:
- [ ] random and PCA subspaces;
- [ ] task-label permutation;
- [x] matched rank/sample size;
- [ ] token/frequency/source shortcut probes;
- [x] probe convergence and calibration audit.

Outputs (**CURRENT RUN COMPLETE; fuller atlas remains planned**):
- `results/atlas/raw_v1/L3_raw_atlas.json`
- `results/atlas/raw_v1/L4_raw_atlas.json`
- `results/atlas/raw_v1/COMPLETE.json`
- `reports/raw_atlas_results.md`
- Planned extensions: tabular family/geometry exports, rank curves, and atlas heatmaps.

Gate:
- [x] G1 returned **equivocal/no-decision**: mandatory refit inference is unavailable; point positional selectivity is negative and cannot select broad or split.

## M4 — Existing K=2 leakage, scrubbing, and counterfactual audit

Tasks:
- [x] Evaluate `x`, `x_pos_priv`, `x_content_priv`, joint, and residual once on the M2-locked architecture-confirmation atlas; do not access the final test.
- [x] Measure absolute, relative, and structural leakage in `x_content_priv`.
- [x] Measure lexical/semantic leakage in `x_pos_priv`.
- [ ] Compare existing K=2 inferentially with the M2-frozen primary simple baseline; report projection, regression residualization, INLP/adversarial scrubbing, PCA, and random alternatives as locked robustness results that cannot replace the primary after scores are visible.
- [x] Consume the frozen positional shifts: neutral prefix/suffix, punctuation/format shifts, and controlled reordering.
- [x] Consume the frozen content changes: entity, event, and lexical substitutions under fixed structure.
- [x] Consume the frozen structure changes: active/passive, dative, attachment/relative-clause, and boundary changes.
- [x] Record every invalid example under the locked missingness rule; do not repair, replace, or add transformations after scores are visible.
- [ ] Use token alignment and token-level/readout-aware metrics; sentence means are secondary only.
- [ ] Test residual joint/bilinear gain after broad positional stripping.
- [x] Repeat matched-seed `g4` vs `g7` sensitivity.

Outputs (**CURRENT RUN COMPLETE; inferential extensions remain planned**):
- `results/atlas/k2_v1/k2_audit.json`
- `results/atlas/k2_v1/*_audit.json`
- `results/atlas/k2_v1/*_functional.json`
- `results/atlas/k2_v1/COMPLETE.json`
- `reports/k2_atlas_audit_results.md`

Gate:
- [x] G2 returned **equivocal/no-decision**. New training is not warranted now; residual PCC remains unsupported.

## Atlas-v1 execution status (2026-08-02)

- [x] Prescore bundle adversarially approved and frozen: `e7c12f4…c8c31`.
- [x] Raw L3/L4 calibration and C1 scoring completed; G1 = **equivocal**.
- [x] All four existing checkpoints transformed; 128 counterfactual and 192 CE rows/checkpoint completed.
- [x] Existing K=2/simple C2 audit completed; G2 = **equivocal**.
- [x] Architecture decision: **do not train now**. See `reports/architecture_decision.md`.
- [x] Implement and run the missing refit inference, Tier-2 collateral, stability, and matched random/sham specificity. All requested jobs executed, but the registered scientific gates remained invalid or incomplete; training remains unwarranted.

## M5 — Architecture decision and confirmatory training preregistration

All paths:
- [x] Record the interim **equivocal/no-decision** stop in `reports/architecture_decision.{md,json}` and authorize no training from the present evidence.
- [ ] After a new prescore independent-evidence plan yields a valid independent architecture-confirmation gate, sign exactly one G3 paper-completion branch before M8; the current stopped/invalid diagnostics are not a final-test branch selection.
- [ ] Select and freeze the IOI mechanistic case or its controlled relation/position fallback, including validity/failure rules; if neither is defensible, amend and re-review the PLAN before M8.

Learned-model path only:
- [ ] Specify branch widths, sparsities, activation types, initialization, branch permutation/alignment, and parameter/L0/token/compute-matched comparators.
- [ ] Lock any coherence penalty family/scope screen, the small-lambda calibration (default `1e-3` vs `1e-2` plus `lambda=0`), training-specific utilization/runtime/budget-promotion thresholds, and whether corrected-loader K=2 must be retrained from zero.
- [ ] For a regularizer claim, lock a paired warmdown/hysteresis protocol before training: planning default `50M` tokens, all five final seeds, zero-regularizer warmdown versus constant-regularizer continuation from the same selected checkpoint, with checkpoint and interpretation rules.

Existing/simple or negative path:
- [ ] Freeze the winning representation, fit procedure, resampling plan, comparators, and `not_applicable` record for training-specific M5/M6/M7 items.

Outputs (**PLANNED**):
- `prereg/next_paper_training_v1.md` (learned path) or signed `not_applicable` record
- `reports/architecture_decision.md`

Gate:
- [ ] G3 passes before implementing a larger architecture or launching long jobs.

## M6 — Trainer and evaluation implementation

Activate only the applicable path:

Common to every learned-model path:
- [ ] unit-norm decoder constraints/projected gradients, sparse-branch dead-latent handling, checkpoint/resume, exact data-order restoration, branch-permutation-aware evaluation, family recovery/leakage/counterfactual metrics, absorption diagnostics, and a deterministic tiny run.

Conditional implementation:
- [ ] generalized `K`-branch configuration and branch-specific width/sparsity/activation only if G3 selects `K>2` or heterogeneous branches;
- [ ] `inc_p`, `inc_scope`, or pair/branch weights with normalized logging only if M5 activates those penalty sweeps;
- [ ] dense rank/effective-rank logging only if the dense-residual gate passes;
- [ ] shared/bilinear evaluation or trainer code only if the residual-PCC gate passes.

Existing-checkpoint/simple-baseline or negative-atlas path:
- [ ] validate extraction, transforms, metrics, sham interventions, hashes, and deterministic reruns; record trainer additions and M7 as `not_applicable` unless a fresh learned-model claim is activated.

Required tests:
- [ ] **All paths:** metric smoke with known synthetic components, partition-hash enforcement, extraction reproducibility, and transform validity/sham checks.
- [ ] **Learned path:** reconstruction sum/shapes, TopK/sparsity invariants, incoherence against exact small Gram matrices, resume equivalence, and data-order/seed reproducibility.

Gate:
- [ ] all checks activated by the signed branch pass; learned-path checks pass before GPU screening.

## M7 — Staged training and comparator matrix

Activate M7 only for the learned-model branch or a fresh-existing-K2 generalization claim. Inputs common to every substage are the signed M5 preregistration, hashed training/discovery/calibration manifests, versioned code/config/environment, seed/data-order map, and comparator-allocation table. Architecture-confirmation and final-test data remain inaccessible. Simple non-generative baselines do not receive “training seeds”; they are fit/evaluated under their locked resampling protocol on the same validation/final examples.

### M7a Engineering smoke
- **Required comparators:** every runnable selected candidate, next-smaller K, K=1, no-incoherence, and activated neutral-assignment/dense/shared control; one engineering seed each at `1M–5M` tokens.
- **Output:** immutable `reports/training/m7a_smoke.md` plus registry rows/checkpoint hashes for every attempted job.
- **Gate:** memory, throughput, resume, data order, branch activity, and metric checks pass.
- **Stop:** engineering failure blocks that implementation; no scientific promotion is allowed from M7a.

### M7b Short screen
- **Required comparators:** selected architecture, next-smaller K, K=1, no-incoherence, and every activated assignment/capacity control at `25M`, two paired seeds each. If a regularizer is active, allocate the same paired seeds to `lambda=0` and the M5-locked small-lambda pair; additional penalty variants use those seeds only if M5 retained the sweep.
- **Tasks:** run the locked lambda calibration; screen `p in {1.5,1.75,2.0,3.0}` and then `cross/within/both` only when activated; apply locked collapse, utilization, FVU, and selectivity rules.
- **Output:** immutable `reports/training/m7b_25m_promotion.md` naming every promoted and stopped config, reason, config/checkpoint hashes, and compute used.
- **Gate/stop:** promote only configs passing all M5 rules on both seeds; stop and record collapsed, dominated, or noncompetitive variants.

### M7c Medium gate
- **Required comparators:** selected architecture, next-smaller K, K=1, no-incoherence, and each assignment/capacity control necessary for a planned headline comparison at `100M`, three paired seeds each; evaluate the M2-frozen primary simple baseline on the same locked validation data.
- **Output:** immutable `reports/training/m7c_100m_promotion.md`, complete per-seed tables, learning curves, registry/compute updates, and stopped-variant reasons.
- **Gate:** frozen validation selectivity, utilization, stability direction, and FVU/retention rules all pass.
- **Stop:** any learned comparator required to identify the source of the headline advantage must either promote or force that claim/selected model to be dropped; it cannot disappear from M7d.

### M7d Confirmatory run
- **Required comparators:** selected architecture, next-smaller K, K=1, no-incoherence, and every promoted assignment/capacity control needed for the headline, each from zero at `1B` with five paired seeds and the corrected data pipeline. Dropping a comparator drops the claim it identifies. Evaluate the M2-frozen primary simple baseline on the same frozen validation examples.
- **Execution:** use matched data order across learned comparisons, archive intermediate checkpoints for learning curves/warmdown, and select the final checkpoint by the preregistered calibration-only rule.
- **Output:** immutable `reports/training/m7d_1b_confirmation.md`, full checkpoint/config/data/environment hashes, five-seed tables, compute ledger, and signed freeze record authorizing M8.
- **Gate:** `4/5` direction, FVU/retention, utilization, and comparator-specific promotion criteria pass before the learned headline proceeds.
- **Stop:** failure selects a narrower/negative branch; never open final test to choose a replacement model.

### M7e Conditional scale extension
- **Inputs/activation:** the M7d report must show an M5-preregistered unresolved learning-curve condition or a paper question that truly requires up to `8B`; decide before M8 and without final-test access.
- **Required comparators:** every learned comparator necessary for the surviving 8B headline receives the same M5-locked budget and seed count; do not multiply irrelevant ablations.
- **Output:** immutable `reports/training/m7e_8b_decision.md` with allocation, results, stopped jobs, and replacement freeze record.
- **Gate/stop:** use the preregistered 8B criterion; a miss narrows the claim and cannot trigger a final-test-informed extension.

### M7f Regularizer warmdown/hysteresis control
- **Activation/inputs:** mandatory only for a regularizer-dependent learned headline, after M7d or activated M7e selects final checkpoints and before M8; no final-test access.
- **Required comparators:** for all five paired final seeds, continue the same checkpoint/data stream for the M5-locked budget (planning default `50M`) with the regularizer set to zero versus held constant.
- **Output:** immutable `reports/training/m7f_warmdown.md`, continuation checkpoint hashes, per-seed separation/FVU/utilization curves, and dependence-versus-suppression interpretation.
- **Gate/stop:** warmdown disappearance can establish dependence only if the active-regularizer result already passes stability/selectivity; inconsistent seed behavior or collateral suppression narrows the claim to negative/limits.

Gate:
- [ ] G4 at every budget; no “finish because compute already started” exception.

## M8 — Final functional evaluation

After G3 branch, representation/checkpoint, code, config, metric, and claim wording are frozen, open the blind final-test manifest exactly once. Learned-model claims run all five headline seeds and learned comparators; existing/simple and negative paths run their branch-specific representations and resampling units without inventing model seeds. Record the opening, hashes, operator, and any technical-invalidity event in `reports/final_test_opening.md`.

### Original Paper-1 core
- [ ] exact/bucketed position prediction;
- [ ] token-identity prediction;
- [ ] matched-token position invariance;
- [ ] branch-specific causal clamping on LM CE and position-dependent tasks.
- [ ] preregistered branch transplant/swap interventions when activation scale and alignment make them valid.
- [ ] matched-magnitude random, inactive-branch/sham, and reconstruction/CE-matched edits; failed scale/alignment checks invalidate the causal interpretation.

### Expanded family evaluation
- [ ] full confirmatory recovery/selectivity/leakage matrix;
- [ ] broad-position shift invariance;
- [ ] syntax/semantic controlled contrasts;
- [ ] residual PCC/bilinear test after positional stripping;
- [ ] domain/source holdout;
- [ ] relation-aware audit only if preregistered.

### Geometry, stability, and absorption
- [ ] every branch: task/dataset/source/bootstrap stability of the selected representation and family assignments;
- [ ] learned path: cross-seed subspace/CCA alignment and Paulo–Belrose Hungarian matching where atom-level comparison is meaningful;
- [ ] learned path: within/cross-branch overlap, usage entropy/Gini, active fractions, revival rates, and branch energy;
- [ ] regularized learned path: consume the frozen M7f warmdown/hysteresis report and test final functional evidence for specialization rather than suppression.

Gate:
- [ ] no headline result without every comparator and inferential unit required by its signed G3 branch; learned-model claims require all five seeds.
- [ ] no scientific miss, unfavorable effect, or surprising subgroup permits another final-test opening.

## M9 — Statistics, theory, and robustness

- [ ] Treat the training seed—not tokens or examples—as the unit for model-level uncertainty.
- [ ] Report per-seed points, mean/median, SD, effect size, and 95% CIs. When bootstrap is used, default to `10,000` nested resamples: source/document/template for raw/existing-task evidence, and training seed outermost with task units inside for learned-model evidence. With five model seeds, show all seed effects and treat `4/5` direction plus the simultaneous bounds—not extra inner resamples—as model-level support.
- [ ] Use paired comparisons when data order/seed is matched.
- [ ] Use document/template-level resampling for task datasets as appropriate.
- [ ] Apply BH only to the preregistered elementary-hypothesis p-values and correction families in §3.5; report hierarchical effect-size CIs separately and never call a BH-adjusted p-value an adjusted CI.
- [ ] Separate confirmatory p-values/CIs from exploratory analyses.
- [ ] Report probe convergence, max-iteration hits, selection metric, and calibration.
- [ ] Run threshold sensitivity without redefining the primary gate.
- [ ] Estimate empirical decoder geometry over training.
- [ ] Estimate descent-cone/statistical-dimension quantities only where the estimator is validated.
- [ ] Clearly distinguish sufficient theoretical bounds from empirical guarantees.
- [ ] Record negative and null outcomes in the same summary tables.

Outputs (**PLANNED**):
- `results/next_paper/summary.tsv`
- `results/next_paper/statistics.tsv`
- `reports/next_paper_gate.md`

## M10 — Mechanistic case study

Choose one case study after the architecture gate; do not select solely for a favorable result.

Primary candidate:
- [ ] IOI-compatible lower-layer analysis on Pythia-160M.
- [ ] Position-family and content intervention sets fixed before evaluation.
- [ ] Branch-specific logit-difference retention.
- [ ] Attribution concentration and cross-branch leakage.
- [ ] Compare the selected representation with raw/projection and sham/matched intervention controls; add K=1 and no-incoherence for a learned K-branch claim.

Fallback if IOI is technically mismatched at this site:
- [ ] complete a controlled relation/position task with a documented circuit and the same preregistered selection rule.

Outputs:
- [ ] one main figure and one table with quantitative intervention results.
- [ ] a signed pre-final-test case-selection record naming IOI or the fallback, its intervention validity checks, and failure criteria.

Gate:
- [ ] one of the two case-study paths must complete. If neither is technically defensible, amend `PLAN.md`, narrow the paper’s acceptance criteria/scope, and obtain review **before** final-test access; infeasibility discovered afterward cannot simply waive the deliverable.

## M11 — Paper writing and evidence assembly

### Claim selection
- [ ] Freeze the narrowest supported headline after G5.
- [ ] Prepare positive, narrow, regularizer-dependent, and negative-result framings before seeing final-test results.
- [ ] Create a claims-to-evidence table with exact artifact paths and failure conditions.

### Draft order
- [ ] Methods and preregistered analysis plan.
- [ ] Dataset/task and discovery-confirmation firewall.
- [ ] Raw separability atlas.
- [ ] Architecture decision and baselines.
- [ ] Training/reconstruction/utilization.
- [ ] Functional selectivity, leakage, and interventions.
- [ ] Stability and theory.
- [ ] Mechanistic case study.
- [ ] Limitations and negative results.
- [ ] Related work and discussion.
- [ ] Abstract/title last.

### Planned main figures
- [ ] family recovery/leakage atlas;
- [ ] architecture decision tree and selected model;
- [ ] reconstruction–selectivity Pareto plot;
- [ ] counterfactual/causal specificity;
- [ ] cross-seed stability;
- [ ] case-study intervention.

### Planned main tables
- [ ] task/data/split manifest;
- [ ] mandatory baseline comparison;
- [ ] component-by-family confirmatory matrix;
- [ ] ablation and warmdown summary;
- [ ] gate/claim outcomes.

## M12 — Paper and artifact freeze

- [ ] Regenerate every paper number/figure from a versioned script/config.
- [ ] Confirm all result paths resolve from the repository layout.
- [ ] Archive exact checkpoints used by the paper.
- [ ] Publish environment lock, data manifests, seeds, and hardware/runtime table.
- [ ] Run secret/license/data-release review.
- [ ] Run independent statistical and claim review.
- [ ] Run adversarial paper/diff review.
- [ ] Freeze final test outputs and claims-to-evidence table.
- [ ] Tag the paper artifact and only then decide whether Paper 2 begins.

---

## 9. Focused Ablation Policy

Ablations answer named threats; they are not an unconstrained grid.

### Mandatory for a learned-model headline
- [ ] `lambda_inc=0` matched control.
- [ ] the M5-locked small-lambda calibration (planning default `1e-3` vs `1e-2`, with `lambda=0`) at M7b.
- [ ] regularizer warmdown/hysteresis when a regularizer is active.
- [ ] selected architecture vs next-smaller K.
- [ ] K=1 matched-parameter SAE.
- [ ] M2-frozen primary projection/scrubbing baseline.
- [ ] selected width/sparsity allocation vs one plausible alternative.
- [ ] initialization control if the selected model uses probe-informed initialization.

For the existing/simple or negative branch, record these learned ablations as `not_applicable`; run only the observational, scrubbing, sham-intervention, sensitivity, and comparator checks needed by that branch.

### Conditional
- [ ] full `lambda_inc in {0,1e-4,1e-3,1e-2,1e-1}` only if the small calibration is non-monotonic or the optimum is unresolved.
- [ ] broad penalty-family/scope sweep only if quadratic cross-only remains a material bottleneck.
- [ ] dense-branch controls only if residual linear predictability passes its gate.
- [ ] relation-aware model only after token-local evidence justifies it.
- [ ] K greater than 3 only if a preregistered smaller-K failure predicts what the extra branch will capture.

For every ablation:
- [ ] state the threat it addresses;
- [ ] hold data, compute, capacity, and selection policy fixed where possible;
- [ ] predeclare promotion metric;
- [ ] report all attempted variants, including stopped/collapsed runs.

---

## 10. Engineering and Project Infrastructure

### Repository and configuration
- [ ] Add `configs/`, `analysis/`, `results/`, `figures/`, and `docs/` as needed; do not create empty trees without a milestone owner.
- [ ] Move run-defining CLI arguments into versioned configs.
- [ ] Add schema/version fields to every result artifact.
- [ ] Add an experiment registry and naming convention.
- [ ] Record commit/diff hash, config hash, data hash, environment hash, and checkpoint hash.

### Data and activations
- [ ] Version activation-extraction code and hidden-state indexing.
- [ ] Persist source mix, document IDs or stable lineage, shuffle seed, and bucket order.
- [ ] Exclude BOS/EOS/padding under a fixed rule.
- [ ] Keep confirmation activations isolated from discovery workflows.
- [ ] Measure activation cache size, throughput, and storage requirements before scale-up.

### Monitoring
- [x] Current trainer logs reconstruction, FVU, incoherence estimate, throughput, source mix, and utilization.
- [ ] Standardize total and branch-only FVU.
- [ ] Add normalized penalty logging across `p`/scope variants.
- [ ] Add branch energy, usage entropy/Gini, duplicate-feature, and suppression diagnostics.
- [ ] Add dense spectrum/effective rank only if a dense branch is selected.
- [ ] Add structured run completion markers and failure reasons.

### Runtime QA and compute governance
- [ ] Estimate GPU-hours and storage before each promotion.
- [ ] Maintain a compute ledger by run/config.
- [ ] Define wall-clock and throughput regression alarms.
- [ ] Preserve failed-run evidence without presenting it as completed science.
- [ ] Never start an 8B matrix without a signed 1B promotion report.

---

## 11. Risks and Mitigations

### Conceptual
- [ ] **Taxonomy lock-in:** task families may reflect our labels, not natural components. Mitigate with hypothesis language, held-out tasks, minimal K, and negative outcomes.
- [ ] **Decodability fallacy:** a probe can extract mixed information. Require leakage, depletion, reconstruction, stability, and intervention evidence.
- [ ] **“Pure content” impossibility:** meaning can depend on order. Claim only measured reduction in specified positional-family leakage.
- [ ] **PCC ambiguity:** shared gain can be unmodeled position. Strip broad position before naming PCC.
- [ ] **Orthogonality overclaim:** low geometric overlap does not imply functional independence. Report both separately.

### Experimental
- [ ] **Circular discovery:** never use the same task/examples to build and confirm a component.
- [ ] **Lexical/template shortcuts:** use matched controls and held-out templates/lemmas.
- [ ] **Parser/label noise:** replicate structural tasks across corpora or state the limitation.
- [ ] **Probe optimization artifacts:** align selection metric to headline metric and report convergence.
- [ ] **Multiple comparisons:** preregister families and use BH correction.
- [ ] **Seed pseudoreplication:** treat model seeds as the model-level unit.

### Modeling
- [ ] **Branch collapse/domination:** monitor energy/utilization and stop early.
- [ ] **Regularizer suppression:** matched-seed no-inc and warmdown controls are mandatory.
- [ ] **Capacity confound:** parameter/L0/compute match every architecture claim.
- [ ] **Unnecessary K:** require a unique held-out role for each added branch.
- [ ] **Dirty-resume confound:** decide and document whether fresh corrected-loader replication is required.

### Reporting and reproducibility
- [ ] **Historical revisionism:** preserve frozen and amended PCC paths separately.
- [ ] **Stale paths/untracked outputs:** repair/migrate and hash artifacts before the paper.
- [ ] **Selective reporting:** registry includes all launches and stop reasons.
- [ ] **Scope explosion:** Tier 1 decides the paper; Tier 2/3 are gated.

---

## 12. Paper Gate and Definition of Done

Common requirements for every branch:
- [ ] historical/artifact readiness is complete;
- [ ] discovery and confirmation are cleanly separated and preregistered;
- [ ] the mandatory minimal synthetic metric smoke passes; any activated full synthetic/dense/theory gate also passes or its claim is removed;
- [ ] the raw family atlas gate is complete;
- [ ] the existing K=2 leakage/scrubbing/counterfactual audit is complete;
- [ ] exactly one G3 completion branch and the narrowest G5 framing are signed before M8;
- [ ] the blind final test is opened once under the technical-invalidity policy and every applicable recovery, selectivity, leakage, stability, and intervention criterion is reported;
- [ ] one mechanistic case study is complete under the current PLAN; omission is allowed only if PLAN acceptance criteria and paper scope were formally narrowed and reviewed before final-test access;
- [ ] statistics, multiple comparisons, and sensitivity analyses are frozen;
- [ ] every claim maps to an artifact and every failed gate appears in the paper;
- [ ] code/config/data/checkpoint provenance is sufficient for independent rerun;
- [ ] the final title and abstract use the narrowest claim supported by G5.

Branch-specific requirements:

**Learned-model branch**
- [ ] five fresh corrected-loader training seeds and every learned comparator needed for the headline complete M7d at matched `1B` budget (plus M7e only if preregistered);
- [ ] matched K=1, no-incoherence, next-smaller-K, assignment/capacity controls, and the M2-frozen primary simple baseline are complete;
- [ ] FVU/retention, utilization, cross-seed stability, warmdown, suppression, absorption, causal/counterfactual, and `4/5` direction gates are reported and pass for any affirmative decomposition claim.

**Existing-checkpoint/simple-baseline branch**
- [ ] the winning representation is frozen and evaluated on the final atlas, scrubbing, counterfactual, valid causal, stability, and case-study suite with document/task/source resampling;
- [ ] every existing checkpoint is reported separately and simple baselines receive matched data/rank/retention controls;
- [ ] no five-seed or learned-model generalization claim is made unless that claim was separately activated and completed the learned-model requirements.

**Negative-atlas branch**
- [ ] the null/equivocal outcome replicates on at least one independent source/dataset and the blind final test;
- [ ] power, detectable-effect, threshold sensitivity, shortcut, probe-convergence, and calibration-frozen-primary-baseline analyses are complete;
- [ ] no new model training, K=1/no-incoherence training control, warmdown, or learned causal claim is required, and the paper explicitly limits conclusions to the measured families/sites/tasks.

---

## 13. Gated Follow-On Program

These items remain visible so the broader MSAE program is not lost, but all are blocked until the next-paper gate.

### Future Paper 2 — heterogeneous K-component MSAE

Precondition:
- [ ] next-paper gate reviewed and approved.

Planned scope:
- [ ] Gemma-2-2B layer 12;
- [ ] sparse TopK branch, JumpReLU branch, and rank-`<=64` dense branch;
- [ ] sparse-sparse and sparse-dense decorrelation;
- [ ] 500M-token SAEBench-compatible training, five seeds;
- [ ] attention-vs-MLP anchored supporting experiment;
- [ ] unsupervised/random-init K discovery with held-out interpretation;
- [ ] dense residual predictability and learned-vs-frozen-PCA control;
- [ ] full SAEBench across target L0 values;
- [ ] Kantamneni 113-task protocol and Quiver-of-Arrows test;
- [ ] K, lambda, heterogeneity, dense on/off, width, and encoder-tying ablations;
- [ ] bootstrap/BH gate report.

### Future Paper 3 — structured branches

Precondition:
- [ ] Future Paper 2 gate reviewed and approved.

Planned scope:
- [ ] subspace-valued atoms with group sparsity;
- [ ] multiscale/nested dictionaries;
- [ ] 50M-token, three-seed reduced-width feasibility gate before full training;
- [ ] Gemma-2-2B layer 12, 500M tokens, five seeds only after feasibility;
- [ ] Engels circular-feature validation and causal clamping;
- [ ] Chanin absorption benchmark at matched L0;
- [ ] atomic-norm/descent-dimension theory with theorem/heuristic boundary;
- [ ] modular-arithmetic and Bias-in-Bios/SHIFT-style case studies;
- [ ] final four-criterion gate.

---

## 14. Immediate Next Actions

Execute in this order:

1. [x] Complete M0 artifact readiness and reconstruct the dirty 1B training state.
2. [x] Write the PCC/positional-family reinterpretation memo, including the later small contrast no-go.
3. [x] Build the Tier-1/Tier-2 label and shortcut-risk inventory.
4. [x] Construct, QA, hash, and blind discovery, calibration, architecture-confirmation, and final-test task/counterfactual manifests.
5. [x] Draft and freeze `prereg/separable_information_atlas_v1.md`.
6. [x] Run the raw L3/L4 separability atlas; record that it was insufficient to decide whether positional signals form one or multiple families.
7. [x] Run existing K=2 leakage, scrubbing, and shift/counterfactual audits.
8. [x] Sign the equivocal/no-decision branch; no learned-model, existing/simple, or negative-atlas claim passed.
9. [x] Complete the five-analysis diagnostic obligation. The base root ran baseline/Tier-2 calibration and all 500 requested raw L3/L4 refits; the additive continuation ran all K2 refits, stability, and specificity jobs and dispositioned their invalid/stopped scientific endpoints without changing the frozen gates.
10. [x] Independently review, freeze, and run the additive diagnostic-only continuation and summary recovery. Preserve the original stop/root record, pair K2 IDs with the exact retained raw IDs, keep all scientific gates unchanged, and prohibit decision promotion/training.
11. [ ] **Immediate next research step:** draft and independently review a new prescore, independent-evidence plan that fixes document/source bootstrap class coverage using discovery/calibration only and evaluates once on a new architecture-confirmation source or dataset. Do not relax or rerun the frozen completion, use descriptive L4 as a fallback, or open the blind final partition.
12. [ ] After that independent gate, sign exactly one G3 completion branch and freeze the primary/fallback case study plus that branch's evaluation plan. Until then, record `equivocal_no_decision` and prohibit new training.
13. [ ] If the learned branch is active, run engineering, 25M, 100M, and 1B gates in sequence; otherwise record M7 as `not_applicable`.
14. [ ] Freeze representations/configs/claims, open the final test once, and complete branch-specific functional, causal, stability, and case-study evaluation.
15. [ ] Freeze the gate, claims-to-evidence table, paper, and reproducibility artifact before any later-paper training.
