# Trained-Copy Controller Method Benchmark v1 — Technical Successor R2

## Goal

Preserve the completed capacity/external-validity R5 result, add its scoped claims and an
analysis-only figure package to the paper, and then run a separately versioned benchmark asking
which registered methods can retain the complete controller of the already-trained synthetic copy
transformers. The benchmark must keep exact ground truth as the positive-control skyline, use fresh
row panels, evaluate joint potency/specificity/safety, and stop before any more realistic bridge or
natural-model experiment. It must not retrain R5, train K2, or infer anything about pretrained or
natural-language transformers.

## Non-goals and prohibited claims

- Do not modify, rerun, retune, or append to either R5 result namespace.
- Do not restore the failed v1 execution or reuse its partial checkpoints.
- Do not train a new copy transformer; the three completed R5 checkpoints are immutable study
  objects and are imported by exact hash.
- Do not call the method benchmark natural-language, pretrained-model, cross-family, or SAE
  generalization evidence.
- Do not describe per-target rank as capacity-equivalent to global rank; report parameter counts,
  per-target ranks, and union ranks.
- Do not claim capacity alone explains R5. The scoped result is that global paired rank 4/8 failed,
  global paired rank 16+ passed, and full-rank unpaired controls still failed.
- Do not launch the next residual/multi-head realism bridge in this protocol.

## Grounded codebase and design findings

`/query-codebase` found that `CopyTransformer`, `train_copy`, and `score_copy_model` are defined in
`scripts/capacity_external_validity_v1_r5.py`; R5 is their only completed R5 execution path. The
earlier method machinery (`TopKSAE`, paired low-rank control, feature transplantation, common causal
scoring) is defined in `scripts/transformer_realistic_bridge_v1_r2.py`. No active design-ledger entry
governs this study. Therefore this plan treats the R5 model/checkpoint contract and the already
frozen joint gates as canonical, while creating a new experiment namespace rather than editing R5.

## Scientific question and representational object

The study asks:

> Given a clean/corrupt counterfactual pair at a known complete `head_pre_ln` causal bottleneck,
> which train-only component-selection or compression methods retain enough of the held-out donor
> delta to provide recovery, signed-sham specificity, matched-control separation, necessity,
> full-vocabulary restoration, and collateral safety?

Donor-compression methods receive the same counterfactual donor object at inference: the clean-minus-
corrupt `head_pre_ln` delta for the row (or the corresponding sham-minus-corrupt delta). This is a
component-disjoint counterfactual-controller approximation/selection benchmark. It is **not**
single-example controller prediction from a corrupt state and is not evidence that a method can
discover the counterfactual without a donor. The exact identity controller is a nondeployable
skyline. Task-aware, label-mean/no-donor, and negative-control methods have separately serialized
inference contracts and may not be pooled with donor-compression methods as though information were
equal.

The insertion path, row cohort, target/contrast definition, LayerNorm/readout behavior, necessity
operation, sham construction, random same-norm control, collateral metric, full-vocabulary metric,
bootstrap, and thresholds remain identical to R5. Native and rowwise true-delta-norm-matched
estimands are co-primary; every family claim requires both.

## Imported trained models and fresh panels

- Import the three R5 model checkpoints for seeds `5101`, `5102`, and `5103` by exact SHA-256.
- Reconstruct the exact R5 architecture/config and require exact checkpoint/config lineage before
  any panel access.
- Generate one fresh label-only controller-fit panel and disjoint development/confirmation panels
  using new frozen seeds. Use 64 blocks x 32 rows for fit and 32 blocks x 8 rows for each evaluation
  panel. Row IDs, row seeds, and panel seeds must be disjoint from all R5 external panels.
- Make controller types prospectively component-disjoint, not merely row-ID-disjoint. Partition the
  nonzero modular target-to-contrast offsets as fit `{1,...,21}`, development `{22,...,26}`, and
  confirmation `{27,...,31}`. Every row has a unique `(query,target,contrast)` tuple within its panel;
  query is fully crossed with target, so each of the 256 evaluation target-query pairs appears once,
  every target appears eight times, and every query appears 32 times. Choose each sham from the full
  non-target, non-contrast vocabulary by a frozen deterministic tuple-disjoint rule;
  require exact zero overlap across panels for both `(query,target,contrast)` and
  `(query,contrast,sham)`. Hash and freeze each tuple inventory.
- Preserve target, contrast, sham, value, query, and controller-type-block counterbalancing. Each
  evaluation row is a unique controller type and blocks are prespecified clusters of eight distinct
  types. Apply R5 model-eligibility and row-support gates unchanged; additionally report unique tuple
  counts, maximum rows per tuple, and per-block tuple counts.
- Development and confirmation are created and hash-frozen before checkpoint loading. Confirmation
  remains unopened until all three exact **and identity** controllers pass development support,
  routing QA, and every joint gate; every registered fit/seed checkpoint exists by exact hash; and
  every method has a finite, schema-complete development record under both registered estimands (or
  an explicit structural `not_applicable` for the zero matched control). Seal these facts and the
  immutable method inventory in a fsynced pre-confirmation manifest before authorization. Estimated-
  method scientific gate outcomes may not affect confirmation authorization.
- Once exact/identity development authorizes confirmation, score every registered method on confirmation;
  do not selectively omit failed development methods.

## Registered methods and information access

Fit each method independently for each fixed R5 model seed. All fitting uses only the new fit panel.
Method seeds are frozen and every seed is retained.

1. **`exact_head_delta`**: insert the true rowwise head delta. Evaluator positive control.
2. **`identity_full64`**: fixed identity mapping of the donor delta. Technical parity skyline.
3. **`output_oracle_rank{k}`**, `k in [4,8,16,32,64]`: project held-out donor deltas onto the top-k
   sign-canonicalized right-singular subspace of fit-panel true deltas. This is the train-L2-optimal
   output-subspace approximation and uses paired deltas during fitting; it is not behavior-optimal.
4. **`paired_linear_rank{k}`**, the same ranks: three seeded factorized global maps trained to
   reconstruct the paired head delta for 1,500 fixed Adam steps.
5. **`target_linear_rank{k}`**, `k in [4,8,16,32]`: three target-indexed factorized maps, with
   per-target and union ranks reported.
6. **`target_nonlinear_rank{k}`**, `k in [4,8,16,32]`: three target-conditioned two-layer GELU
   encoder/decoder maps with empirical Jacobian rank reported for every target.
7. **`ambient_pca_rank{k}`**, global ranks `[4,8,16,32,64]`: fit PCA only to the union of fit-panel
   clean/corrupt/sham head states; predict a controller as reconstructed donor state minus
   reconstructed corrupt state. It receives no paired delta target.
8. **`random_rank{k}`**, the same global ranks: seeded orthogonal projectors applied to donor deltas.
9. **`readout_task_projection`**: per row, project the donor delta onto the frozen span of the model's
   target and contrast readout vectors. This uses model/task weights but no outcome-fitted subspace.
10. **`target_mean_delta`**: target-indexed fit-panel mean delta, used unchanged for actual and sham;
    this is a DiffMean/label-only shortcut control.
11. **`topk_sae_unpaired_selector`** and **`topk_sae_paired_selector`**: share three seeded TopK SAEs
    trained only to reconstruct the fit-panel ambient clean/corrupt/sham head states. The unpaired
    selector freezes the 16 features with greatest ambient fit-state code variance without pair
    identities. The paired selector freezes the 16 features with greatest mean absolute
    clean-minus-corrupt code change. Both transplant exactly those selected codes from donor to
    corrupt. Report representation-training and selector information separately, plus parameter
    count, active budget, reconstruction loss, selected features, and decoded-delta norm. These are
    comparable by site, rows, and intervention path but **not** rank/parameter matched; the paired
    selector is `unsupervised_basis_paired_selector` and is excluded from unpaired-method claims.
12. **`zero`** and within-target donor-permutation controls.

The exact, output-oracle, paired, ambient, random, task-projection, target-mean, both SAE selectors,
zero, and permutation information contracts are serialized in the config and copied into the final
result. The four comparison classes are `donor_compression`, `task_aware`, `label_mean_no_donor`, and
`negative_control`; cross-class pooled rankings are prohibited.

### Frozen method details

- All global linear maps are uncentered, no-intercept maps from donor delta to donor delta. An exact
  zero donor therefore maps to zero. Factorized maps use `U[d,k] @ V[k,d]`, independent normal
  initialization with standard deviation `0.02`, MSE, Adam, batch 128, learning rate `0.003`, 1,500
  steps, and seeds `[8101,8102,8103]`; no validation selection or early stopping occurs.
- Target-linear maps use one such `U,V` pair per target, the same loss/batch/lr/steps, and seeds
  `[8201,8202,8203]`. The actual and sham use the same registered target ID.
- Target-nonlinear maps use target embedding width 16, hidden width 128, GELU, bottleneck k, PyTorch
  default layer initialization after `manual_seed`, MSE, Adam, batch 128, learning rate `0.001`,
  2,000 steps, and seeds `[8301,8302,8303]`. Embedding and linear-layer biases/defaults are enabled
  exactly as instantiated in the frozen implementation; inputs/targets are uncentered and no choice
  may vary after freeze.
- Output-oracle SVD is uncentered, no-intercept, float64. Store sign-canonicalized bases using the
  largest-absolute-coordinate positive convention with lowest-index tie breaking. Rank 64 must
  reproduce identity within `atol=1e-6, rtol=1e-6`.
- Ambient PCA is mean-centered float64 PCA on the concatenated ambient fit states. Its predicted
  delta is `reconstruct(donor_state)-reconstruct(corrupt_state)`, so the shared mean cancels. Ties use
  the same stored-basis convention.
- TopK SAE input width is 64, dictionary width 256, active count 16, with a learned input bias,
  ReLU encoder, linear decoder, no decoder renormalization, MSE, Adam, batch 256, learning rate
  `0.001`, 2,000 steps, encoder weights `Normal(0,1/sqrt(64))`, decoder weights
  `Normal(0,1/sqrt(256))`, zero learned input bias, no encoder/decoder affine bias beyond that shared
  input bias, and seeds `[8401,8402,8403]`. Both selectors choose exactly 16 codes; exact score ties
  choose the lower feature index. No evaluation row participates in fit or selection.
- The readout projection uses the uncentered Euclidean projector onto the row-specific span of the
  frozen target and contrast readout-weight vectors; QR signs/ties are canonicalized. Target-mean
  uses the fit mean by target and returns the same vector for actual and sham.
- Within-target permutation uses seed `8501`: permute fit donor deltas within target, fit an
  uncentered full-rank OLS map from permuted input to the original fit delta, and apply it to held-out
  actual/sham donors. Random projectors use seed `8502` and canonical QR.
- Native uses the predicted vector unchanged. Matched rescales both actual and sham predictions to
  the **actual row's true-delta norm**, exactly matching R5 behavior; it never uses the sham norm.
  Predictions with norm at or below `1e-10` are matched-incomplete and cannot pass. The structural
  zero control receives finite native summaries plus `matched_status=not_applicable` and is forced to
  fail; this expected N/A is not endpoint missingness and cannot authorize a family.
- The complete canonical method table—including input, target, comparison class, centering, bias,
  ranks, parameters, seeds, optimizer, steps, batch, learning rate, initialization, selection count,
  tie/sign rules, sham transform, and native/matched rules—is serialized in config. Its canonical
  SHA-256 is bound before panel creation and copied to every fit, pre-confirmation, and final record.

## Metrics, inference, and family decisions

For each model seed, panel, method seed, and native/matched estimand report:

- direction cosine, relative L2, captured energy, predicted/effective rank, and parameter count;
- behavioral recovery;
- signed sham specificity;
- same-site random matched-control margin;
- collateral error;
- necessity;
- full-vocabulary recovery;
- support, model accuracy, routing QA, and all individual gate decisions.

Use the exact R5 `interval` estimator bound by its frozen source AST hash: 1,000-draw equal-block
hierarchical bootstrap with the same quantiles/method and exact gate thresholds. Each ordinary block
contains unique controller types; because every evaluation tuple is unique, tuple multiplicity is
one. Report this rather than implying that row seeds create repeated independent controller support.
A learned family
passes only if every registered method seed passes every gate under both estimands on both panels for
all three model seeds. Do not aggregate model seeds as independent natural-model families. Plotting
or descriptive means cannot rescue a failed seed or gate.

Prospective interpretations:

- Exact/identity fails: evaluator or patch implementation invalid; stop and do not open confirmation.
- Output oracle rank-k passes but paired rank-k fails: optimization/estimation is the registered
  bottleneck at that rank.
- Only high/full-rank oracle and paired maps pass: global controller capacity is dominant here.
- Paired methods pass while ambient PCA, the genuinely unpaired SAE selector, and random fail: paired
  counterfactual alignment helps relative to the registered unpaired reconstruction controls at this
  site. The paired SAE selector is reported separately and no result generalizes to all SAEs.
- Target-conditioned methods pass where global maps fail: target side information or the larger
  union hypothesis class helps; do not call it a pure nonlinearity or capacity result.
- Exact passes but every estimated family fails: component selection/approximation remains the
  bottleneck under the registered methods.
- Any model-seed disagreement is reported and blocks an all-seed family claim.

## R5 preservation, paper, and analysis-only figures

Before the new scientific run:

1. Create a write-once R5 post-result preservation manifest binding both final result hashes, all
   117+3 checkpoint hashes, freezes, reviews, review binding, launch records, completion events, and
   the absence of technical terminals. Record `no_retry_authorized=true` and never edit R5 files.
2. Add claim-ledger entries and update `PAPER.md` with the global rank threshold, paired/unpaired
   contrast, low-rank target potency with poor collateral/full-vocabulary restoration, nonlinear
   rank-16 16/18 instability, exact trained-copy replication, and the fact that no estimated method
   was evaluated on that trained model.
3. Add an analysis-only script that reads only the two R5 final JSON files and writes a new immutable
   analysis namespace containing CSV/JSON tables plus six figures: rank curves, paired/unpaired
   comparison, recovery-specificity-collateral Pareto, potency versus full-vocabulary recovery,
   nonlinear seed sensitivity, and exact versus incomplete trained-copy controllers. Bind source
   result hashes in every generated summary. The script must not import Torch or open checkpoints.

The scoped paper sentence is:

> Complete causal control is measurable in constructed and trained synthetic systems. Recovering
> it requires both sufficient capacity and counterfactual alignment; targeted potency alone can
> substantially overstate controller completeness and safety.

The accompanying limitation must clarify that “requires” refers only to registered methods in these
constructions and that the exact trained-copy controller is an analytic donor delta at a deliberate
no-bypass bottleneck.

## Lifecycle and failure semantics

1. Write and adversarially review this plan before implementation.
2. Preserve R5, update paper/ledger, generate the analysis-only package, and verify every claim.
3. Implement config, benchmark source, tests, deterministic CPU/CUDA smoke path, and tmux launcher
   without creating or accessing scientific panel payloads or loading R5 checkpoints.
4. Obtain exact-candidate `/adversarial` SHIP. A BLOCK/REVISE candidate is preserved and receives a
   new technical successor; it is never patched after freeze.
5. Create a generator lock, materialize the three label-only panels once, and freeze opaque
   path/hash/support metadata plus exact imported-checkpoint hashes.
6. Obtain exact-freeze `/adversarial` SHIP without opening panel JSONL or loading checkpoints, then
   bind the review.
7. Select a genuinely free GPU by physical index and UUID, acquire an atomic per-UUID lock, launch
   once in tmux, verify worker PID ancestry and exact PID-to-UUID ownership, confirm fit-panel opening,
   and return immediately without waiting for results.

Before the owner creates output/provenance roots it validates source/config/freeze/review/checkpoint
lineage and output absence. Before each first panel read it writes and fsyncs
`ACCESS_MAY_HAVE_OCCURRED`; successful reads receive `OPENED`. Pre-confirmation failure writes
`CONFIRMATION_BLOCKED_UNOPENED`. A post-access crash writes `TECHNICAL_FAILURE_AFTER_ACCESS`. No
automatic retry, fallback GPU, seed deletion, batch/rank change, or threshold change is permitted.
The confirmation access event is unreachable unless the immutable pre-confirmation manifest exists,
hashes every fit artifact and development record, lists the full frozen method inventory, and records
exact/identity development authorization without conditioning on estimated-method outcomes.

## Milestones

- [ ] **M1 — R5 preservation and reporting.** Preservation manifest verifies; paper claims and all
  six analysis figures bind exact R5 result hashes; paper verifier passes.
- [ ] **M2 — Candidate implementation.** Source/config/tests/launcher exist; syntax, unit/mutation
  tests, CPU smoke, CUDA smoke, seed-disjointness, and launcher rendering pass without scientific
  payload or R5 checkpoint access.
- [ ] **M3 — Candidate adversarial gate.** Exact candidate receives SHIP; otherwise preserve and
  version a successor.
- [ ] **M4 — Prepare and freeze.** Lock precedes payload creation; opaque freeze binds panel support,
  hashes, R5 model hashes, candidate, config, and review; panel payloads remain unopened.
- [ ] **M5 — Frozen adversarial gate.** Exact freeze receives SHIP and its review binding verifies.
- [ ] **M6 — One-shot launch.** Free UUID-locked GPU and tmux owner are verified; fit-panel opening
  is recorded; return without waiting.

## Tests and adversarial mutations

- Exact and identity controllers pass all gates on a nonpanel smoke model.
- Zero, within-target permutation, and random controls fail without endpoint missingness.
- An output-oracle rank ordering mutation is detected; rank-64 oracle equals identity within the
  registered numerical tolerance.
- Swapping actual/sham donors or changing target metadata in sham scoring fails a regression test.
- Ambient PCA and the SAE unpaired selector are fit/selected only from unordered states; traps raise
  if either accesses pair identities or paired targets. The paired SAE selector has a distinct
  serialized information contract.
- Readout projection uses the frozen target/contrast vectors and no evaluation labels beyond
  registered row metadata.
- SAE fitting sees only ambient fit states; selected features are fit-only and checkpointed.
- Native and norm-matched estimands are both present, and deleting either prevents family passage.
- Target-linear union ranks and all 32 nonlinear Jacobian ranks are populated.
- Fit/development/confirmation IDs, seeds, blocks, offset pools, `(query,target,contrast)` tuples, and
  `(query,contrast,sham)` tuples are mutually disjoint; tuple multiplicity is one in both evaluation
  panels. Row IDs and row seeds—not controller tuples—must additionally be disjoint from R5, whose
  already-trained models necessarily saw the same finite task vocabulary.
- R5 checkpoint hashes are verified before loading; any drift fails before panel access.
- Candidate/freeze commands are trapped on JSONL resolution and `torch.load` of R5 checkpoints.
- Confirmation remains unopened when exact development is forced to fail.
- A failed estimated method cannot suppress other confirmation methods once exact development passes.
- Existing output/provenance roots, stale GPU locks, PID ancestry mismatch, UUID mismatch, nonfinite
  losses, and timeout all fail closed with truthful terminals.

## Risks and one-way doors

- **Opened confirmation is irreversible.** All methods, seeds, thresholds, inference inputs, and
  interpretations must be frozen first.
- **Donor availability limits the estimand.** This benchmark measures counterfactual component
  selection/compression, not donor-free discovery; the paper must say so.
- **Capacity is not uniform across families.** Global rank, per-target rank, SAE active count, and
  parameter count remain separate axes.
- **Synthetic external validity is narrow.** Three seeds share one architecture and task generator.
- **SAE comparison can be misleading.** Report it as a same-site reconstruction baseline, never a
  capacity-matched rank comparison.
- **Existing R5 checkpoints are already opened and selected evidence.** Their immutable hashes are
  fixed before new panels. Inference is conditional on these three previously R5-qualified
  checkpoints from one architecture/task generator; only per-checkpoint replication wording is
  permitted, never an unconditional trained-transformer population claim.

## Definition of done

- R5 is unchanged and a post-result manifest verifies every frozen/result artifact.
- `PAPER.md`, claim ledger, and six-figure analysis package report R5 with scoped language and exact
  lineage; the paper verifier passes.
- New benchmark config/source/tests/launcher pass deterministic candidate checks and independent
  adversarial review.
- Fresh disjoint panels and exact R5 checkpoint hashes are frozen before any new model inference.
- Exact freeze receives adversarial SHIP and review binding verification.
- A tmux worker is alive on a free UUID-verified GPU, its output namespace is new, and the fit-panel
  access transition is recorded.
- No K2 path, copy-transformer retraining, natural-model claim, threshold relaxation, or R5 mutation
  occurs.
- The assistant returns once the experiment is running and does not wait for results.

## Verification plan

- `python scripts/preserve_capacity_external_validity_v1_r5.py --verify`
- `python scripts/analyze_capacity_external_validity_v1_r5.py --verify`
- `python scripts/verify_paper_claims.py --paper PAPER.md --ledger reports/paper_claim_ledger_v1.json`
- `python -m py_compile scripts/trained_copy_method_benchmark_v1_r2.py`
- `pytest -q tests/test_trained_copy_method_benchmark_v1_r2.py`
- `python scripts/trained_copy_method_benchmark_v1_r2.py candidate-preflight --device cpu`
- `python scripts/trained_copy_method_benchmark_v1_r2.py candidate-preflight --device cuda`
- `python scripts/trained_copy_method_benchmark_v1_r2.py mutation-suite`
- `python scripts/trained_copy_method_benchmark_v1_r2.py verify-freeze --opaque`
- `python scripts/trained_copy_method_benchmark_v1_r2.py verify-review-binding`
- `bash -n scripts/launch_trained_copy_method_benchmark_v1_r2_tmux.sh`
- After launch: `tmux has-session`, exact worker PID/UUID in `nvidia-smi`, new fit-panel opening event,
  and a live controller-training process.

## Alternative considered

Training new copy-transformer seeds together with the method benchmark was rejected. It would mix
model-training variance with controller discovery, discard the already-qualified R5 positive
control, and consume fresh panels before the narrower method question is answered. Reusing the fixed
R5 models with new controller panels is simpler, preserves lineage, and isolates method behavior.


## R2 adversarial repair addendum

R1 candidate `9af7a8e5...b159` was blocked before generator lock or payload creation and is preserved unchanged. R2 is a separately versioned technical successor. It freezes the following repairs prospectively:

- evaluation panels use all 256 target-query pairs exactly once, with 32 eight-row blocks; main and sham tuple multiplicity is one within each evaluation panel and tuple inventories are disjoint across panels;
- the imported R5 implementation source and its preservation inventory entry are hash-bound at candidate, lock, freeze, launch, and checkpoint load;
- fit records and complete development results are atomically persisted, reread, schema/finite/cardinality checked, and reconciled to every fit artifact before an outcome-independent exact/identity authorization can open confirmation;
- `structural_not_applicable` is reserved for zero, while collapsed nonzero predictions are `prediction_incomplete` and fail scientifically without making execution incomplete;
- phase-aware signal and exception terminals cover technical stops before and after panel access; and
- mutation tests cover generator multiplicity, scientific scoring, inference-information traps, lineage drift, confirmation blocking/outcome independence, fit reconciliation, and phase-specific terminal behavior.
