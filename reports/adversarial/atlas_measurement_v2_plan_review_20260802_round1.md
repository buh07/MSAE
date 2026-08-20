# Atlas measurement v2 plan adversarial review — round 1

**Verdict:** BLOCK  
**Origin:** independent forked reviewer  
**Scope:** `docs/rfc-atlas-v2-prescore-measurement.md`

## One-line

The audit misses Tier-1 rows and leaves its scientific and safety gates non-deterministic.

## Blockers

1. M4 named only `data/atlas_completion_v1`, although Tier-1 rows live under `data/atlas_v1/analysis_rows`; the Tier-1 source adapter was undefined.
2. Lexical path rejection did not define canonical containment or symlink handling.
3. Frozen integrity was sampled and retrospective rather than exhaustive and pre-open.
4. The ordinary hierarchical-bootstrap map, seed, strata, ordering, and finiteness predicate were underspecified.
5. Vocabulary selection, bin/coarse maps, applicable sources, family constructs, and non-nestedness were underspecified.
6. No-experiment/no-download assertions lacked enforcement and evidence-producing checks.

## Revisions requested

1. Freeze endpoint aggregation truth tables and status precedence.
2. Freeze CKA/residualization formulas and degeneracy rules.
3. Define a signed, digest-bound blind-final attestation with a disclosure allowlist and mandatory retirement behavior.

## Resolution

The RFC was revised to add separate digest-bound Tier-1/Tier-2 adapters, an exact source-prefix map, canonical pre-open IO containment, exhaustive pre/post freeze verification, a version-independent bootstrap generator, frozen row/label/family rules, endpoint truth tables, exact CKA/residualization formulas, a custodian-signed final attestation contract, and offline/process/IO evidence checks. A second adversarial review is required before implementation.

## Checks run by reviewer

- `check-plan --path docs/rfc-atlas-v2-prescore-measurement.md` → PASS.
- Inspected Tier-1/Tier-2 row roots and schemas, relevant freeze/config records, and existing symlink state.
