# Preregistration — Separable-Information Atlas v1

**State:** prescore freeze candidate. It becomes immutable when `configs/atlas/freeze_record.json` is written and its digest is quoted by the independent adversarial reviewer. Neural C1/C2 scoring is forbidden before that record. Any later change is an explicitly signed amendment and makes affected analyses exploratory.

## 1. Question and evidence tier

This is an architecture-selection study on existing Pythia-160M layer-3/layer-4 activations and four resumed 1B-token K=2 checkpoints. It asks whether absolute position, relative/structural position, and lexical/semantic content form reproducible task-derived subspaces, whether one broad position subspace or two positional subspaces fit better, and whether the existing learned K=2 decomposition adds value over a frozen simple projection baseline.

It is not a final-test study, a natural-ontology claim, a causal proof, or a new-training run. C1/C2 evidence is architecture-confirmation evidence. Final is opened only in M8 after a later signed model/claim freeze.

## 2. Frozen data firewall

The executable sources, packing policy, model/tokenizer revision, source revisions, caps, and prefix vocabularies are in `configs/atlas/data_sources.json`. Realized file hashes are in `configs/atlas/partition_hashes.json`; counts, source hashes/fingerprints, exclusions, and QA are in `reports/atlas_data_qa.json` and `reports/atlas_label_counts.json`.

To keep activation storage/refitted probes feasible, `configs/atlas/analysis_sample_manifest.json` freezes a prescore, label-independent stable-hash sample: discovery 1,000 UD + 1,000 NER base sentences; calibration 500 + 500; all C1 and C2 base sentences. Every selected base retains all four offsets. Within a task, stable `(task,class,base,offset,row)` hashing caps discovery rows at 50,000 and calibration/C1/C2 at 20,000 after applying the already-frozen eligible label set; selection is class-stratified with equal per-class ceilings and unused capacity redistributed by the same hash order. The exact row IDs and per-file SHA-256 digests are materialized in `configs/atlas/task_row_manifest.json`; no runtime sampler is allowed. The exact caps/config are `configs/atlas/analysis_run.json`. These are analysis units, not a new split, and no activation or score informed them.

| Role | May do | Must not do |
|---|---|---|
| discovery | fit scaler, probe, task weights, SVD subspaces, vocabularies | report as confirmation |
| calibration | select ridge alpha, primary simple baseline, and locked rank tie; L4 fallback is disabled | fit the final probe/subspace or report as confirmation |
| C1 | evaluate raw G1 only | fit/select anything; evaluate K=2 G2 |
| C2 | evaluate existing K=2/simple G2 only | fit/select anything; evaluate raw G1 topology |
| final | M8 single opening only | any access/scoring in this work |

C1/C2 are **document-group-disjoint** halves within both LinES and WikiNeural. All sentences from a source document and all offset variants remain in one role. Canonical content hashes, base IDs, and document groups have zero role intersection. LinES provides only five C1 and four C2 document groups, so any structural-task interval that cannot support the frozen group-resampling design is underpowered/equivocal; token count cannot rescue it. `.atlas_final_unlock` is absent. A run requesting `final` must require the exact text `atlas-v1-M8-unlock` in that file and otherwise abort. The private final directory is Git-ignored and mode `0700` with files mode `0600`.

## 3. Representation site and packing

- Model: `EleutherAI/pythia-160m-deduped` at revision `582159a2dfe3e712a8d47ae83dec95ae3bde8e7e`.
- Primary site: block output layer index 3 using the same hidden-state convention as `resolve_hidden_state_index`; layer 4 is always extracted but is descriptive. Atlas-v1 has no data-selected layer fallback.
- Tokenizer: the same pinned model revision; fast word alignment; `add_special_tokens=false`; right padding; maximum length 128.
- Offsets `{0,16,32,48}` use a stable base-sentence-selected prefix word from a partition-disjoint vocabulary. Every prefix word is QA-verified as one model token.
- Absolute labels cover every nonpadding model token, including neutral prefixes and continuation pieces. Corpus word tasks use only first subwords. Prefix words, continuation pieces, invalid labels, incomplete/tail-truncated words, BOS/EOS, and padding are excluded from word tasks and counted.
- Explicit controls: offset, context length, prefix identity, word index, continuation status, capitalization, length, frequency, and source.

## 4. Tasks and families

The authoritative inventory is `analysis/label_inventory/task_inventory.tsv`; shortcut risks and failure actions are `analysis/label_inventory/shortcut_risks.tsv`. Pre-score eligible labels are the deterministic class-minimum intersection in `reports/atlas_label_counts.json`.

Tier-1 families and task aggregation:

1. **Absolute position:** `abs_pos_16` and `abs_pos_8`.
2. **Relative/structural position:** `relative_quartile`, `head_signed_distance`, `dependency_depth`, `boundary_state`.
3. **Lexical/semantic content:** `token_identity_256`, `lemma_identity_256`, `ner_coarse`.

Tier-2 sentinels are UPOS, coarse dependency relation, Number, capitalization, word length, discovery frequency bin, source, continuation status, and context offset. POS/deprel/Number cannot become a new primary family in this study. Relation-aware inputs are out of scope. Unknown labels are `__DROP__`, never fitted from confirmation.

For a task to enter normalized inference, it needs at least two frozen eligible labels and a bootstrap lower 95% bound on raw minus no-information score greater than `max(0.02, 2*bootstrap_SE)`. If not, normalized recovery is undefined and the preregistered family mean uses remaining tasks; a family with fewer than two eligible tasks is ineligible and forces an equivocal primary gate.

## 5. Probe, subspace, and calibration protocol

All probes are standardized ridge least-squares classifiers. Standardization is discovery-only. The alpha grid is `[0.1, 1, 10, 100]`. For each task and candidate representation, fit on discovery and select alpha by calibration macro-F1; ties within `0.005` select the larger alpha, then lexicographically smaller config ID. Refit once on all discovery rows at the frozen alpha. No C1/C2 row changes a scaler, alpha, vocabulary, class map, weight, subspace, representation mapping, or threshold.

Task subspaces are the right singular-vector spans of concatenated discovery standardized-probe coefficient rows. Primary matched-rank candidates are:

- `split_position`: absolute rank 8 plus relative/structural rank 8;
- `broad_position`: SVD of all absolute+relative/structural task weights at rank 16;
- `content`: lexical/semantic rank 8.

PCA rank 16 is the sole negative-control basis in atlas-v1. Higher-rank and Haar controls, canonical-correlation geometry, and cross-projection energy are not implemented and are removed from this frozen stage rather than silently promised. Geometry reports principal angles between the frozen rank-8 absolute and structural bases; geometry alone never promotes a family.

For each component/task, project discovery-standardized activations into the frozen basis, fit the component probe on discovery, and score without fitting on calibration/C1/C2. This separates representation construction from readout evaluation but remains supervised task-derived analysis.

## 6. Scores and denominator

Macro-F1 is primary. The no-information macro-F1 is the analytic expectation of predictions sampled from the discovery label prior against the evaluation label prior. Accuracy, discovery-majority macro-F1, and label-permutation distributions are unavailable in the atlas-v1 driver and are removed rather than silently promised; they cannot affect a decision. Majority would not be a valid normalized denominator because no-signal balanced predictions can exceed it.

For eligible task `t`, component `c`:

`R(c,t) = (F1(c,t) - F1(chance,t)) / (F1(raw,t) - F1(chance,t))`.

No epsilon or imputation is permitted. Fixed-probe diagnostics report unclipped value, numerator, denominator, and undefined reason. The mandatory refit interval is unavailable in this implementation; that missing interval forces the primary outcome to equivocal and is not replaced by the fixed-probe interval.

- assigned recovery: equal-weight mean over eligible tasks in the family;
- leakage: maximum equal-weight family recovery from a nonassigned Tier-1 component;
- selectivity margin: assigned recovery minus leakage;
- complement depletion: raw-normalized recovery minus complement recovery;
- joint-only gain: joint minus the better private representation;
- counterfactual specificity: target-change minus largest matched sentinel/sham change;
- collateral: degradation in frozen Tier-2 sentinel macro-F1 and suffix-LM CE increase;
- reconstruction: total/branch FVU only where the representation claims the same reconstruction target; otherwise `not_applicable`.

## 7. Simple-baseline selection

The finite simple candidates are:

1. `projection_broad16`: broad-position rank-16 projection plus orthogonal complement;
2. `projection_split8_8`: separate rank-8 absolute and rank-8 structural projections plus joint positional complement;
3. `pca16_complement`: discovery PCA rank-16 plus complement (negative/control candidate);
Each maps positional families to its positional projection(s) and content to the complement. On calibration, compute equal-weight macro Tier-1 selectivity subject to all three family assigned recoveries `>=0.65` where measurable and worst absolute Tier-2 sentinel macro-F1 degradation `<=0.10` versus raw. Select the highest selectivity. Ties within `0.01` use fewer fitted degrees of freedom, then lexicographic config ID. If no candidate passes, freeze `projection_broad16` as the comparison baseline but mark baseline selection failed, making G2 equivocal. Other candidates are robustness-only after selection.

The selected baseline ID, all calibration scores, alphas, and the L4 trigger are written to immutable per-layer `L{layer}_calibration_freeze.json` files plus `layer_trigger_freeze.json` before C1/C2 open. Calibration and confirmation are separate program invocations; confirmation aborts if any bundle digest or the trigger is absent/mismatched.

## 8. Inference and compute budget

The independent group is the source document (or a sentence only where the source supplies no document identifier), never a token or offset. All sentences from a document and all four offsets travel together. Within each of 500 hierarchical bootstrap draws, resample discovery groups and the relevant C1/C2 groups independently, preserving source strata; refit discovery scaler/probe/task subspace and reevaluate. Family aggregation equal-weights tasks, then source strata where a task spans sources. Percentile two-sided 95% intervals are effect-size intervals. A fixed-probe/group-resampling calculation is explicitly a diagnostic and cannot satisfy a G1/G2 inferential gate.

One-sided group sign/randomization tests use 9,999 draws and seed `20260731 + stable_hypothesis_index`; BH uses `q=0.05`. The worst-case binomial Monte Carlo SE at 9,999 draws is `0.0051 < 0.01`. The bootstrap count is 500; if a percentile boundary's estimated Monte Carlo uncertainty from a deterministic 100-draw-block jackknife exceeds `0.01` normalized units, increase to 1,000 before opening confirmation or declare that boundary underpowered. Never reduce draws. Cache keys are `(manifest_hash, resample, layer, representation, task)`.

For each simultaneous G2 vector, use the single-step centered max statistic implemented by `simultaneous_bounds`: for observed vector `theta` and bootstrap rows `theta*`, the lower radius is the 95th percentile of `max(theta-theta*)` and the upper radius is the 95th percentile of `max(theta*-theta)`; apply the resulting common radii to every coordinate. NaNs, fewer than 450 valid draws, or a nonfinite radius make the whole vector invalid. This is not a collection of marginal intervals.

Any CI endpoint within `0.01` of a decision boundary, failed convergence, fewer than two eligible family tasks, source/shortcut sign reversal, missing comparator, invalid hash, or conflicting primary axis is **equivocal**, not a pass or negative result.

### BH families

- G1 L3 contains four elementary hypotheses: assigned selectivity above zero for each of three Tier-1 families and split-minus-broad macro positional selectivity. Task variants are aggregated inside a hypothesis.
- L4 has no primary p-values. It is a descriptive site-sensitivity analysis and cannot rescue L3.
- G2 contains one superiority hypothesis per architecture-permitted regularized existing checkpoint (`g4`, `g5`, `g6`) against the single frozen simple baseline on macro Tier-1 selectivity. `g7` is a matched regularizer control outside the replicate family. Retention, collateral, stability, and applicable reconstruction are simultaneous max-statistic noninferiority gates, not extra selection opportunities.
- Geometry, individual task tests, g4/g7 sensitivity, and counterfactual family details are descriptive in this architecture-selection stage unless explicitly included in the simultaneous G2 collateral vector. Higher-rank diagnostics are not run in atlas-v1.

## 9. G1 raw-atlas decision

A Tier-1 family passes only if its one-sided p-value passes its G1 BH family, the two-sided 95% CI for selectivity is above zero, assigned recovery is `>=0.75`, leakage is `<=0.55`, selectivity is `>=0.20`, at least two tasks are eligible, source transfer has the same direction, and no mandatory shortcut audit explains/reverses it.

Then apply exactly:

- **Broad position:** both positional subfamilies pass under broad rank 16; each recovery `>=0.75`, leakage `<=0.55`, margin `>=0.20`; and the upper one-sided 95% bound on split-minus-broad macro positional selectivity is `<0.05`.
- **Split position:** separate absolute/structural rank-8 components each pass; the lower one-sided 95% bound on split-minus-broad selectivity is `>=0.05`; and each has unique assigned-family advantage `>=0.05`.
- **No expansion:** neither broad nor split satisfies those rows. This alone is not a supported negative result.
- **Equivocal:** any interval crosses/is within `0.01` of `0.05`, or evidence is partial, conflicting, underpowered, ineligible, or shortcut-sensitive. Equivocal has precedence.

L3 alone drives G1. L4 reports raw scores and geometry only and cannot rescue L3.

Residual PCC is not promoted unless broad-position-stripped joint/bilinear normalized gain is `>=0.05`, grouped 95% CI is above zero, two locked task variants reproduce, and all usable regularized checkpoints have the same direction. Failure means no PCC/shared branch. Dense residual is not activated in atlas-v1.

## 10. Fixed layer policy

L3 is the fixed primary layer and L4 is descriptive on identical examples. The intended hierarchical, source-stratified, discovery-refit estimator for a calibration-selected fallback is not implemented in atlas-v1; fixed-probe calibration intervals are diagnostics only. Therefore `layer_trigger_freeze.json` must record `l4_fallback_activated=false` before C1/C2 open. An unfavorable or ineligible L3 result is equivocal/no-expansion evidence and cannot be rescued by L4.

## 11. G2 existing K=2/simple audit

Checkpoints remain separate:

- regularized development variations: g4 seed42, g5 seed43, g6 seed44;
- matched-seed no-incoherence control: g7 seed42.

Representations are raw, position-private reconstruction, content-private reconstruction, concatenated private joint readout, additive residual, broad-position-scrubbed content, and the selected simple baseline. Frozen mapping: absolute and structural tasks are assigned to position-private; lexical/semantic tasks to content-private. No favorable remapping on C2.

C2 transform families contain 32 offset, lexical/entity, structural active/passive, and punctuation/format examples, arranged as four equal-weight template groups of eight independently instantiated source/target content pairs. Automated invariants must report zero violations and all 32 content pairs must be distinct within a family. Family effects first average within template group and then equally across the four groups. A sentence-level family estimate needs all four groups and at least 24 valid pairs. A token-level lexical/entity estimate needs at least 16 frozen token-aligned pairs; no other unaligned row may enter it. Every intervention has a seed-frozen matched-magnitude random direction and sham. Suffix LM CE uses the unchanged Pythia suffix logits after the intervention point and reports per-token paired CE; invalid alignment is excluded. Sentinel collateral is the maximum degradation across Tier-2 probes and CE. Simple projections have FVU `not_applicable`; learned generative representations report total and branch-only FVU.

Counterfactual specificity is normalized target sensitivity minus the larger of matched-random and sham sensitivity. It passes only if the lower grouped 95% bound is `>=0.05`, at least three of four template-group point effects have the same positive direction, and all family minimum-row rules above hold. The expected mapping is offset and active/passive to position-private, lexical/entity to content-private, and punctuation/format to neither private branch (sentinel/sham). Any alternate mapping, missing random/sham comparator, or equality/invariant failure is mandatory invalidity rather than an opportunity to relabel a branch.

Stability for g4/g5/g6 is the equal-weight mean pairwise centered linear CKA of each assigned branch on the exact frozen C2 task rows, after component permutation/sign alignment where a component basis is compared. The gate requires mean CKA `>=0.80`, every pair `>=0.70`, and the assigned-minus-nonassigned family selectivity direction to agree in all three checkpoints. Stability loss is `1-mean_CKA` and enters the simultaneous `<=0.05` equivalence vector where that stricter margin applies. g7 is a matched-seed regularizer control and is not counted as a replicate.

The simple baseline matches when simultaneous one-sided upper 95% bounds are `<=0.05` selectivity loss, `<=0.02` assigned-retention loss, `<=0.02` sentinel/LM collateral penalty, and `<=0.05` stability loss. Learned superiority is checked first and requires G2 BH, lower simultaneous selectivity advantage `>=0.05`, all retention/collateral/applicable reconstruction bounds inside margins, and stability. Low broad-position leakage is `<=0.25`; `>0.25` is substantial leakage.

If a requested CE/counterfactual estimator is technically invalid or lacks enough aligned C2 rows, it is missing mandatory evidence and G2 is equivocal; it is not silently dropped.

## 12. Exhaustive joint decision and training authorization

Precedence is top to bottom:

1. **Equivocal/no-decision:** any primary invalidity, ineligibility, underpower, boundary-near interval, missing mandatory G2 comparator/collateral, or conflicting axis. Do not train.
2. **Existing/simple:** the single simple baseline is simultaneously equivalent for at least two eligible Tier-1 families. Prefer the simpler representation; do not train.
3. **Existing-checkpoint:** G1 selects broad/split topology and every corresponding existing-K=2 localization, leakage, counterfactual, collateral, stability, and applicable reconstruction gate passes. Do not train a replacement; current checkpoints remain development evidence until any later final model-generalization claim meets fresh-seed requirements.
4. **Learned-model warranted:** G1 selects broad or split; existing K=2 fails the corresponding topology/family recovery or leakage gate; simple equivalence fails; all other mandatory G2 measurements are valid; and the failure yields a falsifiable new branch mapping. This authorizes a later training preregistration, not training in this work.
5. **Supported negative-atlas:** simultaneous upper 95% bounds for every proposed new-family selectivity effect are below `0.20`, simulated/design sensitivity is `>=80%` for a `0.20` effect, and G2 shows no learned new-family advantage. Sensitivity is frozen as 2,000 seed-20260731 simulations using the realized per-source document-group sizes and observed residual covariance, injecting an additive `0.20` family selectivity effect before rerunning the complete interval/gate calculation. It is the fraction of simulations whose lower simultaneous bound exceeds zero and whose point estimate exceeds `0.20`; `>=0.80` is required. If the realized four/five-group structural design fails this check, supported-negative is impossible. Then train no model and confirm the null only at the later final opening.

Non-rejection, G1 “no expansion,” or simple-baseline failure alone never yields supported negative-atlas.

## 13. Stop/retry and reporting

- Hash or firewall failure stops before extraction.
- Synthetic smoke failure stops neural scoring.
- OOM may reduce extraction batch size only; examples, order, precision, and metrics do not change. A retained failure log and resolved config are required.
- A technical-invalidity rerun retains the invalid output and requires a prescore amendment if examples/metrics change. A scientific failure is not retried.
- Every score-bearing run writes a terminal marker binding the prescore digest and upstream artifact/checkpoint digests. Neural extraction/transforms additionally record resolved device/batch/checkpoint config, model/data/code identities, environment/hardware, start/end, and output hashes. Raw/K=2 fixed-probe diagnostics record resolved analysis config, environment, start/end, and result hashes. A missing or mismatched marker is technical invalidity; these diagnostic manifests do not cure the separately declared missing refit/simultaneous inference.
- Report all checkpoints/tasks, undefined values, denominators, exclusions, controls, and negative/equivocal outcomes. Never describe task-derived families as an unsupervised ontology or joint decodability as causal sharing.
