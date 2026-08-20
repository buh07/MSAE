VERDICT: BLOCK
BOUND_SHA256: b0ceca56e919c1f5e10b1678dc01c796e20022c4c97fbed50e9ab4a70532d227

ONE-LINE: Scientific recovery is conformant, but the shared stale-lock race breaks exclusive GPU ownership.

BLOCKERS
  - [critical] scripts/launch_trained_control_next_studies_v1_r2_tmux.sh:45-53 — failed stale-lock reacquisition proceeds as though it succeeded.
    reasoning — a competing launcher can create the path after line 50’s `mv`; this launcher’s failed `mkdir` is ignored, after which it replaces the competitor’s metadata and cleanup deletes the active lock. A live-PID mock reproduced this exactly.
    impact — two bridge/control workers can be assigned the same physical GPU, invalidating resource isolation and runtime reliability.
    fix — fail immediately when the post-reclamation atomic `mkdir` loses; add the live-owner race regression.

REVISIONS
  - None.

NITS
  - None.

CHECKS RUN
  - Candidate SHA-256 → matched `b0ceca56…`.
  - Protocol parity and R1 preservation → PASS.
  - Shared non-panel suite → `18 passed in 5.29s`.
  - Candidate transitive bindings → PASS.
  - Exact source-diff certificate → PASS.
  - Stale-reacquisition race mock → live replacement lock was deleted.
  - Scientific panels → not accessed.

CONTRACT COVERAGE
  - Float64 rank/condition repair → met by bound source and tests.
  - Four-generator basis/spectrum/projector/serialization checks → met by bound tests.
  - Smoke-only technical QA → met.
  - Scientific protocol parity and R1 lineage → met.
  - Previously identified cleanup paths → met.
  - Stale-lock atomic ownership → unmet.
  - Candidate transitive binding → met.

UNKNOWNS
  - Full panel-touching tests and CUDA checks were not independently rerun under the no-panel-access constraint.
  - Superseded d71cc6d0 candidate exists, but no filesystem review transcript bound to that exact hash was found.
  - Freeze, lock, and frozen-review artifacts remain pending.
