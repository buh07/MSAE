CLAIM: REVISE

SUMMARY: Development supports exact execution and pair-level attention/ablation effects, not end-to-end validation, confirmation, or method claims.

BLOCKERS
  - `results/canonical_induction_circuit_v1_1_20260809/final/result.json:1` — formal status is `DEVELOPMENT_STOP`, confirmation is null, and `technical_positive_control_confirmed` is false — do not claim successful canonical-circuit recovery or end-to-end pipeline validation.
  - `development_gate/result.json:1` — recovery `0.1399 [0.1205, 0.1607]` missed the frozen point threshold `0.25`; selectivity `0.0856 [0.0650, 0.1062]` missed `0.15` — this supports a frozen magnitude-gate failure, not absence of recovery or donor specificity.
  - `scripts/canonical_induction_circuit_v1_1.py:440-467` — “necessity” is a graded two-logit margin decrement, and “sufficiency” is normalized partial margin recovery — ordinary-language claims of essentiality or behavioral sufficiency exceed these estimands.
  - `configs/canonical_induction_circuit_v1_1/run.json:151-160` and `final/result.json:1` — one GPT-2 revision, one development seed/panel, no representation methods, training, or linear controller — no broader encoding-versus-separability or linear-control result was tested.

REVISIONS
  - Report the positive result narrowly: all 128 development rows were informative; the prespecified head-pair mean attention was `0.9078 [0.8816, 0.9271]`, exceeding L5H0/L6H0 by `0.6316 [0.5968, 0.6634]`.
  - Describe causal evidence as a **joint ablation contribution**: L5H5/L6H9 zeroing reduced the clean target-versus-contrast margin by `0.7020 [0.4120, 1.0334]`, with differential effect `0.6661 [0.3361, 1.0800]` versus the control pair. The stored metrics do not establish either head individually as necessary.
  - Describe the negative conjunctively: the pair produced positive but too-small clean-donor recovery and sham selectivity under frozen thresholds. Cached raw margins additionally show patched margins remained negative on all 128 rows; this is descriptive, not a separately frozen endpoint.
  - State that the pipeline executed deterministic capture, joint ablation, final-position donor replacement, and aggregation successfully on development, but failed to validate the complete technical positive control.
  - Qualify the controls: L5H0/L6H0 were prospectively fixed same-layer comparators, not demonstrated matches on baseline attention, function, or other covariates; specificity beyond this single pair is untested.
  - Qualify the intervention: `scripts/canonical_induction_circuit_v1_1.py:388-433` patches only the final-token slice entering each layer’s `attn.c_proj`; it does not replace attention patterns, whole-sequence head activity, or the complete induction circuit.
  - The exact QA passed as frozen—bitwise-equal logits and known-head outputs on 16 repeated clean rows—but does not test repeated patch conditions, independent launches, or hardware portability.
  - The equal-block estimator was implemented exactly (`scripts/...:471-499`), and all eight blocks contributed 16 informative rows. Its 500-draw interval remains conditional on eight arbitrary generated-token blocks, one seed, and one model.
  - Treat the paper implication as methodological only: the result is qualitatively consonant with “causal contribution need not imply sufficient/selective control,” but adds no evidence about representation encoding, separability, SAE/projection performance, or supervised linear control.

EVIDENCE CHECKED
  - `PLAN_CANONICAL_INDUCTION_CIRCUIT_V1_1.md`; `PLAN_CANONICAL_INDUCTION_CIRCUIT_V1.md` — frozen objective, estimands, gates, and technical-only scope.
  - `configs/canonical_induction_circuit_v1_1/run.json` and `FREEZE.json` — frozen thresholds, heads, controls, model revision, seeds, equal-block weighting, single-model scope, and no-method rule.
  - Candidate/frozen adversarial reviews and `FROZEN_REVIEW_BINDING.json` — SHIP records and hashes matched the frozen artifacts.
  - Development `metrics.jsonl`, `QA.json`, `COMPLETE.json`, gate result, and final result — complete 128-row development evidence and formal STOP.
  - `confirmation/BLOCKED.json:1` and `scripts/...:594-620` — runtime confirmation firewall held: confirmation rows and model were not loaded after the development STOP. This does not mean the frozen confirmation file was never hashed during freeze/review.
  - `scripts/...:185-228,388-499,502-521` — generated panel, patch site, operational metric definitions, controls, and hierarchical bootstrap.
  - `PAPER.md:120-125,802-820,822-842` — claim discipline and broader paper scope; manuscript bytes remain identical to the bound prelaunch snapshot.

UNKNOWNS
  - Confirmation-panel replication on its disjoint token pool.
  - Generalization across prompt seeds, GPT-2 checkpoints, model families, GPUs, or natural language.
  - Separate effects of L5H5 and L6H9 and robustness against a broader matched/random head-control set.
  - Full-vocabulary correctness, collateral-logit effects, and circuit-wide sufficiency.
  - Whether low recovery reflects omitted circuit components, the final-position pre-`c_proj` patch site, or the chosen normalized two-logit metric.
  - Performance of any representation method, projection, SAE, supervised linear controller, or nonlinear controller.
