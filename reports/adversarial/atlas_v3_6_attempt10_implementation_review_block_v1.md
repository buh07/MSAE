VERDICT: BLOCK
ONE-LINE: Held-out PASS can bypass replay/provenance checks, and the asynchronous launcher mishandles legitimate fast exits.

BLOCKERS
  - [critical] scripts/run_atlas_rope_v6.py:471-484,487-507 — GENTLE’s exact cached replay is recorded but never gates bundle status or `GENTLE_PASS`.
    reasoning — `_extract_gentle` sets bundle status solely from `score["status"]`; `verify_gentle_bundle` only recomputes the approximate grid score. Neither requires `exact_cached_replay["status"] == "PASS"` nor independently recomputes it.
    impact — Attempt 10 can authorize science despite failing one of its required numerical-QA checks, violating PLAN_ATTEMPT10.md:5,17,55.
    fix — Make bundle PASS require both grid PASS and exact-replay PASS; in `verify_gentle_bundle`, independently recompute exact replay from cached arrays and row IDs, compare it with the signed payload, and reject any non-PASS replay before writing `GENTLE_PASS`.

  - [high] scripts/run_atlas_rope_v6.py:175-184,187-219,228-273 — imported Attempt-9 history is not verified as the exact frozen signed history.
    reasoning — `_verify_attempt9_terminal` does not enforce the SHA pinned in `configs/atlas_rope_v6/amendment.json:2-5` or validate the terminal’s lineage hashes. `_load_grid_history` verifies artifact children but not bundle schema/source/kind, panel hash/counts, authorization lineage, canonical array hashes, signed replay result, runtime identity, or no-training fields. The sentinel verifier similarly omits panel, authorization, row-ID, canonical-hash, runtime, and signed-score lineage checks.
    impact — Cap selection and the post-validation QA bridge are weaker than the plan’s “exact signed caches, row order, repeats, replay, and independent scores” requirement at PLAN_ATTEMPT10.md:24-27.
    fix — Load and enforce the amendment’s terminal SHA; bind terminal lineage to the exact GUM completion SHAs; port the relevant Attempt-9 bundle-verifier checks while allowing its expected grid FAIL; fully verify sentinel row IDs, panel/auth/runtime/canonical hashes and signed pair scores before rescoring under Attempt-10 caps.

  - [high] scripts/run_atlas_rope_v6.py:487-494 — held-out GENTLE verification omits most of the frozen measurement contract.
    reasoning — `verify_gentle_bundle` checks only child inventory/shape/repeat equality indirectly through `_load_grid_history`, then score equality. It never validates schema/source/kind, panel and logical-count lineage, validation-authorization hash, runtime pre/postflight, canonical hashes, inference/no-training attestations, or cached replay.
    impact — A signed but misidentified or runtime-drifted held-out bundle could promote to GENTLE PASS and science authorization, violating the single held-out validation gate.
    fix — Add a GENTLE-specific verifier equivalent to the complete Attempt-9 grid verifier, including exact panel, authorization, runtime, replay, canonical-array, identity, and no-training checks.

  - [high] scripts/launch_atlas_rope_v6_tmux.sh:14-16 — a legitimate fast terminal/completion races the unconditional `tmux display-message`.
    reasoning — Under `set -e`, if the one-shot session exits between `new-session` and `display-message`, line 16 fails without checking the signed terminal/completion paths. The script therefore does not implement the plan’s accepted fast-exit outcome.
    impact — The caller cannot distinguish a legitimate completed/terminalized one-shot run from an unexpected launch failure and may incorrectly retry.
    fix — After launch, branch on `tmux has-session`; if alive, report pane PID/command. If gone, verify and report a signed terminal or signed science completion; otherwise fail as an unexpected early exit. Never relaunch either signed outcome.

  - [high] configs/atlas_rope_v6/science_adapter.json:14,280,294 — the frozen Attempt-10 adapter still declares Attempt-9 result, science-root, and authorization paths.
    reasoning — `verify_frozen_contract` at scripts/run_atlas_rope_v6_science.py:90-122 does not validate these fields, while runtime code silently uses separate Attempt-10 constants at lines 71-73.
    impact — The reviewed/frozen configuration has false namespace and authorization lineage, contradicting PLAN_ATTEMPT10.md:23 and making the signed adapter contract internally inconsistent.
    fix — Change all three fields to the Attempt-10 paths and make `verify_frozen_contract` assert they equal `RESULT_ROOT`, `SCIENCE_ROOT`, and `SCIENCE_AUTHORIZATION`.

REVISIONS
  - [medium] scripts/run_atlas_rope_v6.py:41-42,60-64 — the amendment config is inventoried but never used to drive or validate frozen caps/search order.
    reasoning — constants independently duplicate the JSON values, so a future config/code mismatch can pass `_verify_implementation_candidate`.
    impact — weakens the claim that the signed cap candidate derives from the frozen amendment.
    fix — Parse the amendment once and assert terminal SHA, budgets, grids, required selected caps, source counts, validation source, and permissions exactly match executable constants before retirement or cap selection.

  - [medium] scripts/run_atlas_rope_v6.py:327-331 — retirement records `attempt9_required_absences` as an empty result rather than the exact paths attested absent.
    reasoning — `_attempt9_required_absences()` returns only present violations; after passing, the signed artifact stores `[]`.
    impact — the signed retirement cannot independently show which downstream paths were checked.
    fix — freeze the complete expected-absence path list and store both that list and `present=[]`.

NITS
  - scripts/atlas_rope_v6.py:423 — stale error text says “another attempt-8 process” in Attempt-10 code.
  - scripts/run_atlas_rope_v6_science.py:64 — `_verify_attempt8_history` is imported but unused.

CHECKS RUN
  - `sha256sum configs/atlas_rope_v6/implementation_candidate.json` → exact requested SHA `1633d39dd9eec1d9658171461816faa84e64eabc7e1a1e6994537dfa4c1d5532`.
  - inventory hash/size verification for every candidate-listed file → all 12 entries exact.
  - `.venv-atlas/bin/python -m pytest -q tests/test_atlas_rope_v6.py tests/test_atlas_rope_v6_science.py` → 16 passed, 1 warning.
  - AST hashes of `row_error_metrics`, `score_cell`, and `score_grid` in v5 versus v6 → all byte-identical.
  - static inspection of cap search → 60-cell evaluator, ascending Cartesian order, first-passing selection, and unique coordinatewise minimum logic are implemented as planned.
  - no GPU/model inference run.

CONTRACT COVERAGE
  - Attempt-9 remains immutable and no EWT/GUM rerun path exists → met — fixed read-only histories and only GENTLE technical forward are present.
  - Budget-aligned 60-cell cap selection → met — identical v5/v6 evaluator hashes and tests select `2e-5 / 5e-11`.
  - Exact signed-history verification → unmet — bundle identity, terminal hash/lineage, replay, panel/auth/runtime checks are incomplete.
  - GENTLE-only one-shot validation after authorization → partial — authorization/order exists, but PASS omits mandatory replay/provenance gates.
  - Frozen exploratory science after GENTLE PASS → partial — runtime gate exists, but adapter config declares stale Attempt-9 paths.
  - Endpoint failure terminalization → met — pipeline ERR trap and create-once terminal guard cover downstream stages.
  - Fast terminal/completion accepted without relaunch → unmet — launcher has an unhandled session-exit race.
  - No neural training/checkpoint path → met — static inventory and tests show inference-only code.

UNKNOWNS
  - GENTLE’s operationally unopened status cannot exclude unlogged historical inference, as the plan itself acknowledges.
  - GPU/runtime behavior was not exercised under the read-only, no-model-inference review constraint.
  - The 55 Attempt-9 and 44 frozen regressions were not rerun; only their signed verification report and the focused 16-test suite were checked.
