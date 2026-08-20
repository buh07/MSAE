# PLAN — Relational Objects v3 opened-development study

## Goal

Run a separately versioned, exploratory, measurement-only study asking which relational objects, if
any, provide cross-source edge recovery and edge-specific local attention-block response beyond a frozen
token-pair/nuisance baseline. Begin with label-only feasibility under the final morphology-value
matcher. Update `PAPER.md` only after a valid result or a prespecified stop.

## Non-goals

- Do not modify, resume, reinterpret, or retry relational-objects v2, Relational Attention-Edge
  Discovery 1/2, Attempt 13, Attempt 14, or the closed K2 position/content program.
- Do not train an SAE, neural representation, supervised decomposition, or shared branch.
- Do not inspect or name future confirmation corpora.
- Do not lower support, recovery, or specificity gates after seeing feasibility or representation
  results.
- Do not make publication of the current encoding--separability paper conditional on v3.

This is explicitly an **outcome-informed feasibility successor to v2**, permitted by the v2 stop
clause because it uses a new source-pool policy after v2 failed prescore support. It does not claim
scientific independence from v2. The signed v2 terminal remains final and v3 cannot write any v2
path.

## Immutable parent and exposure bindings

- Corrected v2 parent snapshot manifest:
  `reports/provenance/relational_objects_v3_parent_protocol_v1/manifest.json`, SHA-256
  `ea36578323fc954061ece5cde9266c0ffb7971ea21210baf2532428d2ff867ca`.
- Signed v2 terminal:
  `reports/provenance/relational_objects_v2_development2_prescore_terminal_v2.json`, SHA-256
  `0fc6521c09069a29dd733062e68d8d73cd336b87d4b56a28a55ef656d7f27f50`.
- Exact per-file source-exposure manifest:
  `reports/provenance/relational_objects_v3_source_exposure_v1.json`, SHA-256
  `20f730d24f9c1b89bf33268bac8b46df83af316bb5dbeff9cff4e25773ebd591`.
- Exact parser/source-pool manifest:
  `configs/relational_objects_v3/source_pool_manifest.json`, SHA-256
  `7599db848f2e1e8fcdb4e746b31c556169b059e3842d3270e36d4b2a86a5bfcd`.

The parent snapshot contains the exact corrected morphology-value builder, analysis, runner, common
contracts, tests, config, and v2 plan. V3 receives isolated copies derived from these bytes. A later
v3 freeze binds the complete v3 code tree; neither mutable v2 files nor an unspecified “latest” v2
implementation may be imported at runtime.

## Claim class and source roles

The entire v3 run is opened development and exploratory. The following already-local, already-opened
files are permanently development-only under the exact exposure manifest above:

1. Czech-PDT dev;
2. Spanish-AnCora train;
3. English-EWT train;
4. English-GUM train;
5. Latvian-LVTB train;
6. Ukrainian-IU train;
7. Arabic-PADT train;
8. English-GENTLE test.

No file in this pool may later serve as fresh confirmation. Parser or label-only failure remains
reported and cannot be silently removed. Fresh scientific sources remain unnamed and unopened.

Prior exposure is explicit per file: AnCora and GENTLE supplied scientific endpoints, EWT/GUM supplied
multiple earlier scientific endpoints, Czech-PDT supplied model-forward technical validation, and
Latvian/Ukrainian/Arabic supplied label/tokenizer feasibility without a relational-object model
forward. The exposure manifest records each exact path, hash, revision, prior role, evidence artifact,
and prior support outcome. This prior exposure is why v3 is development-only; none is represented as
endpoint-unseen or confirmatory.

## Prescore feasibility and source selection

Every pool file must pass the standalone strict CoNLL-U parser under an exact hash manifest. The
label-only scout then uses an isolated v3 copy of the exact parent-snapshotted corrected matcher,
without model weights:

- Pythia tokenizer alignment only; no activation extraction;
- genuine `newdoc id` groups;
- exclusion of multiword-token, empty-node, surface-mismatch, ambiguous-alignment, and truncated
  sentences under the frozen rules;
- exact surface UD gap, causal orientation, endpoint UPOS, endpoint morphology **values** for the
  complete fixed vocabulary, punctuation flags, endpoint subtoken counts, query-position bin,
  causal-key-count bin, and sequence-length bin;
- negative pairs that are neither direct edges nor ancestor/descendant pairs;
- document-disjoint positive/nonedge components with no document reuse;
- the same deterministic matching objective and five-fold allocation as corrected v2.

Eligibility remains at least 100 document-disjoint components, at least 500 balanced pairs, and at
least 20 pairs per causal orientation. The scout first reports uncapped availability, then creates the
canonical deterministic cap of at most 150 components and exactly 500 pairs. **Eligibility is
recomputed on that final capped panel**; uncapped support cannot qualify a capped panel that falls
below any floor. No support-preserving bootstrap can rescue a source below the floor.

Select the first two eligible sources in this frozen order: Czech-PDT, Spanish-AnCora, English-EWT,
English-GUM, Latvian-LVTB, Ukrainian-IU, Arabic-PADT, English-GENTLE. The order prioritizes two
high-document, cross-lingual sources and then existing opened comparators; it is frozen before the
exact feasibility scout. If fewer than two sources pass, write a signed prescore terminal and stop.

## Relational objects

For each selected source, keep the snapshotted v2 causal word/subtoken definitions at Pythia-160m-deduped block
3 in eager float32 attention. Compare:

1. ordered child--head residual concatenation;
2. ordered residual difference `head - child`;
3. per-head mean scaled post-RoPE query--key logits;
4. per-head attention-edge mass, descriptive only;
5. concatenated transported values before the output projection;
6. frozen deterministic baseline `B`: residual concatenation plus fixed lexical hashes, morphology,
   punctuation, and sequential geometry.

The two decision paths are unchanged from v2:

- `B + QK` versus `B`;
- `B + transported value` versus `B`.

Concatenation, residual difference, and attention mass are descriptive and cannot be mixed into a
passing path after results.

## Estimation and decision gates

The following restatement, together with the immutable parent snapshot, is authoritative; a conflict
fails closed before opening.

**Recovery.** Give every document-component total weight one. Use five deterministic component folds.
Within the fit source, fit `StandardScaler` and `RidgeClassifier(fit_intercept=true,
class_weight=None, solver=lsqr, tol=1e-6, max_iter=10000)` with alphas `[1,10,100]`; select by mean
fold AUC, breaking ties toward the larger alpha, refit on all fit-source components, and evaluate the
other source. Each of 500 draws independently resamples components with replacement **within every
fixed fold** in fit and test sources, reselects alpha, refits, and uses the same maps for `B` and its
paired augmentation. NumPy linear quantiles over exactly 500 finite draws give the one-sided 97.5%
lower bounds (`q=0.025`). Any algorithmic/nonfinite draw invalidates the endpoint; none is dropped.

The baseline `B` is residual concatenation plus a fixed-seed signed 2,048-dimensional hash of child
and head FORM, lemma, and ordered FORM/lemma pairs; fixed one-hot morphology **values** and punctuation;
and surface gap, query index, causal-key count, and sequence length. The only decision paths are
`B+QK` versus `B` and `B+transport` versus `B`, evaluated independently under a Bonferroni two-path
family. A complete path must pass in both directions: augmented AUC lower bound at least `0.55` and
paired augmented-minus-baseline AUC lower bound at least `0.02`.

**Local intervention.** For query `q`, head `h`, and the earlier-word key span `S`, let
`m_h=sum_{k in S}p_hk`. Every head must satisfy `1e-6 < m_h < 1-1e-6`. Set span probabilities to zero
and renormalize every outside probability by `1/(1-m_h)` in the authoritative float32 intervention.
From cached float32 probabilities/values cast to float64 and summed in increasing key order, compute
`u_in=sum_S p_hk v_hk/m_h` and `u_out=sum_notS p_hk v_hk/(1-m_h)`. Define
`E_local=RMS_h(||u_out-u_in||_2/sqrt(64))`. Define authoritative `E_abs` by literally applying the
float32 zero/renormalize intervention, concatenating all 12 changed head outputs, applying the frozen
attention output projection, and dividing its norm by `sqrt(768)`; the ordered float64 expression
using `m_h(u_out-u_in)` is QA-only. Relative activation-normalized scale remains descriptive.

Functional matching adds the frozen mean-mass bins
`[0,1e-4,1e-3,1e-2,.05,.1,.25,.5,.75,.95,1]`, permits no row/document reuse, and preserves causal
orientation. Cross-fit nuisance regression uses five component folds, component-equal weights,
`StandardScaler`, and `Ridge(alpha=100)` separately for `E_local` and `E_abs`. Its fixed nuisance
vector contains the 2,048-bin endpoint/ordered lexical hashes, morphology values, punctuation,
surface gap, query index, causal-key count, sequence length, all 12 original masses, query/key value
norms, and unablated projected-output norm. The primary effect is the equal-component-weighted paired
true-edge-minus-matched-nonedge held-out residual. Each of 500 draws resamples within every fold,
refits the other folds, and evaluates the held-out fold. The one-sided 95% lower bound is the linear
`q=0.05` quantile; failed draws are never removed.

Decision requirements are:

- augmented AUC lower bound at least `0.55` and paired increment lower bound at least `0.02` in both
  transfer directions for one complete path;
- both `E_local` and `E_abs` lower bounds above zero in every source/orientation, plus true-edge
  `E_abs` lower bound at least `1e-4`;
- in each source/orientation, at least 50% of otherwise recovery-eligible true edges must satisfy the
  all-head mass rule and at least 20% of those eligible edges must enter an exact mass-bin functional
  pair without reuse; publish every attrition denominator and reason;
- at least 20 no-reuse functional document-components must remain in **every** source/orientation;
- endpoint-specific eligibility and exactly 500 finite draws per primary interval.

A development nomination requires one complete QK or transport path to pass recovery, increment,
edge-specific local attention-block response, and support in both directions. A positive opened-development result
authorizes only a new preregistration on unnamed fresh corpora. It does not authorize learned models.

## Lifecycle

Use namespace `relational_objects_v3_opened_development1`. All source-pool, parser, scout, selection,
config, code, test, and environment hashes are frozen before model weights are loaded. The model run
uses a create-once opening, isolated result/run roots, one physical GPU selected by a live free-GPU
check, and a write-once terminal. The exact order is: signed freeze candidate; exact-candidate
adversarial SHIP; synthetic tensor QA and model-backend axis QA on synthetic/tokenizer-only inputs;
signed authorization; exclusive opening with owner nonce; opened-source model load/forward; analysis;
owner-only write-once terminal. Pre-opening failures may be repaired only without creating an opening.
No retry is permitted after opening. A technical failure after opening closes this development
attempt. Backend QA must not read any opened-source row or create a study result.

Before opening, perform an adversarial fresh-pass review of:

- exact source selection and support provenance;
- morphology-value matching and nuisance encoding;
- tensor axes and QK/transport definitions;
- local edge-intervention precision;
- component weighting/bootstrap logic;
- GPU mapping, output isolation, and one-shot terminal ownership;
- the absence of optimizer, checkpoint, backward, or learned-representation paths.

## Milestones

- [ ] **M1 — Source pool and parser:** freeze an exact eight-file manifest and validation identity.
  Acceptance: every file strict-passes with zero coverage/manifest errors, or v3 stops and reports the
  exact error without model inference.
- [ ] **M2 — Feasibility scout:** run a deterministic label/tokenizer-only rebuild under the complete
  matcher. Acceptance: two byte-identical builds select exactly two sources by the frozen order, with
  support and attrition for all eight candidates, or a signed prescore terminal stops before model
  loading.
- [ ] **M3 — Freeze and tests:** create isolated v3 config/code and synthetic
  QK/transport/intervention tests. Acceptance: targeted tests, preservation checks, static no-training
  audit, lifecycle absence checks, and exact-candidate adversarial review all pass before opening.
- [ ] **M4 — Opened development run:** launch one tmux run on a rechecked free GPU. Acceptance: one
  create-once opening and one signed terminal; exact metrics/artifacts; no optimizer, backward,
  checkpoint, representation persistence, fresh-source access, or retry.
- [ ] **M5 — Claim review and paper:** distinguish recovery, specificity, eligibility, and nomination.
  Acceptance: independent post-result claim review and a passing exact claim-ledger verification for
  the updated `PAPER.md`.
- [ ] **M6 — Future boundary:** decide whether fresh confirmation is warranted. Acceptance: either a
  nomination that leaves fresh corpora unnamed/unopened pending a new plan, or a signed stop that
  forbids learned models and further source substitution.

## Verification plan

- Plan gate: run `.agent-workspace/bin/check-plan --path PLAN_RELATIONAL_OBJECTS_V3.md` (or the
  workspace-equivalent path) and require PASS before implementation.
- Parser: run `scripts/validate_opened_conllu.py` against the exact v3 manifest/freeze and require
  `strict_failure_count=0`, `eligible_for_development_forward=true`, and the expected eight hashes.
- Scout determinism: build to two new temporary roots from the same frozen config, compare canonical
  report bytes and recursive child hashes, then preserve both reports; tokenizer libraries are
  allowed, but model weights, `AutoModel`, and forward execution are prohibited.
- Tests/static checks: run parser and v3 targeted `pytest` suites, `python -m py_compile` over every
  new Python file, and `bash -n` over the launcher/pipeline.
- Synthetic backend QA: independently reconstruct QK scaling, attention mass, transported values,
  float32 zero/renormalize intervention, float64 analytic effects, output projection, component
  weights, fold isolation, bootstrap multiplicity, and decision truth tables on tiny tensors.
- Preservation: rehash the Attempt-13/14 preservation manifest, architecture closure, Discovery-2
  opening/terminal, v2 plan/config/prepared manifest/signed terminal, and `PAPER.md` baseline before
  source opening and after terminalization.
- No-training audit: fail if the v3 executable import graph or command surface contains an optimizer,
  `.backward`, checkpoint writer, fitted-representation persistence, or fresh-corpus path.
- Lifecycle: before opening require absent v3 authorization/opening/run/result/terminal paths; verify
  create-once owner semantics and nonowner failure without mutation in tests.
- GPU: immediately before authorization query physical UUID, free memory, utilization, MIG state, and
  visible-device mapping; bind the selected identity in the freeze and repeat it inside the runner.
- Result/claim: verify all endpoint denominators and finite-draw counts, run an independent claim
  review, then run `scripts/verify_paper_claims.py` and require PASS after manuscript update.

## Risks

- Source selection is informed by label/document feasibility. This is allowed only because every
  candidate is permanently development-only and selection occurs before representation outcomes.
- Czech/Spanish tokenization may lose many rows; only post-alignment document-disjoint support counts.
- High-dimensional transport may win by capacity. The paired baseline increment and functional gates
  are therefore mandatory.
- Attention ablation is local and off-manifold. Claims remain restricted to the attention block and
  matched intervention; no downstream syntactic causality claim is authorized.
- A second prescore stop is a valid feasibility result, not permission to lower the floor.

## Definition of done

- `PAPER.md` remains a complete, claim-ledger-verified project synthesis.
- All v2 and prior signed artifacts remain byte-unchanged.
- The exact v3 source pool is parser-valid and fully reported.
- Two sources clear the complete prescore before any model load, or a prescore terminal records why
  the study stopped.
- If opened, all relational objects and controls run under the frozen estimator on one isolated tmux
  job with no representation training.
- A post-result claim review scopes every conclusion and updates the paper without outcome-conditioned
  gate changes.
