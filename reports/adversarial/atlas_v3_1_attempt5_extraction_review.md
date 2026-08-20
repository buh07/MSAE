VERDICT: BLOCK
ONE-LINE: QA authorization, input lineage, signatures, and cache completion are not yet strong enough for irreversible extraction.

BLOCKERS        (must fix before proceeding; empty if none)
  - [critical] scripts/extract_atlas_discovery_v3.py:372,394-399,516-523 — QA is bound to the complete scoring-config digest, but advancing from QA-only to full authorization changes that digest.
    reasoning — a QA produced under `frozen_numerical_qa_authorized` cannot verify after the status changes to `frozen_representation_extraction_authorized`; the only working path is to authorize full extraction before QA is observed.
    impact — the intended two-stage authorization gate is either unusable or bypassed.
    fix — bind QA to a stable protocol/config-content digest that excludes mutable authorization state, then require a separate immutable full-authorization artifact referencing the exact passing `QA_COMPLETE.json` digest; enforce the gate inside `run_qa`/`run_full`, not only `main`.
  - [critical] scripts/extract_atlas_discovery_v3.py:259-267,286-298 — QA opens inference units and intervention pairs without checking their source-manifest digests or exact row/condition semantics.
    reasoning — hashing only the parent manifest does not detect a changed child JSONL. `row_to_unit` also silently overwrites duplicate row IDs, and the selected bare/shift units are never checked to differ only by the frozen position-ID translation.
    impact — QA can sign a pass over tampered, duplicated, misordered, or non-null inputs and falsely authorize the full cache.
    fix — before model load, verify unit, activation-row, and intervention-pair digests; require unique unit/row IDs and exact row order; validate lengths, masks, target indices, and condition-specific invariants for every QA pair, including identical IDs/masks/targets and the exact uniform or prefix position offset.
  - [critical] scripts/extract_atlas_discovery_v3.py:163-176,179-213 — the QA envelope is signed by a newly generated key whose public key is stored in the same envelope.
    reasoning — verification proves only that the co-located key signed the payload; any replacement payload can generate another key and pass. No config-pinned trust anchor or authorized signer fingerprint is checked.
    impact — `run_full` can accept a forged QA pass, so the signature does not enforce provenance or authorization.
    fix — pin an operator/reviewer Ed25519 public-key fingerprint in the frozen config and sign with the corresponding external private key, or replace the self-signature with an immutable authorization record that binds the independently reviewed QA digest.
  - [critical] scripts/extract_atlas_discovery_v3.py:216-234,400-410,472-503 — completed-cache reuse trusts a mutable, unsigned manifest with no required artifact set or structural cache checks.
    reasoning — `_verify_complete_cache` accepts an empty `artifacts` map and does not verify schema, source, row/unit counts, model/layer, QA digest, NPY shape/dtype, row-ID uniqueness/order, or absence of unexpected files.
    impact — a missing, truncated, substituted, or cross-source cache can be returned as complete.
    fix — require the exact artifact set, validate every completion field against frozen inputs, mmap-check NPY shape/dtype, verify the row sidecar against prepared rows, reject extras, and authenticate or independently pin the completion manifest digest.
  - [high] scripts/extract_atlas_discovery_v3.py:246-258,400-413,435-503 — QA and extraction write directly into final directories without an atomic lease or staging promotion.
    reasoning — two processes can both observe an empty directory and concurrently overwrite the same NPZ/NPY; crashes leave a permanently non-resumable partial directory, and completion writes are non-atomic.
    impact — expensive inference is vulnerable to silent concurrent corruption or unsafe manual cleanup.
    fix — acquire an exclusive per-source/stage lock, write to a unique staging directory, fsync files and directory, verify the staged bundle, and atomically rename it into place; make stale-partial recovery explicit and digest-checked.

REVISIONS       (should fix; not blocking)
  - [high] scripts/extract_atlas_discovery_v3.py:71-78,507-531; configs/atlas_discovery_v3/scoring.json:2-11 — configured devices and batch size are advisory because CLI overrides are unrestricted, and CUDA determinism prerequisites are not enforced.
    reasoning — QA/full may run on different GPUs or batch shapes than frozen; `CUBLAS_WORKSPACE_CONFIG` is not set/checked before CUDA initialization.
    impact — numerical tolerance and extracted values need not correspond to the reviewed configuration, and deterministic CUDA matmul may fail at runtime.
    fix — reject device/batch overrides that differ from the per-stage/source config; require and record GPU UUID/capability, CUDA/cuDNN versions, deterministic flags, and `CUBLAS_WORKSPACE_CONFIG` set before importing/initializing Torch.
  - [medium] scripts/atlas_discovery_v3_scoring.py:14-18; tests/test_atlas_discovery_v3_scoring.py:20-22 — out-of-range requested layers silently clamp to the last block.
    reasoning — a corrupted layer setting yields a valid but scientifically different cache.
    impact — layer lineage fails open.
    fix — reject `requested_layer > n_hidden_states-2` and test the failure.
  - [medium] scripts/atlas_discovery_v3_scoring.py:21-39 — tolerance validation permits `atol_floor >= atol_hard_ceiling`, and extraction hardcodes exactly three saved repeats without validating `repeats == 3`.
    reasoning — malformed frozen configuration can be marked valid or fail after inference with indexing errors.
    impact — the frozen QA formula is not fully fail-closed.
    fix — validate floor below ceiling, positive finite rtol, multiplier exactly as frozen, and exactly three repeats before model load.
  - [high] tests/test_atlas_discovery_v3_scoring.py:20-49 — tests exercise only four scalar helpers.
    reasoning — there are no tests for explicit padded position IDs, row alignment, condition invariants, child-file tampering, signature trust, staged authorization, cache tampering, draft refusal, device enforcement, concurrency, or restart behavior.
    impact — the highest-risk extraction gates can regress while the suite remains green.
    fix — add fake-model/temp-root integration tests covering each failure mode and a positive multi-length padded batch with exact expected row order.
  - [medium] scripts/extract_atlas_discovery_v3.py:44-68; configs/atlas_discovery_v3/scoring.json:27-30 — the configured rebuild-check artifact is never opened or verified.
    reasoning — the path/digest currently has no gating effect.
    impact — full extraction can proceed without validating the attempt-5 rebuild attestation the config claims to bind.
    fix — verify its digest, schema, PASS status, and referenced prepared-manifest/config digests in `load_scoring_config`.

NITS            (optional, cap at 5)

CHECKS RUN
  - `.venv-atlas/bin/python -m pytest -q tests/test_atlas_discovery_v3_scoring.py` → 4 passed
  - draft CLI QA invocation → refused before inference due implementation-inventory drift; current extraction SHA-256 is `4df73c1e...`, while config line 17 still pins `5e6fe093...`
  - read-only review of the four requested files and the attempt-5 extraction/QA contract → no large scientific data files opened

CONTRACT COVERAGE
  - row alignment → partial — full extraction checks flattened row order; QA lacks child-digest, uniqueness, and semantic-pair validation
  - explicit position IDs and padding → partial — forwarded explicitly with right-padding masks, but untested and not prevalidated
  - repeat/tolerance formula → partial — nominal formula matches the RFC; malformed configurations and repeat counts are not fail-closed
  - uniform/prefix null comparisons → partial — slicing is coherent for expected inputs, but input invariants are trusted rather than verified
  - signature and lineage → unmet — QA is self-signed without a trust anchor and child inputs are unverified
  - authorization gates → unmet — draft refuses, but staged QA-to-full authorization is digest-incompatible and callable helpers bypass status checks
  - CUDA determinism → partial — deterministic algorithms and TF32 disabling are present; device/config and CUDA prerequisites are unenforced
  - cache correctness and restart safety → unmet — completion validation is incomplete and writes are non-atomic/unlocked
  - no training → met — eval mode, disabled gradients, and inference mode are used; no optimizer/checkpoint path exists
  - draft refusal → met — current config cannot authorize inference (and presently also fails its stale implementation hash)

UNKNOWNS
  - Whether a separate launcher supplies a trusted signing key, exclusive leases, fixed CUDA environment, or staged authorization not visible in the reviewed files.
  - Whether the implementation-inventory drift is an intentional in-progress update; authorization must not occur until the reviewed final hashes are frozen.
