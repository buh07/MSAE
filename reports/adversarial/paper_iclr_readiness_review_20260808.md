VERDICT: BLOCK
ONE-LINE: The central lesson is established, while the evidence is too architecture-local and incomplete for ICLR.

BLOCKERS        (must fix before proceeding; empty if none)
  - [critical] PAPER.md:19-33,43-62,676-686 — the manuscript presents “encoding is not separability” as its scientific contribution but contains no related-work section, citations, or references.
    reasoning — Hewitt and Liang already made selectivity central to probe interpretation (https://aclanthology.org/D19-1275/); Elazar et al. explicitly separated encoded information from behavioral use (https://aclanthology.org/2021.tacl-1.10/); Canby et al. evaluate causal probes by completeness and selectivity (https://aclanthology.org/2025.ijcnlp-long.47/); and Makelov et al. evaluate SAE disentanglement and control against supervised dictionaries (https://openreview.net/forum?id=1Njl73JKjB). The manuscript neither distinguishes its contribution from these results nor identifies a new theorem, benchmark, estimator, or broadly replicated empirical phenomenon.
    impact — the headline contribution currently reads as a careful instance of an established warning, not a novel ICLR-level advance.
    fix — manuscript-only: add a real related-work and contribution section that makes a falsifiable novelty claim against these papers. New evidence: if the novelty is meant to be “stable SAE geometry without selective function,” demonstrate it as a benchmarked phenomenon across standard SAEs, supervised dictionaries, and models rather than only this project-specific K2 system.
  - [critical] PAPER.md:66-81,168-182,619-626 — the decisive learned result comes from one small model/site and a deliberately asymmetric two-branch objective with no semantic supervision.
    reasoning — the content branch has four times the dictionary width and three times the active budget, while neither branch receives position/content labels or invariance losses. A reproducibly mixed solution is therefore predicted by the design itself. The no-incoherence control tests one regularizer, but does not separate “this underconstrained, unequal-capacity trainer mixes” from “the activation is not separable.”
    impact — the evidence cannot support a general negative result about SAEs, transformer organization, or even equal-capacity position/content decompositions; that leaves the paper's ICLR significance too narrow.
    fix — new evidence: before submission, evaluate at minimum an equal-capacity K2, a matched standard SAE/K1 decomposition, a supervised or oracle linear dictionary, and multiple layers/models with the same frozen selectivity tests. If those experiments are not scientifically authorized, narrow the claim and target a venue suited to a single-architecture negative case study.
  - [high] PAPER.md:101-111,242-256,294-318,337-352,676-686 — “causal modularity” is stronger than the reported endpoint.
    reasoning — the manuscript defines specificity as whether an intervention changes an assigned representation more than controls; it does not establish that the component mediates downstream model behavior. AlterRep (https://aclanthology.org/2021.conll-1.15/) and amnesic probing tie interventions to model predictions or behavior, while LEACE evaluates concept erasure and behavioral effects (https://proceedings.neurips.cc/paper_files/paper/2023/hash/d066d21c619d0a78c5b557fa3291a8f4-Abstract-Conference.html). The present evidence supports failure of intervention-specific linear localization, not absence of a causal module.
    impact — this is a claim-validity problem at the title/abstract/conclusion level, not merely terminology.
    fix — manuscript-only: replace “causal modularity” with “selective, intervention-responsive linear organization” wherever no downstream behavior was measured. New evidence: alternatively add matched downstream logit/loss/task mediation tests with completeness, selectivity, and collateral-damage controls.
  - [high] PAPER.md:129-318,617-633 — the evidential narrative is predominantly exploratory and has no fresh replication of the central negative phenomenon.
    reasoning — early probes are explicitly exploratory, several attempts are technical-invalid, Attempts 12–14 are exploratory, and v3/v4 produce no representation result. The one eligible K2 measurement establishes a local conjunction failure, but the progressive reuse of opened sources and hypothesis refinement precludes treating the full sequence as independent confirmation.
    impact — a negative paper needs especially strong power, scope, and replication to distinguish a true absence of selective organization from architecture, layer, corpus, or intervention mismatch.
    fix — new evidence: preregister one fresh confirmatory replication of the final, narrowed K2/selectivity claim across at least one additional model and activation site; report effect sizes and uncertainty for all primary recovery, leakage, and control margins. Do not reopen or alter v4.

REVISIONS       (should fix; not blocking)
  - [high] PAPER.md:83-127,129-318 — methods are distributed through a chronological attempt log rather than a reproducible paper specification.
    reasoning — a reviewer cannot recover the exact datasets/splits, activation extraction, ridge/probe fitting, bootstrap estimands, intervention construction, CKA variant, thresholds, or primary decision rule from the manuscript alone.
    impact — the claim ledger verifies artifact lineage, but it does not replace a self-contained Methods section.
    fix — manuscript-only: reorganize around Methods, Main Results, Robustness, and Measurement Failures; move attempt-by-attempt lifecycle history to an appendix and add equations, dataset statistics, uncertainty intervals, and a single primary-result table.
  - [high] PAPER.md:320-382 — the mechanism discussion is plausible but mostly post hoc.
    reasoning — capacity asymmetry, statistical coupling, integrated activations, and wrong representational object are offered as explanations without factorial ablations that distinguish them.
    impact — the paper explains why failure is unsurprising but does not identify which cause matters, reducing scientific insight.
    fix — new evidence: run only prospectively justified discriminating ablations (equal capacity; supervised pair losses; layer sweep) or label these paragraphs explicitly as hypotheses rather than explanations.
  - [medium] PAPER.md:529-566,631-633,680-683 — v4 occupies substantial main-text space despite producing no representation estimate.
    reasoning — its support-versus-overlap lesson is useful technical provenance, but it cannot strengthen the core representation claim.
    impact — main-text emphasis dilutes the already narrow empirical contribution and makes the manuscript resemble a project audit.
    fix — manuscript-only: retain the accurate v4 summary and warning disclosure, but move lifecycle detail and the full matcher table to a measurement appendix; keep one concise main-text lesson.
  - [medium] PAPER.md:17-41 — the abstract foregrounds protocol chronology rather than a crisp contribution and scope.
    reasoning — multiple stops, repairs, and future-work conditions consume the abstract without naming the eligible study's datasets, model scope, principal effect sizes, or the precise novelty over prior causal-probing/SAE evaluation work.
    impact — ICLR reviewers will struggle to identify the paper's new result before reaching the body.
    fix — manuscript-only: rewrite the abstract around one scoped question, one method contribution if defensible, the main eligible effect/control contrast, and one calibrated conclusion; move v3/v4 lifecycle outcomes out of the abstract.

NITS            (optional, cap at 5)
  - PAPER.md:103 — render the task variable as mathematics rather than literal “(t)”.
  - PAPER.md:441-442 — wrap the long sentence and avoid emphasizing parser edge cases in the main narrative.
  - PAPER.md:538 — shorten the table header; it dominates the narrow Markdown layout.
  - PAPER.md:637-665 — provide an archival code/data release entry rather than only repository-relative artifact paths.

CHECKS RUN
  - `python scripts/verify_paper_claims.py` → PASS: 41 claims and 168 immutable evidence bindings.
  - `grep -nE 'References|Related [Ww]ork|doi|arXiv|OpenReview|ACL|NeurIPS|ICLR' PAPER.md` → no literature positioning or bibliography found.
  - `wc -l -w PAPER.md` → 686 lines and 5,538 words.
  - v4 SHA-256 audit → prepared `0002353…`, result `95fd7a6…`, authorization `d4c914b…`, and closure `a23d0fe…` remain unchanged.
  - primary-literature scope check → the central encoding/use and selectivity distinction substantially overlaps the seven cited probing, concept-erasure, and SAE-evaluation papers.

CONTRACT COVERAGE
  - Preserve v4 unchanged → met — hashes match the signed lineage and no v4 process/tmux session is running.
  - Report v4 support, balance/overlap stop, zero simulations, and no representation/training → met — PAPER.md:529-566 and claims C037–C041.
  - Maintain calibrated representation claims → partial — local limitations are explicit at PAPER.md:64-81 and 617-633, but “causal modularity” overstates the measured endpoint.
  - Establish novelty and impact for ICLR → unmet — no related work, broad benchmark, or contribution distinct from prior probing/SAE evaluation literature.
  - Supply ICLR-level empirical sufficiency → unmet — one model/site, underconstrained unequal-capacity K2, and no fresh final replication.
  - Present a self-contained conference paper → unmet — artifact discipline is strong, but methods, literature positioning, uncertainty synthesis, and conventional paper organization are incomplete.

UNKNOWNS
  - Whether unreported downstream-behavior endpoints exist in the artifacts; PAPER.md defines and argues from representation-change specificity instead.
  - Whether the current code and data can be released in an anonymous, archival form acceptable for review.
  - The exact outcome under a future ICLR reviewer pool; this verdict assesses the current manuscript against the public literature through August 2026.
  - The recorder has no explicit-document scope; this paper review is recorded as a fallback claim review over the worktree.
