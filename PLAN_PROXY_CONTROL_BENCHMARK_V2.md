# PLAN — Proxy-to-Control Benchmark v2

## Goal

Preserve proxy-control benchmark v1 byte-for-byte, produce a create-once cached analysis companion,
update the manuscript around the narrower “potency versus precision” result, and launch a separately
versioned prospective v2 evaluation. V2 asks whether imported, already-trained decompositions and
frozen linear baselines predict sign-aligned, selective, collateral-safe behavioral control on fresh
controlled panels and a fresh naturalistic QA endpoint.

## Non-goals

- Do not edit, rerun, rescore, or reuse the v1 namespace for outputs.
- Do not train additional real-activation K1/K2 SAEs, private/shared models, or context/local models.
- Do not authorize relational v5 or reopen any retired attempt.
- Do not pool incompatible linear-rank and learned-active-code sparsity or reconstruction metrics.
- Do not interpret generated rows, seeds, concepts, or method variants as independent model replicas.
- Do not wait for v2 results in the launch turn or make a result claim before post-result claim review.

## Constraints and frozen scope

- Import all v1 checkpoints, centers/scales, metrics, and terminals by exact SHA-256. The imported
  checkpoints are the float16 serialized v1 artifacts, not the ephemeral live float32 training state.
  Any drift blocks v2 before model loading.
- Reuse the exact three v1 model revisions and early/middle/late layers. Learned methods are imported
  v1 K1, equal K2, asymmetric K2, and capacity-swapped K2 checkpoints with three frozen seeds.
- Fit only nonlearned bases and a behavior-gradient-supervised linear oracle on v2 development rows.
- V2 controlled sources are new `SOURCE_C` and `SOURCE_D` panels prepared before model inference.
  Each concept/source has 16 development blocks x 4 development-only templates and 32 test blocks x
  4 test-only templates. Component-block, not row, is the lowest resampling unit.
- Concepts remain context, lexical substitution, and relative sequential position. Every sham is a
  nontrivial matched change, not an exact no-op. The position counterfactual and sham use the same
  token multiset and preserve the relevant fact while changing its distance versus only nuisance order.
- A new naturalistic context endpoint uses exact, hashed yes/no rows from cached LongBench Qasper and
  HotpotQA. It is reported endpoint-specifically and is not allowed to invalidate controlled endpoints.
- Behavioral specificity is aligned to the signed natural counterfactual:
  `(patch_effect - sham_effect) / full_effect`. Near-zero natural effects remain ineligible.
- Linear and learned proxy associations are reported separately. Method-fixed-effect associations
  residualize rank-transformed metrics on frozen method indicators.
- Synthetic ground-truth projection, behavior-supervised oracle, and random-negative checks run first.
  Real workers may exist in tmux but must wait without model loading until a signed gate PASS appears.
- All outputs are create-once, config-driven, deterministic, offline, hashed, and explicitly
  prospective/exploratory at nine model/layer clusters.

## Codebase grounding

- `scripts/proxy_control_benchmark_v1.py` defines the imported model convention, block-output patch
  hook, TopK state schema, panel extraction, and v1 metrics.
- `results/proxy_control_benchmark_v1_20260808` provides the immutable checkpoints and analysis rows.
- `reports/claim_review/proxy_control_benchmark_v1_post_result_claim_review.md` identifies the signed
  metric, pooled-proxy, component-independence, and positive-control requirements v2 must repair.
- `scripts/verify_paper_claims.py` and `reports/paper_claim_ledger_v1.json` define manuscript evidence
  bindings; new quantitative prose must receive new ledger entries.

## Approach

### 1. Cached v1 analysis companion

A standalone script verifies every imported v1 result/checkpoint hash, then writes a new namespace
containing: sign-aligned sensitivity, learned-only and method-fixed-effect cluster bootstraps,
method/concept/model/layer/source/seed tables, conservative factor-cycle sensitivity intervals using
the eight reconstructed v1 cyclic nuisance groups (explicitly not independent component evidence), a
patch-norm-standardized recovery/collateral Pareto table and figure, and K2
capacity/identity diagnostics. It never imports a transformer or performs a model forward.

### 2. Fresh v2 panels

A label-only prescore materializes exact SOURCE_C/SOURCE_D rows using tokenizers only. Selection may
use tokenizer IDs/lengths and registered dataset labels, but never model activations, logits,
gradients, effect sizes, or method outcomes. Development and test template IDs are disjoint. Base/counterfactual/sham prompts differ, prompt lengths are
matched per tokenizer for controlled rows, answers are one token in every registered tokenizer, and
all sources/concepts clear the component-block floor. Exact naturalistic dataset IDs, prompts,
answers, fingerprints, and hashes are materialized concurrently.

### 3. V2 methods and endpoints

Workers load exact v1 checkpoint state and activation normalization. Linear methods are refit on only
an assignment source's v2 development rows. For the behavior-gradient oracle, let `D=cf-base`,
`S=sham-base`, and `G=sign(full_effect)*d(logit_cf-logit_base)/d(base_hidden)` on development rows.
The frozen matrix is `M=sym(D.T@G/n) - lambda*sym(S.T@G/n)`, with `lambda=1`; the basis is the first
`rank=16` eigenvectors whose descending eigenvalues exceed `1e-8`. No evaluation or naturalistic row
enters this fit. It is not called an architecture or a learned SAE. Component assignment is source-fitted and tested
in both SOURCE_C→SOURCE_D and SOURCE_D→SOURCE_C directions. Naturalistic QA is evaluated separately
with each controlled source's context mapping.

For each component, v2 records recovery, sign-aligned sham specificity, representational specificity,
collateral nonanswer KL, patch/full norm ratio, eligibility, necessity, source/template/block lineage,
and assignment identity. Block bootstrap intervals use 32 test blocks rather than 128 surface rows.

### 4. Naturalistic endpoint and synthetic precondition

Naturalistic rows freeze exact dataset IDs and normalized raw text. Unrelated contexts are paired by
nearest character length with a deterministic nonself rotation, without using answers beyond the
registered yes/no label. At inference, each tokenizer keeps the first and last 96 context tokens and
always retains the complete question/answer suffix; no row is filtered using logits or effects.

The synthetic gate has known private, nuisance, and shared bases plus known target and collateral
behavior. A ground-truth projector must pass capture, leakage, behavioral recovery, specificity, and
collateral thresholds; the behavior-gradient oracle must pass its frozen thresholds; and a random
projector must remain below the specificity cap. Gate failure writes a terminal and workers exit
without a scientific model forward.

### 5. Aggregation and decisions

Aggregation verifies all hashes and reports learned-only, linear-only, and method-fixed-effect
associations with model/layer cluster intervals. It never creates a pooled reconstruction/sparsity
claim. A controlled method/concept/stage passes only when eligibility is at least `0.80`, block-CI
recovery lower bound exceeds `0.10`, sign-aligned specificity lower bound exceeds `0.10`, collateral
KL upper bound is below `0.02`, both transfer directions pass, and at least two models pass at the
same stage. An association is material only when `|rho|>=0.20` and its nine-cluster interval excludes
zero. Synthetic ground-truth thresholds are capture/recovery at least `0.90`, leakage/collateral at
most `0.10/0.05`, and specificity at least `0.80`; the gradient oracle requires recovery at least
`0.70`, specificity at least `0.50`, and target-subspace CKA at least `0.75`; random specificity must
remain below `0.25`. Result-independent branches are:

- oracle passes both transfer directions while unsupervised methods fail → semantic separation may
  require counterfactual supervision; authorize only a separately frozen supervised comparison;
- early layers alone replicate across at least two models → depth-dependent separability hypothesis;
- recovery/stability predict potency but not specificity/safety → potency-versus-precision benchmark;
- positive controls pass but no real method passes → local linear selective manipulability unsupported;
- equal K2 passes prospectively across both directions and two models → historical capacity confound
  merits a new architecture study;
- any endpoint under-supported → that endpoint is ineligible without blocking the others.

## Alternative considered

Training fresh, equal-capacity K2 and supervised context/local models would confound measurement
repair with architecture search and violate the current training condition. Importing v1 checkpoints
keeps the learned objects fixed while changing only prospective panels and corrected estimators.
Reusing SOURCE_A/SOURCE_B would be faster but would not be a fresh evaluation. Natural-corpus-only
confirmation was rejected because available corpora do not supply matched causal counterfactuals for
all three concepts; the naturalistic QA module is therefore a separate external-validity endpoint.

## Milestones

- [x] **M1: plan and preservation design** — acceptance: v1 manifest scope, no-training rule,
  endpoint hierarchy, synthetic gate, and decision table are explicit; fallback adversarial review
  has no blocker.
- [x] **M2: v1 companion** — acceptance: no transformers import/forward path; exact v1 hash check;
  create-once JSON/CSV/figures; deterministic repeated run in two temporary namespaces.
- [x] **M3: paper integration** — acceptance: potency-versus-precision section, limitations, artifact
  map, claim ledger bindings, and `verify_paper_claims.py` pass.
- [x] **M4: v2 core and prescore** — acceptance: controlled/natural panels clear floors; templates and
  blocks are disjoint; all answers are one token; shams nontrivial; core unit tests pass.
- [x] **M5: gate, worker, aggregate, and smoke** — acceptance: CPU synthetic gate passes and random
  negative fails; technical model hook smoke passes; workers cannot model-load before gate; tiny
  create-once smoke is deterministic.
- [ ] **M6: final freeze and adversarial review** — acceptance: complete candidate inventory and v1
  lineage hashes frozen before scientific forward; fallback review verdict SHIP; reproducibility and
  secret checks pass.
- [ ] **M7: launch** — acceptance: only free GPU UUIDs allocated; synthetic gate, waiting workers,
  and dependent aggregate run in named tmux sessions; STARTED/WAITING records and GPU/session state
  verified. Stop without waiting for scientific completion.

## Definition of done

- V1 artifact hashes are unchanged and a complete import manifest is recorded.
- The cached analysis companion and updated paper exist in new namespaces with verified claims.
- V2 config freezes models, revisions, imported checkpoint hashes, sources, templates, blocks,
  methods, ranks, metrics, thresholds, hierarchy, seeds, decision logic, and exact data fingerprints.
- No real SAE training function is reachable from the v2 worker.
- Positive controls gate all real scientific forwards and pass in smoke; gate failure blocks them.
- Controlled rows provide 32 independent test blocks per source/concept and held-out template families;
  naturalistic QA has at least 30 independent cached documents.
- Tests cover sign alignment, sham nontriviality, block bootstrap, proxy-class isolation, oracle gate,
  branch assignment lineage, v1 drift, create-once outputs, and pre-gate worker behavior.
- Candidate review is bound to the final freeze hash.
- Experiments are launched under tmux on free GPUs and this session ends while they are running.

## Risks and mitigations

- **Oracle leakage:** fit per assignment-source development split only; serialize row IDs and basis
  lineage; evaluation source and natural rows are never used in fitting.
- **Generated-row pseudoreplication:** freeze lexical/document blocks and bootstrap blocks; surface
  templates are repeated measurements, not independent support.
- **Off-manifold patches:** retain norm ratio, cap eligibility, norm-standardize descriptive Pareto
  comparisons, and report full natural deltas.
- **Metric direction:** unit-test positive and negative natural effects; the same aligned estimator
  must score correct movement positively.
- **Synthetic tautology:** require both passing ground-truth/oracle controls and a failing random
  control; report the oracle separately from unsupervised methods.
- **Natural QA weakness:** make it endpoint-specific and descriptive if its effect/eligibility floor
  fails; never use it to erase controlled-panel evidence.
- **Nine-cluster power:** cluster intervals and equivalence are primary; 918+ rows are never described
  as model-level replication.

## One-way doors

Model inference on SOURCE_C, SOURCE_D, Qasper, or HotpotQA opens the prospective evaluation panel.
Before the synthetic gate can authorize it, the exact rows, code, metrics, thresholds, decisions,
lineage manifest, tests, and environment must be frozen. No result namespace may be reused.

## Verification plan

- `PYTHONPATH=scripts .venv-atlas/bin/python -m pytest -q tests/test_proxy_control_benchmark_v2.py`
- deterministic companion comparison in two temporary directories
- `python scripts/verify_paper_claims.py`
- Python compilation and shell syntax checks
- tokenizer-only prescore and manifest verification
- CPU synthetic gate plus random-negative assertion
- technical Pythia hook smoke using non-scientific strings
- v1 SHA-256 lineage verification and output-namespace absence
- fallback `/adversarial` on this plan and the final candidate
- repro-guard seed/determinism/path/secret/environment/data checks
- `nvidia-smi`, tmux launch, STARTED/WAITING records, and assigned GPU PID verification
