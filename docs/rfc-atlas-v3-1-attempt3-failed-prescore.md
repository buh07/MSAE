# RFC: Atlas v3.1 discovery study of positional, contextual, lexical, and relational factors

**Status:** revised prescore plan; no v3.1 representation scoring has started  
**Date:** 2026-08-02  
**Scope:** reused-public discovery evidence only; raw-model inference and no-training projection/scrubbing comparators  
**Predecessor:** Atlas/MSAE measurement v2.4 (immutable completed result)

## Prescore revision history

V3.0 ran label-only preparation and no neural inference, representation scoring, or
training. It was retired `FAILED_PRESCORE` because donor documents could later act
as targets, joining pairs into fold-wide chains, and an implementation error then
applied that union across unrelated endpoints. This left only 5--46 local donor
components and 5--8 erroneously global components per source. The immutable v3.0
config, protocol, preflight, manifest, input ledger, and failure marker live under
the `*_v30_failed_prescore` namespaces. V3.1 changes row/component namespaces and
rebuilds from the two raw allowlisted CoNLL-U files; it hard-rejects every v3.0
prepared cache. This support-only revision was made before any activation existed.
The first v3.1 label-only build passed scientific support but was also retired
before inference because its deterministic manifest included the volatile process
snapshot digest. The final build still writes that required snapshot, but excludes
PID/process-table bytes from the scientific manifest so independent rebuilds of
the preflight and prepared manifest can be byte-identical.
That byte-identical build was retired before inference after final adversarial
review found that it attested individual endpoints but had not yet materialized
the required joint four-class specificity population. The final prescore now
freezes that matched population and its shared-node bootstrap completeness.

## Goal

Determine what the v2.4 nominal position branch may have been responding to by separating five constructs that the earlier broad position family conflated:

1. strict absolute sequence index;
2. distance from sequence/sentence/document boundaries;
3. relative sequential position;
4. syntactic/child--head position;
5. accumulated visible context.

At the same time, screen lexical identity, morphology, and matched proper-noun substitution so the study can compare the original **broad-position versus lexical-content** hypothesis with the sharper **token-local versus context-dependent/relational** hypothesis. The common UD inputs do not support a trustworthy entity-type/semantic substitution claim.

The output is a discovery atlas and a recommendation for one later confirmatory decomposition target. It is not evidence that a new architecture works.

## Non-goals

- Do not train or fine-tune an MSAE, SAE, probe backbone, language model, or other neural representation model.
- Do not score, read, relabel, or derive design choices from Atlas v2 C1/C2, the old LinES/WikiNeural partitions, ESLSpok, PUD, or any private/blind-final payload.
- Do not call raw decodability causal localization. In particular, do not reinterpret absolute-position decodability as evidence for an independently causal absolute-index factor.
- Do not promote a decomposition, choose hyperparameters for confirmation, or claim generalization from a post-result task inventory. The atlas may nominate a target; a fresh protocol and fresh data must confirm it.
- Do not implement the Phase-2 learned architecture in this task.
- Do not treat a token-pair contrast or a projection baseline as equivalent to a learned branch.

## Grounding and preserved evidence

- Atlas v2.4 completed with outcome `K2_broad_position_content_selective_not_supported`. Its narrow post-result claim review is supported, but it does not license a claim about all K2 models or strict absolute position.
- Strict absolute position was **ineligible** in v2.4 because GPT-NeoX uses RoPE and a uniform position-ID translation preserves pairwise rotary offsets. V3 therefore includes a uniform position-ID shift as an architectural/null diagnostic, not as an ordinary positive task.
- V2.4 found high relative-quartile recovery in the nominal position branch, but equal or greater content-branch recovery; signed head distance localized more strongly to content; document-context interventions preferentially affected the position branch; and geometry was stable but highly cross-branch-similar.
- The reusable public sources are the complete source-pure `UD_English-EWT` train CoNLL-U (`12,544` sentences in `540` declared documents) and `UD_English-GUM` train CoNLL-U (`11,314` sentences in `197` documents). Both have already influenced project design. In v3 both are explicitly **exploratory discovery sources**, never calibration or confirmation.
- Source-pure CoNLL-U files already exist under `data/atlas_v1/raw`. V3 reparses those files and writes fresh caches. It neither opens the mixed-source v1 partition JSONL files nor reuses subset-shaped v2.4 caches.
- Deterministic code queries located the reusable builders in `scripts/msae_measurement_v2_run.py` and the scored evaluator in `scripts/run_msae_measurement_v2.py`. The design ledger returned no canonical entry for a post-v2 discovery factor atlas, so the choices below are explicit study assumptions.

## Scientific questions

### Q1 — Strict absolute index

Does changing every visible token's position ID by the same constant change its layer-3 activation when token IDs, attention, and all pairwise position differences are fixed?

This is expected to be a numerical null under RoPE. A non-null result is first treated as implementation/numerical QA failure, not a scientific discovery.

### Q2 — Sequential and boundary position

Are start-distance buckets, relative quartile, local order, and token-pair distance cross-corpus decodable after controlling lexical, surface, POS, punctuation, and length nuisances? Do they share a reproducible low-rank subspace?

Sequence-start distance and sentence-start distance coincide in bare-sentence inputs and must not be counted as two independent constructs. Document-start distance is evaluated only in the prefix factorial below.

EWT has explicit paragraph markers but GUM does not expose a common compatible paragraph boundary in the pinned file. EWT paragraph distance is therefore an optional one-source diagnostic and cannot enter cross-corpus nomination.

### Q3 — Context accumulation

For the same target sentence and target tokens, how do activations change under:

- a genuine preceding sentence from the same document;
- a length-matched preceding sentence from a different document/source-matched donor;
- a matched-position target with no prefix and a separator-only matched-position control?

The factorial separates a pure position-ID translation from extra visible context, and separates generic extra context from document-related context. It does not claim that any natural prefix is semantically neutral.

### Q4 — Relative RoPE geometry

Does a virtual position-ID gap inserted after a frozen pivot, while token IDs and attention connectivity remain unchanged, produce a reliable response beyond the uniform-shift null?

This is an off-manifold but precisely controlled diagnostic of relative position IDs. It is reported separately from natural prefix/context effects.

### Q5 — Syntactic/relational position

Do true child--head representations improve cross-corpus prediction of dependency relation, direction/distance, and depth over child-only representations and matched non-head controls? If so, syntax is treated as relation-aware rather than silently pooled with token-local sequential position.

### Q6 — Token-local/lexical factors

Are token identity, lemma identity, capitalization, word length, UPOS, and morphological Number cross-corpus decodable? Do matched proper-noun substitutions define a lexical delta subspace distinct from context-prefix and relative-gap deltas?

## Inputs and firewall

The v3 config contains an exact SHA-256 allowlist for only:

- the pinned, source-pure EWT CoNLL-U file under `data/atlas_v1/raw`, SHA-256 `d68e06122a702464c613076523d56740f047e5bbe89dd90ec32737e04d952143`;
- the pinned, source-pure GUM CoNLL-U file under `data/atlas_v1/raw`, SHA-256 `88c410ca6a51ccc79f9536d75feb1633421691165cd191f8137f8b37569a0329`;
- the pinned Pythia-160M-deduped revision and tokenizer;
- the v3 protocol, config, and implementation inventory needed to bind the run.

The loader rejects every data path other than those two exact canonical CoNLL-U paths; it never opens a mixed-source parent merely to filter it. It also rejects any role/source/path containing `C1`, `C2`, `confirmation`, `final`, `blind`, `private`, `ESLSpok`, `LinES`, `WikiNeural`, `FewNERD`, `WNUT`, or `PUD`, resolves real paths before opening, rejects symlinks and digest mismatches, and restricts all writes to new `data/atlas_discovery_v3_1` and `pilot_runs/20260803_atlas_discovery_v3_1` roots. A pre-open process snapshot and an opened-input ledger are terminal artifacts.

EWT and GUM are not independent confirmation samples because they were used earlier. All intervals are descriptive uncertainty conditional on this frozen exploratory sample, model, layer, task set, and probe procedure.

## Data and construct contract

### Group and row support

Each source/task must have, after deterministic capping:

- at least `100` genuine document groups overall;
- at least `25` groups containing every retained class;
- at most `128` token rows per document group per task;
- at least `490/500` finite ordinary source-stratified document-bootstrap draws;
- at least two labels.

The master seed is `20260803`. A document's five-fold assignment is the first eight SHA-256 bytes of `atlas_discovery_v3_1|fold|20260803|{source}|{document_id}`, interpreted big-endian and reduced modulo five. CoNLL-U `newdoc id` is the document ID; a sentence before the first `newdoc id`, duplicate sentence ID, or duplicate document ID block is an error. For each `(source, task, document)`, candidate rows are ordered **without labels** by SHA-256 of `atlas_discovery_v3_1|row-cap|20260803|{row_id}` and the first `128` are selected. Labels are opened only after this sample is frozen; support is then recomputed and cannot trigger reselection.

The 500 ordinary held-out bootstrap maps resample endpoint-local connected component IDs with replacement, drawing exactly the observed number of components. For component slot `j`, draw `b`, direction `d`, and endpoint `e`, the selected index is the first eight SHA-256 bytes of `atlas_discovery_v3_1|bootstrap|20260803|{d}|{e}|{b}|{j}` modulo the sorted component count. All rows and linked donors in a sampled component receive its multiplicity. A draw is finite only when every frozen target class is present and every metric denominator is finite; no redraw-until-acceptance is allowed.

Donor-linked endpoints use deterministic maximum-cardinality document matching.
Candidate directed interventions are collapsed to one canonical candidate per
unordered document pair by the smallest SHA-256 candidate ID. Edges and nodes are
inserted in UTF-8 order into pinned NetworkX `2.8.8`; `max_weight_matching` runs
with `maxcardinality=True` and a unique candidate-rank preference. The selected
edges are then ordered by candidate ID. A single endpoint-local used-document set
covers both roles: every component contains exactly two distinct documents and no
document occurs in two components of that endpoint. Unmatched candidates never
trigger a fallback or new matching rule. The manifest reports the eligible
document upper bound, candidate edge count, exact maximum and achieved
cardinality, exclusions, and component counts by fold. Each donor-linked endpoint
must have at least 50 total components and at least 5 components in every one of
the five folds; failure retires the endpoint without threshold relaxation.

Primary token identity uses the source-independent, hand-specified closed-class vocabulary `['a','and','but','for','in','is','it','of','on','or','that','the','to','was','with']`. It was defined as a small English function-word ontology, not ranked or filtered using v1/v2 task rows, C1/C2, ESLSpok, EWT, or GUM frequencies. V3 does not add, remove, or rerank a token after source support is read. Rows outside the list are excluded and coverage is reported; any listed class below `25` groups in either source makes the token-identity construct prescore-ineligible. Lemma identity is a nested diagnostic only: each direction derives a fit-source-only vocabulary with document frequency at least `25`, ranks by `(fit-source DF descending, UTF-8 label ascending)`, caps at `128`, and never reselects after held-out support is known. Rare morphology categories use prespecified maps—Number retains only `Sing` and `Plur`; all other Number values are excluded and counted—or are marked screen-ineligible before activation scoring. Token counts cannot rescue group sparsity.

Rows are deterministic first-subword rows parsed directly from CoNLL-U. Full words truncated by the tokenizer, multiword-token artifacts, empty nodes, malformed dependency heads, alignment drift, duplicated IDs, and cross-source duplicate content are excluded and counted. Every source, target, prefix, and lexical donor document belongs to one preassigned document fold. Donors are selected only from the target's fold. Within each donor-linked endpoint a document is used at most once total, whether as target/source or donor, and its two-document matched pair is that endpoint's outer component. Donor-free relative-gap, observational, pair, and relational endpoints retain singleton document components; components are never unioned merely because a document participates in another endpoint.

The v3 config contains literal common label maps. UPOS uses `NOMINAL={NOUN,PROPN,PRON}`, `VERBAL={VERB,AUX}`, `MODIFIER={ADJ,ADV}`, `FUNCTION={ADP,CCONJ,SCONJ,DET,PART}`, `QUANTITY={NUM}`, `PUNCT={PUNCT}`, and `OTHER={INTJ,SYM,X}`. Dependency subtypes are stripped, then mapped to `CORE={nsubj,csubj,obj,iobj}`, `CLAUSAL_COMPLEMENT={ccomp,xcomp}`, `OBLIQUE={obl,vocative,expl,dislocated}`, `NOMINAL={nmod,appos,nummod,acl,amod,det,clf,case}`, `ADVERBIAL={advcl,advmod,discourse}`, `COORD={conj,cc}`, `FUNCTION={aux,cop,mark}`, `MWE={fixed,flat,compound,list}`, `REPAIR_OTHER={parataxis,orphan,goeswith,reparandum,dep}`, plus distinct `root` and `punct`. Unknown labels are errors, not dropped.

Capitalization levels are `lower,title,upper,mixed,nonalpha`; word-length buckets are `1,2,3-4,5-7,8+`; sentence-token-length buckets are `1-4,5-8,9-16,17-32,33-64,65+`. Proper-noun frequency quartiles are source-local but label-blind: rank lowercased proper-noun forms by `(document_frequency ascending, UTF-8 label ascending)` and assign quartile `min(3, floor(4*rank/number_of_forms))`; matching uses only the resulting frozen quartile.

### Frozen observational tasks

| Construct | Task/representation | Role |
|---|---|---|
| sequential start distance | tokenized start-distance buckets `0,1,2-3,4-7,8-15,16-31,32+` on child/token state | selection candidate |
| relative sequential | word-relative quartile; ordered token-pair distance buckets `1,2,3-4,5-8,9+` with selection representation `[left, right-left]` | selection candidate; `right-left` alone is diagnostic |
| syntax/relations | signed head distance, dependency depth, coarse dependency relation on child-only, selection representation `[child, head-child]`, and matched non-head `[child, sham-child]` | selection candidate, relation-aware; `[child,head]` and differences alone are diagnostics |
| lexical identity | fixed 15-token source-independent function-word vocabulary; direction-specific fit-source lemma identity diagnostic | token identity is the selection representative; lemma is nested/zero-weight |
| morphology/surface | Number, UPOS, capitalization, word length, punctuation | screen/control unless a controlled intervention is available |

`relative_quartile` and start-distance are related operationalizations, not independent replication. Likewise token and lemma identity are nested. Reports preserve task-level results and aggregate by construct with one frozen representative weight.

### Frozen intervention populations

Every source builds at least `50` eligible connected document components per intervention where the corpus supports it; otherwise that intervention/source is ineligible.

1. **Uniform position-ID shift:** same input IDs and mask, all position IDs `+16`; exact same target tokens. This is the strict-absolute null.
2. **Virtual relative gap:** same input IDs and mask; choose a deterministic interior pivot and add `+16` only to position IDs after the pivot. Score aligned post-pivot targets and pre-pivot negative-control targets separately.
3. **Prefix position-only control:** for a target whose true prefix has tokenized length `L`, run the bare target with explicit position IDs `L+1 ... L+n`; input IDs and attention visibility remain identical to bare. This matches the target positions of prefixed conditions.
4. **Separator-only control:** run `[separator, target]`, expose the separator, and assign target position IDs `L+1 ... L+n`; the unused position-ID gap is explicit. This separates separator visibility from prefix visibility at matched target positions.
5. **True document prefix:** for a target sentence parsed from CoNLL-U, use the immediately preceding same-document CoNLL-U sentence and run `[true prefix, separator, target]`. Document-initial targets are excluded.
6. **Unrelated matched prefix:** run the same target with a same-source donor prefix whose tokenized length exactly equals `L`, whose document/content hashes differ, and whose preassigned fold matches the target. The target position IDs equal all other matched-position prefix conditions.
7. **Matched proper-noun substitution:** replace one single-token proper noun with a single-token donor proper noun from a different same-fold document while preserving complete token layout and matching capitalization category, Number when annotated, and that corpus's source-local document-frequency quartile. Each corpus freezes its own quartiles once and uses them unchanged whether it is the fit or held-out source. Score the changed token and deterministically selected unchanged-token controls separately. UD supplies no common trustworthy entity subtype, so this is a lexical proper-noun intervention—not an entity-type or semantic intervention.
8. **True-head versus matched non-head:** eligible children have a non-root, fully aligned head. Candidate shams exclude the child and true head and must exactly match the true head on side (`left/right`), broad distance (`near=1-2`, `far=3+`), and coarse UPOS. Process children by SHA-256 of `atlas_discovery_v3_1|sham-child|20260803|{row_id}`; among unused exact-stratum candidates choose minimum absolute distance difference, then SHA-256 of the candidate row ID. A token can be a sham at most once per sentence. No fallback stratum is allowed; unmatched children are excluded and counted. This is a representation-level relational contrast, not a model-input causal intervention, and is labeled accordingly.

All seven model-input intervention conditions store explicit token IDs, attention masks, position IDs, target row IDs, source/donor groups, alignment metadata, component IDs, and reasons for exclusion. The builder first assigns documents to five deterministic fit-source tuning folds, then selects only same-fold donors and forms connected components; no linked document component crosses folds. Cross-corpus transfer always fits in one source and evaluates in the other.

## Analysis contract

### 1. Cross-corpus raw and incremental signal

For each eligible label task, run both transfer directions: EWT fit → GUM evaluate and GUM fit → EWT evaluate. No target-corpus labels select probe alpha, vocabulary, scale, rank, nuisance levels, or basis. Target labels are used only to compute the held-out metric and prespecified support/coverage status after all fit-source choices are frozen.

- Primary probe: standardized deterministic ridge one-vs-rest classifier; alpha is selected by document-group folds entirely inside the fit corpus from `{0.1, 1, 10, 100}`.
- Metrics: macro-F1, balanced accuracy, deterministic independent-prior chance, and normalized recovery `(F1 - chance)/(1 - chance)` when finite. If `p_c` is the fit-source class prior and `q_c` the held-out class prevalence, chance macro-F1 is `mean_c 2 p_c q_c / (p_c + q_c)` with `0/0→0`; no random permutation fit is used.
- Nuisance-only probe: the exact frozen task table below. All categorical levels are learned from the fit source, the first UTF-8 level is the dropped reference, and held-out unseen values map to one explicit `__UNKNOWN__` level that is already present in the fit design. Numeric sentence/token length is encoded only through the frozen buckets. No interactions are added.
- Incremental probe: representation plus the identical nuisance matrix. Incremental signal is paired held-out macro-F1 difference `combined - nuisance_only`, not residualized-label accuracy.
- Inference: 500 ordinary held-out-document bootstrap maps. Intervals are descriptive and pointwise.

A selection-candidate task has robust raw signal only if both transfer directions have normalized-recovery point estimate `>=0.20`, interval lower bound `>0`, and at least `490/500` finite draws. It has incremental signal only if both directions have incremental-F1 point estimate `>=0.02` and interval lower bound `>0`. Nested tasks cannot independently satisfy a construct.

#### Frozen nuisance table

| Target | Nuisance columns (all fit-source encoded) | Explicitly excluded |
|---|---|---|
| start-distance / relative-quartile | token and lemma vocabulary class (with `__NONRETAINED__`), coarse UPOS, punctuation, capitalization, word-length bucket, sentence-length bucket | the other sequential target and any direct position ID |
| ordered pair distance | separately ordered left/right token class, lemma class, coarse UPOS, punctuation, capitalization, and word length; sentence-length bucket; left start-distance bucket | right start distance, either raw position ID, relative quartile, and any endpoint interaction |
| signed head distance / dependency depth / dependency relation | token and lemma class, coarse UPOS, punctuation, capitalization, word length, sentence length, start-distance bucket, relative quartile | true head index/vector and the target dependency label |
| token identity | coarse UPOS, punctuation, capitalization, word length, sentence length, start-distance, relative quartile | lemma identity and token string/hash features |
| lemma identity | coarse UPOS, punctuation, capitalization, word length, sentence length, start-distance, relative quartile | token identity and lemma string/hash features |
| Number | lemma class, coarse UPOS, punctuation, capitalization, word length, start-distance, relative quartile | surface token identity and raw FEATS string |
| UPOS | token and lemma class, punctuation, capitalization, word length, sentence length, start-distance, relative quartile | dependency relation and morphology fields |
| capitalization / word length / punctuation | tokenized start-distance, relative quartile, sentence length, coarse UPOS | token/lemma identity and the other surface attributes |

The table is serialized verbatim in the config. A target with a deterministic or near-deterministic nuisance baseline may still be reported, but it cannot pass incremental signal unless the representation adds the prespecified `0.02` held-out macro-F1.

### 2. Relational advantage

Using the same transfer directions and label vocabularies, compare child-only `child`, primary true-head `[child, head-child]`, and primary matched-non-head `[child, sham-child]` representations. The raw concatenation `[child,head]`, difference `head-child`, and their sham analogues are descriptive only and cannot pass or rescue the construct. A syntax construct has relation-aware advantage only if the **primary** representations satisfy:

- true-head minus child-only macro-F1 is positive in both directions;
- true-head minus matched-non-head macro-F1 has a positive lower bootstrap bound in both directions;
- the result is not rescued by a support-ineligible relation label.

This licenses only the statement that the frozen relation-aware representation is more informative for the selected task, not that syntax is causally disentangled.

### 3. Intervention fingerprints

All aligned source/target activations come from one float32 cache and canonical pooling/reduction path. For each source and intervention, report cosine distance, relative L2 change, delta norm, numerical no-op error, target/control contrast, and the delta covariance spectrum.

- Uniform `+16` and per-pair prefix-position-only shifts must pass elementwise `|shifted-reference| <= atol + 5e-6*|reference|`. Before any non-null metric is opened, three repeated inferences over a fixed 32-unit label-blind QA set per source determine `e = max_abs_repeat_error`. If `2e >= 2e-5`, QA is technically invalid; otherwise `atol = max(5e-7, 2e)`. The formula is frozen now; the derived `atol`, QA row hash, arrays, and pass/fail artifact are signed before the remaining analysis runs. Failing either shift null marks the study technically invalid rather than relaxing the bound.
- Relative-gap response is evaluated as post-pivot minus pre-pivot-control response.
- Prefix effects use the exact factorial: `position_only - bare` (pure translation QA), `separator_only - position_only` (separator visibility), `unrelated_prefix - separator_only` (generic visible-context accumulation), and `true_prefix - unrelated_prefix` (document-related context at identical target positions and prefix length).
- Proper-noun response is changed-token minus matched unchanged-token-control response and is never called semantic/entity-type specificity.

Cross-family specificity is measured by source-held-out linear classification of normalized single-target-token delta directions among `relative_gap`, `true_context`, `unrelated_context`, and `proper_noun_substitution`. Rows are deterministically matched/capped within `(target start-distance bucket, coarse UPOS, capitalization, word-length bucket)` strata; pooled multi-token means are not mixed with token deltas. A nuisance-only construct classifier receives exactly those strata, source-document length, and intervention target count (fixed to one). The representation-delta classifier must improve held-out macro-F1 over that nuisance classifier by at least `0.02` with lower bound `>0` in both directions.

The label-only joint population is frozen before inference. Within each exact
four-column stratum, let `m` be the smallest candidate count among the four
classes. For each class, order rows by SHA-256 of
`atlas_discovery_v3_1|joint-cap|20260803|{source}|{class}|{joint_row_id}`
and retain the first `m`; strata missing any class retain zero rows. No later
representation value, label prevalence, or fit/held-out direction changes this
population. Each class must retain at least 50 rows and 25 distinct target
documents overall, at least 5 rows in every fold, and all four classes must appear
in at least 490/500 shared-node bootstrap draws. The manifest reports candidates,
retained rows, target and donor documents, folds, strata, and exclusions per class.

Because a document may legitimately occur in different endpoint atlases, pooled
cross-family intervals use a frozen node/bootstrap rather than pretending endpoint
components are independent. Each held-out source's genuine document IDs are
resampled `n_documents` times. A singleton row gets its document multiplicity; a
donor-linked row gets the product of its two distinct document multiplicities.
The same document map weights all four construct classes in a draw. Zero-weight
rows are omitted, and missing-class or non-finite draws remain invalid without
redraw. At least 490/500 pooled draws must be finite. A fixture in which one
document appears in two endpoints must reproduce the shared multiplier in both.

Cross-construct CKA is prohibited because the observation axes are unaligned. Each `(source, construct)` instead gets a rank-16 feature-space delta basis from centered, row-L2-normalized deltas. Basis similarity is the mean squared canonical correlation (equivalently normalized projection overlap) between two bases. Within-construct similarity means EWT-basis versus GUM-basis overlap for the same construct; cross-construct similarity means an EWT construct basis versus each GUM basis for a different construct, averaged with the reverse direction. An intervention construct is specific only if its one-vs-rest normalized recovery is `>=0.20` with lower bound `>0` in both directions, the nuisance improvement gate passes, and its within-construct basis overlap exceeds its largest cross-construct overlap. Magnitude alone never establishes specificity.

### 4. Simple projection/scrubbing atlas

Fit rank-`16` task/delta bases on the fit corpus only and apply them unchanged to the other corpus. Ranks `8` and `32` are frozen sensitivity checks: nomination requires the point selectivity for every required construct to have the same positive sign at all three ranks; all threshold and interval gates otherwise use rank 16.

Every organization uses one exact orthogonal projection-plus-complement comparator in **raw activation coordinates**, deliberately privileging the named projected side:

1. Each fit-source probe standardizes raw activations as `z_j=(x_j-m_j)/s_j`, with `s_j>=1e-8`, and learns standardized-coordinate class weights `Wz`. Before basis construction, transform them to raw-coordinate weights `Wraw[k,j]=Wz[k,j]/s_j`, class-center over `k`, discard the intercept, and divide the block by its Frobenius norm. An intervention/relational construct contributes the right singular vectors in the same raw feature coordinates of its centered, row-L2-normalized raw delta matrix. The frozen deltas are: post-pivot `relative_gap - bare`; generic context `unrelated_prefix - separator_only`; document-related context `true_prefix - unrelated_prefix`; lexical `proper_noun_target - source`; and relational syntax `head - child`. Generic and document-related context bases are equal-weighted inside one context construct. Rank-zero/non-finite blocks are ineligible.
2. Orthonormalize each construct block and scale it by `1/sqrt(block_rank)`, so constructs—not row counts or class counts—receive equal input weight.
3. Concatenate construct blocks in the frozen config order, take SVD, retain the first `min(16, numerical_rank)` orthonormal right-feature directions as columns of `B` with singular floor `1e-8`, and form `P = B Bᵀ`. SVD signs/rotations do not affect `P`. Rank below `8` is candidate-ineligible.
4. The projected representation is `x_P = xP`; the additive orthogonal complement is `x_Q = x(I-P)`, both in raw coordinates. Each task probe separately fits its scaler and ridge model using only the fit source for raw, `x_P`, and `x_Q`, then applies those frozen transforms unchanged to the held-out source.
5. For a task with finite raw denominator, branch recovery is `(F1_branch - chance)/(F1_raw - chance)`. For a construct assigned to `P`, leakage is `recovery_Q`; for one assigned to `Q`, leakage is `recovery_P`. Selectivity is assigned recovery minus leakage. Intervention assigned capture is `||delta P||²/||delta||²` for `P` constructs and `||delta Q||²/||delta||²` for `Q` constructs; opposite capture is the other fraction.

Compare these prespecified no-training candidate organizations and exact construct assignments:

| Organization | Projected `P` constructs | Complement-assigned `Q` constructs | External required construct |
|---|---|---|---|
| `broad_position_vs_lexical` | sequential start/relative, child-only syntax labels, relative-gap and context deltas | token identity, proper-noun substitution | none; it is scientifically failed whenever the frozen relation-aware syntax advantage passes, because that result contradicts token-local broad-position assignment |
| `sequential_context_vs_lexical_plus_relational_syntax` | sequential start/relative, relative-gap and context deltas | token identity, proper-noun substitution | syntax must pass relation-aware advantage and is not assigned to either token-local component |
| `token_local_vs_context_dependent` | sequential start/relative, context deltas, true child--head delta basis | token identity, proper-noun substitution | relation-aware syntax tasks are evaluated on paired representations, not relabeled token-local |

Lemma identity is a nested diagnostic for token identity and receives zero additional construct weight. Number, UPOS, capitalization, word length, and punctuation are collateral screens and receive zero nomination weight. For sequential recovery, start-distance and relative-quartile are averaged inside one construct; for syntax, all eligible frozen syntax tasks are equal-averaged inside one construct; token identity is the lexical representative. Each construct then receives equal macro weight, and the two transfer directions receive equal weight only after each direction separately passes all gates. For primary relation-aware evaluation under `token_local_vs_context_dependent`, apply `P` (or `Q`) separately to child and head raw states and form `[child P, (head-child) P]` (or the analogous `Q` representation). The resulting block-diagonal action is the only relational representation that enters nomination; descriptive concatenation/difference variants cannot alter the decision.

For every organization report assigned-task recovery, opposite-side leakage, selectivity, intervention-delta capture, cross-family control capture, basis rank/conditioning, and full cross-source matrices. The no-training comparator is a screening device; it is not capacity-matched to K2 and cannot establish learned-model superiority or equivalence.

An organization is **nominated** only if, separately in both transfer directions:

- every required construct passed support, raw-signal, and applicable incremental/intervention gates;
- macro assigned recovery is at least `0.65`;
- macro selectivity is positive with a positive descriptive lower bound;
- assigned intervention-delta capture exceeds every cross-family control with a positive lower bound;
- no required relation-aware construct is forced into a token-local component.

Candidate status aggregation is fail-closed: any required ineligible endpoint makes that candidate `ineligible`; otherwise any failed scientific gate makes it `eligible_not_passed`; only all-passing endpoints make it `passed`. Missing competitor measurement is never converted into evidence against decomposition. The global outcome is total and deterministic:

1. Any data-firewall, cache-lineage, numerical-null, global extraction failure, or `ineligible` candidate → `technically_ineligible`.
2. Otherwise no passed candidates → `no_decomposition_nominated`.
3. Exactly one passed candidate → its corresponding `nominate_*` outcome.
4. Two or three passed candidates → `multiple_discovery_candidates`, regardless of their point-score ordering.

## Selection and interpretation

The terminal atlas may return exactly one of:

- `nominate_broad_position_vs_lexical`;
- `nominate_sequential_context_vs_lexical_plus_relational_syntax`;
- `nominate_token_local_vs_context_dependent`;
- `multiple_discovery_candidates`;
- `no_decomposition_nominated`;
- `technically_ineligible`.

The outcome chooses only the question to preregister next. It cannot authorize learned training by itself. Before Phase 2, freeze a new confirmation protocol on genuinely fresh document groups/corpora, equalize private-branch capacities, specify direct responsiveness/invariance losses, and compare against the rank-16 projection, K1, equal-capacity K2, global TopK, no-incoherence, and—only if the atlas supports it—a tightly constrained shared branch.

## Milestones

### M1 — Protocol, config, and firewall

- [ ] Add the machine-readable v3 config with exact input/model hashes, task definitions, thresholds, folds, intervention rules, and fresh output namespaces.
- [ ] Add a pre-open firewall and opened-input ledger that reject every non-EWT/GUM role/source/path and every digest mismatch.
- [ ] Add a label-only preflight that writes class/document support and intervention population counts before any model call.

Acceptance: two repeated preflights are byte-identical; only EWT/GUM allowlisted inputs are opened; all exclusions and eligibility reasons are explicit; a fixture referencing C1/C2/final fails before open.

### M2 — Deterministic data and intervention builder

- [ ] Parse and hash the pinned source-pure CoNLL-U files and recover words, lemmas, morphology, head indices, and document/sentence order with one-to-one word/ID assertions internal to that parse; do not open mixed v1 partition files.
- [ ] Build main token rows, token-pair rows, child/head/non-head rows, the seven model-input intervention conditions, and the relational contrast.
- [ ] Freeze row IDs, group ownership, source/donor disjointness, token/attention/position alignment, and manifests.

Acceptance: rebuild hashes match; all target rows align; virtual-gap inputs differ only in post-pivot position IDs; uniform and pair-specific shift-only inputs differ from bare only by one constant; separator-only/true/unrelated prefixes have equal target positions; proper-noun substitutions change exactly one matched token; linked donor/target components never cross folds and donor reuse is at most one; true heads match CoNLL-U and sham heads are never true heads.

### M3 — Raw extraction and cache lineage

- [ ] Implement a CPU smoke path and deterministic GPU extraction for Pythia-160M-deduped layer 3.
- [ ] Write fresh v3 main and intervention caches over the complete allowlisted EWT/GUM populations; do not branch on v2.4 subset-cache reuse.
- [ ] Calibrate numerical tolerance from repeated discovery-only uniform/no-op inference before opening other intervention metrics.

Acceptance: float32 caches have exact ordered row sidecars and digests; repeated no-op replay is bit-identical; uniform-shift QA meets the frozen technical ceiling or the study terminates ineligible; no neural parameter is updated.

### M4 — Cross-corpus probes, relations, interventions, and projections

- [ ] Implement fit-source-only alpha/scaler/vocabulary/nuisance selection and bidirectional transfer evaluation.
- [ ] Implement grouped bootstrap inference, relational advantages, delta fingerprints/specificity, and rank-16 projection/scrubbing organizations.
- [ ] Add planted synthetic fixtures for pure absolute null, relative-gap response, context-only response, lexical-only response, relation-aware gain, nuisance-only shortcut, source reversal, missing class, and overlapping subspaces.

Acceptance: synthetic regimes produce their planted outcomes; target labels never affect preprocessing fitted on the held-out source; every task/intervention retains separate eligibility and finite-draw status; degenerate denominators remain undefined rather than zero.

### M5 — Terminal report and research decision

- [ ] Produce a machine-readable result, a detailed Markdown atlas, environment/config/input/output manifests, completion marker, and the single mechanical outcome above.
- [ ] Run independent `/adversarial` review on the implementation/result bundle and `research-claim-review` on the proposed interpretation.
- [ ] Update `ANALYSIS.md`, `RESULTS.md`, and `TODO.md` only with claims licensed by that review.

Acceptance: all reported numbers resolve to immutable artifacts; the report distinguishes strict-absolute null, observational decoding, relational advantage, controlled intervention, and projection evidence; no confirmation or blind source was accessed; no training process or checkpoint was created.

## Definition of done

- [ ] A frozen v3.1 discovery protocol/config exists before representation scoring.
- [ ] EWT and GUM are the only opened scientific datasets and are labeled reused-public exploratory evidence.
- [ ] Every retained class and intervention population passes document-level support or is prescore-ineligible.
- [ ] Strict absolute, boundary/sequential, context accumulation, syntactic relation, lexical/morphological, and matched proper-noun constructs are reported separately; semantic/entity type is explicitly not estimable from the common UD inputs.
- [ ] Cross-corpus raw and nuisance-incremental signals, controlled intervention fingerprints, relational gains, and simple rank-16 projection/scrubbing results are complete or explicitly ineligible.
- [ ] The atlas returns one and only one allowed outcome without analyst override.
- [ ] No neural training occurs, no old/frozen result is modified, and no C1/C2/confirmation/final/private payload is opened.
- [ ] Unit/synthetic/smoke checks pass; cache/config/data/code/environment hashes and exact rerun commands are recorded.
- [ ] Independent adversarial and research-claim reviews constrain the final interpretation.

## Verification plan

- Plan: run the plan checker on this RFC where supported, then independent `/adversarial` review until no blocker remains.
- Unit: focused `pytest` for firewall, CoNLL-U join, support, alignments, nuisance fitting, group folds/bootstrap, relational matching, delta metrics, and mechanical selection.
- Synthetic: run every planted regime twice and compare result digests.
- Smoke: tiny CPU model/input fixture plus one deterministic Pythia GPU batch; assert zero parameter/optimizer/checkpoint writes.
- Reproducibility: fixed seeds, deterministic Torch settings, pinned model/data/dependency revisions, no hardcoded machine paths, and immutable run roots.
- Data firewall: inspect the opened-input ledger and grep config/logs/manifests for forbidden sources/roles; compare all source digests.
- Results: recompute metrics independently from frozen caches and rows; run `/adversarial work` and `research-claim-review` before updating conclusions.

## Risks & one-way doors

- **Discovery overinterpretation:** tasks were chosen after v2.4. Mitigation: label all v3 inference exploratory and require fresh confirmation before any architecture claim.
- **Absolute/boundary confounding:** bare-sequence index, sentence-start distance, and visible prefix length overlap. Mitigation: uniform-shift, virtual-gap, true-prefix, unrelated-prefix, and no-visible-prefix conditions are separate; no single contrast is called pure boundary causality.
- **Off-manifold virtual positions:** discontinuous position IDs diagnose RoPE sensitivity but may not represent natural text. Mitigation: report separately and require agreement with natural sequential evidence before nomination.
- **Natural-prefix semantic mismatch:** unrelated prefixes are not neutral. Mitigation: exact length/source/fold matching, shift-only and separator-only controls, true-versus-unrelated and generic-context contrasts, and explicit interpretation limits.
- **Cross-corpus label/domain drift:** EWT and GUM annotation/domain differ. Mitigation: fixed coarse common maps, fit-source-only preprocessing, both transfer directions, and per-source reporting.
- **Probe-driven subspace circularity:** the same discovery task builds and evaluates its projection. Mitigation: construct basis only on one source and evaluate unchanged on the other; still label all results exploratory.
- **Relational leakage:** pair representations can encode individual token positions and identities. Mitigation: child-only and matched non-head comparators, nuisance models, matched directions/distances/UPOS, component-group folds, and separate difference/concatenation results.
- **Multiple testing/ranking:** many screens create researcher degrees of freedom. Mitigation: freeze the inventory and mechanical nomination rule; pointwise intervals are descriptive, and confirmation tests only one selected target.
- **Cache lineage drift:** reusing v2 arrays with changed row semantics can silently misalign data. Mitigation: require ordered row IDs and every parent digest; otherwise recompute in a new namespace.
- **Working-tree collision:** the repository contains substantial uncommitted historical work. Mitigation: add v3-named artifacts only, never reset/clean, and do not edit v2.4 data/results.

## Alternatives considered

1. **Train an equal-capacity K2 immediately.** Rejected because v2.4 did not identify a sufficiently specific factor target; a cleaner optimizer cannot repair an ambiguous ontology.
2. **Search many unrelated candidate concepts.** Rejected because it increases post-hoc researcher degrees of freedom. The v3 inventory is limited to the evidence-motivated 50/30/20 allocation: refined position/context, token-local versus contextual/relational, and a small morphology/syntax screen.
3. **Reuse v2.4 C2 as confirmation.** Rejected because its outcomes and support have been inspected and shaped this protocol.
4. **Use only observational probes.** Rejected because decodability cannot distinguish index, boundary, context, lexical, and relational mechanisms. The factorial interventions and relational controls are necessary.
5. **Treat EWT→GUM transfer as confirmation.** Rejected because both sources are reused public development data. Transfer is a robustness diagnostic only.

## Deviations log

- 2026-08-02: initial plan; no v3 representation scoring or neural training has started.
