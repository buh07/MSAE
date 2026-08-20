VERDICT: SHIP
ONE-LINE: The plan isolates a new natural-text benchmark while preserving K2 closure and prospectively freezing joint-control endpoints.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)
  - [medium] PLAN_JOINT_CONTROLLABILITY_V3.md:33 — released SAE formats use different normalization conventions.
    reasoning — finite shapes alone cannot establish semantic equivalence of decoder directions.
    impact — an incorrectly normalized public SAE could create a method-specific artifact.
    fix — record each raw equation/config and treat reconstruction as within-format; use normalized decoder directions and matched raw patch norms for cross-method intervention comparisons.
  - [medium] PLAN_JOINT_CONTROLLABILITY_V3.md:18 — WIKI_A/B are hash partitions of one corpus.
    reasoning — both share source construction and cannot establish domain transfer.
    impact — a favorable result would otherwise be overclaimed.
    fix — encode `within_corpus_transfer=true` in config/results and prohibit `cross_domain` language.
  - [medium] PLAN_JOINT_CONTROLLABILITY_V3.md:47 — a causal toy control does not validate HuggingFace hook placement.
    reasoning — the real intervention path adds patches through architecture-specific block hooks.
    impact — a hook-index error could survive the analytic control.
    fix — add a pre-opening technical hook smoke at each registered architecture that compares a zero patch exactly and a nonzero patch for finite output change; do not inspect scientific labels.

NITS            (optional, cap at 5)
  - PLAN_JOINT_CONTROLLABILITY_V3.md:58 — name teacher-forced continuation NLL as descriptive unless its gate is explicitly frozen.

CHECKS RUN
  - `bin/check-plan --path PLAN_JOINT_CONTROLLABILITY_V3.md` → PLAN: PASS after adding milestones, definition-of-done, and verification sections.
  - inspected `reports/architecture_program_closure_v2.json` → all K2/current-program training authorizations false.
  - inspected free GPU inventory → eight RTX 6000 Ada devices idle.

CONTRACT COVERAGE
  - preserve K2 closure → met — explicit non-goal and acceptance criterion.
  - standard released methods → met — three public SAE releases plus registered baselines.
  - natural task and behavioral/collateral endpoints → met — Wikitext continuation design and gates specified.
  - matched strength → met — three frozen norm ratios.
  - end-to-end positive control → met — blocks real workers.
  - supervised skyline prospectively → met — development-only and no SAE/LM training.
  - launch in tmux and return before results → met — lifecycle step 5/6.

UNKNOWNS
  - Public weight downloads and Gemma license-cache availability must pass preflight.
  - The natural effect gate may fail for small models; the plan correctly preserves that outcome.
