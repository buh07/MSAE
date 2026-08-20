# RFC: Atlas v3.3 attempt 7 external-QA float32 discovery atlas

**Status:** label-only QA-pool and science prescore authorized; neural inference forbidden pending complete implementation and adversarial `SHIP`  
**Date:** 2026-08-02  
**Scientific contract parent:** attempt 5 (`docs/rfc-atlas-v3-1-attempt5-discovery-factor-atlas.md`)  
**Technical redesign parent:** attempt 6 (`docs/rfc-atlas-v3-2-attempt6-discovery-factor-atlas.md`)

## Transparent history

Attempt 5 stopped at its frozen float16 numerical null. Attempt 6 never ran neural inference: its label-only prescore showed that reserving both legacy and fresh *training-document* QA panels removed too much GUM support. The unchanged joint endpoint fell below 40 common rows for several EWT→GUM classes and above the 20% unseen-cell ceiling for GUM→EWT true context. Attempt 6 is permanently `FAILED_PRESCORE`.

Attempt 7 fixes the support conflict without relaxing a science threshold or selecting on activations. Fresh technical QA comes exclusively from the pinned official EWT and GUM **dev+test** documents at the same source revisions. These documents are QA-only and absent from train-science by construction. The exact attempt-5 training challenge documents remain reserved from science. Train science is rebuilt from raw CoNLL-U after those legacy documents are removed, including fresh donor matching and all unchanged support gates.

This is exploratory, precision-conditional method development. It is not attempt-5 replication, is not confirmatory evidence, and cannot license neural training.

## Inputs and roles

### Scientific inputs

Only the same exact pinned EWT-train and GUM-train CoNLL-U files used in attempt 5. Every train document in the exact attempt-5 legacy QA challenge is removed before any attempt-7 task row, donor matching, fold/component map, balancing, or bootstrap is built.

### Technical-QA-only inputs

Official EWT dev/test at revision `4a4d77f599ea53cc405f85d0cec4b2f14f81d42b` and GUM dev/test at revision `1fe635509c649e376dfb449d528424ab78f4eaee`, with part and byte-exact concatenation hashes in `data/atlas_discovery_v3_3_attempt7_qa_raw/PROVENANCE.json`. They may create only numerical-QA reference/translation units. They cannot enter any probe, relation, intervention fingerprint, nuisance fit, basis, projection, bootstrap, or decision.

## Exact QA panels

For each source:

1. replay the exact 32 attempt-5 failing training pairs in their frozen order under the new float32 estimator;
2. select a fresh dev/test panel of 16 pairs: 8 context-factorial and 8 relative-gap, each class ordered by `SHA256(atlas_discovery_v3_3_attempt7|fresh-qa|source|construct|pair_id)` and greedily rejecting any already-selected document/component.

Fresh panels must be document/component-disjoint internally and from legacy panels. Dev/test document IDs must also be absent from the retained train-science manifest. There is no reroll after inference.

Each legacy/fresh source panel receives three identical reference runs and one translated run. Both uniform-shift and prefix-position-only families must pass the unchanged attempt-5 elementwise formula: `|shifted-reference| <= atol + 5e-6*|reference|`, `2e < 2e-5`, `atol=max(5e-7,2e)`. Any family/panel/source failure terminates the atlas without threshold changes, dtype escalation, or retry.

## Float32/no-training contract

The pinned Pythia model/revision/layer are unchanged. Model parameters, computation, extracted hidden state, and cache are float32. Autocast and TF32 are disabled; deterministic algorithms and `CUBLAS_WORKSPACE_CONFIG=:4096:8` are required. EWT and GUM execute sequentially on one physical GPU, and QA/full science extraction share one function. Signed artifacts assert model/device UUID, parameter/hidden/cache dtypes, batch, layer, environment, exact child hashes, zero optimizer/checkpoint creation, and `neural_training_run=false`. All attempt-5 arrays/caches are rejected as full-science inputs.

## Science prescore and analysis

All attempt-5 label tasks, nuisance columns, direction-specific fit-only choices, thresholds, 500-draw bootstrap rules, intervention definitions, source-common 94-cell allowlist, 20% unseen ceiling, common-subset sign gate, relational advantage, delta specificity, rank-8/16/32 projection organizations, candidate decision rules, and terminal outcomes remain unchanged.

Every label-only gate is rerun on the exact legacy-excluded train rebuild. Failure stops before inference. The exact fresh QA documents never reduce science support because their splits are role-separated rather than filtered after scoring.

Before any attempt-7 QA model call, freeze and inventory-bind the complete extractor and downstream analysis implementation: row joins, source-transfer standardization/ridge/alpha selection, nuisance encoders, all bootstrap maps, relations, factorial deltas, cross-family classifier/full-common sign check, feature-space basis overlaps, projections, reports, and terminal aggregation. Synthetic fixtures must cover leakage, missing class, shared documents, nuisance-only signal, source reversal, numerical null, intervention and relation effects, and overlapping bases. Independent adversarial reviews must return `SHIP` on both prescore and full implementation.

## Fail-closed outcome

Any input-role, document-firewall, prescore, lineage, dtype, numerical-QA, cache, or globally required endpoint failure yields `technically_ineligible`. Otherwise attempt-5 candidate rules return exactly one of three exploratory nominations, `multiple_discovery_candidates`, or `no_decomposition_nominated`. No result authorizes a learned architecture; a later genuinely fresh corpus/protocol must confirm one nominated question.
