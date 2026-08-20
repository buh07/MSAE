# PLAN — Attempt 13 Fresh Relational/Sequential Measurement Study

## Goal

Create and execute one new, one-shot, no-neural-training scientific measurement study that asks two
independent questions:

1. **Primary relational syntax:** do true child–head representations improve recovery of dependency
   depth, coarse dependency relation, and signed head distance over child-only, a matched sham head,
   and a matched sequential-distance control?
2. **Secondary sequential/context versus lexical:** does the previously strongest frozen linear
   organization recover sequential/boundary information in one subspace and lexical information in
   its complement while passing controlled functional-capture tests?

The study will use EWT and GUM only for development calibration and two sources with no known prior
label-dependent endpoint scoring—UD English GENTLE and UD English CTeTex—for the one-shot
scientific run. Both sources have prior technical-QA exposure. They will therefore be described only
as **endpoint-outcome-naive**, never broadly fresh, text-unseen, inference-unseen, or independently
confirmatory. A project-wide exposure and content-overlap firewall must substantiate that narrower
classification before authorization.

## Non-goals

- Do not modify, retry, rescore, reinterpret, or promote Attempt 12.
- Do not remove its two low-norm rows or alter any Attempt-12 threshold or capture role.
- Do not train an SAE, supervised decomposition, private/private/shared model, or any neural model.
- Do not use a favorable submetric to authorize training automatically.
- Do not claim transformer-wide generality, model-level replication, or independent confirmation
  beyond the pinned model/layer and the two prespecified scientific sources.
- Do not call GENTLE or CTeTex technically untouched; their previous technical-only exposure remains
  part of the lineage.

## Constraints

- Attempt-12 terminal and result trees must match frozen recursive inventories before and after every
  stage.
- New result/run namespaces must be absent before authorization and create-once afterward.
- All raw sources, prepared children, implementation files, thresholds, task definitions, exclusion
  rules, control construction, capture roles, GPU UUID, and decision logic must be hash-bound before
  any fresh model forward.
- GENTLE and CTeTex must each provide at least 20 genuine upstream `newdoc id` groups; retained task
  classes must occur in at least 10 documents per source.
- Each task and intervention must cap rows per document. Label-only bootstrap coverage must have at
  least 490/500 finite draws before authorization.
- The scientific run is one-shot and terminal. A failed or completed opening cannot be retried under
  any namespace or successor authorization sharing the frozen study key.
- Exact cached replay, signatures, row order, array dtype/shape/finiteness, and source hashes are
  checked independently of scientific eligibility.
- Numerical/runtime eligibility is endpoint-specific. Relation-delta ineligibility cannot erase the
  secondary sequential/context module.
- Signed head distance remains mandatory in the primary module even though it failed previously.
- All neural/representation-training permissions remain false. Ephemeral deterministic linear ridge
  probes are explicitly authorized as score estimators: they may fit only on the prespecified fit
  source, may be used only for the paired transfer score, and their fitted weights must not be
  persisted. A passing measurement can nominate a later comparison but cannot launch it.
- Before the first scientific forward, the runner must atomically create a crash-durable
  `SCIENTIFIC_OPENING_CONSUMED.json` in a registry outside the Attempt-13 namespace. The registry key is
  derived only from the source hashes, model revision, layer, and endpoint protocol—never the
  authorization identity. The authorization/review hashes are payload lineage. Authorization creation
  and execution both reject an existing study key. Creation uses `O_CREAT|O_EXCL`, then file and parent-
  directory `fsync`; its existence prohibits a second forward under every namespace and successor
  authorization. A consumed run without a terminal is still an opened terminal outcome.

## Codebase and design grounding

- `/query-codebase refs relation_rows` found the prepared relation builder at
  `scripts/atlas_discovery_v3_3.py:1504-1550` and the analyzer loader at
  `scripts/analyze_atlas_discovery_v3_3.py:99`.
- `/query-codebase refs singular_floor` found the global any-row invalidation at
  `scripts/analyze_atlas_discovery_v3_3.py:500-507`.
- The existing matched sham uses side, broad-distance, and coarse-head-UPOS strata at
  `scripts/atlas_discovery_v3_3.py:758-830`.
- The prior relational comparison uses child, true head delta, and sham delta at
  `scripts/analyze_atlas_discovery_v3_3.py:181-197`.
- The design ledger has no MSAE-specific entry for this fork. DES-0002 only establishes the
  operator/new-maintainer audience, so the checked-in protocol, executable entrypoints, and
  verification commands must be self-contained.

## Frozen scientific design

### Sources and freshness

- **GENTLE:** pinned file
  `data/atlas_rope_v4_raw/UD_English-GENTLE/fd7a1bfc82896e362c66f59492b5525940f52fa7/en_gentle-ud-test.conllu`.
- **CTETEX:** pinned file
  `data/atlas_rope_v7_attempt11_raw/UD_English-CTeTex/3d2bda424dcdedb8889aeec9f81ee6401994f7f2/en_ctetex-ud-test.conllu`.
- Label-only reconnaissance currently shows 26 GENTLE documents and 196 CTeTex documents. The
  builder must independently reproduce these counts and fail closed on drift.
- Before either source is authorized, a complete recursive repository-root inventory will be
  hash-bound. It includes every regular file below `analysis`, `configs`, `data`, `docs`, `experiments`,
  `pilot_outputs`, `pilot_runs`, `prereg`, `reports`, `results`, `scripts`, and `tests`, plus all
  top-level plans, analyses, patches, snapshots, and text artifacts. Only `.git`, virtual environments,
  tool caches, and the not-yet-created Attempt-13 run/result trees are excluded by an exact frozen
  allowlist. Every included file is content-hashed; unreadable or unclassified files are fatal audit
  gaps.
  The exposure audit searches file contents, manifests, source hashes, row IDs, and source aliases for
  any prior GENTLE/CTeTex use and classifies every hit as technical QA, label-only preparation, or
  label-dependent endpoint scoring. Any unexplained hit or any prior label-dependent endpoint score
  makes the affected source ineligible.
- The audit also hashes normalized document content, sentence content, UD token sequences, and selected
  subtoken-ID sequences for EWT, GUM, GENTLE, CTeTex, and every recoverable prior opened raw/prepared
  source. A sentence collision is equality of any one of three SHA-256 signatures: (a) UTF-8 bytes of
  Python-`str.lower` FORM strings joined by one ASCII space after whitespace collapse; (b) canonical
  compact UTF-8 JSON of the original-case UD FORM sequence; or (c) canonical compact JSON of selected
  subtoken IDs from the pinned tokenizer with `is_split_into_words=True` and no special tokens. Only
  integer-ID CoNLL-U syntactic-word rows count; multiword ranges and empty nodes do not, while
  punctuation does. Historical copies with the same triple of hashes count as one distinct collision.
- Frozen precedence is: prior label-dependent scoring of the same full source makes the source
  ineligible; exact full-document overlap removes the document; any collided sentence with at least
  eight UD words removes the document; at least two distinct collided sentence triples in one document
  removes the document; otherwise the one isolated shorter collision is removed from the eligible
  corpus before **every** task, relation, donor, control, intervention, prefix, adjacency, and model-unit
  constructor. Context pairs may not bridge the removed sentence. A final scan rejects any prepared
  input containing an excluded token/subtoken sequence. The rule is applied symmetrically to both sides
  of a GENTLE–CTeTex collision and identically to prior label-dependent sources. If provenance cannot
  identify a collision, the affected source is ineligible. Known same-source technical copies are
  recorded, not mistaken for scientific independence.
- This refinement is explicitly `prescore-support-amended, endpoint-outcome-blind`, not independent
  confirmation: the first whole-document version left 19 GENTLE documents before any model inference.
  The complete collision census, old/new dispositions, failed snapshot, and amendment rationale must be
  hash-bound in the final freeze and retained in every claim limitation.
- The final exposure ledger will say only that GENTLE and CTeTex are endpoint-outcome-naive if this
  firewall passes. Their earlier technical exposure remains a mandatory limitation.

The exposure/freezing chain has a non-self-referential, frozen order:

1. At the pre-implementation cutoff, write `historical_exposure_manifest.payload.json` over the
   complete historical tree. Its exact allowlist excludes only its own canonical payload/envelope paths
   and an enumerated list of Attempt-13 candidate/output paths. A detached envelope hashes and signs the
   payload. This artifact establishes prior exposure, not the final executable candidate.
2. After implementation and label-only preparation, write `final_freeze_manifest.payload.json`. It
   hashes the historical payload/envelope and every Attempt-13 plan, calibration, implementation, test,
   config, prepared-data, and preflight artifact. It excludes only its own canonical payload/envelope
   paths and the not-yet-created exact review, authorization, consumed-record, run, terminal, and result
   paths. Its detached envelope hashes and signs the payload.
3. `/adversarial` reviews the exact final-freeze digest. Authorization is created last and binds the
   final-freeze and review hashes. Immediately before authorization and again before opening, the runner
   reconciles every repository file against the historical manifest, final candidate, and exact
   late-stage envelope allowlist; any unclassified or modified file is fatal. Thus neither manifest
   attempts to hash itself, while no late-created artifact can silently escape classification.

### Relation-delta rule calibrated on opened EWT/GUM

For a pair of cached float32 representations `h` and `c`, convert both to float64 for the reduction
and define:

`relative_delta_norm = ||h - c||_2 / max(||h||_2, ||c||_2, 1e-12)`.

- Frozen informative threshold: `relative_delta_norm > 1e-4`.
- A relation row is direction-informative only when the true, sham, and sequential-offset-control
  deltas all clear the threshold.
- Below-threshold rows are non-informative **only for the relational delta/capture endpoint**. They
  remain available to separately defined token-level tasks and are always counted and reported.
- For each source/variant, the denominator is exactly the frozen post-support,
  post-control-matching/pre-norm relation-row inventory. A row whose value is equal to or below `1e-4`
  is non-informative. The union exclusion used for relational scoring contains each row once if any of
  the three variants is non-informative; the three variant rates and union rate are reported separately.
- Maximum acceptable non-informative rate: `0.001` (0.1%) per source and per control variant **and**
  for the union. No denominator is recomputed after norm inspection.
- Frozen evaluation order is: control matching → prescore support → norm audit → per-variant and
  union cap decisions → union exclusion → post-exclusion task/class/document/component support
  recheck, with no replacement or backfill. If any variant or the union exceeds its cap, or the
  post-exclusion support recheck fails, the relational module is ineligible for directions testing that
  source; the sequential/context module remains independently eligible.
- Opened EWT/GUM calibration must be emitted and hash-bound before freeze, including counts, exact
  denominators, quantiles, and the selection rationale. The rationale is frozen prospectively: `1e-4`
  classifies numerically near-identical pairs rather than ordinary relational changes, and `0.001`
  limits outcome-dependent row loss to one per thousand while covering the observed opened-development
  true-pair rate. No GENTLE/CTeTex activation may inform either number.

### Relational controls

Every retained row contains:

- the child representation;
- the true head delta;
- the existing matched sham delta: same sentence, same side, near/far distance stratum, coarse head
  UPOS, then closest distance;
- a sequential-offset control drawn from a different document in the **same source**: a donor pair
  whose exact signed UD-token distance, exact signed selected-subtoken-position offset, child coarse
  UPOS, candidate/head coarse UPOS, sentence-length bin, and deterministic within-source fold match the
  true relation. The donor candidate and donor child must have no dependency edge in either direction
  and neither may be an ancestor of the other. The scored control feature is the original target-child
  representation concatenated with the donor-candidate-minus-donor-child delta.

Rows without all controls are excluded label-only before scoring. Matching is frozen and deterministic:
within each source and pre-existing document fold, first construct a maximum-cardinality disjoint
matching of document pairs that share at least one exact eligible stratum; then match token pairs in
both directions inside each document pair. Each donor token-pair is used at most once. Each target
document and donor document contributes at most 24 matched rows, with no fallback or relaxed stratum.
Each relation row stores source-local target/donor document foreign keys and its document-pair component;
  the whole component receives one fold and is the resampling unit for every true-versus-control
  interval. All three paired relational contrasts use the identical deterministic component
  multiplicities in each draw; this endpoint is called the **document-pair-component bootstrap**, not a
  legacy target-document bootstrap.
After matching and again after norm-union exclusion, every source must have at least 20 target documents,
20 donor documents, 10 disjoint document-pair components, and 10 documents containing every retained
task class. The builder enforces these rules and fails the affected endpoint closed when matching is
infeasible. Because both UD and selected-subtoken offsets are exactly matched, any true-head advantage
is not attributable to those measured sequential offsets; unmeasured sequential/context confounding
remains a stated limitation.

For every one of dependency depth, coarse dependency relation, and signed head distance, and in both
transfer directions, the primary endpoint requires:

- task measurability and 490/500 finite document-pair-component-bootstrap draws;
- true-minus-child point margin at least `0.02` and lower confidence bound above zero;
- true-minus-matched-sham point margin at least `0.02` and lower confidence bound above zero;
- true-minus-distance-control point margin at least `0.02` and lower confidence bound above zero.

All three tasks must pass. Missingness is reported per task and cannot be converted to failure in the
secondary module.

### Secondary sequential/context module

The frozen projection is built from the fit source’s start-distance and relative-quartile probe
weights plus relative-gap and context-delta bases. Its complement is the lexical side. Ranks 8, 16,
and 32 are diagnostic; rank 16 is primary.

Construct-specific support after frozen overlap removal and matching is:

- relative gap: at least 20 target documents/components per source; donor support is `not_applicable`;
- context factorial and proper-noun substitution: at least 12 target documents, 12 donor documents,
  and 12 disjoint target–donor components per source (24 unique genuine documents total);
- task constructs: at least 20 unique documents per source in addition to the per-class floor.

All constructs cap target and donor contributions at 24 rows/document. Every capture report includes
target-document, donor-document where applicable, connected-component, and effective bootstrap support;
the component is the resampling unit. An individual intervention failing its label-only floor is
prescore-ineligible and cannot be repaired by finite bootstrap draws.

The module must pass in both directions:

- start distance and relative quartile assigned recovery in the projection;
- token identity assigned recovery in the complement;
- primary-rank macro assigned recovery at least `0.65`;
- macro-selectivity lower confidence bound above zero with at least 490/500 finite draws;
- every construct’s selectivity positive at every rank;
- relative-gap capture preferentially in the projection;
- true-context capture preferentially in the projection;
- proper-noun substitution capture preferentially in the complement;
- true-context projection capture greater than unrelated-context projection capture, with a positive
  lower confidence bound;
- all required capture intervals have at least 490/500 finite draws.

Unrelated context is a negative control, not another positive context construct. The module is
independent of relation-delta eligibility.

### Decision logic

- Relational pass only → nominate a later relation-aware representation comparison.
- Sequential/context pass → nominate a later equal-capacity supervised-versus-frozen-projection
  comparison; do not train in Attempt 13.
- Projection later matches a learned model → prefer the projection.
- Raw decodability is separately classified for every prespecified task using normalized recovery at
  least `0.65`, at least 490/500 finite document-bootstrap draws, and a lower confidence bound above
  zero. Relation-task decodability uses the full true child–head feature; secondary-task decodability
  uses the unprojected activation.
- A measurable task below that raw gate is `not_demonstrated_decodable`; a task above it whose
  specificity/isolation gate fails is `decodable_not_isolated`; structural missingness is `ineligible`.
  Module and overall summaries preserve this vector and never infer decodability merely from failure.
- Either module ineligible → report endpoint-specific missingness; never promote through missingness.
- Private/private/shared remains unauthorized until a separate frozen measurement demonstrates
  incremental shared/interaction signal.

## Approach

Build a new Attempt-13 namespace with a label-only builder, signed preflight/freeze/authorization,
fresh activation extraction, analysis, endpoint overlay, terminal state, and report. Reuse reviewed
low-level parsing, tokenizer alignment, deterministic ridge score estimation, document-bootstrap,
hashing, and signing
utilities by exact source hash, but do not modify or invoke an Attempt-12 continuation path.

The prepared manifest and prescore attestation will be generated before authorization. The exact
candidate will then receive `/adversarial` review. Only a `SHIP` verdict bound to its exact freeze hash
can authorize the tmux pipeline.

### Alternative considered

Reusing ParTUT and ATIS would make the raw texts entirely unseen, but neither provides genuine
`newdoc id` groups, making document-bootstrap uncertainty indefensible. GENTLE and CTeTex are preferred
because they have genuine upstream documents and may be used only if the exposure firewall establishes
that they are endpoint-outcome-naive with prior technical inference exposure.

## Milestones

### M1 — Freeze Attempt 12 and development calibration

- Record Attempt-12 terminal and recursive result/run inventories.
- Emit the EWT/GUM relative-delta calibration without modifying or rescoring Attempt 12.
- Acceptance: exact Attempt-12 hashes are unchanged and calibration contains no fresh-source
  activations.

### M2 — Label-only fresh-source preparation

- Build the complete prior-exposure inventory and cross-source document/sentence/token/subtoken overlap
  audit, then build GENTLE/CTeTex rows, controls, interventions, support tables, exposure ledger, and
  manifest.
- Acceptance: no model forward, at least 20 documents/source, per-class document floors, row caps,
  source-local exact-offset controls, intervention document floors, transfer vocabularies, and
  label-only bootstrap completeness pass or the affected endpoint is frozen ineligible.

### M3 — One-shot runner and analysis implementation

- Add isolated extraction, cache verification, relational and sequential/context analyzers,
  endpoint-specific decision logic, signed lifecycle, tmux launcher, and deterministic smoke tests.
- Acceptance: synthetic tests cover low-norm denominators/rates at/over the cap, independent module
  missingness, exact same-source offset matching, bidirectional nondependency/ancestry exclusion, hard
  donor reuse caps, capture roles/support, raw-versus-isolation outcomes, no-neural-training assertions,
  allowed ephemeral ridge reachability, concurrency, consumed authorization, and write isolation.
  Explicit regression cases must prove shared component multiplicities for correlated donor rows,
  failure after post-norm class/document support loss, rejection of a successor authorization with the
  same study key, and rejection of any late file absent from both freeze manifests/allowlists. Overlap
  regressions cover isolated-short removal from all input roles, long-sentence document removal, two
  distinct collisions, deduplication of historical copies, symmetric cross-source removal, no adjacency
  bridging, and absence of every excluded signature/subtoken sequence from prepared model inputs.

### M4 — Verification and adversarial review

- Run syntax checks, targeted tests, static no-neural-training audit, reproducibility checks, deep manifest
  verification, and source/Attempt-12 inventory verification.
- Freeze all implementation and prepared artifacts.
- Request `/adversarial` on the exact freeze; fix all BLOCK findings and re-review.
- Acceptance: exact candidate receives `VERDICT: SHIP` and authorization binds that review.

### M5 — One-shot scientific execution

- Launch the authorized pipeline under tmux on the frozen free GPU.
- Atomically consume the global study key, extract each endpoint-outcome-naive
  source once, analyze once, and write a signed success/failure terminal.
- Acceptance: tmux ends, result or failure terminal verifies, Attempt 12 remains byte-identical, and
  no training/checkpoint/optimizer artifact exists.

### M6 — Post-result claim review

- Run `research-claim-review` on the signed result before interpreting or recommending training.
- Acceptance: persisted claim review distinguishes endpoint outcome classifications, missingness, and
  technical ineligibility and respects the disclosed technical exposure.

## Verification plan

- `python -m py_compile` on every new Python entrypoint.
- `bash -n` on pipeline and launcher scripts.
- `pytest -q tests/test_atlas_relation_context_v9.py` for deterministic unit/integration tests.
- Static AST and shell audit proving no neural optimizer, backward pass, checkpoint writer, training
  entrypoint, persisted fitted-probe artifact, Attempt-12 write, or old-result promotion is reachable;
  the only permitted estimator fit path is the exact-hashed ephemeral ridge scorer.
- Deep hashes/signatures/row-order/float32/finiteness checks for every prepared child and cache.
- GPU preflight: physical UUID, visible index, `CUDA_VISIBLE_DEVICES`, CUDA/runtime versions.
- Post-run `verify-result`, terminal signature verification, and recursive Attempt-12 inventory check.
- Repro guard: seeds, deterministic Torch, pinned environment, exact source/model revisions, no local
  absolute paths in configs, and no secrets in tracked files.

## Risks and one-way doors

- **Scientific source opening:** the first endpoint-science model forward is irreversible. Authorization
  therefore requires an exact reviewed freeze and an atomic cross-namespace consumed record; a crash
  after consumption cannot be retried.
- **Technical exposure:** GENTLE and CTeTex have prior technical inference exposure and may be called
  endpoint-outcome-naive only if the prospective firewall passes. Claims must retain that limitation.
- **Only 26 GENTLE documents:** support floors and row caps may make an endpoint ineligible. The protocol
  must accept missingness rather than relax support.
- **Distance-control availability:** cross-document stratum matching may reduce relation rows. This is
  checked label-only; no fallback stratum or control may be invented after scoring.
- **Low-norm rule:** `1e-4` and 0.1% are frozen from opened development data. Fresh failure is terminal
  endpoint missingness, not a reason to revise them.
- **Model/layer scope:** one checkpoint and layer cannot establish a universal representation claim.
- No schema or public API is a one-way door. The scientific source opening and one-shot outcome are the
  only irreversible actions.

## Definition of done

- [ ] Attempt 12 is byte-identical before and after Attempt 13.
- [ ] Opened EWT/GUM development calibration freezes the normalized rule without fresh activations.
- [ ] The hash-bound exposure/overlap firewall supports the narrow endpoint-outcome-naive classification;
      otherwise the affected source stops before inference.
- [ ] GENTLE and CTeTex pass label-only document/class/intervention/control support, including exact
      offset matches and hard donor caps, or the affected endpoint freezes prescore-ineligible.
- [ ] All scientific artifacts, exclusions, controls, thresholds, GPU mapping, and decision logic are
      hash-frozen before fresh inference.
- [ ] Exact Attempt-13 code/prepared candidate receives `/adversarial` `SHIP` before authorization.
- [ ] The one-shot tmux run ends in a verified signed terminal with endpoint-specific results.
- [ ] No neural/representation training, optimizer, checkpoint, persisted fitted probe, or private/shared
      implementation is run; only the reviewed ephemeral ridge score estimator is reachable.
- [ ] A separate post-result research-claim review is persisted before scientific recommendations.
