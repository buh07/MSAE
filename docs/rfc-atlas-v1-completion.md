# PLAN — Atlas-v1 Inference and Control Completion

**Status:** approved for implementation after iterative independent adversarial review; final plan verdict `SHIP` on 2026-08-01. Score-bearing work still requires the separate M2 implementation freeze/review.

**Date:** 2026-08-01

**Parent artifacts:** `TODO.md` M3–M5, `prereg/separable_information_atlas_v1.md`, and frozen atlas-v1 digest `e7c12f4407249ccc556c8f56234c8de36af01d29a89de525deed7506876c8c31`.

## Goal

Complete the five missing measurements that currently force G1/G2 to equivocal:

1. 500-draw, discovery-refit, source/document-stratified inference;
2. Tier-2 sentinel collateral and a calibration-only amended simple-baseline selection attempt;
3. cross-checkpoint stability for the three regularized development checkpoints;
4. matched-random and sham representation-distance controls for the frozen C2 counterfactuals;
5. one deterministic amended G1a/G2a evaluation and planning decision that preserves original G1/G2 as equivocal.

The result must either select a branch under the already-frozen decision table or remain explicitly equivocal. “No expansion,” non-rejection, and unfavorable point estimates must not be relabeled as a supported negative.

## Non-goals

- Do not train or fine-tune a new SAE/MSAE/model.
- Do not open, hash-check by reading, extract, or score the blind final payload; `.atlas_final_unlock` must remain absent.
- Do not overwrite or mutate the original freeze, raw-v1 results, K2-v1 results, activation arrays, transforms, or checkpoints.
- Do not add ranks, layers, Tier-1 tasks, architectures, favorable branch mappings, or counterfactual examples.
- Do not claim causal specificity from representation distances or off-manifold CE edits.
- Do not treat a post-point-score completion as though its implementation had been frozen before the first C1/C2 point result.

## Constraints and evidence class

1. **Post-score amendment:** C1/C2 point results are already known. The completion will be frozen and adversarially reviewed before any new Tier-2, refit, stability, or sham score is calculated, but its outcome is `postscore_amended_architecture_evidence`. It may guide the smallest next branch under `TODO.md`; it is not a pristine replacement for the later blind M8 estimate. Every report must say this.
2. **Immutable parent and endpoint naming:** new files live under `configs/atlas_completion/`, `data/atlas_completion_v1/`, `results/atlas/completion_v1/`, a new ignored timestamped run root, and script/test names that do not match the original `atlas_freeze.bundle_files()` globs. Original fields/results remain `G1=equivocal`, `G2=equivocal`, and `architecture_decision=equivocal_no_decision`. New schemas use `G1a_postscore_amended`, `G2a_postscore_amended`, and `planning_decision_v2`; every marker/table carries `evidence_class=postscore_amended_architecture_evidence`. A pass may authorize planning only, pending independent/final evidence. `verify_freeze()` must pass before and after every stage.
3. **Create-once chain:** each score-bearing stage writes resolved config, seed, device/hardware/environment (including the launch-bound GPU UUID), absolute start/end time, upstream hashes, result hashes, and exactly one terminal marker defined below. Every point, draw/error, and shard carries this provenance; shard records and draw registrations are themselves hashed in the stage terminal. Existing terminal output causes refusal. A worker exclusively claims a draw with atomic `mkdir claims/<draw_id>` containing host/PID/start/config hash; an existing live claim blocks duplicate work. A stale claim may be quarantined only when its host/PID is confirmed absent and no completed output exists. Each deterministic draw chunk is written to a same-directory unique `.tmp.<pid>` file, flushed and `fsync`ed, then atomically renamed and hashed; the directory is `fsync`ed before the draw is registered. Resume verifies completed hashes, quarantines orphan temporaries under `invalid_partial/`, writes only absent draw IDs, and never replaces a completed chunk.
4. **Central input firewall:** every executable calls one common resolver before opening a file. A deterministic `upstream_inventory.json`, itself part of the reviewed additive freeze, binds every public activation COMPLETE/artifact, K2 transform COMPLETE/artifact/checkpoint, parent raw/K2 result terminal/artifact, functional result/terminal, parent freeze, and original architecture decision; runtime verification compares opened bytes to this inventory rather than trusting a mutually drifting parent terminal/artifact pair. The readable set is: exact files in the verified parent freeze bundle (including the two `final_checkpoint_*` provenance files); enumerated public-role paths under `configs/atlas/`, `data/atlas_v1/{analysis_rows,partitions,transforms}`; the four public activation roles under the parent run; parent raw/K2 result roots; exact digest-bound checkpoint files returned by `checkpoint_spec` (whose `final_step*` basenames refer to training termination, not the blind atlas final role); and additive config/manifest/run roots. Functional workers first resolve the configured model name plus exact revision to an already-present local Hugging Face snapshot with network disabled/`local_files_only=True`. Before model access they recursively enumerate every snapshot entry, resolve each expected `../../blobs/...` symlink, require its target to be a regular file inside that model repository's canonical `blobs/` directory, and register/digest the exact `(snapshot path,target path,sha256)` set; no other cache file or repo is admitted. The exact denylist is the canonical `data/atlas_v1/private/` tree, `.atlas_final_unlock`, any manifest role equal to `final`, and any symlink target outside an allowed root or the exact registered HF blob set; an unregistered absolute path is also denied. There is no ambiguous basename-wide `final*` rejection. Every terminal marker records the canonical path and SHA-256/parent terminal hash of every opened input; positive fixtures load the parent bundle, provenance, `final_step*` checkpoint, and local pinned LM snapshot through its blob symlinks, while negative fixtures monkeypatch file-open/hash/load calls and require blind-final refusal before access.
5. **Fixed scientific choices:** L3 is primary; L4 is descriptive. Ranks, mappings, alpha grids, labels, thresholds, BH families, 500/9,999 draw counts, source/task aggregation, and gate precedence remain those in the parent preregistration except where this amendment makes an originally underspecified estimator executable.
6. **GPU execution:** all score-bearing experiment commands run inside tmux on launch-time-free GPUs. Refit/statistics CUDA workers load activations as float32, disable TF32, and accumulate/solve the weighted ridge sufficient statistics in CUDA float64 before emitting float32 coefficients. The float64 accumulation was added after a second discovery/calibration-only pilot found float32 coefficient/projector relative errors of `0.00120`/`0.00172`, just above the prespecified `0.001` gates; no completion C1/C2 score had been read. Smoke checks establish numerical agreement with the exact sklearn ridge objective before full launch. The first pilot also found that the parent's iterative sklearn `solver='lsqr'` stops far enough from the exact solution to change 0.01–3.5% of near-tied labels on some tasks even though every absolute macro-F1 difference is `<0.001`. The amended refit estimator is therefore the exact weighted ridge solution. On every task, both unit-weight and one deterministic nonuniform integer document-bootstrap-weight fit must match sklearn `solver='cholesky'` with identical raw sample weights/intercept conventions at: `>=99.9%` predictions, absolute macro-F1 difference `<=0.001`, relative coefficient Frobenius error `<=0.001`, and relative calibration decision-function Frobenius error `<=0.001`. The literal integer-row-replicated sklearn fit must match the weighted sklearn fit to the same coefficient tolerance, proving weights are not normalized in a way that changes effective alpha. Family bases built from the full GPU/reference coefficient sets must have relative projector Frobenius error `<=0.001`. Parent-LSQR absolute macro-F1 differences remain a separately reported `<=0.001` compatibility diagnostic and never choose a branch. This amendment was made before completion C1/C2 scoring. The functional-specificity path is an explicit exception: it retains the parent LM `float16`, hidden-state indexing, and `MSAE(h.float())` casting order so existing actual rows are not redefined.

## Codebase and design grounding

- `scripts/run_raw_atlas.py:164-395` currently freezes alphas/bases and produces only fixed-probe group intervals; `:391-394` explicitly records missing refit inference.
- `scripts/run_raw_atlas.py:242-267` forces `baseline_selection_failed=true` because Tier-2 collateral is absent.
- `scripts/run_k2_atlas_audit.py:180-186` lists the three missing G2 evidence classes.
- `scripts/run_k2_functional_audit.py:198-201` invalidates counterfactual promotion because matched-random/sham representation controls are absent.
- `scripts/atlas_metrics.py:197-212` already defines the required 450-valid-draw simultaneous max-statistic bounds.
- Deterministic `/design` lookup returned no project-ledger entry for this completion. The local choices below are therefore explicit, reversible assumptions; they do not modify a public API or the original freeze.

## Brainstormed approaches

### Chosen: immutable completion extension with GPU weighted ridge refits

Represent group-bootstrap multiplicity as sample weights rather than physically duplicating rows. For each draw, refit the discovery scaler and fixed-alpha ridge probes, rebuild raw task-derived bases, refit component probes, and score source-stratified C1/C2 group resamples. Use deterministic draw IDs so raw/simple and K2 results pair exactly across independent GPU shards.

Why chosen: it implements the missing estimator, preserves group dependence, is shard/resume invariant, and makes 500 refits feasible on the available eight 48-GB GPUs.

### Rejected: fixed-probe bootstrap only

This is fast but is the exact diagnostic already declared insufficient. It cannot clear G1/G2.

### Rejected: mutate/rerun the original atlas-v1 outputs

This would destroy provenance and pretend the implementation was prescore. All completion artifacts must be additive and bind the parent hashes.

### Rejected: open the blind final partition for more power

M8 is the single final opening after a branch/claim freeze. Using it now would invalidate the firewall.

### Rejected: unreviewed new independent corpora

This would add data and label-policy choices beyond the user’s five requested completion items. If the amended evidence remains underpowered, a separately planned independent dataset is the next action rather than an improvised rescue.

## Frozen completion specification

### A. Data rows and Tier-2 eligibility

Build deterministic Tier-2 row manifests from the already-frozen public discovery/calibration/C1/C2 records and activation metadata. Do not rebuild parent Tier-1 rows.

Sentinels are exactly `upos`, `deprel_coarse`, `number`, `capitalization`, `word_length`, `frequency_bin`, `source_type`, `continuation_status`, and `context_offset`.

- Word sentinels use first subwords only and preserve existing `__DROP__`, prefix, continuation, and truncation exclusions.
- Word labels are copied byte-for-byte from `record["labels"][task]`; `source_type` means the existing `UD`/`NER` word label, while resampling source strata use the full `record["source"]` dataset ID. `continuation_status` maps activation codes `0/1/2` exactly to `prefix/first/continuation`, and `context_offset` maps the stored integers to canonical decimal strings. These two tasks use all model-token rows; all other sentinels use first subwords.
- Classes are the discovery/calibration intersection with minimum support in **both** roles: 50/class for UPOS and deprel; 100/class for all other sentinels. At least two classes are required.
- The numeric seed is exactly `20260731`. A row ID is the existing `variant_id:model_token_index`. Hash order is ascending SHA-256 of UTF-8 `seed\0role\0task\0class\0row_id`, with the row ID as final tie-break. Discovery is capped at 50,000 and calibration/C1/C2 at 20,000 rows using the same per-class floor and global hash-ordered remainder redistribution as Tier 1.
- Rows are serialized as one canonical JSON object per line (`sort_keys=true`, separators `(',',':')`, UTF-8, newline terminated); manifests and files use SHA-256 lowercase hex. The builder records exact row IDs, labels, full dataset source, source type, document group, class counts, SHA-256, duplicate checks, and parent base-ID membership. Duplicate row IDs, unknown continuation codes, absent record labels, or any final-role input are fatal. No C1/C2 value is used to choose classes, caps, or rows.
- Sentinel denominator eligibility is frozen on calibration before C2: at least two retained classes. Using the full-discovery fixed raw probe, run exactly 500 calibration document-group bootstrap draws, resampling within every fixed applicable dataset source with seed `(20260731 + stable_hash('sentinel_eligibility',task,0)) mod 2^63`. Each draw equal-weights the same frozen source strata. Define `SE` as the sample standard deviation (`ddof=1`) over the finite aggregate `F1_raw-F1_chance` values and LCB as their 2.5th percentile. Eligibility requires at least 450 finite draws and LCB `>max(0.02,2*SE)`. A missing required source/class or fewer than 450 finite draws makes the sentinel ineligible and baseline selection fail; up to 50 nonfinite draws are retained/reported and never replaced. In C2/refit draws, a nonpositive/nonfinite raw gap makes that coordinate invalid; fewer than 450 finite paired complete-case draws forces G2a equivocal.
- C1 sentinel rows are built only for completeness/diagnostics; baseline selection uses discovery/calibration and G2 collateral uses C2. They cannot affect G1 topology.

### B. Baseline selection and Tier-2 collateral

Run a calibration-only stage before refit confirmation:

1. Use the existing L3 raw calibration bundle and its three frozen candidates: broad-16, split-8+8, PCA-16. The split positional map is the existing SVD-orthonormalized rank-16 union `split_position_joint`, never two overlapping coordinate blocks.
2. Freeze this sentinel-to-component map before fitting: `continuation_status` and `context_offset` map to the candidate's rank-16 positional component because they directly encode packing/position; UPOS, deprel, Number, capitalization, word length, frequency, and source type map to its positional complement because they are the syntax/content/surface/domain collateral that a de-positioned content component is supposed to retain. K2 uses the same map (`pos` versus `content`). This is explicitly an **amended localization-sensitive collateral definition**, not parent complete-representation retention. It avoids the tautological invertible joint representation and the post-score best-of-components maximum; reports must preserve that distinction.
3. For every sentinel, fit a raw probe and the mapped candidate-component probe on discovery; select alpha on calibration with the existing `[0.1,1,10,100]`, `0.005` tie, larger-alpha rule. Raw and complement features use the same discovery global scaler; rank-16 coordinates use the same standardized activations and no second component-specific scaler.
4. Sentinel degradation is `raw macro-F1 - assigned-component macro-F1`. A candidate passes collateral only if every eligible sentinel degradation is `<=0.10`; unavailable/failed sentinel fits make it fail. The output also reports complete-representation round-trip error as a QA result, but complete-representation probe scores cannot select the candidate.
5. Apply predicates in this order: Tier-1 denominator eligibility, Tier-1 retention, then Tier-2 collateral. A candidate is admissible only when each of the three families has at least two calibration-frozen eligible Tier-1 tasks, its assigned recovery is finite and `>=0.65` in **every** family, **every one of the nine registered sentinels is denominator-eligible**, and every sentinel degradation is finite and `<=0.10`. An ineligible family/sentinel or missing recovery/sentinel score makes every candidate fail; it is never omitted from the quantifier. Among admissible candidates select highest calibration Tier-1 macro selectivity; ties within `0.01` apply the parent lower-fitted-rank rule to the candidate's two registered float32 linear feature operators (`B` and `I-BB^T`), using numerical rank at tolerance `max(shape)*eps_float32*largest_singular_value`, then lexicographic candidate ID. This is deliberately operator rank, not the rank of an unregistered prefix/subsample of realized rows. The fitted-rank totals are therefore identical (rank 16 positional and rank 752 complement for every candidate), so this rule normally and transparently falls through to lexicographic ID rather than pretending to discriminate. If none passes, retain `projection_broad16` with `baseline_selection_failed=true`, which forces G2a equivocal.
6. Freeze the selected candidate result and hashes before any completion worker may read C2.

For C2 G2a collateral, fit raw and the prespecified assigned-component probes on discovery at calibration-frozen alphas and report normalized damage

`D_t(rep) = (F1_raw(t)-F1_rep(t)) / (F1_raw(t)-F1_chance(t))`.

Simple assigned components and K2 assigned `pos`/`content` receive identical row, scaler-refit, alpha-selection, and source/group resampling treatment. Every simple candidate must pass a point and draw-level round-trip test: the SVD/QR-orthonormal rank-16 positional projection plus its exact complement reconstructs the standardized activation with maximum relative error `<=1e-5`. K2 suffix-CE reconstruction damage is separately normalized as `(CE_reconstruction-CE_raw)/CE_raw`. Simple CE damage is accepted as zero only after an identity-hook test reconstructs hidden activations and reproduces all frozen raw suffix CE rows within `1e-5`; failure makes simple collateral invalid. No branch-deletion CE value is used as collateral.

For CE, use only the frozen finite `ce_rows` for `k2_reconstruction` and `raw`; every one of the 96 text transforms must have exactly its source and target side. Per side compute `(CE_reconstruction-CE_raw)/CE_raw` (nonpositive raw CE is invalid), average the two sides within transform, eight transforms within each frozen template group, four groups within family, and the three families equally for the point. For each refit draw, use a separate deterministic counterfactual resample: sample the four template groups with replacement within each family, retain both sides/all transforms in a sampled group, and repeat the same aggregation. Its seed is `(20260731 + stable_hash('ce_collateral',draw,0)) mod 2^63`; the identical group maps are used for all checkpoints. This produces one paired CE-damage coordinate per checkpoint/draw and is not pseudoreplicated from tokens. Any missing/nonfinite row invalidates the coordinate.

### C. The 500-draw refit bootstrap

Draw IDs are exactly `0..499`. `stable_hash(stage,layer,draw)` is the unsigned integer from the first eight bytes of SHA-256 over UTF-8 `stage\0layer\0draw` in big-endian order; the NumPy seed is `(20260731 + stable_hash) mod 2^63`. For every role and draw:

Before reading C1/C2 completion scores, freeze **Tier-1 denominator eligibility** on calibration. Using each full-discovery fixed raw probe and its calibration-frozen alpha, run exactly 500 calibration document-group bootstrap draws, resampling within every fixed applicable dataset source. Use seed `(20260731 + stable_hash('tier1_eligibility',task,0)) mod 2^63`; score raw macro-F1 and analytic chance separately within source, then equal-weight the same fixed sources to obtain one raw-minus-chance gap per task/draw. Define `SE` as the finite-draw sample standard deviation (`ddof=1`) and LCB as the 2.5th percentile. A task is eligible only with at least two frozen labels, at least 450 finite draws, and `LCB > max(0.02,2*SE)`. Freeze the eligible-task set and every source before confirmation refits; no C1/C2 value or draw may add/drop a task. A family needs at least two frozen eligible tasks or its primary hypothesis is invalid/equivocal. Within a C1/C2 draw, a nonpositive/nonfinite raw gap in any fixed eligible task/source makes the complete registered draw row nonfinite; there is no epsilon or task deletion.

1. Within each frozen dataset source, sample its document groups with replacement, preserving the original number of groups. A group receives an integer multiplicity; all its sentences, offsets, and task rows share it.
2. The same discovery multiplicity map is used for every task/representation/checkpoint in that draw. C1 and C2 use separate role-specific maps, paired across representations.
3. Refit the global discovery scaler from the original seed-frozen 50,000-row scaler sample using discovery multiplicities. For K2, refit each existing representation scaler from its original deterministically recreated scaler sample.
4. At calibration-frozen alphas, refit raw probes, rebuild absolute/structural/content/broad/split/PCA bases where applicable, and refit component probes. Calibration is not resampled and alpha/baseline/rank are never reselected inside a draw.
5. Before scoring, freeze each task/role's complete applicable dataset-source list from the already-frozen task construction/row manifest—not from draw outcomes. Score macro-F1 separately by every applicable source. Compute normalized recovery within source, then use the fixed equal source weights within task and equal task weights within family. If any applicable source is undefined in a draw, the entire task/draw is nonfinite; sources are never dropped or reweighted draw-by-draw. A primary family needs at least two fully usable tasks.
6. Emit point and draw source-direction checks. A primary family is source-reversed/equivocal if any finite applicable-source point effect has a strictly opposite sign from the aggregate point effect (`source_effect * aggregate_effect < 0`); there is no materiality tolerance. Draw-level reversals are reported as diagnostics. A source cannot be hidden by the aggregate.
7. Refit K2 position/content and assigned-sentinel probes on the identical discovery draw and score the paired C2 draw. g4/g5/g6 are separate development variations; g7 remains the matched regularizer control.
8. Do not substitute failed draws. Record the reason. Simultaneous bounds use strict complete-case draw rows across the entire ordered vector: 500 requested IDs, at least 450 rows where **every** coordinate is finite, and no coordinate-wise deletion. Fewer forces equivocal.

Intervals are percentile two-sided 95% effect intervals (2.5th/97.5th percentiles). One-sided 95% lower/upper bounds are the 5th/95th percentiles and are reported separately. Simultaneous G2 bounds use the existing centered single-step max statistic across the complete registered vector.

The four G1a hypothesis IDs and point statistics are frozen as:

1. `g1a_family_absolute_min_topology`: `min(split_absolute_selectivity, broad_absolute_selectivity)`;
2. `g1a_family_structural_min_topology`: `min(split_structural_selectivity, broad_structural_selectivity)`;
3. `g1a_family_lexical_min_topology`: `min(split_complement_lexical_selectivity, broad_complement_lexical_selectivity)`;
4. `g1a_split_minus_broad_positional`: split positional macro-selectivity minus broad positional macro-selectivity.

The conservative minimum prevents one BH family p-value from being reused to promote a candidate on which that family fails. The first three one-sided alternatives are positive and also require their separate split and broad point/recovery/leakage thresholds. The fourth alternative is positive; split selection uses its 5th-percentile lower bound `>=0.05`, while broad selection uses its 95th-percentile upper bound `<0.05`. A bound within `0.01` of `0.05` is equivocal.

### D. One-sided tests and BH

The parent preregistration names group sign/randomization tests but does not make the nonlinear family statistic executable. Freeze this completion rule before scoring:

- Fit the full-discovery point models once. The randomization test is explicitly **conditional on that fitted discovery sample**; discovery uncertainty is separately represented by the paired discovery/C1 or discovery/C2 refit bootstrap.
- Primitive coordinates are recovery values for every separately named `(topology/checkpoint, assigned-or-specific-nonassigned-representation, task, source)` cell. The leakage maximum is **not** taken inside a task/source primitive. With `G_s` source-document clusters, delete cluster `c` from every primitive that uses it and form the source-stratified jackknife pseudovalue `p_jsc = G_s*theta_js(D_s) - (G_s-1)*theta_js(D_s\c)`. A physical `(source,document_group)` cluster receives one joint sign shared by every task/primitive in which it appears.
- For each primitive/source, `mean_c(p_jsc)` must reconstruct `theta_js(D_s)` within `0.01`; otherwise every dependent hypothesis is invalid. Every point, pseudo reconstruction, and randomized statistic uses the registered order: fixed-source mean within task, eligible-task mean for each assigned/nonassigned representation, maximum over the resulting named nonassigned-representation means, assigned minus that maximum, then topology minimum or learned-minus-simple macro difference as applicable.
- Each of the first three G1a family hypotheses is an explicit intersection-union test. For every topology and every separately named nonassigned representation, form the aggregate assigned-minus-that-specific-leakage contrast only **after** source and task aggregation. Apply the source-stratified sign test below to that contrast; the family p-value is the maximum component p-value across leakage representations and split/broad topologies. Its point statistic remains the identical minimum of those fully aggregated component contrasts. This conservative construction tests that assigned recovery exceeds every registered leakage and that every required topology passes, without exchanging mean-of-max for max-of-means.
- The fourth G1a hypothesis and every G2a checkpoint use a null-imposed source-stratified wild-pseudovalue test because each is a difference of selectivities containing separate nonlinear leakage maxima. Center each primitive pseudovalue within its fixed source to get residual `r_jsc`. For fourth-G1 let `theta_h` be split-minus-broad positional macro selectivity and subtract `theta_h` uniformly from every split assigned-recovery primitive in both positional families; this shifts the split positional macro by exactly `-theta_h`. For G2 let `theta_h` be fully aggregated learned-minus-simple macro selectivity and subtract `theta_h` uniformly from every learned assigned-recovery primitive; this shifts every learned family selectivity, and hence their macro mean, by exactly `-theta_h`. In each case leakage/comparator coordinates remain fixed and the complete recomputed null statistic must be zero to `1e-10`. For each joint cluster sign vector set each primitive/source draw mean to its null mean plus `mean_c(sign_sc*r_jsc)`, then recompute source means, task means, both sides' leakage maxima/family means/selectivities, and their difference. Compare this null distribution with the observed `theta_h`.
- These tests assume joint independent source-document pseudovalue vectors are sign-exchangeable within source. The first three G1 family tests use zero-null signs on each specific assigned-minus-leakage contrast; fourth-G1 and G2 use the explicitly null-imposed centered-residual construction above.
- It is not trusted with very small cluster counts: every required task/source stratum must have at least 10 contributing document groups and the aggregate hypothesis at least 20 nonzero physical clusters. The known 4/5-document LinES strata therefore make any dependent primary hypothesis underpowered/equivocal rather than spuriously precise.
- Draw exactly 9,999 joint sign vectors from NumPy PCG64 with seed `(20260731 + stable_hash('randomization', hypothesis_id, component_id)) mod 2^63`. The one-sided alternative is positive. A component Monte Carlo p-value is `(1 + count(T_perm>=T_obs))/(9,999+1)`; G1 takes the intersection-union maximum defined above and G2 uses its fully recomputed null distribution.
- G1 contains exactly the three family assigned-selectivity hypotheses and split-minus-broad positional macro selectivity. Apply BH at `q<=0.05` across these four.
- G2 superiority contains g4/g5/g6 learned-minus-simple macro Tier-1 selectivity. Apply BH across these three. g7 is descriptive.
- The bootstrap CIs/bounds and randomization p-values are separate gates; neither is described as a multiplicity-adjusted CI.

If any required leave-one primitive is undefined, pseudovalues are nonfinite, primitive or fully aggregated reconstruction fails, a fourth-G1/G2 null does not reconstruct zero, or the minimum-cluster rule fails, that hypothesis is invalid/equivocal rather than replaced with a bootstrap-tail p-value. Unit tests compare the implementation with direct source-stratified enumeration for planted grouped null/positive fixtures; include cases where the winning leakage component differs before versus after task/source aggregation, where the active topology changes, and where split/broad and learned/simple choose different leakage components. They verify reconstruction, intersection-union p-values, fourth-G1/G2 null imposition, and empirical Type-I rejection in `[0.02,0.08]` over at least 500 deterministic null fixtures at nominal `0.05`. Separate realized-design fixtures with 4/5 clusters must return the frozen underpowered/invalid status rather than a p-value.

### E. Cross-checkpoint stability

For g4/g5/g6 only:

- Compute centered linear CKA for each pair on each exact frozen C2 Tier-1 task-row matrix, first at the point sample and then under every paired C2 document/source multiplicity map for draw IDs `0..499`.
- For nonnegative integer row multiplicities `w`, normalize `q=w/sum(w)`, center `X` and `Y` by their `q`-weighted column means, set `Cxy=Xc.T@diag(q)@Yc`, `Cxx=Xc.T@diag(q)@Xc`, and `Cyy=Yc.T@diag(q)@Yc`, and define linear CKA as `||Cxy||_F^2 / sqrt(||Cxx||_F^2*||Cyy||_F^2)`. A zero/nonfinite denominator or fewer than two positive-weight rows is invalid. Tests require agreement within `1e-10` with literal integer row replication.
- Use ambient reconstructed branch activations, so no feature permutation/sign alignment is applied.
- Absolute/structural tasks use the position branch; lexical/semantic tasks use the content branch.
- Equal-weight task CKA within family, then equal-weight the three families. Report every task/family/pair value.
- Stability passes only if overall mean `>=0.80`, every checkpoint-pair overall mean `>=0.70`, and assigned-minus-nonassigned selectivity has the same direction in g4/g5/g6.
- g7 pairwise values are descriptive regularizer-sensitivity results and cannot increase replicate count.

The selected simple baseline also receives a non-degenerate **separate diagnostic** of refit reproducibility. For every draw ID, generate independent discovery group-bootstrap map A with seed stage string `simple_stability_A\0<layer>\0<draw>` and B with `simple_stability_B\0<layer>\0<draw>` under the §C SHA-256 rule, refit the simple task bases under both, and compute centered linear CKA between their assigned component maps on the same weighted C2 task rows. This bootstrap-fit variability is not comparable to K2 training-seed variability and therefore cannot enter a learned-minus-simple contrast or select a branch. The parent K2 stability gate remains an absolute, non-comparative requirement. Learned stability loss is `1-mean_pairwise_CKA_g4g5g6(draw)` and alone enters G2's simultaneous upper-bound vector. Simple A/B values are reported as diagnostics and technical-validity evidence only. Fixtures require identical independent fits to give CKA one and increasing planted rotations to worsen each estimator monotonically.

For memory safety, calculate linear CKA from centered cross-products in CUDA float64 accumulation chunks (or CPU float64 if CUDA float64 smoke is slower), never by constructing an `n x n` Gram matrix.

### F. Matched-random and sham specificity

Preserve the 128 frozen C2 transforms and mappings. Do not edit examples.

Preserve the existing actual estimator exactly: apply the checkpoint MSAE tokenwise to each source/target hidden-state sequence and then average raw/pos/content representations, as in `run_k2_functional_audit.py`. Position shifts use the same cached C2 token rows as the parent audit; other transforms use the same pinned model/revision and hidden-state index on GPU.

Recomputed actual distances must agree with every frozen parent `*_functional.json` row within `1e-6` absolute or the entire specificity extension is technically invalid. The parent value remains authoritative; the recomputation exists to prove the appended controls share its path.

- **Actual:** the unchanged parent tokenwise-then-average source/target representations.
- **Matched random:** create one deterministic ambient Gaussian direction per transform using NumPy PCG64 seed `(20260731 + stable_hash('matched_random',transform_id,0)) mod 2^63`, remove its projections onto both the actual raw sentence-mean delta and raw source mean, and normalize it. Scale it analytically so the raw cosine distance between the source mean and perturbed source mean equals the actual source-target raw cosine distance, then add that vector to **every source token**, apply the MSAE tokenwise, and average. If the two-vector orthogonalization is rank-deficient or the finite positive scale does not reproduce raw cosine distance within `1e-6`, the row is invalid. The control therefore matches the endpoint's raw displacement rather than an unrelated Euclidean norm. It cannot be borrowed from another target-bearing transform.
- **Sham:** independently recompute the full GPU forward path on the exact source token sequence and compare it with the original source representation; do not reuse the cached output. Raw or branch sham cosine distance above `1e-6` is technical invalidity.
- The seed and generated-direction SHA-256 are recorded per row. Absolute cosine with the actual delta and source mean must each be `<=1e-6`; actual-versus-control raw cosine-distance error must be `<=1e-6`. Zero/nonfinite norms or scale are invalid and retained.
- Use cosine distance, as in the parent functional audit. A row's actual, matched-random, and sham normalized branch sensitivities all use the **common actual source-target raw cosine distance**: `d_branch/d_raw_actual`. An actual raw distance `<1e-4` is invalid rather than epsilon-imputed. Sham raw/branch distances are separately checked against the technical threshold and do not supply a denominator. For position/structural families the assigned representation is position; for lexical/entity it is content.
- Row specificity is assigned normalized actual sensitivity minus the larger of assigned normalized matched-random and sham sensitivity. Nonassigned actual sensitivity is a separate mapping gate: assigned group-mean sensitivity must exceed nonassigned by `>=0.05` in at least three of four template groups.
- Average rows within each of four frozen template groups and groups equally. A family requires all four groups and at least 24 valid rows (lexical also requires at least 16 originally frozen `token_aligned=true` rows for its token-aligned secondary result).
- Lexical/entity has two mandatory estimators. The sentence estimator uses all valid rows and the sentence-mean matched-random control above. Before activation scoring, the token-control manifest tokenizes every frozen `token_aligned=true` source/target pair, requires the recomputed source and target `word_ids()` sequences to be exactly equal, and freezes the model-token positions whose common `word_id` belongs to a word index with `source_words[i] != target_words[i]`; hashes bind the input IDs, word IDs, designated positions, and tokenizer revision. A row needs at least one designated position. For every designated token, independently generate a Gaussian with seed `(20260731 + stable_hash('matched_random_token',transform_id,token_index)) mod 2^63`, remove its projections onto that token's actual raw source-target delta and raw source vector, normalize it, and scale it so the source-to-random raw cosine distance equals the actual source-target token cosine distance within `1e-6`; hash the direction/scale, perturb only that source token, and apply the MSAE tokenwise. Rank-deficient orthogonalization, zero/nonfinite scale or delta, actual raw cosine distance `<1e-4`, or mismatch invalidates the **entire row**, never just that token. Compute actual/random/sham branch distances with the common actual per-token raw denominator, average all designated tokens within a valid row, then rows/template groups equally. At least 16 fully valid aligned rows and all four groups are required; it must satisfy the same `>=0.05` lower-bound and 3/4-group mapping rule. No unaligned, unchanged-token, outcome-selected-token, or sentence-scale random direction may enter it.
- Bootstrap the four template groups with 500 draws using seed `(20260731 + stable_hash('specificity',job_family,0)) mod 2^63`; retain all rows within a sampled group and equal-weight groups. The specificity gate requires a lower 95% bound `>=0.05` and positive point specificity in at least three of four groups.
- Punctuation/format is a mandatory neither-branch sentinel. For each private branch, compute the same actual-minus-random/sham specificity; if either branch has lower 95% bound `>=0.05` **or** positive group means in three of four groups, the checkpoint's counterfactual mapping is invalid and G2 is equivocal. Any invariant, norm, row-count, denominator, or sham failure in a required family also invalidates that checkpoint's counterfactual gate.
- This remains representation-distance specificity only, not causal evidence.

### G. G2 simultaneous vectors and decision

Pair raw/simple and K2 draw IDs. Form **one global simultaneous vector** concatenating every registered coordinate below across g4/g5/g6 and the three Tier-1 families; g7 is reported in a separate descriptive vector and cannot loosen the primary radius. Coordinates are oriented as an advantage for learned K2:

1. `A_sel = selectivity_learned - selectivity_simple` for every job/family (margin `0.05`);
2. `A_ret = assigned_recovery_learned - assigned_recovery_simple` for every job/family (margin `0.02`);
3. `A_col = normalized_damage_simple - normalized_damage_learned` for every job/eligible-sentinel and reconstruction CE (margin `0.02`);
4. `L_stab = 1-mean_pairwise_CKA_g4g5g6` for each family (absolute upper margin `0.05`); this is not a learned-minus-simple contrast. Simple A/B CKA is descriptive because its replicate design is not comparable.

Apply one simultaneous max-statistic radius to the full vector. For a job/family, simple equivalence requires upper bounds `A_sel<=0.05`, `A_ret<=0.02`, `A_col<=0.02`, and `L_stab<=0.05` for every applicable collateral/stability coordinate. The existing/simple branch requires at least two equivalent families in **each** of g4/g5/g6; g7 is descriptive.

Learned superiority requires the relevant lower bounds `A_sel>=0.05`, `A_ret>=-0.02`, and `A_col>=-0.02`, plus the simultaneous upper `L_stab<=0.05`, G2 BH, the parent point stability gate, valid counterfactual specificity/mapping, and applicable reconstruction. No matched K=1 checkpoint/FVU artifact exists in the reviewed atlas. Therefore `learned_superiority_valid=false` and both learned-model and affirmative existing-checkpoint learned claims are forced equivocal in this completion; this missing comparator cannot block a simpler-baseline outcome. Boundary proximity (`<=0.01`), conflicting axes, failed baseline selection, or missing evidence has highest-precedence equivocal status. Every thresholded endpoint emits its absolute distance to the threshold and, when it has a registered 500-draw endpoint series, the delete-one-frozen-100-draw-block endpoint range. A fixed calibration or per-template-group point endpoint with no registered draw series emits an explicit `not_applicable` Monte Carlo status and rationale rather than inventing post-hoc resamples. Proximity alone disables the corresponding branch; when the block range is `>0.01` at such a boundary it is additionally labeled Monte-Carlo-underpowered and may not be repaired with extra postscore draws.

Reconstruction is `not_applicable` for the exact projection comparator; existing K2 FVU remains an independent learned-generative gate and is not compared as if the simple projection reconstructed through a decoder.

### H. Exhaustive joint decision and negative sensitivity

The renderer implements every parent-preregistration row as an amended planning endpoint with named machine inputs and precedence:

1. **Equivocal first:** invalid hashes, `<450` paired draws, invalid p-value/pseudovalue reconstruction, denominator/family ineligibility, boundary proximity, failed baseline selection, missing mandatory collateral/stability/specificity, or conflicting axes. In this scoped completion, the named `conflicting_primary_axes` predicate means at least one registered raw point source effect has the opposite sign from its aggregate effect; no unregistered qualitative conflict heuristic is applied.
2. **Existing/simple:** the global simultaneous vector establishes simple equivalence for at least two families in each regularized checkpoint. No topology or new training is claimed.
3. **Existing checkpoint:** requires G1 broad/split, every corresponding K2 localization/recovery/leakage, counterfactual, collateral, stability, and FVU-vs-K1 gate. It is unavailable here because matched K1 is absent.
4. **Learned model:** requires G1 topology, existing-K2 failure on that topology, failed simple equivalence, otherwise valid G2, a falsifiable mapping, and matched-K1 reconstruction evidence. It is unavailable here because matched K1 is absent.
5. **Supported negative:** uses six separate negative-gate effects—split and broad selectivity for each of absolute, structural, and lexical families—not the conservative BH minima. Every one must have a simultaneous upper bound below `0.20`, no learned new-family advantage, and frozen 2,000-simulation sensitivity `>=0.80`.

The negative sensitivity uses only group-effect summaries after the completion freeze. For each of the six negative-gate effects, take the centered delete-one full-statistic pseudovalue residual vector and realized source group counts. A delete-one value removes the physical C1 document group from every applicable task/representation leaf in that source, preserves the registered equal-source/equal-task and leakage-maximum aggregation, and must reconstruct both every source pseudomean and the registered six-coordinate point within `0.01`. The sensitivity calculation is independent of the Section-D randomization minimum-cluster rule: all realized source counts, including the known five-group LinES stratum, are used rather than declared undefined. For each of 2,000 simulations (a new PCG64 with seed `20260731 + simulation_id`), resample the six-coordinate residual cluster vectors within source with replacement and re-center each resampled source vector. Add an effect of exactly `0.20` at the full-statistic coordinate, which is algebraically the result of applying the same frozen source/task weights. Run the already-registered 500 C1 multinomial group-weight bootstrap maps through the complete six-coordinate simultaneous-bound calculation. Sensitivity is the fraction whose numerical point is `>=0.20` (tolerance `1e-12`) and lower simultaneous bound is `>0`. The implementation must reproduce planted independent Gaussian group simulations within `0.03` absolute power of a separate literal reference. Failure/undefined sensitivity for any coordinate makes supported-negative false, never true.

The renderer unit tests cover every row, missing-evidence branch, and precedence collision. It emits all predicate values even when an earlier row decides the outcome.

## Implementation layout

New additive files (names intentionally avoid the parent freeze globs):

- `configs/atlas_completion/analysis.json`
- `configs/atlas_completion/freeze_record.json`
- `prereg/atlas_completion_amendment_v1.md`
- `scripts/build_msae_completion_rows.py`
- `scripts/msa_completion_common.py`
- `scripts/calibrate_msae_completion.py`
- `scripts/run_msae_refit_worker.py`
- `scripts/merge_msae_refit.py`
- `scripts/run_msae_specificity.py`
- `scripts/run_msae_stability.py`
- `scripts/verify_msae_completion.py`
- `scripts/render_msae_completion_decision.py`
- `scripts/launch_msae_completion_tmux.sh`
- `scripts/msa_completion_cpu_runner.sh`
- `scripts/msa_completion_gpu_runner.sh`
- `tests/test_msae_completion.py`

Run artifacts:

- `pilot_runs/20260801_atlas_completion_v1/{baseline,raw_refit,k2_refit,specificity,stability,verification,logs}/`
- promoted immutable summaries under `results/atlas/completion_v1/`
- `reports/atlas_completion_results.md`
- `reports/planning_decision_v2.{md,json}` (original `architecture_decision.{md,json}` remains unchanged)
- adversarial transcripts under `reports/adversarial/`.

The decision renderer binds every upstream completion/stop marker, refuses absent/duplicate draw IDs, checks all hashes/finite values, verifies the parent freeze and absent final unlock, and emits the outcome without editing v1 results.

## Milestones

### M1 — Amendment, manifests, and tests

- Write the completion config/amendment and deterministic Tier-2/control manifests. Each row records its parent base ID; duplicate row IDs or absent parent-base membership are fatal and their zero-failure QA counts are serialized.
- Run a manifest-only eligibility/futility preflight before any score-bearing work. It must enumerate every fixed task/source group count and deterministically record that the 4/5-group LinES strata invalidate the dependent structural G1a randomization test. The present user request explicitly authorizes completing Tier-2, refit, stability, and specificity as diagnostic postscore-amended measurements despite that known joint-decision futility; therefore G2a still runs unless there is technical corruption, final-partition access, or a frozen resource-budget failure. The joint planning decision is nevertheless forced equivocal and no diagnostic can override that precedence.
- Implement common weighted statistics, weighted closed-form ridge, source/group sampler, CKA, pseudovalues, and decision helpers.
- Add unit tests for binary/multiclass ridge against sklearn, weighted-vs-replicated macro-F1/chance, source-stratified resampling, shard invariance, CKA reference, Gaussian matched-norm/orthogonality/sham, simultaneous margins, and final-role refusal.

**Acceptance:** repeat manifest builds, including their deterministic terminal record (which contains no wall-clock field), are byte-identical; no cross-role/final access; original `verify_freeze()` still passes; tests pass; every unit/nonuniform-weight prediction, absolute macro-F1, coefficient, decision-function, literal-replication, and derived-projector numerical gate in Constraint 6 passes, while parent-`lsqr` absolute macro-F1 compatibility remains `<=0.001`.

### M2 — Prescore implementation review and completion freeze

- Run CPU and one-GPU two-draw correctness smokes plus a 10-draw discovery/calibration-only throughput pilot without reading C1/C2 scores. The pilot must exercise the largest registered 768-D raw/complement ridge and every smaller assigned K2 fit; no unregistered 1,536-D joint representation is fitted. It also times shape-matched synthetic/calibration CKA cross-products and the full calibration-transform LM/MSAE actual/random/sham path, including token controls. Extrapolate every stage's wall time, total GPU-hours, peak GPU/host memory, scratch writes, and promoted output size.
- Record exact code/config/manifest/upstream hashes in the additive completion freeze, including the reviewed upstream trust-root inventory. The implementation review approves a candidate digest that excludes only its own transcript/record; the final bundle binds that candidate digest plus the transcript and a machine-readable `SHIP` record, avoiding a circular self-hash while preventing approval from being reused after any candidate edit.
- Run `/adversarial` on the implementation/amendment and revise until `SHIP`; quote the approved digest before score-bearing work.

**Acceptance:** reviewer returns `SHIP`; the extension verifier and parent verifier pass; no C1/C2 completion output exists before the approved freeze. Resource projections use twice the observed 10-draw mean runtime (plus measured fixed startup) before scaling to 500 draws and the actual number of shards. Under that `2x` safety factor, projected raw or K2 stage wall time must be `<=24h`, total allocation `<=192 GPU-hours`, peak host RAM `<=256 GiB`, and new storage `<=250 GiB`. Exceeding any budget deterministically writes `FROZEN_EQUIVOCAL_STOP.json` and stops before score access unless a redesigned plan is re-reviewed—never fewer draws or lower-dimensional unregistered fits.

### M3 — Calibration-only baseline selection

- Discover launch-time-free GPUs and run the create-once baseline calibration in a named tmux session.
- Freeze selection, alpha tables, Tier-2 collateral, hashes, and terminal marker.

**Acceptance:** all eligible sentinels are present or the baseline explicitly fails; no C1/C2/final role is read; selected baseline is immutable before M4.

### M4 — Raw L3/L4 500-draw refit inference

- Launch deterministic draw shards in tmux across available GPUs; L3 is primary, L4 descriptive.
- Resume only missing chunks; merge only after exactly 500 requested IDs and at least 450 finite IDs are present.
- Compute amended G1a intervals, sign/randomization p-values, BH, boundary/MC diagnostics, source-reversal gates, and raw/simple C2 paired draw artifacts.

**Acceptance:** shard-union and a re-run sample are byte/numerically identical; source/document resampling and discovery refits are logged; no fixed-probe interval is substituted; G1a is rendered from the frozen table while original G1 remains equivocal. A deterministic G1a invalidity does not silently skip M5: the authorized diagnostic continuation and its budget accounting are recorded.

### M5 — K2 refits, stability, and specificity

- Launch one K2 refit worker per checkpoint on available GPUs in tmux, consuming identical raw draw IDs.
- Concurrently run stability and four checkpoint-specific specificity workers on remaining/free GPUs; queue safely when fewer GPUs are free.
- Merge amended G2a only after all terminal hashes validate.

**Acceptance:** 500 paired draws/checkpoint with at least 450 finite; all Tier-2 sentinels, three regularized stability pairs, g7 descriptive comparison, 128 actual/random/sham rows per checkpoint, norm/sham checks, CE/FVU bindings, and simultaneous vectors are complete.

### M6 — Strict verification, decision, documentation, and claim review

- After merge, strictly parse every score-bearing JSON leaf, recursively reject non-finite numeric values, and deterministically replay family summaries, bounds, BH, stability, specificity, cross-tree gates, and the decision from terminal-bound leaf artifacts. This replay intentionally calls the frozen production estimators and therefore checks provenance, completeness, serialization, and reproducibility—not independent estimator correctness, which is covered by literal/reference unit fixtures. Freeze a verification marker bound to the promoted result hash.
- Render G1a/G2a and the exhaustive amended planning decision only after that verification marker is complete, without changing original G1/G2.
- Update `TODO.md`, `RESULTS.md`, and `ANALYSIS.md` with exact evidence class and next action.
- Run final deterministic verification, `/adversarial` diff review, and research claim review; revise until no blocker/revision remains.

**Acceptance:** one machine-readable and one narrative amended planning decision agree; every artifact says `postscore_amended_architecture_evidence`; no claim exceeds the gates; original decision remains equivocal; final remains locked; no new training process exists; reviewer returns `SHIP` for the scoped decision.

## tmux/GPU execution policy

For GPU scoring windows, `scripts/launch_msae_completion_tmux.sh` must:

1. query `nvidia-smi` at launch and select only GPUs with no compute process and `<1 GiB` used memory;
2. create session `msae_atlas_completion_20260801` and one logged window per job/shard;
3. set `CUDA_VISIBLE_DEVICES` per window and use `--device cuda:0` inside that namespace;
4. write the command, PID, prelaunch GPU UUID, config/freeze hash, and log path before execution; after CUDA initialization, the worker records the actual CUDA UUID/name and aborts on namespace/UUID drift;
5. never kill, preempt, or reuse another process’s GPU;
6. acquire an atomic per-GPU allocation directory under the run root, then immediately re-query GPU UUID/process/memory before launching each process; release the allocation only after its terminal status is durably written;
7. queued jobs re-run the allocation/query procedure when they actually start; a newly occupied GPU returns the job to the queue rather than colliding or failing the scientific run;
8. preserve failed logs and nonzero terminal status; no automatic scientific-parameter retry.
9. if the tmux session already exists, inspect its run-root/config/freeze ownership marker and refuse on any mismatch; on an exact match, add only deterministically named absent windows and never relaunch a window with a terminal marker. An extant allocation directory is reusable only after the stale-claim host/PID checks in Constraint 3; otherwise it remains blocking.

Merge, strict verification, and rendering are CPU-only tmux windows launched by the create-once CPU wrapper. They set an empty `CUDA_VISIBLE_DEVICES`, record CPU execution in their job manifests, and do not reserve an idle GPU or charge CPU wall time as GPU allocation.

The coordinator monitors `tmux list-windows`, logs, terminal markers, disk, and `nvidia-smi`; it does not infer completion from an absent process alone.

Every launched stage ends in exactly one mutually exclusive state. Concurrent publishers first create one common atomic `TERMINAL_STATE.json` selector and then materialize the selected conventional marker; a process finding a selector without its marker repairs that same bound payload, so a complete/failure race cannot publish both states:

- `MEASUREMENT_COMPLETE.json`: all requested outputs, draw counts, hashes, resource accounting, and the complete opened-input attestation are valid; or
- `FROZEN_EQUIVOCAL_STOP.json`: no completion marker exists, and the file records the frozen stop code, failed gate, requested/completed draw IDs, retained partial hashes, input attestation, and why no scientific retry or decision promotion is allowed.

The merger and renderer refuse a stage with both/neither marker. A frozen stop is rendered as mandatory missing/invalid evidence and cannot be called measurement-complete.
If an upstream frozen stop prevents a downstream stage from launching, the coordinator writes a root-level `NOT_LAUNCHED_UPSTREAM_STOP.json` naming every skipped stage and binding the upstream stop hash; no fake per-stage terminal marker is created.

## Verification plan

- `python -m pytest -q tests/test_msae_completion.py tests/test_atlas_metrics.py tests/test_atlas_data.py`
- `python scripts/qa_atlas_data.py` followed by parent `verify_freeze()`.
- completion manifest rebuild comparison and extension `verify` command.
- discovery/calibration-only GPU smoke, then the complete unit/nonuniform-weight sklearn-`cholesky`, raw-weight-vs-literal-replication, coefficient, decision-function, derived-projector, prediction, and absolute macro-F1 checks in Constraint 6; any failure stops before C1/C2.
- per-stage mutually exclusive complete/stop marker and opened-input-attestation validator.
- final strict JSON parse, recursive finite-number check, recomputation of family summaries, bounds, BH, stability, specificity, and decision from leaf artifacts.
- `scripts/check_msae_paths.py`, `python -m compileall -q scripts tests`, and `git diff --check`.
- confirm `.atlas_final_unlock` absent; search run manifests/results for role `final`; confirm no new training PID.

## Definition of done

- [ ] The parent frozen bundle still verifies byte-for-byte.
- [ ] Additive manifests/config/code are frozen and adversarially approved before score-bearing completion runs.
- [ ] The baseline is calibration-selected with all eligible Tier-2 collateral, or failure is explicit.
- [ ] L3 and descriptive L4 each have 500 requested discovery-refit draws and valid source/document-stratified inference or an explicit frozen inferential-invalidity/underpowered stop, including `<450` complete cases or a minimum-cluster/randomization failure.
- [ ] Every K2 checkpoint has 500 paired refit draws and g4/g5/g6 stability plus g7 descriptive sensitivity are reported, **or** the responsible stage has a valid frozen stop and every downstream skipped stage is named in the root upstream-stop record.
- [ ] Every frozen C2 transform has actual, raw-cosine-displacement-matched random, and sham representation distances with validity checks, **or** specificity has a valid frozen stop recorded as mandatory missing evidence.
- [ ] G1a/G2a and the amended planning decision are rendered only from frozen gates, with equivocal highest precedence and original G1/G2 unchanged.
- [ ] The blind final partition is unopened, no new model is trained, and no postscore-amended result is mislabeled pristine confirmation.
- [ ] Every launched stage has exactly one measurement-complete or frozen-equivocal-stop terminal state; a nonfinite required point forces the stop even when at least 450 draws are finite, and every point/draw/registration is bound to the frozen config hash. Every downstream stage skipped after an upstream stop has exactly one named entry in the root `NOT_LAUNCHED_UPSTREAM_STOP.json`; tests, manifests, hashes, centralized path/firewall checks, parent/extension verifiers, final adversarial review, and claim review pass.
- [ ] `TODO.md`, `RESULTS.md`, `ANALYSIS.md`, and v2 planning-decision artifacts agree on results, evidence class, and next branch/action.

## Risks and one-way doors

- **Post-score bias:** unavoidable for this completion. Mitigation is an additive amendment, prescore implementation freeze for all new endpoints, fixed old gates, no favorable remapping, explicit evidence class, and later M8 blindness.
- **Small structural group count:** may make intervals/pseudovalues unstable. Do not treat token count as replication or replace document groups; return equivocal.
- **GPU ridge numerical drift:** block full runs unless synthetic and discovery/calibration point comparisons meet tolerance with TF32 disabled. Numerical failure is not permission to add jitter silently; record invalidity or amend before C1/C2 execution.
- **Compute/time:** deterministic shards and chunks are resumable within the M2 budgets. Never reduce draws. Because C1/C2 have already been opened, if the frozen 500-draw/100-draw-block Monte Carlo check exceeds `0.01` at a decision boundary, declare that boundary underpowered/equivocal; this completion may not extend to 1,000 after seeing it. For an allowed 450–499-complete series, delete blocks by the original registered draw IDs `0–99`, ..., `400–499` and retain the remaining finite IDs; never compact the series and reinterpret block membership.
- **Counterfactual controls remain noncausal:** even Gaussian directions matched in raw cosine displacement and orthogonalized to the actual delta/source can be off manifold. They may clear representation-distance specificity only.
- **Decision is consequential but reversible:** `planning_decision_v2` is additive and cannot rewrite original equivocal G1/G2. Training remains prohibited unless the amended planning result, later independent evidence, and a separate training preregistration all authorize it.
