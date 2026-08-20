# Draft preregistration — Naturalistic potency-versus-precision confirmation v1

**Status:** design draft only; no study key, source reservation, model forward, result namespace, or
training authorization exists.

## Question

On genuinely natural or naturally sourced behavioral tasks, do frozen token-local linear and imported
SAE-derived components recover a target behavioral change without matched-sham movement or collateral
damage, and do reconstruction, probe recovery, variance capture, or geometric stability predict that
joint control?

This is a confirmation of the potency-versus-precision distinction, not a retry of K2 branch naming.

## Development/confirmation firewall

1. **Opened development pool.** Candidate datasets, prompt formats, answer contrasts, unrelated-context
   matchers, grammatical transformations, and effect-support rules may be developed only here.
2. **Task nomination.** At most one context-retrieval task and one syntactic-agreement task may be
   nominated. Nomination uses support, effect completeness, lexical balance, and sham validity—not
   favorable component or method outcomes.
3. **Freeze.** Exact dataset versions, document IDs, preprocessing, tokenizer outputs, prompts,
   transformations, models, layers, methods, metrics, thresholds, estimators, code hashes, and decision
   rules are frozen before confirmation access.
4. **Untouched confirmation pool.** Confirmation uses disjoint documents, template families where
   templates exist, named entities/lexical blocks, and dataset sources. It is opened once.
5. No confirmation row may be removed or relabeled using a component score, patch result, proxy value,
   or method identity.

## Candidate behavioral modules

### A. Context retrieval

- Natural documents/questions with a one-token or prespecified two-choice answer contrast.
- Base: matched unrelated context plus the unchanged question.
- Counterfactual: the true supporting context plus the unchanged question.
- Sham: a distinct unrelated context matched on dataset, length, answer-frequency stratum, and question
  type, with no answer string or supporting evidence.
- The true, base, and sham contexts are selected without model logits. Development establishes a
  deterministic matcher and a maximum context truncation policy that always retains the question.
- Primary behavior: correct-minus-contrast log-odds.

### B. Natural-source syntactic agreement

- Naturally sourced sentences with a prespecified subject--verb number dependency and at least one
  matched intervening-noun stratum.
- Base/counterfactual: a grammatical number intervention whose target continuation changes between a
  prespecified singular/plural verb pair.
- Sham: a lexical or punctuation change matched on token count and local surface distance that does not
  change the agreement target.
- Primary behavior: grammatical-minus-ungrammatical continuation log-odds.
- Development must demonstrate that the transformation preserves sentence plausibility and that the
  sham is nontrivial but agreement-inactive.

Only modules that pass every prescore gate on opened development are eligible for nomination. The
study may proceed with one nominated module; failure of one module does not invalidate the other.

## Models, layers, and methods

- Reuse the exact frozen Pythia-160M, Pythia-410M, and Qwen2.5-0.5B revisions and early/middle/late
  layers from proxy-control v2. This supplies two model families and three model-level units without
  new decomposition training.
- Import exact v1 K1, equal K2, asymmetric K2, and capacity-swapped K2 artifacts where applicable.
- Primary nonlearned methods: PCA, random orthogonal subspace, task projection, linear erasure,
  paired-delta basis, and the frozen development-only behavior-gradient estimator.
- No new SAE, K2, shared-branch, supervised context/local, or controller training is authorized.
- Reconstruction and sparsity comparisons remain within method class. Constant total TopK is reported
  as unidentifiable rather than a null association.

## Prescore feasibility gates

Each nominated module must independently clear, on opened development and again label-only on
confirmation before component scoring:

- at least **100 genuine document blocks per source** and **200 total confirmation blocks**;
- at least **50 blocks per answer/orientation stratum**;
- no document contributes more than two components;
- no lexical/name block contributes more than 2% of a source;
- at least four held-out surface/template families if templating is used;
- identical registered answer-token support and no truncation of the question/answer suffix;
- nontrivial base, counterfactual, and sham prompts for every tokenizer;
- label-only hierarchical bootstrap coverage at least 0.95;
- no single document changes a raw-effect estimate by more than 10% in leave-one-document-out QA.

Failure makes only that module ineligible. Source substitution after confirmation prescore is
forbidden.

## Behavioral-effect gate

The primary effect floor remains the v2 value: absolute natural counterfactual log-odds change at
least **0.25**. Before component scoring, a module/model/source is eligible only if:

- at least **80%** of confirmation blocks clear the effect floor;
- both effect signs have at least 20 blocks when the design permits both signs;
- the full counterfactual improves the intended answer/grammatical contrast in the prespecified
  direction; and
- sham effects are below 25% of the true-effect magnitude in aggregate with an upper hierarchical
  interval below 0.35.

This gate evaluates whether the behavioral task exists for the model. It does not inspect any
component or method.

## Component evaluation

For every frozen component:

1. **Recovery:** patched target-log-odds movement divided by the signed natural effect.
2. **Sham specificity:** `(target patch effect - sham patch effect) / signed natural effect`.
3. **Representational specificity:** target-delta capture minus matched-sham capture.
4. **Collateral safety:** KL over logits excluding the registered answer pair, plus a task-specific
   collateral set frozen during development.
5. **Necessity:** erasure effect, kept distinct from sufficiency/recovery.
6. **Patch scale:** target-patch norm divided by natural-delta norm; rows above 2.0 are ineligible,
   not clipped.

Primary intervals use a nested bootstrap over model, layer within model, imported seed within method,
source, document block, and surface realization. Models—not rows—are the highest inferential unit.

## Frozen decision thresholds

A method/module/stage passes only if:

- component eligibility is at least 0.80;
- the 95% hierarchical lower bound for recovery exceeds 0.10;
- the 95% hierarchical lower bound for sham specificity exceeds 0.10;
- the 95% hierarchical upper bound for collateral KL is below 0.02;
- both source-transfer directions pass;
- at least two of the three model units pass at the same stage; and
- no prespecified collateral behavior has a material adverse effect.

Equivalence uses a smallest meaningful absolute effect of 0.10. “Did not pass” and “equivalent to
small” remain distinct.

## Positive and negative controls

Before confirmation component scoring:

- an end-to-end synthetic causal model, using the same patching and aggregation code, must allow a
  ground-truth projector and development-only behavior oracle to pass;
- a random projector must remain below 0.25 specificity;
- an answer-direction patch must move the intended log-odds;
- a norm-matched orthogonal patch must not satisfy the joint criterion; and
- gate failure blocks component scoring but leaves task measurability results reportable.

## Result-independent interpretation

1. **Unsupervised methods fail; behavior oracle jointly passes:** the object is locally separable but
   reconstruction objectives do not identify it. A later supervised comparison may be proposed.
2. **Potency rises while collateral safety fails again:** confirm the potency-versus-precision gap on
   natural behavior; do not train another decomposition.
3. **Only an early stage passes in two models:** nominate a depth-dependent integration hypothesis.
4. **No method passes after end-to-end controls pass:** no evaluated local linear component satisfies
   the joint criterion at these sites; do not generalize to all linear or nonlinear controllers.
5. **Task measurability fails:** retire the task without source-shopping; it contributes no component
   result.
6. **Simple projection passes and learned methods do not:** prefer the projection and frame complexity
   as unnecessary.

## Reporting and stopping

- Report every opened module, including prescore and effect-gate failures.
- Keep natural effect, recovery, sham specificity, collateral safety, and patch norm separate.
- No threshold change, row deletion, method addition, or model substitution after confirmation
  opening.
- No learning is automatically authorized by this draft or by a favorable exploratory contrast.
- The current paper remains publishable regardless of whether this successor is opened or positive.
