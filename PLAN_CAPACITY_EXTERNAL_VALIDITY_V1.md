# Capacity-Controlled Discovery and Conditional Trained-Transformer External Validity v1

## Goal

Preserve and report the completed transformer-realistic bridge r2, then distinguish registered global-linear controller-capacity failure from estimation failure on fresh random instances of the same synthetic construction. Only after the capacity study completes with its full-rank positive control valid may a separately frozen trained-transformer complete-circuit study open in the same supervised tmux pipeline. Neither study evaluates or trains K2.

## Scope and claims

The capacity study is a new, separately versioned exact-linear learnability bridge, not a natural-transformer result and not a continuation of the frozen r2 namespace. It reuses the frozen r2 causal metrics, bootstrap, and gate conventions but deliberately changes the generator so the desired controller is provably full-rank and linearly learnable. It uses three new random parameter instances and fresh train/development/confirmation row seeds. The trained-transformer study is external validity relative to analytic construction: a small trained attention-only copy model with an architecture-fixed complete causal bottleneck. It is not a pretrained language model or natural-language claim.

The post-result paper update must state that exact complete control passed the six-operation bridge while registered approximations failed joint control; it must also retain the GPT-2 contribution-without-sufficiency and K2 stable-mixing contrasts. Broad SAE, supervision, K2, and natural-model claims remain prohibited.

## Capacity diagnostic

### Independent units and panels

Use generator seeds `[41011, 41037, 41081]`. For each generator, create disjoint train/development/confirmation panels with seeds derived from frozen base seed `20261110`; train has 32 blocks x 16 rows and each evaluation panel has 24 blocks x 8 rows. Each target occurs in 32 train blocks and 12 evaluation blocks. Generator and row seeds are disjoint. The previous opened r2 panels are evidence only and are never reused for fitting, selection, calibration, or scoring.

### Estimand and causal tensors

For each instance, freeze a 64 x 16 column-orthonormal readout basis `D` and a 64 x 64 full-rank mixing matrix `M = Q1 diag(linspace(0.75,1.25,64)) Q2^T`, with `Q1,Q2` obtained by QR and each column sign fixed so its largest-absolute coordinate is positive; exact ties select the lowest coordinate index, and a zero pivot is a technical failure. This gives condition number at most 5/3 without relying on sampled data. For row `i` with registered target `t`, contrast `c`, and sham `h`, draw Gaussian `g_i` and remove its projection onto `span(D)`. Define:

- corrupt state `s_corrupt[i] = -1.5 D[:,t] + 1.5 D[:,c] + 0.10 g_i`;
- exact causal delta `delta_gt[i] = 4 D[:,t] - 4 D[:,c] + 0.20 epsilon_i`, with independent full-dimensional Gaussian `epsilon_i`;
- hybrid state `s_hybrid[i] = s_corrupt[i] + delta_gt[i]`;
- estimator input `x_obs[i] = delta_gt[i] M` and exact controller `W* = M^{-1}`, so `x_obs W* = delta_gt` rowwise;
- sham delta `delta_sham[i] = 4 D[:,h] - 4 D[:,c] + 0.20 epsilon_sham_i` and `x_sham[i] = delta_sham[i] M`;
- logits `L(s) = 8 * LayerNorm(s, eps=1e-5) @ D`; the insertion operator adds a predicted 64-vector to `s_corrupt`, and the behavioral oracle is `L(s_hybrid)`.

All Gaussian draws are seed-derived. Every panel exactly balances the target, contrast, and sham marginals separately through counterbalanced cyclic offsets; it does not attempt to cover every ordered joint triple. Train `x_obs` must have sampled smallest singular value greater than `1e-5` and condition number below `1e6`. A symbolic basis test, executed before locks for each nonpanel instance, must prove in float64 that every standard basis vector satisfies `(e_j M) W* = e_j` within `1e-10`; a sampled test separately checks every train row within `1e-8`. The observed input transplant `x_obs` is a separate, explicitly nonselective skyline and may not authorize anything. A mutation substituting it for `delta_gt` must fail direction or collateral assertions.

Sham scoring keeps target ID and all target metadata fixed; only donor evidence changes from `x_obs` to its registered sham input. Target-conditioned methods receive the same fixed target ID for actual and sham. Label-only and within-target delta-permutation controls are mandatory. Train/dev/confirmation never share row IDs, seeds, or blocks.

### Registered controller families and information access

At inference all estimated families receive `x_obs`; only explicitly conditioned families also receive the frozen target ID. The fit-information table is frozen in config and emitted verbatim in every result:

1. `exact_delta_gt`: directly inserts `delta_gt`; analytic causal/evaluator positive control, not an estimator.
2. `observed_input_transplant`: directly inserts `x_obs`; rotated-input nonselective skyline, required to fail direction or collateral safety.
3. `closed_form_linear_full64`: uncentered, no-intercept float64 OLS `W_hat = pinv(x_obs, rtol=1e-12) @ delta_gt` on the full-column-rank train matrix, with singular-value and condition gates above; mandatory provably learnable paired-target control. Prediction is `x_obs @ W_hat` with no mean restoration because the true map passes through the origin.
4. `reduced_rank_regression_rank{k}` for `k in [4,8,16,32,64]`: compute full OLS fitted values, take `V_k` from the sign-canonicalized float64 SVD of the uncentered fitted targets (ties resolved by ascending coordinate pivot), and use `W_k = W_hat V_k V_k^T`; this is the closed-form train-MSE-optimal reduced-rank linear regression in the registered global-linear hypothesis class.
5. `paired_linear_rank{k}` for the same ranks: three fixed seeds, a factorized global linear map trained for 1,500 fixed Adam steps on paired `(x_obs, delta_gt)`.
6. `unpaired_pca_rank{k}` for the same ranks: train-only mean-centered PCA reconstruction `mean_x + (x_obs-mean_x) P_k`, with the reconstructed observed delta inserted directly; it receives no target delta or target ID during fitting.
7. `target_linear_rank{k}` for `k in [4,8,16,32]`: three fixed seeds, 16 target-indexed factorized maps trained on paired targets. Report total parameters and the empirical rank of their union; `k` is only a per-target bottleneck and is never declared capacity-matched to a global rank-k map.
8. `target_nonlinear_rank{k}` for `k in [4,8,16,32]`: three fixed seeds, target-conditioned two-layer GELU encoder/decoder with bottleneck k and 128 hidden units, trained on paired targets for 2,000 steps. Report parameters, inference inputs, and empirical Jacobian ranks.
9. `label_only`, `within_target_delta_permutation`, `zero`, and seeded random global rank-k controls.

Every learned seed is retained and must pass independently; descriptive seed means never rescue a seed. The closed-form reduced-rank regression is optimal only for train-distribution squared direction error within global linear maps. It is not a causal-loss upper bound and cannot establish universal rank-k insufficiency. Conditioned/nonlinear methods are separate hypothesis classes, not capacity-matched competitors.

### Direction and causal metrics

For each method/generator/panel report:

- cosine alignment of predicted versus exact delta;
- relative delta L2 error;
- captured delta energy;
- train-basis projection energy and principal-subspace overlap where defined;
- behavioral recovery;
- signed sham specificity;
- same-site/same-path matched-control margin;
- collateral error;
- necessity;
- full-vocabulary recovery.

The common cohort, target support, block bootstrap, gates, and strict/inclusive conventions are copied exactly from the r2 *methods* benchmark. Native control and `oracle_norm_matched_directional_control` are co-primary: matching uses the unseen row-level `||delta_gt||` only to isolate direction quality and is never described as deployable control. A pass requires the full causal conjunction independently under both native and matched estimands. Direction metrics are descriptive for rank-limited methods and cannot override either conjunction; `exact_delta_gt` and `closed_form_linear_full64` additionally require cosine at least `0.999`, relative L2 at most `0.001`, and finite metrics on every row. A method passes an instance only if every seed passes both panels. A family statement requires all three registered random instances, but no cross-construction or natural-model replication claim is allowed.

### Prospective interpretation

- Either exact control fails, or full-rank OLS fails its conditioning/direction gates: evaluator, conditioning, or implementation invalid; stop and leave external validity unopened.
- Global reduced-rank regression fails at rank 8 but passes at a higher rank: the registered global-linear train-MSE class needs more than rank 8 for these instances; do not infer universal rank-8 insufficiency.
- Reduced-rank regression rank 8 passes while learned global-linear rank 8 fails: estimation/optimization of that same global-linear class is the isolated bottleneck.
- A learned global-linear seed passes where closed-form reduced-rank regression fails: report the objective mismatch; do not call either result a capacity bound.
- Paired-target methods pass while unpaired PCA, label-only, and permutation controls fail: paired causal-target information helps relative to the registered representation-reconstruction controls in this construction; do not generalize to supervision or feature discovery broadly.
- Conditioned/nonlinear methods pass while global maps fail: target side information or the larger union hypothesis class helps; parameter/effective-rank differences preclude a pure nonlinearity claim.
- Generator-instance disagreement or rank crossings are reported per instance and preclude an all-instance family claim.
- No global rank below 64 passes: report only that no registered lower-rank global controller met joint gates; do not infer generic discovery failure.

This is intentionally a paired-delta approximation/compression study. It does not by itself test discovery from unpaired natural activations, and no SVD-versus-learned contrast may be generalized to unsupervised feature discovery.

No thresholds, ranks, steps, generators, or interpretations may change after scientific payload creation.

## Conditional trained-transformer study

### Model

Train exactly three seeds `[5101, 5102, 5103]` of a small attention-only copy transformer. Each example contains eight source slots and an index query. The value vocabulary is 32. Learned value and source-position embeddings have width 64. Routing and value inputs are architecturally factorized: Q/K receive only the query-index and source-position embeddings, respectively, while V receives only the value embedding. One pre-layer-norm, one-head attention module has key/query/value width 64; no value embedding can enter Q or K. The sole logit path is `head_pre_ln -> LayerNorm(eps=1e-5) -> Linear(64,32,bias=False)`. There is no query residual, MLP, embedding bypass, or second head. The registered complete patch site is `head_pre_ln`, immediately before layer normalization. This is a single causal bottleneck by architecture; “attention-only” refers to this no-residual logit path.

Each seed trains once with AdamW, learning rate `3e-3`, weight decay `1e-4`, batch 256, exactly 4,000 steps, gradient clip 1.0, and cross-entropy loss. The external train payload is one materialized, hash-bound 256-block x 32-row corpus with seed 20261120; model seed `6100 + model_seed` determines the with-replacement minibatch-index stream. No development/confirmation row is used for fitting, checkpoint selection, stopping, or retry. Development and confirmation each have 24 document-like blocks x 8 rows, use seeds 20261121 and 20261122, and are disjoint from training and from each other. A model endpoint is eligible only if clean copy accuracy is at least 0.95, corrupt rows predict their registered contrast with accuracy at least 0.95, at least 185/192 rows have a clean-minus-corrupt target-versus-contrast margin greater than 1.0, every block contributes at least seven eligible rows, every value has at least five eligible rows marginally, and every query index separately has at least five eligible rows marginally. Any seed failing eligibility is a registered model-level negative; it is never retrained.

For each row, clean and corrupt sequences share query, length, positions, and all nontarget slots; the queried source value changes from target to a distinct counterbalanced contrast. This counterfactual intentionally tests complete **value transport with routing held invariant**, not joint routing/value necessity. A sham donor has a different value but the same query index, block, and template metadata. Target metadata remains fixed while its donor state changes. Values, contrasts, shams, and queried indices are balanced within each panel.

### Controls and gates

Evaluate, for every training seed:

- exact clean head-output transplant into corrupt execution;
- exact head-output ablation;
- `clean_routing_corrupt_value = sum(clean_attention_weights * corrupt_value_vectors)`;
- `corrupt_routing_clean_value = sum(corrupt_attention_weights * clean_value_vectors)`;
- prespecified first-half, second-half, and alternating-coordinate clean-head masks as incomplete head-output controls;
- random same-norm head-output directions;
- sham donor with a different value and the same query index;
- full-vocabulary recovery and collateral damage.

Use the same r2-method recovery, sham specificity, matched-control, collateral, necessity, and full-vocabulary gates as the capacity study. Exact patch must pass every gate for every trained seed on both panels. The coordinate masks are descriptive incomplete controls only: their success indicates redundant coding and their failure indicates insufficiency, but neither outcome affects technical validity or implies coordinate-wise causal minimality. Exact clean/corrupt attention weights must be bit-identical; `corrupt_routing_clean_value` must reproduce the clean head and `clean_routing_corrupt_value` the corrupt head within `atol=1e-7, rtol=1e-6`. These are mandatory architectural routing-invariance QA checks, not causal routing effects. This is a trained synthetic-transformer value-transport positive control, not a general method benchmark.

Prospective external outcomes are: exact patch fails any joint gate -> intervention/evaluator positive control fails; exact patch passes but routing-invariance QA fails -> implementation violates the frozen factorized architecture; exact patch and QA pass while a mask is sufficient -> complete bottleneck is validated with redundant coordinate coding; exact patch and QA pass while masks fail -> complete bottleneck is validated and the registered coordinate subsets are insufficient. Only exact patch plus QA passing every seed/panel constitutes full external qualification.

### Authorization

The external study configs, source, prepared metadata, and freeze are created before capacity inference. Its train/development/confirmation payloads remain unopened until the capacity final exists. It opens only if:

- capacity execution is technically valid for all three registered instances;
- `exact_delta_gt` passes all instances in both panels;
- `closed_form_linear_full64` passes all instances in both panels;
- recovery/direction metrics are finite and complete;
- the exact capacity final hash matches the authorization record.

Otherwise write `BLOCKED_UNOPENED` with all external payload-access and training flags false. Before resolving any external payload path, model initialization, checkpoint-directory creation, or optimizer construction, the owner writes and fsyncs create-once `PRECHECK_NO_ACCESS`, then fsyncs its parent directory. If authorized, it writes and fsyncs `ACCESS_MAY_HAVE_OCCURRED` and its parent directory before the first path resolution, followed by create-once train/development/confirmation access events and a terminal. A crash after `ACCESS_MAY_HAVE_OCCURRED` may never be described as unopened.

## Milestones

- [ ] **M1 — Preserve and report r2.** Verify the immutable post-result manifest, finish the PAPER/claim-ledger update, and pass every claim binding. Failure leaves the new study unimplemented; acceptance is a valid preservation manifest, required claims C076–C080 present, and zero paper-verifier failures.
- [ ] **M2 — Candidate implementation.** Add versioned configs, a single orchestration module, tests, mutation fixtures, and a tmux launcher without creating or reading scientific payloads. Acceptance is passing syntax/tests/smokes and a rendered launcher whose GPU UUID and deferred working directory are verified.
- [ ] **M3 — Candidate adversarial gate.** Submit the exact diff/configs to `/adversarial`; fix every BLOCK/REVISE finding and obtain SHIP before a generator lock exists. Failure is reachable and prevents M4.
- [ ] **M4 — Both locks before payloads.** Create the capacity and external generator locks, in that order, before either study may create any scientific JSONL. A missing lock for either study must block payload creation for both.
- [ ] **M5 — Prepare and freeze both studies.** Generate both disjoint panel sets exactly once, freeze only opaque metadata/hashes, obtain exact-freeze SHIP for both, and bind both reviews before capacity inference. Acceptance includes support, seed-disjointness, payload-access traps, and a forced-stop mutation proving no external access/training when capacity authorization fails.
- [ ] **M6 — One-shot launch.** Select a free physical GPU, UUID-lock it, start the frozen capacity owner in tmux, and verify the process plus registered opening transition. Return immediately. The external stage may open inside the same owner only after the exact hashed capacity authorization passes.

## Lifecycle and immutability

1. Create a post-result preservation manifest for transformer-realistic bridge/method r2 and snapshot pre-update PAPER/ledger.
2. Update PAPER and claim ledger; verify all selectors, pointers, and hashes.
3. Obtain `/adversarial` SHIP on this plan before experiment implementation.
4. Implement config-driven source, tests, nonpanel CPU/GPU smokes, mutation fixtures, and a launcher-render regression.
5. Obtain `/adversarial` SHIP on the exact candidate.
6. Create separate capacity and external generator locks before generating any scientific JSONL.
7. Generate panels exactly once, freeze opaque creation metadata, and obtain exact-frozen `/adversarial` SHIP for both studies without opening payloads.
8. Bind reviews, select a free UUID-locked GPU, launch once in tmux, verify RUNNING state, and return without waiting.

Result, provenance, lock, freeze, and prepared namespaces are create-once. Any pre-tmux software failure receives a terminal and a separately versioned technical successor; no deletion or same-namespace retry. The launcher fails closed on existing namespaces and holds a per-UUID lock. CUDA deterministic algorithms, `CUBLAS_WORKSPACE_CONFIG`, and fixed Python/NumPy/Torch seeds are required.

The prelock timed smoke must cover one rank sweep and 100 transformer steps, recording wall time, peak GPU memory, and projected disk. Eight hours is a hard owner-process timeout; resource budgets are 4 GiB peak GPU memory and 2 GiB result/checkpoint storage. Checkpoints are written only at the final registered step. OOM, preemption, timeout, or nonfinite loss after opening writes a technical terminal; it never triggers an automatic device, batch-size, rank, seed, or same-namespace retry.

## Tests and adversarial mutations

Before locking:

- `exact_delta_gt` and full-rank OLS must pass every nonpanel registered instance;
- zero and random controls must fail without creating endpoint missingness;
- replacing reduced-rank regression by zero must fail recovery;
- swapping `x_obs` for `delta_gt` must fail direction or collateral safety;
- the symbolic 64-vector basis test must fail if `W*` or `M` is perturbed;
- label-only and within-target delta-permutation controls must fail the joint gates;
- coordinate-mask success must change only its descriptive redundancy classification, never exact-patch qualification;
- the external routing-invariance QA must fail if clean/corrupt query indices differ or either hybrid formula is swapped;
- target, block, and split support must be exact;
- learned checkpoints and resolved configs must be hashed;
- train/dev/confirmation row IDs and seeds must be disjoint;
- candidate and freeze operations must be trapped if they attempt to access scientific JSONL;
- either missing generator lock must prevent every capacity and external payload from being created;
- a forced capacity stop must leave every external panel unopened and training false;
- the rendered tmux command must preserve deferred `/proc/self/cwd` expansion under `set -u`.

## Definition of done

- Prior r2 results verify unchanged and PAPER/ledger contain scoped claims.
- K2 remains closed and absent from all new execution paths.
- Exact candidate and exact freezes receive independent SHIP verdicts.
- Both generator locks exist before either payload is created, and both protocols are separately frozen before any scientific opening.
- The tmux process is alive on a free UUID-verified GPU and capacity development has entered its registered opening transition.
- The response returns immediately once running; it does not wait for results.

## Verification plan

Run from the repository root with `MSAE_ROOT=$PWD`:

- Run: `python -m py_compile scripts/capacity_external_validity_v1.py` — expected: exit 0 with no output.
- Run: `pytest -q tests/test_capacity_external_validity_v1.py` — expected: all unit, mutation, support, disjointness, payload-trap, and launcher-render tests pass.
- Run: `python scripts/verify_paper_claims.py --paper PAPER.md --ledger reports/paper_claim_ledger_v1.json` — expected: required claims C076–C080 are present and every ledger binding passes, regardless of unrelated future claim-count growth.
- Run: `python scripts/capacity_external_validity_v1.py candidate-preflight` — expected: config/parity checks and both nonpanel full-rank controls pass, negative controls fail, and no scientific payload is accessed.
- Run: `python scripts/capacity_external_validity_v1.py mutation-suite` — expected: every recovery, incomplete-gap, leakage, and forced-stop mutation is detected.
- Run: `python scripts/capacity_external_validity_v1.py launcher-render --gpu-uuid TEST-UUID` — expected: output contains literal deferred `$(readlink /proc/self/cwd)` and no ordinal-only GPU binding.
- Run: `python scripts/capacity_external_validity_v1.py verify-freezes --opaque` after locks/preparation — expected: hashes/configs/support are valid while scientific JSONL access remains trapped.
- Run: `python scripts/capacity_external_validity_v1.py launch-preflight --gpu-uuid "$UUID"` after review binding — expected: exact reviews, freezes, absent output namespaces, CUDA mapping, and per-UUID lock all pass.
- Run: `tmux has-session -t "$SESSION" && nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader && test -s "$LOG"` — expected: the session is alive, its process uses the selected UUID, and the log records `CAPACITY_DEVELOPMENT_OPENED`.
