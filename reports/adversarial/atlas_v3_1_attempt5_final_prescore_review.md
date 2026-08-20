VERDICT: SHIP
ONE-LINE: Attempt 5 is support-complete, reproducible, source-common, and ready for scoring configuration plus numerical QA.

BLOCKERS        (must fix before proceeding; empty if none)
  - None.

REVISIONS       (should fix; not blocking)
  - None.

NITS            (optional, cap at 5)
  - data/atlas_discovery_v3_1_attempt5/preflight.json:69-76 — GUM→EWT true-context unseen-cell rate is 19.05%, only 0.95 percentage points below the frozen ceiling. Preserve the exact gate and prominently report this boundary sensitivity; the fit-observed-subset sign check remains mandatory.
  - configs/atlas_discovery_v3/run.json:2-8 — the current config correctly remains prescore-only. Create an append-only scoring authorization/config that binds this config, preflight, manifest, allowlist, rebuild report, and scorer inventory; do not mutate or overwrite the prescore evidence.

CHECKS RUN
  - `.venv-atlas/bin/python scripts/run_atlas_discovery_v3.py --config configs/atlas_discovery_v3/run.json --stage validate-config` → config/protocol/inventory valid; representation scoring remains unauthorized.
  - `.venv-atlas/bin/python -m pytest -q -p no:cacheprovider tests/test_atlas_discovery_v3.py` → 19 passed.
  - attempt-4 SHA and allowlist derivation check → pinned attempt-4 preflight hash matches; serialized 94 cells exactly equal the two source-pooled candidate-cell intersection.
  - attempt-5 preflight binding check → config and prepared-manifest SHA-256 values match.
  - independent rebuild comparison → all 39 nonvolatile files are byte-identical; `reports/atlas_v3_1_attempt5_rebuild_check.json` is `PASS`.
  - opened-input ledger/run-root inspection → only pinned EWT, GUM, tokenizer, protocol/config, and common-cell artifact are declared; forbidden/blind flag is false; scoring run root is absent.

CONTRACT COVERAGE
  - source-common population provenance → met — the exact 94-cell allowlist and attempt-4 parent hash are serialized and inventory-bound.
  - class/document/fold support → met — EWT retains 147 and GUM 74 rows and target documents per class; fold minima are 24 and 12.
  - bootstrap completeness → met — both sources have 500/500 finite shared-node draws.
  - cross-source common support → met — maxima are 5.41% EWT→GUM and 19.05% GUM→EWT; minimum common rows/documents is 70.
  - individual endpoint support → met — every required observational and intervention endpoint is eligible.
  - global prescore decision → met — `all_required_measurement_populations_eligible=true` includes individual, joint, and cross-source support predicates.
  - deterministic rebuild → met — 39 nonvolatile artifacts reproduce byte-for-byte.
  - source firewall and lineage → met — fresh attempt-5 schema/root/IDs are bound; earlier failed attempts remain separate; no forbidden source was opened.
  - no inference or training → met — preflight records both false and no scoring run root exists.
  - interpretation limit → met — the RFC calls this source-common adjusted predictive specificity, not exact matching, causality, confirmation, or generalization.

UNKNOWNS
  - Scoring implementation, cache writer, and numerical-QA artifacts do not yet exist and require their own diff review before non-null metrics are opened.
  - The frozen repeat-inference tolerance may still fail; that must terminate technical eligibility rather than trigger relaxation.
  - This SHIP verdict authorizes scoring configuration and numerical QA only, never neural training.
