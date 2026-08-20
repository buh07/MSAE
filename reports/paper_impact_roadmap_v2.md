# Publication-impact roadmap after proxy-control v2

## Decision

The current manuscript is scientifically coherent but not yet a strong ICLR main-track submission.
The most important reason is not that the result is negative. It is that the broad claim that
interpretability or reconstruction proxies need not imply steering utility is already supported by
larger public benchmarks. The paper needs a distinctive, externally validated contribution rather
than more history, more K2 seeds, or another candidate factor.

The strongest defensible distinction is:

> Evaluate **joint controllability** rather than steering potency alone: target recovery, signed-sham
> specificity, collateral behavioral damage, replication, and eligibility at a matched intervention
> budget.

That conjunction is closer to what practitioners need when selecting a representation for safe
control. It also preserves the project's best methodological contribution: favorable proxy or potency
scores cannot substitute for precision and collateral safety.

## Why this positioning is still viable

- SAEBench shows that gains on unsupervised proxies do not reliably translate to practical
  performance, over more than 200 public SAEs and multiple metrics:
  https://proceedings.mlr.press/v267/karvonen25a.html
- AxBench shows that simple prompting, finetuning, and representation baselines can outperform SAEs
  for steering:
  https://proceedings.mlr.press/v267/wu25a.html
- A 2026 study directly analyzes interpretability--utility rank agreement across 90 SAEs, three LLMs,
  five architectures, and six sparsity levels:
  https://openreview.net/pdf?id=5KY99GFqZD
- Causal-probing work already formalizes completeness--selectivity tradeoffs and links reliable
  interventions to behavior:
  https://aclanthology.org/2025.ijcnlp-long.47/
- Recent work predicts SAE steering side effects from pre-intervention statistics and selects cleaner
  features on held-out contexts:
  https://arxiv.org/abs/2606.08365

Therefore “proxies do not imply utility” is not novel enough. A competitive paper must show what
existing benchmarks omit, compare directly to them, and provide a reusable decision procedure.

## Tier 1: must-do evidence

### 1. Standard-SAE joint-control benchmark

Evaluate the frozen v2 joint endpoint on public, standard artifacts rather than only custom K1/K2
objects:

- public SAEs from SAEBench or model-family releases;
- DiffMean, PCA, random orthogonal, task projection, and LEACE;
- AxBench's ReFT-r1 and CAA-style/simple steering baselines where applicable;
- a supervised task dictionary or behavior-supervised linear skyline;
- K2 only as the motivating case study, not the benchmark's center.

Use at least four model units across three genuinely distinct families, three layer stages, multiple
SAE architectures or sparsity budgets, and branch/feature selection on development data only.

**Why it helps:** it makes the result legible relative to the community's actual methods. If the joint
failure survives, the paper establishes that published potency comparisons omit a safety/precision
axis. If standard methods pass, the paper discovers which inductive bias repairs the gap.

### 2. Natural downstream behavior with collateral outcomes

Choose one or two natural tasks prospectively, not many screened concepts. Good candidates have an
unambiguous behavioral contrast and registered collateral outcomes, for example:

- context retrieval or factual recall with unrelated fact retention;
- subject--verb agreement with matched lexical and distance controls;
- one established AxBench concept with held-out generation scoring;
- IOI as a known-circuit positive-control task, not the sole scientific task.

Measure necessity, sufficiency, multi-token persistence, task success, fluency/perplexity or output
quality, and unrelated-task damage. Preserve local log-odds recovery and next-token KL as mechanistic
intermediates.

**Why it helps:** the current natural endpoint is ineligible. Passing natural behavior would remove the
largest external-validity objection; a clean failure after validated positive controls would make the
negative result much stronger.

### 3. Matched-budget three-dimensional frontiers

For every method, sweep intervention strength and compare methods at matched patch norm, target
logit movement, or another preregistered budget. Report a frontier over:

1. target recovery or completeness;
2. signed-sham specificity;
3. collateral behavior damage.

Use model-family panels, hierarchical uncertainty, and dominance probabilities. Threshold decisions
remain frozen, but continuous frontiers become the primary scientific visualization.

**Why it helps:** a single operating point can make a potent method look unsafe merely because it is
stronger. Matching budget makes “potency versus precision” an estimand rather than a slogan.

### 4. End-to-end positive control

Require the complete extraction--selection--patching--behavior pipeline to recover a known causal
mechanism. A supervised IOI dictionary or a small synthetic transformer with known private/shared
features is preferable to metric-only arrays. Keep a random negative and a correlated nuisance
positive control.

**Why it helps:** if the evaluator cannot recover a known circuit, real-model failures are ambiguous.
If it can, failure becomes evidence about the representation or method rather than the measurement
stack.

## Tier 2: the differentiating experiments

### 5. Compare proxy selection with side-effect-aware selection

Prospectively select components using:

- reconstruction, sparsity, probe recovery, and CKA;
- activation magnitude/frequency;
- decoder geometry, coactivation, direct-logit footprint, and other predictors motivated by
  https://arxiv.org/abs/2606.08365;
- a held-out collateral-aware selector.

Fit selectors on opened development models/tasks and test rankings on held-out model families and
behaviors. The target is not raw steering but probability of lying on the joint safe-control frontier.

**Why it helps:** it converts the negative observation into actionable method selection. A benchmark
that says “these proxies fail” is less useful than one that identifies a predictor or certifies that no
available predictor transfers.

### 6. Supervised skyline versus unsupervised decomposition

Validate the supervised skyline on the positive-control task, then compare it at equal rank, active
budget, and intervention norm.

Prospective interpretations:

- skyline passes, unsupervised methods fail: semantic/counterfactual supervision is the missing
  inductive bias;
- both pass: existing K2 objectives/capacity were the problem;
- neither passes after evaluator validation: local linear factorization is inadequate at those sites;
- simple DiffMean/projection matches the skyline: use the simpler method and make simplicity a result.

**Why it helps:** it localizes failure to objective, representation site, or evaluator instead of
leaving “SAEs failed” as an underdetermined diagnosis.

### 7. Real model-level generalization

Treat models, not layers or prompt rows, as the highest inferential unit. Use leave-one-model-family-out
prediction for proxy associations and side-effect selectors. Layers are repeated measures nested
within model; templates/vocabularies are blocks nested within task.

**Why it helps:** nine model--layer clusters are not nine independent models. Model-family holdout is
the minimum evidence for a general selection rule.

## Tier 3: paper and artifact changes

### 8. Rewrite benchmark-first

Recommended main-text order:

1. joint-control problem and literature gap;
2. benchmark endpoint and positive controls;
3. standard methods/models/tasks;
4. primary frontiers and held-out selection;
5. supervised skyline and depth analysis;
6. K2 as a diagnostic case study;
7. measurement postmortems in an appendix.

Move Attempts 1--14, parser development, RoPE numerical QA, and closed relational programs to a
technical appendix or separate audit paper.

**Why it helps:** ICLR reviewers evaluate a contribution, not the persistence of a research process.
The current chronology hides the most important prospective result in Section 4.11.

### 9. Release a one-command benchmark

Provide:

- a versioned schema for potency, sham specificity, collateral, eligibility, and uncertainty;
- adapters for standard SAE repositories and AxBench/SAEBench outputs;
- fixed development/confirmation splits;
- a smoke-tested positive control;
- result envelopes and hash manifests;
- a leaderboard showing full frontiers, not a scalar that can conceal harm.

**Why it helps:** an actionable artifact can be a contribution even if many methods fail. It also
makes the paper relevant to SAE selection rather than only to one architecture history.

### 10. Statistical negative-result upgrade

Predefine a minimum meaningful joint effect and use equivalence/noninferiority tests for target
recovery, sham specificity, and collateral damage. Power calculations must use the true model/task
block structure.

**Why it helps:** “zero passes” can reflect low power. Showing that the upper confidence bound is below
useful control—or that damage exceeds an acceptable margin—supports a materially negative claim.

## Recommended resource packages

### Minimum credible package

- Rewrite the manuscript benchmark-first.
- Run standard released SAEs and simple baselines on one fresh natural task.
- Include three model families and model-level inference.
- Add matched-norm frontiers and an end-to-end positive control.
- Include a supervised skyline.

This is the smallest package that addresses novelty, external validity, and evaluator validity at
once.

### Strong ICLR package

- Everything in the minimum package.
- Two natural behaviors with distinct collateral registries.
- Four or more model units across three families and three depths.
- Multiple standard SAE architectures/sparsity budgets.
- Held-out comparison of conventional versus side-effect-aware selectors.
- Public benchmark adapters and leaderboard.

### If compute or data are insufficient

Do not dilute the paper with more K2 seeds, signal screens, or relational feasibility studies. Narrow
the title and abstract to a rigorously controlled Pythia/K2 case study, make the measurement audit a
central contribution, and consider a venue suited to careful negative or benchmark-methodology work.
That is preferable to claiming broad proxy failure from an ineligible natural endpoint.

## Frozen result-independent decision tree

1. **Joint failure across public SAEs, standard baselines, models, and natural tasks**
   → claim that potency-oriented evaluation systematically overstates collateral-safe control.
2. **Supervised skyline passes; unsupervised methods fail**
   → claim that counterfactual supervision supplies the missing semantic inductive bias.
3. **Side-effect-aware selection transfers**
   → contribute a practical pre-intervention selection method and benchmark.
4. **Only early layers pass**
   → claim a depth-dependent loss of simple modularity during contextual integration.
5. **Simple baselines pass or match learned methods**
   → make simplicity and evaluation discipline the result; do not train more K2.
6. **No method passes, but the end-to-end positive control does**
   → support a local nonseparability result at the tested sites.
7. **The positive control fails**
   → stop scientific interpretation and repair the evaluator.
8. **Natural effect support fails prospectively**
   → declare that task ineligible; do not substitute tasks until one passes.

## Deprioritized work

- more seeds, capacity, or incoherence for K2;
- a private/private/shared branch without an identified shared causal effect;
- a broad new screen for linguistic factors;
- reopening relational v4 or source-shopping for v5;
- metric-threshold changes based on favorable outcomes;
- a synthetic-only SAE benchmark that duplicates SynthSAEBench;
- paper expansion without a related-work distinction and fresh external-validity evidence.
