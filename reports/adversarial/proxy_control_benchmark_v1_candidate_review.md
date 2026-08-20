VERDICT: SHIP
ONE-LINE: The frozen candidate measures behavior and preserves missingness, assignments, component uncertainty, and historical isolation.

freeze_sha256: 9fa74f1731230a8aa0f8c7db29aebbbe0999f74cc355ac565541f31edd42ffdd

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)
  - [medium] scripts/proxy_control_benchmark_v1.py:678-731 — semantic assignment transfers across sources, but the downstream ridge probe is fitted on a deterministic subset of the evaluation source.
    reasoning — this evaluates transferred component selection plus within-source decodability, not a wholly frozen cross-source probe.
    impact — the result must be called source-transferred assignment, not end-to-end cross-source probing.
    fix — preserve the frozen estimator and wording; a future version may separately add a cross-source decoder without relabeling v1.
  - [medium] configs/proxy_control_benchmark_v1/run.json:25-27 — Wikitext and Dolly are opened development activation sources; the fresh panels are controlled generators.
    reasoning — controlled source transfer is stronger for interventions but weaker for natural-corpus generalization.
    impact — the experiment cannot alone establish prevalence on naturally occurring text.
    fix — keep natural-source and controlled-panel evidence separate in the result and paper.
  - [medium] scripts/proxy_control_benchmark_v1.py:903-938 — nine model/layer clusters leave proxy/control association intervals potentially broad.
    reasoning — methods, seeds, concepts, and components are not independent model replications.
    impact — a large row count must not be presented as high-powered model-level evidence.
    fix — use the frozen cluster bootstrap, report the nine-cluster limit, and require post-result claim review before any systematic claim.

NITS            (optional, cap at 5)
  - scripts/proxy_control_benchmark_v1.py:331 — the baseline is correctly named linear erasure rather than exact LEACE.
  - scripts/proxy_control_benchmark_v1.py:756 — per-concept K2 permutation is an optimistic evaluation; use serialized branch IDs to report whether one global identity exists.

CHECKS RUN
  - `pytest -q tests/test_proxy_control_benchmark_v1.py` → 7 passed.
  - deterministic smoke repeated twice → canonical outputs byte-identical.
  - Python compile and shell syntax checks → pass.
  - Pythia and Qwen technical hook smoke → zero patches reproduced logits exactly; nonzero local patches changed logits.
  - tokenizer prescore → both sources retained 48 development and 128 test components per concept for all three models.
  - frozen inventory verification → PASS, candidate inventory `910a20502dc4d72ed61729083c60b529165640e1cb6693dab79db53681da20d2`.
  - preservation audit → all four v4 hashes match; v5 authorization remains false.
  - reproducibility scan → seeded Python/NumPy/Torch, deterministic algorithms, exact model/data revisions, no source hardcoded home paths, and no secrets found.

CONTRACT COVERAGE
  - Proxy hierarchy → met — reconstruction, sparsity, recovery, CKA, leakage, specificity, behavior, and collateral metrics share one schema.
  - Matched baselines → met — K1, equal/asymmetric/swapped K2, PCA, random, task projection, linear erasure, and paired oracle are present.
  - Historical K2 confounds → met — total active budgets, capacity organizations, incoherence, per-concept permutation, and branch identities are explicit.
  - Behavioral causality endpoint → met — natural-delta sufficiency, erasure necessity, sham specificity, target log-odds, non-target KL, effect floor, and patch-norm cap are implemented.
  - Generality → met with stated limit — nine layer/model units across two families and two controlled sources; no natural-corpus-confirmation claim.
  - Positive controls → met — shared/private factors, correlation, asymmetry, nonlinear mixing, common bases, and disjoint train/test rows.
  - Negative statistics → met — raw component rows, component bootstrap intervals, explicit missingness, and frozen smallest effect are retained.
  - One-shot isolation → met — create-once shard paths, frozen inventory, v4 hash verification, and no v5 namespace access.

UNKNOWNS
  - Final runtime and how many controlled rows clear the behavioral-effect floor; missing endpoints remain explicit rather than being imputed.
  - Whether strict CUDA determinism will expose an unsupported kernel during long training; any failure must remain a technical terminal rather than be silently relaunched.
