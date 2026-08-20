CLAIM: SUPPORTED
SUMMARY: The frozen failure decision holds, but it is a high-gate result—not evidence that relational information is absent.

BLOCKERS
  - None for the exact formal decision `RELATIONAL_DECODABILITY_NOT_DEMONSTRATED_FOR_ALL_PRESPECIFIED_TASKS`.

REVISIONS
  - `results/atlas_relation_context_v9_attempt13/report.md:3,11-18` and
    `result.json#/primary_relational_syntax/directions` — describe the raw result as “below the
    prespecified 0.65 normalized-recovery gate,” not generically “not decodable.” All six conditional
    bootstrap intervals for normalized recovery have lower bounds above zero, so there is descriptive
    above-chance transfer, but every point estimate (0.087/0.108 dependency depth, 0.582/0.590 coarse
    deprel, 0.231/0.182 signed distance) misses the much stronger frozen gate in
    `configs/atlas_relation_context_v9/run.json:100-106`. The formal decision is supported; a claim of no
    ordinary decodability is not.
  - `results/atlas_relation_context_v9_attempt13/result.json#/primary_relational_syntax/directions` — keep
    recovery distinct from isolation. No task clears true-minus-child, true-minus-sham, and
    true-minus-sequential-offset requirements in both directions. Coarse deprel is the strongest raw signal,
    yet the sequential control matches or exceeds true in both directions; signed distance beats child
    conditionally but not sham; dependency depth is weak and true is significantly below child for
    CTETEX-to-GENTLE. These patterns do not demonstrate relation-specific representation or nominate an
    architecture.
  - `results/atlas_relation_context_v9_attempt13/COMPLETE.json#/payload/fit_source_component_uncertainty`
    and `scripts/analyze_atlas_relation_context_v9.py:147-216` — intervals resample only test
    document-pair components after fitting and condition on one fitted ridge model and selected alpha. They
    omit fit-source sampling/model-selection uncertainty; this is especially material when GENTLE supplies
    only 10 disjoint components. Do not present the intervals as full two-source population uncertainty.
  - `results/atlas_relation_context_v9_attempt13/result.json#/secondary_sequential_context` — say “not
    measured,” not passed, failed, or falsified. Token identity and required interventions missed prescore
    support, so no secondary scientific score exists and Attempt 13 says nothing outcome-based about
    sequential/context-versus-lexical separation.
  - Preserve the frozen conjunction: all tasks, controls, and directions were required for nomination.
    Favorable individual intervals remain exploratory and were not familywise-adjusted.
  - Preserve negative-evidence asymmetry. The study is exploratory, uses one Pythia-160m checkpoint/layer,
    and its sources had prior technical inference exposure. It supports “this prespecified organization was
    not demonstrated here,” not “relational syntax is absent” or “training cannot ever work.” No SAE,
    position/content, relation-aware, or private/shared training is justified by this outcome.

EVIDENCE CHECKED
  - Signed terminal, STARTED record, activation completions, result completion, and science authorization —
    all Ed25519 signatures and linked SHA-256 identities verified; terminal is complete/no-retry, Attempt 12
    is unchanged, and no optimizer/checkpoint/neural or representation training ran.
  - Adversarial review, final freeze, and run config — exact candidate was SHIP-reviewed before one-shot
    authorization; protocol, layer, sources, 0.65 recovery gate, 0.02 isolation margin, and no-training status
    were frozen.
  - Delta calibration and result audit — the scale-normalized repair was prospective; all 410 GENTLE and 640
    CTETEX relation rows were informative, with zero low-norm exclusions.
  - Prepared manifest and relation rows — the relation endpoint met support, control, fold, row-cap, and
    component requirements; the secondary endpoint remained independently ineligible.
  - Analyzer and results — all six primary direction/task cells were measurable and complete; none reached
    normalized recovery 0.65 or passed every isolation contrast, while every conditional raw-recovery lower
    bound was above zero.
  - No new model inference or experiment was run during claim review.

UNKNOWNS
  - Additional uncertainty from alpha selection and fit-source sampling, especially for the 10-component
    GENTLE fit source.
  - Replication on confirmatory corpora, other layers, models, seeds, or checkpoints.
  - Whether sham/sequential performance reflects lexical/syntactic confounding, control construction, domain
    shift, or genuinely distributed representations.
  - Sequential/context-versus-lexical selectivity, because the secondary module was prescore-ineligible and
    scientifically unscored.
