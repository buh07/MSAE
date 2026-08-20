VERDICT: BLOCK
ONE-LINE: Fresh sentinels can fail without blocking science, and raw post-RoPE Q/K differences are not numerical errors.

BLOCKERS

- [critical] `PLAN.md:49,57,63-71,138-150` — the exact attempt-7 EWT failure arrays are only an “additional calibration-history cell,” and the exact fresh-GUM pairs are only “lineage sentinels”; the uniquely executable authorization gate covers only the new 24 powers-of-two shift×length cells.
  reasoning — a static audit of the 8 fresh-GUM context pairs found prefix-position offsets `{7,9,12,16,17,28,37,41}`. Seven of those eight offsets are absent from the new `{1,4,8,16,32,64}` grid. RoPE finite-precision error need not be monotone in shift, so passing the grid does not imply that the exact unopened conditions pass. Likewise, deriving caps from only the new minimal EWT grid can ignore the signed conditions that motivated the repair.
  impact — attempt 8 can authorize science while the exact fresh GUM panel fails, or freeze a tolerance that does not cover the retained EWT calibration evidence. That leaves the primary held-out lineage non-authorizing and breaks the stated repair contract.
  fix — define the calibration population as the union of (a) the signed attempt-7 EWT arrays and (b) the new minimal-path EWT grid, and derive every maximum/cap from that union after independently verifying identical metric semantics and lineage. Make the exact 16 fresh-GUM pairs a separate mandatory signed PASS bundle under the frozen coordinate/L2/cosine rules, with their two families and actual offsets gated separately and never pooled with the grid. Dual validation must require fresh-GUM sentinels, all 24 fresh-GUM grid cells, and all 24 ESLSpok cells; bind each digest/status in the science authorization.

- [high] `PLAN.md:81-88` — the diagnostic contract reconstructs pre- and post-rotary Q/K but never defines the comparison frame or separates propagated hidden-state divergence from local rotary arithmetic error.
  reasoning — under a global position translation, raw post-RoPE Q and K vectors are expected to rotate by the common shift even in exact arithmetic. Comparing candidate versus reference post-RoPE Q/K directly will therefore report a layer-0 “divergence” by construction. At later layers, pre-rotary Q/K can already differ because earlier attention outputs diverged, which is propagation rather than local rotary error. The forward hook captures only the QKV linear output, so the proposed “native post-rotary” tensors and logits are reconstructions, not captured executed tensors.
  impact — the required “first divergence” report can misidentify expected common rotation or propagated differences as the source of finite-precision failure, defeating the diagnostic goal and inviting a causal overclaim.
  fix — freeze three distinct diagnostics before implementation: (1) pre-rotary reference/candidate difference as propagated-state divergence; (2) local rotary residual comparing float32 and float64 rotations of the same captured pre-Q/K and positions; and (3) translation-equivariance residual after transporting shifted post-Q/K back to the reference RoPE frame (or an algebraically equivalent relative-logit comparison). Apply descriptive floors only to the named residuals, never raw unaligned post-Q/K. Label out-of-band tensors `reconstructed`, prove their formula/source equivalence with fixtures, and define “first divergence” separately for propagation, local rotary residual, and invariant logits.

REVISIONS

- [medium] `PLAN.md:42-47` — 20 hash-selected sequences per length bin may be dominated by a small number of transcript/documents. Although the budgets are explicitly engineering rather than inferential, freeze a maximum contribution per genuine document and a minimum document count per bin/source; otherwise report the panel as a fixed sequence challenge rather than source-level validation. Prescore infeasibility must remain the fallback.
- [medium] `PLAN.md:24,114-118` — prior ESLSpok exposure exclusion should bind source record/document/sentence identities and prior inference-unit `input_ids`, not only exact content/token hashes. Reject exact matches and any candidate construction that is a truncated/prefixed view of a previously opened prior unit; publish retained/excluded counts by length bin. This closes representation exposure through alternate serialization or truncation.
- [medium] `PLAN.md:59-60` — make the executable expressions literal: use `max(norm_ref*norm_candidate,1e-24)` in the cosine denominator, and distinguish `np.array_equal` value equality from byte equality. Require canonical `.npy/.npz` child hashes plus exact dtype/shape/strides/order or compare `tobytes(order='C')`; do not call `np.array_equal` alone byte-exact replay.
- [medium] `PLAN.md:77,81-88,116` — the attention backend is promised but still unnamed. The no-inference prescore must freeze its exact configured value and installed Transformers implementation path/hash, plus QKV split/rotary source hashes, before implementation review; a runtime default is not acceptable.

NITS

None.

CHECKS RUN

- `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN.md` → PASS; the revised plan satisfies the structural plan gate.
- Read-only line-by-line re-review of revised `PLAN.md` against `reports/adversarial/atlas_v3_4_attempt8_plan_review.md` → prior familiar-GUM pooling, hooked/minimal path coupling, EWT/science overlap, aggregate gates, retirement placement, science-adapter scope, ESLSpok labeling, fail order, and structural no-training findings are substantially fixed.
- Read-only lineage audit of attempt-5 GUM, attempt-7 split, attempt-7 terminal, and post-result review → legacy GUM is correctly reclassified as familiar/non-authorizing and attempt 7 remains terminal/no-retry.
- Static no-inference audit of the 16 frozen fresh-GUM pair records → 8 relative-gap and 8 context pairs; context offsets are `[7,9,12,16,17,28,37,41]`, of which only `16` is in the proposed six-shift grid.
- Read-only feasibility inspection of prior ESLSpok prepared inputs → Atlas v2 opened C1/C2 ESLSpok activation units, confirming the need for the revised exposure inventory and the stronger identity/truncation revision above.
- Mathematical review of RoPE translation diagnostics → raw post-rotary Q/K are frame-dependent under a common shift; no neural inference or implementation edit was performed.

CONTRACT COVERAGE

- Every blocker from v1 → partial — familiar GUM pooling, hook/calibration coupling, EWT/science overlap, and aggregate metric ambiguity are fixed, but the exact fresh-GUM held-out cells still do not authorize science.
- Every revision from v1 → met in plan, with narrower follow-ups — retirement is external, science code/adapter is bounded, ESLSpok is exposure-filtered and secondary, fail order is explicit, no-training is structural, and diagnostic capture is much more concrete.
- Attempt-7 terminal/no retry → met — the new root freezes rather than mutates attempt 7 (`PLAN.md:92,104-110,170,193`).
- Calibration/validation leakage firewall → partial — source roles, science disjointness, path separation, and sequential authorization are strong, but the retained EWT/fresh-GUM sentinel evidence is not decision-binding.
- Numerical gate uniqueness/statistical validity → met for the new grid — exact rows/elements, formulas, float64 reductions, integer budgets, missingness, cellwise passage, and non-inferential interpretation are frozen (`PLAN.md:38-71`), subject to minor executable-expression revisions.
- Minimal-versus-hooked estimator identity → met — separate processes/bundles and a shared minimal source-parameterized function prevent diagnostics from tuning thresholds (`PLAN.md:73-88,128-142`).
- Q/K/logit/float64 diagnostic validity → unmet — capture mechanics are feasible in outline, but RoPE frame alignment and local-versus-propagated error decomposition are absent.
- Held-out source roles → partial — fresh GUM and exposure-filtered ESLSpok are now separate and sequential, but exact fresh-GUM sentinels are not mandatory gates.
- Mechanically unchanged scientific atlas → met in plan — original scientific modules/functions and `_forward_units` remain byte-frozen behind a narrow reviewed adapter (`PLAN.md:152-159`).
- No-training boundary → met in plan — labels/estimators are absent technically and optimizer/gradient/checkpoint paths are structurally forbidden (`PLAN.md:12-15,120-126,157,177`).
- Safe to begin implementation → unmet — the two blockers affect frozen one-way validation and diagnostic semantics and must be resolved in the plan before code is written.

UNKNOWNS

- Whether 80 outcome-new ESLSpok bases and 80 science-disjoint EWT bases remain after identity, truncation, length-bin, and document-diversity exclusions; prescore must measure this without inference.
- Whether the installed attention implementation permits exact reconstruction of its rotary computation order and tensors from the QKV hook; source-hash binding and synthetic formula-equivalence tests must settle this before EWT authorization.
