VERDICT: SHIP
ONE-LINE: Extraction now fails closed across authorization, numerical QA, lineage, deterministic runtime, and cache promotion.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)
  - tests/test_atlas_discovery_v3_scoring.py:108-191 — future hardening could add a full signed QA-to-authorization-to-cache integration/tamper test; the current ten targeted tests and inspected production gates are sufficient for this review.

CHECKS RUN
  - `.venv-atlas/bin/python -m pytest -q tests/test_atlas_discovery_v3_scoring.py` → 10 passed, with one unrelated Transformers cache deprecation warning.
  - draft CLI QA invocation with `/dev/null` as the signer → exit 1 at the internal `run_qa` status gate, before signer/model/runtime access.
  - SHA-256 review → scoring helper `0e9980c689f3cd6f058c7a3051f43946777e0db248c220c69d1ececcccc6860c`; extraction `23968b478d5650c8d47fa4114c6400a5819eeae79261da8b6f4666d27126c273`; tests `f719dba4f0ba9258829de0c4f053e8af15aecdac6c72e45ce1d8bcb5d43cc08e`; scoring config `7529a51e9964f5beed775a2423bed1e0b4a11c7057049d4ffef12fa173b9629f`.
  - read-only review of the requested code/config and prior findings; no large scientific data files opened.

CONTRACT COVERAGE
  - configuration and prescore authorization → met — `scripts/extract_atlas_discovery_v3.py:70-124` requires the no-training flag, exact implementation/input/rebuild digests, and the pinned prescore `SHIP` attestation.
  - signatures and staged capability → met — `scripts/extract_atlas_discovery_v3.py:127-170,476-503` pins Ed25519, checks the declared algorithm, and requires the exact full-extraction stage and exact `{EWT,GUM}` QA digest map.
  - row/input lineage and null semantics → met — `scripts/extract_atlas_discovery_v3.py:295-396` checks child digests, uniqueness/order/shape, pair references, role order, and exact position-only translations.
  - numerical QA → met — `scripts/extract_atlas_discovery_v3.py:399-473` verifies exact decision fields and child files, enforces the frozen three-repeat tolerance formula, and promotes only a signed `PASS`.
  - deterministic runtime and hardware binding → met — `scripts/extract_atlas_discovery_v3.py:213-253` enforces CUDA, logical-device UUID, batch/device pins, deterministic algorithms, CUBLAS configuration, TF32-off, eval mode, and disabled gradients.
  - cache correctness and restart safety → met — `scripts/extract_atlas_discovery_v3.py:173-210,511-580` provides exclusive locks, stale-stage refusal, fsync/atomic promotion, exact signed inventories/lineage, exact row order, and NPY dtype/shape/finiteness validation.
  - regression coverage → met — `tests/test_atlas_discovery_v3_scoring.py:34-191` covers scoring helpers, layer rejection, null tampering, multi-length padding/order, signer trust, concurrency, atomic/stale staging, and child-digest tampering.
  - draft refusal and no training → met — `configs/atlas_discovery_v3/scoring.json:31,53` remains non-authorizing, while `scripts/extract_atlas_discovery_v3.py:428-430` refuses QA internally.

UNKNOWNS
  - The production CUDA/model numerical QA and full extraction were intentionally not executed in this read-only review.
  - The deliberate draft-to-QA authorization edit will change the scoring-config digest; the resulting config must be frozen and used consistently by both signed QA artifacts and the full-authorization artifact.
