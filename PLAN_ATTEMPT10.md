# Atlas v3.6 attempt 10 — budget-aligned technical amendment

## Goal

Apply the smallest principled repair to Attempt 9: preserve its signed terminal, import EWT and GUM as opened technical calibration history, select approximate-equivariance caps with the same cell-budget evaluator used at validation, validate once on still-unopened GENTLE, and conditionally run the byte-frozen scientific atlas. Launch the authorized pipeline in tmux and return without waiting for completion. Never train a neural model.

## Context

Attempt 9 passed exact cached replay, byte-identical repeated live inference, observer-safe RoPE diagnosis, every fresh GUM sentinel, and 29/30 GUM grid cells. It terminalized because one `9-16|shift=64` row exceeded the zero-failure relative-L2 and cosine caps. GUM is now opened and may only be calibration. GENTLE remains unopened. The scientific atlas never ran.

## Constraints

- Attempt 7, 8, and 9 artifacts remain immutable; Attempt 9 stays `TERMINAL_GUM_VALIDATION_FAILED` with no retry.
- No new EWT or GUM forward. Import their signed arrays/results only as disclosed calibration history.
- Preserve `atol=2e-5`, `rtol=5e-6`, coordinate budgets (30 elements / 2 rows per cell), panels, rows, ordering, runtime, model, and all scientific definitions.
- Extend only the relative-L2 grid with `2e-5`; retain cosine grid and select `5e-11` mechanically. Select caps by running the exact validation cell evaluator over the EWT+GUM calibration union, not by a global maximum inconsistent with coordinate budgets.
- GENTLE is operationally unopened under verified recorded lineage and required-path absence; this does not prove that no unlogged historical invocation occurred. It is the sole validation panel for this narrow technical amendment and must pass all 30 cells. Any failure signs a no-retry terminal.
- Freeze and independently `/adversarial` review implementation before the first Attempt-10 signature, and validation freeze before opening GENTLE.
- Science remains inaccessible until signed GENTLE PASS. No optimizer, backward, parameter update, checkpoint, technical labels, or training.

## Approach

1. Create Attempt-10-only signer schemas, controller, science adapter, config, tests, reports, and run/result namespaces. Reuse the byte-frozen model/runtime and scientific functions by exact hash. The adapter is a semantically unchanged science computation plus reviewed namespace, authorization, and technical-QA bridge.
2. Verify Attempt-9 terminal, exact run inventory, required downstream absences, EWT/GUM signed caches, row order, repeats, replay, and independent scores. Freeze an unsigned implementation candidate and obtain `/adversarial SHIP` before signing.
3. Sign Attempt-9 retirement, opened-calibration import, and a budget-aligned cap candidate. Cap selection uses exactly 60 grid cells: the 30 signed Attempt-8 EWT cells and 30 signed Attempt-9 GUM cells, each reconstructed from its 200-row base reference, 1,200-row shifted cache, and 200-row manifest. Attempt-7's 72 retained legacy/fresh family rows remain separately verified calibration/replay evidence and must pass strict family scoring under the selected caps, but they do not enter the 40-row cell search because they have no comparable shift-by-length partition. Freeze `atol=2e-5`; search the Cartesian product of relative-L2 `[2e-6,5e-6,1e-5,2e-5]` outer-ascending and cosine `[1e-11,5e-11,1e-10]` inner-ascending; choose the first pair for which every one of the 60 cells passes the unchanged evaluator and budgets. Require the unique coordinatewise-minimal result to be relative L2 `2e-5`, cosine `5e-11`; otherwise stop before validation.
4. Freeze a GENTLE-only validation candidate binding implementation, cap derivation, unchanged science adapter, and unopened GENTLE evidence. Obtain `/adversarial SHIP`, then sign authorization.
5. Freeze an explicit Attempt-10 QA bridge before validation. It independently re-scores signed Attempt-7 EWT families, signed Attempt-8 EWT grid, and signed Attempt-9 GUM grid under the selected caps, never requires a nonexistent Attempt-9 `GUM_PASS`, and cannot introduce a stricter post-validation gate. Launch a tmux pipeline that runs GENTLE once; on PASS signs science authorization and runs the same frozen EWT/GUM scientific computation. GUM's use in technical calibration is disclosed; although technical panels are label-free and sequence-firewalled from science rows, the resulting atlas is exploratory rather than independent confirmation. Any GENTLE, authorization, extraction, bridge, or analysis failure creates an Attempt-10 signed no-retry terminal and stops. Return after observing either a live authorized child or an already-signed terminal/completion; never relaunch a fast legitimate exit.

## Milestones

### M1 — Unsigned amendment and implementation review
- [ ] Implement and test Attempt-10 namespaces, exact history verification, budget-aligned cap selection, GENTLE validation, terminal guards, and frozen-science adapter.
- [ ] Verify no Attempt-10 run root, signature, model call, or training exists.
- [ ] Obtain implementation `/adversarial SHIP`.

Acceptance: exact implementation/report inventory agrees; tests and frozen regressions pass; all previous attempts remain byte-identical.

### M2 — Signed retirement, calibration, and validation freeze
- [ ] Sign Attempt-9 retirement as the first Attempt-10 artifact.
- [ ] Import the exact 30-cell Attempt-8 EWT plus 30-cell Attempt-9 GUM calibration union without new forwards; verify Attempt-7's 72 family rows separately without using them in cell-based cap selection.
- [ ] Sign caps `2e-5 / 2e-5 / 5e-11` selected by exact cell scoring.
- [ ] Create and obtain `/adversarial SHIP` for the GENTLE validation freeze; sign validation authorization.

Acceptance: GENTLE/science outputs remain absent immediately before authorization; cap lineage excludes GENTLE.

### M3 — Asynchronous execution
- [ ] Launch one tmux pipeline: GENTLE → conditional science authorization → EWT/GUM extraction → semantically unchanged analysis, with create-once artifacts and signed terminalization on every downstream failure.
- [ ] Confirm session, pane command, log path, signed authorization, and either a live child PID or a signed terminal/completion. Never relaunch after a legitimate fast exit.

Acceptance: return without waiting once the authorized child is live or the one-shot pipeline has already produced a signed terminal/completion; no training path exists and no legitimate fast exit is relaunched.

## Definition of done

- [ ] Attempt 9 remains immutable and retired; no EWT/GUM rerun occurs.
- [ ] Calibration and validation evaluators are identical and budget-aligned.
- [ ] GENTLE runs only after two adversarial SHIP gates and signed authorization.
- [ ] The frozen scientific computation runs only after signed GENTLE PASS and is labeled exploratory because GUM informed technical calibration.
- [ ] On return, the tmux pipeline is alive or has already produced a signed terminal/completion; no relaunch occurs.
- [ ] No neural training/checkpoint path exists.

## Verification plan

- `check-plan`, `py_compile`, Attempt-10 tests, 55 Attempt-9 tests, and 44 frozen Attempt-7 regressions.
- Exact SHA/inventory verification for Attempt 9, imported calibration arrays, frozen science functions, and candidates.
- Synthetic regression where Attempt-9 GUM fails old caps but EWT+GUM passes mechanically selected budget-aligned caps.
- Tests that EWT/GUM model calls are impossible and GENTLE/science are authorization-gated.
- `/adversarial SHIP` on implementation and validation freeze.
- tmux session/pane/PID/log and GPU-process observation after launch.

## Risks and one-way doors

- **Post-hoc overfit:** GUM informed the cap. Mitigation: disclose it as calibration, freeze before GENTLE, never call GUM validation again.
- **Single held-out corpus:** GENTLE is the sole validation for the narrow technical repair. Claims must remain runtime/panel-specific.
- **GUM dual role:** GUM technical arrays tune numerical QA and GUM supplies a disjoint scientific corpus. Mitigation: sequence firewall, no label use during technical calibration, exact disclosure, and exploratory—not independently confirmatory—scientific claims.
- **Threshold chasing:** no further cap change is authorized; GENTLE failure terminalizes.
- **Scientific drift:** exact source/function/config hashes and a pre-validation adapter freeze.
- **Asynchronous partial failure:** shell uses `set -euo pipefail`, signed terminalization, stage-specific logs/status, and conditional gates.

## Deviations log

- 2026-08-03: Attempt 10 proposed after Attempt 9's signed GUM technical terminal. No Attempt-10 artifacts, model calls, or training existed at plan creation.
- 2026-08-03: First plan review returned `REVISE`. Specified the exact 60-cell EWT/GUM cap-selection union and Cartesian search order; separated Attempt-7's non-cell 72-row evidence; froze an explicit GUM-history QA bridge; bounded GENTLE unopened claims; disclosed GUM's technical/scientific dual role and exploratory claim status; and made fast terminal/completion plus fail-closed downstream terminalization valid asynchronous outcomes.
