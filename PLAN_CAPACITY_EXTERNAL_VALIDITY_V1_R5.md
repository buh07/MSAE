# Capacity/External Validity v1 r5 — technical compatibility recovery

## Goal

Preserve the failed v1 namespace exactly, replace the unavailable `torch.flatnonzero` call in a separately versioned implementation, strengthen runtime-compatibility tests, and rerun the unchanged frozen capacity and conditional external studies against the exact existing payload hashes. This is a technical recovery, not a scientific retry or protocol change.

## Constraints

- Never modify, delete, resume, or relabel `capacity_controller_diagnostic_v1_20260810` or `trained_copy_external_v1_20260810`.
- Preserve the v1 technical terminal, all 27 partial checkpoints, logs, events, freezes, review binding, and external `BLOCKED_UNOPENED` result by exact hash.
- Reuse the existing capacity/external JSONL files by the payload hashes already stored in the v1 freezes; do not regenerate, inspect, or select rows during recovery preparation. Record panel-specific access truth: capacity train/development are `PRIORLY_OPENED_TECHNICAL_RECOVERY`, capacity confirmation is unopened, and every external panel is unopened. Never call the whole capacity bundle unopened.
- Preserve every generator seed, row seed, estimator, rank, learned seed, step count, metric, threshold, bootstrap seed, external authorization rule, and confirmation payload.
- New namespaces use suffix `r5`. No K2 path exists.
- Never resume, copy, import, or initialize from the 27 partial v1 checkpoints. R5 creates fresh models from the unchanged registered seeds and executes every registered step.
- Preserve the rejected pre-binding r2, r3, and r4 candidate manifests and their BLOCK verdicts. None performed a scientific run or created a recovery binding, freeze, or result; none is reused.
- Candidate setup must reject every attempt to read, hash, stat, or glob **any** `.jsonl`, including payloads from earlier studies referenced by preservation manifests.

## Technical change

Replace only `torch.flatnonzero(tt == target)[0]` with a compatibility helper based on `torch.nonzero(mask, as_tuple=False).reshape(-1)` that:

1. requires a one-dimensional Boolean mask;
2. requires at least one match;
3. returns the first index deterministically;
4. works on the installed PyTorch CPU and CUDA builds.

Add an explicit `empirical_jacobian_ranks` helper and execute the real TargetMLP-to-Jacobian path for all 16 target IDs in nonpanel CPU and GPU tests, so the exact path that failed in v1 runs before locking. Search the full r5 source for other unavailable Torch/NumPy APIs, test all model-family fit paths for at least one step/rank, and execute one full nonpanel instance through fit plus development scoring.

## Recovery lineage and lifecycle

1. Write a create-once failure-preservation manifest without reading any scientific JSONL. It must attest: capacity train/development open events present; development-complete, confirmation-open, and capacity final absent; external ACCESS/TRAIN events absent; and external `BLOCKED_UNOPENED` flags true.
2. Create r5 configs whose scientific sections are byte-equivalent to v1 and whose only differences are namespace/runtime/recovery-lineage fields. Verify every common top-level function/class against v1. Derive the expected r5 `fit_methods`, `capacity_pipeline`, and `external_pipeline` ASTs by applying only the registered literal compatibility/lifecycle replacements to the frozen v1 source, rather than trusting digests generated from r5 or broadly exempting the pipelines. Any other change fails. Scan the complete r5 AST and reject `torch.load`, `load_state_dict`, or equivalent restore calls.
3. Candidate preflight verifies the v1 freeze hashes, failure terminal, 27 partial checkpoints, external unopened flags, payload-hash continuity, config scientific parity, and absence of r5 result/provenance/tmux/GPU-lock namespaces. Every M1–M4 preparation command (candidate, binding, freezing, freeze verification, and review binding) executes under the same fail-closed all-JSONL guard. The guard intercepts built-in/Path/`os.open`, bytes and text paths, stat/lstat, Path helpers, standard-library `glob`/`iglob`, Path glob/rglob, listdir, scandir, and subprocess arguments. Standard-library glob/iglob, workspace/temp listdir, and rglob are forbidden; scandir is allowed only for the exact `/tmp` lock-root used by the exact GPU-lock glob.
4. Obtain `/adversarial` SHIP on the plan and exact candidate.
5. Create both r5 recovery bindings before any r5 payload access. They are explicitly `payloads_preexisting=true` and `recovery_binding=true`, transitively bind both original v1 locks/freezes, both candidate hashes, and the v1 failure-preservation hash, and never claim to predate payload creation.
6. Create r5 freezes from reviewed source/config/recovery bindings plus the existing opaque PANEL_METADATA/PREPARED records. Capacity freeze status is panel-specific (`train/dev PRIORLY_OPENED_TECHNICAL_RECOVERY`, confirmation unopened); external freeze status is unopened. Do not stat, glob, hash, or read JSONL.
7. Obtain `/adversarial` SHIP on both exact freezes and bind the reviews.
8. Atomically create the UUID lock with `mkdir`, select that free GPU, and set `CUDA_VISIBLE_DEVICES` to the UUID. Pass the lock path/token and tmux pane-shell PID into the worker; require the Python worker PID ancestry to contain that pane PID and require `nvidia-smi` to map that exact Python PID to the locked UUID. Launch once, verify correctly ordered access/open events, then return with an ETA.

The durable capacity final is the sole external authorization input: r5 rereads it from disk, requires exact equality with the in-memory result, and writes `PRECHECK_NO_ACCESS` before deciding. If false, it writes `BLOCKED_UNOPENED`; if true, it writes `ACCESS_MAY_HAVE_OCCURRED` before the first external read. Every capacity and external panel writes its access event before its read and `OPENED` only after the read succeeds. The worker initializes its terminal paths and outer failure boundary before launch-preflight, freeze/binding revalidation, UUID/lock checks, pane ancestry, or CUDA PID verification. Any failure before external access emits `BLOCKED_UNOPENED`; a failure after access may have occurred emits `TECHNICAL_FAILURE_AFTER_ACCESS`. Both cases also receive durable technical-terminal events. Do not silently patch or retry the namespace.

## Milestones

- [ ] **M1 — Preserve failure.** Create and verify an exact nonpayload manifest of v1 code/config/freeze/reviews/results/provenance/partial checkpoints, panel-specific access/absence facts, and already frozen payload hashes without accessing JSONL.
- [ ] **M2 — Implement compatibility recovery.** Preserve the rejected r2/r3/r4 candidates, then add r5 source/config/launcher/tests with exact scientific parity, fail-closed JSONL protection, UUID-to-process validation, and compatibility helper coverage.
- [ ] **M3 — Candidate adversarial gate.** Pass syntax, tests, CPU/GPU family smokes, full nonpanel-instance smoke, mutation suite, and exact candidate `/adversarial` SHIP before r5 locks.
- [ ] **M4 — Bind and freeze existing payload lineage.** Create both pre-access recovery bindings with `payloads_preexisting=true`, create panel-specific opaque freezes referencing unchanged payload hashes, receive exact-freeze SHIP, and bind reviews.
- [ ] **M5 — Launch and estimate.** Start tmux on a free UUID-verified GPU, confirm live progress, estimate ETA from completed checkpoint/event timestamps, and return without waiting.

## Definition of done

- V1 remains byte-unchanged and externally blocked/unopened.
- R5 differs scientifically from v1 by zero config fields and differs in code only by compatibility, recovery/lifecycle hardening, tests, and namespaces. Exact `fit_methods` AST hashes make the approved one-call replacement machine-checkable.
- The formerly failing nonlinear/Jacobian path passes on the installed CPU and selected CUDA device before launch.
- All 27 v1 checkpoint hashes remain preservation evidence only; source scanning forbids restore APIs, output preflight rejects preexisting r5 checkpoints/namespaces, and every r5 checkpoint is freshly initialized from unchanged registered seeds in a distinct r5 path. Fit records must report every registered step.
- Exact candidate and exact opaque freezes have independent SHIP reviews.
- The r5 tmux owner is alive, capacity train/development are opened, and a CUDA process is visible on the recorded UUID.
- The user receives a measured ETA; the session does not wait for results.

## Verification plan

- Run: `python -m py_compile scripts/capacity_external_validity_v1_r5.py` — expected: exit 0.
- Run: `bash -n scripts/launch_capacity_external_validity_v1_r5_tmux.sh` — expected: exit 0.
- Run: `pytest -q tests/test_capacity_external_validity_v1_r5.py` — expected: compatibility, parity, lineage, mutation, and launcher tests pass.
- Run: `python scripts/capacity_external_validity_v1_r5.py mutation-suite` — expected: all inherited and recovery-specific mutations pass without scientific payload access.
- Run: `python scripts/capacity_external_validity_v1_r5.py verify-parity` — expected: every non-allowlisted config JSON pointer matches v1 and the source diff contains only allowlisted recovery/compatibility changes.
- Run: `CUDA_VISIBLE_DEVICES=$GPU CUBLAS_WORKSPACE_CONFIG=:4096:8 python scripts/capacity_external_validity_v1_r5.py candidate-preflight --device cuda` — expected: every registered model-family path and the empirical-Jacobian path pass on nonpanel data; v1/r5 scientific parity and failure preservation pass without any JSONL access.
- Run: `python scripts/capacity_external_validity_v1_r5.py verify-freezes --opaque` — expected: both freezes pass without JSONL access.
- Inject launch-preflight and GPU-validation failures separately — expected: both provenance terminals and external `BLOCKED_UNOPENED` are written with no access event; direct bytes-path open, `os.open`, standard glob/iglob, nonallowlisted `scandir`, `listdir`, and JSONL access attempts are rejected.
- Run: `tmux has-session -t capacity_external_validity_v1_20260810r5 && nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv,noheader` — expected: live session and selected UUID process.

## Phase-indexed namespace matrix

| Phase | Must exist | Must be absent |
|---|---|---|
| Candidate | r5 plan + plan review; preserved v1 and rejected-r2/r3/r4 manifests | candidate manifests/reviews, recovery bindings, freezes/reviews, review binding, outputs, provenance, launcher log, GPU locks, tmux session |
| Recovery binding | both exact candidate manifests + both candidate SHIP reviews | both recovery bindings, freezes/reviews, review binding, outputs, provenance, launcher log, GPU locks, tmux session |
| Freeze | both recovery bindings | both freezes/reviews, review binding, outputs, provenance, launcher log, GPU locks, tmux session |
| Review binding | both freezes + both exact-freeze SHIP reviews | review binding, outputs, provenance, launcher log, GPU locks, tmux session |
| Launch | all reviewed candidate/binding/freeze artifacts + review binding | outputs, provenance, launcher log, GPU locks, tmux session |

Revalidate the full nonpayload v1 preservation inventory, original locks/freezes/review binding, rejected-r2/r3/r4 manifests, and exact r5 candidate bindings at recovery binding, freeze, and immediately before launch. Any mismatch is a hard stop. The launcher then atomically creates one UUID lock and one tmux session; the worker proves lock-token ownership, pane ancestry, exact worker PID, and GPU UUID before creating mutable result namespaces.
