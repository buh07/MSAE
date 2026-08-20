VERDICT: SHIP
ONE-LINE: Every inference population now has a unique fail-closed schedule before any irreversible validation opening.

BLOCKERS

None.

REVISIONS

None.

NITS

None.

CHECKS RUN

- `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN.md` -> PASS.
- Read-only comparison of `PLAN.md` against `reports/adversarial/atlas_v3_4_attempt8_plan_review_v6.md` -> the v6 blocker is fixed at `PLAN.md:79`: the exact sentinel uses the signed `population_split_v3.json` pair order, separate 16-unit reference/candidate partial batches, independent right-padding, three identical reference repeats, 24 rows per side, bound IDs/shapes/maxima, and no grid pooling.
- Focused read-only order audit of `configs/atlas_discovery_v3_3/population_split_v3.json` and `data/atlas_discovery_v3_3_attempt7_qa_compact_v3/prepared/GUM/intervention_pairs.jsonl` -> exactly 16 fresh GUM pair IDs in frozen order: eight contiguous `context_factorial` pairs followed by eight contiguous `relative_gap` pairs. Frozen `_qa_panel_units` consumes this exact list order and expands the family roles to 8x1 + 8x2 = 24 rows per side.
- Shell-integer grid count audit -> 100 bases, 30 cells, 100 references/200 reference rows, 600 candidates/1,200 candidate rows, and 700 condition units/1,400 selected rows; `PLAN.md:42-46,77` matches.
- Shell-integer sentinel count audit -> 16 pairs, 16 reference units, 16 candidate units, 24 reference rows, and 24 candidate rows; `PLAN.md:49,79,148-150` matches.
- Shell-integer diagnostic count audit -> 20 bases, 20 references, 120 shifted units, 140 total units, and 280 selected rows; `PLAN.md:83,90` matches and applies hooked/unhooked comparison to all 140.
- Read-only regression audit of all prior findings -> retained/minimal EWT union, mandatory exact fresh-GUM validity gates/offsets, five-bin document caps, ESL exposure exclusions, literal cosine/byte semantics, common-frame/local/propagated diagnostics, observer terminalization, exact Transformer source hashes, one cross-stage SDPA contract, Torch/CUDA identity, all four `true` SDPA flags, library allowlist semantics, grid/science batching, terminology, no-training constraints, and sequential authorization remain intact.
- No model configuration or weights were loaded, no tensor library was imported or tensor executed, no forward pass/experiment was run, and no implementation file was modified.

CONTRACT COVERAGE

- V6 blocker: unique exact fresh-GUM sentinel order/batching/padding -> met (`PLAN.md:49,79,116,148-152,175-177`).
- Exact five-bin populations and grid schedule -> met (`PLAN.md:38-47,77`).
- Exact diagnostic population and observer replay -> met (`PLAN.md:81-90,197`).
- Retained-EWT plus minimal-EWT calibration union -> met (`PLAN.md:36,49,57,97,136,175`).
- Task/source support and exposure firewalls -> met in plan (`PLAN.md:23-24,38-49,120,198,200`).
- Cached/live/equivariance metric semantics and cellwise completeness -> met (`PLAN.md:51-71,148`).
- SDPA backend/environment/library lineage across calibration, validation, diagnosis, and science -> met (`PLAN.md:77,83,90,116,157-158`).
- Diagnostic numerical meaning and causal-claim restraint -> met (`PLAN.md:81-90,197,199`).
- Attempt-7 retirement/no retry and fresh-source sequencing -> met (`PLAN.md:9-12,17-23,94-100,106-112,146-152,194-196`).
- Mechanically unchanged scientific atlas and no-training boundary -> met (`PLAN.md:13-15,154-161,172-180`).
- Safe to begin implementation -> met — implementation remains followed by independent review, EWT-only authorization, immutable freeze review, and fail-closed validation gates before any fresh held-out or scientific opening (`PLAN.md:122-161,182-190`).

UNKNOWNS

- Whether all added `65-128` cells clear document diversity and ESL exposure exclusions. This is appropriately deferred to the no-inference prescore with explicit ineligibility rather than fallback/redraw (`PLAN.md:42-47,114-120`).
- The concrete PyTorch SDPA kernel used historically was not recorded. The plan does not overclaim certainty and freezes the strongest reconstructable backend, environment, flag, hardware, library, source, and batch lineage before new inference (`PLAN.md:81-90,114-118`).
