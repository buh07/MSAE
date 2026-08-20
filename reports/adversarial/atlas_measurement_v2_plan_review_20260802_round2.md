# Atlas measurement v2 plan adversarial review — round 2

**Verdict:** BLOCK  
**Origin:** independent forked reviewer

## Blocking finding

The universal per-source all-class support rule contradicted the pooled `source_type` nuisance contract, which would have recreated structural ineligibility.

## Revisions requested

1. Map the observed capitalization label `nonalpha` explicitly.
2. Define family-level CKA aggregation, weighting, and partial-task missingness.
3. Turn “genuine document group” provenance into a signed candidate-manifest contract.

## Resolution

The RFC now gives pooled nuisance tasks an explicit hard-gate exception while retaining per-source total-group checks; maps `nonalpha` separately; specifies equal-weight representative-task family CKA with complete and descriptive partial outputs; and requires signed, digest-bound grouping provenance reviewed independently from the candidate builder. It also records the exact modulo-bias bound and includes the freeze-record trust root in the baseline inventory.

## Checks run by reviewer

- `check-plan --path docs/rfc-atlas-v2-prescore-measurement.md` → PASS.
- Inspected current capitalization labels and completion freeze membership.
