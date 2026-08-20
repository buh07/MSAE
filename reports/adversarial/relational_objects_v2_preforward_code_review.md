VERDICT: BLOCK
ONE-LINE: Morphology matching, intervention precision, and terminal ownership violate the frozen one-shot protocol.

## Blockers found before any model forward

1. `scripts/build_relational_objects_v2.py` and `scripts/analyze_relational_objects_v2.py` encoded only morphology-attribute presence, so `Case=Nom` and `Case=Acc` were indistinguishable.
2. `scripts/run_relational_objects_v2.py` computed float32 `E_abs` by an algebraic identity instead of the literal zero-and-renormalize intervention.
3. A process losing the exclusive opening race could write into the legitimate owner's run root.
4. The handshake preceded readiness checks, functional attrition reasons were incomplete, and the float64 analytic reduction order was not explicit.

## Resolution

All implementation defects were fixed before model loading or endpoint scoring. Morphology values are now coarsened through a fixed config vocabulary and enter both exact strata and one-hot nuisance features; `E_abs` uses a literal float32 zero/renormalize/recompute path; the float64 reference iterates key positions in increasing order; only the opening owner can terminalize; readiness follows preflight; attrition reasons are explicit; and a post-review synthetic-token backend QA path was added.

The morphology correction reduced Latvian label-only support to 77 document-disjoint components and 196 pairs, below the frozen 100/500 floor. Consequently the model-forward study was stopped rather than run. Signed terminal: `reports/provenance/relational_objects_v2_development2_prescore_terminal_v2.json`.

No model weights were loaded; no model forward, endpoint score, training, tmux GPU experiment, or fresh-corpus access occurred.
