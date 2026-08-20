VERDICT: SHIP
ONE-LINE: Signed EWT QA failure mandates technical ineligibility; it yields no scientific organization result.

BLOCKERS

None.

REVISIONS

None.

NITS

- `pilot_runs/20260803_atlas_discovery_v3_3_attempt7/TERMINAL.json:3-13` authenticates the failed envelope/children and attests that later stages did not run, but it does not bind `pipeline.log`, `PIPELINE_COMMANDS.txt`, or an exact recursive run-directory inventory. The terminalizer is also absent from the frozen implementation inventory at `configs/atlas_discovery_v3_3/scoring.json:206-222`. This does not undermine the formal stop—the independently signed EWT failure already triggers it—but future protocols should create the terminal inside an inventory-bound runner and sign the command-log digest plus final run inventory.

CHECKS RUN

- `sha256sum` over the scoring config, SHIP implementation review, prescore review, rebuild report, failed QA envelope, both QA children, and terminal — PASS. The current scoring digest is `2cc24b036a00cae9e96c42404b6b0b9c211e3059f5f0a32876a15bf1b6fb19aa`; QA/terminal lineage and every recorded child digest match bytes on disk.
- Read-only Python audit using the pinned public Ed25519 key — PASS. Both the failed EWT QA envelope and `TERMINAL.json` signatures verify; their canonical message hashes match; the signer fingerprint is the frozen `56308d…025d` value.
- `load_scoring_config(configs/atlas_discovery_v3_3/scoring.json)` plus independent inventory hashing — PASS. The authorized config binds the v3 prescore, compact QA manifest, rebuild, prescore `SHIP`, implementation `SHIP`, extractor, analyzer, tests, and no-training flag (`configs/atlas_discovery_v3_3/scoring.json:194-256`).
- Independent saved-array/row audit — PASS. The exact expected EWT lineage and 48 ordered underlying QA units reconstruct from the frozen legacy/fresh parents; all four NPZ arrays are finite float32 `(72, 768)` arrays; both reference repeats are bit-identical; candidate inputs preserve tokens, masks, and selected positions and differ only by the frozen uniform position-ID translation (`scripts/extract_atlas_discovery_v3_3.py:395-403,406-466`). Recomputed tolerance and all four panel statistics equal the signed payload exactly.
- Run-tree/process/output audit — PASS within the declared run namespace. The run has one EWT staging directory and no promoted `numerical_qa`, GUM QA, full authorization, activation directory, analysis output, or training/checkpoint artifact. `pipeline.log:1-25` contains one EWT QA `STAGE_START` and ends at the frozen QA failure; no attempt-7 extractor/analyzer is running.
- Static fail-closed review — PASS. The extractor signs and preserves a failed QA bundle before raising (`scripts/extract_atlas_discovery_v3_3.py:691-725`), while full authorization requires verified PASS envelopes for both EWT and GUM (`:730-745`). The RFC freezes termination without retry on any panel/family/source failure (`docs/rfc-atlas-v3-3-attempt7-discovery-factor-atlas.md:33-35`). No inference was run during this review.

CONTRACT COVERAGE

- Frozen scoring and implementation provenance → met — all configured hashes and both required `SHIP` attestations match; scoring authorized numerical QA only and explicitly forbade neural training (`configs/atlas_discovery_v3_3/scoring.json:200-256`).
- Signed EWT QA integrity → met — envelope and child hashes/signature verify; the signed model, layer, GPU UUID, float32 dtypes, deterministic runtime, no optimizer/checkpoint/training assertions, parent lineage, and exact row counts are internally consistent (`QA_COMPLETE.json:3-30,77-113,115-119`).
- Frozen numerical gate result → met — all four required EWT cells fail: fresh prefix 5/8 rows, fresh uniform 12/16, legacy prefix 14/16, and legacy uniform 28/32 (`QA_COMPLETE.json:31-75`). In total, 59/72 rows and 1,051/55,296 elements exceed the bound. Exact reference repeats make `e=0`, so the frozen tolerance is valid at `atol=5e-7`, `rtol=5e-6`; the stop is caused by translated-versus-reference discrepancies, not repeated-reference nondeterminism (`:108-113`).
- No retry/GUM/full/analysis/training in the frozen run namespace → met — the log stops after the first EWT failure (`pipeline.log:1-25`), later output paths are absent, and the signed terminal records all corresponding false flags (`TERMINAL.json:9-13,60-66`). The current artifact tree contains only the one failed EWT staging bundle.
- Fail-closed terminal interpretation → met — the signed terminal binds the exact failed envelope and children, copies the recomputed failures, and records `TERMINAL_TECHNICALLY_INELIGIBLE` (`TERMINAL.json:3-8,14-71,74-78`). This is exactly the RFC outcome for any numerical-QA failure (`docs/rfc-atlas-v3-3-attempt7-discovery-factor-atlas.md:49-51`).
- Scientific claim boundary → met — no full activations or representation analysis exist, and `scientific_candidate_decision_available=false` (`TERMINAL.json:10-12,62-66`). Therefore attempt 7 produces no result about any proposed organization, no nomination, no evidence for or against disentanglement, and no authorization to train. The small scale of most discrepancies does not convert this technical failure into a scientific position/content result.

UNKNOWNS

- The unsigned pipeline log and current directory absence cannot cryptographically exclude an unlogged invocation outside the declared run namespace. The signed terminal attests no retry/later stage, and all retained run evidence corroborates it, but this distinction should be preserved in any public provenance wording.
- The artifacts do not determine why an exact position-ID translation exceeds the frozen elementwise tolerance despite bit-identical reference repeats. Diagnosing finite-precision RoPE behavior, kernel effects, or a misspecified null would require a separately prespecified technical study; it cannot justify relaxing or retrying attempt 7.
- GUM numerical QA and all three scientific organizations are genuinely unobserved, not failed. No cross-corpus scientific conclusion can be inferred from the EWT technical stop.
