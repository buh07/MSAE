VERDICT: SHIP
ONE-LINE: The exact r3 candidate satisfies the bridge, methods, preservation, firewall, and conditional-execution contracts.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)

CHECKS RUN
  - Exact current source, configs, tests, launcher, paper, ledger, preservation artifacts, and four r3 QA artifacts → inspected.
  - Targeted pytest suite → 13 passed in 26.83s.
  - Python compilation for both experiment scripts → PASS.
  - Launcher `bash -n` → PASS.
  - Candidate preflight → PASS; 75 claims, 357 evidence bindings, and v1.1 preservation verified.
  - r3 CPU bridge smoke → all six regimes passed with 192/192 rows each; deterministic and NumPy-oracle QA passed.
  - r3 GPU bridge smoke → all six regimes passed with 192/192 rows each; deterministic and NumPy-oracle QA passed.
  - GPU-oracle discrepancy audit → maximum absolute error `1.71661376953125e-05 < 2e-05`; maximum relative L2 approximately `1.83e-07 < 1e-05`.
  - r3 calibration → every regime passed; registered routing and incomplete-control mutations were rejected.
  - r3 GPU methods smoke → 18 methods completed technically; ground truth passed all matched gates; target support passed; every incomplete control remained registered as a negative control.
  - Learned-method smoke → SAE and supervised descriptive seed aggregates were emitted and remained nongating.
  - Checkpoint audit → all six `.pt` files matched the sizes and SHA-256 hashes in `FIT_SUMMARY.json`.
  - Prepared scientific roots → no panel files exist; none were opened or scored.
  - Ruff → unavailable.

CONTRACT COVERAGE
  - Preserve constructed-copy v1.1 and its scoped paper contrast → met.
  - Keep K2 closed and prohibit natural-model generalization → met.
  - Separate the factor-hybrid oracle from the shared insertion path → met.
  - Detect a broken insertion operator rather than passing through oracle self-comparison → met.
  - Exercise soft attention, residual bypass, layer normalization, correlated factors, superposition, and controlled noise → met.
  - Include every registered incomplete factor/path controller → met.
  - Use same-site, same-path matched controls → met.
  - Hard-gate matched-control margin → met.
  - Retain zero-output methods as explicit failures → met.
  - Enforce overall, per-block, and per-target support → met.
  - Require every learned seed to pass independently → met.
  - Keep seed aggregates descriptive → met.
  - Hash every learned checkpoint → met.
  - Keep methods unopened and report `representation_methods_evaluated=false` when the bridge stops → met.
  - Prevent preopening candidate operations from accessing scientific payloads → met.
  - Lock generators before payload creation and separately freeze bridge/method protocols before opening → met in the candidate lifecycle.
  - Launch once under tmux on a free UUID-locked GPU → met in the launcher candidate.

UNKNOWNS
  - Generator locks, generated payload metadata, experiment freezes, and frozen-review bindings do not yet exist; they require the planned independent exact-frozen audit before scientific launch.
