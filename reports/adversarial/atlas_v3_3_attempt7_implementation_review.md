VERDICT: BLOCK
ONE-LINE: Analyzer violates frozen deltas, bootstrap validity, projection assignments, lineage, and terminal ineligibility; inference must remain blocked.

BLOCKERS        (must fix before proceeding; empty if none)
  - [critical] scripts/analyze_atlas_discovery_v3_3.py:34-45 — analysis metadata files are opened without checking their manifest hashes.
    reasoning — `_load_source_bundle` authenticates only inference units, activation rows, and intervention pairs; `relation_rows.jsonl`, `cross_family_rows.jsonl`, every task JSONL, and `pair_rows.jsonl` are then read directly. The frozen manifest already contains hashes for these children, but the analyzer never compares them.
    impact — changing a task label, component/fold, relation row, or cross-family stratum after prescore changes fits, bootstraps, bases, and the terminal decision while every cache/signature check still passes, violating attempt-7 exact lineage.
    fix — before loading any analysis row, verify every source child against the pinned manifest hash and row count, require exact file/endpoint inventories and foreign-key/order integrity, and record that verified inventory in result lineage.
  - [critical] scripts/analyze_atlas_discovery_v3_3.py:57-61,87-100 — nuisance lemma vocabulary is derived from the current task's target labels rather than fit-source lemmas.
    reasoning — `fit_lemma_vocab(fit_rows)` counts `row['label']`; for `start_distance`, syntax, token identity, and the other non-lemma tasks those values are target classes, so `_main_nuisance` maps essentially every actual lemma to `__NONRETAINED__`.
    impact — the nuisance-only and combined probes do not implement the frozen nuisance table, so incremental-F1 gates can be spuriously inflated and are not the prescored estimand.
    fix — derive the capped document-frequency lemma vocabulary once from fit-source lemma-identity/main metadata only, then apply that same frozen fit-only vocabulary to every nuisance design in the direction; add an end-to-end leakage fixture that fails with the current code.
  - [critical] scripts/analyze_atlas_discovery_v3_3.py:114-121 — relation transfer silently drops held-out rows whose labels are absent in the fit source.
    reasoning — line 115 filters `tr` using fit-derived classes before the equality check, so the check cannot detect held-out-only classes; target labels therefore alter the evaluated row population.
    impact — an endpoint that must be ineligible can instead be scored on an easier target-label-selected subset, violating fit-only transfer and fail-closed endpoint eligibility.
    fix — never filter held-out relation rows by their target label; validate the frozen class inventory first and return an explicit ineligible endpoint when fit/held-out class support is not exact.
  - [critical] scripts/atlas_discovery_v3_3_analysis.py:13-20; scripts/analyze_atlas_discovery_v3_3.py:79-85,120-121,153-161,173-194 — bootstrap draws missing a frozen target class remain finite and several gates do not require 490 finite draws.
    reasoning — `macro_f1` returns a finite value for an absent class, and none of the task, relation, pooled-specificity, or projection loops explicitly rejects missing-class draws. Cross-family `pass` checks interval bounds but not `finite >= 490`.
    impact — invalid resamples count toward descriptive lower bounds and can pass raw, incremental, specificity, relation, selectivity, or capture gates contrary to the exact ordinary/node-bootstrap contract.
    fix — centralize draw validation that requires every frozen class, positive finite denominators, and finite paired metrics; never redraw; require at least 490/500 valid draws at every applicable gate and test shared-document multiplicities and missing-class maps end to end.
  - [critical] scripts/analyze_atlas_discovery_v3_3.py:123-142 — the relative-gap and proper-noun vectors are not the frozen single-target deltas, and the required intervention atlas is largely absent.
    reasoning — relative gap is encoded as `(post response) - (pre response)` and proper noun as `(changed response) - (control response)` at lines 125 and 128, then those adjusted vectors are reused for classification and bases. The contract instead freezes raw post-pivot `relative_gap-bare` and raw changed-token `target-source` deltas for those stages; target/control contrasts are separate summaries. Lines 139-142 report only delta norms, basis singular values, and an optional control norm, omitting cosine distance, relative L2, numerical no-op error, explicit target/control contrast, and raw delta-covariance spectrum.
    impact — cross-family specificity mixes multiple token deltas, projection bases are built from the wrong estimand, and the terminal report cannot distinguish null, target, and control effects as required.
    fix — materialize separately named raw single-target deltas and adjusted effect contrasts; use only the exact raw vectors for classifier/basis construction, use adjusted contrasts only for the specified effect summaries, and report all frozen intervention statistics per source/condition.
  - [critical] scripts/analyze_atlas_discovery_v3_3.py:163-197 — projection organizations do not implement their frozen task/construct assignments or construct weighting.
    reasoning — every organization evaluates only `start_distance`, `relative_quartile`, and `token_identity` (line 171), and then averages those three tasks directly (line 195). This double-weights the sequential construct relative to lexical, omits the broad organization's syntax-child recovery entirely, and never performs the required projected/complement paired `[child, head-child]` relation evaluation for `token_local_vs_context_dependent`.
    impact — assigned recovery, leakage, selectivity, and nomination can describe a different organization than the RFC table and can pass while a required syntax/relational construct was never measured.
    fix — encode exact per-organization P/Q/external assignments; aggregate tasks inside sequential and syntax first, then equal-weight constructs; implement the block-diagonal projected paired relation probe and include its gates only where prescribed.
  - [critical] scripts/analyze_atlas_discovery_v3_3.py:167-197 — capture assignment and rank eligibility are hardcoded incorrectly across organizations.
    reasoning — line 187 assigns every intervention except proper noun to P for every candidate even though `token_local_vs_context_dependent` does not assign relative gap to its P block; relation capture is never reported. `make_projector` may return rank below 8, but lines 170-197 never convert that condition to candidate `ineligible`. Rank sensitivity is checked per the three hardcoded tasks rather than every required construct.
    impact — a candidate can pass with the wrong side assignment, missing required construct capture, or a projector explicitly declared rank-ineligible.
    fix — freeze explicit P/Q/unassigned/external mappings for every task and delta family, compute organization-specific assigned/opposite controls including relation where required, mark numerical rank below 8 ineligible, and apply the 8/16/32 positive-sign rule at construct level.
  - [critical] scripts/analyze_atlas_discovery_v3_3.py:196-225 — candidate ineligibility and technical failure are unrepresentable in terminal aggregation.
    reasoning — projection status is only `passed` or `eligible_not_passed`; final statuses again choose only those two values, and `terminal_outcome` is called with `technical_failure=False` unconditionally. Degenerate bases, lineage/cache failures, missing endpoints, and other required failures raise before any total result is written.
    impact — the mandated `technically_ineligible` outcome cannot be produced for the exact failures that require it; a required ineligible endpoint can be collapsed into scientific failure or no terminal artifact.
    fix — model each endpoint as `ineligible`, `eligible_not_passed`, or `passed` with explicit reasons; propagate global firewall/lineage/dtype/QA/cache failures into technical status; aggregate mechanically and write a total fail-closed terminal outcome without converting missing measurements into negative evidence.
  - [critical] scripts/extract_atlas_discovery_v3_3.py:404-445,468-500,523-539 — exact QA order and signed lineage are not preserved or verified.
    reasoning — `_qa_panel_units` discards the frozen pair order by grouping every relative pair before every context pair; the frozen fresh list is context-first, but the emitted rows are uniform-shift-first. The signed lineage omits the activation-row child hash, and `_verify_qa` never checks `qa_input_lineage`, exact model equality, the declared cache dtype, or deterministic environment fields against the frozen parents/config.
    impact — the run is not an exact replay of the frozen panels, and a reused signed QA artifact can pass verification without asserting the complete child/environment lineage required by attempt 7.
    fix — preserve the literal pair-ID order (use explicit index lists rather than reordering for family statistics), include split/config/manifest plus units/rows/pairs hashes for both parents, and validate every signed model/dtype/environment/lineage field and NPZ structure exactly.
  - [high] scripts/extract_atlas_discovery_v3_3.py:504-516,613-680 — the one-physical-GPU sequential and full-cache float32 attestation contracts are incomplete.
    reasoning — locks are source-specific, so EWT and GUM QA/full calls can run concurrently on the same configured GPU. Full completion does not record parameter dtype, hidden dtype, or autocast state, and cache verification does not validate deterministic environment fields; these are explicit signed-artifact requirements.
    impact — concurrency can change numerical behavior/resource use, while a cache that lacks the required computation/determinism attestations is accepted as complete.
    fix — use one attempt-wide GPU extraction lock across both sources/stages, and record/verify exact parameter, computation/hidden, cache, autocast, TF32, deterministic-algorithm, CUBLAS, device UUID, batch, model, and environment fields for QA and full caches.
  - [high] tests/test_atlas_discovery_v3_3_scoring.py:194-323 — tests cover primitives but never exercise the actual analyzer pipeline or decision aggregation.
    reasoning — no test imports `evaluate_direction`, `evaluate_relation_direction`, `bootstrap_metrics`, `delta_for_pair`, `intervention_atlas`, `cross_family_direction`, `projection_direction`, or `run`. The nuisance-only fixture compares two hand-built ridge designs, not the production nuisance builder; shared-document bootstraps, source reversal, relation effects, intervention contrasts, endpoint ineligibility, organization assignments, rank sensitivities, and terminal outcomes are absent.
    impact — every analyzer defect above coexists with 21 passing tests, so the attempt-7 mandatory synthetic-fixture gate is unmet before irreversible inference.
    fix — add minimal temp-root/planted end-to-end fixtures for every RFC-listed regime plus tampered analysis-child lineage, exact QA order, missing-class draws, all organization mappings/ranks, and ineligible-versus-failed aggregation.
  - [high] scripts/analyze_atlas_discovery_v3_3.py:223-230 — the create-once output is not the complete frozen report bundle.
    reasoning — only `result.json` and a minimal unsigned digest marker are written. There is no detailed Markdown atlas, verified artifact inventory, input/environment manifest, exact rerun command, or post-promotion verification; stale PID staging directories are ignored and files/directories are not fsynced.
    impact — the M5/attempt-7 reports contract is unmet, and a crash can leave unaudited partial staging while a later run silently proceeds to another create-once candidate.
    fix — define an exact create-once artifact allowlist containing the machine result, detailed Markdown, lineage/environment/rerun manifest, and authenticated completion inventory; use a lock, refuse stale staging, fsync, verify before and after atomic promotion, and test concurrent/stale recovery.

REVISIONS       (should fix; not blocking)
  - [high] scripts/analyze_atlas_discovery_v3_3.py:4-13,97-100; configs/atlas_discovery_v3_3/scoring.json:163 — closed-form ridge is configured for CUDA but the analyzer does not set/check deterministic algorithms or bind its device UUID before the create-once analysis.
    reasoning — importing the extractor happens only after Torch is already imported, and analysis never calls the extraction determinism/runtime gates.
    impact — probe fitting can depend on an unrecorded GPU/runtime different from the frozen execution environment.
    fix — preferably run deterministic float64 ridge on CPU; otherwise establish the deterministic CUDA environment before Torch initialization, pin/verify the physical GPU and versions, and record them in the terminal bundle.
  - [medium] scripts/analyze_atlas_discovery_v3_3.py:163-165 — raw-coordinate probe-weight blocks are class-centered but not explicitly Frobenius-normalized as frozen.
    reasoning — subsequent orthonormalization often makes a scalar normalization span-invariant, but the executable construction still differs from the literal prescribed algorithm.
    impact — exact protocol auditability is weakened and later changes to block assembly could make the omission material.
    fix — perform and assert finite nonzero Frobenius normalization on every probe block before construct assembly, with a planted scale-invariance test.

NITS            (optional, cap at 5)

CHECKS RUN
  - `.venv-atlas/bin/python -m pytest -q tests/test_atlas_discovery_v3_3_scoring.py` → 21 passed, one unrelated Transformers cache deprecation warning; no neural inference ran.
  - `.venv-atlas/bin/python -m py_compile scripts/extract_atlas_discovery_v3_3.py scripts/atlas_discovery_v3_3_analysis.py scripts/analyze_atlas_discovery_v3_3.py` → passed.
  - `load_scoring_config(configs/atlas_discovery_v3_3/scoring.json)` → refused safely with `unknown scoring schema`: loader requires scoring v2 while the draft is v1.
  - implementation-inventory comparison → current draft is stale for `scripts/analyze_atlas_discovery_v3_3.py`, `tests/test_atlas_discovery_v3_3.py`, and `tests/test_atlas_discovery_v3_3_scoring.py`; current config SHA-256 is `f062975c3424eef6c96e8699a44576d60aa845b0d3428ed3fdc6fb1b0c98367f`.
  - exact-panel probe on the v3 fresh EWT list → frozen first/last constructs are context/relative, while `_qa_panel_units` emits uniform-shift/prefix-position-only, confirming order reversal.
  - missing-class metric probe → a draw containing only class `a` for frozen classes `(a,b)` returned finite macro-F1 `0.5` and normalized recovery `0.25`, confirming invalid draws are counted.

CONTRACT COVERAGE
  - QA authorization, exact panels, and lineage → partial — external/legacy panels, signatures, status gates, and formulas exist; exact order and complete verified child/environment lineage do not.
  - float32/no-training extraction → partial — model/hidden/cache float32 checks and no-gradient inference exist; sequential physical-GPU execution and complete signed dtype/determinism assertions do not.
  - analysis child/cache lineage → unmet — task, relation, pair, and cross-family children are consumed without manifest-hash verification.
  - fit-source-only transfer and nuisance encoding → unmet — task labels construct the lemma nuisance vocabulary and relation evaluation filters held-out labels.
  - endpoint eligibility and 500-draw bootstrap → unmet — missing-class draws remain finite, 490-draw gates are incomplete, and endpoint ineligibility is not represented.
  - relational advantage → partial — raw child/true/sham comparison is present; class handling and projected paired relation evaluation violate the contract.
  - intervention summaries and factorial deltas → unmet — relative/proper vectors are wrong for classifier/basis use and required summaries are missing.
  - cross-family adjusted predictive specificity → partial — fit-only encoders, full/common sign, node weighting, and basis overlap exist; wrong deltas and incomplete bootstrap validity invalidate the decision gate.
  - projector/basis construction and construct weighting → unmet — organization assignments, syntax/relation evaluation, equal construct weights, capture mapping, and rank-ineligibility logic are incomplete or wrong.
  - rank-8/16/32 sensitivity → unmet — low numerical rank is not ineligible and sign checks target the wrong hardcoded task inventory.
  - candidate aggregation and total terminal outcome → unmet — `ineligible` and technical failure cannot reach the terminal aggregator.
  - create-once result/report bundle → partial — final-directory overwrite is refused and rename is atomic, but the required report/inventory and crash-safe staging protocol are absent.
  - mandatory synthetic coverage → unmet — tests pass only helper-level checks and omit most RFC-listed pipeline regimes.
  - current inference authorization → met as a safety stop — the stale draft/schema/inventory cannot load and must not be refreshed until all blockers receive a new independent `SHIP`.

UNKNOWNS
  - No neural model call, activation extraction, or full analysis was run; production CUDA behavior and numerical QA remain intentionally unverified.
  - The current scoring config points to older non-`v3` compact/split/prescore artifacts while tests exercise `*_v3` artifacts; the maintainer must identify the single final prescore graph before regenerating hashes.
