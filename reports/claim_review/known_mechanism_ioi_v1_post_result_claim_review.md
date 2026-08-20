CLAIM: REVISE
SUMMARY: Development qualification failed; task absence, patch failure, and paper-strengthening claims exceed the measured evidence.

BLOCKERS
  - Claim 2 — `development/behavior/*/metrics.jsonl:1-256` — IOI behavior was represented: informative rows were GPT-2 227/256, Pythia 172/256, and Gemma 256/256. The registered **qualification gate** failed; the task itself did not simply fail or disappear.
  - Claim 3 — `development/patch/*/BLOCKED.json:1` and `gates/patch/result.json:1` — every patch worker stopped before model loading, with empty template results. Full-residual recovery and sham movement are unmeasured, so the positive-control pipeline cannot be called failed.
  - Claim 4 — `PLAN_KNOWN_MECHANISM_IOI_V1.md:5,13,44` — no representation method, intervention result, or confirmation evidence was produced. The development behavior result is consistent with a potency-versus-sham-robustness distinction, but does not strengthen an encoding/potency-versus-intervention-specificity conclusion.

REVISIONS
  - Claim 1: **SUPPORTED**, scoped to this exact frozen run. `gates/behavior/result.json:1` records zero eligible models/families: GPT-2 passed 1/4 templates, Pythia 0/4, and Gemma 1/4, under the registered every-template rule.
  - Claim 2: **BLOCK** as stated. Replace with: “All three pinned checkpoints failed the frozen development IOI qualification hierarchy despite substantial directional IOI behavior.”
  - Claim 3: **BLOCK**. Replace with: “The full-residual positive control was structurally blocked and remains unknown.”
  - Claim 4: **BLOCK**. At most report a descriptive endpoint-level analogy: Gemma had 256/256 informative rows but failed three templates on sham-ratio criteria.
  - Claim 5: **SUPPORTED only within this study/namespace**. `run.json:264-271`, both gate results, and `final/result.json:1` prohibit method evaluation/training and report neither occurred. This is not a permanent prohibition on a separately frozen future study.
  - `logs/behavior_gpt2.log:14-18`, `behavior_pythia160.log:14-20`, and `behavior_gemma2.log:15-21` warn that CuBLAS operations were nondeterministic because `CUBLAS_WORKSPACE_CONFIG` was unset, despite `run.json:250` declaring deterministic runtime. Avoid claims of exact numerical reproducibility.

EVIDENCE CHECKED
  - `configs/known_mechanism_ioi_v1/FREEZE.json:1` and frozen-review binding — all 26 inventory entries, config hash, freeze hash, and review hashes matched.
  - Behavior `COMPLETE.json` and raw metrics — 256 finite rows per model; registered metrics and activation hashes matched their completion manifests.
  - `gates/behavior/result.json:1` — measured negative qualification for all three pinned families.
  - Patch and confirmation `BLOCKED.json` terminals — structural stops before model/confirmation-row loading.
  - `gates/patch/result.json:1` and `final/result.json:1` — `DEVELOPMENT_STOP`, no positive control, no confirmation, methods, or training.
  - Runtime logs — no worker failure terminal, but deterministic-CuBLAS warnings were present.

UNKNOWNS
  - Full-residual recovery, sham movement, and hook behavior under patching.
  - Confirmation-panel behavior and cross-family replication.
  - Exact repeatability of forward-derived metrics given the CuBLAS warnings.
  - Generalization beyond these development templates and single pinned checkpoint per family.
