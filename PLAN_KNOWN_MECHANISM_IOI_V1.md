# Known-Mechanism IOI v1 — Endpoint and Intervention Positive Control

## Goal

Close the failed retrieval/agreement prompt-development line and begin a separately versioned study of an established causal task: indirect-object identification (IOI). First qualify the behavior, then validate the complete capture-and-patch pipeline with a full-residual positive control. Do not evaluate representation methods or train any model in this study.

## Constraints

- Preserve behavioral endpoint v6.2, its signed terminal, its thresholds, and the naturalistic endpoint closure byte-for-byte.
- Do not create v6.3, alter the failed endpoints, drop a model, open their confirmation panels, evaluate representation methods, or train a skyline/K2/relational model.
- The IOI development and confirmation panels, templates, vocabulary partitions, estimators, thresholds, layers, seeds, and decision logic are frozen before the first model forward.
- Development behavior is tested independently for GPT-2 small, Pythia-160M, and Gemma-2-2B. A general gate requires at least two distinct model families.
- Full-residual replacement is an end-to-end technical/causal positive control, not evidence that a sparse circuit or representation method succeeds.
- Confirmation is generated before inference, but its prompt JSONLs are neither parsed nor content-hashed by pre-gate workers and model forwards remain blocked until behavior and patch gates both pass in at least two families. The prescore manifest exposes only their frozen hashes.
- Candidate and exact frozen `/adversarial` reviews must return `SHIP` before launch.
- Launch uses UUID-pinned free GPUs in isolated tmux sessions and returns after live-or-clean-terminal handoff.

## Design

### Behavioral object

Each component has a base IOI prompt whose correct continuation is person A, a counterfactual that swaps the repeated giver and makes person B correct, and a same-answer sham that changes only the place and object. Names, places, objects, and templates are disjoint between development and confirmation. All answer names are one token in every tokenizer, and all three prompts within a component have identical tokenizer length.

For every row:

- `base_advantage = logit(A) - logit(B)`;
- `counterfactual_advantage = logit(B) - logit(A)`;
- `effect = min(base_advantage, counterfactual_advantage)`;
- `sham_ratio = |sham_advantage - base_advantage| / effect`.

A row is informative only when both directions are correct and `effect > 0.5`. Every vocabulary set must supply at least 14/16 informative rows and every template at least 56/64. The mean sham ratio must be at most 0.25 and its registered hierarchical-bootstrap 97.5% upper bound must be below 0.35. A model passes only if every template passes.

### End-to-end intervention positive control

After the development behavior gate, capture the final-token output of the frozen final transformer block. On the base prompt, replace that complete residual state with the matched counterfactual state or sham state. Define:

- `recovery = (base_advantage - counter_patch_advantage) / (base_advantage - natural_counter_advantage)`;
- `sham_movement = |base_advantage - sham_patch_advantage| / (base_advantage - natural_counter_advantage)`.

For every template, mean recovery must be at least 0.80 with a 2.5% lower bound above 0.60. Mean sham movement must be at most 0.20 with a 97.5% upper bound below 0.30. The same support rule applies. A model passes only if every template passes. The patch gate requires at least two families.

### Confirmation firewall

Confirmation uses held-out templates, names, places, and objects. It performs the same behavior and full-state intervention checks only after both development gates pass. A general positive result requires every confirmation template to pass in at least two model families. Regardless of outcome, this version never starts representation-method evaluation or training; it can only nominate a future separately frozen benchmark.

## Milestones

- [x] Record the endpoint closure in the paper and claim ledger; bind exact v6.2 and closure hashes.
- [x] Implement and test deterministic panel construction, estimators, hierarchical bootstrap, model-specific gates, capture/replacement hooks, waiters, terminal handling, and launch isolation.
- [x] Prepare tokenizer-only panels and cache attestation without model inference.
- [ ] Obtain candidate `/adversarial: SHIP`, freeze exactly once, obtain frozen `/adversarial: SHIP`, bind the review, and launch.

## Verification plan

- `python -m pytest -q -p no:cacheprovider tests/test_known_mechanism_ioi_v1.py`
- `python -m py_compile scripts/known_mechanism_ioi_v1.py`
- `bash -n scripts/launch_known_mechanism_ioi_v1_tmux.sh`
- Offline cache, preparation, preservation, preflight, and exact-freeze verification.
- Independent candidate and post-freeze adversarial review.
- Launch-time UUID/memory audit and live-or-clean-terminal validation for all expected jobs.

## Definition of done

- [ ] v6.2 and the closure artifacts remain exact and v6.3 does not exist.
- [ ] PAPER and claim ledger accurately scope v6.2; the claim verifier passes.
- [ ] Development and confirmation panels are vocabulary/template disjoint and tokenizer-valid across all models.
- [ ] Unit tests cover estimator signs, strict inequalities, support, bootstrap determinism, family logic, exact replacement, gate-before-model-load, failure/timeout propagation, namespace isolation, and no-method/no-training constraints.
- [ ] Candidate and frozen adversarial reviews are `SHIP` and exactly bound.
- [ ] Development behavior, gated patch, confirmation, two CPU gates, and final aggregator are live in tmux or have registered clean terminals.
- [ ] No representation benchmark or training process starts.

## Risks

- **Task does not transfer to all checkpoints:** eligibility is model-specific and an ineligible checkpoint remains a reported negative qualification result.
- **Patch success is tautological or overclaimed:** the full-residual replacement is explicitly only an end-to-end positive control; no sparse circuit claim is permitted.
- **Sham changes answer behavior:** same-answer shams are required to remain small both naturally and under patching.
- **Confirmation leakage:** held-out lexical/template inventories are frozen and stored separately; pre-gate workers verify only opaque manifest hashes and cannot parse the confirmation JSONLs or forward them before both gates authorize them.
- **Operational collision:** create-once namespaces, UUID guards, terminal waiters, and exact manifests prevent resumption or silent overwrite.

## One-way doors

The freeze and first model forward are one-way. Any frozen-review blocker retires the namespace without repair. Any failed gate blocks downstream stages. The study cannot authorize method evaluation or training by itself.
