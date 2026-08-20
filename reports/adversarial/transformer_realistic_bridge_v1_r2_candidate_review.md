VERDICT: SHIP
ONE-LINE: Both exact r2/r4 candidates are scientifically parity-bound, fail-closed, fully smoke-tested, and ready to lock.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)
  - `validate_gpu()` retains the parity-preserved duplicate deterministic-algorithms call.
  - The two-step supervised smoke is an execution smoke, not evidence that the fitted skyline succeeds after two steps; ground truth is the passing positive control.

CHECKS RUN
  - r2 PLAN review → SHIP; authoritative PRELOCK SHA-256 `f21df200…`.
  - Recovery verifier `check-prelock` → PASS with `payloads_accessed=false`; authorization, both old terminals/freezes/inventories/review bindings, normalized configs, scientific ASTs, superseded index, source, and launcher parity recomputed.
  - Old preserved hashes → bridge/method freezes `59491a94…` / `32da54a8…`; review bindings `081041be…` / `7af99aba…`; terminals `2d5c669c…` / `f9ace474…`.
  - Both terminals → `PRELAUNCH_SOFTWARE_STOP`, no tmux/forward/training/payload access, `no_retry_under_namespace=true`.
  - Candidate preflight → PASS; paper 75 claims / 357 bindings; v1.1 preservation PASS.
  - Full exact r2 pytest suite → 14 passed in 22.62 s.
  - CPU and GPU bridge r4 smokes → all six regimes and independent NumPy/repeated-live QA passed, 1,152 rows each.
  - Calibration → all six fixtures passed; routing and incomplete-controller mutations rejected; `scientific_panels_read=false`.
  - Methods GPU smoke → 18 methods technical, 6,912 records; GT matched gate passed; seven incomplete controls, random/PCA/DiffMean/LEACE, three SAE and three supervised seeds executed; all six checkpoint hashes verified.
  - No K2 import/implementation; `k2_evaluated=false`.
  - No r2 lock/freeze/result/run-provenance namespace existed during review.
  - No scientific JSONL was listed, statted, hashed, or opened.

CONTRACT COVERAGE
  - r2 technical successor/no-retry semantics → met.
  - Exact scientific AST/config parity and staleness protection → met.
  - Both old freezes/bindings/terminals preserved → met.
  - Bridge GT/oracle/skyline/incomplete controls → met.
  - All 18 method paths and learned seeds executable → met.
  - Conditional methods firewall and no K2 → met.
  - Deferred RUN_ROOT rendering under `set -u` → met.
  - Pre-lock absence and namespace immutability → met.
  - Scientific payload firewall → met.

UNKNOWNS
  - Scientific payload continuity, experiment freezes, exact-frozen reviews, launch bindings, GPU selection, and scientific outcomes remain later gates.
