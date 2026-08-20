VERDICT: BLOCK
ONE-LINE: Exact-review binding, exposure audit, preopening GPU checks, QK QA, rebuild proof, and lifecycle tests require repair.

BLOCKERS
- Candidate review acceptance was substring-based and not freeze-bound.
- Exposure audit did not scan all required project artifact families and hardcoded outcome-exposure booleans.
- visible-device/MIG checks did not all occur before scientific opening.
- backend QA did not independently validate primary multi-key mean scaled rotary QK logits.
- the available rebuild comparison used different config hashes and was not an exact-config rebuild proof.
- runtime row-ID/FK lineage, dependency binding, lifecycle coverage, and SIGTERM terminal behavior were incomplete.

STATUS
- Frozen candidate rejected before backend QA or any candidate-source model forward.
- `configs/relational_attention_edges_v1/FINAL_FREEZE.blocked1.json` preserves the rejected freeze.
