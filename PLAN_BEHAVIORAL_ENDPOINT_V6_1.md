# Behavioral Endpoint v6.1 — Dependency-Closure Recovery

## Goal

Launch the already-designed behavioral endpoint v6 assay in a new, one-shot namespace after repairing only the frozen executable dependency closure. Preserve the invalidated v6 freeze and its post-freeze `BLOCK` review as immutable provenance. Make no change to the scientific rows, estimands, thresholds, bootstrap seeds, endpoint gates, model panel, source panel, or confirmation firewall.

## Constraints

- v5 remains a completed exploratory failure. Its thresholds, rows, result, and unopened confirmation artifacts are hash-preserved and cannot be rescored or opened by this study.
- v6 remains permanently invalidated. Its freeze and post-freeze `BLOCK` review are imported by exact hash; v6 is never launched or modified.
- v6.1 is a dependency-closure-only recovery. Before freezing, it proves its scientific configuration equals v6 after removing versioned paths/provenance, and its non-lifecycle function ASTs equal v6.
- The recursive project-local Python import closure is frozen, including `joint_controllability_benchmark_v4_1.py`, `proxy_control_benchmark_v1.py`, and `proxy_control_benchmark_v2.py`.
- No representation methods and no training are present or authorized.
- Development uses the opened v5 panels. Confirmation uses the already prepared, document-disjoint DBpedia and IMDb panels and is opened endpoint/model-wise only after the unchanged development gates pass.
- A positive endpoint still requires at least two eligible model families and every registered template.
- Candidate and post-freeze adversarial reviews must both be `SHIP`. Any post-freeze `BLOCK` permanently invalidates v6.1.
- Launch is one-shot, offline, UUID-pinned, in isolated tmux sessions on six GPUs below 4 GiB allocated memory.

## Approach

1. Verify the invalidated v6 freeze and `BLOCK` report by their registered hashes and re-verify every file in the v6 frozen inventory.
2. Verify v5 preservation, prepared-row hashes, model-cache attestation, scientific config equivalence, and scientific function equivalence.
3. Compute the recursive local import closure from the v6.1/v6 executable entrypoints and freeze it directly rather than relying on transitive manifests.
4. Run an independent candidate adversarial review. Fix any findings before freezing.
5. Freeze v6.1 into a new namespace, verify it, and run an independent post-freeze adversarial review. Bind that review to the exact freeze hash outside the frozen inventory.
6. Launch six development workers, six gated confirmation waiters, two endpoint gates, and one final aggregator in tmux. Stop operator work after verifying every session is live or has a clean terminal.

## Milestones

### M1 — Recovery candidate

- Add recovery provenance and scientific-equivalence checks.
- Freeze recursive project-local imports.
- Add tests for the recovery chain, import closure, one-shot behavior, confirmation firewall, endpoint statistics, and terminal behavior.

### M2 — Candidate review and freeze

- Tests, compile checks, shell syntax, cache preflight, and candidate adversarial review pass.
- Create exactly one v6.1 freeze in the new namespace.

### M3 — Frozen review and launch

- Independent reviewer returns `SHIP` for the immutable freeze.
- Review binding matches exact freeze and report hashes.
- Launcher selects six free GPUs, records physical index/UUID mapping, and starts all 15 tmux sessions.

## Definition of Done

- The original v5 and invalidated v6 artifacts are unchanged and verify by exact hash.
- v6.1 records that v6 was invalidated and that no model forward occurred before this recovery.
- The scientific config and every non-lifecycle function are equivalent to v6.
- Every recursively resolved project-local Python dependency is in the v6.1 candidate inventory.
- The v6.1 freeze and both `SHIP` reports exist and verify; the binding records the exact immutable hashes.
- The one-shot output and provenance namespaces did not exist before launch.
- Fifteen v6.1 tmux jobs are launched on six currently free, UUID-pinned GPUs, or a job already produced its expected clean terminal during the initial handoff check.
- No representation benchmark or training is started.
- The operator returns immediately after launch status; results are not awaited.

## Risks

- **Hidden executable dependency:** mitigated by recursive AST import discovery plus a direct-inventory test.
- **Scientific drift disguised as recovery:** mitigated by deep config equality and per-function AST equality against frozen v6.
- **Confirmation leakage:** per-endpoint/model waiters cannot load a model until the unchanged development result authorizes that exact endpoint/model.
- **GPU remapping:** every worker sees one UUID and verifies it against `EXPECTED_GPU_UUID`.
- **Partial early exit:** launch handoff accepts only a live session or its prespecified clean terminal.

## One-way doors

Creating the v6.1 freeze and opening model inference are one-way. They occur only after both candidate checks and a post-freeze `SHIP`; a post-freeze `BLOCK` permanently invalidates v6.1 rather than permitting mutation.
