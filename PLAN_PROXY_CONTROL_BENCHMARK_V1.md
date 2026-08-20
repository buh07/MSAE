# PLAN — Proxy-to-Control Benchmark v1

## Goal

Create and launch a separately versioned experiment asking whether reconstruction, sparsity,
probe recovery, and geometric stability predict selective downstream control across matched
decomposition methods, transformer layers, model scales, and three prespecified concepts.

The experiment is a new benchmark, not a retry of K2, Attempt 14, relational measurement v4, or an
authorization for relational v5. It must produce useful evidence under every frozen decision branch:
proxy/control dissociation, supervised-only recovery, depth dependence, universal failure, or a
capacity-confounded original K2 result.

## Non-goals

- Do not alter or rerun relational measurement v4 or authorize v5.
- Do not source-shop natural corpora or reopen any signed terminal.
- Do not train more seeds of the unchanged historical K2 configuration as an architecture search.
- Do not claim confirmatory results before the jobs finish and receive post-result claim review.
- Do not interpret representation change alone as a causal behavioral effect.

## Constraints and frozen scope

- Models: exact local revisions of `EleutherAI/pythia-160m-deduped` and
  `EleutherAI/pythia-410m`, plus `Qwen/Qwen2.5-0.5B` as a second model family.
- Layers: early, middle, and late block-output states for each model.
- Development activation sources: cached Wikitext-103 and Dolly training text, with source hashes and
  fixed row caps recorded before model inference.
- Evaluation sources: two deterministic, disjoint controlled-language generators (`SOURCE_A` and
  `SOURCE_B`) with component-disjoint train/test folds and at least 128 components per source. These
  are fresh intervention panels, not independent natural-corpus replications; Wikitext and Dolly
  remain opened development activation sources and are reported separately.
- Concepts: relative sequential distance, lexical identity/content, and coherent-context
  accumulation. Relational syntax is secondary and is not a gate for the primary benchmark.
- Learned methods: standard K1 TopK SAE; equal-capacity K2; historical-ratio asymmetric K2; and
  capacity-swapped K2. Three seeds are frozen for learned methods.
- Nonlearned methods: PCA, random projection, task projection, covariance-adjusted linear erasure,
  and a paired-delta supervised oracle. All concept assignment occurs on one source and is evaluated
  in both source-transfer directions.
- Common metrics: reconstruction, active-code sparsity, probe recovery, cross-seed CKA, leakage and
  selectivity, intervention specificity, downstream log-odds effect, and collateral non-target KL.
- Normalized behavioral recovery is eligible only when the full natural counterfactual changes the
  registered answer log-odds by at least 0.25. Raw effects are always retained, and neither near-zero
  denominators nor clipping may manufacture a finite normalized success.
- Negative inference uses confidence intervals and a frozen smallest effect of interest; final
  aggregation reports equivalence separately from failure to pass. The primary normalized
  specificity smallest effect of interest is 0.10; the bootstrap count is 500.
- Every run is create-once, config-driven, seeded, offline, and writes environment, model, data,
  config, code, and artifact hashes.

## Codebase grounding

- `scripts/train_msae_k2.py` provides the existing TopK branch semantics and activation extraction
  convention; the benchmark will implement a smaller isolated equivalent rather than mutate the
  historical trainer.
- `scripts/run_atlas_context_local_v10.py` demonstrates exact-revision offline model loading,
  block-output intervention hooks, GPU UUID attestation, and create-once result namespaces.
- `scripts/atlas_context_local_v10.py` provides canonical JSON/hash helpers and the existing
  coherent/unrelated context distinction.
- Local caches contain the exact Pythia revisions and both development text sources.

## Approach

### Data and interventions

Generate two disjoint controlled suites. Each component contains a base and counterfactual prompt,
the two single-token answer candidates, a target sequence index, concept label, nuisance metadata,
and a matched sham. Tokenizer eligibility is checked before inference. The generators vary surface
templates and vocabularies across sources, preventing exact-string transfer.

For each model/layer, cache training activations and all controlled prompt activations/logits once.
Each method maps an activation to a target component and complement. Necessity erases the target
component; sufficiency adds the counterfactual target-component delta. A block-output hook applies
the patch at the registered target token. The primary behavioral endpoint is the fraction of the
full-activation counterfactual log-odds effect recovered by the component. Collateral damage is KL on
non-target vocabulary logits plus matched-sham movement. Patches whose norm exceeds twice the matched
natural activation delta are reported but ineligible for the primary control endpoint.

### Matched decompositions

All learned methods use the same centered activation cache, optimizer family, update count, batch
size, and total active-code budget where their definition permits. K2 branch identity is selected on
the development source up to permutation. K1 concept atoms are selected on the development source
only. Linear methods use the same frozen rank. Results are reported at both fixed budget and observed
reconstruction quality; no post-result retuning is allowed.

### Synthetic positive controls

An independent GPU job generates known position-private, lexical-private, and shared latent factors;
sweeps correlation, capacity asymmetry, and linear/nonlinear mixing; and evaluates the same learned
decompositions. Ground-truth subspace recovery and intervention specificity are primary. This is a
mechanism/positive-control module, not a substitute for real-model behavior.

### Aggregation

A CPU aggregation job waits for all nine model/layer shards and the synthetic job, verifies hashes and
finite metrics, then fits a hierarchical source/model/layer bootstrap for proxy-to-control
associations. Nine model/layer clusters still provide limited power, so association intervals and
equivalence are primary and point correlations cannot alone support a systematic-generalization
claim. It reports proxy metrics individually; it does not construct an outcome-selected composite.
The frozen interpretation table is copied verbatim into the result.

## Alternative considered

Reusing Attempt-14 caches would be faster, but would cover one model and one layer and cannot support
the generality or downstream-behavior claim. A broad relational-object successor was also rejected:
v4 did not authorize v5 and relational matching remains under-supported. The controlled two-source
benchmark is narrower, independently supported by construction, and directly addresses the ICLR
review blockers.

## Milestones

- [ ] **Protocol candidate** — write config, plan, source manifest, and result-independent decision
   table; acceptance: source hashes resolve, old v4 hashes are unchanged, output namespace is absent.
- [ ] **Core math and data** — implement deterministic generators, TopK models, linear methods, CKA,
   intervention metrics, equivalence intervals, and create-once artifacts; acceptance: targeted unit
   tests fail before implementation and pass after it.
- [ ] **Worker and synthetic jobs** — implement offline exact-revision extraction, matched training,
   downstream patching, and synthetic DGPs; acceptance: CPU/tiny smoke produces finite schema-valid
   output and would detect label leakage, branch swapping, NaNs, or output reuse.
- [ ] **Final freeze and review** — hash the complete candidate (plan, config, generators, analysis,
   tests, environment, and source manifests) only after implementation; review it for protocol drift,
   pseudo-replication, off-manifold controls, unequal budgets, missing behavioral endpoints, and
   accidental v4/v5 access; acceptance: no unresolved BLOCK finding.
- [ ] **Launch** — allocate only currently free GPU UUIDs, launch six Pythia model/layer shards, one
   sequential three-layer Qwen shard, one synthetic shard, and a dependent aggregator in named tmux
   sessions; acceptance: every session is alive, each job has written STARTED metadata, and GPU
   processes appear on the assigned devices.

## Definition of done

- A frozen config contains exact models/revisions, layers, methods, seeds, source sizes, metrics,
  smallest effects, and all result-independent interpretations.
- V4 prepared/result/authorization/closure hashes match their preserved values and no v5 artifact is
  created.
- Unit and smoke tests pass, including deterministic rebuild, source disjointness, branch
  permutation, intervention hook locality, finite metrics, and create-once failure.
- A reproducibility record covers seeds, deterministic flags, local paths, environment versions,
  source hashes, and code hashes.
- Nine real model/layer experiments (six Pythia shards plus a queued three-layer Qwen shard), one
  synthetic positive-control shard, and one aggregator are running under tmux on preflighted free
  GPUs/CPU.
- The session ends after launch verification without waiting for scientific results.

## Risks and mitigations

- **Off-manifold patches:** compare against full natural activation deltas, matched-norm random
  deltas, and shams; report patch norm ratio and never infer causality from representation distance.
- **Tokenizer filtering changes support:** generate excess components, apply one frozen eligibility
  rule, and fail before inference if either source misses the floor.
- **Method-budget mismatch:** report active budget and reconstruction explicitly, include both equal
  and historical-ratio K2, and avoid declaring a winner from FVU alone.
- **Pseudo-replication:** resample controlled components, sources, model/layer units, and seeds at
  their genuine levels rather than treating tokens as independent.
- **Negative-result underpower:** freeze the smallest effect of interest and distinguish equivalence,
  inconclusive, and positive intervals.
- **Large launch surface:** sharded create-once outputs, per-job heartbeat/STARTED files, and an
  aggregator that refuses partial or hash-drifted inputs.

## One-way doors

Opening the fresh controlled evaluation suite to model inference is a one-shot scientific action.
The config, generators, thresholds, code hashes, and decision table must therefore be frozen before
launch. Historical v4 and v5 namespaces remain outside the candidate inventory.

## Verification plan

- `pytest -q tests/test_proxy_control_benchmark_v1.py`
- `python scripts/proxy_control_benchmark_v1.py freeze --config configs/proxy_control_benchmark_v1/run.json`
- `python scripts/proxy_control_benchmark_v1.py smoke --config ... --output ...`
- repeat smoke and compare canonical result bytes
- run repro-guard searches for seeds, deterministic settings, hardcoded paths, secrets, and hashes
- run fallback `/adversarial` on this plan and the final candidate because sub-agent delegation is
  not authorized in this turn
- preflight `nvidia-smi`, launch tmux sessions, then verify tmux panes, STARTED records, and GPU PIDs
