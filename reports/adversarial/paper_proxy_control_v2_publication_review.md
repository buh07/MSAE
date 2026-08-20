VERDICT: BLOCK
ONE-LINE: The paper's broad benchmark claim is already occupied, while its distinctive joint-control result lacks natural and standard-SAE validation.

BLOCKERS        (must fix before proceeding; empty if none)
  - [critical] PAPER.md:19-38 — the abstract presents proxy-to-control failure across multiple decomposition classes as the main contribution without positioning it against prior benchmark evidence.
    reasoning — SAEBench already reports that proxy improvements do not reliably translate to practical performance (https://proceedings.mlr.press/v267/karvonen25a.html); AxBench already compares representation methods for steering and finds simple baselines outperform SAEs (https://proceedings.mlr.press/v267/wu25a.html); an ICLR-2026 submission directly compares interpretability and steering utility across 90 SAEs, three LLMs, five architectures, and six sparsity levels (https://openreview.net/pdf?id=5KY99GFqZD); and Canby et al. already frame causal probing as a completeness--selectivity tradeoff tied to behavior (https://aclanthology.org/2025.ijcnlp-long.47/).
    impact — without an explicit contrast and a result those papers do not already supply, the headline reads as a smaller replication rather than an ICLR-level contribution.
    fix — rewrite the paper around a genuinely distinct estimand: the jointly preregistered potency--signed-sham-specificity--collateral-safety frontier; add a comparison table against SAEBench, AxBench, Makelov et al., Canby et al., the 90-SAE utility study, and side-effect prediction; then validate that joint endpoint on standard released SAEs and baselines.
  - [critical] PAPER.md:372-408 — the only prospectively interpretable benchmark evidence comes from two generated panels sharing one generator, while the natural endpoint is explicitly ineligible.
    reasoning — lines 405-406 report natural eligibility 0.654 below 0.80; lines 742-747 concede three model units, two from Pythia, shared controlled generation, and no confirmatory natural endpoint.
    impact — the paper cannot support a broad claim about SAE or representation control in natural model behavior; its central result is currently a controlled-template result.
    fix — run one separately frozen naturalistic confirmation on at least one standard task with adequate prospective effect support, untouched templates or instances, model-level replication across at least three genuinely distinct families, and the unchanged joint endpoint. If this is infeasible, narrow the title, abstract, and venue claim to a controlled case study.
  - [critical] PAPER.md:365-403 — the method panel is not anchored to the community's standard released SAE and steering baselines.
    reasoning — the manuscript reports imported K1/K2 variants, custom projections, erasure, PCA/delta, and a rank-limited behavior-gradient oracle, but it does not evaluate the released SAEBench SAE suite, AxBench's DiffMean/ReFT-r1/LoRA baselines, or a validated supervised dictionary skyline. Makelov et al. show that supervised task dictionaries can contextualize SAE control (https://openreview.net/forum?id=1Njl73JKjB), while newer supervised feature-selection work reports SAEs near LoRA on AxBench (https://openreview.net/forum?id=7wZSpvtCbb).
    impact — a reviewer cannot tell whether the negative is about K2 and the custom panel, about unsupervised objective choice, or about the evaluated activation sites.
    fix — use released SAEs and capacity-/norm-matched standard baselines; include a validated supervised skyline and branch-permutation-invariant scoring. Interpret failure by the preregistered oracle/unsupervised decision tree rather than aggregating unlike methods.
  - [high] PAPER.md:378-398 — “behavioral control” is measured through local log-odds recovery and collateral next-token KL, without eligible downstream generation or task performance.
    reasoning — the naturalistic endpoint is descriptive, and the paper contains no passed measure of generated-output quality, target task success, fluency, refusal/safety behavior, or multi-token behavioral persistence.
    impact — the causal-modularity and practical-control framing overreaches what a local next-token intervention establishes.
    fix — add necessity and sufficiency interventions on a natural behavioral task, measure multi-token task success and unrelated-behavior damage, and report norm-matched recovery--damage curves. Retain local log-odds/KL as mechanistic intermediates rather than the sole behavior endpoint.
  - [high] PAPER.md:386-398 — association uncertainty is based on only nine model--layer clusters, with layers nested inside three model units.
    reasoning — lines 739-754 acknowledge that layers are not independent model replications and that the bootstrap does not establish generalization beyond frozen models and choices. Correlation intervals excluding zero across these clusters therefore do not establish population-level proxy predictiveness across models.
    impact — proxy “predicts” language in the abstract can be read as model-general evidence when the independent model count is three.
    fix — either make every proxy association explicitly descriptive for the frozen panel or obtain enough independent model/SAE units for model-level hierarchical inference, with model-family leave-one-out validation and method-fixed effects.
  - [high] PAPER.md:26-28 — the synthetic gate validates metric formulas but not the complete model-intervention pipeline on a known causal mechanism.
    reasoning — SynthSAEBench already supplies large-scale correlated, hierarchical, superposed ground truth and documents a reconstruction/latent-quality gap (https://arxiv.org/abs/2602.14687); the manuscript's analytic synthetic control does not show that model extraction, component construction, patching, and downstream measurement recover a known in-model causal feature.
    impact — a clean failure on real activations remains confounded with evaluator weakness, while the synthetic contribution is too small to be independently novel.
    fix — add an end-to-end positive control using either a known toy transformer mechanism or a validated circuit task such as IOI, and require the full pipeline plus supervised skyline to pass before interpreting real-model failure.

REVISIONS       (should fix; not blocking)
  - [high] PAPER.md:127-415 — eleven chronological subsections bury the prospective benchmark in Section 4.11.
    reasoning — the most decision-relevant study appears after ten historical attempts, several of which are measurement failures rather than evidence for the headline.
    impact — the manuscript reads as a project log and architecture postmortem rather than a focused benchmark paper.
    fix — lead with v2 methods/results, move K2 motivation to one case-study section, and move Attempts 1--14 plus numerical/parser history to an appendix or companion audit.
  - [high] PAPER.md:427-428 — the positive-results list says “recovery and CKA predict behavioral potency,” while v2 reports geometric stability negatively associated with recovery and specificity at lines 389-391.
    reasoning — v1 and v2 use different estimator/aggregation regimes, but the bullet does not mark the first result as exploratory or explain the reversal.
    impact — the reader sees an apparent contradiction in a headline proxy claim.
    fix — replace the bullet with a versioned statement: v1 found a positive exploratory CKA association; v2's prospectively corrected learned-method association was negative. Explain which estimator change prevents direct pooling.
  - [medium] PAPER.md:452-456 — the integrated conclusion returns to one Pythia site after v2 introduced a broader, though still small, model panel.
    reasoning — this is defensibly conservative but leaves unclear whether the conclusion summarizes K2 only or the proxy benchmark.
    impact — the scope of the central claim is ambiguous.
    fix — state two nested conclusions: a Pythia K2 case-study conclusion and a controlled nine-site benchmark conclusion.
  - [high] PAPER.md:41-60 — the introduction has no related-work section, contribution list, or explicit novelty statement.
    reasoning — no citation or bibliography appears despite several directly adjacent 2025--2026 benchmarks.
    impact — reviewers must infer novelty and will likely infer overlap.
    fix — add a current related-work section and a three-item contribution list that distinguishes joint safety, prospective conjunction, and falsification/measurement design from prior SAE utility benchmarks.
  - [medium] PAPER.md:737-762 — limitations name external-validity problems but do not translate them into claim-language constraints throughout the abstract and conclusion.
    reasoning — “proxy metrics therefore tracked” and “across depth” are stated declaratively before the three-model limitation appears much later.
    impact — caveats look appended rather than constitutive of the estimand.
    fix — qualify primary proxy associations as frozen-panel results at first mention and reserve generalized language for confirmed results.
  - [medium] PAPER.md:690-735 — future work devotes substantial space to a closed relational matching program that is not the shortest route to testing the headline.
    reasoning — the publication blocker is external validation of proxy-to-safe-control, not another edge estimand.
    impact — this diffuses the paper's relevance and suggests unresolved research direction.
    fix — demote relational-object work to a separate project; prioritize standard-SAE replication, natural behavior, a supervised skyline, and an end-to-end control.
  - [medium] PAPER.md:383-403 — the manuscript shows isolated point estimates but not full matched-norm Pareto fronts or method uncertainty in the main text.
    reasoning — potency and collateral depend on intervention magnitude, so a single operating point can reverse rankings.
    impact — the claimed potency--precision tradeoff is less actionable for selecting methods.
    fix — make norm-matched recovery--specificity--damage frontiers the primary figures, with bootstrap bands and model-family panels; report dominance rather than only threshold passage.

NITS            (optional, cap at 5)
  - PAPER.md:22 — “nine model--layer units, two model families” should immediately say that two units are Pythia-family models and all are small.
  - PAPER.md:411-413 — figures need publication captions that define axes, units, thresholds, and uncertainty.
  - PAPER.md:795-804 — a path inventory is not a reproducibility package; add a one-command public benchmark interface and environment/data license instructions.
  - PAPER.md:826-827 — the central conclusion should include “among evaluated methods and controlled panels” to avoid universal reading.
  - PAPER.md:5 — “complete project-level synthesis” is accurate internally but is not a compelling main-track paper identity.

CHECKS RUN
  - `python -m py_compile scripts/analyze_proxy_control_benchmark_v2.py scripts/verify_paper_claims.py tests/test_analyze_proxy_control_benchmark_v2.py` → pass.
  - `pytest -q tests/test_analyze_proxy_control_benchmark_v2.py` → 4 passed.
  - `python scripts/verify_paper_claims.py` → PASS; 58 claims and 237 evidence bindings.
  - SHA-256 verification of v1 result, v2 aggregate/terminal, synthetic gate, freeze, claim review, Qwen recovery, and cached-analysis terminal → all matched frozen values.
  - `tmux list-sessions` and `nvidia-smi --query-compute-apps=...` → no experiment session and no GPU process observed.
  - Primary-source literature check → direct overlap found in SAEBench, AxBench, Makelov et al., Canby et al., the 90-SAE interpretability/utility study, SynthSAEBench, and 2026 SAE side-effect prediction.

CONTRACT COVERAGE
  - Preserve v1/v2 and prohibit current-program training → met — frozen hashes match and `reports/architecture_program_closure_v2.json` denies all listed training paths.
  - Produce deterministic cached v2 companion with zero forwards → met — analysis terminal hash matches and `new_model_forwards` is zero.
  - Integrate v2 conjunctively and preserve positive-but-unsafe signals → met — PAPER.md:363-409.
  - Bind new quantitative claims → met — claim verifier passes.
  - Draft unopened naturalistic successor → met — `prereg/proxy_control_naturalistic_confirmation_v1_draft.md` is design-only.
  - Identify venue-level impact blockers → met — blockers above.
  - Demonstrate ICLR-level novelty and external validity → unmet — no literature distinction, standard-SAE benchmark, or eligible natural confirmation exists.

UNKNOWNS
  - Whether the code and frozen artifacts can be released with all model, dataset, and template licenses.
  - Whether the paper must target ICLR main track specifically or could be repositioned as a benchmark/resource paper elsewhere.
  - Whether compute permits standard released-SAE evaluation across larger, genuinely independent model families.
