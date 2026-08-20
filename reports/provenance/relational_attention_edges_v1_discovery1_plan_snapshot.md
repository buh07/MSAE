# PLAN — Relational Attention-Edge Atlas v1 (Discovery 1)

## Goal

Close the completed position/content architecture program without changing Attempts 13 or 14, write
the paper-level encoding-versus-separability synthesis, and execute one **new, measurement-only**
discovery study of a genuinely different representational object:

> Do causally masked, pre-softmax rotary query-key links at Pythia-160m layer 3 distinguish dependency
> edges from exactly matched non-edges across two project-outcome-unseen UD corpora, and add
> conditional predictive performance beyond a linear
> token-pair residual baseline?

The new study is `relational_attention_edges_v1_discovery1`. It is not Attempt 14/15, not a retry of
the position/context atlas, and not an architecture-training authorization.

## Non-goals

- Do not modify or continue Attempt 13 or Attempt 14.
- Do not lower Attempt-14 Gate 4 or claim that its projection matched a learned model.
- Do not train K2, an SAE, a supervised context/local model, a shared branch, an attention model, or
  any other neural/representation model.
- Do not search layers, ranks, models, endpoints, thresholds, or source subsets after seeing results.
- Do not claim isolation or that attention is a causal syntactic mechanism from observational
  attention weights. A passing study establishes only matched cross-source predictive association and
  conditional increment for the exact fitted estimators.
- Do not generalize beyond the exact model, layer, sources, and frozen linear estimators.
- A favorable discovery result may nominate a later preregistered comparison; it cannot start one.

## Constraints and preserved conclusions

- Before any new-study writer is implemented, freeze a complete immutable preservation manifest over
  every Attempt-13/14 plan, config, freeze, authorization, raw/prepared data, cache, run, result,
  scientific-opening record, provenance report, adversarial review, and claim review path. Verify the
  exact recursive entries/digests before preparation, before opening, and after terminalization. New-
  study writers must reject every destination resolving inside a preserved root. Any drift blocks the
  new study.
- Write a closure artifact stating that the position/content architecture line is stopped and that
  no neural training is authorized. The preserved Attempt-14 conclusion is exactly:

  > Context is encoded, but the proposed projection is not specific enough to serve as a
  > context-private component.

- The paper draft must distinguish encoding, recoverability, selectivity, and architectural warrant;
  it must separately preserve supported positive recovery results, failed specificity/isolation
  gates, unmeasured questions, and forbidden claims for Attempts 13/14, and must not state that a
  learned context/local comparator exists.
- The candidate scientific sources are the following already pinned, label-only-scoped snapshots:
  UD Ukrainian-IU commit `21f641ba6109044ce9aafd4b2cbfa20a4ac6e479` (dev SHA-256
  `fc68644aeb86766935f1c3aa0e8baf42cc6325690803631e81e17ed8db79f436`, test
  `5538dec31c89b0cd0e5141d8a9c6bdc0099103eab3c5c6b9078ab95e67be1286`, train
  `f7282b32c72a2c6f304f1df13572b7dd9bff370d3da0abf726da00f6a15d1b14`) and UD Latvian-LVTB commit
  `f42ae0dd20ddef5aa4b88c40e3582e37c57d1e43` (dev
  `d9dec7ed8809ab112f09945400fddf72d4731354624b1b637f5db5a5dabbb91d`, test
  `4237279f832058659ed8494af13239f7efe25058919bc0f5d84050ef47f1968d`, train
  `1fa6a60852b21aafca644c7929e2aaaf7b01899ccc71d7a2fa15f457caed49d2`).
  The scientific sample uses only each treebank's pinned train file; dev/test remain provenance-only
  and receive no model forward. This rule was frozen label-only after observing that Ukrainian raw
  `newdoc id` strings are split-local rather than globally unique. Repeated declarations of the same
  raw ID within a selected train file are conservatively pooled into one resampling cluster (Latvian
  has 3,215 declarations but 2,428 unique raw IDs); an ID may never be split into smaller pseudo-
  documents. Observed cross-split reuse is recorded but is neither pooled nor
  fatal because dev/test cannot reach preparation or inference. Scientific document IDs are
  `source:train:raw_newdoc_id`; no other split prefix is permitted.
  Label-only source/support scouting is development exposure and must be recorded. Before either is
  called endpoint-outcome-unseen, an executable project-wide exposure/overlap audit must search prior
  source, cache, run, result, report, and plan artifacts by aliases, raw-file hashes, normalized
  document/sentence hashes, and token-sequence hashes. Any prior project model forward or endpoint
  score on the same text makes the source ineligible; label-only mentions/scouting remain recorded
  development exposure. Potential Pythia pretraining exposure is unknown.
- Until that audit passes, use only `candidate project-outcome-unseen` language. Any prior project
  model forward, label-dependent endpoint score, unexplained alias/hash/content hit, or revision/hash
  mismatch writes a signed `TERMINAL_PRESCORE_INELIGIBLE` and permanently forbids source inference
  for this study key.
- Only genuine upstream `newdoc id` groups from the two selected train files are resampling groups.
  Every repeated declaration of one raw ID within the same selected file maps to that same group;
  dev/test reuse is provenance-only, never pooled, and cannot enter scientific component IDs.
- At least 160 genuine documents, 80 disjoint two-document components, 480 exactly balanced matched
  pairs, 96 pairs and 16 components in every one of five fit-source folds, and 20 documents per
  retained descriptive relation class are required in each source after every exclusion. Every
  component must contain at least one matched pair in each document-polarity orientation. These floors
  bound document clustering and give roughly 480 paired discrimination units rather than permitting a
  1,536-feature comparison on only 30 examples; failure is prescore-ineligible.
- Positive dependency edges and negative non-edges must be matched across different documents on
  exact causal subtoken gap, exact UD-token gap, query UPOS, key UPOS, query/key selected-subtoken
  counts, and the positive
  edge's child/head causal orientation. For the non-edge this last field is an assigned matching
  stratum copied from its positive partner; it is never an estimator feature. Each source document is
  used in at most one component; each component contains at most 24 matched pairs.
- Model inputs must reproduce the exact natural UD surface using `# text` plus the syntactic words'
  `SpaceAfter=No` metadata. A fast-tokenizer offset map must align every retained syntactic word to
  contiguous selected subtokens. Byte/surface drift, ambiguous spans, empty spans, or truncation make
  the sentence ineligible; inserting a space between every FORM is forbidden. This v1 excludes every
  sentence containing a multiword-token range or empty node rather than guessing child spans, and it
  accepts only sentences whose FORM/spacing reconstruction equals `# text` exactly.
- Matching, support, row order, all thresholds, model revision, implementation hashes, GPU UUID, and
  decision logic are frozen before the first source model forward.
- Exact component bootstrap maps are materialized label-only. Every primary interval requires at
  least 490/500 finite draws.
- Extraction uses float32, eager attention, inference mode, no gradients, and the exact pinned
  Pythia-160m-deduped revision. No optimizer/checkpoint path may exist.
- The signed lifecycle is either `PRESCORE_COMPLETE -> TERMINAL_PRESCORE_INELIGIBLE`, or
  `PRESCORE_COMPLETE -> FROZEN -> REVIEWED_SHIP -> BACKEND_QA_PASS -> AUTHORIZED -> RUNNER_READY ->
  OPENING_CONSUMED -> RUNNING -> TERMINAL_COMPLETE|TERMINAL_FAILED`.
  The global study-key record lives outside the run/result namespace and is created with
  `O_CREAT|O_EXCL`, written and file-fsynced, followed by parent-directory fsync. A concurrent loser
  fails before inference. Every exception before/after opening writes the corresponding signed
  preopening/postopening terminal; postopening failure cannot be retried under another namespace using
  the same sources/model/layer/protocol.
- Immediately before freeze select a GPU with no `nvidia-smi` compute process, at most 1 GiB used
  memory, zero reported utilization, and at least 40 GiB free. Bind physical index, full UUID, and
  non-MIG identity. The launcher obtains an exclusive `flock` keyed by UUID, repeats those checks,
  exports the UUID through `CUDA_VISIBLE_DEVICES`, and the runner requires exactly one Torch-visible
  device with the same UUID before and after loading the model. If it becomes busy, do not launch; a
  different GPU requires a new freeze and exact-candidate review.
- Launch one absent, exact-named tmux session with `remain-on-exit`, an exact frozen command and log
  path. The runner writes signed `RUNNER_READY.json` only after config, key, GPU, namespace, and
  preservation checks; the launcher waits up to 60 seconds for this handshake. Every exit path writes
  a signed terminal, while the shell log and tmux pane exit status remain auditable.

## Design grounding

- Attempt 13 already tested token-local child/head concatenation and differences against sham and
  exact sequential-offset controls; it did not demonstrate strong relation-specific isolation.
- Attempt 14 established transferable context-related linear variance but failed coherent-context
  specificity. It permanently closes position/context as an architecture nomination in this project.
- In Transformers 4.53.2, `GPTNeoXAttention.forward` forms scaled rotary query-key logits before the
  causal mask and softmax, exposes eager attention probabilities, and forms each head's
  pre-projection message as attention probability times the value vector. The new study therefore
  changes the object from token-local residual states to pre-softmax relational query-key features;
  normalized attention and value transport are descriptive only.
- Previous planning mentioned ParTUT/ATIS but rejected them because their one-sentence pseudo-document
  groups cannot support document-level uncertainty. Ukrainian-IU, Arabic-PADT, and Latvian-LVTB
  expose hundreds of raw upstream document groups. After corrected byte-level-tokenizer offset
  alignment and the final pre-softmax-link matching rule, Arabic-PADT retained 437 aligned documents
  but only 31 disjoint matched components, 62 represented documents, and 79 pairs; it fails every
  primary support floor except bidirectional polarity. Arabic-PADT is therefore a disclosed,
  permanently rejected source candidate for this study; no model weights, forward, activations, or
  endpoint scores were used. Ukrainian-IU (195 components, 907 pairs) and Latvian-LVTB (1,153
  components, 7,173 pairs) pass every label-only support floor and were selected with no known prior
  project model-forward or endpoint-scoring use; only the frozen exposure audit may promote that
  status.
- Before further implementation, write and sign a source-amendment artifact binding the exact
  Ukrainian/Arabic/Latvian commits and raw hashes, the exact label-only builder hash, surface/MWT/
  alignment/document/matched-support counts, candidate order and selection rule, Arabic's matched-
  support rejection,
  the train-only rule, a zero-model-load/zero-forward attestation, and this plan digest. M2 verifies
  this immutable historical artifact rather than regenerating the rationale.

## Frozen representational objects

For every matched pair, let the later selected subtoken(s) be the causally permitted query word and
the earlier selected subtoken(s) be the key word. Store explicit `query_is_head`, `query_index`, and
`key_index` fields. Attention is a later-query-to-earlier-key link; transported value is separately
named earlier-key-to-later-query value transport. The positive edge's query/head role is retained only
as a matching stratum, not treated as an estimator feature.

At zero-indexed transformer block 3, whose output is hidden-state index 4, extract:

1. **Pre-softmax query-key link** `z`: for head `h`, last query-word subtoken `q`, and key-word
   subtoken set `K`, apply the model's partial rotary embedding to the captured live Q/K tensors and
   define `z_h = mean_{k in K} ((RoPE(Q[h,q]) dot RoPE(K[h,k])) * scaling)`. This 12-dimensional
   vector is primary. The mean, rather than sum, is frozen before inference; exact key-subtoken count
   is also matched.
2. **Normalized attention link** `a`: define `a_h = sum_{k in K} alpha[h,q,k]` and analyze
   `log(max(a_h, 1e-12))`. Because softmax normalization depends on every earlier key and hence on
   prefix opportunity, this 12-dimensional vector is secondary/descriptive and cannot replace `z`
   in a gate.
3. **Transported value link** `m`: for each head define the actual partial pre-projection message
   `m_h = sum_{k in K} alpha[h,q,k] * V[h,k]`, then concatenate the 12 head vectors. This
   768-dimensional object is secondary/descriptive.
4. **Unweighted value control** `v`: concatenate per-head means of `V_key`; secondary/descriptive.
5. **Token-pair residual baseline** `r`: concatenate the exact hidden-state-index-4 output residual at
   the last query subtoken and the key-word output-residual mean minus that query residual. This is the
   same examined output stage as Attempts 13/14 and is the 1,536-dimensional primary baseline. The
   corresponding block-input pair may be reported descriptively but cannot replace this baseline.

The hook/parser QA must prove on synthetic sequences that captured live QKV, partial rotary
application, scaled pre-softmax logits, attention mass, and transported messages match an independent
recomputation, including a multi-subtoken key word. Re-softmaxed captured logits must reproduce the
model-returned eager attention probabilities within the frozen QA tolerance. Padding positions and
future keys must have zero probability/message contribution.

## Frozen sampling and estimators

### Matched dependency-edge/non-edge components

- A positive is exactly an unordered pair `{c,h}` where syntactic word `c` has basic integer `HEAD=h`;
  enhanced dependencies are ignored. Linear UD-token gap 1 is eligible.
- A negative is exactly an unordered pair `{u,v}` for which neither basic integer `HEAD` directly
  links the pair and neither word is in the other's transitive basic-HEAD ancestor set. It has the same
  causal later-query/earlier-key ordering as its matched positive. There is no separate or ambiguous
  “adjacency” exclusion.
- Reconstruct exact sentence surfaces and align word/subtoken spans before candidate enumeration.
  Matching uses exact relative subtoken and UD-token gaps, endpoint UPOS, and endpoint subtoken
  counts. Exact absolute query index and total sequence length are deliberately not required: they
  made the normalized-softmax design prescore-ineligible, while the primary pre-softmax rotary QK
  score has no normalization denominator. Absolute prefix/context and competing-key lexical content
  remain acknowledged uncontrolled variables and motivate both the cross-document polarity balance
  and residual-pair conditional comparator; no isolation claim is permitted. The result schema and
  post-result claim review must report query-index and total-sequence-length distributions by
  source/class as unmatched, non-gating potential confounders, never as balanced controls.
- Partition documents by the low bit of SHA-256 over namespace/source/raw-document-ID. A document pair
  across partitions is eligible only if it supports at least one positive-from-left/negative-from-
  right match **and** one positive-from-right/negative-from-left match. Select a maximum-cardinality
  document matching; among equal cardinality maximize the capped bidirectional row yield, then break
  ties lexicographically by the SHA-256 pair ID. This label-polarity symmetrization prevents one hash
  partition or document from supplying only one class.
- Within each selected component and each polarity orientation, group candidates by the exact frozen
  stratum, sort positives and negatives independently by SHA-256 row ID, zip without reuse, and then
  sort matched pairs by SHA-256 pair ID. Retain at most the first 12 pairs per orientation (24 total).
  No fallback, replacement, or relaxed stratum exists. Positive and negative examples are exactly
  balanced globally, per component, and per fold.
- Assign the complete document-pair component to one of five deterministic folds. No component may
  cross fit/test roles or bootstrap units. Folds are used only for fit-source alpha selection, never
  for source, stratum, threshold, endpoint, or secondary-analysis selection.

### Transfer scoring

For each direction, fit on the complete fit source and score on the other source:

- With scikit-learn `1.4.1.post1`, use `StandardScaler(copy=True, with_mean=True, with_std=True)` and
  `RidgeClassifier(fit_intercept=True, copy_X=True, max_iter=10000, tol=1e-6,
  class_weight=None, solver="lsqr", positive=False, random_state=None)`. Non-edge is class `0`,
  dependency edge is class `1`, and higher decision score always means edge. Alpha is selected
  separately for each feature set
  from the frozen grid `[1.0, 10.0, 100.0]` using only five deterministic fit-source component folds,
  maximizing the unweighted mean of five fold ROC AUCs and breaking exact ties toward the larger
  alpha. For every alpha/fold, instantiate a fresh scaler-plus-ridge pipeline, fit the scaler and ridge
  only on the other four folds, and score the untouched validation fold. After alpha selection,
  instantiate and fit a fresh scaler and ridge on the complete fit source. A missing class, nonfinite
  feature/score, or undefined fold invalidates that alpha; no valid alpha makes the direction
  ineligible. The held-out source never influences preprocessing, alpha, or weights;
- primary edge features: the 12 mean scaled rotary QK logits;
- primary token baseline: the 1,536 residual-pair features;
- primary conditional model: the identical residual-pair features concatenated with the 12 QK
  logits; it uses the same scaler/ridge/grid/CV rule as the residual-only model;
- report ROC AUC and balanced accuracy; ROC AUC is the decision metric;
- fit weights are ephemeral and never persisted;
- every interval and gate is explicitly named a **conditional-on-this-exact-fit-source-estimator
  test-source component interval**. It resamples held-out
  document-pair components with the precomputed 500 bootstrap maps;
- an empirical paired-label-swap null uses separate precomputed maps and the already-fitted held-out
  scores. It is descriptive because it does not refit the source estimator.

For each direction, order held-out component IDs bytewise. Each precomputed bootstrap-map row contains
exactly `n_components` component indices sampled with replacement. Convert it to component
  multiplicities and repeat **all** examples in a selected component by that multiplicity. The same draw
  and multiplicities are reused for QK-only `z`, residual-only `r`, residual-plus-QK `[r,z]`, their
  paired AUC contrasts, and QK matched-pair directionality. Normalized-attention `a`, transported `m`,
  and value `v` scores cannot reach a gate. Compute ROC AUC, AUC differences, or the fraction of matched pairs whose
edge score exceeds its paired non-edge score on the multiplicity-expanded arrays. A draw is nonfinite
if expansion is empty, either class is absent, any score is nonfinite, or its statistic is undefined;
filter only those draws and require at least 490/500. Report the full held-out sample as the point
estimate and NumPy quantiles `[0.025, 0.5, 0.975]` with `method="linear"` over finite draws. Point
thresholds use `>=`; every lower-bound comparison uses strict `>`; paired contrasts never use
independent maps.

Secondary analyses report normalized-attention `a`, transported-value `m`, and unweighted-value `v`
edge ROC AUC under the identical scaler/ridge/grid/CV procedure. Coarse dependency relation maps basic labels as follows: `nsubj,csubj,
obj,iobj,ccomp,xcomp -> CORE`; `obl,advcl,advmod -> OBLIQUE`; `nmod,appos,acl,amod,nummod,compound,
flat,fixed -> NOMINAL`; `conj,cc -> COORD`; `det,case,mark,aux,cop,clf -> FUNCTION`; `punct -> PUNCT`;
all others -> OTHER, after stripping every subtype suffix beginning at the first `:`. On positive
edges, QK-only `z`, residual-only `r`, and residual-plus-QK `[r,z]` features use the same
scaler/ridge/grid/five-fold
fit-source-only procedure, except alpha maximizes unweighted mean validation macro-F1. The frozen
averaging label set is the prospectively intersected classes clearing 20 documents in both sources;
every validation fold must contain every frozen class or that alpha is invalid. Prediction is
`RidgeClassifier.predict`; held-out macro-F1 is `f1_score(..., labels=frozen_classes,
average="macro", zero_division=0)`. Missing held-out classes make the secondary direction ineligible,
without affecting primary gates. The `a`, `m`, and `v` feature sets receive edge ROC AUC only, not
relation macro-F1. These analyses never enter the discovery decision.

## Prospective gates and decision logic

Each direction must independently satisfy:

1. **Measurability:** all rows finite, no row-ID/alignment failures, all support floors pass, and at
   least 490/500 bootstrap draws are finite.
2. **QK-link recovery:** held-out QK-logit ROC AUC is at least `0.60` and its 95% conditional
   test-source component-
   bootstrap lower bound is above `0.55`.
3. **Increment over token-local linear baseline:** combined residual-plus-QK `[r,z]` AUC minus
   residual-only AUC is at least `0.02` and its paired bootstrap lower bound is above `0`.
4. **Matched-pair directionality:** at least `60%` of held-out matched pairs assign a larger QK-link
   classifier score to the dependency edge than its exactly matched non-edge, with a lower confidence
   bound above `0.50`.

All four gates and all decision-critical intervals consume only `z`, `r`, and `[r,z]`. A focused
negative-reachability test must substitute valid normalized-attention `a` scores and prove they do not
change or enter any gate payload.

Overall decisions:

- All gates pass both directions: `MATCHED_QK_LINK_INCREMENTAL_PREDICTIVE_DISCOVERY` and
  nominate, but do not run, a fresh confirmatory QK-link representation comparison. This is
  not an isolation or causal-mechanism result.
- Recovery passes but the increment or directionality gate fails:
  `MATCHED_QK_LINK_DETECTABLE_NOT_INCREMENTAL`.
- Recovery fails in either direction: `MATCHED_QK_LINK_SIGNAL_NOT_DEMONSTRATED`.
- Any support/technical gate fails: `RELATIONAL_EDGE_STUDY_INELIGIBLE`; do not repair or train.

The result cannot reopen position/context, authorize an SAE, or support a causal-attention claim.

## Approach

Create a new isolated code/config/data/run/result family. Reuse only generic, tested parsing,
hashing, signature, deterministic matching, and metric utilities by import or small copied functions;
do not call an Attempt-13/14 continuation entrypoint. Acquire and hash the two pinned UD snapshots,
build all rows and bootstrap maps label-only, implement/test extraction and analysis, freeze the exact
candidate, obtain `/adversarial` SHIP, run signed synthetic backend QA, authorize one-shot science,
then launch the exact pipeline in tmux on a free bound GPU.

### Alternative considered

ParTUT and ATIS are closer to the model's dominant language but lack genuine document groups; treating
individual sentences as documents would repeat the cluster-support mistake that invalidated earlier
MSAE measurements. Reusing GENTLE/CTeTex or AnCora would not satisfy the requested separate-corpus
fork. Arabic-PADT was considered and rejected label-only because conservative exact-surface/MWT
rules plus the final matched-control construction left only 31 components and 79 pairs. Conditional
on the frozen exposure audit, the Ukrainian/Latvian pair trades English-domain proximity for genuine
document support and project endpoint-outcome-unseen status; all conclusions
will explicitly retain the multilingual/OOD and possible-pretraining-exposure limitations.

## Milestones

### M1 — Close and synthesize the old program

- Verify and record Attempt-13/14 hashes.
- Write `reports/architecture_program_closure_v1.json` and
  `docs/encoding_separability_paper_draft.md`. The closure binds exact terminal decision strings and
  separately enumerates supported positive claims, failed gates, unmeasured claims, and forbidden
  claims.
- Acceptance: the complete preservation manifest has no gaps; no preserved file changes; training
  permissions are false; the paper preserves positive recoverability alongside failed specificity and
  contains no nonexistent learned-model comparison.

### M2 — Acquire and prepare the new relational-edge study

- Copy the pinned Ukrainian-IU and Latvian-LVTB snapshots with provenance; retain Arabic-PADT only in
  the disclosed label-only rejected-candidate ledger.
- Build and freeze the complete prior-exposure/content-overlap audit, then build exact-surface
  tokenization layouts, exact matched components, folds, support audits, rows, inference units, and
  frozen bootstrap/swap maps without loading model weights.
- Acceptance: both sources pass all support floors; source/prepared hashes and development exposure
  are reported; natural-surface and alignment audits have zero retained failures; otherwise
  terminalize prescore-ineligible and do not infer.

### M3 — Implement the extractor and analyzer

- Add a namespace-isolated eager-attention/QKV extractor with pre-softmax rotary-logit recovery,
  feature cache, transfer scoring, decision logic,
  lifecycle, and tmux launcher.
- Acceptance: focused tests cover matching, no ancestry, document disjointness, multi-subtoken
  pooling, exact-surface reconstruction, MWT/empty-node rejection, ambiguous-offset rejection,
  causal/padding masking, feature shapes/finiteness, metric gates, conditional combined-versus-
  residual gain, endpoint missingness, namespace isolation, no optimizer/training path, and
  preservation checks. Negative reachability tests inject Arabic and Ukrainian/Latvian dev/test rows
  and require rejection before inference-unit creation; every retained row/unit must trace to exactly
  one configured pinned train-file hash.

### M4 — Adversarial exact-candidate review and QA

- Freeze the candidate inventory and GPU identity.
- Run `/adversarial` on the exact candidate; fix every BLOCK/REVISE issue and refreeze/re-review.
- Run only synthetic backend QA after SHIP.
- Acceptance: exact-bound `VERDICT: SHIP`, all focused tests pass, synthetic QA passes, and no source
  model forward has occurred.

### M5 — One-shot tmux execution

- Create signed authorization, recheck a free bound GPU, and launch the pipeline in tmux.
- Acceptance: tmux session and GPU UUID are recorded; a signed terminal records complete, failed, or
  ineligible status; no neural training/checkpoint/optimizer exists.

### M6 — Post-result claim review

- Run the research claim review over the frozen result before presenting scientific conclusions.
- Acceptance: report the claim-review verdict and limitations without modifying or rerunning the
  study.

## Definition of done

- [ ] Attempt 13 and Attempt 14 remain byte-identical and permanently closed.
- [ ] A paper draft accurately frames encoding versus separability and includes no learned-comparator
   claim.
- [ ] The new study uses a separate namespace and genuinely different pre-softmax QK-link object.
- [ ] Raw sources, prior-exposure audit, prepared sample, code, thresholds, seeds, GPU, and bootstrap
  maps are hash-bound before science.
- [ ] `/adversarial` returns exact-candidate SHIP before any source model forward.
- [ ] Tests and synthetic QA prove extraction/analysis and fail-closed behavior.
- [ ] The one-shot study runs in tmux on an attested free GPU and records a terminal.
- [ ] No neural/representation training, optimizer, or checkpoint is run or authorized.
- [ ] A post-result claim review precedes any promoted interpretation.

## Risks and one-way doors

- **Scientific opening is irreversible:** source inference consumes the study key even if later code
  fails. Freeze/review/QA must therefore precede authorization.
- **Multilingual OOD scope:** a failure may reflect Pythia's language coverage; it cannot establish
  the absence of relational attention generally.
- **Attention is observational:** success establishes predictive edge organization, not causal use.
- **Fit-source uncertainty:** held-out intervals condition on one fitted source estimator. Do not call
  them full pipeline uncertainty.
- **Attention implementation:** framework hooks can silently change tensor semantics. Exact synthetic
  recomputation and pinned dependency versions are blocking checks.
- **Dirty historical worktree:** candidate inventories must enumerate only the new study and exact
  preserved artifacts rather than pretending the entire repository is clean.

## Verification plan

- `python -m pytest -q tests/test_relational_attention_edges_v1.py`
- `python -m py_compile scripts/relational_attention_edges_v1.py scripts/build_relational_attention_edges_v1.py scripts/analyze_relational_attention_edges_v1.py scripts/run_relational_attention_edges_v1.py`
- Label-only build/rebuild comparison: byte-identical manifests, row files, and bootstrap arrays.
- Hash verification of Attempt-13/14 before freeze, preopening, and postflight.
- Synthetic CPU tests for analysis; synthetic GPU backend QA for eager attention/QKV pooling.
- `/adversarial PLAN_RELATIONAL_EDGE_V1.md`, followed by exact-candidate `/adversarial` review.
- tmux/GPU/process inspection after launch and signed terminal verification after completion.
