# PLAN — Proxy-Control v2 Paper Integration and Publication-Impact Review

## Goal

Close the current K2/position-content training program after the completed prospective v2 benchmark,
produce a create-once analysis-only companion from its cached rows, integrate the supported
potency-versus-precision result into `PAPER.md` and the quantitative claim ledger, draft—but do not
open—a genuinely naturalistic successor study, and adversarially assess what still prevents the paper
from making a strong, relevant venue-level contribution.

## Non-goals

- Do not edit, rescore, overwrite, or rerun proxy-control v1 or v2.
- Do not change any frozen threshold, equivalence classification, controlled row, method decision,
  synthetic result, or Qwen operational-recovery record.
- Do not train more K2 variants, a context/local model, a shared-branch model, or a supervised
  controller.
- Do not perform a new model forward, open a fresh confirmation panel, or select a naturalistic task
  using favorable v2 outcomes.
- Do not claim universal SAE failure, absence of encoded information, or existential linear/nonlinear
  nonseparability.
- Do not make publication of the current paper conditional on a future positive result.

## Constraints and evidence policy

- The authoritative v2 result is
  `results/proxy_control_benchmark_v2_20260808/aggregate/result.json`, bound by its complete terminal
  and the frozen candidate hash.
- The post-result claim review is
  `reports/claim_review/proxy_control_benchmark_v2_post_result_claim_review.md`; all manuscript claims
  must respect its `REVISE` verdict.
- V2's strongest negative is conjunctive: zero evaluated method summaries passed eligibility,
  recovery, sham specificity, collateral safety, both transfer directions, and model replication.
  Positive but unsafe effects must remain visible.
- Natural QA remains descriptive because its approximately 0.65 eligibility is below the frozen 0.80
  requirement.
- SOURCE_C and SOURCE_D are generated panels from one generator. Cross-source transfer is not
  equivalent to natural-domain replication.
- Every new quantitative sentence in `PAPER.md` receives exact path/hash/JSON-pointer bindings in
  `reports/paper_claim_ledger_v1.json` and must pass `scripts/verify_paper_claims.py`.
- Analysis outputs are create-once, deterministic, and declare zero new model forwards.

## Codebase grounding

- Deterministic query
  `/jumbo/lisp/f004ndc/.agent-workspace/bin/query def aggregate --lang python --path
  /jumbo/lisp/f004ndc/experiments/wip/MSAE/scripts/proxy_control_benchmark_v2.py` locates v2 aggregation
  at `scripts/proxy_control_benchmark_v2.py:1032`.
- Deterministic query for `paper_claim_ledger_v1` shows the ledger is consumed only by the frozen v2
  inventory and `scripts/verify_paper_claims.py`; the latter's `main` is at line 15.
- V2 component-level evidence is stored in nine create-once
  `shards/*/component_metrics.jsonl` files; method summaries are in `shards/*/metrics.jsonl`.
- The current manuscript ends the quantitative proxy section at v1 and therefore does not yet report
  v2's prospective results.

## Approach

### 1. Durable program closure

Create a new signed-by-hash decision artifact rather than editing prior closure records. It will bind
the v2 aggregate, synthetic gate, freeze, claim review, and Qwen launch-recovery record and state that
no K2/context-local/shared/supervised training is authorized. It will distinguish architecture
closure from permission to pose a separately versioned naturalistic measurement question.

### 2. Cached v2 analysis companion

Build a standalone script that imports no transformer or model-training module and verifies all v2
terminal/result hashes before analysis. It will write a new create-once namespace containing:

1. a gate-failure waterfall by method, concept, and gate;
2. recovery-versus-collateral and specificity-versus-collateral Pareto tables/plots;
3. early/middle/late trajectories separated into learned and linear classes;
4. K2 target-branch/capacity assignments and negative intervention-specificity diagnostics;
5. concept/model/source/seed stratification;
6. naturalistic eligibility and effect distributions, labeled descriptive;
7. an exact import manifest and result record declaring zero new forwards.

The companion will report the frozen hierarchical summaries rather than recomputing alternative
endpoints. Component rows may be aggregated for figures, but no frozen score or decision will be
replaced.

### 3. Manuscript and claim-ledger integration

Add a prospective v2 subsection after v1, update the abstract, positive/negative interpretation,
capacity mechanism, limitations, artifact map, future-work decision, and conclusion. The framing will
be “potency is not precision”: the benchmark finds behaviorally active directions, yet no evaluated
method achieves the complete replicated and collateral-safe criterion. Quantitative claims will be
ledger-bound, and the natural endpoint will be explicitly ineligible.

### 4. Naturalistic successor draft

Draft a separate preregistration without consuming a study key or accessing new data. It will define:

- opened development tasks versus untouched confirmation tasks;
- at most two focused behaviors with robust natural effects, such as context retrieval and controlled
  syntactic agreement;
- at least two genuinely distinct model families and model-level replication;
- frozen effect-support, block-support, template/vocabulary separation, sham, recovery, collateral,
  and equivalence rules;
- the same nonlearned baselines and no architecture training;
- a result-independent decision tree, including a stop if prospective eligibility again fails.

Task selection must be based on opened development panels and frozen before confirmation. This draft
is planning evidence, not a new experimental result.

### 5. Adversarial publication-impact review

Run fallback `/adversarial` on the integrated paper in a fresh hostile pass. Attack contribution
novelty, generality, statistical support, causal language, naturalistic validity, narrative length,
baseline fairness, positive controls, and whether the artifact is actionable to interpretability
researchers. Supplement the review with a primary-source literature-positioning check and convert the
findings into a prioritized, result-independent impact roadmap.

## Alternative considered

Immediately training a collateral-constrained supervised controller could capitalize on the positive
relative-position oracle signal. It is rejected now because v2's frozen training condition was not
met and because the natural endpoint was ineligible. Such a model would mix architecture search with
the unresolved external-validity question. A no-inference analysis/paper integration plus a separately
versioned naturalistic design is the smaller, scientifically reversible next step.

## Milestones

- [x] **M1: plan review** — acceptance: `/adversarial` returns SHIP after checking preservation,
  quantitative-claim scope, no-inference boundary, and publication-review criteria.
- [x] **M2: closure artifact** — acceptance: exact hashes verify; prior v1/v2 artifacts are unchanged;
  training authorization is false and no experimental namespace is reopened.
- [x] **M3: cached analysis companion** — acceptance: create-once deterministic outputs, zero model
  imports/forwards, all nine shard terminals verified, tables and five required figures produced.
- [x] **M4: manuscript integration** — acceptance: v2 is reported prospectively and conjunctively;
  positive effects and limitations remain visible; claim ledger verifies.
- [x] **M5: naturalistic successor draft** — acceptance: development/confirmation firewall, support
  floors, independent units, models, shams, endpoints, thresholds, and stop rules are explicit; no
  data or model access occurs.
- [x] **M6: adversarial paper review and impact roadmap** — acceptance: a concrete SHIP/REVISE/BLOCK
  paper verdict with file:line findings and a prioritized roadmap separating analysis-only,
  confirmatory, and new-hypothesis work.

## Definition of done

- V1 and v2 result hashes and terminal contents remain unchanged.
- A durable closure record binds the completed v2 evidence and forbids current-program training.
- The v2 cached companion provides gate, Pareto, depth, capacity, stratified, and naturalistic
  descriptive outputs without any new forward.
- `PAPER.md` accurately reports v2, including zero formal passes, positive-but-unsafe signals,
  proxy-class associations, layer tradeoffs, K2 capacity-following, and naturalistic ineligibility.
- Every new numeric paper claim has exact ledger evidence and `verify_paper_claims.py` passes.
- The successor draft is clearly unopened and does not authorize inference or training.
- The adversarial paper review identifies publication blockers rather than merely praising framing.
- The final response explains what was changed and gives a prioritized strategy for improving impact
  without outcome-driven architecture search.

## Risks and mitigations

- **Negative-result overclaim:** report “no evaluated method jointly passed,” not “no separator
  exists”; preserve the positive oracle/PCA/delta effects and their intervals.
- **Proxy cherry-picking:** show all proxy classes, undefined constant sparsity, and method-specific
  association intervals; do not pool incompatible definitions.
- **Threshold shopping:** plot continuous Pareto fronts but never recompute or relabel frozen gates.
- **Generated-source generality:** name the shared generator and make natural confirmation the main
  missing evidence.
- **Narrative sprawl:** adversarially test whether the chronological failure record overwhelms the
  benchmark contribution; move engineering detail to appendices if necessary.
- **Future-study leakage:** keep the successor a draft until opened development tasks establish
  feasibility and a separate freeze authorizes untouched confirmation.

## One-way doors

- Editing v1/v2 outcomes or reopening a frozen namespace is forbidden.
- Opening a new naturalistic confirmation panel is irreversible and is explicitly outside this task.
- The paper's headline can be revised later; no claim of venue readiness is irreversible here.

## Verification plan

- Hash v1/v2 aggregate, synthetic, freeze, claim-review, and terminal inputs before and after work.
- Unit-test analysis helpers on synthetic frames and run the cached analysis twice in temporary
  namespaces for byte-identical JSON/CSV outputs.
- Scan the analysis script for transformer/model imports and record `new_model_forwards: 0`.
- Run Python compilation and targeted tests.
- Run `python scripts/verify_paper_claims.py`.
- Run fallback `/adversarial` on this plan and on the integrated paper.
- Verify no new GPU process, tmux experiment session, model cache write, or result namespace outside
  the declared analysis companion was created.
