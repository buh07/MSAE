# RFC: Atlas v3.2 attempt 6 float32 precision-conditional discovery atlas

**Status:** label-only prescore authorized; neural inference remains forbidden until the complete extractor and downstream analyzer receive independent `SHIP` reviews  
**Date:** 2026-08-02  
**Parent scientific contract:** `docs/rfc-atlas-v3-1-attempt5-discovery-factor-atlas.md`  
**Scope:** exploratory reused-public EWT/GUM evidence; no neural training

## Why this is a new attempt

Attempt 5 terminated at its frozen numerical gate. Three identical float16 inferences were bit-identical, but a uniform `+16` RoPE translation and the prefix-position-only translation failed the prespecified elementwise null in both EWT and GUM. No full cache, downstream result, or scientific endpoint was opened. The failure evidence is authenticated by `pilot_runs/20260803_atlas_discovery_v3_1_attempt5/TERMINAL.json`.

Attempt 6 does not relax or reinterpret attempt 5. It changes the representation estimator from float16 inference to float32 inference and is explicitly exploratory and precision-conditional. Its results cannot be pooled with attempt 5 or described as a successful float16 invariance result. If any attempt-6 technical gate fails, this factor atlas terminates rather than changing dtype, tolerance, rows, or threshold again.

Except for the changes below, the attempt-5 scientific questions, tasks, nuisance table, transfer directions, bootstrap counts, thresholds, projection organizations, mechanical outcome vocabulary, interpretation limits, data firewall, and no-training rule are inherited verbatim.

## Frozen population separation

`configs/atlas_discovery_v3_2/population_split.json` is generated without activations or scientific outcomes and binds all parent hashes and exact IDs.

For each source it defines:

1. **Legacy challenge QA:** the exact 32 attempt-5 QA pairs, preserving their exact input units and order.
2. **Fresh QA:** 16 pairs (8 context-factorial then 8 relative-gap), selected by a new salted hash while greedily enforcing disjoint genuine documents and components from every legacy and already-selected fresh pair.
3. **Science:** a complete rebuild from the pinned CoNLL-U inputs after removing every genuine document involved in either QA panel *before* task capping, donor matching, fold/component construction, joint balancing, or bootstrap creation.

The science rebuild must rerun every attempt-5 label-only task, intervention, class/document, fold, ordinary-bootstrap, joint/common-support, and shared-node-bootstrap gate with the unchanged thresholds. Donor-linked endpoints are rematched only on the retained science documents. It is not acceptable merely to filter the old matched pairs. If any required gate fails, attempt 6 stops at prescore.

The legacy and fresh QA documents are absent from every observational, relational, intervention, nuisance, basis, projection, bootstrap, and decision-bearing science row. QA raw arrays are never an input to downstream analysis.

## Float32 estimator and numerical QA

- Pinned model/revision/layer remain Pythia-160M-deduped, revision `582159a2dfe3e712a8d47ae83dec95ae3bde8e7e`, block 3 / hidden-state index 4.
- Every model floating parameter and score-bearing hidden state must be `torch.float32`.
- Autocast is disabled, TF32 is disabled, deterministic algorithms are enabled, and QA/full science extraction share one exact forward path.
- Both sources run sequentially on one frozen physical GPU. This removes source/GPU confounding. No old activation is reused.
- Each of the four panels (legacy-EWT, fresh-EWT, legacy-GUM, fresh-GUM) receives three identical reference runs and one translated run.
- The attempt-5 elementwise rule is unchanged: `|shifted-reference| <= atol + 5e-6*|reference|`, where `e` is the maximum absolute repeated-reference error, `2e < 2e-5`, and `atol=max(5e-7,2e)`.
- Uniform-shift and prefix-position-only families must both pass in every source and both legacy/fresh panels. Any failure is terminal; there is no subset reroll, threshold relaxation, dtype escalation, or retry.
- Signed QA summaries include shapes/dtypes, maximum absolute error, maximum bound ratio, failing element and row counts, repeat error, and margins. Exact arrays and ordered row manifests remain authoritative.

A signed full-extraction authorization can be issued only after all four promoted QA bundles validate. Full extraction uses only the rebuilt science inference units and writes a fresh float32 cache under `pilot_runs/20260803_atlas_discovery_v3_2_attempt6`.

## Frozen downstream analysis boundary

Before any attempt-6 QA inference:

- freeze and hash the complete row joins, source-transfer ridge/scaler/alpha fitting, nuisance encoders, document/component bootstrap maps, relation-aware comparisons, factorial delta construction, adjusted cross-family classifier, common-subset sign check, delta-basis overlap, rank-8/16/32 projection/scrubbing organizations, candidate aggregation, reports, and terminal decision;
- pass synthetic tests for label leakage, missing classes, shared documents, nuisance-only shortcuts, source reversal, null/intervention deltas, relation-aware gain, and overlapping bases;
- obtain independent adversarial `SHIP` reviews for the prescore rebuild and the full scoring/analyzer implementation.

After QA starts, analysis code and decision thresholds are immutable. A correctness change requires a new attempt. Operators may see signed pass/fail summaries; QA documents are permanently excluded from science regardless of outcome.

## Exact endpoint contract retained from attempt 5

The analysis continues to report, separately:

- strict uniform absolute-index translation as a technical RoPE null;
- start-distance, relative quartile, ordered pair distance, and virtual relative-gap response;
- separator visibility, generic visible-context accumulation, and document-related context;
- token identity, lemma diagnostic, Number, UPOS, capitalization, word length, punctuation, and matched proper-noun substitution;
- child-only versus `[child, head-child]` versus matched `[child, sham-child]` syntax;
- raw signal, incremental signal over frozen nuisances, intervention specificity, basis overlap, and no-training projection/scrubbing organizations.

`source-common` cross-family specificity retains the exact attempt-5 94-cell nuisance allowlist, the 20% unseen-cell ceiling, minimum 40 common rows/25 common documents per heldout class, and the mandatory same-positive-sign check on the fit-observed subset. Missingness remains separate from scientific failure.

## Terminal outcomes

The attempt-5 outcome vocabulary is retained. Any data firewall, prescore, lineage, dtype, QA, cache, or globally required endpoint failure yields `technically_ineligible`. Otherwise candidates aggregate mechanically to one of the three nominations, `multiple_discovery_candidates`, or `no_decomposition_nominated`. The atlas only nominates a question for a later genuinely fresh confirmation study and never authorizes learned training.

## Acceptance criteria

- Attempt-5 failed artifacts and terminal signature validate; no attempt-5 retry or cache exists.
- Population split deterministically rebuilds and legacy/fresh/science documents are exactly disjoint.
- Science preparation is byte-identical on rebuild and all unchanged support gates pass.
- Complete extractor and analyzer implementations, configs, tests, protocol, parent imports, signer, and model/data hashes are inventory-bound before QA.
- Both exact legacy and fresh QA panels pass on both sources under the unchanged elementwise formula.
- Float32 parameters/hidden states, single-GPU execution, disabled autocast/TF32, and no-training flags are signed and independently checked.
- Scientific analysis is complete or explicitly ineligible, returns exactly one allowed outcome, and never consumes QA rows.
- Final implementation/result adversarial review and a separate research-claim review constrain any conclusion.
