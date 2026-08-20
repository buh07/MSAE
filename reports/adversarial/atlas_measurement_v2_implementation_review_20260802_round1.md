# Atlas measurement v2 implementation adversarial review — round 1

VERDICT: BLOCK

## One-line

The audit misapplied v2 support rules, while CKA and cache utilities accepted scientifically invalid lineage.

## Blockers found

1. Raw historical labels/rows were audited directly rather than applying each frozen v2 label contract, document-frequency vocabulary, and deterministic group cap first.
2. CKA accepted equal-length arrays without ordered row-ID alignment.
3. The cache loader allowed manifests that omitted canonical file hashes and identity fields.
4. No-experiment evidence lacked the promised durable process snapshots and deny-path tests.

## Revisions found

1. Endpoint aggregation did not preserve structured finite subordinate values and all blocking reasons.
2. Family CKA accepted NaN/out-of-range values.
3. Provenance/attestation shape helpers could be mistaken for authorization.
4. Config/protocol/freeze/cache files did not all use the central canonical resolver.

## Resolution implemented

- Config now binds a label contract for every input, including full UPOS/dependency/capitalization maps; the CLI records raw support separately, then maps/selects/caps before primary support evaluation.
- All CKA variants require matching ordered row IDs; delta CKA and permutation tests were added.
- Cache manifests now require the exact schema, checkpoint/transform, dtype/shape/offset metadata, and all three canonical file hashes.
- The audit records hashed before/after process snapshots and experiment-marker checks; tests deny network/process/file-open escape paths.
- Structured endpoint aggregation preserves observed values and collects all blocking reasons.
- Family CKA rejects non-finite/out-of-range values.
- Provenance/attestation helpers explicitly return authorization blocked until external cryptographic verification exists, and anti-splitting is enforced structurally.
- Config, protocol, trust root, row inputs, output, and cache members use canonical non-symlink containment checks.

## Checks run by reviewer

- 23 targeted tests passed before the findings.
- Python compilation passed.
- Config/RFC/report and all 54 row-input digests matched.
- Direct malformed-cache and permuted-row probes reproduced the two lineage blockers.
