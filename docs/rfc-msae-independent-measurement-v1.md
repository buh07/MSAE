# PLAN — MSAE independent measurement study v1

> Prospective execution plan, 2026-08-20. This plan begins from the completed
> readiness contract in `docs/rfc-msae-measurement-remediation-readiness-v1.md`
> and the current gate state in `TODO.md`. It does not reinterpret or overwrite
> Atlas-v1, the diagnostic continuation, or measurement-v2.4.

## Goal

Freeze the evidence, source, checkpoints, tasks, thresholds, and endpoints needed
for a new independent measurement attempt; obtain an independent prescore
review; build Stage A; and launch only the calibration replay in a new tmux/GPU
run. The replay may build Stage B only if the frozen numerical gate passes. This
turn must return after a live launch handoff rather than waiting for results.
Confirmation scoring and Stage C remain downstream of a separate post-Stage-B
review and authorization.

The scientific question is broader than absolute position: can the existing K=2
MSAE checkpoints reproducibly separate absolute position,
relative/structural position, and lexical/semantic content while retaining
Tier-2 morphosyntax/surface information and passing specificity controls?

## Non-goals

- Do not change, delete, repair, rerun, or overwrite any historical config,
  result, cache, checkpoint, or terminal artifact.
- Do not use prior scientific outcomes to choose the new source, split,
  tolerance, task, checkpoint, baseline, or threshold.
- Do not call a single checkpoint three independent lineages, and do not use the
  matched-seed `g7` ablation as an independent seed.
- Do not open confirmation neural scores in this turn. Do not build Stage C from
  placeholder or self-asserted evidence.
- Do not authorize new model training or select a final paper branch.
- Do not wait for the launched calibration result.

## Constraints and frozen choices

### Discovery/confirmation firewall and source

- The independent source is **AMALGUM v0.2**, an English, document-grouped,
  machine-annotated web corpus with UD dependencies and entity annotations.
  It is new to this repository's MSAE/Atlas outcome history; an exhaustive
  case-insensitive repository search for `AMALGUM` is captured before download.
  Its machine annotations and possible Pythia pretraining overlap are explicit
  limitations, not hidden claims of human-gold labels or training-data novelty.
- Pin one immutable upstream Git commit before reading corpus contents. Download
  only the public non-Reddit `amalgum/dep` CoNLL-U files. Record commit, URL,
  annotation and upstream-text license/redistribution status by genre, byte size,
  and SHA-256 per physical file. Do not copy restricted raw text into a
  redistributable artifact merely because annotations are CC-BY.
- The sampling algorithm is fixed before content inspection: within each of the
  seven public non-Reddit genres (`academic`, `bio`, `fiction`, `interview`,
  `news`, `whow`, `voyage`), normalize the repository-relative POSIX filename to
  NFC UTF-8, and hash the binary length-prefixed tuple `(protocol_id, revision,
  filename)`, with every length encoded as unsigned 64-bit big-endian. Order by
  `(digest bytes, filename UTF-8 bytes)`; select the first 50 distinct documents,
  assigning zero-based even ranks to C1 and odd ranks to C2 (25 documents per
  genre per role).
  Documents are the independent groups; no document crosses roles. If any genre
  has fewer than 50 valid CoNLL-U documents, or either role fails a label-only
  support rule, stop before Stage A rather than substitute a source/genre/task.
- A label-only audit may parse labels and tokenizer layouts but may not load the
  language model, any MSAE checkpoint, or any historical outcome. Exact selected
  document IDs, file hashes, split hash, duplicate normalized-content audit,
  per-role group/class counts, and dropped-row reasons are frozen before Stage A.
- Independence means exact-canonical and accessible-history near-document/outcome
  independence, not annotation-pipeline, pretraining, or blind-final-overlap
  independence. Original text is reconstructed from integer-token FORM fields,
  respecting `SpaceAfter=No`, NFC-normalized, whitespace-collapsed, and SHA-256
  hashed. A second accessible-history audit lowercases maximal consecutive
  Unicode letter/number sequences and drops punctuation, then forms a set of
  5-grams serialized as the length-prefixed UTF-8 tokens (u64be
  length plus bytes for each token), and uses 128 minima. For permutation `p`,
  hash `u64be(p) || u64be(len(shingle)) || shingle` and interpret all 32 SHA-256
  bytes as one unsigned big-endian integer; duplicates use set semantics and the
  unsigned minimum is retained. Estimated Jaccard is the fraction of 128 equal
  minima. A text with fewer than five tokens uses its complete token sequence as
  one shingle; empty text is invalid. Estimated Jaccard >=0.75 triggers exact
  5-gram Jaccard, and exact >=0.80 is a blocking near duplicate. The coordinator
  compares selected documents/sentences against an enumerable accessible-history
  universe: every regular file present at baseline anywhere under `data/`
  except the new `data/msae_independent_measurement_v1/` namespace whose suffix is `.conllu`,
  `.jsonl`, or `.json` and whose parsed records contain any of `text`,
  `sentence`, `words`, `tokens`, `source_words`, or `target_words`. Before
  source exposure, a candidate-file manifest freezes every visited relative
  path, file SHA-256, recognized record type, record count, and inclusion or
  exclusion reason; unparseable candidate files block rather than disappear.
  The only exclusions are exact non-text metadata records and paths whose
  baseline manifest marks them `sealed_final=true`. The audit records one
  exact/near result for every included record and one reason for every excluded
  file. It **does not open or ask another process to open the sealed
  final partition**. If no pre-existing blind-safe overlap commitment exists,
  final overlap remains explicitly unknowable and is not misreported as checked.
  Any selected-selected or accessible-history collision blocks Stage A. Pre-plan
  name novelty is established
  by `git grep -in AMALGUM <baseline-HEAD> -- .` plus a byte search of every
  pre-existing dirty/untracked file in the baseline inventory. The report binds
  every searched path and digest and excludes only new allowlisted paths, so the
  new RFC itself cannot contaminate the check.
- Calibration replay uses only the already public GUM calibration records and
  prepared units from measurement-v2.4; AMALGUM C1/C2 never enter tolerance
  selection.

### Calibration replay

- Four frozen strata cover short main units, long main units,
  document-context-pair units, and entity-substitution-pair units. Each stratum
  contains exactly eight deterministic units selected from the public GUM
  calibration prepared manifest by a config-bound hash order. Unit IDs, ordered
  input IDs, selected positions, row IDs, input digest, row digest, model blob
  digest, code digest, dtype, layer, and first-subtoken reduction path are bound
  in the raw config before model inference.
- Each stratum has one reference evaluation and three repeats. Every evaluation
  is recomputed by a fresh forward pass in the same process, and every unordered
  pair is checked by the reviewed remediation selector.
- Freeze the ordered ladder
  `[(5e-7,0), (5e-7,1e-6), (5e-7,5e-6), (1e-6,5e-6),
  (2e-6,5e-6), (5e-6,5e-6), (1e-5,5e-6), (2e-5,5e-6)]`
  and safety factor `2.0`. These are prospective engineering bounds anchored to
  the old numerical-QA ceiling, not estimated from AMALGUM or the new replay.
  Failure of the entire ladder is terminal/ineligible; no extrapolation or rerun
  with looser values is permitted.
- Runtime uses deterministic algorithms, TF32 disabled, float16 model weights,
  float32 cached arrays, Pythia-160M-deduped revision
  `582159a2dfe3e712a8d47ae83dec95ae3bde8e7e`, layer 3, offline local files, and
  a recorded package/GPU/driver environment. Cached no-op serialization must be
  byte-exact; batch-versus-unit replay must pass the selected bound; source/target
  counterfactual rows must retain their frozen alignment.
- The auxiliary Stage-B checks are typed observations, not caller assertions.
  `cached_noop_hash_replay` stores and reloads each reference array using the
  registered little-endian float32 NPY schema and requires identical file and
  remediation-payload digests. `canonical_pooling_qa` reruns the same eight units
  one at a time, preserves the registered first-subtoken row order, and applies
  the selected replay tolerance to batch-versus-unit arrays.
  `counterfactual_cache_alignment_qa` uses the two registered pair strata,
  requires exact source/target pair-ID and local-index coverage, and recomputes
  row and payload digests. The GPU CLI constructs all three Stage-B evidence
  records internally from these observations.

### Independent checkpoint lineages and stability

- Freeze candidate checkpoint lineages `g4`, `g5`, and `g6` only. Their exact
  run IDs are `k2_wave2_fast_g4_L3_s42_inc1e2`,
  `k2_wave2_fast_g5_L3_s43_inc1e2`, and
  `k2_wave2_fast_g6_L3_s44_inc1e2`; seeds are 42, 43, and 44. Their checkpoint
  paths are, in that order,
  `pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g4_L3_s42_inc1e2/checkpoints/final_step249244_tok1000000016.pt`,
  `pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g5_L3_s43_inc1e2/checkpoints/final_step249244_tok1000000016.pt`, and
  `pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g6_L3_s44_inc1e2/checkpoints/final_step249675_tok1000000042.pt`.
  Their training-summary paths are the `train_summary.json` sibling of each
  named run's `checkpoints/` directory. Their final checkpoint SHA-256 values are
  `00714ca209027d418156f65dda55b90e6f1887a75ef412acb43a61359d711e97`,
  `933120800d5861dddbe99f725c04467c0684bbd069b6d9f345d2b202a43003ef`,
  and `d4cd3ac52805f70bbcec60857a3c4afd6361248038a541f63a0cfcfe1b5b3e43`.
  Their training-summary SHA-256 values are respectively
  `c2e09c1b82eacd36c012cfe3b58f2d399f2a3fd557a2be7d47f180ada2c09a8f`,
  `82e15a585103ce9d1366402e9f0d84606d2437e427e1acecd5f85fa69fdf2121`, and
  `30d070528818d4342525e5247f76340317dc2c4b8717fcfbc941e44d975bf32a`.
  `g7` has exact run ID `k2_wave2_fast_g7_L3_s42_inc0` and is the seed-42,
  matched-data-order/budget, `lambda_inc=0` control at
  `pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g7_L3_s42_inc0/checkpoints/final_step249244_tok1000000016.pt`;
  its checkpoint digest is
  `76474c4576e024d13d6ae9a3b43f38ac51918c84db1b75121932709d5f8dbc49`,
  its training summary is the sibling `train_summary.json`, and its digest is
  `af3b9f0508d7f98f907864c09c9870ded5ca65dda6f3eb056f5c597b53eb6638`.
  It is matched specifically to g4 but never enters the minimum-three candidate
  seed aggregation. The implementation rehashes all eight physical files and
  rejects any global duplicate run ID, physical path, checkpoint digest, or
  training-summary digest; candidate seeds must also be unique. It rejects every
  path/digest/seed/run-identity mismatch.
- Functional reproducibility is task-first across the three candidate seeds.
  Maximum checkpoint spread is frozen at `0.05` for normalized recovery,
  leakage, and signed selectivity. Crossing the boundary is ineligible; equality
  passes. This is descriptive replication with three seeds, not a population
  p-value or a five-seed learned-model claim.

### Families, tasks, baselines, and endpoints

The Tier-1 claimable families and primary localization tasks are:

1. `absolute_position`: fixed seven-way absolute bucket and four-way neutral
   prefix-offset classification. Controlled position shift is a separate
   counterfactual axis, never a normalized-localization task.
2. `relative_structural_position`: relative quartile, signed head distance, and
   dependency depth. Controlled position shift and document-context anchor are
   separate counterfactual axes.
3. `lexical_semantic_content`: token identity, lemma identity, and entity-binary
   decoding. Token/lemma identity are reported separately but count as one
   nested `identity` construct; entity-binary is the distinct second
   localization construct. Coarse entity type is diagnostic. Entity substitution
   is a counterfactual axis only and cannot supply recovery/leakage/selectivity.

`morphosyntax` (coarse UPOS, coarse dependency relation, Number) remains Tier 2
collateral/sentinel evidence; this protocol does not silently promote it to an
architecture-selection family. Surface/source tasks are Tier-2 shortcut and
nuisance sentinels. Equality at every inclusive support threshold passes. No
unsupported primary task is silently dropped: a support failure blocks Stage A
and requires a new reviewed protocol.

Support requires, separately in C1 and C2, at least 25 document groups per task,
at least 20 groups per retained class, at least two retained classes, no row
shared across roles, no more than 256 selected rows per document, and a maximum
256-class token/lemma vocabulary ranked by `(minimum document frequency across
discovery, calibration, C1, and C2 descending; total frequency descending;
label UTF-8 ascending)` from labels with document frequency >=20 in every role.
AMALGUM participates only in this prescore label/support intersection; no neural
outcome can change it, and the vocabulary is immutable after Stage A. All main
tasks treat AMALGUM as one applicable source and resample its seven genres as fixed highest-level
strata. The `source_genre` nuisance exception requires 25 groups in every genre
and two or more pooled labels with 20 groups each; it never requires one genre
to contain another genre's label. The same pooled deterministic-label exception
applies to every discovery/calibration `source_type`: each named source stratum
must satisfy its own group/cap rule, the pooled role must satisfy label support,
and no stratum is required to contain another stratum's label. Role-specific
source-label maps are frozen before map generation.

The label-only audit freezes all 500 ordinary, unconditional maps for every
registered `(role, task)`, including the historical discovery and calibration
roles described below. After the deterministic per-document, per-label
round-robin cap, every discovery/calibration source stratum with `n` genuine
documents supplies exactly `n` slots; every AMALGUM C1/C2 genre stratum has
`n=25` and supplies exactly 25 slots, all with replacement. For draw `0..499`,
slot `j` indexes the
UTF-8-sorted genre document list by the first eight bytes, interpreted unsigned
big-endian modulo `n`, of SHA-256 over the UTF-8 string
`msae_independent_measurement_v1|20260820|{role}|{task}|{stratum}|{draw}|{j}`.
Every interpolated registry ID must match `[A-Za-z0-9_.:-]+` and therefore cannot
contain the `|` delimiter; otherwise configuration is invalid. There is no
redraw. A normal task draw is finite only when every frozen retained
class is present in the pooled genre-stratified resample and its raw/chance
denominator inputs are structurally defined; source-genre is finite when every
fixed genre stratum contributes at least one sampled document. Hard support is
checked first; every required task/construct needs at least 490/500 finite maps,
with 489 ineligible. The complete maps and per-draw pass matrix are hashed into
Stage A; model scores do not enter this audit. Inference is conditional on the
seven fixed AMALGUM genre strata and does not claim population-level source
generalization.

AMALGUM entities are read from the CoNLL-U `Entity` MISC stream with strict
balanced-parenthesis nesting. Token-level `entity_binary` is `ENTITY` when any
span covers the integer token and `O` otherwise; multiword and empty-node rows
do not become probe rows. For nested spans, binary membership is the union;
coarse type uses the outermost span, ties are errors, and the frozen map is
`person`, `place`, `organization`, `event`, `time`, and `other`. Missing Entity
metadata is `O`; malformed or unknown syntax is an error. Entity substitution
uses a single-token, single-first-subtoken entity mention and a different-document
same-coarse-type donor whose replacement preserves the entire tokenizer word-ID
layout. Candidate donors are ordered by SHA-256 of the length-prefixed tuple
`(protocol_id, role, source_document, donor_document, source_row, donor_row)`
and the first compatible donor is used; no compatible donor blocks the
entity-substitution construct rather than changing type or source. Entity/non-
entity and retained coarse classes use document support, not token counts.

The Stage-C registry is exhaustive and prescore-frozen. For every g4/g5/g6
candidate under a G1 broad-position outcome, `x_pos_priv` is assigned jointly to
absolute and relative/structural position and `x_content_priv` to
lexical/semantic content at L3. Under a G1 split-position outcome, the existing
K=2 checkpoints are structurally incapable of satisfying separate absolute and
relative assignments; G2 records that incompatibility rather than relabeling a
branch. `joint`, both complements, and residual are registered
leakage/diagnostic components. g7 repeats the same matrix as the matched-seed
negative regularizer control but is never a replicate. L4 is descriptive
raw-only and cannot rescue L3. The exact registry contains:

- localization: every `(role, decoding-task, construct, component, L3, recovery|leakage|
  selectivity)` cell; G1 elementary L3 family/component selectivity contrasts;
  G1 broad-versus-split position; raw-gap eligibility; and diagnostic absolute
  position. Task failure stays undefined and blocks its family under the frozen
  two-construct rule; it is never replaced by zero;
- functional reproducibility: recovery/leakage/selectivity task-and-family
  summaries across g4/g5/g6;
- collateral: explicit `(role, component, task, recovery|retention|leakage,
  uncertainty, status)` records for Tier-2 coarse UPOS, coarse dependency
  relation, Number, capitalization, word length, punctuation, sentence-boundary,
  and source-genre, plus LM cross-entropy, reconstruction FVU, and aggregate
  non-target-family retention. Tier-2 records stay outside the G1 BH family but
  every required failure remains visible and blocks applicable non-inferiority;
- counterfactual: neutral prefix shift, within-document context anchor,
  single-token lexical/entity substitution, matched-magnitude random edit,
  inactive-branch sham, and exact no-op;
- baseline: raw activations; the two selectable projection candidates defined
  below; shuffled-label/chance probes; matched-random, sham, and no-op controls;
  the four locked nonwinning robustness transforms defined below; and explicit
  `not_applicable` records only for unavailable K=1 and unregularized/capacity-
  matched learned checkpoints. Nonwinning transforms cannot enter the primary
  score, tie set, replacement, or claim.

The counterfactual registry is an executable matrix, not an open-ended list.
For every `(C2 document, registered row, checkpoint, transform)` it binds source
and target input IDs, word IDs, scored positions, target family, assigned and
each nonassigned component, template-group ID, and payload hashes. The four
groups are: (1) `neutral_prefix_shift`, whose literal prefixes are `"In fact, "`
and `"As a result, "` and whose target is absolute position; (2)
`within_document_context_anchor`, which prepends the immediately preceding
sentence from the same document and targets relative/structural position; (3)
`single_token_lexical_substitution`, whose donor is the first different-document
same-UPOS donor under the already specified hash order and targets lexical
content; and (4) `single_token_entity_substitution`, using the frozen
same-coarse-type donor rule above and targeting lexical/semantic content. A pair
is retained only if source and target word-ID layouts are identical at all
scored original words; prefix rows instead require an exact constant offset and
identical original-word suffix. No compatible row is imputed or substituted.

For a retained row, apply the checkpoint tokenwise to source and target L3
hidden-state sequences and average raw/position/content representations over the
registered aligned original-token positions. Let `d_raw` and `d_c` be cosine
distances of source versus target raw and component means. `d_raw < 1e-4`, a
zero/nonfinite norm, or any alignment/hash failure invalidates the row. Actual
normalized sensitivity is `d_c/d_raw`. For the matched-random control, generate
one ambient Gaussian direction with NumPy PCG64 seed
`(20260820 + stable_hash("matched_random", checkpoint_id, transform_id)) mod
2^63`, where `stable_hash` is the unsigned first eight bytes of SHA-256 over the
NUL-delimited UTF-8 arguments. Remove projections onto both the actual raw
source-target delta and raw source mean, normalize, and solve the unique positive
scale that makes source-to-perturbed-source raw cosine distance equal `d_raw`.
Add the scaled direction to every scored source token, rerun the checkpoint
tokenwise, and average. Orthogonalization rank failure, no finite positive
solution, absolute cosine with either removed vector >`1e-6`, or distance-match
error >`1e-6` invalidates the row. Record direction and scale hashes.

The exact no-op/sham reruns the complete source model/checkpoint path from input
IDs without reusing an activation cache; raw and every branch cosine distance
must be <=`1e-6`. `inactive_branch_sham` is not a second edit: it is the
nonassigned branch response to the same actual and matched-random inputs. Row
specificity is assigned actual normalized sensitivity minus the larger of its
assigned matched-random normalized sensitivity and assigned sham sensitivity.
The separate mapping contrast is assigned actual sensitivity minus the maximum
nonassigned actual sensitivity. Average rows within each of the four groups,
then applicable groups equally. Absolute position must retain its one prefix
group, relative/structural position its one context group, and
lexical/semantic content both lexical and entity groups. Every applicable group
needs >=24 valid rows; every family needs an equal-applicable-group specificity
95% lower bound >=`0.05` and a mapping point contrast >=`0.05` in **every**
applicable group. A non-target transformation never counts toward that family.
Punctuation/format is the neither-branch sentinel: a >=`0.05` lower bound or
positive contrast in three of the four total groups on either branch invalidates
specificity. Any no-op, alignment, scale,
denominator, row-count, or sentinel failure makes the checkpoint-family endpoint
invalid and G2 equivocal; it is never omitted. This is representation-distance
specificity, not a causal claim.

Probe fitting uses the new 500-map estimator specified here, which deliberately
supersedes the old fixed-calibration bootstrap for this independent study: all
selection/refitting is nested inside each draw, while the full-sample point
estimate selects alpha once on the full calibration role. G1/G2 retain the exact decision
thresholds and equivocal precedence in `TODO.md`: recovery >=0.75, leakage
<=0.55, selectivity >=0.20 for family eligibility; simple-baseline match bounds
0.05 selectivity, 0.02 retention, 0.02 collateral, and 0.05 stability; low K2
positional leakage <=0.25. Stage C cannot be eligible unless every required
endpoint is present and valid.

The G1 BH family contains exactly four L3 elementary hypotheses: absolute,
relative/structural, and lexical/semantic assigned-component selectivity, plus
split-minus-broad positional selectivity. The G2 BH family is the three
`(g4|g5|g6, calibration-selected primary baseline, macro Tier-1 selectivity,
L3)` superiority contrasts; g7 is a required control outside the replicate set.
One-sided randomization p-values use BH q<=0.05; separate two-sided hierarchical
bootstrap 95% effect CIs must be above zero for promotion. Retention, collateral,
stability, and applicable reconstruction are simultaneous max-statistic
non-inferiority gates, not additional selection opportunities. Source/genre is
the highest resampling level, document is next, and the probe/subspace is refit
inside every map. No failed/undefined endpoint is removed from its correction
family, alpha is not recycled, and the exhaustive G1/G2 decision-table
equivocal precedence in `TODO.md` is unchanged.

Inference is frozen numerically as follows. Every point, bootstrap draw, and
randomized reconstruction first computes a fixed-genre mean within task, an
equal mean over applicable tasks within family, and then an equal mean over the
seven AMALGUM genres; maxima over named leakage components occur only after
those aggregations. Bootstrap interval quantiles use sorted finite values and
the zero-based nearest-rank index `ceil(p*n)-1`. A required scalar needs at least
490 finite values among its 500 registered paired maps; its two-sided interval
is the 0.025 and 0.975 quantiles. A simultaneous family uses only draw IDs finite
for every coordinate and requires at least 490 such complete draws. For point
vector `theta` and draw vector `theta*`, its lower radius is the 0.95 quantile of
`max_i(theta_i-theta*_i)` and its upper radius the 0.95 quantile of
`max_i(theta*_i-theta_i)`; bounds are `theta_i-lower_radius` and
`theta_i+upper_radius`. NaNs are never coordinatewise discarded, and equality
to every inclusive threshold passes.

Randomization is source/genre-stratified wild pseudovalue inference. Within each
genre with `G` physical documents, form the delete-one pseudovalue
`p_c = G*theta(D) - (G-1)*theta(D\\c)` for every primitive assigned-recovery and
named-leakage coordinate. Any undefined leave-one value, nonfinite pseudovalue,
failure to reconstruct the full statistic to `1e-10`, fewer than 10 documents in
any required genre/task, or fewer than 20 nonzero physical-document vectors
makes the hypothesis invalid. Draw exactly 9,999 joint Rademacher sign vectors
from NumPy PCG64 seed `(20260820 + stable_hash("randomization", hypothesis_id,
component_id)) mod 2^63`; one sign applies jointly to all tasks/components for a
physical document. For the first three G1 family hypotheses, test every specific
assigned-minus-named-leakage contrast under zero-null signs and take the maximum
component p-value (intersection-union). For split-minus-broad G1 and every G2
learned-minus-simple contrast, first compute the complete nonlinear paired
contrast on the full data and every delete-one dataset and form contrast
pseudovalues `q_c=G*delta(D)-(G-1)*delta(D\\c)`. Their genre mean must
reconstruct the observed genre contrast to `1e-10`. The null residual is
`q_c-mean_c(q_c)`; sign-flip these residuals jointly by physical document and
recompute the fixed-genre then overall mean. This permuted contrast is zero-null
by construction and is compared with the unmodified observed contrast.
Positive, negative, and zero planted deltas must pass algebraic reconstruction
tests. With positive alternative, each Monte Carlo p is
`(1 + count(T_perm >= T_obs))/10000`. G1 BH operates on exactly four p-values;
G2 BH on exactly three. A missing/invalid member remains in its family and forces
that decision family equivocal rather than shrinking the denominator.

### Scientific fit/evaluation firewall

The source adapter rebuilds the **same frozen label definitions** on the already
public Atlas-v1 discovery and calibration records, whose exact files, task-row
manifests, and hashes are transitive config dependencies. Discovery is the only
fit role: it supplies vocabularies/class maps and fits scalers, ridge probes, and
task-derived coefficient-SVD subspaces. Calibration is the only selection role:
it selects ridge alpha from `[0.1,1,10,100]` using macro-F1 (ties within 0.005
choose the larger alpha), audits raw gaps, and applies the already frozen simple-
baseline rule. AMALGUM labels participate only in the prospective support
intersection above; no AMALGUM neural value changes a vocabulary, class map,
rank, scaler, alpha rule, candidate, threshold, or component assignment.

Each draw index `d=0..499` binds four ordinary maps: one discovery refit map, one
calibration-selection map, one C1 evaluation map, and one C2 evaluation map. On
draw `d`, fit the scaler, probes, and coefficient-SVD candidates only on the
discovery map; select alpha only on the calibration map; refit the selected
probe/subspace only on that discovery map; and evaluate the fixed result on C1
or C2's map. No C1/C2 row is ever a fit or selection row. Group multiplicities
become sample weights, the 256-row document cap is applied before mapping, and
all fit/selection operations repeat inside each draw. C1 scores raw G1 only and
cannot score or select K2/G2. C2 scores the G1-compatible existing K2 plus the
frozen simple/robustness baselines for G2 only and cannot alter G1 topology.

The raw G1 operands are exact. `projection_broad16` is the rank-16 right-singular
span of concatenated discovery standardized-probe coefficient rows for both
position families. `projection_split8_8` is the pair of separate rank-8 spans for
absolute and relative/structural tasks. `projection_content8` is the rank-8
lexical/semantic span. Rank deficiency is ineligible, never padded. Construction
artifacts bind the discovery map, row/task manifest, scaler, coefficients,
singular values, and basis payload digest.

This new study has a **new discovery/calibration-only baseline-selection gate**;
it does not carry forward the failed historical selection. Its complete ordered
candidate registry is exactly:

1. `projection_broad16_content8`: standardize each discovery activation column
   by discovery weighted mean and population standard deviation (zero variance
   is invalid); fit one-vs-rest ridge probes with intercept for every retained
   absolute, relative/structural, and lexical/semantic class using
   `alpha in [0.1,1,10,100]`, Cholesky solve of `(X'WX + alpha*I)` with the
   intercept unpenalized, and calibration macro-F1 selection (within `0.005`,
   choose larger alpha). Sign-canonicalize each coefficient row by making its
   largest-absolute loading, with lowest-index tie, positive. The first 16 right
   singular vectors of the concatenated absolute+relative coefficient rows are
   the position component; the first 8 from lexical/semantic rows are content.
   Each complement is the orthogonal residual. Exact retained rank is 24.
2. `projection_split8_8_content8`: use the identical scaler, probes, solver,
   alphas, sign convention, and coefficient rows, but take separate rank-8 bases
   from absolute and relative/structural rows and a rank-8 content basis. For
   aggregate position endpoints, concatenate absolute then relative bases and
   deterministically QR-orthonormalize with positive largest-absolute loading;
   overlap causing aggregate rank <16 is invalid. Exact retained rank is 24.

For either selectable candidate, concatenate its 16-dimensional aggregate
position basis and 8-dimensional content basis, record all pairwise principal
angles and the QR union rank, and require union rank 24. Cross-family overlap is
therefore invalid rather than double-counted. Degrees of freedom uses nominal
rank 24 only after that check passes.

The ordered label/class maps are frozen in Stage A. A multiclass probe with `C`
retained classes has `C*(H+1)` fitted coefficients including intercept, and a
binary probe has `2*(H+1)` because it uses the same one-vs-rest form; `H` is raw
activation width. Candidate degrees of freedom are `retained_basis_rank +` the
sum of these probe counts across every fitted Tier-1 and Tier-2 task. Because the
probe set is identical, both candidates have equal probe count and rank 24;
remaining ties resolve by the listed registry order, not an implementation's
sort. A missing class, singular/failed solve, basis rank deficiency, or nonfinite
fit makes that candidate invalid for that map with no alternate solver.

Four additional transforms are locked **nonwinning robustness endpoints**. They
use the same discovery scaler, map weights, task probes, calibration-selected
alphas, component metrics, and C2 evaluation rows, are refit inside each map,
and can never replace the primary candidate: (a) `pca16_8`, the first 16 and
next 8 sign-canonicalized right singular vectors of the centered standardized
discovery activation matrix as position and content; (b) `random16_8`, QR of an
`H x 24` NumPy-PCG64 standard-normal matrix seeded by
`(20260820 + stable_hash("random_projection", draw_id)) mod 2^63`, first 16 then
8 columns, with positive largest-absolute loading; (c) `ridge_position_residual`,
a multi-output ridge (`alpha=1`, unpenalized intercept, the same Cholesky failure
rule) from the concatenated one-hot absolute+relative discovery labels to each
standardized activation column, with its fitted value as position and residual
as content; and (d) `inlp_fixed16`, exactly 16 iterations cycling the ordered
absolute then relative tasks, fitting the same fixed-`alpha=1` one-vs-rest ridge
on the current residual, removing the top sign-canonicalized right singular
direction of its coefficient matrix, and using the 16 removed orthonormal
directions as position and the final residual as content. A deficient rank,
missing class, failed solve, or nonfinite result is reported invalid. PCA and
random use retained rank 24; regression records coefficient rank; INLP must have
removed rank 16. Shuffled-label probes use one PCG64 permutation within each
genre/document map with seed `(20260820 + stable_hash("shuffle", task_id,
draw_id)) mod 2^63`; chance is the frozen calibration class-prior predictor.
Every raw, robustness, shuffled, and chance endpoint/status is retained even
when invalid.

On each map and on the full-sample point fit, a candidate is eligible only when every
Tier-1 raw gap and every required Tier-2 sentinel is measurable, all three
assigned-family recoveries are >=0.65, and worst absolute Tier-2 macro-F1
degradation is <=0.10. Among eligible candidates, let `M` be the maximum
equal-weight Tier-1
selectivity, form the tie set `{c: M - score(c) <= 0.01}`, then minimize the
frozen degrees-of-freedom count, then the ordered registry index. At least
490/500 maps must independently select the exact full-sample winner ID and its
simultaneous gates must pass. If no candidate passes or the
selection-stability rule fails, record baseline selection ineligible and stop
**before any AMALGUM C1/C2 neural scoring**; G1/G2 remain not-run/equivocal. If it
passes, a separately signed calibration-science artifact freezes the winner,
evidence, and candidate digests before C1. Nonwinning candidates remain locked
robustness results and cannot replace the primary after C1/C2 scores. The 500
discovery/calibration maps may reselect candidate IDs only to test selection
stability. After the full-sample winner is signed, every C1/C2 draw refits that
same candidate ID and may not reselect the comparator identity.

## Approach

Add a new, additive study namespace:

- `configs/msae_independent_measurement_v1/` for the raw protocol, source,
  partition, checkpoint, task, endpoint, and authorization freezes;
- `data/msae_independent_measurement_v1/` for immutable raw-source and label-only
  manifests/prepared records;
- `reports/provenance/msae_independent_measurement_v1/` for source-exposure,
  Stage-A, reviews, and launch evidence;
- `pilot_runs/20260820_msae_independent_measurement_v1_calibration/` for the new
  replay only;
- additive scripts/tests named `msae_independent_measurement_v1*`.

M0's exact write allowlist is this RFC; the three new roots
`configs/msae_independent_measurement_v1/`,
`data/msae_independent_measurement_v1/`, and
`reports/provenance/msae_independent_measurement_v1/`; the exact review records
`reports/adversarial/msae_independent_measurement_v1_plan_review.md` and
`reports/adversarial/msae_independent_measurement_v1_prescore_review.md`; the
exact files `scripts/msae_independent_measurement_v1.py`,
`scripts/run_msae_independent_calibration_v1.py`,
`scripts/launch_msae_independent_calibration_v1.sh`, and
`tests/test_msae_independent_measurement_v1.py`; and the create-once run root
`pilot_runs/20260820_msae_independent_measurement_v1_calibration/`. Before M1,
the baseline records `git status --porcelain=v1 -z -uall`, type/size/SHA-256 of
every pre-existing non-allowlisted dirty path, and recursive hashes of all
historical inputs/checkpoints/configs/results named by the transitive closure.
Final prelaunch verification rejects content/status/type drift in that inventory,
any protected historical drift, or any new path outside the allowlist. Allowed
additions receive their own final inventory; no allowlisted prefix permits an
existing historical file to be overwritten.

A CPU-only preparation CLI performs source download, hashing, partitioning,
label audit, and a provisional calibration-stratum candidate. After all scripts
and tests are implemented, a finalizer inventories the complete transitive
execution closure (new scripts/tests, remediation and imported historical
modules, GUM prepared files/manifest, model config/weights, tokenizer files,
requirements lock, Python/Torch/Transformers/CUDA metadata), installs the final
immutable raw config, and only then constructs Stage A. A distinct
GPU replay CLI reads only the frozen GUM strata and raw protocol, writes
create-once arrays/manifests in the new run root, calls the reviewed Stage-B
builder, and terminates eligible/ineligible without changing the config. The
launcher parent acquires the **actual existing UUID flock nonblocking** before
tmux. It rechecks idleness while holding that FD, then forks a minimal lease
broker inheriting the FD; tmux starts the worker with a duplicate of the same
locked open-file description, and both retain it until worker exit. Thus either
process may crash without releasing the lease from the other live process; a
reservation file never substitutes for the flock. Its create-once
lock-acquired record binds broker PID/start-tick, FD target, GPU UUID, nonce, and
config digest. The tmux worker refuses model load unless that broker and record
validate, then registers its pane PID/start-tick with the broker. It runs under
`timeout --signal=TERM --kill-after=60s 6h` with
`CUDA_VISIBLE_DEVICES=<selected GPU UUID>` and, before model load, requires
`torch.cuda.device_count()==1` and exact canonical equality between
`torch.cuda.get_device_properties(0).uuid` and that UUID. Tmux launches
`timeout` as a new process-group leader; the handoff records pane/timeout PID,
Python worker PID, both start ticks, and PGID. The broker watchdog binds that
PGID and exits only after the whole group is gone. Failure cleanup sends TERM
then KILL to the entire PGID and verifies the timeout and Python PIDs are gone;
tests cover broker, pane, timeout, and Python-worker death independently. A
timeout, OOM, exception, CUDA-UUID mismatch, or lease/handoff loss writes a
create-once `technical_failure`/`not_run` terminal and cannot build Stage B;
`ineligible` is reserved for a complete valid replay whose entire frozen ladder
fails. The launcher
creates the run/session and performs one immediate handoff observation. It never
polls for a workload heartbeat or result.

**Alternative rejected:** adapt measurement-v2.4 in place. Its source, roles,
review key, and config path are hardcoded, and editing it would corrupt a frozen
negative result's provenance.

**Alternative rejected:** reuse an outcome-exposed UD source (ESLSpok, GENTLE,
GUMReddit, CHILDES/CTeTex, Spanish AnCora, or the multilingual relational
sources). That would not satisfy a new independent evidence attempt.

**Simpler alternative retained:** this turn launches calibration only. It does
not duplicate the full confirmation pipeline before Stage B demonstrates that
measurement is numerically sound.

## Sequencing and authorization gates

1. Review this plan adversarially; implementation is forbidden until SHIP.
2. Capture baseline git/tmux/GPU/process state and the baseline-HEAD `AMALGUM`
   search. Provision a one-use Ed25519 prescore-review authority in an independent
   reviewer context and freeze its public-key fingerprint before implementation.
3. Resolve/pin/download AMALGUM and build source/split/support/bootstrap
   candidates plus the accessible-history overlap attestation; preserve the sealed
   final unopened and record its overlap as unknown unless a pre-existing
   blind-safe commitment is found. Freeze scientific labels, tasks, endpoints, thresholds, ladder,
   and checkpoint identities, but do not yet claim an execution freeze.
4. Implement deterministic preparation, Stage-A finalizer, replay, launcher, and
   tests. Run CPU-only tests/static checks and a no-model synthetic smoke.
5. Inventory the complete transitive code/data/model/tokenizer/environment
   closure; finalize immutable raw config bytes; rebuild Stage A twice from those
   bytes and require identical output.
6. Obtain an independent `/adversarial` review of the complete prescore diff and
   artifacts. Fix/re-review until SHIP. Store the exact verdict and digest.
7. The independent reviewer signs a canonical envelope binding the SHIP
   transcript, raw config, Stage A, source/partition, scripts, environment,
   checkpoint manifests, a unique nonce, calibration-only scope, single-use
   semantics, and a 24-hour expiry. The launcher verifies the pre-frozen public
   fingerprint and Ed25519 signature and consumes the nonce create-once. The
   current user's explicit instruction to run the reviewed experiment is the
   separate operator authorization; its exact quoted text and digest are bound
   in the envelope. No coordinator-generated signature substitutes for either.
8. Query `nvidia-smi`; choose a GPU with no compute processes, <1024 MiB used,
   and instantaneous utilization <=5%, ordered by `(memory_used, utilization,
   UUID)`. Acquire the existing UUID flock nonblocking in the launcher parent,
   re-query those three conditions while holding it, and abort/release on drift.
   Duplicate the same locked FD into only the bound broker and tmux worker and
   launch the calibration replay under the frozen UUID binding and six-hour
   timeout. The one-shot handoff must verify the broker's lock-acquired artifact,
   live broker PID/start-tick and FD target, and live tmux pane/config/nonce
   lineage.
9. After `tmux new-session -d`, make exactly one non-sleeping observation:
   session/pane exists, pane/worker PIDs, start ticks, and PGID are live, broker
   and worker own the actual flock,
   and launch/config/nonce lineage files exist. If any item is absent, kill the
   newly created tmux session and broker, kill the whole PGID, verify all
   recorded PIDs are gone,
   publish a create-once launch-failure record, and return failure; no child is
   left able to acquire a lock later. On success, return immediately with
   session/run/log paths; do not wait for a heartbeat or Stage B. Tests cover
   contention, delayed child, nonblocking-flock failure, missing handoff, and
   cleanup of both pane and broker.
10. In a later turn, independently inspect Stage B, authorize and run the locked
    discovery/calibration-only scientific baseline gate, and stop if it fails.
    Only a signed passing comparator freeze can authorize AMALGUM confirmation;
    then implement/review/run C1 G1 and C2 G2, and only afterward build Stage C.

## Milestones

- [ ] **M0 — Plan and protected baseline.** Plan receives adversarial SHIP;
  baseline captures dirty paths and protected historical hashes.
- [ ] **M1 — Source and static freeze.** AMALGUM revision/files/partition/support,
  calibration strata/ladder, g4/g5/g6 lineages, families/tasks/thresholds, and
  complete endpoint registries are exact and digest-bound.
- [ ] **M2 — Stage A and harness.** Stage A is ready; replay/launcher are
  config-bound, create-once, offline, deterministic, and synthetic-smoke tested.
- [ ] **M3 — External prescore gate.** Independent adversarial review of the
  complete prescore bytes returns SHIP and the calibration-only authorization
  binds that exact review/config/code/artifact set.
- [ ] **M4 — Live calibration handoff.** An idle locked GPU runs the replay in a
  new tmux session, handoff lineage is verified, and this agent does not await a
  result.

## Definition of done

- [ ] No historical protected artifact changed and no historical run root was
  reused.
- [ ] Source selection is independent of previous MSAE neural outcomes,
  document-disjoint, revision/file/split hashed, and label-only support passes
  without source/task substitution.
- [ ] Three genuinely distinct candidate training lineages and the separate g7
  control are correctly classified and rehashed.
- [ ] Every requested localization, collateral, counterfactual,
  reproducibility, and baseline endpoint is prospectively registered, with all
  task/gate/threshold semantics unambiguous.
- [ ] Stage A is ready; Stage B cannot exist before replay; Stage C cannot exist
  before an eligible B plus real confirmation evidence.
- [ ] Tests cover config tampering, data/checkpoint hash drift, role mixing,
  missing/malformed source labels, exact/near overlap, unsupported tasks, replay
  array and provenance failures, GPU non-idleness, and existing session/run
  roots. Authorization tests separately reject wrong reviewer key/fingerprint,
  altered operator text/digest, expired envelopes, wrong confirmation/training
  scope, absent/duplicate nonce, nonce replay, and every signed-field mutation.
- [ ] The final prescore bytes receive independent adversarial SHIP before any
  model, checkpoint, GPU job, or tmux session is launched.
- [ ] The launched replay is in tmux on a verified idle UUID-locked GPU with a
  new run directory and live handoff record; the response gives monitoring
  commands but contains no claimed replay result.

## Risks and one-way doors

- Opening AMALGUM content consumes it as a future fresh source. The pinned
  filename-only selection rule and exposure record make that one-way door
  auditable.
- Machine annotation can inflate apparent decodability or share GUM parser
  biases. Report it as a limitation and require counterfactual/collateral gates;
  do not call it human-gold semantics.
- AMALGUM web text may overlap Pythia pretraining. This study tests held-out
  experimental documents, not training-data novelty.
- Three old K2 seeds support only checkpoint-stability statements. A learned
  model generalization claim still requires the five fresh seeds in `TODO.md`.
- Entity annotation parsing is a high-risk source adapter. Malformed or weak
  support blocks rather than downgrades the primary family after inspection.
- Source download, signed authorization, and a GPU launch are one-way actions.
  Each occurs only after the preceding digest/review gate.

## Verification plan

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPYCACHEPREFIX=/tmp/msae-independent-pycache .venv-atlas/bin/python -m pytest -q -p no:cacheprovider tests/test_msae_measurement_remediation_v1.py tests/test_msae_independent_measurement_v1.py`
- `PYTHONPYCACHEPREFIX=/tmp/msae-independent-pycache .venv-atlas/bin/python -m py_compile scripts/msae_measurement_remediation_v1.py scripts/msae_independent_measurement_v1.py scripts/run_msae_independent_calibration_v1.py`
- `bash -n scripts/launch_msae_independent_calibration_v1.sh`
- Validate every canonical JSON hash, source/checkpoint physical hash, exact
  registry, split-disjointness, and Stage-A aggregate twice from clean processes.
- Synthetic CPU smoke only before prescore review; monkeypatch model/process/
  network surfaces in unit tests.
- Compare protected baseline before authorization and immediately before launch.
- `/adversarial docs/rfc-msae-independent-measurement-v1.md` before
  implementation; `/adversarial` on the exact prescore diff/artifacts before
  model/GPU/tmux launch.
- At launch, capture `nvidia-smi` inventory, compute processes, GPU UUID,
  exclusive lock, tmux list, process start ticks, config/authorization/script
  digests, then make the one immediate session/pane PID/start-tick/lineage
  observation. No heartbeat is awaited or required, and no result is polled.
