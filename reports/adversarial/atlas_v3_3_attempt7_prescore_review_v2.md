VERDICT: BLOCK
ONE-LINE: Dedicated QA construction still persists five unused scientific intervention conditions per fresh panel.

BLOCKERS
  - [critical] docs/rfc-atlas-v3-3-attempt7-discovery-factor-atlas.md:24 — external dev/test may create only numerical-QA reference/translation units, and `docs/rfc-atlas-v3-3-attempt7-discovery-factor-atlas.md:35` identifies those translations as uniform shift and prefix-position-only. The dedicated builder nevertheless constructs and persists `relative_gap` actual-condition units alongside `bare`/`uniform_shift` at `scripts/atlas_discovery_v3_3_qa_pool.py:2592`, and persists `separator_only`, `true_prefix`, and `unrelated_prefix` alongside `bare`/`prefix_position_only` at `scripts/atlas_discovery_v3_3_qa_pool.py:2760-2766`. It then recursively retains every row referenced by each pair at `scripts/atlas_discovery_v3_3_qa_pool.py:2843-2866`.
    reasoning — these extra units are not used by numerical QA: `scripts/extract_atlas_discovery_v3_3.py:423-445` consumes only relative `bare`/`uniform_shift` and context `bare`/`prefix_position_only`. The persisted bundle confirms the overreach: each source has 64 units and 88 rows (`data/atlas_discovery_v3_3_attempt7_qa_compact_v2/prepared/manifest.json:20-94` and `:98-172`) rather than the 32 units/48 rows required for 8 pairs in each null family. In particular, `true_prefix`/`unrelated_prefix` are scientifically meaningful context interventions, not numerical translations.
    impact — the previous science-constructor blocker is fixed structurally, but the output-role firewall remains incomplete: QA-only dev/test still produces persisted non-QA intervention units that could be scored outside the frozen QA path. The manifest/preflight claim `science_population_constructors_invoked=false` is therefore too broad. Under the RFC's fail-closed input-role rule and mandatory prescore `SHIP`, neural inference remains unauthorized.
    fix — for fresh relative pairs emit only `bare` and `uniform_shift`; for fresh context pairs emit only `bare` and `prefix_position_only`. Prune the pair `rows` maps to those exact keys before collecting row IDs, require exactly 32 units and 48 rows/source, and add an exact condition-key test. Regenerate and rebind the compact manifest, population split, final prescore, rebuild report, and all downstream inventories without running inference.

REVISIONS
  (none beyond the blocker)

NITS
  - tests/test_atlas_discovery_v3_3_scoring.py:241-255 — the compact lineage test checks only construct names; assert exact per-construct row-condition keys so unused scientific conditions cannot re-enter the QA bundle.
  - configs/atlas_discovery_v3_3/qa_compact_v2.json:1 — a v2 artifact still uses the generic `atlas_discovery_v3_3_attempt7_qa_pool_run_v1` schema; a v2-specific schema would make accidental use of retired QA configs easier to reject, though exact root/status/hash checks currently distinguish them.

CHECKS RUN
  - `.venv-atlas/bin/python scripts/run_atlas_discovery_v3_3_qa_pool.py --config configs/atlas_discovery_v3_3/qa_compact_v2.json --stage validate-config` → valid; representation scoring unauthorized.
  - `.venv-atlas/bin/python scripts/run_atlas_discovery_v3_3.py --config configs/atlas_discovery_v3_3/run_final_v2.json --stage validate-config` → valid; representation scoring unauthorized.
  - `.venv-atlas/bin/python scripts/prepare_atlas_discovery_v3_3_split.py --output configs/atlas_discovery_v3_3/population_split_v2.json` → exact existing split reproduced; signed terminal verification passed; 32 legacy and 16 fresh pairs/source.
  - `.venv-atlas/bin/python -m pytest -q -p no:cacheprovider tests/test_atlas_discovery_v3_3.py tests/test_atlas_discovery_v3_3_scoring.py` → 24 passed, one Transformers cache deprecation warning.
  - static call-site audit of `build_prepared_data_legacy_do_not_call` → no callers; the public runner imports only the dedicated EOF `build_prepared_data`.
  - independent compact audit → exact three-file allowlist/source; all child hashes match; ordered unit/row/pair lineage is complete and unique; 8 context plus 8 relative pairs/source; zero legacy/fresh document or component overlap.
  - independent intervention-condition audit → every relative pair contains `bare`, `uniform_shift`, and unused `relative_gap`; every context pair contains `bare`, `prefix_position_only`, and unused `separator_only`, `true_prefix`, `unrelated_prefix`.
  - independent science firewall scan → zero fresh or legacy QA documents in every document-bearing final-science row family.
  - independent terminal audit → Ed25519 signature, message digest, independently pinned attempt-5 scoring-config digest, and signer fingerprint all match.
  - independent rebuild audit → all 36 non-manifest child hashes match; manifest sources and normalized preflights match; rebuild report hashes/status agree.
  - runtime audit → attempt-7 run root absent; no neural extractor or trainer process found; QA/final preflights explicitly report `neural_inference_run=false` and `neural_training_run=false`.

CONTRACT COVERAGE
  - dedicated technical-QA-only entry point; legacy full builder never called → met — static call graph and runner import confirm separation at `scripts/atlas_discovery_v3_3_qa_pool.py:2358`.
  - no science task/relation/proper-noun constructors traversed → met — dedicated path constructs only sequential/context QA candidates.
  - persisted external-QA units limited to numerical references/translations → unmet — five non-QA condition types are retained across the two fresh constructs.
  - technical-only opened-input ledger → met — exact source roles, scope, families, and negative outcome flags are bound.
  - attempt-5 terminal config/signature authentication → met — independent digest, fingerprint, and signature checks passed; substitution tests exist at `tests/test_atlas_discovery_v3_3_scoring.py:274-295`.
  - explicit document/component disjointness and science firewall → met — producer checks at `scripts/prepare_atlas_discovery_v3_3_split.py:160-170`; current sets are clean.
  - attempt-7 lineage labels/session and forbidden retired roots → met — no attempt-6 labels remain, one attempt-7 session is used, and superseded attempt-7 roots are denied.
  - neural-inference/training negative flags → met — both compact and final preflights explicitly record false.
  - unchanged scientific prescore and rebuild correctness → met — global feasibility passes and independent rebuild comparison agrees with `reports/atlas_v3_3_attempt7_final_v2_rebuild_check.json:1-15`.
  - lineage/substitution tests → met for terminal and ledger/file lineage; missing exact QA-condition allowlist test is the blocker-enabling gap.

UNKNOWNS
  - Local hashes establish internal provenance consistency but do not independently prove the UD bytes originated from the declared upstream Git commits.
