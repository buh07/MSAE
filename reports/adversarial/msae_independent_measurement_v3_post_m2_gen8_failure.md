VERDICT: BLOCK
REVIEW_SCOPE: gen8_plan_implementation_fit
PLAN_SHA256: 7bd04a1c466d6a7e5cd6e570eece4e9a19395bf90d5b1e7cf2e4486616c2dfb4
PLAN_REVIEW_SHA256: 1a7dd1752694599322c80ad2d7e7bd03d306f7d618198a4cc6cd25a8f72720b1
SEALED_CONTENT_READS: 0

ONE-LINE: The reviewed supervisor change map cannot produce the registered executable gen8 entrypoint.

BLOCKERS

- [critical] `docs/plan-msae-independent-measurement-v3-post-m8-gen8.md:378-390` permits new/changed supervisor functions `_g8_*` and `main` while forbidding every other function and top-level-statement change, but the frozen substituted predecessor defines `main_gen8_matrix` and its executable bottom statement calls only that function (`scripts/run_msae_independent_measurement_v3_post_m2_gen7_tmux_test.py:1779-1780`, after substitution). The structural comparator keys non-definition statements by their top-level ordinal (`scripts/msae_independent_measurement_v3_post_m2_gen8_runtime.py:4360-4378`), so inserting any permitted new function before the bottom statement also changes that statement's key and is rejected. Replacing the inherited executable function/call is independently rejected because neither `main_gen8_matrix` nor the bottom `if` statement is authorized. Appending the new functions after the bottom statement cannot work when the file is executed because the inherited `SystemExit` occurs first. A decorator/default-expression side effect that secretly rebinds `main_gen8_matrix` would exploit the region checker rather than implement the reviewed control flow and is not acceptable authority.
  - Impact: the exact authorized real-tmux command can execute only the inherited 162-case gen7 matrix, never the reviewed ten-case durable gen8 journal/report path. `changed_regions.json` cannot be honestly published, so capability and every later one-way transition remain blocked.
  - Reproduction: construct the substituted gen7 supervisor baseline and make the honest changes `def main_gen8_matrix -> def main` plus `main_gen8_matrix() -> main()`; `_gen8_changed_region_rows` rejects `function:main_gen8_matrix`. Adding only a permitted `main` before the bottom entrypoint rejects `statement:If` because the ordinal changes.
  - Required resolution: terminate gen8 before `changed_regions.json` and capability, then use a disjoint reviewed successor plan that authorizes changing the actual `main_gen9_matrix` function and executable statement and gives inserted definitions stable comparator keys.

REVISIONS

- None. The reviewed plan/review bytes are create-once authority and cannot be retroactively amended.

CHECKS RUN

- Rehashed the exact reviewed plan and plan review; both match the controls above.
- Ran the structural comparator against the two in-memory supervisor mutations described above; both failed at the exact forbidden nodes.
- Confirmed `reports/analysis/msae_independent_measurement_v3_post_m2_gen8/` is absent, so no changed-region, containment, or capability one-way artifact was created.
- Inspected the three quarantined payloads by metadata policy only; their contents were not opened, hashed, copied, or mapped.
- No tmux, GPU query, model import/call, capability, setup, M4, signing, authorization, launch, confirmation scoring, or Stage C action was run.

UNKNOWNS

- The gen8 containment and capability behavior is unexecuted because the reviewed executable change boundary blocks implementation before those gates.
