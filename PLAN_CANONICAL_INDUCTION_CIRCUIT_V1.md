# Canonical Induction Circuit v1 — End-to-End Technical Positive Control

## Goal

Validate the capture, head-output intervention, and behavioral measurement pipeline on the canonical repeated-token induction task in GPT-2 small. This is a separately versioned technical positive control using prespecified induction heads L5H5 and L6H9; it is not another natural-language endpoint, a representation-method comparison, or a cross-family scientific claim.

## Constraints

- Preserve IOI v1 exactly as its formal `DEVELOPMENT_STOP`: no threshold changes, favorable-template promotion, manual patch continuation, confirmation opening, method evaluation, or relabeling.
- Preserve the exact manuscript and claim-ledger bytes that IOI v1 froze before making the requested post-result paper update; bind that migration explicitly.
- Use the externally established repeated-token induction generator `[A][B] ... [A] -> [B]`, token IDs rather than new natural-language prompt templates, and the frozen GPT-2 revision.
- Prespecify GPT-2 heads L5H5 and L6H9 as induction heads. Use same-layer L5H0 and L6H0 as matched controls; do not discover or rank heads from these outcomes.
- Development and confirmation use disjoint token-ID pools and seeds. Confirmation inputs are frozen before inference but are not parsed or content-hashed by pre-gate workers.
- Set `CUBLAS_WORKSPACE_CONFIG=:4096:8` before Python starts; require exact repeated live inference on a registered QA subset before scientific metrics.
- Measure the induction attention edge, necessity via head-output ablation, sufficiency via clean-to-corrupt head-output replacement, and selectivity against an independently corrupted donor.
- A single-model pass validates only the technical pipeline. It cannot authorize a general method claim; any later representation benchmark must be separately frozen and replicate in at least two model families.
- No SAE, LEACE, projection, public method, supervised controller, or training job exists in this version.
- Candidate and exact post-freeze `/adversarial` reviews must be `SHIP` before launch.

## Design

Each row samples 18 unique registered GPT-2 token IDs. The clean prompt repeats a 16-token sequence and ends at the second occurrence of token 15; the target is token 16. A corrupted prompt replaces token 16 after the first occurrence with alternate 1, while an independently corrupted donor uses alternate 2. All prompts have the same length and second-half query.

The frozen heads are evaluated at the final query token:

1. **Behavior:** clean prefers target over alternate 1; corrupt prefers alternate 1 over target; the smaller signed margin exceeds 0.5.
2. **Attention edge:** known-head attention from the second query occurrence to the clean successor position exceeds matched-control attention.
3. **Necessity:** zeroing known-head pre-projection outputs reduces the clean target margin more than zeroing matched heads.
4. **Sufficiency:** transplanting clean known-head outputs into the corrupt prompt restores the clean target margin.
5. **Selectivity:** the clean-donor recovery exceeds recovery from the independently corrupted donor.

Inference is hierarchical over eight fixed token blocks of sixteen rows. Point estimates give every block equal weight; bootstrap draws resample blocks and then rows within each sampled block, preserving that equal-block estimand even when informative-row counts differ. Development must meet the registered support, attention, necessity, recovery, and selectivity bounds before confirmation model loading. Confirmation repeats the same estimators on a disjoint token pool. The final result can validate the technical positive control only; it never launches downstream methods.

## Milestones

- [x] Preserve IOI v1 and update the paper with the scoped result and CuBLAS warning.
- [x] Implement and test generator disjointness, exact QA, head capture/replacement, controls, gates, lineage, timeouts, and one-shot launch.
- [ ] Obtain candidate `/adversarial: SHIP`, freeze, obtain exact frozen `/adversarial: SHIP`, bind it, and launch in tmux.

## Verification plan

- `python -m pytest -q -p no:cacheprovider tests/test_canonical_induction_circuit_v1.py`
- `python -m py_compile scripts/canonical_induction_circuit_v1.py`
- `bash -n scripts/launch_canonical_induction_circuit_v1_tmux.sh`
- Paper claim verification, exact IOI v1 preservation, tokenizer/cache attestation, prepared-panel verification, and exact freeze verification.
- Reproducibility audit for seeds, environment, exact repeated inference, disjoint tokens, artifact hashes, and runtime versions.
- Independent candidate and post-freeze adversarial review.

## Definition of done

- [x] IOI v1 scientific artifacts and original frozen manuscript bytes verify exactly.
- [x] PAPER reports IOI v1 narrowly and the claim ledger verifies.
- [x] The generator has 128 development and 128 confirmation rows, eight 16-row blocks each, unique tokens within row, and disjoint token pools.
- [x] CPU hook tests prove exact per-head capture, zero ablation, replacement, and matched-control isolation.
- [x] Tests cover strict thresholds, hierarchical bootstrap, QA failure, silent-worker timeout, upstream failure, lineage tampering, confirmation-before-load firewall, and duplicate namespaces.
- [x] `CUBLAS_WORKSPACE_CONFIG` is set in every GPU tmux process before Python imports Torch.
- [ ] Candidate and frozen reviews are `SHIP` and the latter is hash-bound.
- [ ] Development, gated confirmation, development gate, and final aggregator are live or cleanly terminal in four tmux sessions on one free UUID-pinned GPU.
- [ ] No method evaluation or training starts.

## Risks

- **Published head role does not imply necessity under this exact metric:** report a clean technical negative; do not discover replacement heads post hoc.
- **Replacement is overly strong:** it is explicitly a pipeline positive control; matched-head and independent-donor controls constrain interpretation.
- **Token-level confounds:** use unique token IDs, disjoint pools, fixed lengths, corruptions that alter one first-half successor, and block bootstrap.
- **GPU nondeterminism:** set the CuBLAS workspace variable before interpreter startup and stop before metrics unless repeated inference is exact.
- **Scope inflation:** single-model success is never described as cross-family generality or method success.

## One-way doors

The freeze and first GPT-2 forward are one-way. A frozen-review blocker retires the namespace. A development-gate stop seals confirmation. Regardless of outcome, downstream methods require a new protocol and at least two eligible model families for a general claim.
