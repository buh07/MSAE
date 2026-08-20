VERDICT: SHIP
ONE-LINE: The frozen benchmark directly tests proxy-to-control dissociation without reopening v4 or treating controlled panels as corpora.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)
  - [medium] PLAN_PROXY_CONTROL_BENCHMARK_V1.md:31-39 — the two fresh controlled panels are not natural-corpus replications.
    reasoning — deterministic template sources improve intervention validity but do not establish natural-text generality.
    impact — the final paper must keep controlled-source transfer distinct from Wikitext/Dolly development-source transfer.
    fix — preserve the current explicit limitation and do not describe the fresh panel as two-corpus confirmation.
  - [medium] PLAN_PROXY_CONTROL_BENCHMARK_V1.md:65-73 — K1 atom assignment and K2 branch permutation use source labels.
    reasoning — these are supervised evaluation mappings even when the underlying dictionary is unsupervised.
    impact — calling the complete pipeline unsupervised would overstate semantic identification.
    fix — report dictionary training and semantic assignment separately, with source-transfer assignment frozen before the opposite source is scored.

NITS            (optional, cap at 5)
  - PLAN_PROXY_CONTROL_BENCHMARK_V1.md:35 — call the erasure baseline “least-squares concept erasure” unless exact LEACE equations are implemented.
  - PLAN_PROXY_CONTROL_BENCHMARK_V1.md:79 — retain all raw log-odds effects alongside normalized recovery.

CHECKS RUN
  - `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN_PROXY_CONTROL_BENCHMARK_V1.md` → PASS.
  - local model-cache inspection → exact revisions for two Pythia scales and Qwen 0.5B are present.
  - `nvidia-smi` preflight → eight RTX 6000 Ada GPUs free at review time.

CONTRACT COVERAGE
  - Primary proxy-to-control question → met — common eight-level hierarchy and aggregation are frozen.
  - Matched baselines and branch permutation → met — K1, three K2 organizations, five linear controls, and source-transfer assignment are specified.
  - Downstream behavioral intervention → met — natural-delta normalization, target log-odds, non-target KL, sham, and patch-norm eligibility are specified.
  - Generality → met with limitation — three layers, three models, two families; controlled panels are explicitly not natural corpora.
  - Positive controls and equivalence → met — correlated private/shared DGP and smallest-effect logic are frozen.
  - Historical preservation → met — v4 hashes and v5 prohibition are definition-of-done conditions.

UNKNOWNS
  - Runtime until the full shards finish; launch verification rather than result completion is the requested stopping point.
  - Whether tokenizer eligibility leaves the planned component count; the prescore must fail before inference if it does not.
