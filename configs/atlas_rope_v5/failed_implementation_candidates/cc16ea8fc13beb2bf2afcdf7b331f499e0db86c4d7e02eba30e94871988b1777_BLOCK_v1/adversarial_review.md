VERDICT: BLOCK
ONE-LINE: EWT replay remains callable, and the QA bridge adds stricter, mislabeled post-validation gates.

BLOCKERS
  - [high] `scripts/run_atlas_rope_v5.py:772-804` — score-bearing EWT replay is not actually forbidden.
    reasoning — `_extract_grid()` rejects only `validation_caps is None`. Supplying frozen caps with `source="EWT_calibration"` bypasses the guard, loads the EWT panel, and executes four score-bearing forward passes. The regression at `tests/test_atlas_rope_v5.py:571-578` tests only the `None` case.
    impact — attempt 9 can accidentally rerun the terminal attempt-8 calibration despite the explicit no-retry/import-only contract.
    fix — allowlist only `GUM_fresh_validation` and `GENTLE_validation` inside `_extract_grid()` and `verify_grid_bundle()`, require sequential-validation authorization, and test EWT rejection with both absent and populated caps.

  - [high] `scripts/run_atlas_rope_v5_science.py:240-249,268-296` — the QA bridge imposes a new stricter post-validation gate.
    reasoning — `_technical_stat()` passes only when every coordinate satisfies `atol+rtol`. Frozen grid validation instead permits the preregistered per-cell coordinate and row budgets and separately checks relative-L2/cosine. Therefore a valid signed GUM PASS can still fail `_qa_bridge_payload()` at lines 295-296.
    impact — dual held-out PASS does not actually unlock the frozen atlas; science can be stopped by an undisclosed stricter criterion after authorization.
    fix — verify and translate the exact signed sentinel/grid PASS statistics under their frozen budgets. Do not rescore them with an all-coordinate-zero-failure rule unless that additional gate is explicitly preregistered and freeze-bound before validation.

  - [high] `scripts/run_atlas_rope_v5_science.py:256-267` — retained attempt-7 QA families are reported with false aggregation and row counts.
    reasoning — one statistic over all retained attempt-7 rows is copied verbatim into both `uniform_shift` and `prefix_position_only`. This discards the signed legacy/fresh panel boundaries and family-specific indices, while the unchanged analysis later presents those values as family-matched numerical errors.
    impact — scientific output can mislabel aggregate error as construct-specific evidence, violating the unchanged-science and accurate-lineage claims.
    fix — independently reconstruct the signed attempt-7 panel/family segments and preserve their exact statistics and row counts, or label the value explicitly as global aggregate and prohibit family-specific interpretation.

  - [high] `tests/test_atlas_rope_v5_science.py:16-76` — neither QA-bridge failure mode has regression coverage.
    reasoning — science tests cover frozen hashes, effective context, authorization-before-load, and adapter inventory, but never exercise bridge construction against allowed validation failures or family-specific attempt-7 rows.
    impact — both decision-path defects can pass the reported 49-test implementation suite.
    fix — add synthetic GUM cells that PASS frozen budgets with allowed coordinate failures and must remain science-eligible; add exact attempt-7 family segmentation/count tests and reject aggregate aliasing.

REVISIONS
  - [medium] `scripts/run_atlas_rope_v5_science.py:158-188` — assert the exact two-entry artifact inventory in the signed science-cache payload, not only the directory allowlist.
    reasoning — the verifier iterates whatever artifact entries are declared without requiring both `activations.float32.npy` and `row_ids.jsonl`.
    impact — a signed but incomplete inventory could omit cryptographic lineage for a required child.
    fix — require `set(payload["artifacts"]) == {"activations.float32.npy", "row_ids.jsonl"}`.

NITS
  - `PLAN_ATTEMPT9.md:24-33` — renumber the approach steps; numbering jumps from 3 to 5.

CHECKS RUN
  - Candidate SHA-256 recomputation → exact match: `cc16ea8fc13beb2bf2afcdf7b331f499e0db86c4d7e02eba30e94871988b1777`.
  - Exact implementation inventory audit → every declared file matched its byte count and SHA-256.
  - Prescore config/manifest/rebuild, runtime probe, attempt-7 retirement, attempt-8 terminal/staging, and source-provenance bindings → all matched.
  - Attempt-8 required-absence audit → promoted calibration, diagnostic, validation, science, validation authorization, and science authorization paths were absent.
  - Attempt-9 state audit → no signed retirement/import/cap/authorization artifact or run root existed.
  - Static inspection of signer, controller, calibration import/cap derivation, authorization chain, diagnostic gate, science adapter, QA bridge, and tests → completed.
  - `reports/atlas_rope_v5/implementation_verification.json` reports 49 attempt-9 tests and 44 frozen attempt-7 regressions passing; these were not independently rerun during this interrupted review.
  - No model inference, signing, artifact mutation, training, git, network, or record-review operation was performed.

CONTRACT COVERAGE
  - Candidate and evidence lineage → met — exact hashes and byte counts matched.
  - Attempt-8 immutable terminal/import semantics → met — signed history and required absences are independently bound.
  - JSON normalization and create-once signing → met — temporary verification, hard-link no-clobber, inode/hash checks, and signing-fault stop are implemented.
  - Retirement→import→cap→diagnostic→validation order → met — cap candidate precedes diagnostic authorization and validation.
  - Expanded-cap derivation → met — retained attempt-7 plus imported attempt-8 selects `2e-05` over 1,272 rows.
  - No new score-bearing EWT forward → unmet — populated caps bypass the guard.
  - Runtime preflight before authorized forwards → met — technical and science model paths attest before forwarding.
  - Terminal/signing-fault guards → met — controller stages reject both terminal states.
  - Sequential GUM→GENTLE validation → met — validation remains separately authorized and ordered.
  - Frozen science code/settings → met — files, functions, analysis settings, adapter, and namespaces are inventory-bound before validation.
  - Dual PASS as the sole science gate → unmet — the QA bridge adds a stricter unregistered gate.
  - Family-correct numerical QA reporting → unmet — retained rows are aggregated then duplicated across families.
  - No-training boundary → met — candidate permissions and static scan forbid training constructs.

UNKNOWNS
  - The test suites were not independently rerun before the requested immediate verdict.
  - Model/runtime behavior and held-out results remain intentionally unexecuted.
