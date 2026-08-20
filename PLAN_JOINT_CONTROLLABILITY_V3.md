# PLAN — Joint controllability benchmark v3

## Goal

Run a separately versioned, prospective natural-text benchmark asking whether released SAE and linear
representation methods jointly provide target potency, signed matched-sham specificity, collateral
safety, and replication. Preserve the closed K2 program, use no K2 training, validate the complete
intervention evaluator with an end-to-end causal positive control, and stop this session once frozen
workers are alive in tmux.

## Non-goals

- Do not edit, retry, rescore, or reopen proxy-control v1/v2 or any K2 namespace.
- Do not train any SAE or K2 model.
- Do not call a Wikitext hash partition an independent natural domain.
- Do not select rows, methods, budgets, models, or thresholds from component outcomes.
- Do not wait for scientific results in this session.

## Representational benchmark

### Natural task

Use one prespecified naturally sourced Wikitext-103 continuation task. Each component uses one target
article and two disjoint donor articles. The coherent condition supplies a remote prefix plus a common
local suffix; base and sham replace only the remote prefix with two distinct, length-matched natural
prefixes. The outcome is the next natural token against a morphology-matched natural contrast, plus
teacher-forced eight-token continuation loss. Document hashes assign rows before model access to two
opened development partitions and two untouched-at-freeze test partitions, WIKI_A and WIKI_B.

The partitions test transfer within a corpus, not cross-domain replication. Each source has 64
development and 128 test documents; target and donor documents are disjoint and contribute once.
Rows and tokenizer-specific token IDs are frozen before any model forward.

### Models and released SAEs

- GPT-2 small, layers 1/6/10, with released OpenAI-v5 32k TopK residual-post SAEs.
- Pythia-160M-deduped, layer 8, with the SAEBench 4k TopK primary SAE and Standard, Gated,
  JumpReLU, and Matryoshka descriptive variants.
- Gemma-2-2B, layers 0/12/25, with canonical-width Gemma Scope 16k JumpReLU residual SAEs.

The formal `public_sae_primary` method uses the prespecified primary SAE for each model. Pythia-only
architecture variants are descriptive and cannot satisfy model replication alone. Revisions and exact
weight/config hashes are frozen.

### Other methods

Evaluate DiffMean/CAA, paired-delta SVD, task projection, LEACE-style covariance-whitened direction,
PCA, random orthogonal, rank-one ReFT-style behavior-gradient direction, and a rank-16
behavior-supervised skyline. The last two fit only on opened development rows and are evaluation
skylines explicitly authorized by this new protocol; they do not train the language model or an SAE.

### Matched intervention budgets

Evaluate norm ratios 0.25, 0.5, and 1.0 relative to each row's natural activation delta. Actual and
sham patches receive the same norm. Report target recovery, signed-sham specificity, non-target next-
token KL, eight-token continuation recovery/damage, unrelated-document continuation damage,
necessity from removing the selected full-minus-base component, and continuous three-axis frontiers.
No operating point replaces another after opening.

## Gates

1. Label-only/tokenizer prescore: 128 test documents per source, one target/donor contribution,
   exact prompt-length matching within tokenizer, one-token registered target/contrast, disjoint
   development/test document hashes.
2. End-to-end causal positive control: ground projector and supervised skyline pass recovery,
   specificity, and collateral thresholds; random control remains below specificity cap.
3. Model/task effect gate: at least 80% of test blocks have coherent-prefix effect >0.25; aggregate
   sham magnitude is below 25% of coherent effect with upper bound below 0.35.
4. Joint method gate: eligibility >=0.80, lower 95% document-bootstrap bounds for recovery and signed
   specificity >0.10, upper bound for collateral KL <0.02, both source-transfer directions, and at
   least two model families at one registered budget.

Failure is endpoint-specific. No source, budget, or threshold substitution is authorized.

## Lifecycle

1. Create deterministic label-only rows and download only pinned public SAE assets.
2. Unit-test row disjointness, matched budgets, public-SAE loaders, gates, and no K2 training path.
3. Run `/adversarial` on the exact candidate and repair blockers.
4. Create a freeze binding code, config, rows, model revisions, SAE assets, thresholds, review, and
   the preserved architecture closure.
5. Preflight the frozen candidate, select free physical GPU UUIDs, launch one worker per model/layer,
   plus CPU positive-control and aggregate sessions in tmux.
6. Return immediately after confirming sessions and initial logs are alive.

## Milestones

- [ ] **M1: frozen prescore candidate** — prepared rows, pinned SAE manifest, config, tests, and
  architecture hook smoke are complete without scientific model scoring.
- [ ] **M2: reviewed implementation** — targeted tests pass and `/adversarial` returns SHIP on the
  exact candidate with public-SAE lineage, matched budgets, lifecycle, and closure checked.
- [ ] **M3: launched benchmark** — freeze and launch manifests exist and all positive-control,
  worker, and aggregate tmux sessions are alive on distinct free GPU UUIDs.

## Definition of done

- [ ] `reports/architecture_program_closure_v2.json` is unchanged and denies K2 training.
- [ ] Prepared rows are deterministic, document-disjoint, tokenizer-valid, and created without model
  forward or logit filtering.
- [ ] Public SAE encode/decode smoke tests are finite and dimensionally consistent at every registered
  layer; raw loader equations and normalization are recorded.
- [ ] No language-model or SAE parameter has `requires_grad=True`; supervised methods fit only cached
  development activations/gradients.
- [ ] Positive-control failure blocks every real worker before model loading.
- [ ] Candidate review is SHIP and bound to the freeze candidate hash.
- [ ] All tmux workers are alive when this session ends; results are not awaited.

## Verification plan

- Run `python -m py_compile` and the targeted v3 pytest module.
- Run deterministic preparation twice in temporary namespaces and compare JSONL hashes.
- Verify every pinned model/SAE revision and asset SHA-256, and run format-specific finite
  encode/decode tests.
- Run zero-patch exact-replay and nonzero-patch finite-change smoke checks on GPT-2, Pythia, and
  Gemma before the scientific freeze.
- Verify the closure hash before and after launch and scan the candidate for any K2/SAE training call.
- Run frozen preflight, launch through the reviewed tmux launcher, then check session liveness, unique
  GPU UUID assignment, and initial logs without waiting for outputs.

## Risks and mitigations

- Wikitext partitions are not independent domains: label them within-corpus transfer and require a
  later corpus-level confirmation for generalization.
- Public SAE formats differ: implement format-specific loaders and test reconstruction equations
  against each pinned config; never silently coerce a failed loader.
- GPT-2 SAE layer-normalization directions are evaluated in normalized coordinates and mapped to raw
  space only by unit decoder directions plus a matched raw patch norm; disclose this approximation.
- Stronger patches can look less safe: freeze three norm ratios and compare frontiers.
- Small models may fail the behavioral effect gate: preserve the ineligible endpoint rather than
  changing task construction.
- Runtime is large: use seven independent GPU workers and an aggregate waiter; no worker shares a GPU.

## One-way doors

Opening test activations is irreversible. It occurs only after candidate review and freeze. Downloading
pinned public SAE assets and building label-only/tokenizer-only rows is technical preparation, not
scientific opening.
