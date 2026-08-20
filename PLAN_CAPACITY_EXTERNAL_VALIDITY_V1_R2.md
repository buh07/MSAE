# Capacity/External Validity v1 r2 — technical compatibility recovery

## Goal

Preserve the failed v1 namespace exactly, replace the unavailable `torch.flatnonzero` call in a separately versioned implementation, strengthen runtime-compatibility tests, and rerun the unchanged frozen capacity and conditional external studies against the exact existing payload hashes. This is a technical recovery, not a scientific retry or protocol change.

## Constraints

- Never modify, delete, resume, or relabel `capacity_controller_diagnostic_v1_20260810` or `trained_copy_external_v1_20260810`.
- Preserve the v1 technical terminal, all 27 partial checkpoints, logs, events, freezes, review binding, and external `BLOCKED_UNOPENED` result by exact hash.
- Reuse the existing capacity/external JSONL files by the payload hashes already stored in the v1 freezes; do not regenerate, inspect, or select rows during recovery preparation. Record panel-specific access truth: capacity train/development are `PRIORLY_OPENED_TECHNICAL_RECOVERY`, capacity confirmation is unopened, and every external panel is unopened. Never call the whole capacity bundle unopened.
- Preserve every generator seed, row seed, estimator, rank, learned seed, step count, metric, threshold, bootstrap seed, external authorization rule, and confirmation payload.
- New namespaces use suffix `r2`. No K2 path exists.
- Never resume, copy, import, or initialize from the 27 partial v1 checkpoints. R2 creates fresh models from the unchanged registered seeds and executes every registered step.

## Technical change

Replace only `torch.flatnonzero(tt == target)[0]` with a compatibility helper based on `torch.nonzero(mask, as_tuple=False).reshape(-1)` that:

1. requires a one-dimensional Boolean mask;
2. requires at least one match;
3. returns the first index deterministically;
4. works on the installed PyTorch CPU and CUDA builds.

Add an explicit `empirical_jacobian_ranks` helper and execute the real TargetMLP-to-Jacobian path for all 16 target IDs in nonpanel CPU and GPU tests, so the exact path that failed in v1 runs before locking. Search the full r2 source for other unavailable Torch/NumPy APIs, test all model-family fit paths for at least one step/rank, and execute one full nonpanel instance through fit plus development scoring.

## Recovery lineage and lifecycle

1. Write a create-once failure-preservation manifest without reading any scientific JSONL. It must attest: capacity train/development open events present; development-complete, confirmation-open, and capacity final absent; external ACCESS/TRAIN events absent; and external `BLOCKED_UNOPENED` flags true.
2. Create r2 configs whose scientific sections are byte-equivalent to v1 and whose only differences are namespace/runtime/recovery-lineage fields. Verify parity using a frozen JSON-pointer allowlist; every non-allowlisted pointer/value must match exactly. Verify source parity with a compatibility-only textual diff allowlist covering filenames/namespaces, recovery verification, and `torch.flatnonzero` replacement/refactor only.
3. Candidate preflight verifies the v1 freeze hashes, failure terminal, 27 partial checkpoints, external unopened flags, payload-hash continuity, config scientific parity, and absence of r2 result/provenance namespaces.
4. Obtain `/adversarial` SHIP on the plan and exact candidate.
5. Create both r2 recovery bindings before any r2 payload access. They are explicitly `payloads_preexisting=true` and `recovery_binding=true`, transitively bind both original v1 locks/freezes, both candidate hashes, and the v1 failure-preservation hash, and never claim to predate payload creation.
6. Create r2 freezes from reviewed source/config/recovery bindings plus the existing opaque PANEL_METADATA/PREPARED records. Capacity freeze status is panel-specific (`train/dev PRIORLY_OPENED_TECHNICAL_RECOVERY`, confirmation unopened); external freeze status is unopened. Do not stat, glob, hash, or read JSONL.
7. Obtain `/adversarial` SHIP on both exact freezes and bind the reviews.
8. Select a free UUID-locked GPU, launch once in a new tmux session, verify train/development opening and a live CUDA PID, then return with an ETA.

If r2 fails before external access, write a technical terminal and `BLOCKED_UNOPENED` external result. Once `ACCESS_MAY_HAVE_OCCURRED` is durably written, no failure path may describe external as unopened. Every capacity/external stage uses the same pre-access/access/terminal journal state machine. Do not silently patch or retry the namespace.

## Milestones

- [ ] **M1 — Preserve failure.** Create and verify an exact nonpayload manifest of v1 code/config/freeze/reviews/results/provenance/partial checkpoints, panel-specific access/absence facts, and already frozen payload hashes without accessing JSONL.
- [ ] **M2 — Implement compatibility recovery.** Add r2 source/config/launcher/tests with exact scientific parity and compatibility helper coverage.
- [ ] **M3 — Candidate adversarial gate.** Pass syntax, tests, CPU/GPU family smokes, full nonpanel-instance smoke, mutation suite, and exact candidate `/adversarial` SHIP before r2 locks.
- [ ] **M4 — Bind and freeze existing payload lineage.** Create both pre-access recovery bindings with `payloads_preexisting=true`, create panel-specific opaque freezes referencing unchanged payload hashes, receive exact-freeze SHIP, and bind reviews.
- [ ] **M5 — Launch and estimate.** Start tmux on a free UUID-verified GPU, confirm live progress, estimate ETA from completed checkpoint/event timestamps, and return without waiting.

## Definition of done

- V1 remains byte-unchanged and externally blocked/unopened.
- R2 differs scientifically from v1 by zero config fields and differs in code only by compatibility, recovery lineage, tests, and namespaces.
- The formerly failing nonlinear/Jacobian path passes on the installed CPU and selected CUDA device before launch.
- All 27 v1 checkpoint hashes remain preservation evidence only; every r2 checkpoint is freshly initialized and has a distinct r2 path and lineage.
- Exact candidate and exact opaque freezes have independent SHIP reviews.
- The r2 tmux owner is alive, capacity train/development are opened, and a CUDA process is visible on the recorded UUID.
- The user receives a measured ETA; the session does not wait for results.

## Verification plan

- Run: `python -m py_compile scripts/capacity_external_validity_v1_r2.py` — expected: exit 0.
- Run: `bash -n scripts/launch_capacity_external_validity_v1_r2_tmux.sh` — expected: exit 0.
- Run: `pytest -q tests/test_capacity_external_validity_v1_r2.py` — expected: compatibility, parity, lineage, mutation, and launcher tests pass.
- Run: `python scripts/capacity_external_validity_v1_r2.py mutation-suite` — expected: all inherited and recovery-specific mutations pass without scientific payload access.
- Run: `python scripts/capacity_external_validity_v1_r2.py verify-parity` — expected: every non-allowlisted config JSON pointer matches v1 and the source diff contains only allowlisted recovery/compatibility changes.
- Run: `CUDA_VISIBLE_DEVICES=$GPU CUBLAS_WORKSPACE_CONFIG=:4096:8 python scripts/capacity_external_validity_v1_r2.py candidate-preflight --device cuda` — expected: every registered model-family path and the empirical-Jacobian path pass on nonpanel data; v1/r2 scientific parity and failure preservation pass.
- Run: `python scripts/capacity_external_validity_v1_r2.py verify-freezes --opaque` — expected: both freezes pass without JSONL access.
- Run: `tmux has-session -t capacity_external_validity_v1_20260810r2 && nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv,noheader` — expected: live session and selected UUID process.

Before any r2 binding/freeze/launch, absent-check every r2 candidate review, recovery binding, freeze, frozen review, review binding, output, provenance, launcher log, GPU lock, and tmux-session namespace. Any preexisting path is a hard stop.
