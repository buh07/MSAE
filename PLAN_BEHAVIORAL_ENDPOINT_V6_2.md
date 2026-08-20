# Behavioral Endpoint v6.2 — Batch-Accumulation Execution Recovery

## Goal

Run the unchanged v6 behavioral endpoint study in a new one-shot namespace after repairing the execution-only batching defect that terminated all six v6.1 development workers before any metric row was written. Preserve v6.1 as a formal technical failure and do not reinterpret it scientifically.

## Constraints

- v5, invalidated v6, and failed v6.1 remain immutable.
- v6.1 is preserved by an exact manifest containing its freeze, reviews, binding, launch provenance, logs, six worker failures, six confirmation blocks, two gate failures, and final failure.
- No v6.1 result or namespace is edited, deleted, resumed, or reused for output.
- Scientific rows, prompts, models, sources, estimands, thresholds, gates, bootstrap seeds, and confirmation rules are identical to v6.1.
- The only permitted code repairs are:
  1. `condition_logits` plus its `merge_condition_batches` helper: append every batch inside the batch loop and assert complete ordered row coverage;
  2. `final_aggregate`: classify an upstream gate failure directly rather than failing later on a missing `result.json`.
- No representation methods or training are present or authorized.
- Both candidate and exact post-freeze `/adversarial` reviews must be `SHIP`; any post-freeze blocker invalidates v6.2.
- Launch uses six currently free UUID-pinned GPUs and fifteen isolated tmux sessions. The operator stops after live-or-clean-terminal handoff.

## Approach

1. Hash-preserve the complete v6.1 terminal tree and verify its six identical `IndexError` signatures and absence of metric/complete artifacts.
2. Add a multi-batch regression oracle that fails under v6.1 and proves exact ordered accumulation under v6.2.
3. Add unhappy-path coverage for final aggregation after an upstream gate failure.
4. Enforce deep scientific-config equality against v6.1 and AST equality for every function outside the two registered repairs and lifecycle functions.
5. Recompute and directly freeze the recursive project-local dependency closure.
6. Run candidate adversarial review, fix all findings, freeze once, run post-freeze adversarial review, bind its exact hash, and launch.

## Milestones

### M1 — Recovery implementation

- New v6.2 config, script, tests, launcher, namespace, and v6.1 failure-preservation manifest.
- Batch regression and terminal propagation tests pass.
- Existing endpoint, V5, and v6/v6.1 tests continue to pass.

### M2 — Independent review and freeze

- Candidate `/adversarial` returns `SHIP` after any findings are fixed.
- Cache, preservation, preparation, dependency, code-equivalence, and one-shot preflights pass.
- Create and verify the immutable v6.2 freeze.
- Post-freeze `/adversarial` returns `SHIP` and is bound to the exact freeze hash.

### M3 — Launch

- Select six GPUs with under 4 GiB allocated memory.
- Record physical index and UUID mappings.
- Launch six development workers, six gated confirmation waiters, two endpoint gates, and one final aggregator.
- Confirm each expected job is live or has its registered clean terminal, then stop without waiting for results.

## Verification plan

- `.venv-atlas/bin/python -m pytest -q -p no:cacheprovider tests/test_behavioral_endpoint_v6_2.py tests/test_behavioral_endpoint_v6_1.py tests/test_behavioral_endpoint_v6.py tests/test_joint_controllability_assay_v5.py`
- `python -m py_compile scripts/behavioral_endpoint_v6_2.py`
- `bash -n scripts/launch_behavioral_endpoint_v6_2_tmux.sh`
- Offline `cache-preflight`, `preflight`, `freeze`, and `verify-freeze` commands using the v6.2 config.
- Independent candidate and post-freeze `/adversarial` reviews, including exact inventory, recursive imports, failure-tree membership, scientific equivalence, and launcher concurrency.
- Launch-time `nvidia-smi` UUID/memory audit and live-or-clean-terminal validation for all fifteen tmux jobs.

## Definition of done

- [ ] v6.1 terminal artifacts and freeze verify byte-for-byte, exact tree membership is enforced, and they remain untouched.
- [ ] The failure is explicitly classified as technical and pre-metric.
- [ ] A multi-batch test verifies all batches, order, and output shape; it would fail on v6.1.
- [ ] Runtime ordered-coverage validation rejects duplicate, missing, or misordered row indices.
- [ ] The final aggregator reports upstream gate failure directly rather than `FileNotFoundError`.
- [ ] The immutable launch manifest is never rewritten; handoff status is a separate create-once artifact.
- [ ] No scientific config/function changes exist outside the registered repair scope.
- [ ] All relevant tests, compilation, shell syntax, cache, and preservation checks pass.
- [ ] Candidate and frozen reviews are `SHIP` and the frozen review is hash-bound.
- [ ] Fifteen v6.2 tmux sessions start on six free UUID-pinned GPUs, or an expected clean terminal already exists at handoff.
- [ ] No training or representation benchmark starts.

## Risks

- **Partial batching or reordered rows:** exact fake-model multi-batch oracle plus runtime coverage assertions.
- **Outcome-conditioned scientific drift:** deep config comparison and per-function AST comparison.
- **Lost failed-run provenance:** complete terminal/log manifest verified on every preflight and worker.
- **Hidden dependency drift:** recursive local import closure frozen directly.
- **Secondary technical failure:** independent hostile review and explicit upstream-terminal tests.

## One-way doors

The v6.2 freeze and model forwards are one-way. A post-freeze blocker invalidates the namespace; no frozen artifact is edited. Confirmation remains sealed unless its exact endpoint/model development gate passes.
