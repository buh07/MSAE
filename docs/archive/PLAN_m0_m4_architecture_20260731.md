# PLAN — Execute MSAE M0–M4 and make the architecture decision

> Written by `/plan` for the 2026-07-31 execution request. This replaces the completed TODO-consolidation plan, archived at `docs/archive/PLAN_todo_consolidation_20260731.md`. Do not begin implementation until `/adversarial PLAN.md` returns SHIP.

## Goal
Complete the eight requested next steps in their leakage-safe order: reconstruct and classify the historical 1B K=2 state; reinterpret PCC; define the information-family task/shortcut inventory; materialize and freeze discovery, calibration, architecture-confirmation, and blind-final partitions; freeze the atlas preregistration; validate the metric code synthetically; run the Pythia-160M L3/L4 raw atlas and the L3 existing-K=2 audit; and sign a G1/G2/G3 decision about whether any new model training is warranted.

## Non-goals
- Do not run new MSAE/SAE training in this task. Step 8 is a decision, not permission to silently launch M7.
- Do not open or score the blind final-test partition; this task stops after architecture-confirmation evidence.
- Do not rewrite frozen A1/A1b/A1c/A1r/B-light/contrast decisions or relabel resumed 1B checkpoints as fresh confirmatory seeds.
- Do not treat task-derived subspaces as an unsupervised ontology or claim causal separation from probe scores.
- Do not activate full dense-residual/dictionary-identifiability/theory work; only the mandatory minimal synthetic metric smoke is in scope.
- Do not promise paper-final evidence. The result is the preregistered architecture-selection stage, not M8.

## Constraints and grounded evidence
- `TODO.md` §5 requires four disjoint data roles, M2 construction/QA/hashing before representation scoring, M3/M4 use of architecture-confirmation only, and a single later M8 final opening.
- `TODO.md` §3.5 and G1/G2 fix metric eligibility, BH families, effect-size bounds, family gates, equivalence/superiority regions, and equivocal outcomes. The implementation must encode those rules rather than invent new post-result thresholds.
- Historical outputs occupy about 98 GB; do not duplicate checkpoints. Hash final checkpoints in place and keep tracked provenance tables small.
- The current authoritative run says `git_hash=1cef38e-dirty`. `git diff` shows the dirty source adds balanced four-source streaming, optional pretokenization, data monitoring, and cache/TMP routing. The two source files have mtimes 2026-06-01 13:15, preceding the 13:21 launch; preserve their exact bytes and diff before editing.
- The completed fastdata directory has summaries, metrics, logs, and checkpoints but no run manifest. Summary paths point at obsolete `/jumbo/lisp/f004ndc/MSAE`; the current root is `/jumbo/lisp/f004ndc/experiments/wip/MSAE`.
- Deterministic code queries found `load_checkpoint` at `scripts/train_msae_k2.py:669` and all `save_checkpoint` references in that file. The design ledger query for MSAE atlas/provenance returned no entries. The user has fixed the scientific scope; low-risk local implementation choices below are explicit assumptions.
- Eight RTX 6000 Ada GPUs are currently available, but GPU availability can change. Runs must be resumable, config-driven, and leave terminal artifacts even if interrupted.
- The repo has no project lockfile and the default interpreter does not currently expose all atlas dependencies. Create an isolated `.venv-atlas`, pin the minimal atlas requirements, model revision, dataset revisions/file hashes, Python/CUDA/library versions, and run availability smokes; do not mutate or pretend to reconstruct the historical environment.

## Design-bank clarification and explicit assumptions
- Design query: `design query "What is the canonical experiment design for the MSAE separable-information atlas, data partitions, and checkpoint provenance?" --path experiments/wip/MSAE` → no entries.
- Assumption A1: this task implements an **atlas-v1 architecture-selection study**, not the later blind paper-final evaluation.
- Assumption A2 (superseded by the atlas-v1 freeze): use Pythia-160M L3 as the fixed primary site and L4 as descriptive only. No data-selected fallback is active.
- Assumption A3: use source-disjoint English UD corpora for positional/structural/lexical/syntax tasks and coarse English NER corpora for the semantic sentinel:
  - discovery: UD English EWT train + FewNERD train;
  - calibration: UD English GUM train + WNUT-17 validation;
  - architecture-confirmation: UD English LinES test + WikiNeural `val_en`;
  - blind final: UD English PUD test + WikiNeural `test_en`.
  Dataset unavailability may be resolved only by a pre-score amendment naming an equivalent source; no replacement after confirmation scoring.
- Assumption A4: cap each source deterministically by stable base-sentence ID after hashing/shuffling with seed 20260731: discovery 4,000 UD/8,000 NER sentences, calibration 1,500/1,500, architecture-confirmation 1,500/1,500, final all available up to 2,000/2,000. Split architecture-confirmation by base-sentence group into `C1` (G1 topology; 50%) and `C2` (G2 K=2/simple audit; 50%); no sentence or offset variant crosses C1/C2. Exact realized counts/exclusions are frozen.
- Assumption A5: primary tasks are absolute position bucket; normalized sentence-position quartile; signed head-distance bucket; dependency-depth bucket; boundary state; top-frequency token identity; top-frequency lemma identity; and coarse NER. UPOS, coarse dependency relation, morphology Number, capitalization, word length, frequency bin, and source type are sentinels/shortcut controls.
- Assumption A6: primary linear probes are standardized ridge least-squares classifiers so grouped bootstrap refits are computationally tractable and deterministic. The scaler is fit on discovery only; ridge alpha is selected from a fixed calibration grid, then frozen. Discovery and calibration are never scored as confirmation. Final probe/subspace weights are refit on all discovery examples at the frozen alpha and evaluated without fitting on C1/C2. Task subspaces use SVD of discovery weights at preregistered ranks 8 and 16; rank 32 is a boundary diagnostic only and cannot be promoted. Token/lemma vocabularies are discovery-only and NER/UD label maps are frozen common coarse maps.
- Assumption A7: controlled counterfactual pools cover position shifts, lexical/entity substitutions, structural alternations, and punctuation/format shifts. Partition-specific lexicons/templates are disjoint. Automatic QA plus independent adversarial sample review is the validity check; failures are excluded before hashing and counts are reported.
- Assumption A8: final-test blindness is procedural and enforced by a separate private manifest plus an absent unlock token; public files expose source/version/count/hash but no scores. The task must not invoke a final evaluation mode.
- Assumption A9: contexts use `add_special_tokens=False`, fixed maximum length 128, explicit right padding, and no BOS/EOS/pad labels. Each base sentence is rendered at frozen offsets in `{0,16,32,48}` using partition-disjoint neutral prefix tokens; all eligible subwords receive the true model-token absolute-index label, while word-level labels use only the first subword. Tail-truncated words, continuation subwords for word tasks, and invalid alignments are excluded and counted. Offset, context length, prefix identity, word index, and continuation status are explicit controls.
- Assumption A10: L3 alone drives G1. L4 activations are always extracted to satisfy the requested L3/L4 audit, but L4 scores are descriptive robustness and cannot rescue a failed L3 gate. The frozen preregistration disables the originally contemplated fallback trigger; any future fallback requires a new prescore plan and independent confirmation.

## Approach
Build one small, config-driven atlas package rather than extending the older stage-specific scripts again. Shared modules will handle data materialization, hashing, task labels, activation extraction, probe fitting, normalized metrics, subspace geometry, checkpoint transforms, counterfactual scoring, BH correction, and decision rendering. Raw G1 and K=2/simple G2 share one frozen parent protocol and task definitions but **not examples**: raw G1 may score only C1, K=2/simple G2 only C2, and no base sentence, content hash, document group, or offset variant may cross that boundary. The final partition remains inaccessible. Every run writes a resolved config, code/data/environment hashes, seed, hardware, metrics, completion marker, and immutable report under a timestamped ignored run root; promoted compact tables/reports are copied to `results/atlas/` and `reports/`.

Probe evaluation is source-transfer rather than confirmation fitting: discovery supplies all fit rows, calibration selects alpha/baseline/rank decisions, C1 supplies G1 estimates, and C2 supplies G2 estimates. Grouped resampling draws base sentences at the outer level, preserves all offset variants together, refits discovery scalers/probes/subspaces, and reevaluates the fixed C1/C2 groups. A feasibility pilot locks 500 refit bootstraps and 9,999 group-level sign/randomization draws if Monte Carlo standard error is `<=0.01`; otherwise it increases bootstraps before scoring or declares the boundary underpowered. Fits are cached by `(resample, layer, representation, task)` and parallelized. Any interval within `0.01` of a decision boundary is equivocal rather than promoted.

**Alternative considered:** reuse `pcc_stage_a1*.py` and `raw_activation_separability_pilot.py` separately. Rejected because they use incompatible task sets, split semantics, pooling, and gate revisions; combining their outputs would not implement the four-way firewall or a common G1/G2 metric family.

**Simpler option considered:** write only the requested memos/manifests and defer execution. Rejected because the user explicitly asked to run the synthetic test, raw atlas, and K=2 audit and then decide.

## Milestones

Mapping to the user's requested sequence and roadmap: Plan M1 = requested Step 1 / TODO M0; M2 = Step 2 / TODO M1; M3 = Steps 3–4 / TODO M2; M4 = Steps 5–6 / TODO M2b; M5–M6 = Step 7 / TODO M3–M4; M7 = Step 8 / TODO G1–G3; M8 is the requested adversarial/verification wrapper.

### M1 — Historical provenance and path repair
- [ ] Snapshot SHA-256 hashes and byte-identical copies of the two dirty training sources before editing; save the scoped binary patch from `git diff --binary 1cef38e -- scripts/train_msae_k2.py scripts/run_msae_k2_worker.py` as `reports/provenance/1cef38e_dirty_training.patch` and record field-level reconstruction confidence.
- [ ] Inspect checkpoint-embedded args/RNG/step/token metadata and previous-run resume candidates to reconstruct each fastdata job's source checkpoint and limitations without loading model tensors unnecessarily.
- [ ] Restore `pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/run_manifest.tsv`, preserving original IDs/status/times and explicitly labeling it reconstructed.
- [ ] Create `experiments/registry.csv`, `reports/artifact_readiness.md`, `reports/k2_postwave_comparison.md`, final-checkpoint hashes, environment/hardware records, and a path-map.
- [ ] Repair active scripts and live Markdown links to use repository-relative/script-relative paths; do not mutate frozen archived sources or historical JSON summaries. Add a path-resolution checker.

Acceptance: manifest has four terminal rows matching summaries/logs; source/checkpoint hashes resolve; every historical run family in TODO §1 has an evidence class; active scripts contain no obsolete MSAE root; current 1B checkpoints are classified `development_existing_checkpoint`, not fresh confirmation.

### M2 — PCC reinterpretation
- [ ] Generate `analysis/pcc_reinterpretation.md` and `reports/pcc_historical_synthesis.md` directly from frozen A0/A1/A1b/A1c/A1r/B-light/contrast structured tables.
- [ ] Map each task to absolute, relative/structural, lexical/semantic, syntax/morphology, surface/domain, or ambiguous load.
- [ ] Separate observations consistent with unallocated position, genuine interaction, regularizer suppression, probe/metric sensitivity, and insufficient evidence.

Acceptance: frozen and amended gates remain distinct; every PCC family has an artifact-linked disposition; the memo concludes with testable predictions for M3/M4 and does not authorize a PCC branch.

### M3 — Task inventory, counterfactuals, and four frozen partitions
- [ ] Add `analysis/label_inventory/task_inventory.tsv`, `shortcut_risks.tsv`, and a narrative README.
- [ ] Create/lock `.venv-atlas` and dependency/model/dataset revisions, then implement `scripts/build_atlas_data.py` and a deterministic config to download/materialize the declared corpora, build fixed-offset contexts, label all eligible subwords for absolute position and first subwords for word tasks, derive labels, assign stable base-sentence IDs, and log exclusions/fingerprints.
- [ ] Freeze document-grouped discovery fit, calibration selection, C1 G1, C2 G2, and final evaluation units; assert offset variants and duplicates remain in one group. Freeze discovery vocabularies and common coarse label maps.
- [ ] Generate partition-disjoint counterfactual templates and run structural, lexical-change, tokenizer-alignment, duplicate, leakage, and shortcut QA.
- [ ] Write `configs/atlas/task_manifest.json`, `transform_manifest.json`, `partition_hashes.json`, public split summaries, and a private final manifest guarded by an unlock file. Freeze all hashes before M5 scoring.

Acceptance: repeated builds are byte-identical; IDs/hashes do not overlap across roles or C1/C2; context packing/offset/truncation/subword rules pass fixtures; all primary confirmation tasks meet minimum class/sample rules or are marked ineligible before scoring; final unlock is absent and no final labels/scores appear in run artifacts.

### M4 — Freeze preregistration and minimal synthetic gate
- [ ] Write `prereg/separable_information_atlas_v1.md` with exact data hashes, fit/selection/C1/C2 units, tasks, context/subword rules, common labels/vocabularies, ranks, metrics, denominator eligibility, baseline selection, fixed L3/descriptive L4 role, G1/G2 thresholds, BH families, hierarchical resampling budgets, stop/retry rules, and final-blinding policy.
- [ ] Include an exhaustive joint G1×G2 decision table with equivocal as highest-precedence stop: (a) any ineligible/underpowered/boundary-crossing/conflicting primary result → equivocal; (b) simple-baseline simultaneous equivalence with at least two eligible families → existing/simple; (c) broad/split G1 plus existing K=2 failure of the corresponding family recovery/leakage topology and simple non-equivalence → learned-model; (d) broad/split G1 plus existing K=2 passage of all topology/component gates → existing-checkpoint; (e) no-expansion becomes supported negative-atlas only when simultaneous upper bounds for every proposed new-family effect lie below the `0.20` minimum selectivity margin, the design has `>=80%` sensitivity for that effect, and G2 shows no learned new-family advantage; otherwise it is equivocal. Non-rejection alone can never yield negative-atlas.
- [ ] Record the preregistration/manifests/code/config digest before neural scoring in a freeze record and have an independent adversarial review quote that digest into the externally retained review transcript. If RFC-3161/OpenTimestamps is available, also store its receipt; lack of third-party timestamp is a stated limitation, not permission to modify the frozen bundle.
- [ ] Implement shared metric/statistics code and synthetic fixtures for separable, overlapping, shuffled, absent-family, near-zero-denominator, duplicate-cross-role, source-confound reversal, label-vocabulary leakage, imbalance, and train-only-standardization regimes.
- [ ] Run a compute pilot, enumerate expected refits/runtime/storage, verify the 500-refit/9,999-randomization Monte Carlo precision rule, and stop as underpowered/infeasible rather than silently reducing inference.
- [ ] Run the deterministic synthetic smoke and write `reports/synthetic_metric_smoke.md` plus machine-readable results.

Acceptance: the independent pre-score transcript contains the exact freeze digest; synthetic positive regimes pass recovery/selectivity, all leakage/negative regimes fail promotion, undefined denominators remain undefined, BH results match a reference calculation, the compute budget is locked, and any failure blocks M5.

### M5 — Raw L3/L4 architecture-selection atlas
- [ ] Run smoke extraction first, then full discovery/calibration/architecture-confirmation extraction for both frozen layers under one resolved config.
- [ ] Fit/freeze discovery task subspaces and calibration probe/baseline choices; open C1 only after the calibration freeze record exists. Fit no probe/scaler/subspace on C1 labels. Run L3 G1 as primary and L4 descriptively only.
- [ ] Emit raw task scores, normalized recovery/leakage/depletion, family geometry, random/PCA/permutation controls, shortcut audits, hierarchical intervals/p-values, BH decisions, and G1 report.

Acceptance: terminal run artifacts and hashes exist; L3/L4 results use identical examples; no final partition access; G1 chooses broad, split, no-expansion, or equivocal using only preregistered rules.

### M6 — Existing K=2 and simple-baseline audit
- [ ] Evaluate raw, pos-private, content-private, joint, additive residual, broad-position-scrubbed content, and the calibration-frozen simple baseline on the independent C2 confirmation groups for all four existing checkpoints. Fit no probe/scaler/subspace on C2 labels.
- [ ] Score position/content/structure/format counterfactuals token-aligned where valid; add random/sham and matched-magnitude controls.
- [ ] Measure frozen C2 suffix-model next-token CE and sentinel-task collateral for reconstruction, branch removal/scrubbing, and interventions; include CE- or reconstruction-matched random perturbations and simultaneous collateral bounds required by G2.
- [ ] Test residual joint/bilinear gains after broad-position stripping and the matched-seed g4/g7 regularizer sensitivity.
- [ ] Emit leakage, scrubbing, counterfactual, residual-PCC, per-checkpoint, and G2 reports.

Acceptance: every checkpoint is separate; g7 is a regularizer control, not a fourth replicate; inapplicable FVU is explicit; no final access; G2 uses only the calibration-frozen primary simple baseline and simultaneous bounds.

### M7 — Decision, claim review, and roadmap update
- [ ] Render `reports/architecture_decision.md/json` selecting exactly one of four distinct outcomes: learned-model, existing/simple, supported negative-atlas, or equivocal/no-decision.
- [ ] Route scientific conclusions through an independent research-claim review; weaken/block claims as required.
- [ ] Update `TODO.md` checkboxes/status and `RESULTS.md`/`ANALYSIS.md` with exact run/config/artifact paths and evidence class.
- [ ] Run repro-guard and record remaining limitations.

Acceptance: the decision follows G1/G2 mechanically, states whether new training is warranted, does not consume final test, and every supported claim maps to a logged artifact.

### M8 — Independent adversarial review and final verification
- [ ] Run `/adversarial` on the plan before implementation, after the data/prereg freeze, after result/decision artifacts, and on the final worktree; revise until SHIP or report a genuine blocker.
- [ ] Run deterministic tests, lint/type checks where supported, smoke paths, hash rebuild checks, no-final-access audit, path checks, registry completeness, and source-secret scan.

Acceptance: final adversarial verdict SHIP, all checks pass or documented non-code/tooling limitations are non-claim-affecting, and no M7 training job has started.

## Definition of done
- [ ] All eight user-requested steps are represented by completed, versioned artifacts; none is satisfied by prose alone where execution was requested.
- [ ] The dirty 1B state is reconstructable to the limit of available evidence, missing facts are explicit, the manifest is restored, current paths resolve, and checkpoints are correctly classified.
- [ ] PCC evidence is reinterpreted without retroactively changing frozen decisions or mistaking joint decodability for shared causality.
- [ ] Primary and sentinel tasks, shortcut risks, exclusions, data sources, stable IDs, and counterfactual QA are explicit.
- [ ] Discovery/calibration/architecture-confirmation/final roles are disjoint and hash-frozen before scoring; final remains unopened.
- [ ] Preregistered metrics and G1/G2 decisions are executable, multiplicity-controlled, and handle undefined metrics/underpowered cases without analyst discretion.
- [ ] Synthetic metrics pass planted positive and negative regression cases.
- [ ] Raw L3/L4 atlas and all-four-checkpoint K=2 audit complete under the same frozen task/representation/control protocol on independent C1 and C2 confirmation groups.
- [ ] A signed branch decision answers whether new model training is warranted; final claims survive independent claim and adversarial review.
- [ ] Runs/configs/data/code/environment/hardware/hashes are sufficient for another researcher to reproduce the architecture-selection results.

## Verification plan
- Plan: `.agent-workspace/bin/check-plan --path PLAN.md`, then independent `/adversarial PLAN.md` until SHIP.
- Unit/synthetic: `pytest -q tests/test_atlas_metrics.py tests/test_atlas_data.py`; run the synthetic CLI twice and compare hashes.
- Data firewall: rebuild manifests in a temporary directory; compare hashes; assert zero ID/content-hash intersection; assert no final unlock and grep all run logs for `partition=final`.
- Provenance: validate TSV schema/terminal rows; compare checkpoint metadata to summaries; `sha256sum -c` source/checkpoint lists; run relative-path checker.
- Experiment smoke: tiny data/config on CPU where possible and one GPU extraction batch; confirm resolved config, seed, hashes, metrics, and completion marker.
- Full results: validate result schemas, finite/undefined handling, comparator coverage, BH reference calculation, and gate renderer determinism.
- Repro guard: seed/path/secret/environment/data-version checks from the skill output contract.
- Claims: independent research-claim review over the decision and reports; no positive claim if review is BLOCK.
- Final: tests + diff check + final `/adversarial work` review; verify zero active training processes.

## Risks and one-way doors
- **Final-test contamination (one-way):** any score inspection permanently consumes the blind set. Mitigation: private manifest, absent unlock, run-mode guard, log audit, and no M8 invocation.
- **Post-hoc preregistration:** neural scoring before the prereg hash invalidates confirmation. Mitigation: synthetic-only code validation first; write/freeze a timestamped hash record before M5.
- **Reconstructed provenance overconfidence:** mtime and current diff strongly constrain but do not mathematically prove historical bytes. Mitigation: label reconstruction confidence per field and never call it exact where evidence is indirect.
- **Cross-corpus label drift:** UD/NER corpora differ in annotation and domain. Mitigation: coarse common labels, source-disjoint confirmation, class eligibility rules, and explicit dataset limitation.
- **Token identity shortcut:** lexical and syntax tasks can be memorized. Mitigation: held-out corpora/lemmas, ambiguous-token and matched-token analyses, and frequency/surface controls.
- **Probe subspace circularity:** the same tasks cannot construct and confirm. Mitigation: discovery weights only; calibration selection only; independent confirmation scoring.
- **Checkpoint comparison pseudoreplication:** three regularized seeds plus g7 are not four exchangeable seeds. Mitigation: per-checkpoint reporting and matched g4/g7 control interpretation only.
- **Compute interruption:** full probes may outlast one turn. Mitigation: cached activations, resumable per-stage artifacts, terminal markers, and no claims from partial runs.
- **Working-tree collision:** the repository already contains user/uncommitted research work. Mitigation: do not reset/clean; restrict edits to named new artifacts and intentional path fixes, and record the starting status.

## Deviations log
- 2026-07-31: No deviations yet. Design ledger was silent; assumptions A1–A10 are recorded above.
