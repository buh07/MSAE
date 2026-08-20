# PLAN — Consolidate and expand the MSAE experimental roadmap

> Written by `/plan`. Attacked by `/adversarial PLAN.md` before implementation.
> Keep this live: check off milestones, record deviations. Delete/replace per task.

## Goal
Replace `TODO.md` and `TODO_pcc.md` with one evidence-grounded `TODO.md` that carries the MSAE project from its current K=2/PCC checkpoint through a confirmatory, falsifiable study of multiple separable information families and a paper-ready artifact.

## Non-goals
- Do not run new training or evaluation jobs in this task.
- Do not rewrite the historical preregistrations or retroactively change frozen gate outcomes.
- Do not claim that probe decodability, orthogonality, or a low incoherence penalty alone proves a meaningful component.
- Do not commit to K=3, a PCC/shared branch, or a broad-position branch before no-new-training evidence selects among them.
- Do not expand Paper 2/3 into immediate execution work before the next paper gate is complete.

## Constraints
- From mode instructions: direct file operations are allowed; workflow checks are optional, but the user explicitly requires `/adversarial` review.
- From task: merge all actionable content from both TODO files, broaden the original absolute-position framing, and cover experiments and work through paper writing.
- Preserve the distinction among the frozen A1 no-go, diagnostic A1b result, amended A1c/A1r path, B-light result, and later small contrast no-go.
- Treat actual run artifacts as stronger status evidence than stale checkboxes or prose summaries.
- The current workspace contains uncommitted/ignored result artifacts and stale absolute paths; the roadmap must include an artifact-hygiene milestone rather than silently treating the repository as publication-ready.
- `TODO_pcc.md` is untracked and has no Git history. Preserve a byte-identical archived source copy and checksum before retiring the active filename.

Historical precedence for this consolidation is:
1. Frozen preregistration and decision artifacts govern what was decided under each gate; later amendments coexist with rather than rewrite earlier decisions.
2. Within a run, evidence precedence depends on the claim:
   - the manifest defines the intended launch matrix, not completion;
   - a finalized structured summary or aggregate table governs finalized metrics;
   - completion requires a finalized summary plus a terminal completion artifact when both are expected;
   - a status snapshot records state only at its timestamp and cannot override a later final summary;
   - logs are diagnostic fallback evidence and never override a consistent finalized structured artifact;
   - launcher-only, empty-directory, and logs-only attempts remain explicitly incomplete unless a finalized output proves otherwise.
   Conflicts are recorded rather than silently collapsed.
3. Packaged report bundles summarize those primary artifacts when their source run is named.
4. `ANALYSIS.md`, `RESULTS.md`, and status sections in the TODOs are date-bounded secondary summaries; conflicts are recorded, not silently resolved in favor of newer prose.
5. Forward-looking TODO language governs future strategy only and is not evidence that work ran.

## Approach
Organize the unified roadmap as a gated, minimal-to-complex program. First freeze the historical evidence and define operational criteria for an “information component.” Next build a held-out separability atlas over candidate information families using raw activations and existing K=2 checkpoints. Use the atlas and leakage/counterfactual baselines to select the smallest justified architecture (revised K=2, K=3 absolute/structural/content, or private/shared). Only then run staged training budgets, mandatory baselines, confirmatory evaluations, and paper assembly. Separate discovery data/tasks from locked confirmatory data/tasks to prevent using the same probes both to invent and validate the decomposition.

**Alternative considered & rejected:** Merge the two files mechanically and retain the original Paper 1/2/3 checklist. Rejected because it would preserve duplicate/stale actions, mix frozen and amended PCC decisions, and assume an architecture before resolving whether the current joint signal is shared information or under-modeled positional structure.

**Simpler option?** Keeping only a short “next ten actions” list would be simpler, but it would not meet the request for a complete experimental and paper-writing plan or provide defensible go/no-go gates.

**Relevant ADRs:** none (`bin/design list --path experiments/wip/MSAE` returned no matching design entries).

## Milestones

Each milestone is an independently verifiable vertical slice that fits one context window.
- [x] M1: Freeze the two source TODOs and inventory their sections/checklists — acceptance: byte-identical source snapshots, SHA-256 checksums, and a disposition table give every actionable checklist item (including nested items) a stable source ID and resolved destination/evidence.
- [x] M2: Reconcile the two TODOs and the full indexed result/decision history into a single status section — acceptance: every run family in `RESULTS.md` (including partial, launcher-only, smoke/resume, compatibility, superseded, and empty/log-only attempts) and every PCC decision root has an explicit disposition and evidence class.
- [x] M3: Define the expanded scientific question, candidate information families, separability criteria, discovery/confirmation split, and minimal architecture decision tree — acceptance: each candidate claim has a null outcome and a measurable gate.
- [x] M4: Build an ordered experiment roadmap from no-new-training audits through staged training and paper evaluation — acceptance: every stage names inputs, outputs, required baselines, gate, and stop condition.
- [x] M5: Add reproducibility, analysis, paper-writing, claim-language, and artifact-delivery requirements — acceptance: the roadmap ends in a concrete paper freeze rather than only model training.
- [x] M6: Review the draft unified `TODO.md` adversarially against both preserved sources and the disposition table, revise all actionable findings, then retire the active `TODO_pcc.md` filename and run final path/link checks — acceptance: the archived source remains checksum-verifiable, every disposition is resolved, one active `TODO*.md` remains, and the final adversarial verdict is SHIP.

## Definition of done

These are the acceptance criteria that `/adversarial` and verification grade against.
- [ ] `TODO.md` is the sole active TODO document and explicitly supersedes the two previous execution plans without altering frozen historical results; a checksum-verifiable archive preserves the untracked PCC source.
- [ ] The current state distinguishes completed, superseded, exploratory, and unrun work, including the small Stage-B contrast audit.
- [ ] “Separable information” has an operational definition that requires held-out selectivity, depletion/leakage checks, stability, reconstruction accounting, and causal or counterfactual evidence—not probe accuracy alone.
- [ ] Candidate families include absolute position, relative/structural position, lexical/semantic content, syntax/morphology, domain/format/frequency, computational provenance, shared/interactions, and dense residual structure, while treating them as hypotheses rather than an ontology.
- [ ] Discovery and confirmation use disjoint tasks/examples/splits, with predeclared family-level gates and multiple-comparison control.
- [ ] The roadmap selects the smallest justified K/branch design before new long training and includes raw/projection/scrubbing, K=1 SAE, no-incoherence K-branch, capacity-matched, and relevant dense/PCA controls.
- [ ] Training proceeds through smoke, short-budget, medium-budget, and confirmatory budgets with explicit promotion and stop rules; 8B-scale work is conditional rather than automatic.
- [ ] The final phase includes the four original functional probes, seed stability, causal interventions, a mechanistic case study, statistical analysis, limitations, claims-to-evidence mapping, artifact audit, and paper freeze.
- [ ] Paper 2/3 ideas remain visible as gated follow-ons but cannot start before the next-paper gate.
- [ ] All actionable `/adversarial` findings are incorporated or explicitly resolved.

## Verification plan
- Source preservation: checksum `TODO.md` and `TODO_pcc.md`, copy them byte-for-byte to deterministic names `docs/archive/todo_main_premerge_20260731.md` and `docs/archive/pcc_plan_premerge_20260731.md`, record hashes in `docs/archive/todo_merge_disposition_20260731.md`, and verify each archived hash before any retirement.
- Disposition audit: assign a stable source ID to every actionable top-level and nested checklist item in both snapshots. For each ID, record exactly one of: `carried`/`merged` with destination `TODO.md` anchor(s); `superseded` with concrete decision/result evidence; or `intentionally dropped` only when demonstrably non-actionable or duplicate, with rationale and adversarial-review approval. Assert that every source ID has exactly one resolved disposition and that source/checklist totals match the snapshots.
- Structure: inspect headings and checkbox groups; after retirement confirm `find . -maxdepth 1 -name 'TODO*.md'` returns only `TODO.md`.
- Historical consistency: compare the unified status against the complete `RESULTS.md` experiment index, `ANALYSIS.md` evidence classes, all pre-K2 preregistration/report artifacts, K=2 validation/wave decisions, and every PCC decision root through the small Stage-B contrast audit.
- Cross-references: require existing references to resolve; mark future deliverable paths explicitly as planned rather than treating them as broken links.
- Plan quality: run `/adversarial TODO.md` while both preserved source snapshots and the disposition table are available; revise until SHIP, then retire the active source filename and repeat structural/path checks.
- Diff review: inspect `git diff -- TODO.md` for tracked changes and compare the final file directly against both archived source snapshots through the disposition table; do not rely on Git diff for the untracked PCC source.

## Risks & one-way doors ⚠️
- Taxonomy lock-in: treating candidate probe families as ground-truth components would bias architecture selection. Mitigation: hypothesis language, discovery/confirmation separation, null outcomes, and minimal-K selection.
- Circular validation: using the same labels to build and validate a subspace would inflate separation evidence. Mitigation: disjoint task variants/datasets/templates and frozen confirmatory evaluation.
- Scope explosion: an unconstrained “separate everything” program could become unfinishable. Mitigation: staged family screen, minimal viable atlas, capacity-neutral model comparison, and explicit stop conditions.
- Historical revisionism: merging PCC plans could blur the original no-go. Mitigation: immutable chronology and separate frozen/amended decisions.
- Compute escalation: 8B-token matrices are expensive. Mitigation: promote only variants that pass 25M/100M/1B gates; keep a compute ledger.
- Retiring the untracked `TODO_pcc.md` filename is a one-way door unless its bytes are preserved first. Mitigation: archive, checksum, disposition audit, adversarial comparison, and only then remove the active source.

## Open questions
- The final paper title and whether it is framed as “generalized separable information demixing” or a narrower “positional-family demixing” paper must be chosen after the atlas gate, not now.
- Exact confirmatory datasets and effect-size thresholds must be preregistered after pilot variance estimates but before confirmatory runs.
- Whether a fresh-from-zero corrected-loader K=2 replication is required should be decided at the artifact/readiness gate; the current 1B run resumed earlier checkpoints.

## Deviations log (fill during implementation)
- 2026-07-31: No scope deviations. Both sources were archived and audited; the unified TODO passed iterative independent adversarial review after its data firewall, inference, branch, comparator, synthetic, intervention, and paper gates were tightened. `TODO_pcc.md` was retired only after the final `SHIP` verdict.
