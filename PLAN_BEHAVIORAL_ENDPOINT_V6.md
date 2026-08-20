# PLAN — Behavioral endpoint comparison v6

## Goal

Run a separately versioned, task-only study comparing two candidate behavioral endpoints—robust
key-value retrieval and controlled syntactic agreement—before any representation-method benchmark.
Use only opened v5 development documents for endpoint development. Permit fresh confirmation model
forwards only for an endpoint that passes every registered development template in at least two
pinned checkpoints.

## Non-goals

- Do not modify, rescore, continue, or reinterpret v5.
- Do not open v5 confirmation rows.
- Do not lower v5 thresholds, select only its favorable template, or reuse its namespace.
- Do not train or evaluate SAEs, K2, projections, supervised dictionaries, or any representation
  method.
- Do not automatically launch a method benchmark even if an endpoint passes.

## Preservation, checkpoints, and sources

- The first operation—before analysis or preparation—is a complete size/SHA manifest of every v5
  config, freeze, plan, code, test, review, prepared, result, and provenance file. Verify it after
  every phase and at launch/aggregation.
- Bind the exact v5 checkpoint panel without deletion or substitution:
  - `gpt2` revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`, family `gpt2`, float32, batch 16;
  - `EleutherAI/pythia-160m-deduped` revision `582159a2dfe3e712a8d47ae83dec95ae3bde8e7e`, family `pythia`, float32, batch 16;
  - `google/gemma-2-2b` revision `c5ebcd40d208330abc697524c919956e692655cf`, family `gemma`, float32, batch 4.
  Tokenizers use the same name/revision and the content-hashed v5 cache attestation is imported.
- Development fillers are a frozen dev-only projection of the 192 opened v5 development documents
  per source. The projector copies only registered line ranges 1–192 and 385–576 from the exact-hash
  v5 rows file and refuses to deserialize other lines. It verifies each selected row says
  `split=development`. V5 confirmation rows remain sealed; only their already-stored content/window
  hash fields are streamed into a membership set without materializing prompts, labels, IDs, or text. Dataset IDs are
  source-qualified; cross-source exclusion uses only content/window hashes, while within-source row
  indices are unique by construction.
- Confirmation fillers use two newly pinned corpora:
  - DBpedia: dataset `fancyzhx/dbpedia_14`, revision
    `9abd46cf7fc8b4c64290f26993c540b92aa145ac`, configuration `dbpedia_14`, split `train`, fields
    `title+content`;
  - IMDb: dataset `stanfordnlp/imdb`, revision
    `e6281661ce1c48d982bc483cf8a173c1bbeb5d31`, configuration `plain_text`, split `train`, field
    `text`.
- Use global seed `20260811` and process DBpedia before IMDb. Define words by regex `\S+`; join
  DBpedia title and content with one newline before whitespace normalization. Hash complete normalized
  content, require at least 32 words, choose a 32-word window at
  `stable_hash(seed,dataset,split,row_index,"window") mod (len(words)-32+1)`, where
  `stable_hash` is the full unsigned 64-bit value of the first eight bytes, interpreted little-endian (with no 32-bit truncation), of SHA-256 over the UTF-8 string
  `"seed|dataset|split|row_index|window"`, and sort candidates by
  SHA-256 of `(seed,dataset,split,row_index)`, and take the first 192 eligible documents per source. Reject exact
  ID/content/window matches against enumerated v3, v4, v5, v6-development, other-source, and earlier
  selected hashes. Text hashes are SHA-256 over lowercased, whitespace-normalized UTF-8 text, exactly
  matching v5's `norm()`/`text_hash()` convention. Freeze every accepted/rejected record—including minimum-length exclusions—source fingerprint, and count before model
  inference. Each confirmation document appears once per endpoint and source (the endpoints share
  blocks but are analyzed separately).
- Development and confirmation use disjoint prompt templates, key sets, agreement vocabularies, and
  verb assignments. Preparation is label/tokenizer-only and requires offline mode after download.

## Endpoint A — improved retrieval

- Four development key sets, each with four query keys. Use four ordinary answer values and a fifth
  reserved null candidate. Six development templates are independent of three confirmation templates.
- Every prompt with bindings contains a complete four-key/four-value bijection. Within each
  source/template, cross four key sets × four queried keys × four target values = 64 components. The
  matching map binds queried key `q` to registered target `v`.
- Before constructing any retrieval condition, replace an exact case-insensitive occurrence of any
  stage-registered key or candidate in the natural filler with the safe one-token word `neutral`; use
  that same sanitized filler in all seven conditions and freeze the replacement count. This design-time
  nuisance sanitation is independent of model outputs and must preserve condition lengths for all three
  tokenizers.
- Three query-counterfactual maps rotate `q` through each wrong ordinary value and rotate the remaining
  mappings bijectively; their correct candidates are those newly bound values. Two registered sham
  maps keep `q→v` fixed while deranging only the other three key/value records. A genuine no-binding
  prompt uses a template-specific registered 17- or 18-word `unavailable` scaffold (chosen prospectively
  to equal the binding table's 18 in-context tokens for every tokenizer) and the safe query placeholder `item`; the
  complete prompt contains no registered key and none of all five candidate strings, including the null
  candidate; its correct candidate is null. This is exhaustively asserted on full prompt strings, not
  merely on the substituted table span.
- The common candidate set is four ordinary values plus null. For any condition `c`, define
  `C(c)=logit(correct(c))-logmeanexp(logits(other four candidates))` and top-1 margin
  `M(c)=logit(correct(c))-max(logits(other four candidates))`. Also define original-target
  advantage `T_v(c)=logit(v)-logmeanexp(logits(other four candidates))`.
- A component is directionally correct only if `M(c)>0` (strict correct top-1) for match, all three
  counterfactuals, both shams, and no-binding; `C` remains the graded statistic. Define primary
  `F=min_c[T_v(match)-T_v(c)]` over the three query-counterfactuals and no-binding. Thus match must beat
  every alternate or missing-query state while each state must itself predict its semantically correct
  candidate.
- Nuisance is `N=max_s |T_v(sham_s)-T_v(match)|` over the two other-record derangements. Specificity
  ratio is `R=N/max(F,1e-8)` only after absolute directional correctness and `F>0.25`.
- The 192 source documents are deterministically assigned one key set retained across all template
  appearances and exactly two of six templates; each template has 16 documents per set. Freeze all
  map tables and key×value×role×template incidence.
- Freeze full prompt strings. The builder requires all seven condition prompts to have identical token
  length and all five candidates to be one token for every checkpoint tokenizer; otherwise preparation
  fails before freeze.

## Endpoint B — controlled agreement

- Four noun vocabulary sets, each with four reciprocal singular/plural lemma pairs. Four independent
  one-token verb pairs rotate across six development construction templates, so verb pair is not
  identified with template. Three new construction templates and reserved noun/verb sets are held for
  confirmation.
- Per source/template, cross four vocab sets × four subject-lemma slots × two subject numbers × two
  attractor numbers = 64 components. Within each template/set, a deterministic cyclic Latin schedule
  assigns verb `subject + 2*subject_number + attractor_number + template + set + stage_offset (mod 4)`;
  nonzero cyclic offsets assign attractor and lexical-sham lemmas. This rotates every lemma equally
  through subject, attractor, and lexical-sham roles and balances verbs exactly within template/set and
  across subject lemma, subject number, and attractor number. Freeze lemma×role×number×template×verb incidence and require
  the registered main-effects matrix rank/tolerance.
- Frozen prompt schema is `[32-word filler] Sentence: <construction ending immediately before verb>`.
  Conditions are:
  1. original subject and attractor;
  2. reciprocal subject-number flip of the same lemma;
  3. attractor-number flip of the same attractor lemma at the identical token distance from the verb;
  4. same-number lexical substitution of both subject and attractor using their registered rotated
     lemmas.
- Let `A(c)=logit(originally grammatical verb)-logit(originally ungrammatical verb)`.
  A component is directionally correct only if `A(original)>0`, `A(subject flip)<0`,
  `A(attractor flip)>0`, and `A(lexical substitution)>0`. Primary
  `F=A(original)-A(subject flip)` and nuisance
  `N=max(|A(original)-A(attractor flip)|,|A(original)-A(lexical substitution)|)`; ratio
  `R=N/max(F,1e-8)` only after absolute directional correctness and `F>0.25`.
- Reciprocal singular/plural rows, exact separators, token distance, word order, and all prompt strings
  are frozen. Every condition must have identical prompt length, and both verb forms must be one token,
  for all checkpoint tokenizers.

## Prospective gates and crossed hierarchy

For every endpoint/checkpoint/source/template development cell (64 components):

- endpoint-specific absolute directional correctness plus signed `F > 0.25`;
- at least 14/16 eligible in every registered set and therefore at least 56/64 overall;
- 500 deterministic hierarchical bootstrap draws;
- ratio point estimate `<=0.20` and percentile upper bound `<0.30`.

Cell draws resample the four registered key/vocabulary sets and document clusters within sampled
sets. A promotion-relevant endpoint hierarchy is additionally required for each checkpoint/source:
for every draw, resample templates and sets with replacement and sample the 192 unique document IDs
once; use the resulting document multiplicity for every appearance of that document across templates.
For crossed draws, sample one multinomial multiplicity vector over templates, one over sets, and one
over the 192 documents; a component weight is the product of its template, fixed-set, and shared-document
multiplicities. The overall point is the equal-template/equal-set mean. If a sampled set/template
stratum has zero eligible weighted components, assign that draw `+infinity`; retain all draws and compute the 97.5th percentile as the frozen
`higher` order statistic at zero-based index `ceil(0.975*n)-1`. Thus 13 or more infinite values among
500 draws yield an infinite upper bound; strict JSON converts it to the string `"INFINITY"` and the
cell fails. Its ratio point and upper bound must satisfy the same 0.20/0.30 limits, and every template
cell must pass. Seeds derive from the frozen global seed,
endpoint, checkpoint, source, template (or `overall`), and stage. Missing/low-effect components count
against support and never enter ratio denominators.

A checkpoint is development-eligible for an endpoint only if all 12 cells and both source-level
hierarchies pass. An endpoint opens confirmation only if at least two distinct families are eligible.
Other endpoints and ineligible checkpoints remain blocked before model/tokenizer loading.

Confirmation uses three new templates, four reserved set families, 64 components per template, and
two fresh corpora with unchanged cell and hierarchy gates. A final endpoint pass requires at least two
families to pass every confirmation source/template and both confirmation hierarchies. Passing only
authorizes a separately frozen future method study.

## Frozen outcome table

- No endpoint has at least two all-template development families: classify `BOTH_ENDPOINTS_STOP` or
  the corresponding single-endpoint failure; open no confirmation.
- One or more templates pass but an endpoint lacks all-template support: classify that endpoint
  `TEMPLATE_CONDITIONED`; open no confirmation for it.
- Retrieval fails and agreement passes: only agreement confirmation workers may load models.
- Agreement fails and retrieval passes: only retrieval confirmation workers may load models.
- Both endpoints pass: confirm both; do not rank or select one post hoc.
- Only one family passes all development templates: `INSUFFICIENT_MODEL_REPLICATION`; no confirmation.
- Families can differ by endpoint, but each endpoint independently needs two development and then two
  confirmation families.
- After confirmation, future methods may use only endpoints independently passing confirmation.
  Retrieval-only, agreement-only, both-pass, and both-fail states are all reported explicitly.

## Execution and terminals

- Six development workers run concurrently on six distinct free physical GPU UUIDs: one fixed
  endpoint/checkpoint assignment per UUID. The matching confirmation waiter reuses that assignment
  only after its development worker exits; the two endpoint/checkpoint queues never share a UUID.
- Launcher requires six GPUs below 4 GiB, rejects UUID collisions, records assignments, and workers
  verify exactly one visible UUID. Two CPU development aggregators and one final aggregator own gates.
- Atomic terminals distinguish worker `COMPLETE`, upstream `BLOCKED`, technical `FAILED`, scientific
  `PASS`/`FAIL`, `INSUFFICIENT_MODEL_REPLICATION`, `TEMPLATE_CONDITIONED`, and `TIMEOUT`. Every waiter observes failure/timeout terminals and has a
  frozen timeout. Launcher handoff accepts each expected session only if it remains live or has already
  written its expected clean `COMPLETE`/`BLOCKED`/scientific result terminal; fast failures and timeouts
  do not count as a clean handoff. One-shot output/provenance roots abort before inference if already present.
- Review sequence: review/fix mutable candidate; store that SHIP review; freeze once including it;
  separately verify the immutable freeze and store the authorization review outside the inventory. A
  post-freeze `BLOCK` permanently invalidates that candidate; corrections require a new versioned
  namespace, candidate review, and freeze.

## Analysis-only v5 report

The report binds exact v5 metric/completion/gate/freeze hashes and loads no model. It reports, for
every checkpoint×source×template: eligible count, full-effect and ratio mean/median/quantiles/tails,
sham dispersion, key×answer strata, explicit template×source interactions, and a threshold-specific
failure decomposition into weak effects, large sham dispersion, or both. It is descriptive, cannot
rescore v5, and is created only after the initial preservation manifest.

## Milestones

- [ ] **M1 preservation and analysis:** exact v5 preservation manifest; analysis-only template report
  with template/key/answer/source distributions and failure decomposition; no v5 rescoring.
- [ ] **M2 prospective panels:** pinned source cache, exact development/confirmation rows, prompt strings, incidence,
  tokenizer, exclusion, source-schema, and deterministic double-prepare audits.
- [ ] **M3 implementation:** endpoint-only workers, per-endpoint development gates, confirmation
  firewalls, final decision, atomic terminals, tests, and tmux launcher.
- [ ] **M4 adversarial review:** fix mutable-candidate findings before freeze; a post-freeze `BLOCK`
  invalidates the candidate and requires a newly versioned namespace.
- [ ] **M5 launch:** allocate free physical GPUs by UUID, launch once in tmux, and return after
  liveness/initial-log verification without waiting for outcomes.

## Definition of done

- [ ] Every preserved v5 file retains its pre-v6 size/hash; v5 confirmation contains only the original
  `BLOCKED.json` files and no metrics.
- [ ] The template report imports exact development metric hashes, loads no model, and cannot alter
  v5 or v6 decisions.
- [ ] Development rows use only v5 development document IDs; confirmation has zero predecessor,
  development, or cross-source ID/content/window overlap.
- [ ] Every endpoint/source/template has exactly 64 components and frozen balance tables.
- [ ] Retrieval keys/values and agreement nouns/verbs satisfy all-tokenizer length and one-token gates.
- [ ] Gate estimators, hierarchy, strict inequalities, seeds, family uniqueness, and model-specific
  confirmation authorization are frozen and tested.
- [ ] Confirmation cannot load a model until its endpoint has a two-family development PASS and that
  checkpoint passes all of its own endpoint cells.
- [ ] No training or representation-method path exists.
- [ ] Config, code, tests, rows, source fingerprints, cache content hashes, reviews, preservation, and
  deterministic preparation are bound by a one-shot freeze.
- [ ] Compile, tests, launcher syntax, cache/preflight, freeze verification, and `/adversarial` pass.
- [ ] tmux launch records and enforces physical GPU UUIDs; handoff accepts live sessions or validated
  clean terminals for fast stages.

## Risks and alternatives

- Strict all-template gates can stop both endpoints; that is intentional evidence of endpoint
  fragility, not permission to select a favorable template.
- Agreement may be easier than retrieval because its target contrast is linguistically constrained;
  this is a comparison of endpoint validity, not evidence that syntax is more modular.
- A simpler single-template retry was rejected because v5 demonstrated template dependence.
- A method benchmark was rejected because no robust naturalistic endpoint is currently eligible.
- Opening confirmation is the only one-way scientific door and is protected by endpoint-specific,
  model-specific, two-family development barriers.

## Verification plan

- Plan and frozen-candidate `/adversarial` reviews.
- `python -m py_compile` for analysis and assay scripts.
- `pytest -q tests/test_behavioral_endpoint_v6.py`.
- `bash -n scripts/launch_behavioral_endpoint_v6_tmux.sh`.
- Offline deterministic double preparation with byte-identical manifests.
- Exhaustive incidence, tokenization, disjointness, family, estimator, cache-mutation, UUID-mismatch,
  confirmation-no-load, timeout, and forbidden-path tests.
- One-shot preflight/freeze verification immediately before tmux launch.
