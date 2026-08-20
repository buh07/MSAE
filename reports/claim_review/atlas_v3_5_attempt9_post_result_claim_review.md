CLAIM: BLOCK
SUMMARY: Attempt 9 supports a technical non-generalization result, not any position/content decomposition conclusion.

BLOCKERS
  - `pilot_runs/20260803_atlas_rope_technical_v5/TERMINAL.json` — signed `TERMINAL_GUM_VALIDATION_FAILED` with `no_retry_authorized=true` — the protocol stopped before GENTLE and before the scientific atlas.
  - `pilot_runs/20260803_atlas_rope_technical_v5/validation/GUM_grid/COMPLETE.json` — only 29/30 held-out cells passed and `GUM_PASS.json` is absent — the preregistered numerical-validity gate was not met.
  - `configs/atlas_rope_v5/SCIENCE_AUTHORIZATION.json` and `results/atlas_rope_v5_attempt9_science` — both absent — no raw-signal, intervention, projection-organization, or decomposition endpoint was computed.

REVISIONS
  - `reports/atlas_rope_v5/post_result_summary.json` — it is supported to report that exact cached replay and repeated live reference inference were byte-exact, yet EWT-calibrated approximate-equivariance caps failed to generalize to one GUM shift-by-length cell.
  - `pilot_runs/20260803_atlas_rope_technical_v5/diagnostic/hooked/summaries.json` — describe float32 rotary error followed by layerwise propagation as the best supported mechanism, not a proven cause of the fatal GUM coordinate; the diagnostic used selected EWT examples rather than the failing GUM row.
  - Do not describe 29/30 passing cells or the strict sentinel PASS as overall technical validation. The frozen rule required every cell, so the formal result is failure.
  - Do not alter caps or rerun GUM/GENTLE under Attempt 9. Any new robustness study must use a new protocol/namespace and disclose this held-out failure.

EVIDENCE CHECKED
  - `reports/atlas_rope_v5/post_result_summary.json` SHA-256 `a0a2909f3e8c72805924ead7684e81fe88628610b963ea6308351bd6a8403763` — exact signed lineage, cell metrics, fatal-row metadata, diagnostic aggregation, and downstream absences.
  - `pilot_runs/20260803_atlas_rope_technical_v5/TERMINAL.json` SHA-256 `83a369af693019c768284adfef5811bf7cc56eb9d226d8449e514abf12ecbf06` — authenticated terminal status and no-retry rule.
  - `pilot_runs/20260803_atlas_rope_technical_v5/validation/GUM_sentinel/COMPLETE.json` — strict 16-pair / 24-row sentinel PASS with exact replay and byte-identical live repeats.
  - `pilot_runs/20260803_atlas_rope_technical_v5/validation/GUM_grid/COMPLETE.json` — authenticated grid FAIL; fatal `9-16|shift=64` cell had one relative-L2 and one cosine failure.
  - `pilot_runs/20260803_atlas_rope_technical_v5/diagnostic/DIAGNOSTIC_COMPLETE.json` — hooked/unhooked observer equality and explicit threshold-tuning prohibition.
  - Required downstream files — GUM PASS, GENTLE grid/PASS, science authorization, science caches, and science result are absent.

UNKNOWNS
  - Whether the GUM outlier is representative of other corpora, GPUs, library builds, layers, or shift distributions.
  - Whether a scientifically justified robust estimator or distributional numerical criterion would generalize; testing that would be a new study, not a retry.
  - All substantive position/context decomposition outcomes, because none were run.
