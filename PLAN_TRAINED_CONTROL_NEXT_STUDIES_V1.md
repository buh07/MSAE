# Trained-Control Next Studies v1

## Goal

Preserve completed R4.2, update the paper/claim ledger to its post-result review, and launch two
independent synthetic experiments: (A) a trained-copy SAE capacity/selection diagnostic and (B) a
known-ground-truth causal-manifold bridge that explicitly separates donor compression from
donor-free discovery. Both use fresh panels, immutable namespaces, exact positive controls, and
one-shot tmux launches on two atomically reserved GPU UUIDs. They do not modify R4.2, retrain K2, or
support pretrained/natural-language claims.

## Grounded codebase and assumptions

- `scripts/trained_copy_method_benchmark_v1_r4_2.py` provides the checkpoint loader, paired panel
  generator, SAE, native/matched joint-control metrics, durable preconfirmation gate, lineage, and
  GPU ownership logic. Its donor compressors receive the observable clean/corrupt state pair or
  information sufficient to form its delta; exact per-method field access is serialized.
- `scripts/transformer_realistic_bridge_v1_r2.py` supplies deterministic Torch/NumPy precedents for
  soft attention, bypass, layer normalization, shared/nuisance factors, exact/incomplete paths, and
  hierarchical bootstrap, but its fixed geometry does not answer the new question.
- `reports/claim_review/trained_copy_method_benchmark_v1_r4_2_post_result_claim_review.md` is
  canonical: the rank result is `(16,32]`; ambient PCA 32 and task-aware methods passed; random 64 is
  identity; the SAE failure is limited to its registered 16-feature controller.
- No active design-ledger entry governs these successors. The low-risk canonical assumption is to
  retain R4.2's six scientific metrics and gates exactly. Bridge-only exact/incomplete checks are
  technical QA and never replace the scientific gates.

## Non-goals

- No R4.2 threshold change, panel reopening, rerun, or artifact append.
- No universal SAE, alignment, rank, transformer-family, K2, pretrained, or language claim.
- No claim that feature budget, token TopK, decoded rank, parameter count, or patch norm are the same.
- No globally optimal feature-subset claim: both privileged selectors below are explicitly greedy
  fit-only heuristics.
- No independent causal attribution to each bridge realism factor: the full factorial estimates
  main effects and interactions descriptively, but four structural generator seeds are not a
  population of transformer families.

## Preservation and paper contract

Before editing prose, create a write-once content-addressed R4.2 preservation manifest covering:

- plan, config, source, tests, launcher, candidate/freeze reviews and review bindings;
- generator lock, freeze, prepared metadata and all prepared payloads;
- candidate, run events, terminal, launch log, checkpoints, sealed fit/development artifacts,
  preconfirmation, final result, and post-result claim review;
- every frozen R5 checkpoint/dependency referenced by R4.2.

The verifier rehashes this allowlisted inventory before paper edits, after paper edits, and after both
launches. “Signed” means hash-bound by a separate immutable attestation containing the manifest SHA-256 and verified by a deterministic
script; no cryptographic identity signature is claimed.
The attestation is exclusively created read-only at
`reports/provenance/trained_copy_method_benchmark_v1_r4_2_postresult/ATTESTATION.json`; the
preservation verifier rehashes both files and refuses overwrite or drift.

Add a new R4.2 section and new ledger claims; do not rewrite historical evidence C081–C086. C086
remains true for the R5 conditional stage but is explicitly superseded at project level by R4.2.
Every R4.2 claim must state the information contract and the all-checkpoint, both-panel,
both-estimand, all-method-seed conjunction where applicable. Required updates:

- paired-linear 32/64, ambient-PCA 32/64, output-oracle 32/64, readout task projection, and
  target-nonlinear 32 succeeded;
- the sufficient global-rank bracket is `(16,32]`, not an intrinsic rank-32 minimum;
- the R5 counterfactual-alignment result is construction-specific; R4.2 ambient PCA 32 shows pairing
  was unnecessary when the ambient span covered this trained-copy manifold;
- random rank 64 is identity-equivalent QA, not random-baseline success;
- low SAE reconstruction did not yield a useful **TopK-16 / 16-selected-feature** controller;
- readout projection is target/contrast-aware donor compression; target-nonlinear 32 is task-aware
  donor compression with output-space Jacobian union rank 64, not donor-free rank-32 discovery.

## Study A — trained-copy SAE capacity v1

### Fresh panels and fixed model

Reuse the three R5 trained-copy checkpoints by exact hash. Generate new fit/development/confirmation
rows with new seeds, IDs, backgrounds, and offset assignments (offset values necessarily recur). Before freeze, reconstruct every opened R5,
R4/R4.1/R4.2 panel and require zero overlap in IDs, seeds, complete
`(clean_values,corrupt_values,sham_values)` triples, and full condition-pair contents. Target/query and
main offset marginals necessarily recur because vocab=32; their overlap is disclosed rather than
mislabelled fresh. Bind the collision report before any new scientific payload opens.

### SAE coding-capacity × selector-budget design

For each trained checkpoint and three SAE seeds, train five separate width-256 SAEs with token TopK
`{16,32,64,128,256}`. For each SAE evaluate global selected-feature budgets
`{16,32,64,128,256}`, but only combinations with selector budget >= token TopK are primary; all
others are descriptive undercomplete selectors. `256/TopK=256` is the dense/full-code SAE skyline.
Exact delta and identity are the only technical positive controls. Full-code SAE failure remains a
scientific SAE outcome and never blocks confirmation.

For every coding configuration freeze four selectors, using fit rows only:

1. `variance_selector`: descending ambient code variance.
2. `paired_change_selector`: descending mean absolute clean/corrupt code change.
3. `greedy_paired_reconstruction_selector`: greedily add the decoded feature contribution that most
   reduces total fit-delta squared error; deterministic lower-index ties.
4. `greedy_fit_behavior_selector`: greedily add the feature maximizing the arithmetic mean over eligible fit rows of `recovery + full_vocab_recovery + sham_specificity - collateral_error`; each term uses the R4.2 row denominator and scale with denominator floor `1e-6`, no bootstrap, coefficients `(1,1,1,-1)`, and nonfinite candidates score `-inf`; deterministic lower-index ties.

Selectors 3–4 are privileged greedy heuristic skylines, not certified upper bounds or globally
optimal oracles. Therefore:
ordinary failure plus greedy success supports a selector-bottleneck interpretation; failure of all
selectors does **not** prove no control-effective subset exists.

### Frozen comparison strata

All donor methods receive a typed observable `(clean_state, corrupt_state)` pair at inference. Linear methods derive the state difference; SAE transplantation separately encodes each state, copies registered clean codes into corrupt codes, and decodes relative to the corrupt reconstruction. The serialized per-method field contract records this common pair and every derived tensor. Native and rowwise
norm-matched estimands are both required; matched scaling is a privileged ground-truth-normalized
analysis, not deployable inference.

| Stratum | SAE primary budget | Linear rank match | Selector storage comparison | Parameter comparison | Permitted claim |
|---|---:|---:|---:|---:|---|
| S16 | TopK 16 / select 16 | PCA/oracle/paired 16 | 16×64 decoder coords vs 16×64 basis | none | rank/budget-described only |
| S32 | TopK 32 / select 32 | PCA/oracle/paired 32 | 32×64 vs 32×64 | none | rank/budget-described only |
| S64 | TopK 64 / select 64 | PCA/oracle/paired 64 | 64×64 vs 64×64 | none | full ambient-rank comparison |
| P | each SAE (32,832 trainable values) | `paired_latent_width256_parameter_match` (32,768 values, empirical rank ≤64) | n/a | within 0.2% | parameter-matched, not rank-matched |
| Full | TopK/select 256 | identity/oracle 64 | full SAE code | reported | representation/transplant skyline |

No rank-matched PCA claim is made for budgets 128/256 because observed width is 64. Report SAE
trainable count, selector-dependent decoder storage, token TopK, selected budget, decoded empirical
rank, patch norm, fit ambient reconstruction, fit delta reconstruction, direction recovery, and all
joint-control metrics. Linear methods include output oracle ranks 16/32/64, ambient PCA 16/32/64,
paired ranks 16/32/64 plus `paired_latent_width256_parameter_match`, random 16/32, exact, and identity. Random 64 is identity QA only.

### Prospective decisions

- Dense/full-code passes but smaller budgets fail: coding/selection capacity is implicated.
- A greedy selector passes before ordinary selectors: registered selection rule is implicated.
- Rank-matched PCA/paired passes while same-stratum SAE fails: evidence against that SAE
  representation/transplant configuration, not SAEs generally.
- SAE S32+ passes: R4.2's TopK-16/select-16 negative was capacity-confounded.
- Exact or identity fails: Study A confirmation stays unopened; SAE outcomes do not authorize it.

## Study B — causal-manifold bridge v1

### Exact graph, observable controller, and intervention

Create four fixed structural generator seeds. All clean/corrupt/sham members of a paired row share
the identical nuisance realization; only the registered causal/source factors change. The maximum
graph has observed state width 64, two residual layers, four soft-attention heads per layer, one
separately registered bypass, layer normalization after each residual update, and a fixed 32-value
readout. Simpler cells mask unused heads/layers/bypass while retaining the same typed schema.

Typed patch sites are: initial residual (64), eight ordered layer/head transported outputs (8×64),
and bypass output (64), for a fixed flattened observable controller dimension of 640. Site boundaries
are real model intervention sites and are serialized, but no causal/private coordinate labels are
exposed. The donor view contains the complete clean and corrupt typed site-state pair. Its flattened
difference is the input to linear compression; SAE methods separately encode the two flattened site
states. A predicted 640-vector is unflattened into slices `d_s`. Before intervention, the runner
records an immutable original corrupt snapshot `c_s` for every typed site. When execution reaches
site `s`, it **overwrites** the live tensor with `patched_s = c_s + d_s`; downstream consumers then
recompute from that overwritten value. It never adds `d_s` to an upstream-recomputed live tensor and
never treats `d_s` itself as a replacement state. Head slices at one layer are overwritten
simultaneously, the residual and layer norm are recomputed, and execution advances topologically;
bypass is overwritten at its registered merge. Exact, SAE, linear, sham, random, and incomplete
controllers all use this operator. Mutation tests implement and reject both `live_s + d_s` and
`site_s = d_s`.

The exact/identity controller uses all 640 clean-minus-original-corrupt typed site deltas, so the
overwrite equation makes every typed site equal its clean snapshot. Because paired nuisance is
byte-identical, this clean-trace graft changes only registered causal/source differences and equals
the clean-causal/corrupt-nuisance hybrid execution. Two independent implementations (Torch and
NumPy) must prove identity equals the exact hybrid logits within `atol=2e-5`, relative L2 `1e-5`,
and that zeroing any registered active head, active layer aggregate, or bypass slice makes the
incomplete controller miss at least one scientific gate. Per-site and total dimensions are recorded.
If this proof fails, exact is the sole authoritative control and the cell is technically invalid.

### Fully enumerated geometry design

Run the full 2^7 factorial (128 design cells), crossed with all four structural generator seeds:

- causal latent dimension: 16 / 32;
- nuisance latent dimension: 16 / 64;
- nuisance standard-deviation gain: 0.25 / 4.0;
- causal–nuisance correlation: 0.0 / 0.7;
- head/layer complexity: one head and one layer / four heads and two layers;
- bypass: absent / present with gain 0.35;
- routing: deterministic clean routing / distractor routing with logit noise 0.15.

Head count and layer count form one registered complexity factor; no separate head-versus-layer
attribution is claimed. Bypass is independent. All 128 design cells and the complete main-effect and
interaction contrast matrix are materialized before inference; the design is unaliased only if all
128 cells technically qualify. Per-cell QA reports realized causal/nuisance covariance ranks,
singular spectra, gain ratios, correlation, active structure, attention entropy, distractor mass,
and condition numbers.

The same four structural seeds occur in fit/development/confirmation with disjoint row seeds/IDs;
this is a within-generator estimand. Each cell×generator has 32 fit blocks and 8 development and
confirmation blocks, 4 rows per block: 128 fit rows exceed every centered per-cell latent rank, while
global fitting below pools all 16,384 fit rows per generator and records conditioning. Evaluation has
32 rows per cell×generator; support requires ≥30/32 eligible and ≥7/8 blocks. Intervals and gates are
computed separately for every cell×generator×method-seed×estimand using a 1000-draw block bootstrap,
then conjoined across all four generators and method seeds. Any generator-resampled aggregate is
descriptive only.

### Immutable typed information views

A view builder emits four schema-validated inputs:

1. `donor_compression`: full observable clean/corrupt typed-site pair (640 each), with no latent
   causal labels; methods may derive the 640 delta.
2. `corrupt_only`: corrupt final state (64) and query position only.
3. `instruction_conditioned`: the complete typed corrupt execution trace (640), public cell ID/config,
   query position, and transformation offset; no answer/target or clean/donor field. The answer is
   deterministically the registered offset transform of the decoded corrupt value. The corrupt trace
   and cell config are execution inputs, not a counterfactual donor.
4. `answer_conditioned`: corrupt final state plus explicit answer target; a privileged baseline, not
   an upper bound unless analytically certified.

No pooling across views. Source-to-view hashes, forbidden-field perturbation invariance, allowed-field
sensitivity, and empirical collisions are required. Answer identifiability is reported separately
from controller identifiability. Exact duplicate view keys are a data-integrity check only, never an
injectivity argument. The instruction view has a deterministic algebraic certificate: using only the
complete typed corrupt trace, public cell config, query, offset, and frozen public generator weights,
apply the registered causal/source transformation and re-execute every typed site to derive the
complete clean trace, then subtract the supplied corrupt trace. Deliberately repeated nuisance/source
conditions across offsets must reproduce the exact conditional mapping with zero residual risk. The
certificate must match the
exact 640-vector bytewise in NumPy and within the exact tolerance in Torch on fit and development.
Instruction-conditioned views are ineligible if answer accuracy is <0.99, any duplicate collision is
present, or this controller certificate fails. No discovery-bottleneck claim is permitted if the
certificate fails. Mutation QA removes or perturbs corrupt-trace, cell-config, query, and offset fields
one at a time and must break the certificate; perturbing forbidden clean/donor/answer fields must leave
the view and certificate byte-identical.

### Complete method and fit registry

Methods fit **separately per structural generator** but pool its 16,384 fit rows across all 128 cells.
Only the instruction-conditioned families receive the registered public 128-way cell one-hot/config;
no method receives hidden latent factors or ad hoc factor indicators. Every fit matrix must have numerical rank sufficient
for its registered rank and condition number <1e8 or that method is structurally ineligible. All
gradient-trained methods use Adam, deterministic minibatches, biases as stated below, and three
seeds; PCA, SVD/oracle, ridge, exact, identity, and analytic-certificate methods are not Adam fits.
The exact serialized table below is hashed into the generator lock before panel generation.

| View/family | Registered specification | Fit/inference fields |
|---|---|---|
| donor exact/identity | full 640 typed delta | typed state pair |
| donor `output_oracle_rank{k}`, `ambient_pca_rank{k}`, `paired_linear_rank{k}_seed{s}` | `k` in 32,64,128,256,640; paired bias-free factor map, Adam 2000 steps, lr 3e-3, batch 256, seeds 9101–9103 | pair/delta; PCA gets unordered typed states |
| donor random | fixed ranks 32,64,128; seed 9151 | delta |
| donor SAE | width 1280, TopK 64 and 128, selected paired-change budgets 64/128/all; Adam 2500 steps, lr 1e-3, batch 256, seeds 9201–9203 | typed clean/corrupt states |
| `corrupt_only_linear_ridge`, `corrupt_only_mlp_seed{s}` | ridge `1e-5` on `[state64;query_onehot8]` to output640; MLP 72→256→128→640, GELU, bias, 2500 steps, lr 1e-3, batch256, seeds 9301–9303 | corrupt final/query only |
| `instruction_linear_ridge`, `instruction_mlp_seed{s}` | ridge `1e-5` on `[corrupt_trace640;cell_onehot128;query_onehot8;offset_onehot32]` to output640; MLP 808→512→256→640, GELU, bias, 2500 steps, lr 1e-3, batch256, seeds 9401–9403 | corrupt trace/public cell config/query/offset |
| `instruction_analytic_controller_skyline` | no fit; public-generator re-execution certificate above; valid only with exact fit/development controller and behavior metrics | instruction view |
| `answer_linear_ridge`, `answer_mlp_seed{s}` | ridge `1e-5` on `[state64;answer_onehot32]` to output640; MLP 96→256→128→640, GELU, bias, 2500 steps, lr 1e-3, batch256, seeds 9501–9503 | corrupt final/explicit answer |
| negatives | zero, within-cell donor permutation, target permutation, omitted head/layer/bypass | respective typed views |

Nominal rank, empirical output rank/Jacobian union rank, parameter count, patch norm, and contract are
reported separately. The analytic skyline is called a skyline only if its certificate and
development exact-control QA pass; otherwise it is a failed baseline.

### Gates and lifecycle

Both studies use R4.2's exact scientific registry:

- recovery point/lower ≥0.70/0.60;
- sham specificity ≥0.50/0.40;
- matched-control margin ≥0.50/0.40;
- collateral error point/upper ≤0.10/0.15;
- necessity ≥0.50/0.40;
- full-vocabulary recovery ≥0.70/0.60.

Each method must pass every gate natively and norm-matched. Bridge technical QA additionally requires
exact recovery/full-vocabulary ≥0.999, exact collateral upper ≤1e-5, Torch/NumPy agreement, and each
incomplete mutation to miss at least one registered scientific gate. Development confirmation
authorization depends only on: exact/identity technical completeness in every eligible cell, sealed
fit/development artifact reconciliation, information-view firewall/identifiability QA, and an
authorization predicate that reads no estimated-method outcomes. Each of the 128 `design_cell`s is
defined before QA. Confirmation opens only if **all 128** cells pass
exact/identity development QA, view firewall/identifiability, and sealed artifact reconciliation;
otherwise confirmation remains unopened and only technical cell failures are reported. Thus full-factorial
main/interaction claims are never made on an outcome-selected subset. Family decisions conjoin gates
separately across every cell, generator, method seed, panel, and estimand; missingness is never a pass.

Prospective interpretations:

- high nuisance makes ambient PCA fail while same-rank paired compression passes: paired alignment
  helps under the registered nuisance intervention;
- donor compression and the certified instruction analytic skyline pass, but all finite registered
  instruction linear/MLP families fail: estimation under the donor-free view is the bottleneck; this
  claim is prohibited if the skyline or controller-identifiability certificate fails;
- exact passes and all estimated methods fail: approximation/discovery failure at that cell;
- exact fails: evaluator/site invalid for that cell, no method claim;
- no natural-model/K2 implication.

## Common launch, reproducibility, and lifecycle

Use a single coordinator to atomically reserve two distinct global locks named
`/tmp/msae_gpu_<UUID>.lockdir` before launching either study. It rechecks compute PIDs/memory/utilization,
writes index/UUID/token ownership, and launches fixed tmux sessions. Before successful return it performs
an atomic token handoff recorded as `GPU_LOCK_OWNERSHIP_TRANSFERRED` in each worker manifest. Coordinator
cleanup applies only before handoff and on partial-launch failure; after handoff each worker validates and
removes only its own lock on terminal, timeout, or signal. Mock tests cover success, partial failure, crash,
and stale-owner recovery. A bounded handshake requires launch manifest, ownership-transfer event, first
scientific access event, and exact worker PID on UUID; then return without awaiting results.

Both configs freeze Python/CUDA/Torch versions, checkpoint/panel hashes, all Python/NumPy/Torch seeds,
`PYTHONHASHSEED`, deterministic algorithms, CUBLAS workspace, source/config/test/launcher/plan/review
hashes, hard timeouts, and isolated outputs. No hardcoded user-home paths or credentials are allowed.

## Milestones

- [ ] **Milestone 1 — Preserve and document R4.2.** Complete recursive allowlisted preservation,
  post-edit verification, post-result summary, paper/ledger C087+, and passing claim verifier.
- [ ] **Milestone 2 — Study A candidate.** Freshness collision audit; five TopK SAEs; nested selector
  budgets; deterministic greedy selector tests; dense skyline; frozen comparison table; CPU/GPU no-panel
  smoke and mutation suite.
- [ ] **Milestone 3 — Study B candidate.** Enumerated 128-cell factorial; typed graph/patch semantics;
  independent Torch/NumPy exact QA; typed view firewall and Bayes/collision audit; per-cell gates;
  CPU/GPU no-panel smoke and mutation suite.
- [ ] **Milestone 4 — Independent review and freeze.** Repro report; candidate `/adversarial` SHIP;
  generator locks; fresh opaque payloads; exact freeze `/adversarial` SHIP; transitive review binding.
- [ ] **Milestone 5 — Atomic two-GPU launch.** Shared global UUID coordinator, two live tmux sessions,
  exact worker PID/UUID/startup events, then immediate return without results.

## Definition of done

- R4.2 preservation verifier passes before/after all work; R4.2 files remain byte-identical.
- PAPER/ledger accurately incorporate R4.2, retain historical C086 scope, and pass verification.
- Both successors have immutable configs, fresh panels, collision reports, locks, freezes, exact SHIP
  reviews, deterministic tests/smokes, and isolated outputs.
- Both tmux sessions are alive on distinct atomically reserved free UUIDs with scientific execution
  begun; no completion is awaited.
- No K2, pretrained, or natural-language inference runs.

## Risks and one-way doors

- Opening confirmation is irreversible; outcome-independent authorization is mandatory.
- Study A remains conditional on each SAE's token TopK; crossing TopK prevents silently treating global
  selector budget as coding capacity.
- Greedy selectors are privileged heuristic skylines, not upper bounds or exact subset oracles.
- Study B is large (128 cells×4 generators); config-derived timeout and incremental durable artifacts
  are required, but scientific registry cannot change after freeze.
- Answer-conditioned access can trivialize discovery; its view is an explicitly separate privileged
  baseline, not an oracle without an analytic certificate.
- Natural replication remains absent even if all synthetic seeds pass.

## Alternatives considered

- Rerun only SAE select-32: rejected because coding sparsity, selector, basis, and transplant remain
  confounded.
- Call greedy reconstruction an oracle: rejected; it is neither subset-optimal nor control-optimal.
- Fractional bridge design: rejected because aliasing would undermine factor attribution; full 2^7 is
  compute-heavier but unambiguous.
- Disjoint generator seeds across panels: rejected for the primary arm because it changes the estimand
  to OOD transfer; row-disjoint within-generator evaluation is registered instead.
- Jump to pretrained models: rejected until known-ground-truth donor-free discovery is validated.

## Verification plan

- [ ] Plan gate and `/adversarial` → PASS/SHIP before implementation.
- [ ] `python scripts/preserve_trained_copy_method_benchmark_v1_r4_2.py --verify` → exact inventory.
- [ ] `python scripts/verify_paper_claims.py` → all claim bindings/selectors pass.
- [ ] `pytest -q tests/test_trained_copy_sae_capacity_v1.py` → selector, matching, collision, lineage,
  lifecycle, and mutation tests pass.
- [ ] Study A CPU and CUDA candidate preflights → deterministic no-panel/no-checkpoint smoke passes.
- [ ] `pytest -q tests/test_causal_manifold_bridge_v1.py` → graph, factorial, exact/incomplete, view
  firewall, Bayes, gates, lifecycle, and mutation tests pass.
- [ ] Study B CPU and CUDA candidate preflights → all-cell no-panel exact/negative smoke passes.
- [ ] Repro scan → seeds/determinism/paths/secrets/environment/data hashes OK.
- [ ] Both exact candidate and opaque-freeze `/adversarial` reviews → SHIP bound to exact hashes.
- [ ] Coordinator shell syntax and separate deterministic lock tests → pre-handoff failure cleanup;
  one-of-two launch rollback; successful token transfer with coordinator exit; worker timeout/signal
  cleanup; live-owner stale-recovery refusal; PID/UUID remapping refusal → all PASS.
- [ ] Live startup handshake → two sessions, distinct UUIDs, exact PIDs, launch manifests, and first-scientific-access
  events; return immediately.
