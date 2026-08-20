VERDICT: REVISE
ONE-LINE: Pair support is repaired, but the pooled specificity population is not yet prescore-attested.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)
  - [high] scripts/atlas_discovery_v3.py:1855-1889; docs/rfc-atlas-v3-1-discovery-factor-atlas.md:223-233 — `all_required_measurement_populations_eligible` checks observational tasks and individual interventions, but not the required four-class matched/capped cross-family population or its node-bootstrap completeness.
    reasoning — individual counts of 89--540 components do not guarantee support after intersection/capping within `(start-distance, UPOS, capitalization, word-length)` strata. The protocol also requires at least 490/500 finite pooled document-node draws, but the preflight contains no corresponding population, class counts, fold counts, or draw count.
    impact — representation inference could start and only later discover another structurally ineligible specificity endpoint, recreating the measurement brittleness this prescore gate was designed to prevent.
    fix — before neural inference, freeze and materialize the label-only cross-family row matching/capping algorithm; report retained rows and genuine documents per construct and fold, exclusion reasons, and 500 shared-node-bootstrap class-coverage draws; include this endpoint in the global prescore predicate and retire without relaxation if it fails.
  - [high] docs/rfc-atlas-v3-1-discovery-factor-atlas.md:106,171; scripts/atlas_discovery_v3.py:26,511,992-1002 — the signed protocol still names the v3.0 output root and v3.0 sham-order namespace, while the bound implementation uses `data/atlas_discovery_v3_1` and `atlas_discovery_v3_1`.
    reasoning — the sham namespace changes deterministic relational row selection, so this is not solely editorial; the protocol and generated population specify different hashes.
    impact — the frozen population cannot be reconstructed from the protocol alone, and correcting the protocol after scoring would be post hoc.
    fix — correct both literals to the exact v3.1 roots/namespace, update protocol/config/inventory hashes, and perform one final byte-identical label-only rebuild before authorization.

NITS            (optional, cap at 5)
  - docs/rfc-atlas-v3-1-discovery-factor-atlas.md:333 — rename the remaining generic “v3” definition-of-done wording to “v3.1” for unambiguous lineage.

CHECKS RUN
  - `.venv-atlas/bin/python -m pytest -q -p no:cacheprovider tests/test_atlas_discovery_v3.py` → 18 passed.
  - `.venv-atlas/bin/python scripts/run_atlas_discovery_v3.py --config configs/atlas_discovery_v3/run.json --stage validate-config` → config/inventory valid; representation scoring remains unauthorized.
  - retirement/failure-marker digest verification → v3.0 and v3.1-attempt1 preflight/manifest hashes all match their terminal markers.
  - final preflight binding verification → config and prepared-manifest SHA-256 values match; no representation scoring or neural training recorded.
  - `reports/atlas_v3_1_rebuild_check.json` inspection → PASS over 37 nonvolatile files with byte-identical preflight and manifest hashes.

CONTRACT COVERAGE
  - v3.0 immutable retirement → met — digest-bound `FAILED_PRESCORE` marker records no inference/training.
  - v3.1 attempt1 retirement → met — digest-bound `RETIRED_PRESCORE` marker precedes inference.
  - endpoint-local component construction → met — singleton donor-free components and disjoint two-document maximum matchings are asserted in code.
  - individual intervention support → met — both sources exceed 50 total and 5 per fold for donor-linked endpoints.
  - pooled cross-endpoint dependence → met in design/unit helper — one document map and product weights preserve shared-document dependence.
  - pooled specificity measurability → unmet — no frozen joint matched/capped population or pooled finite-draw audit appears in preflight.
  - exact protocol/implementation identity → partial — two stale v3.0 literals conflict with the v3.1 implementation.
  - reproducible label-only rebuild → met — 37 nonvolatile artifacts rebuild byte-identically.
  - source firewall → met — exact EWT/GUM paths and digests are bound; ledger records no forbidden/blind inputs.

UNKNOWNS
  - Whether the frozen four-class stratum matching retains adequate per-construct/per-fold document support in GUM.
  - Whether at least 490/500 shared-node bootstrap draws remain finite after that joint population is frozen.
  - Representation extraction and numerical QA are not implemented yet and were outside this prescore review.
