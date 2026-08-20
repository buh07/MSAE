CLAIM: SUPPORTED
SUMMARY: V4 recovered structural support but no matcher produced two balance-eligible sources; no relational-science or training claim is authorized.

BLOCKERS
  - None for the scoped claim above.

REVISIONS
  - `results/relational_measurement_v4_opened_development1/result.json` — describe
    `STOP_MEASUREMENT_DESIGN_UNCALIBRATED` precisely: no source passed the complete real-covariate
    gate, so zero synthetic panels were scheduled. Do not imply that either primary estimator was
    empirically calibrated and failed.
  - `data/relational_measurement_v4/prepared.json` — report v4 as an opened-development measurement
    study, not confirmatory relational-representation evidence. It loaded no model weights, ran no
    model forward, accessed no activation cache or fresh corpus, and trained no model.
  - `reports/provenance/relational_measurement_v4_tmux.log` — retain the weighted-scaler runtime
    warnings as technical context. Downstream finite-value checks and the signed verifier passed, but
    the warnings should not be silently omitted from a methods appendix.

EVIDENCE CHECKED
  - `reports/provenance/relational_measurement_v4_closure_v1.json` and strict lifecycle verifier —
    `SCIENTIFIC_TERMINAL`; owner-signed `TERMINAL_COMPLETE`, exact result/config/prepared/opening
    lineage, decision `STOP_MEASUREMENT_DESIGN_UNCALIBRATED`, no nomination, and no retry authority.
  - `results/relational_measurement_v4_opened_development1/result.json` — simulations are empty and
    all forbidden-access/training flags are false; no learned model is authorized.
  - `data/relational_measurement_v4/prepared.json` — exact-v3 matching had only EWT structurally
    supported; coarse-exact and optimal-caliper each raised structural support to five sources, but
    every source failed at least one complete balance/positivity gate, leaving no eligible or selected
    source under any matcher and `scheduled_panels=0`.
  - `data/relational_measurement_v4/prepared.json` — the dominant failures were morphology-indicator
    imbalance and propensity overlap: coarse-exact maximum eligible-panel indicator SMDs ranged
    0.1443–0.5101 and propensity central fractions 0.824–0.946; optimal-caliper improved numeric
    balance but indicator SMDs remained 0.1255–0.3712 and propensity central fractions 0.839–0.930,
    against frozen limits 0.10 and 0.99 respectively.
  - `data/relational_measurement_v4/prepared.json` — independent-support gates themselves were often
    repaired: Czech, EWT, Latvian, Spanish, and Ukrainian each reached 150 components/500 pairs under
    both alternative matchers. This distinguishes recovered sample quantity from failed covariate
    comparability.
  - `reports/provenance/relational_measurement_v4_tests.xml`, smoke artifacts, and candidate review —
    124 tests passed; two smoke reports were byte-identical; final adversarial candidate verdict was
    SHIP before authorization.
  - `reports/provenance/relational_measurement_v4_tmux.log` — create-once execution completed without
    a failure artifact; six weighted-scaler numerical warnings occurred during preparation/rebuild,
    but no nonfinite result survived the frozen checks.

UNKNOWNS
  - Whether a newly defined conditional estimand, propensity-based design, controlled counterfactual
    corpus, or different relational object can achieve two-source overlap without outcome-conditioned
    threshold changes.
  - Whether child-head differences, concatenations, QK links, attention-head outputs, or transported
    values show relation-specific functional evidence; v4 intentionally performed no representation
    scoring.
  - Whether either primary estimator passes the six synthetic DGPs on a genuinely eligible panel;
    no v4 panel reached that stage.
  - Whether any favorable relational result would replicate on genuinely fresh corpora or generalize
    across layers, models, languages, or nonlinear representations.
