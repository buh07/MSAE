# Attempt 14 — final context-versus-local falsification study

## Goal

Run one final, measurement-only test of the question:

> Do controlled changes in available prior context preferentially affect a reproducible linear
> subspace, after holding target lexical identity and absolute boundary position fixed and comparing
> against unrelated context and matched lexical substitution?

The primary scientific unit is a disjoint pair of genuine source documents. The study will use two
prospectively frozen Spanish upstream-corpus partitions that have never supplied a model activation or
context-versus-lexical endpoint outcome. It will fit only
deterministic, rank-matched SVD projections on one source and evaluate them on the other source, in
both directions. It is the last prespecified falsification study for the position/context program.

## Non-goals

- Do not train or resume K2, an SAE, a relation-aware model, or a private/private/shared model.
- Do not add seeds, capacity, incoherence, branches, layers, checkpoints, or candidate signal families.
- Do not modify, rescore, reinterpret, or continue Attempt 13.
- Do not lower Attempt-13 recovery thresholds or replace its relational controls.
- Do not run a supervised context/local model in Attempt 14. A passing result can only nominate that
  later comparison after post-result claim review and separate authorization.
- Do not use EWT or GUM as scientific sources. They remain development-only.
- Do not search outcome values across corpora, ranks, thresholds, layers, or model checkpoints.

## Frozen interpretation of Attempt 13

Attempt 13 remains the formal exploratory relational result:

> Cross-corpus relational information was detectable, but strong recovery and relation-specific
> isolation were not demonstrated.

Before any Attempt-14 source preparation, record and later recheck the signed Attempt-13 terminal,
cache completions, result completion, run/result recursive inventories, and the claim-review hash.
No Attempt-13 path is writable or imported as a scientific input.

## Constraints

### No training

- `neural_training_authorized=false`, `representation_training_authorized=false`,
  `supervised_model_training_authorized=false`, and `retry_authorized=false` are frozen in config and
  signed lifecycle artifacts.
- The only fitted objects are ephemeral rank-16 linear SVD projectors. They have no gradient,
  optimizer, learned bias, checkpoint, or persisted weights.
- New execution code must contain no reachable `.train()`, `.backward()`, optimizer, scheduler,
  checkpoint, SAE, or K2-launch path. Static AST tests enforce this.

### Sources and exposure

The first plan review correctly BLOCKED GUMReddit/CHILDES: GUMReddit has only 18 authentic documents and
redacted FORMs, while CHILDES has no `newdoc id` metadata. That review, the original candidate order, both
label-only source censuses, and all rejections remain permanent provenance.

The initially frozen partition census misclassified three single-sentence documents. It is preserved and
superseded by the exact raw-hash census and source selection in
`reports/provenance/atlas_v3_10_attempt14_corrected_source_census_v2.json` and
`reports/provenance/atlas_v3_10_attempt14_source_selection_v4.json`, both written before canonical collision,
joint-component, tokenizer, or activation inspection:

- UD Spanish AnCora, revision `20adddbfcdd773c6dc97ba48ea11ca9364e74185`, all pinned splits;
- source `ANCORA_3LB`: explicit `newdoc id` values beginning `3LB-` (279 total, 3 single-sentence,
  276 multi-sentence documents);
- source `ANCORA_CESS`: explicit `newdoc id` values beginning `CESS-` (1,356 total, 28 single-sentence,
  1,328 multi-sentence documents).

These prefixes identify separately named upstream corpora, not random post hoc partitions. They have
disjoint authentic documents, recoverable surface forms, a shared language/tokenizer, and no historical
repository occurrence, model forward, activation, or endpoint outcome. Attempt 14 is nevertheless
exploratory because both partitions share one UD release and annotation pipeline.

- The complete pre-Attempt-14 repository exposure manifest
  `reports/provenance/atlas_v3_10_attempt14_preacquisition_manifest.json` (SHA-256
  `15007e88c6ebb825f094abf3aa58ebbaeec89bd36ea9ad6f445f2ff5103b5980`) classifies all 14,099
  non-candidate regular files (161,275,571,576 bytes) and found zero pinned AnCora source-name, revision, or
  raw-file-hash hits. It was completed before raw AnCora acquisition into the repository. Any contradictory
  historical text, activation, or endpoint evidence terminates the study.
- A supplemental broad-alias scan
  `reports/provenance/atlas_v3_10_attempt14_exposure_supplement_v1.json` (SHA-256
  `d07dc463315f5d9ec73debf733dc7e2bba1e584bd576e2f9589163b590b4fc12`) found zero
  case-insensitive `AnCora`, `3LB-`, `CESS-CAST`, `CESS-ECE`, `Spanish-AnCora`, or `es_ancora` hits across
  every text-classified file in that working-tree manifest and all nine committed Git trees. This claim is
  explicitly limited to the recorded working-tree and reachable Git-history snapshot; it is not a claim
  about inaccessible or deleted external records.
- No fallback source, prefix, or partition may be introduced after joint support inspection. If either fixed
  partition is ineligible, the decision is `PRESCORE_INELIGIBLE_STOP_NO_TRAINING`.

Before component construction, compute three canonical sentence signatures symmetrically across partitions:
compact original-case integer-row FORM JSON, NFKC-lowercased whitespace-collapsed `# text`, and compact
pinned-tokenizer input-ID JSON. Equality of any signature is a collision. Whole-document equality, any
collided normalized sentence of at least 20 characters, or at least two distinct collision identities in one
document removes every affected document. Otherwise the isolated short sentence is removed from every target,
true-prefix, unrelated-prefix, lexical-target, and lexical-donor role. Removed sentences create permanent
context gaps: adjacency may never bridge them. Document/component floors are rechecked with no source
replacement and no activation-dependent backfill.

### Genuine document and component support

- Document IDs must come from explicit upstream `newdoc id` boundaries; filename, sentence-prefix, or
  fixed-size pseudo-document fallback is forbidden.
- Each source must have at least 128 genuine documents after exclusions and at least 64 accepted paired
  components. The target and donor document in a component are distinct; no document may occur in more
  than one component within a source.
- Each component jointly supplies all context and lexical conditions, so context-versus-lexical
  comparisons use the same independent document pairs.
- Require at least 64 target documents, 64 donor documents, and 64 components. Retain the entire
  maximum-cardinality matching; never truncate it to 64. Candidate edges are first ordered by the frozen
  salted hash, the deterministic matcher optimizes cardinality over all edges, and its full sorted matched
  edge set becomes `label_text_population` only after collision exclusions and all role checks. The 500 exact fit-source
  bootstrap maps are materialized before inference; at least 490 must contain at least 16 distinct
  components. There are no analysis folds because no cross-validation estimator is used.
- Source selection, edge construction, maximum-cardinality document matching, tie-breaking,
  exclusions, and row order are deterministic from the seed and frozen raw/tokenizer hashes.
- Support is measured before model inference. No resampling-until-favorable rule or post-outcome backfill
  is allowed.

## Exact intervention design

Each accepted component contains a target document with adjacent sentences `(previous, target)` and a
distinct donor document containing an unrelated prefix. The previous and donor prefixes have exactly the
same tokenizer-subtoken length. The complete target sentence is byte/token identical across context
conditions. All context conditions have identical total length, target token index, `position_ids`, and
natural-boundary placement.

Every sentence is reconstructed surface-faithfully before any component inspection. The builder parses
integer rows, multiword-token ranges, and `SpaceAfter=No`; it emits each MWT surface once and each non-MWT
integer FORM once, and requires byte equality to the upstream `# text`. Sentences lacking exact equality are
ineligible. The pinned Pythia tokenizer then tokenizes the full reconstructed sentence once with
`add_special_tokens=False` and returns character offsets. Eligible target, donor, and downstream-control
integer rows must be outside every MWT range and map unambiguously to tokenizer offsets. Targets and donors
must each map to exactly one tokenizer ID whose offset, after trimming only leading Unicode-whitespace
characters included by the byte-level pretokenizer, equals the complete integer-row FORM span. No trailing
or internal character may be trimmed. Ambiguous, overlapping, zero-width, or MWT-internal rows are ineligible. The substituted full target surface is
retokenized once and must have the same total ID length and token-index/UD-row correspondence, with exactly
one changed ID at the mapped target position and byte-identical IDs everywhere else. The unchanged
downstream control must map to the same token index before and after substitution. Absolute character
offsets after a different-character-length replacement may shift and are not required to match. Tokenizer collision signatures use these
corrected full-surface IDs. All tokenizer support is recomputed under this rule before model inference.

The natural within-document boundary is exactly one ASCII space. Freeze
`target_segment_surface = " " + target_surface`; tokenize that complete target segment once. For every true
or unrelated prefix, require that tokenizing the full combined surface
`prefix_surface + " " + target_surface` produces exactly
`prefix_ids + target_segment_ids`. This identity must also hold after lexical substitution. No EOS,
end-of-document token, synthetic delimiter, or newline is inserted. Conditions are formed only by
concatenating the verified `prefix_ids + target_segment_ids`. The true sequence therefore exactly tokenizes
the adjacent within-document sentence surfaces joined by ordinary prose whitespace; the unrelated sequence
has identical geometry but different matched-length prefix IDs. Position IDs are the identical integer range
`0..L-1`.

The response location is one single-subtoken target token with UPOS in the frozen open-class set
`{NOUN, VERB, ADJ, ADV, PROPN}`, chosen deterministically by
salted hash from tokens that also admit the frozen lexical substitution below. Selection uses only text,
UD labels, tokenizer alignment, and source/document IDs—never activations.

### Context factorial

Four cached conditions use identical sequence geometry:

1. `true_masked`: actual previous sentence, but its prefix positions have attention mask 0;
2. `true_unmasked`: actual previous sentence with prefix attention enabled;
3. `unrelated_masked`: matched-length donor prefix with prefix attention mask 0;
4. `unrelated_unmasked`: the same donor prefix with attention enabled.

The target segment is always unmasked. Target queries cannot attend masked prefix keys; prefix positions also
cannot attend future target positions under causal masking. Masked-prefix
conditions are separately checked for numerical equivalence at the target.
Define, from the same float32 cache and reduction path:

- `d_true = true_unmasked - true_masked`;
- `d_unrelated = unrelated_unmasked - unrelated_masked`;
- `d_context = d_true - d_unrelated` (the coherent-context difference-in-differences).

The lexical original reuses the exact `true_unmasked` cached row; it is not forwarded or pooled twice. The
only fifth unique sequence is `substituted_true_unmasked`. Exact row lineage enforces that reuse.

The primary context signal is `d_context`. `d_true` versus `d_unrelated` is the prespecified unrelated-
context specificity contrast, not an optional diagnostic.

### Matched lexical substitution

Using the same target/donor document component, replace the selected target token with a different donor
form observed in the paired donor document while keeping the true prefix unmasked. Because every document
occurs in only one component, neither a donor occurrence nor its document can be reused. The replacement
must match:

- exact UD UPOS;
- exact equality of the complete canonical sorted UD FEATS mapping (including an empty map);
- capitalization class;
- tokenizer subtoken count (one);
- source-frequency quartile;
- and sequence/word alignment, with exactly one changed token ID.

The source-frequency quartile is computed from document frequency within the source partition. The donor
form and lemma must satisfy two separate NFKC-lowercase comparisons: donor form differs from target form,
and donor lemma differs from target lemma. The donor
form may not occur in either context prefix or introduce a target-sentence
duplicate. Candidate donor occurrences and target tokens are ordered by the frozen salted hash, and the
maximum-cardinality document matcher resolves ties by that exact order.

Define `d_lexical = substituted - original` at the changed token. Also cache the nearest eligible unchanged,
non-punctuation single-subtoken token strictly downstream of the substitution, with target-to-control offset
in frozen bins `1-2`, `3-4`, or `5-8`; no upstream or missing-control fallback is permitted. Its delta is a
scientific collateral-localization control. Components are never excluded because the changed-token delta
does or does not exceed this control. The lexical-localization gate is evaluated across the frozen population
and a measured failure blocks specificity rather than changing the sample.

## Numerical validity

- All representations are extracted once in float32 and all deltas are computed from that cache in
  float64.
- Exact row IDs, input IDs, attention masks, position IDs, source hashes, tokenizer revision, and cache
  hashes are bound into signed artifacts.
- Masked-prefix equivalence is a technical QA check at the selected target. Because neither prefix is
  attendable, the normalized difference between
  `true_masked` and `unrelated_masked` must be at most `1e-5`. The exact inclusive failure rule is
  `failure_count / frozen_label_text_population_count <= 0.005`, separately by source at the target location.
  Components with a nonfinite representation or a masked-equivalence failure are removed from the
  `context_population` with no backfill.
- The same masked-prefix equivalence statistic is recorded descriptively at the frozen downstream location,
  but a downstream-only discrepancy cannot remove a target-valid context row or change any gate. Gate 6 uses
  finite unmasked original/substituted downstream representations, not masked replay.
- Scientific deltas use `||a-b|| / max(||a||, ||b||, 1e-12)` in float64. The frozen descriptive
  small-delta threshold is `1e-4`, but **no finite component is ever excluded because a scientific delta is
  small**. Every finite low-norm component is retained and its low-norm indicator reported. Context raw
  measurability is a source-level central estimand, not a zero-outlier rule: separately for `d_true` and
  `d_context` in each source, the median normalized magnitude must exceed `1e-4` and its paired 500-map
  bootstrap 95% lower bound must exceed the `1e-5` technical-noise scale. Lexical raw measurability uses the
  same median/lower-bound rule for `d_lexical` on `lexical_population`. The `1e-4` point threshold is ten
  times the frozen technical-equivalence scale; the lower-bound rule requires a population signal above that
  noise scale while allowing heterogeneous weak rows. The fraction at or below `1e-4` is descriptive only.
  Small `d_unrelated` is retained and is neither a technical failure nor adverse scientific evidence.
- A per-component capture denominator at or below `1e-12` yields capture `0.0`; the component is not omitted.
  Fit-matrix rank deficiency is estimator ineligibility at the frozen rank, not a measured negative result
  and not permission to lower the rank.

The inference backend is frozen to Pythia-160m revision
`582159a2dfe3e712a8d47ae83dec95ae3bde8e7e`, hidden-state index 4 (layer 3), float32, eager attention,
`model.eval()`, `torch.inference_mode()`, `use_cache=False`, explicit identical `position_ids`, and an explicit
2-D attention mask. Each component's five unique same-length conditions are forwarded in one paired batch with no
other component. Prefix positions are masked as keys at every layer; target and downstream
control positions remain unmasked. Runtime artifacts attest every invariant.

Population precedence is frozen:

1. `label_text_population` is the full no-backfill maximum-cardinality matched set per source;
2. `context_population` contains each label/text-valid component passing target-location
   masked-equivalence/nonfinite technical QA; it never depends on downstream-only QA or observed lexical behavior;
3. `lexical_population` contains label/text-valid components with finite original, substituted, and downstream
   lexical representations; no scientific delta-size comparison can remove a row;
4. `joint_population` is the complete-case intersection and is the only population used for gates 2, 3, and 5;
5. the target-location context nonfinite and masked-equivalence checks plus the original/substituted/
   downstream lexical nonfinite checks are the exhaustive endpoint-specific activation-dependent removals;
   their counts are reported separately;
6. every population receives the no-backfill 64-component support recheck. Loss of lexical/joint support can
   make specificity ineligible but cannot erase eligible context results or become a favorable pass.

Unit tests may use a toy model. After exact candidate `SHIP` and before science authorization, the immutable
production inference function must additionally pass the signed Pythia synthetic-token backend validation at
the exact pinned revision, layer, dtype, attention implementation, and GPU. This validation uses no AnCora
tokens and cannot change code or thresholds; failure terminates the candidate.

## Frozen projection analysis

For each transfer direction, fit the following exact rank-16 uncentered right-singular subspaces:

- gates 1 and 4: `P_context_context`, fit from `d_context` on the fit source's `context_population` and tested
  on the held-out source's `context_population`;
- gates 2, 3, and 5: `P_context_joint` from `d_context` and `P_lexical_joint` from `d_lexical`, both fit on
  exactly the same fit-source `joint_population` and both tested on exactly the same held-out-source
  `joint_population`;
- gate 6: no projector; evaluate the changed-versus-downstream lexical magnitude on each source's
  `lexical_population`.

Ranks are fixed at 16; no rank sweep is scored. A projector is identifiable only when its fit matrix has at
least 16 distinct rows and numerical rank at least 16 under `s[15] / s[0] >= 1e-6`. A draw failing either
rule is nonfinite; arbitrary zero-singular-value/null-space vectors are forbidden. Projectors are ephemeral
and never written. Capture is the squared-norm fraction `||dP||^2 / ||d||^2`, computed per independent
component and set to zero when its denominator is at most `1e-12`. Every gate statistic is the unweighted
arithmetic mean of its paired per-component capture, capture difference, complement, or normalized-magnitude
difference, except gate 4. Its exact scale-aware paired statistic is
`(||d_true P_context_context||^2 - ||d_unrelated P_context_context||^2) /
max(||d_true||^2 + ||d_unrelated||^2, 1e-12)`. Thus a negligible unrelated response contributes negligible
projected energy instead of an unstable scale-free capture fraction. Its `0.05` margin means that true context
must contribute at least five percentage points more projected energy relative to total paired intervention
energy; this analytic interpretation, not AnCora data, fixes the margin. Gate 5's lexical complement is
defined directly as `||d_lexical(I-P_context_joint)||^2 / ||d_lexical||^2` and is conservatively set to
`0.0` when `||d_lexical||^2 <= 1e-12`; it is never computed as a favorable `1-capture` shortcut for a
zero-energy row. The random geometric reference is the exact analytic Haar expectation
`rank / width = 16 / 768`; there is no sampled random seed or ensemble. The same fitted projectors are applied
unchanged to the held-out source.

All uncertainty uses 500 hierarchical cross-source bootstrap draws that independently resample the exact
fit- and test-source population for that gate. Gates 1--5 refit their required projector or projectors inside
every draw; gate 6 resamples only the evaluated source's `lexical_population`. Thus intervals include
fit-source sampling and projector-estimation uncertainty wherever a projector exists. Every primary interval
needs at least 490 finite draws. Intervals are percentile intervals using NumPy's linear quantile convention
at `0.025, 0.5, 0.975`; nonfinite draws are omitted and their exact count reported. Fewer than 490 finite
draws makes that estimator ineligible rather than scientifically failed. The complete bootstrap maps are
deterministically namespaced by seed, direction, endpoint, draw, source role, and slot.

The exact primary pass vector in **both** transfer directions is:

1. **Reproducible context capture:** held-out `d_context` capture by `P_context_context` is at least `0.10`; the
   bootstrap interval for capture minus the analytic `16/768` reference has lower bound above zero.
2. **Context assignment:** held-out `d_context` capture by `P_context_joint` exceeds capture by
   `P_lexical_joint` by
   at least `0.05`, with lower bound above zero.
3. **Lexical assignment:** held-out `d_lexical` capture by `P_lexical_joint` exceeds capture by
   `P_context_joint` by at
   least `0.05`, with lower bound above zero.
4. **Unrelated-context specificity:** the unweighted mean of the exact common-denominator paired projected-
   energy statistic above is at least `0.05`, with paired-bootstrap lower bound above zero.
5. **Lexical complement preservation:** at least `0.90` of held-out lexical delta energy remains in
   `I-P_context_joint` under the exact denominator-floor rule above, with the bootstrap lower bound at least
   `0.90`.
6. **Lexical localization:** the normalized changed-token lexical-delta magnitude exceeds the strictly
   downstream collateral-token magnitude, with paired bootstrap lower bound above zero.

All thresholds above are frozen in this plan and a calibration/analytic-justification artifact before AnCora
inference. None may be selected from AnCora activations.

## Endpoint-specific decisions

Decision logic has this total precedence:

1. Either frozen source fails label/text prescore, including the post-collision 64-component floor or frozen
   bootstrap-map support → `PRESCORE_INELIGIBLE_STOP_NO_TRAINING`; no model forward.
2. After opening, either source has fewer than 64 rows in `context_population`, or the inclusive masked-QA
   failure-rate rule fails, because of nonfinite or masked-equivalence technical QA →
   `CONTEXT_TECHNICALLY_INELIGIBLE_STOP_NO_TRAINING`.
3. Context technical QA passes but either source fails the finite median/lower-bound raw `d_true` or
   `d_context` measurability rule → `CONTEXT_RAW_EFFECT_NOT_DEMONSTRATED_AT_THIS_LAYER`.
4. Context is raw-measurable but a `P_context_context` point fit is below frozen rank 16 or its gate-1
   bootstrap has fewer than 490/500 finite refits →
   `CONTEXT_ORGANIZATION_UNESTIMABLE_AT_FROZEN_RANK`. Raw context magnitudes remain reportable; this is not
   called nonreproducibility.
5. Gate 1 is finitely estimable but fails in either transfer direction →
   `CONTEXT_NOT_REPRODUCIBLE_ACROSS_SOURCES_AT_THIS_LAYER`.
6. Gate 1 passes, but either source has fewer than 64 lexical/joint rows because of its exhaustive nonfinite
   checks → `CONTEXT_REPRODUCIBLE_SPECIFICITY_TECHNICALLY_INELIGIBLE`. Eligible context estimates remain
   reported; missing specificity is neither a pass nor a measured failure.
7. Specificity populations are technically eligible but either source fails the finite median/lower-bound
   lexical raw-effect rule → `CONTEXT_REPRODUCIBLE_LEXICAL_CONTROL_EFFECT_NOT_DEMONSTRATED`. Context remains
   reportable; separability is untested rather than failed.
8. Lexical effects are measurable but either joint point projector is below frozen rank 16, any gate-2--5
   interval has fewer than 490/500 finite refits, or either gate-6 source interval has fewer than 490/500
   finite draws → `CONTEXT_REPRODUCIBLE_SPECIFICITY_ESTIMATOR_INELIGIBLE`. The result records each affected
   endpoint and exact cause (`joint_rank`, `context_specificity_draws`, `joint_draws`, or
   `lexical_localization_draws`) rather than attributing every cause to rank.
9. Gate 1 passes both directions and all specificity estimates are finite, but gate 4 or any of gates 2, 3,
   5, and 6 fails its prespecified threshold →
   `CONTEXT_DETECTABLE_BUT_NOT_CLEANLY_SEPARABLE_AT_THIS_LAYER`.
10. Context and lexical raw measurability pass and all six gates pass in both directions (gate 6 passes in
    each source) → `NOMINATE_LATER_EQUAL_CAPACITY_SUPERVISED_COMPARISON`. Attempt 14 itself still performs no
    training.

Only a finite eligible estimate can produce `CONTEXT_NOT_REPRODUCIBLE` or
`CONTEXT_DETECTABLE_BUT_NOT_CLEANLY_SEPARABLE`; technical missingness, low-rank estimators, and absent control
effects have their distinct statuses above. No outcome can authorize K2, SAE, relation-aware,
private/shared, or supervised training. A passing nomination requires post-result claim review and a
separate future protocol before any comparison.

No individual favorable contrast can promote the family decision. Missingness, raw signal, reproducibility,
context specificity, lexical specificity, complement preservation, and overall eligibility are reported
separately. Any negative claim is limited to the two Spanish AnCora upstream partitions (3LB and CESS),
Pythia-160m hidden-state layer 3, and this fixed linear protocol. Tokenizer fragmentation and UPOS support are
frozen descriptive reports only; they cannot alter eligibility or support a claim about other languages,
models, layers, or nonlinear representations.

## Approach

Create an isolated Attempt-14 namespace containing:

1. an Attempt-13 immutability attestation and prior-exposure inventory;
2. a label-only paired-component builder and signed prescore manifest;
3. a calibration artifact derived without fresh-source activations;
4. an inference-only cache extractor and frozen bidirectional projection analyzer;
5. signed freeze, exact `/adversarial` review binding, one-shot authorization, global opening record,
   result completion, and terminal;
6. a safely quoted tmux launcher pinned at launch to a currently free physical GPU and exact UUID;
7. a post-result `research-claim-review` before scientific interpretation.

After exact candidate SHIP but before science authorization, run one signed synthetic-token Pythia backend
validation through the exact frozen inference function. It changes all masked prefix IDs while preserving
geometry, checks layer-3 target agreement at `1e-5`, confirms an unmasked negative control changes the target,
and attests eager attention, explicit masks/positions, `use_cache=False`, paired batch shape, dtype, model
revision, and GPU UUID. Failure terminates without opening AnCora. This validation cannot change any threshold
or code; a code change requires a new freeze and adversarial review.

The code may reuse low-level tokenizer loading, hashing, signing, and deterministic
matching utilities only by exact source hash. Attempt-13 scientific outputs are archival evidence, not
calibration data or analysis inputs.

### Alternatives considered

- **More K2/SAE training:** rejected because stable mixed convergence and failed specificity, not seed scarcity,
  is the current evidence.
- **Private/private/shared or relation-aware training:** rejected because no functional nomination exists.
- **Broad signal screening:** rejected as outcome-driven multiple testing.
- **A target-only translated-position baseline:** rejected because it reintroduces approximate RoPE
  equivariance as a global validity dependency. Masked prefixes preserve identical geometry instead.
- **Token-balanced or reusable donor sampling:** rejected because it hides independent-document sparsity.
- **Persisting fitted projections:** rejected; immutable input/result artifacts are sufficient, and fitted
  projection weights would create an avoidable model artifact.

## Design-bank clarification

`design query "final context accumulation measurement study fresh corpora frozen projection no training"`
returned no MSAE-specific canonical choice. The user supplied the material scope decisions: one final
context/local measurement, frozen projection baseline, endpoint-specific decisions, and training only after
functional evidence. Low-risk implementation assumptions are the rank-16 SVD formulation, paired components,
and masked-prefix geometry specified above; `/adversarial` must approve them before implementation.

## Milestones

### M1 — Archival and label-only feasibility

- Record Attempt-13 immutable inventories and the no-training decision.
- Audit prior source exposure and construct joint context/lexical component candidates using labels/text only.
- Acceptance: no model forward; exact source hashes; authentic document IDs; both fixed sources either meet all
  prescore floors or produce a terminal prescore-ineligible decision with no science authorization.

### M2 — Calibration and frozen protocol

- Derive numerical and analytic projection thresholds without fresh-source activations.
- Freeze config, raw sources, prepared rows, calibration, dependencies, seed, rank, metrics, bootstrap,
  decisions, GPU-selection rule, and namespaces.
- Acceptance: calibration lineage proves no fresh-source activation access; independent label-only rebuild is
  byte-identical.

### M3 — Inference-only implementation

- Implement cache extraction, numerical QA, bidirectional refit-bootstrap projection analysis, signed lifecycle,
  and tmux launch.
- Acceptance: deterministic synthetic smoke tests cover intervention geometry/masking, source/document
  disjointness, substitution matching, support loss/no backfill, projection algebra, both-source refitting,
  endpoint decisions, signatures, wrong config/key/review rejection, one-shot consumption, Attempt-13
  immutability, and no-training reachability.

### M4 — Exact adversarial review and authorization

- Freeze the exact candidate inventory and detached signature.
- Obtain `/adversarial` `SHIP` bound to the exact freeze payload and inventory; fix and refreeze every BLOCK or
  REVISE issue before authorization.
- Run the immutable synthetic-token Pythia mask validation only after SHIP and before science authorization.
- Acceptance: review parser, canonical config, signer, source/prepared hashes, synthetic backend QA, namespace
  absence, and free-GPU UUID preflight all pass; no AnCora inference has occurred.

### M5 — One-shot tmux run and claim review

- Launch the frozen pipeline once in tmux on a currently free exact-UUID GPU.
- Verify signed caches, inventories, result, terminal, and Attempt-13 immutability.
- Run post-result research-claim review without new inference.
- Acceptance: terminal is complete or signed no-retry failure; endpoint decisions are rendered without
  promotion through missingness; no training/checkpoint/projection weights exist.

## Definition of done

- [ ] Attempt 13 and its formal wording remain byte-identical and are hash-attested before and after Attempt 14.
- [ ] No K2, SAE, relation-aware, private/shared, or supervised model training is run or authorized.
- [ ] Both fixed sources have authentic upstream document groups and at least 64 disjoint joint components, or
      the study stops prescore-ineligible without model inference.
- [ ] Every context component fixes target tokens, absolute positions, sequence length, and natural-boundary geometry;
      only prefix identity and prefix attention availability vary as prespecified.
- [ ] Every lexical substitution is label/tokenizer matched, changes exactly one target token, and includes a
      collateral-token control.
- [ ] Numerical tolerances, noninformative rules, rank, random baseline, capture minima, specificity margins,
      bootstrap, and decisions are frozen without fresh-source activations.
- [ ] Both transfer directions use rank-matched ephemeral projections and refit fit-source projectors inside all
      primary bootstrap draws.
- [ ] Prescore, numerical validity, raw signal, reproducibility, control specificity, lexical preservation, and
      overall decision are reported independently.
- [ ] The exact frozen candidate receives `/adversarial` SHIP before authorization and any fresh-source forward.
- [ ] Execution occurs once through tmux on a free GPU whose UUID matches the signed preflight.
- [ ] Signed terminal/cache/result inventories verify, no retry is authorized, and post-result claim review is
      persisted before interpretation.

## Risks and one-way doors

- **Fresh endpoint opening:** the first AnCora context/local forward irreversibly opens the fixed
  source/model/protocol combination. A global authorization-independent `O_CREAT|O_EXCL` record is written and
  fsynced before that forward. No retry is allowed after consumption.
- **Support failure:** joint context-plus-lexical matching may yield fewer than 64 components. This is a valid
  terminal prescore result, not permission to relax matching or add sources.
- **Masked-attention leakage:** an incorrect attention mask would invalidate boundary control. Synthetic forward
  tests may use only non-scientific tokens before freeze; fresh-source masked equivalence is endpoint-specific QA.
- **Projection overfit:** 64 components is still small relative to width. Cross-source evaluation and refitting both
  projectors inside the two-source bootstrap are mandatory; conclusions remain exploratory.
- **Shared treebank pipeline:** both fresh source partitions are separately named upstream corpora but share the
  AnCora UD release and annotation pipeline. This limitation must appear in every result and claim.
- **Negative-evidence asymmetry:** failure supports only “not demonstrated at Pythia-160m layer 3 under this
  representation and protocol,” never absence from all models, layers, or nonlinear representations.

## Verification plan

- Plan gate: `.agent-workspace/bin/check-plan --path PLAN_ATTEMPT14.md`.
- Static: Python compilation, shell syntax, AST no-training audit, canonical config/inventory hashing.
- Tests: targeted Attempt-14 pytest suite including deterministic CPU synthetic projection/refit bootstrap smoke.
- Data: source hash audit, authentic-document parser audit, exact joint-component rebuild, exposure audit, row/unit
  foreign keys, and all prescore floors.
- Lifecycle: signature verification, wrong-key/type/config/review tests, namespace absence, global one-shot race
  test, signed pre/post-opening failures, cache/result/terminal inventory reconstruction.
- Runtime: `nvidia-smi` physical index/UUID/free-memory check immediately before launch and exact visible-device
  attestation inside the runner.
- Result: independent signed-artifact audit and `research-claim-review`; no new inference during claim review.
