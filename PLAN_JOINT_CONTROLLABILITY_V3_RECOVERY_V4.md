# PLAN — v3 analysis recovery and corrected context-retrieval benchmark v4

## Goal

Preserve the completed joint-controllability v3 namespace byte-for-byte, recover its frozen
aggregation in a new analysis-only namespace, review the resulting claim, and launch a separately
versioned context-retrieval benchmark whose method workers are blocked unless an opened-development
task gate establishes strong target effects and weak matched-sham effects.

## Constraints

- Never write under `results/joint_controllability_benchmark_v3_20260808`.
- Recovery performs no model forward and accepts only the exact frozen v3 config, freeze, worker
  completions, metric hashes, zero-byte result, and traceback hashes.
- Preserve v3 estimators, thresholds, groupings, bootstrap draws, and seeds exactly.
- Do not train K2, an SAE, a supervised dictionary, or language-model parameters.
- The v4 task is a new controlled-natural context-retrieval estimand, not a retry or relabeling of
  the failed v3 continuation task.
- v4 test panels are document-disjoint from v3 and from v4 opened development panels.
- WIKI_CTX_A/B remain partitions of Wikitext, so any transfer is within-corpus only.

## Milestones

- [ ] **Analysis recovery** — hash-bind v3 inputs, reconstruct the exact aggregate with native JSON
   scalars, and write a new signed result namespace that records the original failure.
- [ ] **Claim review** — independently review the recovered evidence and explicitly distinguish task
   ineligibility from method failure.
- [ ] **Corrected task candidate** — construct a deterministic key-value retrieval task embedded in
   unused natural Wikitext passages. Full, base, and sham prefixes are token-length matched; base
   and sham carry the same answer under unrelated keys, isolating key binding from answer priming.
- [ ] **Opened-development gate** — on development rows only, require each model family and source to
   clear at least 85% target-effect eligibility and the preregistered sham-fraction bound. Failure
   writes a terminal and prevents every test/method worker from loading a model.
- [ ] **Fresh evaluation launch** — after candidate adversarial review and freeze, launch development
   gates, waiting test workers, positive control, and aggregate sessions in tmux on free GPUs; stop
   the interactive session after liveness is verified.

## Definition of done

- [ ] A before/after manifest proves every v3 file is unchanged.
- [ ] Recovery output is in a new namespace, has exact input hashes, contains no inference/training
  import or path, and reproduces 51,456 metric rows.
- [ ] The claim review does not describe zero joint passes as a method-level negative result.
- [ ] v4 rows use documents absent from v3, keep development/test documents disjoint, and provide exact
  full/base/sham token-length matching for every registered tokenizer.
- [ ] The v4 development gate is upstream of public-SAE loading and method scoring.
- [ ] v4 uses the same released methods, budgets, and joint method thresholds as v3. The new task
  adds a stronger development gate and defines sham fractions only on full-effect-eligible rows,
  with a frozen minimum eligible count, so permitted low-effect rows cannot cause ratio explosions.
- [ ] Frozen config, code, rows, reviews, assets, closure, and launch manifest are hash-bound.
- [ ] No K2/SAE/language-model training path exists.

## Risks

- Small models may not retrieve the bound value. This is a valid development-gate failure and must
  stop fresh evaluation rather than trigger template or threshold changes.
- The controlled key-value statement is semi-natural, not naturally occurring discourse. Report it
  as controlled-natural context retrieval and do not generalize to arbitrary natural context.
- Waiting workers share GPU assignments with short development-gate workers. They must remain CPU
  waiters until the combined development terminal exists.
- A passed within-corpus study still requires later cross-corpus confirmation.

## Verification plan

- [ ] Run `PYTHONPATH=scripts .venv-atlas/bin/python -m pytest -q tests/test_joint_controllability_v3_analysis_recovery.py tests/test_joint_controllability_benchmark_v4.py`.
- [ ] Run `.venv-atlas/bin/python -m py_compile scripts/recover_joint_controllability_v3_analysis.py scripts/joint_controllability_benchmark_v4.py`.
- [ ] Unit tests cover native-scalar serialization, v3 hash rejection, recovery non-overwrite, prompt
  matching, document exclusion, gate blocking, and no-training source scan.
- [ ] Run deterministic preparation twice in temporary namespaces and compare all JSONL hashes.
- [ ] Run independent `/adversarial` review of the exact recovery and v4 candidate; fix all blockers before
  freezing or launching.
- [ ] Launch only through the reviewed tmux launcher and verify session names, GPU UUIDs, and initial
  logs without waiting for scientific results.
