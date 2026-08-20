VERDICT: SHIP
ONE-LINE: A frozen source-common adjusted estimand is defensible because it removes extrapolation without weakening support gates.

BLOCKERS        (must fix before proceeding; empty if none)
  - None.

REVISIONS       (should fix; not blocking)
  - None.

NITS            (optional, cap at 5)
  - Proposed attempt-5 protocol — serialize and hash the exact source-common joint-cell set and state explicitly whether support is pooled across the four design classes; do not leave this implicit in prose.
  - Proposed attempt-5 protocol — call zero unseen-cell rate an expectation, not a structural guarantee: post-filter hash balancing can omit a rare fit-source cell. The unchanged retained-sample `<=20%` gate and common-subset sign check must remain authoritative.

CHECKS RUN
  - inspected `data/atlas_discovery_v3_1_attempt4_failed_prescore/FAILED_PRESCORE.json` → attempt 4 is digest-bound `FAILED_PRESCORE`; representation scoring and neural training are both false.
  - reviewed supplied attempt-4 support outcome → row/fold/bootstrap gates passed; only the frozen 20% retained-sample common-support gate failed for GUM-fit→EWT true/unrelated context.
  - reviewed attempt-5 selection order → source-common filtering precedes per-source/fold class balancing, uses only frozen nuisance metadata, and retains all existing fail-closed thresholds.

CONTRACT COVERAGE
  - no activation/outcome-guided selection → met — the revision uses only pre-inference nuisance/support metadata.
  - common-support estimand → met — both sources are restricted symmetrically to the prospectively frozen joint-cell support.
  - class/fold balance → met in design — each source/fold uses the four-class minimum and outcome-blind hash ordering.
  - document support and bootstrap completeness → met in design — `>=50/class`, `>=25 target documents/class`, `>=5/class/fold`, and `>=490/500` remain unchanged.
  - nuisance adjustment → met — the exact marginal-plus-joint model, unknown handling, and common-subset sign check remain frozen.
  - interpretation → met — this is a transductively defined source-common adjusted predictive estimand, not exact matching, causal specificity, or untouched-corpus confirmation.
  - revision lineage → met in proposal — attempt 4 remains immutable, attempt 5 receives a distinct namespace, and failure ends support revision rather than relaxing a gate.

UNKNOWNS
  - Attempt-5 retained class/document/fold counts and pooled finite-draw count; these must pass label-only preflight before any neural inference.
  - Actual retained-sample unseen-cell rates after hash balancing; they must be computed rather than assumed zero.
  - Byte-identical independent attempt-5 rebuild evidence is not yet available.
