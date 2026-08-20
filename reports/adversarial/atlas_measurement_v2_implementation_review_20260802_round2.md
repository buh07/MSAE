# Atlas measurement v2 implementation adversarial review — round 2

VERDICT: REVISE

## One-line

Core fixes are sound, but legacy tasks still influenced v2 eligibility and two exact safety contracts remained incomplete.

## Revisions requested

1. Add per-input required/diagnostic status so nested historical tasks cannot block v2 task measurability.
2. Exercise the CLI safe-refusal path while denying file/process/network helpers, and fail closed when process evidence is unavailable.
3. Make residual CKA degeneracy return structured undefined reasons instead of aborting.
4. Reject empty expected cache identity values, validate endpoint reason types, and move the K2 map-coupling note into cited historical code context.

## Resolution

- Config now marks 39 decision-required files and 15 diagnostics. Endpoint aggregation uses only required files; the report labels every projected task as `required` or `diagnostic`.
- Deny tests cover CLI refusal, row-file open, socket/connect/DNS, subprocess, `os.system`, spawn, and posix-spawn helpers. `/proc` evidence now fails closed when unavailable.
- Residual CKA returns `shape_mismatch`, `row_mismatch`, `nonfinite`, or `insufficient_residual_df` without aborting.
- Cache expected identities must be non-empty; endpoint reasons must be string sequences; K2 coupling is in a separate file:line-cited historical context section.

## Checks run by reviewer

- 28 targeted tests passed before the revisions.
- Compilation and config/report digest checks passed.
- Process snapshots were available with zero experiment-marker matches.
