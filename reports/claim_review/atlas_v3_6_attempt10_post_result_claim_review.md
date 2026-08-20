CLAIM: BLOCK
SUMMARY: Attempt 10 validates deterministic replay, not the position/context hypothesis or broad approximate-equivariance validity.

BLOCKERS
  - `pilot_runs/20260803_atlas_rope_technical_v6/TERMINAL.json` — signed `TERMINAL_GENTLE_VALIDATION_FAILED` with no retry; no science authorization, caches, or result root exists — no position/context scientific claim was tested.
  - `pilot_runs/20260803_atlas_rope_technical_v6/validation/GENTLE_grid/COMPLETE.json` — 2/30 cells fail the frozen zero-row cosine criterion — the claim that the EWT+GUM-calibrated approximate-equivariance gate generalizes to GENTLE is false under the preregistered rule.

REVISIONS
  - The exact cached replay and byte-identical repeated-inference claims are supported on GENTLE and should be reported separately from approximate RoPE equivariance.
  - The “narrow cosine-tail failure” interpretation is supported descriptively: both failures arise from one short-sequence row at shifts 32 and 64, with finite outputs, zero relative-L2 failures, and coordinate failures within budget. It remains panel/runtime-specific, not a universal mechanism claim.
  - Do not call Attempt 10 a scientific negative result. Call it a valid fail-closed technical-QA result that prevented the atlas from opening.
  - Before another held-out attempt, make the relative-L2 and cosine criteria mathematically coherent or nominate one primary normalized metric; the observed relative-L2 cap of `2e-5` permits directional errors that can exceed a cosine cap of `5e-11`.
  - Decouple RoPE-translation-dependent endpoints from atlas endpoints that do not rely on approximate translation equivariance so one technical control cannot erase all otherwise valid scientific measurements.

EVIDENCE CHECKED
  - Signed Attempt-10 terminal SHA `9e11622335af072f6f273596917fd729fe38cfd4c65dd18b883fd43cc06dc109` — terminal GENTLE failure, no retry.
  - Signed GENTLE completion SHA `6251dd3e07c011511dd58eaa942400c7b6fd9703745f57d3823ebe7d69ef4c90` — exact replay PASS, live repeats byte-identical, 28/30 cells PASS.
  - GENTLE cell scores — failures only at `4-8|shift=32` (`5.5402e-11`) and `4-8|shift=64` (`9.9494e-11`) versus cosine cap `5e-11`; relative-L2 maxima `1.1220e-5` and `1.5072e-5` remain below `2e-5`.
  - Row lineage — both failures are selected position 2 of `GENTLE_threat_kelly-12`; no nonfinite row occurred.
  - Output inventory — no `GENTLE_PASS`, science authorization, science cache, or `results/atlas_rope_v6_attempt10_science` exists.

UNKNOWNS
  - Whether the same numerical tail appears under a fresh runtime, model, layer, corpus, or independent technical panel.
  - Whether errors of relative magnitude at most `1.51e-5` have any material downstream effect on atlas estimators.
  - The scientific atlas outcome, because it never ran.
