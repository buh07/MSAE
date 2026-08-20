# PLAN — Paper synthesis and relational-object development study

> Written by `/plan`. Attacked by `/adversarial` before implementation. This plan creates a new
> research question and namespace; it never reopens Relational Attention Edges Discovery 2.

## Goal

Produce a complete evidence-audited `PAPER.md` for the MSAE project and, in a separate development
program, determine whether token-pair/attention-edge objects show cross-source relational recovery
and functional specificity strong enough to justify a future fresh-corpus preregistration.

## Non-goals

- Do not retry, edit, delete, or relabel the signed Discovery-2 opening/terminal or its frozen inputs.
- Do not train K2, a supervised context/local decomposition, a shared branch, an SAE, or any neural
  representation model. Ephemeral ridge probes are fitted analysis estimators, not representation
  training; their coefficients and selected hyperparameters are logged but never deployed as modules.
- Do not weaken Attempt-14 specificity gates or promote its projection as matching an untrained model.
- Do not call parser validation or opened-source development confirmatory evidence.
- Do not inspect, download, or score the future confirmation corpus before a development nomination.
- Do not begin multi-layer or nonlinear screening in this study; those remain later hypotheses.

## Constraints

- `PAPER.md` must separate valid results, exploratory negatives, invalid/technical stops, and claims
  that are unsupported. Every quantitative statement must point through a machine-readable claim ledger to an exact artifact
  SHA-256 and JSON pointer/table row.
- Attempts 13/14 and Relational Discovery 1/2 lifecycle records remain byte-immutable.
- The parser is a new reusable module, not a patch to the frozen Discovery-2 builder.
- Parser behavior follows the CoNLL-U specification, including sentence-initial `0.j` enhanced empty
  nodes, and rejects structurally malformed/truncated input without requiring nonstandard EOF rules.
- Parser validation uses only already-opened local corpora and performs no model forward.
- Development model work uses only already-opened English-EWT and Latvian-LVTB train sources at their
  pinned revisions. EWT has substantial prior project exposure and is not endpoint-unseen; that is acceptable
  only because this study is explicitly opened development. Both sources are permanently development-only at
  opening. Ukrainian-IU remains rejected label-only prescore evidence and cannot reach model inference.
- Future scientific evaluation requires genuinely fresh sources and a new preregistered namespace.
- All experimental runs are config-driven, seeded, append-only, hash-bound, and have a CPU synthetic
  smoke path. No neural optimizer, backward pass, checkpoint writer, or learned representation
  persists. Ephemeral fold-local ridge coefficients are fitted and logged as analysis artifacts.
- Before any opened-source model forward: parser validation must pass, the development protocol and
  implementation must receive `/adversarial` SHIP, exact source/model/config hashes must be frozen,
  and a free GPU identity must be rechecked.

## Codebase and design grounding

- `/query-codebase def/refs _strict_prior_conllu_sentences` showed the defective parser is confined to
  the frozen Discovery-2 builder and its tests; the new parser can be isolated without modifying it.
- `/query-codebase def/refs pool_link_features` showed D2 already implements pooled QK, normalized
  attention, value, transport, and residual features at one call site; v2 may copy/rederive the
  mathematical objects but may not import mutable D2 lifecycle code or write its namespace.
- `/query-codebase def decision_from_primary` located the D2 ridge/gate logic; v2 will define a new
  development-only selection rule rather than reinterpret D2 thresholds.
- `/design` returned no MSAE-specific design canon. The user's requested design therefore governs:
  deterministic nonlearned relational objects first; learned models only after cross-source recovery
  and matched edge-specific functional evidence.

## Approach

### Paper

Build `reports/paper_claim_ledger_v1.json` before prose. Each claim record freezes: claim ID, permitted
wording, exact evidence path and SHA-256, JSON pointer or table row, denominator/unit, evidence status
(`valid`, `exploratory`, `technical-invalid`, or `unsupported`), supersession ancestors, and the final
artifact that wins any conflict. A verifier rejects missing files, hash drift, invalid pointers,
superseded evidence presented as current, or quantitative prose claim IDs absent from the ledger.
Build the manuscript from this ledger and signed post-result reviews. The organizing claim is an
encoding–separability distinction: positional/contextual/syntactic information is decodable and some
geometry is stable, but the tested token-local linear decompositions lack consistent functional
specificity. Technical-invalid attempts are methodological evidence, not negative effect estimates.

### Parser development

Create `scripts/conllu_spec.py` with two explicitly named profiles. `strict` implements the Universal
Dependencies CoNLL-U v2 format specification retrieved on 2026-08-04 (the parser report records the
exact official URL and a vendored specification-note SHA-256). `reader` shares all row, typed-ID,
reference, and tree checks but may normalize CRLF and accept a clean-EOF final sentence while emitting
machine-readable deviation codes; it is never described as conformant. Freeze the strict matrix:

- every non-comment row has exactly ten nonempty tab fields (underscore is nonempty);
- integer IDs are consecutive `1..n`; HEAD is an in-sentence integer including 0, never self; the
  basic HEAD graph is single-rooted/acyclic and HEAD=0 iff DEPREL is `root`;
- range IDs are ordered, nonoverlapping, precede their covered integer rows, and have `_` in LEMMA,
  UPOS, XPOS, HEAD, DEPREL, and DEPS; FEATS is `_` except that exactly `Typo=Yes` is permitted, and
  FORM/MISC follow their ordinary field rules;
- empty IDs accept `0.1`, `0.2`, ... before integer 1 and ordinary `i.1`, `i.2`, ... immediately after
  integer `i`; suffixes start at 1 and are consecutive; HEAD/DEPREL are `_` and DEPS is
  nonempty/non-`_`;
- every integer or empty-node reference in DEPS is either `0` or an ID present in that sentence;
  DEPS entries use `head:relation`, are separated by `|`, and are sorted by typed tuple
  `(integer_part, suffix)` with an absent suffix ordered before suffix 1 (so `i < i.1 < i.9 < i.10`);
  they contain no range heads and prohibit duplicate `(head, relation)` pairs (distinct relations on
  one head remain permitted);
  FORM/LEMMA/UPOS/XPOS/FEATS/MISC accept `_` where the format permits it, while tabs/newlines and
  empty fields are rejected; UPOS, FEATS ordering, and MISC conventions are validated only where the
  cited format marks them mandatory, not where it merely recommends them;
- every sentence has exactly one nonempty `sent_id` and exactly one `text` comment before its rows;
  `sent_id` is unique across the validated treebank/manifest; comments cannot follow data rows; a new
  header or restarted integer ID without a blank separator fails with exact path/line;
- strict UTF-8 in NFC normalization, LF line endings, and a terminal blank line are required; CRLF,
  clean EOF without the sentence-closing blank, partial rows, and partial known metadata headers fail
  in `strict`. Fixtures separately prove that `reader` accepts only the documented CRLF/clean-EOF
  transport deviations and reports them.

The fixture suite includes valid and invalid cases for every rule and records their expected status
from the official format specification. If an official validator is locally available, run it as a
cross-check on fixtures; do not add a network/runtime dependency. The parser-development audit manifest
remains exact and fail-closed at `configs/relational_objects_v2/development_conllu_manifest.json` SHA-256
`33dda86ae1313a4a46fb467bf0c455f36204021ba5865e123bcc7097d15c93ff`, with 14 immutable EWT, GUM,
Ukrainian-IU, and Latvian-LVTB development/QA entries including two byte-verified aggregates. Separately,
the model-forward gate uses a reviewed two-entry manifest containing only the exact EWT-train and
Latvian-train path/hash/role identities and binding the current amended plan. Every entry in both manifests
must pass `strict`; membership cannot change based on representation outcomes.
Publish counts/errors in a deterministic report and byte-identical rebuild. Also run a supplemental
all-opened-file audit; its failures are reported as evidence of input nonconformance but files outside
the exact parser-development and model-forward manifests do not block this study. `reader` results are supplemental and can
never rescue a strict validation error in either exact manifest.

### Relational-object development

Enumerate positive dependency edges and within-sentence negative pair candidates, then pair positives
and negatives across disjoint documents. The canonical recovery stratum, with no fallback, is:

- absolute surface UD-token index gap (not dependency-tree distance);
- causal orientation (`later_query_is_head` versus `later_query_is_child`);
- query UPOS, key UPOS, query/key coarse morphology signatures, punctuation flags;
- query/key selected-subtoken counts;
- fixed query-index bin `[0,4,8,...,256]`, causal-key-count bin of width 8, and sequence-subtoken-length
  bin of width 16.

A negative candidate is neither a direct edge nor an ancestor/descendant pair in either direction.
Its pseudo-head/pseudo-child roles and orientation are copied from the matched positive only after the
candidate is enumerated; roles are never prediction features. Normalized FORM/lemma cannot feasibly be
exact-matched at the required document support, so no lexical-identity matching claim will be made.
Instead, report endpoint FORM/lemma imbalance and include fixed-seed feature-hashed FORM, lemma,
morphology, punctuation, and geometry in every nuisance baseline.

Use document-disjoint components and cross-source transfer. Tokenization keeps only UD words whose
selected model subtokens form a nonempty contiguous span and excludes truncation. Let `r(w)` be the
float32 arithmetic mean of block-3 input hidden states over all selected subtokens of word `w`. For
the causally available directed pair, let query `q` be the **last** selected subtoken of the later
word and `K` all selected subtokens of the earlier word. From the model's eager float32 attention,
let `q_h`, `k_hj`, and `v_hj` be the post-RoPE query/key and pre-output-projection value vectors for
head `h`, and let `p_hqj` be the masked softmax probability. Compare these deterministic objects at
Pythia-160m-deduped block 3 under the same frozen evaluator:

1. child/head residual concatenation `[r(child); r(head)]` (1,536 dimensions);
2. ordered residual difference `r(head)-r(child)` (768 dimensions);
3. per-head scaled rotary QK link, `|K|^-1 sum_j (q_h dot k_hj)/sqrt(64)` (12 dimensions);
4. per-head attention-edge mass, `sum_j p_hqj` (12 dimensions; descriptive only);
5. transported value, concatenating `sum_j p_hqj v_hj` over heads (768 dimensions, before the
   attention output projection, with no mass normalization);
6. nuisance/residual baseline combined separately with QK or transported values.

All masks use the model's ordinary causal and padding mask; no logits or probabilities are recast to
float16. Exact tensor axes, selected row IDs, shapes, pooling equations, rotary implementation,
scaling, masking, and C-order float32 bytes are verified against an independent synthetic reference
before any development forward.

The primary nonlearned baseline `B` is a deterministic feature map: residual concatenation plus one
fixed-seed, signed 2,048-dimensional hashing vector containing child FORM, head FORM, child lemma,
head lemma, and their ordered FORM/lemma pairs; fixed one-hot coarse morphology/punctuation; and four
float geometry fields (surface gap, query index, causal-key count, and sequence length). Residual
difference is reported as a separate descriptive object rather than redundantly included in `B`.
Ridge fitting does not make `B` a learned representation. Two complete, multiplicity-controlled nomination
paths are evaluated independently:

- QK path: `B + QK` versus `B`;
- transport path: `B + transported_value` versus `B`.

A path must pass every one of its own recovery and increment gates in both transfer directions; metrics
may not be mixed across paths. Both paths use one-sided 97.5% component-bootstrap lower bounds, giving
a Bonferroni familywise 5% allowance across the two possible paths. Concatenation, difference, and
attention-weight-only results remain descriptive.

Every row receives weight `1/(number of rows in its document-component)`, normalized so each
component has total weight one. StandardScaler fitting, RidgeClassifier fitting, validation AUC,
held-out AUC, and bootstrap refits all use these weights; bootstrap component multiplicity multiplies
the component's normalized row weights. Tests include deliberately unequal component sizes.

The estimator is frozen as StandardScaler plus RidgeClassifier with alphas `[1, 10, 100]`, `lsqr`,
tolerance `1e-6`, intercept on, no class weighting, and no estimator persistence. Five deterministic
fit-source component folds select alpha by mean fold AUC; ties choose the larger alpha. The selected
alpha refits on all fit-source components and evaluates the untouched other source. Each of 500 draws
independently resamples fit and test document-components **within each fixed fold** with replacement,
thereby retaining every fold, redoes alpha selection and refitting, and uses the same stratified draw
maps for `B` and its paired augmented path. Each component contains a balanced edge/nonedge pair, so
within-fold resampling preserves both classes. Quantiles use NumPy `method="linear"` over exactly 500
defined draws. Any algorithmic failure or nonfinite metric invalidates the entire endpoint; failed
draws are never discarded or assigned a favorable value.

Functional edge-specificity uses an exact local attention intervention for the last selected subtoken
of the later word as query and every selected subtoken of the earlier word as key span `S`. For head
`h`, let `p_hk` be the original causal attention probabilities, `m_h=sum_{k in S} p_hk`, and `v_hk`
the value vectors. For `eps=1e-6`, heads with `m_h<=eps` or `m_h>=1-eps` are
ineligible; an example is functionally ineligible unless **all 12 heads** satisfy this rule, so every
functional contrast uses the same fixed head population. Otherwise set `p'_hk=0` for `k in S` and
`p'_hk=p_hk/(1-m_h)` elsewhere. All other query
rows are byte-unchanged. Define original/post head outputs `o_h=sum_k p_hk v_hk` and `o'_h=sum_k
p'_hk v_hk`. The primary per-example scalar is not computed by subtracting nearly equal float32
outputs and dividing by mass. Cast cached float32 probabilities and values to float64; in increasing
key-index order compute `u_in=sum_{k in S} p_hk v_hk/m_h` and
`u_out=sum_{k not in S} p_hk v_hk/(1-m_h)`, then define

`E_local = RMS_h( ||u_out-u_in||_2 / sqrt(d_head) )`.

This equals the outside-key weighted-mean value minus the removed-span weighted-mean value and removes
the mechanical multiplicative effect of original link mass. It measures local value selectivity, not
edge importance. To prevent a tiny-mass link with a large normalized contrast from passing alone,
also define the unnormalized projected-change RMS

`E_abs = ||W_o concat_h(m_h (u_out-u_in))||_2 / sqrt(768)`.

Mass eligibility uses the cached float32 `m_h`. `E_local`'s authoritative nuisance-regression,
bootstrap, and gate value is the ordered float64 analytic value. `E_abs` is computed in both the
frozen float32 intervention path and an ordered float64 analytic reference; the **float32
intervention-path value** is authoritative for nuisance regression, bootstrap, and gates. Synthetic
QA freezes their atol/rtol and tests masses immediately above both `eps` boundaries. A QA mismatch
stops before development scoring.

For descriptive scale context only, report `E_rel = E_abs / RMS(block_input_at_q)`, requiring the
block-input RMS to exceed `0.1`; no gate divides by an arbitrary numerical floor, and an ineligible
descriptive `E_rel` never invalidates primary `E_local` or `E_abs`. All cached tensors receive an
explicit finiteness check before the precision-specific rules above are applied.

Apply all 12 head-row replacements, concatenate heads, and pass through the frozen attention output
projection. The intervention claim is restricted to **local attention-block functional edge-
specificity**. RMS block-output and final-residual changes are secondary descriptive quantities only;
they cannot support a downstream-model or causal-module claim. The `m≈0` and `m≈1` cases are
ineligible—never silently zeroed, clipped, or evaluated on a changing subset of heads.

Functional positive/nonedge pairs use the recovery stratum plus fixed mean-mass bins
`[0,1e-4,1e-3,1e-2,.05,.1,.25,.5,.75,.95,1]`, where mean mass is the arithmetic mean of all 12
`m_h`; no fallback is permitted. A sentence/token pair or negative candidate may occur in only one
functional pair, and each document may occur in only one connected component. Each component has
equal endpoint weight: first take the arithmetic mean of its pair contrasts, then average components.
For every source/orientation, publish denominators and require: at least 50% of otherwise recovery-
eligible true edges pass the all-head mass rule, and at least 20% of those eligible edges enter an
exact-stratum functional pair without reuse. Failure makes only that functional endpoint ineligible.

Functional effects receive a prespecified lexical/geometry nuisance adjustment rather than an
unsupported exact-lexical-match claim. The fixed nuisance vector contains 2048-bin endpoint FORM,
lemma, and ordered-pair hashes; coarse morphology and punctuation; surface gap; query index;
causal-key count; sequence length; all 12 original `m_h`; query/key value-vector norms; and the
unablated projected-attention-output norm. Within each source and causal orientation, five
component-disjoint folds cross-fit `StandardScaler + Ridge(alpha=100, fit_intercept=True)` separately
for `E_local` and `E_abs`, without edge status as an input. Row weights are inverse component size in
both scaling and regression. The endpoint is the component-mean paired true-edge-minus-nonedge
held-out residual. Folds have balanced component counts (difference at most one). Every bootstrap draw independently
resamples components within **each** fixed fold using draw multiplicities, refits the other four
folds, and evaluates that held-out fold. This preserves all five folds and both pair statuses by
construction. Any reused row, algorithmic failure, or nonfinite quantity invalidates the entire
functional endpoint; no failed draw is omitted from its interval.

“Reused row” means base-row reuse across distinct matched pairs or train/held-out folds; repeated
selection of one component within a bootstrap draw is permitted only through its recorded draw
multiplicity. Functional one-sided 95% lower bounds are the `0.05` NumPy quantile with
`method="linear"`. The raw true-edge `E_abs` estimand is the arithmetic mean within each component
followed by an equal-weight mean over components, and its bootstrap uses the identical within-fold
component maps as the paired adjusted endpoints.

The functional global claim is the intersection across both sources, both orientations, and both
endpoints: every one-sided 95% lower bound must exceed zero, and the one-sided 95% lower bound of the
mean true-edge `E_abs` must be at least `1e-4` in every source/orientation. Because all source,
orientation, and endpoint conditions must pass and no favorable endpoint is selected, this is an
intersection-union rule rather than a
multiplicity-driven union. The permitted wording is: **among exact-stratum-matched, all-head-eligible
opened-development pairs, true edges showed a larger nuisance-adjusted local attention-block
response than nonedges**. This is an association under a precise intervention, not dependency-
relation-specificity, a population-wide effect, or downstream importance. Coarse dependency-relation multiclass transfer is
descriptive and requires 20 source documents per reported class.

Synthetic intervention tests must prove: probability conservation in all 12 heads; zero mass on the
removed span; byte-identical nonintervened rows; equality to a manual output-projection
reconstruction; the analytic normalized-effect identity; exact `E_abs`; ineligibility when any
head has `m≈0` or `m≈1`; nuisance cross-fit train/test separation; equal component weighting; and zero
adjusted metrics when edge/nonedge masses, values, and nuisance variables are equal.

Development nomination requires all of:

- parser validation: zero errors on every distinct hash in the exact opened-development manifest;
  the supplemental all-opened audit is descriptive and cannot add files to the study;
- at least 100 document-disjoint components and 500 balanced edge/nonedge pairs per development source,
  including at least 20 functional components per causal orientation;
- in every source/orientation, all-head functional eligibility covers at least 50% of recovery-
  eligible true edges and exact-stratum no-reuse matching covers at least 20% of all-head-eligible
  true edges, with all denominators and attrition reasons reported;
- one complete QK or transport path whose augmented AUC lower bound is >= 0.55 and whose paired
  augmented-minus-`B` AUC lower bound is >= 0.02 in both directions;
- the same study's nuisance-adjusted true-edge-minus-nonedge lower bounds for both `E_local` and
  `E_abs` > 0, plus the mean true-edge `E_abs` lower bound >= `1e-4`, in every source and causal
  orientation;
- exactly 500/500 finite component-bootstrap draws for every primary interval, otherwise that
  endpoint is invalid rather than summarized conditionally;
- endpoint-specific eligibility: no result can borrow another endpoint's completeness or metric.

Failure of recovery or specificity ends the program without learned models. Passing permits only a
new plan and preregistration using genuinely fresh corpora; it does not itself authorize training.

### One-shot development lifecycle

The exact plan/config/code/source/model/tokenizer/runtime identities define a global development key and code-fixed
lifecycle paths. After parser validation, exact-candidate SHIP, environment checks, and synthetic smoke,
the runner atomically creates a signed `DEVELOPMENT_OPENED` with `O_CREAT|O_EXCL` immediately before
any opened-source model load/forward. It records both sources as permanently development-only, a random
owner nonce, and `retry_authorized=false`. Only that owner may write the append-only run root. Every
owner exception or failed gate writes a signed write-once terminal; concurrent/duplicate writers and
arbitrary output roots fail without mutation. There is no post-opening retry, including for technical
failure. Preopening checks expose no activations/outcomes and may be repaired only before the global
opening exists. Success ends in one signed `TERMINAL_COMPLETE`; it authorizes only claim review, never
training or fresh-corpus access.

**Alternative considered and rejected:** Repair and rerun Discovery 2. Its signed no-retry terminal
forbids this, and doing so would turn a technical stop into an outcome-conditioned retry.

**Simpler option:** Stop after `PAPER.md`. This is scientifically defensible and remains the default
publication path. The extra development study is justified only because it changes the representational
object from tokens to relations and uses deterministic baselines without training.

**Relevant ADRs:** none; the design ledger had no MSAE-specific entry.

## Milestones

- [ ] M1: Evidence-audited `PAPER.md` — acceptance: a machine-readable claim ledger binds each
  headline number to an exact hash/pointer/status/supersession chain and the manuscript verifier passes; valid, exploratory, and invalid attempts are explicitly separated.
- [ ] M2: Standalone CoNLL-U parser and conformance suite — acceptance: tests cover `0.1`, ordinary
  `i.j`, consecutive and skipped IDs/suffixes, sorted and unsorted DEPS, the MWT `Typo=Yes`
  exception, typed ordering through `i.10`, ranges, missing separators, EOF termination, malformed
  IDs, NFC/UTF-8 failure, strict CRLF/final-blank rejection, and reader-profile deviation reporting.
- [ ] M3: Opened-corpus parser validation — acceptance: deterministic JSON/Markdown inventory deduped
  by SHA-256 reports zero parse errors for the 14-entry parser-development audit and for the exact
  two-entry EWT/Latvian model-forward manifest, separately reports the all-opened audit, and performs no
  model import/forward.
- [ ] M4: Development harness and synthetic smoke — acceptance: config, matcher, extractor, relational
  objects, ablation, ridge transfer, bootstrap, provenance, and no-training tests pass on synthetic data.
- [ ] M5: Exact development candidate adversarial review — acceptance: first nonblank line is
  `VERDICT: SHIP`, bound to exact plan, code-tree, config, source, model, tokenizer, and runtime
  identities, before model loading.
- [ ] M6: Opened-source development run — acceptance: one append-only run on a rechecked free GPU,
  one signed no-retry terminal, exact metrics/artifacts, and no neural optimizer/checkpoint/learned
  representation; ephemeral ridge fits are logged analysis estimators.
- [ ] M7: Post-result claim review and manuscript update — acceptance: independent claim verdict is
  recorded and `PAPER.md` labels the development evidence appropriately.
- [ ] M8: Conditional future-study decision — acceptance: either a nomination memo that reserves
  unnamed fresh corpora without opening them, or a signed stop stating that learned/fresh confirmation
  is not authorized.

## Definition of done

- [ ] `PAPER.md` contains Abstract, Introduction, Related framing, Methods, chronological experiment
  record, Results, robustness/validity, limitations, discussion, conclusion, and artifact map.
- [ ] Frozen Attempt 13/14 and Discovery 1/2 hashes still match their preservation/lifecycle records.
- [ ] The new parser passes the frozen CoNLL-U v2 conformance matrix and every hash in the exact opened-
  development manifest; non-development audit failures are retained rather than relaxed away.
- [ ] No new model forward occurs before exact candidate SHIP.
- [ ] Development compares all six prespecified relational objects and matched controls.
- [ ] Recovery and functional-specificity gates are evaluated independently and cross-source.
- [ ] No neural or representation model is trained or authorized; ephemeral ridge analysis estimators
  are explicitly disclosed.
- [ ] Any result claim receives post-result research-claim review before entering `PAPER.md`.

## Verification plan

- Types/syntax: `python -m py_compile` for new Python files; shell syntax for launcher/pipeline.
- Tests: targeted parser conformance tests; matcher/lineage/object/ablation/bootstrap/gate tests;
  existing preservation and no-training tests.
- Parser validation: run the standalone validator over the explicit opened-source manifest and compare
  a second deterministic rebuild byte-for-byte.
- Synthetic smoke: tiny tensors verify manual QK, attention redistribution, pair pooling, feature
  dimensions, and endpoint-specific decision logic without model weights.
- Before launch: exact `/adversarial` candidate review, config/file hash verification, GPU UUID/free
  check, and tmux handshake.
- After results: `/research-claim-review` against the exact terminal/result bundle.

## Risks & one-way doors ⚠️

- The first v2 model forward makes the exact EWT-train/Latvian-train inputs permanently development-only;
  record this transition before loading weights. EWT has prior project model-forward/endpoint exposure, so
  neither source may be described as fresh, confirmatory, or endpoint-unseen.
- Selecting thresholds after seeing development metrics would overfit. All gates above freeze first.
- Attention ablation can be off-manifold and denominator-coupled. Require both the analytic mass-
  normalized selectivity effect and a non-negligible unnormalized projected effect; keep suffix
  responses descriptive, nuisance-adjust paired true-edge/nonedge controls, and avoid causal language
  beyond the precise local attention-block intervention.
- High-dimensional concatenation/transport can win through capacity alone. Use fold-local scaling,
  fixed ridge alphas, residual-only baselines, dimensionality reporting, and combined-minus-baseline
  gates; do not claim semantic modularity from AUC alone.
- Fresh-source selection is a one-way confirmatory door. This plan deliberately stops before naming or
  inspecting future confirmation corpora.
- The Discovery-2 parser defect may tempt an informal retry. Preserve its exact code/config/terminal;
  place every new artifact under the v2 namespace.

## Open questions

- Which fresh corpora should serve confirmation is intentionally unanswered until development produces
  a valid nomination. The future preregistration—not this development plan—must decide them.
- Multi-layer and nonlinear variants remain out of scope unless the single-layer relational object
  first passes recovery and functional specificity.

## Deviations log

- 2026-08-04: New work is named relational-objects v2 rather than Discovery 3, because it changes the
  representational object and preserves Discovery 2's sole-successor terminal.
- 2026-08-04: Parser implementation of prior plan SHA-256
  `37ac45fc1bfe976dd05a9a225cf3a5e45e66633b1a955fdb8b774736191c128c` ran before any successor model
  import/forward. Its supplemental 47-file audit retained a strict failure for Arabic-PADT test SHA-
  256 `793c87bf173d491af2092ef7f87b04a2cf6c596490e7347a2065058a053a6389` at line 11216 (`U+009D` in
  MISC); the failed audit remains at `reports/opened_conllu_all_audit_v1.json` rather than being
  deleted or relaxed. That audit is immutable at SHA-256
  `dd845e8c1c81a13f51f2612f0c2f37b12e252d8e63162cd35e9c906e0cb5d23f`; any correction must use an
  append-only superseding path. Arabic-PADT had already been rejected label-only for the relational study in
  `PLAN_RELATIONAL_EDGE_V1.md:415-437`, before model outcomes. That pre-amendment record retained the 14-entry parser-development audit; the later label-only
  source amendment below creates a separate exact two-entry model-forward manifest. Neither amendment
  removes a source after seeing representation results. No model forward, endpoint score, or study key had
  occurred.
- 2026-08-04: Before any model weight load, forward, activation, or endpoint score, the initial
  Ukrainian-IU/Latvian label-only prescore was ineligible (48/100 document-disjoint components and
  171/417 pairs, respectively). An explicitly opened-development-only label/text scout found EWT at
  150 components/500 pairs and GUM at 97/500. The development comparison is prospectively amended to
  EWT and Latvian with a 150-component cap, retaining the exact matcher and all scientific gates.
  The append-only record is `reports/relational_objects_v2_prescore_source_amendment_v1.json` at SHA-256
  `8f117d905a0f9d0f8719ce4cffdd63581ddd0d277f6d016983107f3d116772ca`; its scout config, manifest, and
  support reports are preserved under `reports/provenance/relational_objects_v2_label_only_scout_v1/`.
  This support-based amendment consumes no fresh source, activation, or scientific endpoint and does
  not change the requirement that any future scientific evaluation use genuinely fresh corpora.
- 2026-08-04: The amended EWT/Latvian candidate may not open until an immutable development2 label-only
  rebuild proves both sources meet at least 100 components and 500 pairs under the exact 150-component
  cap. If either fails, this candidate stops before model loading; no third source substitution is permitted
  without another versioned amendment and independent plan review.
