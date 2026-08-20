VERDICT: REVISE
ONE-LINE: Prior blockers are fixed; authorization scope checks and end-to-end tamper tests remain before inference.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)
  - [high] scripts/extract_atlas_discovery_v3.py:469-478 — full-authorization verification ignores `authorized_stage` and does not require the QA-digest map to contain exactly `EWT` and `GUM`.
    reasoning — a trusted signature with the correct schema/status/config hashes but a wrong or missing stage scope is accepted; extra source entries are also silently ignored.
    impact — the authorization envelope is not verified against the exact capability and source set it claims to grant.
    fix — require `authorized_stage == "full_activation_extraction_only"`, require the exact QA key set `{"EWT","GUM"}`, and add negative tests for altered scope, missing source, extra source, and stale QA digest.
  - [high] tests/test_atlas_discovery_v3_scoring.py:31-136 — the eight tests still do not exercise staged QA-to-full authorization, child-digest/order validation, signed cache verification, atomic promotion, or stale-stage refusal.
    reasoning — helper tests cover padding, translation, signer rejection, and a lock, but the previously blocking workflows are composed only in untested production paths.
    impact — a one-line regression in the highest-risk gates could authorize or reuse invalid extraction while all tests remain green.
    fix — add temp-root integration tests that build minimal signed EWT/GUM QA bundles, authorize full, verify exact cache reuse, and reject child tampering, wrong scope, stale QA/auth digests, incomplete inventories, wrong row order/shape, concurrent promotion, and stale staging.
  - [medium] scripts/extract_atlas_discovery_v3.py:71-115; configs/atlas_discovery_v3/scoring.json:31-38 — configured `neural_training_authorized=false` and the pinned prescore adversarial review are not validated by the loader.
    reasoning — both fields appear to be authorization prerequisites, but deleting or changing the review artifact has no runtime effect and the top-level no-training flag is ignored.
    impact — the executable authorization chain is weaker than the frozen config advertises.
    fix — require the top-level flag to be exactly `false`; verify the review path, digest, and `SHIP` verdict before any stage.
  - [medium] scripts/extract_atlas_discovery_v3.py:388-400,486-509 — signed QA/cache verification omits several exact payload invariants.
    reasoning — QA does not revalidate layer/model/device/GPU/batch/tolerance booleans; cache verification does not check hidden-state index, dtype declarations, configured device/GPU/batch, environment determinism, or the three no-training flags.
    impact — trusted but malformed or wrongly scoped signed envelopes can pass even though their arrays and core digests are valid.
    fix — compare every decision-relevant payload field to the frozen config/prescore/runtime contract and test each rejection.
  - [medium] scripts/extract_atlas_discovery_v3.py:214-231 — GPU UUID lookup uses the CUDA logical index as an `nvidia-smi` physical index.
    reasoning — under `CUDA_VISIBLE_DEVICES` remapping, `cuda:0` and `nvidia-smi -i 0` can refer to different GPUs.
    impact — valid frozen hardware can be falsely rejected, complicating the authorized run; the failure is safe but operationally brittle.
    fix — obtain the UUID from the actual CUDA device/PCI bus mapping or explicitly reject non-empty/remapped `CUDA_VISIBLE_DEVICES`.

NITS            (optional, cap at 5)
  - scripts/extract_atlas_discovery_v3.py:146-159 — verify the envelope's declared signature algorithm is exactly `Ed25519`.

CHECKS RUN
  - `.venv-atlas/bin/python -m pytest -q tests/test_atlas_discovery_v3_scoring.py` → 8 passed
  - draft CLI QA invocation with the current config → refused at the internal `run_qa` authorization gate before runtime/model access
  - implementation-inventory digest comparison → all six pinned entries match; scoring config SHA-256 is `5a0d4e9abe5ee89f2dcc5cc06476e2f177b4edb6a593f4ef8ea1561a00c7ae05`
  - read-only review of requested code/config → no large scientific data files opened

CONTRACT COVERAGE
  - row alignment and child lineage → met — exact digests, uniqueness, flattened order, tensor lengths, and pair references fail closed
  - explicit position IDs and padding → met — explicit IDs/masks are forwarded and multi-length row order is tested
  - QA repeat/tolerance/null semantics → met — three repeats, frozen tolerance, and exact uniform/prefix translations are enforced
  - trusted signatures → met — envelopes use the config-pinned Ed25519 key; authorization scope validation remains partial
  - staged authorization → partial — stable QA config plus separate signed authorization works, but exact stage/source scope is not checked or tested
  - CUDA determinism → met with operational caveat — batch/device/UUID/CUBLAS and deterministic flags are enforced; UUID mapping is remap-sensitive
  - cache correctness → met for core artifacts — exact files, hashes, shape/dtype/finiteness, row sidecar, QA/auth, and core lineage are verified
  - restart/concurrency safety → met by inspection — locks, unique staging, stale-stage refusal, fsync, and atomic promotion are present; integration tests remain absent
  - no training → met — inference mode, disabled gradients, and no optimizer/checkpoint path
  - draft refusal → met — current config refuses QA and full inference

UNKNOWNS
  - Whether the production launcher uses `CUDA_VISIBLE_DEVICES` remapping.
  - The authorized scoring config will have a new digest after its deliberate draft-to-QA status transition and must be frozen/reviewed without other field changes.
