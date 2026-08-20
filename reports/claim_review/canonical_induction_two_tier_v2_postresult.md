CLAIM: SUPPORTED
SUMMARY: The pipeline skyline passed, but the external upstream set was causal yet insufficiently potent and selective.

BLOCKERS
  - None for the narrow registered claim.

REVISIONS
  - results/canonical_induction_two_tier_v2_20260809/final/result.json — do not generalize the Tier-B stop to SAEs, linear methods, induction circuits generally, or model families; none were tested.
  - results/canonical_induction_two_tier_v2_20260809/development/SUMMARY.json — report all four Tier-B endpoints: ablation advantage passed, while recovery, sham selectivity, and control margin failed materially.
  - results/canonical_induction_two_tier_v2_20260809/development/QA.json — label individual-head, class, vocabulary-restoration, token-movement, collateral, and additivity results descriptive; confirmation was not opened.
  - PAPER.md:487-509 — comparisons with v1.1 must remain qualitative because the panel and patch scope differ.

EVIDENCE CHECKED
  - final/result.json — formal DEVELOPMENT_UPSTREAM_SET_STOP; confirmation null; no representation methods or training.
  - development/SUMMARY.json — 128/128 common-cohort rows; technical/support/Tier-A pass; Tier-B fail.
  - development/QA.json and two independent QA NPZs — exact repeated logits, registered head slices, residual states, donor identity, and self-patch checks; 36 descriptive fields with zero missingness.
  - development/metrics.jsonl — joint recovery 0.1659 [0.1451, 0.1883], selectivity 0.1012 [0.0810, 0.1218], circuit-control margin 0.0844 [0.0694, 0.0998], ablation advantage 0.0930 [0.0494, 0.1373].
  - lineage hashes and attempt states — completion, validated marker, gate, block, and final hashes match; states CLOSED, CLOSED_GATE_READY, and CLOSED_BLOCKED.
  - launcher.log — only nonfatal library initialization/deprecation warnings; no traceback, nonfinite, or technical-invalid event.

UNKNOWNS
  - Whether a complete ground-truth induction circuit would pass the same normalized control gates.
  - Whether failure is primarily incomplete head coverage, the c_proj/all-position patch site, mismatch between IOI-derived heads and random-token induction, or distributed/nonlinear computation.
  - Cross-model and natural-language generality; only GPT-2 and one generated development assay were evaluated.
