VERDICT: BLOCK
ONE-LINE: Float32 is defensible, but fresh-only QA would evade the known failure set and leave estimator lineage ambiguous.

BLOCKERS        (must fix before proceeding; empty if none)
  - [critical] scripts/extract_atlas_discovery_v3.py:364-395; pilot_runs/20260803_atlas_discovery_v3_1_attempt5/ATTEMPT5_TECHNICALLY_INVALID.json:4-35 — the proposal replaces the known failing deterministic QA set with a fresh disjoint set.
    reasoning — choosing a new set after both original sets failed is a post-failure rerandomization. A pass would not establish that float32 repaired the observed failure rather than avoiding inputs that expose it. The failure was not marginal: independent recomputation from the signed arrays found null-bound violations in 42/48 EWT and 45/48 GUM activation rows, with maximum absolute differences `0.125` and `0.25`.
    impact — attempt 6 could pass while the exact attempt-5 challenge cases still violate the unchanged null, so the claimed precision repair would be unidentified.
    fix — freeze attempt 6 before inference and require **both** (a) the exact attempt-5 QA unit manifests replayed under float32 and (b) a fresh hash-selected QA set disjoint at genuine-document/component level from the legacy set. Apply the identical formula to both sources and both sets; any failure is a terminal attempt-6 stop with no subset reroll, dtype escalation, or threshold change.
  - [high] configs/atlas_discovery_v3/run.json:43-49; scripts/extract_atlas_discovery_v3.py:245-253,428-468,530-531,572-576 — precision is embedded throughout the attempt-5 estimator and lineage, not merely in model loading.
    reasoning — the prescore model contract says float16, the extractor hard-codes float16 loading and payload identity, and full-cache verification requires `inference_dtype=float16`. Editing only `_load_model` would create a cache whose scientific estimator disagrees with its parent manifest/config.
    impact — an apparently valid attempt-6 cache could be mislabeled as attempt 5 or mix float16 QA, float32 inference, and attempt-5 model identity.
    fix — define a new attempt-6 protocol, prescore-import manifest, scoring schema, cache schemas, run/data roots, row-role manifest, and signer/authorization chain. Freeze `inference_dtype=float32`; assert every floating parameter and extracted hidden state is float32, autocast is disabled, TF32 is false, and QA/full extraction use the identical path. Recompute every activation; hard-reject all attempt-5 activation artifacts.
  - [high] pilot_runs/20260803_atlas_discovery_v3_1_attempt5/staging/qa-EWT-80b366e3ac48-2200637/qa_rows.json:1-25; pilot_runs/20260803_atlas_discovery_v3_1_attempt5/staging/qa-GUM-80b366e3ac48-2200710/qa_rows.json:1-25 — “reuse only unopened label-prescore rows” does not define the attempt-6 scientific population or the unit of disjointness.
    reasoning — attempt-5 raw activations were opened for specific bare/null units, while their documents can contribute other observational and intervention rows. Row-ID-only exclusion would retain correlated same-document observations; excluding after seeing per-row numerical errors would be outcome-dependent.
    impact — support, common-support rates, and bootstrap independence could silently change, and prior technical activations could influence the supposedly unopened score-bearing population.
    fix — before any attempt-6 inference, serialize the complete legacy QA pair/unit/document/component set and a separately hashed fresh QA set. Reserve both QA document/component sets from scientific endpoints, derive the science population by one label-blind rule, and rerun every label-only task/intervention/joint/common-support gate on that exact remainder without relaxation. Bind all retained/excluded row IDs and parent hashes in the attempt-6 import manifest.
  - [high] configs/atlas_discovery_v3/scoring.json:22-35,57-58; docs/rfc-atlas-v3-1-attempt5-discovery-factor-atlas.md:350-361 — raw QA representations can be inspected before the downstream scientific estimator is fully frozen.
    reasoning — the current scoring inventory binds extraction and helper tests, but not a complete analysis/aggregation implementation. A fresh QA run exposes reference activations and intervention-null differences; later analysis choices could be shaped by those values even if named scientific metrics were not computed.
    impact — “scientific endpoints unopened” would not eliminate analysis-path leakage.
    fix — before attempt-6 QA, freeze and inventory-bind the complete downstream row joins, probe/nuisance fitting, bootstrap maps, delta metrics, projection logic, aggregation, and terminal decision code, or enforce a technical operator boundary where only signed pass/fail summaries are visible and QA documents are permanently absent from science. No analysis-code changes after QA except independently reviewed correctness fixes that force a new attempt.
  - [high] pilot_runs/20260803_atlas_discovery_v3_1_attempt5/ATTEMPT5_TECHNICALLY_INVALID.json:1-41; configs/atlas_discovery_v3/scoring.json:27,36-58 — attempt 5 is marked invalid, but its failed bundles remain mutable staging artifacts and its scoring config still authorizes numerical QA.
    reasoning — the unsigned stop marker hashes signed child envelopes, but the authoritative evidence remains under PID-named staging paths; there is no immutable failed-QA archive or explicit execution tombstone.
    impact — cleanup, accidental retry, or later promotion could obscure which failure ended attempt 5.
    fix — archive the two exact three-file QA bundles under an immutable failure namespace, verify their Ed25519 signatures and child hashes, and issue a signed terminal envelope binding the prescore/scoring configs, protocol, failure arrays/rows/envelopes, invalid marker, and absence of full authorization/caches. Attempt 6 must use a new run root and hard-reject attempt-5 scoring authorization and caches.

REVISIONS       (should fix; not blocking)
  - [medium] configs/atlas_discovery_v3/scoring.json:5-19 — source is perfectly confounded with GPU UUID.
    reasoning — at a `5e-7 + 5e-6|x|` gate, device-specific arithmetic matters; EWT always runs on GPU 0 and GUM on GPU 1.
    impact — a source-specific QA or downstream difference cannot be separated from device effects.
    fix — use one GPU sequentially for both score-bearing sources, or freeze a cross-device replay panel and require the same float32 null decision and bounded device agreement before assigning sources to separate GPUs.
  - [medium] pilot_runs/20260803_atlas_discovery_v3_1_attempt5/staging/qa-EWT-80b366e3ac48-2200637/QA_COMPLETE.json:25-43; pilot_runs/20260803_atlas_discovery_v3_1_attempt5/staging/qa-GUM-80b366e3ac48-2200710/QA_COMPLETE.json:25-43 — signed QA summaries contain only booleans and repeat-derived tolerance, not failure magnitude.
    reasoning — auditors must reopen arrays to distinguish a boundary miss from the observed orders-of-magnitude failure.
    impact — the technical diagnosis and attempt-6 comparison are unnecessarily opaque.
    fix — sign per-family maximum absolute error, maximum bound ratio, failing element/row counts, exact repeat error, shapes/dtypes, and margins to ceiling; keep arrays as the authoritative recomputation source.
  - [medium] docs/rfc-atlas-v3-1-attempt5-discovery-factor-atlas.md:220-224 — switching to float32 after seeing float16 failure changes the scientific representation estimator.
    reasoning — it is a justified technical repair, but it is still post-QA method development rather than replication of attempt 5.
    impact — attempt-6 evidence could be overstated as prespecified or comparable to float16 model behavior.
    fix — label attempt 6 explicitly exploratory and precision-conditional; do not pool it with attempt 5, claim float16 invariance, or use it as confirmation. If attempt 6 fails, terminate this atlas rather than iterate again.

NITS            (optional, cap at 5)
  - scripts/extract_atlas_discovery_v3.py:450-456 — preserve float64 difference/bound evaluation in attempt 6; do not compare after casting differences back to float32.

CHECKS RUN
  - verified both QA envelope SHA-256 values, canonical-message hashes, Ed25519 signatures, and child array hashes → PASS.
  - recomputed signed-array repeat behavior → both repeated references are bit-identical (`e=0`) in both sources.
  - recomputed frozen elementwise nulls → EWT: 42/48 rows fail, max error `0.125`; GUM: 45/48 rows fail, max error `0.25`; both uniform and prefix families fail.
  - inspected authorization state → full-extraction authorization and full activation caches are absent; failed QA was never promoted from staging.
  - inspected estimator code/config → float16 is hard-coded in model loading, signed QA identity, cache verification, and cache completion metadata.

CONTRACT COVERAGE
  - retire attempt 5 without threshold relaxation → met in proposal and current stop marker.
  - scientific endpoints remained unopened → met narrowly — no full cache/authorization exists, though raw QA representations were opened.
  - float32 as a new estimator → partial — scientifically defensible, but new schemas/import lineage and dtype assertions are unspecified.
  - fresh disjoint QA → partial — useful as replication, invalid as the sole replacement for the known failing challenge set.
  - no post-selection → unmet — fresh-only subset selection after failure and undefined “unopened rows” create avoidable selection paths.
  - preserved numerical formula/ceiling → met in proposal.
  - fail-closed both-source decision → partial — both-source stop is specified, but legacy-set and terminal no-further-attempt rules are missing.
  - attempt-5 immutable lineage → partial — child evidence is signed and hashed, but remains staged and the terminal marker is not authenticated.
  - neural training prohibition → met — no optimizer/checkpoint/full cache exists and proposal remains inference-only.

UNKNOWNS
  - Whether float32 passes the exact known-failure sets; this is the necessary repair test and must not be inferred from theory.
  - Whether removing both QA document/component sets leaves every attempt-6 prescore and common-support endpoint eligible.
  - Whether the two GPUs are the same model/firmware and agree under float32 at the frozen bound.
  - Whether a complete downstream analysis implementation can be frozen before any attempt-6 QA array is created.
