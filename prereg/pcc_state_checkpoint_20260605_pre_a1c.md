# PCC State Checkpoint (Pre-A1c Confirmation)

## Purpose
This file freezes the PCC project state immediately before the A1c confirmation pass.

It exists to preserve the distinction between:
- the original frozen Stage A1 result,
- the A1b diagnostic explanation,
- and the prospective amendment draft.

## Frozen Record

### 1. Original Frozen A1 Result
- Run root:
  - `/jumbo/lisp/f004ndc/MSAE/pilot_runs/20260605_013756_pcc_stage_a1/`
- Primary decision artifact:
  - [stage_a1_decision.md](/jumbo/lisp/f004ndc/MSAE/pilot_runs/20260605_013756_pcc_stage_a1/stage_a1_decision.md)
- Frozen outcome:
  - `proceed_to_stage_b = false`

### 2. A1b Diagnostic Record
- Run root:
  - `/jumbo/lisp/f004ndc/MSAE/pilot_runs/20260605_030600_pcc_stage_a1b/`
- Primary diagnostic artifacts:
  - [stage_a1b_diagnostic.md](/jumbo/lisp/f004ndc/MSAE/pilot_runs/20260605_030600_pcc_stage_a1b/stage_a1b_diagnostic.md)
  - [stage_a1b_diagnostic_memo.md](/jumbo/lisp/f004ndc/MSAE/pilot_runs/20260605_030600_pcc_stage_a1b/stage_a1b_diagnostic_memo.md)
- Diagnostic outcome:
  - `candidate_amendment_supported = true`

### 3. Prospective Amendment Draft
- Draft artifact:
  - [pcc_gate_revision_v1.md](/jumbo/lisp/f004ndc/MSAE/prereg/pcc_gate_revision_v1.md)
- Status:
  - drafted
  - not yet adopted
  - prospective only

## Governance Note
The A1c confirmation pass must be interpreted as a confirmation step on the same checkpoint family under the proposed revised gate framing.

It must not be treated as evidence that the frozen A1 decision was invalid.

## Locked Inputs for A1c
- Checkpoint family:
  - `g4`, `g5`, `g6`, `g7`
- No new MSAE training
- No new architecture
- No threshold changes beyond the drafted amendment
- Goal:
  - resolve whether the amendment remains supported when NER checkpoint selection is aligned to `macro_f1`
