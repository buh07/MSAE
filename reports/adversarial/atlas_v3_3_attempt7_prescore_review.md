VERDICT: BLOCK
ONE-LINE: Compact outputs are clean, but QA data still traverses prohibited science constructors.

BLOCKERS
  - [critical] docs/rfc-atlas-v3-3-attempt7-discovery-factor-atlas.md:24 — dev/test inputs may create only numerical-QA reference/translation units and cannot enter probes, relations, non-QA interventions, nuisance fits, projections, bootstraps, or decisions. The revised builder still describes itself as building “all label-only rows” at `scripts/atlas_discovery_v3_3_qa_pool.py:1249-1250`, creates every main-task candidate at `scripts/atlas_discovery_v3_3_qa_pool.py:1386-1431`, creates relation rows at `scripts/atlas_discovery_v3_3_qa_pool.py:1482-1528`, and constructs proper-noun substitution candidates at `scripts/atlas_discovery_v3_3_qa_pool.py:1830-1935`; the QA-only branch is reached only afterward at `scripts/atlas_discovery_v3_3_qa_pool.py:2015`.
    reasoning — the persisted per-source bundles are now correctly pruned to 16 QA pairs and their referenced units/rows, but the builder itself is still the copied science builder. QA-only dev/test data therefore enters task, relation, and non-QA intervention construction in memory before those products are discarded. The opened ledger preserves the same contradiction: source roles are corrected, but its scope is still `declared_scientific_inputs_loaded_by_the_v3_runner` at `data/atlas_discovery_v3_3_attempt7_qa_compact/opened_input_ledger.json:22`.
    impact — this does not satisfy the RFC's construction-time role firewall or the prior review's required dedicated QA-only builder. Since `docs/rfc-atlas-v3-3-attempt7-discovery-factor-atlas.md:47-51` requires a prescore `SHIP` and treats an input-role failure as technically ineligible, neural inference must remain blocked.
    fix — move compact QA preparation into a dedicated builder or an early, structurally separate code path that constructs only relative-gap and context-factorial candidates, selects the frozen 8+8 panel, and emits only the referenced units/rows/pairs. Do not compute main task labels, relation rows, proper-noun substitution, cross-family support, bootstrap support, or common-cell machinery in QA mode. Give its ledger a compact-QA schema and `technical_numerical_qa_inputs_only` scope, then regenerate and rebind the compact manifest, split, final science prescore, rebuild, and tests.

REVISIONS
  - [high] scripts/prepare_atlas_discovery_v3_3_split.py:18-23 — terminal verification obtains its public key from the mutable historical scoring config but never checks that file against `payload.scoring_config.path/sha256` before trusting the key, nor checks the public-key fingerprint.
    reasoning — independent verification confirms the current scoring-config digest and key fingerprint match the signed terminal, so the present artifact is authentic. The implementation, however, can authenticate a substituted terminal if both the terminal and unpinned key-bearing config are replaced before split regeneration.
    impact — signed lineage is not fail-closed at its trust root, contrary to the requested signed-terminal verification guarantee.
    fix — require the terminal-declared scoring-config path, verify its SHA-256 before reading `qa_signer`, verify the decoded public-key fingerprint, and record both verified digests in the population-split artifact; add negative tests for config/key/signature substitution.
  - [medium] scripts/prepare_atlas_discovery_v3_3_split.py:37-39 — construction explicitly checks fresh-versus-legacy and fresh-versus-train document overlap, but never explicitly checks `legacy_components & used_components`.
    reasoning — current artifacts and `tests/test_atlas_discovery_v3_3.py:15-22` show zero component overlap, and component identities derive from disjoint documents, but the split builder itself does not fail closed on the RFC's component-disjointness condition.
    impact — a component-identity collision or later component-generation change would be caught only by a separate test, not by the artifact producer.
    fix — reject any legacy/fresh component intersection in the split producer and persist explicit zero document/component intersection counts.
  - [medium] scripts/atlas_discovery_v3_3.py:1288-1360 — the final science ledger and error/counter labels still call the population split an attempt-6 firewall; the persisted stale roles appear at `data/atlas_discovery_v3_3_attempt7_final/opened_input_ledger.json:4` and `data/atlas_discovery_v3_3_attempt7_final/opened_input_ledger.json:19`.
    reasoning — `configs/atlas_discovery_v3_3/run_final.json:170` correctly resolves the prior session-name conflict to one attempt-7 session, but the authoritative lineage ledger remains mislabeled.
    impact — operators and downstream audit code receive internally inconsistent attempt identity even though the data hashes are correct.
    fix — rename all attempt-6 role/error/counter strings to attempt 7, rebuild, and add exact ledger-role assertions.
  - [medium] configs/atlas_discovery_v3_3/run_final.json:60-71 — the final forbidden-cache list retires the old full QA pool but omits the superseded prior science roots `data/atlas_discovery_v3_3_attempt7` and `data/atlas_discovery_v3_3_attempt7_rebuild1`.
    reasoning — `data/atlas_discovery_v3_3_attempt7/SUPERSEDED_PRESCORE.json:1-8` correctly marks the prior prescore superseded before inference, and the final builder pins its own data root. Explicit cache refusal should nevertheless cover every retired attempt-7 parent, not only the old QA pool.
    impact — future extraction/analysis configuration could accidentally accept a superseded science cache unless another exact-root check catches it.
    fix — add both superseded science roots to `forbidden_cache_roots` and test that final extraction rejects them.

NITS
  - data/atlas_discovery_v3_3_attempt7_final/preflight.json:94-96 — add explicit `neural_inference_run=false`, matching the compact QA preflight, rather than relying only on `representation_scoring_run=false`.
  - tests/test_atlas_discovery_v3_3.py:9-32 — add an exact per-source compact-file allowlist test, compact row/unit/pair lineage test, opened-ledger scope/role test, and malformed-terminal negative fixtures; the current three tests do not detect the blocker.

CHECKS RUN
  - `.venv-atlas/bin/python scripts/run_atlas_discovery_v3_3_qa_pool.py --config configs/atlas_discovery_v3_3/qa_compact.json --stage validate-config` → valid; representation scoring unauthorized.
  - `.venv-atlas/bin/python scripts/run_atlas_discovery_v3_3.py --config configs/atlas_discovery_v3_3/run_final.json --stage validate-config` → valid; representation scoring unauthorized.
  - `.venv-atlas/bin/python scripts/prepare_atlas_discovery_v3_3_split.py --output configs/atlas_discovery_v3_3/population_split.json` → existing split reproduced exactly; signature verification succeeded; 32 legacy and 16 fresh pairs/source.
  - `.venv-atlas/bin/python -m pytest -q -p no:cacheprovider tests/test_atlas_discovery_v3_3.py` → 3 passed.
  - independent compact-bundle audit → each source contains exactly `activation_rows.jsonl`, `inference_units.jsonl`, and `intervention_pairs.jsonl`; hashes/counts match the manifest; 64 units, 88 unique ordered rows, and 16 pairs (8 context + 8 relative) per source; every pair reference resolves exactly.
  - independent split/firewall audit → compact manifest and split pair/document/component sets agree; fresh panels are internally document/component-disjoint, legacy-disjoint, and absent from every document-bearing final-science row; all legacy documents are also absent.
  - independent terminal audit → Ed25519 signature valid; message digest, terminal-declared historical scoring-config hash, and public-key fingerprint all match current frozen artifacts.
  - attempt-5 versus final config comparison → `data`, `support`, `probe`, `pooled_bootstrap`, `interventions`, `cross_family`, and `projection` remain structurally identical.
  - independent final rebuild audit → all 36 non-manifest prepared child hashes are identical; manifest `sources` are exactly equal; normalized preflights are equal; report hashes/status agree.
  - retirement and runtime audit → old full QA and prior science retirement-marker hashes match; attempt-7 run root is absent; no extractor/trainer process found; compact/final preflights report no scoring or training.

CONTRACT COVERAGE
  - compact QA persisted artifacts limited to referenced units/rows/pairs → met — exact file-set and lineage audit passed for both sources.
  - QA-only construction-time role firewall → unmet — dev/test still traverses main-task, relation, and proper-noun science constructors before pruning.
  - QA ledger source roles → partial — both sources and manifest are `technical_numerical_qa_only`, but ledger scope still says scientific inputs.
  - exact legacy replay and deterministic fresh 8+8 selection → met — independent reconstruction and producer rerun match the frozen split.
  - signed attempt-5 terminal verification → partial — present signature is authentic, but producer does not authenticate the key-bearing config before trusting it.
  - document/component disjointness and science exclusion → partial — all current sets are clean and document checks fail closed; producer lacks an explicit legacy/fresh component check.
  - old full-pool and prior-science retirement → met — digest-bound markers record no inference/training; final cache denylist should be completed.
  - unchanged scientific gates and feasible final prescore → met — all frozen scientific sections match attempt 5 and the final global gate passes.
  - final rebuild correctness → met — independent child/manifest/preflight comparison agrees with `reports/atlas_v3_3_attempt7_final_rebuild_check.json:1-13`.
  - no neural inference or training → met — no run root/process and all available status evidence is negative.
  - stale session identity → met — final configs now use only `msae_atlas_discovery_v3_3_attempt7_20260803`; stale ledger role strings remain.

UNKNOWNS
  - Local hashes establish internal provenance consistency but do not independently prove the UD bytes originated from the declared upstream Git commits.
