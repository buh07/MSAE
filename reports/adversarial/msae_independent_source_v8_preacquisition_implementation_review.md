VERDICT: SHIP
ONE-LINE: The exact candidate scanner and the remaining source-free control plane now satisfy the frozen pre-acquisition contract.

BLOCKERS        (must fix before proceeding; empty if none)
  - None.

REVISIONS       (should fix; not blocking)
  - None.

NITS            (optional, cap at 5)
  - tests/test_prepare_msae_independent_source_v8.py:437-460 — a permanent fixture for an accepted token ending exactly at the first block boundary would directly pin the new pending-occurrence path; independent synthetic review exercised it successfully.

CHECKS RUN
  - `sha256sum` over every requested input → exact matches: plan `7aec70f8d6f384f2919f5f3086064b437dd34ff7731542aed2d7abe23ac5ae19`; plan review `d159749125a6db4e1dd6a68f2207e4be6b643e2f0d7b8112695cfec98660204d`; registry `ff4a36996f58531353dda9ed8fcbedb4c3a615f2d877e8b31f1462ddc8581a97`; screen `68a7536c95896087960dd4fc5882df85296baaa1a07aaf910e0e7c257b165e2f`; builder `5b3bf93ed412e480e7d84720b235b104bc571bb63faa16504279cd25cf6bc881`; runner `07a15235a860296ffb461d2bc065cdb093fb87656b9dbab3918c20293b4159a3`; tests `3baad53b0d863c4139abeaf3fa303f46fad4338d0342d0289ced15ba83bd76cc`; config `8383d3ba80ac1296887c243e00d09b6b9a5e79b19f771934a1ddd07ceac56df9`; transcript `3629712ae64b00c9e6c9dd2cd1cced774d3a5f328fd72115bf7edbf14e13369b`.
  - Metadata-only `lstat` and `stat` → `data/msae_independent_source_v8`, baseline, authority manifest/review, acquisition entry, acquisition success, and acquisition rejection remain absent; reviewed public artifacts are regular one-link files with expected `0644`/`0755` modes. No source/raw/private/payload/quarantine content was opened.
  - AST extraction plus SHA-256 recomputation of `_predecessor_hashes()` → all 50 public predecessor bindings match, including the complete terminal v7 chain.
  - Public registry canonical reconstruction → 16,133 unique input paths and digest `8070a7cdd536a0dbd6104ff1dfb279ef01fb0acf98e969227625324155227564`; registry and alias-screen bindings agree.
  - `PYTHONPYCACHEPREFIX=<fresh /tmp> python3 -m py_compile` on builder, runner, and v8 tests → pass.
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider` over v4/v4.1/v4.2/v5/v6/v7/v8 source-free suites → 477 passed in 20.31s.
  - Source-free synthetic scanner comparison → a left-context-blocked `xUD_FalseBoundary` at the carried-tail start produced no direct or streamed match; accepted UD tokens ending exactly at the block boundary, continuing into the next block, and already emitted before the tail all matched whole-buffer reference extraction exactly.
  - Reviewed `reports/verification/msae_independent_source_v8_source_free_checks.log` → its bound run records CPython 3.12.3/Unicode 15.0.0, 16,133 history records, 50 predecessors, eligible point snapshot with zero forbidden identities, 477 passing suites, and no source/network/model/GPU/scoring/training operation.
  - Read-only builder/runner control-flow review → exact four-file/no-README acquisition, LICENSE-only evidence, all-four-file candidate pedigree, durable one-shot entry, state-based final recovery, raw/public/private custody, all-disposition history and global training recensus, literal scientific gate order, rejection reconstruction, and success/payload terminal reconstruction are present.

CONTRACT COVERAGE
  - Exact reviewed bindings and source-free precondition → met — all requested hashes match and every pre-acquisition v8 data/control path remains absent.
  - Exact candidate pedigree regex/limits/chunk/carry semantics → met — scripts/prepare_msae_independent_source_v8.py:1624-1717 implements the frozen patterns, 1,048,576-byte blocks, 2,048-byte carry, precise URL/UD limits, ordinary wholly-tail suppression, and exact pending `(pattern,start)` exceptions; the prior tail-left-context false positive is rejected by tests/test_prepare_msae_independent_source_v8.py:456-460 and independent synthetic comparison.
  - All-four-file pedigree and first-gate stop → met — builder lines 1720-1741 scans train/dev/test and `LICENSE.txt`; per-partition URL/`UD_*` fixtures and gate-order checks pass before dedup, support, role/split, or payload creation.
  - Exact four-file/no-README acquisition and LICENSE-only predicate → met — runner constants/config, sparse paths, tree/blob evidence, installed raw census, and terminal reconstruction name only the three CoNLL-U partitions plus `LICENSE.txt`; builder license evidence reads only `LICENSE.txt`.
  - Complete accessible-history and predecessor closure → met source-free — 50/50 predecessor hashes and the exact 16,133-record registry input array reconstruct; builder and runner validate every non-quarantine disposition and lstat-only quarantines before work.
  - One-shot entry, custody, cardinality, and recovery → met source-free — the reviewed runner publishes a durable bound entry before its first subprocess, installs raw via no-follow create-once operations, accepts only a fully reconstructing canonical final, and leaves all other preexisting or uncertain states blocked without retry.
  - History overlap/support before payload and K2/branch stop → met source-free — build order performs source-family, pedigree, dedup, cross-role/history overlap, and support before role/split and private payload; all scoring/training/Stage-C authorizations remain false.
  - Terminal failure/success reconstruction → met source-free — retained rejection binds exact artifact/payload inventory and observed process/training/history status; success re-executes the deterministic scientific pipeline and reconstructs the opaque payload bytes before accepting the seal.
  - V8-M1 implementation gate → met — plan, implementation, runner, tests, config, registry/screen, transcript, and predecessor requirements are reviewed source-free and ready for the separate create-once baseline and authority-review steps.

UNKNOWNS
  - Candidate tree/blob identities, raw hashes, license result, document-group branch, deduplication, overlap, support, and payload feasibility remain intentionally unknown until the separately authorized one-shot acquisition and ordered scientific gates.
  - Full current-worktree identity, actual baseline process/training evidence, and acquisition authorization remain for the create-once baseline, authority manifest, and independent provenance-only authority review; this SHIP verdict does not itself authorize network acquisition.
