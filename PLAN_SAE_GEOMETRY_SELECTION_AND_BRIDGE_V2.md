# SAE Geometry, Basis-vs-Selection, and Bridge Qualification v2

## Goal

Preserve the completed trained-control R2 outcomes, make the confirmed trained-copy SAE result central
in `PAPER.md`, complete a no-forward geometry analysis of the frozen R2 artifacts, and launch two
separately versioned successors on distinct free GPUs:

1. `trained_copy_sae_basis_selection_v1`: a fresh-panel experiment that distinguishes SAE basis
   dispersion from feature-selection failure.
2. `causal_manifold_bridge_v2_technical`: a technical-only positive-control qualification study with
   shared random-control banks and fresh structural/panel seeds. It does not evaluate estimated
   representation methods.

Both studies are new hypotheses/namespaces. Neither reruns, rescales, or appends either R2 namespace.

## Grounded codebase and evidence

- `scripts/trained_copy_sae_capacity_v1_r2.py` defines the confirmed trained-copy activation site,
  model/checkpoint loader, width-256 TopK SAE, transplantation operator, six native/matched metrics,
  deterministic lifecycle, and exact positive controls.
- `results/trained_copy_sae_capacity_v1_r2_20260813/final/result.json` is terminal-complete and shows
  budgets 16/32/64/128 at 0/360 all-gate records each, budget 256 at 360/360, while rank-32 ambient
  PCA/output-oracle/paired-linear pass.
- R2 checkpoints serialize SAE state, fit-only selector order, and linear bases, but not per-example
  codes. Therefore the analysis-only study can measure decoder/basis geometry and selector-set
  overlap, not example-level active-set overlap. The successor must cache only the new study's
  authorized activations/codes to answer the latter prospectively.
- `scripts/causal_manifold_bridge_v1_r2.py` defines the 128-cell typed topological intervention graph.
  Its R2 terminal is a development technical stop: exact numerical/view/incomplete QA passed 512/512,
  but 25/512 cell×generator endpoints lacked support and method-name-seeded single random controls
  made identity-equivalent exact controllers receive different control-margin outcomes.
- Existing R2 panels, outcomes, and seeds are opened development evidence for successor design and
  are never reused as new confirmation data.

## Non-goals

- No rerun, threshold change, row removal, rescore, or artifact append in either R2 namespace.
- No K2 training, pretrained-language-model claim, released-SAE claim, or natural-language claim.
- No claim that an SAE feature budget equals linear rank, token TopK, empirical decoded rank, or
  trainable parameter count.
- No claim that a development-supervised greedy subset is a deployable discovery method or a global
  combinatorial optimum.
- No bridge method comparison, realism-factor inference, or full factorial scientific claim in the
  technical v2 study. Passing v2 only authorizes a later, separately frozen method benchmark.
- No example-level feature-use claim from the R2 analysis-only artifacts, because R2 did not cache
  codes.

## Milestone 1 — immutable R2 preservation

Create `scripts/preserve_trained_control_r2_outcomes.py` and tests. Write a content-addressed manifest
and attestation covering both R2 plans/configs/sources/tests/launchers, candidate and frozen reviews,
generator locks/freezes/review bindings, prepared metadata/payload hashes, launch manifests/events,
terminals, logs, checkpoints, fit/development/confirmation/final artifacts where authorized, the R2
post-result summary/claim review, and the explicit absence of bridge confirmation/final artifacts.

The verifier must reject mutation, deletion, inventory additions under either R2 result/provenance
namespace, terminal/final hash disagreement, or appearance of bridge confirmation/final artifacts.
It is run before and after every paper/analysis/successor milestone and after launch. A separate
paper-input attestation records the exact pre-edit hashes of `PAPER.md` and the claim ledger; neither
mutable paper file is included in the immutable R2 result-namespace inventory.

## Milestone 2 — analysis-only R2 geometry and paper package

Implement `scripts/analyze_trained_copy_sae_geometry_v1.py` with no model loader and no model forward.
Its repository-artifact read firewall allowlists only the frozen final result JSON, frozen R2 SAE
checkpoint files, and frozen R2 `linear_bases.npz` files; interpreter, standard-library, installed
package, shared-library, and read-only font-cache reads are separately allowed runtime dependencies.
Checkpoint loading is weights-only. It refuses model weights, prepared payloads/panel readers,
R5/model modules in `sys.modules`, CUDA, network access, and every other repository/data path. It
writes a new analysis namespace containing:

- an observed-behavior budget table at exactly `{16,32,64,128,256}` with reconstruction, recovery,
  full-vocabulary recovery, collateral error, and pass counts;
- a separately labeled geometry-only table at `{16,32,64,128,160,192,224,256}`; no behavior,
  pass/fail, or interpolation is reported for the unobserved 160/192/224 budgets;
- principal angles and projection coverage between each selector-prefix decoder span and the
  checkpoint's successful ambient-PCA rank-32 and output-oracle rank-32 subspaces;
- numerical rank, singular spectrum, minimum nonzero singular value, and condition number for each
  selector prefix at budgets 16/32/64/128/160/192/224/256;
- Jaccard/overlap matrices only among selector prefixes within the same frozen SAE; cross-SAE
  comparisons use decoder subspace geometry and never compare feature indices;
- recovery–full-vocabulary–collateral Pareto figures and reconstruction-versus-control plots;
- explicit `example_level_active_set_overlap_available=false`.

For decoder-row subset `D_S`, compute a float64 SVD row-orthobasis `Q_S` with numerical-rank tolerance
`max(D_S.shape) * eps * s_max`. For row-orthonormal target basis `P`, angles are
`arccos(clip(svdvals(P @ Q_S.T), 0, 1))` and coverage is
`||P @ Q_S.T||_F^2 / rank(P)`. A rank-zero subset has coverage zero, an empty angle list, and JSON
condition number `"infinite"`; otherwise conditioning is `s_max / s_min_nonzero`.

All figures are derived from a hashed machine-readable summary. Reconstruction-versus-control plots
use one full-code reconstruction point per model×SAE-seed×TopK fit; control outcomes are aggregated
within that fit by registered budget/selector/panel/estimand and never treated as independent
reconstruction replicates. Replicate axes and intervals remain visible. Tests audit every repository/
data artifact path, deny model/R5 imports and prepared-panel parsing, disable CUDA, and use synthetic
matrices with known principal angles/ranks/conditioning. “Below 0.6% reconstruction error” is
explicitly the full-code SAE fit diagnostic, not a reconstruction claim for any fixed subset.

Update `PAPER.md` and `reports/paper_claim_ledger_v1.json` with content-addressed evidence. The prose
must state that all 256-feature selector labels are identical at full budget, that the result is one
trained synthetic copy-transformer design, and that no partial-budget family passed. Preserve the
sentence:

> Despite below-0.6% reconstruction error, every fixed SAE subset containing at most half the
> dictionary failed joint control, whereas a rank-32 PCA subspace and full-code SAE patching
> succeeded across all seeds and panels.

## Milestone 3 — fresh trained-copy basis-vs-selection experiment

### Data and lifecycle

Create a config-driven successor with new row seeds/IDs/content triples and four pairwise-disjoint
splits:

- `fit`: fit fresh SAEs and fit-only geometric/group-sparse selectors;
- `selector_fit`: fit the privileged behavior-supervised subset only;
- `development`: untouched evaluation used for registered development reporting;
- `confirmation`: unopened until exact/identity technical controls and artifact reconciliation pass.

Use the same three R5 checkpoint hashes and activation site, but new SAE seeds. Audit zero overlap
among all four new splits and against every opened R5/R4/R4.1/R4.2/SAE-R2 row ID, row seed, complete
state triple, and full condition-pair content. Marginal recurrence forced by vocabulary 32 is
reported, not called leakage. Use stage-isolated cache roots. Seal `fit` activations/codes before
opening `selector_fit`; seal every privileged selector before opening `development`; keep
confirmation caches uncreated until outcome-independent authorization. Each cache is float32,
created only after its registered model-forward event, hashed, and bound before downstream use.

### Frozen SAE and budgets

Train width-256 SAEs for TopK `{16,64,128}` and seeds `{10601,10602,10603}` on each trained-copy
checkpoint, using the frozen R2 optimizer, steps, batch size, and learning rate. Evaluate budgets
`{128,160,192,224,256}`. Retain R2 variance, paired-change, and greedy reconstruction selectors as
fit-only baselines; replace the ambiguous R2 fit-behavior label with the precisely specified
supervised selector below.

### Basis-versus-selection methods

Freeze these selector definitions, hyperparameters, and inventory before any new payload opens;
fitted orders and coefficients are separately sealed at the registered lifecycle events:

1. `pca_coverage_greedy`: fit-only deterministic forward selection from the empty set, at each step
   maximizing the coverage formula above against the fit rank-32 PCA basis; ties within `1e-12` go to
   the lower feature index. Serialize the complete 256-feature order.
2. `fit_supervised_omp`: on fit rows define column
   `A_j=vec((clean_code-corrupt_code)_j * decoder_j)` and target
   `y=vec(clean_state-corrupt_state)`. Normalize nonzero columns for selection, choose the largest
   absolute residual correlation (ties within `1e-12` to the lower index), refit coefficients by
   float64 SVD least squares on the original unnormalized selected columns using tolerance
   `max(A_S.shape)*eps*s_max`, and continue to 256. Zero-norm columns are ineligible until every
   nonzero column has been ordered, then are appended by ascending index with coefficient zero.
   Serialize the full order and prefix-specific coefficient vector `beta_S`. On evaluation the native
   unweighted donor/sham patches are respectively
   `sum_{j in S}(z_clean-z_corrupt)_j D_j` and
   `sum_{j in S}(z_sham-z_corrupt)_j D_j`; the coefficient skyline multiplies each term by
   `beta_{S,j}`. Both then enter the unchanged R2 norm-matched scoring path. Only unweighted
   transplantation is an SAE-subset result.
3. `selector_fit_behavior_greedy`: a privileged deterministic forward selector trained only on
   `selector_fit`. For each candidate (evaluated in fixed chunks of 32), maximize the unbootstrapped
   arithmetic mean across eligible selector-fit rows of
   `recovery + full_vocab_recovery + sham_specificity - collateral`, with denominator floor `1e-6`;
   ties within `1e-12` go to the lower feature index. Select through budget 224, then append remaining
   indices in ascending order solely to form the canonical full-256 set. Freeze the order before any
   `development`/`confirmation` read. It is a supervised skyline, not an unsupervised SAE result or
   certified global optimum. Candidate scoring uses ordinary unweighted native SAE-code donor and
   sham transplantation exactly as defined above, never norm matching or OMP coefficients, and uses
   the same registered eligibility mask as final native scoring.
4. `selected_decoder_span_oracle`: for each selected subset, project the observable donor delta onto
   the selected decoder-row span and patch that projection. This tests basis coverage independently
   of SAE code transplantation and is explicitly a donor-conditioned geometric skyline. With
   float64 row-orthobasis `Q_S`, native donor and sham patches are exactly
   `delta_state @ Q_S.T @ Q_S` and `sham_delta_state @ Q_S.T @ Q_S`, followed by the unchanged R2
   norm-matched scoring path; a rank-zero span emits zero patches and is ineligible for ratio gates.
5. Frozen ambient-PCA rank 32, output-oracle rank 32, paired-linear rank 32, exact, identity, random
   rank 32, and full-code SAE controls.

Protocol/config, algorithms, hyperparameters, and inventory are locked before payload generation.
The enforced lifecycle is: fit cache -> `FIT_SELECTOR_SEAL` -> selector-fit cache and privileged
selection -> `PRIVILEGED_SELECTOR_SEAL` -> development evaluation -> outcome-independent
confirmation authorization -> confirmation evaluation.

Cache per-example active feature IDs for the new study and report within-SAE active-set overlap,
feature frequency, and cross-example union growth. Feature indices are never compared across
independently trained SAEs as if aligned.

### Metrics and decisions

Use the unchanged six R2 native and norm-matched gates and 1000-draw block bootstrap. Confirmation
authorization reads only exact/identity controls, cache/artifact reconciliation, and split
freshness—not SAE/selector outcomes. Exact/identity/PCA/oracle/random family decisions conjoin both
panels, all three model checkpoints, and both estimands; paired-linear additionally conjoins all
three method seeds; SAE families additionally conjoin all three SAE seeds and TopK settings. At
budget 256 every unweighted selector is collapsed to one canonical `full_code_sae` record per
model×SAE-seed×TopK, rather than counted as multiple selector replications. The coefficient-weighted
OMP skyline remains a distinct `fit_supervised_omp_beta256` method.

Prospective interpretation:

- a supervised or geometric subset at the registered budget 128 passes while fit-only R2 selectors
  fail: the result is consistent with selector discovery being a bottleneck, not proof it is the
  unique bottleneck;
- decoder-span oracle at budget 128 passes but SAE transplantation at the same subset fails: the
  result is consistent with an intervention-operator or coefficient/coding bottleneck, not unique
  evidence for nonlinear coding;
- no registered budget-128 subset/skyline passes while rank-32 PCA does: the result is consistent
  with SAE-basis dispersion or misalignment under the registered selectors/operators, not proof that
  no other small subset exists;
- a selector×TopK×family first passes at 192, 224, or 256 after its immediately lower tested budget
  fails: report that family-specific open-lower/closed-upper feature-budget bracket, without calling
  it an intrinsic minimum;
- full-code SAE or exact controls fail: no SAE compression claim; confirmation stays unopened if an
  exact/identity control fails.

## Milestone 4 — bridge v2 technical qualification only

Create a separate bridge technical-study config/source using fresh structural seeds, panel seeds,
row IDs, and namespace. It inherits the exact typed graph and overwrite semantics without importing
R2 method outcomes. Before qualification, a fail-closed collision audit proves separate zero overlap
of unique row IDs and row seeds against all opened bridge-R2 rows. Scientific-content collisions use
one canonical composite key containing the complete typed source+nuisance trace, public query+offset,
and complete target+contrast+sham condition record; equality of this full key is forbidden while
marginal categorical recurrence is explicitly allowed and reported. Before validation authorization,
the same three checks and exact composite-key definition prove pairwise qualification/validation
disjointness without exposing validation outcomes. Bind both audit hashes into the generator lock and
authorization record.

Before any estimated-method fit exists:

1. Generate a `qualification` panel with 32 blocks × 4 rows per cell×generator and require >=120/128
   eligible rows and >=30/32 blocks in every one of 512 endpoints.
2. Use one shared, serialized bank of 32 norm-matched random controls per row, independent of method
   name. Exact and identity must consume byte-identical control banks and therefore have identical
   control-margin inputs and decisions.
3. The primary isotropic control for tuple
   `(study_id, structural_seed, generator_seed, cell_id, row_id, bank_index)` uses a SHA-256-derived
   64-bit seed: canonical UTF-8 JSON of the tuple, SHA-256, first 8 digest bytes interpreted unsigned
   little-endian. With the environment-pinned NumPy version, use
   `numpy.random.Generator(numpy.random.PCG64DXSM(seed)).standard_normal(d, dtype=float64)` in the
   registered typed source intervention slice. Orthogonalize it against the exact donor delta;
   resampling appends an integer counter to the seed tuple before canonical encoding. If its
   post-projection norm is `<=1e-12`, resample; otherwise scale to donor L2 norm, cast once to float32,
   and serialize in lexicographic row/bank order. A donor norm `<=1e-12` makes the row ineligible
   before bank construction. The nuisance bank uses the same seed/order/norm rules but draws
   coefficients in the registered ground-truth nuisance basis before donor orthogonalization.
4. For each eligible row, define primary control recovery as the arithmetic mean over its fixed 32
   isotropic controls, then row margin as exact recovery minus that mean. The 32 controls are
   exhaustive within-row nuisance integration, not bootstrap units. The endpoint point estimate is
   the equal-weight mean of eligible-block means. Hierarchically bootstrap 1000 draws by resampling
   each eligible block's eligible rows with replacement while preserving that block's observed
   eligible count, then resampling eligible blocks with replacement; use linear empirical quantiles.
   Bootstrap draws use the same pinned PCG64DXSM, seeded from canonical tuple
   `(study_id,panel,endpoint_id,"bootstrap",bootstrap_seed)` by the digest rule above. Config freezes
   the NumPy version and bootstrap seed, and golden-vector tests bind bank and bootstrap draws.
   Retain the R2 margin gate `point >= 0.50` and lower confidence bound `> 0.40`. Report median, 90th
   percentile, maximum, and bootstrap upper confidence bound of mean control recovery descriptively;
   do not set a cap from the opened R2 maxima.
5. Include the prespecified nuisance-subspace negative bank and isotropic bank. The shared isotropic
   bank is primary; the nuisance bank is a ground-truth technical diagnostic, not the scientific
   comparator.
6. Run exact Torch/NumPy, view-firewall, incomplete-controller, support, recovery, specificity,
   collateral, necessity, full-vocabulary, and shared-control-margin QA in all 512 endpoints.
7. Only if every endpoint passes may a fresh `validation` panel (16 blocks × 4 rows) open. Validation
   requires >=60/64 eligible rows and >=15/16 blocks per endpoint, uses identical estimators and gates,
   then writes `BRIDGE_V2_TECHNICALLY_QUALIFIED` or a terminal stop. It contains no
   representation-method registry or training path.

Passing does not reopen bridge v1 or authorize method claims. It only permits a later separately
reviewed bridge-v2 method benchmark. Failure is reported without threshold changes or cell removal.

## Milestone 5 — implementation, adversarial gates, and launch

For each successor provide:

- immutable config, candidate manifest, generator lock, prepared manifest, freeze, exact-hash
  candidate/frozen reviews, review binding, launch manifest, provenance events, one-shot namespace,
  terminal, and deterministic CPU/CUDA smoke path;
- tests for split freshness, outcome-independent confirmation authorization, method inventory,
  native/matched scoring, numerical finiteness, checkpoint/cache hashes, active-set bookkeeping,
  pairwise split and stage-path firewalls, vectorized-versus-scalar selector equivalence,
  shared-control identity, support/estimator gating, absence of bridge training paths, and terminal
  behavior;
- a coordinator launcher that atomically reserves two distinct free GPU UUIDs, survives stale-lock
  races/partial launches/signals, writes PID-to-UUID evidence, waits only for first authorized access,
  and returns immediately.

Bound selector candidate chunks to 32 and enforce hard per-worker ceilings of 24 hours for the SAE
study, 12 hours for bridge qualification, and 20 CPU minutes for analysis. A timeout produces a
signed technical-failure terminal; any partial checkpoints are forensic-only and never permit resume,
cache reuse, or scientific-gate changes.

Run `/adversarial` on this plan before implementation, on exact candidate artifacts before generator
locks/panel generation, and on exact freezes before launch. BLOCK/REVISE candidates are preserved by
hash and superseded; no scientific run starts until both frozen reviews are SHIP.

## Alternatives considered

- **Retry bridge R2 with a lower control-margin threshold:** rejected as outcome-conditioned and
  forbidden by its terminal.
- **Use R2 confirmation to train an oracle subset:** rejected as leakage. The new selector has a
  dedicated development split and fresh untouched evaluation/confirmation.
- **Call full-budget selector variants independent replications:** rejected because all select the
  same complete dictionary.
- **Run the full bridge method registry immediately:** rejected because the positive-control assay,
  not method performance, failed. Technical qualification must precede any method comparison.
- **Infer example-level R2 feature usage by re-forwarding old panels:** rejected by the no-new-forward
  analysis contract; the new study caches its own codes prospectively.

## Definition of done

- R2 preservation verifies before/after every write and after launch; neither R2 namespace changes.
- Analysis-only geometry code executes without importing/calling a model and produces finite
  numeric values (apart from the registered JSON `"infinite"` rank-zero condition sentinel),
  hash-bound tables/figures, and the explicit active-set limitation.
- Paper and ledger claims are content-addressed and scoped to the trained synthetic copy system.
- Each new study has fresh, disjoint payloads, immutable config/lock/freeze/review lineage, real
  deterministic smoke tests, and no preauthorization confirmation access.
- SAE successor contains every registered selector/skyline/baseline and caches active sets only for
  its own new rows.
- Bridge successor uses a shared 32-control bank, exact/identity comparator equality, adequate
  prescore support, no estimated method/training path, and endpoint-complete gating.
- Independent candidate and frozen `/adversarial` verdicts are SHIP and exact-hash bound.
- Focused tests and CUDA smoke checks pass.
- Both experiments launch in tmux on distinct free physical GPUs with live PID/UUID evidence; the
  response returns after startup without waiting for results.

## Risks and one-way doors

- Opening new confirmation panels is irreversible; authorization must remain outcome-independent.
- Selector-fit-supervised subset selection can be mistaken for unsupervised discovery; naming and
  claims must retain the skyline qualifier.
- SAE decoder rows from independent seeds have no shared identity; cross-seed feature overlap is
  prohibited.
- Shared random-bank aggregation changes the bridge estimand and is therefore a new version, never a
  repair or rescore of R2.
- The 128-cell bridge conjunct is deliberately severe; a failure is a qualification stop, not
  permission to select passing cells.
- Large geometry/selection loops may be expensive; hard timeouts and forensic snapshots outside every
  consumable fit/cache registry are required. Every loader/authorization path rejects such snapshots,
  and timeout never changes scientific gates.

## Verification plan

- `python scripts/preserve_trained_control_r2_outcomes.py --verify`
- `pytest -q tests/test_preserve_trained_control_r2_outcomes.py`
- `pytest -q tests/test_analyze_trained_copy_sae_geometry_v1.py`
- `python scripts/analyze_trained_copy_sae_geometry_v1.py --verify`
- `python scripts/verify_paper_claims.py`
- `pytest -q tests/test_trained_copy_sae_basis_selection_v1.py`
- `pytest -q tests/test_causal_manifold_bridge_v2_technical.py`
- `pytest -q tests/test_launch_sae_selection_bridge_v2_tmux.py`
- CPU and CUDA candidate smoke checks for both studies, with `scientific_panel_accessed=false`
- exact freeze verification and post-launch R2 preservation verification
